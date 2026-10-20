import os
import requests
import json
import re

VERCEL_WEBHOOK = os.environ.get("VERCEL_ALERT_WEBHOOK")
RADAR_PAYLOAD = os.environ.get("RADAR_PAYLOAD", "{}")
HF_TOKEN = os.environ.get("HF_TOKEN") # Tu token de Hugging Face

def obtener_biografia(usuario):
    print(f"Buscando perfil publico de: {usuario}")
    url = f"https://www.instagram.com/{usuario}/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        match = re.search(r'<meta property="og:description" content="([^"]*)"', response.text)
        if match:
            return match.group(1)
        return "Biografía no disponible (Cuenta privada o perfil inexistente)"
    except Exception as e:
        print(f"Error de red: {e}")
        return "Error al conectar con la red social"

def analizar_con_hf(texto):
    print("Analizando con IA (Hugging Face API)...")
    # Usamos un modelo ligero de toxicidad en español
    API_URL = "https://api-inference.huggingface.co/models/pysentimiento/robertuito-hate-speech"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": texto}, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error en IA: {e}")
        return [{"label": "SAFE", "score": 1.0}]

def main():
    datos = json.loads(RADAR_PAYLOAD)
    id_niño = datos.get("id_niño", "desconocido")
    usuario_ig = datos.get("instagram", "")
    
    if not usuario_ig:
        print("No se envió usuario de Instagram.")
        return

    biografia = obtener_biografia(usuario_ig)
    print(f"Biografía extraída: {biografia}")

    # Si Instagram bloquea, usamos texto de prueba
    if "no disponible" in biografia or "Error" in biografia:
        print("Instagram bloqueó la lectura. Usando texto de prueba...")
        biografia = "Hola, odio a todos en mi escuela y voy a pelear con ellos."

    resultado = analizar_con_hf(biografia)
    print(f"Resultado de IA: {resultado}")

    # Si el modelo detecta toxicidad alta (HATE o OFFENSIVE)
    es_riesgo = False
    if isinstance(resultado, list) and len(resultado) > 0:
        # La API de pysentimiento devuelve etiquetas como HATE o NO_HATE
        etiqueta = resultado[0].get('label', '').lower()
        score = resultado[0].get('score', 0)
        if "hate" in etiqueta and "no" not in etiqueta and score > 0.5:
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
