"""
Serendipity / Exploration layer (anti filter-bubble).
Mengambil film bagus (cukup populer) yang SENGAJA beda genre dari selera user,
supaya "kejutan" tetap berkualitas, bukan film acak antah-berantah.
"""
import random
from app.core.recommender.catalog import get_catalog

MIN_RATING_COUNT = 100  # ambang agar film kejutan tetap layak (bukan film super-obscure)


def get_serendipity_recommendations(top_k: int, exclude_ids: list = None, avoid_genres: list = None):
    catalog = get_catalog()
    exclude = set(exclude_ids or [])
    avoid = set(g.strip().lower() for g in (avoid_genres or []))

    pool = []
    for movie in catalog:
        if movie["movie_id"] in exclude:
            continue
        if movie.get("rating_count", 0) < MIN_RATING_COUNT:
            continue
        movie_genres = set(g.strip().lower() for g in movie["genres"])
        overlap = len(movie_genres & avoid)  # makin kecil = makin "mengejutkan"
        pool.append((movie, overlap))

    random.shuffle(pool)
    pool.sort(key=lambda x: x[1])  # prioritaskan paling sedikit irisan genre

    recommendations = []
    for movie, overlap in pool[:top_k]:
        recommendations.append({
            "movie_id": movie["movie_id"],
            "title": movie["title"],
            "xai_reason": {
                "primary_factor": "Serendipity / Exploration",
                "matched_features": movie["genres"][:2],
                "similarity_percentage": 0,
                "note": "Sengaja di luar selera utamamu untuk menghindari filter bubble",
            },
        })
    return recommendations
