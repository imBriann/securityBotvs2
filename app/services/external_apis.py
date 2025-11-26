"""
Módulo para interacciones con APIs externas (WhatsApp y DeepSeek).
"""
import httpx
from typing import Optional, Dict
from app.utils.config import APIConfig

# Cliente HTTP global
http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> Optional[httpx.AsyncClient]:
    """Obtiene el cliente HTTP global."""
    return http_client


def set_http_client(client: httpx.AsyncClient):
    """Establece el cliente HTTP global."""
    global http_client
    http_client = client


async def send_whatsapp_message(
    to: str, 
    text: str,
    access_token: str = None,      # <--- AHORA ES OPCIONAL
    phone_number_id: str = None    # <--- AHORA ES OPCIONAL
):
    """
    Envía un mensaje de texto a través de WhatsApp Business API.
    Si no se proveen tokens, se usan los de APIConfig.
    """
    global http_client
    
    # Cargar defaults si es necesario
    if access_token is None:
        access_token = APIConfig.ACCESS_TOKEN
    if phone_number_id is None:
        phone_number_id = APIConfig.PHONE_NUMBER_ID

    if not http_client:
        print("Error: El cliente HTTP no está inicializado.")
        return
        
    if not access_token or not phone_number_id:
        print("Error: ACCESS_TOKEN o PHONE_NUMBER_ID no configurados.")
        return

    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }

    try:
        response = await http_client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(f"Mensaje enviado a {to}: '{text[:50]}...' (Estado: {response.status_code})")
    except httpx.HTTPStatusError as e:
        print(f"Error al enviar mensaje a WhatsApp ({to}): {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        print(f"Error de red al enviar mensaje a WhatsApp ({to}): {e}")
    except Exception as e:
        print(f"Error inesperado en send_whatsapp_message ({to}): {e}")


async def analyze_with_deepseek(
    message_text: str,
    mode: str,
    user_profile: Optional[Dict] = None,  
    api_key: str = None,                  
    api_url: str = None                   
) -> Optional[str]:
    """
    Analiza texto usando la API de DeepSeek.
    """
    global http_client
    
    # Cargar defaults si es necesario
    if api_key is None:
        api_key = APIConfig.DEEPSEEK_API_KEY
    if api_url is None:
        api_url = APIConfig.DEEPSEEK_API_URL
    
    if not http_client:
        print("Error: El cliente HTTP no está inicializado.")
        return "Lo siento, el servicio de análisis no está disponible en este momento (cliente no listo)."
        
    if not api_key:
        print("Error: DEEPSEEK_API_KEY no configurado.")
        return "Lo siento, el servicio de análisis no está disponible en este momento."
        
    if user_profile is None:
        user_profile = {}

    user_name_for_prompt = user_profile.get('nombre', 'usuario')
    last_url_context = user_profile.get('last_analyzed_url', 'Ninguna')

    prompts_config = {
        "nombre": {
             "system": (
                "Eres un experto en extraer nombres de personas de un texto. El usuario te dará un mensaje donde se espera que esté su nombre.\n"
                "Analiza la entrada y responde SOLO con una de estas opciones:\n"
                "- Si encuentras un nombre de persona claro y plausible, responde con: NOMBRE_VALIDO:{nombre_extraido} (ej. NOMBRE_VALIDO:Carlos, NOMBRE_VALIDO:Maria Eugenia).\n"
                "- Si el texto NO parece ser un nombre de persona (ej. 'gato', '123', 'no quiero decirlo'), responde con: NOMBRE_INVALIDO\n"
                "- Si el texto es ambiguo, muy corto, o no estás seguro si es un nombre real (ej. 'si', 'ok', 'xyz'), responde con: NOMBRE_CONFUSO\n"
                "No expliques nada más. Sé estricto con los nombres, deben parecer reales."
            ),
            "user": message_text
        },
        "edad": {
            "system": (
                "Eres un experto en procesamiento de lenguaje natural para extraer la edad de una persona de un texto. El usuario te dará un mensaje donde se espera que indique su edad.\n"
                "La edad puede venir como número ('35'), con palabras ('sesenta años', 'tengo cuarenta y dos'), o de forma más informal.\n"
                "Analiza la entrada y responde SOLO con una de estas opciones:\n"
                "- Si puedes extraer un número de edad plausible (entre 5 y 120 años), responde con: EDAD_VALIDA:{numero_edad} (ej. EDAD_VALIDA:65, EDAD_VALIDA:30).\n"
                "- Si el texto claramente indica que no es una edad o es basura (ej. 'gato', 'no sé', 'ayer comí pollo'), responde con: EDAD_INVALIDA\n"
                "- Si el texto es ambiguo, no estás seguro de poder extraer un número de edad correcto, o parece una respuesta evasiva (ej. 'unos cuantos', 'joven', 'prefiero no decir'), responde con: EDAD_NO_CLARA\n"
                "No expliques nada más. Intenta ser flexible con la forma en que se expresa la edad, pero asegúrate de que el número sea razonable."
            ),
            "user": message_text
        },
        "conocimiento": {
            "system": (
                "Clasifica el siguiente texto SOLO como una de estas opciones: 'Sí', 'No', 'Poco' o 'CONOCIMIENTO_AMBIGUO'.\n"
                "El usuario está respondiendo a la pregunta '¿qué tanto sabes sobre ciberseguridad y estafas en línea?'.\n"
                "- 'Sí': si dice que sabe, tiene experiencia, entiende bien, etc.\n"
                "- 'No': si dice que no sabe, no entiende, es nuevo en esto, etc.\n"
                "- 'Poco': si dice que sabe un poquito, más o menos, algo, regular, etc.\n"
                "- 'CONOCIMIENTO_AMBIGUO': si la respuesta es muy vaga, evasiva, una pregunta como 'qué?' o 'no entiendo la pregunta', o no se puede clasificar claramente en las anteriores (ej. 'depende', 'a veces', 'gracias'). Ten especial cuidado con respuestas cortas que no sean claramente afirmativas o negativas sobre su conocimiento.\n"
                "No expliques nada más. Solo una de las cuatro opciones."
            ),
            "user": message_text
        },
        "intencion": {
            "system": (
                "Eres un asistente inteligente para WhatsApp. Tu tarea es analizar el siguiente mensaje de un usuario y determinar su intención principal. "
                "El usuario ya está registrado.\n"
                "Si el mensaje contiene un saludo (como 'gracias', 'hola') Y TAMBIÉN una pregunta o comando claro, prioriza la pregunta o comando como la intención principal.\n"
                "Responde SOLO con una de estas opciones (una sola palabra, en minúsculas y sin explicaciones adicionales):\n"
                "- saludo: si el mensaje ES PRINCIPALMENTE un saludo o una interacción social simple (ej: solo 'hola', solo 'gracias', 'ok', 'de nada').\n"
                "- analizar: si el usuario quiere que analices un mensaje de texto, el contenido de una imagen, o cualquier cosa que le parezca sospechosa de ser una estafa, phishing, fraude, o que contenga información engañosa.\n"
                "- pregunta_seguridad: si el usuario está haciendo una pregunta específica sobre ciberseguridad, cómo protegerse, qué es un tipo de estafa, etc. (que no sea simplemente reenviar un mensaje para analizar y no sea una pregunta sobre cómo usar el bot).\n"
                "- meta_pregunta: si el usuario está haciendo una pregunta sobre el bot mismo, sus capacidades, o cómo interactuar con él.\n"
                "- solicitar_tip_seguridad: si el usuario pide un consejo, tip o recomendación general de seguridad.\n"
                "- comando_reset: si el usuario quiere cancelar la operación actual y volver al inicio.\n"
                "- irrelevante: si el mensaje no tiene relación con los temas anteriores.\n\n"
                "Prioriza 'analizar' si el texto del mensaje parece ser el contenido de un mensaje sospechoso. "
                "Si hay un saludo y una pregunta de seguridad, la intención es 'pregunta_seguridad'."
            ),
            "user": message_text
        },
        "decision_ver_detalles": {
            "system": (
                "Eres un clasificador de intenciones para un chatbot de WhatsApp. El bot acaba de dar un resumen de un análisis de seguridad (phishing/estafa) y preguntó al usuario si quiere ver los detalles completos.\n"
                "El usuario ha respondido. Tu tarea es determinar si la respuesta del usuario significa que SÍ quiere ver los detalles, o si está diciendo OTRA COSA (una nueva pregunta, un comentario no relacionado, etc.).\n"
                "Considera que el usuario podría ser una persona mayor, así que sé flexible con respuestas afirmativas.\n\n"
                "Responde SOLO con una de estas dos opciones:\n"
                "- QUIERE_DETALLES: Si el usuario expresa afirmativamente que quiere ver los detalles. Ejemplos: \"Sí\", \"Claro\", \"Bueno\", \"Ok\", \"Mándamelos\", \"Más información por favor\", \"Sí quiero los detalles\", \"Dale\", \"Más\", \"Bueno sí\", \"A ver\", \"Quiero saber más\", \"Explícame\", \"Sí, por favor\", \"si\", \"mas informacion\".\n"
                "- OTRA_COSA: Si la respuesta del usuario NO es una clara afirmación para ver los detalles. Ejemplos: \"¿Y eso es peligroso?\", \"No gracias\", \"Qué es phishing?\", \"Entendido\", \"Ok gracias\", \"Y si ya abrí el enlace?\", o cualquier otra pregunta o comentario.\n\n"
                "No expliques nada más. Solo QUIERE_DETALLES u OTRA_COSA."
            ),
            "user": message_text
        },
        "decision_post_phishing_interaction": {
            "system": (
                f"Eres un clasificador de intenciones para un chatbot de WhatsApp llamado SecurityBot-WA. El bot acaba de determinar que un mensaje era una estafa y le preguntó al usuario ({user_name_for_prompt}) si interactuó con ella (SI/NO) o si necesita AYUDA.\n"
                "El usuario ha respondido. Tu tarea es clasificar esta respuesta.\n\n"
                "Responde SOLO con una de estas opciones:\n"
                "- RESPUESTA_SI: Si el usuario indica afirmativamente que SÍ interactuó con la estafa (ej: \"Sí\", \"Sí hice clic\", \"Creo que sí\", \"si\", \"claro\").\n"
                "- RESPUESTA_NO: Si el usuario indica que NO interactuó con la estafa (ej: \"No\", \"No, para nada\", \"No hice nada\", \"nop\").\n"
                "- PIDE_AYUDA: Si el usuario explícitamente pide ayuda o usa la palabra \"AYUDA\" (o variaciones como \"ayudame\").\n"
                "- ES_PREGUNTA: Si el usuario hace una pregunta en lugar de responder directamente SI/NO/AYUDA (ej: \"¿Qué es phishing?\", \"¿Cómo puedo evitar esto?\", \"¿Y si ya di mis datos?\").\n"
                "- ES_COMENTARIO: Si el usuario hace un comentario, agradece, o da una respuesta corta que no es SI/NO/AYUDA ni una pregunta clara (ej: \"Gracias\", \"Ok\", \"Entendido\", \"Qué peligroso\", \"Es una estafa\").\n"
                "- OTRA_COSA: Si la respuesta es muy ambigua, no relacionada, o no encaja en las categorías anteriores.\n\n"
                "No expliques nada más. Solo una de las opciones listadas."
            ),
            "user": message_text
        },
        # Agregar el resto de los prompts del código original
        # (phishing, ayuda_post_estafa, cyber_pregunta)
    }
    
    if mode not in prompts_config:
        print(f"Modo de análisis no reconocido: {mode}")
        return "Error interno: modo de análisis no válido."

    current_prompt = prompts_config[mode]
    payload = {
        "model": APIConfig.DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": current_prompt["system"]},
            {"role": "user", "content": current_prompt["user"]}
        ],
        "temperature": APIConfig.DEEPSEEK_TEMPERATURE,
        "max_tokens": APIConfig.DEEPSEEK_MAX_TOKENS,
        "web_search": True
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        response = await http_client.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        api_response = response.json()
        
        if api_response.get("choices") and api_response["choices"][0].get("message"):
            return api_response["choices"][0]["message"]["content"].strip()
            
        print(f"Respuesta inesperada de DeepSeek API: {api_response}")
        return "No se pudo obtener una respuesta del servicio de análisis."
        
    except httpx.HTTPStatusError as e:
        print(f"Error de API DeepSeek ({mode}): {e.response.status_code} - {e.response.text}")
        return "Hubo un problema al contactar el servicio de análisis."
    except httpx.RequestError as e:
        print(f"Error de red con DeepSeek API ({mode}): {e}")
        return "Problema de conexión con el servicio de análisis."
    except Exception as e:
        print(f"Error inesperado en analyze_with_deepseek ({mode}): {e}")
        return "Lo siento, ocurrió un error inesperado."


async def download_image_from_whatsapp(
    media_id: str,
    access_token: str = None # <--- AHORA ES OPCIONAL
) -> Optional[bytes]:
    """
    Descarga una imagen desde WhatsApp Business API.
    """
    global http_client
    
    if access_token is None:
        access_token = APIConfig.ACCESS_TOKEN

    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        media_info_url = f"https://graph.facebook.com/v18.0/{media_id}"
        media_info_response = await http_client.get(media_info_url, headers=headers)
        media_info_response.raise_for_status()
        image_download_url = media_info_response.json()["url"]
        
        image_response = await http_client.get(image_download_url, headers=headers)
        image_response.raise_for_status()
        return image_response.content
        
    except httpx.HTTPStatusError as e:
        print(f"Error HTTP al descargar imagen (media_id: {media_id}): {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        print(f"Error de red al descargar imagen (media_id: {media_id}): {e}")
    except Exception as e:
        print(f"Error inesperado en download_image_from_whatsapp (media_id: {media_id}): {e}")
    
    return None