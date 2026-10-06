"""
Memperluas query pencarian dengan kamus sinonim dan menambahkan chunk pelengkap dari dokumen top-1 hasil utama.
- Kamus sinonim (synonyms.json) berisi entri pemicu → istilah perluasan. Bila query cocok dengan pemicu, istilah perluasan ditambahkan ke query untuk meningkatkan
    skor cosine terhadap chunk target. Maksimal istilah perluasan unik yang ditambahkan ke query dibatasi oleh MAX_EXPANSION_TERMS (default 8).
- Chunk pelengkap (supplement) hanya diambil dari dokumen top-1 hasil utama, hanya dari dokumen troubleshooting (document_id diawali "ts-"), maksimal SUPPLEMENT_MAX_CHUNKS (default 2) chunk, dibatasi anggaran karakter total SUPPLEMENT_CHAR_BUDGET (default 1700) supaya token tambahan ke model tetap terkendali.
- Fungsi search_expanded() mengembalikan dict {"query": query, "status": status, "results": results}, sama kontrak keluaran dengan search() Phase 2,
  plus perluasan kamus sinonim dan chunk pelengkap. Status bisa "success", "no_relevant_results", atau "empty_query".
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from sklearn.metrics.pairwise import cosine_similarity

from .. import config
from .knowledge_base import get_index

_SYNONYMS_CACHE: list[dict] | None = None
_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)

def _normalize(text: str) -> str:
    text = text.lower()
    text = _PUNCT_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text

def load_synonyms(path: Path | None = None, force_reload: bool = False) -> list[dict]:
    """Muat `synonyms.json` sebagai singleton (mirip pola `knowledge_base.get_index`)."""
    global _SYNONYMS_CACHE
    if _SYNONYMS_CACHE is not None and not force_reload:
        return _SYNONYMS_CACHE
    synonyms_path = path or config.SYNONYMS_PATH
    if not synonyms_path.exists():
        _SYNONYMS_CACHE = []
        return _SYNONYMS_CACHE
    entries = json.loads(synonyms_path.read_text(encoding="utf-8"))
    _SYNONYMS_CACHE = entries
    return entries

def _matched_expansion_terms(query: str, entries: list[dict], max_terms: int) -> list[str]:
    """Cari istilah perluasan yang cocok dengan query, berdasarkan kamus entri pemicu → istilah perluasan. 
    Maksimal istilah perluasan unik yang ditambahkan ke query dibatasi oleh max_terms (default 8).
    """
    query_tokens = set(_normalize(query).split())
    if not query_tokens:
        return []

    matched_terms: list[str] = []
    for entry in entries:
        for pemicu_phrase in entry.get("pemicu", []):
            pemicu_tokens = _normalize(pemicu_phrase).split()
            if pemicu_tokens and all(tok in query_tokens for tok in pemicu_tokens):
                for term in entry.get("perluasan", []):
                    if term not in matched_terms:
                        matched_terms.append(term)
                break  # satu entri cukup dipicu sekali meski >1 pemicu cocok
    return matched_terms[:max_terms]

def _build_query_variants(query: str, entries: list[dict], max_terms: int) -> list[str]:
    """"
    function ini untuk membangun varian query pencarian dengan menambahkan istilah perluasan dari kamus sinonim.
    Jika tidak ada istilah perluasan yang cocok, kembalikan list berisi query asli saja. Jika ada istilah perluasan yang cocok, 
    kembalikan list berisi query asli dan query gabungan dengan istilah perluasan yang cocok. 
    Maksimal istilah perluasan unik yang ditambahkan ke query dibatasi oleh max_terms (default 8).
    """

    terms = _matched_expansion_terms(query, entries, max_terms)
    if not terms:
        return [query]
    return [query, f"{query} {' '.join(terms)}"]

def _combined_scores(variants: list[str], idx) -> list[float]:
    best = None
    for variant in variants:
        query_vec = idx.transform_query(variant)
        sims = cosine_similarity(query_vec, idx.matrix)[0]
        if best is None:
            best = sims
        else:
            best = [max(a, b) for a, b in zip(best, sims)]
    return list(best) if best is not None else []

def _select_supplement_chunks(
    main_results: list[dict],
    ranked_all: list[tuple[float, dict]],
    max_chunks: int,
    char_budget: int,
    document_prefix: str,
) -> list[dict]:
    if not main_results:
        return []
    top1_document_id = main_results[0]["document_id"]
    if not top1_document_id.startswith(document_prefix):
        return []

    already_included = {r["chunk_id"] for r in main_results}
    supplements: list[dict] = []
    used_chars = 0
    for score, chunk in ranked_all:
        if len(supplements) >= max_chunks:
            break
        if chunk["document_id"] != top1_document_id:
            continue
        if chunk["chunk_id"] in already_included:
            continue
        chunk_len = len(chunk["text"])
        if used_chars + chunk_len > char_budget:
            continue
        supplements.append({
            "chunk_id": chunk["chunk_id"],
            "document_id": chunk["document_id"],
            "title": chunk["title"],
            "category": chunk["category"],
            "text": chunk["text"],
            "url": chunk["url"],
            "score": round(float(score), 4),
        })
        already_included.add(chunk["chunk_id"])
        used_chars += chunk_len
    return supplements

def search_expanded(
    query,
    top_k=None,
    score_threshold=None,
    chunks_path=None,
    index=None,
    synonyms_path=None,
):
    """Sama kontrak keluaran dengan `app.retrieval.search.search`, plus
    perluasan kamus sinonim dan chunk pelengkap (lihat docstring modul)."""
    top_k = config.TOP_K if top_k is None else top_k
    score_threshold = config.SCORE_THRESHOLD if score_threshold is None else score_threshold

    query = (query or "").strip()
    if not query:
        return {"query": query, "status": "empty_query", "results": []}

    idx = index or get_index(chunks_path)
    entries = load_synonyms(synonyms_path)
    variants = _build_query_variants(query, entries, config.MAX_EXPANSION_TERMS)
    scores = _combined_scores(variants, idx)

    ranked = sorted(
        ((score, chunk) for score, chunk in zip(scores, idx.chunks)),
        key=lambda pair: pair[0],
        reverse=True,
    )

    main_results = []
    for score, chunk in ranked:
        if score < score_threshold:
            continue
        main_results.append({
            "chunk_id": chunk["chunk_id"],
            "document_id": chunk["document_id"],
            "title": chunk["title"],
            "category": chunk["category"],
            "text": chunk["text"],
            "url": chunk["url"],
            "score": round(float(score), 4),
        })
        if len(main_results) >= top_k:
            break

    status = "success" if main_results else "no_relevant_results"

    supplements = []
    if status == "success":
        supplements = _select_supplement_chunks(
            main_results,
            ranked,
            config.SUPPLEMENT_MAX_CHUNKS,
            config.SUPPLEMENT_CHAR_BUDGET,
            config.SUPPLEMENT_DOCUMENT_PREFIX,
        )

    return {"query": query, "status": status, "results": main_results + supplements}
