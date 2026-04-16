import os
import asyncpg
from bot.config import DATABASE_URL, AUDIO_DIR

# Global connection pool
POOL: asyncpg.Pool = None

async def init_db() -> None:
    """Ma'lumotlar bazasi hovuzini zaxiralaydi va jadvallarni initsializatsiya qiladi."""
    global POOL
    
    os.makedirs(AUDIO_DIR, exist_ok=True)

    # Ulanish hovuzini (pool) yaratish
    POOL = await asyncpg.create_pool(DATABASE_URL)

    async with POOL.acquire() as conn:
        await conn.execute("""
            -- So'zlar jadvali --
            CREATE TABLE IF NOT EXISTS words (
                id              SERIAL PRIMARY KEY,
                english         TEXT NOT NULL UNIQUE,
                russian         TEXT NOT NULL,
                uzbek           TEXT NOT NULL,
                sentence_en_1   TEXT NOT NULL,
                sentence_ru_1   TEXT NOT NULL,
                sentence_uz_1   TEXT NOT NULL,
                sentence_en_2   TEXT NOT NULL,
                sentence_ru_2   TEXT NOT NULL,
                sentence_uz_2   TEXT NOT NULL,
                audio_path      TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Foydalanuvchilar --
            CREATE TABLE IF NOT EXISTS users (
                id          SERIAL PRIMARY KEY,
                telegram_id BIGINT NOT NULL UNIQUE,
                name        TEXT NOT NULL,
                joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active   BOOLEAN DEFAULT TRUE
            );

            -- Qaysi so'z qaysi foydalanuvchiga yuborilgan --
            CREATE TABLE IF NOT EXISTS user_words (
                id           SERIAL PRIMARY KEY,
                user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                word_id      INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
                sent_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cycle_number INTEGER NOT NULL DEFAULT 1,
                UNIQUE(user_id, word_id)
            );

            -- Test sessiyalari --
            CREATE TABLE IF NOT EXISTS quiz_sessions (
                id              SERIAL PRIMARY KEY,
                user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                cycle_number    INTEGER NOT NULL,
                started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at    TIMESTAMP,
                total_questions INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                current_index   INTEGER DEFAULT 0,
                word_ids        TEXT NOT NULL   -- JSON array of word IDs
            );

            -- Test javoblari --
            CREATE TABLE IF NOT EXISTS quiz_answers (
                id          SERIAL PRIMARY KEY,
                session_id  INTEGER NOT NULL REFERENCES quiz_sessions(id) ON DELETE CASCADE,
                word_id     INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
                is_correct  BOOLEAN NOT NULL,
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Xato qilingan so'zlar --
            CREATE TABLE IF NOT EXISTS mistake_words (
                id           SERIAL PRIMARY KEY,
                user_id      BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                word_id      INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
                mistake_count INTEGER DEFAULT 1,
                last_mistake  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, word_id)
            );
            
            -- Sozlamalar jadvali --
            CREATE TABLE IF NOT EXISTS settings (
                key     TEXT PRIMARY KEY,
                value   TEXT NOT NULL
            );
        """)

def get_db() -> asyncpg.Pool:
    """Hovuz ob'ektini qaytaradi."""
    return POOL

async def close_db() -> None:
    """Hovuzni munosib tarzda yopadi."""
    if POOL:
        await POOL.close()

