import os
import asyncio
import random
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, ChannelPostHandler, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))

REPEAT_COUNT = 3
POST_GAP_SECONDS = 4      # gap between messages
DAY_WINDOW_HOURS = 24

# =========================================

today_posts = []
today_date = datetime.utcnow().date()

async def repost_worker(app):
    global today_posts, today_date

    while True:
        now = datetime.utcnow()

        # New day → reset
        if now.date() != today_date:
            today_posts = []
            today_date = now.date()

        if today_posts:
            for repeat_round in range(REPEAT_COUNT):
                random.shuffle(today_posts)

                for msg in today_posts:
                    try:
                        await resend_message(app, msg)
                        await asyncio.sleep(POST_GAP_SECONDS)
                    except Exception as e:
                        print("Send error:", e)

                # gap between repeats (spread in 24 hrs)
                await asyncio.sleep((DAY_WINDOW_HOURS * 3600) // REPEAT_COUNT)

        await asyncio.sleep(60)

async def resend_message(app, msg):
    if msg.text:
        await app.bot.send_message(
            chat_id=CHANNEL_ID,
            text=msg.text
        )

    elif msg.photo:
        await app.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=msg.photo[-1].file_id,
            caption=msg.caption or ""
        )

    elif msg.video:
        await app.bot.send_video(
            chat_id=CHANNEL_ID,
            video=msg.video.file_id,
            caption=msg.caption or ""
        )

async def collect_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global today_posts

    msg = update.channel_post
    if not msg:
        return

    if msg.chat_id != CHANNEL_ID:
        return

    today_posts.append(msg)

async def on_startup(app):
    asyncio.create_task(repost_worker(app))

app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()
app.add_handler(ChannelPostHandler(collect_posts))

app.run_polling()
