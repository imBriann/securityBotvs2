# 🚨 Guía de Troubleshooting - Cloud Run Deployment

## Error: "Container failed to start and listen on the port"

Este error ocurre cuando el contenedor no puede iniciar o escuchar en el puerto correcto.

### ✅ **Soluciones Implementadas:**

1. **✅ Mejor logging en `main.py`** - Ahora verás exactamente qué variable falta
2. **✅ Validación mejorada** - No hace exit si solo falta ADMIN_PHONE_NUMBER
3. **✅ Manejo robusto de errores** - La BD y SVM no bloquean el inicio
4. **✅ Puerto dinámico** - Lee PORT correctamente de Cloud Run

---

## 🔍 **Paso 1: Verificar las Variables de Entorno en Cloud Run**

### Opción A: Verificar en la consola web

1. Ve a Cloud Console: https://console.cloud.google.com/run
2. Selecciona tu servicio `securitybot`
3. Click en "EDIT & DEPLOY NEW REVISION"
4. Revisa la sección "Variables & Secrets"

### Opción B: Verificar con gcloud CLI

```bash
gcloud run services describe securitybot \
  --region us-central1 \
  --format="yaml(spec.template.spec.containers[0].env)"
```

### **Variables OBLIGATORIAS que deben estar configuradas:**

```bash
✅ VERIFY_TOKEN
✅ ACCESS_TOKEN  
✅ PHONE_NUMBER_ID
✅ DEEPSEEK_API_KEY
✅ DATABASE_URL
⚠️  ADMIN_PHONE_NUMBER (opcional, pero recomendado)
```

---

## 🔧 **Paso 2: Volver a Deployar con Variables Correctas**

### **Si NO tienes secrets configurados:**

```bash
gcloud run deploy securitybot \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --timeout 300 \
  --set-env-vars "VERIFY_TOKEN=tu-token" \
  --set-env-vars "ACCESS_TOKEN=tu-access-token" \
  --set-env-vars "PHONE_NUMBER_ID=tu-phone-id" \
  --set-env-vars "DEEPSEEK_API_KEY=tu-deepseek-key" \
  --set-env-vars "DATABASE_URL=postgresql://user:pass@/db?host=/cloudsql/proyecto:region:instancia" \
  --set-env-vars "ADMIN_PHONE_NUMBER=573001234567" \
  --add-cloudsql-instances proyecto:region:instancia
```

### **Si YA tienes secrets configurados (RECOMENDADO):**

```bash
# Verificar que los secrets existen
gcloud secrets list | grep -E "VERIFY_TOKEN|ACCESS_TOKEN|PHONE_NUMBER_ID|DEEPSEEK_API_KEY|DATABASE_URL|ADMIN_PHONE_NUMBER"

# Si faltan, créalos:
echo -n "tu-valor" | gcloud secrets create NOMBRE_SECRET --data-file=-

# Deploy con secrets
gcloud run deploy securitybot \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --timeout 300 \
  --set-secrets "VERIFY_TOKEN=VERIFY_TOKEN:latest" \
  --set-secrets "ACCESS_TOKEN=ACCESS_TOKEN:latest" \
  --set-secrets "PHONE_NUMBER_ID=PHONE_NUMBER_ID:latest" \
  --set-secrets "DEEPSEEK_API_KEY=DEEPSEEK_API_KEY:latest" \
  --set-secrets "DATABASE_URL=DATABASE_URL:latest" \
  --set-secrets "ADMIN_PHONE_NUMBER=ADMIN_PHONE_NUMBER:latest" \
  --add-cloudsql-instances proyecto:region:instancia
```

---

## 📊 **Paso 3: Revisar los Logs en Tiempo Real**

```bash
# Ver logs en tiempo real
gcloud run services logs tail securitybot --region us-central1

# O ver logs recientes
gcloud run services logs read securitybot --region us-central1 --limit 50
```

### **Lo que DEBES ver en los logs al iniciar correctamente:**

```
============================================================
🚀 SecurityBot-WA - Iniciando...
============================================================
📡 Puerto configurado: 8080

🔍 Verificando variables de entorno...
  VERIFY_TOKEN: ✅ OK
  ACCESS_TOKEN: ✅ OK
  PHONE_NUMBER_ID: ✅ OK
  DEEPSEEK_API_KEY: ✅ OK
  ADMIN_PHONE_NUMBER: ✅ OK
  DATABASE_URL: ✅ OK

✅ Todas las variables críticas están configuradas.

🔄 Configurando base de datos PostgreSQL...
✅ Base de datos configurada correctamente.
🔄 Inicializando modelo SVM de detección de phishing...
✅ Modelo SVM listo para usar

============================================================
✅ SecurityBot-WA listo para recibir conexiones
🌐 Escuchando en puerto 8080
============================================================
```

### **Si ves esto, algo está MAL:**

```
❌ ERROR CRÍTICO: Faltan variables de entorno OBLIGATORIAS:
   - ACCESS_TOKEN
   - DATABASE_URL

💡 En Cloud Run, configura estas variables como secrets o env vars.
```

---

## 🗄️ **Paso 4: Verificar Conexión a Cloud SQL**

### Verificar que la instancia existe y está running:

```bash
gcloud sql instances describe securitybot \
  --format="value(state,connectionName)"
```

Debe decir: `RUNNABLE` y mostrar el connection name

### Verificar permisos del Service Account:

```bash
# Obtener el service account
SA=$(gcloud run services describe securitybot \
  --region us-central1 \
  --format="value(spec.template.spec.serviceAccountName)")

echo "Service Account: $SA"

# Verificar que tenga el rol cloudsql.client
gcloud projects get-iam-policy TU_PROYECTO_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:$SA AND bindings.role:roles/cloudsql.client"
```

Si no tiene el rol:

```bash
gcloud projects add-iam-policy-binding TU_PROYECTO_ID \
  --member="serviceAccount:$SA" \
  --role="roles/cloudsql.client"
```

---

## 🐳 **Paso 5: Test Local con Docker**

Prueba el contenedor localmente antes de deployar:

```bash
# Build local
docker build -t securitybot-test .

# Run con tus variables
docker run -p 8080:8080 \
  -e VERIFY_TOKEN="tu-token" \
  -e ACCESS_TOKEN="tu-access" \
  -e PHONE_NUMBER_ID="tu-phone" \
  -e DEEPSEEK_API_KEY="tu-key" \
  -e DATABASE_URL="postgresql://..." \
  -e ADMIN_PHONE_NUMBER="57300..." \
  securitybot-test

# Verificar en otra terminal
curl http://localhost:8080/health
```

---

## ⏱️ **Paso 6: Aumentar Timeout si es Necesario**

Si el contenedor inicia pero tarda mucho:

```bash
gcloud run services update securitybot \
  --timeout=600 \
  --region us-central1
```

---

## 🔄 **Paso 7: Forzar Nueva Revisión**

A veces Cloud Run cachea algo mal:

```bash
# Deploy forzando nueva build
gcloud run deploy securitybot \
  --source . \
  --region us-central1 \
  --no-use-build-cache
```

---

## 📝 **Checklist de Verificación Final**

- [ ] ✅ Todas las variables de entorno configuradas
- [ ] ✅ Cloud SQL instancia RUNNABLE
- [ ] ✅ Service Account tiene rol cloudsql.client
- [ ] ✅ Connection name correcto en DATABASE_URL
- [ ] ✅ Secrets creados y versiones latest disponibles
- [ ] ✅ Puerto 8080 expuesto en Dockerfile
- [ ] ✅ No hay errores en el código de main.py
- [ ] ✅ Logs muestran "listo para recibir conexiones"

---

## 🆘 **Si Nada Funciona**

### Ver TODOS los logs del deployment:

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=securitybot" \
  --limit 100 \
  --format json
```

### Rollback a versión anterior que funcionaba:

```bash
# Ver revisiones
gcloud run revisions list --service securitybot --region us-central1

# Hacer rollback
gcloud run services update-traffic securitybot \
  --to-revisions=securitybot-00002-xxx=100 \
  --region us-central1
```

### Deploy mínimo de prueba:

```bash
# Crear un app.py super simple
cat > test_app.py << 'EOF'
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "Test OK"}
EOF

# Deploy solo esto
gcloud run deploy securitybot-test \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

Si esto funciona, el problema está en tu código. Si no funciona, es un problema de configuración de GCP.

---

## 📞 **Soporte Adicional**

- **Documentación oficial**: https://cloud.google.com/run/docs/troubleshooting
- **Logs de Cloud Run**: https://console.cloud.google.com/logs
- **Status de GCP**: https://status.cloud.google.com/

---

## 🎯 **Comandos de Diagnóstico Rápido**

```bash
# Todo en uno - diagnóstico completo
echo "=== SERVICE STATUS ===" && \
gcloud run services describe securitybot --region us-central1 --format="value(status.url,status.conditions)" && \
echo "\n=== LATEST LOGS ===" && \
gcloud run services logs read securitybot --region us-central1 --limit 10 && \
echo "\n=== ENV VARS ===" && \
gcloud run services describe securitybot --region us-central1 --format="yaml(spec.template.spec.containers[0].env)" && \
echo "\n=== CLOUD SQL ===" && \
gcloud sql instances list
```

Copia y pega este comando para obtener un diagnóstico completo.
