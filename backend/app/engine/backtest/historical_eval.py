"""Avaliação histórica com odds reais — responde 'quando o modelo viu valor, ele
realmente encontrou valor?'. Bem mais restrita que o walk-forward de calibração em
`backtest.py`: além de nunca treinar com jogo futuro, uma aposta só entra aqui se
existir uma ODD REAL capturada antes do apito inicial da partida. Sem isso, qualquer
'ROI' seria uma partida jogada há meses recebendo a odd de agora — viés claro de
look-ahead, exatamente o que a seção 16 da auditoria pediu pra nunca fazer.

Isto é BACKTEST HISTÓRICO REAL, não simulação retrospectiva: nenhuma linha aqui reusa
a odd "atual" contra um resultado antigo. Se não existir par (odd pré-jogo, resultado
real) pra uma partida, ela simplesmente não entra — nunca é preenchida com a odd mais
recente disponível.

PREDICTION TIME, não kickoff, é o corte usado pro treino e pra odd: o corte certo pra
simular 'o que o modelo teria dito' é o instante em que a primeira odd pré-jogo foi
capturada — não o apito inicial. Usar o apito inicial como corte pegaria a odd mais
recente entre várias capturas pré-jogo (a mais próxima do fechamento), inflando edge
artificialmente com informação que só existiu depois da previsão real ter sido feita."""
from datetime import timedelta

from app.core import db
from app.engine.backtest.backtest import actual_outcomes_from_score
from app.engine.backtest.metrics import GradedBet, grade_bet
from app.engine.models.poisson_goals import MODEL_VERSION, compute_strengths_from_matches, predict_fixture
from app.engine.valuebet import valuebet

# só gols tem walk-forward + escalação de força implementados por data de corte. Escanteios
# e cartões dependem de fixture_statistics, que hoje tem estatística de ~1 partida no banco —
# não dá pra fazer walk-forward de nada com isso. Escopo documentado, não expandido à toa.
EVALUABLE_MARKETS = [
    "home_win", "draw", "away_win", "double_chance_1x", "double_chance_12", "double_chance_x2",
    "btts_yes", "btts_no", "over_2_5", "under_2_5",
]

EVALUATION_SOURCE = "HISTORICAL_ODDS_BACKTEST"
_EPSILON = timedelta(milliseconds=1)


class EvaluatedBet:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _find_eligible_fixtures(league_id: int | None) -> list[dict]:
    """Partida elegível = já terminou (resultado real conhecido) E tem pelo menos 1 odd
    capturada ANTES do apito inicial. As duas condições juntas são o que garante que a
    odd usada aqui não é 'a odd de agora' — é uma odd que genuinamente existia antes do
    resultado."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT DISTINCT f.id, f.league_id, f.home_team_id, f.away_team_id,
                          f.home_goals, f.away_goals, f.date, l.football_data_code
                   FROM fixtures f
                   JOIN leagues l ON l.id = f.league_id
                   WHERE f.status = 'FT' AND f.home_goals IS NOT NULL AND f.away_goals IS NOT NULL
                     AND l.football_data_code IS NOT NULL
                     AND (%s IS NULL OR f.league_id = %s)
                     AND EXISTS (
                         SELECT 1 FROM odds_snapshots os
                         WHERE os.fixture_id = f.id AND os.captured_at < f.date
                     )
                   ORDER BY f.date""",
                (league_id, league_id),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {
            "fixture_id": r[0], "league_id": r[1], "home_team_id": r[2], "away_team_id": r[3],
            "home_goals": r[4], "away_goals": r[5], "date": r[6], "fd_code": r[7],
        }
        for r in rows
    ]


def _fetch_training_matches_before(fd_code: str, cutoff) -> list[tuple]:
    """Mesma fonte e mesma forma de dado do walk-forward de calibração (`backtest.py`) —
    só resultados de fd_matches com utc_date estritamente anterior ao corte. Consulta
    separada da usada pela previsão em produção (`poisson_goals._fetch_matches`, sem
    filtro de data) DE PROPÓSITO: a previsão ao vivo tem o direito de usar todo o
    histórico disponível; a avaliação retrospectiva não pode usar nada que só existiu
    depois do corte."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT home_team_id, away_team_id, home_goals, away_goals
                   FROM fd_matches
                   WHERE competition_code = %s AND status = 'FINISHED'
                     AND home_team_id IS NOT NULL AND away_team_id IS NOT NULL
                     AND home_goals IS NOT NULL AND away_goals IS NOT NULL
                     AND utc_date < %s
                   ORDER BY utc_date, fd_match_id""",
                (fd_code, cutoff),
            )
            return cur.fetchall()
    finally:
        conn.close()


def _resolve_actual(market_key: str, actuals: dict[str, bool]) -> bool | None:
    if market_key in actuals:
        return actuals[market_key]
    home_win, draw, away_win = actuals["home_win"], actuals["draw"], actuals["away_win"]
    derived = {
        "double_chance_1x": home_win or draw, "double_chance_12": home_win or away_win,
        "double_chance_x2": draw or away_win, "btts_no": not actuals["btts_yes"],
        "under_2_5": not actuals["over_2_5"],
    }
    return derived.get(market_key)


def evaluate_historical_bets(league_id: int | None = None) -> list[EvaluatedBet]:
    """Ponto de entrada. Devolve uma lista (pode ser vazia — e HOJE, no banco real
    deste projeto, É vazia: nenhuma partida finalizada tem odd capturada antes do apito
    inicial ainda). Uma lista vazia aqui não é bug, é a arquitetura funcionando
    corretamente diante de dado insuficiente — ver relatório de auditoria."""
    evaluated: list[EvaluatedBet] = []

    for fixture in _find_eligible_fixtures(league_id):
        prediction_time, closing_time = valuebet.odds_capture_window(fixture["fixture_id"], fixture["date"])
        if prediction_time is None:
            continue

        # corte = prediction_time, NUNCA o apito inicial — ver docstring do módulo
        training_matches = _fetch_training_matches_before(fixture["fd_code"], prediction_time)
        try:
            model = compute_strengths_from_matches(fixture["league_id"], training_matches)
            prediction = predict_fixture(model, fixture["home_team_id"], fixture["away_team_id"])
        except ValueError:
            continue  # sem histórico suficiente ANTES desta previsão — pula, não inventa força de time

        min_matches = min(prediction.n_matches_home_team, prediction.n_matches_away_team)
        odds_at_prediction_time = valuebet.fetch_odds_before(fixture["fixture_id"], prediction_time + _EPSILON)
        opportunities = valuebet.build_opportunities(odds_at_prediction_time, prediction, min_matches, MODEL_VERSION)

        odds_at_closing = valuebet.fetch_odds_before(fixture["fixture_id"], fixture["date"]) if closing_time else {}
        actuals = actual_outcomes_from_score(fixture["home_goals"], fixture["away_goals"])

        for opp in opportunities:
            if opp.market_key not in EVALUABLE_MARKETS or opp.odd is None:
                continue
            actual = _resolve_actual(opp.market_key, actuals)
            if actual is None:
                continue

            graded: GradedBet = grade_bet(opp.odd, actual)
            closing_odd = None
            if closing_time:
                key = valuebet.MARKET_ODDS_MAP.get(opp.market_key)
                if key and key in odds_at_closing:
                    closing_odd = odds_at_closing[key][0]

            evaluated.append(EvaluatedBet(
                fixture_id=fixture["fixture_id"], league_id=fixture["league_id"], market_key=opp.market_key,
                selection_label=opp.label, model_probability=opp.probability, odd=opp.odd,
                bookmaker_name=opp.bookmaker_name, implied_probability=opp.implied_probability, edge=opp.edge,
                opportunity_score=opp.opportunity_score, confidence=opp.confidence, data_quality=opp.data_quality,
                bet_result=graded.bet_result, profit=graded.profit, prediction_time=prediction_time,
                closing_odd=closing_odd, closing_captured_at=closing_time,
            ))

    return evaluated


def persist_evaluated_bets(backtest_run_id: int, evaluated: list[EvaluatedBet]) -> int:
    if not evaluated:
        return 0
    conn = db.get_connection()
    saved = 0
    try:
        with conn.cursor() as cur:
            for b in evaluated:
                cur.execute(
                    """INSERT INTO backtest_bets (
                           backtest_run_id, fixture_id, market_key, predicted_probability,
                           implied_probability, edge_predicted, opportunity_score, odd_used,
                           bookmaker_name, result, profit_loss, odds_captured_at, closing_odd,
                           closing_odds_captured_at, odds_known_before_kickoff, evaluation_source
                       ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        backtest_run_id, b.fixture_id, b.market_key, b.model_probability,
                        b.implied_probability, b.edge, b.opportunity_score, b.odd,
                        b.bookmaker_name, b.bet_result, b.profit, b.prediction_time, b.closing_odd,
                        b.closing_captured_at, True, EVALUATION_SOURCE,
                    ),
                )
                saved += 1
        conn.commit()
    finally:
        conn.close()
    return saved
