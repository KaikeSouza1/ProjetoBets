"""Comandos que um lead manda pro número do bot (ex.: "/odds") e a resposta que o
CodeChat devolve na hora — diferente da fila de notificação (services/notifications/),
que é push assíncrono; isso aqui é pergunta -> resposta síncrona, então nunca passa
pela fila, responde direto via WhatsAppProvider."""
import datetime

from app.core import db
from app.services.opportunity_notifications import PLAN_LIMITS, eligible_opportunities, format_ticket_message

NO_OPPORTUNITY_MESSAGE = "Sem oportunidade com confiança suficiente pra hoje. Tenta de novo mais tarde."


def _lead_plan(phone: str) -> str:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT plan FROM whatsapp_leads WHERE phone = %s ORDER BY created_at DESC LIMIT 1", (phone,))
            row = cur.fetchone()
            return row[0] if row else "gratis"
    finally:
        conn.close()


def handle_command(from_phone: str, text: str, opportunities: list | None = None) -> str | None:
    """None quando `text` não é um comando reconhecido — quem chama não deve responder
    nada nesse caso (não vira eco de toda mensagem que o número recebe). `opportunities`
    normalmente vem de `eligible_opportunities` (produção) — parâmetro existe pra teste
    injetar oportunidades reais sem depender do dashboard completo (mesmo padrão de
    `opportunity_notifications.enqueue_daily_opportunities`)."""
    normalized = text.strip().lower()
    if normalized not in ("/odds", "odds"):
        return None

    plan = _lead_plan(from_phone)
    limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["gratis"])
    available = eligible_opportunities(datetime.date.today()) if opportunities is None else opportunities
    picks = available[:limit]
    if not picks:
        return NO_OPPORTUNITY_MESSAGE
    return format_ticket_message(picks)
