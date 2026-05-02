import os
from pyrogram import Client, filters

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_INPUT = os.getenv("CHANNEL_ID")  # Puede ser -100xxx o @username

# Convertir CHANNEL_ID correctamente
if CHANNEL_INPUT.startswith('@'):
    CHANNEL_ID = CHANNEL_INPUT  # Es username, mantener como string
else:
    CHANNEL_ID = int(CHANNEL_INPUT)  # Es ID numérico

# Archivo de persistencia local
DATA_FILE = "bot_data.json"

# Cargar datos guardados al iniciar
def cargar_datos():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error cargando datos: {e}")
    return {"notas": [], "archivos": []}

# Guardar datos inmediatamente
def guardar_datos():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ Datos guardados: {len(data['notas'])} notas, {len(data['archivos'])} archivos")
    except Exception as e:
        print(f"Error guardando datos: {e}")

# Inicializar datos
data = cargar_datos()

app = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

@app.on_message(filters.command("start"))
async def start(client, message):
    # Verificar si el bot puede acceder al canal
    try:
        await client.get_chat(CHANNEL_ID)
        canal_ok = "✅"
    except:
        canal_ok = "❌"
    
    texto = (
        "👋 **Bot para HostingGuru**\n\n"
        f"📊 **Estado:**\n"
        f"📋 Notas: {len(data['notas'])}\n"
        f"📂 Archivos: {len(data['archivos'])}\n"
        f"📡 Canal: {canal_ok}\n\n"
        "📒 **Comandos:**\n"
        "• `/nota <texto>` - Guardar nota\n"
        "• `/lista` - Ver contenido\n"
        "• `/buscar <palabra>` - Buscar\n"
        "• `/exportar` - **Hacer backup**\n"
        "• `/importar` - Restaurar backup\n"
        "• `/status` - Ver estado\n\n"
        "⚠️ **Importante:**\n"
        "• Usa `/exportar` regularmente\n"
        "• Los archivos están SEGUROS en el canal"
    )
    await message.reply_text(texto)

@app.on_message(filters.command("nota"))
async def nota(client, message):
    if len(message.command) < 2:
        await message.reply_text("✍️ Uso: `/nota <texto>`\nEjemplo: `/nota Comprar leche`")
        return
    
    texto = " ".join(message.command[1:])
    data["notas"].append(texto)
    guardar_datos()
    
    try:
        await client.send_message(CHANNEL_ID, f"NOTA|{texto}")
        await message.reply_text(f"✅ Nota guardada: `{texto}`")
    except Exception as e:
        await message.reply_text(f"✅ Nota guardada localmente\n⚠️ Error en canal: `{e}`")

@app.on_message(filters.document | filters.video | filters.photo)
async def guardar_archivo(client, message):
    caption = message.caption or f"Archivo {len(data['archivos'])+1}"
    
    try:
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
            nombre = f"Imagen_{len(data['archivos'])+1}"
            file_id = message.photo.file_id

        data["archivos"].append({
            "msg_id": enviado.id,
            "caption": nombre,
            "file_id": file_id
        })
        guardar_datos()
        await message.reply_text(f"📂 **Archivo guardado:** `{nombre}`")
    
    except Exception as e:
        await message.reply_text(f"❌ Error: `{e}`\n\n¿El bot es admin del canal?")

@app.on_message(filters.command("lista"))
async def lista(client, message):
    if not data["archivos"] and not data["notas"]:
        await message.reply_text("📭 **No hay contenido guardado**\n\nEnvía archivos o usa `/nota` para comenzar.")
        return
    
    texto = ""
    
    if data["archivos"]:
        texto += "**📂 Archivos guardados:**\n"
        for i, f in enumerate(data["archivos"][:20], 1):
            nombre = f['caption'][:50]
            texto += f"`{i}.` {nombre}\n"
        if len(data["archivos"]) > 20:
            texto += f"\n*... y {len(data['archivos'])-20} más*\n"
    
    if data["notas"]:
        texto += "\n**📋 Notas:**\n"
        for i, n in enumerate(data["notas"][:15], 1):
            nota = n[:60]
            texto += f"`{i}.` {nota}\n"
        if len(data["notas"]) > 15:
            texto += f"\n*... y {len(data['notas'])-15} más*\n"

    if texto:
        texto += "\n\n👉 Escribe el `número` para descargar\n👉 Escribe `del <número>` para eliminar"
        await message.reply_text(texto)

@app.on_message(filters.text & ~filters.command(["start", "nota", "lista", "buscar", "exportar", "importar", "limpiar", "status"]))
async def manejar_archivos(client, message):
    txt = message.text.strip()

    if txt.isdigit():
        indice = int(txt) - 1
        if 0 <= indice < len(data["archivos"]):
            archivo = data["archivos"][indice]
            try:
                await client.copy_message(
                    message.chat.id,
                    CHANNEL_ID,
                    archivo["msg_id"]
                )
                await message.reply_text(f"✅ **Descargado:** `{archivo['caption']}`")
            except Exception as e:
                await message.reply_text(f"❌ Error: `{e}`")
        else:
            await message.reply_text("❌ **Número inválido.** Usa `/lista`")

    elif txt.lower().startswith("del "):
        try:
            num = int(txt.split()[1]) - 1
            if 0 <= num < len(data["archivos"]):
                archivo = data["archivos"].pop(num)
                guardar_datos()
                try:
                    await client.delete_messages(CHANNEL_ID, archivo["msg_id"])
                    await message.reply_text(f"🗑️ **Eliminado:** `{archivo['caption']}`")
                except:
                    await message.reply_text(f"🗑️ **Eliminado de la lista** (no del canal)")
            else:
                await message.reply_text("❌ **Número inválido.** Usa `/lista`")
        except:
            await message.reply_text("❌ **Uso:** `del <número>`")

@app.on_message(filters.command("buscar"))
async def buscar(client, message):
    if len(message.command) < 2:
        await message.reply_text("🔍 **Uso:** `/buscar <palabra>`")
        return
    
    palabra = " ".join(message.command[1:]).lower()
    
    notas_encontradas = [n for n in data["notas"] if palabra in n.lower()]
    archivos_encontrados = [f for f in data["archivos"] if palabra in f["caption"].lower()]

    if not notas_encontradas and not archivos_encontrados:
        await message.reply_text(f"❌ No encontré `{palabra}`")
        return

    respuesta = f"🔍 **Resultados para:** `{palabra}`\n\n"
    
    if notas_encontradas:
        respuesta += "**📋 Notas:**\n"
        for nota in notas_encontradas[:5]:
            respuesta += f"• {nota[:100]}\n"
        respuesta += "\n"
    
    if archivos_encontrados:
        respuesta += "**📂 Archivos:**\n"
        for archivo in archivos_encontrados[:5]:
            respuesta += f"• {archivo['caption'][:100]}\n"
    
    await message.reply_text(respuesta)

@app.on_message(filters.command("exportar"))
async def exportar(client, message):
    import json, base64, zlib
    
    status_msg = await message.reply_text("⏳ **Generando backup...**")
    
    try:
        export_data = {
            "version": "2.0",
            "notas": data["notas"],
            "archivos": [
                {"caption": f["caption"], "file_id": f["file_id"]}
                for f in data["archivos"]
            ]
        }
        
        json_str = json.dumps(export_data, ensure_ascii=False)
        compressed = zlib.compress(json_str.encode('utf-8'))
        codigo = base64.b64encode(compressed).decode('ascii')
        
        await status_msg.delete()
        await message.reply_text(
            f"💾 **Backup**\n\n"
            f"📋 Notas: {len(data['notas'])}\n"
            f"📂 Archivos: {len(data['archivos'])}\n\n"
            f"```\n{codigo}\n```\n\n"
            f"⚠️ **GUARDA ESTE CÓDIGO**\n"
            f"Para restaurar: Responde a ESTE mensaje con `/importar`"
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: `{str(e)[:200]}`")

@app.on_message(filters.command("importar"))
async def importar(client, message):
    import json, base64, zlib
    
    if not message.reply_to_message:
        await message.reply_text("❌ Responde al mensaje que contiene el código de backup.")
        return
    
    status_msg = await message.reply_text("⏳ **Restaurando...**")
    
    try:
        codigo_texto = message.reply_to_message.text
        if "```" in codigo_texto:
            codigo_texto = codigo_texto.split("```")[1].strip()
        
        compressed = base64.b64decode(codigo_texto)
        json_str = zlib.decompress(compressed).decode('utf-8')
        import_data = json.loads(json_str)
        
        data["notas"] = import_data.get("notas", [])
        data["archivos"] = [
            {"msg_id": None, "caption": a["caption"], "file_id": a["file_id"]}
            for a in import_data.get("archivos", [])
        ]
        guardar_datos()
        
        await status_msg.edit_text(
            f"✅ **Restaurado**\n\n"
            f"📋 Notas: {len(data['notas'])}\n"
            f"📂 Archivos: {len(data['archivos'])}"
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: `{str(e)[:200]}`")

@app.on_message(filters.command("status"))
async def status(client, message):
    await message.reply_text(
        f"📊 **Estado**\n\n"
        f"📋 Notas: `{len(data['notas'])}`\n"
        f"📂 Archivos: `{len(data['archivos'])}`\n"
        f"💾 Datos guardados: `{'Sí' if os.path.exists(DATA_FILE) else 'No'}`\n\n"
        f"💡 Usa `/exportar` para hacer backup"
    )

@app.on_message(filters.command("limpiar"))
async def limpiar_memoria(client, message):
    if len(message.command) > 1 and message.command[1].lower() == "confirmar":
        data["notas"].clear()
        data["archivos"].clear()
        guardar_datos()
        await message.reply_text("🧹 **Memoria limpiada**")
    else:
        await message.reply_text("⚠️ Para confirmar: `/limpiar confirmar`")

print("=" * 50)
print("🚀 Bot iniciado")
print(f"📁 Canal: {CHANNEL_ID}")
print(f"📊 Datos: {len(data['notas'])} notas, {len(data['archivos'])} archivos")
print("=" * 50)

app.run()
