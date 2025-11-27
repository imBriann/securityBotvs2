"""
Sistema de Detección de Estafas con SVM - Entrenamiento
Especializado en contexto colombiano - Actualizado 2025
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import pickle
import re
from datetime import datetime
import requests
from urllib.parse import urlparse
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# DATASET DE ENTRENAMIENTO EXPANDIDO (Actualizado 2025 - Contexto Colombiano)
# ============================================================================

PHISHING_MESSAGES = [
    # Estafas bancarias Colombia 2024-2025
    "BANCOLOMBIA: Su tarjeta ha sido BLOQUEADA por actividad sospechosa. Ingrese URGENTE a http://bancol0mbia-seguridad.com/verificar para desbloquearla.",
    "Davivienda Alerta: Detectamos transacción de $2.500.000 COP. Si no fue usted, confirme sus datos en http://davivienda-verify.co/seguro",
    "BANCO DE BOGOTA - Su cuenta presenta movimientos irregulares. ACTUALICE sus datos YA en http://bdbogota-actualizacion.net o será suspendida",
    "Aviso BBVA Colombia: Debe verificar identidad para evitar bloqueo. Clic aquí: http://bbva-col-verify.com/urgente TOKEN: 947382",
    "Nequi Urgente: Su cuenta Nequi requiere verificación inmediata. Complete el proceso: http://nequi-verificacion.co/user/",
    "COLPATRIA Informa: Transacción rechazada por falta de actualización de datos. Ingrese a http://colpatria-update.com.co/cliente",
    
    # Estafas de premios y sorteos Colombia
    "FELICITACIONES! Ha ganado $15.000.000 en el sorteo de Baloto. Reclame su premio en http://baloto-premios.co/ganador codigo: BAL2025",
    "Éxito te premia! Has sido seleccionado para ganar un bono de $500.000. Reclámalo ya: http://exito-bonos.com/premio ID:EX8473",
    "Gana Colombia - Usted resultó GANADOR del iPhone 15 Pro. Reclame en las próximas 24h: http://gana-colombia.net/premio2025",
    "CLARO Sorteo Especial: Ganaste un Samsung Galaxy S24! Ingresa tus datos: http://claro-sorteos.co/winner PIN:CL9284",
    "Alkosto Aniversario: GANASTE compra de $2.000.000! Valida aquí: http://alkosto-premio.com/validar antes de mañana",
    
    # Phishing de entidades gubernamentales
    "DIAN Colombia: Tiene devolución pendiente de $1.800.000. Solicítela en http://dian-devoluciones.gov.co/tramite REF:2025-DV",
    "Ministerio de Salud: Actualice datos para asignación subsidio. http://minsalud-subsidios.co/actualizar DOC:CC",
    "SISBEN: Verifique su clasificación urgente en http://sisben-consulta.gov.co/verificar o perderá beneficios",
    "SENA Convocatoria: Fue preseleccionado para curso gratuito. Confirme: http://sena-inscripciones.edu.co/curso ID:SN2025",
    "Procuraduría General: Tiene proceso pendiente. Consulte en http://procuraduria-consultas.gov.co/expediente COD:PG8473",
    
    # Estafas de delivery y comercio
    "Rappi: Su pedido #9473 fue devuelto. Actualice dirección en http://rappi-entregas.co/actualizar o será cancelado",
    "Mercado Libre Alerta: Problema con su compra #ML847362. Verifique: http://mercadolibre-soporte.com/problema",
    "Amazon Colombia: Paquete retenido en aduana. Pague $85.000 en http://amazon-aduanas.co/pago GUIA:AMZ9473",
    "Servientrega Aviso: Paquete para usted requiere pago adicional $45.000. http://servientrega-pagos.com/guia TRK:SV2025",
    
    # Estafas de empleo
    "Oferta Trabajo Remoto: Gane $3.500.000/mes desde casa. Inscribase: http://trabajo-remoto-col.com/registro No requiere experiencia",
    "Banco de Occidente busca asesores. Salario $2.800.000 + prestaciones. Aplique: http://occidente-empleo.co/postular",
    "Rappi busca domiciliarios. Gane hasta $150.000/día. Registrese: http://rappi-registro.com/domiciliario CUPOS LIMITADOS",
    
    # Estafas románticas/sexting
    "Hola! Vi tu perfil y me gustaste mucho 😍 Quiero conocerte mejor, mira mis fotos: http://citas-colombia.net/perfil/maria2025",
    "Hola amor, soy Carolina de Medellín, chatea conmigo: http://chicas-calientes.co/chat/carolina PIN:9473",
    
    # Estafas de criptomonedas
    "Invierte en Bitcoin y duplica tu dinero en 30 días! Plataforma colombiana regulada: http://crypto-colombia.co/invertir",
    "BINANCE COLOMBIA: Promoción especial, deposite $500.000 y reciba $500.000 GRATIS: http://binance-promo.co/deposito",
    
    # Estafas de servicios públicos
    "EPM Informa: Factura vencida #947382 por $186.000. Evite corte del servicio: http://epm-pagos.com.co/factura",
    "ACUEDUCTO BOGOTA: Deuda pendiente. Pague ya en http://acueducto-bog.co/deuda o suspenderemos servicio mañana",
    "Gas Natural: Su servicio será cortado por mora. Pague urgente: http://gasnatural-pagos.co/mora REF:GN2025",
    
    # Estafas de Netflix/streaming
    "Netflix Colombia: Su suscripción expira hoy. Renueve en http://netflix-renovacion.co/pago o perderá acceso",
    "Spotify Premium: Problema con su pago. Actualice datos: http://spotify-pagos.com/actualizar",
    
    # Estafas WhatsApp/redes sociales
    "WhatsApp: Su cuenta será desactivada por violar políticas. Verifique: http://whatsapp-verificacion.net/cuenta",
    "Facebook Security: Alguien intentó acceder a su cuenta desde Cali. Cambie contraseña: http://fb-security.co/cambiar",
    "Instagram: Su cuenta @usuario fue reportada. Evite suspensión: http://instagram-apelacion.com/verificar",
    
    # Estafas de seguros/salud
    "SURA EPS: Requiere actualización de datos para mantener afiliación. http://sura-actualizacion.com.co/eps",
    "Seguro funerario: Cubra a su familia por solo $15.000/mes. Info: http://seguros-funerarios.co/cotizar",
    
    # Estafas de créditos rápidos
    "Crédito aprobado $5.000.000! Sin requisitos, deposito inmediato: http://creditos-rapidos-col.com/solicitud",
    "Finanzas Fácil: Préstamo preaprobado hasta $8.000.000. Reclámelo: http://finanzas-facil.co/prestamo ID:FF2025",
    
    # Nuevas modalidades 2025
    "Gobierno Nacional: Subsidio único de $800.000 por COVID-19. Reclame: http://subsidio-covid.gov.co/reclamar",
    "Policía Nacional: Multa de tránsito pendiente #PO847392. Pague con descuento 50%: http://policia-multas.gov.co/pagar",
    "TransMilenio: Su tarjeta Tullave fue bloqueada. Reactive: http://transmilenio-tullave.co/activar",
]

LEGITIMATE_MESSAGES = [
    # Mensajes legítimos de bancos (sin URLs o URLs reales)
    "Bancolombia le informa: Compra aprobada por $45.000 en EXITO. Saldo disponible: $1.250.000. No comparte este mensaje.",
    "Davivienda: Su transferencia de $200.000 a Juan Perez fue exitosa. Ref: 847392847. Consulte en www.davivienda.com",
    "BBVA: Retiro en cajero por $100.000. Nuevo saldo: $850.000. Si no reconoce, llame al 018000912220",
    "Nequi: Recibiste $50.000 de Maria Lopez. Tu nuevo saldo es $320.000",
    "Banco de Bogotá: Pago de tarjeta recibido por $300.000. Próximo pago: 15/Dic/2025",
    
    # Mensajes legítimos de servicios
    "Su código de verificación de WhatsApp es: 847-392. No comparta este código con nadie.",
    "Rappi: Tu pedido #RP847392 está en camino. Llega en 25 minutos. Gracias por tu compra!",
    "Uber: Tu viaje con Juan (Chevrolet Spark XYZ123) llegará en 3 minutos. Calificación: 4.9⭐",
    "Netflix: Tu próximo pago de $16.900 será el 15/Dic/2025. Gracias por ser parte de Netflix.",
    "Claro Colombia: Recarga exitosa $10.000. Saldo: $15.000. Vigencia: 30 días.",
    
    # Mensajes personales normales
    "Hola mamá, llegué bien a Bogotá. Te llamo en la noche. Te quiero!",
    "No olvides la reunión de mañana a las 3pm en la oficina. Trae los documentos.",
    "Feliz cumpleaños! Espero que la pases super bien hoy. Un abrazo!",
    "Ya salí del trabajo, llego en 20 minutos a casa. ¿Necesitas que compre algo?",
    "Gracias por el almuerzo de ayer, estuvo delicioso! Nos vemos el fin de semana.",
    
    # Notificaciones legítimas de apps
    "Amazon: Su paquete llegará mañana entre 8am-12pm. Rastree en amazon.com.co con #AMZ847392",
    "Mercado Libre: Califica tu compra y ayuda a otros compradores. Tu opinión es importante.",
    "iFood: Tu pedido de La Parrilla está listo! El domiciliario va en camino.",
    "LinkedIn: Tienes 3 nuevas solicitudes de conexión y 5 vistas de perfil esta semana.",
    "Gmail: Nuevo correo de trabajo@empresa.com con asunto 'Reunión mensual'",
    
    # Mensajes de servicios públicos legítimos
    "EPM informa: Su factura de Diciembre 2025 por $125.000 está disponible en www.epm.com.co",
    "Acueducto Bogotá: Mantenimiento programado en su sector el 28/Nov de 8am a 12pm.",
    "ETB: Su plan de internet ha sido renovado exitosamente. Vigencia: 30 días.",
    
    # Mensajes de salud
    "EPS Sura: Recuerde su cita médica el 30/Nov a las 10am con Dr. Rodríguez. Consultorio 304.",
    "Laboratorio Clínico: Sus resultados están listos. Puede recogerlos en horario de 8am-5pm.",
    
    # Mensajes educativos
    "SENA: Inscripciones abiertas para cursos virtuales 2025. Consulte oferta en www.senasofiaplus.edu.co",
    "Universidad Nacional: Resultados de admisión disponibles en www.unal.edu.co desde el 1 de Diciembre.",
    
    # Mensajes de trabajo
    "Recursos Humanos: Recuerde subir su certificado de vacunación al portal antes del viernes.",
    "Nómina: Su pago de Noviembre fue consignado exitosamente. Revise su cuenta.",
    
    # Confirmaciones de citas/reservas
    "Recordatorio: Cita odontológica mañana 29/Nov a las 4pm con Dra. Martinez.",
    "Reserva confirmada: Hotel Bogotá Plaza - 2 noches desde 01/Dic/2025. Código: HP847392",
    
    # Mensajes de transporte
    "Avianca: Check-in disponible para su vuelo AV8473 Bogotá-Cartagena del 30/Nov.",
    "TransMilenio: Por obras, la ruta B23 tendrá desvío desde mañana. Consulte rutas alternas.",
]

# ============================================================================
# FUNCIONES DE EXTRACCIÓN DE CARACTERÍSTICAS
# ============================================================================

def extract_url_features(text):
    """Extrae características de URLs en el texto"""
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
    
    features = {
        'num_urls': len(urls),
        'has_url': 1 if urls else 0,
        'suspicious_domain': 0,
        'ip_address': 0,
        'shortened_url': 0,
        'suspicious_tld': 0
    }
    
    suspicious_patterns = [
        'verificar', 'actualizar', 'seguridad', 'urgente', 'premio',
        'ganador', 'verificacion', 'actualizacion', 'confirm', 'verify'
    ]
    
    suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.gq', '.xyz', '.top', '.club']
    shorteners = ['bit.ly', 'tinyurl', 'goo.gl', 't.co', 'ow.ly', 'is.gd']
    
    for url in urls:
        parsed = urlparse(url.lower())
        domain = parsed.netloc
        
        # Verificar patrones sospechosos en dominio
        if any(pattern in domain for pattern in suspicious_patterns):
            features['suspicious_domain'] = 1
        
        # Detectar IP en lugar de dominio
        if re.match(r'\d+\.\d+\.\d+\.\d+', domain):
            features['ip_address'] = 1
        
        # Detectar acortadores de URL
        if any(shortener in domain for shortener in shorteners):
            features['shortened_url'] = 1
        
        # Detectar TLDs sospechosos
        if any(domain.endswith(tld) for tld in suspicious_tlds):
            features['suspicious_tld'] = 1
    
    return features

def extract_text_features(text):
    """Extrae características del texto"""
    text_lower = text.lower()
    
    # Palabras clave urgentes en español
    urgency_words = [
        'urgente', 'inmediatamente', 'ahora', 'ya', 'rápido', 'expira',
        'último', 'hoy', 'mañana', '24 horas', 'caducidad'
    ]
    
    # Palabras relacionadas con dinero/premios
    money_words = [
        'ganaste', 'premio', 'millones', 'gratis', 'descuento',
        'promoción', 'sorteo', 'ganador', 'dinero', '$', 'cop', 'pesos'
    ]
    
    # Palabras relacionadas con acciones requeridas
    action_words = [
        'verificar', 'confirmar', 'actualizar', 'validar', 'ingresar',
        'completar', 'enviar', 'responder', 'clic', 'click', 'descargar'
    ]
    
    # Palabras relacionadas con amenazas
    threat_words = [
        'bloqueada', 'suspendida', 'cancelada', 'desactivada', 'cerrada',
        'multa', 'deuda', 'mora', 'corte', 'perderá', 'problema'
    ]
    
    features = {
        'length': len(text),
        'num_words': len(text.split()),
        'has_urgency': sum(1 for word in urgency_words if word in text_lower),
        'has_money': sum(1 for word in money_words if word in text_lower),
        'has_action': sum(1 for word in action_words if word in text_lower),
        'has_threat': sum(1 for word in threat_words if word in text_lower),
        'num_numbers': len(re.findall(r'\d+', text)),
        'num_caps': sum(1 for c in text if c.isupper()),
        'has_exclamation': text.count('!'),
        'has_question': text.count('?'),
        'num_dots': text.count('.'),
    }
    
    return features

def create_feature_vector(text):
    """Combina todas las características en un vector"""
    url_feats = extract_url_features(text)
    text_feats = extract_text_features(text)
    
    # Combinar diccionarios
    all_features = {**url_feats, **text_feats}
    
    return list(all_features.values())

# ============================================================================
# PREPARACIÓN DE DATOS
# ============================================================================

def prepare_dataset():
    """Prepara el dataset completo"""
    
    # Crear DataFrame
    data = {
        'message': PHISHING_MESSAGES + LEGITIMATE_MESSAGES,
        'label': [1] * len(PHISHING_MESSAGES) + [0] * len(LEGITIMATE_MESSAGES)
    }
    
    df = pd.DataFrame(data)
    
    # Mezclar datos
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    print(f"📊 Dataset creado:")
    print(f"   Total mensajes: {len(df)}")
    print(f"   Phishing: {sum(df['label'] == 1)} ({sum(df['label'] == 1)/len(df)*100:.1f}%)")
    print(f"   Legítimos: {sum(df['label'] == 0)} ({sum(df['label'] == 0)/len(df)*100:.1f}%)")
    
    return df

# ============================================================================
# ENTRENAMIENTO DEL MODELO
# ============================================================================

def train_model(df):
    """Entrena el modelo SVM con optimización de hiperparámetros"""
    
    print("\n🔧 Iniciando entrenamiento del modelo SVM...")
    
    # Separar features y labels
    X = df['message']
    y = df['label']
    
    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Pipeline con TF-IDF y SVM
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 3),  # unigrams, bigrams, trigrams
            min_df=1,
            max_df=0.8,
            sublinear_tf=True
        )),
        ('svm', SVC(kernel='rbf', probability=True, random_state=42))
    ])
    
    # Grid Search para optimizar hiperparámetros
    param_grid = {
        'svm__C': [0.1, 1, 10, 100],
        'svm__gamma': ['scale', 'auto', 0.001, 0.01, 0.1],
    }
    
    print("🔍 Buscando mejores hiperparámetros...")
    grid_search = GridSearchCV(
        pipeline, param_grid, cv=5, scoring='f1', 
        n_jobs=-1, verbose=1
    )
    
    grid_search.fit(X_train, y_train)
    
    # Mejor modelo
    best_model = grid_search.best_estimator_
    
    print(f"\n✅ Mejores parámetros encontrados:")
    print(f"   C: {grid_search.best_params_['svm__C']}")
    print(f"   Gamma: {grid_search.best_params_['svm__gamma']}")
    
    # Evaluación
    y_pred = best_model.predict(X_test)
    
    print(f"\n📈 Resultados en conjunto de prueba:")
    print(f"   Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    
    print("\n📊 Reporte de Clasificación:")
    print(classification_report(y_test, y_pred, 
                                target_names=['Legítimo', 'Phishing']))
    
    print("\n🎯 Matriz de Confusión:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"   Verdaderos Negativos: {cm[0][0]}")
    print(f"   Falsos Positivos: {cm[0][1]}")
    print(f"   Falsos Negativos: {cm[1][0]}")
    print(f"   Verdaderos Positivos: {cm[1][1]}")
    
    # Cross-validation
    print("\n🔄 Validación cruzada (5-fold):")
    cv_scores = cross_val_score(best_model, X, y, cv=5, scoring='f1')
    print(f"   F1 Score promedio: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
    
    return best_model, X_test, y_test

# ============================================================================
# GUARDADO DEL MODELO
# ============================================================================

def save_model(model, filename='svm_phishing_model.pkl'):
    """Guarda el modelo entrenado"""
    
    model_data = {
        'model': model,
        'trained_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': '2.0',
        'country': 'Colombia',
        'description': 'SVM para detección de phishing/estafas en mensajes colombianos'
    }
    
    with open(filename, 'wb') as f:
        pickle.dump(model_data, f)
    
    print(f"\n💾 Modelo guardado exitosamente en: {filename}")
    print(f"   Fecha: {model_data['trained_date']}")
    print(f"   Versión: {model_data['version']}")

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Función principal de entrenamiento"""
    
    print("="*70)
    print("🛡️  SISTEMA DE DETECCIÓN DE ESTAFAS CON SVM")
    print("    SecurityBot-WA - Colombia 2025")
    print("="*70)
    
    # Preparar dataset
    df = prepare_dataset()
    
    # Entrenar modelo
    model, X_test, y_test = train_model(df)
    
    # Guardar modelo
    save_model(model)
    
    print("\n" + "="*70)
    print("✅ ENTRENAMIENTO COMPLETADO EXITOSAMENTE")
    print("="*70)
    
    # Pruebas rápidas
    print("\n🧪 Pruebas rápidas:")
    
    test_messages = [
        "BANCOLOMBIA: Su cuenta fue bloqueada. Verifique en http://banco-seguro.co",
        "Hola mamá, ya llegué bien a casa. Te llamo luego.",
        "Ganaste $10.000.000! Reclama tu premio en http://premio-falso.com URGENTE"
    ]
    
    for msg in test_messages:
        pred = model.predict([msg])[0]
        proba = model.predict_proba([msg])[0]
        label = "🚨 PHISHING" if pred == 1 else "✅ LEGÍTIMO"
        confidence = max(proba) * 100
        
        print(f"\n   Mensaje: {msg[:60]}...")
        print(f"   Predicción: {label} (Confianza: {confidence:.1f}%)")

if __name__ == "__main__":
    main()