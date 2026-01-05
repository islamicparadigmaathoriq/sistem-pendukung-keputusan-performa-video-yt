import streamlit as st
from data_layer import DataManager
from model_layer import SAWModel
from ui_layer import UserInterface

#===============================================
#Konfigurasi Aplikasi
#===============================================
st.set_page_config(page_title="SPK Evaluasi Konten YouTube", layout="wide", page_icon="🎥")
#===============================================
#Inisialisasi Komponen
#===============================================
def main():
    ui = UserInterface()
    
    st.title("🎥 SPK Evaluasi Performa Konten YouTube (Metode SAW)")
    st.markdown("Sistem Pendukung Keputusan berbasis Web untuk Konten Kreator")
    
    if 'dm' not in st.session_state:
        st.session_state['dm'] = DataManager(None)
    
    dm = st.session_state['dm']
#===============================================
#2. RENDER SIDEBAR (Sekarang return list kompetitor otomatis)
#===============================================
    api_key, channel_id, competitors, weights = ui.render_sidebar(dm)
    
    if st.sidebar.button("🚀 Analisis Channel", type="primary"):
        if not api_key:
            st.error("⚠️ Mohon masukkan YouTube API Key di Sidebar.")
            return
        if not channel_id:
            st.error("⚠️ Mohon Cari dan Pilih Channel Utama terlebih dahulu.")
            return
#===============================================
#A. CHANNEL UTAMA
#===============================================
        with st.spinner("Mengambil data Channel Utama..."):
            main_info = dm.get_channel_info(channel_id)
            if not main_info:
                st.error("Gagal mengambil data channel utama.")
                return
            
            uploads_id = main_info['contentDetails']['relatedPlaylists']['uploads']
            df_videos = dm.fetch_videos(uploads_id)

        if df_videos.empty:
            st.warning("Tidak ada video publik ditemukan pada channel ini.")
            return
#===============================================
#B. KOMPETITOR (OTOMATIS DARI UI)
#===============================================
        comp_data_list = []
        if any(competitors):
            with st.status("Sedang menganalisis kompetitor terpilih...", expanded=True):
                for i, comp_id in enumerate(competitors):
                    if comp_id: 
                        st.write(f"Mengambil data Kompetitor {i+1}...")
                        c_info = dm.get_channel_info(comp_id)
                        if c_info:
                            c_up_id = c_info['contentDetails']['relatedPlaylists']['uploads']
                            c_df = dm.fetch_videos(c_up_id)
                            if not c_df.empty:
                                c_df['engagement_rate'] = ((c_df['like_count'] + c_df['comment_count']) / c_df['view_count'] * 100).fillna(0)
                                comp_data_list.append((c_info, c_df))
                        else:
                            st.warning(f"Gagal mengambil data kompetitor ID: {comp_id}")
#===============================================
#C. PROSES SAW
#===============================================
        model = SAWModel(weights)
        df_processed = model.calculate_engagement_rate(df_videos)
        df_normalized = model.normalize_data(df_processed)
        df_final = model.calculate_preference(df_normalized)
        df_final['Rank'] = df_final.index + 1
#===============================================
# D. OUTPUT
#===============================================
        ui.render_overview(main_info, df_final)
        if comp_data_list:
            ui.render_comparison(main_info, df_processed, comp_data_list)
        ui.render_ranking_table(df_final)
        ui.render_analytics(df_final)

if __name__ == "__main__":
    main()

