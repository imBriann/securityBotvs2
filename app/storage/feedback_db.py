"""
Sistema de logs y feedback para autoentrenamiento RLHF (Reinforcement Learning from Human Feedback).
SecurityBot-WA - Colombia 2025 - PostgreSQL Version

Este módulo maneja:
1. Registro de cada análisis realizado (mensaje, veredictos SVM + DeepSeek)
2. Captura de feedback del usuario (👍 o 👎)
3. Extracción de datos seguros para reentrenamiento del modelo SVM
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict
from app.utils.config import DatabaseConfig
from app.storage.users_state import get_db_connection


def init_feedback_db():
    """Crea las tablas de logs de análisis y feedback si no existen."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Tabla principal de logs de análisis
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS analisis_logs (
                        id SERIAL PRIMARY KEY,
                        phone_number VARCHAR(20) NOT NULL,
                        message_content TEXT NOT NULL,
                        message_length INTEGER,
                        svm_prediction VARCHAR(20),
                        svm_confidence REAL,
                        has_urls INTEGER DEFAULT 0,
                        url_risk_levels TEXT,
                        deepseek_verdict TEXT,
                        final_verdict VARCHAR(20),
                        final_is_scam INTEGER,
                        user_feedback VARCHAR(20) DEFAULT NULL,
                        feedback_timestamp TIMESTAMP DEFAULT NULL,
                        reviewed_by_admin INTEGER DEFAULT 0,
                        admin_notes TEXT DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (phone_number) REFERENCES usuarios(telefono) ON DELETE CASCADE
                    )
                """)
                
                # Tabla de estadísticas agregadas
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS feedback_stats (
                        id SERIAL PRIMARY KEY,
                        stat_date DATE UNIQUE,
                        total_analyses INTEGER DEFAULT 0,
                        total_positive_feedback INTEGER DEFAULT 0,
                        total_negative_feedback INTEGER DEFAULT 0,
                        total_unreviewed_negatives INTEGER DEFAULT 0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Índices para mejorar rendimiento
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_analisis_phone 
                    ON analisis_logs(phone_number)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_analisis_feedback 
                    ON analisis_logs(user_feedback)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_analisis_created 
                    ON analisis_logs(created_at DESC)
                """)
                
                conn.commit()
                print("✅ Tablas de feedback inicializadas en PostgreSQL")
                
    except Exception as e:
        print(f"❌ Error al inicializar tablas de feedback: {e}")


def log_interaction(
    phone: str,
    msg: str,
    svm_res: dict,
    deepseek_res: str,
    final_verdict: dict
) -> int:
    """
    Guarda una interacción completa de análisis para futuro entrenamiento.
    
    Args:
        phone: Número de teléfono del usuario
        msg: Contenido del mensaje analizado
        svm_res: Diccionario resultado del SVM
        deepseek_res: Respuesta del análisis de DeepSeek
        final_verdict: Diccionario con veredicto final
    
    Returns:
        ID del log creado
    """
    try:
        # Preparar datos de URLs
        url_analysis = svm_res.get('url_analysis', [])
        has_urls = 1 if url_analysis else 0
        url_risk_levels = ','.join([
            f"{u.get('domain', 'N/A')}:{u.get('risk_level', 'DESCONOCIDO')}" 
            for u in url_analysis
        ]) if url_analysis else None
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO analisis_logs 
                    (phone_number, message_content, message_length, svm_prediction, svm_confidence,
                     has_urls, url_risk_levels, deepseek_verdict, final_verdict, final_is_scam)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    phone,
                    msg[:500],  # Limitar a 500 caracteres
                    len(msg),
                    "phishing" if svm_res.get('is_phishing_svm') else "legitimo",
                    svm_res.get('confidence', 0.0),
                    has_urls,
                    url_risk_levels,
                    deepseek_res[:1000] if deepseek_res else None,
                    final_verdict.get('risk_level', 'DESCONOCIDO'),
                    1 if final_verdict.get('is_scam') else 0
                ))
                
                log_id = cursor.fetchone()['id']
                conn.commit()
                
                print(f"📝 Log creado (ID: {log_id}) para {phone}")
                return log_id
                
    except Exception as e:
        print(f"❌ Error al guardar log de interacción: {e}")
        return -1


def update_user_feedback(phone: str, feedback_type: str) -> bool:
    """
    Actualiza el último log de análisis de este usuario con su feedback.
    
    Args:
        phone: Número de teléfono del usuario
        feedback_type: 'POSITIVO' (👍) o 'NEGATIVO' (👎)
    
    Returns:
        True si se actualizó correctamente
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Buscar el último análisis sin feedback de este usuario
                cursor.execute("""
                    SELECT id FROM analisis_logs 
                    WHERE phone_number = %s AND user_feedback IS NULL
                    ORDER BY id DESC LIMIT 1
                """, (phone,))
                
                row = cursor.fetchone()
                
                if row:
                    log_id = row['id']
                    cursor.execute("""
                        UPDATE analisis_logs 
                        SET user_feedback = %s, feedback_timestamp = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (feedback_type, log_id))
                    conn.commit()
                    
                    print(f"✅ Feedback '{feedback_type}' registrado para log ID {log_id}")
                    return True
                else:
                    print(f"⚠️ No hay análisis pendiente de feedback para {phone}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error al actualizar feedback: {e}")
        return False


def get_feedback_stats() -> Dict:
    """
    Obtiene estadísticas generales del feedback del sistema.
    
    Returns:
        Diccionario con conteos y porcentajes
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Conteos básicos
                cursor.execute("SELECT COUNT(*) as cnt FROM analisis_logs")
                total_analyses = cursor.fetchone()['cnt']
                
                cursor.execute(
                    "SELECT COUNT(*) as cnt FROM analisis_logs WHERE user_feedback = %s",
                    ('POSITIVO',)
                )
                positive_feedback = cursor.fetchone()['cnt']
                
                cursor.execute(
                    "SELECT COUNT(*) as cnt FROM analisis_logs WHERE user_feedback = %s",
                    ('NEGATIVO',)
                )
                negative_feedback = cursor.fetchone()['cnt']
                
                cursor.execute("""
                    SELECT COUNT(*) as cnt FROM analisis_logs 
                    WHERE user_feedback = %s AND reviewed_by_admin = 0
                """, ('NEGATIVO',))
                unreviewed_negatives = cursor.fetchone()['cnt']
                
                # Calcular tasa de acierto
                if positive_feedback + negative_feedback > 0:
                    accuracy_rate = (positive_feedback / (positive_feedback + negative_feedback)) * 100
                else:
                    accuracy_rate = 0.0
                
                feedback_coverage = 0.0
                if total_analyses > 0:
                    feedback_coverage = ((positive_feedback + negative_feedback) / total_analyses) * 100
                
                return {
                    'total_analyses': total_analyses,
                    'positive_feedback': positive_feedback,
                    'negative_feedback': negative_feedback,
                    'unreviewed_negatives': unreviewed_negatives,
                    'accuracy_rate': round(accuracy_rate, 2),
                    'feedback_coverage': round(feedback_coverage, 2)
                }
                
    except Exception as e:
        print(f"❌ Error al obtener estadísticas: {e}")
        return {}


def get_data_for_retraining(min_confidence: float = 0.8, limit: int = 100) -> List[Dict]:
    """
    Extrae datos SEGUROS para reentrenamiento del modelo.
    
    Args:
        min_confidence: Confianza mínima del SVM
        limit: Número máximo de registros
    
    Returns:
        Lista de diccionarios con mensaje, veredicto y metadata
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        message_content,
                        final_is_scam,
                        user_feedback,
                        reviewed_by_admin,
                        svm_confidence,
                        created_at
                    FROM analisis_logs 
                    WHERE (
                        user_feedback = %s
                        OR reviewed_by_admin = 1
                    )
                    AND message_content IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT %s
                """, ('POSITIVO', limit))
                
                rows = cursor.fetchall()
                data = [dict(row) for row in rows]
                
                print(f"📊 Extraídos {len(data)} registros seguros para reentrenamiento")
                return data
                
    except Exception as e:
        print(f"❌ Error al extraer datos para reentrenamiento: {e}")
        return []


def get_unreviewed_negatives(limit: int = 50) -> List[Dict]:
    """
    Obtiene dislikes/negativos sin revisar por administrador.
    
    Args:
        limit: Número máximo de registros
    
    Returns:
        Lista de análisis que el usuario marcó como incorrecto
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id,
                        phone_number,
                        message_content,
                        svm_prediction,
                        final_verdict,
                        final_is_scam,
                        feedback_timestamp,
                        created_at
                    FROM analisis_logs 
                    WHERE user_feedback = %s AND reviewed_by_admin = 0
                    ORDER BY feedback_timestamp DESC
                    LIMIT %s
                """, ('NEGATIVO', limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
    except Exception as e:
        print(f"❌ Error al obtener negativos sin revisar: {e}")
        return []


def mark_as_reviewed(log_id: int, admin_decision: str, notes: str = None) -> bool:
    """
    Marca un registro como revisado por administrador.
    
    Args:
        log_id: ID del log de análisis
        admin_decision: 'VALIDADO' o 'RECHAZADO'
        notes: Notas adicionales del admin
    
    Returns:
        True si se actualizó exitosamente
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE analisis_logs 
                    SET reviewed_by_admin = 1, admin_notes = %s, user_feedback = %s
                    WHERE id = %s
                """, (notes, admin_decision, log_id))
                conn.commit()
                
                print(f"✅ Log ID {log_id} marcado como revisado: {admin_decision}")
                return True
                
    except Exception as e:
        print(f"❌ Error al marcar como revisado: {e}")
        return False


def get_recent_logs(phone: str = None, limit: int = 20) -> List[Dict]:
    """
    Obtiene logs recientes para inspección.
    
    Args:
        phone: Si se proporciona, solo obtiene logs de ese usuario
        limit: Número máximo de registros
    
    Returns:
        Lista de logs recientes
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                if phone:
                    cursor.execute("""
                        SELECT * FROM analisis_logs
                        WHERE phone_number = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (phone, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM analisis_logs
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (limit,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
    except Exception as e:
        print(f"❌ Error al obtener logs: {e}")
        return []


def get_next_pending_negative_review() -> Optional[Dict]:
    """
    Obtiene el siguiente log con feedback NEGATIVO que no ha sido revisado.
    
    Returns:
        Diccionario con los datos del caso o None
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id, 
                        message_content, 
                        svm_prediction, 
                        deepseek_verdict, 
                        final_verdict, 
                        final_is_scam,
                        phone_number as user_phone,
                        message_content as original_user_message,
                        CASE 
                            WHEN final_is_scam = 1 THEN 'ESTAFA'
                            ELSE 'LEGÍTIMO'
                        END as bot_verdict,
                        created_at
                    FROM analisis_logs 
                    WHERE user_feedback = %s AND reviewed_by_admin = 0 
                    ORDER BY created_at ASC 
                    LIMIT 1
                """, ('NEGATIVO',))
                
                row = cursor.fetchone()
                return dict(row) if row else None
                
    except Exception as e:
        print(f"❌ Error obteniendo siguiente caso de revisión: {e}")
        return None


def mark_admin_decision(log_id: int, bot_was_wrong: bool, admin_notes: str = None) -> bool:
    """
    Guarda la decisión del administrador sobre un análisis revisado.
    
    Args:
        log_id: ID del análisis a marcar
        bot_was_wrong: True si el bot falló, False si estaba correcto
        admin_notes: Notas opcionales del admin
    
    Returns:
        True si se actualizó exitosamente
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                admin_correction = "CORREGIR_ERROR" if bot_was_wrong else "CONFIRMAR_BOT"
                
                cursor.execute("""
                    UPDATE analisis_logs 
                    SET reviewed_by_admin = 1,
                        admin_notes = %s 
                    WHERE id = %s
                """, (admin_notes or admin_correction, log_id))
                conn.commit()
                
                print(f"✅ Admin decision guardada: Log ID {log_id} → {admin_correction}")
                return True
                
    except Exception as e:
        print(f"❌ Error guardando decisión del admin: {e}")
        return False


def count_pending_reviews() -> int:
    """
    Cuenta cuántos casos NEGATIVOS siguen pendientes de revisión.
    
    Returns:
        Número de casos pendientes
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as cnt FROM analisis_logs 
                    WHERE user_feedback = %s AND reviewed_by_admin = 0
                """, ('NEGATIVO',))
                result = cursor.fetchone()
                return result['cnt'] if result else 0
                
    except Exception as e:
        print(f"❌ Error contando pendientes: {e}")
        return 0


# Inicializar tablas al importar el módulo
try:
    init_feedback_db()
except Exception as e:
    print(f"⚠️ No se pudo inicializar feedback_db: {e}")