import os
import requests
import json
from datetime import datetime, timezone

VERCEL_WEBHOOK = os.environ.get("VERCEL_ALERT_WEBHOOK")
RADAR_ANALISIS_WEBHOOK = os.environ.get("RADAR_ANALISIS_WEBHOOK")
RADAR_WEBHOOK_SECRET = os.environ.get("RADAR_WEBHOOK_SECRET")
RADAR_PAYLOAD = os.environ.get("RADAR_PAYLOAD", "{}")
HF_TOKEN = os.environ.get("HF_TOKEN")
APIFY_TOKEN = os.environ.get("APIFY_TOKEN")

def analizar_texto(texto):
    if not texto or texto == "no disponible" or texto == "error" or texto == "Perfil sin biografía": return False
    
    print(f"Analizando texto con IA: '{texto[:50]}...'")
    API_URL = "https://router.huggingface.co/hf-inference/models/tanaos/tanaos-guardrail-spanish"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": texto}, timeout=10)
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            etiqueta = data[0].get('label', '').lower()
            score = data[0].get('score', 0)
            if ("unsafe" in etiqueta or "toxic" in etiqueta or "hate" in etiqueta) and score > 0.5:
                return True
    except Exception:
        pass

    print("Usando Plan B (Palabras clave)...")
    palabras_riesgo = ["odio", "matar", "pelear", "tonto", "muerte", "puta", "pendejo", "gorda", "feo"]
    return any(p in texto.lower() for p in palabras_riesgo)

def obtener_biografia_instagram(usuario):
    print(f"Extrayendo perfil real de Instagram: {usuario} (Usando Apify)")
    
    url_run = "https://api.apify.com/v2/acts/apify~instagram-profile-scraper/run-sync-get-dataset-items"
    headers = {"Authorization": f"Bearer {APIFY_TOKEN}", "Content-Type": "application/json"}
    payload = {"usernames": [usuario]}
    
    try:
        r = requests.post(url_run, headers=headers, json=payload, timeout=60)
        print(f"Diagnóstico Apify - Status: {r.status_code}")
        
        if r.status_code in [200, 201]:
            data = r.json()
            print(f"Diagnóstico Apify - Elementos recibidos: {len(data)}")
            if isinstance(data, list) and len(data) > 0:
                perfil = data[0]
                bio = perfil.get('biography') or perfil.get('bio') or perfil.get('description')
                if bio:
                    return bio
                return "Perfil sin biografía"
            return "Perfil no encontrado"
        return "Error en API"
    except Exception as e:
        print(f"Error de conexión con Apify: {e}")
        return "error"

def main():
    try:
        datos = json.loads(RADAR_PAYLOAD) if RADAR_PAYLOAD else {}
    except:
        datos = {}
    
    # Valores por defecto para prueba manual en GitHub
    if not datos:
        print("Ejecución manual detectada. Usando valores de prueba.")
        datos = {
            "id_niño": "12345678-1234-1234-1234-123456789012", # UUID de prueba
            "instagram": "iJesusbernal" # Perfil de prueba
        }

    id_niño = datos.get("id_niño", "desconocido")
    usuario_ig = datos.get("instagram", "")
    
    redes = {
        "Instagram": usuario_ig
    }

    alertas_detectadas = []

    for red, usuario in redes.items():
        if not usuario: continue
        print(f"--- Revisando {red}: {usuario} ---")
        
        biografia = obtener_biografia_instagram(usuario)
        print(f"Biografía extraída: {biografia}")

        if analizar_texto(biografia):
            print(f"¡ALERTA en {red}!")
            alertas_detectadas.append(red)

    # 1. Enviar alertas si hay riesgo
    if alertas_detectadas:
        alerta = {
            "id_niño": id_niño,
            "red_social": ", ".join(alertas_detectadas),
            "tipo_riesgo": "Posible ciberacoso detectado",
            "fecha": datetime.now(timezone.utc).isoformat()
        }
        r = requests.post(VERCEL_WEBHOOK, json=alerta)
        print("Alerta enviada a Vercel:", r.status_code)
    else:
        print("Perfiles seguros. No se envía alerta de riesgo.")

    # 2. Reportar finalización a Bilt
    print("Reportando estado final a Bilt...")
    fecha_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    status_bilt = {
        "id_niño": id_niño,
        "fecha": fecha_utc,
        "sin_riesgos": len(alertas_detectadas) == 0
    }
    
    if RADAR_ANALISIS_WEBHOOK and RADAR_WEBHOOK_SECRET:
        headers_bilt = {
            "Content-Type": "application/json",
            "x-radar-secret": RADAR_WEBHOOK_SECRET
        }
        try:
            rb = requests.post(RADAR_ANALISIS_WEBHOOK, json=status_bilt, headers=headers_bilt, timeout=10)
            print("Confirmación enviada a Bilt:", rb.status_code, rb.text)
        except Exception as e:
            print("Error al reportar a Bilt:", e)
    else:
        print("Faltan secretos de Bilt. No se pudo reportar.")

if __name__ == "__main__":
    main()
