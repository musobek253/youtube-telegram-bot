"""
Gemini API bilan ishlash servisi.
Har kuni 3 ta yangi inglizcha so'z va gap generatsiya qiladi.
"""
from __future__ import annotations

import json
import logging
import re

import google.generativeai as genai

from bot.config import GEMINI_API_KEY, WORDS_PER_DAY
from bot.database.models import get_all_english_words

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-flash-latest")

# ─────────────────────────── Prompt ───────────────────────────

def _build_prompt(existing_words: list[str]) -> str:
    existing_str = ", ".join(existing_words) if existing_words else "yo'q"
    return f"""
Sen bolalar uchun inglizcha o'rgatuvchi assistantsan.

Quyidagi shartlarga rioya qil:
1. Bolalar uchun mos, oddiy {WORDS_PER_DAY} ta inglizcha so'z tanlang (A1-A2 daraja).
2. Bu so'zlarni ISHLATMA (ular allaqachon o'rgatilgan): [{existing_str}]
3. Har bir so'z uchun:
   - Ruscha va O'zbekcha tarjima ber
   - 2 ta ODDIY inglizcha gap tuz (shu so'z bilan)
   - Har bir gapning ruscha va o'zbekcha tarjimasini qo'sh

Javobni faqat JSON formatida qaytar, boshqa hech narsa yozma:
{{
  "words": [
    {{
      "english": "apple",
      "russian": "яблоко",
      "uzbek": "olma",
      "sentences": [
        {{
          "en": "I eat an apple every day.",
          "ru": "Я ем яблоко каждый день.",
          "uz": "Men har kuni olma yeyman."
        }},
        {{
          "en": "She has a red apple.",
          "ru": "У неё есть красное яблоко.",
          "uz": "Uning qizil olmasi bor."
        }}
      ]
    }}
  ]
}}
""".strip()


# ─────────────────────────── Parsing ───────────────────────────

def _parse_response(text: str) -> list[dict] | None:
    """Gemini javobidan JSON ni ajratib oladi."""
    # Markdown code block ni tozalash
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        data = json.loads(text)
        return data.get("words", [])
    except json.JSONDecodeError as e:
        logger.error("JSON parse xatosi: %s\nMatn: %s", e, text[:500])
        return None


def _normalize_word(raw: dict) -> dict | None:
    """Har bir so'z dict ni kerakli formatga keltiradi."""
    try:
        sentences = raw["sentences"]
        return {
            "english":        raw["english"].strip().lower(),
            "russian":        raw["russian"].strip(),
            "uzbek":          raw["uzbek"].strip(),
            "sentence_en_1":  sentences[0]["en"].strip(),
            "sentence_ru_1":  sentences[0]["ru"].strip(),
            "sentence_uz_1":  sentences[0]["uz"].strip(),
            "sentence_en_2":  sentences[1]["en"].strip(),
            "sentence_ru_2":  sentences[1]["ru"].strip(),
            "sentence_uz_2":  sentences[1]["uz"].strip(),
        }
    except (KeyError, IndexError) as e:
        logger.warning("So'z normalizatsiya xatosi: %s | Raw: %s", e, raw)
        return None


# ─────────────────────────── Public API ───────────────────────────

async def fetch_daily_words() -> list[dict]:
    """
    Gemini API dan bugungi 3 ta yangi so'zni oladi.
    Bazadagi mavjud so'zlarni prompt ga qo'shadi.
    Qaytaradi: normalize qilingan word dict lar ro'yxati.
    """
    existing = await get_all_english_words()
    prompt = _build_prompt(existing)

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        logger.info("Gemini so'rov (%d-urinish)...", attempt)
        try:
            response = await _model.generate_content_async(prompt)
            raw_words = _parse_response(response.text)
            if not raw_words:
                logger.warning("Bo'sh javob, qayta urinish...")
                continue

            words = []
            existing_set = set(w.lower() for w in existing)
            for raw in raw_words:
                word = _normalize_word(raw)
                if word and word["english"] not in existing_set:
                    words.append(word)
                    existing_set.add(word["english"])

            if words:
                logger.info("Gemini dan %d ta yangi so'z olindi.", len(words))
                return words

        except Exception as e:
            logger.error("Gemini API xatosi (%d-urinish): %s", attempt, e)

    logger.error("Gemini dan so'z olib bo'lmadi, bo'sh ro'yxat qaytarildi.")
    return []
