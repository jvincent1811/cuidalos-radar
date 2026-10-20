import os
import requests
import json

VERCEL_WEBHOOK = os.environ.get("VERCEL_ALERT_WEBHOOK")
RADAR_PAYLOAD = os.environ.get("RADAR_PAYLOAD", "{}")
HF_TOKEN = os.environ.get("HF_TOKEN")
APIFY_TOKEN = os.environ.get("APIFY_TOKEN")

def analizar_texto(texto):
    if not texto or texto == "no disponible": return False
    
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
    
    # Usamos directUrls que es el formato estándar de Apify
    url_run = "https://api.apify.com/v2/acts/apify~instagram-profile-scraper/run-sync-get-dataset-items"
    headers = {"Authorization": f"Bearer {APIFY_TOKEN}", "Content-Type": "application/json"}
    payload = {"directUrls": [f"https://www.instagram.com/{usuario}/"]}
    
    try:
        r = requests.post(url_run, headers=headers, json=payload, timeout=60)
        print(f"Diagnóstico Apify - Status: {r.status_code}")
        
        if r.status_code in [200, 201]:
            data = r.json()
            print(f"Diagnóstico Apify - Elementos recibidos: {len(data)}")
            if isinstance(data, list) and len(data) > 0:
                bio = data[0].get('biography', '')
                return bio if bio else "Perfil sin biografía"
            return "Perfil no encontrado"
        else:
            print(f"Diagnóstico Apify - Error: {r.text}")
            return "Error en API"
    except Exception as e:
        print(f"Error de conexión con Apify: {e}")
        return "error"

def main():
    datos = json.loads(RADAR_PAYLOAD)
    id_niño = datos.get("id_niño", "desconocido")
    
    redes = {
        "Instagram": datos.get("instagram")
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

    if alertas_detectadas:
        alerta = {
            "id_niño": id_niño,
            "red_social": ", ".join(alertas_detectadas),
            "tipo_riesgo": "Posible ciberacoso detectado",
            "fecha": "2026-10-20T12:00:00Z"
        }
        r = requests.post(VERCEL_WEBHOOK, json=alerta)
        print("Alerta enviada a Vercel:", r.status_code)
    else:
        print("Perfiles seguros. No se envía alerta.")

if __name__ == "__main__":
    main()
