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
from app.services import analysis_service as analysis_svc
from app.services.dashboard_service import build_dashboard
from app.services.notifications import queue as notification_queue

# 'gratis' = 1 palpite simples/dia, 'pro' = 3 simples + 1 múltipla (ver `_find_multipla`)
PLAN_LIMITS = {"gratis": 1, "pro": 3}

# múltipla de verdade: 2+ mercados de UMA MESMA partida combinados (ex.: "mais de 2.5
# gols" + "ambas marcam" do mesmo jogo) — não é juntar o palpite de 3 jogos diferentes
# numa probabilidade combinada (isso não é múltipla de nada, é só 3 apostas soltas
# listadas juntas; achado do usuário revisando a mensagem real, 26/08/2026, corrigido
# aqui). `MULTIPLA_LEGS` é o número de mercados combinados na múltipla.
MULTIPLA_LEGS = 2


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
        # achado real (26/08/2026, print do usuário): "Celta de Vigo x Osasuna" saiu no
        # "PALPITE DO DIA" jogando só AMANHÃ. O filtro antigo (`< reference_date`) só
        # cortava jogo passado, deixava passar qualquer dia dentro da janela de 3 dias
        # do dashboard. "Do dia" é `==`, não `>=` — a janela de 3 dias do
        # `build_dashboard` existe só pra ter partida candidata com odd já capturada
        # cedo, nunca pra oferecer jogo de outro dia como se fosse de hoje.
        if summary.date.date() != reference_date:
            continue
        out.append(summary)
    return out


BRAND_NAME = "GreenOdds"


def _market_family(market_key: str) -> str:
    """Agrupa mercados que são a MESMA aposta disfarçada ou diretamente derivados um do
    outro — nunca deveriam entrar juntos numa múltipla (achado real: "mais de 2.5 gols"
    + "mais de 3.5 gols" do mesmo jogo não é combinação nenhuma, quem bate 3.5 SEMPRE
    bate 2.5 também; a "probabilidade combinada" calculada como produto ficava menor
    que a probabilidade real de qualquer uma das duas sozinha, o oposto de uma
    múltipla de verdade). `double_chance`/`draw_no_bet` também derivam direto de
    home_win/draw/away_win, por isso entram na mesma família que 1x2."""
    if market_key in ("home_win", "draw", "away_win") or market_key.startswith(("double_chance_", "draw_no_bet_")):
        return "1x2"
    if market_key.startswith("btts_"):
        return "btts"
    if market_key.startswith(("corner_over_", "corner_under_")):
        return "corners_ou"
    if market_key.startswith(("card_over_", "card_under_")):
        return "cards_ou"
    if market_key.startswith(("over_", "under_")):
        return "goals_ou"
    return market_key


def _multipla_candidate_legs(fixture_id: int) -> list:
    """Até `MULTIPLA_LEGS` mercados de famílias DIFERENTES da MESMA partida (ver
    `_market_family`), com confiança mínima e odd real, ranqueados por
    opportunity_score — os melhores mercados desse jogo específico, não os melhores
    jogos do dia. Devolve lista vazia se a partida não tiver mercados de famílias
    distintas suficientes (nunca força uma múltipla fraca, ou redundante, só pra
    preencher). Lista vazia também se a fixture não existir mais no momento da checagem
    (removida/id inválido) — nunca deixa isso derrubar o job inteiro que monta o
    bilhete do dia."""
    try:
        result = analysis_svc.get_fixture_markets(fixture_id)
    except ValueError:
        return []
    candidates = []
    for data in result["families"].values():
        if data["error"]:
            continue
        for o in data["opportunities"]:
            if o.confidence in _MIN_CONFIDENCE_FOR_NOTIFICATION and o.odd is not None and o.opportunity_score is not None:
                candidates.append(o)
    candidates.sort(key=lambda o: o.opportunity_score, reverse=True)

    legs = []
    seen_families = set()
    for o in candidates:
        family = _market_family(o.market_key)
        if family in seen_families:
            continue
        legs.append(o)
        seen_families.add(family)
        if len(legs) == MULTIPLA_LEGS:
            break
    return legs if len(legs) == MULTIPLA_LEGS else []


def find_multipla(opportunities: list) -> dict | None:
    """Primeira partida (na ordem já ranqueada por `eligible_opportunities`) que tem
    mercados suficientes pra montar uma múltipla de verdade — não precisa ser a mesma
    partida do palpite #1 simples. `None` se nenhuma partida do dia render 2 mercados
    com confiança mínima (dia fraco: sem múltipla, não inventa uma)."""
    for summary in opportunities:
        legs = _multipla_candidate_legs(summary.fixture_id)
        if legs:
            return {"summary": summary, "legs": legs}
    return None


def format_ticket_message(simple_picks: list, multipla: dict | None = None) -> str:
    """Bilhete formatado — nunca mostra a odd real (o valor do produto é o palpite e a
    probabilidade, não a cotação; a odd muda a cada minuto e o usuário confere no
    próprio site da casa antes de apostar).

    `simple_picks`: partidas DIFERENTES, 1 mercado cada — nunca soma probabilidade
    entre elas, são apostas independentes, não uma combinada.
    `multipla`: dict de `find_multipla` (mesma partida, 2+ mercados combinados) — só
    aqui existe "Probabilidade Combinada" de verdade, porque é isso que uma múltipla é."""
    is_single = len(simple_picks) <= 1 and multipla is None
    header = f"🎯 {'PALPITE DO DIA' if is_single else 'BILHETE DO DIA'} — {BRAND_NAME}"
    lines = [header, ""]

    if simple_picks:
        if multipla:
            lines.append("SIMPLES:")
        for i, summary in enumerate(simple_picks, start=1):
            best = summary.best_opportunity
            lines.append(
                f"{i}. {summary.home_team} x {summary.away_team} | {best.label} ({best.probability * 100:.0f}% prob)"
            )

    if multipla:
        if simple_picks:
            lines.append("")
        m_summary = multipla["summary"]
        legs = multipla["legs"]
        lines.append(f"MÚLTIPLA ({m_summary.home_team} x {m_summary.away_team}):")
        combined_probability = 1.0
        for leg in legs:
            combined_probability *= leg.probability
            lines.append(f"• {leg.label} ({leg.probability * 100:.0f}% prob)")
        lines.append(f"📊 Probabilidade Combinada: {combined_probability * 100:.1f}%")

    lines.append("")
    lines.append("⚠️ Aposte com responsabilidade.")
    return "\n".join(lines)


def enqueue_daily_opportunities(
    reference_date: datetime.date | None = None, opportunities: list | None = None, multipla: dict | None = None,
) -> dict:
    """`opportunities`/`multipla` normalmente vêm de `eligible_opportunities`/
    `find_multipla` (produção) — parâmetros existem pra teste injetar dado real sem
    precisar montar fixture+odds+modelo completos só pra popular o dashboard (mesmo
    padrão do `provider` em queue.process_pending). `multipla` omitido (`None`, o
    padrão) recalcula de verdade a partir de `opportunities`; passar `multipla={}`
    força "sem múltipla" mesmo com oportunidades disponíveis — só usado em teste.

    Um bilhete só por lead por dia (não um registro de fila por palpite) — o produto é
    o bilhete inteiro, não picks soltos; `idempotency_key` não inclui mais fixture/mercado
    porque não faz sentido reenviar metade de um bilhete já mandado."""
    reference_date = reference_date or datetime.date.today()
    opportunities = eligible_opportunities(reference_date) if opportunities is None else opportunities
    if multipla is None:
        multipla = find_multipla(opportunities)
    elif not multipla:
        multipla = None
    leads = _fetch_active_leads()

    enqueued = skipped_no_opportunity = skipped_duplicate = 0
    for lead_id, _name, phone, plan in leads:
        limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["gratis"])
        picks = opportunities[:limit]
        lead_multipla = multipla if plan == "pro" else None
        if not picks and not lead_multipla:
            skipped_no_opportunity += 1
            continue
        idempotency_key = f"lead:{lead_id}:{reference_date.isoformat()}"
        queued = notification_queue.enqueue(phone, format_ticket_message(picks, lead_multipla), idempotency_key)
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
