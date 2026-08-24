"""Schemas de partida, mercados e oportunidades — o contrato entre o motor e o frontend.
O frontend nunca vê uma linha de SQL nem um dataclass do engine, só estes modelos."""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class DataState(str, Enum):
    """Estado de disponibilidade de dado de uma partida — o frontend precisa saber
    diferenciar 'sem oportunidade boa' de 'ainda não dá pra saber'. Nunca inventa dado
    pra preencher um estado melhor; ver match_service._resolve_state para a regra exata."""
    READY = "READY"                        # modelo + odd disponíveis, nenhuma família de mercado faltando
    PARTIAL = "PARTIAL"                     # modelo + odd disponíveis, mas 1+ família de mercado sem dado (ex.: só gols)
    NO_ODDS = "NO_ODDS"                     # modelo disponível, nenhuma odd capturada ainda
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"  # liga/time sem histórico suficiente pro modelo
    STALE = "STALE"                          # a última sincronização com as fontes externas está velha demais pra confiar


class OpportunityOut(BaseModel):
    market_key: str
    label: str
    probability: float
    odd: float | None = None
    bookmaker_name: str | None = None
    implied_probability: float | None = None
    edge: float | None = None
    expected_value: float | None = None
    confidence: str
    data_quality: int
    opportunity_score: float | None = None


class MarketFamilyOut(BaseModel):
    family: str
    error: str | None = None
    lambda_home: float | None = None
    lambda_away: float | None = None
    n_matches_home_team: int | None = None
    n_matches_away_team: int | None = None
    opportunities: list[OpportunityOut] = []


class MatchSummaryOut(BaseModel):
    fd_match_id: int
    fixture_id: int | None = None
    date: datetime
    status: str
    league_id: int
    league_name: str
    league_country: str | None = None
    home_team_id: int
    home_team: str
    away_team_id: int
    away_team: str
    home_goals: int | None = None
    away_goals: int | None = None
    state: DataState
    best_opportunity: OpportunityOut | None = None


class MatchHeaderOut(BaseModel):
    fd_match_id: int
    fixture_id: int | None = None
    date: datetime
    status: str
    league_id: int
    league_name: str
    league_country: str | None = None
    referee: str | None = None
    home_team_id: int
    home_team: str
    away_team_id: int
    away_team: str
    home_goals: int | None = None
    away_goals: int | None = None
    state: DataState
    league_maturity_notice: str | None = None


class ReasonOut(BaseModel):
    text: str


class MatchAnalysisOut(BaseModel):
    state: DataState
    best_opportunity: OpportunityOut | None = None
    other_opportunities: list[OpportunityOut] = []
    reasons: list[str] = []
    empty_message: str | None = None
    stale_notice: str | None = None  # populado quando state==STALE, mesmo com best_opportunity presente


class MatchMarketsOut(BaseModel):
    state: DataState
    families: list[MarketFamilyOut] = []


class RecentResultOut(BaseModel):
    date: datetime
    opponent: str
    home_away: str
    goals_for: int
    goals_against: int
    result: str


class StandingRowOut(BaseModel):
    rank: int | None = None
    team: str
    points: int | None = None
    played: int | None = None
    win: int | None = None
    draw: int | None = None
    lose: int | None = None
    goals_for: int | None = None
    goals_against: int | None = None


class MatchFormOut(BaseModel):
    home_form: list[RecentResultOut] = []
    away_form: list[RecentResultOut] = []
    standings: list[StandingRowOut] = []


class PlayerPredictionOut(BaseModel):
    player_id: int
    name: str
    n_matches: int
    avg_minutes: float
    prob_score: float
    prob_assist: float
    prob_card: float
    confidence: str
    odd: float | None = None
    bookmaker_name: str | None = None
    implied_probability: float | None = None
    edge: float | None = None


class TeamPlayersOut(BaseModel):
    players: list[PlayerPredictionOut] = []
    error: str | None = None


class MatchPlayersOut(BaseModel):
    state: DataState
    home: TeamPlayersOut
    away: TeamPlayersOut
