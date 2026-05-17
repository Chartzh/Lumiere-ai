import requests
from fastapi import APIRouter, HTTPException
from app.core.config import settings

router = APIRouter()

@router.get("/test-tmdb/{movie_id}")
def test_fetch_movie(movie_id: int):
    """
    Endpoint manual testing untuk mengambil poster dan sinopsis dari TMDB berdasarkan Movie ID
    """
    # Pastikan API Key tersedia
    if not settings.TMDB_API_KEY:
        raise HTTPException(status_code=500, detail="TMDB API Key belum terkonfigurasi di .env")
        
    # URL resmi TMDB untuk detail film
    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    
    # Parameter untuk request (API Key dan Bahasa)
    params = {
        "api_key": settings.TMDB_API_KEY,
        "language": "id-ID" # Menggunakan bahasa Indonesia untuk sinopsis jika tersedia
    }
    
    try:
        response = requests.get(url, params=params)
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Film tidak ditemukan di TMDB")
        elif response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Gagal terhubung ke TMDB")
            
        data = response.json()
        
        # Ekstrak data poster path dan sinopsis (overview) sesuai kebutuhan proyek
        # Base URL untuk image TMDB standar biasanya menggunakan w500
        poster_path = data.get("poster_path")
        full_poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
        
        return {
            "status": "Success",
            "movie_id": movie_id,
            "title": data.get("title"),
            "synopsis": data.get("overview"),
            "poster_url": full_poster_url
        }
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Koneksi error: {str(e)}")