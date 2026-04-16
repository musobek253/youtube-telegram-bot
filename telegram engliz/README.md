# Telegram Inglizcha O'rgatuvchi Bot

Bolalar uchun mo'ljallangan aqlli Telegram bot. Har kuni 3 ta yangi inglizcha so'z, tarjimalar, gaplar va ovozli talaffuz bilan o'rgatadi.

## Imkoniyatlari

- **Avtomatik so'z yaratish**: Gemini AI yordamida har kuni bazada yo'q bo'lgan 3 ta yangi so'z va ularga mos gaplar generatsiya qilinadi.
- **Ovozli talaffuz**: gTTS yordamida barcha so'zlar va gaplar Telegram Voice xabar ko'rinishida yuboriladi.
- **Kundalik xabarnoma**: APScheduler yordamida barcha foydalanuvchilarga har kuni soat 07:00 da (sozlash mumkin) darslar yetkaziladi.
- **Interval Takrorlash (Spaced Repetition)**: Har 10 kunda, foydalanuvchi o'rgangan 30 ta so'zi asosida interaktiv test (Quiz) topshiradi.
- **Xatolar ustida ishlash**: Testda xato qilingan so'zlar keyingi testlarga avtomatik qo'shiladi.

## Texnologiyalar

- **Python 3.11+**
- **aiogram 3.7.0** (Asinxron Telegram Bot AP)
- **google-generativeai** (Gemini AI)
- **gTTS** (Ovoz generatsiyasi)
- **aiosqlite** (Asinxron SQLite bazasi)
- **APScheduler** (Vaqt bo'yicha vazifalar)

## O'rnatish

1. Repozitoriyni yuklab oling:
   ```bash
   git clone <repo-url>
   cd "telegram engliz"
   ```

2. Virtual muhit yarating va faollashtiring:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\\Scripts\\activate    # Windows
   ```

3. Kutubxonalarni o'rnating:
   ```bash
   pip install -r requirements.txt
   ```

4. `.env` faylini `telegram engliz` papkasida (huddi shu README.md turgan joyda) yarating:
   ```env
   BOT_TOKEN=123456789:ABCdefg_hijklMNOP
   GEMINI_API_KEY=AIzaSyA...
   ADMIN_IDS=123456789,987654321
   DB_PATH=bot/database/words.db
   AUDIO_DIR=bot/audio
   SEND_HOUR=7
   SEND_MINUTE=0
   TIMEZONE=Asia/Tashkent
   ```

5. Botni ishga tushiring:
   ```bash
   python bot/main.py
   ```

## Admin Buyruqlari

Faqat `.env` da ko'rsatilgan `ADMIN_IDS` ishlata oladi:
- `/admin_stats` - Bot statistikasi (userlar, bazadagi jami so'zlar).
- `/admin_prepare` - Soat 07:00 ni kutmasdan, aynan hozir Gemini dan 3 ta so'z olib tayyorlab qo'yadi.
- `/admin_send` - Tayyorlab qo'yilgan so'zlarni hoziroq hammaga tarqatadi.
- `/admin_list` - Oxirgi 10 ta olingan so'zni ro'yxatini ko'rsatadi.
- `/admin_word <so'z>` - Bazada shu so'z bor/yo'qligini tekshiradi (masalan, `/admin_word apple`).
