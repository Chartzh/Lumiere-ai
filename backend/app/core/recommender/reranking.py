import numpy as np
from app.core.recommender.catalog import get_catalog


def jaccard_similarity(genres1: list, genres2: list):
    """Jaccard Similarity antara dua himpunan genre."""
    set1 = set(g.strip().lower() for g in genres1)
    set2 = set(g.strip().lower() for g in genres2)
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    if not union:
        return 0.0
    return len(intersection) / len(union)


def apply_mmr_reranking(raw_ncf_candidates: list, top_k: int, diversity_factor: float = 0.5):
    r"""
    Maximal Marginal Relevance (MMR) untuk diversifikasi rekomendasi.
    MMR = ArgMax [ lambda * Score(Di) - (1 - lambda) * Max Similarity(Di, Dj in S) ]
    diversity_factor (lambda): makin tinggi = makin relevan; makin rendah = makin beragam.
    """
    if not raw_ncf_candidates:
        return []

    movie_genres_map = {m["movie_id"]: m["genres"] for m in get_catalog()}

    candidates = []
    for candidate in raw_ncf_candidates:
        c_copy = dict(candidate)
        c_copy["genres"] = movie_genres_map.get(candidate["movie_id"], ["Drama"])
        candidates.append(c_copy)

    selected = []
    remaining = list(candidates)

    while len(selected) < top_k and remaining:
        if not selected:
            best_idx = int(np.argmax([c["score"] for c in remaining]))
            selected.append(remaining.pop(best_idx))
        else:
            mmr_scores = []
            for c in remaining:
                max_sim = 0.0
                for s in selected:
                    sim = jaccard_similarity(c["genres"], s["genres"])
                    if sim > max_sim:
                        max_sim = sim
                mmr_score = diversity_factor * c["score"] - (1 - diversity_factor) * max_sim
                mmr_scores.append(mmr_score)
            best_idx = int(np.argmax(mmr_scores))
            selected.append(remaining.pop(best_idx))

    recommendations = []
    for movie in selected:
        recommendations.append({
            "movie_id": movie["movie_id"],
            "title": movie.get("title", "Movie ID " + str(movie["movie_id"])),
            "xai_reason": {
                "primary_factor": "Collaborative Filtering + Diversification",
                "matched_features": movie["genres"][:2],
                "similarity_percentage": min(100, max(0, int(movie["score"] * 100))),
            },
        })
    return recommendations
