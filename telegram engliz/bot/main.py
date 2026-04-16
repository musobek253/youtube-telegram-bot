"""
Bot asosiy ishga tushirish nuqtasi.
"""
from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN
from bot.database.db import init_db
from bot.handlers import admin, quiz, start
from bot.services.scheduler_service import setup_scheduler

# ─────────────────── Logging ───────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ─────────────────── Main ───────────────────────

async def main() -> None:
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN .env faylda topilmadi!")
        sys.exit(1)

    # Ma'lumotlar bazasini initsializatsiya
    logger.info("DB initsializatsiya qilinmoqda...")
    await init_db()
    logger.info("DB tayyor.")

    # Bot va Dispatcher
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Routerlarni qo'shish (tartib muhim)
    dp.include_router(start.router)
    dp.include_router(quiz.router)
    dp.include_router(admin.router)

    # Scheduler
    scheduler = await setup_scheduler(bot)
    scheduler.start()
    logger.info("Scheduler ishga tushdi.")

    # Webhook/polling boshlash
    logger.info("Bot polling boshlandi...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    asyncio.run(main())
