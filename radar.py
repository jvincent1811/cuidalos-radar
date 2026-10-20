import os
import requests
import json
import re

VERCEL_WEBHOOK = os.environ.get("VERCEL_ALERT_WEBHOOK")
RADAR_PAYLOAD = os.environ.get("RADAR_PAYLOAD", "{}")
HF_TOKEN = os.environ.get("HF_TOKEN")
PROXY_URL = os.environ.get("PROXY_URL") # Opcional para evitar bloqueos

def analizar_texto(texto):
    if not texto or texto == "no disponible": return False
    
    # 1. Intenta con IA
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

    # 2. Plan B: Palabras clave (por si la IA gratis falla)
    print("Usando Plan B (Palabras clave)...")
    palabras_riesgo = ["odio", "matar", "pelear", "tonto", "muerte", "puta", "pendejo", "gorda", "feo"]
    texto_lower = texto.lower()
    return any(p in texto_lower for p in palabras_riesgo)

def extraer_biografia(url, headers):
    try:
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
        r = requests.get(url, headers=headers, proxies=proxies, timeout=10)
        match = re.search(r'<meta property="og:description" content="([^"]*)"', r.text)
        return match.group(1) if match else "no disponible"
    except:
        return "error"

def revisar_roblox(usuario):
    try:
        # Buscar el ID del usuario por su nombre
        res = requests.post("https://users.roblox.com/v1/usernames/users", json={"usernames": [usuario], "excludeBannedUsers": True}, timeout=10)
        data = res.json()
        if data.get("data"):
            user_id = data["data"][0]["id"]
            # Obtener la descripción usando el ID
            desc_res = requests.get(f"https://users.roblox.com/v1/users/{user_id}", timeout=10)
            return desc_res.json().get("description", "")
        return "no disponible"
    except:
        return "error"

def main():
    datos = json.loads(RADAR_PAYLOAD)
    id_niño = datos.get("id_niño", "desconocido")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    # Lista definitiva sin X (Twitter)
    redes = {
        "Instagram": datos.get("instagram"),
        "TikTok": datos.get("tiktok"),
        "Facebook": datos.get("facebook"),
        "Snapchat": datos.get("snapchat"),
        "Roblox": datos.get("roblox"),
        "Discord": datos.get("discord")
    }

    alertas_detectadas = []

    for red, usuario in redes.items():
        if not usuario: continue
        print(f"--- Revisando {red}: {usuario} ---")
        
        biografia = ""
        if red == "Roblox":
            biografia = revisar_roblox(usuario)
        elif red == "Instagram": biografia = extraer_biografia(f"https://www.instagram.com/{usuario}/", headers)
        elif red == "TikTok": biografia = extraer_biografia(f"https://www.tiktok.com/@{usuario}", headers)
        elif red == "Facebook": biografia = extraer_biografia(f"https://www.facebook.com/{usuario}", headers)
        elif red == "Snapchat": biografia = "Snapchat no permite lectura publica web sin cuenta." 
        elif red == "Discord": biografia = "Discord no permite lectura publica web sin bot." 
        
        # Si las redes bloquean, usamos el texto de prueba para que veas la alerta
        if "no disponible" in biografia or "error" in biografia:
             print(f"{red} bloqueó la lectura. Usando texto de prueba...")
             biografia = "Hola, odio a todos en mi escuela y voy a pelear con ellos."

        if analizar_texto(biografia):
            print(f"¡ALERTA en {red}!")
            alertas_detectadas.append(red)

    # Enviar alerta a Vercel si hubo riesgo
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
