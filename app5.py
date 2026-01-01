import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
import plotly.express as px
from datetime import datetime, timedelta

# ==========================================
# KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="SPK Penentuan Waktu Unggah YouTube (SAW)",
    page_icon="📊",
    layout="wide"
)

# ==========================================
# 1. LAYER LOGIKA APLIKASI (BACKEND)
# ==========================================

# --- Fungsi Mencari Channel ---
def search_channels(api_key, keyword):
    youtube = build("youtube", "v3", developerKey=api_key)
    req = youtube.search().list(
        part="snippet", q=keyword, type="channel", maxResults=5
    )
    res = req.execute()
    channels = []
    for item in res.get("items", []):
        sn = item.get("snippet", {})
        channels.append({
            "title": sn.get("title", ""),
            "id": sn.get("channelId", ""),
            "desc": sn.get("description", ""),
            "img": sn.get("thumbnails", {}).get("default", {}).get("url", "")
        })
    return channels

# --- Fungsi Mengambil Video & Statistik ---
def get_video_stats(api_key, channel_id, limit=50):
    youtube = build("youtube", "v3", developerKey=api_key)
    
    # Langkah 1: Ambil daftar video (Search)
    search_req = youtube.search().list(
        part="snippet", channelId=channel_id, type="video", order="date", maxResults=limit
    )
    search_res = search_req.execute()
    
    video_ids = [item['id']['videoId'] for item in search_res.get('items', [])]
    
    # Langkah 2: Ambil detail statistik (Videos)
    stats_req = youtube.videos().list(
        part="snippet,statistics", id=",".join(video_ids)
    )
    stats_res = stats_req.execute()
    
    data = []
    for item in stats_res.get('items', []):
        stats = item.get('statistics', {})
        sn = item.get('snippet', {})
        
        data.append({
            "Video Title": sn.get('title'),
            "Published At": sn.get('publishedAt'),
            "Views": int(stats.get('viewCount', 0)),
            "Likes": int(stats.get('likeCount', 0)),
            "Comments": int(stats.get('commentCount', 0))
        })
    
    return pd.DataFrame(data)

# --- Fungsi Preprocessing ---
def preprocess_data(df):
    # Konversi ke Datetime
    df['Published At'] = pd.to_datetime(df['Published At'])
    
    # Konversi ke WIB (UTC + 7)
    df['Waktu_WIB'] = df['Published At'] + timedelta(hours=7)
    
    # Ekstrak Hari dan Jam
    hari_map = {
        'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu',
        'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'
    }
    df['Hari'] = df['Waktu_WIB'].dt.day_name().map(hari_map)
    df['Jam'] = df['Waktu_WIB'].dt.hour
    
    # Buat Alternatif (Gabungan Hari-Jam)
    df['Alternatif'] = df['Hari'] + " - Jam " + df['Jam'].astype(str) + ":00"
    
    return df

# --- Fungsi Perhitungan SAW ---
def calculate_saw(df, w_views, w_likes, w_comments):
    # 1. Agregasi Rata-rata per Alternatif
    grouped = df.groupby('Alternatif')[['Views', 'Likes', 'Comments']].mean().reset_index()
    
    # 2. Normalisasi (R)
    max_v = grouped['Views'].max()
    max_l = grouped['Likes'].max()
    max_c = grouped['Comments'].max()
    
    # Cegah pembagian dengan nol
    grouped['Norm_Views'] = grouped['Views'] / max_v if max_v > 0 else 0
    grouped['Norm_Likes'] = grouped['Likes'] / max_l if max_l > 0 else 0
    grouped['Norm_Comments'] = grouped['Comments'] / max_c if max_c > 0 else 0
    
    # 3. Hitung Perkalian Bobot (W * R)
    # Kolom ini dibuat agar bisa ditampilkan di tabel rincian (Transparansi Sistem)
    grouped['Bobot_x_Views'] = grouped['Norm_Views'] * w_views
    grouped['Bobot_x_Likes'] = grouped['Norm_Likes'] * w_likes
    grouped['Bobot_x_Comments'] = grouped['Norm_Comments'] * w_comments
    
    # 4. Hitung Nilai Preferensi (V) - Penjumlahan hasil kali
    grouped['Nilai Preferensi (V)'] = (
        grouped['Bobot_x_Views'] + 
        grouped['Bobot_x_Likes'] + 
        grouped['Bobot_x_Comments']
    )
    
    # Urutkan dari nilai tertinggi
    return grouped.sort_values(by='Nilai Preferensi (V)', ascending=False)

# ==========================================
# 2. LAYER PRESENTASI (UI STREAMLIT)
# ==========================================

# --- SIDEBAR (INPUT PARAMETER) ---
with st.sidebar:
    st.header("⚙️ Konfigurasi Sistem")
    
    # Input API Key
    api_key = st.text_input("🔑 YouTube API Key", type="password", help="Masukkan API Key dari Google Cloud Console")
    
    st.divider()
    
    # Input Bobot Kriteria
    st.subheader("⚖️ Bobot Kriteria (SAW)")
    st.info("Pastikan total bobot = 1.0 (100%)")
    
    # Slider Bobot
    w1 = st.slider("Bobot Views (C1)", 0.0, 1.0, 0.5, 0.05)
    w2 = st.slider("Bobot Likes (C2)", 0.0, 1.0, 0.3, 0.05)
    # Bobot C3 otomatis dihitung sisanya
    w3 = st.number_input("Bobot Comments (C3) - Otomatis", value=round(1.0 - (w1 + w2), 2), disabled=True)
    
    # Validasi
    if round(w1 + w2 + w3, 2) != 1.0:
        st.error("⚠️ Total bobot tidak 1.0! Harap sesuaikan.")
    
    st.divider()
    st.caption("(Islamic Paradigma AThoriq - 2026")

# --- MAIN CONTENT ---
st.title("📈 SPK Penentuan Waktu Unggah YouTube")
st.markdown("**Metode Simple Additive Weighting (SAW)**")

# Tab Navigasi
tab1, tab2, tab3, tab4 = st.tabs(["1. Pencarian Data", "2. Data Mentah", "3. Engine SAW", "4. Hasil Analisis SAW"])

# --- TAB 1: PENCARIAN ---
with tab1:
    st.header("1. Pencarian Channel")
    col_search, col_btn = st.columns([3, 1])
    
    with col_search:
        keyword = st.text_input("🔍 Masukkan Nama Channel", placeholder="Contoh: Nekonomaki")
    with col_btn:
        st.write("") 
        st.write("")
        search_clicked = st.button("Cari Channel", type="primary")

    # Logika Pencarian
    if search_clicked and api_key and keyword:
        try:
            with st.spinner("Mencari channel..."):
                results = search_channels(api_key, keyword)
                
            if not results:
                st.warning("Channel tidak ditemukan.")
            else:
                st.session_state['search_results'] = results
                st.success("Ditemukan beberapa channel:")
        
        except Exception as e:
            st.error(f"Terjadi kesalahan saat mencari: {e}")
                
    # Tampilkan Hasil dengan Profil
    if 'search_results' in st.session_state:
        results = st.session_state['search_results']
        
        # Mapping nama ke data object
        channel_map = {f"{c['title']} ({c['id']})": c for c in results}
        
        selected_label = st.radio("Silakan Pilih Channel yang Benar:", list(channel_map.keys()))
        selected_data = channel_map[selected_label]
        
        st.divider()
        st.markdown("### ✅ Detail Pilihan")
        
        # Layout 2 Kolom: Kiri Foto, Kanan Teks
        col_img, col_desc = st.columns([1, 4])
        
        with col_img:
            if selected_data['img']:
                st.image(selected_data['img'], width=120, caption="Foto Profil")
            else:
                st.write("🚫 No Image")
                
        with col_desc:
            st.markdown(f"**Nama Channel:** {selected_data['title']}")
            st.markdown(f"**Channel ID:** `{selected_data['id']}`")
            st.markdown(f"**Deskripsi:**")
            st.caption(selected_data['desc'] if selected_data['desc'] else "(Tidak ada deskripsi)")
            
            # Simpan ke Session State
            st.session_state['selected_channel_id'] = selected_data['id']
            st.session_state['selected_channel_name'] = selected_data['title']
            
            st.info("Channel terpilih. Silakan lanjut ke **Tab 2: Data Mentah**.")

# --- TAB 2: DATA MENTAH ---
with tab2:
    if 'selected_channel_id' in st.session_state:
        st.subheader(f"Data Video dari: {st.session_state['selected_channel_name']}")
        
        if st.button("📥 Ambil & Proses Data Video"):
            with st.spinner("Mengambil data dari API..."):
                try:
                    # Ambil Data
                    raw_df = get_video_stats(api_key, st.session_state['selected_channel_id'])
                    
                    # Preprocessing
                    clean_df = preprocess_data(raw_df)
                    
                    # Simpan ke Session State
                    st.session_state['data_clean'] = clean_df
                    st.success(f"Berhasil mengambil {len(clean_df)} video!")
                    
                except Exception as e:
                    st.error(f"Gagal mengambil data: {e}")
        
        # Tampilkan Tabel
        if 'data_clean' in st.session_state:
            st.dataframe(st.session_state['data_clean'], use_container_width=True)
            st.caption("Data ini sudah dikonversi ke WIB dan diekstrak Hari/Jam-nya.")
    else:
        st.warning("⚠️ Silakan pilih channel di Tab 1 terlebih dahulu.")

# --- TAB 3: ENGINE SAW ---
with tab3:
    st.header("Mesin Perhitungan (Calculation Layer)")
    
    # CEK DULU: Apakah data sudah ada?
    if 'data_clean' in st.session_state:
        # Jalankan Perhitungan SAW
        df_final = calculate_saw(st.session_state['data_clean'], w1, w2, w3)
            
        # --- 1. EXPANDER NORMALISASI (R) ---
        with st.expander("🧮 Lihat Langkah 1: Matriks Normalisasi (R)", expanded=True):
            st.write("Rumus: $R_{ij} = x_{ij} / max(x_{ij})$")
            st.dataframe(df_final[['Alternatif', 'Norm_Views', 'Norm_Likes', 'Norm_Comments']])
                
        # --- 2. EXPANDER PERKALIAN BOBOT (W x R) ---
        with st.expander("🧮 Lihat Langkah 2: Perkalian Bobot (W x R)", expanded=True):
            st.write("Sesuai rumus: $V_i = \sum w_j \\times r_{ij}$")
                
            # Buat view khusus
            detail_view = df_final[['Alternatif', 'Bobot_x_Views', 'Bobot_x_Likes', 'Bobot_x_Comments', 'Nilai Preferensi (V)']]
            # Rename kolom agar dosen paham
            detail_view.columns = [
                'Alternatif', 
                f'C1 (Views) x {w1}', 
                f'C2 (Likes) x {w2}', 
                f'C3 (Komen) x {w3}', 
                'Total Nilai (V)'
            ]
            # Menerapkan fix subset formatting agar tidak error
            st.dataframe(detail_view.style.format("{:.4f}", subset=detail_view.columns[1:]))
            st.caption("Kolom Total Nilai (V) adalah hasil penjumlahan ketiga kolom bobot di sampingnya.")
    
    else:
        st.warning("⚠️ Data belum tersedia. Silakan ambil data di **Tab 2** terlebih dahulu.")

# --- TAB 4: HASIL ANALISIS SAW ---
with tab4:
    st.header("Hasil Keputusan (Presentation Layer)")
    
    # CEK LAGI: Apakah data sudah ada?
    if 'data_clean' in st.session_state:
        # Kita hitung ulang df_final agar variabelnya tersedia di blok ini
        df_final = calculate_saw(st.session_state['data_clean'], w1, w2, w3)
        
        st.subheader("🏆 Perankingan Waktu Unggah Terbaik")

        # --- HASIL AKHIR ---
        # Ambil Top 1
        best_time = df_final.iloc[0]['Alternatif']
        best_score = df_final.iloc[0]['Nilai Preferensi (V)']
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Waktu Terbaik", best_time)
        col_m2.metric("Skor SAW Tertinggi", f"{best_score:.4f}")
        col_m3.metric("Total Alternatif", f"{len(df_final)} Slot Waktu")
        
        st.divider()
        
        # Tabel & Grafik
        col_res1, col_res2 = st.columns([1, 1])
        
        with col_res1:
            st.markdown("##### Tabel Peringkat (Top 10)")
            display_df = df_final[['Alternatif', 'Views', 'Likes', 'Comments', 'Nilai Preferensi (V)']].head(10)
            st.dataframe(display_df.style.background_gradient(subset=['Nilai Preferensi (V)'], cmap='Greens'), use_container_width=True)
            
        with col_res2:
            st.markdown("##### Visualisasi Skor Preferensi")
            fig = px.bar(
                df_final.head(10).sort_values(by='Nilai Preferensi (V)', ascending=True),
                x='Nilai Preferensi (V)',
                y='Alternatif',
                orientation='h',
                title='Grafik Perbandingan Alternatif Terbaik',
                color='Nilai Preferensi (V)',
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig, use_container_width=True)
            
    else:
        st.warning("⚠️ Data belum tersedia. Silakan ambil data di **Tab 2** terlebih dahulu.")