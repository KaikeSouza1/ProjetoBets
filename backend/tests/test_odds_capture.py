"""Integração real: prova a seleção de partidas elegíveis pra captura automática de
odds sem chamar a API-Football de verdade (só testa a query de elegibilidade —
`fetch_and_store_odds` em si já é exercitado manualmente há sessões)."""
from datetime import datetime, timedelta, timezone

import pytest

from app.core import db
from app.engine.jobs.odds import _select_fixtures_for_capture

LEAGUE_ID = 71
HOME_TEAM_ID = 12
AWAY_TEAM_ID = 24

IDS = {
    "in_window_no_capture": 999999101,
    "outside_window": 999999102,
    "in_window_recent_capture": 999999103,
    "already_finished": 999999104,
    "recent_failed_attempt": 999999105,
}


@pytest.fixture
def synthetic_fixtures():
    now = datetime.now(timezone.utc)
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO fixtures (id, league_id, date, status, home_team_id, away_team_id)
                   VALUES (%s, %s, %s, 'NS', %s, %s)""",
                (IDS["in_window_no_capture"], LEAGUE_ID, now + timedelta(hours=12), HOME_TEAM_ID, AWAY_TEAM_ID),
            )
            cur.execute(
                """INSERT INTO fixtures (id, league_id, date, status, home_team_id, away_team_id)
                   VALUES (%s, %s, %s, 'NS', %s, %s)""",
                (IDS["outside_window"], LEAGUE_ID, now + timedelta(days=3), HOME_TEAM_ID, AWAY_TEAM_ID),
            )
            cur.execute(
                """INSERT INTO fixtures (id, league_id, date, status, home_team_id, away_team_id)
                   VALUES (%s, %s, %s, 'NS', %s, %s)""",
                (IDS["in_window_recent_capture"], LEAGUE_ID, now + timedelta(hours=6), HOME_TEAM_ID, AWAY_TEAM_ID),
            )
            cur.execute(
                """INSERT INTO odds_snapshots (fixture_id, bookmaker_id, bet_type_id, captured_at)
                   VALUES (%s, 8, 1, %s)""",
                (IDS["in_window_recent_capture"], now - timedelta(minutes=30)),
            )
            cur.execute(
                """INSERT INTO fixtures (id, league_id, date, status, home_team_id, away_team_id)
                   VALUES (%s, %s, %s, 'FT', %s, %s)""",
                (IDS["already_finished"], LEAGUE_ID, now - timedelta(hours=2), HOME_TEAM_ID, AWAY_TEAM_ID),
            )
            # sem odds_snapshots nenhuma (a captura falhou), mas houve uma TENTATIVA
            # recente logada em raw_api_payloads — achado real: sem essa 2ª camada de
            # cooldown, essa fixture seria retentada em todo restart do scheduler
            cur.execute(
                """INSERT INTO fixtures (id, league_id, date, status, home_team_id, away_team_id)
                   VALUES (%s, %s, %s, 'NS', %s, %s)""",
                (IDS["recent_failed_attempt"], LEAGUE_ID, now + timedelta(hours=8), HOME_TEAM_ID, AWAY_TEAM_ID),
            )
            cur.execute(
                """INSERT INTO raw_api_payloads (source, endpoint, params, payload, fetched_at)
                   VALUES ('api-football', 'odds', %s, '{}', %s)""",
                ('{"fixture": %d}' % IDS["recent_failed_attempt"], now - timedelta(minutes=5)),
            )
        conn.commit()
    finally:
        conn.close()

    yield

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM odds_snapshots WHERE fixture_id = ANY(%s)", (list(IDS.values()),))
            cur.execute(
                "DELETE FROM raw_api_payloads WHERE source='api-football' AND endpoint='odds' AND params->>'fixture' = %s",
                (str(IDS["recent_failed_attempt"]),),
            )
            cur.execute("DELETE FROM fixtures WHERE id = ANY(%s)", (list(IDS.values()),))
        conn.commit()
    finally:
        conn.close()


def test_selects_only_fixtures_inside_capture_window_without_recent_odds(synthetic_fixtures):
    selected = _select_fixtures_for_capture(max_fixtures=50, cooldown_hours=3)

    assert IDS["in_window_no_capture"] in selected
    assert IDS["outside_window"] not in selected  # fora da janela hoje±1 dia da API-Football
    assert IDS["in_window_recent_capture"] not in selected  # já capturado há 30min, dentro do cooldown de 3h
    assert IDS["already_finished"] not in selected  # não é mais NS/TBD
    assert IDS["recent_failed_attempt"] not in selected  # tentativa (com ou sem sucesso) há 5min, dentro do RETRY_COOLDOWN_MINUTES


def test_prioritizes_fixtures_never_captured_over_fixtures_with_old_capture(synthetic_fixtures):
    # dá um "capture antigo" (fora do cooldown) pro fixture sem captura nenhuma perder
    # prioridade se estivesse competindo por espaço no limite
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE odds_snapshots SET captured_at = %s WHERE fixture_id = %s",
                (datetime.now(timezone.utc) - timedelta(hours=10), IDS["in_window_recent_capture"]),
            )
        conn.commit()
    finally:
        conn.close()

    # limite alto o bastante pra incluir os 2 fixtures sintéticos mesmo com outros
    # fixtures reais também elegíveis na janela (ambiente compartilhado, não isolado)
    selected = _select_fixtures_for_capture(max_fixtures=1000, cooldown_hours=3)
    assert selected.index(IDS["in_window_no_capture"]) < selected.index(IDS["in_window_recent_capture"]), (
        "quem nunca foi capturado deve vir antes de quem já tem captura (mesmo antiga)"
    )


def test_respects_max_fixtures_limit(synthetic_fixtures):
    selected = _select_fixtures_for_capture(max_fixtures=0, cooldown_hours=3)
    assert selected == []
