"""Camada da tela principal — a pergunta que o produto responde: 'quais partidas dos
próximos dias merecem atenção, e qual mercado tem melhor relação probabilidade x odd?'
Nunca decide isso pela maior probabilidade crua — usa opportunity_score (edge escalado
por confiança/qualidade de dado), calculado em `engine.valuebet`."""
from datetime import date as date_cls, timedelta

from app.api.schemas.dashboard import DashboardOut, DashboardSummaryOut, DayBucketOut
from app.api.schemas.match import MatchSummaryOut
from app.services import analysis_service as svc
from app.services import match_service

# uma oportunidade "forte" pesa edge relevante E confiança/qualidade de dado consistentes —
# nunca só a maior probabilidade (ver valuebet.calculate_opportunity_score)
STRONG_EDGE_THRESHOLD = 0.05
STRONG_CONFIDENCE_LEVELS = {"alta", "média"}


def _is_strong(best) -> bool:
    if best is None or best.edge is None:
        return False
    return best.edge >= STRONG_EDGE_THRESHOLD and best.confidence in STRONG_CONFIDENCE_LEVELS


def _day_label(day: date_cls, today: date_cls) -> str:
    delta = (day - today).days
    if delta == 0:
        return "Hoje"
    if delta == 1:
        return "Amanhã"
    return f"+{delta} dias"


def build_dashboard(
    days_ahead: int = 14,
    league_id: int | None = None,
    min_edge: float | None = None,
    min_confidence: str | None = None,
    sort_by: str = "valor",
) -> DashboardOut:
    all_matches = svc.list_upcoming(days_ahead=days_ahead)
    if league_id is not None:
        all_matches = [m for m in all_matches if m["league_id"] == league_id]

    # buscado 1x pra todo o dashboard, não por partida — cada partida chamando isso
    # seria a mesma classe de N+1 que a odds já tinha (ver valuebet.fetch_latest_odds)
    last_updated = svc.get_last_updated()
    summaries: list[MatchSummaryOut] = [
        match_service.get_summary(m, last_updated=last_updated, sort_by=sort_by) for m in all_matches
    ]

    confidence_rank = {"baixa": 0, "média": 1, "alta": 2}
    min_conf_rank = confidence_rank.get(min_confidence, 0) if min_confidence else 0

    if sort_by == "probabilidade":
        # aqui a pergunta é "o que tem mais chance de acontecer", não "onde tem valor" —
        # min_edge não faz sentido nesse modo (probabilidade alta não implica edge
        # nenhum), só confiança continua filtrando
        def passes_filters(s: MatchSummaryOut) -> bool:
            if s.best_opportunity is None:
                return False
            return confidence_rank.get(s.best_opportunity.confidence, 0) >= min_conf_rank

        ranked = sorted(
            (s for s in summaries if passes_filters(s)),
            key=lambda s: s.best_opportunity.probability,
            reverse=True,
        )
    else:
        def passes_filters(s: MatchSummaryOut) -> bool:
            if s.best_opportunity is None or s.best_opportunity.opportunity_score is None:
                return False
            if min_edge is not None and (s.best_opportunity.edge or 0) < min_edge:
                return False
            if confidence_rank.get(s.best_opportunity.confidence, 0) < min_conf_rank:
                return False
            return True

        ranked = sorted(
            (s for s in summaries if passes_filters(s)),
            key=lambda s: s.best_opportunity.opportunity_score,
            reverse=True,
        )

    best_opportunity = ranked[0] if ranked else None
    strong_count = sum(1 for s in ranked if _is_strong(s.best_opportunity))

    today = date_cls.today()
    days: list[DayBucketOut] = []
    for offset in range(days_ahead + 1):
        day = today + timedelta(days=offset)
        day_matches = [s for s in summaries if s.date.date() == day]
        if day_matches:
            days.append(DayBucketOut(label=_day_label(day, today), date=day.isoformat(), matches=day_matches))

    empty_message = None
    if not summaries:
        empty_message = "Nenhum jogo encontrado neste período. Tente aumentar a janela de dias."
    elif not ranked:
        empty_message = "Existem jogos neste período, mas nenhuma odd apresenta valor suficiente com os filtros atuais."

    return DashboardOut(
        summary=DashboardSummaryOut(
            matches_analyzed=len(summaries),
            opportunities_found=len(ranked),
            strong_opportunities=strong_count,
            last_updated=last_updated,
        ),
        best_opportunity=best_opportunity,
        opportunities=ranked,
        days=days,
        empty_message=empty_message,
    )
