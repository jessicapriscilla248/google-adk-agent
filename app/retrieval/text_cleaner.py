"""Pembersihan teks ringan sebelum chunking/indexing.

Melakukan normalisasi seperti menghapus sintaks Markdown yang mengganggu (bold, inline code backtick, bullet marker) dan merapikan whitespace. 
Tidak mengubah istilah teknis, nama perintah, atau makna kalimat.
"""
import re

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_HEADING_MARK_RE = re.compile(r"^#+\s*", re.MULTILINE)
_BULLET_RE = re.compile(r"^[ \t]*[-*]\s+", re.MULTILINE)
_MULTI_BLANK_RE = re.compile(r"\n{3,}")
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")

def clean_text(text):
    text = _BOLD_RE.sub(r"\1", text)
    text = _INLINE_CODE_RE.sub(r"\1", text)
    text = _HEADING_MARK_RE.sub("", text)
    text = _BULLET_RE.sub("- ", text)
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = _MULTI_BLANK_RE.sub("\n\n", text)
    return text.strip()

def split_into_paragraphs(text):
    """Memecah teks bersih menjadi daftar paragraf non-kosong."""
    paragraphs = [p.strip() for p in text.split("\n\n")]
    return [p for p in paragraphs if p]
