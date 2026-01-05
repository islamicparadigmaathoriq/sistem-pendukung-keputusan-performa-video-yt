import streamlit as st
import plotly.express as px
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import re

class UserInterface:
    def __init__(self):
        # CSS CUSTOM UNTUK TAMPILAN
        st.markdown("""
        <style>
        /* Kotak Metric Rounded */
        div[data-testid="stMetric"] {
            background-color: #f8f9fa;
            border: 1px solid #e0e0e0;
            padding: 15px;
            border-radius: 15px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        }
        /* Custom Card untuk Video Terbaik (Judul Panjang) */
        .video-card {
            background-color: #f8f9fa;
            border: 1px solid #e0e0e0;
            padding: 15px;
            border-radius: 15px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
            height: 100%;
        }
        .video-label {
            font-size: 14px; color: #6c757d; margin-bottom: 5px;
        }
        .video-title {
            font-size: 16px; font-weight: bold; color: #000;
            line-height: 1.4; /* Jarak antar baris */
            word-wrap: break-word; /* Wrap teks panjang */
        }
        </style>
        """, unsafe_allow_html=True)

    def _render_competitor_selector(self, index, data_manager):
        """Helper untuk search kompetitor"""
        st.markdown(f"**Kompetitor {index}**")
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input(f"Cari Komp {index}", key=f"q_comp_{index}", 
                                  placeholder="Nama Channel...", label_visibility="collapsed")
        with col2:
            is_search = st.button("🔍", key=f"btn_comp_{index}")

        if is_search and query:
            with st.spinner(f"Mencari..."):
                results = data_manager.search_channels(query)
                st.session_state[f'res_comp_{index}'] = results
        
        selected_id = ""
        if f'res_comp_{index}' in st.session_state:
            results = st.session_state[f'res_comp_{index}']
            if results:
                options = [f"{r['title']}" for r in results]
                choice = st.selectbox(f"Pilih Hasil K-{index}", options, key=f"sel_comp_{index}", label_visibility="collapsed")
                idx = options.index(choice)
                target = results[idx]
                selected_id = target['channel_id']
                
                c_img, c_txt = st.columns([1, 3])
                with c_img: st.image(target['thumbnail'], width=40)
                with c_txt: st.caption(f"ID: `{selected_id}`")
            else:
                st.warning("Tidak ditemukan.")
        return selected_id

    def render_sidebar(self, data_manager):
        st.sidebar.header("⚙️ Konfigurasi Sistem")
        with st.sidebar.expander("ℹ️ Cara dapatkan API Key?"):
            st.caption("""
            1. Buka [Google Cloud Console](https://console.cloud.google.com/).
            2. Buat **Project Baru**.
            3. Cari **"YouTube Data API v3"** lalu klik **Enable**.
            4. Masuk ke menu **Credentials** -> **Create Credentials** -> **API Key**.
            5. Copy API Key tersebut dan tempel di bawah ini.
            """)
        api_key = st.sidebar.text_input("1. Masukkan YouTube API Key", type="password")
        if api_key:
            data_manager.update_key(api_key)
        
        st.sidebar.divider()

        # Channel Utama
        st.sidebar.markdown("### 2. Channel Utama")
        query = st.sidebar.text_input("Cari Channel Utama", placeholder="Contoh: GadgetIn")
        if st.sidebar.button("🔍 Cari Utama"):
            if api_key and query:
                with st.spinner("Mencari..."):
                    results = data_manager.search_channels(query)
                    st.session_state['search_results_main'] = results
            else:
                st.sidebar.warning("Isi API Key & Nama Channel.")

        selected_channel_id = None
        if 'search_results_main' in st.session_state and st.session_state['search_results_main']:
            results = st.session_state['search_results_main']
            options = [f"{r['title']}" for r in results]
            choice = st.sidebar.selectbox("Pilih Hasil:", options, key="main_select")
            idx = options.index(choice)
            target = results[idx]
            selected_channel_id = target['channel_id']
            
            col_img, col_info = st.sidebar.columns([1, 3])
            with col_img:
                if target['thumbnail']: st.image(target['thumbnail'], width=50)
            with col_info: st.caption(f"**{target['title']}**")

        st.sidebar.divider()

        # Kompetitor
        st.sidebar.markdown("### 3. Komparasi (Opsional)")
        comp1_id = self._render_competitor_selector(1, data_manager)
        comp2_id = self._render_competitor_selector(2, data_manager)
        
        st.sidebar.divider()
        
        # Bobot
        st.sidebar.header("⚖️ Bobot SAW")
        w_views = st.sidebar.slider("Views (C1)", 0.0, 1.0, 0.30)
        w_likes = st.sidebar.slider("Likes (C2)", 0.0, 1.0, 0.25)
        w_comments = st.sidebar.slider("Comments (C3)", 0.0, 1.0, 0.20)
        w_er = st.sidebar.slider("Engagement Rate (C4)", 0.0, 1.0, 0.25)
        
        total = w_views + w_likes + w_comments + w_er
        if round(total, 2) != 1.0:
            st.sidebar.error(f"⚠️ Total: {total:.2f} (Wajib 1.0)")
        else:
            st.sidebar.success("✅ Bobot Valid")
        
        # --- FITUR BARU: MONITOR KUOTA API ---
        st.sidebar.divider()
        st.sidebar.markdown("### 📊 Monitor Kuota API")
        used = data_manager.used_quota
        limit_daily = 10000 # Batas gratis harian standar
        
        st.sidebar.caption(f"Estimasi Penggunaan Sesi Ini: **{used}** units")
        st.sidebar.progress(min(used / limit_daily, 1.0))
        st.sidebar.caption("*Catatan: Ini estimasi sesi.*")
        # -------------------------------------

        return api_key, selected_channel_id, [comp1_id, comp2_id], {'views': w_views, 'likes': w_likes, 'comments': w_comments, 'er': w_er}

    def render_overview(self, channel_info, df):
        st.markdown("### 📊 Overview Channel")
        niche = channel_info.get('niche_detected', 'Umum')
        
        color = "#0077b6" 
        if "Jepang" in niche: color = "#d62828"
        if "Korea" in niche: color = "#9b2226"
        if "Indonesia" in niche: color = "#2a9d8f"
        
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
        with c1:
            st.plotly_chart(px.bar(df_comp, x="Nama Channel", y="Avg Views", color="Status", title="Perbandingan Views"), use_container_width=True)
        with c2:
            st.plotly_chart(px.bar(df_comp, x="Nama Channel", y="Avg ER (%)", color="Status", title="Perbandingan Engagement"), use_container_width=True)
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
        
        # Download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            temp = df_disp.copy()
            if 'published_at' in temp.columns: temp['published_at'] = temp['published_at'].dt.tz_localize(None)
            temp.to_excel(writer, index=False)
        st.download_button("💾 Download Excel", output.getvalue(), "saw_result.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def render_analytics(self, df):
        st.markdown("### 📈 Dashboard Analitik & Strategi")
        
        best = df.iloc[0]
        # Cari Insight Utama
        best_day = df.groupby('day_name')['view_count'].mean().idxmax()
        
        # --- FITUR BARU: CUSTOM HTML CARD UNTUK JUDUL ---
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f"""
            <div class="video-card">
                <div class="video-label">Video Terbaik</div>
                <div class="video-title">{best['title']}</div>
            </div>
            """, unsafe_allow_html=True)
        m2.metric("Skor SAW Tertinggi", f"{best['preference_score']:.4f}")
        m3.metric("Views Video Terbaik", f"{best['view_count']:,}")
        st.divider()

        t1, t2, t3, t4, t5 = st.tabs(["Peta Strategi", "Top 5", "Korelasi", "Word Cloud", "Statistik"])
        
        # --- [PERBAIKAN 3: SORTING HARI INDONESIA] ---
        days_indo = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
        # ---------------------------------------------

        with t1:
            st.markdown("#### Analisis Waktu Upload")
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("**1. Tren Harian**")
                # Reindex menggunakan nama hari Indonesia
                df_hari = df.groupby('day_name')['view_count'].mean().reindex(days_indo).reset_index()
                st.plotly_chart(px.line(df_hari, x='day_name', y='view_count', markers=True, title="Tren Harian"), use_container_width=True)
            with c2:
                st.markdown("**2. Heatmap Zona Waktu**")
                # Reindex heatmap juga
                hmap = df.pivot_table(index='day_name', columns='hour', values='view_count', aggfunc='mean').fillna(0).reindex(days_indo)
                st.plotly_chart(px.imshow(hmap, labels=dict(x="Jam", y="Hari"), color_continuous_scale='RdYlGn', title="Heatmap"), use_container_width=True)

            # AUTOMATIC INSIGHT TEKS
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
            
            if corr > 0.5:
                msg = "Terdapat **korelasi positif kuat**. Video dengan views tinggi cenderung memiliki interaksi (ER) yang tinggi juga."
            elif corr < -0.5:
                msg = "Terdapat **korelasi negatif**. Video views tinggi justru memiliki persentase interaksi rendah (mungkin viral tapi pasif)."
            else:
                msg = "Korelasi lemah/acak. Tidak ada hubungan pasti antara jumlah views dengan tingkat keaktifan penonton."
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
            
            avg_er = desc.loc['mean', 'engagement_rate']
            std_views = desc.loc['std', 'view_count']
            
            st.info(f"""
            💡 **Ringkasan:**
            - Rata-rata Engagement Rate channel ini adalah **{avg_er:.2f}%**.
            - Standar deviasi views sebesar **{std_views:,.0f}**, menunjukkan {'variasi performa video sangat tinggi (tidak stabil)' if std_views > desc.loc['mean','view_count'] else 'performa video cukup konsisten'}.
            """)
