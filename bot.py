import yt_dlp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
import os

TOKEN = os.getenv("TOKEN")  # tu token de BotFather
COOKIES = "www.youtube.com_cookies.txt"  # archivo de cookies

# --- Menú principal ---
def start(update, context):
    botones = [
        [InlineKeyboardButton("⬇️ Descargar en 144p", callback_data="descargar_144")],
        [InlineKeyboardButton("⬇️ Descargar en 240p", callback_data="descargar_240")]
    ]
    reply_markup = InlineKeyboardMarkup(botones)
    update.message.reply_text("🎬 Bienvenido al bot de descargas. Elige la calidad:", reply_markup=reply_markup)

# --- Descargar video ---
def descargar_video(update, context, calidad):
    query = update.callback_query
    url = context.user_data.get("url")
    if not url:
        query.message.reply_text("❌ Primero envíame el enlace del video.")
        return

    opciones = {
        'format': f'best[height<={calidad}]',
        'outtmpl': '%(title)s.%(ext)s',
        'cookiefile': COOKIES
    }
    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=True)
            archivo = ydl.prepare_filename(info)
            with open(archivo, "rb") as f:
                query.message.reply_video(video=f, caption=f"🎬 {info['title']} descargado en {calidad}p")
    except Exception as e:
        query.message.reply_text(f"⚠️ Error al descargar: {e}")

# --- Manejo de botones ---
def manejar_botones(update, context):
    query = update.callback_query
    if query.data == "descargar_144":
        descargar_video(update, context, 144)
    elif query.data == "descargar_240":
        descargar_video(update, context, 240)

# --- Guardar enlace ---
def enlace(update, context):
    if not context.args:
        update.message.reply_text("❌ Uso: /enlace <URL>")
        return
    url = context.args[0]
    context.user_data["url"] = url
    update.message.reply_text("✅ Enlace guardado. Ahora elige la calidad con /start")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("enlace", enlace))
    dp.add_handler(CallbackQueryHandler(manejar_botones))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()