import { useCallback } from "react"

import { api } from "@/services/api"

import { useAsync } from "./useAsync"

export function useMatchHeader(id: number) {
  return useAsync(useCallback(() => api.match(id), [id]), [id])
}

export function useMatchAnalysis(id: number) {
  return useAsync(useCallback(() => api.matchAnalysis(id), [id]), [id])
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
