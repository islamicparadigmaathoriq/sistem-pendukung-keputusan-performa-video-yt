import pandas as pd
from googleapiclient.discovery import build
import datetime

class DataManager:
    #==========================================================
    # Fungsi Inisialisasi & Setup
    #==========================================================
    def __init__(self, api_key):
        self.api_key = api_key
        self.youtube = None
        self.used_quota = 0 
        
        if self.api_key:
            try:
                self.youtube = build('youtube', 'v3', developerKey=api_key)
            except:
                pass

    def update_key(self, new_api_key):
        self.api_key = new_api_key
        try:
            self.youtube = build('youtube', 'v3', developerKey=new_api_key)
        except:
            pass

    #==========================================================
    # Fungsi Pencarian Channel
    #==========================================================
    def search_channels(self, query, limit=5):
        """Mencari channel berdasarkan nama"""
        if not self.youtube: return []
        try:
            self.used_quota += 100 
            request = self.youtube.search().list(
                part="snippet", q=query, type="channel", maxResults=limit
            )
            response = request.execute()
            results = []
            for item in response['items']:
                thumb = item['snippet']['thumbnails'].get('high', {}).get('url') or "https://via.placeholder.com/150"
                results.append({
                    'channel_id': item['snippet']['channelId'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'thumbnail': thumb, 
                    'publish_time': item['snippet']['publishedAt']
                })
            return results
        except:
            return []

    #==========================================================
    # DETEKSI NICHE
    #==========================================================
    def _detect_niche(self, channel_item):
        """Deteksi Niche + Geografi"""
        topics = channel_item.get('topicDetails', {}).get('topicCategories', [])
        text = (channel_item['snippet']['title'] + " " + channel_item['snippet']['description']).lower()
        
        base_niche = "Umum"
        geo_tag = ""

        # 1. Geografi
        if any(x in text for x in ['j-pop', 'jpop', 'japanese', 'japan', 'anime']): geo_tag = "(Jepang)"
        elif any(x in text for x in ['k-pop', 'kpop', 'korea', 'drakor']): geo_tag = "(Korea)"
        elif any(x in text for x in ['indonesia', 'indo', 'jakarta']): geo_tag = "(Indonesia)"

        # 2. Topik
        niche_map = {
            'Technology': 'Teknologi', 'Gaming': 'Gaming',
            'Lifestyle': 'Vlog & Lifestyle', 'Entertainment': 'Hiburan',
            'Music': 'Musik', 'Sport': 'Olahraga', 'Food': 'Kuliner'
        }
        
        found = False
        for url in topics:
            for key, label in niche_map.items():
                if key in url: 
                    base_niche = label; found = True; break
            if found: break
        
        if not found:
            if any(x in text for x in ['game', 'play', 'esport']): base_niche = "Gaming"
            elif any(x in text for x in ['gadget', 'review', 'tech']): base_niche = "Teknologi"
            elif any(x in text for x in ['song', 'music', 'cover']): base_niche = "Musik"
            elif any(x in text for x in ['vlog', 'daily', 'travel']): base_niche = "Vlog & Lifestyle"
            elif any(x in text for x in ['resep', 'masak', 'kuliner', 'food']): base_niche = "Kuliner"

        return f"{base_niche} {geo_tag}".strip()

    def get_channel_info(self, channel_id):
        if not self.youtube: return None
        try:
            self.used_quota += 1
            request = self.youtube.channels().list(
                part="snippet,contentDetails,statistics,topicDetails",
                id=channel_id
            )
            response = request.execute()
            if response['items']:
                item = response['items'][0]
                item['niche_detected'] = self._detect_niche(item)
                return item
            return None
        except:
            return None
            
    #==========================================================
    # CARI KOMPETITOR BERDASARKAN NICHE
    #==========================================================
    def search_competitors_by_niche(self, niche_keyword, exclude_channel_id, limit=5):
        """Mencari 5 channel lain berdasarkan niche/topik"""
        if not self.youtube: return []
        
        # Bersihkan keyword (misal: "Gaming (Indonesia)" -> "Gaming Indonesia")
        clean_query = niche_keyword.replace("(", "").replace(")", "")
        
        try:
            self.used_quota += 100
            request = self.youtube.search().list(
                part="snippet",
                q=clean_query, # Cari berdasarkan topik
                type="channel",
                order="viewCount", # Cari yang populer
                maxResults=limit + 1 # Ambil lebih 1 untuk jaga-jaga kalau ada channel utama
            )
            response = request.execute()
            
            results = []
            for item in response['items']:
                cid = item['snippet']['channelId']
                # Jangan masukkan channel utama ke daftar kompetitor
                if cid != exclude_channel_id:
                    thumb = item['snippet']['thumbnails'].get('default', {}).get('url')
                    results.append({
                        'channel_id': cid,
                        'title': item['snippet']['title'],
                        'thumbnail': thumb
                    })
            return results[:limit] # Kembalikan maksimal 5
        except:
            return []

    #==========================================================
    # KATEGORISASI CHANNEL
    #==========================================================
    def categorize_channel(self, channel_info):
        """
        Kategorikan channel berdasarkan subscribers dan performa
        Returns: dict dengan kategori, level, dan benchmark
        """
        stats = channel_info.get('statistics', {})
        subs = int(stats.get('subscriberCount', 0))
        total_videos = int(stats.get('videoCount', 0))
        total_views = int(stats.get('viewCount', 0))
        
        # Hitung average views per video
        avg_views = total_views / total_videos if total_videos > 0 else 0
        
        # Kriteria Kategorisasi
        if subs < 10000:
            category = "🌱 Pemula (Beginner)"
            level = "pemula"
            color = "#6c757d"  # Abu-abu
            benchmark = {
                'subs_target': '10K subscribers',
                'focus': 'Konsistensi upload, niche yang jelas, SEO dasar',
                'challenge': 'Membangun audience awal, menemukan gaya konten',
                'strategy': 'Upload rutin (2-3x/minggu), riset keyword, kolaborasi micro-influencer'
            }
        elif subs < 100000:
            category = "🚀 Menengah (Intermediate)"
            level = "menengah"
            color = "#0dcaf0"  # Cyan
            benchmark = {
                'subs_target': '100K subscribers',
                'focus': 'Engagement rate, kualitas produksi, branding',
                'challenge': 'Meningkatkan retention, monetisasi, scaling content',
                'strategy': 'Optimalkan CTR & AVD, diversifikasi konten, sponsorship'
            }
        elif subs < 1000000:
            category = "⭐ Mapan (Established)"
            level = "mapan"
            color = "#ffc107"  # Kuning/Gold
            benchmark = {
                'subs_target': '1M subscribers (Gold Button)',
                'focus': 'Skalabilitas, tim produksi, multiple revenue streams',
                'challenge': 'Mempertahankan growth, kompetisi ketat, burnout',
                'strategy': 'Professional production, merchandise, komunitas loyal'
            }
        else:
            category = "💎 Profesional (Pro/Celebrity)"
            level = "profesional"
            color = "#dc3545"  # Merah
            benchmark = {
                'subs_target': 'Maintain & grow beyond 1M',
                'focus': 'Brand deals, media exposure, viral content',
                'challenge': 'Inovasi konten, stay relevant, manajemen tim besar',
                'strategy': 'Multi-platform presence, exclusive content, big collaborations'
            }
        
        return {
            'category': category,
            'level': level,
            'color': color,
            'subs': subs,
            'avg_views': avg_views,
            'total_videos': total_videos,
            'benchmark': benchmark
        }

    #==========================================================
    # Fungsi Analisis Video
    #==========================================================
    def fetch_videos(self, uploads_playlist_id, limit=50):
        if not self.youtube: return pd.DataFrame()
        videos = []
        #==========================================================
        # lokalisasi
        #==========================================================  
        day_map = {
            'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu',
            'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'
        }

        try:
            self.used_quota += 1
            pl_req = self.youtube.playlistItems().list(
                part="snippet,contentDetails", playlistId=uploads_playlist_id, maxResults=limit
            )
            pl_res = pl_req.execute()
            video_ids = [item['contentDetails']['videoId'] for item in pl_res['items']]
            
            if not video_ids: return pd.DataFrame()
            
            #==========================================================
            # treking kuota
            #==========================================================  
            self.used_quota += 1
            vid_req = self.youtube.videos().list(
                part="snippet,statistics,contentDetails", id=','.join(video_ids)
            )
            vid_res = vid_req.execute()
            
            for item in vid_res['items']:
                stats = item['statistics']
                snippet = item['snippet']
                
                view = int(stats.get('viewCount', 0))
                like = int(stats.get('likeCount', 0))
                comm = int(stats.get('commentCount', 0))

                #==========================================================
                # timezone handling
                #==========================================================                
                pub_utc = pd.to_datetime(snippet['publishedAt'])
                pub_wib = pub_utc + pd.Timedelta(hours=7) if pub_utc.tzinfo is None else pub_utc.tz_convert('Asia/Jakarta')
                
                day_en = pub_wib.day_name()
                
                videos.append({
                    'video_id': item['id'],
                    'title': snippet['title'],
                    'published_at': pub_wib,
                    'view_count': view,
                    'like_count': like,
                    'comment_count': comm,
                    'duration': item['contentDetails']['duration'],
                    'day_name': day_map.get(day_en, day_en),
                    'hour': pub_wib.hour
                })
            return pd.DataFrame(videos)
        except:
            return pd.DataFrame()
