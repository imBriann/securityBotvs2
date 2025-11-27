"""
Sistema de logs y feedback para autoentrenamiento RLHF (Reinforcement Learning from Human Feedback).
SecurityBot-WA - Colombia 2025

Este módulo maneja:
1. Registro de cada análisis realizado (mensaje, veredictos SVM + DeepSeek)
2. Captura de feedback del usuario (👍 o 👎)
3. Extracción de datos seguros para reentrenamiento del modelo SVM
"""

import sqlite3
import datetime
from typing import Optional, List, Dict
from app.utils.config import DB_NAME


def init_feedback_db():
    """Crea la tabla de logs de análisis si no existe."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # Tabla principal de logs de análisis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analisis_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT NOT NULL,
                message_content TEXT NOT NULL,
                message_length INTEGER,
                svm_prediction TEXT,
                svm_confidence REAL,
                has_urls INTEGER DEFAULT 0,
                url_risk_levels TEXT,
                deepseek_verdict TEXT,
                final_verdict TEXT,
                final_is_scam INTEGER,
                user_feedback TEXT DEFAULT NULL,
                feedback_timestamp DATETIME DEFAULT NULL,
                reviewed_by_admin INTEGER DEFAULT 0,
                admin_notes TEXT DEFAULT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (phone_number) REFERENCES usuarios(telefono)
            )
        """)
        
        # Tabla de estadísticas agregadas (para queries rápidas)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stat_date DATE UNIQUE,
                total_analyses INTEGER DEFAULT 0,
                total_positive_feedback INTEGER DEFAULT 0,
                total_negative_feedback INTEGER DEFAULT 0,
                total_unreviewed_negatives INTEGER DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        print("✅ Tablas de feedback inicializadas")


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
        svm_res: Diccionario resultado del SVM (con 'is_phishing_svm', 'confidence', 'url_analysis', etc)
        deepseek_res: Respuesta del análisis de DeepSeek
        final_verdict: Diccionario con veredicto final ('is_scam', 'risk_level', etc)
    
    Returns:
        ID del log creado
    """
    try:
        # Preparar datos de URLs
        url_analysis = svm_res.get('url_analysis', [])
        has_urls = 1 if url_analysis else 0
        url_risk_levels = ','.join([f"{u.get('domain', 'N/A')}:{u.get('risk_level', 'DESCONOCIDO')}" 
                                   for u in url_analysis]) if url_analysis else None
        
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO analisis_logs 
                (phone_number, message_content, message_length, svm_prediction, svm_confidence,
                 has_urls, url_risk_levels, deepseek_verdict, final_verdict, final_is_scam)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                phone,
                msg[:500],  # Limitar a 500 caracteres para la BD
                len(msg),
                "phishing" if svm_res.get('is_phishing_svm') else "legitimo",
                svm_res.get('confidence', 0.0),
                has_urls,
                url_risk_levels,
                deepseek_res[:1000] if deepseek_res else None,  # Resumen
                final_verdict.get('risk_level', 'DESCONOCIDO'),
                1 if final_verdict.get('is_scam') else 0
            ))
            conn.commit()
            log_id = cursor.lastrowid
            
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
        True si se actualizó correctamente, False en caso contrario
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            # Buscar el último análisis sin feedback de este usuario
            cursor.execute("""
                SELECT id FROM analisis_logs 
                WHERE phone_number = ? AND user_feedback IS NULL
                ORDER BY id DESC LIMIT 1
            """, (phone,))
            
            row = cursor.fetchone()
            
            if row:
                log_id = row[0]
                cursor.execute("""
                    UPDATE analisis_logs 
                    SET user_feedback = ?, feedback_timestamp = CURRENT_TIMESTAMP
                    WHERE id = ?
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
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Conteos básicos
            cursor.execute("SELECT COUNT(*) as cnt FROM analisis_logs")
            total_analyses = cursor.fetchone()['cnt']
            
            cursor.execute("SELECT COUNT(*) as cnt FROM analisis_logs WHERE user_feedback = 'POSITIVO'")
            positive_feedback = cursor.fetchone()['cnt']
            
            cursor.execute("SELECT COUNT(*) as cnt FROM analisis_logs WHERE user_feedback = 'NEGATIVO'")
            negative_feedback = cursor.fetchone()['cnt']
            
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM analisis_logs 
                WHERE user_feedback = 'NEGATIVO' AND reviewed_by_admin = 0
            """)
            unreviewed_negatives = cursor.fetchone()['cnt']
            
            # Calcular tasa de acierto
            if positive_feedback + negative_feedback > 0:
                accuracy_rate = (positive_feedback / (positive_feedback + negative_feedback)) * 100
            else:
                accuracy_rate = 0.0
            
            return {
                'total_analyses': total_analyses,
                'positive_feedback': positive_feedback,
                'negative_feedback': negative_feedback,
                'unreviewed_negatives': unreviewed_negatives,
                'accuracy_rate': round(accuracy_rate, 2),
                'feedback_coverage': round((positive_feedback + negative_feedback) / total_analyses * 100, 2) if total_analyses > 0 else 0
            }
            
    except Exception as e:
        print(f"❌ Error al obtener estadísticas: {e}")
        return {}


def get_data_for_retraining(min_confidence: float = 0.8, limit: int = 100) -> List[Dict]:
    """
    Extrae datos SEGUROS para reentrenamiento del modelo.
    
    FILTRO DE SEGURIDAD:
    - Solo toma mensajes con feedback POSITIVO (usuario confirmó que fue correcto)
    - O mensajes revisados manualmente por un administrador
    - Excluye datos potencialmente envenenados (dislikes no revisados)
    
    Args:
        min_confidence: Confianza mínima del SVM para incluir datos positivos
        limit: Número máximo de registros a retornar
    
    Returns:
        Lista de diccionarios con mensaje, veredicto y metadata
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Consulta segura: solo datos positivos o revisados
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
                    user_feedback = 'POSITIVO'
                    OR reviewed_by_admin = 1
                )
                AND message_content IS NOT NULL
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
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
    Útil para auditoría manual de posibles errores del bot.
    
    Args:
        limit: Número máximo de registros
    
    Returns:
        Lista de análisis que el usuario marcó como incorrecto
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
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
                WHERE user_feedback = 'NEGATIVO' AND reviewed_by_admin = 0
                ORDER BY feedback_timestamp DESC
                LIMIT ?
            """, (limit,))
            
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
        admin_decision: 'VALIDADO' o 'RECHAZADO' (si el bot tenía razón o no)
        notes: Notas adicionales del admin
    
    Returns:
        True si se actualizó exitosamente
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE analisis_logs 
                SET reviewed_by_admin = 1, admin_notes = ?, user_feedback = ?
                WHERE id = ?
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
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if phone:
                cursor.execute("""
                    SELECT * FROM analisis_logs
                    WHERE phone_number = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (phone, limit))
            else:
                cursor.execute("""
                    SELECT * FROM analisis_logs
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
    except Exception as e:
        print(f"❌ Error al obtener logs: {e}")
        return []


# Inicializar tablas al importar el módulo
init_feedback_db()


def get_next_pending_negative_review() -> Optional[Dict]:
    """
    Obtiene el siguiente log con feedback NEGATIVO que no ha sido revisado.
    Usado para el flujo interactivo de revisión del admin.
    
    Returns:
        Diccionario con los datos del caso o None si no hay pendientes
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    id, 
                    message_content, 
                    svm_prediction, 
                    deepseek_verdict, 
                    final_verdict, 
                    final_is_scam,
                    created_at
                FROM analisis_logs 
                WHERE user_feedback = 'NEGATIVO' AND reviewed_by_admin = 0 
                ORDER BY created_at ASC 
                LIMIT 1
            """)
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
        bot_was_wrong: True si el bot falló, False si el bot estaba correcto
        admin_notes: Notas opcionales del admin
    
    Returns:
        True si se actualizó exitosamente
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            # Decisión del admin
            admin_correction = "CORREGIR_ERROR" if bot_was_wrong else "CONFIRMAR_BOT"
            
            cursor.execute("""
                UPDATE analisis_logs 
                SET reviewed_by_admin = 1,
                    admin_notes = ? 
                WHERE id = ?
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
    Útil para estadísticas.
    
    Returns:
        Número de casos pendientes
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM analisis_logs 
                WHERE user_feedback = 'NEGATIVO' AND reviewed_by_admin = 0
            """)
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"❌ Error contando pendientes: {e}")
        return 0
