"""Endpoint Profil Selera + Evolusi Selera.

- GET  /profile/{user_id}            : ringkasan selera (cache bila ada, atau on-the-fly).
- POST /profile/{user_id}/refresh    : paksa hitung ulang + simpan cache & snapshot.
- GET  /profile/{user_id}/evolution  : deret snapshot (evolusi selera).

Flag query:
  - recompute (bool)       : abaikan cache, hitung ulang.
  - include_credits (bool) : sertakan sutradara/aktor favorit via TMDB (lebih lambat).
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core import profile as taste

router = APIRouter()


@router.get("/profile/{user_id}")
def get_profile(
    user_id: int,
    recompute: bool = False,
    include_credits: bool = False,
    db: Session = Depends(get_db),
):
    # Default: tidak menyimpan (murni on-the-fly) kecuali user minta recompute.
    result = taste.get_or_compute(
        db, user_id, recompute=recompute, include_credits=include_credits, persist=recompute
    )
    if result is None:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")
    return {"status": "Success", "profile": result}


@router.post("/profile/{user_id}/refresh")
def refresh_profile(
    user_id: int,
    include_credits: bool = True,
    db: Session = Depends(get_db),
):
    result = taste.get_or_compute(
        db, user_id, recompute=True, include_credits=include_credits, persist=True, source="recompute"
    )
    if result is None:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")
    return {"status": "Success", "profile": result}


@router.get("/profile/{user_id}/evolution")
def get_evolution(user_id: int, db: Session = Depends(get_db)):
    result = taste.get_evolution(db, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")
    return {"status": "Success", "evolution": result}
