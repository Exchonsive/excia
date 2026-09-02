# EXCIA — Asisten Spiritual AI

> Asisten spiritual berbasis Islam yang membantu menjawab pertanyaan secara empatik, dengan referensi ayat Al-Qur'an dan artikel pendukung yang relevan.

## Ringkasan proyek

EXCIA adalah aplikasi berbasis Python dan Streamlit yang menerima curhatan atau pertanyaan pengguna, mengklasifikasikan intent, mencari referensi yang relevan di Pinecone, lalu menghasilkan nasihat yang dibangun dari konteks Al-Qur'an dan artikel Islam. Aplikasi ini juga menerapkan validasi JSON schema untuk menjaga struktur output dari model Gemini.

## Arsitektur saat ini

| Komponen | Detail |
| --- | --- |
| Frontend | Streamlit (`app.py`) |
| Backend | `backend.py` dengan kelas `ExciaOrchestrator` |
| Intent classifier | `Exchonsive/excia-indobert-intent` via `transformers` |
| Embedding model | `paraphrase-multilingual-MiniLM-L12-v2` via `sentence-transformers` |
| Vector DB | Pinecone index `excia-index` |
| LLM | Google Gemini via `google.genai` |
| Bahasa utama | Python |

## Fitur utama

- Normalisasi teks Bahasa Indonesia untuk mengurangi variasi slang dan input user.
- Prediksi intent secara lokal menggunakan IndoBERT.
- Pencarian vektor untuk ayat Al-Qur'an dan artikel Islam.
- Retrieval-Augmented Generation (RAG) dengan kandidat sumber yang dibatasi ke konteks yang ditemukan. 
- Validasi respons model dengan JSON Schema.
- Rate limiter, cache in-memory, dan fallback model Gemini untuk menangani overload atau quota limit.
- UI chat yang menampilkan nasihat, referensi ayat, terjemahan, tafsir, dan artikel pendukung.
- Verifikasi programatik agar ayat yang dipakai sesuai dengan kandidat yang ditemukan di database.

## Struktur file

```text
.
├── app.py             # Frontend Streamlit
├── backend.py         # Orchestrator EXCIA, retrieval, validasi, dan pipeline utama
├── requirements.txt   # Dependensi Python
├── README.md          # Dokumentasi proyek
├── LICENSE            # Lisensi proyek
└── .gitignore
```

## Dependensi

Daftar dependensi yang benar saat ini ada di [requirements.txt](requirements.txt):

```txt
# UI Framework
streamlit

# Vector Database
pinecone

# Embeddings & NLP
sentence-transformers
transformers
torch

# LLM
google-genai

# Utilities
python-dotenv
requests
huggingface-hub
```

## Variabel environment

Sebelum menjalankan aplikasi, buat file `.env` di root project dengan variabel berikut:

```bash
PINECONE_API_KEY="your_pinecone_api_key"
GEMINI_API_KEY="your_gemini_api_key"
```

Anda juga bisa menyetelnya langsung di terminal:

```bash
export PINECONE_API_KEY="your_pinecone_api_key"
export GEMINI_API_KEY="your_gemini_api_key"
```

Catatan:
- `backend.py` memeriksa keberadaan `PINECONE_API_KEY` dan `GEMINI_API_KEY` saat aplikasi diinisialisasi.
- `GEMINI_API_KEY` bisa berupa string tunggal atau beberapa key yang dipisahkan koma untuk fallback otomatis.

## Cara menjalankan

### 1) Clone repo

```bash
git clone https://github.com/Exchonsive/excia.git
cd excia
```

### 2) Buat virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

Pada Windows:

```bash
.venv\Scripts\activate
```

### 3) Install dependensi

```bash
pip install -r requirements.txt
```

### 4) Jalankan aplikasi

```bash
streamlit run app.py
```

Aplikasi akan berjalan di browser pada URL lokal Streamlit biasanya:

```text
http://localhost:8501
```

## Alur kerja aplikasi

1. Pengguna mengirim pesan di Streamlit.
2. `ExciaOrchestrator` melakukan normalisasi teks dan prediksi intent.
3. Query di-encode menggunakan embedding model multilingual.
4. Sistem mencari metadata ayat dan artikel yang relevan di Pinecone.
5. Konteks hasil retrieval dikirim ke Gemini bersama prompt yang dibatasi oleh sumber.
6. Model menghasilkan output JSON terstruktur berupa `is_relevant`, `nasihat`, `ayat_dipilih_index`, `confidence`, dan `alasan_confidence`.
7. Backend melakukan validasi programatik untuk memastikan ayat yang dipakai sesuai dengan hasil retrieval.
8. Hasil akhirnya ditampilkan di UI.

## Implementasi keamanan dan kontrol kualitas

Versi saat ini sudah menambahkan beberapa layer untuk menjaga kualitas output:

- RAG-only prompt: model diarahkan hanya memakai kandidat sumber dari database.
- JSON Schema enforcement: respons model harus sesuai format yang telah ditentukan.
- Rate limiter dan backoff: mencegah overload API dan membatasi pemanggilan.
- Cache in-memory: mengurangi panggilan berulang untuk prompt yang sama.
- Fallback model Gemini: mencoba model alternatif jika terjadi 503 atau rate limit.
- Verifikasi programatik: Python mengecek apakah ayat yang dipilih benar-benar sesuai dengan hasil retrieval.

## Catatan pengembang

- Model intent ditampilkan dan dipakai via `AutoTokenizer` dan `AutoModelForSequenceClassification`.
- Kelas utama memiliki fungsi `proses_curhatan()` untuk menjalankan satu siklus full pipeline.
- Cache di-reset otomatis saat sesi Streamlit berjalan ulang.
- Model yang dipakai untuk generation bisa berganti antara `gemini-3.1-flash-lite`, `gemini-2.5-flash-lite`, dan `gemini-2.5-flash` tergantung kondisi API.

## Lisensi

Proyek ini dilisensikan di bawah file [LICENSE](LICENSE).

## Kontribusi

Kontribusi sangat terbuka. Silakan buat pull request atau ajukan issue jika ada saran, perbaikan, atau fitur yang ingin ditambahkan.

## Sumber referensi

- Streamlit: https://streamlit.io/
- Pinecone: https://www.pinecone.io/
- SentenceTransformers: https://www.sbert.net/
- Google Generative AI: https://ai.google.dev/
- Hugging Face: https://huggingface.co/

