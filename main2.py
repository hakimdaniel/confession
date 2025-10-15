import os
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# ================== CONFIG ==================
TOKEN = os.environ.get("BOT_TOKEN")  # Simpan token di environment variable di Render
PUBLIC_CHANNEL_ID = os.environ.get("PUBLIC_CHANNEL")       # e.g. "@uitmppconfession"
PRIVATE_CHANNEL_ID = os.environ.get("PRIVATE_CHANNEL")     # e.g. "-1003149603399"
COOLDOWN_SECONDS = 10
DAILY_IMAGE_QUOTA = 3
# ============================================

# ====== DATA ======
user_data = {}
banned_users = set()
username_to_id = {}  # mapping username -> user_id
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
        "Hantar mesej secara personal, mesej anda akan dihantar ke channel @uitmppconfession.\n"
        "Contact @d4n13lh4k1m untuk masalah.\n\n"
        "Admin commands (hanya private channel):\n"
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

# ----- BAN COMMAND -----
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Hanya private channel
    if str(update.effective_chat.id) != PRIVATE_CHANNEL_ID:
        await update.message.reply_text("❌ Command /ban hanya dari private channel.")
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
    user_id = update.message.from_user.id
    username = update.message.from_user.username or f"user{user_id}"

    reset_daily_quotas()

    # Simpan mapping username -> id
    username_to_id[username] = user_id

    # ====== CHECK BAN ======
    if user_id in banned_users:
        await update.message.reply_text("❌ Kamu tidak dibenarkan menggunakan bot ini.")
        return

    # ====== COOLDOWN ======
    last_time = user_data.get(user_id, {}).get('last_message_time')
    now = datetime.now()
    if last_time and (now - last_time).total_seconds() < COOLDOWN_SECONDS:
        wait_time = int(COOLDOWN_SECONDS - (now - last_time).total_seconds())
        await update.message.reply_text(f"⏳ Tunggu {wait_time} saat sebelum mesej lagi")
        return

    # ====== INIT USER DATA ======
    if user_id not in user_data:
        user_data[user_id] = {'last_message_time': now, 'image_count': 0, 'last_reset': datetime.now()}
    user_data[user_id]['last_message_time'] = now

    # ====== IMAGE QUOTA ======
    if update.message.photo:
        if user_data[user_id]['image_count'] >= DAILY_IMAGE_QUOTA:
            await update.message.reply_text(f"❌ Quota gambar {DAILY_IMAGE_QUOTA} hari ini sudah habis.")
            return
        user_data[user_id]['image_count'] += 1

    caption_from_user = update.message.caption or ""
    text_to_send = update.message.text or caption_from_user

    # ----- PUBLIC CHANNEL (anonymous) -----
    try:
        if update.message.text:
            await context.bot.send_message(chat_id=PUBLIC_CHANNEL_ID, text=update.message.text)
        elif update.message.photo:
            photo = update.message.photo[-1]
            await context.bot.send_photo(chat_id=PUBLIC_CHANNEL_ID, photo=photo.file_id, caption=caption_from_user)
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal hantar ke public channel: {e}")
        return

    # ----- PRIVATE CHANNEL (log) -----
    try:
        log_text = f"@{username} : {text_to_send}"
        await context.bot.send_message(chat_id=PRIVATE_CHANNEL_ID, text=log_text)
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal hantar log ke private channel: {e}")
        return

    await update.message.reply_text(f"✅ Mesej dihantar. Tunggu {COOLDOWN_SECONDS} saat sebelum mesej seterusnya.")

# ================== MAIN ==================
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE, handle_message))

    print("Bot is running...")
    app.run_polling()
