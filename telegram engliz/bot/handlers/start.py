"""
/start, /help, /mystats, /pause, /resume handlerlar.
ReplyKeyboardMarkup (Menu) bilan qo'shilgan.
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from bot.database import models as db
from bot.utils.formatter import format_user_stats

logger = logging.getLogger(__name__)
router = Router()

# ─────────────────── Menu Keyboard ───────────────────────

menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📊 Statistikam"),
            KeyboardButton(text="📖 Yordam")
        ],
        [
            KeyboardButton(text="⏸ To'xtatish"),
            KeyboardButton(text="▶️ Davom ettirish")
        ]
    ],
    resize_keyboard=True,
    is_persistent=True
)

# ─────────────────── /start ───────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user = message.from_user
    name = user.full_name or user.username or "Do'stim"

    is_new = await db.register_user(user.id, name)

    if is_new:
        text = (
            f"👋 Salom, <b>{name}</b>!\n\n"
            "📚 Men sizga <b>har kuni 3 ta yangi inglizcha so'z</b> o'rgataman!\n\n"
            "⏰ <b>Har kuni soat 07:00 da</b> quyidagilarni olasiz:\n"
            "  • 3 ta yangi so'z (tarjimali)\n"
            "  • Har so'z uchun 2 ta gap (tarjimali)\n"
            "  • 🔊 Ovozli talaffuz\n\n"
            "🎯 Har <b>10 kunda</b> o'rganilgan so'zlar bo'yicha <b>test</b> topshirasiz!\n\n"
            "Pastdagi tugmalar orqali botni boshqaring! 🚀"
        )
    else:
        await db.set_user_active(user.id, True)
        text = (
            f"✅ Xush kelibsiz, <b>{name}</b>!\n\n"
            "Siz allaqachon ro'yxatdasiz. Xabarlar davom etadi! 📚"
        )

    await message.answer(text, reply_markup=menu_keyboard, parse_mode="HTML")


# ─────────────────── /help var Yordam ───────────────────────

@router.message(Command("help"))
@router.message(F.text == "📖 Yordam")
async def cmd_help(message: Message) -> None:
    text = (
        "📖 <b>Bot haqida</b>\n\n"
        "Bu bot bolalarga inglizcha so'zlarni o'rgatadi:\n"
        "  📅 Har kuni soat <b>07:00</b> da 3 ta so'z\n"
        "  🔊 Ovozli talaffuz bilan\n"
        "  🧠 Har 10 kunda test\n"
        "  📊 Xatolar keyingi testlarda qaytariladi\n\n"
        "Menyudan foydalanib botni boshqaring 😊"
    )
    await message.answer(text, reply_markup=menu_keyboard, parse_mode="HTML")


# ─────────────────── /mystats va Statistikam ───────────────────────

@router.message(Command("mystats"))
@router.message(F.text == "📊 Statistikam")
async def cmd_mystats(message: Message) -> None:
    stats = await db.get_user_stats(message.from_user.id)
    text = format_user_stats(stats)
    await message.answer(text, reply_markup=menu_keyboard, parse_mode="HTML")


# ─────────────────── /pause va To'xtatish ───────────────────────

@router.message(Command("pause"))
@router.message(F.text == "⏸ To'xtatish")
async def cmd_pause(message: Message) -> None:
    await db.set_user_active(message.from_user.id, False)
    await message.answer(
        "⏸ Xabarlar to'xtatildi.\n"
        "Qayta yoqish uchun <b>▶️ Davom ettirish</b> tugmasini bosing.",
        reply_markup=menu_keyboard,
        parse_mode="HTML",
    )


# ─────────────────── /resume va Davom ettirish ───────────────────────

@router.message(Command("resume"))
@router.message(F.text == "▶️ Davom ettirish")
async def cmd_resume(message: Message) -> None:
    await db.set_user_active(message.from_user.id, True)
    await message.answer(
        "▶️ Xabarlar qayta yoqildi!\n"
        "Ertaga soat 07:00 da yangi so'zlar keladi 📚",
        reply_markup=menu_keyboard,
        parse_mode="HTML",
    )
