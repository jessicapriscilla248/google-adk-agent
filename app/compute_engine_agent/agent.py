"""
Dipanggil oleh `main_agent` untuk menjawab pertanyaan troubleshooting Compute Engine. Model LLM yang dipakai sama dengan `main_agent`, tapi instruksi, tools, dan callback berbeda.
Menjawab pertanyaan troubleshooting dan konsep dasar Google Cloud Compute Engine berdasarkan knowledge base lokal 
"""
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from .. import config
from ..retrieval.search import search as _search_raw
from .prompt import COMPUTE_ENGINE_AGENT_INSTRUCTION, REFUSAL_MESSAGE
from .tools import _shape_response, search_knowledge_base

# untuk menolak pertanyaan yang jelas-jelas di luar scope Compute Engine (topik lain selain Compute Engine) tanpa diteruskan ke compute_engine_agent, lihat `main_agent/scope.py::check_scope` dan `main_agent/agent.py::scope_guard_callback`.
_NON_SUCCESS_STATUSES = ("no_relevant_results", "empty_query", "error")

# memaksa pemanggilan tool search_knowledge_base + fallback query mentah pengguna + penolakan bila hasil tool tetap kosong 
_FORCE_SEARCH_TOOL_CONFIG = types.ToolConfig(
    function_calling_config=types.FunctionCallingConfig(
        mode=types.FunctionCallingConfigMode.ANY,
        allowed_function_names=["search_knowledge_base"],
    )
)

def _extract_user_text(content: types.Content | None) -> str:
    if content is None or not content.parts:
        return ""
    return " ".join(part.text for part in content.parts if part.text)

def _shortcircuit_refusal_on_empty_retrieval(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    """function ini dipakai di compute_engine_agent untuk menolak pertanyaan yang jelas-jelas di luar scope Compute Engine (topik lain selain Compute Engine) tanpa diteruskan ke compute_engine_agent, dan memaksa pemanggilan tool search_knowledge_base + fallback query mentah pengguna + penolakan bila hasil tool tetap kosong.
    Return value:
        - LlmResponse dengan REFUSAL_MESSAGE bila pertanyaan jelas-jelas di luar scope Compute Engine (topik lain selain Compute Engine) atau bila hasil tool tetap kosong setelah fallback query mentah pengguna
        - None bila pertanyaan masih dalam scope Compute Engine (atau ambigu, sehingga perlu diteruskan ke compute_engine_agent untuk penolakan lebih lanjut)
    """
    if not llm_request.contents:
        return None
    last_content = llm_request.contents[-1]
    if not last_content.parts:
        return None

    found_tool_result = False
    for part in last_content.parts:
        function_response = part.function_response
        if function_response is None or function_response.name != "search_knowledge_base":
            continue
        found_tool_result = True
        status = (function_response.response or {}).get("status")
        if status in _NON_SUCCESS_STATUSES:
            raw_user_text = _extract_user_text(callback_context.user_content)
            if raw_user_text:
                fallback_result = _search_raw(raw_user_text)
                if fallback_result["status"] == "success":
                    function_response.response = _shape_response(fallback_result)
                    continue
            return LlmResponse(
                content=types.Content(
                    role="model", parts=[types.Part(text=REFUSAL_MESSAGE)]
                )
            )

    if found_tool_result:
        return None

    if llm_request.config is None:
        llm_request.config = types.GenerateContentConfig()
    llm_request.config.tool_config = _FORCE_SEARCH_TOOL_CONFIG
    return None

compute_engine_agent = LlmAgent(
    name="compute_engine_agent",
    model=config.PRIMARY_MODEL,
    description=(
        "Menjawab pertanyaan troubleshooting dan konsep dasar Google Cloud Compute Engine berdasarkan knowledge base lokal (Phase 1-2), dalam Bahasa Indonesia."),
    instruction=COMPUTE_ENGINE_AGENT_INSTRUCTION,
    tools=[search_knowledge_base],
    generate_content_config=config.PRIMARY_GENERATE_CONTENT_CONFIG,
    before_model_callback=_shortcircuit_refusal_on_empty_retrieval,
    # mencegah hop ke peer agent lain (misal `main_agent` atau `other_gcp_service_agent`) setelah compute_engine_agent menjawab, supaya SETIAP pesan pengguna baru selalu melewati main_agent lagi
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)
