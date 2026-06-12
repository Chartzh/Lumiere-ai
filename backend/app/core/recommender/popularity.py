from app.core.recommender.catalog import get_catalog


def get_popularity_recommendations(top_k: int):
    """
    Film terpopuler berdasarkan JUMLAH RATING nyata (ratings.dat), terurut dari
    katalog. similarity_percentage memakai rata-rata rating nyata (metrik asli),
    bukan konstanta.
    """
    catalog = get_catalog()
    selected = catalog[:top_k]  # katalog sudah terurut rating_count DESC

    recommendations = []
    for movie in selected:
        avg = movie.get("avg_rating", 0.0) or 0.0
        recommendations.append({
            "movie_id": movie["movie_id"],
            "title": movie["title"],
            "xai_reason": {
                "primary_factor": "Popularity",
                "matched_features": movie["genres"][:2],
                "similarity_percentage": min(99, int(avg / 5.0 * 100)),
                "rating_count": movie.get("rating_count", 0),
            },
        })
    return recommendations
