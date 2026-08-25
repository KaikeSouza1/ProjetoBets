"""Liga o Opportunity Engine (dashboard, já ranqueado por opportunity_score) à fila de
notificação (services/notifications/queue.py). Nunca manda nada de verdade daqui — só
enfileira; o envio real fica a cargo de notifications.queue.process_pending + o
WhatsAppProvider configurado (console por padrão, sem credencial real).

Regra de negócio: cada lead recebe as N melhores oportunidades do dia conforme seu
plano (PLAN_LIMITS). idempotency_key inclui a data — evita reenviar a mesma
oportunidade pro mesmo número no mesmo dia se o job rodar de novo, mas permite
oportunidades novas no dia seguinte mesmo que fixture/mercado se repitam."""
import datetime

from app.core import db
from app.services.dashboard_service import build_dashboard
from app.services.notifications import queue as notification_queue

# 'gratis' = 1 odd/dia, 'pro' = 3 (múltipla combinada ainda não implementada —
# ver nota no fim do arquivo; não fabricado aqui, é um degrau futuro real).
PLAN_LIMITS = {"gratis": 1, "pro": 3}


def _fetch_active_leads() -> list[tuple[int, str, str, str]]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, phone, plan FROM whatsapp_leads")
            return cur.fetchall()
    finally:
        conn.close()


# mesmo corte de confiança que dashboard_service.STRONG_CONFIDENCE_LEVELS já usa pra
# destacar oportunidade "forte" na interface — reaproveitado aqui, não inventado. No
# dashboard, 'baixa' confiança ainda aparece (com aviso de maturidade de liga) porque
# há contexto visual pro usuário julgar; numa notificação de WhatsApp isolada, sem
# esse contexto, uma estimativa sustentada por amostra mínima (achado real: partida
# com data_quality=3 chegando a soar "100% de probabilidade") não deveria ser enviada
# como recomendação — filtrada aqui, não em `dashboard_service` (a tela continua
# mostrando tudo, com aviso; só a notificação exige confiança mínima).
_MIN_CONFIDENCE_FOR_NOTIFICATION = {"média", "alta"}


def eligible_opportunities(reference_date: datetime.date) -> list:
    """Top oportunidades do dashboard (já ranqueadas por opportunity_score), só as
    que realmente têm o que mostrar: odd real, edge calculado, confiança mínima, e a
    partida ainda não começou hoje ou depois — nunca manda oportunidade de jogo já em
    andamento/passado nem estimativa sustentada por amostra mínima."""
    dashboard = build_dashboard(days_ahead=3, sort_by="valor")
    out = []
    for summary in dashboard.opportunities:
        best = summary.best_opportunity
        if best is None or best.opportunity_score is None or best.odd is None:
            continue
        if best.confidence not in _MIN_CONFIDENCE_FOR_NOTIFICATION:
            continue
        if summary.date.date() < reference_date:
            continue
        out.append(summary)
    return out


BRAND_NAME = "GreenOdds"


def format_ticket_message(opportunities: list) -> str:
    """Bilhete formatado — nunca mostra a odd real (o valor do produto é o palpite e a
    probabilidade, não a cotação; a odd muda a cada minuto e o usuário confere no
    próprio site da casa antes de apostar). Mesmo layout pra 1 palpite ou pra múltipla
    — só o título e o rodapé de probabilidade combinada mudam."""
    is_multiple = len(opportunities) > 1
    header = f"🎯 {'BILHETE MÚLTIPLA' if is_multiple else 'PALPITE DO DIA'} — {BRAND_NAME}"

    lines = [header, ""]
    combined_probability = 1.0
    for i, summary in enumerate(opportunities, start=1):
        best = summary.best_opportunity
        combined_probability *= best.probability
        lines.append(
            f"{i}. {summary.home_team} x {summary.away_team} | {best.label} ({best.probability * 100:.0f}% prob)"
        )

    if is_multiple:
        lines.append("")
        lines.append(f"📊 Probabilidade Combinada: {combined_probability * 100:.1f}%")

    lines.append("")
    lines.append("⚠️ Aposte com responsabilidade.")
    return "\n".join(lines)


def enqueue_daily_opportunities(reference_date: datetime.date | None = None, opportunities: list | None = None) -> dict:
    """`opportunities` normalmente vem de `eligible_opportunities` (produção) —
    parâmetro existe pra teste injetar oportunidades reais (MatchSummaryOut/
    OpportunityOut de verdade) sem precisar montar fixture+odds+modelo completos
    só pra popular o dashboard (mesmo padrão do `provider` em queue.process_pending).

    Um bilhete só por lead por dia (não um registro de fila por palpite) — o produto é
    o bilhete inteiro, não picks soltos; `idempotency_key` não inclui mais fixture/mercado
    porque não faz sentido reenviar metade de um bilhete já mandado."""
    reference_date = reference_date or datetime.date.today()
    opportunities = eligible_opportunities(reference_date) if opportunities is None else opportunities
    leads = _fetch_active_leads()

    enqueued = skipped_no_opportunity = skipped_duplicate = 0
    for lead_id, _name, phone, plan in leads:
        limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["gratis"])
        picks = opportunities[:limit]
        if not picks:
            skipped_no_opportunity += 1
            continue
        idempotency_key = f"lead:{lead_id}:{reference_date.isoformat()}"
        queued = notification_queue.enqueue(phone, format_ticket_message(picks), idempotency_key)
        if queued:
            enqueued += 1
        else:
            skipped_duplicate += 1

    result = {
        "enqueued": enqueued,
        "skipped_no_opportunity": skipped_no_opportunity,
        "skipped_duplicate": skipped_duplicate,
        "n_leads": len(leads),
        "n_opportunities_available": len(opportunities),
    }
    print(f"[opportunity_notifications] {result}")
    return result
