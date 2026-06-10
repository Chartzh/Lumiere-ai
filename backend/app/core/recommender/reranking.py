import numpy as np
from app.core.recommender.dummy_data import DUMMY_MOVIES

def jaccard_similarity(genres1: list, genres2: list):
    """
    Computes Jaccard Similarity between two sets of genres.
    """
    set1 = set(g.strip().lower() for g in genres1)
    set2 = set(g.strip().lower() for g in genres2)
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    if not union:
        return 0.0
    return len(intersection) / len(union)

def apply_mmr_reranking(raw_ncf_candidates: list, top_k: int, diversity_factor: float = 0.5):
    r"""
    Applies Maximal Marginal Relevance (MMR) algorithm to diversify recommendations.
    
    Formula:
    MMR = ArgMax_{Di in R \ S} [ lambda * Score(Di) - (1 - lambda) * Max_{Dj in S} Similarity(Di, Dj) ]
    
    Parameters:
    - raw_ncf_candidates: list of dicts like [{"movie_id": 550, "score": 0.95, "title": "Fight Club"}]
    - top_k: number of recommendations to return
    - diversity_factor: lambda parameter in MMR (0 to 1, higher values prioritize relevance, lower prioritizes diversity)
    """
    if not raw_ncf_candidates:
        return []
        
    # Map movie_id to genres using DUMMY_MOVIES
    movie_genres_map = {m["movie_id"]: m["genres"] for m in DUMMY_MOVIES}
    
    # Pre-populate genres for candidates
    candidates = []
    for candidate in raw_ncf_candidates:
        c_copy = dict(candidate)
        c_copy["genres"] = movie_genres_map.get(candidate["movie_id"], ["Drama"])  # default fallback genre
        candidates.append(c_copy)
        
    selected = []
    remaining = list(candidates)
    
    # MMR iterative greedy selection
    while len(selected) < top_k and remaining:
        if not selected:
            # First item: select the candidate with the highest relevance score
            best_idx = np.argmax([c["score"] for c in remaining])
            best_candidate = remaining.pop(best_idx)
            selected.append(best_candidate)
        else:
            mmr_scores = []
            for c in remaining:
                c_genres = c["genres"]
                
                # Compute maximum similarity to already selected items
                max_sim = 0.0
                for s in selected:
                    sim = jaccard_similarity(c_genres, s["genres"])
                    if sim > max_sim:
                        max_sim = sim
                        
                # MMR score formula
                mmr_score = diversity_factor * c["score"] - (1 - diversity_factor) * max_sim
                mmr_scores.append(mmr_score)
                
            best_idx = np.argmax(mmr_scores)
            best_candidate = remaining.pop(best_idx)
            selected.append(best_candidate)
            
    # Format recommendation structures with XAI reasons
    recommendations = []
    for movie in selected:
        recommendations.append({
            "movie_id": movie["movie_id"],
            "title": movie.get("title", f"Movie ID {movie['movie_id']}"),
            "xai_reason": {
                "primary_factor": "Collaborative Filtering + Diversification",
                "matched_features": movie["genres"][:2],
                # Map score to percentage (clamped between 0 and 100)
                "similarity_percentage": min(100, max(0, int(movie["score"] * 100)))
            }
        })
        
    return recommendations
