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


def test_market_family_groups_nested_goal_lines_together():
    # achado real: "mais de 2.5" + "mais de 3.5" do mesmo jogo não é combinação
    # nenhuma — quem bate 3.5 SEMPRE bate 2.5, não pode entrar junto numa múltipla
    assert svc._market_family("over_2_5") == svc._market_family("over_3_5") == svc._market_family("under_1_5")


def test_market_family_groups_1x2_derived_markets_together():
    assert (
        svc._market_family("home_win")
        == svc._market_family("double_chance_1x")
        == svc._market_family("draw_no_bet_home")
    )


def test_market_family_distinguishes_goals_corners_and_cards():
    families = {svc._market_family(k) for k in ("over_2_5", "corner_over_9_5", "card_over_2_5", "btts_yes")}
    assert len(families) == 4


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


def test_gratis_lead_gets_one_pick_pro_lead_gets_up_to_three_in_one_ticket(leads_and_queue):
    opportunities = [
        _make_opportunity(999991001, "home_win", 0.09),
        _make_opportunity(999991002, "btts_yes", 0.07),
        _make_opportunity(999991003, "over_2_5", 0.05),
        _make_opportunity(999991004, "away_win", 0.03),  # 4ª — nenhum plano hoje inclui
    ]
    # multipla={} força "sem múltipla" — este teste é sobre limite de plano nos picks
    # simples, não sobre a múltipla (que tem teste dedicado abaixo, com fixture real)
    svc.enqueue_daily_opportunities(datetime.date.today(), opportunities=opportunities, multipla={})

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            # 1 bilhete só por lead (não 1 registro por palpite) — o número de picks
            # dentro do texto que muda por plano, não a quantidade de linhas na fila
            cur.execute("SELECT message FROM notification_queue WHERE to_phone = %s", (LEAD_GRATIS_PHONE,))
            rows = cur.fetchall()
            assert len(rows) == 1
            assert "PALPITE DO DIA" in rows[0][0]
            assert rows[0][0].count("Grêmio x Bahia") == 1

            cur.execute("SELECT message FROM notification_queue WHERE to_phone = %s", (LEAD_PRO_PHONE,))
            rows = cur.fetchall()
            assert len(rows) == 1
            assert "BILHETE DO DIA" in rows[0][0]
            assert "MÚLTIPLA" not in rows[0][0]
            assert rows[0][0].count("Grêmio x Bahia") == 3
    finally:
        conn.close()


def test_multipla_combines_two_different_markets_from_the_same_match(leads_and_queue):
    # partida real (Grêmio x Bahia, liga 71) com odds reais capturadas — múltipla
    # precisa dos mercados de verdade do fixture, não dá pra injetar synthetic aqui
    opportunities = [_make_opportunity(1570349, "over_2_5", 0.05)]
    multipla = svc.find_multipla(opportunities)

    if multipla is None:
        pytest.skip("nenhuma múltipla disponível pro fixture de teste no momento (dado real, pode variar)")

    assert multipla["legs"][0].market_key != multipla["legs"][1].market_key
    from app.services.opportunity_notifications import _market_family
    assert _market_family(multipla["legs"][0].market_key) != _market_family(multipla["legs"][1].market_key)

    msg = svc.format_ticket_message(opportunities, multipla)
    assert "MÚLTIPLA" in msg
    assert "Probabilidade Combinada" in msg


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
