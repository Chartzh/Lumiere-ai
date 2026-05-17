from fastapi import FastAPI
from app.core.config import settings
from app.api.endpoints import movies  # 1. Import module movies yang baru
from app.db.session import engine  # 1. Import engine
from app.db import models          # 2. Import models agar terbaca oleh Base

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

@app.get("/")
def read_root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "status": "Online"
    }

# 2. Daftarkan router movies ke dalam aplikasi utama
app.include_router(movies.router, prefix="/api/v1", tags=["Movies Testing"])

# 3. Perintah untuk membuat semua tabel di database jika belum ada
models.Base.metadata.create_create_all=False # (Ketik baris di bawah untuk eksekusi)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

@app.get("/")
def read_root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "status": "Online"
    }

app.include_router(movies.router, prefix="/api/v1", tags=["Movies Testing"])