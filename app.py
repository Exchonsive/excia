import streamlit as st
from backend import ExciaOrchestrator

# 1. Konfigurasi Halaman (Pastikan layout="wide" aktif)
st.set_page_config(page_title="EXCIA - Asisten Spiritual", page_icon="🕋", layout="wide")

# 2. Injeksi CSS Khusus (Sudah Diperbaiki Full Width & Bar Bawah)
st.markdown(
    """
    <link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap' rel='stylesheet'>
    <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stAppViewBlock"] {
            background: linear-gradient(135deg, #0f172a 0%, #0a2540 100%) !important;
            color: #e0f2fe;
            font-family: 'Inter', Arial, sans-serif;
        }
        [data-testid="stHeader"] {display: none;}
        
        /* PERBAIKAN 1: LAYOUT MELEBAR SAMPAI PINGGIR */
        .block-container {
            padding-top: 2rem; 
            padding-bottom: 6rem; 
            max-width: 95% !important; /* Diubah dari 800px agar full width */
        }
        
        .main-title {
            font-size: 5rem;
            font-weight: 900;
            color: #38bdf8;
            text-align: center;
            letter-spacing: -0.03em;
            margin-bottom: 0.15rem;
            text-shadow: 0 4px 32px #0ff3, 0 1px 0 #222b;
        }
        .main-subtitle {
            font-size: 1.08rem;
            color: #a5b4fc;
            text-align: center;
            margin-bottom: 2.5rem;
            font-weight: 400;
        }
        
        /* Modifikasi Chat Bubble */
        .chat-bubble {
            border-radius: 12px;
            padding: 1.2rem 1.5rem;
            margin-bottom: 1.2rem;
            text-align: left;
            line-height: 1.6;
        }
        .chat-bubble.nasihat {
            background: rgba(34,211,238,0.12);
            border-left: 4px solid #38bdf8;
            color: #ffffff;
            font-size: 1.1rem;
            font-weight: 600;
            box-shadow: 0 4px 20px rgba(56,189,248,0.1);
        }
        .chat-bubble.surah {
            color: #38bdf8;
            font-size: 0.95rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            margin-bottom: 0.5rem;
            margin-top: 1rem;
        }
        .chat-bubble.ayat {
            background: rgba(59,130,246,0.08);
            border: 1px solid rgba(125,211,252,0.3);
            color: #bae6fd;
            font-size: 1.8rem;
            font-weight: 700;
            text-align: right;
            direction: rtl; 
            line-height: 2.2;
            padding: 1.5rem;
            font-family: 'Amiri', 'Scheherazade New', serif;
        }
        .chat-bubble.terjemahan {
            color: #a5b4fc;
            font-size: 1.05rem;
            font-style: italic;
            margin-top: -0.5rem;
            margin-bottom: 1.5rem;
        }
        .chat-bubble.tafsir, .chat-bubble.artikel {
            background: rgba(59,130,246,0.05);
            border: 1px solid rgba(165,180,252,0.2);
            color: #cbd5e1;
            font-size: 0.95rem;
        }
        
        /* PERBAIKAN 2: MENGHANCURKAN BAR PUTIH BAWAAN STREAMLIT */
        [data-testid="stBottom"], [data-testid="stBottom"] > div {
            background-color: #0a2540 !important; /* Samakan dengan warna dasar gradient paling bawah */
            background: transparent !important;
        }
        [data-testid="stBottomBlock"] {
            background: transparent !important;
        }

        /* Desain Input Chat Box */
        [data-testid="stChatInput"] {
            background-color: #1e293b !important; 
            border: 1px solid #38bdf8 !important;
            border-radius: 12px !important;
        }
        [data-testid="stChatInput"] textarea {
            color: #ffffff !important;
        }
        [data-testid="stChatInput"] textarea::placeholder {
            color: #94a3b8 !important;
        }
        [data-testid="stChatInput"] svg {
            fill: #38bdf8 !important; 
        }
        [data-testid="stChatMessageContent"] {
            color: #e0f2fe !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# 3. Inisialisasi Mesin
@st.cache_resource
def siapkan_mesin():
    repo_hf = "Exchonsive/excia-indobert-intent"
    return ExciaOrchestrator(repo_hf)

try:
    excia = siapkan_mesin()
except Exception as exc:
    st.error("Maaf, mesin EXCIA sedang tidak bisa dijalankan saat ini. Periksa konfigurasi API terlebih dahulu.")
    st.caption(str(exc))
    st.stop()

# 4. Header Web
st.markdown(
    """
    <div class="main-title">EXCIA</div>
    <div class="main-subtitle">Asisten Spiritual AI<br>Mencerahkan pikiranmu dengan panduan dari Al-Qur'an</div>
    """,
    unsafe_allow_html=True,
)

# 5. INISIALISASI MEMORI CHAT (Session State)
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Halo! Aku EXCIA. Ceritakan apa yang sedang membebani pikiranmu hari ini, insyaAllah kita cari solusinya bersama dari petunjuk Al-Qur'an."}
    ]

# 6. MENAMPILKAN RIWAYAT CHAT
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.write(msg["content"])
        else:
            if msg["content"]:
                st.markdown(f"<div class='chat-bubble nasihat'>{msg['content']}</div>", unsafe_allow_html=True)
            
            if msg.get("raw_quran"):
                st.markdown("### 📖 Sumber Referensi")
                surah = msg["raw_quran"].get('surat', '-')
                ayat = msg["raw_quran"].get('ayat', '-')
                teks_arab = msg["raw_quran"].get('teks_arab', None)
                teks_terjemah = msg.get("teks_terjemah", None)
                teks_tafsir_bersih = msg.get("teks_tafsir_bersih", "")
                
                st.markdown(f"<div class='chat-bubble surah'>SURAH {surah} • AYAT {ayat}</div>", unsafe_allow_html=True)
                if teks_arab:
                    st.markdown(f"<div class='chat-bubble ayat'>{teks_arab}</div>", unsafe_allow_html=True)
                if teks_terjemah:
                    st.markdown(f"<div class='chat-bubble terjemahan'>\"{teks_terjemah}\"</div>", unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    with st.expander("📚 Baca Tafsir Lengkap"):
                        if teks_tafsir_bersih:
                            st.markdown(f"<div class='chat-bubble tafsir'>{teks_tafsir_bersih}</div>", unsafe_allow_html=True)
                        else:
                            st.write("Tidak ada tafsir spesifik.")

                with col2:
                    with st.expander("📝 Baca Artikel Terkait"):
                        if msg.get("raw_artikel"):
                            judul = msg["raw_artikel"].get('judul', '-')
                            url = msg["raw_artikel"].get('url', None)
                            cuplikan = (msg["raw_artikel"].get('teks_lengkap', '') or '')[:500]
                            st.markdown(f"<div class='chat-bubble artikel'><b>{judul}</b><br><br>{cuplikan}...</div>", unsafe_allow_html=True)
                            if url:
                                st.markdown(f"<a href='{url}' target='_blank' style='color:#38bdf8; font-weight:bold; text-decoration:none;'>🔗 Buka sumber</a>", unsafe_allow_html=True)

# 7. LOGIKA INPUT CHAT BARU
if prompt := st.chat_input("Tulis curhatan atau pertanyaanmu di sini..."):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("EXCIA sedang menyiapkan nasihat dan rujukan terbaik..."):
            hasil = excia.proses_curhatan(prompt)
            
            teks_lengkap_raw = hasil['raw_quran'].get('teks_lengkap', '') if hasil['raw_quran'] else ''
            teks_terjemah_terpisah = hasil['raw_quran'].get('teks_terjemah', None) if hasil['raw_quran'] else None
            teks_tafsir_final = teks_lengkap_raw
            
            if hasil['raw_quran'] and not teks_terjemah_terpisah and "Terjemahan:" in teks_lengkap_raw and "Tafsir:" in teks_lengkap_raw:
                try:
                    potongan_awal = teks_lengkap_raw.split("Tafsir:")[0]
                    teks_terjemah_terpisah = potongan_awal.split("Terjemahan:")[1].strip()
                    teks_tafsir_final = teks_lengkap_raw.split("Tafsir:")[1].strip()
                except:
                    pass

            st.markdown(f"<div class='chat-bubble nasihat'>{hasil['nasihat_ai']}</div>", unsafe_allow_html=True)
            
            if hasil['raw_quran']:
                st.markdown("### 📖 Sumber Referensi")
                surah = hasil['raw_quran'].get('surat', '-')
                ayat = hasil['raw_quran'].get('ayat', '-')
                teks_arab = hasil['raw_quran'].get('teks_arab', None)
                
                st.markdown(f"<div class='chat-bubble surah'>SURAH {surah} • AYAT {ayat}</div>", unsafe_allow_html=True)
                if teks_arab:
                    st.markdown(f"<div class='chat-bubble ayat'>{teks_arab}</div>", unsafe_allow_html=True)
                if teks_terjemah_terpisah:
                    st.markdown(f"<div class='chat-bubble terjemahan'>\"{teks_terjemah_terpisah}\"</div>", unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    with st.expander("📚 Baca Tafsir Lengkap"):
                        st.markdown(f"<div class='chat-bubble tafsir'>{teks_tafsir_final}</div>", unsafe_allow_html=True)

                with col2:
                    with st.expander("📝 Baca Artikel Terkait"):
                        if hasil['raw_artikel']:
                            judul = hasil['raw_artikel'].get('judul', '-')
                            url = hasil['raw_artikel'].get('url', None)
                            cuplikan = (hasil['raw_artikel'].get('teks_lengkap', '') or '')[:500]
                            st.markdown(f"<div class='chat-bubble artikel'><b>{judul}</b><br><br>{cuplikan}...</div>", unsafe_allow_html=True)
                            if url:
                                st.markdown(f"<a href='{url}' target='_blank' style='color:#38bdf8; font-weight:bold; text-decoration:none;'>🔗 Buka sumber</a>", unsafe_allow_html=True)

        st.session_state.messages.append({
            "role": "assistant",
            "content": hasil['nasihat_ai'],
            "raw_quran": hasil['raw_quran'],
            "raw_artikel": hasil['raw_artikel'],
            "teks_terjemah": teks_terjemah_terpisah,
            "teks_tafsir_bersih": teks_tafsir_final
        })