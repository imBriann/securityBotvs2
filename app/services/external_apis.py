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
    text: str = None,               # Ahora es opcional si usas template
    message_type: str = "text",     # "text", "template", o "interactive"
    template_name: str = None,      # Nombre de la plantilla (ej. "tyc")
    template_language: str = "es_CO", 
    template_components: list = None, # Para pasar la imagen o variables
    interactive_type: str = None,   # "button", "list" para mensajes interactivos
    interactive_body: str = None,   # Cuerpo del mensaje interactivo
    interactive_footer: str = None, # Pie del mensaje interactivo
    interactive_buttons: list = None, # Botones [{"type": "reply", "reply": {"id": "x", "title": "text"}}]
    interactive_action: dict = None, # Acción personalizada (list_items, etc.)
    access_token: str = None,
    phone_number_id: str = None
):
    """
    Envía un mensaje (texto, plantilla, o interactivo) a través de WhatsApp Business API.
    """
    global http_client
    
    if access_token is None:
        access_token = APIConfig.ACCESS_TOKEN
    if phone_number_id is None:
        phone_number_id = APIConfig.PHONE_NUMBER_ID

    if not http_client or not access_token or not phone_number_id:
        print("Error: Cliente HTTP o credenciales no configuradas.")
        return

    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Construcción del Payload según el tipo
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": message_type
    }

    if message_type == "text":
        if not text:
            print("Error: Se intentó enviar mensaje de texto sin contenido.")
            return
        payload["text"] = {"body": text}
        
    elif message_type == "template":
        if not template_name:
            print("Error: Se requiere template_name para mensajes de plantilla.")
            return
        payload["template"] = {
            "name": template_name,
            "language": {"code": template_language},
            "components": template_components or []
        }
    
    elif message_type == "interactive":
        if not interactive_type:
            print("Error: Se requiere interactive_type para mensajes interactivos.")
            return
        
        interactive_payload = {
            "type": interactive_type
        }
        
        # Agregar body y footer si existen
        if interactive_body or interactive_footer:
            interactive_payload["body"] = {}
            if interactive_body:
                interactive_payload["body"]["text"] = interactive_body
            if interactive_footer:
                interactive_payload["footer"] = {"text": interactive_footer}
        
        # Agregar botones o acción
        if interactive_type == "button" and interactive_buttons:
            interactive_payload["action"] = {
                "buttons": interactive_buttons
            }
        elif interactive_action:
            interactive_payload["action"] = interactive_action
        
        payload["interactive"] = interactive_payload

    try:
        print(f"📤 Payload para {to} (tipo={message_type}): {str(payload)[:200]}...")
        response = await http_client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        # Log más limpio dependiendo del tipo
        if message_type == "text":
            content_log = text[:30] if text else "Vacío"
        elif message_type == "template":
            content_log = f"Template: {template_name}"
        elif message_type == "interactive":
            content_log = f"Interactive: {interactive_type}"
        else:
            content_log = f"Tipo: {message_type}"
        print(f"✅ Mensaje enviado a {to}: [{content_log}] (Estado: {response.status_code})")
    except Exception as e:
        print(f"❌ Error enviando mensaje a {to}: {type(e).__name__}: {str(e)[:150]}")
        print(f"   Payload que falló: {str(payload)[:300]}")


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
                "- 'ALTO': si dice que sabe, tiene experiencia, entiende bien, etc.\n"
                "- 'BAJO': si dice que no sabe, no entiende, es nuevo en esto, etc.\n"
                "- 'MEDIO': si dice que sabe un poquito, más o menos, algo, regular, etc.\n"
                "- 'BAJO': si la respuesta es muy vaga, evasiva, una pregunta como 'qué?' o 'no entiendo la pregunta', o no se puede clasificar claramente en las anteriores (ej. 'depende', 'a veces', 'gracias'). Ten especial cuidado con respuestas cortas que no sean claramente afirmativas o negativas sobre su conocimiento.\n"
                "No expliques nada más. Solo una de las cuatro opciones."
            ),
            "user": message_text
        },
        "intencion": {
            "system": (
                "Eres un clasificador de intenciones experto para un chatbot de seguridad en WhatsApp.\n"
                "Tu tarea es analizar el mensaje del usuario y determinar su intención principal.\n\n"
                
                "**CONTEXTO:** El usuario ya está registrado y puede interactuar normalmente con el bot.\n\n"
                
                "**REGLAS DE CLASIFICACIÓN:**\n"
                "1. Si hay múltiples intenciones, prioriza la más específica y accionable\n"
                "2. Un saludo + pregunta = prioriza la pregunta\n"
                "3. Mensajes sospechosos reenviados = SIEMPRE 'analizar'\n"
                "4. Preguntas sobre el bot = 'meta_pregunta' (no 'pregunta_seguridad')\n\n"
                
                "**RESPONDE SOLO CON UNA DE ESTAS PALABRAS:**\n\n"
                
                "• **saludo** - Únicamente saludos sociales simples sin otra intención clara\n"
                "  Ejemplos: 'hola', 'buenos días', 'gracias', 'ok', 'entendido', 'perfecto', 'de nada'\n"
                "  NO uses si hay una pregunta o solicitud después del saludo\n\n"
                
                "• **analizar** - Usuario envía contenido sospechoso para que lo analices\n"
                "  Ejemplos: \n"
                "  - 'Revisa este mensaje: [contenido sospechoso]'\n"
                "  - Mensajes reenviados con enlaces\n"
                "  - 'Me llegó esto, ¿es real?' + [mensaje]\n"
                "  - Contenido de promociones dudosas\n"
                "  - Mensajes con urgencia sospechosa ('actúa ya', 'ganaste un premio')\n"
                "  - Cualquier texto que parezca phishing/estafa\n\n"
                
                "• **pregunta_seguridad** - Pregunta educativa sobre ciberseguridad\n"
                "  Ejemplos:\n"
                "  - '¿Qué es el phishing?'\n"
                "  - '¿Cómo protejo mi cuenta de WhatsApp?'\n"
                "  - '¿Es seguro hacer clic en enlaces de correos?'\n"
                "  - '¿Qué hago si me hackean?'\n"
                "  - '¿Cómo creo contraseñas seguras?'\n"
                "  NO uses si la pregunta es sobre el bot mismo\n\n"
                
                "• **meta_pregunta** - Pregunta sobre el bot, sus funciones o cómo usarlo\n"
                "  Ejemplos:\n"
                "  - '¿Qué puedes hacer?'\n"
                "  - '¿Cómo te uso?'\n"
                "  - '¿Puedo enviarte imágenes?'\n"
                "  - '¿Entiendes audios?'\n"
                "  - '¿Para qué sirves?'\n"
                "  - '¿Quién te creó?'\n\n"
                
                "• **solicitar_consejo** - Pide un consejo o tip de seguridad general\n"
                "  Ejemplos:\n"
                "  - 'Dame un consejo de seguridad'\n"
                "  - 'Necesito tips para protegerme'\n"
                "  - '¿Alguna recomendación?'\n"
                "  - 'Quiero aprender a protegerme'\n\n"
                
                "• **reportar_incidente** - Usuario reporta que ya cayó en una estafa\n"
                "  Ejemplos:\n"
                "  - 'Hice clic en un enlace y di mis datos'\n"
                "  - 'Creo que me hackearon'\n"
                "  - 'Ya transferí el dinero'\n"
                "  - 'Abrí un archivo sospechoso'\n"
                "  - 'Di mi contraseña en un sitio falso'\n\n"
                
                "• **consulta_resultado** - Pregunta sobre un análisis previo\n"
                "  Ejemplos:\n"
                "  - '¿Y entonces es seguro?'\n"
                "  - '¿Debería hacer clic?'\n"
                "  - '¿Qué hago con ese mensaje?'\n"
                "  - 'Explícame más sobre lo que encontraste'\n\n"
                
                "• **feedback** - Da feedback o comenta sobre el servicio\n"
                "  Ejemplos:\n"
                "  - 'Muy útil tu análisis'\n"
                "  - 'No me gustó la respuesta'\n"
                "  - 'Excelente servicio'\n"
                "  - '👍', '👎'\n\n"
                
                "• **cancelar** - Quiere cancelar la operación actual\n"
                "  Ejemplos:\n"
                "  - 'Cancelar'\n"
                "  - 'Olvídalo'\n"
                "  - 'Ya no'\n"
                "  - 'Detente'\n"
                "  - 'Empezar de nuevo'\n\n"
                
                "• **spam_test** - Usuario está probando el bot con mensajes sin sentido\n"
                "  Ejemplos:\n"
                "  - 'asdfasdf'\n"
                "  - '123456'\n"
                "  - 'jajajaja' (sin contexto)\n"
                "  - Emojis aleatorios repetidos\n\n"
                
                "• **irrelevante** - Mensaje no relacionado con seguridad ni el bot\n"
                "  Ejemplos:\n"
                "  - 'Qué hora es?'\n"
                "  - 'Me gusta el fútbol'\n"
                "  - 'Dónde queda X lugar?'\n"
                "  - Conversaciones personales\n\n"
                
                "**IMPORTANTE:** Responde SOLO con una palabra en minúsculas, sin explicaciones."
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
        "phishing": {
            "system": (
                "Eres SecurityBot-WA, un analista experto en ciberseguridad. Tu misión es dar un veredicto final sobre si un mensaje es PHISHING o LEGÍTIMO.\n"
                "Recibes el mensaje del usuario Y un reporte técnico (SVM).\n\n"
                "**INSTRUCCIONES PARA EL VEREDICTO HÍBRIDO (Prioritario):**\n\n"
                "1. **Prioridad a la URL:** Si el mensaje contiene una URL de una institución educativa (.edu.co), gobierno (.gov.co) o empresa reconocida, y el texto NO pide dinero ni contraseñas urgentemente, clasifícalo como **LEGÍTIMO**, incluso si el SVM dice 'Estafa'.\n"
                "2. **Falsos Positivos del SVM:** El modelo técnico a veces es agresivo. Si ves que el SVM dice 'Confianza 100%' pero el mensaje es solo un enlace a una universidad (ej. unipamplona.edu.co o javeriana.edu.co), IGNORA AL SVM. Es un falso positivo típico del overfitting.\n"
                "3. **Red Flags de Ingeniería Social:** Si hay urgencia ('su cuenta será bloqueada', 'confirme ahora'), errores ortográficos, o URLs raras (bit.ly, ngrok, dominios extraños), entonces SÍ apóyate en el SVM y marca como **ESTAFA**.\n"
                "4. **ALERTA CRÍTICA:** Si el SVM menciona 'ALERTA CRÍTICA' o 'contexto bancario + URL acortada', es DEFINITIVAMENTE ESTAFA sin excepciones.\n\n"
                "**FORMATO DE RESPUESTA (Estricto):**\n"
                "Parte 1: Resumen de 2 líneas con emoji (✅ para Seguro, ⚠️ para Precaución, 🚨 para Estafa).\n"
                "---DETALLES_SIGUEN---\n"
                "Parte 2: Explicación amigable. Si contradices al SVM, explica claramente: 'Aunque mi sistema automático se alarmó, verifiqué manualmente y el enlace es oficial de la universidad...'\n\n"
                "IMPORTANTE: Siempre sé empático pero claro. Prioriza las URLs legítimas sobre predicciones técnicas agresivas."
            ),
            "user": message_text
        },
        "cyber_pregunta": {
            "system": (
                "Eres SecurityBot-WA, un asistente experto en ciberseguridad amigable y útil para usuarios colombianos.\n"
                "El usuario te hará una pregunta sobre seguridad digital, privacidad, virus, contraseñas o estafas.\n"
                "Responde de forma clara, educativa y práctica. Evita tecnicismos excesivos si no son necesarios. Usa emojis para hacer la lectura más amena.\n"
                "Si la pregunta no tiene nada que ver con seguridad o tecnología, responde amablemente que solo puedes ayudar con temas de seguridad digital."
            ),
            "user": message_text
        },
        "ayuda_post_estafa": {
            "system": (
                "Eres un experto en respuesta a incidentes de seguridad para ciudadanos.\n"
                "El usuario acaba de indicar que CAYÓ en una estafa o interactuó con un enlace malicioso.\n"
                "Tu tarea es darle una lista de pasos de emergencia CLAROS y ACCIONABLES para mitigar el daño.\n"
                "Ejemplos de consejos: Contactar al banco inmediatamente, cambiar contraseñas desde otro dispositivo, activar doble factor de autenticación, reportar el número, desconectar internet si descargó algo, etc.\n"
                "Mantén la calma y sé empático, pero urgente en las acciones."
            ),
            "user": message_text
        }
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