import streamlit as st
from backend import ExciaOrchestrator

# 1. Konfigurasi Halaman (Harus di paling atas)
st.set_page_config(page_title="EXCIA - Asisten Spiritual", page_icon="✨", layout="wide")

# 2. Inisialisasi Mesin Backend (Menggunakan Cache agar tidak perlu load model berulang kali)
@st.cache_resource
def siapkan_mesin():
    # GANTI STRING DI BAWAH DENGAN KREDENSIAL ASLIMU
    repo_hf = "USERNAME_KAMU/excia-indobert-intent" 
    kunci_pinecone = "API_KEY_PINECONE_KAMU"
    kunci_gemini = "API_KEY_GEMINI_KAMU"
    
    return ExciaOrchestrator(repo_hf, kunci_pinecone, kunci_gemini)

excia = siapkan_mesin()

# 3. Header UI
st.title("✨ EXCIA: Asisten Spiritual AI")
st.markdown("Ceritakan apa yang sedang membebani pikiranmu hari ini. Sistem akan mencarikan panduan dari Al-Qur'an dan merangkumnya khusus untukmu.")
st.divider()

# 4. Form Input User
teks_input = st.text_area("Tuliskan curhatan atau pertanyaanmu di sini:", height=100, placeholder="Contoh: Jujur aku lagi overthinking banget soal kerjaan...")
tombol_kirim = st.button("Minta Nasihat", type="primary")

# 5. Logika Eksekusi dan Desain 3 Panel
if tombol_kirim and teks_input:
    with st.spinner("EXCIA sedang menganalisis dan mencari referensi terbaik untukmu..."):
        # Panggil fungsi dari backend.py
        hasil = excia.proses_curhatan(teks_input)
        
        st.success(f"Analisis Selesai! Kategori terdeteksi: **{hasil['intent']}**")
        
        # --- DESAIN UI GRID ---
        # Panel 1: Nasihat AI (Lebar penuh di atas)
        st.subheader("💡 Nasihat untukmu")
        st.info(hasil['nasihat_ai'])
        
        st.divider()
        st.subheader("📚 Sumber Referensi yang Digunakan")
        
        # Membagi layar menjadi 2 kolom untuk referensi raw data
        kolom_kiri, kolom_kanan = st.columns(2)
        
        # Panel 2: Kartu Al-Qur'an (Kolom Kiri)
        with kolom_kiri:
            with st.expander("📖 Referensi Al-Qur'an", expanded=True):
                if hasil['raw_quran']:
                    st.markdown(f"**Surat {hasil['raw_quran']['surat']} Ayat {hasil['raw_quran']['ayat']}**")
                    st.write("Tafsir Kemenag:")
                    st.write(hasil['raw_quran']['teks_lengkap'])
                else:
                    st.write("Tidak ada ayat yang spesifik ditemukan.")
                    
        # Panel 3: Artikel Pendukung (Kolom Kanan)
        with kolom_kanan:
            with st.expander("📝 Artikel Pendukung", expanded=True):
                if hasil['raw_artikel']:
                    st.markdown(f"**[{hasil['raw_artikel']['judul']}]({hasil['raw_artikel']['url']})**")
                    st.write(hasil['raw_artikel']['teks_lengkap'][:500] + "...") # Tampilkan cuplikan saja
                else:
                    st.write("Tidak ada artikel terkait ditemukan.")