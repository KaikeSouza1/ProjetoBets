"""Camada de serviço do backtest — o que a API expõe. Dois tipos de avaliação, NUNCA
misturados numa resposta só sem rótulo:

  CALIBRATION  — walk-forward de `engine.backtest.backtest`, sem odd, valida só se a
                 probabilidade do modelo é honesta (Brier/hit-rate). Tem dado real hoje
                 (225 partidas BSA, 7 PD).
  HISTORICAL_ODDS — `engine.backtest.historical_eval`, com odd real pré-jogo. É o único
                 jeito honesto de falar em ROI/edge/opportunity_score. Tem ZERO partidas
                 elegíveis no banco real hoje — a resposta reflete isso, nunca finge."""
from dataclasses import dataclass

from app.core import db
from app.engine.backtest import metrics
from app.engine.backtest.backtest import run_goals_backtest
from app.engine.backtest.historical_eval import EVALUATION_SOURCE, evaluate_historical_bets, persist_evaluated_bets
from app.services import analysis_service as svc


@dataclass
class CalibrationSummary:
    league_id: int
    metrics: list[dict]  # market_key, hit_rate, brier_score, n_bets, confidence, date_from, date_to


def get_calibration_summary(league_id: int) -> CalibrationSummary:
    rows = svc.get_latest_backtest_metrics(league_id)
    for row in rows:
        row["confidence"] = metrics.sample_confidence_label(row["n_bets"])
    return CalibrationSummary(league_id=league_id, metrics=rows)


def get_calibration_curve(league_id: int, market_key: str) -> list[dict]:
    """Probabilidade prevista vs frequência real, direto das linhas já persistidas pela
    última rodada de walk-forward desta liga — a pergunta 'quando o modelo diz 70%, 70%
    das vezes aconteceu?' (seção 9 da auditoria), com dado genuíno (225 partidas BSA
    hoje), não com odds (que ainda não existem historicamente)."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT bb.predicted_probability, bb.actual_outcome
                   FROM backtest_bets bb
                   WHERE bb.market_key = %s AND bb.actual_outcome IS NOT NULL
                     AND bb.backtest_run_id = (
                         SELECT MAX(backtest_run_id) FROM backtest_metrics
                         WHERE league_id = %s AND market_key = %s
                     )""",
                (market_key, league_id, market_key),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    predictions = [(float(p), bool(o)) for p, o in rows]
    return metrics.calibration_table(predictions)


def run_calibration_backtest(league_id: int, min_training_matches: int = 30):
    """Propaga ValueError (ex.: liga sem partida suficiente) — vira 422 no handler
    global, nunca um 500 genérico."""
    return run_goals_backtest(league_id, min_training_matches=min_training_matches)


def _get_or_create_historical_run(league_id: int | None) -> int:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO backtest_runs (date_from, date_to, notes)
                   VALUES (NULL, NULL, %s) RETURNING id""",
                (f"avaliação histórica com odds reais — {EVALUATION_SOURCE}, liga={league_id or 'todas'}",),
            )
            run_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    return run_id


def run_historical_odds_backtest(league_id: int | None = None) -> dict:
    evaluated = evaluate_historical_bets(league_id)
    if not evaluated:
        return {"n_bets": 0, "n_fixtures": 0, "message": "Nenhuma partida elegível — ver /summary para o motivo."}
    run_id = _get_or_create_historical_run(league_id)
    saved = persist_evaluated_bets(run_id, evaluated)
    return {"n_bets": saved, "n_fixtures": len({b.fixture_id for b in evaluated}), "backtest_run_id": run_id}


_INSUFFICIENT_DATA_MESSAGE = (
    "Nenhuma partida no banco tem odd real capturada ANTES do apito inicial e resultado "
    "final conhecido ao mesmo tempo — sem esse par, ROI/edge/opportunity score não podem "
    "ser calculados sem inventar dado. Ver /api/backtests/{league_id}/historical para o "
    "requisito exato."
)


def get_historical_odds_summary(league_id: int | None = None) -> dict:
    evaluated = evaluate_historical_bets(league_id)
    if not evaluated:
        return {
            "n_bets": 0, "insufficient_data": True, "message": _INSUFFICIENT_DATA_MESSAGE,
            "hit_rate": None, "roi": None, "by_edge": [], "by_opportunity_score": [], "by_market": [],
            "calibration": [],
        }

    results = [b.bet_result for b in evaluated]
    profits = [b.profit for b in evaluated]

    hr = metrics.hit_rate(results)
    roi = metrics.roi_and_yield(results, profits)

    edges = [b.edge for b in evaluated]
    by_edge = metrics.bucket_performance(edges, results, profits, metrics.DEFAULT_EDGE_BUCKETS)

    scores = [b.opportunity_score if b.opportunity_score is not None else -1.0 for b in evaluated]
    by_score = metrics.bucket_performance(scores, results, profits, metrics.DEFAULT_SCORE_BUCKETS)

    by_market: dict[str, dict] = {}
    for market_key in {b.market_key for b in evaluated}:
        idx = [i for i, b in enumerate(evaluated) if b.market_key == market_key]
        m_results = [results[i] for i in idx]
        m_profits = [profits[i] for i in idx]
        m_hr = metrics.hit_rate(m_results)
        m_roi = metrics.roi_and_yield(m_results, m_profits)
        by_market[market_key] = {
            "market_key": market_key, "n_bets": m_hr["n"], "hit_rate": m_hr["hit_rate"],
            "roi": m_roi["roi"], "yield_pct": m_roi["yield_pct"], "confidence": m_hr["confidence"],
        }

    calibration = metrics.calibration_table([(b.model_probability, b.bet_result == metrics.GREEN) for b in evaluated])

    return {
        "n_bets": len(evaluated), "insufficient_data": hr["n"] < metrics.MIN_SAMPLE_INSUFFICIENT,
        "message": None if hr["n"] >= metrics.MIN_SAMPLE_INSUFFICIENT else _INSUFFICIENT_DATA_MESSAGE,
        "hit_rate": hr, "roi": roi, "by_edge": by_edge, "by_opportunity_score": by_score,
        "by_market": list(by_market.values()), "calibration": calibration,
    }
