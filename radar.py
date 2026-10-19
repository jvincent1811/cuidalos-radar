import os
import requests

# 1. Configuración
HF_TOKEN = os.environ.get("HF_TOKEN")
VERCEL_WEBHOOK = os.environ.get("VERCEL_ALERT_WEBHOOK")

# Datos de prueba (Luego Bilt enviará estos datos)
usuario_instagram = "usuario_prueba_123" 
id_niño = "niño_123"

def analizar_con_huggingface(texto):
    print(f"Analizando texto: {texto}")
    API_URL = "https://api-inference.huggingface.co/models/tanaos/tanaos-guardrail-spanish"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": texto}
    
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()

def main():
    # Aquí iría la búsqueda real. Para prueba, usamos un texto simulado.
    bio_simulada = "Hola, me gusta el futbol y odio a todos"
    
    resultado = analizar_con_huggingface(bio_simulada)
    print("Resultado de la IA:", resultado)

    # Si la IA detecta riesgo, enviamos alerta a Vercel
    # (Esto es un ejemplo simplificado para probar el flujo)
    es_peligroso = True # Cambiaremos esto por la lógica real de la IA después
    
    if es_peligroso:
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
