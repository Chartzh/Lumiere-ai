"""Endpoint Onboarding (Kontrak utama + alias kompatibilitas).

Kontrak utama:
    POST /api/v1/onboarding
    body: { user_id: int, genres: [str], movie_ids: [int], mood?: str }
    Aturan advisor: minimal 3 genre DAN 5 film.

Alias kompatibilitas (frontend lama):
    POST /api/v1/auth/onboarding
    body: { user_id, favorite_genres: [str], favorite_movie_ids?: [int], mood?: str }

Setelah onboarding tersimpan, satu snapshot selera diseed (source='onboarding')
supaya 'evolusi selera' punya titik awal.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models
from app.core import profile as taste

router = APIRouter()

MIN_GENRES = 3
MIN_MOVIES = 5


class OnboardingRequest(BaseModel):
    user_id: int
    genres: List[str]
    movie_ids: List[int]
    mood: Optional[str] = None


class LegacyOnboardingRequest(BaseModel):
    user_id: int
    favorite_genres: List[str]
    favorite_movie_ids: Optional[List[int]] = None
    mood: Optional[str] = None


def _save_onboarding(db, user_id, genres, movie_ids, mood):
    unique_genres = []
    for g in genres or []:
        g2 = g.strip()
        if g2 and g2 not in unique_genres:
            unique_genres.append(g2)
    unique_movie_ids = list(dict.fromkeys(movie_ids or []))

    if len(unique_genres) < MIN_GENRES:
        raise HTTPException(status_code=400, detail="Pilih minimal " + str(MIN_GENRES) + " genre.")
    if len(unique_movie_ids) < MIN_MOVIES:
        raise HTTPException(status_code=400, detail="Pilih minimal " + str(MIN_MOVIES) + " film.")

    user = db.query(models.UserProfile).filter(models.UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User tidak ditemukan. Buat akun dulu via /api/v1/auth/register.",
        )

    genres_str = ", ".join(unique_genres)
    movies_str = ",".join(str(m) for m in unique_movie_ids)

    pref = (
        db.query(models.OnboardingPreference)
        .filter(models.OnboardingPreference.user_id == user.id)
        .first()
    )
    if pref:
        pref.preferred_genres = genres_str
        pref.preferred_movie_ids = movies_str
        if mood is not None:
            pref.mood = mood
    else:
        pref = models.OnboardingPreference(
            user_id=user.id,
            preferred_genres=genres_str,
            preferred_movie_ids=movies_str,
            mood=mood,
        )
        db.add(pref)
    db.commit()

    # Seed snapshot evolusi selera (maju ke depan). Aman bila gagal.
    try:
        taste.get_or_compute(
            db, user.id, recompute=True, include_credits=False, persist=True, source="onboarding"
        )
    except Exception as e:
        print("=== [ONBOARDING] gagal seed taste snapshot: " + str(e) + " ===")

    return {
        "status": "Success",
        "user_id": user_id,
        "saved_genres": unique_genres,
        "saved_movie_ids": unique_movie_ids,
        "mood": mood,
    }


@router.post("/onboarding")
def submit_onboarding(req: OnboardingRequest, db: Session = Depends(get_db)):
    """Kontrak utama onboarding (genres + movie_ids + mood opsional)."""
    return _save_onboarding(db, req.user_id, req.genres, req.movie_ids, req.mood)


@router.post("/auth/onboarding")
def submit_onboarding_legacy(req: LegacyOnboardingRequest, db: Session = Depends(get_db)):
    """Alias kompatibilitas untuk frontend lama (favorite_genres/favorite_movie_ids)."""
    return _save_onboarding(db, req.user_id, req.favorite_genres, req.favorite_movie_ids or [], req.mood)
