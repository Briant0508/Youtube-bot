import os
import datetime
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")
DATA_FILE = "data.json"

# --- Cargar datos ---
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {"tareas": [], "notas": [], "archivos": []}

def guardar_datos():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

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
        "Puedes enviar documentos, fotos o videos (hasta 2 GB) y los guardaré."
    )
    await update.message.reply_text(texto)

# --- Añadir tarea ---
async def nueva_tarea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("✍️ Escribe el nombre de la tarea después de /tarea")
        return
    texto = " ".join(context.args)
    context.user_data["tarea_texto"] = texto

    hoy = datetime.date.today()
    botones = []
    for i in range(10):
        dia = hoy + datetime.timedelta(days=i)
        botones.append([InlineKeyboardButton(dia.strftime("%d-%m-%Y"), callback_data=f"fecha_{dia}_{texto}")])
    reply_markup = InlineKeyboardMarkup(botones)
    await update.message.reply_text("📅 Selecciona la fecha límite:", reply_markup=reply_markup)

async def manejar_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # <-- evita el mensaje "El bot no responde"
    _, fecha_str, texto = query.data.split("_", 2)
    fecha = datetime.datetime.strptime(fecha_str, "%Y-%m-%d")
    tarea = {"texto": texto, "fecha": fecha_str, "completada": False}
    data["tareas"].append(tarea)
    guardar_datos()
    await query.edit_message_text(f"✅ Tarea añadida: *{texto}* (vence {fecha_str})")

# --- Listado de tareas ---
async def listado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not data["tareas"]:
        await update.message.reply_text("📭 No tienes tareas pendientes.")
        return
    for i, t in enumerate(data["tareas"], start=1):
        botones = [
            [InlineKeyboardButton("✅ Completar", callback_data=f"completar_{i-1}")],
            [InlineKeyboardButton("🗑️ Eliminar", callback_data=f"eliminar_{i-1}")]
        ]
        reply_markup = InlineKeyboardMarkup(botones)
        await update.message.reply_text(
            f"{i}. {t['texto']} - vence {t['fecha']} [{'✔️' if t['completada'] else '❌'}]",
            reply_markup=reply_markup
        )

async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    accion, indice = query.data.split("_")
    indice = int(indice)
    if accion == "completar":
        data["tareas"][indice]["completada"] = True
        guardar_datos()
        await query.edit_message_text(f"🎉 Tarea completada: *{data['tareas'][indice]['texto']}*")
    elif accion == "eliminar":
        tarea = data["tareas"].pop(indice)
        guardar_datos()
        await query.edit_message_text(f"🗑️ Tarea eliminada: *{tarea['texto']}*")

# --- Notas ---
async def nota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("✍️ Escribe el texto después de /nota")
        return
    texto = " ".join(context.args)
    data["notas"].append(texto)
    guardar_datos()
    await update.message.reply_text(f"✅ Nota guardada: {texto}")

# --- Guardar archivos ---
async def guardar_archivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    archivo = update.message.document or update.message.video or update.message.photo[-1]
    entrada = {"file_id": archivo.file_id, "caption": update.message.caption or ""}
    data["archivos"].append(entrada)
    guardar_datos()
    await update.message.reply_text("📂 Archivo guardado correctamente.")

# --- Listar archivos ---
async def archivos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not data["archivos"]:
        await update.message.reply_text("📭 No tienes archivos guardados.")
        return
    botones = []
    for i, f in enumerate(data["archivos"], start=1):
        botones.append([
            InlineKeyboardButton(f"📂 Archivo {i} {f['caption']}", callback_data=f"descargar_{i-1}"),
            InlineKeyboardButton("🗑️ Eliminar", callback_data=f"eliminar_archivo_{i-1}")
        ])
    await update.message.reply_text("📂 Archivos guardados:", reply_markup=InlineKeyboardMarkup(botones))

# --- Descargar o eliminar archivo ---
async def manejar_archivos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    accion, tipo, indice = query.data.split("_")
    indice = int(indice)
    if accion == "descargar":
        await query.message.reply_document(document=data["archivos"][indice]["file_id"])
    elif accion == "eliminar":
        archivo = data["archivos"].pop(indice)
        guardar_datos()
        await query.edit_message_text(f"🗑️ Archivo eliminado: {archivo['caption']}")

# --- Buscar ---
async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🔍 Uso: /buscar <palabra>")
        return
    palabra = " ".join(context.args).lower()

    resultados_notas = [n for n in data["notas"] if palabra in n.lower()]
    resultados_archivos = [f for f in data["archivos"] if palabra in f["caption"].lower()]

    if not resultados_notas and not resultados_archivos:
        await update.message.reply_text("❌ No encontré coincidencias.")
        return

    if resultados_notas:
        texto = "📋 Notas encontradas:\n" + "\n".join([f"- {n}" for n in resultados_notas])
        await update.message.reply_text(texto)

    if resultados_archivos:
        botones = []
        for i, f in enumerate(resultados_archivos, start=1):
            botones.append([
                InlineKeyboardButton(f"📂 Archivo {i} {f['caption']}", callback_data=f"descargar_{data['archivos'].index(f)}"),
                InlineKeyboardButton("🗑️ Eliminar", callback_data=f"eliminar_archivo_{data['archivos'].index(f)}")
            ])
        await update.message.reply_text("📂 Archivos encontrados:", reply_markup=InlineKeyboardMarkup(botones))

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
    app.add_handler(CallbackQueryHandler(manejar_botones, pattern="^(completar|eliminar)_"))
    app.add_handler(CallbackQueryHandler(manejar_archivos, pattern="^(descargar|eliminar_archivo)_"))

    app.run_polling()

if __name__ == "__main__":
    main()
