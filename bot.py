import os
import logging
import tempfile
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp
from pydub import AudioSegment

# ========== CONFIGURATION ==========
# 🔴 Replace with your NEW bot token
TOKEN = "8866299232:AAH6IUtnTZYw9e8y7daPicXFd-aiMC_JWK0"

# Your channels
CHANNELS = [
    {"name": "Pykillinux", "url": "https://t.me/pykillinux"},
    {"name": "Music Search", "url": "https://t.me/music_search"}
]

# ========== LANGUAGE DICTIONARY ==========
LANG = {
    'fa': {
        'welcome': "🎵 **تبدیل‌کننده و دانلودر صدا**\n\n"
                   "برای استفاده از این ربات، لطفاً ابتدا در کانال‌های زیر عضو شوید:\n\n",
        'join_channels': "• {name}\n",
        'check_btn': "✅ بررسی عضویت",
        'subscribed': "✅ **تبریک! شما در تمام کانال‌ها عضو هستید.**\n\n"
                      "🎵 حالا می‌توانید:\n"
                      "• یک فایل صوتی ارسال کنید تا به MP3 تبدیل شود\n"
                      "• یک لینک یوتیوب ارسال کنید تا دانلود شود\n"
                      "• یک لینک اینستاگرام (ریل) ارسال کنید تا دانلود شود",
        'not_subscribed': "❌ **شما هنوز در تمام کانال‌ها عضو نشده‌اید.**\n\n"
                          "لطفاً روی لینک کانال‌های زیر کلیک کرده و عضو شوید، سپس دوباره روی دکمه **بررسی عضویت** کلیک کنید.",
        'send_prompt': "👋 سلام! لطفاً یک فایل صوتی، لینک یوتیوب یا لینک اینستاگرام ارسال کنید.",
        'converting': "🔄 در حال تبدیل فایل به MP3...",
        'conversion_error': "❌ خطا در تبدیل فایل. لطفاً دوباره تلاش کنید.",
        'youtube_processing': "🔄 در حال دریافت اطلاعات از یوتیوب...",
        'choose_quality': "🎬 **{title}**\n\nکیفیت مورد نظر را انتخاب کنید:",
        'downloading_video': "🔄 در حال دانلود ویدیو با کیفیت {quality}...",
        'downloading_audio': "🔄 در حال دانلود و استخراج MP3...",
        'download_complete': "✅ دانلود کامل شد!",
        'youtube_error': "❌ خطا در دریافت اطلاعات. لطفاً لینک معتبر ارسال کنید.",
        'lang_changed': "🌐 زبان به فارسی تغییر کرد.",
        'lang_btn': "🌐 تغییر زبان",
        'lang_prompt': "زبان خود را انتخاب کنید:",
        'cancel': "❌ عملیات لغو شد.",
        'video_caption': "📹 {title}\nکیفیت: {quality}",
        'audio_caption': "🎵 استخراج شده از یوتیوب",
        'not_allowed': "❌ **دسترسی محدود شده است.**\n\nلطفاً ابتدا در کانال‌های زیر عضو شوید:",
        'help': "برای راهنمایی بیشتر از /start استفاده کنید.",
        'audio_sent': "🎵 فایل MP3 با کیفیت بالا",
        'instagram_processing': "🔄 در حال دریافت اطلاعات از اینستاگرام...",
        'instagram_downloading': "🔄 در حال دانلود ریل اینستاگرام...",
        'instagram_error': "❌ خطا در دریافت اطلاعات. لطفاً لینک معتبر اینستاگرام ارسال کنید.",
        'instagram_caption': "📸 ریل اینستاگرام\n{title}",
        'instagram_audio_caption': "🎵 صدای استخراج شده از ریل اینستاگرام",
    },
    'en': {
        'welcome': "🎵 **Audio Converter & Downloader**\n\n"
                   "To use this bot, please join the following channels first:\n\n",
        'join_channels': "• {name}\n",
        'check_btn': "✅ Check Subscription",
        'subscribed': "✅ **Congratulations! You are subscribed to all channels.**\n\n"
                      "🎵 Now you can:\n"
                      "• Send an audio file to convert to MP3\n"
                      "• Send a YouTube link to download\n"
                      "• Send an Instagram link (Reel) to download",
        'not_subscribed': "❌ **You haven't joined all channels yet.**\n\n"
                          "Please click the channel links below and join, then click the **Check Subscription** button again.",
        'send_prompt': "👋 Hello! Please send an audio file, a YouTube link, or an Instagram link.",
        'converting': "🔄 Converting file to MP3...",
        'conversion_error': "❌ Conversion failed. Please try again.",
        'youtube_processing': "🔄 Fetching video information from YouTube...",
        'choose_quality': "🎬 **{title}**\n\nChoose the quality you want:",
        'downloading_video': "🔄 Downloading video in {quality}...",
        'downloading_audio': "🔄 Downloading and extracting MP3...",
        'download_complete': "✅ Download complete!",
        'youtube_error': "❌ Error fetching information. Please send a valid link.",
        'lang_changed': "🌐 Language changed to English.",
        'lang_btn': "🌐 Change Language",
        'lang_prompt': "Select your language:",
        'cancel': "❌ Operation cancelled.",
        'video_caption': "📹 {title}\nQuality: {quality}",
        'audio_caption': "🎵 Extracted from YouTube",
        'not_allowed': "❌ **Access restricted.**\n\nPlease join the channels below first:",
        'help': "Use /start for more information.",
        'audio_sent': "🎵 High Quality MP3",
        'instagram_processing': "🔄 Fetching information from Instagram...",
        'instagram_downloading': "🔄 Downloading Instagram Reel...",
        'instagram_error': "❌ Error fetching information. Please send a valid Instagram link.",
        'instagram_caption': "📸 Instagram Reel\n{title}",
        'instagram_audio_caption': "🎵 Audio extracted from Instagram Reel",
    }
}

# ========== LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== USER DATA ==========
user_lang = {}  # user_id -> 'fa' or 'en'
user_subscribed = {}  # user_id -> bool (cached)

# ========== SUBSCRIPTION CHECK ==========
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    for channel in CHANNELS:
        try:
            channel_identifier = channel["url"].split("/")[-1]
            member = await context.bot.get_chat_member(
                chat_id=f"@{channel_identifier}",
                user_id=user_id
            )
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            logger.error(f"Error checking {channel['name']}: {e}")
            return False
    return True

def build_channel_keyboard(lang: str):
    keyboard = []
    for channel in CHANNELS:
        keyboard.append([InlineKeyboardButton(f"📢 {channel['name']}", url=channel["url"])])
    keyboard.append([InlineKeyboardButton(LANG[lang]['check_btn'], callback_data="check_subscription")])
    toggle_text = "🇬🇧 English" if lang == 'fa' else "🇮🇷 فارسی"
    keyboard.append([InlineKeyboardButton(toggle_text, callback_data="toggle_lang")])
    return InlineKeyboardMarkup(keyboard)

def build_quality_keyboard(title: str, url: str, lang: str, formats):
    keyboard = []
    for res in ['1080p', '720p', '480p', '360p']:
        height = int(res.replace('p', ''))
        if any(f.get('height') == height for f in formats):
            keyboard.append([InlineKeyboardButton(f"📹 Video {res}", callback_data=f"video_{res}_{url}")])
    keyboard.append([InlineKeyboardButton("🎵 MP3 Audio", callback_data=f"audio_{url}")])
    keyboard.append([InlineKeyboardButton(LANG[lang]['cancel'], callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

def build_instagram_keyboard(title: str, url: str, lang: str):
    keyboard = [
        [InlineKeyboardButton("📹 Video (MP4)", callback_data=f"insta_video_{url}")],
        [InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"insta_audio_{url}")],
        [InlineKeyboardButton(LANG[lang]['cancel'], callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ========== AUDIO CONVERSION ==========
async def convert_audio_to_mp3(input_path: str, output_path: str):
    try:
        audio = AudioSegment.from_file(input_path)
        audio.export(output_path, format="mp3", bitrate="192k")
        return True
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        return False

# ========== HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_lang:
        user_lang[user_id] = 'fa'
    lang = user_lang[user_id]
    
    message = LANG[lang]['welcome']
    for channel in CHANNELS:
        message += LANG[lang]['join_channels'].format(name=channel['name'])
    message += "\n" + LANG[lang]['help']
    
    await update.message.reply_text(
        message,
        reply_markup=build_channel_keyboard(lang),
        parse_mode="Markdown"
    )

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = user_lang.get(user_id, 'fa')
    
    if await check_subscription(user_id, context):
        user_subscribed[user_id] = True
        await query.edit_message_text(
            LANG[lang]['subscribed'],
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            LANG[lang]['not_subscribed'],
            reply_markup=build_channel_keyboard(lang),
            parse_mode="Markdown"
        )

async def toggle_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    current = user_lang.get(user_id, 'fa')
    new_lang = 'en' if current == 'fa' else 'fa'
    user_lang[user_id] = new_lang
    
    message = LANG[new_lang]['welcome']
    for channel in CHANNELS:
        message += LANG[new_lang]['join_channels'].format(name=channel['name'])
    message += "\n" + LANG[new_lang]['help']
    
    await query.edit_message_text(
        message,
        reply_markup=build_channel_keyboard(new_lang),
        parse_mode="Markdown"
    )

# ========== AUDIO CONVERSION HANDLER ==========
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_lang.get(user_id, 'fa')
    
    if not await check_subscription(user_id, context):
        await update.message.reply_text(
            LANG[lang]['not_allowed'],
            reply_markup=build_channel_keyboard(lang),
            parse_mode="Markdown"
        )
        return
    
    file = None
    filename = "audio.m4a"
    if update.message.audio:
        file = update.message.audio
        filename = file.file_name or "audio.m4a"
    elif update.message.voice:
        file = update.message.voice
        filename = "voice.ogg"
    elif update.message.document:
        file = update.message.document
        filename = file.file_name or "audio.m4a"
    else:
        await update.message.reply_text("⚠️ لطفاً یک فایل صوتی ارسال کنید.")
        return

    processing_msg = await update.message.reply_text(LANG[lang]['converting'])
    try:
        file_obj = await context.bot.get_file(file.file_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as input_file:
            input_path = input_file.name
            await file_obj.download_to_drive(input_path)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as output_file:
            output_path = output_file.name

        if await convert_audio_to_mp3(input_path, output_path):
            with open(output_path, 'rb') as mp3_file:
                await update.message.reply_audio(
                    audio=mp3_file,
                    filename=filename.replace('.m4a', '.mp3').replace('.ogg', '.mp3').replace('.wav', '.mp3'),
                    performer="High Quality Converter",
                    title="Converted Audio",
                    caption=LANG[lang]['audio_sent']
                )
            await processing_msg.delete()
        else:
            await processing_msg.edit_text(LANG[lang]['conversion_error'])
        os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)
    except Exception as e:
        logger.error(f"Audio processing error: {e}")
        await processing_msg.edit_text(LANG[lang]['conversion_error'])

# ========== YOUTUBE HANDLERS ==========
async def handle_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_lang.get(user_id, 'fa')
    
    if not await check_subscription(user_id, context):
        await update.message.reply_text(
            LANG[lang]['not_allowed'],
            reply_markup=build_channel_keyboard(lang),
            parse_mode="Markdown"
        )
        return
    
    url = update.message.text.strip()
    processing_msg = await update.message.reply_text(LANG[lang]['youtube_processing'])
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['tv', 'web'],
                'skip': ['dash', 'hls'],
            }
        },
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        },
        'ignoreerrors': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise Exception("No info extracted")
            title = info.get('title', 'Video')
            formats = info.get('formats', [])
            
            keyboard = build_quality_keyboard(title, url, lang, formats)
            await processing_msg.edit_text(
                LANG[lang]['choose_quality'].format(title=title),
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"YouTube error: {e}")
        await processing_msg.edit_text(LANG[lang]['youtube_error'])

async def youtube_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    lang = user_lang.get(user_id, 'fa')
    
    if data == "cancel":
        await query.edit_message_text(LANG[lang]['cancel'])
        return
    
    parts = data.split('_')
    if parts[0] == "video":
        resolution = parts[1]
        url = '_'.join(parts[2:])
        await download_youtube_video(query, url, resolution, lang)
    elif parts[0] == "audio":
        url = '_'.join(parts[1:])
        await download_youtube_audio(query, url, lang)

async def download_youtube_video(query, url, resolution, lang):
    await query.edit_message_text(LANG[lang]['downloading_video'].format(quality=resolution))
    try:
        height = int(resolution.replace('p', ''))
        ydl_opts = {
            'format': f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]',
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['tv', 'web'],
                    'skip': ['dash', 'hls'],
                }
            },
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            'ignoreerrors': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise Exception("Download failed")
            filepath = ydl.prepare_filename(info)
            with open(filepath, 'rb') as video_file:
                await query.message.reply_video(
                    video=video_file,
                    caption=LANG[lang]['video_caption'].format(title=info.get('title', 'Video'), quality=resolution)
                )
            os.unlink(filepath)
        await query.edit_message_text(LANG[lang]['download_complete'])
    except Exception as e:
        logger.error(f"Video download error: {e}")
        await query.edit_message_text(LANG[lang]['youtube_error'])

async def download_youtube_audio(query, url, lang):
    await query.edit_message_text(LANG[lang]['downloading_audio'])
    try:
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['tv', 'web'],
                    'skip': ['dash', 'hls'],
                }
            },
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            'ignoreerrors': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise Exception("Download failed")
            filepath = ydl.prepare_filename(info).replace('.webm', '.mp3')
            with open(filepath, 'rb') as audio_file:
                await query.message.reply_audio(
                    audio=audio_file,
                    performer="YouTube",
                    title=info.get('title', 'Audio'),
                    caption=LANG[lang]['audio_caption']
                )
            os.unlink(filepath)
        await query.edit_message_text(LANG[lang]['download_complete'])
    except Exception as e:
        logger.error(f"Audio download error: {e}")
        await query.edit_message_text(LANG[lang]['youtube_error'])

# ========== INSTAGRAM HANDLERS ==========
async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_lang.get(user_id, 'fa')
    
    if not await check_subscription(user_id, context):
        await update.message.reply_text(
            LANG[lang]['not_allowed'],
            reply_markup=build_channel_keyboard(lang),
            parse_mode="Markdown"
        )
        return
    
    url = update.message.text.strip()
    processing_msg = await update.message.reply_text(LANG[lang]['instagram_processing'])
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        },
        'ignoreerrors': True,
        'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise Exception("No info extracted")
            title = info.get('title', 'Instagram Reel')
            # Remove "Instagram" from title if present
            title = title.replace('Instagram', '').strip()
            
            keyboard = build_instagram_keyboard(title, url, lang)
            await processing_msg.edit_text(
                f"📸 **{title}**\n\n{LANG[lang]['lang_prompt']}",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Instagram error: {e}")
        await processing_msg.edit_text(LANG[lang]['instagram_error'])

async def instagram_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    lang = user_lang.get(user_id, 'fa')
    
    if data == "cancel":
        await query.edit_message_text(LANG[lang]['cancel'])
        return
    
    parts = data.split('_')
    if parts[0] == "insta":
        if parts[1] == "video":
            url = '_'.join(parts[2:])
            await download_instagram_video(query, url, lang)
        elif parts[1] == "audio":
            url = '_'.join(parts[2:])
            await download_instagram_audio(query, url, lang)

async def download_instagram_video(query, url, lang):
    await query.edit_message_text(LANG[lang]['instagram_downloading'])
    try:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            'ignoreerrors': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise Exception("Download failed")
            filepath = ydl.prepare_filename(info)
            title = info.get('title', 'Instagram Reel')
            title = title.replace('Instagram', '').strip()
            
            with open(filepath, 'rb') as video_file:
                await query.message.reply_video(
                    video=video_file,
                    caption=LANG[lang]['instagram_caption'].format(title=title)
                )
            os.unlink(filepath)
        await query.edit_message_text(LANG[lang]['download_complete'])
    except Exception as e:
        logger.error(f"Instagram video download error: {e}")
        await query.edit_message_text(LANG[lang]['instagram_error'])

async def download_instagram_audio(query, url, lang):
    await query.edit_message_text(LANG[lang]['instagram_downloading'])
    try:
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            'ignoreerrors': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise Exception("Download failed")
            filepath = ydl.prepare_filename(info).replace('.webm', '.mp3')
            title = info.get('title', 'Instagram Reel')
            title = title.replace('Instagram', '').strip()
            
            with open(filepath, 'rb') as audio_file:
                await query.message.reply_audio(
                    audio=audio_file,
                    performer="Instagram",
                    title=title,
                    caption=LANG[lang]['instagram_audio_caption']
                )
            os.unlink(filepath)
        await query.edit_message_text(LANG[lang]['download_complete'])
    except Exception as e:
        logger.error(f"Instagram audio download error: {e}")
        await query.edit_message_text(LANG[lang]['instagram_error'])

# ========== MESSAGE HANDLER ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_lang.get(user_id, 'fa')
    text = update.message.text or ""
    
    # Check for YouTube links
    if "youtube.com" in text.lower() or "youtu.be" in text.lower():
        await handle_youtube(update, context)
    # Check for Instagram links
    elif "instagram.com" in text.lower() or "instagr.am" in text.lower():
        await handle_instagram(update, context)
    # Check for audio files
    elif update.message.audio or update.message.voice or update.message.document:
        await handle_audio(update, context)
    else:
        await update.message.reply_text(LANG[lang]['send_prompt'])

# ========== MAIN ==========
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="check_subscription"))
    app.add_handler(CallbackQueryHandler(toggle_language, pattern="toggle_lang"))
    app.add_handler(CallbackQueryHandler(youtube_callback, pattern="video_"))
    app.add_handler(CallbackQueryHandler(youtube_callback, pattern="audio_"))
    app.add_handler(CallbackQueryHandler(instagram_callback, pattern="insta_"))
    app.add_handler(CallbackQueryHandler(youtube_callback, pattern="cancel"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    print("🤖 Combined Bot is running...")
    print("✅ Audio Converter: Ready")
    print("✅ YouTube Downloader: Ready (with latest yt-dlp fixes)")
    print("✅ Instagram Reel Downloader: Ready")
    print("✅ Subscription Check: Enabled")
    print("✅ Language Toggle: Enabled")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
