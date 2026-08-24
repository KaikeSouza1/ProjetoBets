"""Liga só-API-Football (ex.: Copa do Brasil, sem football_data_code) precisa aparecer
na listagem/detalhe de partida mesmo sem fonte de calendário football-data.org — ver
analysis_service._fixtures_only_league_matches / _get_fixtures_only_league_match."""
from datetime import datetime, timedelta, timezone

import pytest

from app.core import db
from app.services import analysis_service as svc

FIXTURE_ID = 999999301
LEAGUE_ID = 73  # Copa do Brasil — sem football_data_code
HOME_TEAM_ID = 26
AWAY_TEAM_ID = 7


@pytest.fixture
def synthetic_cup_fixture():
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO fixtures (id, league_id, date, status, home_team_id, away_team_id)
                   VALUES (%s, %s, %s, 'NS', %s, %s)""",
                (FIXTURE_ID, LEAGUE_ID, datetime.now(timezone.utc) + timedelta(days=1), HOME_TEAM_ID, AWAY_TEAM_ID),
            )
        conn.commit()
    finally:
        conn.close()

    yield

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM fixtures WHERE id = %s", (FIXTURE_ID,))
        conn.commit()
    finally:
        conn.close()


def test_cup_fixture_appears_in_list_upcoming(synthetic_cup_fixture):
    matches = svc.list_upcoming(days_ahead=3)
    ours = [m for m in matches if m["fd_match_id"] == FIXTURE_ID]
    assert len(ours) == 1
    assert ours[0]["fixture_id"] == FIXTURE_ID
    assert ours[0]["league_id"] == LEAGUE_ID
    assert ours[0]["has_full_data"] is True


def test_cup_fixture_resolves_via_get_upcoming_match(synthetic_cup_fixture):
    match = svc.get_upcoming_match(FIXTURE_ID)
    assert match is not None
    assert match["league_id"] == LEAGUE_ID
    assert match["home_team_id"] == HOME_TEAM_ID
    assert match["away_team_id"] == AWAY_TEAM_ID


def test_leagues_without_fd_code_never_appear_twice(synthetic_cup_fixture):
    # a liga sem football_data_code não deveria também bater na query de fd_matches
    # (JOIN exige football_data_code = competition_code, então não tem como duplicar,
    # mas o teste documenta a garantia explicitamente)
    matches = svc.list_upcoming(days_ahead=3)
    ours = [m for m in matches if m["fd_match_id"] == FIXTURE_ID]
    assert len(ours) == 1
