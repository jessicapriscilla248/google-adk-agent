"""Satu sumber konfigurasi untuk seluruh aplikasi, dibaca dari environment
variable dengan default yang masuk akal (sesuai Phase 2/Phase 3).

PENTING: mengimpor modul ini TIDAK boleh memerlukan `GOOGLE_API_KEY`. Modul ini
hanya membaca environment variable dan membangun objek konfigurasi; key API
hanya benar-benar dibutuhkan saat agent dijalankan lewat ADK/`google-genai`
(di luar scope modul ini).

Pergantian model = ubah environment variable `PRIMARY_MODEL`/`BACKUP_MODEL`.
Tidak ada logika auto-fallback di sini (keputusan Phase 4 Langkah 3) — memilih
model cadangan dilakukan manual oleh operator.
"""
import os
from pathlib import Path

from google.genai import types

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent

# gemini-3.5-flash-lite
PRIMARY_MODEL = os.environ.get("PRIMARY_MODEL", "gemini-3.5-flash-lite")
# Cadangan gemini-3.6-flash
BACKUP_MODEL = os.environ.get("BACKUP_MODEL", "gemini-3.6-flash")

# retrieval (TOP_K=3, SCORE_THRESHOLD=0.17)
TOP_K = int(os.environ.get("TOP_K", 3))
SCORE_THRESHOLD = float(os.environ.get("SCORE_THRESHOLD", 0.17))

# chunks untuk knowledge base
CHUNK_SIZE_CHARS = int(os.environ.get("CHUNK_SIZE_CHARS", 800))
CHUNK_OVERLAP_CHARS = int(os.environ.get("CHUNK_OVERLAP_CHARS", 150))
MIN_CHUNK_CHARS = int(os.environ.get("MIN_CHUNK_CHARS", 200))

# path data knowledge base 
KNOWLEDGE_BASE_DIR = Path(os.environ.get("KNOWLEDGE_BASE_DIR", str(PROJECT_ROOT / "data" / "knowledge_base")))
DOCUMENTS_DIR = KNOWLEDGE_BASE_DIR / "documents"
SOURCES_PATH = KNOWLEDGE_BASE_DIR / "sources.json"
CHUNKS_PATH = KNOWLEDGE_BASE_DIR / "chunks.json"
SYNONYMS_PATH = KNOWLEDGE_BASE_DIR / "synonyms.json"


# Maksimal istilah (cegah dilusi vektor TF-IDF bila banyak entri kamus cocok sekaligus).
MAX_EXPANSION_TERMS = int(os.environ.get("MAX_EXPANSION_TERMS", 8))
# Chunk pelengkap, hanya dari dokumen top-1 hasil utama, hanya dokumen troubleshooting
SUPPLEMENT_MAX_CHUNKS = int(os.environ.get("SUPPLEMENT_MAX_CHUNKS", 2))
SUPPLEMENT_CHAR_BUDGET = int(os.environ.get("SUPPLEMENT_CHAR_BUDGET", 1700))
SUPPLEMENT_DOCUMENT_PREFIX = os.environ.get("SUPPLEMENT_DOCUMENT_PREFIX", "ts-")

# parameter model gemini default tidak pakai thingking
PRIMARY_GENERATE_CONTENT_CONFIG = types.GenerateContentConfig(
    temperature=0.2,
    max_output_tokens=int(os.environ.get("PRIMARY_MAX_OUTPUT_TOKENS", 1024)),
)

# model gemini cadangan (backup) pakai thinking, karena model ini lebih besar dan lebih mahal, jadi dibatasi outputnya agar tidak boros token
BACKUP_GENERATE_CONTENT_CONFIG = types.GenerateContentConfig(
    temperature=0.2,
    max_output_tokens=int(os.environ.get("BACKUP_MAX_OUTPUT_TOKENS", 4096)),
    thinking_config=types.ThinkingConfig(
        thinking_budget=int(os.environ.get("BACKUP_THINKING_BUDGET", 1024)),
    ),
)

# Parameter main agent untuk memutuskan transfer_to_agent atau lanjut ke OUT_OF_SCOPE_MESSAGE apa adanya
MAIN_AGENT_GENERATE_CONTENT_CONFIG = types.GenerateContentConfig(
    temperature=0.0,
    max_output_tokens=int(os.environ.get("MAIN_AGENT_MAX_OUTPUT_TOKENS", 256)),
)
