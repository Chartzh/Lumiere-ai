from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class Movie(Base):
    """Katalog film MovieLens 1M (menggantikan DUMMY_MOVIES).
    movie_id = MovieLens ID, identik dengan key pada model_config.json,
    sehingga bisa dijembatani ke index model NCF.
    """
    __tablename__ = "movies"
    movie_id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    genres = Column(Text, nullable=False)            # dipisah pipe, ex: "Action|Sci-Fi"
    rating_count = Column(Integer, default=0)        # popularitas nyata
    avg_rating = Column(Float, default=0.0)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, index=True)
    # user_id eksternal (MovieLens UserID atau sistem auth SvelteKit)
    user_id_movielens = Column(Integer, unique=True, nullable=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    preferences = relationship("OnboardingPreference", back_populates="user", cascade="all, delete-orphan")


class OnboardingPreference(Base):
    __tablename__ = "onboarding_preferences"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    preferred_genres = Column(Text, nullable=False)               # "Action, Sci-Fi, Drama"
    preferred_movie_ids = Column(Text, nullable=True)             # "260,1196,2858" (5 film onboarding)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("UserProfile", back_populates="preferences")
