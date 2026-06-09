from app.core.recommender.dummy_data import DUMMY_MOVIES

def get_popularity_recommendations(top_k: int):
    """
    Returns a list of the most popular movies from the dummy dataset,
    accompanied by Explainable AI (XAI) justifications.
    """
    # Simply slice the top_k movies from our list to simulate popularity ranking
    selected_movies = DUMMY_MOVIES[:top_k]
    
    recommendations = []
    for movie in selected_movies:
        recommendations.append({
            "movie_id": movie["movie_id"],
            "title": movie["title"],
            "xai_reason": {
                "primary_factor": "Popularity",
                "matched_features": movie["genres"][:2],  # Highlight typical genres for the movie
                "similarity_percentage": 95  # Simulated global popularity match score
            }
        })
    return recommendations
