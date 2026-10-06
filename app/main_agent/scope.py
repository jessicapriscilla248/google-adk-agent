"""
Mencegat kasus yang di luar scope (layanan Google Cloud lain yang disebut tanpa kata kata dari isi Compute Engine).
"""
import json
import re
from .. import config

# daftar ini dipakai di check_scope() untuk mendeteksi pertanyaan yang jelas-jelas di luar scope Compute Engine, sehingga bisa langsung ditolak tanpa diteruskan ke compute_engine_agent.
_OTHER_GCP_SERVICES = (
    "cloud storage",
    "gcs",
    "bucket",
    "bigquery",
    "gke",
    "kubernetes engine",
    "cloud run",
    "cloud functions",
    "cloud sql",
    "pub/sub",
    "pubsub",
    "app engine",
    "firebase",
    "spanner",
    "bigtable",
    "dataflow",
    "vertex ai",
)

# daftar kata yang isinya berkaitan dengan Compute Engine, dipakai di check_scope() untuk menandai pertanyaan yang masih dalam scope Compute Engine
_COMPUTE_ENGINE_ANCHORS = (
    "compute engine",
    "gce",
    "vm",
    "virtual machine",
    "instance",
    "machine type",
    "disk vm",
    "boot disk",
    "persistent disk",
    "ssh",
    "rdp",
    "managed instance group",
    "instance group",
)

_PUNCTUATION_RE = re.compile(r"[^\w\s/]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")

def _normalize(text: str) -> str:
    lowered = text.lower()
    # normalisasi: hapus tanda baca, ganti whitespace beruntun jadi satu spasi, trim, dan tambahkan spasi di awal/akhir supaya pencarian kata/frasa bisa pakai " {kata} " (bukan regex word boundary \b yang tidak mengenali /).
    stripped = _PUNCTUATION_RE.sub(" ", lowered)
    collapsed = _WHITESPACE_RE.sub(" ", stripped).strip()
    return f" {collapsed} "


def check_scope(text: str) -> str:
    """function ini dipakai di main_agent.py untuk mendeteksi pertanyaan yang jelas-jelas di luar scope Compute Engine, sehingga bisa langsung ditolak tanpa diteruskan ke compute_engine_agent. 
    Return value:
        - "pass" jika pertanyaan masih dalam scope Compute Engine (atau ambigu, sehingga perlu diteruskan ke compute_engine_agent untuk penolakan lebih lanjut)
        - "out_of_scope" jika pertanyaan jelas-jelas di luar scope Compute Engine (misal menyinggung layanan Google Cloud lain seperti Cloud Storage, BigQuery, GKE, Cloud Run, atau topik tak terkait Google Cloud)
    """
    if not text or not text.strip():
        return "pass"

    normalized = _normalize(text)

    mentions_other_service = any(f" {service} " in normalized for service in _OTHER_GCP_SERVICES)
    if not mentions_other_service:
        return "pass"

    mentions_compute_engine = any(f" {anchor} " in normalized for anchor in _COMPUTE_ENGINE_ANCHORS)
    if mentions_compute_engine:
        return "pass"

    return "out_of_scope"

# deteksi pertanyaan ambigu yg terlalu singkat/umum (<= 8 token) untuk didiagnosis, sehingga diarahkan minta klarifikasi dulu (CLARIFY_MESSAGE) sebelum diteruskan ke compute_engine_agent.
# Empat syarat SEKALIGUS harus terpenuhi (lihat `check_ambiguous`):
#   (a) giliran PERTAMA sesi ini,
#   (b) pendek (<= _AMBIGUOUS_MAX_TOKENS token setelah normalisasi),
#   (c) memuat kata keluhan umum (_COMPLAINT_WORDS),
#   (d) TIDAK memuat istilah spesifik apa pun (pemicu synonyms.json, judul
#       12 topik, kode error HURUF_BESAR_GARIS_BAWAH, nomor port, atau frasa
#       definisional "apa itu").
_AMBIGUOUS_MAX_TOKENS = 8

_COMPLAINT_WORDS = ("masalah", "bermasalah", "error", "rusak", "kenapa", "bantu", "gagal", "tidak bisa",)

_DEFINITIONAL_PHRASES = ("apa itu",)

# kata yang khas dari judul topik trouble shooting
_TOPIC_TITLE_TERMS = (
    "ssh", "rdp", "firewall", "internet", "terhubung", "memblokir", "koneksi",
    "permission", "denied", "quota", "exceeded", "disk", "lambat", "startup",
    "konfigurasi", "jaringan", "diakses", "start",
)

_ERROR_CODE_RE = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")
_PORT_NUMBER_RE = re.compile(r"\bport\b\s*:?\s*\d{1,5}\b|\b\d{1,5}\b\s*/\s*(?:tcp|udp)\b", re.IGNORECASE)

def _load_synonym_trigger_phrases() -> tuple[str, ...]:
    """untuk menghindari duplikasi, setiap frase pemicu di-normalisasi (lowercase, hapus tanda baca, collapse whitespace) dan disimpan sebagai tuple unik. Hasilnya dipakai di check_ambiguous() untuk mendeteksi pertanyaan ambigu yang memuat istilah spesifik."""
    try:
        with open(config.SYNONYMS_PATH, encoding="utf-8") as f:
            entries = json.load(f)
    except (OSError, json.JSONDecodeError):
        return ()
    phrases = []
    for entry in entries:
        for phrase in entry.get("pemicu", []):
            phrases.append(_normalize(phrase).strip())
    return tuple(dict.fromkeys(p for p in phrases if p))

_SYNONYM_TRIGGER_PHRASES = _load_synonym_trigger_phrases()

def _has_specific_term(original_text: str, normalized: str) -> bool:
    if _ERROR_CODE_RE.search(original_text):
        return True
    if _PORT_NUMBER_RE.search(normalized):
        return True
    if any(f" {phrase} " in normalized for phrase in _DEFINITIONAL_PHRASES):
        return True
    if any(f" {term} " in normalized for term in _TOPIC_TITLE_TERMS):
        return True
    if any(f" {phrase} " in normalized for phrase in _SYNONYM_TRIGGER_PHRASES):
        return True
    return False

def check_ambiguous(text: str, is_first_turn: bool) -> bool:
    """untuk check_ambiguous(), syarat (a) giliran pertama ditentukan pemanggil, syarat (b) pendek ditentukan di sini, syarat (c) memuat kata keluhan umum ditentukan di sini, syarat (d) TIDAK memuat istilah spesifik ditentukan di sini."""

    if not is_first_turn:
        return False
    if not text or not text.strip():
        return False

    normalized = _normalize(text)
    tokens = normalized.split()
    if len(tokens) > _AMBIGUOUS_MAX_TOKENS:
        return False

    has_complaint = any(f" {w} " in normalized for w in _COMPLAINT_WORDS)
    if not has_complaint:
        return False

    if _has_specific_term(text, normalized):
        return False

    return True
