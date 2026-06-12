from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class Movie(Base):
    """Katalog film MovieLens 1M (menggantikan DUMMY_MOVIES).
    movie_id = MovieLens ID, identik dengan key pada model_config.json,
    sehingga bisa dijembatani ke index model NCF.
    """
    __tablename__ = "movies"
    movie_id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    genres = Column(Text, nullable=False)            # dipisah pipe, ex: "Action|Sci-Fi"
    rating_count = Column(Integer, default=0)        # popularitas nyata
    avg_rating = Column(Float, default=0.0)


class UserProfile(Base):
    """Profil pengguna Lumiere.

    Auth memakai EMAIL sebagai kredensial publik, namun di belakangnya identitas
    nyata yang dipakai seluruh sistem rekomendasi tetap `id` (integer biasa).
    Jadi: email = label login, `id` = user_id yang dipakai endpoint /recommend, dll.

    Kolom taste_* menyimpan RINGKASAN SELERA (cache) supaya bisa langsung disajikan
    tanpa hitung ulang. Bila kosong, profil dihitung on-the-fly dari history onboarding.
    """
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, index=True)
    # user_id eksternal (MovieLens UserID) -> dipakai untuk NCF user lama (1..6040)
    user_id_movielens = Column(Integer, unique=True, nullable=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    # --- Auth (email dummy) ---
    email = Column(String(255), unique=True, nullable=True, index=True)
    display_name = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=True)   # opsional: auth berpassword (pbkdf2). Kosong = login email-saja.
    # --- Ringkasan selera (cache JSON) ---
    taste_summary = Column(Text, nullable=True)        # JSON string ringkasan selera
    taste_updated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    preferences = relationship("OnboardingPreference", back_populates="user", cascade="all, delete-orphan")
    taste_snapshots = relationship("TasteSnapshot", back_populates="user", cascade="all, delete-orphan")
    interactions = relationship("UserInteraction", back_populates="user", cascade="all, delete-orphan")


class OnboardingPreference(Base):
    __tablename__ = "onboarding_preferences"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    preferred_genres = Column(Text, nullable=False)               # "Action, Sci-Fi, Drama"
    preferred_movie_ids = Column(Text, nullable=True)             # "260,1196,2858" (5 film onboarding)
    mood = Column(String(50), nullable=True)                      # mood opsional saat onboarding
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("UserProfile", back_populates="preferences")


class TasteSnapshot(Base):
    """Snapshot selera pengguna pada satu titik waktu.

    Karena katalog tidak memuat riwayat rating ber-timestamp per pengguna,
    EVOLUSI selera dibangun maju ke depan: tiap kali profil selera dihitung/diperbarui
    (mis. setelah onboarding atau setelah menyukai film baru), satu snapshot disimpan.
    Deret snapshot inilah yang menjadi 'evolusi selera' yang jujur dan dapat diaudit.
    """
    __tablename__ = "taste_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(50), nullable=True)            # "onboarding" | "recompute" | "manual"
    genre_distribution = Column(Text, nullable=True)      # JSON {genre: count}
    dominant_genres = Column(Text, nullable=True)         # "Action, Sci-Fi, Drama"
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    user = relationship("UserProfile", back_populates="taste_snapshots")


class UserInteraction(Base):
    """Interaksi pengguna dengan film: favorite / rating / review.

    Sinyal ini dipakai untuk MEMPERBARUI rekomendasi & profil selera:
      - favorite atau rating >= 4 -> film jadi seed tambahan content-based
        (rekomendasi berikutnya bergeser mengikuti selera terbaru),
      - tiap interaksi memicu recompute profil selera + snapshot evolusi.

    Catatan jujur: model NCF pra-latih TIDAK dilatih ulang real-time tiap
    interaksi; pembaruan via content-based boosting + pengayaan profil selera.
    """
    __tablename__ = "user_interactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    movie_id = Column(Integer, nullable=False, index=True)
    interaction_type = Column(String(20), nullable=False)   # "favorite" | "rating" | "review"
    rating = Column(Integer, nullable=True)                 # 1..5 (untuk rating/review)
    review = Column(Text, nullable=True)                    # teks review (opsional)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("UserProfile", back_populates="interactions")
