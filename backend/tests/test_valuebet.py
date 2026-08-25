"""Testes puros do núcleo de valuebet — nenhum toca banco. Casos mínimos pedidos:
odd 2.00 / 1.50 / 3.00 contra probabilidades conhecidas, checando implied_probability e edge."""
import math
from types import SimpleNamespace

import pytest

from app.engine.valuebet.valuebet import (
    build_opportunities, calculate_opportunity_score, confidence_label,
    data_quality_score, edge, expected_value, implied_probability,
)


# ==================== implied_probability ====================

@pytest.mark.parametrize("odd,expected", [(2.00, 0.5), (1.50, 2 / 3), (3.00, 1 / 3)])
def test_implied_probability(odd, expected):
    assert math.isclose(implied_probability(odd), expected, rel_tol=1e-9)


# ==================== edge ====================

@pytest.mark.parametrize("odd,model_prob,expected_edge", [
    (2.00, 0.60, 0.60 - 0.5),
    (1.50, 0.70, 0.70 - 2 / 3),
    (3.00, 0.40, 0.40 - 1 / 3),
])
def test_edge_consistent_with_implied_probability(odd, model_prob, expected_edge):
    implied = implied_probability(odd)
    assert math.isclose(edge(model_prob, implied), expected_edge, rel_tol=1e-9)


def test_edge_zero_when_model_matches_market():
    # odd "justa" pra uma probabilidade: edge deve ser ~0
    odd = 1 / 0.6
    assert math.isclose(edge(0.6, implied_probability(odd)), 0.0, abs_tol=1e-9)


# ==================== expected_value ====================

@pytest.mark.parametrize("odd,model_prob,expected_ev", [
    (2.00, 0.60, 0.6 * 2.00 - 1),
    (1.50, 0.70, 0.7 * 1.50 - 1),
    (3.00, 0.40, 0.4 * 3.00 - 1),
])
def test_expected_value(odd, model_prob, expected_ev):
    assert math.isclose(expected_value(model_prob, odd), expected_ev, rel_tol=1e-9)


# ==================== confidence_label ====================

@pytest.mark.parametrize("n,expected", [(0, "baixa"), (5, "baixa"), (6, "média"), (14, "média"), (15, "alta"), (100, "alta")])
def test_confidence_label_boundaries(n, expected):
    assert confidence_label(n) == expected


# ==================== data_quality_score ====================

def test_data_quality_score_zero_sample_no_odds():
    assert data_quality_score(0, has_odds=False) == 0


def test_data_quality_score_saturates_at_30_matches():
    assert data_quality_score(30, has_odds=True) == 100
    assert data_quality_score(300, has_odds=True) == 100  # não cresce além de 30 — documentado no docstring


def test_data_quality_score_odds_bonus_is_20_points():
    without_odds = data_quality_score(15, has_odds=False)
    with_odds = data_quality_score(15, has_odds=True)
    assert with_odds - without_odds == 20


# ==================== calculate_opportunity_score ====================

def test_opportunity_score_none_without_edge():
    assert calculate_opportunity_score(None, "alta", 100) is None


def test_opportunity_score_full_confidence_full_quality_equals_edge():
    # confidence_weight=1.0 (alta) e quality=100 -> fator = 1.0 * (0.5+0.5) = 1.0 -> score == edge
    assert math.isclose(calculate_opportunity_score(0.10, "alta", 100), 0.10, rel_tol=1e-9)


def test_opportunity_score_low_confidence_low_quality_shrinks_edge():
    score = calculate_opportunity_score(0.10, "baixa", 0)
    assert math.isclose(score, 0.10 * 0.3 * 0.5, rel_tol=1e-9)
    assert score < 0.10  # nunca amplifica o edge, só reduz


def test_opportunity_score_monotonic_in_quality():
    low_q = calculate_opportunity_score(0.10, "alta", 0)
    high_q = calculate_opportunity_score(0.10, "alta", 100)
    assert high_q > low_q


# ==================== build_opportunities (puro, sem DB) ====================

def _fake_prediction(markets: dict) -> SimpleNamespace:
    return SimpleNamespace(markets=markets)


def test_build_opportunities_without_odds_has_no_score_but_has_probability():
    prediction = _fake_prediction({"btts_yes": 0.61, "over_2_5": 0.55})
    opportunities = build_opportunities({}, prediction, min_matches_for_market=20, model_version="test-v1")
    assert len(opportunities) == 2
    for o in opportunities:
        assert o.odd is None
        assert o.edge is None
        assert o.opportunity_score is None
        assert o.probability in (0.61, 0.55)


def test_build_opportunities_with_odds_computes_edge_and_score():
    prediction = _fake_prediction({"btts_yes": 0.61})
    # (8, "Yes") é a chave de odds pro mercado btts_yes, ver GOALS_ODDS_MAP
    odds_lookup = {(8, "Yes"): (1.82, "Bet365")}
    opportunities = build_opportunities(odds_lookup, prediction, min_matches_for_market=20, model_version="test-v1")
    assert len(opportunities) == 1
    o = opportunities[0]
    assert o.odd == 1.82
    assert o.bookmaker_name == "Bet365"
    assert math.isclose(o.implied_probability, 1 / 1.82, rel_tol=1e-9)
    assert math.isclose(o.edge, 0.61 - 1 / 1.82, rel_tol=1e-9)
    assert o.opportunity_score is not None
    assert o.model_version == "test-v1"  # toda previsão persistida precisa saber qual modelo/versão a gerou


def test_build_opportunities_never_invents_an_odd():
    # mercado sem chave nenhuma no odds_lookup (ex.: escanteios sem odd capturada)
    prediction = _fake_prediction({"corner_over_9_5": 0.5})
    opportunities = build_opportunities({}, prediction, min_matches_for_market=3, model_version="test-v1")
    assert opportunities[0].odd is None
    assert opportunities[0].opportunity_score is None


def test_build_opportunities_probability_is_native_float_not_numpy():
    # regressão: np.float64 vindo do modelo Poisson não pode vazar pra fora do
    # motor — psycopg2 não sabe adaptar esse tipo (achado real durante a Fase de
    # snapshots, ver valuebet.build_opportunities)
    import numpy as np
    prediction = _fake_prediction({"over_2_5": np.float64(0.55)})
    opportunities = build_opportunities({}, prediction, min_matches_for_market=10, model_version="test-v1")
    assert type(opportunities[0].probability) is float
