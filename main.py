
import os
import logging
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from pyrogram import Client, filters, enums
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardRemove
import yt_dlp

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# CONFIGURATION
API_ID = 34373587
API_HASH = "b023ab5ca734ae960daa33fcf791230c"
BOT_TOKEN = "8420666514:AAF7h5ZsQZvGRwkWmnOJOXKNHTr7YC8P5KQ"

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# User Data
user_downloads = {} # chat_id -> url
user_languages = {} # chat_id -> 'en' | 'ru' | 'uz'

# Language Strings
LANG_STRINGS = {
    'en': {
        'welcome': "Welcome! Send me a YouTube link.",
        'help': "Send me a link, and I'll download it for you.",
        'about': "I'm a YouTube Downloader Bot.",
        'help_btn': "Help",
        'about_btn': "About Us",
        'settings_btn': "Settings / Language",
        'send_link': "Please send a YouTube link.",
        'format_select': "Select format:",
        'downloading': "Downloading...",
        'uploading': "Uploading...",
        'downloaded': "Downloaded. Sending...",
        'audio_sent': "Audio sent!",
        'video_sent': "Video sent!",
        'error': "Error: {}",
        'link_not_found': "Link not found. Please send again.",
        'select_lang': "Please select your language:",
        'lang_set': "Language set to English 🇺🇸",
        'format_audio': "🎵 Audio (MP3)",
        'format_360': "📹 360p",
        'format_720': "📹 720p",
        'format_best': "⭐️ Best",
        'file_toolarge': "File too large!",
    },
    'ru': {
        'welcome': "Добро пожаловать! Отправьте мне ссылку на YouTube.",
        'help': "Отправьте ссылку, и я скачаю видео для вас.",
        'about': "Я бот для скачивания с YouTube.",
        'help_btn': "Помощь",
        'about_btn': "О нас",
        'settings_btn': "Настройки / Язык",
        'send_link': "Пожалуйста, отправьте ссылку на YouTube.",
        'format_select': "Выберите формат:",
        'downloading': "Скачивание...",
        'uploading': "Загрузка...",
        'downloaded': "Скачано. Отправляю...",
        'audio_sent': "Аудио отправлено!",
        'video_sent': "Видео отправлено!",
        'error': "Ошибка: {}",
        'link_not_found': "Ссылка не найдена. Отправьте снова.",
        'select_lang': "Пожалуйста, выберите язык:",
        'lang_set': "Язык установлен на Русский 🇷🇺",
        'format_audio': "🎵 Аудио (MP3)",
        'format_360': "📹 360p",
        'format_720': "📹 720p",
        'format_best': "⭐️ Лучшее",
        'file_toolarge': "Файл слишком большой!",
    },
    'uz': {
        'welcome': "Assalomu alaykum! YouTube linkini yuboring.",
        'help': "Menga link yuboring va men yuklab beraman.",
        'about': "Men YouTube Downloader botman.",
        'help_btn': "Yordam",
        'about_btn': "Biz haqimizda",
        'settings_btn': "Sozlamalar / Til",
        'send_link': "Iltimos, YouTube havolasini yuboring.",
        'format_select': "Formatni tanlang:",
        'downloading': "Yuklanmoqda...",
        'uploading': "Jo'natilmoqda...",
        'downloaded': "Yuklab bo'lindi. Jo'natilmoqda...",
        'audio_sent': "Audio yuklandi!",
        'video_sent': "Video yuklandi!",
        'error': "Xatolik: {}",
        'link_not_found': "Havola topilmadi. Qaytadan yuboring.",
        'select_lang': "Iltimos, tilingizni tanlang:",
        'lang_set': "Til O'zbekchaga o'zgartirildi 🇺🇿",
        'format_audio': "🎵 Audio (MP3)",
        'format_360': "📹 360p",
        'format_720': "📹 720p",
        'format_best': "⭐️ Eng yaxshi",
        'file_toolarge': "Fayl juda katta!",
    }
}

def get_string(chat_id, key):
    lang = user_languages.get(chat_id, 'en')
    return LANG_STRINGS[lang].get(key, key)

def get_main_keyboard(chat_id):
    lang = user_languages.get(chat_id, 'en')
    buttons = [
        [KeyboardButton(LANG_STRINGS[lang]['help_btn']), KeyboardButton(LANG_STRINGS[lang]['about_btn'])],
        [KeyboardButton(LANG_STRINGS[lang]['settings_btn'])]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_progress_bar_string(current, total, length=10):
    completed = int(current * length / total)
    remainder = length - completed
    progress_bar = "■" * completed + "□" * remainder
    percent = int(current * 100 / total)
    return f"[{progress_bar}] {percent}%"

def get_size_string(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

@app.on_message(filters.command("start"))
async def start(client, message):
    # Always ask for language on start
    buttons = [
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz")]
    ]
    await message.reply_text(
        "Please select your language / Пожалуйста, выберите язык / Iltimos, tilni tanlang:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex("^lang_"))
async def handle_language(client, callback_query: CallbackQuery):
    lang_code = callback_query.data.split("_")[1]
    user_languages[callback_query.message.chat.id] = lang_code
    
    await callback_query.answer()
    await callback_query.message.delete()
    
    welcome_text = get_string(callback_query.message.chat.id, 'welcome')
    lang_set_text = get_string(callback_query.message.chat.id, 'lang_set')
    
    await client.send_message(
        chat_id=callback_query.message.chat.id,
        text=f"{lang_set_text}\n{welcome_text}",
        reply_markup=get_main_keyboard(callback_query.message.chat.id)
    )

@app.on_message(filters.text)
async def handle_message(client, message):
    chat_id = message.chat.id
    text = message.text
    
    # Check menu buttons
    lang = user_languages.get(chat_id, 'en')
    if text == LANG_STRINGS[lang]['help_btn']:
        await message.reply_text(get_string(chat_id, 'help'))
        return
    elif text == LANG_STRINGS[lang]['about_btn']:
        await message.reply_text(get_string(chat_id, 'about'))
        return
    elif text == LANG_STRINGS[lang]['settings_btn']:
        # Show language selection again
         buttons = [
            [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz")]
        ]
         await message.reply_text(get_string(chat_id, 'select_lang'), reply_markup=InlineKeyboardMarkup(buttons))
         return

    if 'youtube.com' in text or 'youtu.be' in text:
        # Store URL
        user_downloads[chat_id] = text
        
        # Format selection buttons with translated text
        buttons = [
            [
                InlineKeyboardButton(get_string(chat_id, 'format_audio'), callback_data="fmt_audio"),
                InlineKeyboardButton(get_string(chat_id, 'format_360'), callback_data="fmt_360"),
            ],
            [
                InlineKeyboardButton(get_string(chat_id, 'format_720'), callback_data="fmt_720"),
                InlineKeyboardButton(get_string(chat_id, 'format_best'), callback_data="fmt_best"),
            ]
        ]
        await message.reply_text(
            get_string(chat_id, 'format_select'),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await message.reply_text(get_string(chat_id, 'send_link'))

@app.on_callback_query(filters.regex("^fmt_"))
async def handle_format_callback(client, callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    url = user_downloads.get(chat_id)
    
    if not url:
        await callback_query.answer(get_string(chat_id, 'link_not_found'), show_alert=True)
        return

    format_type = callback_query.data
    await callback_query.answer("Wait...")
    await callback_query.message.edit_text(get_string(chat_id, 'downloading'))

    try:
        ydl_opts = {
            'outtmpl': f'%(title)s.%(ext)s',
            'noplaylist': True,
             # Fix for 403 Forbidden
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        }

        # Set format based on selection
        if format_type == "fmt_audio":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            
            # Check for local ffmpeg (development) or use system default (production/docker)
            local_ffmpeg = os.path.join(os.getcwd(), 'ffmpeg')
            if os.path.exists(local_ffmpeg):
                ydl_opts['ffmpeg_location'] = local_ffmpeg
            # else: yt-dlp automatically finds it in PATH
            
        elif format_type == "fmt_360":
            ydl_opts['format'] = 'best[height<=360]'
        elif format_type == "fmt_720":
            ydl_opts['format'] = 'best[height<=720]'
        else: # fmt_best
            ydl_opts['format'] = 'best' 

        # Add progress hook
        last_update_time = [0]
        loop = asyncio.get_running_loop()
        def hook(d):
             download_progress_hook(d, client, chat_id, callback_query.message.id, loop, last_update_time)
        ydl_opts['progress_hooks'] = [hook]

        # Download
        filename = await download_wrapper(url, ydl_opts)
        
        # Determine actual filename if converted to mp3
        if format_type == "fmt_audio":
             base, _ = os.path.splitext(filename)
             mp3_filename = base + ".mp3"
             if os.path.exists(mp3_filename):
                 filename = mp3_filename
        
        await callback_query.message.edit_text(get_string(chat_id, 'downloaded'))
        
        # Send
        is_audio = format_type == "fmt_audio"
        caption = get_string(chat_id, 'audio_sent') if is_audio else get_string(chat_id, 'video_sent')
        
        if is_audio:
            await client.send_audio(
                chat_id=chat_id,
                audio=filename,
                caption=caption,
                progress=progress,
                progress_args=(client, chat_id, callback_query.message.id, get_string(chat_id, 'uploading'))
            )
        else:
            await client.send_video(
                chat_id=chat_id,
                video=filename,
                caption=caption,
                progress=progress,
                progress_args=(client, chat_id, callback_query.message.id, get_string(chat_id, 'uploading'))
            )
        
        # Cleanup
        os.remove(filename)
        await callback_query.message.delete()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await callback_query.message.edit_text(get_string(chat_id, 'error').format(e))

async def download_wrapper(url, opts):
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        filename = await loop.run_in_executor(pool, lambda: run_download(url, opts))
    return filename

def run_download(url, opts):
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# Reuse previous hooks
def download_progress_hook(d, client, chat_id, message_id, loop, last_update_time):
    if d['status'] == 'downloading':
        current_time = time.time()
        if current_time - last_update_time[0] > 3:
            try:
                # Get localized string for "Downloading..."
                # Since we don't have chat_id easily accessible for language lookup inside this static hook wrapper efficiently without passing it down,
                # we'll use a generic "Downloading..." or try to lookup if possible.
                # For simplicity, we use EN or simple text. In a complex app, pass language string.
                # Let's use the dictionary:
                lang = user_languages.get(chat_id, 'en')
                loading_text = LANG_STRINGS[lang]['downloading']
                
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded_bytes = d.get('downloaded_bytes', 0)
                
                if total_bytes:
                    progress_str = get_progress_bar_string(downloaded_bytes, total_bytes)
                    size_str = f"{get_size_string(downloaded_bytes)} / {get_size_string(total_bytes)}"
                    text = f"{loading_text}\n{progress_str}\n{size_str}"
                else:
                    text = f"{loading_text} {d.get('_percent_str', 'N/A')}"
                
                asyncio.run_coroutine_threadsafe(
                    client.edit_message_text(chat_id=chat_id, message_id=message_id, text=text),
                    loop
                )
                last_update_time[0] = current_time
            except Exception:
                pass

last_upload_update_time = 0
async def progress(current, total, client, chat_id, message_id, text_prefix):
    global last_upload_update_time
    current_time = time.time()
    if current_time - last_upload_update_time > 3:
        try:
            progress_str = get_progress_bar_string(current, total)
            size_str = f"{get_size_string(current)} / {get_size_string(total)}"
            text = f"{text_prefix}\n{progress_str}\n{size_str}"
            await client.edit_message_text(chat_id=chat_id, message_id=message_id, text=text)
            last_upload_update_time = current_time
        except Exception:
            pass

if __name__ == '__main__':
    print("Bot ishga tushdi...")
    app.run()
