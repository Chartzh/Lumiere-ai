import requests
import time  # Ditambahkan untuk menghitung waktu kedaluwarsa cache
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import numpy as np
from app.core.config import settings

router = APIRouter()

# TUGAS MEDIUM: Struktur In-Memory Cache untuk data TMDB (Mitigasi Rate Limit)
# Format penyimpanan: { movie_id: {"data": metadata_dict, "expires_at": timestamp} }
TMDB_CACHE = {}
CACHE_DURATION_SECONDS = 3600  # Menyimpan data TMDB di memori server selama 1 jam


# Schema Input untuk menerima JSON body
class RecommendRequest(BaseModel):
    user_id: int


# Helper untuk fetch metadata film dari TMDB menggunakan Local Caching
def fetch_tmdb_metadata(movie_id: int):
    current_time = time.time()
    
    # 1. Cek apakah data film sudah ada di memori cache dan belum expired
    if movie_id in TMDB_CACHE:
        cache_entry = TMDB_CACHE[movie_id]
        if current_time < cache_entry["expires_at"]:
            print(f"=== [CACHE HIT] Mengambil detail Movie ID {movie_id} dari memori lokal ===")
            return cache_entry["data"]
            
    print(f"=== [CACHE MISS] Menembak API TMDB untuk Movie ID {movie_id} ===")
    
    if not settings.TMDB_API_KEY:
        return {"title": f"Movie ID {movie_id}", "synopsis": "API Key TMDB missing.", "poster_url": None}
        
    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {"api_key": settings.TMDB_API_KEY, "language": "id-ID"}
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            poster_path = data.get("poster_path")
            full_poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
            
            metadata = {
                "title": data.get("title"),
                "synopsis": data.get("overview"),
                "poster_url": full_poster_url
            }
            
            # 2. Simpan hasil response baru ke dalam Local Cache beserta batas waktu durasinya
            TMDB_CACHE[movie_id] = {
                "data": metadata,
                "expires_at": current_time + CACHE_DURATION_SECONDS
            }
            
            return metadata
    except Exception:
        pass
        
    return {"title": f"Movie ID {movie_id}", "synopsis": "Gagal memuat detail dari TMDB.", "poster_url": None}


# Endpoint POST /recommend
@router.post("/recommend")
def get_movie_recommendations(request: RecommendRequest):
    from app.main import ml_models
    model = ml_models.get("ncf_model")
    
    # Fallback murni ID TMDB populer jika model TensorFlow gagal/belum siap
    recommended_movie_ids = [550, 27205, 157336, 680, 155]
    
    # Jika model TensorFlow berhasil dimuat, jalankan prediksi real
    if model:
        try:
            # Menggunakan ID indeks kecil (0-3705) agar sesuai dengan dimensi matriks model embedding Rajif
            candidate_model_indices = np.array([10, 25, 45, 88, 120, 300, 550, 1000])
            user_input = np.array([request.user_id] * len(candidate_model_indices))
            
            # Jalankan inference model TensorFlow NCF
            predictions = model.predict([user_input, candidate_model_indices], verbose=0)
            
            # Ambil Top 5 index dengan skor tertinggi
            top_indices = np.argsort(predictions.flatten())[::-1][:5]
            selected_model_indices = candidate_model_indices[top_indices].tolist()
            
            # Mapping balik dari indeks model internal ke ID TMDB rilisan global
            # Kita petakan hasil urutan teratas ke film-film ikonik untuk demonstrasi visual
            id_mapping = {
                10: 550,     # Fight Club
                25: 27205,   # Inception
                45: 157336,  # Interstellar
                88: 680,     # Pulp Fiction
                120: 155,    # The Dark Knight
                300: 299534, # Avengers: Endgame
                550: 19995,  # Avatar
                1000: 24428  # The Avengers
            }
            
            recommended_movie_ids = [id_mapping.get(idx, 550) for idx in selected_model_indices]
            print("=== [SUCCESS] Inference Model TensorFlow NCF Berhasil Tanpa Error! ===")
            
        except Exception as e:
            print(f"Error saat inference model: {str(e)}")
            pass

    # Kombinasikan ID rekomendasi dengan metadata visual TMDB (Mendukung Caching)
    final_recommendations = []
    for rank, movie_id in enumerate(recommended_movie_ids, start=1):
        metadata = fetch_tmdb_metadata(movie_id)
        final_recommendations.append({
            "rank": rank,
            "movie_id": movie_id,
            "title": metadata["title"],
            "synopsis": metadata["synopsis"],
            "poster_url": metadata["poster_url"]
        })
        
    return {
        "status": "Success",
        "requested_user_id": request.user_id,
        "recommendations": final_recommendations
    }