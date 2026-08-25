"""Integração real com Postgres pro lookup de plano do lead; oportunidades injetadas
(mesmo padrão de test_opportunity_notifications.py) pra não depender de fixture+odds+
modelo completos só pra testar o comando."""
import datetime

import pytest

from app.api.schemas.match import DataState, MatchSummaryOut, OpportunityOut
from app.core import db
from app.services import whatsapp_commands as svc

PHONE_GRATIS = "5599999990010"
PHONE_PRO = "5599999990011"
PHONE_UNKNOWN = "5599999990012"


def _make_opportunity(fixture_id: int) -> MatchSummaryOut:
    return MatchSummaryOut(
        fd_match_id=fixture_id, fixture_id=fixture_id,
        date=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3),
        status="NS", league_id=71, league_name="Liga Teste",
        home_team_id=26, home_team="Grêmio", away_team_id=30, away_team="Bahia",
        state=DataState.READY,
        best_opportunity=OpportunityOut(
            market_key="home_win", label="Vitória da casa", probability=0.55,
            odd=2.10, bookmaker_name="Bet365", implied_probability=1 / 2.10,
            edge=0.55 - 1 / 2.10, expected_value=0.55 * 2.10 - 1,
            confidence="alta", data_quality=80, opportunity_score=0.09, model_version="test-v1",
        ),
    )


@pytest.fixture
def leads():
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO whatsapp_leads (name, phone, plan) VALUES
                       ('Teste Grátis', %s, 'gratis'), ('Teste Pro', %s, 'pro')""",
                (PHONE_GRATIS, PHONE_PRO),
            )
        conn.commit()
    finally:
        conn.close()

    yield

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM whatsapp_leads WHERE phone IN (%s, %s)", (PHONE_GRATIS, PHONE_PRO))
        conn.commit()
    finally:
        conn.close()


def test_non_command_text_returns_none(leads):
    assert svc.handle_command(PHONE_GRATIS, "oi tudo bem?") is None


def test_odds_command_respects_plan_limit(leads):
    opportunities = [_make_opportunity(999992001), _make_opportunity(999992002), _make_opportunity(999992003)]

    reply_gratis = svc.handle_command(PHONE_GRATIS, "/odds", opportunities=opportunities)
    reply_pro = svc.handle_command(PHONE_PRO, "/odds", opportunities=opportunities)

    assert reply_gratis.count("Grêmio x Bahia") == 1
    assert reply_pro.count("Grêmio x Bahia") == 3


def test_unknown_phone_defaults_to_gratis_limit():
    opportunities = [_make_opportunity(999992004), _make_opportunity(999992005)]
    reply = svc.handle_command(PHONE_UNKNOWN, "/odds", opportunities=opportunities)
    assert reply.count("Grêmio x Bahia") == 1


def test_no_opportunities_returns_fallback_message(leads):
    reply = svc.handle_command(PHONE_GRATIS, "/odds", opportunities=[])
    assert reply == svc.NO_OPPORTUNITY_MESSAGE
