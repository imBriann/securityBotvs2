import os
import sys
from dotenv import load_dotenv
import uvicorn
from app.api.whatsapp_webhook import app
from app.storage.users_state import setup_database
from app.services.svm_classifier import initialize_svm

# Cargar variables de entorno (para desarrollo local)
load_dotenv()

print("="*60)
print("🚀 SecurityBot-WA - Iniciando...")
print("="*60)

# Obtener puerto de Cloud Run o usar default
PORT = int(os.getenv("PORT", "8080"))
print(f"📡 Puerto configurado: {PORT}")

# Validar variables de entorno CRÍTICAS
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
ADMIN_PHONE_NUMBER = os.getenv("ADMIN_PHONE_NUMBER")
DATABASE_URL = os.getenv("DATABASE_URL")

print("\n🔍 Verificando variables de entorno...")
print(f"  VERIFY_TOKEN: {'✅ OK' if VERIFY_TOKEN else '❌ FALTA'}")
print(f"  ACCESS_TOKEN: {'✅ OK' if ACCESS_TOKEN else '❌ FALTA'}")
print(f"  PHONE_NUMBER_ID: {'✅ OK' if PHONE_NUMBER_ID else '❌ FALTA'}")
print(f"  DEEPSEEK_API_KEY: {'✅ OK' if DEEPSEEK_API_KEY else '❌ FALTA'}")
print(f"  ADMIN_PHONE_NUMBER: {'✅ OK' if ADMIN_PHONE_NUMBER else '⚠️  FALTA (comandos admin deshabilitados)'}")
print(f"  DATABASE_URL: {'✅ OK' if DATABASE_URL else '❌ FALTA'}")

# Validar variables críticas (sin admin que es opcional)
critical_vars = {
    "VERIFY_TOKEN": VERIFY_TOKEN,
    "ACCESS_TOKEN": ACCESS_TOKEN,
    "PHONE_NUMBER_ID": PHONE_NUMBER_ID,
    "DEEPSEEK_API_KEY": DEEPSEEK_API_KEY,
    "DATABASE_URL": DATABASE_URL
}

missing_vars = [var for var, value in critical_vars.items() if not value]

if missing_vars:
    print("\n❌ ERROR CRÍTICO: Faltan variables de entorno OBLIGATORIAS:")
    for var in missing_vars:
        print(f"   - {var}")
    print("\n💡 En Cloud Run, configura estas variables como secrets o env vars.")
    print("💡 Para desarrollo local, crea el archivo app/.env")
    sys.exit(1)

if not ADMIN_PHONE_NUMBER:
    print("\n⚠️  ADVERTENCIA: ADMIN_PHONE_NUMBER no configurado.")
    print("   Los comandos administrativos no funcionarán.")

print("\n✅ Todas las variables críticas están configuradas.\n")

# Configurar base de datos al inicio
print("🔄 Configurando base de datos PostgreSQL...")
try:
    setup_database()
    print("✅ Base de datos configurada correctamente.")
except Exception as e:
    print(f"❌ Error configurando base de datos: {e}")
    print("⚠️  El bot continuará pero las funciones de BD pueden fallar.")

# Inicializar modelo SVM para análisis de phishing
print("🔄 Inicializando modelo SVM de detección de phishing...")
try:
    if initialize_svm():
        print("✅ Modelo SVM listo para usar")
    else:
        print("⚠️  Advertencia: Modelo SVM no disponible, se usará solo DeepSeek para análisis")
except Exception as e:
    print(f"⚠️  Error inicializando SVM: {e}")
    print("   El bot continuará con análisis solo de DeepSeek.")

print("\n" + "="*60)
print("✅ SecurityBot-WA listo para recibir conexiones")
print(f"🌐 Escuchando en puerto {PORT}")
print("="*60 + "\n")

if __name__ == "__main__":
    print("💻 Modo desarrollo local - Iniciando con uvicorn...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)