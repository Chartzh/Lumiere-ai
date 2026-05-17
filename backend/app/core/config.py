import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Lumiere Backend API"
    TMDB_API_KEY: str = os.getenv("TMDB_API_KEY")
    TMDB_ACCESS_TOKEN: str = os.getenv("TMDB_ACCESS_TOKEN")
    DATABASE_URL: str = os.getenv("DATABASE_URL")

settings = Settings()