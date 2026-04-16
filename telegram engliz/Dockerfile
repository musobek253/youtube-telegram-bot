FROM python:3.11-slim

# Ishchi katalogni yaratish
WORKDIR /app

# Audio formatlash (pydub) uchun ffmpeg o'rnatish kerak bo'ladi
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Kutubxonalarni nusxalash va o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Barcha kodlarni nusxalash
COPY . .

# Botni ishga tushirish
CMD ["python", "-m", "bot.main"]
