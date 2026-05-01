import os
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")

# --- Inicializar Firebase ---
# Sube tu archivo de credenciales JSON a HostingGuru y pon su ruta aquí
cred = credentials.Certificate("firebase-cred.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

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
        "Puedes enviar documentos, fotos o videos (hasta 2 GB) y los guardaré en Firebase."
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
    db.collection("tareas").add(tarea)
    await query.edit_message_text(f"✅ Tarea añadida: *{texto}* (vence {fecha_str})")

# --- Listado de tareas ---
async def listado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    docs = db.collection("tareas").stream()
    tareas = [doc.to_dict() for doc in docs]
    if not tareas:
        await update.message.reply_text("📭 No tienes tareas pendientes.")
        return
    for i, t in enumerate(tareas, start=1):
        botones = [
            [InlineKeyboardButton("✅ Completar", callback_data=f"completar_{doc.id}")],
            [InlineKeyboardButton("🗑️ Eliminar", callback_data=f"eliminar_{doc.id}")]
        ]
        reply_markup = InlineKeyboardMarkup(botones)
        await update.message.reply_text(
            f"{i}. {t['texto']} - vence {t['fecha']} [{'✔️' if t['completada'] else '❌'}]",
            reply_markup=reply_markup
        )

async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    accion, doc_id = query.data.split("_")
    ref = db.collection("tareas").document(doc_id)
    tarea = ref.get().to_dict()
    if accion == "completar":
        ref.update({"completada": True})
        await query.edit_message_text(f"🎉 Tarea completada: *{tarea['texto']}*")
    elif accion == "eliminar":
        ref.delete()
        await query.edit_message_text(f"🗑️ Tarea eliminada: *{tarea['texto']}*")

# --- Notas ---
async def nota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("✍️ Escribe el texto después de /nota")
        return
    texto = " ".join(context.args)
    db.collection("notas").add({"texto": texto})
    await update.message.reply_text(f"✅ Nota guardada: {texto}")

# --- Guardar archivos ---
async def guardar_archivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    archivo = update.message.document or update.message.video or update.message.photo[-1]
    entrada = {"file_id": archivo.file_id, "caption": update.message.caption or ""}
    db.collection("archivos").add(entrada)
    await update.message.reply_text("📂 Archivo guardado correctamente.")

# --- Listar archivos ---
async def archivos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    docs = db.collection("archivos").stream()
    archivos = [doc for doc in docs]
    if not archivos:
        await update.message.reply_text("📭 No tienes archivos guardados.")
        return
    botones = []
    for i, doc in enumerate(archivos, start=1):
        f = doc.to_dict()
        botones.append([
            InlineKeyboardButton(f"📂 Archivo {i} {f['caption']}", callback_data=f"descargar_{doc.id}"),
            InlineKeyboardButton("🗑️ Eliminar", callback_data=f"eliminar_{doc.id}")
        ])
    await update.message.reply_text("📂 Archivos guardados:", reply_markup=InlineKeyboardMarkup(botones))

# --- Descargar o eliminar archivo ---
async def manejar_archivos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    accion, doc_id = query.data.split("_")
    ref = db.collection("archivos").document(doc_id)
    archivo = ref.get().to_dict()
    if accion == "descargar":
        await query.message.reply_document(document=archivo["file_id"])
    elif accion == "eliminar":
        ref.delete()
        await query.edit_message_text(f"🗑️ Archivo eliminado: {archivo['caption']}")

# --- Buscar ---
async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🔍 Uso: /buscar <palabra>")
        return
    palabra = " ".join(context.args).lower()

    notas = [doc.to_dict()["texto"] for doc in db.collection("notas").stream() if palabra in doc.to_dict()["texto"].lower()]
    archivos = [doc for doc in db.collection("archivos").stream() if palabra in doc.to_dict()["caption"].lower()]

    if not notas and not archivos:
        await update.message.reply_text("❌ No encontré coincidencias.")
        return

    if notas:
        texto = "📋 Notas encontradas:\n" + "\n".join([f"- {n}" for n in notas])
        await update.message.reply_text(texto)

    if archivos:
        botones = []
        for i, doc in enumerate(archivos, start=1):
            f = doc.to_dict()
            botones.append([
                InlineKeyboardButton(f"📂 Archivo {i} {f['caption']}", callback_data=f"descargar_{doc.id}"),
                InlineKeyboardButton("🗑️ Eliminar", callback_data=f"eliminar_{doc.id}")
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
    app.add_handler(CallbackQueryHandler(manejar_archivos, pattern="^(descargar|eliminar)_"))

    app.run_polling()

if __name__ == "__main__":
    main()
