import os
import logging
import tempfile
import subprocess
import json
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp
from pydub import AudioSegment
from PIL import Image

# ========== CONFIGURATION ==========
# 🔴 TEMPORARY: Hardcoded token (remove after testing!)
TOKEN = "8832684689:AAF7jtsSopJYoHkPQvtOePMUchVLniOu4Oo"   # Replace with your actual token

# Your channels
CHANNELS = [
    {"name": "Pykillinux", "url": "https://t.me/pykillinux"},
    {"name": "Music Search", "url": "https://t.me/music_search"}
]

# Admin ID (replace with your Telegram user ID)
ADMIN_IDS = [310141017]  # Add your user ID here

# ========== LANGUAGE DICTIONARY ==========
LANG = {
    'fa': {
        # ... (keep existing translations, add new ones below)
        'video_conversion': "🎬 **تبدیل ویدیو به MP4**\n\nکیفیت مورد نظر را انتخاب کنید:",
        'image_conversion': "🖼 **تبدیل تصویر**\n\nنوع خروجی را انتخاب کنید:",
        'convert_to_jpg': "تبدیل به JPG",
        'convert_to_png': "تبدیل به PNG",
        'link_download': "🔗 **در حال دانلود از لینک...**",
        'link_error': "❌ خطا در دانلود. لطفاً لینک معتبر ارسال کنید.",
        'video_quality_720': "720p",
        'video_quality_1080': "1080p",
        'video_quality_480': "480p",
        'converting_video': "🔄 در حال تبدیل ویدیو به MP4...",
        'converting_image': "🔄 در حال تبدیل تصویر...",
        'download_complete_link': "✅ دانلود کامل شد!",
        'send_video_or_link': "📹 لطفاً یک ویدیو، تصویر یا لینک مستقیم ارسال کنید.",
    },
    'en': {
        # ... existing English translations
        'video_conversion': "🎬 **Convert Video to MP4**\n\nChoose the quality:",
        'image_conversion': "🖼 **Image Conversion**\n\nChoose output format:",
        'convert_to_jpg': "Convert to JPG",
        'convert_to_png': "Convert to PNG",
        'link_download': "🔗 **Downloading from link...**",
        'link_error': "❌ Download failed. Please send a valid link.",
        'video_quality_720': "720p",
        'video_quality_1080': "1080p",
        'video_quality_480': "480p",
        'converting_video': "🔄 Converting video to MP4...",
        'converting_image': "🔄 Converting image...",
        'download_complete_link': "✅ Download complete!",
        'send_video_or_link': "📹 Please send a video, image, or direct download link.",
    }
}

# ========== LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== USER DATA ==========
user_lang = {}
user_subscribed = {}
USER_DATA_FILE = 'user_data.json'

def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

user_data = load_user_data()

def track_user(user_id, username=None, first_name=None, last_name=None, action=None):
    now = datetime.now().isoformat()
    uid = str(user_id)
    if uid not in user_data:
        user_data[uid] = {
            'first_seen': now,
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'total_messages': 0,
            'actions': {},
            'last_active': now,
            'subscribed': False,
        }
    user = user_data[uid]
    user['last_active'] = now
    user['total_messages'] += 1
    if username:
        user['username'] = username
    if first_name:
        user['first_name'] = first_name
    if last_name:
        user['last_name'] = last_name
    if action:
        user['actions'][action] = user['actions'].get(action, 0) + 1
    save_user_data(user_data)
    return user

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

def build_video_conversion_keyboard(lang: str, file_id: str):
    keyboard = [
        [InlineKeyboardButton("720p", callback_data=f"vidconv_720_{file_id}")],
        [InlineKeyboardButton("1080p", callback_data=f"vidconv_1080_{file_id}")],
        [InlineKeyboardButton("480p", callback_data=f"vidconv_480_{file_id}")],
        [InlineKeyboardButton(LANG[lang]['cancel'], callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_image_conversion_keyboard(lang: str, file_id: str, current_format: str):
    keyboard = []
    if current_format.lower() in ['jpg', 'jpeg']:
        keyboard.append([InlineKeyboardButton(LANG[lang]['convert_to_png'], callback_data=f"imgconv_png_{file_id}")])
    elif current_format.lower() == 'png':
        keyboard.append([InlineKeyboardButton(LANG[lang]['convert_to_jpg'], callback_data=f"imgconv_jpg_{file_id}")])
    else:
        keyboard.append([InlineKeyboardButton(LANG[lang]['convert_to_jpg'], callback_data=f"imgconv_jpg_{file_id}")])
        keyboard.append([InlineKeyboardButton(LANG[lang]['convert_to_png'], callback_data=f"imgconv_png_{file_id}")])
    keyboard.append([InlineKeyboardButton(LANG[lang]['cancel'], callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

# ========== CONVERSION FUNCTIONS ==========
async def convert_video_to_mp4(input_path: str, output_path: str, quality: str):
    """Convert video to MP4 with specified quality (720p, 1080p, 480p)"""
    try:
        # Map quality to height
        height = int(quality.replace('p', ''))
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vf', f'scale=-2:{height}',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '22',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-y',
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Video conversion error: {e}")
        return False

async def convert_image(input_path: str, output_path: str, output_format: str):
    """Convert image to JPG or PNG"""
    try:
        img = Image.open(input_path)
        if output_format.lower() == 'jpg':
            img = img.convert('RGB')
            img.save(output_path, 'JPEG', quality=95)
        elif output_format.lower() == 'png':
            img.save(output_path, 'PNG')
        return True
    except Exception as e:
        logger.error(f"Image conversion error: {e}")
        return False

async def download_link_to_file(url: str, output_path: str):
    """Download a file from a direct link"""
    try:
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        return False
    except Exception as e:
        logger.error(f"Link download error: {e}")
        return False

# ========== HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    track_user(user.id, user.username, user.first_name, user.last_name, 'start')
    user_id = user.id
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

# ========== AUDIO CONVERSION ==========
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    track_user(user.id, user.username, user.first_name, user.last_name, 'audio_conversion')
    user_id = user.id
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

        audio = AudioSegment.from_file(input_path)
        audio.export(output_path, format="mp3", bitrate="192k")
        with open(output_path, 'rb') as mp3_file:
            await update.message.reply_audio(
                audio=mp3_file,
                filename=filename.replace('.m4a', '.mp3').replace('.ogg', '.mp3').replace('.wav', '.mp3'),
                performer="High Quality Converter",
                title="Converted Audio",
                caption=LANG[lang]['audio_sent']
            )
        await processing_msg.delete()
        os.unlink(input_path)
        os.unlink(output_path)
    except Exception as e:
        logger.error(f"Audio processing error: {e}")
        await processing_msg.edit_text(LANG[lang]['conversion_error'])

# ========== VIDEO CONVERSION ==========
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    track_user(user.id, user.username, user.first_name, user.last_name, 'video_conversion')
    user_id = user.id
    lang = user_lang.get(user_id, 'fa')
    
    if not await check_subscription(user_id, context):
        await update.message.reply_text(
            LANG[lang]['not_allowed'],
            reply_markup=build_channel_keyboard(lang),
            parse_mode="Markdown"
        )
        return
    
    video = update.message.video
    if not video:
        await update.message.reply_text("⚠️ لطفاً یک ویدیو ارسال کنید.")
        return
    
    file_id = video.file_id
    keyboard = build_video_conversion_keyboard(lang, file_id)
    await update.message.reply_text(
        LANG[lang]['video_conversion'],
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def video_conversion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    lang = user_lang.get(user_id, 'fa')
    
    if data == "cancel":
        await query.edit_message_text(LANG[lang]['cancel'])
        return
    
    parts = data.split('_')
    if parts[0] == "vidconv":
        quality = parts[1]
        file_id = parts[2]
        await query.edit_message_text(LANG[lang]['converting_video'])
        
        try:
            # Get file
            file = await context.bot.get_file(file_id)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as input_file:
                input_path = input_file.name
                await file.download_to_drive(input_path)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as output_file:
                output_path = output_file.name
            
            # Convert
            success = await convert_video_to_mp4(input_path, output_path, quality)
            if success:
                with open(output_path, 'rb') as vid_file:
                    await query.message.reply_video(
                        video=vid_file,
                        caption=f"📹 MP4 {quality}",
                        supports_streaming=True
                    )
                await query.edit_message_text(LANG[lang]['download_complete'])
            else:
                await query.edit_message_text(LANG[lang]['conversion_error'])
            os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
        except Exception as e:
            logger.error(f"Video conversion callback error: {e}")
            await query.edit_message_text(LANG[lang]['conversion_error'])

# ========== IMAGE CONVERSION ==========
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    track_user(user.id, user.username, user.first_name, user.last_name, 'image_conversion')
    user_id = user.id
    lang = user_lang.get(user_id, 'fa')
    
    if not await check_subscription(user_id, context):
        await update.message.reply_text(
            LANG[lang]['not_allowed'],
            reply_markup=build_channel_keyboard(lang),
            parse_mode="Markdown"
        )
        return
    
    photo = update.message.photo
    if photo:
        # Use the largest photo
        file_id = photo[-1].file_id
        current_format = 'jpg'
    else:
        # Document image
        doc = update.message.document
        if not doc or not doc.mime_type or not doc.mime_type.startswith('image/'):
            await update.message.reply_text("⚠️ لطفاً یک تصویر ارسال کنید.")
            return
        file_id = doc.file_id
        current_format = doc.mime_type.split('/')[-1]  # jpg, png, etc.
    
    keyboard = build_image_conversion_keyboard(lang, file_id, current_format)
    await update.message.reply_text(
        LANG[lang]['image_conversion'],
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def image_conversion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    lang = user_lang.get(user_id, 'fa')
    
    if data == "cancel":
        await query.edit_message_text(LANG[lang]['cancel'])
        return
    
    parts = data.split('_')
    if parts[0] == "imgconv":
        output_format = parts[1]  # 'jpg' or 'png'
        file_id = parts[2]
        await query.edit_message_text(LANG[lang]['converting_image'])
        
        try:
            file = await context.bot.get_file(file_id)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".img") as input_file:
                input_path = input_file.name
                await file.download_to_drive(input_path)
            ext = '.' + output_format
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as output_file:
                output_path = output_file.name
            
            success = await convert_image(input_path, output_path, output_format)
            if success:
                with open(output_path, 'rb') as img_file:
                    if output_format == 'jpg':
                        await query.message.reply_photo(photo=img_file, caption="🖼 JPG Image")
                    else:
                        await query.message.reply_document(document=img_file, filename=f"image.{output_format}", caption="🖼 PNG Image")
                await query.edit_message_text(LANG[lang]['download_complete'])
            else:
                await query.edit_message_text(LANG[lang]['conversion_error'])
            os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
        except Exception as e:
            logger.error(f"Image conversion callback error: {e}")
            await query.edit_message_text(LANG[lang]['conversion_error'])

# ========== LINK TO FILE ==========
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    user = update.effective_user
    track_user(user.id, user.username, user.first_name, user.last_name, 'link_download')
    user_id = user.id
    lang = user_lang.get(user_id, 'fa')
    
    if not await check_subscription(user_id, context):
        await update.message.reply_text(
            LANG[lang]['not_allowed'],
            reply_markup=build_channel_keyboard(lang),
            parse_mode="Markdown"
        )
        return
    
    processing_msg = await update.message.reply_text(LANG[lang]['link_download'])
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            output_path = tmp_file.name
        success = await download_link_to_file(url, output_path)
        if success:
            # Determine file size
            file_size = os.path.getsize(output_path)
            if file_size > 50 * 1024 * 1024:
                await processing_msg.edit_text("❌ File too large for Telegram (max 50 MB).")
                os.unlink(output_path)
                return
            # Send as document
            with open(output_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(url.split('/')[-1]) or 'file.bin',
                    caption="📁 File downloaded from link"
                )
            await processing_msg.edit_text(LANG[lang]['download_complete_link'])
        else:
            await processing_msg.edit_text(LANG[lang]['link_error'])
        if os.path.exists(output_path):
            os.unlink(output_path)
    except Exception as e:
        logger.error(f"Link download error: {e}")
        await processing_msg.edit_text(LANG[lang]['link_error'])

# ========== YOUTUBE & INSTAGRAM (unchanged) ==========
# ... (keep existing handlers for youtube and instagram)

# ========== MESSAGE HANDLER ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    lang = user_lang.get(user_id, 'fa')
    text = update.message.text or ""
    
    # Check for YouTube or Instagram
    if "youtube.com" in text.lower() or "youtu.be" in text.lower():
        await handle_youtube(update, context)
        return
    elif "instagram.com" in text.lower() or "instagr.am" in text.lower():
        await handle_instagram(update, context)
        return
    # Check if it's a direct download link (starts with http/https)
    elif text.startswith('http://') or text.startswith('https://'):
        await handle_link(update, context, text)
        return
    # Check for video
    elif update.message.video:
        await handle_video(update, context)
        return
    # Check for photo or image document
    elif update.message.photo or (update.message.document and update.message.document.mime_type and update.message.document.mime_type.startswith('image/')):
        await handle_image(update, context)
        return
    # Check for audio
    elif update.message.audio or update.message.voice or (update.message.document and update.message.document.mime_type and update.message.document.mime_type.startswith('audio/')):
        await handle_audio(update, context)
        return
    else:
        await update.message.reply_text(LANG[lang]['send_prompt'])

# ========== STATS (Admin) ==========
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to view stats.")
        return
    
    total_users = len(user_data)
    total_messages = sum(u['total_messages'] for u in user_data.values())
    
    stats_text = f"""
📊 **Bot Statistics**

👥 Total Users: {total_users}
💬 Total Messages: {total_messages}

**Actions Summary:**
"""
    action_counts = {}
    for user in user_data.values():
        for action, count in user.get('actions', {}).items():
            action_counts[action] = action_counts.get(action, 0) + count
    
    for action, count in action_counts.items():
        stats_text += f"• {action}: {count}\n"
    
    stats_text += "\n**Top 5 Most Active Users:**\n"
    sorted_users = sorted(user_data.values(), key=lambda x: x['total_messages'], reverse=True)[:5]
    for i, user in enumerate(sorted_users, 1):
        name = user.get('first_name', 'Unknown')
        username = user.get('username', 'No username')
        stats_text += f"{i}. {name} (@{username}) - {user['total_messages']} messages\n"
    
    await update.message.reply_text(stats_text, parse_mode="Markdown")

# ========== MAIN ==========
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="check_subscription"))
    app.add_handler(CallbackQueryHandler(toggle_language, pattern="toggle_lang"))
    app.add_handler(CallbackQueryHandler(youtube_callback, pattern="video_"))
    app.add_handler(CallbackQueryHandler(youtube_callback, pattern="audio_"))
    app.add_handler(CallbackQueryHandler(instagram_callback, pattern="insta_"))
    app.add_handler(CallbackQueryHandler(video_conversion_callback, pattern="vidconv_"))
    app.add_handler(CallbackQueryHandler(image_conversion_callback, pattern="imgconv_"))
    app.add_handler(CallbackQueryHandler(youtube_callback, pattern="cancel"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    print("🤖 Combined Bot is running...")
    print("✅ Audio Converter: Ready")
    print("✅ YouTube Downloader: Ready")
    print("✅ Instagram Reel Downloader: Ready")
    print("✅ Video Converter: Ready (MP4 480p/720p/1080p)")
    print("✅ Image Converter: Ready (JPG ↔ PNG)")
    print("✅ Link to File: Ready")
    print("✅ Subscription Check: Enabled")
    print("✅ Language Toggle: Enabled")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
