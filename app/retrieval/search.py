"""Retrieval sederhana berbasis TF-IDF + cosine similarity.

Alur: query -> TF-IDF vector (memakai vocabulary yang sama dengan korpus) ->
cosine similarity terhadap seluruh chunk -> urutkan menurun -> ambil top K ->
buang hasil yang skornya di bawah SCORE_THRESHOLD.

Skor adalah cosine similarity TF-IDF (0..1). Cari kecocokan kata, bukan kecocokan makna. 
Query yang memakai sinonim atau istilah berbeda dari dokumen bisa mendapat skor rendah meski secara
makna relevan, ini yang jadi keterbatasan dari penerapan TF-IDF sederhana.
"""
from sklearn.metrics.pairwise import cosine_similarity
from ..config import TOP_K as DEFAULT_TOP_K
from ..config import SCORE_THRESHOLD as DEFAULT_SCORE_THRESHOLD
from .knowledge_base import get_index

def search(query, top_k=DEFAULT_TOP_K, score_threshold=DEFAULT_SCORE_THRESHOLD, chunks_path=None, index=None):
    """Mengembalikan dict hasil retrieval dengan format yang konsisten:

    {
      "query": str,
      "status": "success" | "no_relevant_results" | "empty_query",
      "results": [
        {"chunk_id", "document_id", "title", "category", "text", "url", "score"}
      ]
    }
    """
    query = (query or "").strip()
    if not query:
        return {"query": query, "status": "empty_query", "results": []}

    idx = index or get_index(chunks_path)
    query_vec = idx.transform_query(query)
    sims = cosine_similarity(query_vec, idx.matrix)[0]

    ranked = sorted(
        ((score, chunk) for score, chunk in zip(sims, idx.chunks)),
        key=lambda pair: pair[0],
        reverse=True,
    )

    results = []
    for score, chunk in ranked:
        if score < score_threshold:
            continue
        results.append({
            "chunk_id": chunk["chunk_id"],
            "document_id": chunk["document_id"],
            "title": chunk["title"],
            "category": chunk["category"],
            "text": chunk["text"],
            "url": chunk["url"],
            "score": round(float(score), 4),
        })
        if len(results) >= top_k:
            break

    status = "success" if results else "no_relevant_results"
    return {"query": query, "status": status, "results": results}
