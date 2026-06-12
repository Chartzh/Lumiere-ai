"""Auto-migrasi ringan untuk kolom/tabel baru.

Tabel di Supabase mungkin sudah lebih dulu ada (dibuat versi sebelumnya).
`ensure_schema()` menambahkan kolom & tabel baru secara idempoten memakai
`ADD COLUMN IF NOT EXISTS` (didukung PostgreSQL/Supabase) sehingga deploy baru
tidak perlu migrasi manual dan tidak error bila kolom sudah ada.

Dipanggil saat startup (lifespan) SETELAH Base.metadata.create_all().
Aman bila DB tidak terjangkau: error ditangkap & di-log, app tetap hidup.
"""
from sqlalchemy import text

# Statement idempoten. Hanya untuk PostgreSQL (Supabase).
_ALTERS = [
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS email VARCHAR(255)",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS display_name VARCHAR(100)",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS taste_summary TEXT",
    "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS taste_updated_at TIMESTAMP",
    "ALTER TABLE onboarding_preferences ADD COLUMN IF NOT EXISTS mood VARCHAR(50)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_user_profiles_email ON user_profiles (email)",
]


def ensure_schema(engine):
    """Jalankan ALTER idempoten. Tidak melempar error ke caller."""
    try:
        with engine.begin() as conn:
            for stmt in _ALTERS:
                try:
                    conn.execute(text(stmt))
                except Exception as e:
                    print(f"=== [MIGRATE] lewati '{stmt[:48]}...': {e} ===")
        print("=== [MIGRATE] ensure_schema selesai ===")
    except Exception as e:
        print(f"=== [MIGRATE] DB tidak terjangkau, lewati migrasi: {e} ===")
