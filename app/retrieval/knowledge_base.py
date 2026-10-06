"""
Function ini memisahkan tanggung jawab "memuat dan men-cache index" dari tanggung jawab "menghitung kemiripan dan memfilter hasil" di `search.py`.
"""
from .indexer import build_index
_INDEX_CACHE = None

def get_index(chunks_path=None, force_rebuild=False):
    """Mengembalikan `SearchIndex` singleton, membangunnya jika belum ada."""
    global _INDEX_CACHE
    if _INDEX_CACHE is None or force_rebuild:
        _INDEX_CACHE = build_index(chunks_path)
    return _INDEX_CACHE
