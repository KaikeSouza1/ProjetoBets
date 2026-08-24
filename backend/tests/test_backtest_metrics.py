"""Testes puros das métricas de avaliação — nenhum toca banco."""
import math

from app.engine.backtest.metrics import (
    GREEN, PUSH, RED, UNRESOLVED, VOID,
    bucket_performance, calibration_table, grade_bet, hit_rate,
    roi_and_yield, sample_confidence_label,
)
from app.engine.backtest.metrics import brier_score_binary, brier_score_multiclass


# ==================== Brier ====================

def test_brier_binary_perfect_calibration_is_zero():
    assert brier_score_binary([(1.0, True), (0.0, False)]) == 0.0


def test_brier_binary_worst_case_is_one():
    assert brier_score_binary([(1.0, False), (0.0, True)]) == 1.0


def test_brier_binary_always_50_50_is_quarter():
    pairs = [(0.5, True), (0.5, False), (0.5, True), (0.5, False)]
    assert math.isclose(brier_score_binary(pairs), 0.25)


def test_brier_binary_empty_is_none():
    assert brier_score_binary([]) is None


def test_brier_multiclass_perfect_is_zero():
    rows = [({"home_win": 1.0, "draw": 0.0, "away_win": 0.0}, "home_win")]
    assert brier_score_multiclass(rows) == 0.0


def test_brier_multiclass_uniform_guess_on_3_classes():
    # 1/3 pra cada classe, acertou "draw": (1/3-0)^2 + (1/3-1)^2 + (1/3-0)^2
    rows = [({"home_win": 1 / 3, "draw": 1 / 3, "away_win": 1 / 3}, "draw")]
    expected = (1 / 3) ** 2 + (1 / 3 - 1) ** 2 + (1 / 3) ** 2
    assert math.isclose(brier_score_multiclass(rows), expected)


def test_brier_multiclass_range_can_exceed_binary_range():
    # prova que a escala é [0,2], não [0,1] — nunca comparar lado a lado com o binário
    rows = [({"home_win": 0.0, "draw": 0.0, "away_win": 1.0}, "home_win")]
    assert brier_score_multiclass(rows) == 2.0


# ==================== calibração ====================

def test_calibration_table_matches_predicted_to_realized():
    predictions = [(0.75, True)] * 69 + [(0.75, False)] * 31  # 100 previsões a 75%, 69% aconteceram
    table = calibration_table(predictions, buckets=[(0.7, 0.8)])
    row = table[0]
    assert row["n"] == 100
    assert math.isclose(row["mean_predicted"], 0.75)
    assert math.isclose(row["realized_frequency"], 0.69)
    assert row["confidence"] == "representativa"


def test_calibration_table_empty_bucket_has_no_numbers_but_is_not_omitted():
    table = calibration_table([], buckets=[(0.9, 1.0)])
    assert len(table) == 1
    assert table[0]["n"] == 0
    assert table[0]["mean_predicted"] is None
    assert table[0]["confidence"] == "insuficiente"


# ==================== grading ====================

def test_grade_bet_green_profit_matches_odd():
    graded = grade_bet(odd=2.00, actual_outcome=True)
    assert graded.bet_result == GREEN
    assert math.isclose(graded.profit, 1.0)

    graded = grade_bet(odd=1.50, actual_outcome=True)
    assert math.isclose(graded.profit, 0.5)


def test_grade_bet_red_always_loses_full_stake_regardless_of_odd():
    assert grade_bet(odd=5.00, actual_outcome=False).profit == -1.0
    assert grade_bet(odd=1.10, actual_outcome=False).profit == -1.0


def test_grade_bet_unresolved_when_outcome_unknown():
    graded = grade_bet(odd=2.00, actual_outcome=None)
    assert graded.bet_result == UNRESOLVED
    assert graded.profit is None


def test_grade_bet_respects_custom_stake():
    graded = grade_bet(odd=2.00, actual_outcome=True, stake=10.0)
    assert graded.profit == 10.0


# ==================== hit rate vs ROI (nunca a mesma coisa) ====================

def test_hit_rate_excludes_push_void_unresolved():
    results = [GREEN, GREEN, RED, PUSH, VOID, UNRESOLVED]
    stats = hit_rate(results)
    assert stats["n"] == 3  # só GREEN/GREEN/RED contam
    assert math.isclose(stats["hit_rate"], 2 / 3)


def test_low_hit_rate_can_still_have_positive_roi():
    # 1 acerto em odd alta cobre 2 erros — hit rate baixo, ROI positivo
    results = [GREEN, RED, RED]
    profits = [9.0, -1.0, -1.0]
    hr = hit_rate(results)
    roi = roi_and_yield(results, profits)
    assert math.isclose(hr["hit_rate"], 1 / 3)
    assert roi["roi"] > 0
    assert roi["roi"] != hr["hit_rate"]  # nunca confundir as duas


def test_roi_and_yield_are_equal_under_fixed_stake():
    results = [GREEN, RED]
    profits = [1.0, -1.0]
    stats = roi_and_yield(results, profits, stake=1.0)
    assert math.isclose(stats["roi"] * 100, stats["yield_pct"])


def test_roi_zero_settled_bets_is_insufficient_not_zero():
    stats = roi_and_yield([PUSH, VOID, UNRESOLVED], [None, None, None])
    assert stats["n"] == 0
    assert stats["roi"] is None
    assert stats["confidence"] == "insuficiente"


# ==================== sample confidence ====================

def test_sample_confidence_thresholds():
    assert sample_confidence_label(5) == "insuficiente"
    assert sample_confidence_label(19) == "insuficiente"
    assert sample_confidence_label(20) == "limitada"
    assert sample_confidence_label(99) == "limitada"
    assert sample_confidence_label(100) == "representativa"


def test_sample_confidence_thresholds_are_configurable():
    assert sample_confidence_label(50, insufficient=10, limited=60) == "limitada"


# ==================== buckets (edge / opportunity score) ====================

def test_bucket_performance_never_shows_number_for_tiny_sample():
    values = [0.02]
    results = [GREEN]
    profits = [2.0]
    buckets = bucket_performance(values, results, profits, buckets=[(0.0, 0.03), (0.03, 0.05)])
    low_bucket = buckets[0]
    assert low_bucket["n_bets"] == 1
    assert low_bucket["confidence"] == "insuficiente"  # 1 aposta nunca é "resultado", é ruído


def test_bucket_performance_uses_exact_requested_edges_not_tuned():
    # garante que os buckets pedidos (0-3/3-5/5-10/10-15/15+) não são silenciosamente
    # trocados por outra faixa "mais bonita"
    values = [0.01, 0.04, 0.07, 0.12, 0.20]
    results = [GREEN] * 5
    profits = [1.0] * 5
    buckets = [(0.0, 0.03), (0.03, 0.05), (0.05, 0.10), (0.10, 0.15), (0.15, 999.0)]
    rows = bucket_performance(values, results, profits, buckets)
    assert [r["n_bets"] for r in rows] == [1, 1, 1, 1, 1]
