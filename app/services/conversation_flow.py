import asyncio
import os
import re
import logging
from typing import Dict, Optional
from app.services.external_apis import send_whatsapp_message, analyze_with_deepseek
from app.services.admin_commands import handle_admin_command, is_admin, is_admin_command
from app.services.svm_classifier import svm_classifier, initialize_svm
from app.storage.users_state import db_update_user, db_get_user
from app.storage.feedback_db import (
    log_interaction, 
    update_user_feedback,
    mark_admin_decision,
    get_next_pending_negative_review,
    count_pending_reviews
)
from app.utils.preprocessing import normalize_text, extract_first_url
from app.utils.config import (
    ESTADO_PENDIENTE_TERMINOS, ESTADO_PENDIENTE_NOMBRE, ESTADO_PENDIENTE_EDAD,
    ESTADO_PENDIENTE_CONOCIMIENTO, ESTADO_REGISTRADO, ESTADO_ESPERANDO_RESPUESTA_PHISHING,
    ESTADO_ESPERANDO_MAS_DETALLES, ESTADO_ADMIN_REVISANDO, SECURITY_TIPS
)
import random
import uuid
import datetime
import traceback
import numpy as np
import cv2
import pytesseract
from PIL import Image

# Usar /tmp en Cloud Run (efímero), imagenes_recibidas en local
if os.environ.get("CLOUD_RUN") or os.environ.get("GOOGLE_CLOUD_PROJECT"):
    IMAGES_DIR = "/tmp/images"
else:
    IMAGES_DIR = "imagenes_recibidas"

if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR, mode=0o777)

# ===== FUNCIÓN AUXILIAR PARA PLANTILLAS DE FEEDBACK =====
async def solicitar_feedback_template(telefono: str, nombre_usuario: str):
    """
    Envía la plantilla de feedback aprobada por Meta.
    ESTRUCTURA VALIDADA: Body + parameter_name='nombre'
    """
    
    # 1. Configuración exacta que funcionó en el diagnóstico
    NOMBRE_PLANTILLA = "feedback_analisis"
    CODIGO_IDIOMA = "es_CO" 
    
    # 2. Componentes (La combinación ganadora 🏆)
    components = [
        {
            "type": "body",
            "parameters": [
                {
                    "type": "text",
                    # OJO: Esto es lo que Meta exigía para tu plantilla nueva
                    "parameter_name": "nombre", 
                    "text": str(nombre_usuario) if nombre_usuario else "Usuario"
                }
            ]
        }
    ]

    # 3. Envío
    # Nota: No usamos try/except aquí para que si falla, el error suba 
    # y active el fallback en la función que lo llama.
    await send_whatsapp_message(
        to=telefono,
        text="", # Parámetro correcto (no message_body) - requerido pero vacío para templates
        message_type="template",
        template_name=NOMBRE_PLANTILLA,
        template_language=CODIGO_IDIOMA, 
        template_components=components
    )

async def handle_user_message(telefono_remitente: str, message_object: dict, message_type: str, 
                               text_recibido_original: str, current_user: Dict):
    """Punto de entrada principal para manejar mensajes del usuario"""
    
    user_state = current_user["estado"]
    user_name = current_user["nombre"] if current_user and current_user["nombre"] else "tú"
    
    print(f"DEBUG: Handler para {telefono_remitente}, Estado: {user_state}")
    
    # ===== VERIFICACIÓN DE COMANDOS ADMINISTRATIVOS (PRIORIDAD MÁXIMA) =====
    if message_type == "text" and is_admin_command(text_recibido_original):
        print(f"🔧 Detectado posible comando admin: {text_recibido_original[:20]}")
        admin_response = await handle_admin_command(telefono_remitente, text_recibido_original)
        if admin_response:
            print(f"✅ Comando admin ejecutado para {telefono_remitente}")
            await send_whatsapp_message(telefono_remitente, admin_response)
            return
        elif is_admin(telefono_remitente):
            await send_whatsapp_message(telefono_remitente, 
                "❌ Comando no reconocido. Usa `/help` para ver comandos disponibles.")
            return
    # ===== FIN DE COMANDOS ADMINISTRATIVOS =====
    
    # ===== LÓGICA UNIFICADA PARA BOTONES (FEEDBACK) =====
    # Unificamos: interactive (button_reply/list_reply) + button (template buttons)
    btn_text = ""
    
    # Caso A: Botones Interactivos (button_reply, list_reply)
    if message_type == "interactive":
        interactive_type = message_object.get("interactive", {}).get("type")
        
        if interactive_type == "button_reply":
            # Estructura: interactive.button_reply.title
            btn_text = message_object.get("interactive", {}).get("button_reply", {}).get("title", "")
            btn_id = message_object.get("interactive", {}).get("button_reply", {}).get("id", "")
            logging.info(f"🔘 Button Reply detectado: '{btn_text}' (ID: {btn_id})")
            print(f"🔘 Button Reply por {telefono_remitente}: {btn_text} (ID: {btn_id})")
        
        elif interactive_type == "list_reply":
            # Estructura: interactive.list_reply.title
            btn_text = message_object.get("interactive", {}).get("list_reply", {}).get("title", "")
            logging.info(f"🔘 List Reply detectado: '{btn_text}'")
            print(f"🔘 List Reply por {telefono_remitente}: {btn_text}")
    
    # Caso B: Botones de Plantilla (Template Buttons)
    elif message_type == "button":
        # Estructura: button.text
        btn_text = message_object.get("button", {}).get("text", "")
        logging.info(f"🔘 Template Button detectado: '{btn_text}'")
        print(f"🔘 Template Button por {telefono_remitente}: {btn_text}")
    
    # Procesamos cualquier botón detectado
    if btn_text:
        btn_text_norm = btn_text.lower()
        
        # Palabras clave negativas (PRIMERO - más específicas)
        if any(x in btn_text_norm for x in ["no", "malo", "error", "equivoc", "fallo", "incorrecto", "👎"]):
            print(f"❌ Feedback NEGATIVO detectado: '{btn_text}'")
            updated = update_user_feedback(telefono_remitente, "NEGATIVO")
            if updated:
                await send_whatsapp_message(telefono_remitente, 
                    "Entendido 😓. He marcado este análisis para revisión humana. Gracias por corregirme.")
            return
        
        # Palabras clave positivas (DESPUÉS)
        elif any(x in btn_text_norm for x in ["útil", "util", "bueno", "excelente", "correcto", "si", "sí", "👍"]):
            print(f"✅ Feedback POSITIVO detectado: '{btn_text}'")
            updated = update_user_feedback(telefono_remitente, "POSITIVO")
            if updated:
                await send_whatsapp_message(telefono_remitente, 
                    "¡Genial! 🥳 Me alegra haber ayudado. Guardaré este caso como un éxito.")
            return
        
        else:
            print(f"⚠️ Botón detectado pero no es feedback: '{btn_text}'")

    # ===== FIN LÓGICA UNIFICADA BOTONES =====
    
    # Detectar comandos de reset
    normalized_text = normalize_text(text_recibido_original)
    reset_commands = ["empezar de nuevo", "reset", "cancelar", "olvidalo", "ya no", "detente"]
    is_reset_command = any(cmd in normalized_text for cmd in reset_commands) and len(normalized_text) < 30
    
    if is_reset_command:
        await handle_reset_command(telefono_remitente, user_name)
        return
    
    # ===== INTERCEPTOR ESPECIAL PARA MODO REVISIÓN DE ADMINISTRADOR =====
    if user_state == ESTADO_ADMIN_REVISANDO:
        await handle_admin_review_flow(telefono_remitente, text_recibido_original, current_user)
        return
    # =====================================================================
    
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

async def handle_onboarding_process(telefono: str, text_received: str, user_data: Dict, message_type: str):
    """Maneja el proceso de registro del usuario"""
    # AHORA PERMITIMOS TEXTO, BOTONES Y MENSAJES INTERACTIVOS:
    if message_type not in ["text", "button", "interactive"]:
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
            "⚠️ Para que podamos continuar, necesito que aceptes los términos. Solo escribe *ACEPTO* si estás de acuerdo o presiona el boton. Si no deseas continuar, puedes responder *NO ACEPTO*. ¡Gracias! 💙")

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
                    f"¡Perfecto, {user_name}! 👍 Ya casi terminamos con tu registro.\n\n"
                    "Cuéntame, ¿qué tanto sabes sobre ciberseguridad y estafas en línea? \n"
                    "Puedes escribir un resumen de tu experiencia (Ej: 'Solo sé lo básico') y la IA lo clasificará como *Bajo*, *Medio* o *Alto*."
                )
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
    """
    Maneja el estado de solicitud de nivel de conocimiento en ciberseguridad
    usando la IA para clasificar la respuesta libre del usuario.
    """
    current_user = db_get_user(telefono)
    
    # 2. Llamamos a DeepSeek para clasificar la respuesta
    # El prompt para 'conocimiento' está configurado para devolver SOLO la palabra ALTO, MEDIO o BAJO.
    clasificacion_ia = await analyze_with_deepseek(
        message_text=text_received,
        mode="conocimiento", 
        user_profile=dict(current_user) if current_user else {} # Pasamos los datos del usuario
    )

    nivel_conocimiento = None

    if clasificacion_ia:
        # Normalizamos la respuesta de la IA
        respuesta_limpia = clasificacion_ia.upper().strip()

        if "ALTO" in respuesta_limpia:
            nivel_conocimiento = "ALTO"
        elif "MEDIO" in respuesta_limpia:
            nivel_conocimiento = "MEDIO"
        elif "BAJO" in respuesta_limpia:
            nivel_conocimiento = "BAJO"

    # 3. Procesamiento del resultado
    if nivel_conocimiento:
        # Actualizamos la base de datos y cambiamos el estado a REGISTRADO
        db_update_user(telefono, {"conocimiento": nivel_conocimiento, "estado": ESTADO_REGISTRADO})
        
        # Respuesta final de bienvenida
        await send_whatsapp_message(
            telefono, 
            f"¡Excelente, {user_name}! Tu perfil se ha completado exitosamente. 🎉\n\n"
            f"Hemos clasificado tu nivel de ciberseguridad como: *{nivel_conocimiento}*.\n\n"
            "A partir de ahora, puedes: \n"
            "1️⃣ Preguntarme cualquier duda sobre seguridad.\n"
            "2️⃣ Enviarme enlaces o fotos sospechosas para analizar.\n"
            "¡Estoy aquí para ayudarte a navegar seguro! 👍"
        )
    else:
        # Fallback si la IA no pudo clasificar o hubo un error en la API
        await send_whatsapp_message(
            telefono, 
            f"⚠️ Lo siento, {user_name}, no pude entender tu nivel de conocimiento con claridad. Para terminar tu registro, por favor, solo responde: *Bajo*, *Medio* o *Alto*."
        )

async def handle_registered_user_message(telefono: str, message_object: dict, message_type: str, 
                                        text_recibido: str, user_data: Dict):
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

async def handle_text_message(telefono: str, text: str, user_data: Dict):
    """Maneja mensajes de texto para usuarios registrados"""
    cleaned_text = re.sub(r'\s+', ' ', text).strip()
    nombre_usuario = user_data["nombre"] if user_data and user_data["nombre"] else "tú"
    user_profile_dict = dict(user_data)
    
    # ===== CAPTURA RÁPIDA DE FEEDBACK (RLHF) =====
    # Detectar respuestas de feedback ANTES de hacer análisis de intención
    text_lower = cleaned_text.lower()
    
    if any(word in text_lower for word in ["útil", "utilidad", "me ayudó", "me sirvió", "si fue útil", "sí fue útil"]):
        print(f"✅ Feedback POSITIVO detectado de {telefono}: '{cleaned_text}'")
        updated = update_user_feedback(telefono, "POSITIVO")
        if updated:
            await send_whatsapp_message(telefono, 
                f"¡Gracias por tu feedback, {nombre_usuario}! 🧠✅ Me alegra haber ayudado. Tu opinión me ayuda a mejorar cada día.")
        else:
            await send_whatsapp_message(telefono, 
                f"Recibí tu feedback, {nombre_usuario}, pero no pude guardarlo. ¿Quieres intentar de nuevo?")
        return
    
    elif any(word in text_lower for word in ["no útil", "no me ayudó", "no sirve", "incorrecto", "equivocado", "mal", "no fue útil", "no es útil"]):
        print(f"❌ Feedback NEGATIVO detectado de {telefono}: '{cleaned_text}'")
        updated = update_user_feedback(telefono, "NEGATIVO")
        if updated:
            await send_whatsapp_message(telefono, 
                f"Entendido, {nombre_usuario}. 🧠⚠️ Un humano revisará este caso para mejorar mi entrenamiento. Gracias por ayudarme a crecer.")
        else:
            await send_whatsapp_message(telefono, 
                f"Recibí tu feedback, {nombre_usuario}, pero no pude guardarlo. ¿Quieres intentar de nuevo?")
        return
    # ===== FIN CAPTURA FEEDBACK =====
    
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
        await handle_solicitar_consejo(telefono, nombre_usuario)
    
    else:
        await handle_intencion_desconocida(telefono, nombre_usuario, intencion, cleaned_text)

async def handle_saludo(telefono: str, nombre_usuario: str, user_data: Dict):
    """Maneja saludos del usuario"""
    user_dict = dict(user_data)
    
    # Personalizar saludo según contexto
    greeting_options = [
        f"¡Hola de nuevo, {nombre_usuario}! 👋",
        f"¡Hey {nombre_usuario}! 😊",
        f"¡Qué tal, {nombre_usuario}! 👋",
    ]
    
    greeting = random.choice(greeting_options)
    
    # Agregar contexto si hay interacciones previas
    if user_dict.get("last_analyzed_url"):
        greeting += f" ¿Listo para analizar otro mensaje?"
    elif user_dict.get("last_image_timestamp"):
        greeting += f" ¿Necesitas ayuda con algo?"
    else:
        greeting += f" ¿En qué te puedo ayudar hoy?"
    
    await send_whatsapp_message(telefono, greeting)

async def handle_analizar_mensaje(telefono: str, mensaje: str, user_data: Dict, image_context: dict = None):
    """
    Maneja la solicitud de análisis de mensaje con LÓGICA HÍBRIDA (SVM Local + DeepSeek IA).
    """
    nombre_usuario = user_data["nombre"] if user_data and user_data["nombre"] else "tú"
    
    await send_whatsapp_message(telefono, 
        f"🔍 Analizando mensaje con doble verificación (IA + Detección Técnica)... dame unos segundos, {nombre_usuario}.")
    
    # ========== PASO 1: ANÁLISIS TÉCNICO LOCAL (SVM) ==========
    if not svm_classifier.model:
        print("⚠️ Modelo SVM no estaba cargado, inicializando...")
        initialize_svm()
    
    svm_result = svm_classifier.analyze_message(mensaje)
    svm_verdict = svm_result['final_verdict']
    
    # Preparamos un reporte técnico legible para DeepSeek
    detalles_tecnicos = (
        f"📊 REPORTE TÉCNICO (Detección Local SVM):\n"
        f"• Nivel de Riesgo: {svm_verdict['risk_level']}\n"
        f"• Confianza del Modelo: {svm_result['confidence']*100:.1f}%\n"
        f"• Clasificación: {'PHISHING/ESTAFA DETECTADO' if svm_verdict['is_scam'] else 'PARECE LEGÍTIMO'}\n"
        f"• Razón Principal: {svm_verdict['main_reason']}\n"
    )
    
    # Agregar análisis de URLs si existen
    if svm_result['url_analysis']:
        detalles_tecnicos += f"\n📍 ANÁLISIS DE ENLACES:\n"
        for url_data in svm_result['url_analysis']:
            detalles_tecnicos += f"   • URL: {url_data['url'][:40]}...\n"
            detalles_tecnicos += f"   • Riesgo: {url_data['risk_level']}\n"
    
    # Si hay alerta crítica, la marcamos
    if svm_result.get('critical_red_flag'):
        detalles_tecnicos += f"\n🚨 ALERTA CRÍTICA: {svm_result.get('override_reason', '')}\n"
    
    # ========== PASO 2: CONSTRUCCIÓN DEL PROMPT HÍBRIDO ==========
    prompt_combinado = (
        f"MENSAJE A ANALIZAR:\n"
        f"'''{mensaje}'''\n\n"
        f"─────────────────────────────────────\n"
        f"{detalles_tecnicos}\n"
        f"─────────────────────────────────────\n\n"
        f"INSTRUCCIÓN: Actúa como juez final. Combina el análisis técnico anterior con tu "
        f"análisis humanístico del texto (ingenería social, urgencia, manipulación). "
        f"Emite un veredicto definitivo sobre si este es phishing/estafa o legítimo."
    )
    
    extracted_url = extract_first_url(mensaje)
    if not extracted_url and image_context and image_context.get("ocr_text_original"):
        extracted_url = extract_first_url(image_context.get("ocr_text_original"))

    user_profile_dict = dict(user_data)
    
    # ========== PASO 3: CONSULTA A DEEPSEEK (Juez Final) ==========
    analisis_completo = await analyze_with_deepseek(prompt_combinado, "phishing", user_profile_dict)

    if analisis_completo:
        # Separamos el veredicto corto de los detalles largos
        partes = analisis_completo.split("---DETALLES_SIGUEN---", 1)
        resumen_breve = partes[0].strip()
        detalles_completos = partes[1].strip() if len(partes) > 1 else analisis_completo

        # ========== PASO 4: ENVIAR VEREDICTO CORTO ==========
        await send_whatsapp_message(telefono, resumen_breve)
        
        await asyncio.sleep(0.5)
        
        # ========== PASO 5: INVITAR A VER DETALLES ==========
        await send_whatsapp_message(telefono, 
            f"📋 Tengo un informe técnico detallado explicando por qué llegamos a esta conclusión.\n\n"
            "¿Quieres ver el **análisis completo**? (Responde SÍ o NO)")

        # ========== PASO 6: ACTUALIZAR ESTADO Y GUARDAR CONTEXTO ==========
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
        
        # === GUARDAR LOG PARA RLHF ===
        final_verdict = {
            'is_scam': svm_verdict['is_scam'],
            'risk_level': svm_verdict['risk_level'],
            'main_reason': svm_verdict['main_reason']
        }
        log_interaction(
            phone=telefono,
            msg=mensaje,
            svm_res=svm_result,
            deepseek_res=analisis_completo,
            final_verdict=final_verdict
        )
        
        print(f"✅ Análisis híbrido completado para {telefono}")
        
    else:
        # Fallback si falla DeepSeek
        fallback_msg = (
            f"Tuve problemas con mi conexión a IA, pero mi sistema local de detección dice:\n\n"
            f"⚠️ **Nivel de Riesgo: {svm_verdict['risk_level']}**\n"
            f"{svm_verdict['main_reason']}\n\n"
            f"Te recomendaría no hacer clic en enlace alguno de este mensaje."
        )
        await send_whatsapp_message(telefono, fallback_msg)

async def handle_pregunta_seguridad(telefono: str, pregunta: str, user_profile: dict, nombre_usuario: str):
    """Maneja preguntas sobre ciberseguridad"""
    await send_whatsapp_message(telefono, 
        f"🤔 ¡Buena pregunta sobre seguridad, {nombre_usuario}! "
        f"Déjame consultar para darte la mejor respuesta posible... 💡")
    
    respuesta = await analyze_with_deepseek(pregunta, "cyber_pregunta", user_profile)
    
    if respuesta:
        await send_whatsapp_message(telefono, respuesta)
        
        await send_whatsapp_message(telefono, 
            f"¿Esta información te ayudó, {nombre_usuario}? "
            f"Si tienes más dudas o quieres un consejo práctico, ¡solo pregúntame! 😊")
    else:
        await send_whatsapp_message(telefono, 
            f"Mis disculpas, {nombre_usuario}. Tuve un inconveniente técnico. "
            f"¿Podrías reformular tu pregunta o intentarlo de nuevo? 🙏")

async def handle_meta_pregunta(telefono: str, pregunta: str, nombre_usuario: str):
    """Maneja preguntas sobre el bot y sus capacidades"""
    normalized_pregunta = normalize_text(pregunta)
    
    # Detectar tipo específico de pregunta
    if any(word in normalized_pregunta for word in ["que haces", "que puedes hacer", "para que sirves", "quien eres", "que eres"]):
        await send_whatsapp_message(telefono, 
            f"👋 ¡Hola, {nombre_usuario}! Soy *SecurityBot-WA*, tu asistente de ciberseguridad.\n\n"
            f"🎯 *Mis capacidades:*\n\n"
            f"🔍 *Analizar contenido sospechoso*\n"
            f"  • Mensajes de texto con enlaces\n"
            f"  • Imágenes con texto (OCR)\n"
            f"  • Capturas de pantalla\n\n"
            f"🛡️ *Responder preguntas*\n"
            f"  • ¿Qué es el phishing?\n"
            f"  • ¿Cómo proteger mis cuentas?\n"
            f"  • ¿Es seguro este enlace?\n\n"
            f"💡 *Darte consejos*\n"
            f"  • Tips de seguridad\n"
            f"  • Mejores prácticas\n"
            f"  • Prevención de estafas\n\n"
            f"🆘 *Ayuda en emergencias*\n"
            f"  • Pasos si caíste en una estafa\n"
            f"  • Qué hacer si te hackearon\n\n"
            f"¿En qué te puedo ayudar hoy? 😊")
    
    elif any(word in normalized_pregunta for word in ["imagen", "foto", "captura", "screenshot", "picture"]):
        await send_whatsapp_message(telefono, 
            f"📸 ¡Sí, {nombre_usuario}! Puedo analizar imágenes.\n\n"
            f"*¿Qué tipo de imágenes?*\n"
            f"✅ Capturas de mensajes sospechosos\n"
            f"✅ Fotos de pantallas con texto\n"
            f"✅ Publicaciones dudosas\n"
            f"✅ Promociones que parezcan falsas\n\n"
            f"Uso *OCR (reconocimiento de texto)* para leer el contenido y analizarlo. "
            f"¡Envíame la imagen cuando quieras! 🖼️")
    
    else:
        # Respuesta genérica para otras preguntas sobre el bot
        await send_whatsapp_message(telefono, 
            f"🤖 Soy SecurityBot-WA, {nombre_usuario}.\n\n"
            f"*En resumen, puedo:*\n"
            f"• 🔍 Analizar mensajes e imágenes sospechosas\n"
            f"• 🛡️ Responder preguntas de ciberseguridad\n"
            f"• 💡 Darte consejos de protección\n"
            f"• 🆘 Ayudarte si caíste en una estafa\n\n"
            f"¿Sobre qué aspecto específico quieres saber más? "
            f"O simplemente envíame algo para analizar. 😊")

async def handle_solicitar_consejo(telefono: str, nombre_usuario: str):
    """Maneja solicitud de consejos de seguridad"""
    tip = random.choice(SECURITY_TIPS)
    await send_whatsapp_message(telefono, 
        f"💡 *Consejo de Seguridad para {nombre_usuario}:*\n\n"
        f"{tip}\n\n"
        f"¿Quieres otro consejo? Solo pídemelo. También puedo responder "
        f"preguntas específicas sobre seguridad. 😊")

async def handle_intencion_desconocida(telefono: str, nombre_usuario: str, intencion: str, texto: str):
    """Maneja intenciones no reconocidas o errores de clasificación"""
    print(f"⚠️ INTENCIÓN NO RECONOCIDA: '{intencion}' para '{texto[:50]}...' de {nombre_usuario} ({telefono})")
    
    await send_whatsapp_message(telefono, 
        f"🤔 {nombre_usuario}, no estoy completamente seguro de cómo ayudarte con eso.\n\n"
        f"*Puedo asistirte con:*\n\n"
        f"1️⃣ *Analizar contenido sospechoso*\n"
        f"   Envíame mensajes, enlaces o imágenes dudosas\n\n"
        f"2️⃣ *Responder preguntas de seguridad*\n"
        f"   Ej: '¿Qué es el phishing?'\n\n"
        f"3️⃣ *Darte consejos prácticos*\n"
        f"   Solo pídeme un tip de seguridad\n\n"
        f"¿Cuál de estas opciones te interesa?")

async def handle_image_message(telefono: str, message_object: dict, user_data: Dict):
    """Maneja mensajes de imagen"""
    nombre_usuario = user_data["nombre"] if user_data and user_data["nombre"] else "tú"
    image_id_wa = message_object.get("image", {}).get("id")
    if image_id_wa:
        asyncio.create_task(process_incoming_image_task(telefono, user_data, image_id_wa))
    else:
        await send_whatsapp_message(telefono, 
            f"⚠️ Vaya, {nombre_usuario}, parece que hubo un problema con la imagen que enviaste. ¿Podrías intentar mandarla de nuevo, por favor?")

async def process_incoming_image_task(telefono: str, user_data: Dict, image_id_whatsapp: str):
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

    # Enviar mensaje indicando que está procesando
    await send_whatsapp_message(telefono, 
        f"📸 {user_name}, estoy analizando la imagen... dame un momento. 🔍")

    try:
        image_path = os.path.join(IMAGES_DIR, image_file_name)

        def save_and_ocr_sync(path, data_bytes):
            """Extrae texto con OCR ROBUSTO - múltiples intentos para garantizar precisión"""
            with open(path, "wb") as f:
                f.write(data_bytes)

            nparr = np.frombuffer(data_bytes, np.uint8)
            img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img_cv is None:
                return ""

            # ===== ESTRATEGIA MULTI-INTENTO PARA MÁXIMA PRECISIÓN =====
            
            # INTENTO 1: Procesamiento BALANCEADO (velocidad + calidad)
            def ocr_intento_1(img):
                """Procesamiento balanceado: rapidez + calidad"""
                h, w = img.shape[:2]
                
                # Redimensión moderada (1200px máx - mejor que 800)
                if w > 1200 or h > 1000:
                    scale = min(1200 / w, 1000 / h) if w > 0 and h > 0 else 1
                    new_w, new_h = int(w * scale), int(h * scale)
                    img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                # Thresholding OTSU (más preciso que adaptativo para la mayoría)
                _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # Cleanup leve (1 iteración)
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
                th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=1)
                
                # Upscale si es pequeña
                h, w = th.shape
                if w < 700 and w > 0:
                    scale = min(2.0, 700 / w)
                    th = cv2.resize(th, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
                
                # Tesseract con PSM 6 (mejor para bloques de texto uniformes)
                img_pil = Image.fromarray(th)
                config = "--oem 1 --psm 6 -l spa+eng"
                texto = pytesseract.image_to_string(img_pil, config=config, timeout=8)
                return texto.strip()
            
            # INTENTO 2: Procesamiento ADAPTATIVO (para imágenes difíciles)
            def ocr_intento_2(img):
                """Para imágenes complejas o de baja calidad"""
                h, w = img.shape[:2]
                if w > 1200 or h > 1000:
                    scale = min(1200 / w, 1000 / h) if w > 0 and h > 0 else 1
                    img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
                
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                # Thresholding adaptativo (mejor para variación de iluminación)
                th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, blockSize=13, C=2)
                
                # Limpieza más fuerte
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
                th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=1)
                th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=1)
                
                # Upscale
                h, w = th.shape
                if w < 700:
                    th = cv2.resize(th, None, fx=min(2.0, 700/w if w > 0 else 1), 
                                   fy=min(2.0, 700/w if w > 0 else 1), interpolation=cv2.INTER_CUBIC)
                
                # PSM 3 para detectar bloques
                img_pil = Image.fromarray(th)
                config = "--oem 1 --psm 3 -l spa+eng"
                texto = pytesseract.image_to_string(img_pil, config=config, timeout=8)
                return texto.strip()
            
            # INTENTO 3: Sin preprocessing fuerte (imagen con mínimo ajuste)
            def ocr_intento_3(img):
                """Último intento: imagen con mínimo procesamiento"""
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                # Solo threshold OTSU, nada más
                _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                img_pil = Image.fromarray(th)
                config = "--oem 1 --psm 6 -l spa+eng"
                texto = pytesseract.image_to_string(img_pil, config=config, timeout=8)
                return texto.strip()
            
            # Ejecutar intentos en orden
            intentos = [
                ("Balanceado", ocr_intento_1),
                ("Adaptativo", ocr_intento_2),
                ("Mínimo procesamiento", ocr_intento_3),
            ]
            
            texto_extraido = ""
            for nombre_intento, func_intento in intentos:
                try:
                    texto = func_intento(img_cv)
                    if texto and len(texto) > 15:  # Si extrae más de 15 caracteres
                        print(f"✅ OCR {nombre_intento}: {len(texto)} caracteres")
                        texto_extraido = texto
                        break
                    else:
                        print(f"⚠️ OCR {nombre_intento}: insuficiente ({len(texto)} chars)")
                except Exception as e:
                    print(f"ℹ️ OCR {nombre_intento}: {type(e).__name__}")
                    continue
            
            return texto_extraido

        try:
            # Intentar OCR con timeout
            text_ocr = await asyncio.to_thread(save_and_ocr_sync, image_path, image_bytes)
        except (asyncio.TimeoutError, RuntimeError) as timeout_error:
            # Si Tesseract agota timeout, continuar SIN texto OCR
            print(f"⚠️ OCR timeout para {telefono}: {type(timeout_error).__name__}")
            text_ocr = None
        except Exception as ocr_error:
            # Otros errores de OCR
            print(f"⚠️ Error OCR para {telefono}: {ocr_error}")
            text_ocr = None
        
        # Si no se extrajo texto, intentar análisis directo de imagen
        if not text_ocr:
            print(f"ℹ️ Usando análisis directo sin OCR para {telefono}")
            text_for_analysis = f"(Mi análisis de la imagen que recibí de {user_name} sin extraer texto - solo análisis visual)"
        else:
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
        error_trace = traceback.format_exc()
        print(f"ERROR en process_incoming_image_task (tel: {telefono}, img_id: {image_id_whatsapp}):")
        print(error_trace)
        await send_whatsapp_message(telefono, 
            f"⚠️ Lo siento mucho, {user_name}, ocurrió un error inesperado mientras procesaba tu imagen. Por favor, intenta más tarde. 🙏")

async def handle_estado_esperando_detalles(telefono: str, text: str, user_data: Dict, message_type: str):
    """Maneja la respuesta de si quiere ver detalles o no."""
    nombre_usuario = user_data["nombre"] if user_data and user_data["nombre"] else "tú"
    
    if message_type != "text":
        await send_whatsapp_message(telefono, 
            f"Hola {nombre_usuario}, esperaba un mensaje de texto (SÍ o NO).")
        return

    print(f"DEBUG: {telefono} en ESPERANDO_MAS_DETALLES, recibió: '{text}'")

    user_profile_dict = dict(user_data)
    decision_ia = await analyze_with_deepseek(normalize_text(text), "decision_ver_detalles", user_profile_dict)
    print(f"DEBUG: Decisión de IA para ver detalles ({telefono}): {decision_ia}")

    # ===== CASO 1: El usuario QUIERE ver detalles =====
    if decision_ia == "QUIERE_DETALLES":
        detalles = user_data["last_analysis_details"]
        if detalles:
            await send_whatsapp_message(telefono, detalles)
        else:
            await send_whatsapp_message(telefono, "⚠️ No pude recuperar los detalles, pero el veredicto anterior se mantiene.")
        
        await asyncio.sleep(3)
        
        # Pedir Feedback
        try:
            await solicitar_feedback_template(telefono, nombre_usuario)
        except Exception as e:
            print(f"⚠️ Error: {e}")
            await send_whatsapp_message(telefono, 
                "¿Te fue útil este análisis? (Responde 'útil' o 'no útil')")

    # ===== CASO 2: El usuario NO quiere detalles =====
    else:
        await send_whatsapp_message(telefono, "Entendido, mantenemos el chat breve.")
        
        await asyncio.sleep(1)
        try:
            await solicitar_feedback_template(telefono, nombre_usuario)
        except Exception as e:
            print(f"⚠️ Error: {e}")
            await send_whatsapp_message(telefono, 
                "¿Te fue útil mi análisis rápido? (Responde 'útil' o 'no útil')")

    # Volver al estado normal
    db_update_user(telefono, {"estado": ESTADO_REGISTRADO, "last_analysis_details": None})

async def handle_post_phishing_response(telefono: str, text: str, user_data: Dict, message_type: str):
    """Maneja la respuesta del usuario después de un análisis de phishing"""
    nombre_usuario = user_data["nombre"] if user_data and user_data["nombre"] else "tú"
    if message_type != "text":
        await send_whatsapp_message(telefono, 
            f"Hola {nombre_usuario}, estaba esperando una respuesta de SÍ, NO o AYUDA en texto.")
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
        db_update_user(telefono, {"estado": ESTADO_REGISTRADO, "last_analyzed_url": None})

    elif decision_usuario == "RESPUESTA_NO":
        await send_whatsapp_message(telefono, 
            f"¡Excelente noticia, {nombre_usuario}! 👏 Me alegra mucho que no hayas interactuado.")
        db_update_user(telefono, {"estado": ESTADO_REGISTRADO, "last_analyzed_url": None})

    elif decision_usuario == "PIDE_AYUDA":
        await send_whatsapp_message(telefono, 
            f"🆘 De acuerdo, {nombre_usuario}. Te prepararé los pasos de ayuda específicos...")
        respuesta_ayuda = await analyze_with_deepseek("El usuario escribió AYUDA.", 
                                                    "ayuda_post_estafa", user_profile_dict)
        if respuesta_ayuda:
            await send_whatsapp_message(telefono, respuesta_ayuda)
        db_update_user(telefono, {"estado": ESTADO_REGISTRADO, "last_analyzed_url": None})

    else:
        await send_whatsapp_message(telefono, 
            f"🤔 {nombre_usuario}, por favor responde con *SÍ*, *NO*, o *AYUDA*. ¡Gracias!")

async def handle_admin_review_flow(telefono_remitente: str, text_recibido: str, current_user: Dict):
    """Maneja el bucle interactivo de revisión de casos negativos para administradores"""
    
    try:
        normalized_input = normalize_text(text_recibido).upper()
        
        yes_patterns = ["SÍ", "SI", "YES", "S", "CORRECTO", "BIEN", "OK"]
        no_patterns = ["NO", "N", "MAL", "INCORRECTO", "ERROR"]
        exit_patterns = ["SALIR", "CANCELAR", "DONE", "TERMINADO"]
        
        case_id = current_user["last_analyzed_url"] if current_user else None
        if not case_id:
            await send_whatsapp_message(telefono_remitente, 
                "⚠️ No tengo registro del caso. Inicia de nuevo con `/revisar`.")
            db_update_user(telefono_remitente, {"estado": ESTADO_REGISTRADO, "last_analyzed_url": None})
            return
        
        if any(exit in normalized_input for exit in exit_patterns):
            await send_whatsapp_message(telefono_remitente, 
                "✋ Revisión finalizada.")
            db_update_user(telefono_remitente, {"estado": ESTADO_REGISTRADO, "last_analyzed_url": None})
            return
        
        if any(yes in normalized_input for yes in yes_patterns):
            bot_was_wrong = True
        elif any(no in normalized_input for no in no_patterns):
            bot_was_wrong = False
        else:
            await send_whatsapp_message(telefono_remitente, 
                "❓ Responde: *SÍ* (bot equivocado) / *NO* (bot correcto) / *SALIR*")
            return
        
        mark_admin_decision(case_id, bot_was_wrong=bot_was_wrong)
        print(f"✅ Decisión guardada para caso {case_id}: bot_was_wrong={bot_was_wrong}")
        
        next_case = get_next_pending_negative_review()
        
        if next_case:
            db_update_user(telefono_remitente, {"last_analyzed_url": str(next_case["id"])})
            
            pending_count = count_pending_reviews()
            
            mensaje_siguiente = (
                f"🕵️‍♂️ CASO #{next_case['id']}\n\n"
                f"💬 Mensaje: \"{next_case['original_user_message'][:100]}...\"\n"
                f"🤖 Bot: *{next_case['bot_verdict']}*\n"
                f"😞 Usuario: 👎\n\n"
                f"*¿Bot se equivocó?*\n"
                f"SI / NO / SALIR"
            )
            await send_whatsapp_message(telefono_remitente, mensaje_siguiente)
        else:
            await send_whatsapp_message(telefono_remitente, 
                "🎉 ¡Completado! Todos los casos revisados.")
            db_update_user(telefono_remitente, {"estado": ESTADO_REGISTRADO, "last_analyzed_url": None})
    
    except Exception as e:
        print(f"❌ Error en review: {e}")
        await send_whatsapp_message(telefono_remitente, 
            f"⚠️ Error: {str(e)}")
        db_update_user(telefono_remitente, {"estado": ESTADO_REGISTRADO, "last_analyzed_url": None})