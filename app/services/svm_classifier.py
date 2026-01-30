"""
Módulo mejorado de clasificación SVM con validación de URLs
SecurityBot-WA - Colombia 2025
"""
from typing import Optional, Tuple, Dict, List
import pickle
import os
import re
import httpx
from urllib.parse import urlparse
import asyncio


class URLValidator:
    """Validador de URLs para detectar enlaces maliciosos"""
    
    # Dominios legítimos conocidos en Colombia
    LEGITIMATE_DOMAINS = {
        # Bancos
        'bancolombia.com', 'davivienda.com', 'bancodebogota.com', 'bbva.com.co',
        'bancoagrario.gov.co', 'bancopopular.com.co', 'avvillas.com.co',
        'colpatria.com.co', 'bancocajasocial.com', 'bancow.com.co',
        
        # Nequi y fintech
        'nequi.com.co', 'daviplata.com', 'movii.com.co', 'powwi.co',
        
        # Gobierno
        'gov.co', 'dian.gov.co', 'procuraduria.gov.co', 'policia.gov.co',
        'sisben.gov.co', 'minsalud.gov.co',
        
        # Servicios públicos
        'epm.com.co', 'eaab.com.co', 'codensa.com.co', 'etb.com.co',
        'gasnatural.com.co',
        
        # E-commerce y delivery
        'mercadolibre.com.co', 'amazon.com.co', 'exito.com', 'falabella.com.co',
        'rappi.com.co', 'ifood.com.co', 'ubereats.com',
        
        # Telecomunicaciones
        'claro.com.co', 'movistar.co', 'tigo.com.co', 'wom.co', 'virginmobile.co', 'virg.in',
        
        # Streaming
        'netflix.com', 'spotify.com', 'primevideo.com', 'disneyplus.com',
        
        # Educación
        'sena.edu.co', 'senasofiaplus.edu.co', 'unal.edu.co', 'icfes.gov.co',
        'unipamplona.edu.co', 'unandes.edu.co', 'javeriana.edu.co', 'mineducacion.gov.co',
        
        # Transporte
        'avianca.com', 'latam.com', 'wingo.com', 'transmilenio.gov.co',
        
        # Redes sociales y comunicación
        'whatsapp.com', 'facebook.com', 'instagram.com', 'x.com',
        'linkedin.com', 'telegram.org'
    }
    
    # TLDs sospechosos
    SUSPICIOUS_TLDS = [
        '.tk', '.ml', '.ga', '.cf', '.gq', '.xyz', '.top', '.club',
        '.work', '.click', '.link', '.download', '.stream', '.trade'
    ]
    
    # Acortadores de URL conocidos
    URL_SHORTENERS = [
        'bit.ly', 'tinyurl.com', 'goo.gl', 't.co', 'ow.ly', 'is.gd',
        'buff.ly', 'adf.ly', 'shorte.st', 'ouo.io'
    ]
    
    # Patrones sospechosos en URLs
    SUSPICIOUS_PATTERNS = [
        r'verificar', r'actualizar', r'seguridad', r'urgente', r'premio',
        r'ganador', r'verificacion', r'actualizacion', r'confirm', r'verify',
        r'secure', r'account', r'login', r'signin', r'update', r'validate',
        r'suspended', r'locked', r'blocked', r'winner', r'claim'
    ]
    
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
    
    def extract_urls(self, text: str) -> List[str]:
        """Extrae todas las URLs de un texto"""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.findall(url_pattern, text)
    
    def analyze_url_structure(self, url: str) -> Dict:
        """Analiza la estructura de una URL y detecta características sospechosas"""
        parsed = urlparse(url.lower())
        domain = parsed.netloc
        path = parsed.path
        
        analysis = {
            'url': url,
            'domain': domain,
            'is_legitimate': False,
            'is_suspicious': False,
            'risk_score': 0,
            'flags': []
        }
        
        # Verificar si es dominio legítimo conocido
        for legit_domain in self.LEGITIMATE_DOMAINS:
            if domain == legit_domain or domain.endswith('.' + legit_domain):
                analysis['is_legitimate'] = True
                return analysis
        
        # Verificar IP en lugar de dominio (muy sospechoso)
        if re.match(r'\d+\.\d+\.\d+\.\d+', domain):
            analysis['is_suspicious'] = True
            analysis['risk_score'] += 40
            analysis['flags'].append('URL usa dirección IP en lugar de dominio')
        
        # Verificar TLDs sospechosos
        for tld in self.SUSPICIOUS_TLDS:
            if domain.endswith(tld):
                analysis['is_suspicious'] = True
                analysis['risk_score'] += 30
                analysis['flags'].append(f'Usa TLD sospechoso: {tld}')
                break
        
        # Verificar acortadores de URL (MUY SOSPECHOSO en contexto bancario)
        for shortener in self.URL_SHORTENERS:
            if shortener in domain:
                analysis['is_suspicious'] = True
                analysis['risk_score'] += 45  # Aumentado de 15 a 45
                analysis['flags'].append('⚠️ URL ACORTADA - Los bancos NUNCA usan acortadores de enlaces')
                break
        
        # Verificar patrones sospechosos en dominio/path
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, domain + path):
                analysis['is_suspicious'] = True
                analysis['risk_score'] += 20
                analysis['flags'].append(f'Contiene patrón sospechoso: {pattern}')
        
        # Verificar subdominios excesivos (ej: banco.verificar.seguridad.com)
        subdomain_count = domain.count('.')
        if subdomain_count > 3:
            analysis['risk_score'] += 15
            analysis['flags'].append('Múltiples subdominios (posible imitación)')
        
        # Verificar caracteres sospechosos en dominio (ej: bancol0mbia con cero)
        if re.search(r'[0-9]', domain.replace('www.', '').split('.')[0]):
            analysis['risk_score'] += 25
            analysis['flags'].append('Dominio contiene números (posible imitación)')
        
        # Verificar guiones múltiples (ej: banco-colombia-seguro.com)
        if domain.count('-') >= 2:
            analysis['risk_score'] += 15
            analysis['flags'].append('Múltiples guiones en dominio')
        
        # BONIFICACIÓN DE CONFIANZA: Dominios educativos y gubernamentales
        # Reduce el riesgo automáticamente porque estos dominios son verificados por el estado
        if domain.endswith('.edu.co') or domain.endswith('.gov.co'):
            analysis['risk_score'] = max(0, analysis['risk_score'] - 30)  # Reducir riesgo
            analysis['flags'].append("✅ Dominio institucional (.edu/.gov) - Genera confianza")
        
        # Clasificación final
        if analysis['risk_score'] >= 50:
            analysis['is_suspicious'] = True
        
        return analysis
    
    async def check_url_online(self, url: str) -> Dict:
        """Verifica si una URL está activa y obtiene información adicional"""
        result = {
            'is_reachable': False,
            'status_code': None,
            'redirects': False,
            'final_url': url
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.head(url)
                result['is_reachable'] = True
                result['status_code'] = response.status_code
                result['final_url'] = str(response.url)
                result['redirects'] = (str(response.url) != url)
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def validate_url(self, url: str) -> Dict:
        """Validación completa de URL (síncrona)"""
        analysis = self.analyze_url_structure(url)
        
        # Clasificación de riesgo
        if analysis['is_legitimate']:
            risk_level = 'BAJO'
            recommendation = '✅ URL de fuente legítima conocida'
        elif analysis['risk_score'] >= 70:
            risk_level = 'CRÍTICO'
            recommendation = '🚨 NO ABRIR - URL altamente sospechosa'
        elif analysis['risk_score'] >= 50:
            risk_level = 'ALTO'
            recommendation = '⚠️ PELIGRO - Evitar abrir esta URL'
        elif analysis['risk_score'] >= 30:
            risk_level = 'MEDIO'
            recommendation = '⚠️ PRECAUCIÓN - Verificar antes de abrir'
        else:
            risk_level = 'BAJO'
            recommendation = 'ℹ️ URL parece segura, pero siempre verifica'
        
        return {
            **analysis,
            'risk_level': risk_level,
            'recommendation': recommendation
        }


class ImprovedSVMClassifier:
    """
    Clasificador SVM mejorado con validación de URLs integrada
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Inicializa el clasificador SVM mejorado.
        
        Args:
            model_path: Ruta al archivo del modelo entrenado (.pkl)
        """
        self.model = None
        self.model_data = None
        
        if model_path:
            self.model_path = model_path
        else:
            # Usar ruta absoluta relativa al archivo actual para funcionar en cualquier contexto
            current_dir = os.path.dirname(os.path.abspath(__file__))
            app_root = os.path.dirname(current_dir)  # Sube a app/
            self.model_path = os.path.join(app_root, "models", "svm_phishing_model.pkl")
        
        self.url_validator = URLValidator()
        
    def load_model(self) -> bool:
        """
        Carga el modelo SVM pre-entrenado.
        
        Returns:
            True si el modelo se cargó exitosamente, False en caso contrario
        """
        print(f"🔍 Buscando modelo SVM en: {self.model_path}")
        print(f"   Ruta absoluta resolvida: {os.path.abspath(self.model_path)}")
        print(f"   Existe: {os.path.exists(self.model_path)}")
        
        if not os.path.exists(self.model_path):
            print(f"⚠️ No se encontró el modelo SVM en {self.model_path}")
            # Listar archivos disponibles para debugging
            models_dir = os.path.dirname(self.model_path)
            if os.path.exists(models_dir):
                print(f"   Archivos en {models_dir}:")
                for f in os.listdir(models_dir):
                    print(f"      - {f}")
            return False
            
        try:
            with open(self.model_path, 'rb') as f:
                self.model_data = pickle.load(f)
                self.model = self.model_data.get('model')
            
            print(f"✅ Modelo SVM cargado exitosamente desde {self.model_path}")
            print(f"   Fecha entrenamiento: {self.model_data.get('trained_date', 'N/A')}")
            print(f"   Versión: {self.model_data.get('version', 'N/A')}")
            return True
        except Exception as e:
            import traceback
            print(f"❌ Error al cargar el modelo SVM: {e}")
            print(traceback.format_exc())
            return False
    
    def predict(self, text: str) -> Optional[Tuple[str, float]]:
        """
        Predice si un mensaje es phishing/estafa.
        
        Args:
            text: Texto del mensaje a clasificar
            
        Returns:
            Tupla (predicción, confianza) donde predicción es "phishing" o "legítimo"
            y confianza es un valor entre 0 y 1. Retorna None si hay error.
        """
        if not self.model:
            print("❌ Modelo SVM no cargado. Llama a load_model() primero.")
            return None
            
        try:
            # Hacer predicción
            prediction = self.model.predict([text])[0]
            
            # Obtener probabilidad
            probabilities = self.model.predict_proba([text])[0]
            confidence = max(probabilities)
            
            label = "phishing" if prediction == 1 else "legítimo"
            
            return (label, confidence)
            
        except Exception as e:
            print(f"❌ Error en predicción SVM: {e}")
            return None
    
    def analyze_message(self, text: str, check_urls: bool = True) -> Dict:
        """
        Analiza un mensaje completo con SVM y validación de URLs.
        
        Args:
            text: Texto del mensaje a analizar
            check_urls: Si True, también valida URLs encontradas
            
        Returns:
            Diccionario completo con análisis
        """
        result = {
            'text': text[:100] + '...' if len(text) > 100 else text,
            'timestamp': None,
            'svm_prediction': None,
            'url_analysis': [],
            'final_verdict': None,
            'confidence': 0.0,
            'risk_level': 'DESCONOCIDO',
            'recommendations': []
        }
        
        # Predicción SVM
        svm_result = self.predict(text)
        
        if svm_result:
            label, confidence = svm_result
            result['svm_prediction'] = label
            result['confidence'] = confidence
            result['is_phishing_svm'] = (label == "phishing")
        else:
            result['error'] = 'No se pudo realizar predicción SVM'
            return result
        
        # Análisis de URLs si está habilitado
        if check_urls:
            urls = self.url_validator.extract_urls(text)
            
            for url in urls:
                url_analysis = self.url_validator.validate_url(url)
                result['url_analysis'].append(url_analysis)
        
        # NUEVA LÓGICA: Detectar contexto bancario + URL acortada (PHISHING CRÍTICO)
        text_lower = text.lower()
        banking_keywords = [
            'bancolombia', 'davivienda', 'bbva', 'banco', 'nequi', 'daviplata',
            'cuenta', 'tarjeta', 'bloquead', 'suspendid', 'desactivad',
            'actualiz', 'verificar', 'confirmar'
        ]
        
        has_banking_context = any(keyword in text_lower for keyword in banking_keywords)
        has_shortened_url = any('tinyurl' in url or 'bit.ly' in url or 't.co' in url or 'goo.gl' in url 
                               for url in self.url_validator.extract_urls(text))
        
        # Si tiene contexto bancario + URL acortada = PHISHING CRÍTICO
        if has_banking_context and has_shortened_url:
            result['critical_red_flag'] = True
            result['is_phishing_svm'] = True  # Forzar clasificación de phishing
            result['confidence'] = max(result['confidence'], 0.95)  # Aumentar confianza
            result['override_reason'] = '🚨 ALERTA CRÍTICA: Mensaje bancario con URL acortada (técnica común de phishing)'
        
        # Veredicto final combinando SVM y URLs
        result['final_verdict'] = self._compute_final_verdict(result)
        
        return result
    
    def _compute_final_verdict(self, analysis: Dict) -> Dict:
        """
        Computa el veredicto final con 'Lógica de Freno de Mano' para evitar Falsos Positivos.
        
        CONCEPTO: Si el SVM es agresivo pero las URLs son seguras (especialmente dominios educativos/gubernamentales),
        bajamos la alarma de CRÍTICO/ALTO a MEDIO/BAJO para evitar falsos positivos.
        """
        is_phishing_svm = analysis.get('is_phishing_svm', False)
        svm_confidence = analysis.get('confidence', 0.0)
        url_analysis = analysis.get('url_analysis', [])
        critical_red_flag = analysis.get('critical_red_flag', False)
        
        # Evaluar si todas las URLs son seguras (riesgo BAJO)
        urls_are_safe = False
        if url_analysis:
            urls_are_safe = all(u['risk_level'] == 'BAJO' for u in url_analysis)
        
        # Inicializar veredicto
        verdict = {
            'is_scam': False,
            'risk_level': 'BAJO',
            'confidence': svm_confidence,
            'main_reason': '',
            'recommendations': []
        }
        
        # CASO 1: ALERTA CRÍTICA (Bancos + URL Acortada) - Esto sigue siendo prioritario SIN EXCEPCIONES
        if critical_red_flag:
            verdict['is_scam'] = True
            verdict['risk_level'] = 'CRÍTICO'
            verdict['confidence'] = 0.98
            verdict['main_reason'] = (
                '🚨 PHISHING DETECTADO: Los bancos JAMÁS envían enlaces acortados. '
                'Esta es una técnica clásica de estafa para ocultar el destino real del enlace.'
            )
        
        # CASO 2: SVM dice ESTAFA pero URLs parecen SEGURAS (Posible Falso Positivo)
        # ESTA ES LA CORRECCIÓN CLAVE PARA EL OVERFITTING DEL SVM
        elif is_phishing_svm and urls_are_safe:
            # En lugar de confiar ciegamente en el SVM, bajamos la alarma
            verdict['is_scam'] = False
            verdict['risk_level'] = 'MEDIO'  # Bajamos de ALTO/CRÍTICO a MEDIO
            verdict['confidence'] = 0.45  # Bajamos la confianza del SVM artificialmente
            verdict['main_reason'] = (
                'El sistema detectó patrones inusuales en el texto, pero el enlace parece legítimo. '
                'Podría ser un falso positivo, pero verifica con precaución.'
            )
        
        # CASO 3: Predicción SVM pura (solo si no hay contradicción con URLs seguras)
        elif is_phishing_svm and svm_confidence > 0.75:
            verdict['is_scam'] = True
            verdict['risk_level'] = 'ALTO'
            verdict['main_reason'] = 'El análisis de patrones de texto coincide con campañas de estafa conocidas.'
            
        elif is_phishing_svm and svm_confidence > 0.6:
            verdict['risk_level'] = 'MEDIO'
            verdict['main_reason'] = 'El mensaje contiene lenguaje comúnmente usado en spam o estafas.'
        
        # CASO 4: URLs explícitamente maliciosas (tienen prioridad sobre predicción negativa del SVM)
        has_critical_url = any(
            url['risk_level'] == 'CRÍTICO' for url in url_analysis
        )
        has_high_risk_url = any(
            url['risk_level'] in ['ALTO', 'CRÍTICO'] for url in url_analysis
        )
        
        if has_critical_url:
            verdict['is_scam'] = True
            verdict['risk_level'] = 'CRÍTICO'
            verdict['main_reason'] = 'Se detectaron enlaces clasificados como peligrosos o maliciosos.'
        elif has_high_risk_url and is_phishing_svm:
            verdict['is_scam'] = True
            verdict['risk_level'] = 'ALTO'
            verdict['main_reason'] = 'Combinación de contenido sospechoso y URLs de riesgo'
        
        # Generar recomendaciones según riesgo
        if verdict['is_scam']:
            verdict['recommendations'] = [
                '🚫 NO hacer clic en ningún enlace del mensaje',
                '🚫 NO proporcionar información personal o financiera',
                '🗑️ Eliminar el mensaje inmediatamente',
                '📞 Si es de un banco/entidad, contactar directamente por canales oficiales',
                '⚠️ Reportar el número/remitente como spam'
            ]
        elif verdict['risk_level'] == 'MEDIO':
            verdict['recommendations'] = [
                '🔍 Verificar la fuente oficial manualmente',
                '⚠️ No ingresar datos personales si tienes dudas',
                'ℹ️ Confirmar la veracidad por otro canal'
            ]
        else:
            verdict['recommendations'] = [
                '✅ Puedes proceder, pero siempre mantente alerta',
                '🔗 Verifica que la URL en el navegador coincida con la institución'
            ]
        
        return verdict
    
    def get_detailed_report(self, text: str) -> str:
        """
        Genera un reporte detallado en formato texto.
        
        Args:
            text: Mensaje a analizar
            
        Returns:
            Reporte formateado como string
        """
        analysis = self.analyze_message(text)
        
        report = []
        report.append("="*60)
        report.append("🛡️ REPORTE DE ANÁLISIS DE SEGURIDAD")
        report.append("="*60)
        
        # ALERTA CRÍTICA si existe
        if analysis.get('critical_red_flag'):
            report.append("\n" + "🚨"*20)
            report.append("⚠️ ALERTA CRÍTICA DETECTADA ⚠️")
            report.append("🚨"*20)
            report.append(f"\n{analysis.get('override_reason', '')}")
            report.append("\n" + "🚨"*20)
        
        # Predicción SVM
        report.append("\n📊 ANÁLISIS DE CONTENIDO (SVM):")
        if analysis['svm_prediction']:
            emoji = "🚨" if analysis['is_phishing_svm'] else "✅"
            report.append(f"   {emoji} Clasificación: {analysis['svm_prediction'].upper()}")
            report.append(f"   📈 Confianza: {analysis['confidence']*100:.1f}%")
        
        # Análisis de URLs
        if analysis['url_analysis']:
            report.append("\n🔗 ANÁLISIS DE ENLACES:")
            for i, url_data in enumerate(analysis['url_analysis'], 1):
                report.append(f"\n   URL #{i}: {url_data['url']}")
                report.append(f"   📍 Nivel de riesgo: {url_data['risk_level']}")
                report.append(f"   💡 {url_data['recommendation']}")
                if url_data['flags']:
                    report.append("   ⚠️ Señales de alerta:")
                    for flag in url_data['flags']:
                        report.append(f"      • {flag}")
        
        # Veredicto final
        verdict = analysis['final_verdict']
        report.append("\n" + "="*60)
        report.append("🎯 VEREDICTO FINAL:")
        report.append("="*60)
        
        if verdict['is_scam']:
            report.append(f"🚨 MENSAJE IDENTIFICADO COMO ESTAFA/PHISHING")
        else:
            report.append(f"ℹ️ MENSAJE PARECE LEGÍTIMO")
        
        report.append(f"📊 Nivel de Riesgo: {verdict['risk_level']}")
        report.append(f"💬 {verdict['main_reason']}")
        
        report.append("\n📝 RECOMENDACIONES:")
        for rec in verdict['recommendations']:
            report.append(f"   {rec}")
        
        report.append("\n" + "="*60)
        
        return "\n".join(report)


# ============================================================================
# INSTANCIA GLOBAL Y FUNCIONES DE UTILIDAD
# ============================================================================

# Instancia global del clasificador mejorado
svm_classifier = ImprovedSVMClassifier()


def initialize_svm(model_path: Optional[str] = None) -> bool:
    """
    Inicializa el clasificador SVM global mejorado.
    
    Args:
        model_path: Ruta opcional al modelo
        
    Returns:
        True si se inicializó correctamente
    """
    global svm_classifier
    if model_path:
        svm_classifier = ImprovedSVMClassifier(model_path)
    return svm_classifier.load_model()


def get_svm_classifier() -> ImprovedSVMClassifier:
    """
    Obtiene la instancia global del clasificador SVM mejorado.
    
    Returns:
        Instancia del clasificador
    """
    return svm_classifier


def quick_check(text: str) -> Dict:
    """
    Verificación rápida de un mensaje.
    
    Args:
        text: Mensaje a verificar
        
    Returns:
        Resultado simplificado del análisis
    """
    result = svm_classifier.analyze_message(text)
    verdict = result['final_verdict']
    
    return {
        'is_scam': verdict['is_scam'],
        'risk_level': verdict['risk_level'],
        'confidence': result['confidence'],
        'message': verdict['main_reason']
    }