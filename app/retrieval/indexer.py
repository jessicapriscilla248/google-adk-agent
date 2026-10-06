"""Membangun representasi TF-IDF dari chunks.json.

Index dibangun in-memory dari chunks.json setiap kali dipanggil. Korpus
berukuran kecil (puluhan-ratusan chunk), sehingga fit TF-IDF berlangsung dalam
hitungan milidetik dan tidak memerlukan index terpisah yang di-pickle ke disk.
"""
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from ..config import CHUNKS_PATH as DEFAULT_CHUNKS_PATH

# Stopword Bahasa Indonesia umum. Korpus seluruhnya berbahasa Indonesia
# (kecuali istilah teknis resmi seperti "firewall", "quota", "VM"), sehingga daftar
# stopword bahasa Inggris bawaan scikit-learn tidak relevan di sini. 
INDONESIAN_STOPWORDS = [
    "yang", "untuk", "dengan", "adalah", "dapat", "atau", "ini", "itu", "pada", "dari",
    "ke", "akan", "juga", "sudah", "karena", "oleh", "saat", "jika", "maka", "bisa",
    "tidak", "dan", "di", "dalam", "ada", "apa", "tersebut", "secara", "setelah",
    "sebelum", "harus", "agar", "sebagai", "seperti", "lebih", "antara", "atas",
    "bagi", "namun", "tetapi", "serta", "masih", "sangat", "semua", "beberapa",
    "sendiri", "hal", "cara",
]

class SearchIndex:
    """Bungkus chunks + TF-IDF vectorizer + matrix supaya bisa dipakai berulang
    untuk banyak query tanpa membangun ulang index setiap kali (dipakai oleh cli.py)."""

    def __init__(self, chunks):
        if not chunks:
            raise ValueError("Tidak ada chunk untuk diindeks. Jalankan chunker.py terlebih dahulu.")
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            sublinear_tf=True,
            stop_words=INDONESIAN_STOPWORDS,
        )
        self.matrix = self.vectorizer.fit_transform([c["text"] for c in chunks])

    def transform_query(self, query):
        return self.vectorizer.transform([query])

def load_chunks(chunks_path=None):
    chunks_path = chunks_path or DEFAULT_CHUNKS_PATH
    if not chunks_path.exists():
        raise FileNotFoundError(
            f"{chunks_path} tidak ditemukan. Jalankan `python -m app.retrieval.chunker` terlebih dahulu."
        )
    return json.loads(chunks_path.read_text(encoding="utf-8"))

def build_index(chunks_path=None):
    chunks = load_chunks(chunks_path)
    return SearchIndex(chunks)
