import pandas as pd

class SAWModel:
#================================================================================================
#Fungsi Inisialisasi
#================================================================================================
    def __init__(self, weights):
        """
        weights: Dictionary {'views': float, 'likes': float, 'comments': float, 'er': float}
        """
        self.weights = weights
#================================================================================================
#Fungsi Perhitungan Metrik
#================================================================================================
    def calculate_engagement_rate(self, df):
        """Menghitung Engagement Rate (ER)"""
        # Rumus: (Likes + Comments) / Views * 100
        # Hindari pembagian 0
        df['engagement_rate'] = df.apply(
            lambda x: ((x['like_count'] + x['comment_count']) / x['view_count'] * 100) 
            if x['view_count'] > 0 else 0, axis=1
        )
        return df
#================================================================================================
#Fungsi Normalisasi
#================================================================================================
    def normalize_data(self, df):
        """Normalisasi Matriks (Metode Benefit)"""
        # Copy dataframe agar data asli aman
        df_norm = df.copy()
        
        # Mencari nilai Max tiap kriteria
        max_views = df['view_count'].max()
        max_likes = df['like_count'].max()
        max_comments = df['comment_count'].max()
        max_er = df['engagement_rate'].max()
        
        # Rumus Normalisasi: Rij = Xij / Max(Xj)
        df_norm['norm_views'] = df['view_count'] / max_views if max_views > 0 else 0
        df_norm['norm_likes'] = df['like_count'] / max_likes if max_likes > 0 else 0
        df_norm['norm_comments'] = df['comment_count'] / max_comments if max_comments > 0 else 0
        df_norm['norm_er'] = df['engagement_rate'] / max_er if max_er > 0 else 0
        
        return df_norm
#================================================================================================
#Fungsi Perhitungan Skor Preferensi
#================================================================================================
    def calculate_preference(self, df_norm):
        """Menghitung Nilai Preferensi (V)"""
        # V = W1*R1 + W2*R2 + ...
        df_norm['preference_score'] = (
            (self.weights['views'] * df_norm['norm_views']) +
            (self.weights['likes'] * df_norm['norm_likes']) +
            (self.weights['comments'] * df_norm['norm_comments']) +
            (self.weights['er'] * df_norm['norm_er'])
        )

        return df_norm.sort_values(by='preference_score', ascending=False).reset_index(drop=True)
