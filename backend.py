import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
import google.generativeai as genai

class ExciaOrchestrator:
    def __init__(self, hf_repo_name):
        print("Memuat Komponen EXCIA...")
        
        # 1. Mengambil API Key dengan Aman dari Environment Variables
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        if not pinecone_api_key or not gemini_api_key:
            raise ValueError("Kritikal Error: API Key PINECONE_API_KEY atau GEMINI_API_KEY belum diatur!")
        
        # 2. Load IndoBERT (Pilar 1)
        self.tokenizer = AutoTokenizer.from_pretrained(hf_repo_name)
        self.intent_model = AutoModelForSequenceClassification.from_pretrained(hf_repo_name)
        self.label_mapping = {0: "Aqidah", 1: "Fiqih/Hukum", 2: "Akhlak/Psikologi", 3: "Kisah/Sejarah", 4: "Muamalah/Sosial"}
        
        # 3. Load MiniLM & Pinecone (Pilar 2 & 3)
        self.embed_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.pc = Pinecone(api_key=pinecone_api_key)
        self.index = self.pc.Index("excia-index")
        
        # 4. Konfigurasi LLM Gemini (Pilar 4)
        genai.configure(api_key=gemini_api_key)
        self.llm = genai.GenerativeModel('gemini-3.5-flash')
        
        # Kamus Normalisasi Slang
        self.kamus_slang = {"yg": "yang", "gmn": "bagaimana", "gimana": "bagaimana", "bgt": "sekali", "banget": "sekali", "gk": "tidak", "nggak": "tidak", "insecure": "kurang percaya diri", "overthinking": "terlalu banyak berpikir"}

    def normalisasi_teks(self, teks):
        kata_kata = teks.lower().split()
        teks_normal = [self.kamus_slang.get(kata, kata) for kata in kata_kata]
        return " ".join(teks_normal)

    def prediksi_intent(self, teks):
        inputs = self.tokenizer(teks, return_tensors="pt", truncation=True, padding=True, max_length=128)
        with torch.no_grad():
            outputs = self.intent_model(**inputs)
        prediksi_idx = torch.argmax(outputs.logits, dim=1).item()
        return self.label_mapping[prediksi_idx]

    def cari_referensi(self, teks_vektor, intent_kategori):
        # Tarik Ayat Al-Qur'an (Universal)
        hasil_quran = self.index.query(
            vector=teks_vektor, 
            top_k=4, 
            include_metadata=True,
            filter={"tipe_dokumen": {"$eq": "quran"}}
        )
        
        # Tarik Artikel (Spesifik sesuai tebakan IndoBERT)
        hasil_artikel = self.index.query(
            vector=teks_vektor, 
            top_k=1, 
            include_metadata=True,
            filter={"tipe_dokumen": {"$eq": "artikel"}, "intent_kategori": {"$eq": intent_kategori}}
        )
        return hasil_quran, hasil_artikel

    def cari_referensi_terpisah(self, vektor_quran, vektor_artikel, intent_kategori):
        # Tarik Ayat Al-Qur'an menggunakan vektor murni
        hasil_quran = self.index.query(
            vector=vektor_quran, 
            top_k=4, 
            include_metadata=True,
            filter={"tipe_dokumen": {"$eq": "quran"}}
        )
        
        # Tarik Artikel menggunakan vektor ekspansi
        hasil_artikel = self.index.query(
            vector=vektor_artikel, 
            top_k=1, 
            include_metadata=True,
            filter={"tipe_dokumen": {"$eq": "artikel"}, "intent_kategori": {"$eq": intent_kategori}}
        )
        return hasil_quran, hasil_artikel

    def proses_curhatan(self, input_user: str, chat_history: list = None):
        teks_baku = self.normalisasi_teks(input_user)
        intent = self.prediksi_intent(teks_baku)

        # --- FIX 1: Query Rewriting ---
        konteks_history = ""
        if chat_history:
            for msg in chat_history[-6:]:  # ambil 6 pesan terakhir saja agar prompt tidak terlalu panjang
                role = "Pengguna" if msg["role"] == "user" else "EXCIA"
                konteks_history += f"{role}: {msg['content']}\n"
        # Normalisasi query menjadi bentuk deklaratif sebelum di-embed
        # supaya "ayat apa yang menjelaskan X" dan "ayat tentang X" → vektor sama
        teks_rewrite = self._rewrite_query(teks_baku)

        vektor_quran = self.embed_model.encode(
            teks_rewrite, normalize_embeddings=True
        ).tolist()
        teks_ekspansi_artikel = f"Artikel Islami tentang {intent}. Topik: {teks_rewrite}"
        vektor_artikel = self.embed_model.encode(
            teks_ekspansi_artikel, normalize_embeddings=True
        ).tolist()

        data_quran, data_artikel = self.cari_referensi_terpisah(
            vektor_quran, vektor_artikel, intent
        )

        # --- FIX 2: Kirim skor ke Gemini supaya dia tahu mana kandidat terkuat ---
        teks_tafsir_gabungan = ""
        if data_quran and data_quran['matches']:
            for i, match in enumerate(data_quran['matches']):
                meta = match['metadata']
                skor = match['score']
                teks_tafsir_gabungan += (
                    f"\nKandidat [{i+1}] (Skor Relevansi: {skor:.4f})"
                    f" - Surah {meta.get('surat')} Ayat {meta.get('ayat')}:\n"
                    f"{meta.get('teks_lengkap')}\n"
                )
        else:
            teks_tafsir_gabungan = "Tidak ada referensi ayat."

        teks_artikel = (
            data_artikel['matches'][0]['metadata']['teks_lengkap']
            if data_artikel and data_artikel['matches']
            else "Tidak ada artikel terkait."
        )

        prompt_llm = f"""
        Kamu adalah Asisten Spiritual EXCIA yang sedang bercakap-cakap dengan pengguna.

        [RIWAYAT PERCAKAPAN SEBELUMNYA]:
        {konteks_history if konteks_history else "Ini adalah awal percakapan."}

        [PESAN TERBARU PENGGUNA]: "{input_user}"

        [KANDIDAT AYAT DARI DATABASE]:
        {teks_tafsir_gabungan}

        [ARTIKEL PENDUKUNG]: {teks_artikel}

        INSTRUKSI MUTLAK:
        1. Baca riwayat percakapan untuk memahami konteks emosi dan masalah pengguna secara utuh.
        2. Berikan nasihat yang NYAMBUNG dengan keseluruhan cerita, bukan hanya pesan terakhir.
        3. PRIORITASKAN kandidat ayat dengan Skor Relevansi tertinggi.
        4. WAJIB sebutkan nama Surah dan angka Ayat yang kamu pilih.
        5. Langsung berikan nasihat hangat tanpa perkenalan robotik agar tidak terlalu panjang response mu namun tetap sopan.
        """

        respons_llm = self.llm.generate_content(prompt_llm)

        # --- FIX 3: Sinkronisasi UI lebih robust pakai nomor ayat saja ---
        ayat_terpilih = data_quran['matches'][0]['metadata'] if data_quran['matches'] else None

        if data_quran and data_quran['matches']:
            for match in data_quran['matches']:
                nomor_ayat = str(match['metadata'].get('ayat'))
                nama_surat_raw = match['metadata'].get('surat', '')
                # Normalisasi: hapus strip, lowercase, hapus "al-" prefix untuk matching longgar
                nama_surat_norm = nama_surat_raw.lower().replace('-', ' ').replace("al ", "")
                teks_respon_norm = respons_llm.text.lower().replace('-', ' ').replace("al ", "")

                if nomor_ayat in respons_llm.text and nama_surat_norm in teks_respon_norm:
                    ayat_terpilih = match['metadata']
                    break

        return {
            "intent": intent,
            "nasihat_ai": respons_llm.text,
            "raw_quran": ayat_terpilih,
            "raw_artikel": (
                data_artikel['matches'][0]['metadata']
                if data_artikel and data_artikel['matches']
                else None
            ),
        }

    # --- Tambahkan method baru ini di dalam class ExciaOrchestrator ---
    def _rewrite_query(self, teks: str) -> str:
        """
        Normalisasi query dari bentuk pertanyaan → pernyataan deklaratif.
        Tujuan: menyamakan distribusi vektor untuk query yang semantiknya sama
        tapi phrasing-nya berbeda.
        """
        # Pola pertanyaan umum → strip jadi inti topik
        prefixes_to_strip = [
            "ayat apa yang menjelaskan tentang",
            "ayat apa tentang",
            "ayat yang membahas",
            "tolong carikan ayat tentang",
            "cari ayat tentang",
            "apa kata quran tentang",
            "bagaimana islam memandang",
            "jelaskan tentang",
        ]
        teks_lower = teks.lower().strip(" ?")
        for prefix in prefixes_to_strip:
            if teks_lower.startswith(prefix):
                teks_lower = teks_lower[len(prefix):].strip()
                break

        # Tambahkan framing deklaratif agar lebih cocok dengan konten Quran
        return f"ajaran Islam tentang {teks_lower}"