"""
APScheduler — kundalik 07:00 da so'z jo'natish va quiz tekshirish.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from bot.config import SEND_HOUR, SEND_MINUTE, TIMEZONE, WORDS_PER_DAY
from bot.database import models as db
from bot.services.gemini_service import fetch_daily_words
from bot.services.tts_service import prepare_all_audio_for_word
from bot.services.quiz_service import check_and_trigger_quiz
from bot.utils.formatter import (
    format_daily_header,
    format_daily_word,
    format_daily_footer,
)

logger = logging.getLogger(__name__)


# ─────────────────── So'zlarni tayyorlash (06:55) ──────────────────

async def prepare_daily_words() -> list[dict]:
    """
    Gemini dan so'zlar olib, ovoz yaratib, DB ga saqlaydi.
    Har kuni 06:55 da ishlaydi.
    """
    logger.info("=== Kundalik so'zlarni tayyorlash boshlandi ===")

    words_data = await fetch_daily_words()
    if not words_data:
        logger.error("Gemini dan so'z olib bo'lmadi!")
        return []

    saved_words = []
    for word_data in words_data:
        word_id = await db.save_word(word_data)
        word_data["id"] = word_id

        # Audio fayllarni yaratish (EN + RU)
        audio_paths = await prepare_all_audio_for_word(word_data)

        # DB ga inglizcha so'z audio saqlanadi (asosiy)
        if "word_en" in audio_paths:
            await db.update_word_audio(word_id, audio_paths["word_en"])

        # word_data ga barcha yo'llar saqlanadi
        word_data["audio_paths"] = audio_paths

        saved_words.append(word_data)
        logger.info("So'z saqlandi: '%s' (id=%d)", word_data["english"], word_id)

    logger.info("=== %d ta so'z tayyor ===", len(saved_words))
    return saved_words


# ─────────────────── Yordamchi: ovoz xavfsiz yuborish ──────────────────

async def _send_voice_safe(bot, chat_id: int, file_path: str | None, caption: str) -> None:
    """
    Audio faylni xavfsiz yuboradi.
    file_path None yoki mavjud bo'lmasa — o'tkazib yuboradi.
    """
    from aiogram.types import FSInputFile

    if not file_path:
        return
    try:
        audio_file = FSInputFile(file_path)
        await bot.send_voice(
            chat_id,
            voice=audio_file,
            caption=caption,
            parse_mode="HTML",
        )
    except Exception as err:
        logger.warning("Audio yuborishda xato (chat=%d): %s", chat_id, err)


# ─────────────────── Qayta urinish funksiyasi ──────────────────

async def retry_prepare_and_send(bot) -> None:
    """
    Agar so'z olinmay qolsa, 10 daqiqadan keyin ishga tushadigan funksiya.
    """
    global _scheduler
    logger.info("=== Qayta urinish: So'zlarni tayyorlash va jo'natish ===")
    words = await prepare_daily_words()
    
    if words:
        await send_daily_words(bot)
    else:
        logger.error("Qayta urinishda ham so'z olib bo'lmadi! 10 daqiqadan so'ng yana urinib ko'ramiz.")
        if _scheduler:
            run_date = datetime.now() + timedelta(minutes=10)
            _scheduler.add_job(
                retry_prepare_and_send,
                trigger=DateTrigger(run_date=run_date, timezone=TIMEZONE),
                args=[bot],
                name="Retry prepare and send",
                misfire_grace_time=60,
            )

# ─────────────────── Jo'natish (07:00) ──────────────────

async def send_daily_words(bot) -> None:
    """
    Barcha aktiv foydalanuvchilarga bugungi so'zlarni yuboradi.
    Har kuni 07:00 da ishlaydi.
    """
    logger.info("=== Kundalik xabarlar jo'natish boshlandi ===")

    words = await db.get_latest_words(limit=WORDS_PER_DAY)
    if not words:
        logger.error("Jo'natilajak so'zlar topilmadi, biroq qayta urinish ishga tushishi mumkin.")

    users = await db.get_all_active_users()
    if not users:
        logger.info("Aktiv foydalanuvchilar yo'q, jo'natish to'xtatildi.")
        return

    logger.info("%d ta aktiv foydalanuvchi topildi.", len(users))
    sent_any = False

    if words:
        for user in users:
            try:
                telegram_id = user["telegram_id"]
                user_db_id = user["id"]
                cycle = await db.get_user_current_cycle(user_db_id)

                # Shu siklda foydalanuvchiga jo'natib bo'lingan so'zlarni olamiz
                sent_word_ids = await db.get_user_cycle_words(user_db_id, cycle)
                
                # Faqat jo'natilmagan so'zlarni ajratib olamiz
                words_to_send = [w for w in words if w["id"] not in sent_word_ids]
                
                if not words_to_send:
                    logger.info("User=%d ga barcha so'nggi so'zlar oldin jo'natilgan, o'tkazib yuborilmoqda.", telegram_id)
                    continue

                sent_any = True

                # Header
                await bot.send_message(
                    telegram_id,
                    format_daily_header(),
                    parse_mode="HTML",
                )

                # Har bir so'z
                for i, word in enumerate(words_to_send, start=1):
                    text = format_daily_word(word, i, len(words_to_send))
                    await bot.send_message(telegram_id, text, parse_mode="HTML")

                    paths = word.get("audio_paths", {})

                    # ── So'z ovozi: avval inglizcha, keyin ruscha ──
                    await _send_voice_safe(
                        bot, telegram_id,
                        paths.get("word_en") or word.get("audio_path"),
                        caption=f"🇬🇧 <b>{word['english'].upper()}</b> — inglizcha talaffuz",
                    )
                    await _send_voice_safe(
                        bot, telegram_id,
                        paths.get("word_ru"),
                        caption=f"🇷🇺 <b>{word['russian']}</b> — ruscha talaffuz",
                    )

                    # ── 1-gap ovozi: avval inglizcha, keyin ruscha ──
                    await _send_voice_safe(
                        bot, telegram_id,
                        paths.get("sentence_1_en"),
                        caption=f"🇬🇧 1️⃣ <i>{word['sentence_en_1']}</i>",
                    )
                    await _send_voice_safe(
                        bot, telegram_id,
                        paths.get("sentence_1_ru"),
                        caption=f"🇷🇺 1️⃣ <i>{word['sentence_ru_1']}</i>",
                    )

                    # ── 2-gap ovozi: avval inglizcha, keyin ruscha ──
                    await _send_voice_safe(
                        bot, telegram_id,
                        paths.get("sentence_2_en"),
                        caption=f"🇬🇧 2️⃣ <i>{word['sentence_en_2']}</i>",
                    )
                    await _send_voice_safe(
                        bot, telegram_id,
                        paths.get("sentence_2_ru"),
                        caption=f"🇷🇺 2️⃣ <i>{word['sentence_ru_2']}</i>",
                    )

                    # user_words ga belgilash
                    await db.mark_word_sent(user_db_id, word["id"], cycle)

                # Footer
                total_learned = len(await db.get_user_cycle_words(user_db_id, cycle))
                await bot.send_message(
                    telegram_id,
                    format_daily_footer(cycle, total_learned),
                    parse_mode="HTML",
                )

                logger.info("✅ user=%d ga jo'natildi.", telegram_id)

            except Exception as e:
                logger.error("❌ user=%d ga jo'natishda xato: %s", user.get("telegram_id"), e)

    logger.info("=== Jo'natish tugadi ===")

    # Agar hech kimga yangi so'z jo'natilmagan bo'lsa (yoki yangi so'z yo'qligidan), retry qilamiz
    if not sent_any:
        global _scheduler
        logger.error("Hech kimga yangi bugungi so'z jo'natilmadi. Gemini xatosi bo'lishi mumkin. 10 daqiqadan so'ng qayta uriniladi.")
        if _scheduler:
            run_date = datetime.now() + timedelta(minutes=10)
            _scheduler.add_job(
                retry_prepare_and_send,
                trigger=DateTrigger(run_date=run_date, timezone=TIMEZONE),
                args=[bot],
                name="Retry prepare and send (Initial fallback)",
                misfire_grace_time=60,
            )

# ─────────────────── Quiz tekshirish (07:01) ──────────────────

async def check_quiz_triggers(bot) -> None:
    """
    Har bir foydalanuvchi uchun 10 kunlik sikl tugaganini tekshiradi.
    Har kuni 07:01 da ishlaydi.
    """
    logger.info("=== Quiz trigger tekshiruvi boshlandi ===")
    users = await db.get_all_active_users()

    for user in users:
        try:
            await check_and_trigger_quiz(bot, user)
        except Exception as e:
            logger.error(
                "Quiz trigger xatosi (user=%d): %s",
                user.get("telegram_id"), e,
            )

    logger.info("=== Quiz tekshiruvi tugadi ===")


# ─────────────────── Scheduler setup ──────────────────

_scheduler: AsyncIOScheduler | None = None

async def update_schedule(hour: int, minute: int) -> None:
    """Yangi vaqt kiritilganda scheduler'dagi jarayonlarni yangilaydi (reschedule_job)"""
    global _scheduler
    if not _scheduler:
        return
        
    _scheduler.reschedule_job(
        "prepare_words",
        trigger=CronTrigger(hour=hour, minute=max(0, minute - 5), timezone=TIMEZONE)
    )
    _scheduler.reschedule_job(
        "send_words",
        trigger=CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE)
    )
    _scheduler.reschedule_job(
        "check_quiz",
        trigger=CronTrigger(hour=hour, minute=(minute + 1) % 60, timezone=TIMEZONE)
    )
    logger.info("Scheduler vaqti yangilandi: %02d:%02d", hour, minute)


async def setup_scheduler(bot) -> AsyncIOScheduler:
    """
    Scheduler ni sozlab qaytaradi.
    Bot ishga tushganda chaqiriladi.
    """
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    
    # Bazadan oxirgi kiritilgan vaqtni o'qib olish (default: config dagi)
    setting_time = await db.get_setting("send_time")
    hour, minute = SEND_HOUR, SEND_MINUTE
    if setting_time:
        try:
            h_str, m_str = setting_time.split(":")
            hour, minute = int(h_str), int(m_str)
        except ValueError:
            pass

    # 06:55 — Gemini dan so'zlarni olish va tayyor qilish
    _scheduler.add_job(
        prepare_daily_words,
        CronTrigger(hour=hour, minute=max(0, minute - 5), timezone=TIMEZONE),
        id="prepare_words",
        name="Kundalik so'zlar ni tayyorlash",
        max_instances=1,
        coalesce=True,
    )

    # 07:00 — Barcha foydalanuvchilarga yuborish
    _scheduler.add_job(
        send_daily_words,
        CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE),
        args=[bot],
        id="send_words",
        name="Kundalik so'zlarni yuborish",
        max_instances=1,
        coalesce=True,
    )

    # 07:01 — Quiz trigger tekshirish
    _scheduler.add_job(
        check_quiz_triggers,
        CronTrigger(hour=hour, minute=(minute + 1) % 60, timezone=TIMEZONE),
        args=[bot],
        id="check_quiz",
        name="Quiz triggerlarini tekshirish",
        max_instances=1,
        coalesce=True,
    )

    logger.info(
        "Scheduler sozlandi: %02d:%02d (Asia/Tashkent)",
        hour, minute,
    )
    return _scheduler
