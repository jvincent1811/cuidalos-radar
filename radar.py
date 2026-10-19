import os
import requests

# 1. Configuración
HF_TOKEN = os.environ.get("HF_TOKEN")
VERCEL_WEBHOOK = os.environ.get("VERCEL_ALERT_WEBHOOK")

# Datos de prueba
id_niño = "niño_123"

def analizar_con_huggingface(texto):
    print(f"Analizando texto: {texto}")
    API_URL = "https://router.huggingface.co/hf-inference/models/tanaos/tanaos-guardrail-spanish"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": texto}
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        data = response.json()
        # Si Hugging Face responde con un error, usamos el plan B
        if isinstance(data, dict) and "error" in data:
            print("Hugging Face falló. Usando análisis de palabras clave...")
            return revisar_palabras(texto)
        return data
    except Exception as e:
        print("Error de conexión con IA. Usando análisis de palabras clave...")
        return revisar_palabras(texto)

def revisar_palabras(texto):
    texto = texto.lower()
    palabras_riesgo = ["odio", "matar", "tonto", "feo", "golpear", "muerte"]
    for palabra in palabras_riesgo:
        if palabra in texto:
            return [{"label": "TOXIC", "score": 0.9}]
    return [{"label": "SAFE", "score": 0.99}]

def main():
    bio_simulada = "Hola, me gusta el futbol y odio a todos"
    
    resultado = analizar_con_huggingface(bio_simulada)
    print("Resultado de la IA:", resultado)

    # El radar detecta riesgo y envía la alerta
    alerta = {
        "id_niño": id_niño,
        "red_social": "Instagram",
        "tipo_riesgo": "Lenguaje sospechoso detectado",
        "fecha": "2026-10-19T12:00:00Z"
    }
    
    r = requests.post(VERCEL_WEBHOOK, json=alerta)
    print("Alerta enviada a Vercel:", r.status_code)

if __name__ == "__main__":
    main()
