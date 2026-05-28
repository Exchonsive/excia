# EXCIA

> EXCIA — Asisten Spiritual AI yang membantu memberikan nasihat berbasis referensi Al-Qur'an dan artikel pendukung.

Ringkasan
- Bahasa: Python
- UI: Streamlit (`app.py`)
- Orkestrator: `backend.py` (kelas `ExciaOrchestrator`)
- Tujuan: menerima 'curhatan' pengguna, menentukan intent, menarik ayat/ artikel relevan dari Pinecone, lalu menghasilkan nasihat dengan LLM Gemini.

Fitur Utama
- Normalisasi slang dan pre-processing teks.
- Klasifikasi intent menggunakan model IndoBERT (HF repo `Exchonsive/excia-indobert-intent`).
- Embedding dengan `paraphrase-multilingual-MiniLM-L12-v2` (SentenceTransformers).
- Penyimpanan/pencarian vektor menggunakan Pinecone (index: `excia-index`).
- Generasi jawaban/penyusunan nasihat menggunakan Google Gemini (`gemini-3.5-flash`).
- Tampilan chat interaktif dengan Streamlit, lengkap dengan tampilan ayat (Arab), terjemahan, tafsir, dan artikel.

Persyaratan (dilihat di `requirements.txt`)
- streamlit==1.32.0
- pinecone-client==3.1.0
- sentence-transformers==2.5.1
- transformers==4.38.2
- torch==2.2.1
- google-generativeai


Arsitektur & Alur Kerja Singkat
1. Pengguna memasukkan pesan melalui antarmuka Streamlit (`app.py`).
2. `ExciaOrchestrator` menormalisasi teks, memprediksi intent, lalu membuat embedding query.
3. Query embedding digunakan untuk mencari ayat dan artikel di Pinecone.
4. Hasil pencarian dirangkum/diurutkan, lalu dikirimkan ke LLM Gemini untuk menyusun nasihat yang kontekstual.
5. Hasil (nasihat, metadata ayat, artikel) ditampilkan di UI dan disimpan di `st.session_state`.

Cara Menjalankan (lokal)
1. Buat environment virtual Python (disarankan). Contoh:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Set environment variables sebelum menjalankan:

```
export PINECONE_API_KEY="<your-pinecone-key>"
export GEMINI_API_KEY="<your-gemini-key>"
```

3. Jalankan aplikasi Streamlit:

```
streamlit run app.py
```

Catatan Keamanan
- Jangan pernah commit API key ke repository. Gunakan secrets manager atau CI/CD secret store.
- Pastikan index Pinecone (`excia-index`) sudah dibuat dan berisi dokumen dengan metadata yang sesuai (`tipe_dokumen`, `surat`, `ayat`, `teks_lengkap`, dsb.).

Catatan Pengembang
- Model HF untuk intent: `Exchonsive/excia-indobert-intent` di-load pada inisialisasi.
- LLM yang dipakai di `backend.py` adalah `gemini-3.5-flash` melalui `google.generativeai`.

