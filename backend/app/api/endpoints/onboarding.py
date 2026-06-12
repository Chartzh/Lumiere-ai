from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db import models

router = APIRouter()

MIN_GENRES = 3
MIN_MOVIES = 5


class OnboardingRequest(BaseModel):
    user_id: int
    genres: List[str]
    movie_ids: List[int]


@router.post("/onboarding")
def submit_onboarding(req: OnboardingRequest, db: Session = Depends(get_db)):
    """Simpan pilihan onboarding user baru. Aturan advisor: minimal 3 genre DAN 5 film."""
    unique_genres = [g.strip() for g in req.genres if g.strip()]
    unique_movie_ids = list(dict.fromkeys(req.movie_ids))

    if len(unique_genres) < MIN_GENRES:
        raise HTTPException(status_code=400, detail=f"Pilih minimal {MIN_GENRES} genre.")
    if len(unique_movie_ids) < MIN_MOVIES:
        raise HTTPException(status_code=400, detail=f"Pilih minimal {MIN_MOVIES} film.")

    user = db.query(models.UserProfile).filter(models.UserProfile.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan. Buat UserProfile dulu.")

    genres_str = ", ".join(unique_genres)
    movies_str = ",".join(str(m) for m in unique_movie_ids)

    pref = db.query(models.OnboardingPreference).filter(
        models.OnboardingPreference.user_id == user.id
    ).first()

    if pref:
        pref.preferred_genres = genres_str
        pref.preferred_movie_ids = movies_str
    else:
        pref = models.OnboardingPreference(
            user_id=user.id, preferred_genres=genres_str, preferred_movie_ids=movies_str
        )
        db.add(pref)

    db.commit()
    return {
        "status": "Success",
        "user_id": req.user_id,
        "saved_genres": unique_genres,
        "saved_movie_ids": unique_movie_ids,
    }
