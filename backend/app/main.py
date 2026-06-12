from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import requests

from app.core.config import settings
from app.api.endpoints import movies, onboarding
from app.core.recommender import catalog
from app.architecture import load_ncf_model

ml_models = {}


def download_model(url: str, dest_path: str):
    print(f"=== [STARTUP] Downloading NCF Model from {url}... ===")
    response = requests.get(url, stream=True, timeout=60)
    if response.status_code == 200:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"=== [STARTUP] Model downloaded successfully to {dest_path} ===")
    else:
        raise Exception(f"Failed to download model, HTTP status: {response.status_code}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Muat katalog film dari Supabase ke memori (pengganti DUMMY_MOVIES)
    print("=== [STARTUP] Memuat katalog film dari Supabase... ===")
    catalog.warm_cache()

    # 2. Muat model NCF
    print("=== [STARTUP] Loading TensorFlow Model... ===")
    url = "https://ccodbglbolcxaohndouu.supabase.co/storage/v1/object/public/models/lumiere_ncf.h5"
    dest_path = "/tmp/lumiere_ncf.h5"
    try:
        download_model(url, dest_path)
        ml_models["ncf_model"] = load_ncf_model(dest_path)
        print("=== [STARTUP] Model 'lumiere_ncf.h5' Loaded Successfully from /tmp! ===")
    except Exception as e:
        print(f"=== [STARTUP] Gagal mengunduh atau memuat model: {str(e)} ===")
        print("=== [STARTUP] Mengaktifkan MOCK_MODE untuk NCF Model ===")
        ml_models["ncf_model"] = {"status": "mock_mode"}
    yield
    print("=== [SHUTDOWN] Cleaning up resources... ===")
    ml_models.clear()


app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(movies.router, prefix="/api/v1", tags=["Movies & Recommendation"])
app.include_router(onboarding.router, prefix="/api/v1", tags=["Onboarding"])


@app.get("/")
def read_root():
    return {
        "message": "Welcome to Lumiere AI Engine Production API",
        "status": "Online",
    }
