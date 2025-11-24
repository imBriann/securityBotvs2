"""
Módulo de configuración centralizada.
Maneja todas las variables de entorno, constantes y configuraciones del sistema.
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


class APIConfig:
    """Configuración de APIs externas."""
    
    # WhatsApp Business API
    VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
    ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
    PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
    
    # DeepSeek API
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    DEEPSEEK_MODEL = "deepseek-chat"
    DEEPSEEK_TEMPERATURE = 0.4
    DEEPSEEK_MAX_TOKENS = 1600
    
    @classmethod
    def validate(cls) -> bool:
        """
        Valida que todas las variables de entorno críticas estén configuradas.
        
        Returns:
            True si todas las variables están configuradas, False en caso contrario
        """
        required_vars = [
            cls.VERIFY_TOKEN,
            cls.ACCESS_TOKEN,
            cls.PHONE_NUMBER_ID,
            cls.DEEPSEEK_API_KEY
        ]
        
        if not all(required_vars):
            print("ERROR CRÍTICO: Una o más variables de entorno no están configuradas.")
            return False
        return True


class TesseractConfig:
    """Configuración de Tesseract OCR."""
    
    @staticmethod
    def get_path() -> str:
        """
        Obtiene la ruta del ejecutable de Tesseract según el sistema operativo.
        
        Returns:
            Ruta al ejecutable de Tesseract
        """
        if os.name == "nt":  # Windows
            return os.getenv("TESSERACT_CMD_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        else:  # Linux/Unix
            return "/usr/bin/tesseract"
    
    @staticmethod
    def validate_installation() -> bool:
        """
        Valida que Tesseract esté instalado en la ruta configurada.
        
        Returns:
            True si existe, False en caso contrario
        """
        path = TesseractConfig.get_path()
        if os.path.exists(path):
            return True
        else:
            print(f"ADVERTENCIA: Tesseract OCR no encontrado en {path}.")
            return False


class OCRConfig:
    """Configuración específica para OCR."""
    
    # Configuración de Tesseract
    TESSERACT_CONFIG = "--oem 3 --psm 6 -l spa+eng"
    
    # Umbral de redimensionamiento de imagen
    MIN_IMAGE_WIDTH = 800
    RESIZE_FACTOR = 1.5
    
    # Directorio de imágenes
    IMAGES_DIR = "imagenes_recibidas"
    
    @classmethod
    def ensure_images_dir(cls):
        """Crea el directorio de imágenes si no existe."""
        if not os.path.exists(cls.IMAGES_DIR):
            os.makedirs(cls.IMAGES_DIR)
            print(f"Directorio de imágenes creado: {cls.IMAGES_DIR}")


class MessageConfig:
    """Configuración de mensajería."""
    
    # Caché de mensajes procesados
    PROCESSED_MESSAGE_IDS_CACHE_SIZE = 1000
    
    # Timeouts
    HTTP_CLIENT_TIMEOUT = 45.0
    
    # URLs de WhatsApp
    WHATSAPP_API_VERSION = "v18.0"
    
    @classmethod
    def get_messages_url(cls, phone_number_id: str) -> str:
        """Construye la URL de mensajes de WhatsApp."""
        return f"https://graph.facebook.com/{cls.WHATSAPP_API_VERSION}/{phone_number_id}/messages"
    
    @classmethod
    def get_media_info_url(cls, media_id: str) -> str:
        """Construye la URL de información de media."""
        return f"https://graph.facebook.com/{cls.WHATSAPP_API_VERSION}/{media_id}"


class SecurityTips:
    """Consejos de seguridad para usuarios."""
    
    TIPS = [
        "🛡️ Usa contraseñas únicas y fuertes para cada una de tus cuentas importantes. ¡Un gestor de contraseñas puede ayudarte mucho!",
        "🔒 Activa la verificación en dos pasos (2FA) siempre que esté disponible, especialmente en tu correo, redes sociales y bancos.",
        "❓ Desconfía de mensajes inesperados que te pidan información personal o te urjan a hacer clic en enlaces, ¡incluso si parecen de contactos conocidos!",
        "🔗 Antes de hacer clic en un enlace, especialmente en correos o mensajes, verifica que la dirección web (URL) sea legítima y no una imitación.",
        "🔄 Mantén tu sistema operativo, navegador y antivirus siempre actualizados para protegerte de las últimas amenazas.",
        "🚫 No descargues archivos de fuentes desconocidas o correos sospechosos, podrían contener malware.",
        "👀 Revisa periódicamente los permisos de las aplicaciones en tu teléfono y redes sociales. ¡Quita los que no necesites!",
        "💸 Sé muy cuidadoso con ofertas que parecen demasiado buenas para ser verdad, ¡usualmente lo son y pueden ser una estafa!",
        "📞 Si recibes una llamada o mensaje sospechoso de tu banco o una entidad, cuelga y contáctalos directamente a través de sus canales oficiales.",
        "📶 Evita conectarte a redes Wi-Fi públicas no seguras para realizar transacciones bancarias o ingresar información sensible."
    ]


class OnboardingMessages:
    """Mensajes del proceso de onboarding."""
    
    WELCOME_MESSAGE = (
        "👋 ¡Hola! Soy SecurityBot-WA, tu asistente virtual para ayudarte a navegar seguro en el mundo digital en Colombia. 😊\n\n"
        "Para darte la mejor orientación y cumplir con la Ley 1581 de 2012 (protección de datos personales), "
        "necesito tu autorización para guardar algunos datos como tu número de teléfono, y más adelante, "
        "tu nombre, edad y nivel de conocimiento en ciberseguridad.\n\n"
        "🔐 Tu información será confidencial y se usará exclusivamente para mejorar tu experiencia. "
        "¡Nunca la compartiré con terceros!\n\n"
        "📄 Puedes conocer más detalles en nuestros Términos y Política de Privacidad: "
        "https://drive.google.com/file/d/1x7fp9FO3vRGaRcpEeJTbVa050B5aordr/view?usp=sharing\n\n"
        "👉 Si estás de acuerdo, por favor responde con: ACEPTO"
    )
    
    TERMS_ACCEPTED = (
        "¡Excelente! 😊 Gracias por aceptar. Para que mis consejos sean aún mejores para ti, "
        "¿podrías decirme tu nombre, por favor?"
    )
    
    REGISTRATION_COMPLETE_TEMPLATE = (
        "¡Genial, {nombre}! ✅ ¡Hemos completado tu registro! Muchas gracias por tu tiempo y confianza. 🙏\n\n"
        "🛡️ A partir de ahora, estoy a tu disposición. Puedes enviarme cualquier mensaje de texto o imagen "
        "que te parezca sospechosa, y la analizaré contigo. También puedes hacerme preguntas sobre seguridad "
        "digital y cómo protegerte de fraudes en línea.\n\n"
        "¡Estoy aquí para ayudarte a navegar el mundo digital de forma más segura! 😊"
    )


class ResetCommands:
    """Comandos de reinicio/cancelación."""
    
    COMMANDS = [
        "empezar de nuevo",
        "reset",
        "cancelar",
        "olvidalo",
        "ya no",
        "detente"
    ]
    
    MAX_LENGTH = 30  # Longitud máxima para considerar un comando válido


# Validar configuración crítica al importar
if not APIConfig.validate():
    print("⚠️ Algunas variables de entorno críticas no están configuradas.")
    print("   El bot podría no funcionar correctamente.")

# Validar Tesseract
if not TesseractConfig.validate_installation():
    print("⚠️ Tesseract OCR no está disponible.")
    print("   El procesamiento de imágenes no funcionará.")

# Asegurar directorio de imágenes
OCRConfig.ensure_images_dir()