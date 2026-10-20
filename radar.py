import os
import requests
import json
import re

VERCEL_WEBHOOK = os.environ.get("VERCEL_ALERT_WEBHOOK")
RADAR_PAYLOAD = os.environ.get("RADAR_PAYLOAD", "{}")
HF_TOKEN = os.environ.get("HF_TOKEN")

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

def obtener_biografia_real(usuario, red):
    print(f"Extrayendo perfil real de {red.capitalize()}: {usuario} (Usando Jina AI Reader)")
    
    # Jina AI lee la página web desde sus servidores, evadiendo bloqueos
    if red.lower() == "instagram":
        url = f"https://r.jina.ai/https://www.instagram.com/{usuario}/"
    elif red.lower() == "tiktok":
        url = f"https://r.jina.ai/https://www.tiktok.com/@{usuario}"
    elif red.lower() == "facebook":
        url = f"https://r.jina.ai/https://www.facebook.com/{usuario}"
    else:
        return "no disponible"

    try:
        # Jina nos devuelve el texto limpio de la página
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            # Buscamos la etiqueta de descripción que es donde va la biografía
            match = re.search(r'(?:Description:|og:description.*?content=")([^"\n]+)', r.text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "no disponible"
    except Exception as e:
        print(f"Error de conexión con Jina: {e}")
        return "error"

def main():
    datos = json.loads(RADAR_PAYLOAD)
    id_niño = datos.get("id_niño", "desconocido")
    
    redes = {
        "Instagram": datos.get("instagram"),
        "TikTok": datos.get("tiktok"),
        "Facebook": datos.get("facebook")
    }

    alertas_detectadas = []

    for red, usuario in redes.items():
        if not usuario: continue
        print(f"--- Revisando {red}: {usuario} ---")
        
        biografia = obtener_biografia_real(usuario, red)
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
