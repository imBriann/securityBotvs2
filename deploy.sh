#!/bin/bash
# 🚀 Script de Deployment Rápido para Google Cloud Run
# SecurityBot-WA
# 
# USO: ./deploy.sh [OPCIÓN]
# OPCIONES:
#   quick    - Deploy rápido con env vars (para testing)
#   secure   - Deploy con Secret Manager (PRODUCCIÓN)
#   status   - Ver estado del servicio
#   logs     - Ver logs recientes
#   rollback - Rollback al revision anterior

set -e  # Exit on error

# ========== CONFIGURACIÓN ==========
PROJECT_ID="securitybot-485719"  # 🔴 CAMBIAR: Tu proyecto GCP
REGION="us-central1"              # 🔴 CAMBIAR: Tu región preferida
SERVICE_NAME="securitybot"
CLOUD_SQL_INSTANCE="securitybot-485719:us-central1:securitybot"  # 🔴 CAMBIAR: Tu instancia Cloud SQL

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ========== FUNCIONES ==========

print_header() {
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}================================${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_prerequisites() {
    print_header "Verificando prerequisitos"
    
    # Verificar gcloud
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI no está instalado"
        exit 1
    fi
    
    # Verificar proyecto
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
        print_warning "Proyecto actual: $CURRENT_PROJECT"
        echo "Cambiando a proyecto: $PROJECT_ID"
        gcloud config set project $PROJECT_ID
    fi
    
    echo "✅ Prerequisitos OK"
}

deploy_quick() {
    print_header "Deploy Rápido con Variables de Entorno"
    print_warning "¡ATENCIÓN! Este método expone las credenciales."
    print_warning "Solo usar para testing. Para producción, usa: ./deploy.sh secure"
    echo ""
    
    read -p "¿Continuar con deploy rápido? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    
    # Solicitar credenciales
    echo ""
    read -p "VERIFY_TOKEN: " VERIFY_TOKEN
    read -p "ACCESS_TOKEN: " ACCESS_TOKEN
    read -p "PHONE_NUMBER_ID: " PHONE_NUMBER_ID
    read -p "DEEPSEEK_API_KEY: " DEEPSEEK_API_KEY
    read -p "DATABASE_URL: " DATABASE_URL
    read -p "ADMIN_PHONE_NUMBER (sin +): " ADMIN_PHONE_NUMBER
    
    echo ""
    print_header "Iniciando deployment..."
    
    gcloud run deploy $SERVICE_NAME \
        --source . \
        --region $REGION \
        --platform managed \
        --allow-unauthenticated \
        --memory 512Mi \
        --cpu 1 \
        --timeout 300 \
        --max-instances 10 \
        --min-instances 0 \
        --set-env-vars "VERIFY_TOKEN=$VERIFY_TOKEN" \
        --set-env-vars "ACCESS_TOKEN=$ACCESS_TOKEN" \
        --set-env-vars "PHONE_NUMBER_ID=$PHONE_NUMBER_ID" \
        --set-env-vars "DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY" \
        --set-env-vars "DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions" \
        --set-env-vars "DATABASE_URL=$DATABASE_URL" \
        --set-env-vars "ADMIN_PHONE_NUMBER=$ADMIN_PHONE_NUMBER" \
        --add-cloudsql-instances $CLOUD_SQL_INSTANCE
        
    echo ""
    echo "✅ Deploy completado!"
    show_service_url
}

deploy_secure() {
    print_header "Deploy Seguro con Secret Manager"
    
    echo "Este método requiere que los secrets ya estén creados en Secret Manager."
    echo "Si no los has creado, ejecuta primero: ./deploy.sh create-secrets"
    echo ""
    
    read -p "¿Los secrets ya están creados? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Ejecuta: ./deploy.sh create-secrets"
        exit 1
    fi
    
    print_header "Iniciando deployment seguro..."
    
    gcloud run deploy $SERVICE_NAME \
        --source . \
        --region $REGION \
        --platform managed \
        --allow-unauthenticated \
        --memory 512Mi \
        --cpu 1 \
        --timeout 300 \
        --max-instances 10 \
        --min-instances 0 \
        --set-secrets "VERIFY_TOKEN=VERIFY_TOKEN:latest" \
        --set-secrets "ACCESS_TOKEN=ACCESS_TOKEN:latest" \
        --set-secrets "PHONE_NUMBER_ID=PHONE_NUMBER_ID:latest" \
        --set-secrets "DEEPSEEK_API_KEY=DEEPSEEK_API_KEY:latest" \
        --set-secrets "DATABASE_URL=DATABASE_URL:latest" \
        --set-secrets "ADMIN_PHONE_NUMBER=ADMIN_PHONE_NUMBER:latest" \
        --set-env-vars "DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions" \
        --add-cloudsql-instances $CLOUD_SQL_INSTANCE
        
    echo ""
    echo "✅ Deploy seguro completado!"
    show_service_url
}

create_secrets() {
    print_header "Crear Secrets en Secret Manager"
    
    echo "Se te pedirá ingresar cada credencial."
    echo "Los valores se almacenarán de forma segura en Secret Manager."
    echo ""
    
    read -p "VERIFY_TOKEN: " VERIFY_TOKEN
    echo -n "$VERIFY_TOKEN" | gcloud secrets create VERIFY_TOKEN --data-file=- 2>/dev/null || \
        echo -n "$VERIFY_TOKEN" | gcloud secrets versions add VERIFY_TOKEN --data-file=-
    
    read -p "ACCESS_TOKEN: " ACCESS_TOKEN
    echo -n "$ACCESS_TOKEN" | gcloud secrets create ACCESS_TOKEN --data-file=- 2>/dev/null || \
        echo -n "$ACCESS_TOKEN" | gcloud secrets versions add ACCESS_TOKEN --data-file=-
    
    read -p "PHONE_NUMBER_ID: " PHONE_NUMBER_ID
    echo -n "$PHONE_NUMBER_ID" | gcloud secrets create PHONE_NUMBER_ID --data-file=- 2>/dev/null || \
        echo -n "$PHONE_NUMBER_ID" | gcloud secrets versions add PHONE_NUMBER_ID --data-file=-
    
    read -p "DEEPSEEK_API_KEY: " DEEPSEEK_API_KEY
    echo -n "$DEEPSEEK_API_KEY" | gcloud secrets create DEEPSEEK_API_KEY --data-file=- 2>/dev/null || \
        echo -n "$DEEPSEEK_API_KEY" | gcloud secrets versions add DEEPSEEK_API_KEY --data-file=-
    
    read -p "DATABASE_URL: " DATABASE_URL
    echo -n "$DATABASE_URL" | gcloud secrets create DATABASE_URL --data-file=- 2>/dev/null || \
        echo -n "$DATABASE_URL" | gcloud secrets versions add DATABASE_URL --data-file=-
    
    read -p "ADMIN_PHONE_NUMBER (sin +, ej: 573001234567): " ADMIN_PHONE_NUMBER
    echo -n "$ADMIN_PHONE_NUMBER" | gcloud secrets create ADMIN_PHONE_NUMBER --data-file=- 2>/dev/null || \
        echo -n "$ADMIN_PHONE_NUMBER" | gcloud secrets versions add ADMIN_PHONE_NUMBER --data-file=-
    
    echo ""
    echo "✅ Secrets creados/actualizados exitosamente!"
    echo "Ahora puedes ejecutar: ./deploy.sh secure"
}

show_status() {
    print_header "Estado del Servicio"
    gcloud run services describe $SERVICE_NAME --region $REGION
}

show_logs() {
    print_header "Logs Recientes"
    gcloud run services logs read $SERVICE_NAME --region $REGION --limit 50
}

tail_logs() {
    print_header "Logs en Tiempo Real"
    echo "Presiona Ctrl+C para detener"
    gcloud run services logs tail $SERVICE_NAME --region $REGION
}

show_service_url() {
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)")
    echo ""
    echo "🌐 URL del servicio: $SERVICE_URL"
    echo ""
    echo "Prueba el health check:"
    echo "  curl $SERVICE_URL/health"
    echo ""
    echo "Configura el webhook de WhatsApp con:"
    echo "  URL: $SERVICE_URL/webhook"
    echo "  Verify Token: [tu VERIFY_TOKEN]"
}

rollback() {
    print_header "Rollback a Revision Anterior"
    
    # Listar revisiones
    echo "Revisiones disponibles:"
    gcloud run revisions list --service $SERVICE_NAME --region $REGION
    
    echo ""
    read -p "¿Hacer rollback a la revisión anterior? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    
    # Obtener la revisión anterior
    PREV_REVISION=$(gcloud run revisions list --service $SERVICE_NAME --region $REGION --format="value(metadata.name)" --limit=2 | tail -n 1)
    
    echo "Haciendo rollback a: $PREV_REVISION"
    gcloud run services update-traffic $SERVICE_NAME --region $REGION --to-revisions=$PREV_REVISION=100
    
    echo "✅ Rollback completado!"
}

test_deployment() {
    print_header "Test de Deployment"
    
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)" 2>/dev/null)
    
    if [ -z "$SERVICE_URL" ]; then
        print_error "Servicio no encontrado. ¿Ya hiciste deploy?"
        exit 1
    fi
    
    echo "Testing health check..."
    HEALTH_RESPONSE=$(curl -s "$SERVICE_URL/health")
    
    if [[ $HEALTH_RESPONSE == *"healthy"* ]]; then
        echo "✅ Health check OK: $HEALTH_RESPONSE"
    else
        print_error "Health check falló: $HEALTH_RESPONSE"
        exit 1
    fi
    
    echo ""
    echo "Testing webhook verification..."
    WEBHOOK_RESPONSE=$(curl -s "$SERVICE_URL/webhook?hub.mode=subscribe&hub.verify_token=test&hub.challenge=test123")
    
    if [ "$WEBHOOK_RESPONSE" == "test123" ]; then
        echo "✅ Webhook verification OK"
    else
        print_warning "Webhook verification necesita configuración"
    fi
}

# ========== MAIN ==========

case "$1" in
    quick)
        check_prerequisites
        deploy_quick
        ;;
    secure)
        check_prerequisites
        deploy_secure
        ;;
    create-secrets)
        check_prerequisites
        create_secrets
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    tail)
        tail_logs
        ;;
    test)
        test_deployment
        ;;
    rollback)
        check_prerequisites
        rollback
        ;;
    *)
        echo "🚀 SecurityBot - Script de Deployment"
        echo ""
        echo "Uso: ./deploy.sh [OPCIÓN]"
        echo ""
        echo "Opciones:"
        echo "  quick          Deploy rápido con env vars (testing)"
        echo "  secure         Deploy con Secret Manager (PRODUCCIÓN)"
        echo "  create-secrets Crear secrets en Secret Manager"
        echo "  status         Ver estado del servicio"
        echo "  logs           Ver logs recientes"
        echo "  tail           Ver logs en tiempo real"
        echo "  test           Test básico del deployment"
        echo "  rollback       Rollback a la versión anterior"
        echo ""
        echo "Ejemplo:"
        echo "  ./deploy.sh secure"
        exit 1
        ;;
esac
