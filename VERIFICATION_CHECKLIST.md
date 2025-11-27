# ✅ CHECKLIST DE VERIFICACIÓN - SISTEMA DE REVISIÓN INTERACTIVA

## Verificación Pre-Producción

### Fase 1: Archivos Modificados
```
□ app/utils/config.py
  ├─ □ ESTADO_ADMIN_REVISANDO = 99 existe
  └─ Verificar: from app.utils.config import ESTADO_ADMIN_REVISANDO

□ app/storage/feedback_db.py
  ├─ □ get_next_pending_negative_review() definida
  ├─ □ mark_admin_decision() definida
  ├─ □ count_pending_reviews() definida
  └─ Verificar: from app.storage.feedback_db import [funciones]

□ app/services/admin_commands.py
  ├─ □ execute_start_review_command() definida
  ├─ □ "/revisar" en commands_map
  ├─ □ Imports de feedback_db
  ├─ □ Imports de config (ESTADO_ADMIN_REVISANDO, ESTADO_REGISTRADO)
  └─ Verificar: imports en línea 1-20

□ app/services/conversation_flow.py
  ├─ □ Interceptor de ESTADO_ADMIN_REVISANDO presente
  ├─ □ handle_admin_review_flow() definida
  ├─ □ Imports de feedback_db actualizados
  ├─ □ Import de ESTADO_ADMIN_REVISANDO
  └─ Verificar: estado interception antes de otros routers
```

### Fase 2: Validación Sintáctica
```
□ conversation_flow.py → No tiene errores (get_errors)
□ admin_commands.py → No tiene errores (get_errors)
□ feedback_db.py → No tiene errores (get_errors)
□ config.py → No tiene errores (get_errors)
□ Todos los imports resueltos → No "undefined" en IDE
```

### Fase 3: Funcionalidad Core
```
□ Test 1: Comando /revisar funciona
  ├─ Admin escribe /revisar
  ├─ Sistema responde con primer caso
  └─ Verifica: CASO DE REVISIÓN #1 en mensaje

□ Test 2: Parse de decisiones
  ├─ Admin responde SI → marca bot_was_wrong=True
  ├─ Admin responde NO → marca bot_was_wrong=False
  ├─ Admin responde SÍ → reconoce acentuado
  └─ Admin responde inválida → pide clarificación

□ Test 3: Avance de casos
  ├─ Después de SI/NO → presenta siguiente caso
  ├─ Muestra progreso: (2 de 3)
  └─ Contador aumenta correctamente

□ Test 4: Finalización
  ├─ Último caso + respuesta → mensaje 🎉
  ├─ Admin vuelve a ESTADO_REGISTRADO
  └─ last_analyzed_url se limpia

□ Test 5: SALIR en cualquier momento
  ├─ Admin puede escribir SALIR
  ├─ Finaliza revisión inmediatamente
  └─ Estado vuelve a REGISTRADO
```

### Fase 4: Base de Datos
```
□ Tabla analisis_logs tiene campos:
  ├─ reviewed_by_admin (BOOLEAN)
  ├─ admin_notes (TEXT)
  └─ Verificar: SELECT * FROM analisis_logs LIMIT 1

□ Datos se guardan correctamente:
  ├─ mark_admin_decision(1, True) actualiza reviewed_by_admin
  ├─ admin_notes contiene "Bot equivocado" o "Bot correcto"
  └─ Timestamp se actualiza

□ Funciones de consulta:
  ├─ get_next_pending_negative_review() retorna Row o None
  ├─ count_pending_reviews() retorna entero >= 0
  └─ Datos están en orden correcto
```

### Fase 5: Seguridad
```
□ Solo admins pueden usar /revisar
  ├─ Verificar: is_admin(telefono) en execute_start_review_command
  └─ Usuario no-admin → "❌ No autorizado"

□ Validación de caso_id
  ├─ Si case_id es NULL → retorna error
  └─ Reinicia estado limpiamente

□ Manejo de excepciones
  ├─ Try/catch en handle_admin_review_flow
  ├─ Errores se loguean a console
  └─ Estado se resetea automáticamente
```

### Fase 6: Mensajes y UX
```
□ Mensaje de iniciación:
  ├─ Emojis presentes (🕵️‍♂️, 💬, 🤖, 😞)
  ├─ Formato: CASO #ID (N de M)
  ├─ Opciones claras: SI / NO / SALIR
  └─ Detalles del usuario (phone masked)

□ Mensaje de progreso:
  ├─ Avanza a caso siguiente
  ├─ Contador correcto (N de M)
  └─ Emojis consistentes

□ Mensaje de finalización:
  ├─ Contiene 🎉 emoji
  ├─ Incluye decisión guardada
  └─ Invita a flujo normal

□ Mensaje de salida:
  ├─ Confirma "Revisión finalizada"
  └─ Retorna a estado normal
```

### Fase 7: Estado Machine
```
□ Usuario registrado:
  ├─ estado = 4 (ESTADO_REGISTRADO)
  ├─ last_analyzed_url = NULL
  └─ Comportamiento: flujo normal

□ Admin ejecuta /revisar:
  ├─ estado → 99 (ESTADO_ADMIN_REVISANDO)
  ├─ last_analyzed_url → "1" (primer caso)
  └─ Comportamiento: interceptado en handle_user_message

□ Admin responde SI/NO:
  ├─ decision guardada en BD
  ├─ estado sigue siendo 99
  ├─ last_analyzed_url → "2" (siguiente caso)
  └─ Comportamiento: loop continúa

□ Último caso + respuesta:
  ├─ decision guardada en BD
  ├─ next_case = NULL
  ├─ estado → 4 (ESTADO_REGISTRADO)
  ├─ last_analyzed_url → NULL
  └─ Comportamiento: retorna a normal

□ Admin escribe SALIR:
  ├─ estado → 4 (ESTADO_REGISTRADO)
  ├─ last_analyzed_url → NULL
  └─ Comportamiento: retorna a normal (sin guardar última decisión)
```

### Fase 8: Integración
```
□ Webhooks funcionan:
  ├─ Mensajes normales siguen llegando
  ├─ Mensajes en revisión se interceptan
  └─ No hay conflictos con otros handlers

□ Otros comandos admin funcionan:
  ├─ /help muestra /revisar
  ├─ /feedback_stats sigue disponible
  ├─ /retrain_report sigue disponible
  └─ /do_retrain sigue disponible

□ Flujo usuario normal no afectado:
  ├─ Usuarios no-admin pueden enviar mensajes
  ├─ Reciben análisis normales
  ├─ Pueden dar feedback 👍/👎
  └─ Su estado no cambia
```

---

## Prueba de Aceptación Final

### Test End-to-End: Revisión de 3 Casos

```
PRE: Hay 3+ casos con feedback negativo (reviewed_by_admin = False)

PASO 1: Admin inicia revisión
  Escribe:  /revisar
  Espera:   Mensaje con "CASO DE REVISIÓN #1" (1 de ~3)
  ✓ PASS / ✗ FAIL

PASO 2: Admin responde SI al primer caso
  Escribe:  SI
  Espera:   "Bot guardada" + "CASO DE REVISIÓN #2" (2 de ~3)
  ✓ PASS / ✗ FAIL

PASO 3: Admin responde NO al segundo caso
  Escribe:  NO
  Espera:   "Decisión guardada" + "CASO DE REVISIÓN #3" (3 de ~3)
  ✓ PASS / ✗ FAIL

PASO 4: Admin responde SÍ (acentuado) al tercer caso
  Escribe:  SÍ
  Espera:   "🎉 ¡Excelente! Has completado"
  ✓ PASS / ✗ FAIL

PASO 5: Admin vuelve a flujo normal
  Escribe:  Hola bot
  Espera:   Respuesta normal (sin presentar casos)
  ✓ PASS / ✗ FAIL

RESULTADO: ___/5 PASOS COMPLETADOS
```

### Test de Manejo de Errores

```
TEST 1: Respuesta inválida
  Escribe:  HOLAAAA
  Espera:   "No entendí tu respuesta..." (pide clarificación)
  ✓ PASS / ✗ FAIL

TEST 2: SALIR en medio de revisión
  Escribe:  SALIR
  Espera:   "Revisión finalizada" (no procesa más casos)
  ✓ PASS / ✗ FAIL

TEST 3: Sin casos pendientes
  Setup:    Todos los casos ya están reviewed_by_admin = True
  Escribe:  /revisar
  Espera:   "No hay reportes pendientes"
  ✓ PASS / ✗ FAIL

TEST 4: Acceso no autorizado
  Setup:    Usuario no-admin
  Escribe:  /revisar
  Espera:   "❌ No autorizado" o comando ignorado
  ✓ PASS / ✗ FAIL

RESULTADO: ___/4 TESTS COMPLETADOS
```

---

## Verificación de Logs

### Console Output Esperado

```
✓ Cuando admin ejecuta /revisar:
  DEBUG: Handler para +569XXXXXXXX, Estado: 4
  DEBUG: Detectado posible comando admin: /revisar
  ✅ Comando admin ejecutado para +569XXXXXXXX

✓ Cuando admin responde SI:
  DEBUG: Handler para +569XXXXXXXX, Estado: 99
  ✅ Decisión guardada para caso 1: bot_was_wrong=True

✓ Cuando admin escribe SALIR:
  DEBUG: Revisión finalizada. Volviendo a ESTADO_REGISTRADO

✓ Si hay error:
  ❌ Error en handle_admin_review_flow: [error details]
```

---

## Sign-Off

```
Verificador: ___________________
Fecha: ___________________
Versión: 1.0 (RLHF + Interactive Review)

Resultado General: □ APROBADO  □ REQUIERE AJUSTES

Notas:
_________________________________________________
_________________________________________________
_________________________________________________

Listo para Producción: □ SÍ  □ NO

Próxima Revisión: ___________________
```

---

## Documentos de Referencia

- `IMPLEMENTATION_COMPLETE.md` - Estado final de implementación
- `INTERACTIVE_REVIEW_FLOW.md` - Flujo detallado
- `RLHF_SYSTEM_COMPLETE.md` - Sistema RLHF completo
- `test_interactive_review.py` - Suite de tests automatizados

---

**Este checklist debe completarse antes de deployar a producción.**
