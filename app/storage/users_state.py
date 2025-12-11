"""
Módulo de gestión de usuarios con PostgreSQL.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Optional, Dict
from app.utils.config import DatabaseConfig

# --- Constantes de estado de usuario ---
ESTADO_PENDIENTE_TERMINOS = 0
ESTADO_PENDIENTE_NOMBRE = 1
ESTADO_PENDIENTE_EDAD = 2
ESTADO_PENDIENTE_CONOCIMIENTO = 3
ESTADO_REGISTRADO = 4
ESTADO_ESPERANDO_RESPUESTA_PHISHING = 5
ESTADO_ESPERANDO_MAS_DETALLES = 6


@contextmanager
def get_db_connection():
    """
    Context manager para conexiones a PostgreSQL.
    Maneja automáticamente el cierre de la conexión.
    """
    conn = None
    try:
        conn = psycopg2.connect(
            **DatabaseConfig.get_connection_params(),
            cursor_factory=RealDictCursor
        )
        yield conn
    except psycopg2.Error as e:
        print(f"❌ Error de conexión a PostgreSQL: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def setup_database():
    """
    Crea las tablas necesarias en PostgreSQL si no existen.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Tabla de usuarios
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS usuarios (
                        telefono VARCHAR(20) PRIMARY KEY,
                        nombre VARCHAR(100),
                        edad INTEGER,
                        conocimiento VARCHAR(20),
                        acepto_terminos INTEGER DEFAULT 0,
                        estado INTEGER DEFAULT 0,
                        mensajes_enviados INTEGER DEFAULT 0,
                        last_analysis_details TEXT,
                        last_image_ocr_text TEXT,
                        last_image_analysis_raw TEXT,
                        last_image_id_processed VARCHAR(100),
                        last_image_timestamp TIMESTAMP,
                        last_analyzed_url TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Tabla de imágenes procesadas
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS imagenes_procesadas (
                        id SERIAL PRIMARY KEY,
                        telefono_usuario VARCHAR(20),
                        nombre_archivo_imagen VARCHAR(255),
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (telefono_usuario) REFERENCES usuarios(telefono) ON DELETE CASCADE
                    )
                """)
                
                # Índices para mejorar rendimiento
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_usuarios_estado 
                    ON usuarios(estado)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_imagenes_telefono 
                    ON imagenes_procesadas(telefono_usuario)
                """)
                
                conn.commit()
                print("✅ Tablas de PostgreSQL creadas/verificadas exitosamente")
                
    except Exception as e:
        print(f"❌ Error al configurar base de datos PostgreSQL: {e}")
        raise


def db_get_user(telefono: str) -> Optional[Dict]:
    """
    Obtiene un usuario de la base de datos.
    
    Args:
        telefono: Número de teléfono del usuario
        
    Returns:
        Dict con datos del usuario o None si no existe
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM usuarios WHERE telefono = %s",
                    (telefono,)
                )
                user = cursor.fetchone()
                return dict(user) if user else None
                
    except Exception as e:
        print(f"❌ Error al obtener usuario {telefono}: {e}")
        return None


def db_create_user(telefono: str):
    """
    Crea un nuevo usuario en la base de datos.
    
    Args:
        telefono: Número de teléfono del usuario
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO usuarios (telefono, acepto_terminos, estado)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (telefono) DO NOTHING
                """, (telefono, 0, ESTADO_PENDIENTE_TERMINOS))
                conn.commit()
                print(f"✅ Usuario {telefono} creado exitosamente")
                
    except Exception as e:
        print(f"❌ Error al crear usuario {telefono}: {e}")
        raise


def db_update_user(telefono: str, data: Dict):
    """
    Actualiza los datos de un usuario.
    
    Args:
        telefono: Número de teléfono del usuario
        data: Diccionario con los campos a actualizar
    """
    if not data:
        print(f"⚠️ db_update_user llamado para {telefono} sin datos")
        return
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Construir query dinámicamente
                fields = ", ".join([f"{key} = %s" for key in data.keys()])
                fields += ", updated_at = CURRENT_TIMESTAMP"
                values = list(data.values())
                values.append(telefono)
                
                query = f"UPDATE usuarios SET {fields} WHERE telefono = %s"
                
                print(f"🔄 Actualizando usuario {telefono}: {list(data.keys())}")
                cursor.execute(query, tuple(values))
                conn.commit()
                print(f"✅ Usuario {telefono} actualizado exitosamente")
                
    except Exception as e:
        print(f"❌ Error al actualizar usuario {telefono}: {e}")
        print(f"   Campos: {list(data.keys())}")
        raise


def db_save_image_record(telefono_usuario: str, nombre_archivo_imagen: str):
    """
    Guarda un registro de imagen procesada.
    
    Args:
        telefono_usuario: Número de teléfono del usuario
        nombre_archivo_imagen: Nombre del archivo de imagen
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO imagenes_procesadas (telefono_usuario, nombre_archivo_imagen)
                    VALUES (%s, %s)
                """, (telefono_usuario, nombre_archivo_imagen))
                conn.commit()
                print(f"✅ Registro de imagen guardado para {telefono_usuario}")
                
    except Exception as e:
        print(f"❌ Error al guardar registro de imagen: {e}")
        raise


def db_delete_user(telefono: str) -> bool:
    """
    Elimina un usuario y sus datos relacionados.
    
    Args:
        telefono: Número de teléfono del usuario
        
    Returns:
        True si se eliminó exitosamente
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # PostgreSQL CASCADE eliminará automáticamente las imágenes relacionadas
                cursor.execute("DELETE FROM usuarios WHERE telefono = %s", (telefono,))
                conn.commit()
                print(f"✅ Usuario {telefono} eliminado exitosamente")
                return True
                
    except Exception as e:
        print(f"❌ Error al eliminar usuario {telefono}: {e}")
        return False


def db_get_user_count() -> int:
    """
    Obtiene el número total de usuarios.
    
    Returns:
        Número de usuarios registrados
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM usuarios")
                result = cursor.fetchone()
                return result['count'] if result else 0
                
    except Exception as e:
        print(f"❌ Error al contar usuarios: {e}")
        return 0


def db_get_users_by_state(estado: int, limit: int = 10) -> list:
    """
    Obtiene usuarios por estado.
    
    Args:
        estado: Estado a filtrar
        limit: Número máximo de usuarios
        
    Returns:
        Lista de usuarios
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM usuarios 
                    WHERE estado = %s 
                    ORDER BY updated_at DESC 
                    LIMIT %s
                """, (estado, limit))
                users = cursor.fetchall()
                return [dict(user) for user in users] if users else []
                
    except Exception as e:
        print(f"❌ Error al obtener usuarios por estado: {e}")
        return []


# Inicializar la BD al importar el módulo
try:
    setup_database()
except Exception as e:
    print(f"⚠️ No se pudo inicializar la base de datos: {e}")
    print("   Asegúrate de que PostgreSQL esté corriendo y las credenciales sean correctas")