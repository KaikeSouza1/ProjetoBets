"""Achado real (26/08/2026): lead 'pro' cadastrado com '5542998528674' (13 dígitos,
com o 9 do celular) mandou /odds e o WhatsApp reportou o remetente como
'554298528674' (12 dígitos, sem o 9) — comparação exata falhava, caindo pro plano
'gratis' (1 palpite) mesmo sendo 'pro' (3 palpites)."""
import pytest

from app.core import db
from app.services.whatsapp_commands import _lead_plan, _normalize_br_phone

STORED_WITH_NINE = "5542998528674"
INCOMING_WITHOUT_NINE = "554298528674"


def test_normalizes_by_stripping_the_mobile_nine():
    assert _normalize_br_phone(STORED_WITH_NINE) == _normalize_br_phone(INCOMING_WITHOUT_NINE)


def test_leaves_non_matching_formats_untouched():
    # não é o padrão 55+DDD+9+8 dígitos — nada a remover, passa direto
    assert _normalize_br_phone("12345") == "12345"
    assert _normalize_br_phone("+1 555 123 4567") == "15551234567"


@pytest.fixture
def pro_lead_registered_with_nine():
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO whatsapp_leads (name, phone, plan) VALUES ('Teste Nove', %s, 'pro') RETURNING id",
                (STORED_WITH_NINE,),
            )
            lead_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    yield

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM whatsapp_leads WHERE id = %s", (lead_id,))
        conn.commit()
    finally:
        conn.close()


def test_lead_plan_matches_despite_missing_mobile_nine(pro_lead_registered_with_nine):
    assert _lead_plan(INCOMING_WITHOUT_NINE) == "pro"
