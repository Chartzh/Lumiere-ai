"""Endpoint Interaksi pengguna: favorite, rating, review.

Tiap interaksi:
  1. disimpan (upsert per (user, movie, type)),
  2. memicu recompute profil selera + snapshot evolusi (source="interaction"),
  3. otomatis memengaruhi rekomendasi berikutnya: film favorite / rating>=4
     menjadi seed tambahan content-based (lihat movies._determine_user_state).

Catatan jujur: model NCF pra-latih TIDAK dilatih ulang real-time tiap interaksi;
pembaruan dilakukan via content-based boosting + pengayaan profil selera.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models
from app.core.recommender.catalog import get_movie
from app.core import profile as taste

router = APIRouter()

VALID_TYPES = {"favorite", "rating", "review"}


class InteractionRequest(BaseModel):
    user_id: int
    movie_id: int
    type: str                       # "favorite" | "rating" | "review"
    rating: Optional[int] = None    # 1..5 (wajib utk rating; opsional utk review)
    review: Optional[str] = None    # teks review (wajib utk review)


def _serialize(it):
    return {
        "id": it.id,
        "user_id": it.user_id,
        "movie_id": it.movie_id,
        "type": it.interaction_type,
        "rating": it.rating,
        "review": it.review,
        "created_at": it.created_at.isoformat() + "Z" if it.created_at else None,
        "updated_at": it.updated_at.isoformat() + "Z" if it.updated_at else None,
    }


def _recompute_taste(db, user_id):
    """Recompute profil selera + simpan snapshot evolusi. Aman bila gagal."""
    try:
        taste.get_or_compute(
            db, user_id, recompute=True, include_credits=False,
            persist=True, source="interaction",
        )
    except Exception as e:
        print("=== [INTERACTION] gagal recompute selera: " + str(e) + " ===")


@router.post("/interactions")
def upsert_interaction(req: InteractionRequest, db: Session = Depends(get_db)):
    """Simpan/perbarui interaksi (favorite / rating / review) untuk satu film."""
    itype = (req.type or "").strip().lower()
    if itype not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="type harus salah satu dari: favorite, rating, review.")

    user = db.query(models.UserProfile).filter(models.UserProfile.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan. Register dulu via /api/v1/auth/register.")

    if get_movie(req.movie_id) is None:
        raise HTTPException(status_code=404, detail="Film tidak ditemukan di katalog.")

    if req.rating is not None and (req.rating < 1 or req.rating > 5):
        raise HTTPException(status_code=400, detail="rating harus 1..5.")
    if itype == "rating" and req.rating is None:
        raise HTTPException(status_code=400, detail="rating wajib diisi (1..5) untuk type=rating.")
    if itype == "review" and not (req.review and req.review.strip()):
        raise HTTPException(status_code=400, detail="review (teks) wajib diisi untuk type=review.")

    # Upsert per (user, movie, type).
    it = (
        db.query(models.UserInteraction)
        .filter(
            models.UserInteraction.user_id == user.id,
            models.UserInteraction.movie_id == req.movie_id,
            models.UserInteraction.interaction_type == itype,
        )
        .first()
    )
    if it:
        if req.rating is not None:
            it.rating = req.rating
        if req.review is not None:
            it.review = req.review.strip() or None
    else:
        it = models.UserInteraction(
            user_id=user.id,
            movie_id=req.movie_id,
            interaction_type=itype,
            rating=req.rating,
            review=(req.review.strip() if req.review else None),
        )
        db.add(it)
    db.commit()
    db.refresh(it)

    _recompute_taste(db, user.id)

    return {
        "status": "Success",
        "interaction": _serialize(it),
        "note": "Interaksi tersimpan. Rekomendasi & profil selera akan memperhitungkan film ini.",
    }


@router.delete("/interactions/{interaction_id}")
def delete_interaction(interaction_id: int, db: Session = Depends(get_db)):
    """Hapus satu interaksi (mis. unfavorite). Memicu recompute selera."""
    it = db.query(models.UserInteraction).filter(models.UserInteraction.id == interaction_id).first()
    if not it:
        raise HTTPException(status_code=404, detail="Interaksi tidak ditemukan.")
    user_id = it.user_id
    db.delete(it)
    db.commit()
    _recompute_taste(db, user_id)
    return {"status": "Success", "deleted_id": interaction_id}


@router.get("/users/{user_id}/interactions")
def list_interactions(user_id: int, type: Optional[str] = Query(default=None), db: Session = Depends(get_db)):
    """Daftar interaksi user (opsional difilter ?type=favorite|rating|review)."""
    user = db.query(models.UserProfile).filter(models.UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")
    q = db.query(models.UserInteraction).filter(models.UserInteraction.user_id == user.id)
    if type:
        q = q.filter(models.UserInteraction.interaction_type == type.strip().lower())
    rows = q.order_by(models.UserInteraction.created_at.desc()).all()
    return {
        "status": "Success",
        "user_id": user.id,
        "count": len(rows),
        "interactions": [_serialize(r) for r in rows],
    }
