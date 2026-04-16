"""
Quiz (Test) yaratish va boshqarish servisi.
10 kunlik siklda 30 ta so'z bo'yicha InlineKeyboard testlar.
"""
from __future__ import annotations

import json
import logging
import random

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import MAX_MISTAKE_WORDS, WORDS_PER_CYCLE
from bot.database import models as db

logger = logging.getLogger(__name__)

# ─────────────────────── Keyboard yaratish ───────────────────────

async def build_quiz_keyboard(
    word: dict,
    all_words: list[dict],
    session_id: int,
) -> InlineKeyboardMarkup:
    """
    4 tanlovli InlineKeyboard yaratadi.
    To'g'ri javob + 3 ta chalg'ituvchi variantlar.
    """
    correct_answer = word["uzbek"]
    correct_word_id = word["id"]

    # Chalg'ituvchi variantlarni tanlash
    other_words = [w for w in all_words if w["id"] != correct_word_id]
    distractors = random.sample(other_words, min(3, len(other_words)))
    options = [correct_answer] + [w["uzbek"] for w in distractors]
    random.shuffle(options)

    buttons = []
    for option in options:
        is_correct = option == correct_answer
        callback = f"quiz:{session_id}:{correct_word_id}:{'1' if is_correct else '0'}"
        buttons.append(
            [InlineKeyboardButton(text=option, callback_data=callback)]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─────────────────────── Test sessiyasi ───────────────────────

async def start_quiz_for_user(
    user_id: int,
    telegram_id: int,
    cycle: int,
) -> dict | None:
    """
    Foydalanuvchi uchun yangi quiz sessiyasi yaratadi.
    Joriy siklning 30 ta so'zi + oldingi siklning xato so'zlari.
    Qaytaradi: {'session_id': int, 'word': dict, 'total': int, 'index': int}
    """
    # Joriy sikl so'zlari
    word_ids = await db.get_user_cycle_words(user_id, cycle)
    if not word_ids:
        logger.warning("user_id=%d uchun sikl=%d so'zlari topilmadi.", user_id, cycle)
        return None

    # Oldingi sikldan xato so'zlarni qo'shish
    mistake_ids = await db.get_top_mistake_words(user_id, limit=MAX_MISTAKE_WORDS)
    extra_ids = [mid for mid in mistake_ids if mid not in word_ids]
    all_ids = word_ids + extra_ids

    # Tasodifiy tartibda aralashtirish
    random.shuffle(all_ids)

    session_id = await db.create_quiz_session(user_id, cycle, all_ids)
    logger.info(
        "Quiz sessiyasi yaratildi: user_id=%d, session_id=%d, jami=%d savol",
        user_id, session_id, len(all_ids),
    )

    words = await db.get_words_by_ids([all_ids[0]])
    if not words:
        return None

    return {
        "session_id": session_id,
        "word": words[0],
        "total": len(all_ids),
        "index": 0,
    }


async def get_next_question(session_id: int) -> dict | None:
    """
    Joriy sessiyaning keyingi savolini qaytaradi.
    Agar savollar tugasa None qaytaradi.
    """
    session = await db.get_active_quiz(session_id)
    if not session:
        return None

    word_ids: list[int] = json.loads(session["word_ids"])
    current_index: int = session["current_index"]

    if current_index >= len(word_ids):
        return None

    next_word_id = word_ids[current_index]
    words = await db.get_words_by_ids([next_word_id])
    if not words:
        return None

    return {
        "session_id": session_id,
        "word": words[0],
        "total": len(word_ids),
        "index": current_index,
    }


async def process_answer(
    session_id: int,
    word_id: int,
    is_correct: bool,
    user_id: int,
) -> dict:
    """
    Javobni qayta ishlaydi, xato bo'lsa mistake_words ga qo'shadi.
    Qaytaradi: {'is_correct': bool, 'finished': bool, 'result': dict|None}
    """
    await db.save_quiz_answer(session_id, word_id, is_correct)

    if not is_correct:
        await db.add_mistake(user_id, word_id)

    # Sessiya tugaganini tekshirish
    session = await db.get_active_quiz(user_id)
    if session is None:
        return {"is_correct": is_correct, "finished": True, "result": None}

    word_ids: list[int] = json.loads(session["word_ids"])
    current_index: int = session["current_index"]

    if current_index >= len(word_ids):
        await db.complete_quiz_session(session_id)
        result = await db.get_quiz_result(session_id)
        return {"is_correct": is_correct, "finished": True, "result": result}

    return {"is_correct": is_correct, "finished": False, "result": None}


async def load_all_active_words_for_session(session: dict) -> list[dict]:
    """Quiz keyboard uchun barcha so'zlarni yuklaydi."""
    word_ids: list[int] = json.loads(session["word_ids"])
    return await db.get_words_by_ids(word_ids)


# ─────────────────────── Sikl tekshirish ───────────────────────

async def check_and_trigger_quiz(bot, user: dict) -> None:
    """
    Foydalanuvchi uchun 10 kunlik sikl tugaganini tekshiradi.
    Agar tugagan bo'lsa quiz boshlaydi.
    """
    from bot.utils.formatter import format_quiz_question

    user_id = user["id"]
    telegram_id = user["telegram_id"]

    cycle = await db.get_user_current_cycle(user_id)
    word_ids = await db.get_user_cycle_words(user_id, cycle)

    if len(word_ids) < WORDS_PER_CYCLE:
        return  # Sikl hali tugamagan

    # Aktiv quiz bor-yo'qligini tekshirish
    active = await db.get_active_quiz(user_id)
    if active:
        return  # Quiz hali davom etmoqda

    logger.info("user_id=%d uchun sikl=%d tugadi, quiz boshlanmoqda.", user_id, cycle)

    quiz_data = await start_quiz_for_user(user_id, telegram_id, cycle)
    if not quiz_data:
        return

    session = await db.get_active_quiz(user_id)
    if not session:
        return

    all_words = await load_all_active_words_for_session(session)
    text, keyboard = await format_quiz_question(quiz_data, all_words, session["id"])

    await bot.send_message(
        telegram_id,
        "🎯 <b>10 kunlik test vaqti!</b>\n"
        f"Jami <b>{quiz_data['total']}</b> ta savol. Boshlaylik!\n\n" + text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
