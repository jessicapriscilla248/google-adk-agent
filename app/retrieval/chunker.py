"""Memecah dokumen menjadi chunks siap-index.

dokumen dibersihkan (text_cleaner), lalu dipecah per baris (baris kosong dihapus). 
Baris di sini adalah satuan terkecil yang tidak dipecah lagi (kalimat atau item bullet utuh), sehingga penggabungan baris menjadi chunk tidak pernah memotong kalimat di tengah. 
Baris digabung sampai mendekati CHUNK_SIZE_CHARS, dengan overlap beberapa baris terakhir dibawa ke chunk berikutnya (CHUNK_OVERLAP_CHARS), supaya konteks tidak terputus total di batas chunk. \
Chunk terakhir yang terlalu pendek digabung ke chunk sebelumnya agar tidak ada chunk yang nyaris kosong.
"""
import json

from ..config import CHUNK_SIZE_CHARS, CHUNK_OVERLAP_CHARS, MIN_CHUNK_CHARS, CHUNKS_PATH
from .document_loader import load_documents
from .text_cleaner import clean_text

DEFAULT_CHUNKS_PATH = CHUNKS_PATH


def _lines_of(text):
    return [line.strip() for line in text.split("\n") if line.strip()]


def _chunk_lines(lines, chunk_size, overlap):
    """Mengelompokkan baris menjadi list-of-list-of-baris sesuai batas ukuran."""
    groups = []
    current = []
    current_len = 0
    for line in lines:
        line_len = len(line) + 1  # +1 untuk spasi penyambung
        if current and current_len + line_len > chunk_size:
            groups.append(current)
            # overlap: bawa baris-baris terakhir dari chunk sebelumnya
            overlap_lines = []
            overlap_len = 0
            for prev_line in reversed(current):
                overlap_len += len(prev_line) + 1
                overlap_lines.insert(0, prev_line)
                if overlap_len >= overlap:
                    break
            current = list(overlap_lines)
            current_len = sum(len(l) + 1 for l in current)
        current.append(line)
        current_len += line_len
    if current:
        groups.append(current)

    # Gabungkan chunk terakhir yang terlalu pendek ke chunk sebelumnya
    if len(groups) > 1:
        last_text_len = sum(len(l) for l in groups[-1])
        if last_text_len < MIN_CHUNK_CHARS:
            tail = groups.pop()
            # hindari duplikasi baris overlap yang sudah ada di akhir chunk sebelumnya
            existing = set(groups[-1])
            new_lines = [l for l in tail if l not in existing]
            groups[-1] = groups[-1] + new_lines
    return groups


def build_chunks(documents, chunk_size=CHUNK_SIZE_CHARS, overlap=CHUNK_OVERLAP_CHARS):
    chunks = []
    for doc in documents:
        cleaned = clean_text(doc["text"])
        lines = _lines_of(cleaned)
        if not lines:
            continue
        groups = _chunk_lines(lines, chunk_size, overlap)
        for idx, group in enumerate(groups, start=1):
            chunk_id = f"{doc['document_id']}::chunk-{idx:02d}"
            chunks.append({
                "chunk_id": chunk_id,
                "document_id": doc["document_id"],
                "title": doc["title"],
                "category": doc["category"],
                "text": " ".join(group),
                "url": doc["url"],
                "source_ids": doc.get("source_ids", []),
            })
    return chunks


def main():
    documents = load_documents()
    chunks = build_chunks(documents)
    DEFAULT_CHUNKS_PATH.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Dibuat {len(chunks)} chunk dari {len(documents)} dokumen -> {DEFAULT_CHUNKS_PATH}")


if __name__ == "__main__":
    main()
