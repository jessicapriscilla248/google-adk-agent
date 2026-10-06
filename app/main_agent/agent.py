"""support_agent: LLM agent utama untuk Google Cloud Support Assistant.
- Mendelegasikan pertanyaan Compute Engine ke compute_engine_agent.
- Menolak pertanyaan di luar topik (topik lain selain Compute Engine) dengan jawaban standar OUT_OF_SCOPE_MESSAGE.
- Menolak pertanyaan ambigu (tidak jelas) dengan jawaban standar CLARIFY_MESSAGE.
- Menolak pertanyaan ambigu yang tidak jelas dengan jawaban standar CLARIFY_MESSAGE, kecuali pertanyaan itu jelas di luar topik (topik lain selain Compute Engine) — dalam hal ini langsung ditolak dengan OUT_OF_SCOPE_MESSAGE.
"""
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from .. import config
from ..compute_engine_agent.agent import compute_engine_agent
from .prompt import CLARIFY_MESSAGE, MAIN_AGENT_INSTRUCTION, OUT_OF_SCOPE_MESSAGE
from .scope import check_ambiguous, check_scope

def _extract_user_text(content: types.Content | None) -> str:
    if content is None or not content.parts:
        return ""
    return " ".join(part.text for part in content.parts if part.text)

def scope_guard_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    """Function ini dipanggil sebelum model dipanggil (0 request Gemini) untuk mencegat kasus JELAS di luar scope, lalu (bila masih "pass") kasus AMBIGU. 
    Keduanya sengaja konservatif (lihat scope.py) — kasus yang tidak yakin selalu diteruskan ke router LLM, yang akan memutuskan apakah perlu klarifikasi atau diteruskan ke sub-agent."""
    user_text = _extract_user_text(callback_context.user_content)
    if check_scope(user_text) == "out_of_scope":
        return LlmResponse(
            content=types.Content(
                role="model", parts=[types.Part(text=OUT_OF_SCOPE_MESSAGE)]
            )
        )
    # Jika masih "pass" (tidak jelas), periksa apakah perlu klarifikasi
    # Klarifikasi hanya diberikan bila pertanyaan ambigu, bukan bila pertanyaan jelas di luar scope (topik lain selain Compute Engine)
    # Kalau diluar scope, langsung ditolak dengan OUT_OF_SCOPE_MESSAGE.
    is_first_turn = len(callback_context.session.events) <= 1
    if check_ambiguous(user_text, is_first_turn):
        return LlmResponse(
            content=types.Content(
                role="model", parts=[types.Part(text=CLARIFY_MESSAGE)]
            )
        )
    return None

def build_main_agent(sub_agent: LlmAgent, use_guard: bool = True) -> LlmAgent:
    """
    Function ini membangun LLM agent utama (router) untuk Google Cloud Support Assistant.
    - Mendelegasikan pertanyaan Compute Engine ke compute_engine_agent.
    - Menolak pertanyaan di luar topik (topik lain selain Compute Engine) dengan jawaban standar OUT_OF_SCOPE_MESSAGE.
    - Menolak pertanyaan ambigu (tidak jelas) dengan jawaban standar CLARIFY_MESSAGE.
    - Menolak pertanyaan ambigu yang tidak jelas dengan jawaban standar CLARIFY_MESSAGE, kecuali pertanyaan itu jelas di luar topik (topik lain selain Compute Engine) — dalam hal ini langsung ditolak dengan OUT_OF_SCOPE_MESSAGE.
    """

    kwargs = dict(
        name="main_agent",
        model=config.PRIMARY_MODEL,
        description=("Router Google Cloud Support Assistant: memberikan pertanyaan Compute Engine ke compute_engine_agent, menolak topik lain."),
        instruction=MAIN_AGENT_INSTRUCTION,
        sub_agents=[sub_agent],
        generate_content_config=config.MAIN_AGENT_GENERATE_CONTENT_CONFIG,
    )
    if use_guard:
        kwargs["before_model_callback"] = scope_guard_callback
    return LlmAgent(**kwargs)

root_agent = build_main_agent(compute_engine_agent)
