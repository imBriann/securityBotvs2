"""
Módulo para comandos administrativos del bot.
Autor: SecurityBot-WA Admin Panel
Actualizado para PostgreSQL
"""
import os
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from app.storage.users_state import get_db_connection, setup_database, db_update_user
from app.utils.config import DatabaseConfig, AdminConfig, ESTADO_ADMIN_REVISANDO, ESTADO_REGISTRADO
from app.services.trainer import (
    generate_retraining_report,
    analyze_feedback_quality,
    get_retraining_summary
)
from app.storage.feedback_db import (
    get_next_pending_negative_review,
    mark_admin_decision,
    count_pending_reviews
)

# Número de teléfono del administrador desde variable de entorno
ADMIN_PHONE_NUMBER = AdminConfig.ADMIN_PHONE_NUMBER


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
        "/feedback_stats": execute_feedback_stats_command,
        "/retrain_report": execute_retrain_report_command,
        "/review_negatives": execute_review_negatives_command,
        "/do_retrain": execute_do_retrain_command,
        "/revisar": execute_start_review_command,
    }

    if command_name in commands_map:
        if command_name in ["/user", "/deleteuser", "/setstate"] and not args:
            return (
                f"❌ El comando `{command_name}` requiere argumentos.\n"
                "Usa `/help` para más información."
            )

        try:
            # Comandos especiales que necesitan phone_number
            if command_name == "/revisar":
                return await commands_map[command_name](phone_number)
            elif args:
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
    Ejecuta el comando de reset: borra todas las tablas y las recrea.
    ⚠️ COMANDO DESTRUCTIVO - Requiere confirmación

    Returns:
        Mensaje de confirmación
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Eliminar todas las tablas en orden inverso (respetando foreign keys)
                cursor.execute("DROP TABLE IF EXISTS feedback_stats CASCADE")
                cursor.execute("DROP TABLE IF EXISTS analisis_logs CASCADE")
                cursor.execute("DROP TABLE IF EXISTS imagenes_procesadas CASCADE")
                cursor.execute("DROP TABLE IF EXISTS usuarios CASCADE")
                conn.commit()

        print("✅ Tablas de PostgreSQL eliminadas por comando ADMIN.")

        # Recrear las tablas vacías
        setup_database()

        # Importar y recrear tablas de feedback
        from app.storage.feedback_db import init_feedback_db
        init_feedback_db()

        print("✅ Base de datos recreada por comando ADMIN.")

        return (
            "🔄 *RESET COMPLETADO*\n\n"
            "✅ Todas las tablas eliminadas\n"
            "✅ Base de datos recreada\n"
            "✅ Todos los usuarios borrados\n"
            "✅ Todos los análisis eliminados\n\n"
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
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Contar usuarios totales
                cursor.execute("SELECT COUNT(*) as count FROM usuarios")
                total_users = cursor.fetchone()["count"]

                # Contar usuarios registrados
                cursor.execute("SELECT COUNT(*) as count FROM usuarios WHERE estado = 4")
                registered_users = cursor.fetchone()["count"]

                # Contar usuarios que aceptaron términos
                cursor.execute(
                    "SELECT COUNT(*) as count FROM usuarios WHERE acepto_terminos = 1"
                )
                accepted_terms = cursor.fetchone()["count"]

                # Contar imágenes procesadas
                cursor.execute("SELECT COUNT(*) as count FROM imagenes_procesadas")
                total_images = cursor.fetchone()["count"]

                # Obtener usuarios por estado
                cursor.execute(
                    """
                    SELECT estado, COUNT(*) as count 
                    FROM usuarios 
                    GROUP BY estado
                    ORDER BY estado
                """
                )
                states = cursor.fetchall()

                # Nivel de conocimiento
                cursor.execute(
                    """
                    SELECT conocimiento, COUNT(*) as count 
                    FROM usuarios 
                    WHERE conocimiento IS NOT NULL
                    GROUP BY conocimiento
                """
                )
                knowledge_levels = cursor.fetchall()

        state_names: Dict[int, str] = {
            0: "Pendiente Términos",
            1: "Pendiente Nombre",
            2: "Pendiente Edad",
            3: "Pendiente Conocimiento",
            4: "Registrado",
            5: "Esperando Resp. Phishing",
            6: "Esperando Más Detalles",
        }

        # 🔧 AQUÍ estaba el error de f-string con backslash
        stats_by_state = "\n".join(
            [
                f"  • {state_names.get(state['estado'], 'Estado ' + str(state['estado']))}:  {state['count']}"
                for state in states
            ]
        )

        knowledge_stats = (
            "\n".join(
                [
                    f"  • {level['conocimiento']}: {level['count']}"
                    for level in knowledge_levels
                ]
            )
            if knowledge_levels
            else "  • Sin datos"
        )

        completion_rate = (
            (registered_users / total_users * 100) if total_users > 0 else 0
        )

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


async def execute_list_users_command(args: Optional[List[str]] = None) -> str:
    """
    Lista los usuarios del sistema.

    Args:
        args: Argumentos opcionales [limite]

    Returns:
        Lista de usuarios
    """
    try:
        limit = int(args[0]) if args and args[0].isdigit() else 10

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT telefono, nombre, edad, conocimiento, estado, acepto_terminos
                    FROM usuarios
                    ORDER BY updated_at DESC
                    LIMIT %s
                """,
                    (limit,),
                )

                users = cursor.fetchall()

        if not users:
            return "📭 No hay usuarios registrados en el sistema."

        state_emoji = {
            0: "⏳",
            1: "📝",
            2: "🎂",
            3: "🧠",
            4: "✅",
            5: "🔍",
            6: "📄",
        }

        user_list: List[str] = []
        for user in users:
            tel = user["telefono"][-4:]  # Últimos 4 dígitos
            nombre = user["nombre"] or "Sin nombre"
            edad = user["edad"] or "?"
            conocimiento = user["conocimiento"] or "?"
            estado = user["estado"]
            emoji = state_emoji.get(estado, "❓")

            user_list.append(
                f"{emoji} *{nombre}* (···{tel})\n"
                f"   Edad: {edad} | Conocimiento: {conocimiento}"
            )

        return (
            f"👥 *ÚLTIMOS {len(users)} USUARIOS*\n\n"
            + "\n\n".join(user_list)
            + "\n\n_Usa `/user [telefono]` para ver detalles completos_"
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

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM usuarios WHERE telefono = %s",
                    (phone,),
                )
                user = cursor.fetchone()

                if not user:
                    return f"❌ Usuario con teléfono `{phone}` no encontrado."

                # Contar imágenes del usuario
                cursor.execute(
                    "SELECT COUNT(*) as count FROM imagenes_procesadas WHERE telefono_usuario = %s",
                    (phone,),
                )
                image_count = cursor.fetchone()["count"]

        state_names = {
            0: "⏳ Pendiente Términos",
            1: "📝 Pendiente Nombre",
            2: "🎂 Pendiente Edad",
            3: "🧠 Pendiente Conocimiento",
            4: "✅ Registrado",
            5: "🔍 Esperando Resp. Phishing",
            6: "📄 Esperando Más Detalles",
        }

        # 🔧 AQUÍ también había un f-string con backslash
        estado_legible = state_names.get(
            user["estado"], "Estado " + str(user["estado"])
        )

        return (
            "👤 *DETALLES DE USUARIO*\n\n"
            f"📞 *Teléfono:* {user['telefono']}\n"
            f"👤 *Nombre:* {user['nombre'] or 'Sin nombre'}\n"
            f"🎂 *Edad:* {user['edad'] or 'No especificada'}\n"
            f"🧠 *Conocimiento:* {user['conocimiento'] or 'No especificado'}\n"
            f"📝 *Términos aceptados:* {'✅ Sí' if user['acepto_terminos'] else '❌ No'}\n"
            f"📍 *Estado:* {estado_legible}\n"
            f"💬 *Mensajes enviados:* {user['mensajes_enviados']}\n"
            f"🖼️ *Imágenes procesadas:* {image_count}\n"
            f"🔗 *Último URL analizado:* {user['last_analyzed_url'] or 'Ninguno'}\n"
            f"📅 *Última imagen:* {user['last_image_timestamp'] or 'Ninguna'}"
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
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM usuarios")
                users = cursor.fetchall()

                cursor.execute("SELECT COUNT(*) as count FROM imagenes_procesadas")
                images = cursor.fetchone()["count"]

        export_data: List[str] = [
            "📦 *EXPORTACIÓN DE DATOS*",
            f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total usuarios: {len(users)}",
            f"Total imágenes: {images}",
            "",
            "--- USUARIOS ---",
        ]

        for user in users[:20]:  # Limitar a 20 para no saturar el mensaje
            export_data.append(
                f"Tel: {user['telefono']}, Nombre: {user['nombre']}, "
                f"Edad: {user['edad']}, Conocimiento: {user['conocimiento']}, "
                f"Estado: {user['estado']}"
            )

        if len(users) > 20:
            export_data.append(f"\n... y {len(users) - 20} usuarios más")

        return "\n".join(export_data)

    except Exception as e:
        return f"❌ Error exportando datos: {str(e)}"


async def execute_backup_command() -> str:
    """
    Crea un backup de la base de datos PostgreSQL.

    Returns:
        Mensaje de confirmación
    """
    try:
        import subprocess

        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

        # Obtener parámetros de conexión
        db_params = DatabaseConfig.get_connection_params()

        # Comando pg_dump
        cmd = [
            "pg_dump",
            "-h",
            db_params["host"],
            "-p",
            str(db_params["port"]),
            "-U",
            db_params["user"],
            "-d",
            db_params["database"],
            "-f",
            backup_name,
        ]

        # Ejecutar backup
        env = os.environ.copy()
        env["PGPASSWORD"] = db_params["password"]

        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode == 0:
            file_size = os.path.getsize(backup_name) / 1024  # KB

            return (
                "💾 *BACKUP CREADO*\n\n"
                f"📁 Archivo: `{backup_name}`\n"
                f"📊 Tamaño: {file_size:.2f} KB\n"
                f"⏰ Hora: {datetime.now().strftime('%H:%M:%S')}\n\n"
                "✅ Backup guardado correctamente."
            )
        else:
            return f"❌ Error creando backup: {result.stderr}"

    except Exception as e:
        return (
            f"❌ Error creando backup: {str(e)}\n\n"
            "💡 Asegúrate de tener pg_dump instalado en el sistema."
        )


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

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Verificar si existe
                cursor.execute(
                    "SELECT nombre FROM usuarios WHERE telefono = %s",
                    (phone,),
                )
                user = cursor.fetchone()

                if not user:
                    return f"❌ Usuario `{phone}` no encontrado."

                nombre = user["nombre"] or "Sin nombre"

                # Eliminar usuario (CASCADE eliminará imágenes y análisis automáticamente)
                cursor.execute(
                    "DELETE FROM usuarios WHERE telefono = %s",
                    (phone,),
                )
                conn.commit()

        return (
            "🗑️ *USUARIO ELIMINADO*\n\n"
            f"📞 Teléfono: {phone}\n"
            f"👤 Nombre: {nombre}\n\n"
            "✅ Usuario y sus datos asociados han sido eliminados."
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
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Total de imágenes
                cursor.execute("SELECT COUNT(*) as count FROM imagenes_procesadas")
                total = cursor.fetchone()["count"]

                # Imágenes por usuario (top 5)
                cursor.execute(
                    """
                    SELECT u.nombre, u.telefono, COUNT(i.id) as count
                    FROM imagenes_procesadas i
                    JOIN usuarios u ON i.telefono_usuario = u.telefono
                    GROUP BY u.nombre, u.telefono
                    ORDER BY count DESC
                    LIMIT 5
                """
                )
                top_users = cursor.fetchall()

                # Imágenes recientes (últimas 24h)
                cursor.execute(
                    """
                    SELECT COUNT(*) as count FROM imagenes_procesadas
                    WHERE timestamp >= NOW() - INTERVAL '1 day'
                """
                )
                recent = cursor.fetchone()["count"]

        top_list = (
            "\n".join(
                [
                    f"  {i+1}. {user['nombre'] or 'Sin nombre'} (···{user['telefono'][-4:]}): {user['count']} imgs"
                    for i, user in enumerate(top_users)
                ]
            )
            if top_users
            else "  • Sin datos"
        )

        return (
            "🖼️ *ESTADÍSTICAS DE IMÁGENES*\n\n"
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
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM imagenes_procesadas")
                count = cursor.fetchone()["count"]

                cursor.execute("DELETE FROM imagenes_procesadas")
                conn.commit()

        return (
            "🗑️ *LIMPIEZA DE IMÁGENES*\n\n"
            f"📊 Registros eliminados: {count}\n"
            "✅ Tabla de imágenes limpiada correctamente.\n\n"
            "_Nota: Los archivos físicos en /imagenes_recibidas no fueron eliminados._"
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

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT nombre FROM usuarios WHERE telefono = %s",
                    (phone,),
                )
                user = cursor.fetchone()

                if not user:
                    return f"❌ Usuario `{phone}` no encontrado."

                cursor.execute(
                    "UPDATE usuarios SET estado = %s WHERE telefono = %s",
                    (new_state, phone),
                )
                conn.commit()

        state_names = {
            0: "Pendiente Términos",
            1: "Pendiente Nombre",
            2: "Pendiente Edad",
            3: "Pendiente Conocimiento",
            4: "Registrado",
            5: "Esperando Resp. Phishing",
            6: "Esperando Más Detalles",
        }

        return (
            "✅ *ESTADO ACTUALIZADO*\n\n"
            f"👤 Usuario: {user['nombre'] or 'Sin nombre'}\n"
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
        health_report: List[str] = ["🏥 *HEALTH CHECK*\n"]

        # Verificar base de datos PostgreSQL
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) as count FROM usuarios")
                    user_count = cursor.fetchone()["count"]
                    health_report.append(f"✅ PostgreSQL: OK ({user_count} usuarios)")
        except Exception as e:
            health_report.append(f"❌ PostgreSQL: ERROR - {str(e)}")

        # Verificar directorio de imágenes
        if os.path.exists("imagenes_recibidas"):
            img_count = len(
                [
                    f
                    for f in os.listdir("imagenes_recibidas")
                    if f.endswith((".jpg", ".png"))
                ]
            )
            health_report.append(
                f"✅ Directorio imágenes: OK ({img_count} archivos)"
            )
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

        # Verificar configuración de PostgreSQL
        if DatabaseConfig.validate():
            health_report.append("✅ Config PostgreSQL: OK")
        else:
            health_report.append("❌ Config PostgreSQL: Incompleta")

        health_report.append(
            f"\n⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

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
        "_SecurityBot-WA Admin Commands (PostgreSQL)_\n\n"
        "*📊 Información y Estadísticas:*\n"
        "• `/stats` - Estadísticas completas del bot\n"
        "• `/users [limite]` - Lista últimos usuarios (def: 10)\n"
        "• `/user [telefono]` - Detalles de un usuario\n"
        "• `/images` - Estadísticas de imágenes\n"
        "• `/health` - Estado de salud del sistema\n\n"
        "*🧠 RLHF (Machine Learning Feedback):*\n"
        "• `/feedback_stats` - Estadísticas de feedback del usuario\n"
        "• `/retrain_report` - Reporte de reentrenamiento disponible\n"
        "• `/review_negatives` - Ver casos marcados como incorrectos\n"
        "• `/revisar` - 🆕 Modo de revisión interactiva (caso por caso)\n"
        "• `/do_retrain` - Ejecutar reentrenamiento seguro\n\n"
        "*🛠️ Gestión de Datos:*\n"
        "• `/export` - Exportar datos a texto\n"
        "• `/backup` - Crear backup de PostgreSQL (pg_dump)\n"
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


# ============================================================================
# COMANDOS RLHF (Reinforcement Learning from Human Feedback)
# ============================================================================


async def execute_feedback_stats_command() -> str:
    """
    Muestra estadísticas de feedback del sistema RLHF.

    Returns:
        Estadísticas de feedback formateadas
    """
    try:
        summary = get_retraining_summary()
        return summary
    except Exception as e:
        return f"❌ Error obteniendo estadísticas de feedback: {str(e)}"


async def execute_retrain_report_command() -> str:
    """
    Genera un reporte detallado sobre el estado del reentrenamiento.

    Returns:
        Reporte de reentrenamiento
    """
    try:
        report = generate_retraining_report()
        return f"```\n{report}\n```"
    except Exception as e:
        return f"❌ Error generando reporte: {str(e)}"


async def execute_review_negatives_command(
    args: Optional[List[str]] = None,
) -> str:
    """
    Muestra casos que los usuarios marcaron como incorrectos (dislikes).
    Útil para auditoría manual.

    Args:
        args: Argumentos opcionales [limite]

    Returns:
        Lista de casos negativos sin revisar
    """
    try:
        from app.storage.feedback_db import get_unreviewed_negatives

        limit = int(args[0]) if args and args[0].isdigit() else 10
        negatives = get_unreviewed_negatives(limit)

        if not negatives:
            return (
                "✅ *SIN CASOS PROBLEMÁTICOS*\n\n"
                "No hay dislikes sin revisar. ¡El bot ha sido muy acertado!"
            )

        report: List[str] = [
            f"⚠️ *CASOS MARCADOS COMO INCORRECTOS (Primeros {len(negatives)})*\n"
        ]

        for i, case in enumerate(negatives, 1):
            verdict = "ESTAFA" if case.get("final_is_scam") else "LEGÍTIMO"
            msg_preview = case.get("message_content", "N/A")[:60]
            timestamp = case.get("feedback_timestamp", "N/A")

            report.append(
                f"\n*Caso {i}:*\n"
                f"  ID: {case.get('id')}\n"
                f"  Usuario: ···{case.get('phone_number', 'N/A')[-4:]}\n"
                f"  Veredicto Bot: {verdict}\n"
                f"  Mensaje: \"{msg_preview}...\"\n"
                f"  Feedback: {timestamp}"
            )

        report.append(
            "\n_Revisa estos casos manualmente y decide si el bot acertó o se equivocó._\n"
            "_Usa /help para ver cómo marcar como validado._"
        )

        return "\n".join(report)

    except Exception as e:
        return f"❌ Error revisando negativos: {str(e)}"


async def execute_do_retrain_command() -> str:
    """
    Ejecuta el reentrenamiento del modelo SVM.
    Implementa múltiples capas de seguridad para evitar data poisoning.

    Returns:
        Resultado del reentrenamiento
    """
    try:
        from app.services.trainer import execute_retraining

        print("🧠 Iniciando reentrenamiento...")
        result = execute_retraining(force_unsafe=False)

        if result.get("success"):
            return (
                "🎯 *REENTRENAMIENTO INICIADO*\n\n"
                f"✅ {result.get('message', 'Proceso iniciado')}\n\n"
                "📝 *Instrucciones para completar:*\n"
                "```\n"
                "python -m app.scripts.retrain_svm\n"
                "```\n\n"
                "⏰ El proceso puede tomar 1-5 minutos dependiendo del volumen de datos."
            )
        else:
            error = result.get("error", "Error desconocido")
            recommendation = result.get("recommendation", "")

            return (
                "❌ *NO SE PUEDE REENTRENAR AHORA*\n\n"
                f"Razón: {error}\n\n"
                f"💡 Recomendación: {recommendation}\n\n"
                "⚠️ Por seguridad, no entrenaremos con datos potencialmente envenenados."
            )

    except Exception as e:
        return f"❌ Error en reentrenamiento: {str(e)}"


async def execute_start_review_command(phone_number: str) -> str:
    """
    Inicia el modo de revisión interactiva para el admin.
    Obtiene el primer caso pendiente y entra en modo ESTADO_ADMIN_REVISANDO.

    Returns:
        Mensaje con el primer caso a revisar
    """
    try:
        # Contar pendientes
        pending_count = count_pending_reviews()

        if pending_count == 0:
            return (
                "✅ *NO HAY REVISIONES PENDIENTES*\n\n"
                "Todos los dislikes ya han sido auditados. ¡Excelente trabajo!"
            )

        # Obtener el primer caso
        caso = get_next_pending_negative_review()

        if not caso:
            return "❌ Error obteniendo caso de revisión."

        # Cambiar estado del admin a REVISANDO
        db_update_user(
            phone_number,
            {
                "estado": ESTADO_ADMIN_REVISANDO,
                "last_analyzed_url": str(caso["id"]),  # Guardar ID del caso
            },
        )

        # Formatear mensaje
        msg_preview = caso.get("message_content", "N/A")[:300]
        final_verdict = caso.get("final_verdict", "DESCONOCIDO")

        msg = (
            f"🕵️‍♂️ *CASO DE REVISIÓN #{caso['id']}*\n"
            f"_({1} de {pending_count})_\n\n"
            "📩 *Mensaje del usuario:*\n"
            f"_{msg_preview}_\n\n"
            f"🤖 *Bot Veredicto:* {final_verdict}\n"
            "👤 *Usuario Respondió:* 👎 (No está de acuerdo)\n\n"
            "*¿El bot se equivocó realmente?*\n\n"
            "Responde:\n"
            "🔴 *SI* → El bot falló, usuario tenía razón\n"
            "🟢 *NO* → El bot estaba bien, usuario está equivocado\n"
            "🚪 *SALIR* → Terminar revisión"
        )

        print(f"✅ Admin {phone_number} entra en modo revisión. Caso {caso['id']}")
        return msg

    except Exception as e:
        return f"❌ Error iniciando revisión: {str(e)}"
