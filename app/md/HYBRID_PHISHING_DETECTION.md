# 🛡️ Sistema Híbrido de Detección de Phishing (SVM + DeepSeek)

## 📋 Descripción General

SecurityBot-WA ahora implementa un **sistema híbrido de detección de phishing** que combina:

1. **SVM Local (Machine Learning)** - Análisis técnico rápido sin latencia de red
2. **DeepSeek API (LLM)** - Análisis humanístico y contextual
3. **Juez Final** - DeepSeek actúa como "juez" que combina ambas perspectivas

## 🔄 Flujo de Procesamiento

```
Usuario envía mensaje sospechoso
    ↓
[PASO 1: SVM Local - Análisis Técnico Rápido]
    • Valida estructura de URLs
    • Detecta patrones de phishing conocidos
    • Identifica contexto bancario + URL acortada (FLAG CRÍTICO)
    • Retorna: risk_level, confidence, is_scam
    ↓
[PASO 2: Inyección de Contexto]
    • Prepara reporte técnico del SVM
    • Inyecta análisis SVM en el prompt
    • Construye "prompt híbrido" para DeepSeek
    ↓
[PASO 3: DeepSeek como "Juez Final"]
    • Recibe: mensaje original + reporte técnico SVM
    • Aplica "REGLAS DE DECISIÓN" (ver abajo)
    • Retorna: veredicto final con 2 partes (resumen + detalles)
    ↓
[PASO 4: Respuesta al Usuario]
    • Envía resumen corto inmediatamente
    • Guarda detalles completos en BD
    • Cambia estado a ESPERANDO_MAS_DETALLES
    ↓
Usuario dice "SÍ" para ver detalles
    ↓
Envía análisis completo guardado
```

## 🎯 Reglas de Decisión (Lógica Híbrida)

El prompt de DeepSeek implementa estas reglas para combinar análisis técnico + humanístico:

### Regla 1: Confianza en Detección Técnica
```
Si SVM dice "RIESGO: CRÍTICO" o "RIESGO: ALTO"
    → Veredicto DEBE ser ESTAFA/PHISHING (a menos que sea claramente inofensivo)
```

**Por qué:** El SVM está entrenado para detectar patrones técnicos reales. Si reporta riesgo alto, es muy probable que sea estafa.

### Regla 2: Ingeniería Social Humana
```
Si SVM dice "RIESGO: BAJO" PERO DeepSeek detecta:
    • Urgencia extrema ("¡AHORA!", "Hoy mismo!")
    • Manipulación emocional ("ganaste", "premio")
    • Solicitud de información personal/financiera
    → Veredicto: SOSPECHOSO o ESTAFA
```

**Por qué:** Algunos textos de estafa son bien escritos y pueden pasar la detección técnica, pero el análisis humanístico los descubre.

### Regla 3: Alerta Crítica Absoluta
```
Si SVM detecta: "Contexto Bancario + URL Acortada"
    → Veredicto DEFINITIVAMENTE ESTAFA (sin excepciones)
```

**Por qué:** Esta es la técnica clásica de phishing:
- El usuario ve algo relacionado a su banco (crea legitimidad)
- Pero el enlace está acortado (oculta el destino real)
- Los bancos JAMÁS envían enlaces acortados

Ejemplo:
```
❌ "Hola, tu cuenta Nequi está bloqueada. 
Haz clic aquí para desbloquearla: bit.ly/actualizar-nequi"
```

## 📊 Implementación Técnica

### Archivo: `app/services/external_apis.py`

**Cambio:** Actualización del prompt "phishing"

```python
"phishing": {
    "system": (
        "Eres un experto analista de ciberseguridad (SecurityBot-WA). Tu trabajo es emitir un veredicto FINAL...\n"
        "Recibirás el mensaje del usuario Y un reporte técnico de un modelo local de IA (SVM).\n\n"
        "**LÓGICA HÍBRIDA (Reglas de Decisión):**\n"
        "1. Si el reporte SVM dice 'RIESGO: CRÍTICO' o 'RIESGO: ALTO', tu veredicto DEBE ser 'ESTAFA/PHISHING'...\n"
        # ... (más reglas)
    )
}
```

**Resultado:** DeepSeek ahora entiende que debe respetar los resultados técnicos pero también aplicar su juicio humanístico.

### Archivo: `app/services/conversation_flow.py`

**Cambio:** Nueva función `handle_analizar_mensaje` con 6 pasos

```python
async def handle_analizar_mensaje(telefono, mensaje, user_data, image_context=None):
    # PASO 1: Análisis técnico local (SVM)
    svm_result = svm_classifier.analyze_message(mensaje)
    
    # PASO 2: Construcción del prompt híbrido
    prompt_combinado = f"MENSAJE: {mensaje}\n\nREPORTE TÉCNICO (SVM): {detalles_tecnicos}"
    
    # PASO 3: Consulta a DeepSeek con reporte técnico
    analisis_completo = await analyze_with_deepseek(prompt_combinado, "phishing", user_profile)
    
    # PASO 4: Enviar resumen corto
    await send_whatsapp_message(telefono, resumen_breve)
    
    # PASO 5: Preguntar por detalles
    await send_whatsapp_message(telefono, "¿Quieres ver el análisis completo?")
    
    # PASO 6: Guardar estado y detalles
    db_update_user(telefono, {"estado": ESPERANDO_MAS_DETALLES, "last_analysis_details": detalles})
```

### Archivo: `app/main.py`

**Cambio:** Inicialización del SVM en startup

```python
from app.services.svm_classifier import initialize_svm

# En el bloque de inicialización:
print("🔄 Inicializando modelo SVM...")
if initialize_svm():
    print("✅ Modelo SVM listo")
else:
    print("⚠️ Modelo SVM no disponible, fallback a DeepSeek")
```

**Resultado:** El modelo SVM se carga una sola vez al iniciar la app, mejorando rendimiento.

## ⚡ Ventajas de la Arquitectura Híbrida

| Aspecto | SVM Local | DeepSeek API | Híbrido |
|--------|----------|-------------|---------|
| **Latencia** | 🟢 Ultra-rápido (<100ms) | 🟡 Lento (2-5s) | 🟢 Rápido (2-5s total) |
| **Detección Técnica** | 🟢 Excelente | 🟡 Buena | 🟢 Excelente |
| **Contexto Humano** | 🔴 No contextual | 🟢 Muy contextual | 🟢 Muy contextual |
| **Costo** | 🟢 Gratis (local) | 🔴 $ por API | 🟢 Optimizado (1 llamada) |
| **Explicabilidad** | 🔴 Caja negra | 🟢 Explica razonamiento | 🟢 Explica todo |
| **Robustez** | 🟡 Parámetros fijos | 🟡 Dependencia de API | 🟢 Redundancia SVM |

## 📈 Ejemplo de Análisis en Acción

### Mensaje de Entrada:
```
"¡ALERTA! Tu cuenta Nequi está bloqueada por seguridad.
Accede aquí AHORA para desbloquearla:
bit.ly/actualizar-nequi

¿Preguntas? Contacta: +57 3001234567"
```

### PASO 1: Análisis SVM
```
Detectado:
✓ Contexto bancario: "Nequi", "cuenta bloqueada"
✓ Urgencia: "¡ALERTA!", "AHORA"
✓ URL acortada: "bit.ly" (RIESGO CRÍTICO)
✓ Enlace sospechoso: No puedo verificar destino real

Resultado SVM:
🚨 ALERTA CRÍTICA: Contexto bancario + URL acortada
   Risk Level: CRÍTICO
   Confidence: 98%
   Is Scam: TRUE
```

### PASO 2: Prompt Híbrido a DeepSeek
```
MENSAJE A ANALIZAR:
"¡ALERTA! Tu cuenta Nequi está bloqueada..."

─────────────────────────────────────
📊 REPORTE TÉCNICO (SVM):
• Nivel de Riesgo: CRÍTICO
• Confianza: 98%
• Clasificación: PHISHING/ESTAFA DETECTADO
• Razón: Contexto bancario + URL acortada (técnica clásica)

🚨 ALERTA CRÍTICA: Los bancos JAMÁS envían enlaces acortados
─────────────────────────────────────

INSTRUCCIÓN: Actúa como juez final...
```

### PASO 3: Respuesta de DeepSeek

**Parte 1 (Resumen):**
```
🚨 *PHISHING CRÍTICO DETECTADO*

Este es un ataque de phishing clásico. 
El mensaje simula ser de Nequi pero usa una técnica antigua para ocultar el destino real del enlace.
```

**Parte 2 (Detalles):**
```
---DETALLES_SIGUEN---

📊 ANÁLISIS TÉCNICO:
El sistema local detectó múltiples banderas rojas:
• URLs acortadas (bit.ly, tinyurl, etc.) nunca son usadas por bancos legítimos
• Palabras de urgencia extrema ("ALERTA", "bloqueada", "AHORA")
• Solicitud de acción inmediata (patrón de ingeniería social)

🔍 ANÁLISIS HUMANÍSTICO:
El texto usa técnicas de manipulación:
• Crea alarma ("tu cuenta está bloqueada")
• Falsifica urgencia ("AHORA")
• Oculta el destino del enlace (acortador)

⚠️ RECOMENDACIONES:
1. NO hacer clic en el enlace
2. NO proporcionar información personal
3. Ir directamente a app.nequi.com (escribe la URL manualmente)
4. Reportar el número como spam
5. Si accediste, cambiar contraseña inmediatamente
```

### PASO 4: Respuesta al Usuario
```
🚨 *PHISHING CRÍTICO DETECTADO*
Este es un ataque de phishing clásico. 
El mensaje simula ser de Nequi pero usa una técnica antigua para ocultar el destino real del enlace.

📋 Tengo un informe técnico detallado explicando por qué llegamos a esta conclusión.
¿Quieres ver el **análisis completo**? (Responde SÍ o NO)
```

Si el usuario dice "SÍ", se envía el análisis completo de la Parte 2.

## 🔧 Configuración y Ajustes

### Si el modelo SVM no está disponible:
```python
# El sistema detecta automáticamente que no hay modelo y fallback a:
# 1. Usa solo DeepSeek (con reducción de funcionalidad)
# 2. Muestra advertencia en logs
# 3. Sigue funcionando normalmente
```

### Para entrenar un nuevo modelo SVM:
```bash
# Ver documentación en: app/services/svm_classifier.py
# Necesitas:
# - Dataset etiquetado (phishing/legítimo)
# - sklearn, pickle
# - ~5 minutos de entrenamiento

# El modelo se guarda en: models/svm_phishing_model.pkl
```

### Para ajustar sensibilidad:
```python
# En svm_classifier.py, función _compute_final_verdict()
# Modificar los thresholds:
if analysis['risk_score'] >= 70:  # <- Aumentar para menos falsos positivos
    risk_level = 'CRÍTICO'
```

## 📝 Logs y Debugging

El sistema registra información en diferentes niveles:

```
✅ Análisis híbrido completado para 573501234567
   SVM Veredicto: True (es estafa)
   Riesgo SVM: CRÍTICO

🔍 Ejecutando análisis SVM...
📊 URLs encontradas: 1
🚨 ALERTA CRÍTICA: Contexto bancario + URL acortada
```

## 🚀 Beneficios para el Usuario Final

1. **Más Precisión** - Combinación de dos enfoques reduce falsos positivos/negativos
2. **Explicaciones Claras** - El usuario entiende POR QUÉ es una estafa
3. **Respuestas Rápidas** - Veredicto inmediato + detalles bajo demanda
4. **Contexto Local** - Conoce bancos y servicios colombianos específicos

## 📞 Soporte Técnico

Si tienes dudas sobre el funcionamiento del sistema híbrido:

1. Revisa los logs de aplicación
2. Verifica que el modelo SVM esté en `models/svm_phishing_model.pkl`
3. Prueba manualmente: `python -c "from app.services.svm_classifier import quick_check; print(quick_check('mensaje'))"`

---

**Versión:** 1.0  
**Fecha:** Noviembre 2025  
**Desarrollado para:** SecurityBot-WA Colombia
