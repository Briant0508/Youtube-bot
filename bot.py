import os
import json
import base64
import zlib
from pyrogram import Client, filters

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# Archivo de persistencia local (para sobrevivir reinicios)
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

# Guardar datos inmediatamente (para sobrevivir reinicios)
def guardar_datos():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ Datos guardados: {len(data['notas'])} notas, {len(data['archivos'])} archivos")
    except Exception as e:
        print(f"Error guardando datos: {e}")

# Inicializar datos desde archivo (no desde memoria vacía)
data = cargar_datos()

app = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

@app.on_message(filters.command("start"))
async def start(client, message):
    texto = (
        "👋 **Bot para HostingGuru - Plan Free**\n\n"
        f"📊 **Estado actual:**\n"
        f"📋 Notas: {len(data['notas'])}\n"
        f"📂 Archivos: {len(data['archivos'])}\n\n"
        "📒 **Comandos:**\n"
        "• `/nota <texto>` - Guardar nota\n"
        "• `/lista` - Ver contenido\n"
        "• `/buscar <palabra>` - Buscar\n"
        "• `/exportar` - **Hacer backup** (guardar código)\n"
        "• `/importar` - Restaurar backup\n\n"
        "⚠️ **IMPORTANTE para HostingGuru:**\n"
        "• El bot se reinicia cada pocas horas\n"
        "• **Usa `/exportar` regularmente** para no perder datos\n"
        "• Los archivos físicos están SEGUROS en el canal\n"
        "• El backup solo guarda las referencias (lista)"
    )
    await message.reply_text(texto)

@app.on_message(filters.command("nota"))
async def nota(client, message):
    if len(message.command) < 2:
        await message.reply_text("✍️ Uso: `/nota <texto>`\nEjemplo: `/nota Comprar leche`")
        return
    
    texto = " ".join(message.command[1:])
    data["notas"].append(texto)
    guardar_datos()  # Guardar inmediatamente
    
    try:
        # Guardar también en el canal como respaldo
        await client.send_message(CHANNEL_ID, f"NOTA|{texto}")
        await message.reply_text(f"✅ Nota guardada (y respaldada en canal)\n\n`{texto}`")
    except Exception as e:
        await message.reply_text(f"✅ Nota guardada localmente (error en canal: {e})")

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
        guardar_datos()  # Guardar inmediatamente
        await message.reply_text(f"📂 **Archivo guardado:** `{nombre}`")
    
    except Exception as e:
        await message.reply_text(f"❌ Error: `{e}`")

@app.on_message(filters.command("lista"))
async def lista(client, message):
    if not data["archivos"] and not data["notas"]:
        await message.reply_text(
            "📭 **No hay contenido guardado**\n\n"
            "Envía archivos o usa `/nota` para comenzar.\n\n"
            "💡 **Tip:** Si acabas de reiniciar el bot y tenías datos,\n"
            "usa `/importar` con tu último backup."
        )
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
        texto += "\n\n👉 **Comandos rápidos:**\n"
        texto += "• `número` - Descargar archivo\n"
        texto += "• `del número` - Eliminar archivo\n"
        texto += "• `/buscar palabra` - Buscar"
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
                await message.reply_text(f"❌ Error al descargar: `{e}`\n\n¿El archivo aún existe en el canal?")
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
                    await message.reply_text(f"🗑️ **Eliminado de la lista** (no se pudo eliminar del canal)")
            else:
                await message.reply_text("❌ **Número inválido.** Usa `/lista`")
        except (IndexError, ValueError):
            await message.reply_text("❌ **Uso correcto:** `del <número>`\nEjemplo: `del 1`")

@app.on_message(filters.command("buscar"))
async def buscar(client, message):
    if len(message.command) < 2:
        await message.reply_text("🔍 **Uso:** `/buscar <palabra>`\nEjemplo: `/buscar proyecto`")
        return
    
    palabra = " ".join(message.command[1:]).lower()
    
    notas_encontradas = [n for n in data["notas"] if palabra in n.lower()]
    archivos_encontrados = [f for f in data["archivos"] if palabra in f["caption"].lower()]

    if not notas_encontradas and not archivos_encontrados:
        await message.reply_text(f"❌ **No encontré resultados** para: `{palabra}`")
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
    status_msg = await message.reply_text("⏳ **Generando copia de seguridad...**\n\n(Esto solo toma unos segundos)")
    
    try:
        # Preparar datos completos
        export_data = {
            "version": "2.0",
            "notas": data["notas"],
            "archivos": [
                {
                    "caption": f["caption"],
                    "file_id": f["file_id"]
                }
                for f in data["archivos"]
            ]
        }
        
        # Convertir a JSON y comprimir
        json_str = json.dumps(export_data, ensure_ascii=False)
        compressed = zlib.compress(json_str.encode('utf-8'))
        codigo = base64.b64encode(compressed).decode('ascii')
        
        # Dividir en partes (Telegram max 4096 caracteres)
        CHUNK_SIZE = 3500
        total_size = len(codigo)
        
        if total_size <= CHUNK_SIZE:
            await status_msg.delete()
            await message.reply_text(
                f"💾 **Copia de seguridad**\n\n"
                f"📋 Notas: {len(data['notas'])}\n"
                f"📂 Archivos: {len(data['archivos'])}\n\n"
                f"```\n{codigo}\n```\n\n"
                f"⚠️ **GUARDA ESTE CÓDIGO**\n"
                f"Para restaurar: Responde a ESTE mensaje con `/importar`"
            )
        else:
            # Partir en múltiples mensajes
            parts = [codigo[i:i+CHUNK_SIZE] for i in range(0, total_size, CHUNK_SIZE)]
            
            await status_msg.edit_text(f"📦 **Backup grande** ({len(parts)} partes)\n\nEnviando...")
            
            for i, part in enumerate(parts, 1):
                await message.reply_text(
                    f"📦 **Parte {i}/{len(parts)}**\n\n"
                    f"```\n{part}\n```"
                )
            
            await message.reply_text(
                f"✅ **Backup completado**\n\n"
                f"Total: {len(parts)} partes\n"
                f"Para restaurar: Responde a la **PRIMERA parte** con `/importar`"
            )
    
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error al exportar:** `{str(e)[:200]}`")

@app.on_message(filters.command("importar"))
async def importar(client, message):
    if not message.reply_to_message:
        await message.reply_text(
            "❌ **Error:** Debes responder al mensaje que contiene el código de backup.\n\n"
            "1. Busca el mensaje con el código de `/exportar`\n"
            "2. Responde a ESE mensaje con `/importar`"
        )
        return
    
    status_msg = await message.reply_text("⏳ **Restaurando copia de seguridad...**")
    
    try:
        # Obtener código del mensaje
        codigo_texto = message.reply_to_message.text
        
        # Extraer código entre triple backticks si existe
        if "```" in codigo_texto:
            codigo_texto = codigo_texto.split("```")[1].strip()
        
        # Decodificar y descomprimir
        compressed = base64.b64decode(codigo_texto)
        json_str = zlib.decompress(compressed).decode('utf-8')
        import_data = json.loads(json_str)
        
        # Restaurar datos
        nuevas_notas = import_data.get("notas", [])
        nuevos_archivos = []
        
        for archivo in import_data.get("archivos", []):
            nuevos_archivos.append({
                "msg_id": None,  # Se perderá, pero el file_id sirve para reenviar
                "caption": archivo["caption"],
                "file_id": archivo["file_id"]
            })
        
        # Reemplazar datos actuales
        data["notas"] = nuevas_notas
        data["archivos"] = nuevos_archivos
        guardar_datos()
        
        await status_msg.edit_text(
            f"✅ **Copia restaurada exitosamente**\n\n"
            f"📋 Notas recuperadas: {len(data['notas'])}\n"
            f"📂 Archivos recuperados: {len(data['archivos'])}\n\n"
            f"⚠️ **Nota:** Los archivos están en el canal, pero los msg_id se perdieron.\n"
            f"Usa `/lista` para ver tu contenido."
        )
    
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error al importar:** `{str(e)[:200]}`\n\nAsegúrate de responder al mensaje de backup correcto.")

@app.on_message(filters.command("status"))
async def status(client, message):
    tamaño_archivo = 0
    if os.path.exists(DATA_FILE):
        tamaño_archivo = os.path.getsize(DATA_FILE)
    
    await message.reply_text(
        f"📊 **Estado del Bot**\n\n"
        f"📋 Notas en memoria: `{len(data['notas'])}`\n"
        f"📂 Archivos en memoria: `{len(data['archivos'])}`\n"
        f"💾 Datos guardados en disco: `{'Sí' if tamaño_archivo > 0 else 'No'}`\n"
        f"📦 Tamaño del archivo: `{tamaño_archivo} bytes`\n\n"
        f"🔄 **Para hosting gratuito:**\n"
        f"• El bot se reinicia cada pocas horas\n"
        f"• Los datos persisten en `{DATA_FILE}`\n"
        f"• Pero recomiendo `/exportar` periódicamente\n\n"
        f"💡 **Si pierdes datos:** Usa `/importar` con tu último backup"
    )

@app.on_message(filters.command("limpiar"))
async def limpiar_memoria(client, message):
    if len(message.command) > 1 and message.command[1].lower() == "confirmar":
        data["notas"].clear()
        data["archivos"].clear()
        guardar_datos()
        await message.reply_text(
            "🧹 **Memoria limpiada**\n\n"
            "✅ Datos locales eliminados\n"
            "⚠️ Los archivos en el canal NO se eliminan\n"
            "💡 Para recuperar la lista, necesitarás un backup"
        )
    else:
        await message.reply_text(
            "⚠️ **Limpiar toda la memoria local**\n\n"
            "Esto eliminará TODAS las notas y referencias de archivos.\n"
            "Los archivos en el canal NO se tocan.\n\n"
            "**Consecuencias:**\n"
            "• Perderás el acceso a los archivos desde el bot\n"
            "• Los archivos seguirán en el canal, pero no podrás listarlos\n\n"
            "Para confirmar: `/limpiar confirmar`\n"
            "Para hacer backup primero: `/exportar`"
        )

print("=" * 50)
print("🚀 Bot iniciado - Optimizado para HostingGuru")
print(f"📁 Archivo de datos: {DATA_FILE}")
print(f"📊 Datos cargados: {len(data['notas'])} notas, {len(data['archivos'])} archivos")
print("💾 Los datos se guardan automáticamente en cada cambio")
print("⚠️ IMPORTANTE: Usa /exportar periódicamente para hacer backup")
print("=" * 50)

app.run()
