import os
import time
import torch
import re
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
import google.generativeai as genai

class ExciaOrchestrator:
    def __init__(self, hf_repo_name):
        print("Memuat Komponen EXCIA...")
        
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        gemini_keys_raw = os.getenv("GEMINI_API_KEYS")
        
        if not pinecone_api_key or not gemini_keys_raw:
            raise ValueError("Kritikal Error: API Key PINECONE_API_KEY atau GEMINI_API_KEYS belum diatur!")
        
        self.gemini_keys = [k.strip() for k in gemini_keys_raw.split(",")]
        self.current_key_idx = 0 
        
        self.tokenizer = AutoTokenizer.from_pretrained(hf_repo_name)
        self.intent_model = AutoModelForSequenceClassification.from_pretrained(hf_repo_name)
        self.label_mapping = {0: "Aqidah", 1: "Fiqih/Hukum", 2: "Akhlak/Psikologi", 3: "Kisah/Sejarah", 4: "Muamalah/Sosial"}
        
        self.embed_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.pc = Pinecone(api_key=pinecone_api_key)
        self.index = self.pc.Index("excia-index")
        
        genai.configure(api_key=self.gemini_keys[self.current_key_idx])
        self.llm = genai.GenerativeModel('gemini-1.5-flash-8b') # Memastikan pakai model teringan dan tercepat
        
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

    def cari_referensi_terpisah(self, vektor_quran, vektor_artikel, intent_kategori):
        
        hasil_quran = self.index.query(
            vector=vektor_quran, 
            top_k=5, 
            include_metadata=True,
            filter={"tipe_dokumen": {"$eq": "quran"}}
        )
        
        hasil_artikel = self.index.query(
            vector=vektor_artikel, 
            top_k=1, 
            include_metadata=True,
            filter={"tipe_dokumen": {"$eq": "artikel"}, "intent_kategori": {"$eq": intent_kategori}}
        )
        return hasil_quran, hasil_artikel

    def _generate_dengan_cadangan(self, prompt_teks):
        maks_percobaan = len(self.gemini_keys)
        
        for percobaan in range(maks_percobaan):
            try:
                return self.llm.generate_content(prompt_teks).text
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "ResourceExhausted" in error_msg or "quota" in error_msg.lower():
                    print(f"⚠️ Kunci ke-{self.current_key_idx + 1} Limit! Mengganti ke kunci cadangan...")
                    self.current_key_idx = (self.current_key_idx + 1) % len(self.gemini_keys)
                    genai.configure(api_key=self.gemini_keys[self.current_key_idx])
                    self.llm = genai.GenerativeModel('gemini-3.1-flash-lite')
                    time.sleep(1) 
                    continue 
                else:
                    raise e
        return "Maaf, seluruh server EXCIA saat ini sedang melayani banyak pengguna. Mohon tunggu beberapa menit dan coba lagi ya."

    def proses_curhatan(self, input_user: str, chat_history: list = None):
        teks_baku = self.normalisasi_teks(input_user)
        intent = self.prediksi_intent(teks_baku)

        persona_panduan = {
            "Aqidah": "Fokus pada penguatan iman, tauhid, dan keyakinan kepada ketetapan Allah. Gunakan bahasa yang meneguhkan hati.",
            "Fiqih/Hukum": "Jawablah dengan gaya yang lugas, jelas, dan terstruktur. Fokus pada batasan syariat secara objektif.",
            "Akhlak/Psikologi": "Jawablah dengan Penuh Empati, kelembutan, dan dukungan emosional layaknya seorang psikolog Islami.",
            "Kisah/Sejarah": "Gunakan pendekatan bercerita (storytelling). Ambil hikmah (ibrah) dari ayat atau tokoh masa lalu.",
            "Muamalah/Sosial": "Fokus pada etika berinteraksi dengan sesama, adab bermasyarakat, dan berikan solusi praktis."
        }
        instruksi_persona = persona_panduan.get(intent, "Berikan nasihat yang hangat dan menenangkan.")

        konteks_history = ""
        if chat_history:
            for msg in chat_history[-6:]: 
                role = "Pengguna" if msg["role"] == "user" else "EXCIA"
                konteks_history += f"{role}: {msg['content']}\n"
                
        teks_rewrite = self._rewrite_query(teks_baku)

        vektor_quran = self.embed_model.encode(teks_rewrite, normalize_embeddings=True).tolist()
        vektor_artikel = self.embed_model.encode(f"Artikel Islami tentang {intent}. Topik: {teks_rewrite}", normalize_embeddings=True).tolist()

        data_quran, data_artikel = self.cari_referensi_terpisah(vektor_quran, vektor_artikel, intent)

        teks_tafsir_gabungan = ""
        if data_quran and data_quran['matches']:
            for i, match in enumerate(data_quran['matches']):
                meta = match['metadata']
                teks_utuh = meta.get('teks_lengkap', '')
                teks_potong = teks_utuh[:1000] + "...[dipotong untuk efisiensi token]" if len(teks_utuh) > 1000 else teks_utuh
                teks_tafsir_gabungan += f"\nKandidat [{i+1}] - Surah {meta.get('surat')} Ayat {meta.get('ayat')}:\n{teks_potong}\n"
        else:
            teks_tafsir_gabungan = "Tidak ada referensi ayat."

        teks_artikel = "Tidak ada artikel terkait."
        if data_artikel and data_artikel['matches']:
            artikel_utuh = data_artikel['matches'][0]['metadata']['teks_lengkap']
            teks_artikel = artikel_utuh[:1200] + "...[dipotong untuk efisiensi token]" if len(artikel_utuh) > 1200 else artikel_utuh

        prompt_llm = f"""
        Kamu adalah Asisten Spiritual EXCIA.

        [RIWAYAT PERCAKAPAN SEBELUMNYA]:
        {konteks_history if konteks_history else "Ini adalah awal percakapan."}

        [PESAN TERBARU PENGGUNA]: "{input_user}"
        
        [KANDIDAT AYAT DARI DATABASE (Ada 10 Kandidat)]:
        {teks_tafsir_gabungan}

        [ARTIKEL PENDUKUNG]: {teks_artikel}

        INSTRUKSI MUTLAK:
        1. GAYA BAHASA: {instruksi_persona}
        2. Pilih 1 ayat paling cocok dari list Kandidat Database. Jika tidak ada yang cocok sama sekali di list, gunakan pengetahuanmu sendiri.
        3. WAJIB sebutkan nama Surah dan angka Ayat secara eksplisit di dalam teks jawabanmu.
        """

        teks_nasihat_ai = self._generate_dengan_cadangan(prompt_llm)

        # --- FIX: SINKRONISASI UI ANTI-MELESET ---
        ayat_terpilih = None

        if data_quran and data_quran['matches']:
            # 1. Coba cari ayat yang benar-benar disebut Gemini di dalam list database
            for match in data_quran['matches']:
                nomor_ayat = str(match['metadata'].get('ayat'))
                nama_surat_norm = match['metadata'].get('surat', '').lower().replace('-', ' ').replace("al ", "").strip()
                teks_respon_norm = teks_nasihat_ai.lower().replace('-', ' ').replace("al ", "").strip()

                if nomor_ayat in teks_nasihat_ai and nama_surat_norm in teks_respon_norm:
                    ayat_terpilih = match['metadata']
                    break
            
            # 2. Jika Gemini ternyata menyebut Surah/Ayat di luar database (Halusinasi)
            if not ayat_terpilih:
                if "surah" in teks_nasihat_ai.lower() and "ayat" in teks_nasihat_ai.lower():
                    ayat_terpilih = None # KOSONGKAN UI agar tidak memalukan/salah
                else:
                    ayat_terpilih = data_quran['matches'][0]['metadata']

        return {
            "intent": intent,
            "nasihat_ai": teks_nasihat_ai,
            "raw_quran": ayat_terpilih,
            "raw_artikel": data_artikel['matches'][0]['metadata'] if data_artikel and data_artikel['matches'] else None
        }

    def _rewrite_query(self, teks: str) -> str:
        # Regex sakti untuk membuang semua basa-basi user di awal kalimat
        pola_basa_basi = r"^(?:tolong |coba |carikan |cari |tampilkan |berikan |apa |bagaimana |ayat |surah |dalil |tentang |mengenai |yang |membahas |menjelaskan |kata quran |aku |dalam )+"
        teks_lower = teks.lower().strip(" ?")
        inti_kueri = re.sub(pola_basa_basi, "", teks_lower).strip()
        
        return f"ajaran Islam tentang {inti_kueri}"