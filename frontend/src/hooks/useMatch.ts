import { useCallback } from "react"

import { api, type SortBy } from "@/services/api"

import { useAsync } from "./useAsync"

export function useMatchHeader(id: number) {
  return useAsync(useCallback(() => api.match(id), [id]), [id])
}

export function useMatchAnalysis(id: number, sortBy: SortBy = "valor") {
  return useAsync(useCallback(() => api.matchAnalysis(id, sortBy), [id, sortBy]), [id, sortBy])
}

export function useMatchMarkets(id: number) {
  return useAsync(useCallback(() => api.matchMarkets(id), [id]), [id])
}

export function useMatchForm(id: number) {
  return useAsync(useCallback(() => api.matchForm(id), [id]), [id])
}

export function useMatchPlayers(id: number) {
  return useAsync(useCallback(() => api.matchPlayers(id), [id]), [id])
}
