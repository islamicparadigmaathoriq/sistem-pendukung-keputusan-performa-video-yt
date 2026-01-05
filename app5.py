import streamlit as st
from data_layer import DataManager
from model_layer import SAWModel
from ui_layer import UserInterface

#===============================================
# KONFIGURASI HALAMAN (Wajib Paling Atas)
#===============================================
st.set_page_config(page_title="SPK Evaluasi Konten YouTube", layout="wide", page_icon="🎥")

def main():
    #===============================================
    # INISIALISASI KOMPONEN
    #===============================================
    ui = UserInterface()
    
    st.title("🎥 SPK Evaluasi Performa Konten YouTube (Metode SAW)")
    st.markdown("Sistem Pendukung Keputusan berbasis Web untuk Konten Kreator")
    
    # Inisialisasi Data Manager di Session State
    if 'dm' not in st.session_state:
        st.session_state['dm'] = DataManager(None)
    
    dm = st.session_state['dm']
    
    #===============================================
    # RENDER SIDEBAR
    #===============================================
    api_key, channel_id, competitors, weights = ui.render_sidebar(dm)
    
    #===============================================
    # EKSEKUSI UTAMA (SAAT TOMBOL DIKLIK)
    #===============================================
    if st.sidebar.button("🚀 Analisis Channel", type="primary"):
        # 1. Validasi Input
        if not api_key:
            st.error("⚠️ Mohon masukkan YouTube API Key di Sidebar.")
            return
        if not channel_id:
            st.error("⚠️ Mohon Cari dan Pilih Channel Utama terlebih dahulu.")
            return

        # 2. AMBIL DATA CHANNEL UTAMA
        with st.spinner("Mengambil data Channel Utama..."):
            main_info = dm.get_channel_info(channel_id)
            if not main_info:
                st.error("Gagal mengambil data channel utama. Periksa API Key atau Koneksi.")
                return 
                
            uploads_id = main_info['contentDetails']['relatedPlaylists']['uploads']
            df_videos = dm.fetch_videos(uploads_id)

        if df_videos.empty:
            st.warning("Tidak ada video publik ditemukan pada channel ini.")
            return

        # 3. AMBIL DATA KOMPETITOR
        comp_data_list = []
        if any(competitors):
            with st.status("Sedang menganalisis kompetitor...", expanded=True):
                for i, comp_id in enumerate(competitors):
                    if comp_id: 
                        st.write(f"Mengambil data Kompetitor {i+1}...")
                        c_info = dm.get_channel_info(comp_id)
                        if c_info:
                            c_up_id = c_info['contentDetails']['relatedPlaylists']['uploads']
                            c_df = dm.fetch_videos(c_up_id)
                            if not c_df.empty:
                                # Hitung ER manual untuk kompetitor
                                c_df['engagement_rate'] = ((c_df['like_count'] + c_df['comment_count']) / c_df['view_count'] * 100).fillna(0)
                                comp_data_list.append((c_info, c_df))
                        else:
                            st.warning(f"Gagal mengambil data kompetitor ID: {comp_id}")

        # 4. PROSES SAW (HITUNG SKOR)
        # Menghitung ER untuk Channel Utama
        model = SAWModel(weights)
        df_processed = model.calculate_engagement_rate(df_videos)
        
        # Normalisasi & Preferensi
        df_normalized = model.normalize_data(df_processed)
        df_final = model.calculate_preference(df_normalized)
        df_final['Rank'] = df_final.index + 1

        # 5. RENDER OUTPUT (TAMPILKAN HASIL)
        # A. Overview Statistik
        ui.render_overview(main_info, df_final)
        
        # B. Analisis Strategi & Positioning (Fitur Baru)
        if 'main_category' in st.session_state:
            comp_cats = st.session_state.get('competitor_categories', [])
            # Selalu tampilkan analisis meskipun tidak ada kompetitor (untuk melihat benchmark diri sendiri)
            ui.render_category_comparison(
                st.session_state['main_category'], 
                comp_cats
            )
        
        # C. Grafik Perbandingan (Jika ada kompetitor)
        if comp_data_list:
            ui.render_comparison(main_info, df_processed, comp_data_list)
        
        # D. Tabel Peringkat & Analisis Detail
        ui.render_ranking_table(df_final)
        ui.render_analytics(df_final)

if __name__ == "__main__":
    main()
