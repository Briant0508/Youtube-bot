import os
import datetime
from pyrogram import Client, filters

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # Puede ser -100... o @username

data = {"tareas": [], "notas": [], "archivos": []}

app = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# --- Bienvenida ---
@app.on_message(filters.command("start"))
async def start(client, message):
    texto = (
        "👋 Bienvenido al Bot de Productividad.\n\n"
        "📅 Tareas:\n"
        "• /tarea <texto>\n"
        "• /listado\n\n"
        "📒 Notas:\n"
        "• /nota <texto>\n"
        "• /buscar <palabra>\n\n"
        "📂 Archivos:\n"
        "• /archivos → lista numerada\n"
        "• Luego escribe el número para descargar\n"
        "• O escribe 'del <número>' para eliminar\n\n"
        "🔄 /reconstruir → recuperar memoria desde el canal"
    )
    await message.reply_text(texto)

# --- Tareas ---
@app.on_message(filters.command("tarea"))
async def nueva_tarea(client, message):
    if len(message.command) < 2:
        await message.reply_text("✍️ Escribe el nombre de la tarea después de /tarea")
        return
    texto = " ".join(message.command[1:])
    fecha = datetime.date.today().strftime("%d-%m-%Y")
    tarea = {"texto": texto, "fecha": fecha, "completada": False}
    data["tareas"].append(tarea)
    await client.send_message(CHANNEL_ID, f"TAREA|{texto}|{fecha}|False")
    await message.reply_text(f"✅ Tarea añadida: {texto} (vence {fecha})")

@app.on_message(filters.command("listado"))
async def listado(client, message):
    if not data["tareas"]:
        await message.reply_text("📭 No tienes tareas pendientes.")
        return
    texto = "\n".join([f"{i+1}. {t['texto']} - {t['fecha']} [{'✔️' if t['completada'] else '❌'}]" for i, t in enumerate(data["tareas"])])
    await message.reply_text(texto)

# --- Notas ---
@app.on_message(filters.command("nota"))
async def nota(client, message):
    if len(message.command) < 2:
        await message.reply_text("✍️ Escribe el texto después de /nota")
        return
    texto = " ".join(message.command[1:])
    data["notas"].append(texto)
    await client.send_message(CHANNEL_ID, f"NOTA|{texto}")
    await message.reply_text(f"✅ Nota guardada: {texto}")

# --- Guardar archivos ---
@app.on_message(filters.document | filters.video | filters.photo)
async def guardar_archivo(client, message):
    archivo = message.document or message.video or message.photo
    entrada = {"file_id": archivo.file_id, "caption": message.caption or f"Archivo {len(data['archivos'])+1}"}
    data["archivos"].append(entrada)
    await client.send_message(CHANNEL_ID, f"ARCHIVO|{entrada['file_id']}|{entrada['caption']}")
    await message.reply_text("📂 Archivo guardado correctamente.")

# --- Listar archivos ---
@app.on_message(filters.command("archivos"))
async def archivos(client, message):
    if not data["archivos"]:
        await message.reply_text("📭 No tienes archivos guardados.")
        return
    texto = "📂 Archivos guardados:\n"
    for i, f in enumerate(data["archivos"], start=1):
        texto += f"{i}. Archivo: {f['caption']}\n"
    texto += "\n👉 Escribe el número para descargar.\n👉 O escribe 'del <número>' para eliminar."
    await message.reply_text(texto)

# --- Descargar o eliminar por número ---
@app.on_message(filters.text)
async def manejar_archivos(client, message):
    txt = message.text.strip()
    # Descargar
    if txt.isdigit():
        indice = int(txt) - 1
        if 0 <= indice < len(data["archivos"]):
            archivo = data["archivos"][indice]
            if "file_id" in archivo:
    try:
        # Intentar como documento
        await message.reply_document(archivo["file_id"], caption=archivo["caption"])
    except:
        try:
            # Intentar como video
            await message.reply_video(archivo["file_id"], caption=archivo["caption"])
        except:
            try:
                # Intentar como foto
                await message.reply_photo(archivo["file_id"], caption=archivo["caption"])
            except:
                await message.reply_text("❌ No pude enviar el archivo, revisa el tipo.")
        else:
            await message.reply_text("❌ Número inválido. Usa /archivos para ver la lista.")
    # Eliminar
    elif txt.lower().startswith("del "):
        try:
            num = int(txt.split()[1]) - 1
            if 0 <= num < len(data["archivos"]):
                archivo = data["archivos"].pop(num)
                await message.reply_text(f"🗑️ Archivo eliminado: {archivo['caption']}")
            else:
                await message.reply_text("❌ Número inválido. Usa /archivos para ver la lista.")
        except:
            await message.reply_text("❌ Uso: del <número>")

# --- Buscar ---
@app.on_message(filters.command("buscar"))
async def buscar(client, message):
    if len(message.command) < 2:
        await message.reply_text("🔍 Uso: /buscar <palabra>")
        return
    palabra = " ".join(message.command[1:]).lower()
    notas = [n for n in data["notas"] if palabra in n.lower()]
    archivos = [f for f in data["archivos"] if palabra in f["caption"].lower()]

    if not notas and not archivos:
        await message.reply_text("❌ No encontré coincidencias.")
        return

    if notas:
        texto = "📋 Notas encontradas:\n" + "\n".join([f"- {n}" for n in notas])
        await message.reply_text(texto)
    if archivos:
        texto = "📂 Archivos encontrados:\n" + "\n".join([f"- {f['caption']}" for f in archivos])
        await message.reply_text(texto)

# --- Reconstrucción ---
@app.on_message(filters.command("reconstruir"))
async def reconstruir(client, message):
    async for msg in client.get_chat_history(CHANNEL_ID, limit=200):
        if msg.text and msg.text.startswith("TAREA|"):
            _, texto, fecha, estado = msg.text.split("|")
            data["tareas"].append({"texto": texto, "fecha": fecha, "completada": estado == "True"})
        elif msg.text and msg.text.startswith("NOTA|"):
            _, texto = msg.text.split("|", 1)
            data["notas"].append(texto)
        elif msg.text and msg.text.startswith("ARCHIVO|"):
            _, file_id, caption = msg.text.split("|", 2)
            data["archivos"].append({"file_id": file_id, "caption": caption})
    await message.reply_text("✅ Memoria reconstruida desde el canal.")

# --- Comando de prueba ---
@app.on_message(filters.command("test"))
async def test(client, message):
    await client.send_message(CHANNEL_ID, "✅ El bot puede escribir en el canal configurado.")

app.run()
