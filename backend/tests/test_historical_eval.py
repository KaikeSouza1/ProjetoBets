"""Integração real: fabrica 1 partida finalizada com odd pré-jogo (o cenário que HOJE
não existe no banco real do projeto — ver relatório de auditoria) pra provar que o
pipeline funciona quando o dado existir, e limpa tudo no final.

Usa times reais (12, 24) que já têm histórico BSA — só o resultado final e a odd
são fabricados. Data da partida (20/08/2026) é posterior a todo o histórico finalizado
de BSA no banco (até 17/08/2026), então o treino usa o histórico real completo."""
from datetime import datetime, timedelta, timezone

import pytest

from app.core import db
from app.engine.backtest.historical_eval import evaluate_historical_bets

FIXTURE_ID = 999999001
LEAGUE_ID = 71  # Serie A (Brazil), football_data_code='BSA'
HOME_TEAM_ID = 12
AWAY_TEAM_ID = 24
KICKOFF = datetime(2026, 8, 20, 20, 0, tzinfo=timezone.utc)
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


def test_real_database_has_zero_eligible_historical_bets_today():
    """Não é um teste 'deveria passar sempre' — documenta o achado real da auditoria.
    Se este teste começar a falhar (bets > 0), é uma boa notícia: significa que o
    projeto já tem odd pré-jogo genuína pra alguma partida encerrada."""
    bets = evaluate_historical_bets(league_id=None)
    assert len(bets) == 0
