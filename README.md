# EXCIA — Asisten Spiritual AI

> Asisten Spiritual AI yang membantu memberikan nasihat berbasis referensi Al-Qur'an dan artikel pendukung menggunakan teknologi AI dan vector search.

## 📋 Ringkasan Singkat

| Aspek | Deskripsi |
|-------|----------|
| **Bahasa** | Python 3.8+ |
| **UI** | Streamlit (`app.py`) |
| **Backend** | `backend.py` (kelas `ExciaOrchestrator`) |
| **Tujuan** | Menerima curhatan pengguna, menentukan intent, mencari ayat/artikel relevan, lalu menghasilkan nasihat spiritual berbasis Al-Qur'an |

## ✨ Fitur Utama

- **Normalisasi Teks**: Normalisasi slang dan pre-processing teks Bahasa Indonesia
- **Klasifikasi Intent**: Menggunakan model IndoBERT (`Exchonsive/excia-indobert-intent`) untuk memahami maksud pengguna
- **Embedding Multilingual**: Embedding teks dengan `paraphrase-multilingual-MiniLM-L12-v2` (SentenceTransformers)
- **Vector Search**: Penyimpanan dan pencarian vektor menggunakan Pinecone (index: `excia-index`)
- **Generasi Nasihat**: Penyusunan nasihat kontekstual dengan Google Gemini (`gemini-3.5-flash`)
- **UI Interaktif**: Chat interface dengan Streamlit, menampilkan ayat (teks Arab), terjemahan, tafsir, dan artikel pendukung
- **In-Memory Caching**: Caching hasil untuk performa lebih baik
- **JSON Schema Validation**: Enforced JSON response dari LLM untuk output yang terstruktur

## 🏗️ Tech Stack

| Komponen | Teknologi |
|----------|----------|
| **Framework UI** | Streamlit 1.32.0 |
| **Vector DB** | Pinecone 3.1.0 |
| **Embeddings** | SentenceTransformers 2.5.1 |
| **Intent Classification** | Transformers 4.38.2, IndoBERT |
| **Deep Learning** | PyTorch 2.2.1 |
| **LLM** | Google Generative AI (Gemini) |

## 📦 Dependensi

Lihat `requirements.txt` untuk daftar lengkap semua dependensi:
```
streamlit==1.32.0
pinecone-client==3.1.0
sentence-transformers==2.5.1
transformers==4.38.2
torch==2.2.1
google-generativeai==0.5.0
python-dotenv==1.0.0
requests>=2.31.0
```

## 📊 Struktur Proyek

```
.
├── app.py              # Frontend Streamlit (UI Chat)
├── backend.py          # Backend Orchestrator (Logic)
├── requirements.txt    # Dependensi Python
├── README.md           # Dokumentasi (file ini)
├── LICENSE             # Lisensi proyek
└── .env.example        # Template environment variables
```

## 🔧 Arsitektur & Alur Kerja

**Alur Kerja:**
1. Pengguna memasukkan pesan melalui antarmuka Streamlit (`app.py`)
2. `ExciaOrchestrator` menormalisasi teks dan memprediksi intent menggunakan model IndoBERT
3. Teks ditransformasi menjadi embedding menggunakan SentenceTransformers
4. Embedding digunakan untuk mencari ayat dan artikel relevan di Pinecone
5. Hasil pencarian diproses dan dikirim ke Google Gemini dengan JSON Schema untuk penyusunan nasihat
6. Hasil (nasihat, metadata ayat, artikel) ditampilkan di UI dan di-cache di `st.session_state`

## 🚀 Cara Menjalankan (Lokal)

### Prerequisites
- Python 3.8 atau lebih tinggi
- Pinecone API Key (gratis: https://www.pinecone.io/)
- Google Gemini API Key (gratis: https://aistudio.google.com/app/apikey)

### Setup Langkah demi Langkah

**1. Clone repository dan masuk folder:**
```bash
git clone https://github.com/Exchonsive/excia.git
cd excia
```

**2. Buat virtual environment Python (disarankan):**
```bash
python -m venv .venv

# Untuk Linux/macOS:
source .venv/bin/activate

# Untuk Windows:
.venv\Scripts\activate
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Konfigurasi environment variables:**

Buat file `.env` di root folder:
```bash
cat > .env << EOF
PINECONE_API_KEY="your-pinecone-api-key-here"
GEMINI_API_KEY="your-gemini-api-key-here"
EOF
```

Atau set langsung di terminal:
```bash
export PINECONE_API_KEY="your-pinecone-api-key"
export GEMINI_API_KEY="your-gemini-api-key"
```

**5. Jalankan aplikasi Streamlit:**
```bash
streamlit run app.py
```

Aplikasi akan terbuka di `http://localhost:8501`

## 🛡️ Mitigasi Halusinasi & Keamanan Pemanggilan API

Saya telah menambahkan beberapa langkah di backend untuk mengurangi halusinasi LLM dan meningkatkan keamanan panggilan API:

- **Retrieval-Augmented Generation (RAG)**: selalu sertakan hasil pencarian (ayat/artikel) sebagai konteks eksplisit ke LLM; hindari menjawab tanpa sumber.
- **Enforce JSON Schema**: response LLM divalidasi terhadap JSON Schema; bila tidak valid sistem akan meminta re-generation atau menggunakan template jawaban konservatif.
- **Source Attribution & Highlighting**: sertakan metadata sumber (surat/ayat/id artikel) dan confidence score; tampilkan potongan sumber di UI agar jawaban dapat dilacak.
- **Output Filtering & Safety Layers**: filter profanity, tautan berbahaya, dan klaim medis/diagnostik; tandai respons yang memerlukan rujukan manusia.
- **Verification Step (LLM as verifier)**: jalankan langkah verifikasi internal (model verifier atau heuristik) untuk mendeteksi probabilitas halusinasi.
- **Conservative Generation**: gunakan pengaturan temperatur lebih rendah dan top_p lebih konservatif; tambahkan prompt constraints seperti "jawab hanya berdasarkan sumber yang tersedia".
- **Rate Limiting & Backoff**: implementasi rate limiter, retries eksponensial, dan circuit-breaker pada panggilan eksternal (Gemini, Pinecone).
- **Input Validation & Sanitization**: validasi schema input, batasi panjang konteks, dan normalisasi teks untuk mencegah injection atau prompt tampering.
- **Logging & Monitoring**: log permintaan/responses dengan redaksi PII, kumpulkan telemetry untuk analisis kasus halusinasi, dan pasang alerting untuk pola anomali.
- **Fallback & Human-in-the-loop**: jika confidence rendah atau mismatch sumber, fallback ke template aman dan kirim flag untuk review manusia.

Integrasi spesifik di `backend.py`:
- `generate_with_sources()` — menyusun prompt RAG lengkap dengan metadata sumber.
- `validate_llm_response()` — melakukan validasi JSON Schema dan filter keamanan sebelum mengembalikan hasil ke UI.
- `retry_api_call()` — wrapper untuk pemanggilan eksternal dengan exponential backoff dan circuit-breaker.
- `verifier_check()` — langkah verifikasi internal (panggilan model/verifier) untuk mengevaluasi faithfulness.

Rekomendasi operasional:
- Buat end-to-end tests yang mensimulasikan adversarial prompts dan edge cases.
- Simpan sampel kasus halusinasi untuk analisis dan potensi fine-tuning model retrieval atau reranker.
- Gunakan secrets manager dan batasi scope API key pada lingkungan production.

## 📝 Catatan Pengembang

- Model intent classification di-load sekali pada inisialisasi `ExciaOrchestrator`
- Cache in-memory di-reset setiap kali Streamlit rerun
- JSON Schema di-enforce di level API untuk memastikan response terstruktur
- PyTorch CUDA support opsional; code support CPU fallback
- Model HF untuk intent: `Exchonsive/excia-indobert-intent`
- LLM yang dipakai di `backend.py` adalah `gemini-3.5-flash` melalui `google.generativeai`

## 📄 License

Proyek ini dilisensikan di bawah lisensi yang ditentukan di file [LICENSE](LICENSE).

## 🤝 Contributing

Kontribusi sangat diterima! Silakan buat pull request atau buka issue untuk saran dan perbaikan.

## 🔗 Links & Resources

Live: https://chatexcia.streamlit.app/

