import os
import requests
import time
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import numpy as np
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.db import models
from app.core.recommender.popularity import get_popularity_recommendations
from app.core.recommender.content_based import get_content_based_recommendations
from app.core.recommender.reranking import apply_mmr_reranking
from app.architecture import load_ncf_model

router = APIRouter()

TMDB_CACHE = {}
CACHE_DURATION_SECONDS = 3600

class RecommendRequest(BaseModel):
    user_id: int

def resolve_demo_user_state(user_id: int):
    # user_id==1 -> Old User (NCF+MMR); ==2 -> New User+genre; >=3 -> New User popularity
    if user_id == 1:
        return False, []
    elif user_id == 2:
        return True, ["Action", "Sci-Fi", "Adventure"]
    else:
        return True, []

def fetch_tmdb_metadata(movie_id: int):
    current_time = time.time()

    if movie_id in TMDB_CACHE:
        cache_entry = TMDB_CACHE[movie_id]
        if current_time < cache_entry["expires_at"]:
            print(f"=== [CACHE HIT] Movie ID {movie_id} dari memori lokal ===")
            return cache_entry["data"]

    print(f"=== [CACHE MISS] Menembak API TMDB untuk Movie ID {movie_id} ===")

    if not settings.TMDB_API_KEY:
        return {"title": f"Movie ID {movie_id}", "synopsis": "API Key TMDB missing.", "poster_url": None}

    url = "https://api.themoviedb.org/3/movie/" + str(movie_id)
    params = {"api_key": settings.TMDB_API_KEY, "language": "id-ID"}

    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            poster_path = data.get("poster_path")
            full_poster_url = ("https://image.tmdb.org/t/p/w500" + poster_path) if poster_path else None

            metadata = {
                "title": data.get("title"),
                "synopsis": data.get("overview"),
                "poster_url": full_poster_url,
            }
            TMDB_CACHE[movie_id] = {"data": metadata, "expires_at": current_time + CACHE_DURATION_SECONDS}
            return metadata
    except Exception:
        pass

    return {"title": f"Movie ID {movie_id}", "synopsis": "Gagal memuat detail dari TMDB.", "poster_url": None}

def generate_recommendations(user_id: int, db: Session):
    from app.main import ml_models
    model = ml_models.get("ncf_model")

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
            model = load_ncf_model(dest_path)   # FIX: build + load_weights
            ml_models["ncf_model"] = model
            is_mock_mode = False
            print("=== [LATE INITIALIZATION SUCCESS] TensorFlow NCF model initialized and cached! ===")
        except Exception as e:
            print(f"=== [LATE INITIALIZATION FAILED] Live initialization failed: {str(e)} ===")

    # 1. Status user
    is_new_user = True
    genres = []

    try:
        user = db.query(models.UserProfile).filter(models.UserProfile.id == user_id).first()
        if user:
            if user.user_id_movielens is not None:
                is_new_user = False
            pref = db.query(models.OnboardingPreference).filter(models.OnboardingPreference.user_id == user.id).first()
            if pref and pref.preferred_genres:
                genres = [g.strip() for g in pref.preferred_genres.split(",") if g.strip()]
        else:
            # FIX B: profil tidak ada (DB kosong/seeding) -> pakai fallback deterministik
            print(f"=== [DB EMPTY/SEEDING] Profil user_id={user_id} belum ada. Fallback deterministik. ===")
            is_new_user, genres = resolve_demo_user_state(user_id)
    except Exception as e:
        print(f"=== [DB CONNECTION ERROR] Fallback to Mock User State: {str(e)} ===")
        is_new_user, genres = resolve_demo_user_state(user_id)

    # 2. Routing
    recommendations = []

    if is_new_user:
        if not genres:
            print("=== [ROUTING] New User (No Onboarding Genres) -> Popularity Recommender ===")
            recommendations = get_popularity_recommendations(top_k=5)
        else:
            print(f"=== [ROUTING] New User (Genres: {genres}) -> Content-Based Recommender ===")
            recommendations = get_content_based_recommendations(user_genres=genres, top_k=5)
    else:
        print(f"=== [ROUTING] Old User (ID: {user_id}) -> NCF Recommender ===")
        if is_mock_mode:
            print("=== [ROUTING FAILSAFE] NCF Model in Mock Mode. Fallback Content-Based/Popularity ===")
            if genres:
                recommendations = get_content_based_recommendations(user_genres=genres, top_k=5)
            else:
                recommendations = get_popularity_recommendations(top_k=5)
        else:
            try:
                candidate_model_indices = np.array([10, 25, 45, 88, 120, 300, 550, 1000])
                user_input = np.array([user_id] * len(candidate_model_indices))
                predictions = model.predict([user_input, candidate_model_indices], verbose=0)

                id_mapping = {
                    10: 550, 25: 27205, 45: 157336, 88: 680,
                    120: 155, 300: 299534, 550: 19995, 1000: 24428,
                }
                title_mapping = {
                    550: "Fight Club", 27205: "Inception", 157336: "Interstellar",
                    680: "Pulp Fiction", 155: "The Dark Knight",
                    299534: "Avengers: Endgame", 19995: "Avatar", 24428: "The Avengers",
                }

                raw_ncf_candidates = []
                scores = predictions.flatten()
                for idx, model_idx in enumerate(candidate_model_indices):
                    movie_id = id_mapping.get(model_idx)
                    if movie_id:
                        raw_ncf_candidates.append({
                            "movie_id": movie_id,
                            "score": float(scores[idx]),
                            "title": title_mapping.get(movie_id, f"Movie ID {movie_id}"),
                        })

                print("=== [MMR RERANKING] Applying MMR Reranking on NCF Candidates ===")
                recommendations = apply_mmr_reranking(raw_ncf_candidates, top_k=5, diversity_factor=0.5)
                print("=== [SUCCESS] Inference NCF + MMR Berhasil! ===")
            except Exception as e:
                print(f"=== [NCF INFERENCE ERROR] Fallback to Popularity: {str(e)} ===")
                recommendations = get_popularity_recommendations(top_k=5)

    # 3. Gabung metadata TMDB
    final_recommendations = []
    for rank, rec in enumerate(recommendations, start=1):
        movie_id = rec["movie_id"]
        metadata = fetch_tmdb_metadata(movie_id)
        final_recommendations.append({
            "rank": rank,
            "movie_id": movie_id,
            "title": metadata.get("title", rec.get("title")),
            "synopsis": metadata.get("synopsis", "Detail film tidak tersedia."),
            "poster_url": metadata.get("poster_url"),
            "xai_reason": rec["xai_reason"],
        })

    return {
        "status": "Success",
        "requested_user_id": user_id,
        "user_type": "New User" if is_new_user else "Old User",
        "mock_mode_active": is_mock_mode,
        "recommendations": final_recommendations,
    }

@router.get("/recommend/{user_id}")
def get_recommendations_get(user_id: int, db: Session = Depends(get_db)):
    return generate_recommendations(user_id, db)

@router.post("/recommend")
def get_recommendations_post(request: RecommendRequest, db: Session = Depends(get_db)):
    return generate_recommendations(request.user_id, db)