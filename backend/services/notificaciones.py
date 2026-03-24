"""
Servicio de Notificaciones — WhatsApp automático para alertas de emergencia.

Prioridad de canales:
  1. Green API (WhatsApp via QR — principal)
  2. Meta Cloud API (WhatsApp oficial — respaldo)
  3. Twilio SMS (último recurso)
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Green API (WhatsApp via QR) ──
GREENAPI_ID   = os.getenv("GREENAPI_ID_INSTANCE", "")
GREENAPI_TOKEN = os.getenv("GREENAPI_API_TOKEN", "")

# ── Meta WhatsApp Cloud API ──
WA_TOKEN    = os.getenv("WHATSAPP_TOKEN", "")
WA_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
WA_API_URL  = f"https://graph.facebook.com/v21.0/{WA_PHONE_ID}/messages"

# ── Twilio SMS (fallback) ──
TWILIO_SID   = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

twilio_client = None
if TWILIO_SID and TWILIO_TOKEN:
    from twilio.rest import Client
    twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)


# ═══════════════════════════════════════════════════════
#  CANAL 1: GREEN API (WhatsApp via QR — como WhatsApp Web)
# ═══════════════════════════════════════════════════════

def enviar_whatsapp_greenapi(destinatario: str, mensaje: str) -> bool:
    """Envía mensaje de WhatsApp usando Green API REST."""
    if not GREENAPI_ID or not GREENAPI_TOKEN:
        print("⚠️ Green API no configurado (faltan GREENAPI_ID_INSTANCE o GREENAPI_API_TOKEN)")
        return False

    # Limpiar número: solo dígitos, sin + ni espacios
    num_limpio = ''.join(c for c in str(destinatario) if c.isdigit())
    if not num_limpio or len(num_limpio) < 8:
        print(f"⚠️ Número inválido para Green API: {destinatario}")
        return False

    url = f"https://api.green-api.com/waInstance{GREENAPI_ID}/sendMessage/{GREENAPI_TOKEN}"

    payload = {
        "chatId": f"{num_limpio}@c.us",
        "message": mensaje
    }

    try:
        print(f"📱 [GreenAPI] Enviando WhatsApp a {num_limpio}...")
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()

        if resp.status_code == 200 and data.get("idMessage"):
            print(f"✅ [GreenAPI] WhatsApp enviado. ID: {data['idMessage']}")
            return True
        else:
            print(f"❌ [GreenAPI] Error: {data}")
            return False
    except Exception as e:
        print(f"❌ [GreenAPI] Exception: {e}")
        return False


# ═══════════════════════════════════════════════════════
#  CANAL 2: META CLOUD API (WhatsApp oficial)
# ═══════════════════════════════════════════════════════

def enviar_whatsapp_meta(destinatario: str, mensaje: str) -> bool:
    """Envía alerta por WhatsApp Cloud API (Meta) con mensaje de texto libre."""
    if not WA_TOKEN or not WA_PHONE_ID:
        print("⚠️ Meta WhatsApp Cloud API no configurado")
        return False

    num_limpio = str(destinatario).replace(" ", "").replace("-", "")
    if num_limpio.startswith("+"):
        num_limpio = num_limpio[1:]

    payload = {
        "messaging_product": "whatsapp",
        "to": num_limpio,
        "type": "text",
        "text": {"preview_url": True, "body": mensaje}
    }
    headers = {
        "Authorization": f"Bearer {WA_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        print(f"📱 [MetaAPI] Enviando WhatsApp a {num_limpio}...")
        resp = requests.post(WA_API_URL, json=payload, headers=headers, timeout=10)
        data = resp.json()
        if resp.status_code in (200, 201):
            msg_id = data.get("messages", [{}])[0].get("id", "?")
            print(f"✅ [MetaAPI] WhatsApp enviado. ID: {msg_id}")
            return True
        else:
            error = data.get("error", {})
            print(f"❌ [MetaAPI] Error {resp.status_code}: {error.get('message', data)}")
            return False
    except Exception as e:
        print(f"❌ [MetaAPI] Exception: {e}")
        return False


# ═══════════════════════════════════════════════════════
#  CANAL 3: TWILIO SMS (último recurso)
# ═══════════════════════════════════════════════════════

def enviar_sms_twilio(destinatario: str, mensaje: str) -> bool:
    """Envía SMS via Twilio como último recurso."""
    if not twilio_client:
        print("❌ Twilio no configurado.")
        return False

    try:
        num_limpio = str(destinatario).replace(" ", "").replace("-", "").replace("whatsapp:", "")
        if not num_limpio.startswith("+"):
            num_limpio = f"+{num_limpio}"

        remitente_sms = "+15674025393"
        # SMS tiene límite de 160 chars, truncar
        body_sms = mensaje[:160]

        print(f"📩 [Twilio] Enviando SMS a {num_limpio}...")
        message = twilio_client.messages.create(
            from_=remitente_sms, body=body_sms, to=num_limpio
        )
        print(f"✅ [Twilio] SMS enviado. SID: {message.sid}")
        return True
    except Exception as e:
        print(f"❌ [Twilio] Error: {e}")
        return False


# ═══════════════════════════════════════════════════════
#  FUNCIONES PRINCIPALES — Mensajes de Emergencia
# ═══════════════════════════════════════════════════════

def construir_mensaje_vecino(nombre: str, ubicacion: str, lat=None, lon=None) -> str:
    """Construye el mensaje de emergencia para contactos de VECINO."""
    mapa = ""
    if lat and lon:
        mapa = f"🗺️ https://maps.google.com/?q={lat},{lon}\n\n"

    return (
        f"🚨 *ALERTA DE EMERGENCIA — SISDEL* 🚨\n\n"
        f"Se ha activado una alerta de pánico:\n"
        f"👤 *{nombre}*\n"
        f"📍 {ubicacion}\n"
        f"{mapa}"
        f"Nuestras unidades han sido notificadas.\n"
        f"Si usted es familiar, manténgase informado.\n\n"
        f"_Central de Monitoreo SISDEL_"
    )


def construir_mensaje_piloto(nombre: str, placas: str, tipo_vehiculo: str, lat=None, lon=None) -> str:
    """Construye el mensaje de emergencia para contactos de PILOTO."""
    mapa = ""
    if lat and lon:
        mapa = f"🗺️ https://maps.google.com/?q={lat},{lon}\n\n"

    vehiculo_info = f"{tipo_vehiculo} — Placas: {placas}" if placas else tipo_vehiculo or "No especificado"

    return (
        f"🚨 *ALERTA DE EMERGENCIA — SEGURIDAD* 🚨\n\n"
        f"Se ha activado una alerta de pánico:\n"
        f"🚗 *{nombre}* — {vehiculo_info}\n"
        f"📍 Ubicación GPS:\n"
        f"{mapa}"
        f"Agentes de seguridad han sido notificados.\n"
        f"Manténgase en contacto.\n\n"
        f"_Central de Monitoreo_"
    )


def enviar_alerta_contacto(destinatario: str, mensaje: str) -> dict:
    """
    Envía mensaje a un contacto individual usando la cadena de prioridad:
    Green API → Meta Cloud API → Twilio SMS
    
    Retorna dict con resultado.
    """
    resultado = {"telefono": destinatario, "canal": None, "exito": False}

    # 1. Green API (principal)
    if enviar_whatsapp_greenapi(destinatario, mensaje):
        resultado["canal"] = "GREEN_API"
        resultado["exito"] = True
        return resultado

    # 2. Meta Cloud API (respaldo)
    if enviar_whatsapp_meta(destinatario, mensaje):
        resultado["canal"] = "META_API"
        resultado["exito"] = True
        return resultado

    # 3. Twilio SMS (último recurso)
    if enviar_sms_twilio(destinatario, mensaje):
        resultado["canal"] = "TWILIO_SMS"
        resultado["exito"] = True
        return resultado

    resultado["canal"] = "NINGUNO"
    print(f"❌ No se pudo enviar a {destinatario} por ningún canal.")
    return resultado


# ── Compatibilidad con código existente ──
def enviar_alerta_sms(destinatario: str, nombre_vecino: str, ubicacion: str):
    """Función de compatibilidad con el código anterior de emergencias.py."""
    mensaje = construir_mensaje_vecino(nombre_vecino, ubicacion)
    return enviar_alerta_contacto(destinatario, mensaje)
