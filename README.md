# 🛡️ SecurityBot-WA

Bot de WhatsApp inteligente para detección de mensajes de phishing y estafas usando ML (SVM) + DeepSeek AI.

## 🚀 Quick Start - Deployment en Google Cloud Run

```bash
# 1. Configurar proyecto GCP
gcloud config set project TU_PROYECTO_ID

# 2. Crear secrets (RECOMENDADO para producción)
./deploy.sh create-secrets

# 3. Deploy
./deploy.sh secure
```

## 📚 Documentación de Deployment

- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Checklist completo pre-deployment
- **[DEPLOYMENT_CLOUD_RUN.md](DEPLOYMENT_CLOUD_RUN.md)** - Guía detallada paso a paso
- **[deploy.sh](deploy.sh)** - Script automatizado de deployment

## ⚠️ IMPORTANTE - Seguridad

### ✅ Cambios de seguridad implementados:

1. **Archivo .env removido de git** - Las credenciales ya no están expuestas
2. **.gitignore configurado** - Protección de archivos sensibles
3. **.dockerignore optimizado** - Builds de Docker más rápidos
4. **Dockerfile ajustado para Cloud Run** - Compatible con GCP

### 🔴 ACCIONES REQUERIDAS ANTES DEL DEPLOY:

**Tu código tenía credenciales expuestas en git. DEBES:**

1. **Regenerar ACCESS_TOKEN de WhatsApp**
   - Ve a: https://developers.facebook.com/apps/
   - Regenera el token (el actual está comprometido)

2. **Considerar rotar DEEPSEEK_API_KEY**
   - También estaba expuesta en el repositorio

3. **Hacer commit de los cambios de seguridad**
   ```bash
   git add .
   git commit -m "feat: security fixes and Cloud Run deployment"
   git push origin main
   ```

## 🏗️ Arquitectura

```
┌─────────────────┐
│  WhatsApp User  │
└────────┬────────┘
         │ Webhook
         ▼
┌─────────────────────────┐
│   Google Cloud Run      │
│  (FastAPI + Uvicorn)    │
└────┬──────────────┬─────┘
     │              │
     │              ▼
     │    ┌──────────────────┐
     │    │  Cloud SQL       │
     │    │  (PostgreSQL)    │
     │    └──────────────────┘
     │
     ▼
┌──────────────────┐
│  DeepSeek API    │
│  (AI Analysis)   │
└──────────────────┘
```

## 🔧 Stack Tecnológico

- **Framework**: FastAPI + Uvicorn
- **Base de Datos**: PostgreSQL (Cloud SQL)
- **ML**: Scikit-learn (SVM)
- **AI**: DeepSeek API
- **OCR**: Tesseract
- **Deployment**: Google Cloud Run
- **CI/CD**: Cloud Build

## 📁 Estructura del Proyecto

```
securityBot/
├── app/
│   ├── api/              # Endpoints de WhatsApp webhook
│   ├── services/         # Lógica de negocio
│   ├── storage/          # Manejo de BD (PostgreSQL)
│   ├── utils/            # Configuración y utilidades
│   └── main.py           # Entry point
├── Dockerfile            # Configuración del container
├── requirements.txt      # Dependencias Python
├── deploy.sh            # Script de deployment
└── DEPLOYMENT_*.md      # Documentación

```

## 🔑 Variables de Entorno Requeridas

```bash
# WhatsApp Business API
VERIFY_TOKEN=tu-verify-token
ACCESS_TOKEN=tu-access-token-whatsapp
PHONE_NUMBER_ID=tu-phone-number-id

# DeepSeek AI
DEEPSEEK_API_KEY=tu-deepseek-api-key
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions

# PostgreSQL (Cloud SQL)
DATABASE_URL=postgresql://USER:PASS@/DB?host=/cloudsql/PROYECTO:REGION:INSTANCIA
```

## 🧪 Testing Local

### Usando Docker:

```bash
# Build
docker build -t securitybot .

# Run
docker run -p 8080:8080 \
  -e VERIFY_TOKEN="test" \
  -e ACCESS_TOKEN="test" \
  -e PHONE_NUMBER_ID="test" \
  -e DEEPSEEK_API_KEY="test" \
  -e DATABASE_URL="postgresql://..." \
  securitybot

# Test health
curl http://localhost:8080/health
```

### Usando Python directo:

```bash
# Crear .env con tus credenciales
cp .env.example app/.env

# Instalar dependencias
pip install -r requirements.txt

# Correr
python -m app.main
```

## 📊 Features

- ✅ Detección de phishing con SVM + DeepSeek AI
- ✅ Análisis de URLs sospechosas
- ✅ OCR para análisis de imágenes
- ✅ Sistema de feedback y aprendizaje (RLHF)
- ✅ Comandos administrativos
- ✅ Flujo conversacional interactivo
- ✅ Multi-idioma (Español)

## 🛠️ Comandos Útiles

```bash
# Ver logs
./deploy.sh logs

# Ver logs en tiempo real
./deploy.sh tail

# Ver estado del servicio
./deploy.sh status

# Test del deployment
./deploy.sh test

# Rollback a versión anterior
./deploy.sh rollback
```

## 🐛 Troubleshooting

### Error de conexión a Cloud SQL
```bash
# Verificar connection name
gcloud sql instances describe INSTANCIA --format="value(connectionName)"

# Verificar permisos
gcloud projects add-iam-policy-binding PROYECTO \
  --member="serviceAccount:SA@PROJECT.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

### Ver logs detallados
```bash
gcloud run services logs read securitybot --region us-central1 --limit 100
```

### Problemas de memoria
```bash
# Aumentar memoria
gcloud run services update securitybot --memory 1Gi --region us-central1
```

## 📝 Próximos Pasos After Deployment

1. ✅ Deploy exitoso
2. Configure webhook de WhatsApp con la URL del servicio
3. Test con mensajes reales
4. Configure alertas de monitoreo
5. Configure backups automáticos de Cloud SQL
6. Configure budget alerts en GCP

## 📄 Licencia

Proyecto privado - Todos los derechos reservados

## 🆘 Soporte

Para problemas de deployment:
1. Revisa [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
2. Revisa logs: `./deploy.sh logs`
3. Consulta [DEPLOYMENT_CLOUD_RUN.md](DEPLOYMENT_CLOUD_RUN.md)

---

**Desarrollado para detección de phishing en Colombia 🇨🇴**
