from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from app.core.recommender.dummy_data import DUMMY_MOVIES

def get_content_based_recommendations(user_genres: list, top_k: int):
    """
    Computes recommendations using Cosine Similarity between user-selected onboarding genres
    and the dummy dataset's movie genre tags.
    """
    if not user_genres:
        return []
        
    # Standardize user genres casing and strip spaces
    user_genres_clean = [g.strip().lower() for g in user_genres]
    
    # 1. Collect all unique genres to construct binary vectors
    all_genres = set()
    for movie in DUMMY_MOVIES:
        for genre in movie["genres"]:
            all_genres.add(genre.lower())
    all_genres = sorted(list(all_genres))
    
    # 2. Build user preference vector
    user_vector = np.zeros(len(all_genres))
    for ug in user_genres_clean:
        if ug in all_genres:
            user_vector[all_genres.index(ug)] = 1
            
    # 3. Build movie profiles matrix
    movie_vectors = []
    for movie in DUMMY_MOVIES:
        movie_vector = np.zeros(len(all_genres))
        for mg in movie["genres"]:
            mg_lower = mg.lower()
            if mg_lower in all_genres:
                movie_vector[all_genres.index(mg_lower)] = 1
        movie_vectors.append(movie_vector)
    movie_vectors = np.array(movie_vectors)
    
    # If the user vector is all zeros (no matching genres in database), return fallback
    if np.sum(user_vector) == 0:
        # Avoid division by zero, return empty or default list
        return []
        
    # 4. Compute Cosine Similarity
    user_vector_2d = user_vector.reshape(1, -1)
    similarities = cosine_similarity(user_vector_2d, movie_vectors)[0]
    
    # 5. Retrieve indices sorted by similarity score in descending order
    sorted_indices = np.argsort(similarities)[::-1]
    
    recommendations = []
    for idx in sorted_indices:
        if len(recommendations) >= top_k:
            break
            
        movie = DUMMY_MOVIES[idx]
        score = float(similarities[idx])
        
        # Identify features (genres) that matched between user and movie
        matched = [g for g in movie["genres"] if g.strip().lower() in user_genres_clean]
        
        # Create XAI justification block
        xai_reason = {
            "primary_factor": "Genre Match",
            "matched_features": matched if matched else [movie["genres"][0]],
            "similarity_percentage": int(score * 100)
        }
        
        recommendations.append({
            "movie_id": movie["movie_id"],
            "title": movie["title"],
            "xai_reason": xai_reason
        })
        
    return recommendations
