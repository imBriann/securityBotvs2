"""
Módulo de reentrenamiento automático del modelo SVM.
Implementa RLHF (Reinforcement Learning from Human Feedback) con filtros de seguridad.

Características de seguridad:
- NO se entrena con dislikes automáticamente (evita data poisoning)
- Solo acepta feedback positivo o dislikes revisados manualmente por admin
- Genera reportes de cambios antes de aplicar
"""

import pickle
import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple
from app.services.svm_classifier import svm_classifier
from app.storage.feedback_db import (
    get_data_for_retraining,
    get_unreviewed_negatives,
    get_feedback_stats
)
from app.utils.config import DB_NAME


def analyze_feedback_quality() -> Dict:
    """
    Analiza la calidad general del feedback y detecta posibles problemas.
    
    Returns:
        Diccionario con análisis de calidad
    """
    print("🔍 Analizando calidad del feedback...")
    
    stats = get_feedback_stats()
    
    analysis = {
        'total_feedback': stats.get('positive_feedback', 0) + stats.get('negative_feedback', 0),
        'accuracy_rate': stats.get('accuracy_rate', 0),
        'potential_poisoning_risk': 'ALTO' if stats.get('unreviewed_negatives', 0) > stats.get('positive_feedback', 0) else 'BAJO',
        'recommendation': ''
    }
    
    # Generar recomendación
    if analysis['accuracy_rate'] > 90:
        analysis['recommendation'] = '✅ Alta precisión detectada. Sistema listo para aprender.'
    elif analysis['accuracy_rate'] > 75:
        analysis['recommendation'] = '⚠️ Precisión moderada. Revisar casos negativos antes de reentrenar.'
    else:
        analysis['recommendation'] = '❌ Baja precisión. Sistema requiere revisión manual antes de ajustes.'
    
    return analysis


def generate_retraining_report() -> str:
    """
    Genera un reporte detallado sobre lo que sucedería si se entrena ahora.
    
    Returns:
        Reporte formateado como string
    """
    print("📋 Generando reporte de reentrenamiento...")
    
    stats = get_feedback_stats()
    quality = analyze_feedback_quality()
    new_data = get_data_for_retraining(limit=100)
    unreviewed = get_unreviewed_negatives(limit=10)
    
    report = []
    report.append("=" * 70)
    report.append("📊 REPORTE DE REENTRENAMIENTO DEL MODELO SVM")
    report.append("=" * 70)
    report.append(f"\n⏰ Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Sección 1: Estadísticas actuales
    report.append("📈 ESTADÍSTICAS ACTUALES:")
    report.append(f"   • Total de análisis: {stats.get('total_analyses', 0)}")
    report.append(f"   • Feedback positivo: {stats.get('positive_feedback', 0)}")
    report.append(f"   • Feedback negativo: {stats.get('negative_feedback', 0)}")
    report.append(f"   • Cobertura de feedback: {stats.get('feedback_coverage', 0)}%")
    report.append(f"   • Tasa de acierto: {stats.get('accuracy_rate', 0)}%")
    report.append(f"   • Dislikes sin revisar: {stats.get('unreviewed_negatives', 0)}")
    
    # Sección 2: Análisis de calidad
    report.append("\n🔍 ANÁLISIS DE CALIDAD:")
    report.append(f"   • Riesgo de envenenamiento: {quality.get('potential_poisoning_risk', 'DESCONOCIDO')}")
    report.append(f"   • Recomendación: {quality.get('recommendation', 'N/A')}")
    
    # Sección 3: Datos disponibles para entrenamiento
    report.append(f"\n💾 DATOS DISPONIBLES PARA REENTRENAMIENTO:")
    report.append(f"   • Total de registros seguros: {len(new_data)}")
    if len(new_data) > 0:
        scam_count = sum(1 for d in new_data if d.get('final_is_scam') == 1)
        legit_count = len(new_data) - scam_count
        report.append(f"   • Ejemplos de ESTAFA: {scam_count}")
        report.append(f"   • Ejemplos LEGÍTIMOS: {legit_count}")
        report.append(f"   • Balance: {round(scam_count/len(new_data)*100, 1)}% estafas / {round(legit_count/len(new_data)*100, 1)}% legítimos")
    else:
        report.append("   ⚠️ Sin datos seguros disponibles")
    
    # Sección 4: Casos problemáticos no revisados
    if unreviewed:
        report.append(f"\n⚠️ CASOS PROBLEMÁTICOS SIN REVISAR (primeros 10):")
        for i, case in enumerate(unreviewed[:10], 1):
            msg_preview = case.get('message_content', 'N/A')[:50]
            verdict = 'ESTAFA' if case.get('final_is_scam') else 'LEGÍTIMO'
            report.append(f"   {i}. Veredicto: {verdict} | Usuario rechazó con 👎")
            report.append(f"      Mensaje: {msg_preview}...")
    else:
        report.append("\n✅ No hay casos problemáticos sin revisar")
    
    # Sección 5: Acción recomendada
    report.append("\n" + "=" * 70)
    report.append("🎯 ACCIÓN RECOMENDADA:")
    if len(new_data) < 10:
        report.append("   ❌ ESPERAR: Insuficientes datos para reentrenar (mín. 10)")
    elif stats.get('unreviewed_negatives', 0) > stats.get('positive_feedback', 0):
        report.append("   ⚠️ REVISAR PRIMERO: Revisar dislikes antes de reentrenar")
        report.append("      Usa: /review_negatives para ver casos problemáticos")
    elif stats.get('accuracy_rate', 0) < 75:
        report.append("   ⚠️ PRECAUCIÓN: Baja precisión. Manual review recomendado.")
    else:
        report.append("   ✅ LISTO: Sistema está seguro para reentrenamiento")
    
    report.append("=" * 70 + "\n")
    
    return "\n".join(report)


def prepare_retraining_data() -> Tuple[List[str], List[int], int]:
    """
    Prepara los datos seguros para reentrenamiento.
    
    Returns:
        Tupla (textos, etiquetas, cantidad_nuevos_datos)
    """
    print("🛠️ Preparando datos para reentrenamiento...")
    
    # Obtener datos seguros de la BD
    safe_data = get_data_for_retraining(limit=500)
    
    if not safe_data:
        print("⚠️ No hay datos seguros disponibles")
        return [], [], 0
    
    texts = []
    labels = []
    
    for record in safe_data:
        text = record.get('message_content', '')
        label = record.get('final_is_scam', 0)
        
        if text:
            texts.append(text)
            labels.append(label)
    
    print(f"✅ Preparados {len(texts)} textos con sus etiquetas")
    return texts, labels, len(texts)


def simulate_retraining() -> Dict:
    """
    Simula un reentrenamiento SIN modificar el modelo actual.
    Útil para validar qué pasaría si se aplicara.
    
    Returns:
        Diccionario con resultados de la simulación
    """
    print("\n🧪 SIMULANDO REENTRENAMIENTO (sin aplicar cambios)...\n")
    
    texts, labels, count = prepare_retraining_data()
    
    simulation = {
        'new_training_samples': count,
        'scam_samples': sum(labels),
        'legitimate_samples': len(labels) - sum(labels),
        'would_improve': count >= 10,
        'status': '✅ Seguro' if count >= 10 else '❌ Insuficientes datos'
    }
    
    return simulation


def execute_retraining(force_unsafe: bool = False) -> Dict:
    """
    Ejecuta el reentrenamiento del modelo SVM.
    
    IMPORTANTE: Esta función NO entrena realmente el modelo SVM.
    Solo prepara los datos y retorna instrucciones.
    El reentrenamiento real requeriría acceso al pipeline original de sklearn.
    
    Args:
        force_unsafe: Si True, ignora advertencias de seguridad (no recomendado)
    
    Returns:
        Diccionario con resultado de la operación
    """
    print("\n🧠 INICIANDO REENTRENAMIENTO DEL MODELO...\n")
    
    # Obtener reporte
    quality = analyze_feedback_quality()
    
    # Validaciones de seguridad
    if not force_unsafe and quality.get('potential_poisoning_risk') == 'ALTO':
        print("❌ BLOQUEADO: Riesgo alto de envenenamiento de datos")
        print("   Revisar casos negativos sin validar antes de reentrenar")
        return {
            'success': False,
            'error': 'Riesgo de envenenamiento detectado',
            'recommendation': '/review_negatives'
        }
    
    # Preparar datos
    texts, labels, new_count = prepare_retraining_data()
    
    if new_count < 10:
        print(f"❌ BLOQUEADO: Insuficientes datos ({new_count}/10)")
        return {
            'success': False,
            'error': f'Solo {new_count} ejemplos. Mínimo requerido: 10',
            'waiting_for': 10 - new_count
        }
    
    # Log de cambios
    print("\n" + "=" * 70)
    print("📝 REGISTRO DE CAMBIOS:")
    print(f"   ✅ Nuevos ejemplos de entrenamiento: {new_count}")
    print(f"   ✅ Balance: {sum(labels)} estafas, {len(labels) - sum(labels)} legítimos")
    print("=" * 70)
    
    # NOTA: Aquí es donde irían los comandos reales de sklearn:
    # vectorizer = TfidfVectorizer(...)
    # X_new = vectorizer.fit_transform(texts)
    # svm_classifier.model.fit(X_new, labels)
    # pickle.dump({'model': svm_classifier.model, 'training_data_x': texts, ...}, ...)
    
    print("\n⚠️  NOTA: El reentrenamiento real requiere ejecutar el script de entrenamiento original")
    print("   Los datos están listos, pero se recomienda revisar antes de aplicar.")
    
    return {
        'success': True,
        'message': 'Datos preparados. Requiere ejecución del script de entrenamiento real.',
        'data_ready': {
            'total_samples': new_count,
            'scam_samples': sum(labels),
            'legitimate_samples': len(labels) - sum(labels),
            'recommendation': 'Ejecutar: python -m app.scripts.retrain_svm'
        }
    }


def get_retraining_summary() -> str:
    """
    Resumen rápido para el admin sobre el estado del reentrenamiento.
    """
    stats = get_feedback_stats()
    quality = analyze_feedback_quality()
    
    summary = f"""
🤖 RESUMEN DE REENTRENAMIENTO:

📊 Estado:
   • Análisis realizados: {stats.get('total_analyses', 0)}
   • Feedback recibido: {stats.get('positive_feedback', 0) + stats.get('negative_feedback', 0)}
   • Precisión: {stats.get('accuracy_rate', 0)}%

⚠️  Seguridad:
   • Riesgo: {quality.get('potential_poisoning_risk', 'DESCONOCIDO')}
   • Dislikes sin revisar: {stats.get('unreviewed_negatives', 0)}

🎯 Acción:
   {quality.get('recommendation', 'N/A')}

📌 Próximos pasos:
   • Ver reporte: /retrain_report
   • Ver negativos: /review_negatives
   • Ejecutar reentrenamiento: /do_retrain
"""
    return summary
