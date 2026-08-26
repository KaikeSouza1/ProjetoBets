"""Comandos que um lead manda pro número do bot (ex.: "/odds") e a resposta que o
CodeChat devolve na hora — diferente da fila de notificação (services/notifications/),
que é push assíncrono; isso aqui é pergunta -> resposta síncrona, então nunca passa
pela fila, responde direto via WhatsAppProvider."""
import datetime
import re

from app.core import db
from app.services.opportunity_notifications import PLAN_LIMITS, eligible_opportunities, format_ticket_message

NO_OPPORTUNITY_MESSAGE = "Sem oportunidade com confiança suficiente pra hoje. Tenta de novo mais tarde."


def _normalize_br_phone(phone: str) -> str:
    """Chave de comparação — remove o 9º dígito extra do celular brasileiro (DDD + 9 +
    8 dígitos vs DDD + 8 dígitos) quando presente. Achado real (26/08/2026): lead com
    plano 'pro' caiu pro grátis (1 palpite em vez de 3) porque o número que o WhatsApp
    devolveu no webhook ('554298528674', 12 dígitos) não batia, em comparação exata,
    com o número cadastrado no formulário ('5542998528674', 13 dígitos, com o 9) — o
    mesmo número de verdade, duas grafias diferentes. Só normaliza o padrão
    +55 DDD [9] XXXXXXXX; formato fora disso passa direto, sem inventar regra."""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("55") and len(digits) == 13 and digits[4] == "9":
        return digits[:4] + digits[5:]
    return digits


def _lead_plan(phone: str) -> str:
    target = _normalize_br_phone(phone)
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT phone, plan, created_at FROM whatsapp_leads ORDER BY created_at DESC")
            for stored_phone, plan, _created_at in cur.fetchall():
                if _normalize_br_phone(stored_phone) == target:
                    return plan
            return "gratis"
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
