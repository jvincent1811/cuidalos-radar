import os
import requests
import json
from datetime import datetime, timezone

VERCEL_WEBHOOK = os.environ.get("VERCEL_ALERT_WEBHOOK")
RADAR_ANALISIS_WEBHOOK = os.environ.get("RADAR_ANALISIS_WEBHOOK")
RADAR_WEBHOOK_SECRET = os.environ.get("RADAR_WEBHOOK_SECRET")
RADAR_PAYLOAD = os.environ.get("RADAR_PAYLOAD", "{}")
HF_TOKEN = os.environ.get("HF_TOKEN")
APIFY_TOKEN = os.environ.get("APIFY_TOKEN")

def analizar_texto(texto):
    if not texto or texto == "no disponible" or texto == "error" or texto == "Perfil sin biografía": 
        return False
    
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

def revisar_instagram(usuario):
    print(f"Extrayendo perfil real de Instagram: {usuario} (Usando Apify)")
    url_run = "https://api.apify.com/v2/acts/apify~instagram-profile-scraper/run-sync-get-dataset-items"
    headers = {"Authorization": f"Bearer {APIFY_TOKEN}", "Content-Type": "application/json"}
    payload = {"usernames": [usuario]}
    
    try:
        r = requests.post(url_run, headers=headers, json=payload, timeout=60)
        if r.status_code in [200, 201]:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                perfil = data[0]
                # Extraemos si es privado
                es_privado = perfil.get('is_private', False)
                bio = perfil.get('biography') or perfil.get('bio') or perfil.get('description') or ""
                
                estado = "privado" if es_privado else "publico"
                return {"red": "Instagram", "estado": estado, "biografia": bio}
        return {"red": "Instagram", "estado": "no_encontrado", "biografia": ""}
    except Exception as e:
        print(f"Error de conexión con Apify: {e}")
        return {"red": "Instagram", "estado": "error", "biografia": ""}

def main():
    try:
        datos = json.loads(RADAR_PAYLOAD) if RADAR_PAYLOAD else {}
    except:
        datos = {}
    
    if not datos or not datos.get("id_niño"):
        print("No se recibieron datos válidos desde Bilt. Cancelando análisis para ahorrar créditos.")
        return

    id_niño = datos.get("id_niño")
    usuario_ig = datos.get("instagram", "")
    
    resultados_redes = []
    alertas_detectadas = []

    if usuario_ig:
        print(f"--- Revisando Instagram: {usuario_ig} ---")
        resultado = revisar_instagram(usuario_ig)
        
        # Solo analizamos si es público y tiene biografía
        if resultado["estado"] == "publico" and resultado["biografia"]:
            print(f"Biografía extraída: {resultado['biografia']}")
            if analizar_texto(resultado["biografia"]):
                print("¡ALERTA en Instagram!")
                alertas_detectadas.append("Instagram")
                resultado["riesgo"] = True
            else:
                resultado["riesgo"] = False
        else:
            print(f"Perfil {resultado['estado']} o sin biografía. No se analiza texto.")
            resultado["riesgo"] = False
            
        resultados_redes.append(resultado)

    # 1. Enviar alertas si hay riesgo
    if alertas_detectadas:
        alerta = {
            "id_niño": id_niño,
            "red_social": ", ".join(alertas_detectadas),
            "tipo_riesgo": "Posible ciberacoso detectado",
            "fecha": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        r = requests.post(VERCEL_WEBHOOK, json=alerta)
        print("Alerta enviada a Vercel:", r.status_code)
    else:
        print("Perfiles seguros. No se envía alerta de riesgo.")

    # 2. Reportar finalización a Bilt (Con el detalle por red)
    print("Reportando estado final a Bilt...")
    fecha_utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    status_bilt = {
        "id_niño": id_niño,
        "fecha": fecha_utc,
        "sin_riesgos": len(alertas_detectadas) == 0,
        "redes": resultados_redes # <-- AQUÍ ENVIAMOS EL DETALLE POR RED
    }
    
    if RADAR_ANALISIS_WEBHOOK and RADAR_WEBHOOK_SECRET:
        headers_bilt = {
            "Content-Type": "application/json",
            "x-radar-secret": RADAR_WEBHOOK_SECRET
        }
        try:
            rb = requests.post(RADAR_ANALISIS_WEBHOOK, json=status_bilt, headers=headers_bilt, timeout=10)
            print("Confirmación enviada a Bilt:", rb.status_code, rb.text)
        except Exception as e:
            print("Error al reportar a Bilt:", e)
    else:
        print("Faltan secretos de Bilt. No se pudo reportar.")

if __name__ == "__main__":
    main()
