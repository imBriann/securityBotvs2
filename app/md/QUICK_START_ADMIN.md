# 🚀 QUICK START - SISTEMA DE REVISIÓN INTERACTIVA

## Para Administradores

### ¿Qué es?
Sistema que permite revisar casos de seguridad uno-por-uno vía WhatsApp, validando si el bot acertó o se equivocó.

### ¿Cómo usar?

#### Paso 1: Iniciar revisión
```
Escribe en WhatsApp: /revisar

Bot responde:
🕵️‍♂️ CASO DE REVISIÓN #1
(1 de ~3)

👤 Usuario: XXXX****XXXX
💬 Mensaje: "Haz clic aquí"
🤖 Veredicto del bot: CRÍTICO
😞 Usuario opinó: El bot se equivocó

¿El bot realmente se equivocó?
• SI - Bot estaba equivocado
• NO - Bot estaba correcto
• SALIR - Finalizar revisión
```

#### Paso 2: Responder SI/NO
```
Escribe: SI        (el bot se equivocó)
o
Escribe: NO        (el bot acertó)

Bot guarda tu decisión y presenta siguiente caso
(automático)
```

#### Paso 3: Repetir
```
Para cada caso adicional:
Escribe: SI o NO

Bot avanza automáticamente:
(2 de ~3) → presenta caso 2
(3 de ~3) → presenta caso 3
```

#### Paso 4: Finalizar
```
Después del último caso, bot confirma:

🎉 ¡Excelente! Has completado la revisión 
de todos los casos pendientes.

📊 Decisión guardada: [tu último veredicto]

Volviendo al estado normal. ¿En qué 
puedo ayudarte?
```

---

## 📝 Respuestas Válidas

### Para "Bot estaba equivocado"
```
Escribe cualquiera de estos:
• SI
• SÍ (con acento)
• BIEN
• CORRECTO
• OK
```

### Para "Bot estaba correcto"
```
Escribe cualquiera de estos:
• NO
• MAL
• INCORRECTO
• ERROR
```

### Para Salir en Cualquier Momento
```
Escribe:
• SALIR
• CANCELAR
• TERMINADO

Bot finalizará inmediatamente sin revisar 
más casos
```

---

## ⚡ Atajos Útiles

### Ver comandos disponibles
```
/help
```

### Ver estadísticas de feedback
```
/feedback_stats
```

### Ver reporte de reentrenamiento
```
/retrain_report
```

### Listar casos negativos pendientes
```
/review_negatives
```

### Ejecutar reentrenamiento
```
/do_retrain
```

---

## 🎯 Casos de Uso

### Caso 1: Revisar 5 casos rápidamente
```
/revisar
SI          ← (caso 1 guardado, avanza)
NO          ← (caso 2 guardado, avanza)
SI          ← (caso 3 guardado, avanza)
BIEN        ← (caso 4 guardado, avanza)
CORRECTO    ← (caso 5 guardado, finaliza)
🎉 Listo!
```

### Caso 2: Solo revisar 2 casos y salir
```
/revisar
SI          ← (caso 1 guardado)
NO          ← (caso 2 guardado)
SALIR       ← (finaliza sin revisar más)
✋ Revisión finalizada
```

### Caso 3: No hay casos pendientes
```
/revisar
ℹ️ No hay reportes pendientes. Todos están 
validados. ✅
```

### Caso 4: Escupo respuesta inválida
```
/revisar
[presenta caso 1]
HOLA        ← (respuesta inválida)
❓ No entendí tu respuesta. Por favor responde con:
• SÍ (bot estaba equivocado)
• NO (bot estaba correcto)
• SALIR (finalizar revisión)
```

---

## 🔍 Preguntas Frecuentes

### P: ¿Qué pasa si no hay casos para revisar?
R: Bot responde "No hay reportes pendientes". Todos están validados.

### P: ¿Puedo salir en medio de la revisión?
R: Sí, escribe "SALIR" en cualquier momento. Los casos pendientes quedarán para revisar después.

### P: ¿Se guardan mis decisiones?
R: Sí, cada vez que respondes SI/NO, tu decisión se guarda automáticamente.

### P: ¿Puedo revisar casos en otro momento?
R: Sí, cuando quieras vuelves a escribir `/revisar` y continúas con los pendientes.

### P: ¿Mi decisión afecta el modelo?
R: Sí, tus validaciones ayudan a entrenar el modelo para mejorar.

### P: ¿Qué diferencia hay entre SI y NO?
- **SI**: El bot se equivocó (veredicto fue incorrecto)
- **NO**: El bot acertó (veredicto fue correcto)

### P: ¿Hay límite de casos?
R: No, puedes revisar tantos como necesites.

### P: ¿Se puede revisar el mismo caso dos veces?
R: No, una vez revisado no vuelve a aparecer.

---

## 🛠️ Troubleshooting

### Problema: "No tengo registro del caso"
**Solución:** Escribe `/revisar` de nuevo para reiniciar

### Problema: Respuesta inválida se rechaza
**Solución:** Verifica escribiste SI, NO o SALIR (sensible a tildes)

### Problema: No veo el siguiente caso
**Solución:** Espera 2 segundos, bot lo está preparando

### Problema: Bot no responde
**Solución:** Verifica conexión a Internet y reintenta

---

## 📊 Ejemplo de Sesión Completa

```
┌─────────────────────────────────────────┐
│ Admin                    Bot             │
├─────────────────────────────────────────┤
│ /revisar                                 │
│                    🕵️‍♂️ CASO 1/3        
│                    [detalles]            
│ SI                                      │
│                    ✅ Guardado          
│                    🕵️‍♂️ CASO 2/3        
│                    [detalles]            
│ NO                                      │
│                    ✅ Guardado          
│                    🕵️‍♂️ CASO 3/3        
│                    [detalles]            
│ CORRECTO                                │
│                    🎉 Completado!       
└─────────────────────────────────────────┘

Tiempo total: ~2 minutos para 3 casos
```

---

## 💡 Consejos

1. **Sé consistente:** Usa las mismas palabras cada vez (SI/NO)

2. **Rápido pero cuidadoso:** Lee el mensaje antes de responder

3. **Revisa en lotes:** Es más eficiente revisar 5+ casos de una vez

4. **Verifica patrones:** Busca patrones de error para entrenar mejor

5. **Usa en horas bajas:** Cuando tengas tiempo para concentrarte

---

## 📋 Checklist Antes de Empezar

```
□ Eres administrador autorizado
□ Tienes acceso a WhatsApp del bot
□ Hay casos pendientes (/review_negatives)
□ Tienes tiempo disponible (5+ minutos)
□ Conexión a Internet estable
```

---

## 🎓 Casos de Aprendizaje

### Para Entrenar Bien el Modelo

Cuando revises, aprenderás qué casos son realmente:

```
VEREDICTO: CRÍTICO (Phishing)
Respuestas:
- SI → Bot acertó bien (es phishing realmente)
- NO → Bot fue conservador, no era phishing

VEREDICTO: SOSPECHOSO (Malware)
Respuestas:
- SI → Bot detectó bien
- NO → Falsa alarma

VEREDICTO: SEGURO (Legítimo)
Respuestas:
- SI → Error: era phishing pero pasó
- NO → Bot acertó (es seguro realmente)
```

---

## 🔐 Seguridad

- ✅ Solo admins pueden revisar
- ✅ Tus decisiones se validan automáticamente
- ✅ Los datos se almacenan de forma segura
- ✅ El modelo se mejora gradualmente

---

## 📞 Soporte

Si encuentras problemas:

1. Verifica que escribes SI/NO/SALIR
2. Usa `/revisar` para reiniciar
3. Consulta `/help` para comandos

---

**¿Listo? Escribe `/revisar` y comienza! 🚀**
