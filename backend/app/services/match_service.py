"""Monta as respostas de partida (header/análise/mercados/forma/jogadores) a partir do
`analysis_service` (consultas) e do `valuebet` (ranking) — só orquestra e traduz para os
schemas da API. Nenhum cálculo estatístico mora aqui."""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from app.api.schemas.match import (
    DataState, MarketFamilyOut, MatchAnalysisOut, MatchFormOut, MatchHeaderOut,
    MatchMarketsOut, MatchPlayersOut, MatchSummaryOut, OpportunityOut, PlayerPredictionOut,
    RecentResultOut, StandingRowOut, TeamPlayersOut,
)
from app.core import config
from app.services import analysis_service as svc
from app.services import snapshot_service

# probabilidades fora dessa faixa (ex.: "mais de 0.5 gols: 96%") são quase sempre
# verdadeiras e não ajudam ninguém a decidir nada — não valem destaque sem odd pra comparar
_INTERESTING_PROB_RANGE = (0.15, 0.85)

# ~3 rodadas num campeonato de 20 times (10 jogos/rodada) — abaixo disso a força de
# ataque/defesa de boa parte dos times ainda foi calibrada com poucos jogos da
# temporada atual (elenco pode ter mudado no meio-tempo entre temporadas)
LEAGUE_MATURITY_THRESHOLD_MATCHES = 30


def _league_maturity_notice(league_id: int) -> str | None:
    n = svc.get_league_maturity().get(league_id, 0)
    if n >= LEAGUE_MATURITY_THRESHOLD_MATCHES:
        return None
    return (
        f"Temporada ainda recente nesta liga — só {n} jogo(s) finalizado(s) até agora. "
        "Estimativas tendem a ficar mais confiáveis conforme mais jogos rolam."
    )


def _is_stale(last_updated: datetime | None) -> bool:
    """Limiar em `config.DATA_STALE_THRESHOLD_HOURS` — configuração operacional
    (ajustável por .env), não uma verdade estatística sobre quando um dado 'expira'."""
    if last_updated is None:
        return True
    threshold = timedelta(hours=config.DATA_STALE_THRESHOLD_HOURS)
    return (datetime.now(timezone.utc) - last_updated) > threshold


# sentinel pra distinguir "não passou last_updated, busca você mesmo" de "passou None
# de propósito" — usado pelos endpoints de 1 partida só; o dashboard busca 1x pra todas
# as 127 partidas e passa o valor explicitamente, pra não reintroduzir o N+1 que a fase
# de performance acabou de eliminar.
_UNSET = object()


def _resolve_last_updated(last_updated):
    return svc.get_last_updated() if last_updated is _UNSET else last_updated


def _map_opportunity(o) -> OpportunityOut:
    return OpportunityOut(**asdict(o))


def _map_family(family_name: str, data: dict) -> MarketFamilyOut:
    prediction = data.get("prediction")
    return MarketFamilyOut(
        family=family_name,
        error=data["error"],
        lambda_home=getattr(prediction, "lambda_home", None),
        lambda_away=getattr(prediction, "lambda_away", None),
        n_matches_home_team=getattr(prediction, "n_matches_home_team", None),
        n_matches_away_team=getattr(prediction, "n_matches_away_team", None),
        opportunities=[_map_opportunity(o) for o in data["opportunities"]],
    )


def _resolve_state(fixture_id: int | None, families: dict, last_updated: datetime | None) -> DataState:
    if all(data["error"] for data in families.values()):
        return DataState.INSUFFICIENT_DATA
    if _is_stale(last_updated):
        return DataState.STALE
    if fixture_id is None:
        return DataState.NO_ODDS
    any_odds = any(o.odd is not None for data in families.values() if not data["error"] for o in data["opportunities"])
    if not any_odds:
        return DataState.NO_ODDS
    any_family_missing = any(data["error"] for data in families.values())
    return DataState.PARTIAL if any_family_missing else DataState.READY


def _families_and_state(match: dict, last_updated: datetime | None) -> tuple[dict, DataState]:
    if match["fixture_id"]:
        result = svc.get_fixture_markets(match["fixture_id"])
        families = result["families"]
    else:
        families = svc.get_match_preview(match["league_id"], match["home_team_id"], match["away_team_id"])["families"]
    return families, _resolve_state(match["fixture_id"], families, last_updated)


def _best_and_others(families: dict, sort_by: str = "valor") -> tuple[OpportunityOut | None, list[OpportunityOut]]:
    """`sort_by="valor"` (padrão): rankeia por opportunity_score (edge × confiança ×
    qualidade) — só usa probabilidade crua quando não há odd pra calcular edge nenhum.
    `sort_by="probabilidade"`: ignora edge de propósito — mostra o que tem MAIOR chance
    de acontecer, com ou sem odd. Não é 'melhor aposta', é 'resultado mais provável';
    o usuário decide qual pergunta quer responder."""
    all_opps = [o for data in families.values() if not data["error"] for o in data["opportunities"]]

    if sort_by == "probabilidade":
        interesting = [o for o in all_opps if _INTERESTING_PROB_RANGE[0] <= o.probability <= _INTERESTING_PROB_RANGE[1]]
        pool = sorted(interesting or all_opps, key=lambda o: o.probability, reverse=True)
        if not pool:
            return None, []
        return _map_opportunity(pool[0]), [_map_opportunity(o) for o in pool[1:]]

    ranked = sorted((o for o in all_opps if o.opportunity_score is not None), key=lambda o: o.opportunity_score, reverse=True)
    if ranked:
        best, rest = ranked[0], ranked[1:]
        return _map_opportunity(best), [_map_opportunity(o) for o in rest]

    interesting = [o for o in all_opps if _INTERESTING_PROB_RANGE[0] <= o.probability <= _INTERESTING_PROB_RANGE[1]]
    pool = interesting or all_opps
    if not pool:
        return None, []
    pool = sorted(pool, key=lambda o: o.probability, reverse=True)
    return _map_opportunity(pool[0]), [_map_opportunity(o) for o in pool[1:]]


def _build_reasons(families: dict, best_market_key: str | None, home_form: list[dict], away_form: list[dict]) -> list[str]:
    if best_market_key is None:
        return []
    reasons = []
    for family_name, data in families.items():
        if data["error"]:
            continue
        prediction = data["prediction"]
        opp = next((o for o in data["opportunities"] if o.market_key == best_market_key), None)
        if opp is None:
            continue

        if family_name == "gols":
            reasons.append(
                f"Modelo estima {prediction.lambda_home:.2f} gols esperados para o mandante e "
                f"{prediction.lambda_away:.2f} para o visitante."
            )
            if best_market_key in ("btts_yes", "btts_no") and (home_form or away_form):
                home_btts = sum(1 for m in home_form if m["goals_for"] > 0 and m["goals_against"] > 0)
                away_btts = sum(1 for m in away_form if m["goals_for"] > 0 and m["goals_against"] > 0)
                reasons.append(
                    f"Nos últimos {len(home_form)} jogos, o mandante teve ambas as equipes "
                    f"marcando em {home_btts}; o visitante, em {away_btts} dos últimos {len(away_form)}."
                )
        elif family_name in ("escanteios", "cartões"):
            reasons.append(
                f"Modelo estima {prediction.lambda_home + prediction.lambda_away:.1f} "
                f"{family_name} no total da partida (mandante {prediction.lambda_home:.1f} + visitante {prediction.lambda_away:.1f})."
            )

        reasons.append(
            f"Amostra: {prediction.n_matches_home_team} jogos do mandante, "
            f"{prediction.n_matches_away_team} do visitante."
        )
        if opp.odd is not None:
            reasons.append(
                f"Odd {opp.odd:.2f} implica {opp.implied_probability * 100:.1f}% de probabilidade; "
                f"modelo estima {opp.probability * 100:.1f}% — edge estimado {opp.edge * 100:+.1f}%."
            )
        break
    return reasons


def get_header(match: dict, last_updated=_UNSET) -> MatchHeaderOut:
    _families, state = _families_and_state(match, _resolve_last_updated(last_updated))
    return MatchHeaderOut(
        fd_match_id=match["fd_match_id"], fixture_id=match["fixture_id"], date=match["date"], status=match["status"],
        league_id=match["league_id"], league_name=match["league_name"], league_country=match.get("league_country"),
        referee=match.get("referee"), home_team_id=match["home_team_id"], home_team=match["home_team"],
        away_team_id=match["away_team_id"], away_team=match["away_team"],
        home_goals=match["home_goals"], away_goals=match["away_goals"], state=state,
        league_maturity_notice=_league_maturity_notice(match["league_id"]),
    )


def get_summary(match: dict, last_updated=_UNSET, sort_by: str = "valor") -> MatchSummaryOut:
    families, state = _families_and_state(match, _resolve_last_updated(last_updated))
    best, _others = _best_and_others(families, sort_by)
    return MatchSummaryOut(
        fd_match_id=match["fd_match_id"], fixture_id=match["fixture_id"], date=match["date"], status=match["status"],
        league_id=match["league_id"], league_name=match["league_name"], league_country=match.get("league_country"),
        home_team_id=match["home_team_id"], home_team=match["home_team"],
        away_team_id=match["away_team_id"], away_team=match["away_team"],
        home_goals=match["home_goals"], away_goals=match["away_goals"], state=state, best_opportunity=best,
    )


_EMPTY_MESSAGES = {
    DataState.INSUFFICIENT_DATA: (
        "Essa liga ou esses times ainda não têm histórico suficiente para uma estimativa confiável."
    ),
    DataState.NO_ODDS: (
        "Modelo disponível, mas as odds ainda não foram coletadas para esta partida. "
        "Atualizaremos quando o mercado entrar na janela de coleta."
    ),
}


def _stale_message() -> str:
    return (
        f"Os dados usados nesta estimativa não são atualizados há mais de "
        f"{config.DATA_STALE_THRESHOLD_HOURS}h — pode não refletir o cenário atual."
    )


def get_analysis(
    match: dict, last_updated=_UNSET, source: str = snapshot_service.MANUAL_VIEW, sort_by: str = "valor",
) -> MatchAnalysisOut:
    """`source` default é MANUAL_VIEW (alguém abriu esta partida pela API) —
    `snapshot_service.capture_snapshots_for_upcoming_matches` passa PERIODIC_JOB pra
    marcar snapshots de uma captura sistemática. Nunca misture os dois sem o rótulo."""
    families, state = _families_and_state(match, _resolve_last_updated(last_updated))
    best, others = _best_and_others(families, sort_by)

    home_form = svc.get_recent_form(match["home_team_id"], limit=10)
    away_form = svc.get_recent_form(match["away_team_id"], limit=10)
    reasons = _build_reasons(families, best.market_key if best else None, home_form, away_form)

    empty_message = None if best else _EMPTY_MESSAGES.get(state, "Dados insuficientes para produzir uma estimativa.")
    stale_notice = _stale_message() if state == DataState.STALE else None

    # snapshot só aqui — é o ponto em que alguém (ou o job periódico) de fato avaliou
    # essa partida, não a listagem do dashboard (evita reescrever a mesma linha 127x por
    # request ali)
    all_opps = [o for data in families.values() if not data["error"] for o in data["opportunities"]]
    if all_opps:
        snapshot_service.record_snapshot(match["fixture_id"], match["fd_match_id"], all_opps, source=source)

    return MatchAnalysisOut(
        state=state, best_opportunity=best, other_opportunities=others, reasons=reasons,
        empty_message=empty_message, stale_notice=stale_notice,
    )


def get_markets(match: dict, last_updated=_UNSET) -> MatchMarketsOut:
    families, state = _families_and_state(match, _resolve_last_updated(last_updated))
    return MatchMarketsOut(state=state, families=[_map_family(name, data) for name, data in families.items()])


def get_form(match: dict) -> MatchFormOut:
    home_form = svc.get_recent_form(match["home_team_id"], limit=10)
    away_form = svc.get_recent_form(match["away_team_id"], limit=10)
    standings = svc.get_standings(match["league_id"])
    return MatchFormOut(
        home_form=[RecentResultOut(**m) for m in home_form],
        away_form=[RecentResultOut(**m) for m in away_form],
        standings=[StandingRowOut(**s) for s in standings],
    )


def get_players(match: dict, last_updated=_UNSET) -> MatchPlayersOut:
    if not match["fixture_id"]:
        return MatchPlayersOut(
            state=DataState.NO_ODDS,
            home=TeamPlayersOut(players=[], error="Depende da partida entrar na janela de captura da API-Football."),
            away=TeamPlayersOut(players=[], error="Depende da partida entrar na janela de captura da API-Football."),
        )
    result = svc.get_player_predictions(match["fixture_id"])
    _families, state = _families_and_state(match, _resolve_last_updated(last_updated))
    return MatchPlayersOut(
        state=state,
        home=TeamPlayersOut(
            players=[PlayerPredictionOut(**asdict(p)) for p in result["home"]["players"]],
            error=result["home"]["error"],
        ),
        away=TeamPlayersOut(
            players=[PlayerPredictionOut(**asdict(p)) for p in result["away"]["players"]],
            error=result["away"]["error"],
        ),
    )
