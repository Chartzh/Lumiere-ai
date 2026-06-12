"""Layanan profil selera (taste profile) Lumiere.

Karena katalog TIDAK menyimpan riwayat rating ber-timestamp per pengguna,
profil selera dihitung dari sinyal yang tersedia:
  - genre pilihan onboarding (preferred_genres)
  - genre dari 5 film onboarding (preferred_movie_ids) via katalog
  - (opsional) sutradara & aktor favorit via TMDB credits dari film-film itu

Hasilnya bisa:
  - dihitung ON-THE-FLY tiap permintaan (default GET /profile), atau
  - disimpan sebagai cache (UserProfile.taste_summary) + snapshot evolusi
    (TasteSnapshot) supaya 'evolusi selera' terbentuk maju ke depan.
"""
import json
from collections import Counter
from datetime import datetime

from app.db import models
from app.core.recommender.catalog import get_movie


def _load_onboarding(db, user):
    """Ambil sinyal selera terbaru dari onboarding milik user."""
    pref = (
        db.query(models.OnboardingPreference)
        .filter(models.OnboardingPreference.user_id == user.id)
        .order_by(models.OnboardingPreference.created_at.desc())
        .first()
    )
    genres, seed_ids, mood = [], [], None
    if pref:
        if pref.preferred_genres:
            genres = [g.strip() for g in pref.preferred_genres.split(",") if g.strip()]
        if pref.preferred_movie_ids:
            seed_ids = [int(x) for x in pref.preferred_movie_ids.split(",") if x.strip().isdigit()]
        mood = pref.mood
    return genres, seed_ids, mood, pref


def _load_liked_interactions(db, user):
    """movie_id yang disukai (favorite / rating>=4) dari interaksi user."""
    try:
        rows = (
            db.query(models.UserInteraction)
            .filter(models.UserInteraction.user_id == user.id)
            .all()
        )
    except Exception as e:
        print("=== [TASTE] gagal baca interaksi: " + str(e) + " ===")
        return []
    liked = []
    for r in rows:
        if r.interaction_type == "favorite" or ((r.rating or 0) >= 4):
            liked.append(r.movie_id)
    return list(dict.fromkeys(liked))


def _confidence(genre_count, seed_count):
    """Skor keyakinan profil 0..100 dari banyaknya sinyal yang dimiliki user."""
    score = min(100, genre_count * 12 + seed_count * 10)
    if score >= 70:
        level = "Tinggi"
    elif score >= 40:
        level = "Sedang"
    else:
        level = "Rendah"
    return {"score": score, "level": level}


def _favorite_credits(seed_movies, top_n=3):
    """Agregasi sutradara & aktor favorit dari TMDB credits (butuh jaringan).

    Aman: bila TMDB gagal/timeout, kembalikan list kosong tanpa melempar error.
    """
    from app.core.tmdb import fetch_tmdb_credits  # import lokal: hemat saat tak dipakai

    directors = Counter()
    actors = Counter()
    for m in seed_movies:
        try:
            credits = fetch_tmdb_credits(m["movie_id"], m["title"], m.get("year"))
            for d in credits.get("directors", []):
                directors[d] += 1
            for name in credits.get("raw_cast", []):
                actors[name] += 1
        except Exception as e:
            print("=== [TASTE CREDITS] gagal " + str(m.get("movie_id")) + ": " + str(e) + " ===")
    fav_dir = [{"name": n, "count": c} for n, c in directors.most_common(top_n)]
    fav_act = [{"name": n, "count": c} for n, c in actors.most_common(top_n)]
    return fav_dir, fav_act


def compute_taste_profile(db, user, include_credits=False):
    """Hitung ringkasan selera secara on-the-fly dari history onboarding."""
    genres, seed_ids, mood, pref = _load_onboarding(db, user)
    liked_ids = _load_liked_interactions(db, user)
    all_seed_ids = list(dict.fromkeys(list(seed_ids) + liked_ids))

    genre_counter = Counter()
    for g in genres:
        genre_counter[g] += 1

    decade_counter = Counter()
    seed_movies = []
    for mid in all_seed_ids:
        m = get_movie(mid)
        if not m:
            continue
        seed_movies.append(m)
        for g in m["genres"]:
            genre_counter[g] += 1
        if m.get("year"):
            decade = (int(m["year"]) // 10) * 10
            decade_counter[str(decade) + "s"] += 1

    dominant = [g for g, _ in genre_counter.most_common(5)]

    fav_dir, fav_act = ([], [])
    if include_credits and seed_movies:
        fav_dir, fav_act = _favorite_credits(seed_movies)

    profile = {
        "user_id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "onboarded": pref is not None,
        "dominant_genres": dominant,
        "genre_distribution": dict(genre_counter),
        "decade_distribution": dict(decade_counter),
        "favorite_mood": mood,
        "favorite_directors": fav_dir,
        "favorite_actors": fav_act,
        "stats": {
            "distinct_genres": len([g for g in genre_counter if genre_counter[g] > 0]),
            "onboarding_genre_count": len(genres),
            "seed_movie_count": len(seed_movies),
            "interaction_liked_count": len(liked_ids),
        },
        "confidence": _confidence(len(genres), len(seed_movies)),
        "computed_at": datetime.utcnow().isoformat() + "Z",
        "data_note": (
            "Profil dihitung dari preferensi onboarding (genre + film favorit). "
            "Katalog tidak memuat riwayat tontonan ber-timestamp, sehingga sutradara/"
            "aktor favorit berasal dari film onboarding via TMDB credits."
        ),
    }
    return profile


def save_snapshot(db, user, profile, source="recompute"):
    """Simpan cache ringkasan ke UserProfile + 1 baris TasteSnapshot (evolusi)."""
    now = datetime.utcnow()
    user.taste_summary = json.dumps(profile, ensure_ascii=False)
    user.taste_updated_at = now

    snap = models.TasteSnapshot(
        user_id=user.id,
        source=source,
        genre_distribution=json.dumps(profile.get("genre_distribution", {}), ensure_ascii=False),
        dominant_genres=", ".join(profile.get("dominant_genres", [])),
    )
    db.add(snap)
    db.commit()
    return snap


def get_or_compute(db, user_id, recompute=False, include_credits=False, persist=True, source="recompute"):
    """Sajikan ringkasan selera: dari cache bila ada, atau hitung on-the-fly.

    - recompute=False & cache ada -> kembalikan cache (served_from='cache').
    - selain itu -> hitung; bila persist=True simpan cache + snapshot evolusi.
    Kembalikan None bila user tidak ada.
    """
    user = db.query(models.UserProfile).filter(models.UserProfile.id == user_id).first()
    if not user:
        return None

    if not recompute and user.taste_summary:
        try:
            cached = json.loads(user.taste_summary)
            cached["served_from"] = "cache"
            cached["taste_updated_at"] = (
                user.taste_updated_at.isoformat() + "Z" if user.taste_updated_at else None
            )
            return cached
        except Exception:
            pass  # cache rusak -> hitung ulang di bawah

    profile = compute_taste_profile(db, user, include_credits=include_credits)
    if persist:
        try:
            save_snapshot(db, user, profile, source=source)
        except Exception as e:
            db.rollback()
            print("=== [TASTE] gagal simpan snapshot: " + str(e) + " ===")
    profile["served_from"] = "computed"
    return profile


def get_evolution(db, user_id):
    """Deret snapshot selera (evolusi maju ke depan)."""
    user = db.query(models.UserProfile).filter(models.UserProfile.id == user_id).first()
    if not user:
        return None
    snaps = (
        db.query(models.TasteSnapshot)
        .filter(models.TasteSnapshot.user_id == user.id)
        .order_by(models.TasteSnapshot.created_at.asc())
        .all()
    )
    timeline = []
    for s in snaps:
        try:
            dist = json.loads(s.genre_distribution) if s.genre_distribution else {}
        except Exception:
            dist = {}
        timeline.append({
            "snapshot_id": s.id,
            "source": s.source,
            "dominant_genres": [g.strip() for g in (s.dominant_genres or "").split(",") if g.strip()],
            "genre_distribution": dist,
            "created_at": s.created_at.isoformat() + "Z" if s.created_at else None,
        })
    return {
        "user_id": user.id,
        "snapshots": timeline,
        "count": len(timeline),
        "note": (
            "Evolusi dibangun maju: tiap kali profil dihitung ulang (mis. setelah "
            "onboarding atau menyukai film baru) satu snapshot tersimpan. Deret inilah "
            "evolusi selera yang jujur, bukan rekonstruksi histori yang tidak tersedia."
        ),
    }
