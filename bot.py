import os
import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # ID del canal privado

data = {"tareas": [], "notas": [], "archivos": []}

# --- Bienvenida ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "👋 Bienvenido al Bot de Productividad.\n\n"
        "📅 Gestión de tareas:\n"
        "• /tarea <texto> → añadir tarea con fecha límite\n"
        "• /listado → ver tareas pendientes\n\n"
        "📒 Notas y archivos:\n"
        "• /nota <texto> → guardar una nota\n"
        "• /buscar <palabra> → buscar en notas y archivos\n"
        "• /archivos → ver todos los archivos guardados\n\n"
        "Los datos se guardan en el canal privado."
    )
    await update.message.reply_text(texto)

# --- Añadir tarea ---
async def nueva_tarea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("✍️ Escribe el nombre de la tarea después de /tarea")
        return
    texto = " ".join(context.args)
    hoy = datetime.date.today()
    botones = []
    for i in range(10):
        dia = hoy + datetime.timedelta(days=i)
        botones.append([InlineKeyboardButton(dia.strftime("%d-%m-%Y"), callback_data=f"fecha_{dia}_{texto}")])
    reply_markup = InlineKeyboardMarkup(botones)
    await update.message.reply_text("📅 Selecciona la fecha límite:", reply_markup=reply_markup)

async def manejar_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, fecha_str, texto = query.data.split("_", 2)
    tarea = {"texto": texto, "fecha": fecha_str, "completada": False}
    data["tareas"].append(tarea)
    # Guardar en canal
    await query.message.bot.send_message(CHANNEL_ID, f"TAREA|{texto}|{fecha_str}|False")
    await query.edit_message_text(f"✅ Tarea añadida: *{texto}* (vence {fecha_str})")

# --- Notas ---
async def nota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("✍️ Escribe el texto después de /nota")
        return
    texto = " ".join(context.args)
    data["notas"].append(texto)
    # Guardar en canal
    await update.message.bot.send_message(CHANNEL_ID, f"NOTA|{texto}")
    await update.message.reply_text(f"✅ Nota guardada: {texto}")

# --- Guardar archivos ---
async def guardar_archivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    archivo = update.message.document or update.message.video or update.message.photo[-1]
    entrada = {"file_id": archivo.file_id, "caption": update.message.caption or ""}
    data["archivos"].append(entrada)
    # Guardar en canal
    await update.message.bot.send_message(CHANNEL_ID, f"ARCHIVO|{entrada['file_id']}|{entrada['caption']}")
    await update.message.reply_text("📂 Archivo guardado correctamente.")

# --- Reconstrucción al iniciar ---
async def reconstruir_memoria(app: Application):
    # Leer últimos mensajes del canal
    mensajes = await app.bot.get_chat_history(CHANNEL_ID, limit=100)
    for msg in mensajes:
        if msg.text and msg.text.startswith("TAREA|"):
            _, texto, fecha, estado = msg.text.split("|")
            data["tareas"].append({"texto": texto, "fecha": fecha, "completada": estado == "True"})
        elif msg.text and msg.text.startswith("NOTA|"):
            _, texto = msg.text.split("|", 1)
            data["notas"].append(texto)
        elif msg.text and msg.text.startswith("ARCHIVO|"):
            _, file_id, caption = msg.text.split("|", 2)
            data["archivos"].append({"file_id": file_id, "caption": caption})

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tarea", nueva_tarea))
    app.add_handler(CommandHandler("nota", nota))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.PHOTO, guardar_archivo))
    app.add_handler(CallbackQueryHandler(manejar_fecha, pattern="^fecha_"))

    # Reconstruir memoria al iniciar
    app.post_init = lambda _: reconstruir_memoria(app)

    app.run_polling()

if __name__ == "__main__":
    main()
