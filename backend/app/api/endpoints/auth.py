"""Endpoint Auth sederhana berbasis EMAIL DUMMY.

Permintaan: login pakai email, tapi di belakangnya identitas yang dipakai
seluruh sistem rekomendasi tetap `user_id` integer biasa (UserProfile.id).

- /auth/register : buat UserProfile. Email opsional; bila kosong dibuat
  otomatis dari id -> userN@lumiere.local. Mengembalikan access_token + user_id.
- /auth/login    : cari user via email, kembalikan access_token + user_id.
- /auth/me/{id}  : ambil ringkas profil akun.

Catatan: token bersifat DUMMY (membungkus user_id). Cukup agar frontend punya
access_token + user_id yang konsisten; bukan keamanan tingkat produksi.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models

router = APIRouter()

DUMMY_EMAIL_DOMAIN = "lumiere.local"


def _dummy_email_for(user_id):
    return "user" + str(user_id) + "@" + DUMMY_EMAIL_DOMAIN


def _token_for(user_id):
    # Token dummy: hanya membungkus user_id (bukan JWT bertanda tangan).
    return "lumiere-dummy-" + str(user_id)


def _serialize(user):
    return {
        "user_id": user.id,
        "email": user.email,
        "username": user.username,
        "display_name": user.display_name,
        "user_id_movielens": user.user_id_movielens,
    }


def _auth_response(user):
    payload = {"access_token": _token_for(user.id), "token_type": "bearer"}
    payload.update(_serialize(user))
    return payload


class RegisterRequest(BaseModel):
    email: Optional[str] = None
    display_name: Optional[str] = None
    username: Optional[str] = None
    # Bila ingin memetakan ke user lama MovieLens (1..6040) untuk jalur NCF penuh.
    user_id_movielens: Optional[int] = None


class LoginRequest(BaseModel):
    email: str


def _unique_username(db, desired, current_id):
    taken = (
        db.query(models.UserProfile)
        .filter(models.UserProfile.username == desired, models.UserProfile.id != current_id)
        .first()
    )
    if taken:
        return desired + str(current_id)
    return desired


@router.post("/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    email = (req.email or "").strip().lower() or None

    # Idempoten: kalau email sudah terdaftar, anggap login.
    if email:
        existing = db.query(models.UserProfile).filter(models.UserProfile.email == email).first()
        if existing:
            return _auth_response(existing)

    # Buat user baru. username NOT NULL & unik -> isi setelah dapat id.
    user = models.UserProfile(
        username="__pending__",
        email=email,
        display_name=req.display_name,
        user_id_movielens=req.user_id_movielens,
    )
    db.add(user)
    db.flush()  # dapatkan user.id tanpa commit penuh

    if email:
        base_username = req.username or email.split("@")[0]
    else:
        base_username = req.username or ("user" + str(user.id))
    user.username = _unique_username(db, base_username, user.id)

    # Email dummy otomatis: di belakangnya tetap user_id biasa.
    if not user.email:
        user.email = _dummy_email_for(user.id)

    db.commit()
    db.refresh(user)
    return _auth_response(user)


@router.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    email = (req.email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email wajib diisi.")
    user = db.query(models.UserProfile).filter(models.UserProfile.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email belum terdaftar. Silakan register dulu.")
    return _auth_response(user)


@router.get("/auth/me/{user_id}")
def me(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.UserProfile).filter(models.UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")
    return {"status": "Success", "user": _serialize(user)}
