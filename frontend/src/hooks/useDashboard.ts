import { useCallback } from "react"

import { api, type DashboardFilters } from "@/services/api"

import { useAsync } from "./useAsync"

export function useDashboard(filters: DashboardFilters) {
  const fetcher = useCallback(() => api.dashboard(filters), [
    filters.days_ahead, filters.league_id, filters.min_edge, filters.min_confidence,
  ])
  return useAsync(fetcher, [fetcher])
}

export function useLeagues() {
  return useAsync(api.leagues, [])
}
