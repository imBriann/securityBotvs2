import os
from dotenv import load_dotenv
import uvicorn
from app.api.whatsapp_webhook import app
from app.storage.users_state import setup_database

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

if __name__ == "__main__":
    print("Iniciando servidor FastAPI localmente con Uvicorn...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)