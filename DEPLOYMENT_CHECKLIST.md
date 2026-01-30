# ✅ Checklist Pre-Deployment para Google Cloud Run

## 🔒 SEGURIDAD (CRÍTICO)

- [x] **.env removido de git** ✅ 
  - Archivo `app/.env` eliminado del repositorio
  - Archivo `.env.example` creado como plantilla
  
- [x] **.gitignore configurado** ✅
  - Protege archivos sensibles
  - Excluye archivos innecesarios

- [ ] **Credenciales NO están en el código fuente**
  - ⚠️ Verifica que no haya hardcoded credentials en ningún archivo .py

- [ ] **Rotar tokens expuestos** ⚠️ IMPORTANTE
  - Tu `ACCESS_TOKEN` actual estaba en git público
  - **DEBES regenerarlo** en WhatsApp Business antes del deploy
  - Tu `DEEPSEEK_API_KEY` también estaba expuesta - considera rotarla

- [ ] **Usar Secret Manager en producción**
  - No uses variables de entorno simples para producción
  - Configura secrets según la guía DEPLOYMENT_CLOUD_RUN.md

---

## 🔧 CONFIGURACIÓN

- [x] **Dockerfile optimizado para Cloud Run** ✅
  - HEALTHCHECK removido (no compatible)
  - Puerto 8080 configurado
  - Usuario no-root configurado

- [x] **.dockerignore configurado** ✅
  - Optimiza el build de Docker
  - Reduce tamaño de la imagen

- [x] **Health endpoint creado** ✅
  - Endpoint `/health` disponible en la app

- [x] **DATABASE_URL parser mejorado** ✅
  - Soporta Cloud SQL con socket Unix
  - Soporta conexiones TCP estándar

- [ ] **Variables de entorno preparadas**
  - `VERIFY_TOKEN`
  - `ACCESS_TOKEN` (regenerado)
  - `PHONE_NUMBER_ID`
  - `DEEPSEEK_API_KEY` (opcional: rotada)
  - `DATABASE_URL`

---

## 🗄️ BASE DE DATOS

- [ ] **Cloud SQL instancia creada**
  - PostgreSQL 15 o superior recomendado
  - Configuración de región: `us-central1` (o tu preferida)
  - Storage suficiente (10GB mínimo)

- [ ] **Base de datos y usuario creados**
  ```sql
  CREATE DATABASE securitybot;
  CREATE USER securitybot_user WITH PASSWORD 'password_seguro';
  GRANT ALL PRIVILEGES ON DATABASE securitybot TO securitybot_user;
  ```

- [ ] **Connection Name anotado**
  - Formato: `proyecto:region:instancia`
  - Ejemplo: `securitybot-485719:us-central1:securitybot`

- [ ] **DATABASE_URL formateada correctamente**
  - Para Cloud SQL: `postgresql://USER:PASS@/DB?host=/cloudsql/PROYECTO:REGION:INSTANCIA`

---

## 🚀 GOOGLE CLOUD PLATFORM

- [ ] **Proyecto GCP creado y seleccionado**
  ```bash
  gcloud projects list
  gcloud config set project TU_PROYECTO_ID
  ```

- [ ] **APIs habilitadas**
  ```bash
  gcloud services enable run.googleapis.com
  gcloud services enable cloudbuild.googleapis.com
  gcloud services enable sqladmin.googleapis.com
  gcloud services enable secretmanager.googleapis.com
  ```

- [ ] **Facturación habilitada**
  - Verifica en: https://console.cloud.google.com/billing

- [ ] **Service Account con permisos**
  - Cloud Run Admin
  - Cloud SQL Client
  - Secret Manager Secret Accessor (si usas secrets)

---

## 📱 WHATSAPP BUSINESS API

- [ ] **Aplicación de Facebook configurada**
  - WhatsApp Business API habilitada
  - Número de teléfono verificado

- [ ] **Tokens regenerados** ⚠️
  - `ACCESS_TOKEN` nuevo (el anterior está comprometido)
  - `VERIFY_TOKEN` confirmado

- [ ] **Webhook será configurado POST-deployment**
  - URL: `https://tu-servicio.run.app/webhook`
  - Verify Token: tu `VERIFY_TOKEN`
  - Eventos: `messages`, `message_status`

---

## 🧪 TESTING LOCAL (OPCIONAL)

- [ ] **Docker build local exitoso**
  ```bash
  docker build -t securitybot-test .
  ```

- [ ] **Container corre localmente**
  ```bash
  docker run -p 8080:8080 \
    -e VERIFY_TOKEN="test" \
    -e ACCESS_TOKEN="test" \
    -e PHONE_NUMBER_ID="test" \
    -e DEEPSEEK_API_KEY="test" \
    -e DATABASE_URL="postgresql://..." \
    securitybot-test
  ```

- [ ] **Health check responde**
  ```bash
  curl http://localhost:8080/health
  ```

---

## 📝 PRE-DEPLOYMENT

- [ ] **Código commiteado y pusheado**
  ```bash
  git add .
  git commit -m "Ready for Cloud Run deployment"
  git push origin main
  ```

- [ ] **Revisar requirements.txt**
  - Todas las dependencias listadas
  - Versiones específicas definidas

- [ ] **Revisar Dockerfile**
  - Copia todos los archivos necesarios
  - WORKDIR correcto
  - CMD apunta a `app.main:app`

---

## 🎯 DEPLOYMENT

Sigue la guía completa en: **[DEPLOYMENT_CLOUD_RUN.md](DEPLOYMENT_CLOUD_RUN.md)**

Comando básico:
```bash
gcloud run deploy securitybot \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances PROYECTO:REGION:INSTANCIA \
  --set-secrets "..." 
```

---

## ✅ POST-DEPLOYMENT

- [ ] **Verificar health check**
  ```bash
  curl https://tu-servicio.run.app/health
  ```

- [ ] **Configurar webhook en WhatsApp**
  - URL correcta
  - Verificación exitosa

- [ ] **Enviar mensaje de prueba**
  - Responde el bot
  - Logs sin errores

- [ ] **Revisar logs**
  ```bash
  gcloud run services logs read securitybot --limit 100
  ```

- [ ] **Monitorear métricas**
  - CPU usage
  - Memory usage
  - Request count
  - Error rate

---

## 🚨 ACCIONES URGENTES DESPUÉS DE ESTA REVISIÓN

### ⚠️ CRÍTICO - Hacer AHORA:

1. **Regenerar ACCESS_TOKEN de WhatsApp**
   - Tu token actual estaba expuesto en git
   - Ve a: https://developers.facebook.com/apps/
   - Regenera el token y guárdalo de forma segura

2. **Considerar rotar DEEPSEEK_API_KEY**
   - También estaba expuesta en git
   - Ve a tu dashboard de DeepSeek y genera una nueva

3. **Commit y push de los cambios de seguridad**
   ```bash
   git add .
   git commit -m "Security fixes: remove .env, add .gitignore"
   git push origin main
   ```

4. **Verificar que .env no esté en GitHub remote**
   - Ve a tu repositorio en GitHub
   - Busca el archivo `app/.env`
   - Si aparece en el historial, considera hacer un force push o limpiar historial

---

## 📊 Monitoreo Continuo

- [ ] **Alertas configuradas**
  - Error rate > 5%
  - Response time > 5s
  - Memory usage > 80%

- [ ] **Budget alerts**
  - Configurar límite de gasto mensual

- [ ] **Backup de base de datos**
  - Automated backups habilitados en Cloud SQL

---

## 📞 Soporte

Si encuentras problemas:
1. Revisa logs: `gcloud run services logs read securitybot`
2. Verifica guía: DEPLOYMENT_CLOUD_RUN.md
3. Documentación oficial: https://cloud.google.com/run/docs
