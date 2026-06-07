from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # <-- Tambahkan ini
from contextlib import asynccontextmanager
import tensorflow as tf
import os
from app.core.config import settings
from app.api.endpoints import movies
from app.db.session import engine
from app.db import models

ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=== [STARTUP] Loading TensorFlow Model... ===")
    model_path = os.path.join(os.path.dirname(__file__), "model_weights", "lumiere_ncf.h5")
    if os.path.exists(model_path):
        try:
            ml_models["ncf_model"] = tf.keras.models.load_model(model_path)
            print("=== [STARTUP] Model 'lumiere_ncf.h5' Loaded Successfully! ===")
        except Exception as e:
            print(f"=== [STARTUP] Gagal memuat model: {str(e)} ===")
            ml_models["ncf_model"] = None
    else:
        print(f"=== [STARTUP] Warning: File model tidak ditemukan... ===")
        ml_models["ncf_model"] = None
    yield
    print("=== [SHUTDOWN] Cleaning up resources... ===")
    ml_models.clear()

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0", lifespan=lifespan)

# TUGAS MEDIUM 2: Konfigurasi CORS agar bisa diakses dari frontend SvelteKit
# Di fase produksi, lo bisa mengganti "*" dengan URL hosting murni SvelteKit milik tim lo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Mengizinkan semua origin akses (aman untuk fase development)
    allow_credentials=True,
    allow_methods=["*"],  # Mengizinkan semua method (GET, POST, PUT, DELETE)
    allow_headers=["*"],  # Mengizinkan semua jenis HTTP Headers
)

app.include_router(movies.router, prefix="/api/v1", tags=["Movies & Recommendation"])