import json
import os
import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")
DATA_FILE = "data.json"

# --- Cargar datos ---
def cargar_datos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"tareas": [], "notas": [], "archivos": []}

def guardar_datos(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = cargar_datos()

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
        "Puedes enviar documentos, fotos o videos y los guardaré en data.json."
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
    guardar_datos(data)
    await query.edit_message_text(f"✅ Tarea añadida: *{texto}* (vence {fecha_str})")

# --- Listado de tareas ---
async def listado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not data["tareas"]:
        await update.message.reply_text("📭 No tienes tareas pendientes.")
        return
    for i, t in enumerate(data["tareas"], start=1):
        await update.message.reply_text(
            f"{i}. {t['texto']} - vence {t['fecha']} [{'✔️' if t['completada'] else '❌'}]"
        )

# --- Notas ---
async def nota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("✍️ Escribe el texto después de /nota")
        return
    texto = " ".join(context.args)
    data["notas"].append({"texto": texto})
    guardar_datos(data)
    await update.message.reply_text(f"✅ Nota guardada: {texto}")

# --- Guardar archivos ---
async def guardar_archivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    archivo = update.message.document or update.message.video or update.message.photo[-1]
    entrada = {"file_id": archivo.file_id, "caption": update.message.caption or ""}
    data["archivos"].append(entrada)
    guardar_datos(data)
    await update.message.reply_text("📂 Archivo guardado correctamente.")

# --- Listar archivos ---
async def archivos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not data["archivos"]:
        await update.message.reply_text("📭 No tienes archivos guardados.")
        return
    for i, f in enumerate(data["archivos"], start=1):
        await update.message.reply_text(f"{i}. {f['caption']}")

# --- Buscar ---
async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🔍 Uso: /buscar <palabra>")
        return
    palabra = " ".join(context.args).lower()

    notas = [n["texto"] for n in data["notas"] if palabra in n["texto"].lower()]
    archivos = [f for f in data["archivos"] if palabra in f["caption"].lower()]

    if not notas and not archivos:
        await update.message.reply_text("❌ No encontré coincidencias.")
        return

    if notas:
        texto = "📋 Notas encontradas:\n" + "\n".join([f"- {n}" for n in notas])
        await update.message.reply_text(texto)

    if archivos:
        texto = "📂 Archivos encontrados:\n" + "\n".join([f"- {f['caption']}" for f in archivos])
        await update.message.reply_text(texto)

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tarea", nueva_tarea))
    app.add_handler(CommandHandler("listado", listado))
    app.add_handler(CommandHandler("nota", nota))
    app.add_handler(CommandHandler("buscar", buscar))
    app.add_handler(CommandHandler("archivos", archivos))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.PHOTO, guardar_archivo))
    app.add_handler(CallbackQueryHandler(manejar_fecha, pattern="^fecha_"))

    app.run_polling()

if __name__ == "__main__":
    main()
