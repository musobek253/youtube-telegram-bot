"""
Matn formatlash yordamchi funksiyalar.
Telegram HTML parse_mode uchun chiroyli xabarlar.
"""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup

from bot.services.quiz_service import build_quiz_keyboard


# ─────────────────── Kunlik so'z xabari ───────────────────────

def format_daily_word(word: dict, index: int, total: int) -> str:
    """
    Bitta so'z uchun chiroyli Telegram HTML xabar.
    index: 1-dan boshlanadigan tartib raqam.
    """
    return (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📚 <b>So'z {index}/{total}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🇬🇧 <b>{word['english'].upper()}</b>\n"
        f"🇷🇺 {word['russian']}\n"
        f"🇺🇿 {word['uzbek']}\n\n"
        f"📝 <i>Gaplar:</i>\n\n"
        f"  1️⃣ {word['sentence_en_1']}\n"
        f"      🇷🇺 <i>{word['sentence_ru_1']}</i>\n"
        f"      🇺🇿 <i>{word['sentence_uz_1']}</i>\n\n"
        f"  2️⃣ {word['sentence_en_2']}\n"
        f"      🇷🇺 <i>{word['sentence_ru_2']}</i>\n"
        f"      🇺🇿 <i>{word['sentence_uz_2']}</i>\n"
    )


def format_daily_header() -> str:
    return (
        "☀️ <b>Bugungi inglizcha so'zlar!</b>\n"
        "Har kuni 3 ta so'z o'rganib, kelajagingizni yarating! 🚀\n"
    )


def format_daily_footer(cycle: int, total_learned: int) -> str:
    return (
        f"\n✅ <b>Bugungi dars tugadi!</b>\n"
        f"📊 Jami o'rgangan so'zlar: <b>{total_learned}</b> ta\n"
        f"🔄 Sikl: <b>{cycle}</b>\n"
        f"\n💡 <i>Eslab qoling: takrorlash — bilimning onasi!</i>"
    )


# ─────────────────── Quiz savoli ───────────────────────

async def format_quiz_question(
    quiz_data: dict,
    all_words: list[dict],
    session_id: int,
) -> tuple[str, InlineKeyboardMarkup]:
    """
    Quiz savol matni va InlineKeyboard qaytaradi.
    Savol: Inglizcha so'z ko'rsatiladi, o'zbekcha tarjima topish kerak.
    """
    word = quiz_data["word"]
    index = quiz_data["index"] + 1
    total = quiz_data["total"]

    text = (
        f"🧠 <b>Savol {index}/{total}</b>\n\n"
        f"🇬🇧 <b>{word['english'].upper()}</b>\n\n"
        f"<i>O'zbekcha tarjimasini toping:</i>"
    )

    keyboard = await build_quiz_keyboard(word, all_words, session_id)
    return text, keyboard


# ─────────────────── Quiz natija ───────────────────────

def format_quiz_result(result: dict) -> str:
    total = result["total_questions"]
    correct = result["correct_answers"]
    wrong = total - correct
    accuracy = round(correct / total * 100) if total > 0 else 0

    if accuracy >= 90:
        emoji = "🏆"
        grade = "A'lo!"
    elif accuracy >= 70:
        emoji = "⭐"
        grade = "Yaxshi!"
    elif accuracy >= 50:
        emoji = "👍"
        grade = "O'rtacha"
    else:
        emoji = "💪"
        grade = "Ko'proq mashq qiling!"

    feedback = "🎉 Ajoyib natija! Davom eting!" if accuracy >= 80 else "📖 Xato so'zlarni qayta o'rganing!"
    return (
        f"{emoji} <b>Test yakunlandi! {grade}</b>\n\n"
        f"📊 <b>Natijalar:</b>\n"
        f"  ✅ To'g'ri: <b>{correct}</b> ta\n"
        f"  ❌ Xato: <b>{wrong}</b> ta\n"
        f"  📈 Foiz: <b>{accuracy}%</b>\n\n"
        f"{feedback}"
    )


# ─────────────────── Statistika ───────────────────────

def format_user_stats(stats: dict) -> str:
    if not stats:
        return "❌ Statistika topilmadi."

    return (
        f"📊 <b>Sizning statistikangiz</b>\n\n"
        f"👤 Ism: <b>{stats['name']}</b>\n"
        f"📚 O'rganilgan so'zlar: <b>{stats['words_learned']}</b> ta\n"
        f"🎯 Topshirilgan testlar: <b>{stats['quizzes_done']}</b> ta\n"
        f"✅ Aniqlik darajasi: <b>{stats['accuracy']}%</b>\n"
    )


# ─────────────────── Javob feedback ───────────────────────

def format_answer_feedback(is_correct: bool, word: dict) -> str:
    if is_correct:
        return f"✅ <b>To'g'ri!</b>\n🇬🇧 {word['english']} = 🇺🇿 {word['uzbek']}"
    return (
        f"❌ <b>Xato!</b>\n"
        f"🇬🇧 {word['english']}\n"
        f"🇷🇺 {word['russian']}\n"
        f"🇺🇿 {word['uzbek']}\n"
        f"<i>Bu so'zni yodlashga harakat qiling!</i>"
    )
