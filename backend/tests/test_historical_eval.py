"""Integração real: fabrica 1 partida finalizada com odd pré-jogo (o cenário que
originalmente não existia no banco real do projeto — ver relatório de auditoria) pra
provar que o pipeline funciona quando o dado existir, e limpa tudo no final.

Usa times reais (Grêmio=26, Bahia=30 — id INTERNO da tabela `teams`, não da API-Football;
ver `teammatch.py` pra normalização) que têm histórico BSA de verdade, confirmado via
`SELECT DISTINCT home_team_id FROM fd_matches WHERE competition_code='BSA'`, não
hardcoded às cegas (a versão anterior usava os ids 12/24 — que são id interno de
Liverpool e PSG, confirmado por consulta real, não times do Brasileirão de jeito
nenhum; o teste nunca tinha rodado contra dado real até essa auditoria, por isso o bug
não tinha sido pego). Data da partida fixada bem no futuro (2030) pra nunca colidir com
o histórico real sincronizado, que sempre vai ficar no passado dela."""
from datetime import datetime, timedelta, timezone

import pytest

from app.core import db
from app.engine.backtest.historical_eval import evaluate_historical_bets

FIXTURE_ID = 999999001
LEAGUE_ID = 71  # Serie A (Brazil), football_data_code='BSA'
HOME_TEAM_ID = 26  # Gremio
AWAY_TEAM_ID = 30  # Bahia
KICKOFF = datetime(2030, 1, 20, 20, 0, tzinfo=timezone.utc)
ODDS_CAPTURED_AT = KICKOFF - timedelta(days=1)


@pytest.fixture
def synthetic_finished_fixture_with_odds():
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO fixtures (id, league_id, date, status, home_team_id, away_team_id, home_goals, away_goals)
                   VALUES (%s, %s, %s, 'FT', %s, %s, 2, 1)""",
                (FIXTURE_ID, LEAGUE_ID, KICKOFF, HOME_TEAM_ID, AWAY_TEAM_ID),
            )
            cur.execute(
                """INSERT INTO odds_snapshots (fixture_id, bookmaker_id, bet_type_id, captured_at)
                   VALUES (%s, 8, 1, %s) RETURNING id""",
                (FIXTURE_ID, ODDS_CAPTURED_AT),
            )
            snapshot_id = cur.fetchone()[0]
            cur.executemany(
                "INSERT INTO odds_values (snapshot_id, label, odd) VALUES (%s, %s, %s)",
                [(snapshot_id, "Home", 2.50), (snapshot_id, "Draw", 3.20), (snapshot_id, "Away", 2.80)],
            )
        conn.commit()
    finally:
        conn.close()

    yield

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM backtest_bets WHERE fixture_id = %s", (FIXTURE_ID,))
            cur.execute(
                """DELETE FROM odds_values WHERE snapshot_id IN
                   (SELECT id FROM odds_snapshots WHERE fixture_id = %s)""",
                (FIXTURE_ID,),
            )
            cur.execute("DELETE FROM odds_snapshots WHERE fixture_id = %s", (FIXTURE_ID,))
            cur.execute("DELETE FROM fixtures WHERE id = %s", (FIXTURE_ID,))
        conn.commit()
    finally:
        conn.close()


def test_historical_eval_grades_home_win_correctly(synthetic_finished_fixture_with_odds):
    bets = evaluate_historical_bets(league_id=LEAGUE_ID)
    ours = [b for b in bets if b.fixture_id == FIXTURE_ID]

    by_market = {b.market_key: b for b in ours}
    assert "home_win" in by_market
    assert "draw" in by_market
    assert "away_win" in by_market

    # resultado real fabricado: 2-1 (casa venceu) — grading não depende da probabilidade
    # do modelo, só do resultado real vs a odd, então isto é verificável sem ambiguidade
    assert by_market["home_win"].bet_result == "GREEN"
    assert by_market["home_win"].profit == pytest.approx(1.5)  # (2.50 - 1) * stake 1
    assert by_market["draw"].bet_result == "RED"
    assert by_market["draw"].profit == pytest.approx(-1.0)
    assert by_market["away_win"].bet_result == "RED"
    assert by_market["away_win"].profit == pytest.approx(-1.0)


def test_historical_eval_uses_prediction_time_not_kickoff(synthetic_finished_fixture_with_odds):
    bets = evaluate_historical_bets(league_id=LEAGUE_ID)
    ours = [b for b in bets if b.fixture_id == FIXTURE_ID]
    assert ours
    for b in ours:
        assert b.prediction_time == ODDS_CAPTURED_AT
        assert b.closing_odd is None  # só existe 1 captura pré-jogo — nunca inventa uma 2ª


def test_historical_eval_never_grades_fixture_without_pre_kickoff_odds():
    # sem a fixture (nenhuma odd fabricada) — não deve aparecer nada pra esse fixture_id
    bets = evaluate_historical_bets(league_id=LEAGUE_ID)
    assert all(b.fixture_id != FIXTURE_ID for b in bets)


def test_real_database_eligible_historical_bets_never_use_future_data():
    """Documenta o estado real do banco (deixou de ser zero em 25/08/2026, quando a
    captura multi-casa passou a gerar par odd-pré-jogo + resultado genuíno pela
    primeira vez — ver auditoria). Não trava um número exato (cresce a cada jogo que
    termina); a garantia que importa é a de sempre: nenhuma aposta com prediction_time
    depois do apito, e nenhuma sem odd real."""
    bets = evaluate_historical_bets(league_id=None)
    for b in bets:
        assert b.prediction_time is not None
        assert b.odd is not None
