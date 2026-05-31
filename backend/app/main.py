import json
import numpy as np
import tensorflow as tf
from fastapi import FastAPI, HTTPException
from app.core.config import settings
from app.api.endpoints import movies  
from app.db.session import engine  
from app.db import models  

# 1. Load file konfigurasi mapping index
try:
    with open("app/model_config.json", "r") as f:
        model_config = json.load(f)
except Exception as e:
    # Fallback jika posisi folder saat deploy terbaca sebagai root lokal
    with open("model_config.json", "r") as f:
        model_config = json.load(f)

USER_TO_INDEX = model_config["user_to_index"]
INDEX_TO_MOVIE = model_config["index_to_movie"]
MOVIE_ID_TO_TITLE = model_config["movie_id_to_title"]
ALL_MOVIE_INDICES = list(map(int, INDEX_TO_MOVIE.keys()))

# 2. Load bobot model .h5 murni
try:
    model = tf.keras.models.load_model("app/lumiere_ncf.h5")
except Exception as e:
    model = tf.keras.models.load_model("lumiere_ncf.h5")

# =====================================================================
# 🚀 INITIALIZATION & ROUTING
# =====================================================================

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

# Perintah membuat tabel PostgreSQL bawaan Arghi
models.Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "status": "Online",
        "ai_engine": "Neural Collaborative Filtering (NCF) v1 - Active"
    }

# Include router database bawaan Arghi
app.include_router(movies.router, prefix="/api/v1", tags=["Movies Testing"])


# =====================================================================
# 🎬 NEW ENDPOINT: LIVE AI RECOMMENDATION FOR FRONTEND
# =====================================================================
@app.get("/api/v1/recommend/{user_id}")
def get_ai_recommendations(user_id: str, top_k: int = 10):
    """
    Endpoint khusus untuk Herlita & Zaky (Frontend) menembak ID User 
    dan langsung mendapatkan Top-K rekomendasi film dari model Rajif.
    """
    # 1. Validasi apakah User ID terdaftar di dataset latihan
    if user_id not in USER_TO_INDEX:
        raise HTTPException(
            status_code=404, 
            detail=f"User ID '{user_id}' tidak ditemukan dalam database matriks latihan (Cold Start)."
        )
    
    # 2. Ambil indeks internal user
    user_idx = USER_TO_INDEX[user_id]
    
    # 3. Siapkan array input untuk TensorFlow (Pasangkan user_idx dengan SEMUA film yang ada)
    num_items = len(ALL_MOVIE_INDICES)
    user_input_array = np.full(shape=(num_items,), fill_value=user_idx, dtype=np.int32)
    movie_input_array = np.array(ALL_MOVIE_INDICES, dtype=np.int32)
    
    # 4. Jalankan Prediksi Inferensi (model.predict)
    predictions = model.predict([user_input_array, movie_input_array], verbose=0).flatten()
    
    # 5. Ambil Top-K indeks dengan nilai rating prediksi tertinggi
    top_indices = np.argsort(predictions)[::-1][:top_k]
    
    # 6. Terjemahkan kembali menjadi struktur JSON yang dimengerti Frontend
    recommendations = []
    for idx in top_indices:
        movie_idx_internal = ALL_MOVIE_INDICES[idx]
        original_movie_id = INDEX_TO_MOVIE[str(movie_idx_internal)]
        movie_title = MOVIE_ID_TO_TITLE.get(str(original_movie_id), "Unknown Title")
        
        recommendations.append({
            "movie_id": int(original_movie_id),
            "title": movie_title,
            "confidence_score": float(predictions[idx]) # Skala 0 - 1 hasil sigmoid
        })
        
    return {
        "requested_user_id": user_id,
        "total_results": len(recommendations),
        "results": recommendations
    }