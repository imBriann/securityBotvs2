import os
import asyncio
import httpx
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse

from app.services.conversation_flow import handle_user_message
from app.services.external_apis import send_whatsapp_message, set_http_client 
from app.storage.users_state import db_get_user, db_create_user
from app.utils.preprocessing import normalize_text
from app.utils.config import APIConfig

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PROCESSED_MESSAGE_IDS_CACHE_SIZE = 1000
processed_message_ids = deque(maxlen=PROCESSED_MESSAGE_IDS_CACHE_SIZE)
user_locks = defaultdict(asyncio.Lock)

http_client: httpx.AsyncClient = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    print("Iniciando aplicación y cliente HTTP...")
    http_client = httpx.AsyncClient(timeout=45.0)

    set_http_client(http_client)
    
    yield
    print("Cerrando cliente HTTP y finalizando aplicación...")
    if http_client:
        await http_client.aclose()

app = FastAPI(lifespan=lifespan)

@app.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook_subscription(request: Request):
    if request.query_params.get("hub.mode") == "subscribe" and \
       request.query_params.get("hub.verify_token") == VERIFY_TOKEN:
        print("Verificación de Webhook exitosa.")
        return PlainTextResponse(request.query_params.get("hub.challenge", ""), status_code=200)
    print(f"Fallo en verificación de Webhook. Token: {request.query_params.get('hub.verify_token')}")
    raise HTTPException(status_code=403, detail="Verification token mismatch.")

@app.post("/webhook")
async def whatsapp_webhook_handler(request: Request):
    data = await request.json()
    try:
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        message_object = value.get("messages", [{}])[0]

        if not message_object:
            return JSONResponse(content={}, status_code=200)

        telefono_remitente = message_object.get("from")
        message_type = message_object.get("type")
        whatsapp_message_id = message_object.get("id")
        text_recibido_original = ""
        
        if message_type == "text":
            text_recibido_original = message_object.get("text", {}).get("body", "").strip()

        print(f"DEBUG: Webhook IN: Tel: {telefono_remitente}, MsgID: {whatsapp_message_id}, Type: {message_type}, Text: '{text_recibido_original[:50]}...'")

        if not telefono_remitente or not whatsapp_message_id:
            print(f"Webhook ignorado: falta telefono_remitente o whatsapp_message_id.")
            return JSONResponse(content={}, status_code=200)

        if whatsapp_message_id in processed_message_ids:
            print(f"Webhook duplicado ignorado para message_id: {whatsapp_message_id}")
            return JSONResponse(content={}, status_code=200)

        processed_message_ids.append(whatsapp_message_id)

    except (KeyError, IndexError, TypeError) as e:
        print(f"Error al parsear estructura básica del webhook: {e}")
        return JSONResponse(content={}, status_code=200)

    async with user_locks[telefono_remitente]:
        current_user = db_get_user(telefono_remitente)

        if not current_user:
            db_create_user(telefono_remitente)
            current_user = db_get_user(telefono_remitente)
            
            if not current_user:
                print(f"Error CRÍTICO: No se pudo crear/leer usuario {telefono_remitente}.")
                return JSONResponse(content={"status": "error interno"}, status_code=500)

            await send_whatsapp_message(
                to=telefono_remitente,  # Usar nombre de argumentos es más seguro
                text="👋 ¡Hola! Soy SecurityBot-WA, tu asistente virtual para ayudarte a navegar seguro en el mundo digital en Colombia. 😊\n\n"
                     "Para darte la mejor orientación y cumplir con la Ley 1581 de 2012 (protección de datos personales), necesito tu autorización para guardar algunos datos como tu número de teléfono, y más adelante, tu nombre, edad y nivel de conocimiento en ciberseguridad.\n\n"
                     "🔒 Tu información será confidencial y se usará exclusivamente para mejorar tu experiencia. ¡Nunca la compartiré con terceros!\n\n"
                     "📄 Puedes conocer más detalles en nuestros Términos y Política de Privacidad: https://drive.google.com/file/d/1x7fp9FO3vRGaRcpEeJTbVa050B5aordr/view?usp=sharing\n\n"
                     "👉 Si estás de acuerdo, por favor responde con: ACEPTO",
                access_token=APIConfig.ACCESS_TOKEN,
                phone_number_id=APIConfig.PHONE_NUMBER_ID 
            )
            return JSONResponse(content={}, status_code=200)

        # Delegar el manejo del mensaje al módulo conversation_flow
        await handle_user_message(
            telefono_remitente=telefono_remitente,
            message_object=message_object,
            message_type=message_type,
            text_recibido_original=text_recibido_original,
            current_user=current_user
        )

    return JSONResponse(content={}, status_code=200)