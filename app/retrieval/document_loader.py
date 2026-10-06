"""Memuat dokumen mentah dari data/knowledge_base/documents/*.json.
"""
import json
from pathlib import Path

from ..config import DOCUMENTS_DIR as DEFAULT_DOCUMENTS_DIR
from ..config import SOURCES_PATH as DEFAULT_SOURCES_PATH

REQUIRED_FIELDS = {"document_id", "title", "category", "url", "text"}


def load_documents(documents_dir=None):
    """Mengembalikan list dict dokumen, diurutkan berdasarkan document_id."""
    documents_dir = Path(documents_dir) if documents_dir else DEFAULT_DOCUMENTS_DIR
    documents = []
    for path in sorted(documents_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = REQUIRED_FIELDS - data.keys()
        if missing:
            raise ValueError(f"Dokumen {path.name} kehilangan field wajib: {missing}")
        documents.append(data)
    if not documents:
        raise FileNotFoundError(f"Tidak ada dokumen ditemukan di {documents_dir}")
    return documents


def load_sources(sources_path=None):
    sources_path = Path(sources_path) if sources_path else DEFAULT_SOURCES_PATH
    data = json.loads(sources_path.read_text(encoding="utf-8"))
    return {s["id"]: s for s in data["sources"]}
