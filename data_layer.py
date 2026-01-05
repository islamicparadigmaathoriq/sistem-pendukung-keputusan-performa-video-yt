import pandas as pd
from googleapiclient.discovery import build
import datetime

class DataManager:
    def __init__(self, api_key):
        self.api_key = api_key
        self.youtube = None
        # Inisialisasi Counter Kuota (Estimasi)
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

    def search_channels(self, query, limit=5):
        """Mencari channel berdasarkan nama"""
        if not self.youtube: return []
        try:
            # SEARCH COST: 100 Units per call
            self.used_quota += 100 
            
            request = self.youtube.search().list(
                part="snippet",
                q=query,
                type="channel",
                maxResults=limit
            )
            response = request.execute()
            
            results = []
            for item in response['items']:
                snippet = item['snippet']
                thumbnails = snippet.get('thumbnails', {})
                thumb_url = thumbnails.get('high', {}).get('url') or \
                            thumbnails.get('medium', {}).get('url') or \
                            thumbnails.get('default', {}).get('url') or \
                            "https://via.placeholder.com/150"

                results.append({
                    'channel_id': item['snippet']['channelId'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'thumbnail': thumb_url, 
                    'publish_time': item['snippet']['publishedAt']
                })
            return results
        except Exception as e:
            return []

    def _detect_niche(self, channel_item):
        """Deteksi Niche + Geografi"""
        topics = channel_item.get('topicDetails', {}).get('topicCategories', [])
        text = (channel_item['snippet']['title'] + " " + channel_item['snippet']['description']).lower()
        
        base_niche = "Umum / Campuran"
        geo_tag = ""

        # 1. Geografi
        if any(x in text for x in ['j-pop', 'jpop', 'japanese', 'japan', 'anime', 'tokyo', 'vtuber']): geo_tag = "(Jepang)"
        elif any(x in text for x in ['k-pop', 'kpop', 'korea', 'seoul', 'drakor', 'mv']): geo_tag = "(Korea)"
        elif any(x in text for x in ['indonesia', 'indo', 'dangdut', 'koplo', 'jakarta', 'official video']): geo_tag = "(Indonesia)"
        elif any(x in text for x in ['usa', 'us', 'uk', 'western', 'hollywood', 'vevo']): geo_tag = "(Barat)"

        # 2. Topik
        niche_map = {
            'Technology': 'Teknologi', 'Gaming': 'Gaming',
            'Lifestyle': 'Vlog & Lifestyle', 'Entertainment': 'Hiburan',
            'Music': 'Musik', 'Knowledge': 'Edukasi', 'Sport': 'Olahraga',
            'Food': 'Kuliner', 'Fashion': 'Fashion'
        }
        
        found_topic = False
        for url in topics:
            for key, label in niche_map.items():
                if key in url: 
                    base_niche = label
                    found_topic = True
                    break
            if found_topic: break
        
        if not found_topic:
            if any(x in text for x in ['game', 'play', 'esport', 'minecraft']): base_niche = "Gaming"
            elif any(x in text for x in ['gadget', 'review', 'tech', 'hp']): base_niche = "Teknologi"
            elif any(x in text for x in ['song', 'music', 'cover', 'lirik']): base_niche = "Musik"
            elif any(x in text for x in ['vlog', 'daily', 'travel']): base_niche = "Vlog & Lifestyle"

        return f"{base_niche} {geo_tag}".strip()

    def get_channel_info(self, channel_id):
        if not self.youtube: return None
        try:
            # CHANNEL LIST COST: 1 Unit
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

    def fetch_videos(self, uploads_playlist_id, limit=50):
        if not self.youtube: return pd.DataFrame()
        videos = []
        
        # --- [PERBAIKAN 1: KAMUS HARI INDONESIA] ---
        day_map = {
            'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu',
            'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'
        }
        # -------------------------------------------

        try:
            # PLAYLIST ITEMS COST: 1 Unit
            self.used_quota += 1
            
            pl_request = self.youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=limit
            )
            pl_response = pl_request.execute()
            video_ids = [item['contentDetails']['videoId'] for item in pl_response['items']]
            
            if not video_ids: return pd.DataFrame()

            # VIDEOS LIST COST: 1 Unit
            self.used_quota += 1
            
            vid_request = self.youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=','.join(video_ids)
            )
            vid_response = vid_request.execute()
            
            for item in vid_response['items']:
                stats = item['statistics']
                snippet = item['snippet']
                
                view_count = int(stats.get('viewCount', 0))
                like_count = int(stats.get('likeCount', 0))
                comment_count = int(stats.get('commentCount', 0))
                
                # Konversi ke WIB
                pub_date_utc = pd.to_datetime(snippet['publishedAt'])
                if pub_date_utc.tzinfo is None:
                    pub_date_wib = pub_date_utc + pd.Timedelta(hours=7)
                else:
                    pub_date_wib = pub_date_utc.tz_convert('Asia/Jakarta')
                
                # --- [PERBAIKAN 2: KONVERSI NAMA HARI KE INDONESIA] ---
                day_english = pub_date_wib.day_name()
                day_indo = day_map.get(day_english, day_english)
                # ------------------------------------------------------

                videos.append({
                    'video_id': item['id'],
                    'title': snippet['title'],
                    'published_at': pub_date_wib,
                    'view_count': view_count,
                    'like_count': like_count,
                    'comment_count': comment_count,
                    'duration': item['contentDetails']['duration'],
                    'day_name': day_indo, # Simpan nama hari Indonesia
                    'hour': pub_date_wib.hour
                })
            return pd.DataFrame(videos)
        except:
            return pd.DataFrame()