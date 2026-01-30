<div align="center">

# 🛡️ SecurityBot-WA

### *Asistente Inteligente de Seguridad para WhatsApp*

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-Private-red.svg)]()
[![Cloud Run](https://img.shields.io/badge/Cloud%20Run-Ready-4285F4?logo=googlecloud)](https://cloud.google.com/run)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?logo=postgresql)](https://www.postgresql.org/)

**Bot de WhatsApp que combina Machine Learning (SVM) e Inteligencia Artificial (DeepSeek) para detectar y prevenir intentos de phishing, estafas y mensajes maliciosos en tiempo real.**

[Características](#-características-principales) •
[Instalación](#-instalación) •
[Deployment](#-deployment) •
[Documentación](#-documentación)

---

</div>

## 📖 Tabla de Contenidos

- [¿Qué es SecurityBot-WA?](#-qué-es-securitybot-wa)
- [¿Cómo Funciona?](#-cómo-funciona)
- [Características Principales](#-características-principales)
- [Arquitectura](#-arquitectura)
- [Stack Tecnológico](#-stack-tecnológico)
- [Instalación](#-instalación)
- [Configuración](#-configuración)
- [Deployment](#-deployment)
- [Uso](#-uso)
- [Comandos Administrativos](#-comandos-administrativos)
- [Sistema RLHF](#-sistema-rlhf-reinforcement-learning-from-human-feedback)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [API Reference](#-api-reference)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap)
- [Contribución](#-contribución)
- [Licencia](#-licencia)

---

## 🎯 ¿Qué es SecurityBot-WA?

**SecurityBot-WA** es un asistente virtual inteligente desarrollado para WhatsApp Business que protege a los usuarios colombianos contra:

- 🎣 **Phishing** - Suplantación de identidad bancaria, institucional y comercial
- 💰 **Estafas financieras** - Fraudes de inversión, préstamos falsos, premios ficticios
- 🔗 **URLs maliciosas** - Enlaces peligrosos que roban información personal
- 📱 **Ingeniería social** - Mensajes que manipulan psicológicamente a las víctimas
- 🖼️ **Imágenes fraudulentas** - Capturas falsas de transferencias, documentos adulterados

El bot utiliza un **sistema híbrido de análisis** que combina:
- **SVM (Support Vector Machine)**: Modelo de machine learning entrenado con datos locales
- **DeepSeek AI**: Inteligencia artificial avanzada para análisis contextual
- **OCR (Tesseract)**: Reconocimiento óptico de caracteres para analizar imágenes
- **Validación de URLs**: Verificación de enlaces contra bases de datos de amenazas

### 🎭 ¿Por qué es importante?

En Colombia, el **fraude digital creció un 300% en 2024**. SecurityBot-WA democratiza el acceso a tecnología de ciberseguridad avanzada, protegiendo a usuarios sin conocimientos técnicos a través de la plataforma más usada: **WhatsApp**.

---

## 🔬 ¿Cómo Funciona?

### Flujo de Interacción

```mermaid
graph TD
    A[👤 Usuario recibe mensaje sospechoso] --> B{Envía al bot por WhatsApp}
    B --> C[🔍 Análisis SVM<br/>Machine Learning]
    B --> D[🤖 Análisis DeepSeek AI<br/>Inteligencia Artificial]
    B --> E[🔗 Validación de URLs<br/>Base de datos de amenazas]
    C --> F[📊 Sistema de Fusión]
    D --> F
    E --> F
    F --> G{Veredicto Final}
    G -->|SEGURO| H[✅ Mensaje confiable]
    G -->|SOSPECHOSO| I[⚠️ Posible amenaza]
    G -->|PELIGROSO| J[🚨 Phishing confirmado]
    H --> K[👍 Usuario da feedback]
    I --> K
    J --> K
    K --> L[🔄 Reentrenamiento RLHF]
    L --> C
```

### Proceso Detallado

1. **📥 Recepción**: El usuario envía un mensaje, imagen o URL sospechosa
2. **🧹 Preprocesamiento**: Limpieza y normalización del texto
3. **🔎 Análisis Múltiple**:
   - **SVM**: Clasifica patrones lingüísticos de estafa
   - **DeepSeek**: Evalúa contexto, urgencia y técnicas de manipulación
   - **URL Checker**: Verifica dominios contra listas de phishing conocido
   - **OCR**: Si es imagen, extrae texto para análisis
4. **⚖️ Fusión de Resultados**: Combina veredictos con sistema de ponderación
5. **📨 Respuesta al Usuario**: Explicación clara del análisis con recomendaciones
6. **📊 Feedback Loop**: El usuario indica si el análisis fue correcto (👍/👎)
7. **🎓 Aprendizaje Continuo**: El sistema mejora su precisión con cada interacción

---

## ✨ Características Principales

### 🔐 Detección Avanzada de Phishing

- **Análisis híbrido SVM + AI** con precisión >90%
- **Detección de urgencia artificial** ("¡Actúa ahora!", "Última oportunidad")
- **Identificación de suplantación** (bancos, gobierno, empresas conocidas)
- **Análisis de solicitudes sospechosas** (datos personales, contraseñas, códigos OTP)

### 🌐 Validación Inteligente de URLs

- Base de datos con **50+ dominios legítimos colombianos**
- Detección de **TLDs sospechosos** (.tk, .ml, .ga, etc.)
- Identificación de **typosquatting** (bancolombia.com vs bancolombla.com)
- Verificación de **protocolo seguro** (HTTP vs HTTPS)
- Evaluación de **longitud y complejidad** de URLs

### 🖼️ Análisis de Imágenes con OCR

- Extracción de texto de capturas de pantalla
- Detección de **transferencias bancarias falsas**
- Análisis de **documentos fraudulentos**
- Identificación de **interfaces de phishing clonadas**

### 💬 Flujo Conversacional Inteligente

- **Onboarding interactivo** con aceptación de términos
- **Recolección de datos del usuario** (nombre, edad, nivel de conocimiento)
- **Respuestas contextuales** adaptadas al perfil del usuario
- **Explicaciones educativas** sobre técnicas de phishing
- **Tips de seguridad** personalizados

### 🔄 Sistema RLHF (Reinforcement Learning from Human Feedback)

- **Captura de feedback** del usuario (👍 correcto / 👎 incorrecto)
- **Revisión manual** por administradores de casos negativos
- **Reentrenamiento automático** del modelo SVM
- **Métricas de calidad** y estadísticas de precisión
- **Auditoría completa** de decisiones

### 🛠️ Panel Administrativo

Comandos disponibles para administradores:

| Comando | Descripción |
|---------|-------------|
| `/stats` | Estadísticas de uso y efectividad |
| `/feedback` | Resumen de feedback positivo/negativo |
| `/pendientes` | Casos que requieren revisión manual |
| `/revisar` | Iniciar flujo de revisión interactiva |
| `/export` | Exportar datos para reentrenamiento |
| `/retrain` | Generar reporte de calidad del modelo |
| `/reset {telefono}` | Reiniciar perfil de usuario |

### 🔒 Seguridad y Privacidad

- **Encriptación end-to-end** de WhatsApp preservada
- **No almacenamiento de contenido sensible** (contraseñas, tarjetas)
- **Anonimización de datos** para análisis
- **Cumplimiento GDPR** y leyes colombianas de protección de datos
- **Secrets Manager** para credenciales en producción

---

## 🏗️ Arquitectura

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                         CAPA DE USUARIO                         │
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐  │
│  │   Usuario 1  │     │   Usuario 2  │ ... │  Admin User  │  │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘  │
│         │                     │                     │          │
└─────────┼─────────────────────┼─────────────────────┼──────────┘
          │                     │                     │
          └─────────────────────┴─────────────────────┘
                                │
                    WhatsApp Business API
                                │
┌───────────────────────────────┼──────────────────────────────────┐
│                               │   GOOGLE CLOUD RUN               │
│                               ▼                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                     FASTAPI APPLICATION                    │ │
│  │                                                            │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │              whatsapp_webhook.py                     │ │ │
│  │  │  - Verifica webhook (GET)                            │ │ │
│  │  │  - Recibe mensajes (POST)                            │ │ │
│  │  │  - Anti-duplicación                                  │ │ │
│  │  └─────────────┬────────────────────────────────────────┘ │ │
│  │                │                                           │ │
│  │                ▼                                           │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │          conversation_flow.py                        │ │ │
│  │  │  - Máquina de estados                                │ │ │
│  │  │  - Lógica conversacional                             │ │ │
│  │  │  - Enrutamiento de mensajes                          │ │ │
│  │  └─────┬────────────────┬────────────────┬──────────────┘ │ │
│  │        │                │                │                 │ │
│  │        ▼                ▼                ▼                 │ │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────────┐          │ │
│  │  │   SVM    │   │ DeepSeek │   │     OCR      │          │ │
│  │  │Classifier│   │    AI    │   │  Tesseract   │          │ │
│  │  └──────────┘   └──────────┘   └──────────────┘          │ │
│  │        │                │                │                 │ │
│  │        └────────────────┴────────────────┘                 │ │
│  │                         │                                   │ │
│  │                         ▼                                   │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │              external_apis.py                        │ │ │
│  │  │  - send_whatsapp_message()                           │ │ │
│  │  │  - analyze_with_deepseek()                           │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│                               │                                  │
└───────────────────────────────┼──────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
        ┌──────────────────┐    ┌──────────────────┐
        │   Cloud SQL      │    │  DeepSeek API    │
        │  (PostgreSQL)    │    │  (External)      │
        │                  │    │                  │
        │  - usuarios      │    │  - Chat          │
        │  - analisis_logs │    │  - Completions   │
        │  - feedback_stats│    │                  │
        └──────────────────┘    └──────────────────┘
```

### Base de Datos (PostgreSQL)

#### Tabla `usuarios`
```sql
- telefono (PK)
- nombre
- edad
- conocimiento
- estado
- mensajes_enviados
- last_analysis_details
- last_image_ocr_text
- created_at / updated_at
```

#### Tabla `analisis_logs`
```sql
- id (PK)
- phone_number (FK)
- message_content
- svm_prediction / svm_confidence
- has_urls / url_risk_levels
- deepseek_verdict
- final_verdict / final_is_scam
- user_feedback (👍/👎)
- reviewed_by_admin
- admin_notes
- created_at
```

#### Tabla `feedback_stats`
```sql
- stat_date (PK)
- total_analyses
- total_positive_feedback
- total_negative_feedback
- total_unreviewed_negatives
```

---

## 🔧 Stack Tecnológico

### Backend
- **[FastAPI](https://fastapi.tiangolo.com/)** v0.104+ - Framework web moderno y rápido
- **[Uvicorn](https://www.uvicorn.org/)** v0.24+ - Servidor ASGI de alto rendimiento
- **[Python](https://www.python.org/)** 3.11+ - Lenguaje de programación

### Machine Learning & AI
- **[scikit-learn](https://scikit-learn.org/)** v1.7.2 - SVM para clasificación de phishing
- **[DeepSeek API](https://deepseek.com/)** - Análisis contextual con IA avanzada
- **[pandas](https://pandas.pydata.org/)** v2.1.3 - Procesamiento de datos
- **[NumPy](https://numpy.org/)** v1.26.2 - Computación numérica

### Procesamiento de Imágenes
- **[Tesseract OCR](https://github.com/tesseract-ocr/tesseract)** v4.0+ - Reconocimiento óptico de caracteres
- **[pytesseract](https://github.com/madmaze/pytesseract)** v0.3.10 - Wrapper de Python
- **[OpenCV](https://opencv.org/)** v4.8.1 - Procesamiento de imágenes
- **[Pillow](https://python-pillow.org/)** v10.1.0 - Manipulación de imágenes

### Base de Datos
- **[PostgreSQL](https://www.postgresql.org/)** 15+ - Base de datos relacional
- **[psycopg2](https://www.psycopg.org/)** v2.9.10 - Adaptador PostgreSQL para Python
- **[Cloud SQL](https://cloud.google.com/sql)** - PostgreSQL administrado en GCP

### APIs & Comunicación
- **[WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)** - Integración con WhatsApp
- **[httpx](https://www.python-httpx.org/)** v0.25.1 - Cliente HTTP asíncrono
- **[requests](https://requests.readthedocs.io/)** v2.31.0 - Cliente HTTP

### DevOps & Cloud
- **[Docker](https://www.docker.com/)** - Contenerización
- **[Google Cloud Run](https://cloud.google.com/run)** - Serverless container platform
- **[Cloud Build](https://cloud.google.com/build)** - CI/CD automatizado
- **[Secret Manager](https://cloud.google.com/secret-manager)** - Gestión de secretos

### Utilidades
- **[python-dotenv](https://github.com/theskumar/python-dotenv)** v1.0.0 - Variables de entorno
- **[joblib](https://joblib.readthedocs.io/)** v1.3.2 - Serialización de modelos ML

---

## 🚀 Instalación

### Requisitos Previos

- **Python 3.11+** instalado
- **PostgreSQL 15+** (o acceso a Cloud SQL)
- **Tesseract OCR** instalado en el sistema
- **Cuenta de WhatsApp Business** con API habilitada
- **DeepSeek API Key**
- **(Opcional) Docker** para desarrollo local

### 1️⃣ Clonar el Repositorio

```bash
git clone https://github.com/tu-usuario/securityBot.git
cd securityBot
```

### 2️⃣ Crear Entorno Virtual

```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3️⃣ Instalar Dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4️⃣ Instalar Tesseract OCR

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng
```

**macOS:**
```bash
brew install tesseract tesseract-lang
```

**Windows:**
- Descargar desde: https://github.com/UB-Mannheim/tesseract/wiki
- Agregar a PATH o configurar `TESSERACT_CMD_PATH` en `.env`

### 5️⃣ Configurar PostgreSQL

**Opción A: Local**
```bash
# Crear base de datos
createdb securitybot

# Crear usuario
createuser -P securitybot_user
# (ingresar password cuando se solicite)

# Otorgar permisos
psql -c "GRANT ALL PRIVILEGES ON DATABASE securitybot TO securitybot_user;"
```

**Opción B: Cloud SQL (para producción)**
```bash
# Ver sección de Deployment
```

---

## ⚙️ Configuración

### Variables de Entorno

Crear archivo `app/.env` basado en [.env.example](.env.example):

```bash
# WhatsApp Business API
VERIFY_TOKEN="tu-verify-token-seguro"
ACCESS_TOKEN="EAAxxxxxxxxxxxxx"  # Token de WhatsApp Business
PHONE_NUMBER_ID="123456789"

# DeepSeek AI
DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxx"
DEEPSEEK_API_URL="https://api.deepseek.com/v1/chat/completions"

# PostgreSQL
# Para desarrollo local:
DATABASE_URL="postgresql://securitybot_user:password@localhost:5432/securitybot"

# Para Cloud SQL (producción):
# DATABASE_URL="postgresql://user:pass@/dbname?host=/cloudsql/proyecto:region:instancia"
```

### Configurar WhatsApp Business

1. **Crear app en Meta for Developers**
   - Ve a: https://developers.facebook.com/apps/
   - Crea una nueva app de tipo "Business"

2. **Habilitar WhatsApp**
   - En el dashboard, agrega el producto "WhatsApp"
   - Configura un número de teléfono de prueba

3. **Obtener credenciales**
   - `PHONE_NUMBER_ID`: En WhatsApp > API Setup
   - `ACCESS_TOKEN`: En WhatsApp > API Setup > Temporary token
   - `VERIFY_TOKEN`: Crea uno seguro (cualquier string)

4. **Configurar webhook** (después del deploy)
   - URL: `https://tu-dominio.com/webhook`
   - Verify Token: El que configuraste
   - Suscripciones: `messages`, `message_status`

### Configurar Administrador

Edita [app/services/admin_commands.py](app/services/admin_commands.py#L18):

```python
ADMIN_PHONE_NUMBER = "573505894033"  # Cambiar por tu número (sin +)
```

---

## 🚀 Deployment

### Opción 1: Docker Local (Testing)

```bash
# Build
docker build -t securitybot .

# Run
docker run -p 8080:8080 \
  --env-file app/.env \
  securitybot

# Verificar
curl http://localhost:8080/health
```

### Opción 2: Google Cloud Run (Producción) ⭐

#### Paso 1: Configurar GCP

```bash
# Instalar gcloud CLI
curl https://sdk.cloud.google.com | bash

# Inicializar
gcloud init

# Habilitar APIs
gcloud services enable run.googleapis.com \
  cloudbuild.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com
```

#### Paso 2: Crear Cloud SQL

```bash
# Crear instancia PostgreSQL
gcloud sql instances create securitybot \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Crear base de datos
gcloud sql databases create securitybot --instance=securitybot

# Crear usuario
gcloud sql users create securitybot_user \
  --instance=securitybot \
  --password=PASSWORD_SEGURO
```

#### Paso 3: Configurar Secrets

```bash
# Editar deploy.sh líneas 14-16 con tu información
nano deploy.sh

# Crear secrets
./deploy.sh create-secrets
```

#### Paso 4: Deploy

```bash
# Deploy seguro con Secret Manager
./deploy.sh secure

# O deployment rápido (solo testing)
./deploy.sh quick
```

#### Paso 5: Configurar Webhook

```bash
# Obtener URL del servicio
gcloud run services describe securitybot \
  --region us-central1 \
  --format="value(status.url)"

# Configurar en Meta for Developers:
# URL: https://tu-servicio.run.app/webhook
# Verify Token: [tu VERIFY_TOKEN]
```

### Comandos de Deployment

```bash
./deploy.sh status          # Ver estado del servicio
./deploy.sh logs            # Ver logs
./deploy.sh tail            # Logs en tiempo real
./deploy.sh test            # Test básico
./deploy.sh rollback        # Rollback a versión anterior
```

📚 **Documentación completa**: Ver [DEPLOYMENT_CLOUD_RUN.md](DEPLOYMENT_CLOUD_RUN.md)

---

## 📱 Uso

### Para Usuarios Finales

1. **Iniciar conversación**
   - Envía un mensaje al número de WhatsApp del bot
   - Acepta términos y condiciones
   - Completa tu perfil (nombre, edad, nivel de conocimiento)

2. **Analizar mensajes**
   ```
   Usuario: [Envía mensaje sospechoso]
   Bot: 🔍 Analizando tu mensaje...
   Bot: 🚨 ALERTA DE PHISHING...
   ```

3. **Analizar imágenes**
   ```
   Usuario: [Envía captura de pantalla]
   Bot: 📸 Analizando imagen...
   Bot: ⚠️ Advertencia: Detectamos...
   ```

4. **Dar feedback**
   ```
   Bot: ¿El análisis fue correcto?
   Usuario: 👍  [o]  👎
   Bot: ¡Gracias! Tu feedback mejora el sistema
   ```

### Ejemplo de Conversación

```
👤 Usuario:
"¡FELICIDADES! Has ganado $5.000.000 en la lotería Baloto.
Para reclamar tu premio, haz clic aquí: http://baloto-premio.tk
y envía tus datos bancarios. ¡Tienes 24 horas!"

🤖 Bot:
🔍 Analizando tu mensaje...

🚨 ALERTA DE PHISHING DETECTADO

📊 Análisis:
├─ SVM: PHISHING (98% confianza)
├─ DeepSeek: PELIGROSO
└─ URL: SOSPECHOSA (.tk es TLD de riesgo)

⚠️ Señales de peligro:
• Solicita datos bancarios
• Urgencia artificial (24 horas)
• Dominio sospechoso (.tk)
• Promesa de premio no solicitado

💡 Recomendación:
NO compartas datos personales ni hagas clic en el enlace.
Baloto NUNCA solicita información bancaria por WhatsApp.

🔗 Verifica información oficial en: www.baloto.com

¿Este análisis te fue útil? 
Responde 👍 (correcto) o 👎 (incorrecto)
```

---

## 🛠️ Comandos Administrativos

Solo disponibles para el número configurado como `ADMIN_PHONE_NUMBER`.

### `/stats` - Estadísticas Generales

```
📊 ESTADÍSTICAS DEL SISTEMA

👥 Usuarios:
├─ Total registrados: 1,234
├─ Activos hoy: 89
└─ Nuevos (7 días): 156

📨 Análisis:
├─ Total realizados: 5,678
├─ Phishing detectado: 892 (15.7%)
├─ Mensajes seguros: 4,234 (74.6%)
└─ Sospechosos: 552 (9.7%)

🎯 Precisión:
├─ Feedback positivo: 87.3%
├─ Feedback negativo: 12.7%
└─ Casos sin revisar: 23
```

### `/feedback` - Resumen de Feedback

```
📊 FEEDBACK DE USUARIOS

✅ Positivos: 456 (87%)
❌ Negativos: 67 (13%)

Últimos 7 días:
├─ Lunes: 89% precisión
├─ Martes: 91% precisión
...
└─ Domingo: 85% precisión

🔍 Casos que requieren atención: 12
```

### `/pendientes` - Casos para Revisar

```
📋 CASOS PENDIENTES DE REVISIÓN

Total sin revisar: 12 casos

🔴 Prioridad Alta (5):
├─ ID 234: Usuario reportó falso positivo
├─ ID 235: Duda en clasificación SVM
...

🟡 Prioridad Media (7):
├─ ID 240: Feedback negativo reciente
...

Usa /revisar para iniciar revisión interactiva
```

### `/revisar` - Revisión Interactiva

```
🔍 REVISIÓN DE CASO #234

📱 Usuario: +57 300 123 4567
📅 Fecha: 2026-01-30 14:23

💬 Mensaje analizado:
"Hola, soy del banco. Tu cuenta fue bloqueada.
Llama al 300-999-8888 para reactivarla."

🤖 VEREDICTO DEL BOT: PHISHING (95% confianza)

📊 Análisis:
├─ SVM: Phishing (0.95)
├─ DeepSeek: Peligroso
└─ URLs: No detectadas

❓ ¿El bot se equivocó al marcarlo como PHISHING?
Responde: SI (bot falló) / NO (bot acertó) / SALIR
```

### `/retrain` - Reporte de Reentrenamiento

```
📊 ANÁLISIS DE CALIDAD DEL MODELO

Datos disponibles para reentrenamiento:
├─ Feedback positivo: 456 casos
├─ Revisados por admin: 45 casos
└─ Total útil: 501 casos

📈 Calidad de datos:
├─ Phishing confirmado: 123
├─ Legítimo confirmado: 378
└─ Balance: 24.5% / 75.5% ✅

🎯 Recomendación: READY TO RETRAIN
Precisión esperada: +2.3%
```

### `/reset {telefono}` - Reiniciar Usuario

```
/reset 573001234567

🔄 Usuario reiniciado correctamente

Estado anterior: Registrado
Estado nuevo: Pendiente términos

El usuario debe aceptar términos nuevamente.
```

---

## 🔄 Sistema RLHF (Reinforcement Learning from Human Feedback)

SecurityBot-WA incluye un sistema completo de aprendizaje continuo:

### Flujo RLHF

```
1. Usuario interactúa con el bot
   ↓
2. Bot realiza análisis (SVM + AI)
   ↓
3. Bot envía veredicto al usuario
   ↓
4. Usuario da feedback: 👍 (correcto) o 👎 (incorrecto)
   ↓
5. Sistema registra feedback en BD
   ↓
6. Si feedback es negativo → Cola de revisión admin
   ↓
7. Admin revisa caso con /revisar
   ↓
8. Admin decide: Bot se equivocó (SI) o Bot acertó (NO)
   ↓
9. Sistema marca decisión final
   ↓
10. Casos validados → Dataset de reentrenamiento
    ↓
11. Reentrenamiento periódico del modelo SVM
    ↓
12. Despliegue de nuevo modelo mejorado
    ↓
13. Incremento de precisión del bot
```

### Métricas RLHF

- **Tasa de feedback**: % de usuarios que dan feedback
- **Precisión percibida**: % de feedback positivo
- **Tasa de revisión**: % de casos negativos revisados por admin
- **Calidad del dataset**: Balance phishing/legítimo
- **Mejora iterativa**: Incremento de precisión por versión

---

## 📁 Estructura del Proyecto

```
securityBot/
├── 📄 README.md                      # Este archivo
├── 📄 requirements.txt                # Dependencias Python
├── 🐳 Dockerfile                      # Configuración Docker
├── 🚀 deploy.sh                       # Script de deployment
├── 📋 DEPLOYMENT_CLOUD_RUN.md         # Guía de deployment
├── ✅ DEPLOYMENT_CHECKLIST.md         # Checklist pre-deployment
├── 📝 .env.example                    # Plantilla de variables
├── 🔒 .gitignore                      # Archivos ignorados por git
├── 🐋 .dockerignore                   # Archivos ignorados por Docker
│
├── 📁 app/                            # Aplicación principal
│   ├── 📄 __init__.py
│   ├── 🚀 main.py                     # Entry point
│   │
│   ├── 📁 api/                        # Endpoints HTTP
│   │   ├── 📄 __init__.py
│   │   └── 🌐 whatsapp_webhook.py     # Webhook de WhatsApp
│   │
│   ├── 📁 services/                   # Lógica de negocio
│   │   ├── 📄 __init__.py
│   │   ├── 💬 conversation_flow.py    # Máquina de estados
│   │   ├── 🤖 svm_classifier.py       # Clasificador ML
│   │   ├── 🌐 external_apis.py        # WhatsApp + DeepSeek
│   │   ├── 🛠️ admin_commands.py       # Comandos admin
│   │   ├── 🎓 trainer.py              # Sistema de reentrenamiento
│   │   └── 🧪 test_svm.py             # Tests del modelo
│   │
│   ├── 📁 storage/                    # Capa de datos
│   │   ├── 📄 __init__.py
│   │   ├── 👥 users_state.py          # Gestión de usuarios
│   │   └── 📊 feedback_db.py          # Sistema de feedback
│   │
│   ├── 📁 utils/                      # Utilidades
│   │   ├── 📄 __init__.py
│   │   ├── ⚙️ config.py                # Configuración central
│   │   └── 🧹 preprocessing.py        # Limpieza de texto
│   │
│   └── 📁 md/                         # Documentación interna
│       ├── 📘 RESUMEN_EJECUTIVO.md
│       ├── 📘 RLHF_SYSTEM.md
│       ├── 📘 IMPLEMENTATION_COMPLETE.md
│       └── ... (otros documentos técnicos)
│
├── 📁 imagenes_recibidas/             # Imágenes procesadas
│   └── 📝 .gitkeep
│
└── 📁 tests/                          # Tests
    ├── 🧪 test_interactive_review.py
    └── 🐛 debug_template.py
```

---

## 📡 API Reference

### Endpoints

#### `GET /webhook`
Verificación del webhook de WhatsApp.

**Query Parameters:**
- `hub.mode`: "subscribe"
- `hub.verify_token`: Token de verificación
- `hub.challenge`: Challenge a devolver

**Response:** 
- `200`: Challenge string (verificación exitosa)
- `403`: Token incorrecto

#### `POST /webhook`
Recepción de mensajes de WhatsApp.

**Body:** Notificación de WhatsApp (ver [documentación oficial](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/components))

**Response:**
- `200`: Mensaje procesado

#### `GET /health`
Health check para Cloud Run.

**Response:**
```json
{
  "status": "healthy",
  "service": "SecurityBot-WA"
}
```

### Funciones Principales

#### `handle_user_message(telefono, message_object, message_type, text, user)`
Punto de entrada principal para procesar mensajes.

#### `svm_classifier.analyze_message(message)`
Analiza mensaje con SVM.

**Returns:**
```python
{
    "is_phishing": bool,
    "confidence": float,
    "suspicious_patterns": List[str]
}
```

#### `analyze_with_deepseek(prompt)`
Analiza con DeepSeek AI.

**Returns:** String con veredicto y explicación

---

## 🐛 Troubleshooting

### Problema: "Error de conexión a PostgreSQL"

**Solución:**
```bash
# Verificar cadena de conexión
echo $DATABASE_URL

# Para Cloud SQL, verificar formato:
# postgresql://user:pass@/db?host=/cloudsql/proyecto:region:instancia

# Verificar instancia corriendo
gcloud sql instances describe INSTANCIA
```

### Problema: "Tesseract not found"

**Solución:**
```bash
# Linux
sudo apt-get install tesseract-ocr tesseract-ocr-spa

# Verificar instalación
tesseract --version

# Si persiste, configurar manualmente en .env:
# TESSERACT_CMD_PATH=/usr/bin/tesseract
```

### Problema: "WhatsApp webhook verification failed"

**Solución:**
1. Verificar `VERIFY_TOKEN` en `.env` coincide con Meta
2. Verificar URL es HTTPS
3. Verificar endpoint `/webhook` responde correctamente:
   ```bash
   curl "https://tu-dominio.com/webhook?hub.mode=subscribe&hub.verify_token=TU_TOKEN&hub.challenge=test"
   ```

### Problem: "SVM model not found"

**Solución:**
```bash
# El modelo se inicializa automáticamente
# Si falla, verificar permisos en app/models/

mkdir -p app/models
chmod 755 app/models

# Reiniciar servicio
```

### Problema: "Cloud Run cold start timeout"

**Solución:**
```bash
# Aumentar timeout
gcloud run services update securitybot \
  --timeout=300 \
  --region=us-central1

# O configurar min-instances
gcloud run services update securitybot \
  --min-instances=1 \
  --region=us-central1
```

---

## 🗺️ Roadmap

### ✅ Fase 1 - Completada (Q4 2025)
- [x] Detección básica de phishing con SVM
- [x] Integración con WhatsApp Business API
- [x] Análisis de URLs sospechosas
- [x] OCR para imágenes
- [x] Sistema de feedback básico

### ✅ Fase 2 - Completada (Q1 2026)
- [x] Integración con DeepSeek AI
- [x] Sistema RLHF completo
- [x] Panel administrativo
- [x] Deployment en Cloud Run
- [x] Documentación completa

### 🚧 Fase 3 - En Progreso (Q2 2026)
- [ ] Dashboard web para administradores
- [ ] Métricas en tiempo real (Grafana)
- [ ] Soporte multi-idioma (inglés, portugués)
- [ ] Integración con APIs de threat intelligence
- [ ] Sistema de alertas automatizado

### 📋 Fase 4 - Planificado (Q3 2026)
- [ ] App móvil para administradores
- [ ] Modelo de detección de voz (voicemails de phishing)
- [ ] Análisis de videos
- [ ] Integración con más plataformas (Telegram, Signal)
- [ ] API pública para terceros

### 🎯 Fase 5 - Futuro (Q4 2026+)
- [ ] Red neuronal personalizada (reemplazar SVM)
- [ ] Detección de deepfakes
- [ ] Blockchain para auditoría inmutable
- [ ] Expansión a más países de Latinoamérica

---

## 🤝 Contribución

Este es un proyecto privado. Para contribuciones internas:

1. Crear branch desde `main`:
   ```bash
   git checkout -b feature/nueva-funcionalidad
   ```

2. Hacer cambios y commit:
   ```bash
   git add .
   git commit -m "feat: descripción del cambio"
   ```

3. Push y crear Pull Request:
   ```bash
   git push origin feature/nueva-funcionalidad
   ```

4. Solicitar code review

### Convenciones de Código

- **Python**: PEP 8
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/)
- **Branches**: `feature/`, `fix/`, `docs/`, `refactor/`
- **Testing**: Pytest para pruebas unitarias

---

## 📄 Licencia

**Proyecto Privado** - Todos los derechos reservados © 2026

Este software es propiedad privada y confidencial. No está permitido:
- Usar, copiar o modificar sin autorización
- Distribuir o sublicenciar
- Realizar ingeniería inversa

Para consultas sobre licenciamiento, contactar al administrador.

---

## 📞 Contacto y Soporte

**Desarrollado para la comunidad colombiana 🇨🇴**

- 📧 **Email de soporte**: [Configurar email]
- 💬 **WhatsApp**: [Número del bot en producción]
- 📱 **Administrador**: +57 350 589 4033

### Enlaces Útiles

- 📚 [Documentación de WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)
- 🤖 [DeepSeek AI Documentation](https://deepseek.com/docs)
- ☁️ [Google Cloud Run Docs](https://cloud.google.com/run/docs)
- 🐘 [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

## 🙏 Agradecimientos

- **Meta/Facebook** - WhatsApp Business API
- **DeepSeek** - IA avanzada para análisis contextual
- **Google Cloud** - Infraestructura serverless confiable
- **Comunidad Open Source** - Por las increíbles herramientas

---

## 📊 Estadísticas del Proyecto

![Python](https://img.shields.io/badge/Python-85%25-blue)
![SQL](https://img.shields.io/badge/SQL-10%25-orange)
![Markdown](https://img.shields.io/badge/Markdown-5%25-green)

**Líneas de código**: ~8,500  
**Archivos Python**: 15  
**Funciones**: 120+  
**Endpoints**: 3  
**Comandos admin**: 9  
**Tablas BD**: 3  

---

<div align="center">

### ⭐ Si este proyecto te ayuda a estar más seguro, considera dar una estrella ⭐

**SecurityBot-WA** - *Protegiendo a Colombia del phishing digital*

</div>
