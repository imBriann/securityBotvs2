# 🧠 RLHF System - Documentación Completa

## Visión General

Sistema de retroalimentación humana reforzada (RLHF) completo que permite:
1. ✅ Captura automática de feedback del usuario (+👍/-👎)
2. ✅ Almacenamiento seguro en base de datos
3. ✅ Revisión manual por administrador (caso-por-caso)
4. ✅ Protección contra envenenamiento de datos
5. ✅ Auto-mejora del modelo con validación multi-capa

## Componentes del Sistema

### 1. Captura de Feedback (Users)
**Ubicación:** `conversation_flow.py` línea ~60

Usuarios pueden enviar:
- 👍 = Feedback POSITIVO (bot acertó)
- 👎 = Feedback NEGATIVO (bot falló)

```python
if message_type == "text" and text_recibido_original in ["👍", "👎"]:
    feedback_tipo = "POSITIVO" if text_recibido_original == "👍" else "NEGATIVO"
    update_user_feedback(telefono_remitente, feedback_tipo)
```

### 2. Almacenamiento Seguro (Database)
**Archivo:** `feedback_db.py` (220 líneas)

#### Tabla: `analisis_logs`
```sql
CREATE TABLE analisis_logs (
    id INTEGER PRIMARY KEY,
    user_phone TEXT,
    original_user_message TEXT,
    detected_threats TEXT,
    svm_score REAL,
    svm_verdict TEXT,
    deepseek_analysis TEXT,
    deepseek_verdict TEXT,
    final_verdict TEXT,
    feedback_tipo TEXT,  -- POSITIVO, NEGATIVO, NULL
    reviewed_by_admin BOOLEAN,
    admin_notes TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

#### Tabla: `feedback_stats`
```sql
CREATE TABLE feedback_stats (
    id INTEGER PRIMARY KEY,
    user_phone TEXT UNIQUE,
    total_positivos INTEGER DEFAULT 0,
    total_negativos INTEGER DEFAULT 0,
    total_feedback INTEGER DEFAULT 0,
    last_feedback_at TIMESTAMP
)
```

### 3. Revisión Interactiva (Admin)
**Comando:** `/revisar`  
**Ubicación:** `admin_commands.py` + `conversation_flow.py`

**Flujo:**
```
Admin: /revisar
  → Obtiene primer caso negativo no revisado
  → Cambia a ESTADO_ADMIN_REVISANDO
  → Presenta caso con SI/NO/SALIR

Admin: SI/NO
  → Guarda decisión (mark_admin_decision)
  → Obtiene siguiente caso
  → Repite o finaliza

Admin: SALIR
  → Finaliza revisión
  → Vuelve a ESTADO_REGISTRADO
```

### 4. Protección Contra Envenenamiento
**Validación Multi-Capa:**

1. **Tier 1:** Solo acepta feedback de NEGATIVOS revisados manualmente
2. **Tier 2:** Análisis de calidad de datos (detector de anomalías)
3. **Tier 3:** Validación antes de reentrenamiento

**Código en `trainer.py`:**
```python
def analyze_feedback_quality():
    # Detecta patrones sospechosos
    # Rechaza datos contaminados
    # Valida distribución de clases
```

### 5. Auto-Mejora del Modelo
**Archivo:** `trainer.py` (280 líneas)

**Comandos Admin:**
- `/feedback_stats` → Muestra estadísticas de feedback
- `/retrain_report` → Genera reporte de reentrenamiento
- `/review_negatives` → Lista casos negativos
- `/do_retrain` → Ejecuta reentrenamiento (con validaciones)

**Flujo de Reentrenamiento:**
```
/do_retrain
  ↓
Analiza calidad de datos → analyze_feedback_quality()
  ├─ Si calidad baja: rechaza
  └─ Si calidad OK: continúa
  ↓
Prepara datos seguros → prepare_retraining_data()
  ├─ Solo POSITIVOS confirmados
  └─ Solo NEGATIVOS revisados + bot_was_wrong=True
  ↓
Simula reentrenamiento → simulate_retraining()
  ├─ Valida accuracy no baja
  └─ Valida precision/recall estables
  ↓
Ejecuta reentrenamiento → execute_retraining()
  └─ Actualiza modelo SVM localmente
  ↓
Genera reporte → generate_retraining_report()
```

## Flujos de Uso

### Caso A: Usuario da Feedback POSITIVO
```
1. Bot analiza mensaje → veredicto: "SEGURO"
2. Usuario reacciona: 👍
3. Sistema:
   - Guarda en analisis_logs feedback_tipo='POSITIVO'
   - Actualiza feedback_stats total_positivos++
   - Envía: "¡Gracias! Me ayudas a saber que acerté"
```

### Caso B: Usuario da Feedback NEGATIVO
```
1. Bot analiza mensaje → veredicto: "CRÍTICO"
2. Usuario reacciona: 👎
3. Sistema:
   - Guarda en analisis_logs feedback_tipo='NEGATIVO'
   - Actualiza feedback_stats total_negativos++
   - Envía: "Un humano revisará este caso"
   - MARCA reviewed_by_admin = False (requiere admin)
```

### Caso C: Admin Revisa Casos
```
1. Admin: /revisar
2. Sistema presenta: "¿El bot realmente se equivocó?"
3. Admin: SI (bot estaba equivocado)
4. Sistema:
   - Marca reviewed_by_admin = True
   - Guarda admin_notes = "Bot equivocado"
   - Presenta siguiente caso
5. Repite hasta terminar o SALIR
```

### Caso D: Admin Reentrena Modelo
```
1. Admin: /do_retrain
2. Sistema:
   - Analiza calidad datos:
     * Verifica no hay patrones anómalos
     * Cuenta POSITIVOS vs NEGATIVOS
   - Simula reentrenamiento:
     * Valida accuracy mejora
     * Verifica robustez
   - Ejecuta reentrenamiento:
     * Retrain SVM con datos seguros
     * Actualiza modelo.pkl
   - Genera reporte con métricas
```

## Funciones Clave

### feedback_db.py
```python
log_interaction(data)              # Guarda análisis completo
update_user_feedback(phone, tipo)  # Captura 👍/👎
mark_admin_decision(id, bool)      # Admin valida caso
get_next_pending_negative_review() # Obtiene caso para revisar
count_pending_reviews()            # Cuenta casos pendientes
```

### trainer.py
```python
analyze_feedback_quality()         # Detecta datos malos
generate_retraining_report()       # Crea reporte
prepare_retraining_data()          # Filtra datos seguros
execute_retraining()               # Reentrena modelo
```

### admin_commands.py
```python
/revisar                    # Inicia modo revisión interactiva
/feedback_stats             # Muestra estadísticas
/retrain_report             # Genera reporte
/review_negatives           # Lista negativos pendientes
/do_retrain                 # Ejecuta reentrenamiento
```

## Seguridad

### 1. Control de Acceso
- Solo admins pueden usar comandos RLHF
- Verificación `is_admin(telefono)` en cada comando

### 2. Validación de Datos
- Todos los inputs normalizados
- Queries parametrizadas (previene SQL injection)
- Try/catch en funciones críticas

### 3. Prevención de Envenenamiento
- Feedback NEGATIVO requiere revisión admin manual
- Análisis de calidad detects outliers
- Validación de accuracy antes de usar datos

### 4. Auditoría
- Todos los cambios logged en console
- admin_notes guarda quién y cuándo
- Timestamps en todas las operaciones

## Estados de Usuario

```
Nuevo Usuario
  ↓
ESTADO_PENDIENTE_TERMINOS (0)
  ↓
ESTADO_PENDIENTE_NOMBRE (1)
  ↓
ESTADO_PENDIENTE_EDAD (2)
  ↓
ESTADO_PENDIENTE_CONOCIMIENTO (3)
  ↓
ESTADO_REGISTRADO (4) ← Usuario normal
  ├─ Envía mensajes a analizar
  ├─ Recibe veredicto
  └─ Puede dar feedback 👍/👎
  
Si es admin en ESTADO_REGISTRADO:
  ↓
/revisar
  ↓
ESTADO_ADMIN_REVISANDO (99)
  ├─ Revisa casos negativos
  ├─ Responde SI/NO a cada caso
  └─ Loop hasta terminar o SALIR
  ↓
Vuelve a ESTADO_REGISTRADO
```

## Estadísticas e Informes

### Estadísticas Disponibles (/feedback_stats)
```
📊 Estadísticas de Feedback Global:

USUARIO: +56987654321
- Feedback Positivo: 15
- Feedback Negativo: 3
- Total: 18
- Tasa de Confianza: 83.3%

CASOS PENDIENTES DE REVISIÓN: 7
```

### Reporte de Reentrenamiento (/retrain_report)
```
🔄 Reporte de Reentrenamiento

Datos Disponibles:
- Feedback POSITIVO confirmado: 45
- Feedback NEGATIVO validado: 8
- Total seguro para retrain: 53

Calidad de Datos:
- Riesgo de envenenamiento: BAJO
- Anomalías detectadas: 0
- Distribución de clases: BALANCEADA ✅

Simulación de Reentrenamiento:
- Accuracy esperado: 94.2%
- Cambio respecto actual: +1.8%
- Estabilidad: ROBUSTA ✅
```

## Validación del Sistema

✅ **Imports Validados:** Todos resueltos  
✅ **Errores Sintácticos:** 0 en todos los archivos  
✅ **Funciones Principales:** 11 implementadas  
✅ **Base de Datos:** 2 tablas + funciones  
✅ **Admin Commands:** 5 comandos RLHF  
✅ **Flujo Interactivo:** Completo  
✅ **Seguridad:** Multi-capa  

## Archivos del Sistema

```
📁 app/
├── 📁 services/
│   ├── 📄 conversation_flow.py      (Handle RLHF feedback + interactive review)
│   ├── 📄 admin_commands.py         (RLHF commands interface)
│   ├── 📄 external_apis.py          (DeepSeek analysis)
│   └── 📄 svm_classifier.py         (ML detection)
├── 📁 storage/
│   ├── 📄 users_state.py            (User state management)
│   └── 📄 feedback_db.py            (NEW: RLHF database)
├── 📁 utils/
│   ├── 📄 config.py                 (States + ESTADO_ADMIN_REVISANDO)
│   └── 📄 preprocessing.py          (Text normalization)
├── 📄 main.py                       (FastAPI entry)
└── 📁 api/
    └── 📄 whatsapp_webhook.py       (Webhook handler)

📁 RLHF Documentation/
├── 📄 RLHF_SYSTEM.md                (Visión general)
├── 📄 RLHF_IMPLEMENTATION.md        (Detalles implementación)
├── 📄 RLHF_COMPLETE.md              (Status completo)
├── 📄 INTERACTIVE_REVIEW_FLOW.md    (Flujo interactivo)
└── 📄 RLHF_SYSTEM.md                (Este archivo)
```

## Próximos Pasos (Opcional)

1. **Métricas Dashboard:** Crear visualización web de estadísticas
2. **Auto-Retrain Scheduler:** Ejecutar reentrenamiento automático cada N días
3. **Feedback Gamification:** Rewards para usuarios con feedback consistente
4. **A/B Testing:** Comparar veredictos bot vs admin

## Status Final: ✅ COMPLETAMENTE IMPLEMENTADO

Sistema RLHF listo para:
- ✅ Capturar feedback en tiempo real
- ✅ Revisar casos interactivamente
- ✅ Proteger contra envenenamiento de datos
- ✅ Auto-mejorar modelo con validaciones
- ✅ Mantener auditoría completa
