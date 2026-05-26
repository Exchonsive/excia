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
        self.llm = genai.GenerativeModel('gemini-1.5-flash')
        
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
            top_k=1, 
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

    def proses_curhatan(self, input_user):
        teks_baku = self.normalisasi_teks(input_user)
        intent = self.prediksi_intent(teks_baku)
        vektor_query = self.embed_model.encode(teks_baku).tolist()
        
        data_quran, data_artikel = self.cari_referensi(vektor_query, intent)
        
        teks_tafsir = data_quran['matches'][0]['metadata']['teks_lengkap'] if data_quran['matches'] else "Tidak ada referensi ayat."
        teks_artikel = data_artikel['matches'][0]['metadata']['teks_lengkap'] if data_artikel['matches'] else "Tidak ada artikel terkait."
        
        prompt_llm = f"""
        Kamu adalah Asisten Spiritual EXCIA. Pengguna sedang menceritakan masalahnya: "{input_user}".
        
        BERIKUT ADALAH DATA REFERENSI YANG WAJIB KAMU GUNAKAN:
        [1] Tafsir Al-Qur'an: {teks_tafsir}
        [2] Artikel Pendukung: {teks_artikel}
        
        INSTRUKSI MUTLAK:
        1. Berikan nasihat yang hangat, empatik, dan menenangkan menggunakan bahasa sehari-hari.
        2. Rangkum intisari dari referensi Tafsir dan Artikel di atas ke dalam nasihatmu.
        3. DILARANG KERAS mengutip ayat di luar konteks referensi. DILARANG KERAS memodifikasi atau menerjemahkan ulang ayat. Fokus pada nasihat psikologis/spiritualnya saja.
        """
        
        respons_llm = self.llm.generate_content(prompt_llm)
        
        return {
            "intent": intent,
            "nasihat_ai": respons_llm.text,
            "raw_quran": data_quran['matches'][0]['metadata'] if data_quran['matches'] else None,
            "raw_artikel": data_artikel['matches'][0]['metadata'] if data_artikel['matches'] else None
        }