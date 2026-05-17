from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    # user_id eksternal (misal dari dataset MovieLens atau sistem auth SvelteKit)
    user_id_movielens = Column(Integer, unique=True, nullable=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relasi one-to-many ke preferensi onboarding
    preferences = relationship("OnboardingPreference", back_populates="user", cascade="all, delete-orphan")


class OnboardingPreference(Base):
    __tablename__ = "onboarding_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    
    # Menyimpan daftar genre pilihan (misal didapat dari onboarding di frontend)
    # Disimpan dalam bentuk string teks yang dipisahkan koma (ex: "Action, Sci-Fi, Drama")
    preferred_genres = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relasi balik ke UserProfile
    user = relationship("UserProfile", back_populates="preferences")