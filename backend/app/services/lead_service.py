"""Captação da landing page — quem se cadastrou pra receber odd no WhatsApp. Nunca
confirma pagamento nem envia mensagem nenhuma; só registra a intenção. O envio de
fato depende do usuário mandar a primeira mensagem no WhatsApp (ver landing/src/config.ts)
antes de qualquer robô poder responder."""
from app.core import db


def create_lead(name: str, phone: str, plan: str) -> None:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO whatsapp_leads (name, phone, plan) VALUES (%s, %s, %s)",
                (name, phone, plan),
            )
        conn.commit()
    finally:
        conn.close()
