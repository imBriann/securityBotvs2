# 🤖 Sistema RLHF (Reinforcement Learning from Human Feedback)

## Descripción General

SecurityBot-WA implementa un sistema de **aprendizaje reforzado con retroalimentación humana** que permite que el bot mejore continuamente basado en la opinión de los usuarios, con **múltiples capas de seguridad** para evitar envenenamiento de datos (data poisoning).

**Principio Central:** El bot NUNCA se entrena automáticamente con feedback negativo. Solo aprende cuando:
1. ✅ El usuario confirma que el bot acertó (👍)
2. ✅ Un administrador revisa manualmente y valida un error
3. ✅ Hay suficientes datos confirmados para minimizar riesgo

---

## 1. Arquitectura del Sistema

```
┌──────────────────────────────────────────────────────────────┐
│                    USUARIO FINAL                             │
│           Envía mensaje → Bot analiza → Veredicto            │
│           User da 👍 o 👎 para feedback                       │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
          ┌────────────────────────────────────┐
          │    CAPTURA DE FEEDBACK (BD)        │
          │  app/storage/feedback_db.py        │
          │                                    │
          │ • log_interaction() - guarda       │
          │ • update_user_feedback() - captura│
          │ • get_data_for_retraining() - lee │
          └────────────────┬───────────────────┘
                           ↓
        ┌──────────────────────────────────────┐
        │   FILTRO DE SEGURIDAD (Defensa)      │
        │                                      │
        │ • Solo datos positivos o revisados   │
        │ • Excluye dislikes sin auditar       │
        │ • Detecta anomalías/patrones raros   │
        └────────────────┬─────────────────────┘
                         ↓
      ┌────────────────────────────────────────┐
      │   AUTO-MEJORA SEGURA (Trainer)         │
      │   app/services/trainer.py              │
      │                                        │
      │ • Análisis de calidad                  │
      │ • Generación de reportes               │
      │ • Reentrenamiento diferido             │
      └────────────────┬─────────────────────┘
                       ↓
       ┌───────────────────────────────────────┐
       │    COMANDOS ADMIN PARA AUDITORÍA      │
       │    app/services/admin_commands.py     │
       │                                       │
       │ /feedback_stats      → ver progreso   │
       │ /retrain_report      → análisis       │
       │ /review_negatives    → casos errores  │
       │ /do_retrain          → ejecutar       │
       └───────────────────────────────────────┘
```

---

## 2. Flujo de Feedback del Usuario

### Escenario: Usuario da feedback 👍/👎

```
PASO 1: Usuario recibe análisis del bot
   "🚨 PHISHING DETECTADO - No hagas clic"

PASO 2: Usuario responde con emoji
   Usuario: "👍"  (o "👎")
   
PASO 3: Sistema RLHF captura feedback
   update_user_feedback(phone, "POSITIVO")
   
PASO 4: Sistema guarda en BD
   analisis_logs.user_feedback = "POSITIVO"
   analisis_logs.feedback_timestamp = NOW()
   
PASO 5: Bot responde al usuario
   👍 → "¡Gracias! 🧠✅ Tu feedback me ayuda a mejorar."
   👎 → "Tomaré nota. Un humano revisará esto. 🧠⚠️"
   
PASO 6: Admin puede revisar después
   /review_negatives  →  Ver errores del bot
   /retrain_report    →  Analizar si se puede entrenar
```

---

## 3. Tabla de Base de Datos: `analisis_logs`

```sql
CREATE TABLE analisis_logs (
    id INTEGER PRIMARY KEY,                    -- Identificador único
    phone_number TEXT NOT NULL,                -- Teléfono del usuario
    message_content TEXT NOT NULL,             -- Mensaje analizado
    message_length INTEGER,                    -- Largo del mensaje
    svm_prediction TEXT,                       -- "phishing" o "legitimo"
    svm_confidence REAL,                       -- Confianza 0-1
    has_urls INTEGER,                          -- 1 si contiene URLs
    url_risk_levels TEXT,                      -- "dominio:ALTO,dominio:BAJO"
    deepseek_verdict TEXT,                     -- Análisis de DeepSeek
    final_verdict TEXT,                        -- Veredicto final (CRÍTICO/ALTO/BAJO)
    final_is_scam INTEGER,                     -- 1 si es estafa, 0 si legítimo
    
    -- FEEDBACK DEL USUARIO (Lo importante)
    user_feedback TEXT DEFAULT NULL,           -- "POSITIVO", "NEGATIVO", o NULL
    feedback_timestamp DATETIME DEFAULT NULL,  -- Cuándo dio feedback
    
    -- AUDITORÍA DEL ADMIN
    reviewed_by_admin INTEGER DEFAULT 0,       -- Admin lo validó manualmente
    admin_notes TEXT DEFAULT NULL,             -- Notas del admin
    
    -- TIMESTAMPS
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP  -- Cuándo se analizó
);
```

**Ejemplo de un registro:**

```
id: 1
phone_number: "573505894033"
message_content: "Tu cuenta Nequi está bloqueada verifica bit.ly/xyz"
final_verdict: "CRÍTICO"
final_is_scam: 1
user_feedback: "POSITIVO"  ← Usuario confirmó que fue correcto
feedback_timestamp: "2025-11-27 14:32:15"
reviewed_by_admin: 0
```

---

## 4. Funciones del Sistema

### 📝 `feedback_db.py` - Almacenamiento

| Función | Descripción | Uso |
|---------|-------------|-----|
| `init_feedback_db()` | Crea tabla si no existe | Al iniciar app |
| `log_interaction()` | Guarda un análisis completo | Después de cada análisis |
| `update_user_feedback()` | Registra feedback 👍/👎 | Cuando usuario responde |
| `get_feedback_stats()` | Estadísticas generales | Admin dashboard |
| `get_data_for_retraining()` | Extrae datos SEGUROS | Trainer (RLHF) |
| `get_unreviewed_negatives()` | Dislikes sin auditar | Admin review |
| `mark_as_reviewed()` | Admin valida un error | Admin audit |

### 🧠 `trainer.py` - Auto-Mejora Segura

| Función | Descripción | Protecciones |
|---------|-------------|--------------|
| `analyze_feedback_quality()` | Evalúa confiabilidad del feedback | Detecta data poisoning |
| `generate_retraining_report()` | Reporte exhaustivo | Múltiples validaciones |
| `prepare_retraining_data()` | Prepara textos + etiquetas | Solo datos positivos/validados |
| `simulate_retraining()` | Simula SIN modificar modelo | Validación previa |
| `execute_retraining()` | Entrena realmente | Requiere validaciones de seguridad |

### ⚙️ `admin_commands.py` - Interfaz Admin

| Comando | Efecto | Acceso |
|---------|--------|--------|
| `/feedback_stats` | Ver progreso de aprendizaje | Admin solo |
| `/retrain_report` | Reporte completo de reentrenamiento | Admin solo |
| `/review_negatives [N]` | Ver N últimos errores del bot | Admin solo |
| `/do_retrain` | Ejecutar reentrenamiento | Admin solo |

---

## 5. Flujo de Seguridad: Prevención de Data Poisoning

### Escenario Malicioso: Estafador quiere envenenar el modelo

```
┌─────────────────────────────────────────────────────────┐
│ ATAQUE: Estafador intenta engañar al bot               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Paso 1: Estafador envía un link real malicioso        │
│         "Click aquí: https://robo-banco.fake"          │
│                                                         │
│ Paso 2: Bot detecta correctamente: "🚨 PHISHING"      │
│                                                         │
│ Paso 3: Estafador responde: 👎 (dislike)             │
│         Intenta "entrenar" al bot a que es legítimo    │
│                                                         │
│ Paso 4: SISTEMA RLHF BLOQUEA                          │
│  ❌ "Dislike rechazado - solo usamos datos positivos  │
│      o validados manualmente por admin"                │
│                                                         │
│ Paso 5: Admin revisa después                          │
│  ✅ "/review_negatives" → Ve el error del estafador   │
│  ✅ Puede marcar como "VALIDADO" si era legítimo      │
│  ❌ O marcar como "RECHAZADO" si el bot tenía razón    │
│                                                         │
│ Resultado: 🛡️ Modelo NO se entrena con datos falsos   │
│            🛡️ Bot sigue siendo seguro                  │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Criterios de Entrenamiento

El sistema RLHF **SOLO** usa datos si cumplen:

```python
# Datos ACEPTADOS para entrenar:
✅ user_feedback = 'POSITIVO'              # Usuario confirmó acierto
✅ reviewed_by_admin = 1                   # Admin lo validó manualmente
✅ svm_confidence > 0.8                    # Confianza alta del SVM

# Datos RECHAZADOS:
❌ user_feedback = 'NEGATIVO' (sin auditar)  # Podría ser envenenamiento
❌ reviewed_by_admin = 0 (si negativo)       # No validado por humano
❌ Demasiados dislikes vs aciertos           # Señal de anomalía
```

---

## 7. Uso de Comandos Admin

### Comando 1: Ver Estadísticas de Feedback

```
Admin: /feedback_stats

Bot responde:
┌────────────────────────────────────┐
│ 🤖 RESUMEN DE REENTRENAMIENTO:     │
│                                    │
│ 📊 Estado:                         │
│  • Análisis realizados: 47         │
│  • Feedback recibido: 12           │
│  • Precisión: 91.7%                │
│                                    │
│ ⚠️ Seguridad:                       │
│  • Riesgo: BAJO                    │
│  • Dislikes sin revisar: 1         │
│                                    │
│ 🎯 Acción:                         │
│  ✅ Sistema listo para entrenar    │
└────────────────────────────────────┘
```

### Comando 2: Ver Reporte de Reentrenamiento

```
Admin: /retrain_report

Bot responde:
┌────────────────────────────────────┐
│ 📊 REPORTE DE REENTRENAMIENTO      │
│ Generado: 2025-11-27 14:32:15      │
│                                    │
│ 📈 ESTADÍSTICAS:                   │
│  • Total análisis: 47              │
│  • Feedback positivo: 11           │
│  • Feedback negativo: 1            │
│  • Cobertura: 25.5%                │
│  • Tasa de acierto: 91.7%          │
│  • Dislikes sin revisar: 1         │
│                                    │
│ 💾 DATOS DISPONIBLES:              │
│  • Total seguro: 11                │
│  • Estafas: 8 | Legítimos: 3       │
│  • Balance: 72.7% estafas          │
│                                    │
│ 🎯 ACCIÓN RECOMENDADA:             │
│  ✅ LISTO: Sistema seguro          │
└────────────────────────────────────┘
```

### Comando 3: Revisar Casos de Error

```
Admin: /review_negatives

Bot responde:
┌────────────────────────────────────┐
│ ⚠️ CASOS MARCADOS COMO INCORRECTOS  │
│ (Primeros 10)                      │
│                                    │
│ *Caso 1:*                          │
│  ID: 42                            │
│  Usuario: ···3033                  │
│  Veredicto Bot: LEGÍTIMO           │
│  Mensaje: "Revisa esto..."         │
│  Feedback: 2025-11-27 14:30:00     │
│                                    │
│ Revisa estos casos manualmente     │
│ y decide si el bot acertó.         │
└────────────────────────────────────┘
```

### Comando 4: Ejecutar Reentrenamiento

```
Admin: /do_retrain

Bot responde:
┌────────────────────────────────────┐
│ 🎯 REENTRENAMIENTO INICIADO        │
│                                    │
│ ✅ Sistema listo para aprender     │
│                                    │
│ 📝 Instrucciones para completar:   │
│ python -m app.scripts.retrain_svm  │
│                                    │
│ ⏰ Proceso: 1-5 minutos            │
└────────────────────────────────────┘
```

---

## 8. Flujo Completo: De Feedback a Mejora

```
Día 1: Usuario A da feedback
├─ Usuario A analiza phishing
├─ Bot dice: "ESTAFA"
├─ Usuario A responde: "👍" (acierto)
├─ Sistema guarda: feedback = "POSITIVO"

Día 2: Usuario B da feedback
├─ Usuario B analiza enlace educativo
├─ Bot dice: "CRÍTICO"
├─ Usuario B responde: "👎" (error)
├─ Sistema guarda: feedback = "NEGATIVO", reviewed_by_admin = 0
└─ NO se usa para entrenar (aún)

Día 3: Admin revisa
├─ Admin: /review_negatives
├─ Admin ve: "Universidad link → Bot lo marcó como CRÍTICO"
├─ Admin: /mark_reviewed 2 VALIDADO
│  (Log ID 2 fue un error real del bot)
├─ Sistema actualiza: reviewed_by_admin = 1
└─ Ahora SÍ se puede usar para entrenar

Día 5: Reentrenamiento
├─ Admin: /retrain_report
├─ Sistema: "✅ 15 datos seguros, 91% precisión, LISTO"
├─ Admin: /do_retrain
├─ Sistema prepara datos:
│  - Positivos (aciertos confirmados): 12
│  - Negativos (validados): 3
│  - Total: 15 ejemplos de entrenamiento
├─ Admin: python -m app.scripts.retrain_svm
└─ ✅ Modelo mejorado con nuevo conocimiento

Resultado Final:
✅ Bot aprende de sus errores
✅ Pero SOLO de errores auditados manualmente
✅ Usuarios no pueden envenenar el modelo
✅ Transparencia total: Admin controla el proceso
```

---

## 9. Métricas de Éxito

| Métrica | Descripción | Meta |
|---------|-------------|------|
| **Precisión** | % de aciertos vs errores | > 90% |
| **Cobertura de Feedback** | % mensajes con feedback | > 30% |
| **Data Poisoning** | Intentos bloqueados | 0 (100%) |
| **Tiempo de Auditoría** | Minutos desde error a revisión | < 24 horas |
| **Mejora Post-Entrenamiento** | Aumento de precisión | +5% por ciclo |

---

## 10. Casos de Uso por Tipo de Usuario

### 👨‍💼 Administrador
```
Día 1: /feedback_stats → Revisar progreso
Día 2: /review_negatives → Auditar errores  
Día 3: /retrain_report → Análisis completo
Día 4: /do_retrain → Entrenar modelo mejorado
```

### 👤 Usuario Final
```
1. Envía mensaje para analizar
2. Recibe veredicto del bot
3. Da feedback: "👍" (acertaste) o "👎" (te equivocaste)
4. Recibe confirmación
5. (Invisible para usuario) Sistema aprende
```

### 🤖 Bot
```
1. Analiza mensaje (SVM + DeepSeek)
2. Emite veredicto
3. Espera feedback
4. Registra análisis + feedback en BD
5. (Periódicamente) Sistema mejora basado en aciertos auditados
```

---

## 11. Ventajas vs Desventajas

| Ventaja | Beneficio |
|---------|-----------|
| 🛡️ **Seguridad máxima** | No hay data poisoning |
| 📈 **Mejora continua** | Bot aprende de aciertos |
| 🤝 **Interacción usuario** | Usuarios sienten que participan |
| 📊 **Transparencia** | Admin audita cada paso |
| ⚡ **Rápido** | Feedback en tiempo real |

| Desventaja | Mitigación |
|------------|-----------|
| ⏳ **Lento** (requiere auditoría) | Vale la pena para seguridad |
| 💻 **Requiere admin manual** | Herramientas automatizan detección |
| 📉 **Menos aprendizaje** | Mejor calidad > cantidad |

---

## 12. Próximas Mejoras Posibles

```
Fase 1 (Actual): ✅
• Captura manual de feedback (👍/👎)
• Almacenamiento en BD
• Reporte para admin
• Reentrenamiento semi-automático

Fase 2 (Futuro):
• Detección automática de anomalías
• Scoring de confianza por usuario
• A/B testing con versiones del modelo
• Reentrenamiento completamente automático
  (después de validaciones de seguridad)

Fase 3 (Advanced):
• Federated learning (entrenar en múltiples bots)
• Active learning (preguntar feedback en casos inciertos)
• Interpretability (explicar por qué el bot aprende X)
```

---

## Resumen Ejecutivo

🎯 **SecurityBot-WA ahora puede APRENDER de sus interacciones, pero de forma SEGURA:**

✅ Los usuarios dan feedback directo (👍/👎)
✅ Sistema registra CADA análisis en BD
✅ Admin audita errores manualmente
✅ Bot se entrena SOLO con datos validados
✅ Imposible envenenar el modelo con ataques

**Resultado:** Un bot que mejora continuamente mientras mantiene máxima seguridad. 🛡️🤖

