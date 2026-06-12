from app.core.recommender.catalog import get_catalog


def get_genre_recommendations(genre: str, top_k: int):
    """
    Rekomendasi per-genre yang DI-RANKING (bukan katalog mentah).
    Difilter per genre lalu diurutkan popularitas (katalog sudah terurut
    rating_count DESC).
    """
    target = genre.strip().lower()
    catalog = get_catalog()

    matches = []
    for movie in catalog:
        if target in [g.strip().lower() for g in movie["genres"]]:
            matches.append(movie)

    recommendations = []
    for movie in matches[:top_k]:
        avg = movie.get("avg_rating", 0.0) or 0.0
        recommendations.append({
            "movie_id": movie["movie_id"],
            "title": movie["title"],
            "xai_reason": {
                "primary_factor": "Genre Browse (Ranked)",
                "matched_features": [genre],
                "similarity_percentage": min(99, int(avg / 5.0 * 100)),
            },
        })
    return recommendations
