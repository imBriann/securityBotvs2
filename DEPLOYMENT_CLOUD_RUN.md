# 🚀 Guía de Deployment en Google Cloud Run

## 📋 Prerequisitos

1. **Cuenta de Google Cloud Platform (GCP)**
   - Proyecto creado en GCP
   - Facturación habilitada

2. **Cloud SQL (PostgreSQL) configurado**
   - Instancia de Cloud SQL creada
   - Base de datos `postgres` (o el nombre que uses)
   - Usuario con permisos

3. **Google Cloud SDK instalado**
   ```bash
   # Instalar gcloud CLI
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud init
   ```

4. **APIs habilitadas en tu proyecto**
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable sqladmin.googleapis.com
   gcloud services enable artifactregistry.googleapis.com
   ```

---

## 🔧 Paso 1: Configuración de Variables de Entorno

En Google Cloud Run, las variables de entorno se configuran al momento del deploy, **NO uses archivos .env**.

Prepara estos valores:
- `VERIFY_TOKEN`: Token de verificación de WhatsApp
- `ACCESS_TOKEN`: Token de acceso de WhatsApp Business API
- `PHONE_NUMBER_ID`: ID del número de teléfono de WhatsApp
- `DEEPSEEK_API_KEY`: API key de DeepSeek
- `DATABASE_URL`: URL de conexión a Cloud SQL

### Formato de DATABASE_URL para Cloud SQL:

```
postgresql://USUARIO:PASSWORD@/NOMBRE_DB?host=/cloudsql/PROYECTO:REGION:INSTANCIA
```

**Ejemplo real:**
```
postgresql://postgres:MiPassword123@/securitybot?host=/cloudsql/securitybot-485719:us-central1:securitybot
```

---

## 🐳 Paso 2: Build y Deploy

### Opción A: Deploy directo desde código fuente

```bash
# Navegar al directorio del proyecto
cd /home/brian/Documentos/securityBot/securityBot

# Deploy con Cloud Build (más simple)
gcloud run deploy securitybot \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars "VERIFY_TOKEN=tu-verify-token" \
  --set-env-vars "ACCESS_TOKEN=tu-access-token" \
  --set-env-vars "PHONE_NUMBER_ID=tu-phone-id" \
  --set-env-vars "DEEPSEEK_API_KEY=tu-deepseek-key" \
  --set-env-vars "DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions" \
  --set-env-vars "DATABASE_URL=postgresql://USER:PASS@/DB?host=/cloudsql/PROYECTO:REGION:INSTANCIA" \
  --add-cloudsql-instances PROYECTO:REGION:INSTANCIA
```

### Opción B: Build manual + Deploy

```bash
# 1. Configurar proyecto
export PROJECT_ID="tu-proyecto-id"
export REGION="us-central1"
export SERVICE_NAME="securitybot"

# 2. Build de la imagen
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# 3. Deploy con la imagen
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars "..." \
  --add-cloudsql-instances PROYECTO:REGION:INSTANCIA
```

---

## 🔒 Paso 3: Configurar Secrets (Más Seguro - RECOMENDADO)

En lugar de pasar variables de entorno directamente, usa **Secret Manager**:

```bash
# 1. Crear secrets
echo -n "tu-verify-token" | gcloud secrets create VERIFY_TOKEN --data-file=-
echo -n "tu-access-token" | gcloud secrets create ACCESS_TOKEN --data-file=-
echo -n "tu-phone-id" | gcloud secrets create PHONE_NUMBER_ID --data-file=-
echo -n "tu-deepseek-key" | gcloud secrets create DEEPSEEK_API_KEY --data-file=-
echo -n "postgresql://..." | gcloud secrets create DATABASE_URL --data-file=-

# 2. Deploy usando secrets
gcloud run deploy securitybot \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-secrets "VERIFY_TOKEN=VERIFY_TOKEN:latest" \
  --set-secrets "ACCESS_TOKEN=ACCESS_TOKEN:latest" \
  --set-secrets "PHONE_NUMBER_ID=PHONE_NUMBER_ID:latest" \
  --set-secrets "DEEPSEEK_API_KEY=DEEPSEEK_API_KEY:latest" \
  --set-secrets "DATABASE_URL=DATABASE_URL:latest" \
  --add-cloudsql-instances PROYECTO:REGION:INSTANCIA
```

---

## 🗄️ Paso 4: Conectar Cloud SQL

### Verificar conexión Cloud SQL:

1. **Instancia Connection Name**: Formato `proyecto:region:instancia`
   ```bash
   gcloud sql instances describe NOMBRE_INSTANCIA --format="value(connectionName)"
   ```

2. **Crear usuario y base de datos** (si no existe):
   ```bash
   gcloud sql databases create securitybot --instance=NOMBRE_INSTANCIA
   gcloud sql users create usuario --instance=NOMBRE_INSTANCIA --password=PASSWORD
   ```

3. **Permisos**: Cloud Run necesita permisos para conectarse
   ```bash
   gcloud projects add-iam-policy-binding PROYECTO \
     --member="serviceAccount:SERVICE_ACCOUNT@PROJECT.iam.gserviceaccount.com" \
     --role="roles/cloudsql.client"
   ```

---

## 📱 Paso 5: Configurar Webhook de WhatsApp

Después del deploy, obtendrás una URL como:
```
https://securitybot-HASH.us-central1.run.app
```

Configura el webhook en WhatsApp Business:

1. **URL del Webhook**: `https://tu-servicio.run.app/webhook`
2. **Verify Token**: El mismo que configuraste en `VERIFY_TOKEN`
3. **Suscribirse a eventos**: `messages`, `message_status`

---

## ✅ Paso 6: Verificación

### 1. Health check
```bash
curl https://tu-servicio.run.app/health
# Debe responder: {"status":"healthy","service":"SecurityBot-WA"}
```

### 2. Ver logs
```bash
gcloud run services logs read securitybot --region us-central1 --limit 50
```

### 3. Verificar webhook GET
```bash
curl "https://tu-servicio.run.app/webhook?hub.mode=subscribe&hub.verify_token=TU_TOKEN&hub.challenge=test"
# Debe responder: test
```

---

## 🔄 Actualizaciones

Para actualizar el servicio después de cambios en el código:

```bash
# Commit cambios
git add .
git commit -m "Descripción de cambios"
git push

# Re-deploy (usa la misma configuración anterior)
gcloud run deploy securitybot \
  --source . \
  --region us-central1
```

---

## 🐛 Troubleshooting

### Error: "Cloud SQL connection failed"
- Verifica que el connection name sea correcto
- Verifica permisos del service account
- Verifica que la instancia de Cloud SQL esté running

### Error: "Container failed to start"
- Revisa logs: `gcloud run services logs read securitybot --limit 100`
- Verifica variables de entorno
- Verifica que todas las dependencias en requirements.txt sean compatibles

### Error: "Database connection timeout"
- Aumenta timeout: `--timeout 300`
- Verifica credenciales de DATABASE_URL
- Verifica que la base de datos existe

### Error de memoria
- Aumenta memoria: `--memory 1Gi`
- Optimiza el código para usar menos recursos

---

## 💰 Estimación de Costos

**Cloud Run** (con Free Tier):
- Primeros 2 millones de requests/mes: GRATIS
- 180,000 vCPU-segundos/mes: GRATIS
- 360,000 GiB-segundos de memoria/mes: GRATIS

**Cloud SQL**:
- Instancia shared-core (db-f1-micro): ~$10-15/mes
- Almacenamiento: ~$0.17/GB/mes

**Estimado total mensual**: $10-20 USD (con tráfico bajo-medio)

---

## 📚 Recursos Adicionales

- [Cloud Run QuickStart](https://cloud.google.com/run/docs/quickstarts)
- [Cloud SQL para Cloud Run](https://cloud.google.com/sql/docs/postgres/connect-run)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp/cloud-api)

---

## 🆘 Comandos Útiles

```bash
# Ver servicios de Cloud Run
gcloud run services list

# Describir servicio
gcloud run services describe securitybot --region us-central1

# Ver logs en tiempo real
gcloud run services logs tail securitybot --region us-central1

# Eliminar servicio
gcloud run services delete securitybot --region us-central1

# Ver métricas
gcloud monitoring dashboards list
```
