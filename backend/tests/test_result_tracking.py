"""Integração real com Postgres. Reaproveita times reais (Grêmio=26, Bahia=30 — mesmos
da suite de historical_eval) e fixture sintética finalizada 2-1 (casa venceu)."""
import pytest

from app.core import db
from app.services.result_tracking import resolve_pending_snapshots

FIXTURE_ID = 999999002
LEAGUE_ID = 71
HOME_TEAM_ID = 26
AWAY_TEAM_ID = 30


@pytest.fixture
def finished_fixture_with_snapshots():
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO fixtures (id, league_id, date, status, home_team_id, away_team_id, home_goals, away_goals)
                   VALUES (%s, %s, now() - interval '2 hours', 'FT', %s, %s, 2, 1)""",
                (FIXTURE_ID, LEAGUE_ID, HOME_TEAM_ID, AWAY_TEAM_ID),
            )
            # 3 previsões pendentes: 2 resolvíveis (mercado de gols), 1 não (escanteio —
            # nunca deveria virar GREEN/RED sem ter resolução implementada)
            for market_key, label in [("home_win", "Vitória da casa"), ("btts_yes", "Ambas marcam — sim")]:
                cur.execute(
                    """INSERT INTO prediction_snapshots
                           (fixture_id, market_key, market_label, model_probability, confidence, data_quality)
                       VALUES (%s, %s, %s, 0.5, 'baixa', 50)""",
                    (FIXTURE_ID, market_key, label),
                )
            cur.execute(
                """INSERT INTO prediction_snapshots
                       (fixture_id, market_key, market_label, model_probability, confidence, data_quality)
                   VALUES (%s, 'corner_over_9_5', 'Mais de 9.5 escanteios', 0.5, 'baixa', 50)""",
                (FIXTURE_ID,),
            )
        conn.commit()
    finally:
        conn.close()

    yield

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM prediction_snapshots WHERE fixture_id = %s", (FIXTURE_ID,))
            cur.execute("DELETE FROM fixtures WHERE id = %s", (FIXTURE_ID,))
        conn.commit()
    finally:
        conn.close()


def test_resolve_pending_snapshots_grades_goals_markets_correctly(finished_fixture_with_snapshots):
    result = resolve_pending_snapshots()
    assert result["resolved"] >= 2
    assert result["skipped_unresolvable_market"] >= 1

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT market_key, actual_outcome, resolved_at FROM prediction_snapshots WHERE fixture_id = %s",
                (FIXTURE_ID,),
            )
            rows = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    finally:
        conn.close()

    # 2-1 em casa: home_win = True, btts_yes = True (os 2 marcaram)
    assert rows["home_win"][0] is True
    assert rows["home_win"][1] is not None
    assert rows["btts_yes"][0] is True

    # escanteio nunca é inventado — fica NULL, não vira GREEN nem RED sem saber de verdade
    assert rows["corner_over_9_5"][0] is None
    assert rows["corner_over_9_5"][1] is None


def test_resolve_pending_snapshots_is_idempotent(finished_fixture_with_snapshots):
    first = resolve_pending_snapshots()
    second = resolve_pending_snapshots()
    assert first["resolved"] >= 2
    assert second["resolved"] == 0  # já resolvido — WHERE actual_outcome IS NULL exclui de novo
