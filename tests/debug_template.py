import os
import requests
import json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# CONFIGURACIÓN
TOKEN = "EAAIUbXSn5WcBP9VSMhjvpkdnlbuZCZCKmyPSyJFPRuhAxsJ3SOdom5I6ktLx6NoFIUGPtJteSlmnASHJATqkCJ2lkHjJm4xDFaCMfTxeF6VI9pwOoJOChdYCbE1kQ6Csidf5pnwCA6qR0nO4FDjezHf3MhOUaAZB8fsPZCuZCdU8BCXPNeVMWfJZAhsptDq2lP1gZDZD"
URL = "https://graph.facebook.com/v18.0/588185097722099/messages"
TELEFONO = "573505894033" # Tu número (el que sale en los logs)
TEMPLATE_NAME = "feedback_analisis"
IDIOMA = "es_CO" # Probamos con Colombia primero
NOMBRE_VAR = "Brian"

def probar_envio(nombre_prueba, componentes):
    print(f"\n🧪 PROBANDO: {nombre_prueba}...")
    
    payload = {
        "messaging_product": "whatsapp",
        "to": TELEFONO,
        "type": "template",
        "template": {
            "name": TEMPLATE_NAME,
            "language": {"code": IDIOMA},
            "components": componentes
        }
    }
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(URL, headers=headers, json=payload)
        datos = response.json()
        
        if response.status_code == 200:
            print("✅ ¡ÉXITO! Meta aceptó el mensaje.")
            print(f"📩 Respuesta: {json.dumps(datos, indent=2)}")
            return True
        else:
            print("❌ FALLÓ.")
            print(f"⚠️ Error: {json.dumps(datos, indent=2)}")
            return False
            
    except Exception as e:
        print(f"💥 Error de conexión: {e}")
        return False

# --- INTENTO 1: Variable en BODY con 'parameter_name' (La forma 'correcta' nueva) ---
c1 = [{
    "type": "body",
    "parameters": [
        {
            "type": "text",
            "parameter_name": "nombre", # El nombre exacto de la variable {{nombre}}
            "text": NOMBRE_VAR
        }
    ]
}]

# --- INTENTO 2: Variable en BODY posicional (La forma clásica {{1}}) ---
c2 = [{
    "type": "body",
    "parameters": [
        {
            "type": "text",
            "text": NOMBRE_VAR
        }
    ]
}]

# --- INTENTO 3: Variable en HEADER (Por si acaso está en negrita arriba) ---
c3 = [{
    "type": "header",
    "parameters": [
        {
            "type": "text",
            "text": NOMBRE_VAR
        }
    ]
}]

print("🔎 INICIANDO DIAGNÓSTICO DE PLANTILLA WHATSAPP")
print("------------------------------------------------")

if probar_envio("Opción 1 (Named Params)", c1):
    print("\n🏆 LA SOLUCIÓN ES: Usar parameter_name='nombre'")
elif probar_envio("Opción 2 (Positional Params)", c2):
    print("\n🏆 LA SOLUCIÓN ES: Usar solo text (sin parameter_name)")
elif probar_envio("Opción 3 (Header Params)", c3):
    print("\n🏆 LA SOLUCIÓN ES: Cambiar 'body' por 'header'")
else:
    print("\n💀 TODAS FALLARON. Revisa el nombre de la plantilla o el idioma en Meta.")