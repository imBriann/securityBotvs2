"""
Módulo para procesamiento y normalización de texto.
"""
import re
import unicodedata
from typing import Optional, List


def normalize_text(text: str) -> str:
    """
    Normaliza texto: convierte a minúsculas, elimina espacios extra y acentos.
    
    Args:
        text: Texto a normalizar
        
    Returns:
        Texto normalizado
    """
    if not text:
        return ""
    
    # Convertir a minúsculas y eliminar espacios extra
    text = text.lower().strip()
    
    # Quitar acentos comunes de vocales
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


def clean_whitespace(text: str) -> str:
    """
    Limpia espacios en blanco excesivos de un texto.
    
    Args:
        text: Texto a limpiar
        
    Returns:
        Texto con espacios normalizados
    """
    if not text:
        return ""
    
    # Reemplazar múltiples espacios/tabs/saltos de línea por un solo espacio
    return re.sub(r'\s+', ' ', text).strip()


def extract_first_url(text: str) -> Optional[str]:
    """
    Extrae la primera URL encontrada en un texto.
    
    Args:
        text: Texto donde buscar URLs
        
    Returns:
        Primera URL encontrada o None si no hay ninguna
    """
    if not text:
        return None
    
    # Expresión regular mejorada para URLs
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    match = re.search(url_pattern, text)
    
    return match.group(0) if match else None


def extract_all_urls(text: str) -> List[str]:
    """
    Extrae todas las URLs encontradas en un texto.
    
    Args:
        text: Texto donde buscar URLs
        
    Returns:
        Lista de URLs encontradas
    """
    if not text:
        return []
    
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(url_pattern, text)


def remove_emojis(text: str) -> str:
    """
    Elimina emojis de un texto.
    
    Args:
        text: Texto con posibles emojis
        
    Returns:
        Texto sin emojis
    """
    if not text:
        return ""
    
    # Patrón para detectar emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticones
        "\U0001F300-\U0001F5FF"  # símbolos y pictogramas
        "\U0001F680-\U0001F6FF"  # transporte y símbolos de mapa
        "\U0001F1E0-\U0001F1FF"  # banderas
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    
    return emoji_pattern.sub(r'', text).strip()


def extract_phone_numbers(text: str) -> List[str]:
    """
    Extrae números de teléfono de un texto.
    
    Args:
        text: Texto donde buscar números de teléfono
        
    Returns:
        Lista de números de teléfono encontrados
    """
    if not text:
        return []
    
    # Patrón para números de teléfono (formato internacional y local)
    phone_pattern = r'(?:\+\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
    matches = re.findall(phone_pattern, text)
    
    # Filtrar matches muy cortos que podrían ser falsos positivos
    return [match for match in matches if len(re.sub(r'\D', '', match)) >= 7]


def extract_emails(text: str) -> List[str]:
    """
    Extrae direcciones de correo electrónico de un texto.
    
    Args:
        text: Texto donde buscar emails
        
    Returns:
        Lista de emails encontrados
    """
    if not text:
        return []
    
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(email_pattern, text)


def sanitize_for_display(text: str, max_length: int = 50) -> str:
    """
    Sanitiza un texto para mostrarlo en logs (limita longitud y muestra preview).
    
    Args:
        text: Texto a sanitizar
        max_length: Longitud máxima del preview
        
    Returns:
        Texto sanitizado para display
    """
    if not text:
        return "(vacío)"
    
    # Limpiar espacios
    clean_text = clean_whitespace(text)
    
    if len(clean_text) <= max_length:
        return f"'{clean_text}'"
    
    return f"'{clean_text[:max_length]}...'"


def contains_suspicious_keywords(text: str) -> bool:
    """
    Verifica si un texto contiene palabras clave sospechosas comunes en phishing.
    
    Args:
        text: Texto a analizar
        
    Returns:
        True si contiene keywords sospechosos
    """
    if not text:
        return False
    
    text_normalized = normalize_text(text)
    
    # Palabras clave sospechosas en español
    suspicious_keywords = [
        'urgente', 'inmediatamente', 'verificar cuenta', 'suspendida',
        'datos personales', 'confirmar identidad', 'haz clic aqui',
        'ganaste', 'premio', 'loteria', 'transferencia', 'banco',
        'tarjeta bloqueada', 'actualizar datos', 'codigo de verificacion',
        'felicidades', 'reclama tu premio', 'oferta limitada',
        'actua ahora', 'expira', 'ultimo aviso', 'reembolso',
        'seguridad', 'restablecer contrasena', 'confirma tu cuenta'
    ]
    
    for keyword in suspicious_keywords:
        if keyword in text_normalized:
            return True
    
    return False


def count_suspicious_indicators(text: str) -> dict:
    """
    Cuenta varios indicadores sospechosos en un texto.
    
    Args:
        text: Texto a analizar
        
    Returns:
        Diccionario con conteos de indicadores
    """
    return {
        'urls': len(extract_all_urls(text)),
        'phone_numbers': len(extract_phone_numbers(text)),
        'emails': len(extract_emails(text)),
        'has_suspicious_keywords': contains_suspicious_keywords(text),
        'length': len(text),
        'word_count': len(text.split()) if text else 0
    }


def is_likely_command(text: str, commands: List[str]) -> bool:
    """
    Verifica si un texto es probablemente un comando de la lista.
    
    Args:
        text: Texto a verificar
        commands: Lista de comandos válidos
        
    Returns:
        True si el texto es un comando reconocido
    """
    if not text:
        return False
    
    normalized = normalize_text(text)
    
    # Verificar coincidencia exacta o si algún comando está en el texto
    for command in commands:
        cmd_normalized = normalize_text(command)
        if normalized == cmd_normalized or cmd_normalized in normalized:
            # Asegurar que sea comando corto (no parte de mensaje largo)
            if len(normalized) < 30 or normalized == cmd_normalized:
                return True
    
    return False


def truncate_for_storage(text: str, max_length: int = 5000) -> str:
    """
    Trunca un texto para almacenamiento en base de datos.
    
    Args:
        text: Texto a truncar
        max_length: Longitud máxima
        
    Returns:
        Texto truncado si excede el límite
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length] + "...[truncado]"