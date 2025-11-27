"""
Script de Prueba para el Sistema SVM de Detección de Estafas
SecurityBot-WA - Colombia 2025
"""

import sys
import os

# Asegurar que podemos importar los módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.svm_classifier import (
    initialize_svm,
    get_svm_classifier,
    quick_check
)


def print_separator(char="=", length=70):
    """Imprime una línea separadora"""
    print(char * length)


def test_initialization():
    """Prueba 1: Inicialización del modelo"""
    print_separator()
    print("🧪 PRUEBA 1: Inicialización del Modelo SVM")
    print_separator()
    
    success = initialize_svm('app/models/svm_phishing_model.pkl')
    
    if success:
        print("✅ Modelo SVM inicializado correctamente")
        return True
    else:
        print("❌ Error al inicializar el modelo SVM")
        print("💡 Asegúrate de haber ejecutado train_svm_model.py primero")
        return False


def test_phishing_detection():
    """Prueba 2: Detección de mensajes de phishing"""
    print("\n")
    print_separator()
    print("🧪 PRUEBA 2: Detección de Mensajes de Phishing")
    print_separator()
    
    phishing_messages = [
        "BANCOLOMBIA: Su cuenta fue BLOQUEADA. Verifique URGENTE en http://bancol0mbia-seguro.co",
        "Ganaste $15.000.000 en el sorteo! Reclama tu premio: http://premio-falso.com código: WIN2025",
        "DIAN: Devolución pendiente de $2.000.000. Solicítela en http://dian-devolucion.co urgente",
        "Nequi Alerta: Verifique su cuenta en http://nequi-verify.tk o será bloqueada",
        "WhatsApp: Su cuenta será desactivada. Confirme identidad: http://wa-verificar.ml",
        "BBVA Estimado cliente: A partir del 19/06/2023, no podra utilizar su cuenta. Hasta que actualice el nuevo sistema de seguridad: https://tinyurl.com/b5ekydek"
    ]
    
    classifier = get_svm_classifier()
    results = []
    
    for i, msg in enumerate(phishing_messages, 1):
        print(f"\n📧 Mensaje #{i}:")
        print(f"   {msg[:60]}...")
        
        result = quick_check(msg)
        
        emoji = "🚨" if result['is_scam'] else "❌"
        print(f"   {emoji} Veredicto: {'ESTAFA' if result['is_scam'] else 'LEGÍTIMO'}")
        print(f"   📊 Nivel de riesgo: {result['risk_level']}")
        print(f"   📈 Confianza: {result['confidence']*100:.1f}%")
        
        results.append(result['is_scam'])
    
    # Calcular precisión
    correct = sum(results)
    total = len(results)
    accuracy = (correct / total) * 100
    
    print(f"\n📊 Resultado: {correct}/{total} phishing detectados correctamente ({accuracy:.1f}%)")
    
    return accuracy >= 80  # Mínimo 80% de detección


def test_legitimate_detection():
    """Prueba 3: Detección de mensajes legítimos"""
    print("\n")
    print_separator()
    print("🧪 PRUEBA 3: Detección de Mensajes Legítimos")
    print_separator()
    
    legitimate_messages = [
        "Bancolombia le informa: Compra aprobada por $45.000 en EXITO. Saldo: $1.250.000",
        "Hola mamá, ya llegué bien a Bogotá. Te llamo en la noche!",
        "No olvides la reunión de mañana a las 3pm en la oficina.",
        "Rappi: Tu pedido está en camino. Llega en 25 minutos.",
        "Netflix: Tu próximo pago será el 15/Dic/2025. Gracias por ser parte de Netflix."
    ]
    
    classifier = get_svm_classifier()
    results = []
    
    for i, msg in enumerate(legitimate_messages, 1):
        print(f"\n📧 Mensaje #{i}:")
        print(f"   {msg[:60]}...")
        
        result = quick_check(msg)
        
        emoji = "✅" if not result['is_scam'] else "❌"
        print(f"   {emoji} Veredicto: {'ESTAFA' if result['is_scam'] else 'LEGÍTIMO'}")
        print(f"   📊 Nivel de riesgo: {result['risk_level']}")
        print(f"   📈 Confianza: {result['confidence']*100:.1f}%")
        
        results.append(not result['is_scam'])
    
    # Calcular precisión
    correct = sum(results)
    total = len(results)
    accuracy = (correct / total) * 100
    
    print(f"\n📊 Resultado: {correct}/{total} legítimos identificados correctamente ({accuracy:.1f}%)")
    
    return accuracy >= 80  # Mínimo 80% de detección


def test_url_validation():
    """Prueba 4: Validación de URLs"""
    print("\n")
    print_separator()
    print("🧪 PRUEBA 4: Validación de URLs")
    print_separator()
    
    test_cases = [
        {
            'url': 'https://www.bancolombia.com/personas',
            'expected_safe': True,
            'description': 'URL legítima de Bancolombia'
        },
        {
            'url': 'http://bancol0mbia-seguro.co/verificar',
            'expected_safe': False,
            'description': 'Imitación de Bancolombia con "0" en lugar de "o"'
        },
        {
            'url': 'http://192.168.1.1/login',
            'expected_safe': False,
            'description': 'URL con dirección IP (muy sospechoso)'
        },
        {
            'url': 'http://premio-ganador.tk/claim',
            'expected_safe': False,
            'description': 'TLD sospechoso (.tk)'
        },
        {
            'url': 'https://www.davivienda.com',
            'expected_safe': True,
            'description': 'URL legítima de Davivienda'
        }
    ]
    
    classifier = get_svm_classifier()
    validator = classifier.url_validator
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n🔗 URL #{i}: {test['description']}")
        print(f"   {test['url']}")
        
        analysis = validator.validate_url(test['url'])
        
        is_safe = (analysis['risk_level'] in ['BAJO']) or analysis['is_legitimate']
        is_correct = (is_safe == test['expected_safe'])
        
        emoji = "✅" if is_correct else "❌"
        print(f"   {emoji} Nivel de riesgo: {analysis['risk_level']}")
        print(f"   💡 {analysis['recommendation']}")
        
        if analysis['flags']:
            print(f"   ⚠️ Alertas:")
            for flag in analysis['flags'][:2]:  # Mostrar solo primeras 2
                print(f"      • {flag}")
        
        results.append(is_correct)
    
    # Calcular precisión
    correct = sum(results)
    total = len(results)
    accuracy = (correct / total) * 100
    
    print(f"\n📊 Resultado: {correct}/{total} URLs validadas correctamente ({accuracy:.1f}%)")
    
    return accuracy >= 80  # Mínimo 80% de precisión


def test_detailed_report():
    """Prueba 5: Generación de reporte detallado"""
    print("\n")
    print_separator()
    print("🧪 PRUEBA 5: Generación de Reporte Detallado")
    print_separator()
    
    test_message = (
        "BBVA Estimado cliente: A partir del 19/06/2023, no podra utilizar su cuenta. Hasta que actualice el nuevo sistema de seguridad: https://tinyurl.com/b5ekydek"
    )
    
    print(f"\n📧 Mensaje de prueba:")
    print(f"   {test_message}")
    
    classifier = get_svm_classifier()
    report = classifier.get_detailed_report(test_message)
    
    print("\n" + report)
    
    return True


def test_performance():
    """Prueba 6: Rendimiento y velocidad"""
    print("\n")
    print_separator()
    print("🧪 PRUEBA 6: Rendimiento del Sistema")
    print_separator()
    
    import time
    
    test_message = "BANCOLOMBIA: Verifique su cuenta en http://banco-falso.co"
    
    # Medir tiempo de predicción SVM
    start = time.time()
    for _ in range(100):
        quick_check(test_message)
    end = time.time()
    
    avg_time = (end - start) / 100 * 1000  # en milisegundos
    
    print(f"⏱️ Tiempo promedio de análisis: {avg_time:.2f}ms")
    
    if avg_time < 100:
        print("✅ Rendimiento EXCELENTE (< 100ms)")
        return True
    elif avg_time < 500:
        print("✅ Rendimiento BUENO (< 500ms)")
        return True
    else:
        print("⚠️ Rendimiento ACEPTABLE (> 500ms)")
        return False


def run_all_tests():
    """Ejecuta todas las pruebas"""
    print("\n")
    print_separator("=", 70)
    print("🛡️  SISTEMA DE PRUEBAS - SVM PHISHING DETECTOR")
    print("    SecurityBot-WA Colombia 2025")
    print_separator("=", 70)
    
    tests = [
        ("Inicialización del Modelo", test_initialization),
        ("Detección de Phishing", test_phishing_detection),
        ("Detección de Legítimos", test_legitimate_detection),
        ("Validación de URLs", test_url_validation),
        ("Reporte Detallado", test_detailed_report),
        ("Rendimiento", test_performance)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Error en prueba '{test_name}': {e}")
            results.append((test_name, False))
    
    # Resumen final
    print("\n")
    print_separator("=", 70)
    print("📊 RESUMEN DE PRUEBAS")
    print_separator("=", 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        emoji = "✅" if result else "❌"
        status = "PASÓ" if result else "FALLÓ"
        print(f"   {emoji} {test_name}: {status}")
    
    print(f"\n📈 Resultados: {passed}/{total} pruebas pasadas ({passed/total*100:.1f}%)")
    
    print_separator("=", 70)
    
    if passed == total:
        print("🎉 ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE!")
        print("✅ El sistema está listo para producción")
    elif passed >= total * 0.8:
        print("✅ La mayoría de pruebas pasaron")
        print("⚠️ Revisa las pruebas fallidas antes de usar en producción")
    else:
        print("❌ Varias pruebas fallaron")
        print("🔧 Revisa la configuración y modelo antes de continuar")
    
    print_separator("=", 70)
    print()


if __name__ == "__main__":
    run_all_tests()