// Espelha os schemas Pydantic do backend (backend/app/api/schemas). Mantenha em sincronia manualmente —
// é o contrato entre times; se o backend mudar um schema, este arquivo muda junto.

export type DataState = "READY" | "PARTIAL" | "NO_ODDS" | "INSUFFICIENT_DATA" | "STALE"
export type Confidence = "alta" | "média" | "baixa"

export interface League {
  id: number
  name: string
  country: string | null
}

export interface Opportunity {
  market_key: string
  label: string
  probability: number
  odd: number | null
  bookmaker_name: string | null
  implied_probability: number | null
  edge: number | null
  expected_value: number | null
  confidence: Confidence
  data_quality: number
  opportunity_score: number | null
}

export interface MarketFamily {
  family: string
  error: string | null
  lambda_home: number | null
  lambda_away: number | null
  n_matches_home_team: number | null
  n_matches_away_team: number | null
  opportunities: Opportunity[]
}

export interface MatchSummary {
  fd_match_id: number
  fixture_id: number | null
  date: string
  status: string
  league_id: number
  league_name: string
  league_country: string | null
  home_team_id: number
  home_team: string
  away_team_id: number
  away_team: string
  home_goals: number | null
  away_goals: number | null
  state: DataState
  best_opportunity: Opportunity | null
}

export interface MatchHeader {
  fd_match_id: number
  fixture_id: number | null
  date: string
  status: string
  league_id: number
  league_name: string
  league_country: string | null
  referee: string | null
  home_team_id: number
  home_team: string
  away_team_id: number
  away_team: string
  home_goals: number | null
  away_goals: number | null
  state: DataState
  league_maturity_notice: string | null
}

export interface MatchAnalysis {
  state: DataState
  best_opportunity: Opportunity | null
  other_opportunities: Opportunity[]
  reasons: string[]
  empty_message: string | null
  stale_notice: string | null
}

export interface MatchMarkets {
  state: DataState
  families: MarketFamily[]
}

export interface RecentResult {
  date: string
  opponent: string
  home_away: string
  goals_for: number
  goals_against: number
  result: "V" | "E" | "D"
}

export interface StandingRow {
  rank: number | null
  team: string
  points: number | null
  played: number | null
  win: number | null
  draw: number | null
  lose: number | null
  goals_for: number | null
  goals_against: number | null
}

export interface MatchForm {
  home_form: RecentResult[]
  away_form: RecentResult[]
  standings: StandingRow[]
}

export interface PlayerPrediction {
  player_id: number
  name: string
  n_matches: number
  avg_minutes: number
  prob_score: number
  prob_assist: number
  prob_card: number
  confidence: Confidence
  odd: number | null
  bookmaker_name: string | null
  implied_probability: number | null
  edge: number | null
}

export interface TeamPlayers {
  players: PlayerPrediction[]
  error: string | null
}

export interface MatchPlayers {
  state: DataState
  home: TeamPlayers
  away: TeamPlayers
}

export interface DashboardSummary {
  matches_analyzed: number
  opportunities_found: number
  strong_opportunities: number
  last_updated: string | null
}

export interface DayBucket {
  label: string
  date: string
  matches: MatchSummary[]
}

export interface Dashboard {
  summary: DashboardSummary
  best_opportunity: MatchSummary | null
  opportunities: MatchSummary[]
  days: DayBucket[]
  empty_message: string | null
}

export type SampleConfidence = "insuficiente" | "limitada" | "representativa"

export interface BacktestMetric {
  market_key: string
  hit_rate: number | null
  brier_score: number
  n_bets: number
  confidence: SampleConfidence
  date_from: string | null
  date_to: string | null
}

export interface CalibrationSummary {
  league_id: number
  metrics: BacktestMetric[]
}

export interface HitRateStat {
  n: number
  hit_rate: number | null
  confidence: SampleConfidence
}

export interface RoiStat {
  n: number
  roi: number | null
  yield_pct: number | null
  total_profit: number | null
  confidence: SampleConfidence
}

export interface PerformanceBucket {
  bucket_low: number
  bucket_high: number
  n_bets: number
  hit_rate: number | null
  roi: number | null
  yield_pct: number | null
  confidence: SampleConfidence
}

export interface CalibrationRow {
  bucket_low: number
  bucket_high: number
  n: number
  mean_predicted: number | null
  realized_frequency: number | null
  confidence: SampleConfidence
}

export interface MarketBreakdown {
  market_key: string
  n_bets: number
  hit_rate: number | null
  roi: number | null
  yield_pct: number | null
  confidence: SampleConfidence
}

export interface HistoricalOddsSummary {
  n_bets: number
  insufficient_data: boolean
  message: string | null
  hit_rate: HitRateStat | null
  roi: RoiStat | null
  by_edge: PerformanceBucket[]
  by_opportunity_score: PerformanceBucket[]
  by_market: MarketBreakdown[]
  calibration: CalibrationRow[]
}
