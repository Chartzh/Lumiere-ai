"""Klien TMDB terpusat (metadata + credits).

Catatan ID-space: movie_id MovieLens BUKAN TMDB id, jadi semua lookup memakai
/search/movie berdasarkan judul (+ tahun) untuk menebak TMDB id, baru ambil credits.

Dipakai oleh:
  - endpoint rekomendasi (poster + sinopsis)  -> fetch_tmdb_metadata
  - profil selera (sutradara/aktor favorit)   -> fetch_tmdb_credits
"""
import time
import requests
from app.core.config import settings

TMDB_BASE = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p/w500"
PROFILE_IMG_BASE = "https://image.tmdb.org/t/p/w185"

CACHE_DURATION_SECONDS = 3600
_META_CACHE = {}
_CREDITS_CACHE = {}
_ID_CACHE = {}


def _api_key():
    return settings.TMDB_API_KEY


def search_tmdb_id(title, year=None):
    """Tebak TMDB id dari judul (+ tahun). Hasil di-cache."""
    cache_key = (title, year)
    cached = _ID_CACHE.get(cache_key)
    now = time.time()
    if cached and (now - cached["ts"] < CACHE_DURATION_SECONDS):
        return cached["data"]

    tmdb_id = None
    try:
        params = {"api_key": _api_key(), "query": title, "language": "en-US"}
        if year:
            params["year"] = year
        resp = requests.get(TMDB_BASE + "/search/movie", params=params, timeout=10)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                tmdb_id = results[0].get("id")
    except Exception as e:
        print("=== [TMDB ID ERROR] " + str(title) + ": " + str(e) + " ===")

    _ID_CACHE[cache_key] = {"ts": now, "data": tmdb_id}
    return tmdb_id


def fetch_tmdb_metadata(movie_id, title, year):
    """Poster + sinopsis (judul TMDB bila ada)."""
    now = time.time()
    cached = _META_CACHE.get(movie_id)
    if cached and (now - cached["ts"] < CACHE_DURATION_SECONDS):
        return cached["data"]

    data = {"title": title, "synopsis": "Detail film tidak tersedia.", "poster_url": None}
    try:
        params = {"api_key": _api_key(), "query": title, "language": "en-US"}
        if year:
            params["year"] = year
        resp = requests.get(TMDB_BASE + "/search/movie", params=params, timeout=10)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                first = results[0]
                poster_path = first.get("poster_path")
                data = {
                    "title": first.get("title") or title,
                    "synopsis": first.get("overview") or "Detail film tidak tersedia.",
                    "poster_url": (IMG_BASE + poster_path) if poster_path else None,
                }
    except Exception as e:
        print("=== [TMDB META ERROR] movie " + str(movie_id) + ": " + str(e) + " ===")

    _META_CACHE[movie_id] = {"ts": now, "data": data}
    return data


def fetch_tmdb_credits(movie_id, title, year, top_cast=3):
    """Ambil sutradara + cast utama satu film.

    Return: {"directors": [..], "cast": [{name, profile_url}], "raw_cast": [name,...]}
    """
    now = time.time()
    cached = _CREDITS_CACHE.get(movie_id)
    if cached and (now - cached["ts"] < CACHE_DURATION_SECONDS):
        return cached["data"]

    data = {"directors": [], "cast": [], "raw_cast": []}
    try:
        tmdb_id = search_tmdb_id(title, year)
        if tmdb_id:
            resp = requests.get(
                TMDB_BASE + "/movie/" + str(tmdb_id) + "/credits",
                params={"api_key": _api_key()},
                timeout=10,
            )
            if resp.status_code == 200:
                payload = resp.json()
                crew = payload.get("crew", [])
                cast = payload.get("cast", [])
                directors = [c.get("name") for c in crew if c.get("job") == "Director" and c.get("name")]
                main_cast = []
                raw_cast = []
                for c in cast[:top_cast]:
                    name = c.get("name")
                    if not name:
                        continue
                    raw_cast.append(name)
                    profile_path = c.get("profile_path")
                    main_cast.append({
                        "name": name,
                        "profile_url": (PROFILE_IMG_BASE + profile_path) if profile_path else None,
                    })
                data = {"directors": directors, "cast": main_cast, "raw_cast": raw_cast}
    except Exception as e:
        print("=== [TMDB CREDITS ERROR] movie " + str(movie_id) + ": " + str(e) + " ===")

    _CREDITS_CACHE[movie_id] = {"ts": now, "data": data}
    return data
