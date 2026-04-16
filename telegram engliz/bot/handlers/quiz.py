"""
Quiz callback handler — InlineKeyboard tugmalariga javoblar.
Callback format: quiz:{session_id}:{word_id}:{is_correct}
"""
from __future__ import annotations

import json
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.database import models as db
from bot.services.quiz_service import (
    get_next_question,
    load_all_active_words_for_session,
    process_answer,
)
from bot.utils.formatter import (
    format_answer_feedback,
    format_quiz_question,
    format_quiz_result,
)

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("quiz:"))
async def handle_quiz_answer(callback: CallbackQuery) -> None:
    """
    Foydalanuvchi quiz javobini tanlasa ishlaydi.
    Callback data: quiz:{session_id}:{word_id}:{1|0}
    """
    await callback.answer()  # loading indikatorini to'xtatish

    parts = callback.data.split(":")
    if len(parts) != 4:
        return

    _, session_id_str, word_id_str, correct_str = parts
    session_id = int(session_id_str)
    word_id = int(word_id_str)
    is_correct = correct_str == "1"

    # Foydalanuvchini topish
    user_record = await db.get_user(callback.from_user.id)
    if not user_record:
        await callback.message.answer("❌ Foydalanuvchi topilmadi. /start bosing.")
        return

    user_db_id = user_record["id"]

    # Tanlangan so'z ma'lumotini olish
    word = await db.get_word_by_id(word_id)
    if not word:
        return

    # Javobni qayta ishlash
    result_info = await process_answer(session_id, word_id, is_correct, user_db_id)

    # Feedback xabar — tugmalarni olib tashlash
    feedback_text = format_answer_feedback(is_correct, word)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(feedback_text, parse_mode="HTML")

    # Quiz tugaganmi?
    if result_info["finished"]:
        result = result_info["result"]
        if result:
            result_text = format_quiz_result(result)
            await callback.message.answer(result_text, parse_mode="HTML")
        else:
            await callback.message.answer("🎉 <b>Test yakunlandi!</b>", parse_mode="HTML")
        return

    # Keyingi savolni jo'natish
    active_session = await db.get_active_quiz(user_db_id)
    if not active_session:
        return

    next_q = await get_next_question(active_session["id"])
    if not next_q:
        # Barcha savollar tugadi
        await db.complete_quiz_session(session_id)
        final = await db.get_quiz_result(session_id)
        if final:
            await callback.message.answer(
                format_quiz_result(final), parse_mode="HTML"
            )
        return

    all_words = await load_all_active_words_for_session(active_session)
    text, keyboard = await format_quiz_question(next_q, all_words, active_session["id"])
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
