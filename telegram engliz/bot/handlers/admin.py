"""
Admin buyruqlari — faqat ADMIN_IDS ga ruxsat beriladi.
/admin_send  — qo'lda so'z jo'natish
/admin_stats — bot statistikasi
/admin_prepare — Gemini dan so'z tayyorlash
"""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message

from bot.config import ADMIN_IDS, WORDS_PER_DAY
from bot.database import models as db
from bot.services.gemini_service import fetch_daily_words
from bot.services.scheduler_service import prepare_daily_words, send_daily_words
from bot.services.tts_service import prepare_all_audio_for_word

logger = logging.getLogger(__name__)
router = Router()


def is_admin(message: Message) -> bool:
    return message.from_user.id in ADMIN_IDS


# ─────────────────── /admin_stats ───────────────────────

@router.message(Command("admin_stats"))
async def cmd_admin_stats(message: Message) -> None:
    if not is_admin(message):
        return

    users = await db.get_all_active_users()
    all_words = await db.get_all_english_words()

    text = (
        "📊 <b>Bot statistikasi</b>\n\n"
        f"👥 Aktiv foydalanuvchilar: <b>{len(users)}</b>\n"
        f"📚 Jami so'zlar bazada: <b>{len(all_words)}</b>\n"
    )
    await message.answer(text, parse_mode="HTML")


# ─────────────────── /admin_prepare ───────────────────────

@router.message(Command("admin_prepare"))
async def cmd_admin_prepare(message: Message) -> None:
    """Qo'lda Gemini dan so'z olish va DB ga saqlash."""
    if not is_admin(message):
        return

    await message.answer("⏳ Gemini dan so'zlar olinmoqda...")
    words = await prepare_daily_words()

    if not words:
        await message.answer("❌ So'z olib bo'lmadi. Log ga qarang.")
        return

    text = f"✅ <b>{len(words)} ta so'z tayyor!</b>\n\n"
    for w in words:
        text += f"• <b>{w['english']}</b> — {w['uzbek']}\n"

    await message.answer(text, parse_mode="HTML")


# ─────────────────── /admin_send ───────────────────────

@router.message(Command("admin_send"))
async def cmd_admin_send(message: Message) -> None:
    """Hozir barcha foydalanuvchilarga so'zlarni qo'lda jo'natish."""
    if not is_admin(message):
        return

    bot = message.bot
    await message.answer("📤 Jo'natish boshlandi...")
    await send_daily_words(bot)
    await message.answer("✅ Jo'natish yakunlandi!")


# ─────────────────── /admin_word ───────────────────────

@router.message(Command("admin_word"))
async def cmd_admin_word(message: Message) -> None:
    """
    /admin_word apple
    Bitta so'zni bazadan tekshirib, fotoida ko'rsatish.
    """
    if not is_admin(message):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Ishlatilishi: /admin_word <inglizcha so'z>")
        return

    word_text = parts[1].strip().lower()
    all_words = await db.get_all_english_words()

    if word_text in [w.lower() for w in all_words]:
        await message.answer(f"✅ <b>{word_text}</b> bazada mavjud.", parse_mode="HTML")
    else:
        await message.answer(f"❌ <b>{word_text}</b> bazada yo'q.", parse_mode="HTML")


# ─────────────────── /admin_list ───────────────────────

@router.message(Command("admin_list"))
async def cmd_admin_list(message: Message) -> None:
    """So'nggi 10 ta so'zni ko'rsatish."""
    if not is_admin(message):
        return

    words = await db.get_latest_words(limit=10)
    if not words:
        await message.answer("Bazada hech qanday so'z yo'q.")
        return

    lines = [f"{i+1}. <b>{w['english']}</b> — {w['uzbek']}" for i, w in enumerate(words)]
    text = "📋 <b>So'nggi 10 ta so'z:</b>\n\n" + "\n".join(lines)
    await message.answer(text, parse_mode="HTML")


# ─────────────────── /set_time ───────────────────────

@router.message(Command("set_time"))
async def cmd_set_time(message: Message) -> None:
    """
    Botning so'z yuborish vaqtini o'zgartiradi.
    Foydalanish: /set_time 07:00
    """
    if not is_admin(message):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Ishlatilishi: <code>/set_time HH:MM</code>\nMasalan: <code>/set_time 07:00</code>", parse_mode="HTML")
        return

    time_str = parts[1].strip()
    try:
        h_str, m_str = time_str.split(":")
        hour = int(h_str)
        minute = int(m_str)
        
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            raise ValueError()
            
    except ValueError:
        await message.answer("❌ Noto'g'ri vaqt formati! Iltimos <code>HH:MM</code> ko'rinishida kiriting.", parse_mode="HTML")
        return

    # Bazaga saqlaymiz
    await db.set_setting("send_time", f"{hour:02d}:{minute:02d}")
    
    # Scheduler ni yangilaymiz
    from bot.services.scheduler_service import update_schedule
    await update_schedule(hour, minute)

    await message.answer(f"✅ Vaqt muvaffaqiyatli <b>{hour:02d}:{minute:02d}</b> ga o'zgartirildi!", parse_mode="HTML")
