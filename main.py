import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from supabase import create_client

# ================= ENV =================
BOT_TOKEN = os.getenv("BOT_TOKEN")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

TARGET_CHANNEL = int(os.getenv("TARGET_CHANNEL"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))
# ======================================

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- DB HELPERS ----------
def get_settings():
    return (
        supabase
        .table("bot_settings")
        .select("*")
        .eq("id", 1)
        .execute()
        .data[0]
    )

def update_settings(**kwargs):
    supabase.table("bot_settings").update(kwargs).eq("id", 1).execute()

def time_allowed(slots):
    hour = datetime.now().hour
    return any(start <= hour <= end for start, end in slots)

# ---------- ADMIN PANEL ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    s = get_settings()
    slots_text = "\n".join([f"{a}-{b}" for a, b in s["time_slots"]])

    keyboard = [
        [InlineKeyboardButton("⏱ Set Time Slots", callback_data="set_slots")],
        [
            InlineKeyboardButton("▶️ Repost ON", callback_data="on"),
            InlineKeyboardButton("⛔ Repost OFF", callback_data="off"),
        ],
    ]

    await update.message.reply_text(
        f"🔧 Repost Control Panel\n\nCurrent Slots:\n{slots_text}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# ---------- BUTTON HANDLER ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.from_user.id != ADMIN_ID:
        return

    if q.data == "on":
        update_settings(repost_enabled=True)
        await q.edit_message_text("▶️ Repost ENABLED")

    elif q.data == "off":
        update_settings(repost_enabled=False)
        await q.edit_message_text("⛔ Repost DISABLED")

    elif q.data == "set_slots":
        context.user_data["awaiting_slots"] = True
        await q.edit_message_text(
            "⏱ Time slots bhejo (har line me ek):\n\n"
            "Example:\n9-11\n13-15\n18-22"
        )

# ---------- SLOT INPUT ----------
async def slot_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.user_data.get("awaiting_slots"):
        return

    try:
        slots = []
        for line in update.message.text.strip().splitlines():
            a, b = map(int, line.split("-"))
            if 0 <= a <= 23 and 0 <= b <= 23:
                slots.append([a, b])

        if not slots:
            raise ValueError

        update_settings(time_slots=slots)
        context.user_data["awaiting_slots"] = False

        await update.message.reply_text(
            "✅ Time slots saved:\n" +
            "\n".join([f"{a}-{b}" for a, b in slots])
        )
    except:
        await update.message.reply_text("❌ Invalid format")

# ---------- REPOST LOGIC ----------
async def repost_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post

    if msg.chat.id != TARGET_CHANNEL:
        return

    sender = msg.from_user.id if msg.from_user else None
    if sender not in [ADMIN_ID, context.bot.id]:
        return

    s = get_settings()
    if not s["repost_enabled"]:
        return

    if not time_allowed(s["time_slots"]):
        return

    for _ in range(s["repeat_count"] - 1):
        await asyncio.sleep(s["delay_seconds"])

        if msg.text:
            await context.bot.send_message(TARGET_CHANNEL, msg.text)
        elif msg.photo:
            await context.bot.send_photo(TARGET_CHANNEL, msg.photo[-1].file_id, caption=msg.caption)
        elif msg.video:
            await context.bot.send_video(TARGET_CHANNEL, msg.video.file_id, caption=msg.caption)
        elif msg.document:
            await context.bot.send_document(TARGET_CHANNEL, msg.document.file_id, caption=msg.caption)
        elif msg.audio:
            await context.bot.send_audio(TARGET_CHANNEL, msg.audio.file_id, caption=msg.caption)
        elif msg.voice:
            await context.bot.send_voice(TARGET_CHANNEL, msg.voice.file_id)
        elif msg.animation:
            await context.bot.send_animation(TARGET_CHANNEL, msg.animation.file_id, caption=msg.caption)
        elif msg.sticker:
            await context.bot.send_sticker(TARGET_CHANNEL, msg.sticker.file_id)

# ---------- APP ----------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, slot_input))
app.add_handler(MessageHandler(filters.ChatType.CHANNEL, repost_handler))

app.run_polling()
