from fastapi import APIRouter

from app.api.schemas.backtest import (
    BacktestRunOut, CalibrationRowOut, CalibrationSummaryOut, HistoricalOddsSummaryOut, RunHistoricalBacktestOut,
)
from app.engine.backtest import metrics
from app.services import backtest_service

router = APIRouter(prefix="/api/backtests", tags=["backtests"])


@router.get("", response_model=CalibrationSummaryOut)
def get_calibration(league_id: int):
    """Calibração (Brier score, taxa de acerto) do modelo de gols via walk-forward —
    SEM odd, então SEM ROI. Ver GET /historical pro que precisa de odd real."""
    summary = backtest_service.get_calibration_summary(league_id)
    return summary


@router.post("/run", response_model=BacktestRunOut)
def run_calibration(league_id: int):
    """Roda a validação walk-forward (ValueError -> 422 quando a liga não tem partidas
    suficientes ainda, tratado pelo handler global em main.py)."""
    summary = backtest_service.run_calibration_backtest(league_id)
    return BacktestRunOut(
        backtest_run_id=summary.backtest_run_id,
        n_matches_evaluated=summary.n_matches_evaluated,
        metrics=[
            {
                "market_key": k, "hit_rate": v["hit_rate"], "brier_score": v["brier_score"],
                "n_bets": v["n_bets"], "confidence": metrics.sample_confidence_label(v["n_bets"]),
            }
            for k, v in summary.metrics.items()
        ],
    )


@router.get("/calibration-curve", response_model=list[CalibrationRowOut])
def get_calibration_curve(league_id: int, market_key: str = "home_win"):
    """Probabilidade prevista vs frequência real, por faixa — dado genuíno da última
    rodada de walk-forward desta liga (POST /run precisa ter rodado ao menos 1 vez)."""
    return backtest_service.get_calibration_curve(league_id, market_key)


@router.get("/historical", response_model=HistoricalOddsSummaryOut)
def get_historical_odds_summary(league_id: int | None = None):
    """Avaliação com odds REAIS pré-jogo — ROI, hit rate, buckets de edge/opportunity
    score, calibração. `insufficient_data=True` quando não há amostra suficiente; a
    causa mais provável hoje é zero partidas com odd capturada antes do apito inicial
    E resultado conhecido ao mesmo tempo (ver historical_eval.py)."""
    return backtest_service.get_historical_odds_summary(league_id)


@router.post("/historical/run", response_model=RunHistoricalBacktestOut)
def run_historical_odds_backtest(league_id: int | None = None):
    """Reavalia e persiste (append) as apostas históricas elegíveis em `backtest_bets`.
    Idempotente na leitura (GET /historical não depende de já ter rodado isto)."""
    return backtest_service.run_historical_odds_backtest(league_id)
