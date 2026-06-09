from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Membuat engine koneksi
engine = create_engine(settings.DATABASE_URL)

# Membuat session factory untuk berinteraksi dengan DB
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class untuk membuat model/skema tabel
Base = declarative_base()

# Dependency untuk mendapatkan instance DB di endpoint FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()