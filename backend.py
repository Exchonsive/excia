import os
import re
import json
import time
import hashlib
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
from google import genai
from google.genai import types

# ─────────────────────────────────────────────────────────────────────────────
#  KONSTANTA
# ─────────────────────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD  = 60    # Di bawah ini, UI tampilkan disclaimer
MIN_CALL_INTERVAL     = 3.0   # Detik minimum antar Gemini call (free tier: 30 RPM)
CACHE_MAX_SIZE        = 50    # Maksimum entri cache in-memory

# JSON Schema di-enforce di level API — bukan sekadar instruksi prompt.
# is_relevant menggabungkan off-topic guard + jawaban dalam 1 call.
RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    required=["is_relevant", "nasihat", "ayat_dipilih_index", "confidence", "alasan_confidence"],
    properties={
        "is_relevant": types.Schema(
            type=types.Type.BOOLEAN,
            description=(
                "true jika pesan relevan dengan Islam (ibadah, akhlak, aqidah, fiqih, "
                "kisah nabi/sahabat, doa, Al-Qur'an, hadis, atau masalah hidup dari "
                "perspektif Islam). false jika sama sekali tidak ada kaitannya."
            ),
        ),
        "nasihat": types.Schema(
            type=types.Type.STRING,
            description=(
                "Teks nasihat lengkap dalam Bahasa Indonesia jika is_relevant true. "
                "String kosong jika is_relevant false."
            ),
        ),
        "ayat_dipilih_index": types.Schema(
            type=types.Type.INTEGER,
            description=(
                "Index kandidat ayat yang dipilih (1–5). "
                "0 jika tidak ada yang relevan atau is_relevant false."
            ),
        ),
        "confidence": types.Schema(
            type=types.Type.INTEGER,
            description="Skor keyakinan 0–100. 0 jika is_relevant false.",
        ),
        "alasan_confidence": types.Schema(
            type=types.Type.STRING,
            description="Satu kalimat singkat alasan skor confidence.",
        ),
    },
)


class ExciaOrchestrator:
    """
    Pipeline EXCIA — 1 Gemini call per pesan dengan:
      Layer 1 : response_schema (enforce struktur di level inference)
      Layer 2 : RAG-only context (hanya Pinecone, tanpa general knowledge)
      Layer 3 : verifikasi programatik Python (hakim akhir validitas ayat)
      Extra   : rate limiter + exponential backoff + response cache
    """

    def __init__(self, hf_repo_name: str):
        print("Memuat Komponen EXCIA...")

        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        gemini_keys_raw  = os.getenv("GEMINI_API_KEY")

        if not pinecone_api_key or not gemini_keys_raw:
            raise ValueError(
                "Kritikal Error: PINECONE_API_KEY atau GEMINI_API_KEY belum diatur!"
            )

        self.gemini_keys     = [k.strip() for k in gemini_keys_raw.split(",")]
        self.current_key_idx = 0
        self._last_call_time = 0.0          # untuk rate limiter
        self._response_cache: dict = {}     # cache in-memory {hash: hasil}

        # ── IndoBERT intent classifier ────────────────────────────────────
        self.tokenizer    = AutoTokenizer.from_pretrained(hf_repo_name)
        self.intent_model = AutoModelForSequenceClassification.from_pretrained(hf_repo_name)
        self.label_mapping = {
            0: "Aqidah",
            1: "Fiqih/Hukum",
            2: "Akhlak/Psikologi",
            3: "Kisah/Sejarah",
            4: "Muamalah/Sosial",
        }

        # ── Embedding model ───────────────────────────────────────────────
        self.embed_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

        # ── Pinecone ──────────────────────────────────────────────────────
        self.pc    = Pinecone(api_key=pinecone_api_key)
        self.index = self.pc.Index("excia-index")

        # ── Gemini client (SDK baru: google-genai) ────────────────────────
        self.client = genai.Client(api_key=self.gemini_keys[self.current_key_idx])

        # ── Kamus normalisasi slang ───────────────────────────────────────
        self.kamus_slang = {
            "yg":           "yang",
            "gmn":          "bagaimana",
            "gimana":       "bagaimana",
            "bgt":          "sekali",
            "banget":       "sekali",
            "gk":           "tidak",
            "nggak":        "tidak",
            "insecure":     "kurang percaya diri",
            "overthinking": "terlalu banyak berpikir",
        }

        print("EXCIA siap digunakan.")

    # ══════════════════════════════════════════════════════════════════════════
    #  RATE LIMITER + EXPONENTIAL BACKOFF + CACHE
    # ══════════════════════════════════════════════════════════════════════════

    def _rate_limit_wait(self):
        """Pastikan jeda minimum MIN_CALL_INTERVAL detik antar Gemini call."""
        elapsed = time.time() - self._last_call_time
        if elapsed < MIN_CALL_INTERVAL:
            time.sleep(MIN_CALL_INTERVAL - elapsed)

    def _cache_key(self, prompt: str) -> str:
        """MD5 hash prompt sebagai cache key."""
        return hashlib.md5(prompt.encode()).hexdigest()

    def _cache_get(self, key: str):
        return self._response_cache.get(key)

    def _cache_set(self, key: str, value: str):
        # Buang entri terlama jika cache penuh
        if len(self._response_cache) >= CACHE_MAX_SIZE:
            oldest = next(iter(self._response_cache))
            del self._response_cache[oldest]
        self._response_cache[key] = value

    def _ganti_key(self):
        """Rotasi ke API key berikutnya."""
        self.current_key_idx = (self.current_key_idx + 1) % len(self.gemini_keys)
        self.client = genai.Client(api_key=self.gemini_keys[self.current_key_idx])
        print(f"⚠️  Ganti ke key ke-{self.current_key_idx + 1}")

    def _generate_dengan_cadangan(self, prompt_teks: str) -> str:
        """
        Generate dengan:
        - Cache        : prompt identik tidak re-call API
        - Rate limiter : jeda minimum antar call
        - Key rotation : ganti key jika 429
        - Model fallback: turun ke model lebih ringan jika 503 overload
        - Exponential backoff: tunggu makin lama tiap retry
        """
        cache_key = self._cache_key(prompt_teks)
        cached    = self._cache_get(cache_key)
        if cached:
            print("✅ Cache hit — skip API call")
            return cached

        # Urutan model fallback: mulai dari paling ringan, turun jika overload
        model_fallback = [
            "gemini-3.1-flash-lite", # primer : 15 RPM, GA sejak 7 Mei 2026
            "gemini-2.5-flash-lite", # fallback 1: 15 RPM jika 3.1 overload
            "gemini-2.5-flash",      # fallback 2: 10 RPM terakhir dicoba
        ]
        model_idx     = 0
        maks_retry    = len(self.gemini_keys) * len(model_fallback) * 2
        backoff_detik = 5.0

        for percobaan in range(maks_retry):
            model_saat_ini = model_fallback[model_idx % len(model_fallback)]
            try:
                self._rate_limit_wait()
                self._last_call_time = time.time()

                response = self.client.models.generate_content(
                    model=model_saat_ini,
                    contents=prompt_teks,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=RESPONSE_SCHEMA,
                        temperature=0.3,
                        top_p=0.85,
                    ),
                )
                hasil = response.text
                self._cache_set(cache_key, hasil)
                return hasil

            except Exception as exc:
                pesan = str(exc)
                is_rate_limit  = any(k in pesan for k in ("429", "ResourceExhausted", "quota", "RESOURCE_EXHAUSTED"))
                is_unavailable = any(k in pesan for k in ("503", "UNAVAILABLE", "high demand", "overloaded"))

                if is_unavailable:
                    # Server overload — coba model berikutnya di fallback list
                    model_idx += 1
                    model_baru = model_fallback[model_idx % len(model_fallback)]
                    print(f"⚠️  503 overload pada {model_saat_ini}, "
                          f"coba {model_baru} (percobaan {percobaan + 1})...")
                    time.sleep(3)

                elif is_rate_limit:
                    print(f"⏳ Rate limit pada {model_saat_ini} "
                          f"(percobaan {percobaan + 1}/{maks_retry}), "
                          f"tunggu {backoff_detik:.0f}s...")
                    # Ganti key dulu
                    if len(self.gemini_keys) > 1:
                        self._ganti_key()
                        time.sleep(2)
                    else:
                        time.sleep(backoff_detik)
                        backoff_detik = min(backoff_detik * 2, 60)

                else:
                    raise

        # Semua percobaan habis
        return json.dumps({
            "is_relevant":        True,
            "nasihat":            (
                "Maaf, server EXCIA sedang sangat sibuk saat ini. "
                "Mohon tunggu 1–2 menit lalu coba lagi ya 🙏"
            ),
            "ayat_dipilih_index": 0,
            "confidence":         0,
            "alasan_confidence":  "Server tidak tersedia sementara.",
        })

    # ══════════════════════════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _parse_json_response(self, raw: str) -> dict:
        """Parse JSON dari respons Gemini. Tahan terhadap markdown fence."""
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return {}

    def _rewrite_query(self, teks: str) -> str:
        """Buang basa-basi, sisakan inti topik untuk embedding."""
        pola = (
            r"^(?:tolong |coba |carikan |cari |tampilkan |berikan |apa |bagaimana |"
            r"ayat |surah |dalil |tentang |mengenai |yang |membahas |menjelaskan |"
            r"kata quran |aku |dalam )+"
        )
        inti = re.sub(pola, "", teks.lower().strip(" ?")).strip()
        return f"ajaran Islam tentang {inti}"

    def normalisasi_teks(self, teks: str) -> str:
        return " ".join(self.kamus_slang.get(k, k) for k in teks.lower().split())

    def prediksi_intent(self, teks: str) -> str:
        inputs = self.tokenizer(
            teks, return_tensors="pt", truncation=True, padding=True, max_length=128
        )
        with torch.no_grad():
            outputs = self.intent_model(**inputs)
        idx = torch.argmax(outputs.logits, dim=1).item()
        return self.label_mapping[idx]

    # ══════════════════════════════════════════════════════════════════════════
    #  RETRIEVAL
    # ══════════════════════════════════════════════════════════════════════════

    def cari_referensi_terpisah(self, vektor_quran, vektor_artikel, intent_kategori):
        hasil_quran = self.index.query(
            vector=vektor_quran,
            top_k=5,
            include_metadata=True,
            filter={"tipe_dokumen": {"$eq": "quran"}},
        )
        hasil_artikel = self.index.query(
            vector=vektor_artikel,
            top_k=1,
            include_metadata=True,
            filter={
                "tipe_dokumen":    {"$eq": "artikel"},
                "intent_kategori": {"$eq": intent_kategori},
            },
        )
        return hasil_quran, hasil_artikel

    # ══════════════════════════════════════════════════════════════════════════
    #  LAYER 3 — VERIFIKASI PROGRAMATIK
    # ══════════════════════════════════════════════════════════════════════════

    def _verifikasi_dan_sinkronkan(self, parsed: dict, data_quran: dict):
        """
        Python sebagai hakim akhir validitas ayat.
        Return metadata ayat yang valid dari Pinecone, atau None.
        """
        idx     = parsed.get("ayat_dipilih_index", 0)
        matches = (data_quran or {}).get("matches", [])

        if idx == 0 or not isinstance(idx, int) or idx < 1 or idx > len(matches):
            return None

        ayat_meta    = matches[idx - 1]["metadata"]
        nasihat      = parsed.get("nasihat", "").lower()
        nama_surat   = (
            ayat_meta.get("surat", "").lower()
            .replace("-", " ").replace("al ", "").strip()
        )
        nomor_ayat   = str(ayat_meta.get("ayat", ""))
        nasihat_norm = nasihat.replace("-", " ").replace("al ", "").strip()

        if "ayat" in nasihat and nomor_ayat not in nasihat:
            return None
        if "surah" in nasihat and nama_surat and nama_surat not in nasihat_norm:
            return None

        return ayat_meta

    # ══════════════════════════════════════════════════════════════════════════
    #  MAIN ORCHESTRATOR
    # ══════════════════════════════════════════════════════════════════════════

    def proses_curhatan(self, input_user: str, chat_history: list = None) -> dict:
        """Pipeline utama EXCIA — 1 Gemini call per pesan."""

        # ── Normalisasi & intent (lokal, gratis) ──────────────────────────
        teks_baku = self.normalisasi_teks(input_user)
        intent    = self.prediksi_intent(teks_baku)

        persona_panduan = {
            "Aqidah":           "Fokus pada penguatan iman dan tauhid. Gunakan bahasa yang meneguhkan hati.",
            "Fiqih/Hukum":      "Jawab dengan lugas dan terstruktur. Fokus pada batasan syariat secara objektif.",
            "Akhlak/Psikologi": "Jawab dengan empati dan kelembutan layaknya psikolog Islami.",
            "Kisah/Sejarah":    "Gunakan pendekatan storytelling. Ambil hikmah dari ayat atau tokoh masa lalu.",
            "Muamalah/Sosial":  "Fokus pada etika bermasyarakat dan berikan solusi praktis.",
        }
        instruksi_persona = persona_panduan.get(intent, "Berikan nasihat yang hangat dan menenangkan.")

        # ── History percakapan ────────────────────────────────────────────
        konteks_history = ""
        if chat_history:
            for msg in chat_history[-4:]:   # Kurangi dari 6 → 4 untuk hemat token
                role = "Pengguna" if msg["role"] == "user" else "EXCIA"
                konteks_history += f"{role}: {msg['content'][:300]}\n"  # potong panjang

        # ── Embedding & retrieval Pinecone (gratis) ───────────────────────
        teks_rewrite   = self._rewrite_query(teks_baku)
        vektor_quran   = self.embed_model.encode(
            teks_rewrite, normalize_embeddings=True
        ).tolist()
        vektor_artikel = self.embed_model.encode(
            f"Artikel Islami tentang {intent}. Topik: {teks_rewrite}",
            normalize_embeddings=True,
        ).tolist()

        data_quran, data_artikel = self.cari_referensi_terpisah(
            vektor_quran, vektor_artikel, intent
        )

        # ── Siapkan konteks ayat (Layer 2: RAG-only) ──────────────────────
        matches       = (data_quran or {}).get("matches", [])
        ada_referensi = bool(matches)

        if ada_referensi:
            teks_tafsir_gabungan = ""
            for i, match in enumerate(matches):
                meta        = match["metadata"]
                teks_utuh   = meta.get("teks_lengkap", "")
                # Potong lebih pendek untuk hemat token → 600 karakter
                teks_potong = (
                    teks_utuh[:600] + "...[dipotong]"
                    if len(teks_utuh) > 600 else teks_utuh
                )
                teks_tafsir_gabungan += (
                    f"\nKandidat [{i+1}] — Surah {meta.get('surat')} "
                    f"Ayat {meta.get('ayat')}:\n{teks_potong}\n"
                )
        else:
            teks_tafsir_gabungan = "KOSONG — tidak ada ayat ditemukan di database."

        if data_artikel and data_artikel.get("matches"):
            artikel_utuh = data_artikel["matches"][0]["metadata"].get("teks_lengkap", "")
            # Potong lebih pendek → 800 karakter
            teks_artikel = (
                artikel_utuh[:800] + "...[dipotong]"
                if len(artikel_utuh) > 800 else artikel_utuh
            )
        else:
            teks_artikel = "Tidak ada artikel terkait."

        # ── Prompt (ringkas untuk hemat token) ───────────────────────────
        prompt_llm = f"""Kamu adalah Asisten Spiritual EXCIA berbasis Al-Qur'an.

LANGKAH 1 — CEK RELEVANSI:
Jika pesan tidak berkaitan Islam: is_relevant=false, nasihat="", index=0, confidence=0.

LANGKAH 2 — JAWAB (hanya jika relevan):
- Hanya rujuk ayat dari kandidat di bawah. Jangan mengarang ayat.
- Jika pakai ayat, sebut nama Surah dan nomor Ayat secara eksplisit.
- Gaya: {instruksi_persona}

[RIWAYAT]: {konteks_history if konteks_history else "Awal percakapan."}
[PESAN]: "{input_user}"

[KANDIDAT AYAT]:
{teks_tafsir_gabungan}

[ARTIKEL]: {teks_artikel}

Confidence: 85-100=ayat sangat cocok, 60-84=cukup relevan, 40-59=kurang pas, 0-39=tidak ada referensi.
"""

        # ── Generate + parse ──────────────────────────────────────────────
        raw_response = self._generate_dengan_cadangan(prompt_llm)
        parsed       = self._parse_json_response(raw_response)

        # ── Cek is_relevant ───────────────────────────────────────────────
        if not parsed.get("is_relevant", True):
            return {
                "intent":            None,
                "nasihat_ai":        (
                    "Maaf, aku EXCIA — asisten spiritual berbasis Al-Qur'an. "
                    "Aku hanya bisa membantu pertanyaan seputar Islam, ibadah, akhlak, "
                    "atau tantangan hidup dari sudut pandang Islam. "
                    "Untuk pertanyaan lain, kamu bisa mencarinya di mesin pencari ya 😊"
                ),
                "raw_quran":         None,
                "raw_artikel":       None,
                "confidence":        None,
                "alasan_confidence": None,
                "off_topic":         True,
            }

        # ── Ekstrak & validasi ────────────────────────────────────────────
        nasihat_ai = parsed.get("nasihat") or "Maaf, terjadi kesalahan memproses jawaban."
        alasan     = parsed.get("alasan_confidence", "")

        try:
            confidence = int(parsed.get("confidence", 0))
            confidence = max(0, min(100, confidence))
        except (TypeError, ValueError):
            confidence = None

        # Layer 3: verifikasi programatik
        ayat_terpilih = self._verifikasi_dan_sinkronkan(parsed, data_quran)

        return {
            "intent":            intent,
            "nasihat_ai":        nasihat_ai,
            "raw_quran":         ayat_terpilih,
            "raw_artikel":       (
                data_artikel["matches"][0]["metadata"]
                if data_artikel and data_artikel.get("matches") else None
            ),
            "confidence":        confidence,
            "alasan_confidence": alasan,
            "off_topic":         False,
        }