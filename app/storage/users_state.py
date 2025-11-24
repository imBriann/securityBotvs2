import sqlite3

from app.utils.config import DB_NAME

# --- Constantes de estado de usuario ---

ESTADO_PENDIENTE_TERMINOS = 0
ESTADO_PENDIENTE_NOMBRE = 1
ESTADO_PENDIENTE_EDAD = 2
ESTADO_PENDIENTE_CONOCIMIENTO = 3
ESTADO_REGISTRADO = 4
ESTADO_ESPERANDO_RESPUESTA_PHISHING = 5
ESTADO_ESPERANDO_MAS_DETALLES = 6


# --- Funciones de Base de Datos ---

def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def setup_database():
    conn_setup = get_db_connection()
    cursor_setup = conn_setup.cursor()

    cursor_setup.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            telefono TEXT PRIMARY KEY,
            nombre TEXT,
            edad INTEGER,
            conocimiento TEXT,
            acepto_terminos INTEGER DEFAULT 0,
            estado INTEGER DEFAULT 0,
            mensajes_enviados INTEGER DEFAULT 0,
            last_analysis_details TEXT,
            last_image_ocr_text TEXT,
            last_image_analysis_raw TEXT,
            last_image_id_processed TEXT,
            last_image_timestamp DATETIME,
            last_analyzed_url TEXT
        );
        """
    )

    cursor_setup.execute(
        """
        CREATE TABLE IF NOT EXISTS imagenes_procesadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telefono_usuario TEXT,
            nombre_archivo_imagen TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telefono_usuario) REFERENCES usuarios(telefono)
        );
        """
    )

    conn_setup.commit()
    conn_setup.close()


def db_get_user(telefono: str) -> sqlite3.Row | None:
    conn_db = get_db_connection()
    cursor_db = conn_db.cursor()
    cursor_db.execute("SELECT * FROM usuarios WHERE telefono = ?", (telefono,))
    user = cursor_db.fetchone()
    conn_db.close()
    return user


def db_create_user(telefono: str):
    conn_db = get_db_connection()
    cursor_db = conn_db.cursor()
    try:
        cursor_db.execute(
            "INSERT INTO usuarios (telefono, acepto_terminos, estado) "
            "VALUES (?, ?, ?)",
            (telefono, 0, ESTADO_PENDIENTE_TERMINOS),
        )
        conn_db.commit()
    except sqlite3.IntegrityError:
        print(f"Intento de crear usuario duplicado: {telefono}")
    finally:
        conn_db.close()


def db_update_user(telefono: str, data: dict):
    if not data:
        print(f"DEBUG: db_update_user llamado para {telefono} sin datos. Retornando.")
        return

    fields = ", ".join([f"{key} = ?" for key in data])
    values = list(data.values())
    values.append(telefono)

    conn_db = None
    query = f"UPDATE usuarios SET {fields} WHERE telefono = ?"

    try:
        conn_db = get_db_connection()
        cursor_db = conn_db.cursor()
        print(
            f"DEBUG: Ejecutando SQL: {query} con valores "
            f"(excepto el último que es el teléfono): {tuple(values[:-1])} "
            f"para tel: {telefono}"
        )
        cursor_db.execute(query, tuple(values))
        conn_db.commit()
        print(f"DEBUG: Commit exitoso para {telefono} en db_update_user.")
    except sqlite3.Error as e_sqlite:
        print(
            "ERROR SQLITE en db_update_user para "
            f"{telefono}: {e_sqlite}. Query: {query}, "
            f"Values (sin token): "
            f"{[(v[:20] + '...' if isinstance(v, str) and len(v) > 50 else v) for v in tuple(values)]}"
        )
        if conn_db:
            conn_db.rollback()
        raise
    except Exception as e_general:
        print(
            "ERROR GENERAL en db_update_user para "
            f"{telefono}: {e_general}. Query: {query}, "
            f"Values (sin token): "
            f"{[(v[:20] + '...' if isinstance(v, str) and len(v) > 50 else v) for v in tuple(values)]}"
        )
        if conn_db:
            conn_db.rollback()
        raise
    finally:
        if conn_db:
            conn_db.close()
            print(f"DEBUG: Conexión DB cerrada para {telefono} en db_update_user.")


def db_save_image_record(telefono_usuario: str, nombre_archivo_imagen: str):
    conn_db = get_db_connection()
    cursor_db = conn_db.cursor()
    cursor_db.execute(
        "INSERT INTO imagenes_procesadas (telefono_usuario, nombre_archivo_imagen) "
        "VALUES (?, ?)",
        (telefono_usuario, nombre_archivo_imagen),
    )
    conn_db.commit()
    conn_db.close()


# Inicializar la BD al importar el módulo
setup_database()
