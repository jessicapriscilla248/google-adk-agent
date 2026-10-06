"""Konstanta prompt untuk `compute_engine_agent`.

`REFUSAL_MESSAGE` adalah SATU sumber kebenaran untuk kalimat penolakan baku,
dipakai oleh instruction di bawah, oleh `tools.py` (pesan pengarah saat tidak
ada hasil), dan oleh test regresi bahasa (`tests/test_prompt.py`).

Catatan review Phase 3 (lihat research/model_comparison.md Bagian 6/8): 3 dari
4 kesalahan bahasa yang ditemukan adalah pertanyaan BAHASA INDONESIA yang
dijawab penolakan berbahasa INGGRIS, karena kalimat penolakan di system prompt
Phase 3 (`research/phase3_experiments/system_prompt.txt`) ditulis dalam Bahasa
Inggris. Scope Bahasa-Indonesia-saja di Phase 4 TIDAK otomatis menghilangkan
risiko ini — mitigasinya adalah membakukan kalimat penolakan dalam Bahasa
Indonesia di SATU tempat (di sini), bukan membiarkan model menyusun kalimat
penolakannya sendiri.
"""

REFUSAL_MESSAGE = (
    "Maaf, informasi ini tidak tersedia di knowledge base Compute Engine yang "
    "saya miliki. Saya tidak bisa menjawab berdasarkan pengetahuan umum untuk "
    "topik support teknis seperti ini."
)

# ADK dapat menafsirkan `{nama}` di dalam `instruction` sebagai variabel state
# yang harus di-resolve dari session (lihat google.adk.agents.llm_agent).
# Instruksi di bawah ini SENGAJA tidak memakai kurung kurawal literal apa pun
# (termasuk saat mengutip format JSON) untuk menghindari ADK salah menafsirkannya
# sebagai placeholder yang tidak ada di session state.
#
# Phase 6 Langkah 2 (O8, efisiensi token runtime): dirampingkan dari versi
# Phase 4/5 (404 kata, konstanta final dengan REFUSAL_MESSAGE tertanam).
# Phase 6b Langkah 2: ditambah aturan "permintaan berisiko" (jangan beri
# langkah/perintah untuk 0.0.0.0/0 administratif, Owner/Editor, atau
# menonaktifkan/menghapus firewall secara luas — lihat TC-24 di
# phase6/hasil_e2e.md Bagian 5) dan baris kategori kini eksplisit memperbolehkan
# hasil tool MANA PUN (bukan wajib hasil pertama) selama label dan topik
# berasal dari hasil yang SAMA (lihat TC-26).
# Phase 6c: ditambah aturan ketidakmampuan eksplisit di AWAL jawaban untuk
# permintaan berbentuk perintah, dan larangan frasa yang menyiratkan agent
# akan MENERAPKAN perubahan sendiri (lihat `phase6/jawaban_untuk_tinjauan.md`
# — TC-24 Langkah 6 sempat menulis "konfirmasikan apakah Anda ingin
# melanjutkan penerapan", menyiratkan agent ikut menerapkan). Paragraf
# "permintaan berisiko" dipertegas: alternatif HANYA disebut jika benar ADA
# di hasil tool — contoh alternatif (source range/IAP/least privilege)
# DIHAPUS dari instruksi supaya tidak terbaca sebagai daftar wajib-sebut
# lepas dari hasil tool (lihat TC-24: chunk-nya sendiri TIDAK memuat IAP,
# docs/architecture.md Bagian 13).
# Phase 6d: daftar kata kerja contoh ("buka/restart/berikan/hapus") DIHAPUS
# — aturan "permintaan tindakan" dibuat GENERIK ("melakukan/mengubah sesuatu
# pada project mereka") karena DIUKUR Phase 6c, VARIAN-iii ("izinkan RDP...")
# tidak memicu kalimat ketidakmampuan karena "izinkan" tak ada di contoh.
# Penegakan utama sekarang BUKAN lagi lewat kalimat instruksi saja — DIUKUR
# Phase 6c (TC-24, tool_called=False) model bisa menjawab tanpa pernah
# memanggil tool sama sekali; `agent.py` kini memaksa panggilan tool lewat
# `tool_config` (function calling mode ANY) di luar instruksi ini (lihat
# `_shortcircuit_refusal_on_empty_retrieval`). Klarifikasi dipertegas HARUS
# "dari situ" (hasil tool), bukan dikarang model (motivasi: VARIAN-i Phase
# 6c punya pertanyaan klarifikasi ke-3 yang tidak ada di KB).
# Phase 8 Langkah 4 (SATU edit, dua perubahan, DIUKUR Phase 7
# `phase7/jawaban_live.md`): (a) kalimat ketidakmampuan akses project
# sebelumnya bisa muncul pada pertanyaan how-to/kenapa biasa (TC-03, TC-14)
# dan di TC-14 mendahului baris kategori — kondisi dipertegas EKSPLISIT
# ("bagaimana cara.../kenapa..." dikecualikan) dan posisinya dipindah jadi
# baris KEDUA (setelah "Kategori terkait", yang kini ditandai "SELALU" baris
# pertama), bukan lagi "awali jawaban". (b) "Sumber:" dipertegas HANYA URL
# dari hasil yang BENAR-BENAR dipakai menjawab, tanpa perintah/contoh tak
# relevan (motivasi: TC-25 menyertakan URL known-issues yang tidak dipakai
# dan perintah SSH tak relevan). Template tetap dijaga di ~220 kata (lihat
# tests/test_prompt.py), konstanta FINAL (dengan REFUSAL_MESSAGE ~26 kata
# yang WAJIB dikutip verbatim) 247->249 kata — relevan karena instruksi ini
# terkirim ULANG di setiap giliran compute_engine_agent (lihat Bagian 6
# docs/architecture.md, 2x per pertanyaan).
COMPUTE_ENGINE_AGENT_INSTRUCTION = f"""\
Anda asisten dukungan teknis Google Cloud Compute Engine berbasis knowledge \
base. Tidak punya akses ke project/VM/log pengguna, tidak bertindak atas \
namanya.

Alur: (1) identifikasi masalah, (2) tentukan kategori, (3) panggil \
search_knowledge_base sebelum menjawab, (4) susun jawaban hanya dari hasil \
tool, (5) tampilkan sumber. URL persis dari hasil tool.

Tolak apa adanya, tanpa tambahan: "{REFUSAL_MESSAGE}" HANYA jika status \
tool bukan success, ATAU topik hasil BERBEDA dari topik pertanyaan. Konten \
diagnostik tetap sah jika topik sama.

Permintaan berisiko (buka firewall 0.0.0.0/0 SSH/RDP, Owner/Editor, \
nonaktifkan/hapus firewall): JANGAN beri langkah/perintah; jelaskan \
risiko, arahkan ke alternatif di hasil tool bila ada, atau nyatakan \
keterbatasan.

Jika topik cocok, format: baris pertama SELALU "Kategori terkait: \
<kategori_label> - Topik: <title>" dari hasil dasar (label-topik hasil \
SAMA; hilangkan jika kosong; tidak ada pada penolakan). HANYA bila \
pengguna minta Anda melakukan/mengubah sesuatu pada project mereka (BUKAN \
pertanyaan "bagaimana cara..."/"kenapa..."), baris KEDUA nyatakan \
ketidakmampuan itu, baru langkah; jangan tulis frasa yang menyiratkan Anda \
menerapkan perubahan sendiri. Lalu 1-2 kalimat identifikasi; langkah \
berurutan, read-only dahulu, ubah konfigurasi perlu konfirmasi; jika hasil \
tool memuat klarifikasi, tulis "Agar lebih tepat, mohon info:" maksimal 3 \
pertanyaan dari situ; lalu "Sumber:" HANYA URL dari hasil yang \
benar-benar dipakai menjawab, tanpa perintah/contoh tak relevan.

Jangan sarankan restart/stop-start sebagai langkah pertama; known issue \
jangan digeneralisasi.

Selalu Bahasa Indonesia termasuk penolakan; istilah teknis/perintah/kode \
error seperti aslinya. Jawaban ringkas, tidak tambah info luar hasil tool.
"""
