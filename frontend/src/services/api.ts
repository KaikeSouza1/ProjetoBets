import type {
  BacktestMetric, CalibrationRow, CalibrationSummary, Dashboard, HistoricalOddsSummary, League,
  MatchAnalysis, MatchForm, MatchHeader, MatchMarkets, MatchPlayers, MatchSummary,
} from "@/types/api"

const BASE = import.meta.env.VITE_API_BASE_URL ?? "/api"

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(
  path: string,
  params?: Record<string, string | number | undefined>,
  method: "GET" | "POST" = "GET",
): Promise<T> {
  const url = new URL(BASE + path, window.location.origin)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value))
    }
  }
  const res = await fetch(url.toString(), { method })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, body.detail ?? res.statusText)
  }
  return res.json()
}

export interface DashboardFilters {
  days_ahead?: number
  league_id?: number
  min_edge?: number
  min_confidence?: string
}

export const api = {
  health: () => request<{ status: string; database: boolean }>("/health"),
  leagues: () => request<League[]>("/leagues"),
  dashboard: (filters: DashboardFilters = {}) => request<Dashboard>("/dashboard", { ...filters }),
  matches: (params: { from?: string; to?: string; league_id?: number } = {}) =>
    request<MatchSummary[]>("/matches", params),
  match: (id: number) => request<MatchHeader>(`/matches/${id}`),
  matchAnalysis: (id: number) => request<MatchAnalysis>(`/matches/${id}/analysis`),
  matchMarkets: (id: number) => request<MatchMarkets>(`/matches/${id}/markets`),
  matchForm: (id: number) => request<MatchForm>(`/matches/${id}/form`),
  matchPlayers: (id: number) => request<MatchPlayers>(`/matches/${id}/players`),
  calibration: (leagueId: number) => request<CalibrationSummary>("/backtests", { league_id: leagueId }),
  calibrationCurve: (leagueId: number, marketKey: string) =>
    request<CalibrationRow[]>("/backtests/calibration-curve", { league_id: leagueId, market_key: marketKey }),
  runCalibrationBacktest: (leagueId: number) =>
    request<{ backtest_run_id: number; n_matches_evaluated: number; metrics: BacktestMetric[] }>(
      "/backtests/run", { league_id: leagueId }, "POST",
    ),
  historicalOddsSummary: (leagueId?: number) =>
    request<HistoricalOddsSummary>("/backtests/historical", { league_id: leagueId }),
  runHistoricalOddsBacktest: (leagueId?: number) =>
    request<{ n_bets: number; n_fixtures: number; backtest_run_id: number | null; message: string | null }>(
      "/backtests/historical/run", { league_id: leagueId }, "POST",
    ),
}
