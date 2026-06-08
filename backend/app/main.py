from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  
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

# Daftarkan port default SvelteKit lokal agar allow_credentials=True bisa berjalan valid
origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # Menggunakan list origin spesifik (Aman untuk browser)
    allow_credentials=True,       # Tetap True untuk handle session/cookies frontend jika ada
    allow_methods=["*"],          # Mengizinkan semua method (GET, POST, PUT, DELETE)
    allow_headers=["*"],          # Mengizinkan semua jenis HTTP Headers
)

app.include_router(movies.router, prefix="/api/v1", tags=["Movies & Recommendation"])