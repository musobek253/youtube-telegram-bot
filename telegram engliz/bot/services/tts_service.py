"""
Text-to-Speech servisi.
gTTS yordamida inglizcha va ruscha so'z/gaplarni .ogg formatga o'giradi.
"""
from __future__ import annotations

import asyncio
import logging
import os
from io import BytesIO
from functools import partial

from gtts import gTTS

from bot.config import AUDIO_DIR

logger = logging.getLogger(__name__)


def _generate_audio_sync(text: str, lang: str = "en") -> bytes:
    """Sinxron gTTS chaqiruvi — executor ichida ishlaydi."""
    buf = BytesIO()
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()


async def text_to_ogg(text: str, file_path: str, lang: str = "en") -> str:
    """
    Matnni ovozga aylantiradi va file_path ga .ogg sifatida saqlaydi.
    Qaytaradi: saqlangan fayl yo'li.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    loop = asyncio.get_event_loop()
    mp3_bytes = await loop.run_in_executor(
        None, partial(_generate_audio_sync, text, lang)
    )

    ogg_path = file_path if file_path.endswith(".ogg") else file_path + ".ogg"

    with open(ogg_path, "wb") as f:
        f.write(mp3_bytes)

    logger.debug("Audio saqlandi: %s", ogg_path)
    return ogg_path


# ─────────────── Inglizcha so'z audiolari ───────────────

async def generate_word_audio(word_id: int, english_word: str) -> str:
    """
    Inglizcha so'z uchun audio fayl yaratadi.
    Fayl nomi: audio/{word_id}_en.ogg
    """
    file_path = os.path.join(AUDIO_DIR, f"{word_id}_en.ogg")

    if os.path.exists(file_path):
        logger.debug("Audio allaqachon mavjud: %s", file_path)
        return file_path

    return await text_to_ogg(english_word, file_path, lang="en")


async def generate_sentence_audio(word_id: int, sentence: str, index: int = 1) -> str:
    """
    Inglizcha gap uchun audio fayl yaratadi.
    Fayl nomi: audio/{word_id}_s{index}_en.ogg
    """
    file_path = os.path.join(AUDIO_DIR, f"{word_id}_s{index}_en.ogg")

    if os.path.exists(file_path):
        return file_path

    return await text_to_ogg(sentence, file_path, lang="en")


# ─────────────── Ruscha so'z audiolari ───────────────

async def generate_word_audio_ru(word_id: int, russian_word: str) -> str:
    """
    Ruscha so'z uchun audio fayl yaratadi.
    Fayl nomi: audio/{word_id}_ru.ogg
    """
    file_path = os.path.join(AUDIO_DIR, f"{word_id}_ru.ogg")

    if os.path.exists(file_path):
        logger.debug("RU audio allaqachon mavjud: %s", file_path)
        return file_path

    return await text_to_ogg(russian_word, file_path, lang="ru")


async def generate_sentence_audio_ru(word_id: int, sentence_ru: str, index: int = 1) -> str:
    """
    Ruscha gap uchun audio fayl yaratadi.
    Fayl nomi: audio/{word_id}_s{index}_ru.ogg
    """
    file_path = os.path.join(AUDIO_DIR, f"{word_id}_s{index}_ru.ogg")

    if os.path.exists(file_path):
        return file_path

    return await text_to_ogg(sentence_ru, file_path, lang="ru")


# ─────────────── Barcha audiolarni tayyorlash ───────────────

async def prepare_all_audio_for_word(word: dict) -> dict[str, str]:
    """
    Bir so'z uchun barcha audio fayllarni tayyorlaydi:
      - so'zning inglizcha va ruscha ovozi
      - 2 ta gap (har biri inglizcha va ruscha)
    Qaytaradi:
      {
        'word_en': path, 'word_ru': path,
        'sentence_1_en': path, 'sentence_1_ru': path,
        'sentence_2_en': path, 'sentence_2_ru': path,
      }
    """
    word_id = word["id"]
    paths: dict[str, str] = {}

    try:
        # ── So'z ovozlari ──
        paths["word_en"] = await generate_word_audio(word_id, word["english"])
        paths["word_ru"] = await generate_word_audio_ru(word_id, word["russian"])

        # ── Gap ovozlari ──
        paths["sentence_1_en"] = await generate_sentence_audio(
            word_id, word["sentence_en_1"], index=1
        )
        paths["sentence_1_ru"] = await generate_sentence_audio_ru(
            word_id, word["sentence_ru_1"], index=1
        )
        paths["sentence_2_en"] = await generate_sentence_audio(
            word_id, word["sentence_en_2"], index=2
        )
        paths["sentence_2_ru"] = await generate_sentence_audio_ru(
            word_id, word["sentence_ru_2"], index=2
        )

        logger.info("'%s' so'zi uchun barcha audio tayyor.", word["english"])
    except Exception as e:
        logger.error("Audio yaratish xatosi ('%s'): %s", word.get("english"), e)

    return paths
