"""Integração real com Postgres. `fixtures_with_incomplete_statistics` é a correção do
achado real na auditoria de cota (25/08/2026): `fetch_statistics` grava só os
`stat_type` que a API devolver — uma fixture pode ter LINHA em `fixture_statistics`
sem ter Corner Kicks/Cards pros dois times, e o guard antigo (`NOT EXISTS` sobre
fixture_id só) tratava isso como 'já processado', nunca retentando."""
import pytest

from app.core import db
from app.engine.jobs import fixture_detail

LEAGUE_ID = 71
FIXTURE_NONE = 999993001       # nenhuma estatística
FIXTURE_PARTIAL = 999993002    # tem linha, mas falta Corner Kicks do visitante
FIXTURE_COMPLETE = 999993003   # tem tudo
HOME_TEAM_ID, AWAY_TEAM_ID = 26, 30


@pytest.fixture
def fixtures_with_various_stats():
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            for fid in (FIXTURE_NONE, FIXTURE_PARTIAL, FIXTURE_COMPLETE):
                cur.execute(
                    """INSERT INTO fixtures (id, league_id, date, status, home_team_id, away_team_id, home_goals, away_goals)
                       VALUES (%s, %s, now() - interval '1 day', 'FT', %s, %s, 1, 0)""",
                    (fid, LEAGUE_ID, HOME_TEAM_ID, AWAY_TEAM_ID),
                )

            # PARTIAL: só o time da casa tem Corner Kicks, o visitante não
            cur.execute(
                """INSERT INTO fixture_statistics (fixture_id, team_id, stat_type, value) VALUES
                       (%s, %s, 'Corner Kicks', '5'), (%s, %s, 'Yellow Cards', '2'), (%s, %s, 'Yellow Cards', '1')""",
                (FIXTURE_PARTIAL, HOME_TEAM_ID, FIXTURE_PARTIAL, HOME_TEAM_ID, FIXTURE_PARTIAL, AWAY_TEAM_ID),
            )

            # COMPLETE: os dois times com Corner Kicks e cartão
            for team_id in (HOME_TEAM_ID, AWAY_TEAM_ID):
                cur.execute(
                    """INSERT INTO fixture_statistics (fixture_id, team_id, stat_type, value) VALUES
                           (%s, %s, 'Corner Kicks', '6'), (%s, %s, 'Yellow Cards', '1')""",
                    (FIXTURE_COMPLETE, team_id, FIXTURE_COMPLETE, team_id),
                )
        conn.commit()
    finally:
        conn.close()

    yield

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            fids = (FIXTURE_NONE, FIXTURE_PARTIAL, FIXTURE_COMPLETE)
            cur.execute("DELETE FROM fixture_statistics WHERE fixture_id = ANY(%s)", (list(fids),))
            cur.execute("DELETE FROM fixture_player_stats WHERE fixture_id = ANY(%s)", (list(fids),))
            cur.execute("DELETE FROM fixtures WHERE id = ANY(%s)", (list(fids),))
        conn.commit()
    finally:
        conn.close()


def test_incomplete_includes_none_and_partial_but_not_complete(fixtures_with_various_stats):
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            incomplete = set(fixture_detail.fixtures_with_incomplete_statistics(cur, league_ids=[LEAGUE_ID]))
    finally:
        conn.close()
    assert FIXTURE_NONE in incomplete
    assert FIXTURE_PARTIAL in incomplete  # achado real: linha existe, mas está incompleta
    assert FIXTURE_COMPLETE not in incomplete


def test_missing_player_stats_true_until_any_row_exists(fixtures_with_various_stats):
    player_id = 999993099
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            missing = set(fixture_detail.fixtures_missing_player_stats(cur, league_ids=[LEAGUE_ID]))
            assert FIXTURE_COMPLETE in missing

            cur.execute(
                "INSERT INTO players (id, name) VALUES (%s, 'Jogador Teste') ON CONFLICT DO NOTHING",
                (player_id,),
            )
            cur.execute(
                """INSERT INTO fixture_player_stats (fixture_id, team_id, player_id, minutes)
                   VALUES (%s, %s, %s, 90)""",
                (FIXTURE_COMPLETE, HOME_TEAM_ID, player_id),
            )
        conn.commit()
        with conn.cursor() as cur:
            missing_after = set(fixture_detail.fixtures_missing_player_stats(cur, league_ids=[LEAGUE_ID]))
            assert FIXTURE_COMPLETE not in missing_after
    finally:
        conn.close()
        cleanup = db.get_connection()
        try:
            with cleanup.cursor() as cur:
                cur.execute("DELETE FROM fixture_player_stats WHERE player_id = %s", (player_id,))
                cur.execute("DELETE FROM players WHERE id = %s", (player_id,))
            cleanup.commit()
        finally:
            cleanup.close()
