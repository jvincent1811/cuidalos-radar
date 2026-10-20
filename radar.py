import os
import requests
import json
import time

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
    
    # Lanzamos el "Actor" de Apify para Instagram
    url_run = "https://api.apify.com/v2/acts/apify~instagram-profile-scraper/run-sync-get-dataset-items"
    headers = {"Authorization": f"Bearer {APIFY_TOKEN}", "Content-Type": "application/json"}
    payload = {"usernames": [usuario]}
    
    try:
        r = requests.post(url_run, headers=headers, json=payload, timeout=60)
        if r.status_code in [200, 201]:
            data = r.json()
            if data and len(data) > 0:
                # Apify nos devuelve la biografía en el campo 'biography'
                bio = data[0].get('biography', '')
                return bio if bio else "no disponible"
        return "no disponible"
    except Exception as e:
        print(f"Error de Apify: {e}")
        return "error"

def main():
    datos = json.loads(RADAR_PAYLOAD)
    id_niño = datos.get("id_niño", "desconocido")
    
    redes = {
        "Instagram": datos.get("instagram"),
        "Roblox": datos.get("roblox")
    }

    alertas_detectadas = []

    for red, usuario in redes.items():
        if not usuario: continue
        print(f"--- Revisando {red}: {usuario} ---")
        
        biografia = ""
        if red == "Instagram":
            biografia = obtener_biografia_instagram(usuario)
        elif red == "Roblox":
            # El código de Roblox que ya teníamos (ese sí funciona gratis)
            try:
                res = requests.post("https://users.roblox.com/v1/usernames/users", json={"usernames": [usuario], "excludeBannedUsers": True}, timeout=10)
                data = res.json()
                if data.get("data"):
                    user_id = data["data"][0]["id"]
                    desc_res = requests.get(f"https://users.roblox.com/v1/users/{user_id}", timeout=10)
                    biografia = desc_res.json().get("description", "")
            except:
                biografia = "error"
        
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
