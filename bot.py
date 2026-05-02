import os
from pyrogram import Client, filters

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # -100... o @username

# Memoria interna ligera: solo nombres y file_id
data = {"notas": [], "archivos": []}

app = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# --- Bienvenida ---
@app.on_message(filters.command("start"))
async def start(client, message):
    texto = (
        "👋 Bienvenido al Bot de Productividad.\n\n"
        "📒 Notas:\n"
        "• /nota <texto>\n"
        "• /buscar <palabra>\n\n"
        "📂 Archivos:\n"
        "• Envía un archivo → se guarda en el canal\n"
        "• /lista → muestra lo que el bot tiene guardado\n"
        "• Escribe el número → descarga\n"
        "• Escribe 'del <número>' → elimina también del canal"
    )
    await message.reply_text(texto)

# --- Guardar notas ---
@app.on_message(filters.command("nota"))
async def nota(client, message):
    if len(message.command) < 2:
        await message.reply_text("✍️ Escribe el texto después de /nota")
        return
    texto = " ".join(message.command[1:])
    data["notas"].append(texto)
    enviado = await client.send_message(CHANNEL_ID, f"NOTA|{texto}")
    await message.reply_text(f"✅ Nota guardada: {texto}")

# --- Guardar archivos ---
@app.on_message(filters.document | filters.video | filters.photo)
async def guardar_archivo(client, message):
    caption = message.caption or f"Archivo {len(data['archivos'])+1}"

    if message.document:
        enviado = await client.send_document(CHANNEL_ID, message.document.file_id, caption=caption)
        nombre = message.document.file_name or caption
    elif message.video:
        enviado = await client.send_video(CHANNEL_ID, message.video.file_id, caption=caption)
        nombre = message.video.file_name or caption
    elif message.photo:
        enviado = await client.send_photo(CHANNEL_ID, message.photo.file_id, caption=caption)
        nombre = "Imagen"

    data["archivos"].append({"msg_id": enviado.id, "caption": nombre})
    await message.reply_text(f"📂 Archivo guardado: {nombre}")

# --- Lista interna ---
@app.on_message(filters.command("lista"))
async def lista(client, message):
    texto = ""
    if data["archivos"]:
        texto += "📂 Archivos guardados:\n"
        for i, f in enumerate(data["archivos"], start=1):
            texto += f"{i}. {f['caption']}\n"
    if data["notas"]:
        texto += "\n📋 Notas:\n"
        for n in data["notas"]:
            texto += f"- {n}\n"

    if texto:
        texto += "\n👉 Escribe el número para descargar.\n👉 O escribe 'del <número>' para eliminar."
        await message.reply_text(texto)
    else:
        await message.reply_text("📭 No hay contenido guardado en esta sesión.")

# --- Manejo de selección ---
@app.on_message(filters.text)
async def manejar_archivos(client, message):
    txt = message.text.strip()

    # Descargar
    if txt.isdigit():
        indice = int(txt) - 1
        if 0 <= indice < len(data["archivos"]):
            archivo = data["archivos"][indice]
            await client.forward_messages(message.chat.id, CHANNEL_ID, archivo["msg_id"])
        else:
            await message.reply_text("❌ Número inválido. Usa /lista para ver la lista.")

    # Eliminar
    elif txt.lower().startswith("del "):
        try:
            num = int(txt.split()[1]) - 1
            if 0 <= num < len(data["archivos"]):
                archivo = data["archivos"].pop(num)
                await client.delete_messages(CHANNEL_ID, archivo["msg_id"])
                await message.reply_text(f"🗑️ Archivo eliminado: {archivo['caption']}")
            else:
                await message.reply_text("❌ Número inválido. Usa /lista para ver la lista.")
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

app.run()
