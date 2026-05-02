import os
import json
import base64
import zlib
from pyrogram import Client, filters

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_INPUT = os.getenv("CHANNEL_ID")

# Convertir CHANNEL_ID correctamente (acepta @username o ID numérico)
if CHANNEL_INPUT.startswith('@'):
    CHANNEL_ID = CHANNEL_INPUT
else:
    CHANNEL_ID = int(CHANNEL_INPUT)

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

# ==================== COMANDOS PRINCIPALES ====================

@app.on_message(filters.command("start"))
async def start(client, message):
    # Verificar si el bot puede acceder al canal
    try:
        await client.get_chat(CHANNEL_ID)
        canal_ok = "✅"
    except:
        canal_ok = "❌"
    
    texto = (
        "👋 **Bot de Almacenamiento v3.0**\n\n"
        f"📊 **Estado actual:**\n"
        f"📋 Notas: {len(data['notas'])}\n"
        f"📂 Archivos: {len(data['archivos'])}\n"
        f"📡 Canal: {canal_ok}\n\n"
        "📒 **Comandos:**\n"
        "• `/nota <texto>` - Guardar nota\n"
        "• `/lista` - Ver contenido\n"
        "• `/buscar <palabra>` - Buscar\n"
        "• `/exportar` - Hacer backup (¡Importante!)\n"
        "• `/importar` - Restaurar backup\n"
        "• `/status` - Ver estado detallado\n"
        "• `/reparar` - Reparar referencias rotas\n"
        "• `/limpiar` - Limpiar memoria local\n\n"
        "🎮 **Comandos rápidos:**\n"
        "• `número` - Descargar archivo (ej: `5`)\n"
        "• `del número` - Eliminar archivo (ej: `del 3`)\n\n"
        "⚠️ **Importante:**\n"
        "• Usa `/exportar` regularmente\n"
        "• Los archivos están SEGUROS en el canal"
    )
    await message.reply_text(texto)

@app.on_message(filters.command("nota"))
async def nota(client, message):
    if len(message.command) < 2:
        await message.reply_text("✍️ **Uso:** `/nota <texto>`\nEjemplo: `/nota Comprar leche`")
        return
    
    texto = " ".join(message.command[1:])
    data["notas"].append(texto)
    guardar_datos()
    
    try:
        await client.send_message(CHANNEL_ID, f"NOTA|{texto}")
        await message.reply_text(f"✅ **Nota guardada:**\n`{texto}`")
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
            tipo = "document"
        elif message.video:
            enviado = await client.send_video(CHANNEL_ID, message.video.file_id, caption=caption)
            nombre = message.video.file_name or caption
            file_id = message.video.file_id
            tipo = "video"
        elif message.photo:
            enviado = await client.send_photo(CHANNEL_ID, message.photo.file_id, caption=caption)
            nombre = f"Imagen_{len(data['archivos'])+1}"
            file_id = message.photo.file_id
            tipo = "photo"

        data["archivos"].append({
            "msg_id": enviado.id,
            "caption": nombre,
            "file_id": file_id,
            "tipo": tipo
        })
        guardar_datos()
        await message.reply_text(f"📂 **Archivo guardado:** `{nombre}`")
    
    except Exception as e:
        await message.reply_text(f"❌ **Error al guardar:** `{e}`\n\n¿El bot es admin del canal?")

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
            # Mostrar emoji según el tipo
            tipo_emoji = "🎬" if f.get("tipo") == "video" else "📄" if f.get("tipo") == "document" else "🖼️"
            texto += f"{tipo_emoji} `{i}.` {nombre}\n"
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
        texto += "• Escribe el `número` para descargar\n"
        texto += "• Escribe `del <número>` para eliminar"
        await message.reply_text(texto)

# ==================== MANEJO DE ARCHIVOS (CORREGIDO CON DETECCIÓN DE TIPO) ====================

@app.on_message(filters.text & ~filters.command(["start", "nota", "lista", "buscar", "exportar", "importar", "limpiar", "status", "reparar"]))
async def manejar_archivos(client, message):
    txt = message.text.strip()

    # Descargar archivo por número
    if txt.isdigit():
        indice = int(txt) - 1
        if 0 <= indice < len(data["archivos"]):
            archivo = data["archivos"][indice]
            
            try:
                # Método 1: Usar msg_id si existe
                if archivo.get("msg_id") is not None:
                    await client.copy_message(
                        message.chat.id,
                        CHANNEL_ID,
                        archivo["msg_id"]
                    )
                else:
                    # Método 2: Usar file_id con detección de tipo
                    file_id = archivo["file_id"]
                    caption = archivo["caption"]
                    tipo = archivo.get("tipo", "document")
                    
                    # Enviar según el tipo guardado
                    if tipo == "video":
                        await client.send_video(message.chat.id, file_id, caption=caption)
                    elif tipo == "photo":
                        await client.send_photo(message.chat.id, file_id, caption=caption)
                    else:
                        # Si es documento o no hay tipo, intentar como documento
                        try:
                            await client.send_document(message.chat.id, file_id, caption=caption)
                        except Exception as e:
                            # Si falla como documento, intentar como video
                            if "DOCUMENT" in str(e) and "VIDEO" in str(e):
                                await client.send_video(message.chat.id, file_id, caption=caption)
                            else:
                                raise e
                
                await message.reply_text(f"✅ **Descargado:** `{archivo['caption']}`")
            
            except Exception as e:
                await message.reply_text(
                    f"❌ **Error al descargar**\n\n"
                    f"Archivo: `{archivo['caption']}`\n"
                    f"Error: `{e}`\n\n"
                    f"💡 Usa `/reparar` para intentar recuperar este archivo."
                )
        else:
            await message.reply_text("❌ **Número inválido.** Usa `/lista`")

    # Eliminar archivo por número
    elif txt.lower().startswith("del "):
        try:
            num = int(txt.split()[1]) - 1
            if 0 <= num < len(data["archivos"]):
                archivo = data["archivos"].pop(num)
                guardar_datos()
                
                # Intentar eliminar del canal solo si tiene msg_id
                if archivo.get("msg_id") is not None:
                    try:
                        await client.delete_messages(CHANNEL_ID, archivo["msg_id"])
                    except:
                        pass
                
                await message.reply_text(f"🗑️ **Eliminado:** `{archivo['caption']}`")
            else:
                await message.reply_text("❌ **Número inválido.** Usa `/lista`")
        except:
            await message.reply_text("❌ **Uso correcto:** `del <número>`\nEjemplo: `del 1`")

# ==================== BUSCAR ====================

@app.on_message(filters.command("buscar"))
async def buscar(client, message):
    if len(message.command) < 2:
        await message.reply_text("🔍 **Uso:** `/buscar <palabra>`\nEjemplo: `/buscar proyecto`")
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
            tipo_emoji = "🎬" if archivo.get("tipo") == "video" else "📄" if archivo.get("tipo") == "document" else "🖼️"
            respuesta += f"{tipo_emoji} {archivo['caption'][:100]}\n"
    
    await message.reply_text(respuesta)

# ==================== BACKUP (EXPORTAR/IMPORTAR) ====================

@app.on_message(filters.command("exportar"))
async def exportar(client, message):
    status_msg = await message.reply_text("⏳ **Generando copia de seguridad...**")
    
    try:
        export_data = {
            "version": "3.0",
            "notas": data["notas"],
            "archivos": [
                {
                    "caption": f["caption"],
                    "file_id": f["file_id"],
                    "tipo": f.get("tipo", "document")
                }
                for f in data["archivos"]
            ]
        }
        
        json_str = json.dumps(export_data, ensure_ascii=False)
        compressed = zlib.compress(json_str.encode('utf-8'))
        codigo = base64.b64encode(compressed).decode('ascii')
        
        await status_msg.delete()
        
        # Si el código es muy largo, partirlo
        if len(codigo) > 3500:
            partes = [codigo[i:i+3500] for i in range(0, len(codigo), 3500)]
            await message.reply_text(f"📦 **Backup grande** ({len(partes)} partes)\n\n")
            for i, parte in enumerate(partes, 1):
                await message.reply_text(f"**Parte {i}/{len(partes)}**\n\n```\n{parte}\n```")
            await message.reply_text(
                f"✅ **Backup completado**\n\n"
                f"📋 Notas: {len(data['notas'])}\n"
                f"📂 Archivos: {len(data['archivos'])}\n\n"
                f"⚠️ Para restaurar: Responde a la **PRIMERA parte** con `/importar`"
            )
        else:
            await message.reply_text(
                f"💾 **Copia de seguridad**\n\n"
                f"📋 Notas: {len(data['notas'])}\n"
                f"📂 Archivos: {len(data['archivos'])}\n\n"
                f"```\n{codigo}\n```\n\n"
                f"⚠️ **GUARDA ESTE CÓDIGO**\n"
                f"Para restaurar: Responde a ESTE mensaje con `/importar`"
            )
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error al exportar:** `{str(e)[:200]}`")

@app.on_message(filters.command("importar"))
async def importar(client, message):
    if not message.reply_to_message:
        await message.reply_text(
            "❌ **Error:** Debes responder al mensaje que contiene el código de backup.\n\n"
            "1. Encuentra el mensaje con el código\n"
            "2. Responde a ESE mensaje con `/importar`"
        )
        return
    
    status_msg = await message.reply_text("⏳ **Restaurando copia de seguridad...**\n\nEsto puede tomar unos segundos...")
    
    try:
        codigo_texto = message.reply_to_message.text
        if "```" in codigo_texto:
            codigo_texto = codigo_texto.split("```")[1].strip()
        
        compressed = base64.b64decode(codigo_texto)
        json_str = zlib.decompress(compressed).decode('utf-8')
        import_data = json.loads(json_str)
        
        data["notas"] = import_data.get("notas", [])
        data["archivos"] = []
        
        # Restaurar archivos y buscar sus msg_id en el canal
        for a in import_data.get("archivos", []):
            archivo = {
                "msg_id": None,
                "caption": a["caption"],
                "file_id": a["file_id"],
                "tipo": a.get("tipo", "document")  # Mantener el tipo original
            }
            
            # Buscar el mensaje en el canal para obtener msg_id
            try:
                async for msg in client.get_chat_history(CHANNEL_ID, limit=500):
                    encontrado = False
                    
                    if msg.document and msg.document.file_id == a["file_id"]:
                        archivo["msg_id"] = msg.id
                        archivo["tipo"] = "document"
                        encontrado = True
                    elif msg.video and msg.video.file_id == a["file_id"]:
                        archivo["msg_id"] = msg.id
                        archivo["tipo"] = "video"
                        encontrado = True
                    elif msg.photo and msg.photo.file_id == a["file_id"]:
                        archivo["msg_id"] = msg.id
                        archivo["tipo"] = "photo"
                        encontrado = True
                    
                    if encontrado:
                        break
            except:
                pass  # Si no encuentra, queda None y usará file_id con el tipo guardado
            
            data["archivos"].append(archivo)
        
        guardar_datos()
        
        msg_ids_encontrados = sum(1 for a in data["archivos"] if a["msg_id"] is not None)
        
        await status_msg.edit_text(
            f"✅ **Copia restaurada exitosamente**\n\n"
            f"📋 Notas: {len(data['notas'])}\n"
            f"📂 Archivos: {len(data['archivos'])}\n"
            f"📡 msg_id recuperados: {msg_ids_encontrados}/{len(data['archivos'])}\n"
            f"🎬 Tipos de archivo: Documentos/{sum(1 for a in data['archivos'] if a.get('tipo')=='document')} | Videos/{sum(1 for a in data['archivos'] if a.get('tipo')=='video')} | Fotos/{sum(1 for a in data['archivos'] if a.get('tipo')=='photo')}\n\n"
            f"💡 Ahora puedes descargar los archivos con sus números."
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error al importar:** `{str(e)[:200]}`")

# ==================== REPARAR ARCHIVOS (MEJORADO) ====================

@app.on_message(filters.command("reparar"))
async def reparar(client, message):
    status_msg = await message.reply_text("🔄 **Reparando referencias de archivos...**\n\nEsto puede tomar unos segundos...")
    
    reparados = 0
    fallidos = 0
    tipos_corregidos = 0
    
    for i, archivo in enumerate(data["archivos"]):
        if archivo.get("msg_id") is None:
            # Intentar obtener el mensaje por file_id
            try:
                async for msg in client.get_chat_history(CHANNEL_ID, limit=1000):
                    encontrado = False
                    
                    if msg.document and msg.document.file_id == archivo["file_id"]:
                        archivo["msg_id"] = msg.id
                        if archivo.get("tipo") != "document":
                            archivo["tipo"] = "document"
                            tipos_corregidos += 1
                        encontrado = True
                        reparados += 1
                        
                    elif msg.video and msg.video.file_id == archivo["file_id"]:
                        archivo["msg_id"] = msg.id
                        if archivo.get("tipo") != "video":
                            archivo["tipo"] = "video"
                            tipos_corregidos += 1
                        encontrado = True
                        reparados += 1
                        
                    elif msg.photo and msg.photo.file_id == archivo["file_id"]:
                        archivo["msg_id"] = msg.id
                        if archivo.get("tipo") != "photo":
                            archivo["tipo"] = "photo"
                            tipos_corregidos += 1
                        encontrado = True
                        reparados += 1
                    
                    if encontrado:
                        break
                else:
                    fallidos += 1
            except Exception as e:
                fallidos += 1
                print(f"Error reparando archivo {i}: {e}")
    
    guardar_datos()
    
    await status_msg.edit_text(
        f"✅ **Reparación completada**\n\n"
        f"🔧 Reparados: {reparados}\n"
        f"🏷️ Tipos corregidos: {tipos_corregidos}\n"
        f"❌ Fallidos: {fallidos}\n"
        f"📂 Total archivos: {len(data['archivos'])}\n\n"
        f"💡 Ahora intenta descargar de nuevo con el número del archivo.\n"
        f"Los archivos fallidos probablemente fueron eliminados del canal."
    )

# ==================== ESTADO Y MANTENIMIENTO ====================

@app.on_message(filters.command("status"))
async def status(client, message):
    msg_id_validos = sum(1 for a in data["archivos"] if a.get("msg_id") is not None)
    msg_id_invalidos = len(data["archivos"]) - msg_id_validos
    
    videos = sum(1 for a in data["archivos"] if a.get("tipo") == "video")
    documentos = sum(1 for a in data["archivos"] if a.get("tipo") == "document")
    fotos = sum(1 for a in data["archivos"] if a.get("tipo") == "photo")
    sin_tipo = len(data["archivos"]) - (videos + documentos + fotos)
    
    texto = (
        f"📊 **Estado del Bot v3.0**\n\n"
        f"📋 Notas en memoria: `{len(data['notas'])}`\n"
        f"📂 Archivos en memoria: `{len(data['archivos'])}`\n"
        f"   ├─ Con msg_id válido: `{msg_id_validos}`\n"
        f"   └─ Sin msg_id (usarán file_id): `{msg_id_invalidos}`\n\n"
        f"🎬 **Tipos de archivo:**\n"
        f"   ├─ Videos: `{videos}`\n"
        f"   ├─ Documentos: `{documentos}`\n"
        f"   ├─ Fotos: `{fotos}`\n"
        f"   └─ Sin tipo: `{sin_tipo}`\n\n"
        f"💾 Datos guardados en disco: `{'Sí' if os.path.exists(DATA_FILE) else 'No'}`\n"
        f"📡 Canal: `{CHANNEL_ID}`\n\n"
        f"💡 **Recomendaciones:**\n"
        f"• Usa `/exportar` para hacer backup\n"
        f"• Usa `/reparar` si hay archivos sin msg_id\n"
        f"• Usa `/lista` para ver tu contenido"
    )
    await message.reply_text(texto)

@app.on_message(filters.command("limpiar"))
async def limpiar_memoria(client, message):
    if len(message.command) > 1 and message.command[1].lower() == "confirmar":
        data["notas"].clear()
        data["archivos"].clear()
        guardar_datos()
        await message.reply_text(
            "🧹 **Memoria limpiada exitosamente**\n\n"
            "✅ Datos locales eliminados\n"
            "⚠️ Los archivos en el canal NO se eliminaron\n"
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

# ==================== INICIO ====================

print("=" * 60)
print("🚀 Bot de Almacenamiento v3.0 iniciado")
print(f"📡 Canal: {CHANNEL_ID}")
print(f"📋 Notas cargadas: {len(data['notas'])}")
print(f"📂 Archivos cargados: {len(data['archivos'])}")
print(f"💾 Archivo de datos: {DATA_FILE}")
print("=" * 60)

app.run()
