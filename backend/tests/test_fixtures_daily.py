"""Integração real com Postgres. `_recently_synced` é a trava contra o achado real da
auditoria de cota: `run_daily_sync` roda inteiro de novo em todo restart do scheduler
(deploy, ou o crash loop investigado em 25/08/2026) — sem isso, restart repetido em
sequência curta refaz as 3 chamadas de fixtures (ontem/hoje/amanhã) do zero, cada vez."""
import datetime

import pytest

from app.core import db
from app.engine.jobs import fixtures_daily

TEST_DATE = datetime.date(2099, 1, 1)  # nunca colide com sync real


@pytest.fixture
def clean_raw_payload():
    yield
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM raw_api_payloads WHERE source='api-football' AND endpoint='fixtures' AND params->>'date' = %s",
                (TEST_DATE.isoformat(),),
            )
        conn.commit()
    finally:
        conn.close()


def _seed_recent_payload(minutes_ago: int):
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO raw_api_payloads (source, endpoint, params, payload, fetched_at)
                   VALUES ('api-football', 'fixtures', %s, '{}', now() - (%s || ' minutes')::interval)""",
                ('{"date": "%s"}' % TEST_DATE.isoformat(), minutes_ago),
            )
        conn.commit()
    finally:
        conn.close()


def test_no_recent_payload_means_not_recently_synced(clean_raw_payload):
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            assert fixtures_daily._recently_synced(cur, TEST_DATE) is False
    finally:
        conn.close()


def test_payload_inside_cooldown_counts_as_recently_synced(clean_raw_payload):
    _seed_recent_payload(minutes_ago=5)
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            assert fixtures_daily._recently_synced(cur, TEST_DATE) is True
    finally:
        conn.close()


def test_payload_outside_cooldown_does_not_count(clean_raw_payload):
    _seed_recent_payload(minutes_ago=fixtures_daily.SYNC_FRESHNESS_COOLDOWN_MINUTES + 5)
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            assert fixtures_daily._recently_synced(cur, TEST_DATE) is False
    finally:
        conn.close()


def test_sync_skips_api_call_when_recently_synced(clean_raw_payload, monkeypatch):
    _seed_recent_payload(minutes_ago=1)

    def _fail_if_called(day):
        raise AssertionError("não deveria chamar a API — sync recente já existe")

    monkeypatch.setattr(fixtures_daily.api_football_fixtures, "fetch_fixtures_for_date", _fail_if_called)
    saved = fixtures_daily.sync_fixtures_for_date(TEST_DATE)
    assert saved == 0
