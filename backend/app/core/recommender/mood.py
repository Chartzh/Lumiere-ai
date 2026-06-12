"""Mood filter: petakan mood (suasana hati) -> kumpulan genre -> rekomendasi.

Mengandalkan mesin content-based yang sudah ada (cosine genre) sehingga konsisten
dengan jalur onboarding. Tidak butuh model NCF.
"""
from app.core.recommender.content_based import get_content_based_recommendations
from app.core.recommender.genre_based import get_genre_recommendations

# Mood -> genre MovieLens valid. Key di-normalisasi lower-case.
MOOD_GENRE_MAP = {
    "santai":        ["Comedy", "Romance", "Animation"],
    "ringan":        ["Comedy", "Animation", "Children's"],
    "bahagia":       ["Comedy", "Musical", "Romance"],
    "menegangkan":   ["Thriller", "Horror", "Mystery"],
    "menantang":     ["Action", "Adventure", "Sci-Fi"],
    "mengharukan":   ["Drama", "Romance", "War"],
    "penasaran":     ["Mystery", "Crime", "Film-Noir"],
    "nostalgia":     ["Musical", "Western", "Children's"],
    "berpikir":      ["Drama", "Documentary", "Film-Noir"],
    "epik":          ["Adventure", "Fantasy", "War"],
    "romantis":      ["Romance", "Drama", "Comedy"],
    "seram":         ["Horror", "Thriller", "Mystery"],
}


def list_moods():
    """Daftar mood + genre yang dipetakan (untuk dropdown/chips frontend)."""
    return [{"mood": m, "genres": g} for m, g in MOOD_GENRE_MAP.items()]


def genres_for_mood(mood):
    if not mood:
        return []
    return MOOD_GENRE_MAP.get(mood.strip().lower(), [])


def get_mood_recommendations(mood, top_k=15, extra_genres=None):
    """Rekomendasi berdasarkan mood.

    extra_genres: opsional, genre tambahan dari preferensi user untuk mempersempit.
    Return: (recommendations, genres_used)
    """
    genres = genres_for_mood(mood)
    if extra_genres:
        for g in extra_genres:
            if g and g not in genres:
                genres.append(g)

    if not genres:
        return [], []

    recs = get_content_based_recommendations(user_genres=genres, top_k=top_k)
    # Fallback: bila content-based kosong (mis. katalog kecil), pakai genre pertama.
    if not recs:
        recs = get_genre_recommendations(genres[0], top_k=top_k)

    # Tandai primary_factor sebagai Mood untuk transparansi (XAI).
    for r in recs:
        xai = r.get("xai_reason", {})
        xai["primary_factor"] = "Mood Match"
        xai["mood"] = mood
        r["xai_reason"] = xai
    return recs, genres
