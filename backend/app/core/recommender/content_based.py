from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from app.core.recommender.catalog import get_catalog, get_movie


def get_content_based_recommendations(user_genres: list, top_k: int, seed_movie_ids: list = None):
    """
    Content-Based Filtering via Cosine Similarity antara genre pilihan user
    (onboarding) dan tag genre film di katalog (Supabase).

    seed_movie_ids: opsional. ID 5 film yang dipilih user saat onboarding.
    Genre dari film-film ini digabung ke profil minat user.
    """
    catalog = get_catalog()
    user_genres_clean = [g.strip().lower() for g in (user_genres or [])]

    # Gabungkan genre dari film-film seed onboarding (kalau ada)
    if seed_movie_ids:
        for mid in seed_movie_ids:
            movie = get_movie(mid)
            if movie:
                for g in movie["genres"]:
                    gl = g.strip().lower()
                    if gl not in user_genres_clean:
                        user_genres_clean.append(gl)

    if not user_genres_clean:
        return []

    # 1. Vocabulary genre
    all_genres = set()
    for movie in catalog:
        for genre in movie["genres"]:
            all_genres.add(genre.lower())
    all_genres = sorted(list(all_genres))
    genre_index = {g: i for i, g in enumerate(all_genres)}

    # 2. Vektor user
    user_vector = np.zeros(len(all_genres))
    for ug in user_genres_clean:
        if ug in genre_index:
            user_vector[genre_index[ug]] = 1

    if np.sum(user_vector) == 0:
        return []

    # 3. Matriks film
    movie_vectors = np.zeros((len(catalog), len(all_genres)))
    for i, movie in enumerate(catalog):
        for mg in movie["genres"]:
            mgl = mg.lower()
            if mgl in genre_index:
                movie_vectors[i, genre_index[mgl]] = 1

    # 4. Cosine similarity
    similarities = cosine_similarity(user_vector.reshape(1, -1), movie_vectors)[0]
    sorted_indices = np.argsort(similarities)[::-1]

    recommendations = []
    for idx in sorted_indices:
        if len(recommendations) >= top_k:
            break
        movie = catalog[idx]
        score = float(similarities[idx])
        if score <= 0:
            break
        matched = [g for g in movie["genres"] if g.strip().lower() in user_genres_clean]
        recommendations.append({
            "movie_id": movie["movie_id"],
            "title": movie["title"],
            "xai_reason": {
                "primary_factor": "Genre Match",
                "matched_features": matched if matched else [movie["genres"][0]],
                "similarity_percentage": int(score * 100),
            },
        })
    return recommendations
