import streamlit as st
from backend import ExciaOrchestrator

# ─────────────────────────────────────────────────────────────────────────────
#  1. KONFIGURASI HALAMAN
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EXCIA - Asisten Spiritual",
    page_icon="✨",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
#  2. CSS GLOBAL
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap' rel='stylesheet'>
    <style>
        html, body,
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewBlock"] {
            background: linear-gradient(135deg, #0f172a 0%, #0a2540 100%) !important;
            color: #e0f2fe;
            font-family: 'Inter', Arial, sans-serif;
        }
        [data-testid="stHeader"] { display: none; }

        .block-container {
            padding-top: 3rem;
            padding-bottom: 7rem;
            max-width: 90% !important;
        }

        /* ── Typography ── */
        .main-title {
            font-size: 4.5rem;
            font-weight: 900;
            color: #38bdf8;
            text-align: center;
            letter-spacing: -0.04em;
            margin-bottom: 0.2rem;
            text-shadow: 0 4px 32px rgba(56,189,248,0.4), 0 1px 0 rgba(0,0,0,0.5);
        }
        .main-subtitle {
            font-size: 1.1rem;
            color: #94a3b8;
            text-align: center;
            margin-bottom: 3.5rem;
            font-weight: 400;
            letter-spacing: 0.02em;
        }

        /* ── Badge intent ── */
        .badge-intent {
            display: inline-block;
            background: rgba(56,189,248,0.1);
            border: 1px solid rgba(56,189,248,0.3);
            color: #7dd3fc;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 8px;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }

        /* ── Badge confidence ── */
        .badge-confidence-high {
            display: inline-block;
            background: rgba(16,185,129,0.1);
            border: 1px solid rgba(16,185,129,0.35);
            color: #6ee7b7;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 8px;
            letter-spacing: 0.04em;
        }
        .badge-confidence-low {
            display: inline-block;
            background: rgba(245,158,11,0.1);
            border: 1px solid rgba(245,158,11,0.35);
            color: #fcd34d;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 8px;
            letter-spacing: 0.04em;
        }
        .disclaimer-box {
            background: rgba(245,158,11,0.08);
            border: 1px solid rgba(245,158,11,0.25);
            border-radius: 10px;
            padding: 0.8rem 1.2rem;
            margin-top: 0.5rem;
            margin-bottom: 0.8rem;
            color: #fcd34d;
            font-size: 0.9rem;
            line-height: 1.6;
        }

        /* ── Chat bubbles ── */
        .chat-bubble {
            border-radius: 14px;
            padding: 1.4rem 1.6rem;
            margin-bottom: 1.2rem;
            text-align: left;
            line-height: 1.7;
            font-size: 1.05rem;
        }
        .chat-bubble.nasihat {
            background: rgba(30,41,59,0.7);
            border-left: 4px solid #38bdf8;
            color: #f8fafc;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }

        /* ── Referensi Qur'an ── */
        .ref-header {
            font-size: 1.2rem;
            font-weight: 700;
            color: #38bdf8;
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .chat-bubble.surah {
            color: #7dd3fc;
            font-size: 0.9rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            margin-bottom: 0.5rem;
            margin-top: 0.5rem;
        }
        .chat-bubble.ayat {
            background: rgba(15,23,42,0.4);
            border: 1px solid rgba(56,189,248,0.15);
            color: #bae6fd;
            font-size: 2rem;
            font-weight: 700;
            text-align: right;
            direction: rtl;
            line-height: 2.4;
            padding: 1.5rem 2rem;
            border-radius: 16px;
            font-family: 'Amiri', 'Scheherazade New', serif;
            box-shadow: inset 0 2px 10px rgba(0,0,0,0.2);
        }
        .chat-bubble.terjemahan {
            color: #94a3b8;
            font-size: 1.1rem;
            font-style: italic;
            margin-top: -0.5rem;
            margin-bottom: 2rem;
            padding-left: 1rem;
            border-left: 2px solid rgba(148,163,184,0.3);
        }

        /* ── Expanders ── */
        .chat-bubble.tafsir,
        .chat-bubble.artikel {
            background: rgba(15,23,42,0.3);
            border: 1px solid rgba(148,163,184,0.15);
            color: #cbd5e1;
            font-size: 0.95rem;
            line-height: 1.8;
            border-radius: 12px;
        }
        .scrollable-box {
            max-height: 380px;
            overflow-y: auto;
            padding-right: 12px;
        }
        .scrollable-box::-webkit-scrollbar { width: 6px; }
        .scrollable-box::-webkit-scrollbar-track { background: transparent; }
        .scrollable-box::-webkit-scrollbar-thumb {
            background: rgba(56,189,248,0.3);
            border-radius: 8px;
        }
        .scrollable-box::-webkit-scrollbar-thumb:hover {
            background: rgba(56,189,248,0.6);
        }
        .artikel-title {
            font-size: 1.1rem;
            color: #e0f2fe;
            font-weight: 700;
            margin-bottom: 1rem;
            padding-bottom: 0.8rem;
            border-bottom: 1px solid rgba(148,163,184,0.2);
        }
        .btn-sumber {
            display: inline-block;
            margin-top: 1.5rem;
            padding: 0.6rem 1.4rem;
            background: transparent;
            color: #38bdf8 !important;
            border: 1px solid #38bdf8;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.85rem;
            transition: all 0.2s ease;
            text-align: center;
            width: 100%;
        }
        .btn-sumber:hover {
            background: #38bdf8;
            color: #0f172a !important;
        }

        /* ── Streamlit overrides ── */
        [data-testid="stBottom"],
        [data-testid="stBottom"] > div,
        [data-testid="stBottomBlock"] {
            background: transparent !important;
        }

        /* ── Chat input ── */
        [data-testid="stChatInput"] {
            background-color: rgba(30,41,59,0.8) !important;
            border: 1px solid rgba(56,189,248,0.4) !important;
            border-radius: 16px !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
        }
        [data-testid="stChatInput"] textarea {
            color: #f8fafc !important;
            font-size: 1.05rem;
        }
        [data-testid="stChatInput"] textarea::placeholder { color: #64748b !important; }
        [data-testid="stChatInput"] svg { fill: #38bdf8 !important; }

        /* ── Avatar ── */
        [data-testid="stChatMessageAvatarUser"]      { background-color: #334155; }
        [data-testid="stChatMessageAvatarAssistant"] { background-color: #0284c7; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
#  3. KONSTANTA
# ─────────────────────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 60  # harus sama dengan di backend.py

# ─────────────────────────────────────────────────────────────────────────────
#  4. INISIALISASI MESIN
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def siapkan_mesin():
    repo_hf = "Exchonsive/excia-indobert-intent"
    return ExciaOrchestrator(repo_hf)


try:
    excia = siapkan_mesin()
except Exception as exc:
    st.error(
        "Maaf, mesin EXCIA sedang tidak bisa dijalankan. "
        "Periksa konfigurasi API terlebih dahulu."
    )
    st.caption(str(exc))
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
#  5. HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="main-title">EXCIA</div>
    <div class="main-subtitle">
        Asisten Spiritual AI berbasis Al-Qur'an &amp; Pemahaman Kontekstual
    </div>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
#  6. SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role":               "assistant",
            "content":            "Halo! Aku EXCIA. Ceritakan apa yang sedang membebani pikiranmu hari ini, insyaAllah kita cari solusinya bersama dari petunjuk Al-Qur'an.",
            "intent":             None,
            "raw_quran":          None,
            "raw_artikel":        None,
            "teks_terjemah":      None,
            "teks_tafsir_bersih": "",
            "confidence":         None,
            "alasan_confidence":  None,
        }
    ]

# ─────────────────────────────────────────────────────────────────────────────
#  7. HELPER: render badge confidence + disclaimer
# ─────────────────────────────────────────────────────────────────────────────
def render_confidence(confidence, alasan: str):
    """Tampilkan badge hijau (≥60) atau kuning (<60) beserta disclaimer."""
    if confidence is None:
        return
    if confidence >= CONFIDENCE_THRESHOLD:
        st.markdown(
            f"<div class='badge-confidence-high'>✅ Keyakinan jawaban: {confidence}/100</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='badge-confidence-low'>⚠️ Keyakinan jawaban: {confidence}/100</div>",
            unsafe_allow_html=True,
        )
        alasan_tampil = alasan or "Topik mungkin terlalu umum atau belum terdapat di database."
        st.markdown(
            f"<div class='disclaimer-box'>"
            f"🔔 <b>Catatan:</b> Referensi yang tersedia kurang spesifik untuk pertanyaan ini "
            f"({alasan_tampil}). "
            f"Untuk kepastian hukum atau fatwa, disarankan berkonsultasi langsung dengan "
            f"<b>ustadz, kyai, atau ulama</b> terpercaya."
            f"</div>",
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────────────────────────────────────
#  8. HELPER: render satu pesan asisten
# ─────────────────────────────────────────────────────────────────────────────
def render_pesan_asisten(msg: dict):
    """Render bubble asisten lengkap: badge intent, confidence, nasihat, quran, artikel."""

    # Badge intent
    if msg.get("intent"):
        st.markdown(
            f"<div class='badge-intent'>🎯 Topik Terdeteksi: {msg['intent']}</div>",
            unsafe_allow_html=True,
        )

    # Badge confidence + disclaimer
    render_confidence(msg.get("confidence"), msg.get("alasan_confidence", ""))

    # Bubble nasihat
    if msg.get("content"):
        st.markdown(
            f"<div class='chat-bubble nasihat'>{msg['content']}</div>",
            unsafe_allow_html=True,
        )

    # Referensi Al-Qur'an
    if msg.get("raw_quran"):
        st.markdown("<div class='ref-header'>📖 Sumber Referensi</div>", unsafe_allow_html=True)

        surah         = msg["raw_quran"].get("surat", "-")
        ayat          = msg["raw_quran"].get("ayat", "-")
        teks_arab     = msg["raw_quran"].get("teks_arab")
        teks_terjemah = msg.get("teks_terjemah")
        teks_tafsir   = msg.get("teks_tafsir_bersih", "")

        st.markdown(
            f"<div class='chat-bubble surah'>SURAH {surah} • AYAT {ayat}</div>",
            unsafe_allow_html=True,
        )
        if teks_arab:
            st.markdown(
                f"<div class='chat-bubble ayat'>{teks_arab}</div>",
                unsafe_allow_html=True,
            )
        if teks_terjemah:
            st.markdown(
                f"<div class='chat-bubble terjemahan'>\"{teks_terjemah}\"</div>",
                unsafe_allow_html=True,
            )

        col1, col2 = st.columns(2)
        with col1:
            with st.expander("📚 Baca Tafsir Lengkap", expanded=False):
                if teks_tafsir:
                    st.markdown(
                        f"<div class='scrollable-box'>"
                        f"<div class='chat-bubble tafsir'>{teks_tafsir}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<div class='chat-bubble tafsir'>"
                        "Tafsir tidak tersedia untuk ayat ini."
                        "</div>",
                        unsafe_allow_html=True,
                    )

        with col2:
            with st.expander("📝 Baca Artikel Terkait", expanded=False):
                if msg.get("raw_artikel"):
                    judul    = msg["raw_artikel"].get("judul", "Artikel Pendukung")
                    url      = msg["raw_artikel"].get("url")
                    cuplikan = (msg["raw_artikel"].get("teks_lengkap", "") or "")[:600]

                    html_artikel = (
                        f"<div class='scrollable-box'>"
                        f"<div class='chat-bubble artikel'>"
                        f"<div class='artikel-title'>{judul}</div>"
                        f"{cuplikan}..."
                    )
                    if url:
                        html_artikel += (
                            f"<br><a href='{url}' target='_blank' class='btn-sumber'>"
                            f"🔗 Baca Selengkapnya</a>"
                        )
                    html_artikel += "</div></div>"
                    st.markdown(html_artikel, unsafe_allow_html=True)
                else:
                    st.markdown(
                        "<div class='chat-bubble artikel'>"
                        "Maaf, saat ini belum ada artikel yang spesifik terkait topik ini "
                        "di dalam database."
                        "</div>",
                        unsafe_allow_html=True,
                    )

# ─────────────────────────────────────────────────────────────────────────────
#  9. TAMPILKAN RIWAYAT CHAT
# ─────────────────────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    avatar_icon = "👤" if msg["role"] == "user" else "✨"
    with st.chat_message(msg["role"], avatar=avatar_icon):
        if msg["role"] == "user":
            st.write(msg["content"])
        else:
            render_pesan_asisten(msg)

# ─────────────────────────────────────────────────────────────────────────────
#  10. LOGIKA INPUT CHAT BARU
# ─────────────────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Tulis curhatan atau pertanyaanmu di sini..."):

    # Simpan & tampilkan pesan user
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.write(prompt)

    # Proses & tampilkan respons asisten
    with st.chat_message("assistant", avatar="✨"):
        with st.spinner("EXCIA sedang mencari rujukan terbaik..."):
            hasil = excia.proses_curhatan(prompt, chat_history=st.session_state.messages)

            # ── Parsing terjemah & tafsir dari teks_lengkap ──────────────
            teks_terjemah_terpisah = None
            teks_tafsir_final      = ""

            if hasil["raw_quran"]:
                teks_lengkap_raw       = hasil["raw_quran"].get("teks_lengkap", "") or ""
                teks_terjemah_terpisah = hasil["raw_quran"].get("teks_terjemah") or None
                teks_tafsir_final      = teks_lengkap_raw

                # Coba pisah terjemahan & tafsir jika belum ada field terpisah
                if (
                    not teks_terjemah_terpisah
                    and "Terjemahan:" in teks_lengkap_raw
                    and "Tafsir:" in teks_lengkap_raw
                ):
                    try:
                        bagian_awal            = teks_lengkap_raw.split("Tafsir:")[0]
                        teks_terjemah_terpisah = bagian_awal.split("Terjemahan:")[1].strip()
                        teks_tafsir_final      = teks_lengkap_raw.split("Tafsir:")[1].strip()
                    except (IndexError, AttributeError):
                        pass

            # ── Susun dict pesan untuk session state & render ─────────────
            msg_asisten = {
                "role":               "assistant",
                "content":            hasil["nasihat_ai"],
                "intent":             hasil.get("intent"),
                "raw_quran":          hasil["raw_quran"],
                "raw_artikel":        hasil["raw_artikel"],
                "teks_terjemah":      teks_terjemah_terpisah,
                "teks_tafsir_bersih": teks_tafsir_final,
                "confidence":         hasil.get("confidence"),
                "alasan_confidence":  hasil.get("alasan_confidence", ""),
            }

            render_pesan_asisten(msg_asisten)

    # Simpan ke session state agar tampil saat scroll riwayat
    st.session_state.messages.append(msg_asisten)