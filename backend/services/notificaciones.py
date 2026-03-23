import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Configuración de Twilio desde .env
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

client = None
if TWILIO_SID and TWILIO_TOKEN:
    client = Client(TWILIO_SID, TWILIO_TOKEN)

def enviar_alerta_sms(destinatario: str, nombre_vecino: str, ubicacion: str):
    """
    Envía una alerta de pánico usando SMS tradicional (Twilio) para garantizar entrega inmediata.
    """
    if not client:
        print("❌ Twilio no configurado. Revisa las variables de entorno.")
        return False
    
    try:
        # Formatear el número para SMS (quitar prefijos y espacios)
        num_limpio = str(destinatario).replace(" ", "").replace("-", "").replace("whatsapp:", "")
        if not num_limpio.startswith("+"):
            num_limpio = f"+{num_limpio}"
        
        # El remitente SMS es el número de Twilio (+15674025393)
        remitente_sms = "+15674025393" 

        print(f"--- Intentando enviar ALERTA SMS ---")
        print(f"Para: {num_limpio}")
        
        body_sms = (
            f"🚨 ALERTA PÁNICO SISDEL\n"
            f"Vecino: {nombre_vecino}\n"
            f"Ubicación: {ubicacion}\n"
            f"Acude de inmediato."
        )

        message = client.messages.create(
            from_=remitente_sms,
            body=body_sms,
            to=num_limpio
        )
        print(f"✅ SMS enviado con éxito. SID: {message.sid}")
        return True
    except Exception as e:
        print(f"❌ Error enviando SMS: {str(e)}")
        return False
