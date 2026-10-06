# Google Cloud Compute Engine Support Assistant

Asisten support teknis membantu user mendapatkan informasi dan memberikan rekomendasi langkah  troubleshooting pada Google Cloud Compute Engine berdasarkan dokumentasi resmi dari Google Cloud.

## Tujuan Project
Mengembangkan sistem AI Support Assistant dengan knowledge based multi agent yang dapat membantu user memahami dan menangani masalah yang dihadapi pada layanan Google Cloud Compute Engine. Sistem akan menerima pertanyaan dari customer yang kemudian diproses oleh 2 agent. Berikut adalah 2 agent yang akan bekerja di dalam sistem:

1. Main Agent: Mengatur alur pertanyaan.
2. Compute Engine Agent: Melakukan troubleshooting layanan compute engine.

## Fitur yang Dikembangkan
1. Menerima pertanyaan user
2. Menentukan kategori masalah pertanyaan user
3. Routing ke agent compute engine
4. Mencari dokumentasi dari knowledge base
5. Menyusun rekomendasi troubleshooting
6. Memberikan jawaban terstruktur
7. Menangani pertanyaan di luar scope
8. Menampilkan referensi dokumentasi

## Project yang Dikembangkan
1. Fokus: Compute Engine
2. Framework: Google ADK
3. Model: Gemini 3.5 Flash Lite

## Setup

```bash
python -m venv .venv
pip install -r requirements.txt
```

## Menjalankan Agent
### `adk web` (UI chat bawaan ADK)

```bash
adk web .
```


