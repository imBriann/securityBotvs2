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

@app.get("/health")
async def health_check():
    """
    Health check endpoint para Google Cloud Run.
    Cloud Run verifica que el servicio esté respondiendo correctamente.
    """
    return {"status": "healthy", "service": "SecurityBot-WA"}

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
        
        # LÓGICA DE LECTURA ROBUSTA
        if message_type == "text":
            text_recibido_original = message_object.get("text", {}).get("body", "").strip()
            
        elif message_type == "button":
            # Caso 1: Botón de respuesta rápida (Quick Reply) de una Plantilla
            # Intentamos leer el texto visible del botón
            text_recibido_original = message_object.get("button", {}).get("text", "").strip()
            # Si el texto falla, leemos el payload (dato oculto)
            if not text_recibido_original:
                text_recibido_original = message_object.get("button", {}).get("payload", "").strip()
                
        elif message_type == "interactive":
            # Caso 2: Botones Interactivos o Listas (Menús)
            interactive_obj = message_object.get("interactive", {})
            interactive_type = interactive_obj.get("type")
            
            if interactive_type == "button_reply":
                text_recibido_original = interactive_obj.get("button_reply", {}).get("title", "").strip()
            elif interactive_type == "list_reply":
                text_recibido_original = interactive_obj.get("list_reply", {}).get("title", "").strip()

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

            # --- AQUÍ ENVIAMOS TU PLANTILLA TYC ---
            await send_whatsapp_message(
                to=telefono_remitente,
                message_type="template",
                template_name="tyc",
                template_language="es_CO",
                template_components=[
                    {
                        "type": "header",
                        "parameters": [
                            {
                                "type": "image",
                                "image": {
                                    "link": "https://i.ibb.co/n8zgC5SG/portada1.jpg" 
                                }
                            }
                        ]
                    }
                ]
            )
            # --------------------------------------
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