import os
from telegram.ext import Updater, CommandHandler
import yt_dlp

TOKEN = os.getenv("TOKEN")

def start(update, context):
    update.message.reply_text("Envíame un enlace de YouTube y lo descargo en 240p.")

def download(update, context):
    url = update.message.text.strip()
    ydl_opts = {
        'format': 'best[height<=240]',
        'outtmpl': 'video.mp4'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    update.message.reply_video(open("video.mp4", "rb"))

updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("download", download))

updater.start_polling()
updater.idle()
