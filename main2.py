import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from datetime import datetime

# ================== CONFIG ==================
TOKEN = os.environ.get("TOKEN")  # Pakai env variable untuk keamanan
PUBLIC_CHANNEL_ID = os.environ.get("PUBLIC_CHANNEL_ID", "@uitmppconfession")
PRIVATE_CHANNEL_ID = os.environ.get("PRIVATE_CHANNEL_ID", "-1003149603399")
COOLDOWN_SECONDS = 10
DAILY_IMAGE_QUOTA = 3
# ============================================

# ====== DATA ======
user_data = {}
banned_users = set([
    # Masukkan user_id yang ingin dibanned langsung
])
username_to_id = {}  # Mapping username -> user_id untuk command /ban
# ==================

# ----- START -----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello, saya bot @uitmppconfession\n"
        f"⏱ Setiap mesej diselangi {COOLDOWN_SECONDS} saat.\n"
        f"📸 Maksimum {DAILY_IMAGE_QUOTA} gambar per hari.\n\n"
        f"Patuhi peraturan jika tak mahu di bann.\n"
        f"Contact @d4n13lh4k1m untuk sebarang masalah."
    )

# ----- HELP -----
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Mula hantar mesej secara personal di bot ini, mesej anda akan dikirim ke channel @uitmppconfession\n"
        "Sebarang masalah boleh contact @d4n13lh4k1m\n\n"
        "Command untuk admin:\n"
        "/ban @username - Ban user dari private channel"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

# ----- RESET DAILY QUOTAS -----
def reset_daily_quotas():
    now = datetime.now()
    for user_id in user_data:
        if 'last_reset' not in user_data[user_id] or user_data[user_id]['last_reset'].date() < now.date():
            user_data[user_id]['image_count'] = 0
            user_data[user_id]['last_reset'] = now

# ----- BAN COMMAND (hanya private channel) -----
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Hanya private channel yang boleh jalankan command
    if str(update.effective_chat.id) != PRIVATE_CHANNEL_ID:
        await update.message.reply_text("❌ Command /ban hanya boleh dijalankan dari private channel.")
        return
    if not context.args:
        await update.message.reply_text("Gunakan /ban @username")
        return
    username = context.args[0].lstrip("@")
    if username in username_to_id:
        user_id = username_to_id[username]
        banned_users.add(user_id)
        await update.message.reply_text(f"✅ @{username} telah dibanned.")
    else:
        await update.message.reply_text(f"❌ Username @{username} belum pernah kirim pesan.")

# ----- HANDLE PM -----
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_id = update.message.from_user.id
    username = update.message.from_user.username or f"user{user_id}"

    reset_daily_quotas()
    username_to_id[username] = user_id

    # ====== CHECK BAN ======
    if user_id in banned_users:
        await update.message.reply_text("❌ Kamu tidak dibenarkan menggunakan bot ini.")
        return
    # =======================

    # ====== COOLDOWN ======
    last_time = user_data.get(user_id, {}).get('last_message_time')
    now = datetime.now()
    if last_time and (now - last_time).total_seconds() < COOLDOWN_SECONDS:
        wait_time = int(COOLDOWN_SECONDS - (now - last_time).total_seconds())
        await update.message.reply_text(f"⏳ Tunggu {wait_time} saat sebelum hantar message lagi")
        return

    # Inisialisasi user data
    if user_id not in user_data:
        user_data[user_id] = {'last_message_time': now, 'image_count': 0, 'last_reset': datetime.now()}

    # Cek quota gambar
    if update.message.photo:
        if user_data[user_id]['image_count'] >= DAILY_IMAGE_QUOTA:
            await update.message.reply_text(f"❌ Quota masa ni dah habis, {DAILY_IMAGE_QUOTA} gambar hari ini.")
            return
        user_data[user_id]['image_count'] += 1

    user_data[user_id]['last_message_time'] = now

    caption_from_user = update.message.caption or ""

    # ----- Forward ke public channel (anonymous) -----
    try:
        if update.message.text:
            await context.bot.send_message(chat_id=PUBLIC_CHANNEL_ID, text=update.message.text)
        elif update.message.photo:
            photo = update.message.photo[-1]
            await context.bot.send_photo(chat_id=PUBLIC_CHANNEL_ID, photo=photo.file_id, caption=caption_from_user)
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal hantar ke public channel: {e}")
        return

    # ----- Forward ke private channel (log asli) -----
    try:
        log_text = f"@{username} : {update.message.text or caption_from_user}"
        await context.bot.send_message(chat_id=PRIVATE_CHANNEL_ID, text=log_text)
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal hantar log ke private channel: {e}")
        return

    await update.message.reply_text(f"✅ Mesej dihantar. Tunggu {COOLDOWN_SECONDS} saat sebelum mesej seterusnya.")

# ================== MAIN ==================
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ban", ban_command))

    # Message handler: text + photo
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

    print("Bot is running...")
    app.run_polling()
