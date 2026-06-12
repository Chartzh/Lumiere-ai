"""
Katalog film berbasis Supabase (menggantikan DUMMY_MOVIES) DENGAN FALLBACK.

Urutan sumber data:
  1. Tabel `movies` di Supabase (utama).
  2. Jika DB gagal/tak terjangkau -> file movies_catalog.json yang dibundel.
  3. Jika dua-duanya gagal -> katalog kosong (API tetap hidup, tidak 500).

Dengan begini, kalau host DB Supabase tidak bisa di-resolve (mis. saat dev
lokal tanpa koneksi DB), endpoint genre/trending/popularity TIDAK lagi
melempar 500 — ia otomatis pakai katalog JSON.

Struktur tiap item:
    {"movie_id": int, "title": str, "year": int|None,
     "genres": [str,...], "rating_count": int, "avg_rating": float}
Terurut rating_count DESC -> indeks awal = film terpopuler.
"""
import os
import json
from sqlalchemy import text

_CATALOG = []
_BY_ID = {}
_LOADED = False
_SOURCE = None  # "supabase" | "json:<path>" | "empty"


def _normalize_genres(value):
    if isinstance(value, list):
        return [str(g).strip() for g in value if str(g).strip()]
    if isinstance(value, str):
        return [g.strip() for g in value.split("|") if g.strip()]
    return []


def _fallback_paths():
    here = os.path.dirname(os.path.abspath(__file__))
    env = os.environ.get("LUMIERE_CATALOG_JSON")
    candidates = []
    if env:
        candidates.append(env)
    candidates += [
        os.path.join(here, "movies_catalog.json"),                  # di samping catalog.py
        "movies_catalog.json",                                        # cwd (root backend)
        "/app/movies_catalog.json",                                   # root container
        os.path.join(here, "..", "..", "..", "movies_catalog.json"),  # root project
    ]
    return candidates


def _load_from_db():
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        rows = db.execute(text(
            "SELECT movie_id, title, year, genres, rating_count, avg_rating "
            "FROM movies ORDER BY rating_count DESC"
        )).fetchall()
        catalog = []
        for r in rows:
            catalog.append({
                "movie_id": int(r[0]),
                "title": r[1],
                "year": int(r[2]) if r[2] is not None else None,
                "genres": _normalize_genres(r[3]),
                "rating_count": int(r[4] or 0),
                "avg_rating": float(r[5] or 0.0),
            })
        return catalog
    finally:
        db.close()


def _load_from_json():
    for path in _fallback_paths():
        try:
            if path and os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                catalog = []
                for c in data:
                    catalog.append({
                        "movie_id": int(c["movie_id"]),
                        "title": c.get("title"),
                        "year": int(c["year"]) if c.get("year") is not None else None,
                        "genres": _normalize_genres(c.get("genres")),
                        "rating_count": int(c.get("rating_count") or 0),
                        "avg_rating": float(c.get("avg_rating") or 0.0),
                    })
                catalog.sort(key=lambda m: m["rating_count"], reverse=True)
                return catalog, path
        except Exception as e:
            print(f"=== [CATALOG] Gagal baca {path}: {e} ===")
    return None, None


def _load():
    global _CATALOG, _BY_ID, _LOADED, _SOURCE
    catalog = None
    try:
        catalog = _load_from_db()
        _SOURCE = "supabase"
        print(f"=== [CATALOG] Dimuat {len(catalog)} film dari Supabase ===")
    except Exception as e:
        print(f"=== [CATALOG] DB tidak terjangkau ({e}); fallback ke movies_catalog.json ===")
        catalog, path = _load_from_json()
        if catalog is None:
            print("=== [CATALOG] Fallback JSON TIDAK ditemukan; katalog kosong ===")
            catalog = []
            _SOURCE = "empty"
        else:
            _SOURCE = "json:" + path
            print(f"=== [CATALOG] Dimuat {len(catalog)} film dari {path} (fallback) ===")

    _CATALOG = catalog
    _BY_ID = {m["movie_id"]: m for m in catalog}
    _LOADED = True


def get_catalog():
    """List film terurut popularitas. Lazy-load saat pertama dipanggil."""
    if not _LOADED:
        _load()
    return _CATALOG


def get_movie(movie_id):
    if not _LOADED:
        _load()
    return _BY_ID.get(int(movie_id))


def get_source():
    """Info sumber katalog aktif (untuk debugging / endpoint health)."""
    return _SOURCE


def warm_cache():
    """Dipanggil saat startup app agar request pertama tidak lambat.
    Tidak melempar error kalau DB down — otomatis pakai fallback JSON."""
    try:
        _load()
    except Exception as e:
        print(f"=== [CATALOG] warm_cache gagal total: {e} ===")
