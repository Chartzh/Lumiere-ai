import json
import os
import numpy as np
import tensorflow as tf
from fastapi import FastAPI, HTTPException

# ── LOCK PATH ABSOLUT FILE KONFIGURASI DAN MODEL ──────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "model_config.json")
MODEL_PATH = os.path.join(BASE_DIR, "lumiere_ncf.h5")

# 1. Load file konfigurasi mapping index
try:
    with open(CONFIG_PATH, "r") as f:
        model_config = json.load(f)
except Exception as e:
    raise RuntimeError(f"Gagal memuat model_config.json di path {CONFIG_PATH}. Error: {str(e)}")

USER_TO_INDEX = model_config["user_to_index"]
INDEX_TO_MOVIE = model_config["index_to_movie"]
MOVIE_ID_TO_TITLE = model_config["movie_id_to_title"]
ALL_MOVIE_INDICES = list(map(int, INDEX_TO_MOVIE.keys()))

# 2. Load bobot model .h5 murni
try:
    model = tf.keras.models.load_model(MODEL_PATH)
except Exception as e:
    raise RuntimeError(f"Gagal memuat lumiere_ncf.h5 di path {MODEL_PATH}. Error: {str(e)}")

# ── INITIALIZATION ───────────────────────────────────────────────────
app = FastAPI(title="Lumiere AI Engine Testing", version="1.0.0")

@app.get("/")
def read_root():
    return {
        "message": "Welcome to Lumiere AI Engine Deployment Testing",
        "status": "Online",
        "ai_engine": "Neural Collaborative Filtering (NCF) v1 - Active"
    }

@app.get("/api/v1/recommend/{user_id}")
def get_ai_recommendations(user_id: str, top_k: int = 10):
    if user_id not in USER_TO_INDEX:
        raise HTTPException(
            status_code=404, 
            detail=f"User ID '{user_id}' tidak ditemukan dalam database matriks latihan."
        )
    
    user_idx = USER_TO_INDEX[user_id]
    num_items = len(ALL_MOVIE_INDICES)
    user_input_array = np.full(shape=(num_items,), fill_value=user_idx, dtype=np.int32)
    movie_input_array = np.array(ALL_MOVIE_INDICES, dtype=np.int32)
    
    predictions = model.predict([user_input_array, movie_input_array], verbose=0).flatten()
    top_indices = np.argsort(predictions)[::-1][:top_k]
    
    recommendations = []
    for idx in top_indices:
        movie_idx_internal = ALL_MOVIE_INDICES[idx]
        original_movie_id = INDEX_TO_MOVIE[str(movie_idx_internal)]
        movie_title = MOVIE_ID_TO_TITLE.get(str(original_movie_id), "Unknown Title")
        
        recommendations.append({
            "movie_id": int(original_movie_id),
            "title": movie_title,
            "confidence_score": float(predictions[idx])
        })
        
    return {
        "requested_user_id": user_id,
        "total_results": len(recommendations),
        "results": recommendations
    }