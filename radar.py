import os
import requests
import json
import re
from transformers import pipeline

# 1. Configuración
VERCEL_WEBHOOK = os.environ.get("VERCEL_ALERT_WEBHOOK")
RADAR_PAYLOAD = os.environ.get("RADAR_PAYLOAD", "{}")

def obtener_biografia(usuario):
    print(f"Buscando perfil publico de: {usuario}")
    url = f"https://www.instagram.com/{usuario}/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # Extraemos la biografía desde la etiqueta meta de Instagram
        match = re.search(r'<meta property="og:description" content="([^"]*)"', response.text)
        if match:
            return match.group(1)
        return "Biografía no disponible (Cuenta privada o perfil inexistente)"
    except Exception as e:
        print(f"Error de red: {e}")
        return "Error al conectar con la red social"

def main():
    datos = json.loads(RADAR_PAYLOAD)
    id_niño = datos.get("id_niño", "desconocido")
    usuario_ig = datos.get("instagram", "")
    
    if not usuario_ig:
        print("No se envió usuario de Instagram.")
        return

    # 2. Obtener texto real del perfil
    biografia = obtener_biografia(usuario_ig)
    print(f"Biografía extraída: {biografia}")

    # Si no hay biografía, terminamos
    if "no disponible" in biografia or "Error" in biografia:
        print("No se pudo analizar el perfil.")
        return

    # 3. Análisis con IA Local (Hugging Face)
    print("Cargando modelo de IA de Hugging Face (Ciberacoso)...")
    classifier = pipeline("text-classification", model="JonatanGk/roberta-base-bne-finetuned-cyberbullying-spanish")
    
    resultado = classifier(biografia)[0]
    print(f"Resultado de IA: {resultado['label']} (Probabilidad: {resultado['score']:.2f})")

    # El modelo devuelve LABEL_1 para riesgo, LABEL_0 para seguro
    if resultado['label'] == "LABEL_1" and resultado['score'] > 0.50:
        alerta = {
            "id_niño": id_niño,
            "red_social": "Instagram",
            "tipo_riesgo": "Posible ciberacoso detectado en biografía",
            "fecha": "2026-10-19T12:00:00Z"
        }
        r = requests.post(VERCEL_WEBHOOK, json=alerta)
        print("Alerta enviada a Vercel:", r.status_code)
    else:
        print("Perfil seguro. No se envía alerta.")

if __name__ == "__main__":
    main()
