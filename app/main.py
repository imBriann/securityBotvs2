import os
from dotenv import load_dotenv
import uvicorn
from app.api.whatsapp_webhook import app
from app.storage.users_state import setup_database
from app.services.svm_classifier import initialize_svm

load_dotenv()

# Validar variables de entorno críticas
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not all([VERIFY_TOKEN, ACCESS_TOKEN, PHONE_NUMBER_ID, DEEPSEEK_API_KEY]):
    print("ERROR CRÍTICO: Una o más variables de entorno no están configuradas.")
    exit(1)

# Configurar base de datos al inicio
setup_database()

# Inicializar modelo SVM para análisis de phishing
print("🔄 Inicializando modelo SVM de detección de phishing...")
if initialize_svm():
    print("✅ Modelo SVM listo para usar")
else:
    print("⚠️ Advertencia: Modelo SVM no disponible, se usará solo DeepSeek para análisis")

if __name__ == "__main__":
    print("Iniciando servidor FastAPI localmente con Uvicorn...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)