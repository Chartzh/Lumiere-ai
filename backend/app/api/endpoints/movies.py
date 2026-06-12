import os
import json
import time
import requests
import numpy as np
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.db import models
from app.core.recommender.catalog import get_movie
from app.core.recommender.popularity import get_popularity_recommendations
from app.core.recommender.content_based import get_content_based_recommendations
from app.core.recommender.reranking import apply_mmr_reranking
from app.core.recommender.genre_based import get_genre_recommendations
from app.core.recommender.exploration import get_serendipity_recommendations
from app.architecture import load_ncf_model

router = APIRouter()

# ===================== Konfigurasi =====================
DEFAULT_TOP_K = 10
NCF_CANDIDATE_POOL = 60          # ambil N kandidat teratas dari NCF lalu MMR -> top_k
MODEL_URL = "https://ccodbglbolcxaohndouu.supabase.co/storage/v1/object/public/models/lumiere_ncf.h5"
MODEL_DEST = "/tmp/lumiere_ncf.h5"

TMDB_CACHE = {}
CACHE_DURATION_SECONDS = 3600


class RecommendRequest(BaseModel):
    user_id: int


# ===================== model_config.json (mapping NCF) =====================
_CONFIG = None


def _load_model_config():
    """Muat mapping index<->movie_id dari model_config.json (sekali, lalu cache)."""
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG
    candidates = [
        "model_config.json",
        "/app/model_config.json",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "model_config.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, "r") as f:
                _CONFIG = json.load(f)
            print(f"=== [CONFIG] model_config.json dimuat dari {path} ===")
            return _CONFIG
    print("=== [CONFIG] model_config.json TIDAK ditemukan ===")
    return None


# ===================== state user demo =====================
def resolve_demo_user_state(user_id):
    if user_id == 1:
        return False, []                                # Old User -> NCF penuh
    elif user_id == 2:
        return True, ["Action", "Sci-Fi", "Adventure"]   # New User -> Content-Based
    else:
        return True, []                                 # New User skip onboarding -> Popularity


def _determine_user_state(user_id, db):
    is_new_user = True
    genres = []
    seed_movie_ids = []
    try:
        user = db.query(models.UserProfile).filter(models.UserProfile.id == user_id).first()
        if user:
            if user.user_id_movielens is not None:
                is_new_user = False
            pref = db.query(models.OnboardingPreference).filter(
                models.OnboardingPreference.user_id == user.id
            ).first()
            if pref:
                if pref.preferred_genres:
                    genres = [g.strip() for g in pref.preferred_genres.split(",") if g.strip()]
                if getattr(pref, "preferred_movie_ids", None):
                    seed_movie_ids = [int(x) for x in pref.preferred_movie_ids.split(",") if x.strip().isdigit()]
        else:
            is_new_user, genres = resolve_demo_user_state(user_id)
    except Exception as e:
        print(f"=== [DB ERROR] {str(e)} -> pakai skenario demo ===")
        is_new_user, genres = resolve_demo_user_state(user_id)
    return is_new_user, genres, seed_movie_ids


# ===================== model (late init) =====================
def _ensure_model_loaded():
    from app.main import ml_models
    model = ml_models.get("ncf_model")
    is_mock_mode = (model is None) or (isinstance(model, dict) and model.get("status") == "mock_mode")
    if is_mock_mode:
        try:
            if not os.path.exists(MODEL_DEST):
                print("=== [LATE INIT] Mengunduh model NCF dari Supabase... ===")
                resp = requests.get(MODEL_URL, stream=True, timeout=60)
                if resp.status_code != 200:
                    raise Exception(f"Download gagal, HTTP status: {resp.status_code}")
                os.makedirs(os.path.dirname(MODEL_DEST), exist_ok=True)
                with open(MODEL_DEST, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            model = load_ncf_model(MODEL_DEST)
            ml_models["ncf_model"] = model
            is_mock_mode = False
            print("=== [LATE INIT] Model berhasil dimuat. ===")
        except Exception as e:
            print(f"=== [LATE INIT FAILED] {str(e)} ===")
            model = None
            is_mock_mode = True
    return model, is_mock_mode


# ===================== NCF penuh + MMR =====================
def _ncf_recommend(user_id, model, top_k):
    """
    Skor SELURUH film yang dikenal model (via index_to_movie di model_config),
    ambil pool kandidat teratas, lalu re-ranking MMR untuk diversifikasi.
    """
    config = _load_model_config()
    if not config:
        raise Exception("model_config.json tidak tersedia")

    user_to_index = config["user_to_index"]
    index_to_movie = config["index_to_movie"]

    if str(user_id) not in user_to_index:
        raise Exception(f"UserID {user_id} tidak ada di mapping NCF (bukan user lama)")

    user_idx = int(user_to_index[str(user_id)])

    movie_indices = np.array([int(k) for k in index_to_movie.keys()], dtype=np.int32)
    user_array = np.full(len(movie_indices), user_idx, dtype=np.int32)

    preds = model.predict([user_array, movie_indices], batch_size=2048, verbose=0).flatten()

    pool_size = max(top_k, NCF_CANDIDATE_POOL)
    top_pool = np.argsort(preds)[::-1][:pool_size]

    raw_candidates = []
    for i in top_pool:
        model_idx = int(movie_indices[i])
        movie_id = int(index_to_movie[str(model_idx)])
        movie = get_movie(movie_id)
        raw_candidates.append({
            "movie_id": movie_id,
            "score": float(preds[i]),  # 0..1 (sigmoid)
            "title": movie["title"] if movie else None,
        })

    return apply_mmr_reranking(raw_candidates, top_k=top_k, diversity_factor=0.5)


# ===================== routing inti =====================
def _route_recommendations(user_id, db, top_k, model, is_mock_mode):
    is_new_user, genres, seed_movie_ids = _determine_user_state(user_id, db)

    if is_new_user:
        if genres or seed_movie_ids:
            engine = "Content-Based (Onboarding)"
            recs = get_content_based_recommendations(user_genres=genres, top_k=top_k, seed_movie_ids=seed_movie_ids)
        else:
            engine = "Popularity (Skip Onboarding)"
            recs = get_popularity_recommendations(top_k=top_k)
    else:
        if is_mock_mode or model is None:
            if genres:
                engine = "Content-Based (NCF Fallback)"
                recs = get_content_based_recommendations(user_genres=genres, top_k=top_k, seed_movie_ids=seed_movie_ids)
            else:
                engine = "Popularity (NCF Fallback)"
                recs = get_popularity_recommendations(top_k=top_k)
        else:
            try:
                engine = "NCF + MMR"
                recs = _ncf_recommend(user_id, model, top_k)
                if not recs:
                    engine = "Popularity (NCF Empty Fallback)"
                    recs = get_popularity_recommendations(top_k=top_k)
            except Exception as e:
                print(f"=== [NCF ERROR] {str(e)} ===")
                engine = "Popularity (NCF Error Fallback)"
                recs = get_popularity_recommendations(top_k=top_k)

    return recs, is_new_user, engine


# ===================== TMDB metadata (cari via judul + tahun) =====================
def fetch_tmdb_metadata(movie_id, title, year):
    """
    MovieLens movie_id BUKAN TMDB id, jadi poster dicari via /search/movie
    pakai judul (+ tahun) untuk akurasi.
    """
    now = time.time()
    cached = TMDB_CACHE.get(movie_id)
    if cached and (now - cached["ts"] < CACHE_DURATION_SECONDS):
        return cached["data"]

    data = {"title": title, "synopsis": "Detail film tidak tersedia.", "poster_url": None}
    try:
        url = "https://api.themoviedb.org/3/search/movie"
        params = {"api_key": settings.TMDB_API_KEY, "query": title, "language": "en-US"}
        if year:
            params["year"] = year
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                first = results[0]
                poster_path = first.get("poster_path")
                data = {
                    "title": first.get("title") or title,
                    "synopsis": first.get("overview") or "Detail film tidak tersedia.",
                    "poster_url": ("https://image.tmdb.org/t/p/w500" + poster_path) if poster_path else None,
                }
    except Exception as e:
        print(f"=== [TMDB ERROR] movie {movie_id} ({title}): {str(e)} ===")

    TMDB_CACHE[movie_id] = {"ts": now, "data": data}
    return data


def _enrich(recommendations):
    final = []
    for rank, rec in enumerate(recommendations, start=1):
        movie_id = rec["movie_id"]
        movie = get_movie(movie_id)
        title = (movie["title"] if movie else None) or rec.get("title")
        year = movie["year"] if movie else None
        meta = fetch_tmdb_metadata(movie_id, title, year)
        final.append({
            "rank": rank,
            "movie_id": movie_id,
            "title": meta.get("title") or title,
            "year": year,
            "synopsis": meta.get("synopsis", "Detail film tidak tersedia."),
            "poster_url": meta.get("poster_url"),
            "xai_reason": rec["xai_reason"],
        })
    return final


# ===================== Core builder =====================
def generate_recommendations(user_id, db, top_k=DEFAULT_TOP_K, section="for_you"):
    model, is_mock_mode = _ensure_model_loaded()
    recs, is_new_user, engine = _route_recommendations(user_id, db, top_k, model, is_mock_mode)
    return {
        "status": "Success",
        "section": section,
        "requested_user_id": user_id,
        "user_type": "New User" if is_new_user else "Old User",
        "engine": engine,
        "mock_mode_active": is_mock_mode,
        "recommendations": _enrich(recs),
    }


# ===================================================================
# ENDPOINTS (rute statik HARUS sebelum /recommend/{user_id})
# ===================================================================
@router.get("/recommend/foryou/{user_id}")
def recommend_foryou(user_id: int, top_k: int = DEFAULT_TOP_K, db: Session = Depends(get_db)):
    return generate_recommendations(user_id, db, top_k=top_k, section="for_you")


@router.get("/recommend/trending")
def recommend_trending(top_k: int = 15):
    return {
        "status": "Success",
        "section": "trending",
        "engine": "Popularity",
        "recommendations": _enrich(get_popularity_recommendations(top_k=top_k)),
    }


@router.get("/recommend/genre/{genre}")
def recommend_genre(genre: str, top_k: int = 15):
    return {
        "status": "Success",
        "section": "genre:" + genre,
        "engine": "Genre Browse (Ranked)",
        "recommendations": _enrich(get_genre_recommendations(genre, top_k=top_k)),
    }


@router.get("/recommend/serendipity/{user_id}")
def recommend_serendipity(user_id: int, top_k: int = 10, db: Session = Depends(get_db)):
    is_new_user, genres, seed_movie_ids = _determine_user_state(user_id, db)
    recs = get_serendipity_recommendations(top_k=top_k, avoid_genres=genres)
    return {
        "status": "Success",
        "section": "serendipity",
        "requested_user_id": user_id,
        "engine": "Exploration",
        "recommendations": _enrich(recs),
    }


@router.post("/recommend")
def recommend_post(request: RecommendRequest, top_k: int = DEFAULT_TOP_K, db: Session = Depends(get_db)):
    return generate_recommendations(request.user_id, db, top_k=top_k)


@router.get("/recommend/{user_id}")
def recommend_get(user_id: int, top_k: int = DEFAULT_TOP_K, db: Session = Depends(get_db)):
    return generate_recommendations(user_id, db, top_k=top_k)
