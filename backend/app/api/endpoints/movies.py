import os
import tensorflow as tf
import requests
import time  # Ditambahkan untuk menghitung waktu kedaluwarsa cache
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.db import models

# Import recommender modules
from app.core.recommender.popularity import get_popularity_recommendations
from app.core.recommender.content_based import get_content_based_recommendations
from app.core.recommender.reranking import apply_mmr_reranking

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


# Core recommendation router logic
def generate_recommendations(user_id: int, db: Session):
    from app.main import ml_models
    model = ml_models.get("ncf_model")
    
    # Check if NCF model is in mock mode (either loading failed or not ready)
    is_mock_mode = (model is None) or (isinstance(model, dict) and model.get("status") == "mock_mode")
    
    if is_mock_mode:
        print("=== [LATE INITIALIZATION] NCF Model is in Mock Mode. Attempting live initialization... ===")
        url = "https://ccodbglbolcxaohndouu.supabase.co/storage/v1/object/public/models/lumiere_ncf.h5"
        dest_path = "/tmp/lumiere_ncf.h5"
        try:
            if not os.path.exists(dest_path):
                print(f"=== [LATE INITIALIZATION] Downloading model from {url}... ===")
                response = requests.get(url, stream=True, timeout=60)
                if response.status_code == 200:
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with open(dest_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    print(f"=== [LATE INITIALIZATION] Download complete: {dest_path} ===")
                else:
                    raise Exception(f"Download HTTP status: {response.status_code}")
            else:
                print(f"=== [LATE INITIALIZATION] Model already exists at {dest_path} ===")
            
            print("=== [LATE INITIALIZATION] Loading Keras model... ===")
            model = tf.keras.models.load_model(dest_path)
            ml_models["ncf_model"] = model
            is_mock_mode = False
            print("=== [LATE INITIALIZATION SUCCESS] TensorFlow NCF model initialized and cached! ===")
        except Exception as e:
            print(f"=== [LATE INITIALIZATION FAILED] Live initialization failed: {str(e)} ===")
    
    # 1. Determine User State: New or Old, and Onboarding Genres
    is_new_user = True
    genres = []
    
    try:
        # Query User Profile from DB
        user = db.query(models.UserProfile).filter(models.UserProfile.id == user_id).first()
        if user:
            # Check user_id_movielens. If present, they are an old/existing user with historical training data
            if user.user_id_movielens is not None:
                is_new_user = False
            
            # Fetch onboarding preferences
            pref = db.query(models.OnboardingPreference).filter(models.OnboardingPreference.user_id == user.id).first()
            if pref and pref.preferred_genres:
                genres = [g.strip() for g in pref.preferred_genres.split(",") if g.strip()]
        else:
            # User profile not found in database, classify as new user
            is_new_user = True
            genres = []
    except Exception as e:
        print(f"=== [DB CONNECTION ERROR] Fallback to Mock User State: {str(e)} ===")
        # DB is offline or port problem: apply deterministic fallbacks based on user_id
        # user_id == 1: Old user (test NCF + MMR)
        # user_id == 2: New user with onboarding genres (test Content-based)
        # user_id >= 3: New user who skipped onboarding (test Popularity)
        if user_id == 1:
            is_new_user = False
            genres = []
        elif user_id == 2:
            is_new_user = True
            genres = ["Action", "Sci-Fi", "Adventure"]
        else:
            is_new_user = True
            genres = []

    # 2. Recommendation Routing Logic
    recommendations = []
    
    if is_new_user:
        if not genres:
            # New user, skipped onboarding -> Popularity recommendations
            print("=== [ROUTING] New User (No Onboarding Genres) -> Popularity Recommender ===")
            recommendations = get_popularity_recommendations(top_k=5)
        else:
            # New user, completed onboarding -> Content-Based recommendations
            print(f"=== [ROUTING] New User (Genres: {genres}) -> Content-Based Recommender ===")
            recommendations = get_content_based_recommendations(user_genres=genres, top_k=5)
    else:
        # Old user -> NCF Model recommendations
        print(f"=== [ROUTING] Old User (ID: {user_id}) -> NCF Recommender ===")
        if is_mock_mode:
            print("=== [ROUTING FAILSAFE] NCF Model is in Mock Mode. Falling back to Content-Based or Popularity ===")
            if genres:
                recommendations = get_content_based_recommendations(user_genres=genres, top_k=5)
            else:
                recommendations = get_popularity_recommendations(top_k=5)
        else:
            try:
                # Run real NCF model inference
                candidate_model_indices = np.array([10, 25, 45, 88, 120, 300, 550, 1000])
                user_input = np.array([user_id] * len(candidate_model_indices))
                predictions = model.predict([user_input, candidate_model_indices], verbose=0)
                
                # Format candidate list for MMR
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
                title_mapping = {
                    550: "Fight Club",
                    27205: "Inception",
                    157336: "Interstellar",
                    680: "Pulp Fiction",
                    155: "The Dark Knight",
                    299534: "Avengers: Endgame",
                    19995: "Avatar",
                    24428: "The Avengers"
                }
                
                raw_ncf_candidates = []
                scores = predictions.flatten()
                for idx, model_idx in enumerate(candidate_model_indices):
                    movie_id = id_mapping.get(model_idx)
                    if movie_id:
                        raw_ncf_candidates.append({
                            "movie_id": movie_id,
                            "score": float(scores[idx]),
                            "title": title_mapping.get(movie_id, f"Movie ID {movie_id}")
                        })
                
                # Filter candidates using MMR reranking
                print("=== [MMR RERANKING] Applying MMR Reranking on NCF Candidates ===")
                recommendations = apply_mmr_reranking(raw_ncf_candidates, top_k=5, diversity_factor=0.5)
                print("=== [SUCCESS] Inference Model TensorFlow NCF + MMR Berhasil! ===")
            except Exception as e:
                print(f"=== [NCF INFERENCE ERROR] Fallback to Popularity: {str(e)} ===")
                recommendations = get_popularity_recommendations(top_k=5)

    # 3. Combine recommendation items with TMDB metadata
    final_recommendations = []
    for rank, rec in enumerate(recommendations, start=1):
        movie_id = rec["movie_id"]
        # Fetch TMDB metadata (synopsis, poster, etc.)
        metadata = fetch_tmdb_metadata(movie_id)
        
        final_recommendations.append({
            "rank": rank,
            "movie_id": movie_id,
            "title": metadata.get("title", rec.get("title")),
            "synopsis": metadata.get("synopsis", "Detail film tidak tersedia."),
            "poster_url": metadata.get("poster_url"),
            "xai_reason": rec["xai_reason"]
        })
        
    return {
        "status": "Success",
        "requested_user_id": user_id,
        "user_type": "New User" if is_new_user else "Old User",
        "mock_mode_active": is_mock_mode,
        "recommendations": final_recommendations
    }


# Rerouted endpoints to support both GET /recommend/{user_id} and POST /recommend
@router.get("/recommend/{user_id}")
def get_recommendations_get(user_id: int, db: Session = Depends(get_db)):
    return generate_recommendations(user_id, db)


@router.post("/recommend")
def get_recommendations_post(request: RecommendRequest, db: Session = Depends(get_db)):
    return generate_recommendations(request.user_id, db)