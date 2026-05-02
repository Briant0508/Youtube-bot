import os
from pyrogram import Client, filters

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # -100... o @username

# Memoria interna ligera
data = {"notas": [], "archivos": []}

app = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# --- Bienvenida ---
@app.on_message(filters.command("start"))
async def start(client, message):
    texto = (
        "👋 Bienvenido al Bot.\n\n"
        "📒 Notas:\n"
        "• /nota <texto>\n"
        "• /buscar <palabra>\n\n"
        "📂 Archivos:\n"
        "• Envía un archivo → se guarda en el canal\n"
        "• /lista → muestra lo que el bot tiene guardado\n"
        "• Escribe el número → descarga\n"
        "• Escribe 'del <número>' → elimina también del canal\n\n"
        "💾 Persistencia:\n"
        "• /exportar → genera un código con toda la memoria\n"
        "• /importar → responde al código para restaurar"
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
    await client.send_message(CHANNEL_ID, f"NOTA|{texto}")
    await message.reply_text(f"✅ Nota guardada: {texto}")

# --- Guardar archivos ---
@app.on_message(filters.document | filters.video | filters.photo)
async def guardar_archivo(client, message):
    caption = message.caption or f"Archivo {len(data['archivos'])+1}"

    if message.document:
        enviado = await client.send_document(CHANNEL_ID, message.document.file_id, caption=caption)
        nombre = message.document.file_name or caption
        file_id = message.document.file_id
    elif message.video:
        enviado = await client.send_video(CHANNEL_ID, message.video.file_id, caption=caption)
        nombre = message.video.file_name or caption
        file_id = message.video.file_id
    elif message.photo:
        enviado = await client.send_photo(CHANNEL_ID, message.photo.file_id, caption=caption)
        nombre = "Imagen"
        file_id = message.photo.file_id

    data["archivos"].append({"msg_id": enviado.id, "caption": nombre, "file_id": file_id})
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

# --- Exportar memoria como código ---
@app.on_message(filters.command("exportar"))
async def exportar(client, message):
    contenido = ["MEMORIA_START"]
    for n in data["notas"]:
        contenido.append(f"NOTA|{n}")
    for f in data["archivos"]:
        contenido.append(f"ARCHIVO|{f['caption']}|{f['file_id']}")
    contenido.append("MEMORIA_END")

    codigo = "\n".join(contenido)
    await message.reply_text(f"💾 Copia este código y guárdalo:\n\n{codigo}")

# --- Importar memoria desde código ---
@app.on_message(filters.command("importar"))
async def importar(client, message):
    if not message.reply_to_message or "MEMORIA_START" not in message.reply_to_message.text:
        await message.reply_text("❌ Debes responder al mensaje que contiene el código de memoria.")
        return

    lineas = message.reply_to_message.text.strip().splitlines()
    data["notas"].clear()
    data["archivos"].clear()

    for linea in lineas:
        if linea.startswith("NOTA|"):
            _, texto = linea.split("|", 1)
            data["notas"].append(texto)
        elif linea.startswith("ARCHIVO|"):
            _, nombre, file_id = linea.split("|", 2)
            data["archivos"].append({"msg_id": None, "caption": nombre, "file_id": file_id})

    await message.reply_text("✅ Memoria restaurada desde el código.")

app.run()
