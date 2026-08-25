"""Integração real com Postgres — leads e fila reais, oportunidades injetadas (mesmos
schemas pydantic reais que o dashboard produz, sem precisar montar fixture+odds+modelo
completos). Ver services/opportunity_notifications.py."""
import datetime

import pytest

from app.api.schemas.match import DataState, MatchSummaryOut, OpportunityOut
from app.core import db
from app.services import opportunity_notifications as svc

LEAD_GRATIS_PHONE = "5599999990001"
LEAD_PRO_PHONE = "5599999990002"


def _make_opportunity(fixture_id: int, market_key: str, score: float) -> MatchSummaryOut:
    return MatchSummaryOut(
        fd_match_id=fixture_id,
        fixture_id=fixture_id,
        date=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3),
        status="NS",
        league_id=71,
        league_name="Liga Teste",
        home_team_id=26,
        home_team="Grêmio",
        away_team_id=30,
        away_team="Bahia",
        state=DataState.READY,
        best_opportunity=OpportunityOut(
            market_key=market_key, label="Vitória da casa", probability=0.55,
            odd=2.10, bookmaker_name="Bet365", implied_probability=1 / 2.10,
            edge=0.55 - 1 / 2.10, expected_value=0.55 * 2.10 - 1,
            confidence="alta", data_quality=80, opportunity_score=score, model_version="test-v1",
        ),
    )


@pytest.fixture
def leads_and_queue():
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO whatsapp_leads (name, phone, plan) VALUES
                       ('Teste Grátis', %s, 'gratis'), ('Teste Pro', %s, 'pro')
                   RETURNING id""",
                (LEAD_GRATIS_PHONE, LEAD_PRO_PHONE),
            )
            lead_ids = [r[0] for r in cur.fetchall()]
        conn.commit()
    finally:
        conn.close()

    yield lead_ids

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM notification_queue WHERE to_phone IN (%s, %s)", (LEAD_GRATIS_PHONE, LEAD_PRO_PHONE))
            cur.execute("DELETE FROM whatsapp_leads WHERE id = ANY(%s)", (lead_ids,))
        conn.commit()
    finally:
        conn.close()


def test_gratis_lead_gets_one_pro_lead_gets_up_to_three(leads_and_queue):
    opportunities = [
        _make_opportunity(999991001, "home_win", 0.09),
        _make_opportunity(999991002, "btts_yes", 0.07),
        _make_opportunity(999991003, "over_2_5", 0.05),
        _make_opportunity(999991004, "away_win", 0.03),  # 4ª — nenhum plano hoje inclui
    ]
    # n_leads/enqueued totais não são fixáveis aqui — a tabela tem leads reais de
    # produção além dos 2 de teste; a asserção que importa é por telefone, abaixo.
    svc.enqueue_daily_opportunities(datetime.date.today(), opportunities=opportunities)

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT to_phone FROM notification_queue WHERE to_phone = %s", (LEAD_GRATIS_PHONE,))
            assert len(cur.fetchall()) == 1
            cur.execute("SELECT to_phone FROM notification_queue WHERE to_phone = %s", (LEAD_PRO_PHONE,))
            assert len(cur.fetchall()) == 3
    finally:
        conn.close()


def test_same_day_rerun_does_not_duplicate(leads_and_queue):
    opportunities = [_make_opportunity(999991005, "home_win", 0.08)]
    today = datetime.date.today()

    svc.enqueue_daily_opportunities(today, opportunities=opportunities)
    svc.enqueue_daily_opportunities(today, opportunities=opportunities)

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM notification_queue WHERE to_phone IN (%s, %s)",
                (LEAD_GRATIS_PHONE, LEAD_PRO_PHONE),
            )
            # 1 grátis + 1 pro (só a 1ª oportunidade existe) — 2ª chamada não duplica
            assert cur.fetchone()[0] == 2
    finally:
        conn.close()


def test_no_opportunities_skips_leads_without_sending_anything(leads_and_queue):
    svc.enqueue_daily_opportunities(datetime.date.today(), opportunities=[])

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM notification_queue WHERE to_phone IN (%s, %s)",
                (LEAD_GRATIS_PHONE, LEAD_PRO_PHONE),
            )
            assert cur.fetchone()[0] == 0
    finally:
        conn.close()
