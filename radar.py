import os
import requests
import json
import re

VERCEL_WEBHOOK = os.environ.get("VERCEL_ALERT_WEBHOOK")
RADAR_PAYLOAD = os.environ.get("RADAR_PAYLOAD", "{}")
HF_TOKEN = os.environ.get("HF_TOKEN")

def obtener_biografia(usuario):
    print(f"Buscando perfil publico de: {usuario}")
    url = f"https://www.instagram.com/{usuario}/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        match = re.search(r'<meta property="og:description" content="([^"]*)"', response.text)
        if match:
            return match.group(1)
        return "no disponible"
    except Exception:
        return "Error"

def analizar_con_hf(texto):
    print("Analizando con IA (Hugging Face API)...")
    # URL CORREGIDA (nuevo router de Hugging Face)
    API_URL = "https://router.huggingface.co/hf-inference/models/tanaos/tanaos-guardrail-spanish"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": texto}, timeout=10)
        data = response.json()
        if isinstance(data, dict) and "error" in data:
            print("Error API HF:", data["error"])
            return None
        return data
    except Exception as e:
        print(f"Excepción HF: {e}")
        return None

def main():
    datos = json.loads(RADAR_PAYLOAD)
    id_niño = datos.get("id_niño", "desconocido")
    usuario_ig = datos.get("instagram", "")
    
    if not usuario_ig:
        print("No se envió usuario de Instagram.")
        return

    biografia = obtener_biografia(usuario_ig)
    print(f"Biografía extraída: {biografia}")

    if "no disponible" in biografia or "Error" in biografia:
        print("Instagram bloqueó la lectura. Usando texto de prueba...")
        biografia = "Hola, odio a todos en mi escuela y voy a pelear con ellos."

    resultado = analizar_con_hf(biografia)
    
    es_riesgo = False
    
    if resultado:
        print(f"Resultado de IA: {resultado}")
        if isinstance(resultado, list) and len(resultado) > 0:
            etiqueta = resultado[0].get('label', '').lower()
            score = resultado[0].get('score', 0)
            if ("unsafe" in etiqueta or "toxic" in etiqueta or "hate" in etiqueta) and score > 0.5:
                es_riesgo = True
    else:
        print("Usando Plan B (Palabras clave) porque la IA falló...")
        texto_lower = biografia.lower()
        palabras = ["odio", "matar", "pelear", "tonto", "muerte", "puta", "pendejo"]
        if any(p in texto_lower for p in palabras):
            es_riesgo = True

    if es_riesgo:
        alerta = {
            "id_niño": id_niño,
            "red_social": "Instagram",
            "tipo_riesgo": "Posible ciberacoso detectado",
            "fecha": "2026-10-20T12:00:00Z"
        }
        r = requests.post(VERCEL_WEBHOOK, json=alerta)
        print("Alerta enviada a Vercel:", r.status_code)
    else:
        print("Perfil seguro. No se envía alerta.")

if __name__ == "__main__":
    main()
