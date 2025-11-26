import asyncio
import os
import re
import sqlite3
from app.services.external_apis import send_whatsapp_message, analyze_with_deepseek
# from app.services.svm_classifier import extract_first_url
from app.storage.users_state import db_update_user, db_get_user
from app.utils.preprocessing import normalize_text, extract_first_url
from app.utils.config import (
    ESTADO_PENDIENTE_TERMINOS, ESTADO_PENDIENTE_NOMBRE, ESTADO_PENDIENTE_EDAD,
    ESTADO_PENDIENTE_CONOCIMIENTO, ESTADO_REGISTRADO, ESTADO_ESPERANDO_RESPUESTA_PHISHING,
    ESTADO_ESPERANDO_MAS_DETALLES, SECURITY_TIPS
)
import random
import uuid
import datetime
import numpy as np
import cv2
import pytesseract
from PIL import Image

IMAGES_DIR = "imagenes_recibidas"
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

async def handle_user_message(telefono_remitente: str, message_object: dict, message_type: str, 
                               text_recibido_original: str, current_user: sqlite3.Row):
    """Punto de entrada principal para manejar mensajes del usuario"""
    
    user_state = current_user["estado"]
    user_name = current_user["nombre"] if current_user and current_user["nombre"] else "tú"
    
    print(f"DEBUG: Handler para {telefono_remitente}, Estado: {user_state}")
    
    # Detectar comandos de reset
    normalized_text = normalize_text(text_recibido_original)
    reset_commands = ["empezar de nuevo", "reset", "cancelar", "olvidalo", "ya no", "detente"]
    is_reset_command = any(cmd in normalized_text for cmd in reset_commands) and len(normalized_text) < 30
    
    if is_reset_command:
        await handle_reset_command(telefono_remitente, user_name)
        return
    
    # Manejo de feedback
    if message_type == "text" and text_recibido_original in ["👍", "👎"]:
        if user_state == ESTADO_REGISTRADO:
            print(f"FEEDBACK recibido de {telefono_remitente}: {text_recibido_original}")
            await send_whatsapp_message(telefono_remitente, "¡Gracias por tu feedback! 😊")
            return
    
    # Enrutamiento según estado del usuario
    if user_state == ESTADO_ESPERANDO_MAS_DETALLES:
        await handle_estado_esperando_detalles(telefono_remitente, text_recibido_original, current_user, message_type)
    
    elif user_state == ESTADO_ESPERANDO_RESPUESTA_PHISHING:
        await handle_post_phishing_response(telefono_remitente, text_recibido_original, current_user, message_type)
    
    elif user_state < ESTADO_REGISTRADO:
        await handle_onboarding_process(telefono_remitente, text_recibido_original, current_user, message_type)
    
    elif user_state == ESTADO_REGISTRADO:
        await handle_registered_user_message(telefono_remitente, message_object, message_type, 
                                             text_recibido_original, current_user)
    
    else:
        print(f"Error: Usuario {telefono_remitente} en estado desconocido: {user_state}")
        await send_whatsapp_message(telefono_remitente, 
            f"¡Hola {user_name}! Parece que hubo un pequeño error con mi memoria. ¿Podrías intentar enviarme tu mensaje de nuevo? Gracias. 😊")
        db_update_user(telefono_remitente, {"estado": ESTADO_REGISTRADO})

async def handle_reset_command(telefono: str, user_name: str):
    """Maneja comandos de reset/cancelar"""
    await send_whatsapp_message(telefono, f"De acuerdo, {user_name}. Hemos cancelado la operación actual y volvemos al inicio. ¿En qué te puedo ayudar? 😊")
    db_update_user(telefono, {
        "estado": ESTADO_REGISTRADO,
        "last_analysis_details": None,
        "last_image_ocr_text": None,
        "last_image_analysis_raw": None,
        "last_image_id_processed": None,
        "last_image_timestamp": None,
        "last_analyzed_url": None
    })

async def handle_onboarding_process(telefono: str, text_received: str, user_data: sqlite3.Row, message_type: str):
    """Maneja el proceso de registro del usuario"""
    if message_type != "text":
        user_name = user_data["nombre"] if user_data and user_data["nombre"] else "tú"
        await send_whatsapp_message(telefono, 
            f"¡Hola, {user_name}! 😊 Para que podamos configurar tu perfil, necesito que me respondas con mensajes de texto. ¡Gracias!")
        return
    
    estado_actual = user_data["estado"]
    user_name = user_data["nombre"] if user_data and user_data["nombre"] else "amigo/a"

    if estado_actual == ESTADO_PENDIENTE_TERMINOS:
        await handle_terminos_aceptacion(telefono, text_received)
    
    elif estado_actual == ESTADO_PENDIENTE_NOMBRE:
        await handle_nombre_input(telefono, text_received)
    
    elif estado_actual == ESTADO_PENDIENTE_EDAD:
        await handle_edad_input(telefono, text_received, user_name)
    
    elif estado_actual == ESTADO_PENDIENTE_CONOCIMIENTO:
        await handle_conocimiento_input(telefono, text_received, user_name)

async def handle_terminos_aceptacion(telefono: str, text_received: str):
    """Maneja la aceptación de términos"""
    normalized_text = normalize_text(text_received)
    
    is_explicit_acceptance = "acepto" in normalized_text or \
                             (normalized_text == "si") or \
                             ("si acepto" in normalized_text)
    
    is_explicit_rejection = "no acepto" in normalized_text or \
                            "no quiero" in normalized_text or \
                            "no estoy de acuerdo" in normalized_text or \
                            normalized_text == "no"

    if is_explicit_acceptance and not ("no" in normalized_text and "acepto" not in normalized_text):
        db_update_user(telefono, {"acepto_terminos": 1, "estado": ESTADO_PENDIENTE_NOMBRE})
        await send_whatsapp_message(telefono, 
            "¡Excelente! 😊 Gracias por aceptar. Para que mis consejos sean aún mejores para ti, ¿podrías decirme tu nombre, por favor?")
    elif is_explicit_rejection:
        await send_whatsapp_message(telefono, 
            "Entendido. Si cambias de opinión y deseas aceptar los términos para usar mis servicios, solo escribe *ACEPTO*. ¡Estaré aquí para ayudarte! 👍")
    else:
        await send_whatsapp_message(telefono, 
            "⚠️ Para que podamos continuar, necesito que aceptes los términos. Solo escribe *ACEPTO* si estás de acuerdo. Si no deseas continuar, puedes responder *NO ACEPTO*. ¡Gracias! 💙")

async def handle_nombre_input(telefono: str, text_received: str):
    """Maneja la entrada del nombre"""
    ia_result = await analyze_with_deepseek(text_received, "nombre")
    
    if ia_result and ia_result.startswith("NOMBRE_VALIDO:"):
        nombre_extraido = ia_result.split(":", 1)[1].strip().title()
        db_update_user(telefono, {"nombre": nombre_extraido, "estado": ESTADO_PENDIENTE_EDAD})
        await send_whatsapp_message(telefono, 
            f"¡Un placer conocerte, {nombre_extraido}! 👋 Ahora, si no es molestia, ¿me dirías cuántos años tienes? (Solo el número, por ejemplo: 35). Esto me ayuda a darte consejos más adecuados.")
    elif ia_result == "NOMBRE_INVALIDO":
        await send_whatsapp_message(telefono, 
            "🤔 Mmm, eso no me parece un nombre de persona. ¿Podrías intentarlo de nuevo, por favor? Solo necesito tu primer nombre o cómo te gustaría que te llame. ¡Gracias!")
    else:
        await send_whatsapp_message(telefono, 
            "🤔 No estoy seguro de haber entendido tu nombre. ¿Podrías escribirlo de nuevo, un poquito más claro, por favor? ¡Gracias!")

async def handle_edad_input(telefono: str, text_received: str, user_name: str):
    """Maneja la entrada de edad"""
    ia_result = await analyze_with_deepseek(text_received, "edad")
    
    if ia_result and ia_result.startswith("EDAD_VALIDA:"):
        try:
            edad_num = int(ia_result.split(":", 1)[1])
            if 5 <= edad_num <= 120:
                db_update_user(telefono, {"edad": edad_num, "estado": ESTADO_PENDIENTE_CONOCIMIENTO})
                await send_whatsapp_message(telefono, 
                    f"¡Perfecto, {user_name}! 👍 Ya casi terminamos. Cuéntame, ¿qué tanto sabes sobre ciberseguridad y estafas en línea? Puedes responder: *Sí* (si sabes bastante), *Poco*, o *No* (si no sabes mucho). ¡Tu honestidad me ayuda a ayudarte mejor! 😊")
            else:
                await send_whatsapp_message(telefono, 
                    f"⚠️ Entendí el número {edad_num}, pero parece una edad un poco inusual, {user_name}. ¿Podrías confirmarla o escribirla de nuevo? ¡Gracias!")
        except ValueError:
            await send_whatsapp_message(telefono, 
                f"⚠️ ¡Uy! Hubo un pequeño error al procesar la edad, {user_name}. ¿Podrías escribirla solo con números, como '60' o '35'? ¡Mil gracias!")
    elif ia_result == "EDAD_INVALIDA":
        await send_whatsapp_message(telefono, 
            f"🤔 {user_name}, eso no me parece una edad. ¿Podrías decirme cuántos años tienes usando números, por ejemplo '55'? ¡Gracias!")
    else:
        await send_whatsapp_message(telefono, 
            f"🤔 No estoy seguro de haber entendido tu edad, {user_name}. ¿Podrías escribirla solo con números, por ejemplo '70'? ¡Gracias por tu paciencia!")

async def handle_conocimiento_input(telefono: str, text_received: str, user_name: str):
    """Maneja la entrada de nivel de conocimiento"""
    ia_result = await analyze_with_deepseek(text_received, "conocimiento")

    if ia_result in ["Sí", "No", "Poco"]:
        db_update_user(telefono, {"conocimiento": ia_result, "estado": ESTADO_REGISTRADO})
        await send_whatsapp_message(telefono, 
            f"¡Genial, {user_name}! ✅ ¡Hemos completado tu registro! Muchas gracias por tu tiempo y confianza. 🙏\n\n"
            f"🛡️ A partir de ahora, estoy a tu disposición. Puedes enviarme cualquier mensaje de texto o imagen que te parezca sospechosa, "
            f"y la analizaré contigo. También puedes hacerme preguntas sobre seguridad digital y cómo protegerte de fraudes en línea.\n\n"
            f"¡Estoy aquí para ayudarte a navegar el mundo digital de forma más segura! 😊")
    else:
        await send_whatsapp_message(telefono, 
            f"⚠️ Ups, {user_name}. No entendí bien tu respuesta sobre tu conocimiento. ¿Podrías decirme si sabes *Sí*, *Poco*, o *No* sobre ciberseguridad? ¡Una de esas tres opciones me ayuda mucho! 👍")

async def handle_registered_user_message(telefono: str, message_object: dict, message_type: str, 
                                        text_recibido: str, user_data: sqlite3.Row):
    """Maneja mensajes de usuarios ya registrados"""
    user_name = user_data["nombre"] if user_data and user_data["nombre"] else "tú"
    
    if message_type == "text":
        if not text_recibido:
            await send_whatsapp_message(telefono, 
                f"Hola {user_name}, ¿necesitas ayuda con algo? Puedes enviarme un mensaje que te parezca sospechoso o hacerme una pregunta sobre seguridad. ¡Estoy aquí para ti! 💙")
            return
        
        await handle_text_message(telefono, text_recibido, user_data)
    
    elif message_type == "image":
        await handle_image_message(telefono, message_object, user_data)
    
    elif message_type == "audio":
        await send_whatsapp_message(telefono, 
            f"¡Hola, {user_name}! Recibí tu mensaje de audio. 🎤 Aún estoy aprendiendo a procesarlos, ¡pero espero poder ayudarte con ellos muy pronto! 😊")
    
    else:
        await send_whatsapp_message(telefono, 
            f"Recibí un tipo de mensaje ({message_type}) que aún no sé cómo procesar del todo, {user_name}. Por ahora, mi especialidad son los mensajes de texto e imágenes. 📄🖼️")

async def handle_text_message(telefono: str, text: str, user_data: sqlite3.Row):
    """Maneja mensajes de texto para usuarios registrados"""
    cleaned_text = re.sub(r'\s+', ' ', text).strip()
    nombre_usuario = user_data["nombre"] if user_data and user_data["nombre"] else "tú"
    user_profile_dict = dict(user_data)
    
    intencion = await analyze_with_deepseek(cleaned_text, "intencion", user_profile_dict)
    print(f"DEBUG: Intención clasificada para {telefono} ({nombre_usuario}): {intencion} para texto: '{cleaned_text[:50]}...'")

    if intencion == "saludo":
        await handle_saludo(telefono, nombre_usuario, user_data)
    
    elif intencion == "analizar":
        await handle_analizar_mensaje(telefono, cleaned_text, user_data)
    
    elif intencion == "pregunta_seguridad":
        await handle_pregunta_seguridad(telefono, cleaned_text, user_profile_dict, nombre_usuario)
    
    elif intencion == "meta_pregunta":
        await handle_meta_pregunta(telefono, cleaned_text, nombre_usuario)
    
    elif intencion == "solicitar_tip_seguridad":
        await handle_solicitar_tip(telefono, nombre_usuario)
    
    else:
        await handle_intencion_no_clara(telefono, nombre_usuario, intencion, cleaned_text)

async def handle_saludo(telefono: str, nombre_usuario: str, user_data: sqlite3.Row):
    """Maneja saludos del usuario"""
    # CORRECCIÓN: Convertimos el objeto Row a diccionario real para usar .get()
    user_dict = dict(user_data)
    
    greeting = f"¡Hola de nuevo, {nombre_usuario}! 👋"
    last_interaction_info = ""
    
    # Ahora usamos user_dict en lugar de user_data para usar .get()
    if user_dict.get("last_image_timestamp"):
        last_interaction_info = " La última vez que interactuamos fue sobre un análisis reciente."
    elif user_dict.get("last_analyzed_url"):
        last_interaction_info = " Recientemente analizamos un enlace."
    
    greeting += last_interaction_info + " ¿En qué te puedo ayudar hoy? 😊"
    await send_whatsapp_message(telefono, greeting)

async def handle_analizar_mensaje(telefono: str, mensaje: str, user_data: sqlite3.Row, image_context: dict = None):
    """Maneja la solicitud de análisis de mensaje"""
    nombre_usuario = user_data["nombre"] if user_data and user_data["nombre"] else "tú"
    
    await send_whatsapp_message(telefono, 
        f"🔍 ¡Entendido, {nombre_usuario}! Estoy revisando el mensaje que me enviaste. Te aviso en un momento con mi análisis... 👍")
    
    extracted_url = extract_first_url(mensaje)
    if not extracted_url and image_context and image_context.get("ocr_text_original"):
        extracted_url = extract_first_url(image_context.get("ocr_text_original"))

    user_profile_dict = dict(user_data)
    analisis_completo = await analyze_with_deepseek(mensaje, "phishing", user_profile_dict)

    if analisis_completo:
        partes = analisis_completo.split("---DETALLES_SIGUEN---", 1)
        resumen_breve = partes[0].strip()
        detalles_completos = partes[1].strip() if len(partes) > 1 else ""

        await send_whatsapp_message(telefono, resumen_breve)
        await send_whatsapp_message(telefono, f"{nombre_usuario}, ¿quieres que te dé más detalles y mis recomendaciones sobre esto? 😊")

        db_updates = {
            "estado": ESTADO_ESPERANDO_MAS_DETALLES,
            "last_analysis_details": detalles_completos,
            "last_analyzed_url": extracted_url
        }
        
        if image_context and image_context.get("is_from_image_processing"):
            db_updates.update({
                "last_image_ocr_text": image_context.get("ocr_text_original"),
                "last_image_analysis_raw": analisis_completo,
                "last_image_id_processed": image_context.get("image_db_id"),
                "last_image_timestamp": datetime.datetime.now().isoformat()
            })
        
        db_update_user(telefono, db_updates)
    else:
        await send_whatsapp_message(telefono, 
            f"Lo siento mucho, {nombre_usuario}, tuve un problema al intentar analizar tu mensaje. ¿Podrías intentarlo de nuevo un poco más tarde, por favor? 🙏")

async def handle_pregunta_seguridad(telefono: str, pregunta: str, user_profile: dict, nombre_usuario: str):
    """Maneja preguntas sobre seguridad"""
    await send_whatsapp_message(telefono, 
        f"🤔 ¡Buena pregunta sobre seguridad, {nombre_usuario}! Déjame consultar mis datos para darte la mejor respuesta. Un momento, por favor... 💡")
    
    respuesta = await analyze_with_deepseek(pregunta, "cyber_pregunta", user_profile)
    
    if respuesta:
        await send_whatsapp_message(telefono, respuesta)
        await send_whatsapp_message(telefono, f"Espero que esta información te sea útil, {nombre_usuario}. 👍")
    else:
        await send_whatsapp_message(telefono, 
            f"Mis disculpas, {nombre_usuario}. Parece que tuve un inconveniente al procesar tu pregunta de seguridad. ¿Podrías intentar reformularla? Gracias por tu paciencia. 😊")

async def handle_meta_pregunta(telefono: str, pregunta: str, nombre_usuario: str):
    """Maneja preguntas sobre el bot"""
    normalized_pregunta = normalize_text(pregunta)
    
    if "imagen" in normalized_pregunta and ("puedo" in normalized_pregunta or "enviar" in normalized_pregunta):
        await send_whatsapp_message(telefono, 
            f"¡Claro que sí, {nombre_usuario}! Puedes enviarme imágenes que te parezcan sospechosas y las analizaré para ti. 🖼️👍")
    elif "que haces" in normalized_pregunta or "para que sirves" in normalized_pregunta:
        await send_whatsapp_message(telefono, 
            f"Soy SecurityBot-WA, {nombre_usuario}. Estoy aquí para ayudarte a analizar mensajes de texto o imágenes que te parezcan sospechosas de ser estafas o phishing. También puedo responder tus preguntas sobre ciberseguridad. 😊")
    elif "audio" in normalized_pregunta and "entiendes" in normalized_pregunta:
        await send_whatsapp_message(telefono, 
            f"¡Hola, {nombre_usuario}! Por el momento, mi especialidad son los mensajes de texto e imágenes. Aún estoy aprendiendo a procesar audios, ¡pero espero poder ayudarte con ellos muy pronto! 😊")
    else:
        await send_whatsapp_message(telefono, 
            f"Entendido, {nombre_usuario}. Si tienes un mensaje o imagen para analizar, ¡envíamelo! O si tienes una pregunta sobre ciberseguridad o quieres un consejo, también puedo ayudarte con eso. 😊")

async def handle_solicitar_tip(telefono: str, nombre_usuario: str):
    """Maneja solicitud de consejos de seguridad"""
    tip = random.choice(SECURITY_TIPS)
    await send_whatsapp_message(telefono, 
        f"¡Claro, {nombre_usuario}! Aquí tienes un consejo de seguridad para ti:\n\n{tip}\n\nEspero te sea útil. 😊")

async def handle_intencion_no_clara(telefono: str, nombre_usuario: str, intencion: str, texto: str):
    """Maneja intenciones no claras o irrelevantes"""
    print(f"Intención clasificada como '{intencion}' para '{texto[:50]}...' de {nombre_usuario}.")
    await send_whatsapp_message(telefono, 
        f"Vaya, {nombre_usuario}, no estoy completamente seguro de cómo ayudarte con eso. 🤔\n"
        f"Recuerda que puedo:\n"
        f"1. Analizar un mensaje o imagen sospechosa 🔍\n"
        f"2. Responder preguntas sobre ciberseguridad 🛡️\n"
        f"3. Darte un consejo de seguridad ráp💡\n\n"
        f"¿Qué te gustaría hacer?")
async def handle_image_message(telefono: str, message_object: dict, user_data: sqlite3.Row):
    """Maneja mensajes de imagen"""
    nombre_usuario = user_data["nombre"] if user_data and user_data["nombre"] else "tú"
    image_id_wa = message_object.get("image", {}).get("id")
    if image_id_wa:
        await send_whatsapp_message(telefono, 
            f"🖼️ ¡Recibí tu imagen, {nombre_usuario}! La voy a revisar con cuidado y te envío mi análisis en un momento. 🧐")
        asyncio.create_task(process_incoming_image_task(telefono, user_data, image_id_wa))
    else:
        await send_whatsapp_message(telefono, 
            f"⚠️ Vaya, {nombre_usuario}, parece que hubo un problema con la imagen que enviaste. ¿Podrías intentar mandarla de nuevo, por favor?")
async def process_incoming_image_task(telefono: str, user_data: sqlite3.Row, image_id_whatsapp: str):
    """Procesa imágenes recibidas con OCR"""
    from app.services.external_apis import download_image_from_whatsapp
    user_name = user_data["nombre"] if user_data and user_data["nombre"] else "tú"
    print(f"Iniciando tarea de procesamiento de imagen para {telefono} ({user_name}), image_id: {image_id_whatsapp}")

    image_bytes = await download_image_from_whatsapp(image_id_whatsapp)
    if not image_bytes:
        await send_whatsapp_message(telefono, 
            f"⚠️ Lo siento, {user_name}, no pude descargar la imagen que enviaste. ¿Podrías intentar enviarla de nuevo?")
        return

    image_file_name = f"{telefono}_{uuid.uuid4().hex[:8]}.jpg"

    try:
        image_path = os.path.join(IMAGES_DIR, image_file_name)

        def save_and_ocr_sync(path, data_bytes):
            with open(path, "wb") as f:
                f.write(data_bytes)

            nparr = np.frombuffer(data_bytes, np.uint8)
            img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img_cv is None:
                return ""

            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            h, w = th.shape
            if w < 800:
                th = cv2.resize(th, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_LINEAR)

            img_pil = Image.fromarray(th)
            config = "--oem 3 --psm 6 -l spa+eng"
            texto = pytesseract.image_to_string(img_pil, config=config)
            return texto.strip()

        text_ocr = await asyncio.to_thread(save_and_ocr_sync, image_path, image_bytes)
        
        if not text_ocr:
            await send_whatsapp_message(telefono, 
                f"🤔 {user_name}, no pude encontrar texto legible en la imagen. Para que pueda ayudarte mejor, asegúrate de que la imagen sea clara. ¡Gracias!")
            return
        
        text_for_analysis = f"(El siguiente texto fue extraído de una imagen que me envió {user_name}. El OCR podría tener errores, por favor intenta entender el contexto original):\n---\n{text_ocr}\n---"
        
        image_context = {
            "is_from_image_processing": True,
            "ocr_text_original": text_ocr,
            "image_db_id": image_file_name
        }
        
        await handle_analizar_mensaje(telefono, text_for_analysis, user_data, image_context=image_context)
        print(f"Tarea de procesamiento de imagen para {telefono} ({user_name}) completada exitosamente.")

    except pytesseract.TesseractNotFoundError:
        print("ERROR CRÍTICO: Tesseract OCR no está instalado o no en PATH.")
        await send_whatsapp_message(telefono, 
            f"⚠️ ¡Uy, {user_name}! Parece que tengo un problema técnico con mi sistema para leer imágenes. Lamento no poder analizarla esta vez.")
    except Exception as e:
        print(f"ERROR en process_incoming_image_task (tel: {telefono}, img_id: {image_id_whatsapp}): {e}")
        await send_whatsapp_message(telefono, 
            f"⚠️ Lo siento mucho, {user_name}, ocurrió un error inesperado mientras procesaba tu imagen. Por favor, intenta más tarde. 🙏")
async def handle_estado_esperando_detalles(telefono: str, text: str, user_data: sqlite3.Row, message_type: str):
    """Maneja el estado cuando el usuario debe decidir si quiere ver detalles"""
    nombre_usuario = user_data["nombre"] if user_data and user_data["nombre"] else "tú"
    if message_type != "text":
        await send_whatsapp_message(telefono, 
            f"Hola {nombre_usuario}, esperaba un mensaje de texto para saber si querías más detalles. Si es así, por favor, escribe algo como 'sí, muéstrame'.")
        return

    print(f"DEBUG: {telefono} en ESPERANDO_MAS_DETALLES, recibió: '{text}'")

    user_profile_dict = dict(user_data)
    decision_ia = await analyze_with_deepseek(normalize_text(text), "decision_ver_detalles", user_profile_dict)
    print(f"DEBUG: Decisión de IA para ver detalles ({telefono}): {decision_ia}")

    if decision_ia == "QUIERE_DETALLES":
        detalles = user_data["last_analysis_details"]
        if detalles:
            await send_whatsapp_message(telefono, detalles)
            await send_whatsapp_message(telefono, 
                f"{nombre_usuario}, ¿te fue útil este análisis? Puedes responder con un 👍 o 👎, o simplemente seguir con otra consulta.")
            
            new_state = ESTADO_REGISTRADO
            analisis_lower = detalles.lower()
            
            if ("¿llegaste a hacer clic" in analisis_lower and 
                ("sí o no" in analisis_lower or "si o no" in analisis_lower) and 
                "escribe ayuda" in analisis_lower):
                new_state = ESTADO_ESPERANDO_RESPUESTA_PHISHING
                print(f"INFO: Usuario {telefono} movido a ESPERANDO_RESPUESTA_PHISHING después de ver detalles.")
            
            db_update_user(telefono, {"estado": new_state, "last_analysis_details": None})
        else:
            await send_whatsapp_message(telefono, 
                "Parece que no tengo los detalles guardados. Por favor, envía el mensaje original de nuevo para analizarlo.")
            db_update_user(telefono, {"estado": ESTADO_REGISTRADO, "last_analysis_details": None})

    elif decision_ia == "OTRA_COSA":
        print(f"DEBUG: {telefono} dijo OTRA_COSA. Tratando como nueva consulta.")
        db_update_user(telefono, {"estado": ESTADO_REGISTRADO, "last_analysis_details": None})
        current_user_reloaded = db_get_user(telefono)
        
        if current_user_reloaded:
            await handle_text_message(telefono, text, current_user_reloaded)
        else:
            print(f"ERROR: No se pudo recargar el usuario {telefono} después de OTRA_COSA.")
            await send_whatsapp_message(telefono, 
                "Hubo un pequeño problema, ¿podrías enviar tu consulta de nuevo, por favor?")
    else:
        print(f"WARN: Respuesta no esperada de IA para decision_ver_detalles ({telefono}): {decision_ia}")
        await send_whatsapp_message(telefono, 
            f"🤔 {nombre_usuario}, no estoy seguro de cómo proceder. Si querías ver los detalles, puedes intentarlo de nuevo diciendo 'sí, quiero verlos'.")
async def handle_post_phishing_response(telefono: str, text: str, user_data: sqlite3.Row, message_type: str):
    """Maneja la respuesta del usuario después de un análisis de phishing"""
    nombre_usuario = user_data["nombre"] if user_data and user_data["nombre"] else "tú"
    if message_type != "text":
        await send_whatsapp_message(telefono, 
            f"Hola {nombre_usuario}, estaba esperando una respuesta de SÍ, NO o AYUDA en texto. Si quieres analizar otra cosa, envíala después de responder, por favor. 👍")
        return

    normalized_input = normalize_text(text)
    user_profile_dict = dict(user_data)

    decision_usuario = await analyze_with_deepseek(normalized_input, "decision_post_phishing_interaction", user_profile_dict)
    print(f"DEBUG: Decisión IA en handle_post_phishing_response ({telefono}): {decision_usuario}")

    if decision_usuario == "RESPUESTA_SI":
        await send_whatsapp_message(telefono, 
            f"🆘 Entendido, {nombre_usuario}. No te preocupes, vamos a ver qué pasos puedes seguir. Dame un momento... 🛡️")
        respuesta_ayuda = await analyze_with_deepseek("El usuario indicó que SÍ interactuó con la estafa.", 
                                                    "ayuda_post_estafa", user_profile_dict)
        if respuesta_ayuda:
            await send_whatsapp_message(telefono, respuesta_ayuda)
        else:
            await send_whatsapp_message(telefono, 
                f"Lo lamento, {nombre_usuario}, tuve dificultades para generar los pasos de ayuda. Si es urgente, te recomiendo contactar directamente a las autoridades. 🙏")
        db_update_user(telefono, {"estado": ESTADO_REGISTRADO, "last_analyzed_url": None})

    elif decision_usuario == "RESPUESTA_NO":
        await send_whatsapp_message(telefono, 
            f"¡Excelente noticia, {nombre_usuario}! 👏 Me alegra mucho que no hayas interactuado con ese mensaje sospechoso. ¡Sigue así, desconfiando y verificando siempre! 😊")
        db_update_user(telefono, {"estado": ESTADO_REGISTRADO, "last_analyzed_url": None})

    elif decision_usuario == "PIDE_AYUDA":
        await send_whatsapp_message(telefono, 
            f"🆘 De acuerdo, {nombre_usuario}. Te prepararé los pasos de ayuda específicos. Un momento... 🛡️")
        respuesta_ayuda = await analyze_with_deepseek("El usuario escribió AYUDA tras un análisis de estafa.", 
                                                    "ayuda_post_estafa", user_profile_dict)
        if respuesta_ayuda:
            await send_whatsapp_message(telefono, respuesta_ayuda)
        else:
            await send_whatsapp_message(telefono, 
                f"Lo lamento, {nombre_usuario}, tuve dificultades para generar los pasos de ayuda. 🙏")
        db_update_user(telefono, {"estado": ESTADO_REGISTRADO, "last_analyzed_url": None})

    elif decision_usuario == "ES_PREGUNTA":
        print(f"DEBUG: Usuario {telefono} hizo una pregunta en estado ESPERANDO_RESPUESTA_PHISHING")
        await send_whatsapp_message(telefono, 
            f"🤔 ¡Claro, {nombre_usuario}! Déjame responder tu pregunta. Un momento...")
        respuesta = await analyze_with_deepseek(text, "cyber_pregunta", user_profile_dict)
        if respuesta:
            await send_whatsapp_message(telefono, respuesta)
            await send_whatsapp_message(telefono, 
                f"Espero que eso haya aclarado tu duda, {nombre_usuario}. Recordando el mensaje sospechoso, ¿llegaste a interactuar con él (SÍ/NO) o necesitas AYUDA específica?")
        else:
            await send_whatsapp_message(telefono, 
                f"Mis disculpas, {nombre_usuario}, no pude procesar tu pregunta. Volviendo al tema: ¿interactuaste con el mensaje (SÍ/NO) o necesitas AYUDA?")

    elif decision_usuario == "ES_COMENTARIO":
        if "gracias" in normalized_input:
            respuesta_usuario = f"¡De nada, {nombre_usuario}! 😊 "
        elif "ok" in normalized_input or "entendido" in normalized_input:
            respuesta_usuario = f"Entendido, {nombre_usuario}. "
        else:
            respuesta_usuario = f"Ok, {nombre_usuario}, he tomado nota de tu comentario. "
        
        respuesta_usuario += f"Sobre el mensaje que analizamos, ¿llegaste a interactuar con él (SÍ/NO) o necesitas AYUDA específica?"
        await send_whatsapp_message(telefono, respuesta_usuario)

    else:
        print(f"DEBUG: Respuesta no clasificada ({decision_usuario}) en ESPERANDO_RESPUESTA_PHISHING para {telefono}")
        await send_whatsapp_message(telefono, 
            f"🤔 {nombre_usuario}, no estoy seguro de haber entendido tu respuesta. Por favor responde con *SÍ*, *NO*, o escribe *AYUDA*. ¡Gracias!")