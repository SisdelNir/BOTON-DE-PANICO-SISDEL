import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Configuración de Twilio desde .env
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
TEMPLATE_NAME = os.getenv("TWILIO_TEMPLATE_NAME", "alerta_panico")

client = None
if TWILIO_SID and TWILIO_TOKEN:
    client = Client(TWILIO_SID, TWILIO_TOKEN)

def enviar_alerta_whatsapp(destinatario: str, nombre_vecino: str, ubicacion: str):
    """
    Envía una alerta de pánico usando la plantilla oficial de WhatsApp en Twilio.
    """
    if not client:
        print("❌ Twilio no configurado. Revisa las variables de entorno (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN).")
        return False
    
    try:
        # Asegurarse de que el número tenga el formato correcto para WhatsApp en Twilio
        # Twilio espera 'whatsapp:+1234567890'
        num_limpio = str(destinatario).replace(" ", "").replace("-", "").replace("whatsapp:", "")
        if not num_limpio.startswith("+"):
            num_limpio = f"+{num_limpio}"
        
        target = f"whatsapp:{num_limpio}"

        print(f"--- Intentando enviar WhatsApp ---")
        print(f"Para: {target}")
        print(f"Plantilla: {TEMPLATE_NAME}")
        print(f"Variables: 1={nombre_vecino}, 2={ubicacion}")

        # Enviar el cuerpo exacto de la plantilla aprobada por Meta
        # Twilio matchea automáticamente el body con la plantilla si coincide
        body_plantilla = (
            f"🚨 ALERTA DE PÁNICO: Sisdel Internacional.\n"
            f"El usuario {nombre_vecino} ha activado el Botón de Emergencia.\n"
            f"📍 Ubicación aproximada: {ubicacion}\n"
            f"Acude de inmediato o da aviso."
        )

        message = client.messages.create(
            from_=TWILIO_FROM,
            body=body_plantilla,
            to=target
        )
        print(f"✅ WhatsApp enviado con éxito. SID: {message.sid}")
        return True
    except Exception as e:
        print(f"❌ Error crítico enviando WhatsApp: {str(e)}")
        return False
