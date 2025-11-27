"""
Módulo para comandos administrativos del bot.
Autor: SecurityBot-WA Admin Panel
"""
import os
import sqlite3
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from app.storage.users_state import get_db_connection, setup_database
from app.utils.config import DB_NAME

# Número de teléfono del administrador (sin el símbolo +)
ADMIN_PHONE_NUMBER = "573505894033"


def is_admin(phone_number: str) -> bool:
    """
    Verifica si un número de teléfono pertenece al administrador.
    
    Args:
        phone_number: Número de teléfono a verificar
        
    Returns:
        True si es el administrador, False en caso contrario
    """
    return phone_number == ADMIN_PHONE_NUMBER


def is_admin_command(text: str) -> bool:
    """
    Verifica si un texto es un comando administrativo.
    
    Args:
        text: Texto a verificar
        
    Returns:
        True si es un comando admin
    """
    if not text:
        return False
    return text.strip().startswith("/")


async def handle_admin_command(phone_number: str, command: str) -> Optional[str]:
    """
    Maneja comandos administrativos.
    
    Args:
        phone_number: Número de teléfono del usuario
        command: Comando a ejecutar
        
    Returns:
        Mensaje de respuesta o None si no es un comando admin válido
    """
    if not is_admin(phone_number):
        print(f"⚠️ Intento de comando admin desde número no autorizado: {phone_number}")
        return None
    
    command_parts = command.strip().split()
    command_name = command_parts[0].lower()
    args = command_parts[1:] if len(command_parts) > 1 else []
    
    print(f"🔧 ADMIN COMMAND: {command_name} | Args: {args}")
    
    # Manejar comando /help directamente (no es async)
    if command_name == "/help":
        return get_admin_help_message()
    
    # Diccionario de comandos async disponibles
    commands_map = {
        "/reset": execute_reset_command,
        "/stats": execute_stats_command,
        "/users": execute_list_users_command,
        "/user": execute_user_details_command,
        "/export": execute_export_command,
        "/backup": execute_backup_command,
        "/deleteuser": execute_delete_user_command,
        "/broadcast": execute_broadcast_command,
        "/images": execute_images_stats_command,
        "/clearimages": execute_clear_images_command,
        "/setstate": execute_set_state_command,
        "/health": execute_health_check_command,
    }
    
    if command_name in commands_map:
        if command_name in ["/user", "/deleteuser", "/setstate"] and not args:
            return f"❌ El comando `{command_name}` requiere argumentos.\nUsa `/help` para más información."
        
        try:
            if args:
                return await commands_map[command_name](args)
            else:
                return await commands_map[command_name]()
        except Exception as e:
            error_msg = f"❌ Error ejecutando {command_name}: {str(e)}"
            print(error_msg)
            return error_msg
    else:
        return (
            f"❌ Comando `{command_name}` no reconocido.\n\n"
            "Usa `/help` para ver todos los comandos disponibles."
        )


async def execute_reset_command() -> str:
    """
    Ejecuta el comando de reset: borra la base de datos y la reinicia.
    ⚠️ COMANDO DESTRUCTIVO - Requiere confirmación
    
    Returns:
        Mensaje de confirmación
    """
    try:
        # Cerrar todas las conexiones activas
        conn = get_db_connection()
        conn.close()
        
        # Eliminar el archivo de la base de datos
        if os.path.exists(DB_NAME):
            os.remove(DB_NAME)
            print(f"✅ Base de datos {DB_NAME} eliminada por comando ADMIN.")
        
        # Recrear la base de datos vacía
        setup_database()
        print("✅ Base de datos recreada por comando ADMIN.")
        
        return (
            "🔄 *RESET COMPLETADO*\n\n"
            "✅ Base de datos eliminada\n"
            "✅ Base de datos recreada\n"
            "✅ Todos los usuarios borrados\n"
            "✅ Todas las imágenes eliminadas\n\n"
            "🚀 El sistema está listo para empezar de cero."
        )
    
    except Exception as e:
        error_msg = f"❌ Error al ejecutar reset: {str(e)}"
        print(error_msg)
        return error_msg


async def execute_stats_command() -> str:
    """
    Muestra estadísticas completas del bot.
    
    Returns:
        Mensaje con las estadísticas
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Contar usuarios totales
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total_users = cursor.fetchone()[0]
        
        # Contar usuarios registrados
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE estado = 4")
        registered_users = cursor.fetchone()[0]
        
        # Contar usuarios que aceptaron términos
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE acepto_terminos = 1")
        accepted_terms = cursor.fetchone()[0]
        
        # Contar imágenes procesadas
        cursor.execute("SELECT COUNT(*) FROM imagenes_procesadas")
        total_images = cursor.fetchone()[0]
        
        # Obtener usuarios por estado
        cursor.execute("""
            SELECT estado, COUNT(*) as count 
            FROM usuarios 
            GROUP BY estado
            ORDER BY estado
        """)
        states = cursor.fetchall()
        
        # Nivel de conocimiento
        cursor.execute("""
            SELECT conocimiento, COUNT(*) as count 
            FROM usuarios 
            WHERE conocimiento IS NOT NULL
            GROUP BY conocimiento
        """)
        knowledge_levels = cursor.fetchall()
        
        conn.close()
        
        state_names = {
            0: "Pendiente Términos",
            1: "Pendiente Nombre",
            2: "Pendiente Edad",
            3: "Pendiente Conocimiento",
            4: "Registrado",
            5: "Esperando Resp. Phishing",
            6: "Esperando Más Detalles"
        }
        
        stats_by_state = "\n".join([
            f"  • {state_names.get(state, f'Estado {state}')}: {count}"
            for state, count in states
        ])
        
        knowledge_stats = "\n".join([
            f"  • {level}: {count}"
            for level, count in knowledge_levels
        ]) if knowledge_levels else "  • Sin datos"
        
        completion_rate = (registered_users / total_users * 100) if total_users > 0 else 0
        
        return (
            "📊 *ESTADÍSTICAS DEL BOT*\n"
            f"_Generadas: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n\n"
            f"👥 *Usuarios totales:* {total_users}\n"
            f"✅ *Usuarios registrados:* {registered_users}\n"
            f"📝 *Términos aceptados:* {accepted_terms}\n"
            f"🖼️ *Imágenes procesadas:* {total_images}\n"
            f"📈 *Tasa de completación:* {completion_rate:.1f}%\n\n"
            f"*📍 Estados de usuarios:*\n{stats_by_state}\n\n"
            f"*🧠 Nivel de conocimiento:*\n{knowledge_stats}"
        )
    
    except Exception as e:
        error_msg = f"❌ Error al obtener estadísticas: {str(e)}"
        print(error_msg)
        return error_msg


async def execute_list_users_command(args: List[str] = None) -> str:
    """
    Lista los usuarios del sistema.
    
    Args:
        args: Argumentos opcionales [limite]
    
    Returns:
        Lista de usuarios
    """
    try:
        limit = int(args[0]) if args and args[0].isdigit() else 10
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT telefono, nombre, edad, conocimiento, estado, acepto_terminos
            FROM usuarios
            ORDER BY rowid DESC
            LIMIT ?
        """, (limit,))
        
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            return "📭 No hay usuarios registrados en el sistema."
        
        state_emoji = {
            0: "⏳", 1: "📝", 2: "🎂", 3: "🧠", 4: "✅", 5: "🔍", 6: "📄"
        }
        
        user_list = []
        for user in users:
            tel = user[0][-4:]  # Últimos 4 dígitos
            nombre = user[1] or "Sin nombre"
            edad = user[2] or "?"
            conocimiento = user[3] or "?"
            estado = user[4]
            emoji = state_emoji.get(estado, "❓")
            
            user_list.append(
                f"{emoji} *{nombre}* (···{tel})\n"
                f"   Edad: {edad} | Conocimiento: {conocimiento}"
            )
        
        return (
            f"👥 *ÚLTIMOS {len(users)} USUARIOS*\n\n"
            + "\n\n".join(user_list) +
            f"\n\n_Usa `/user [telefono]` para ver detalles completos_"
        )
    
    except Exception as e:
        return f"❌ Error listando usuarios: {str(e)}"


async def execute_user_details_command(args: List[str]) -> str:
    """
    Muestra detalles completos de un usuario.
    
    Args:
        args: [telefono]
    
    Returns:
        Detalles del usuario
    """
    try:
        phone = args[0]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM usuarios WHERE telefono = ?", (phone,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return f"❌ Usuario con teléfono `{phone}` no encontrado."
        
        # Contar imágenes del usuario
        cursor.execute(
            "SELECT COUNT(*) FROM imagenes_procesadas WHERE telefono_usuario = ?",
            (phone,)
        )
        image_count = cursor.fetchone()[0]
        
        conn.close()
        
        state_names = {
            0: "⏳ Pendiente Términos",
            1: "📝 Pendiente Nombre",
            2: "🎂 Pendiente Edad",
            3: "🧠 Pendiente Conocimiento",
            4: "✅ Registrado",
            5: "🔍 Esperando Resp. Phishing",
            6: "📄 Esperando Más Detalles"
        }
        
        return (
            f"👤 *DETALLES DE USUARIO*\n\n"
            f"📞 *Teléfono:* {user[0]}\n"
            f"👤 *Nombre:* {user[1] or 'Sin nombre'}\n"
            f"🎂 *Edad:* {user[2] or 'No especificada'}\n"
            f"🧠 *Conocimiento:* {user[3] or 'No especificado'}\n"
            f"📝 *Términos aceptados:* {'✅ Sí' if user[4] else '❌ No'}\n"
            f"📍 *Estado:* {state_names.get(user[5], f'Estado {user[5]}')}\n"
            f"💬 *Mensajes enviados:* {user[6]}\n"
            f"🖼️ *Imágenes procesadas:* {image_count}\n"
            f"🔗 *Último URL analizado:* {user[12] or 'Ninguno'}\n"
            f"📅 *Última imagen:* {user[11] or 'Ninguna'}"
        )
    
    except Exception as e:
        return f"❌ Error obteniendo detalles: {str(e)}"


async def execute_export_command() -> str:
    """
    Exporta datos de la base de datos en formato texto.
    
    Returns:
        Datos exportados
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM usuarios")
        users = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) FROM imagenes_procesadas")
        images = cursor.fetchone()[0]
        
        conn.close()
        
        export_data = [
            "📦 *EXPORTACIÓN DE DATOS*",
            f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total usuarios: {len(users)}",
            f"Total imágenes: {images}",
            "",
            "--- USUARIOS ---"
        ]
        
        for user in users[:20]:  # Limitar a 20 para no saturar el mensaje
            export_data.append(
                f"Tel: {user[0]}, Nombre: {user[1]}, Edad: {user[2]}, "
                f"Conocimiento: {user[3]}, Estado: {user[5]}"
            )
        
        if len(users) > 20:
            export_data.append(f"\n... y {len(users) - 20} usuarios más")
        
        return "\n".join(export_data)
    
    except Exception as e:
        return f"❌ Error exportando datos: {str(e)}"


async def execute_backup_command() -> str:
    """
    Crea un backup de la base de datos.
    
    Returns:
        Mensaje de confirmación
    """
    try:
        if not os.path.exists(DB_NAME):
            return "❌ No existe base de datos para hacer backup."
        
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        import shutil
        shutil.copy2(DB_NAME, backup_name)
        
        file_size = os.path.getsize(backup_name) / 1024  # KB
        
        return (
            f"💾 *BACKUP CREADO*\n\n"
            f"📁 Archivo: `{backup_name}`\n"
            f"📊 Tamaño: {file_size:.2f} KB\n"
            f"⏰ Hora: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"✅ Backup guardado correctamente."
        )
    
    except Exception as e:
        return f"❌ Error creando backup: {str(e)}"


async def execute_delete_user_command(args: List[str]) -> str:
    """
    Elimina un usuario del sistema.
    
    Args:
        args: [telefono]
    
    Returns:
        Mensaje de confirmación
    """
    try:
        phone = args[0]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si existe
        cursor.execute("SELECT nombre FROM usuarios WHERE telefono = ?", (phone,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return f"❌ Usuario `{phone}` no encontrado."
        
        nombre = user[0] or "Sin nombre"
        
        # Eliminar imágenes asociadas
        cursor.execute("DELETE FROM imagenes_procesadas WHERE telefono_usuario = ?", (phone,))
        
        # Eliminar usuario
        cursor.execute("DELETE FROM usuarios WHERE telefono = ?", (phone,))
        
        conn.commit()
        conn.close()
        
        return (
            f"🗑️ *USUARIO ELIMINADO*\n\n"
            f"📞 Teléfono: {phone}\n"
            f"👤 Nombre: {nombre}\n\n"
            f"✅ Usuario y sus datos asociados han sido eliminados."
        )
    
    except Exception as e:
        return f"❌ Error eliminando usuario: {str(e)}"


async def execute_broadcast_command(args: List[str]) -> str:
    """
    Información sobre el comando broadcast (no implementado por seguridad).
    
    Returns:
        Mensaje informativo
    """
    return (
        "📢 *COMANDO BROADCAST*\n\n"
        "⚠️ Por razones de seguridad y privacidad, el envío masivo de mensajes "
        "debe implementarse con cuidado.\n\n"
        "💡 *Recomendación:* Implementa esta funcionalidad con:\n"
        "• Confirmación previa\n"
        "• Límite de destinatarios\n"
        "• Rate limiting\n"
        "• Opt-out automático\n\n"
        "_Contacta al desarrollador para habilitar esta función._"
    )


async def execute_images_stats_command() -> str:
    """
    Estadísticas de imágenes procesadas.
    
    Returns:
        Estadísticas de imágenes
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total de imágenes
        cursor.execute("SELECT COUNT(*) FROM imagenes_procesadas")
        total = cursor.fetchone()[0]
        
        # Imágenes por usuario (top 5)
        cursor.execute("""
            SELECT u.nombre, u.telefono, COUNT(i.id) as count
            FROM imagenes_procesadas i
            JOIN usuarios u ON i.telefono_usuario = u.telefono
            GROUP BY i.telefono_usuario
            ORDER BY count DESC
            LIMIT 5
        """)
        top_users = cursor.fetchall()
        
        # Imágenes recientes (últimas 24h)
        cursor.execute("""
            SELECT COUNT(*) FROM imagenes_procesadas
            WHERE timestamp >= datetime('now', '-1 day')
        """)
        recent = cursor.fetchone()[0]
        
        conn.close()
        
        top_list = "\n".join([
            f"  {i+1}. {user[0] or 'Sin nombre'} (···{user[1][-4:]}): {user[2]} imgs"
            for i, user in enumerate(top_users)
        ]) if top_users else "  • Sin datos"
        
        return (
            f"🖼️ *ESTADÍSTICAS DE IMÁGENES*\n\n"
            f"📊 *Total procesadas:* {total}\n"
            f"🕐 *Últimas 24h:* {recent}\n\n"
            f"*🏆 Top usuarios:*\n{top_list}"
        )
    
    except Exception as e:
        return f"❌ Error en estadísticas de imágenes: {str(e)}"


async def execute_clear_images_command() -> str:
    """
    Limpia el registro de imágenes procesadas.
    
    Returns:
        Mensaje de confirmación
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM imagenes_procesadas")
        count = cursor.fetchone()[0]
        
        cursor.execute("DELETE FROM imagenes_procesadas")
        conn.commit()
        conn.close()
        
        return (
            f"🗑️ *LIMPIEZA DE IMÁGENES*\n\n"
            f"📊 Registros eliminados: {count}\n"
            f"✅ Tabla de imágenes limpiada correctamente.\n\n"
            f"_Nota: Los archivos físicos en /imagenes_recibidas no fueron eliminados._"
        )
    
    except Exception as e:
        return f"❌ Error limpiando imágenes: {str(e)}"


async def execute_set_state_command(args: List[str]) -> str:
    """
    Cambia el estado de un usuario.
    
    Args:
        args: [telefono, nuevo_estado]
    
    Returns:
        Mensaje de confirmación
    """
    try:
        if len(args) < 2:
            return "❌ Uso: `/setstate [telefono] [estado]`\nEstados: 0-6"
        
        phone = args[0]
        new_state = int(args[1])
        
        if new_state not in range(0, 7):
            return "❌ Estado inválido. Debe ser entre 0 y 6."
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT nombre FROM usuarios WHERE telefono = ?", (phone,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return f"❌ Usuario `{phone}` no encontrado."
        
        cursor.execute("UPDATE usuarios SET estado = ? WHERE telefono = ?", (new_state, phone))
        conn.commit()
        conn.close()
        
        state_names = {
            0: "Pendiente Términos", 1: "Pendiente Nombre", 2: "Pendiente Edad",
            3: "Pendiente Conocimiento", 4: "Registrado", 5: "Esperando Resp. Phishing",
            6: "Esperando Más Detalles"
        }
        
        return (
            f"✅ *ESTADO ACTUALIZADO*\n\n"
            f"👤 Usuario: {user[0] or 'Sin nombre'}\n"
            f"📞 Teléfono: {phone}\n"
            f"📍 Nuevo estado: {state_names.get(new_state, f'Estado {new_state}')}"
        )
    
    except ValueError:
        return "❌ El estado debe ser un número entre 0 y 6."
    except Exception as e:
        return f"❌ Error cambiando estado: {str(e)}"


async def execute_health_check_command() -> str:
    """
    Verifica el estado de salud del sistema.
    
    Returns:
        Reporte de salud
    """
    try:
        health_report = ["🏥 *HEALTH CHECK*\n"]
        
        # Verificar base de datos
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM usuarios")
            conn.close()
            health_report.append("✅ Base de datos: OK")
        except Exception as e:
            health_report.append(f"❌ Base de datos: ERROR - {str(e)}")
        
        # Verificar directorio de imágenes
        if os.path.exists("imagenes_recibidas"):
            img_count = len([f for f in os.listdir("imagenes_recibidas") if f.endswith(('.jpg', '.png'))])
            health_report.append(f"✅ Directorio imágenes: OK ({img_count} archivos)")
        else:
            health_report.append("⚠️ Directorio imágenes: No existe")
        
        # Verificar archivo .env
        if os.path.exists(".env"):
            health_report.append("✅ Archivo .env: OK")
        else:
            health_report.append("❌ Archivo .env: No encontrado")
        
        # Verificar variables de entorno críticas
        from app.utils.config import APIConfig
        if APIConfig.validate():
            health_report.append("✅ Variables de entorno: OK")
        else:
            health_report.append("⚠️ Variables de entorno: Faltan algunas")
        
        health_report.append(f"\n⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(health_report)
    
    except Exception as e:
        return f"❌ Error en health check: {str(e)}"


def get_admin_help_message() -> str:
    """
    Retorna el mensaje de ayuda para comandos administrativos.
    
    Returns:
        Mensaje con la lista de comandos
    """
    return (
        "🔧 *PANEL DE ADMINISTRACIÓN*\n"
        "_SecurityBot-WA Admin Commands_\n\n"
        
        "*📊 Información y Estadísticas:*\n"
        "• `/stats` - Estadísticas completas del bot\n"
        "• `/users [limite]` - Lista últimos usuarios (def: 10)\n"
        "• `/user [telefono]` - Detalles de un usuario\n"
        "• `/images` - Estadísticas de imágenes\n"
        "• `/health` - Estado de salud del sistema\n\n"
        
        "*🛠️ Gestión de Datos:*\n"
        "• `/export` - Exportar datos a texto\n"
        "• `/backup` - Crear backup de la BD\n"
        "• `/setstate [tel] [estado]` - Cambiar estado de usuario\n"
        "• `/deleteuser [telefono]` - Eliminar usuario\n"
        "• `/clearimages` - Limpiar registros de imágenes\n\n"
        
        "*⚠️ Comandos Críticos:*\n"
        "• `/reset` - ⚠️ Resetear TODO el sistema\n\n"
        
        "*📢 Otros:*\n"
        "• `/broadcast` - Info sobre envío masivo\n"
        "• `/help` - Mostrar esta ayuda\n\n"
        
        f"_Admin: ···{ADMIN_PHONE_NUMBER[-4:]}_"
    )