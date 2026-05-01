import os
import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TOKEN")
tareas = []

# --- Mensaje de bienvenida ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "👋 ¡Bienvenido al Bot de Recordatorios!\n\n"
        "Este bot te ayuda a organizar tus tareas con fechas límite.\n\n"
        "📌 Comandos principales:\n"
        "• /tarea <nombre> → Añadir una tarea y elegir fecha límite.\n"
        "• /listado → Ver todas tus tareas pendientes.\n\n"
        "Cuando añadas una tarea, recibirás avisos:\n"
        "⏳ 3 días antes de la fecha límite\n"
        "⚠️ El mismo día de vencimiento\n"
        "🔔 Recordatorios diarios si no la completas."
    )
    await update.message.reply_text(texto)

# --- Añadir tarea con selector de fecha ---
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
    _, fecha_str, texto = query.data.split("_", 2)
    fecha = datetime.datetime.strptime(fecha_str, "%Y-%m-%d")
    tarea = {"texto": texto, "fecha": fecha, "completada": False}
    tareas.append(tarea)

    # Aviso 3 días antes
    recordatorio = fecha - datetime.timedelta(days=3)
    context.job_queue.run_once(aviso_tarea, recordatorio, data=(query.message.chat_id, tarea))

    # Aviso en la fecha límite
    context.job_queue.run_once(aviso_limite, fecha, data=(query.message.chat_id, tarea))

    await query.edit_message_text(f"✅ Tarea añadida: *{texto}* (vence {fecha_str})")

# --- Recordatorios ---
async def aviso_tarea(context: ContextTypes.DEFAULT_TYPE):
    chat_id, tarea = context.job.data
    if not tarea["completada"]:
        await context.bot.send_message(chat_id=chat_id,
            text=f"⏳ Te quedan 3 días para completar: *{tarea['texto']}*")

async def aviso_limite(context: ContextTypes.DEFAULT_TYPE):
    chat_id, tarea = context.job.data
    if not tarea["completada"]:
        await context.bot.send_message(chat_id=chat_id,
            text=f"⚠️ Hoy vence la tarea: *{tarea['texto']}*")
        # Recordatorio diario si no se completa
        context.job_queue.run_daily(aviso_diario, time=datetime.time(hour=9),
                                    data=(chat_id, tarea))

async def aviso_diario(context: ContextTypes.DEFAULT_TYPE):
    chat_id, tarea = context.job.data
    if not tarea["completada"]:
        hoy = datetime.datetime.now().date()
        if hoy > tarea["fecha"].date():
            await context.bot.send_message(chat_id=chat_id,
                text=f"❌ Tarea *{tarea['texto']}* no cumplida. Plazo caducado.")
        else:
            await context.bot.send_message(chat_id=chat_id,
                text=f"🔔 Recordatorio: aún no completaste *{tarea['texto']}*")

# --- Listado con botones ---
async def listado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not tareas:
        await update.message.reply_text("📭 No tienes tareas pendientes.")
        return
    for i, t in enumerate(tareas, start=1):
        botones = [
            [InlineKeyboardButton("✅ Completar", callback_data=f"completar_{i-1}")],
            [InlineKeyboardButton("🗑️ Eliminar", callback_data=f"eliminar_{i-1}")]
        ]
        reply_markup = InlineKeyboardMarkup(botones)
        await update.message.reply_text(
            f"{i}. {t['texto']} - vence {t['fecha'].strftime('%d-%m-%Y')} [{'✔️' if t['completada'] else '❌'}]",
            reply_markup=reply_markup
        )

async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    accion, indice = query.data.split("_")
    indice = int(indice)
    if accion == "completar":
        tareas[indice]["completada"] = True
        await query.edit_message_text(f"🎉 Tarea completada: *{tareas[indice]['texto']}*")
    elif accion == "eliminar":
        tarea = tareas.pop(indice)
        await query.edit_message_text(f"🗑️ Tarea eliminada: *{tarea['texto']}*")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tarea", nueva_tarea))
    app.add_handler(CommandHandler("listado", listado))
    app.add_handler(CallbackQueryHandler(manejar_fecha, pattern="^fecha_"))
    app.add_handler(CallbackQueryHandler(manejar_botones))

    app.run_polling()

if __name__ == "__main__":
    main()
