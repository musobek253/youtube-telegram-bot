import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]

# Gemini AI
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# Database
DATABASE_URL: str = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/telegram_engliz"
)

# Audio
AUDIO_DIR: str = os.getenv("AUDIO_DIR", "bot/audio")

# Scheduling
SEND_HOUR: int = int(os.getenv("SEND_HOUR", "7"))
SEND_MINUTE: int = int(os.getenv("SEND_MINUTE", "0"))
TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Tashkent")

# Words per day
WORDS_PER_DAY: int = 3

# Quiz cycle (days)
QUIZ_CYCLE_DAYS: int = 10
WORDS_PER_CYCLE: int = WORDS_PER_DAY * QUIZ_CYCLE_DAYS   # 30

# Max extra mistake words added to quiz
MAX_MISTAKE_WORDS: int = 5
