import os
import requests
from flask import Flask, request, jsonify
from transformers import pipeline

app = Flask(__name__)

# Cargamos la IA UNA SOLA VEZ en la memoria de Railway
print("Cargando modelo de IA en memoria...")
classifier = pipeline("text-classification", model="JonatanGk/roberta-base-bne-finetuned-cyberbullying-spanish")
print("Modelo cargado y listo.")

VERCEL_WEBHOOK = os.environ.get("VERCEL_ALERT_WEBHOOK")

@app.route('/radar', methods=['POST'])
def analizar():
    datos = request.json
    id_niño = datos.get("id_niño", "desconocido")
    usuario_ig = datos.get("instagram", "")

    if not usuario_ig:
        return jsonify({"error": "Falta usuario de Instagram"}), 400

    # Por ahora usamos el texto de prueba (luego conectaremos el scraping real)
    biografia = "Hola, odio a todos en mi escuela y voy a pelear con ellos."
    
    resultado = classifier(biografia)[0]
    etiqueta = resultado['label'].lower()

    # Si hay riesgo, enviamos la alerta a Vercel
    if "not" not in etiqueta and resultado['score'] > 0.5:
        alerta = {
            "id_niño": id_niño,
            "red_social": "Instagram",
            "tipo_riesgo": f"Posible ciberacoso ({resultado['label']})",
            "fecha": "2026-10-20T12:00:00Z"
        }
        requests.post(VERCEL_WEBHOOK, json=alerta)
        print("Alerta enviada a Vercel")
        return jsonify({"status": "Alerta enviada"}), 200
    
    return jsonify({"status": "Perfil seguro"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
