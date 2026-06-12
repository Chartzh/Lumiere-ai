"""Endpoint Mood Filter.

- GET /moods                     : daftar mood + genre yang dipetakan (untuk chips frontend).
- GET /recommend/mood/{mood}     : rekomendasi sesuai mood (content-based).
    Query: top_k (int), user_id (opsional -> pakai genre onboarding sbg penajam).

Catatan rute: {user_id} pada /recommend/{user_id} bertipe int, jadi tidak
bentrok dengan /recommend/mood/{mood} (3 segmen, segmen kedua 'mood').
"""
from fastapi import APIRouter, Depends
from typing import Optional
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models
from app.core.recommender.mood import list_moods, get_mood_recommendations
from app.api.endpoints.movies import _enrich

router = APIRouter()


@router.get("/moods")
def get_moods():
    return {"status": "Success", "moods": list_moods()}


@router.get("/recommend/mood/{mood}")
def recommend_by_mood(
    mood: str,
    top_k: int = 15,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    extra_genres = None
    if user_id is not None:
        user = db.query(models.UserProfile).filter(models.UserProfile.id == user_id).first()
        if user:
            pref = (
                db.query(models.OnboardingPreference)
                .filter(models.OnboardingPreference.user_id == user.id)
                .first()
            )
            if pref and pref.preferred_genres:
                extra_genres = [g.strip() for g in pref.preferred_genres.split(",") if g.strip()]

    recs, genres_used = get_mood_recommendations(mood, top_k=top_k, extra_genres=extra_genres)
    return {
        "status": "Success",
        "section": "mood:" + mood,
        "engine": "Mood Filter (Content-Based)",
        "mood": mood,
        "genres_used": genres_used,
        "recommendations": _enrich(recs),
    }
