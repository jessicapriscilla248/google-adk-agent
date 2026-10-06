"""Tool ADK yang membungkus retrieval Phase 2 (`app.retrieval.search.search`).

ADK membaca docstring dan type hint fungsi ini untuk membangun deskripsi tool
yang dikirim ke model, sehingga keduanya ditulis lengkap dan akurat.

Phase 6 Langkah 1 (O7, efisiensi token runtime): keluaran yang dilihat model
dirampingkan — field `score`, `query` (top-level), dan `category` mentah
DIHAPUS (tidak pernah dibaca model, hanya dipakai internal/evaluasi); field
`status` dipertahankan apa adanya karena dipakai `before_model_callback` O6
di `agent.py`. Field `category` mentah diganti `kategori_label` Bahasa
Indonesia lewat `CATEGORY_LABELS` di bawah.

Phase 7 Langkah 4: panggilan retrieval UTAMA tool ini kini lewat
`search_expanded` (lapisan perluasan kamus sinonim + chunk pelengkap di
`app/retrieval/expand.py`), BUKAN `search()` Phase 2 langsung — kontrak
keluaran (`query`/`status`/`results`) identik, jadi `_shape_response` di
bawah tidak perlu berubah. `search()` asli TIDAK disentuh dan tetap dipakai
apa adanya oleh fallback query mentah O6e di `agent.py` (lihat Aturan Keras
Phase 7 no. 3 — `agent.py` sengaja tidak diubah).
"""
from .prompt import REFUSAL_MESSAGE
from ..retrieval.expand import search_expanded as _search

_NO_RESULTS_HINT = (
    "Tidak ada hasil yang cukup relevan di knowledge base untuk pertanyaan ini. "
    f"Gunakan kalimat penolakan baku berikut, apa adanya: \"{REFUSAL_MESSAGE}\""
)

# Label Bahasa Indonesia untuk tiap `category` mentah di chunks.json (10
# kategori yang ada di korpus per 2026-10-02 — lihat
# docs/architecture.md Bagian 10 poin 1 untuk cara verifikasinya). Kategori
# yang tidak dikenal (mis. korpus berubah di masa depan) -> label kosong,
# bukan error, supaya tool tidak pernah gagal karena mapping ini.
CATEGORY_LABELS: dict[str, str] = {
    "vm_lifecycle": "Siklus hidup VM",
    "networking": "Jaringan",
    "ssh_rdp": "SSH dan RDP",
    "iam_permission": "IAM dan izin akses",
    "disk_storage": "Disk dan penyimpanan",
    "quota": "Quota",
    "performance": "Performa",
    "general_troubleshooting": "Troubleshooting umum",
    "instance_configuration": "Konfigurasi instance",
    "firewall": "Firewall",
}


def _label_for_category(category: str) -> str:
    return CATEGORY_LABELS.get(category, "")


def _shape_response(result: dict) -> dict:
    """Ubah keluaran mentah `search()` (Phase 2, punya `score`/`category`
    mentah) ke kontrak O7 yang dilihat model (lihat docstring modul).

    Diekstrak jadi fungsi terpisah (Phase 6e) supaya `agent.py` bisa memakai
    ulang SHAPING yang sama persis saat menulis ulang `function_response`
    untuk fallback query mentah pengguna (lihat
    `_shortcircuit_refusal_on_empty_retrieval`), tanpa duplikasi logika.
    """
    response = {
        "status": result["status"],
        "results": [
            {
                "title": r["title"],
                "kategori_label": _label_for_category(r["category"]),
                "url": r["url"],
                "text": r["text"],
            }
            for r in result["results"]
        ],
    }
    if result["status"] != "success":
        response["message"] = _NO_RESULTS_HINT
    return response


def search_knowledge_base(query: str) -> dict:
    """Mencari jawaban di knowledge base Compute Engine berdasarkan kemiripan kata (TF-IDF).

    Panggil tool ini untuk SETIAP pertanyaan pengguna tentang Google Cloud
    Compute Engine sebelum menyusun jawaban apa pun. Jangan menjawab dari
    pengetahuan umum tanpa memanggil tool ini terlebih dahulu.

    Args:
        query: Pertanyaan pengguna dalam Bahasa Indonesia, disalin langsung
            (tidak perlu diterjemahkan atau diringkas terlebih dahulu).

    Returns:
        Dict dengan field:
          - status: "success" jika ada hasil relevan, "no_relevant_results"
            jika tidak ada hasil yang cukup relevan, "empty_query" jika query
            kosong, atau "error" jika terjadi kegagalan internal saat mencari.
          - results: list hasil (kosong jika status bukan "success"), masing-
            masing berisi title, kategori_label (Bahasa Indonesia, bisa
            kosong jika kategori tidak dikenal), url, dan text. Field url
            HANYA boleh disalin persis dari sini; jangan pernah mengarang URL.
          - message: hanya ada ketika status BUKAN "success" — berisi arahan
            eksplisit untuk memakai kalimat penolakan baku, jangan mengarang
            jawaban pengganti.
    """
    try:
        result = _search(query)
    except Exception as exc:  # noqa: BLE001 - tool tidak boleh melempar exception ke agent
        return {
            "status": "error",
            "results": [],
            "message": (
                f"Terjadi kegagalan internal saat mencari knowledge base ({exc}). "
                f"Gunakan kalimat penolakan baku berikut, apa adanya: \"{REFUSAL_MESSAGE}\""
            ),
        }

    return _shape_response(result)
