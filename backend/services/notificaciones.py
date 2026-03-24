import os
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Twilio SMS (fallback) ──
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

twilio_client = None
if TWILIO_SID and TWILIO_TOKEN:
    from twilio.rest import Client
    twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)

# ── WhatsApp Cloud API (Meta) ──
WA_TOKEN    = os.getenv("WHATSAPP_TOKEN", "")
WA_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
WA_API_URL  = f"https://graph.facebook.com/v21.0/{WA_PHONE_ID}/messages"


def enviar_whatsapp(destinatario: str, nombre_vecino: str, ubicacion: str) -> bool:
    """Envía alerta por WhatsApp Cloud API (Meta) con mensaje de texto libre."""
    if not WA_TOKEN or not WA_PHONE_ID:
        print("⚠️ WhatsApp Cloud API no configurado (faltan WHATSAPP_TOKEN o WHATSAPP_PHONE_ID)")
        return False

    num_limpio = str(destinatario).replace(" ", "").replace("-", "")
    if num_limpio.startswith("+"):
        num_limpio = num_limpio[1:]

    # Mensaje de texto libre (funciona en la ventana de 24h o con números de prueba)
    payload = {
        "messaging_product": "whatsapp",
        "to": num_limpio,
        "type": "text",
        "text": {
            "preview_url": True,
            "body": (
                f"🚨 *ALERTA DE EMERGENCIA - SISDEL* 🚨\n\n"
                f"Se ha recibido una alerta de pánico de:\n"
                f"👤 *{nombre_vecino}*\n"
                f"📍 Ubicación: {ubicacion}\n\n"
                f"Nuestras unidades han sido notificadas.\n"
                f"Si usted es familiar, manténgase informado.\n\n"
                f"_Central de Monitoreo SISDEL_"
            )
        }
    }

    headers = {
        "Authorization": f"Bearer {WA_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        print(f"📱 Enviando WhatsApp a {num_limpio}...")
        resp = requests.post(WA_API_URL, json=payload, headers=headers, timeout=10)
        data = resp.json()

        if resp.status_code in (200, 201):
            msg_id = data.get("messages", [{}])[0].get("id", "?")
            print(f"✅ WhatsApp enviado. ID: {msg_id}")
            return True
        else:
            error = data.get("error", {})
            print(f"❌ WhatsApp error {resp.status_code}: {error.get('message', data)}")
            return False
    except Exception as e:
        print(f"❌ Error enviando WhatsApp: {e}")
        return False


def enviar_alerta_sms(destinatario: str, nombre_vecino: str, ubicacion: str):
    """Envía alerta: intenta WhatsApp primero, SMS como fallback."""

    # 1. Intentar WhatsApp Cloud API
    wa_ok = enviar_whatsapp(destinatario, nombre_vecino, ubicacion)
    if wa_ok:
        return True

    # 2. Fallback: SMS via Twilio
    if not twilio_client:
        print("❌ Ni WhatsApp ni Twilio configurados.")
        return False

    try:
        num_limpio = str(destinatario).replace(" ", "").replace("-", "").replace("whatsapp:", "")
        if not num_limpio.startswith("+"):
            num_limpio = f"+{num_limpio}"

        remitente_sms = "+15674025393"
        print(f"--- Fallback: enviando SMS a {num_limpio} ---")

        body_sms = (
            f"🚨 ALERTA PÁNICO SISDEL\n"
            f"Vecino: {nombre_vecino}\n"
            f"Ubicación: {ubicacion}\n"
            f"Acude de inmediato."
        )

        message = twilio_client.messages.create(
            from_=remitente_sms,
            body=body_sms,
            to=num_limpio
        )
        print(f"✅ SMS enviado. SID: {message.sid}")
        return True
    except Exception as e:
        print(f"❌ Error enviando SMS: {e}")
        return False
