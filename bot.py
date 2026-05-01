import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import yt_dlp

TOKEN = os.getenv("TOKEN")

async def start(update: Update, context):
    await update.message.reply_text("Envíame un enlace de YouTube y lo descargo en 240p.")

async def download(update: Update, context):
    url = update.message.text.strip()
    ydl_opts = {'format': 'best[height<=240]', 'outtmpl': 'video.mp4'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    await update.message.reply_video(open("video.mp4", "rb"))

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download))

app.run_polling()
