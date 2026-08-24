"""Integração real com Postgres — usa fixture_id/fd_match_id NULL (ambos aceitos pelo
schema) pra não depender de nenhuma partida específica existir, e limpa a própria linha
no final. Ver core/schema.sql: prediction_snapshots."""
from dataclasses import dataclass

from app.core import db
from app.services import snapshot_service


@dataclass
class _FakeOpportunity:
    market_key: str
    label: str
    probability: float
    odd: float | None
    bookmaker_name: str | None
    implied_probability: float | None
    edge: float | None
    expected_value: float | None
    confidence: str
    data_quality: int
    opportunity_score: float | None


def _cleanup(ids: list[int]):
    if not ids:
        return
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM prediction_snapshots WHERE id = ANY(%s)", (ids,))
        conn.commit()
    finally:
        conn.close()


def test_record_and_read_back_snapshot():
    opp = _FakeOpportunity(
        market_key="btts_yes", label="Ambas marcam — sim", probability=0.61,
        odd=1.82, bookmaker_name="Bet365", implied_probability=1 / 1.82,
        edge=0.61 - 1 / 1.82, expected_value=0.61 * 1.82 - 1,
        confidence="alta", data_quality=87, opportunity_score=0.05,
    )
    saved = snapshot_service.record_snapshot(fixture_id=None, fd_match_id=None, opportunities=[opp])
    assert saved == 1

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, market_key, model_probability, odd, confidence, data_quality, opportunity_score
                   FROM prediction_snapshots
                   WHERE fixture_id IS NULL AND fd_match_id IS NULL AND market_key = 'btts_yes'
                   ORDER BY created_at DESC LIMIT 1"""
            )
            row = cur.fetchone()
    finally:
        conn.close()

    assert row is not None
    row_id, market_key, prob, odd, confidence, quality, score = row
    assert market_key == "btts_yes"
    assert float(prob) == 0.61
    assert float(odd) == 1.82
    assert confidence == "alta"
    _cleanup([row_id])


def test_record_snapshot_is_append_only_not_overwrite():
    opp_a = _FakeOpportunity(
        market_key="over_2_5", label="Mais de 2.5 gols", probability=0.55, odd=1.91,
        bookmaker_name="Bet365", implied_probability=1 / 1.91, edge=0.55 - 1 / 1.91,
        expected_value=0.55 * 1.91 - 1, confidence="alta", data_quality=90, opportunity_score=0.03,
    )
    opp_b = _FakeOpportunity(**{**opp_a.__dict__, "probability": 0.58, "odd": 1.85})

    snapshot_service.record_snapshot(None, None, [opp_a])
    snapshot_service.record_snapshot(None, None, [opp_b])

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, model_probability FROM prediction_snapshots
                   WHERE fixture_id IS NULL AND fd_match_id IS NULL AND market_key = 'over_2_5'
                   ORDER BY created_at"""
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    assert len(rows) >= 2  # as duas chamadas geraram linhas separadas, nenhuma sobrescreveu a outra
    probs = [float(r[1]) for r in rows[-2:]]
    assert probs == [0.55, 0.58]
    _cleanup([r[0] for r in rows])


def test_record_snapshot_skips_empty_list():
    assert snapshot_service.record_snapshot(None, None, []) == 0
