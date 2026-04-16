"""
DB CRUD operatsiyalar — so'zlar, foydalanuvchilar, quiz va xatolar (PostgreSQL uchun).
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from bot.database.db import get_db

# ─────────────────────────── WORDS ───────────────────────────

async def get_all_english_words() -> list[str]:
    """Bazadagi barcha inglizcha so'zlarni qaytaradi (takrorlanmaslik uchun)."""
    pool = get_db()
    rows = await pool.fetch("SELECT english FROM words")
    return [r["english"] for r in rows]

async def save_word(word_data: dict[str, Any]) -> int:
    """Yangi so'zni bazaga saqlaydi. Agar mavjud bo'lsa, ID ni qaytaradi."""
    sql = """
        INSERT INTO words
            (english, russian, uzbek,
             sentence_en_1, sentence_ru_1, sentence_uz_1,
             sentence_en_2, sentence_ru_2, sentence_uz_2,
             audio_path)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT(english) DO UPDATE SET
            russian      = excluded.russian,
            uzbek        = excluded.uzbek,
            sentence_en_1 = excluded.sentence_en_1,
            sentence_ru_1 = excluded.sentence_ru_1,
            sentence_uz_1 = excluded.sentence_uz_1,
            sentence_en_2 = excluded.sentence_en_2,
            sentence_ru_2 = excluded.sentence_ru_2,
            sentence_uz_2 = excluded.sentence_uz_2
        RETURNING id
    """
    pool = get_db()
    row_id = await pool.fetchval(
        sql,
        word_data["english"],
        word_data["russian"],
        word_data["uzbek"],
        word_data["sentence_en_1"],
        word_data["sentence_ru_1"],
        word_data["sentence_uz_1"],
        word_data["sentence_en_2"],
        word_data["sentence_ru_2"],
        word_data["sentence_uz_2"],
        word_data.get("audio_path")
    )
    return row_id

async def update_word_audio(word_id: int, audio_path: str) -> None:
    pool = get_db()
    await pool.execute(
        "UPDATE words SET audio_path = $1 WHERE id = $2",
        audio_path, word_id
    )

async def get_latest_words(limit: int = 3) -> list[dict]:
    """Eng so'nggi N ta so'zni qaytaradi."""
    pool = get_db()
    rows = await pool.fetch(
        "SELECT * FROM words ORDER BY created_at DESC LIMIT $1", limit
    )
    return [dict(r) for r in rows]

async def get_word_by_id(word_id: int) -> dict | None:
    pool = get_db()
    row = await pool.fetchrow("SELECT * FROM words WHERE id = $1", word_id)
    return dict(row) if row else None

async def get_words_by_ids(word_ids: list[int]) -> list[dict]:
    if not word_ids:
        return []
    pool = get_db()
    # asyncpg expects an array parameter for IN = ANY($1)
    rows = await pool.fetch("SELECT * FROM words WHERE id = ANY($1::int[])", word_ids)
    return [dict(r) for r in rows]

# ─────────────────────────── USERS ───────────────────────────

async def register_user(telegram_id: int, name: str) -> bool:
    """Foydalanuvchini ro'yxatdan o'tkazadi. True — yangi, False — allaqachon bor."""
    pool = get_db()
    existing = await pool.fetchval(
        "SELECT id FROM users WHERE telegram_id = $1", telegram_id
    )
    if existing:
        return False
        
    await pool.execute(
        "INSERT INTO users (telegram_id, name) VALUES ($1, $2)",
        telegram_id, name
    )
    return True

async def get_user(telegram_id: int) -> dict | None:
    pool = get_db()
    row = await pool.fetchrow("SELECT * FROM users WHERE telegram_id = $1", telegram_id)
    return dict(row) if row else None

async def get_all_active_users() -> list[dict]:
    pool = get_db()
    rows = await pool.fetch("SELECT * FROM users WHERE is_active = TRUE")
    return [dict(r) for r in rows]

async def set_user_active(telegram_id: int, active: bool) -> None:
    pool = get_db()
    await pool.execute(
        "UPDATE users SET is_active = $1 WHERE telegram_id = $2",
        active, telegram_id
    )

async def get_user_stats(telegram_id: int) -> dict:
    """Foydalanuvchi statistikasini qaytaradi."""
    pool = get_db()
    row = await pool.fetchrow(
        """
        SELECT
            u.name,
            u.joined_at,
            (SELECT COUNT(*) FROM user_words uw
             JOIN users u2 ON u2.id = uw.user_id
             WHERE u2.telegram_id = $1) AS words_learned,
            (SELECT COUNT(*) FROM quiz_sessions qs
             JOIN users u2 ON u2.id = qs.user_id
             WHERE u2.telegram_id = $1 AND qs.completed_at IS NOT NULL) AS quizzes_done,
            (SELECT COALESCE(SUM(qs.correct_answers), 0) FROM quiz_sessions qs
             JOIN users u2 ON u2.id = qs.user_id
             WHERE u2.telegram_id = $1 AND qs.completed_at IS NOT NULL) AS total_correct,
            (SELECT COALESCE(SUM(qs.total_questions), 0) FROM quiz_sessions qs
             JOIN users u2 ON u2.id = qs.user_id
             WHERE u2.telegram_id = $1 AND qs.completed_at IS NOT NULL) AS total_questions
        FROM users u
        WHERE u.telegram_id = $1
        """,
        telegram_id
    )
    if not row:
        return {}
    
    total_q = row["total_questions"]
    acc = round((row["total_correct"] / total_q) * 100) if total_q > 0 else 0
    return {
        "name": row["name"],
        "joined_at": row["joined_at"],
        "words_learned": row["words_learned"],
        "quizzes_done": row["quizzes_done"],
        "accuracy": acc,
    }

# ─────────────────────────── USER_WORDS ───────────────────────────

async def mark_word_sent(user_id: int, word_id: int, cycle: int) -> None:
    pool = get_db()
    await pool.execute(
        """INSERT INTO user_words (user_id, word_id, cycle_number)
           VALUES ($1, $2, $3)
           ON CONFLICT (user_id, word_id) DO NOTHING""",
        user_id, word_id, cycle
    )

async def get_user_cycle_words(user_id: int, cycle: int) -> list[int]:
    pool = get_db()
    rows = await pool.fetch(
        "SELECT word_id FROM user_words WHERE user_id = $1 AND cycle_number = $2",
        user_id, cycle
    )
    return [r["word_id"] for r in rows]

async def get_user_current_cycle(user_id: int) -> int:
    pool = get_db()
    c = await pool.fetchval(
        "SELECT MAX(cycle_number) FROM user_words WHERE user_id = $1", user_id
    )
    return c or 1

# ─────────────────────────── QUIZ ───────────────────────────

async def create_quiz_session(user_id: int, cycle: int, word_ids: list[int]) -> int:
    pool = get_db()
    session_id = await pool.fetchval(
        """INSERT INTO quiz_sessions
           (user_id, cycle_number, total_questions, word_ids)
           VALUES ($1, $2, $3, $4)
           RETURNING id""",
        user_id, cycle, len(word_ids), json.dumps(word_ids)
    )
    return session_id

async def get_active_quiz(user_id: int) -> dict | None:
    pool = get_db()
    row = await pool.fetchrow(
        """SELECT * FROM quiz_sessions
           WHERE user_id = $1 AND completed_at IS NULL
           ORDER BY started_at DESC LIMIT 1""",
        user_id
    )
    return dict(row) if row else None

async def save_quiz_answer(
    session_id: int, word_id: int, is_correct: bool
) -> None:
    pool = get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO quiz_answers (session_id, word_id, is_correct) VALUES ($1, $2, $3)",
                session_id, word_id, is_correct
            )
            if is_correct:
                await conn.execute(
                    "UPDATE quiz_sessions SET correct_answers = correct_answers + 1 WHERE id = $1",
                    session_id
                )
            await conn.execute(
                "UPDATE quiz_sessions SET current_index = current_index + 1 WHERE id = $1",
                session_id
            )

async def complete_quiz_session(session_id: int) -> None:
    pool = get_db()
    await pool.execute(
        "UPDATE quiz_sessions SET completed_at = CURRENT_TIMESTAMP WHERE id = $1",
        session_id
    )

async def get_quiz_result(session_id: int) -> dict | None:
    pool = get_db()
    row = await pool.fetchrow("SELECT * FROM quiz_sessions WHERE id = $1", session_id)
    return dict(row) if row else None

# ─────────────────────────── MISTAKE WORDS ───────────────────────────

async def add_mistake(user_id: int, word_id: int) -> None:
    pool = get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO mistake_words (user_id, word_id, mistake_count, last_mistake)
            VALUES ($1, $2, 1, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, word_id) DO UPDATE SET
                mistake_count = mistake_words.mistake_count + 1,
                last_mistake = CURRENT_TIMESTAMP
            """,
            user_id, word_id
        )

# ─────────────────── SETTINGS ───────────────────────

async def get_setting(key: str, default: str = None) -> str | None:
    pool = get_db()
    async with pool.acquire() as conn:
        val = await conn.fetchval("SELECT value FROM settings WHERE key = $1", key)
        return val if val is not None else default

async def set_setting(key: str, value: str) -> None:
    pool = get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO settings (key, value) 
            VALUES ($1, $2)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """,
            key, value
        )

async def get_top_mistake_words(user_id: int, limit: int = 5) -> list[int]:
    """Eng ko'p xato qilingan so'z ID larini qaytaradi."""
    pool = get_db()
    rows = await pool.fetch(
        """SELECT word_id FROM mistake_words
           WHERE user_id = $1
           ORDER BY mistake_count DESC, last_mistake DESC
           LIMIT $2""",
        user_id, limit
    )
    return [r["word_id"] for r in rows]
