import streamlit as st
import plotly.express as px
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import re

class UserInterface:
    def __init__(self):
        st.markdown("""
        <style>
        div[data-testid="stMetric"] { background-color: #f8f9fa; border: 1px solid #e0e0e0; padding: 15px; border-radius: 15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
        .video-card { background-color: #f8f9fa; border: 1px solid #e0e0e0; padding: 15px; border-radius: 15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); height: 100%; }
        .video-title { font-size: 16px; font-weight: bold; color: #000; line-height: 1.4; word-wrap: break-word; }
        </style>
        """, unsafe_allow_html=True)

    def render_sidebar(self, data_manager):
        st.sidebar.header("⚙️ Konfigurasi Sistem")
        
        # 1. API KEY
        api_key = st.sidebar.text_input("1. Masukkan YouTube API Key", type="password")
        st.sidebar.info("""
        ℹ️ **Belum punya API Key?**
        1. Buka [Google Cloud Console](https://console.cloud.google.com/).
        2. Buat **Project Baru** → Cari **"YouTube Data API v3"** → Enable.
        3. Menu **Credentials** → **Create Credentials** → **API Key**.
        """)
        
        if api_key: data_manager.update_key(api_key)
        st.sidebar.divider()

        # 2. CHANNEL UTAMA
        st.sidebar.markdown("### 2. Channel Utama")
        query = st.sidebar.text_input("Cari Channel Utama", placeholder="Contoh: GadgetIn")
        
        if st.sidebar.button("🔍 Cari Utama"):
            if api_key and query:
                with st.spinner("Mencari..."):
                    st.session_state['res_main'] = data_manager.search_channels(query)
            else:
                st.sidebar.warning("Isi API Key & Nama Channel.")

        selected_channel_id = None
        main_niche = None
        
        if 'res_main' in st.session_state and st.session_state['res_main']:
            options = [f"{r['title']}" for r in st.session_state['res_main']]
            choice = st.sidebar.selectbox("Pilih Hasil:", options, key="main_select")
            idx = options.index(choice)
            target = st.session_state['res_main'][idx]
            selected_channel_id = target['channel_id']
            
            c1, c2 = st.sidebar.columns([1, 3])
            with c1: st.image(target['thumbnail'], width=50)
            with c2: st.caption(f"**{target['title']}**")
            
            # --- DETEKSI NICHE OTOMATIS UTK REKOMENDASI ---
            if api_key:
                with st.spinner("Mendeteksi Niche..."):
                    # Kita panggil get_info sebentar untuk tau nichenya
                    info = data_manager.get_channel_info(selected_channel_id)
                    if info:
                        main_niche = info.get('niche_detected', 'Umum')
                        st.sidebar.success(f"🏷️ Niche Terdeteksi: **{main_niche}**")
                        st.session_state['detected_niche'] = main_niche

        st.sidebar.divider()

        # 3. KOMPETITOR OTOMATIS
        st.sidebar.markdown("### 3. Pilih Kompetitor")
        selected_competitors = []
        
        if selected_channel_id and 'detected_niche' in st.session_state:
            niche = st.session_state['detected_niche']
            
            # Tombol Cari Kompetitor
            if st.sidebar.button(f"🔍 Cari 5 Kompetitor ({niche})"):
                with st.spinner("Mencari kompetitor sejenis..."):
                    comps = data_manager.search_competitors_by_niche(niche, selected_channel_id)
                    st.session_state['competitor_candidates'] = comps
            
            # Tampilkan Pilihan jika sudah ada kandidat
            if 'competitor_candidates' in st.session_state and st.session_state['competitor_candidates']:
                candidates = st.session_state['competitor_candidates']
                cand_names = [c['title'] for c in candidates]
                
                st.sidebar.caption("Pilih maksimal 2 kompetitor:")
                selected_names = st.sidebar.multiselect(
                    "Kandidat:", 
                    options=cand_names,
                    max_selections=2,
                    label_visibility="collapsed"
                )
                
                # Ambil ID dari nama yang dipilih
                for name in selected_names:
                    for cand in candidates:
                        if cand['title'] == name:
                            selected_competitors.append(cand['channel_id'])
                            break
            else:
                st.sidebar.caption("Klik tombol cari untuk melihat rekomendasi.")
        else:
            st.sidebar.caption("Pilih Channel Utama dulu.")

        st.sidebar.divider()
        
        # 4. BOBOT
        st.sidebar.header("⚖️ Bobot SAW")
        w_v = st.sidebar.slider("Views (C1)", 0.0, 1.0, 0.30)
        w_l = st.sidebar.slider("Likes (C2)", 0.0, 1.0, 0.25)
        w_c = st.sidebar.slider("Comments (C3)", 0.0, 1.0, 0.20)
        w_e = st.sidebar.slider("Engagement Rate (C4)", 0.0, 1.0, 0.25)
        
        if round(w_v+w_l+w_c+w_e, 2) != 1.0: st.sidebar.error("⚠️ Total Bobot harus 1.0")
        else: st.sidebar.success("✅ Bobot Valid")
        
        st.sidebar.divider()
        st.sidebar.caption(f"Estimasi Kuota: **{data_manager.used_quota}** units")
        st.sidebar.progress(min(data_manager.used_quota/10000, 1.0))

        return api_key, selected_channel_id, selected_competitors, {'views': w_v, 'likes': w_l, 'comments': w_c, 'er': w_e}

    def render_overview(self, channel_info, df):
        st.markdown("### 📊 Overview Channel")
        niche = channel_info.get('niche_detected', 'Umum')
        color = "#0077b6" 
        if "Jepang" in niche: color = "#d62828"
        elif "Korea" in niche: color = "#9b2226"
        elif "Indonesia" in niche: color = "#2a9d8f"
        
        st.markdown(f"**Kategori/Niche:** <span style='background-color:{color}20; padding:5px 10px; border-radius:10px; color:{color}; font-weight:bold; border: 1px solid {color}'>🏷️ {niche}</span>", unsafe_allow_html=True)
        
        stats = channel_info['statistics']
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Subscribers", f"{int(stats['subscriberCount']):,}")
        c2.metric("Total Video", f"{int(stats['videoCount']):,}")
        c3.metric("Rata-rata Views", f"{df['view_count'].mean():,.0f}")
        c4.metric("Rata-rata ER", f"{df['engagement_rate'].mean():.2f}%")
        st.divider()

    def render_comparison(self, main_info, main_df, comp_data_list):
        if not comp_data_list: return
        st.markdown("### ⚔️ Analisis Komparasi")
        
        comp_summary = [{
            "Nama Channel": main_info['snippet']['title'],
            "Avg Views": main_df['view_count'].mean(),
            "Avg ER (%)": main_df['engagement_rate'].mean(),
            "Subs": int(main_info['statistics']['subscriberCount']),
            "Status": "Utama"
        }]

        for c_info, c_df in comp_data_list:
            comp_summary.append({
                "Nama Channel": c_info['snippet']['title'],
                "Avg Views": c_df['view_count'].mean(),
                "Avg ER (%)": c_df['engagement_rate'].mean(),
                "Subs": int(c_info['statistics']['subscriberCount']),
                "Status": "Kompetitor"
            })
        
        df_comp = pd.DataFrame(comp_summary)
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.bar(df_comp, x="Nama Channel", y="Avg Views", color="Status", title="Perbandingan Views"), use_container_width=True)
        with c2: st.plotly_chart(px.bar(df_comp, x="Nama Channel", y="Avg ER (%)", color="Status", title="Perbandingan Engagement"), use_container_width=True)
        st.divider()

    def render_ranking_table(self, df_result):
        st.markdown("### 🏆 Hasil Pemeringkatan (SAW)")
        with st.expander("🔍 Filter Data"):
            c1, c2 = st.columns(2)
            if 'published_at' in df_result.columns:
                df_result['year'] = df_result['published_at'].dt.year
                years = sorted(df_result['year'].unique(), reverse=True)
                sel_year = c1.selectbox("Tahun:", ["Semua"] + list(years))
            else: sel_year = "Semua"
            min_v = int(df_result['view_count'].min())
            max_v = int(df_result['view_count'].max())
            sel_min_v = c2.slider("Min Views:", min_v, max_v, min_v)

        df_disp = df_result.copy()
        if sel_year != "Semua": df_disp = df_disp[df_disp['year'] == sel_year]
        df_disp = df_disp[df_disp['view_count'] >= sel_min_v]

        st.caption(f"Menampilkan **{len(df_disp)}** video.")
        with st.expander("🧮 Detail Perhitungan (Normalisasi)"):
            norm_cols = ['title', 'norm_views', 'norm_likes', 'norm_comments', 'norm_er']
            if all(c in df_disp.columns for c in norm_cols):
                df_n = df_disp[norm_cols].copy()
                df_n.columns = ['Judul', 'R1 (Views)', 'R2 (Likes)', 'R3 (Komen)', 'R4 (ER)']
                st.dataframe(df_n.style.format("{:.4f}", subset=df_n.columns[1:]))

        cols = ['title', 'published_at', 'view_count', 'like_count', 'comment_count', 'engagement_rate', 'preference_score', 'Rank']
        df_show = df_disp[cols].copy()
        df_show.columns = ['Judul', 'Waktu (WIB)', 'Views', 'Likes', 'Komen', 'ER (%)', 'Skor V', 'Rank']
        st.dataframe(df_show.style.highlight_max(axis=0, subset=['Skor V'], color='#90ee90'))
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            temp = df_disp.copy()
            if 'published_at' in temp.columns: temp['published_at'] = temp['published_at'].dt.tz_localize(None)
            temp.to_excel(writer, index=False)
        st.download_button("💾 Download Excel", output.getvalue(), "saw_result.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def render_analytics(self, df):
        st.markdown("### 📈 Dashboard Analitik & Strategi")
        best = df.iloc[0]
        best_day = df.groupby('day_name')['view_count'].mean().idxmax()
        
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f"""
            <div class="video-card">
                <div class="video-label">Video Terbaik</div>
                <div class="video-title">{best['title']}</div>
            </div>""", unsafe_allow_html=True)
        m2.metric("Skor SAW Tertinggi", f"{best['preference_score']:.4f}")
        m3.metric("Views Video Terbaik", f"{best['view_count']:,}")
        st.divider()

        t1, t2, t3, t4, t5 = st.tabs(["Peta Strategi", "Top 5", "Korelasi", "Word Cloud", "Statistik"])
        days_indo = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
        
        with t1:
            st.markdown("#### Analisis Waktu Upload")
            c1, c2 = st.columns(2)
            with c1:
                df_hari = df.groupby('day_name')['view_count'].mean().reindex(days_indo).reset_index()
                st.plotly_chart(px.line(df_hari, x='day_name', y='view_count', markers=True, title="Tren Harian"), use_container_width=True)
            with c2:
                hmap = df.pivot_table(index='day_name', columns='hour', values='view_count', aggfunc='mean').fillna(0).reindex(days_indo)
                st.plotly_chart(px.imshow(hmap, labels=dict(x="Jam", y="Hari"), color_continuous_scale='RdYlGn', title="Heatmap"), use_container_width=True)
            
            best_hour = df.groupby('hour')['view_count'].mean().idxmax()
            st.info(f"""
            💡 **Insight Otomatis:**
            Berdasarkan data historis, hari **{best_day}** memiliki rata-rata views tertinggi.
            Secara spesifik, jam **{best_hour}:00 WIB** adalah waktu yang paling potensial menarik penonton (Heatmap Hijau).
            """)

        with t2:
            st.plotly_chart(px.bar(df.head(5), x='preference_score', y='title', orientation='h', title="Top 5 Video SAW"), use_container_width=True)
            
        with t3:
            corr = df['view_count'].corr(df['engagement_rate'])
            st.plotly_chart(px.scatter(df, x='view_count', y='engagement_rate', size='preference_score', title=f"Korelasi: {corr:.2f}"), use_container_width=True)
            if corr > 0.5: msg = "Terdapat **korelasi positif kuat**."
            elif corr < -0.5: msg = "Terdapat **korelasi negatif**."
            else: msg = "Korelasi lemah/acak."
            st.info(f"💡 **Analisis Statistik:** {msg}")

        with t4:
            txt = " ".join(df.head(30)['title'].tolist())
            clean = " ".join(re.findall(r"[a-zA-Z0-9]+", txt))
            if clean:
                wc = WordCloud(width=800, height=400, background_color='white').generate(clean)
                fig, ax = plt.subplots()
                ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
                st.pyplot(fig)
            else: st.warning("Data teks kurang.")

        with t5:
            desc = df[['view_count', 'like_count', 'engagement_rate']].describe()
            st.dataframe(desc.style.format("{:.2f}"))
