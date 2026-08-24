from datetime import date

from pydantic import BaseModel


class BacktestMetricOut(BaseModel):
    market_key: str
    hit_rate: float | None = None  # None pro 1x2_multiclass_brier — não é uma pergunta binária
    brier_score: float
    n_bets: int
    confidence: str  # insuficiente | limitada | representativa — ver engine.backtest.metrics
    date_from: date | None = None
    date_to: date | None = None


class CalibrationSummaryOut(BaseModel):
    league_id: int
    metrics: list[BacktestMetricOut]


class BacktestRunOut(BaseModel):
    backtest_run_id: int
    n_matches_evaluated: int
    metrics: list[BacktestMetricOut]


class HitRateOut(BaseModel):
    n: int
    hit_rate: float | None = None
    confidence: str


class RoiOut(BaseModel):
    n: int
    roi: float | None = None
    yield_pct: float | None = None
    total_profit: float | None = None
    confidence: str


class BucketOut(BaseModel):
    bucket_low: float
    bucket_high: float
    n_bets: int
    hit_rate: float | None = None
    roi: float | None = None
    yield_pct: float | None = None
    confidence: str


class CalibrationRowOut(BaseModel):
    bucket_low: float
    bucket_high: float
    n: int
    mean_predicted: float | None = None
    realized_frequency: float | None = None
    confidence: str


class MarketBreakdownOut(BaseModel):
    market_key: str
    n_bets: int
    hit_rate: float | None = None
    roi: float | None = None
    yield_pct: float | None = None
    confidence: str


class HistoricalOddsSummaryOut(BaseModel):
    """Avaliação com odds reais pré-jogo — NUNCA confundir com CalibrationSummaryOut.
    `insufficient_data=True` significa exatamente isso: poucas ou nenhuma partida
    elegível ainda, não que a estratégia performou mal."""
    n_bets: int
    insufficient_data: bool
    message: str | None = None
    hit_rate: HitRateOut | None = None
    roi: RoiOut | None = None
    by_edge: list[BucketOut] = []
    by_opportunity_score: list[BucketOut] = []
    by_market: list[MarketBreakdownOut] = []
    calibration: list[CalibrationRowOut] = []


class RunHistoricalBacktestOut(BaseModel):
    n_bets: int
    n_fixtures: int
    backtest_run_id: int | None = None
    message: str | None = None
