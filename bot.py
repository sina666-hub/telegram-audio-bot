import os
import logging
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp
from pydub import AudioSegment

# ========== CONFIGURATION ==========
# 🔴 STEP 1: Get your NEW token from @BotFather (revoke the old one first)
# 🔴 STEP 2: Paste your NEW token between the quotes below
TOKEN = "8866299232:AAH6IUtnTZYw9e8y7daPicXFd-aiMC_JWK0"

# Your channels (replace with your own if needed)
CHANNELS = [
    {"name": "Pykillinux", "url": "https://t.me/pykillinux"},
    {"name": "Music Search", "url": "https://t.me/music_search"}
]

# ========== LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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

def build_channel_keyboard():
    keyboard = []
    for channel in CHANNELS:
        keyboard.append([InlineKeyboardButton(f"📢 {channel['name']}", url=channel["url"])])
    keyboard.append([InlineKeyboardButton("✅ Check Subscription", callback_data="check_subscription")])
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
    message = (
        "🎵 **تبدیل‌کننده صدای باکیفیت**\n\n"
        "برای استفاده از این ربات، لطفاً ابتدا در کانال‌های زیر عضو شوید:\n\n"
    )
    for channel in CHANNELS:
        message += f"• {channel['name']}\n"
    message += "\nپس از عضویت، روی دکمه **بررسی عضویت** کلیک کنید."
    await update.message.reply_text(message, reply_markup=build_channel_keyboard(), parse_mode="Markdown")

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if await check_subscription(user_id, context):
        await query.edit_message_text(
            "✅ **تبریک! شما در تمام کانال‌ها عضو هستید.**\n\n"
            "🎵 حالا می‌توانید از ربات استفاده کنید.\n"
            "فایل صوتی خود را ارسال کنید تا به MP3 تبدیل شود.\n\n"
            "📥 **راهنمایی:**\n"
            "• فایل‌های M4A، OGG، WAV، FLAC و ... پشتیبانی می‌شوند.\n"
            "• لینک یوتیوب را ارسال کنید تا دانلود شود.",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            "❌ **شما هنوز در تمام کانال‌ها عضو نشده‌اید.**\n\n"
            "لطفاً روی لینک کانال‌های زیر کلیک کرده و عضو شوید، سپس دوباره روی دکمه **بررسی عضویت** کلیک کنید.",
            reply_markup=build_channel_keyboard(),
            parse_mode="Markdown"
        )

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_subscription(user_id, context):
        await update.message.reply_text(
            "❌ **دسترسی محدود شده است.**\n\n"
            "لطفاً ابتدا در کانال‌های زیر عضو شوید:",
            reply_markup=build_channel_keyboard(),
            parse_mode="Markdown"
        )
        return

    file = None
    if update.message.audio:
        file = update.message.audio
    elif update.message.voice:
        file = update.message.voice
    elif update.message.document:
        file = update.message.document
    else:
        await update.message.reply_text("⚠️ لطفاً یک فایل صوتی ارسال کنید.")
        return

    processing_msg = await update.message.reply_text("🔄 در حال تبدیل فایل...")
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
                    filename=f"{file.file_name.split('.')[0]}.mp3" if hasattr(file, 'file_name') else "converted.mp3",
                    performer="High Quality Converter",
                    title="Converted Audio"
                )
            await processing_msg.delete()
        else:
            await processing_msg.edit_text("❌ خطا در تبدیل فایل. لطفاً دوباره تلاش کنید.")
        os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)
    except Exception as e:
        logger.error(f"Audio processing error: {e}")
        await processing_msg.edit_text("❌ خطا در پردازش فایل.")

async def handle_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_subscription(user_id, context):
        await update.message.reply_text(
            "❌ **دسترسی محدود شده است.**\n\n"
            "لطفاً ابتدا در کانال‌های زیر عضو شوید:",
            reply_markup=build_channel_keyboard(),
            parse_mode="Markdown"
        )
        return

    url = update.message.text.strip()
    processing_msg = await update.message.reply_text("🔄 در حال دریافت اطلاعات از یوتیوب...")
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Video')
            formats = info.get('formats', [])
            keyboard = []
            for res in ['1080p', '720p', '480p', '360p']:
                if any(f.get('height') == int(res.replace('p', '')) for f in formats):
                    keyboard.append([InlineKeyboardButton(f"📹 Video {res}", callback_data=f"youtube_video_{res}_{url}")])
            keyboard.append([InlineKeyboardButton("🎵 Audio MP3", callback_data=f"youtube_audio_{url}")])
            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
            await processing_msg.edit_text(
                f"🎬 **{title}**\n\nکیفیت مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"YouTube error: {e}")
        await processing_msg.edit_text("❌ خطا در دریافت اطلاعات. لطفاً لینک معتبر ارسال کنید.")

async def youtube_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split('_')
    if data == "cancel":
        await query.edit_message_text("❌ عملیات لغو شد.")
        return
    if parts[0] == "youtube":
        if parts[1] == "video":
            resolution = parts[2]
            url = '_'.join(parts[3:])
            await download_youtube_video(query, url, resolution)
        elif parts[1] == "audio":
            url = '_'.join(parts[2:])
            await download_youtube_audio(query, url)

async def download_youtube_video(query, url, resolution):
    await query.edit_message_text(f"🔄 در حال دانلود ویدیو با کیفیت {resolution}...")
    try:
        height = int(resolution.replace('p', ''))
        ydl_opts = {
            'format': f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]',
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
            with open(filepath, 'rb') as video_file:
                await query.message.reply_video(
                    video=video_file,
                    caption=f"📹 {info.get('title', 'Video')}\nکیفیت: {resolution}"
                )
            os.unlink(filepath)
        await query.edit_message_text("✅ دانلود کامل شد!")
    except Exception as e:
        logger.error(f"Video download error: {e}")
        await query.edit_message_text("❌ خطا در دانلود. لطفاً دوباره تلاش کنید.")

async def download_youtube_audio(query, url):
    await query.edit_message_text("🔄 در حال دانلود و استخراج MP3...")
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info).replace('.webm', '.mp3')
            with open(filepath, 'rb') as audio_file:
                await query.message.reply_audio(
                    audio=audio_file,
                    performer="YouTube",
                    title=info.get('title', 'Audio'),
                    caption="🎵 استخراج شده از یوتیوب"
                )
            os.unlink(filepath)
        await query.edit_message_text("✅ دانلود کامل شد!")
    except Exception as e:
        logger.error(f"Audio download error: {e}")
        await query.edit_message_text("❌ خطا در دانلود. لطفاً دوباره تلاش کنید.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    if "youtube.com" in text.lower() or "youtu.be" in text.lower():
        await handle_youtube(update, context)
    elif update.message.audio or update.message.voice or update.message.document:
        await handle_audio(update, context)
    else:
        await update.message.reply_text(
            "👋 سلام! لطفاً یک فایل صوتی یا لینک یوتیوب ارسال کنید.\n\n"
            "برای راهنمایی بیشتر از /start استفاده کنید."
        )

# ========== MAIN ==========
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="check_subscription"))
    app.add_handler(CallbackQueryHandler(youtube_callback, pattern="youtube_"))
    app.add_handler(CallbackQueryHandler(youtube_callback, pattern="cancel"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    print("🤖 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
