import { useCallback, useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"

import { DayGroup } from "@/components/dashboard/DayGroup"
import { EmptyState } from "@/components/shared/EmptyState"
import { ErrorState } from "@/components/shared/ErrorState"
import { LoadingState } from "@/components/shared/LoadingState"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useAsync } from "@/hooks/useAsync"
import { useLeagues } from "@/hooks/useDashboard"
import { api } from "@/services/api"
import type { MatchSummary } from "@/types/api"

function groupByDay(matches: MatchSummary[]) {
  const map = new Map<string, MatchSummary[]>()
  for (const m of matches) {
    const day = m.date.slice(0, 10)
    if (!map.has(day)) map.set(day, [])
    map.get(day)!.push(m)
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, ms]) => ({ label: new Date(date).toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "2-digit" }), date, matches: ms }))
}

export function MatchesPage() {
  const [params, setParams] = useSearchParams()
  const leagueId = params.get("league_id") ? Number(params.get("league_id")) : undefined
  const leagues = useLeagues()

  const fetcher = useCallback(() => api.matches({ league_id: leagueId }), [leagueId])
  const matches = useAsync(fetcher, [fetcher])

  const [localLeague, setLocalLeague] = useState<string>(leagueId ? String(leagueId) : "all")

  const days = useMemo(() => groupByDay(matches.data ?? []), [matches.data])

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold">Jogos</h1>
          <p className="text-sm text-muted-foreground">Todos os jogos dos próximos 14 dias, com ou sem odd disponível.</p>
        </div>
        <Select
          value={localLeague}
          onValueChange={(v) => {
            setLocalLeague(v)
            if (v === "all") setParams({})
            else setParams({ league_id: v })
          }}
        >
          <SelectTrigger className="w-48"><SelectValue placeholder="Todas as ligas" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas as ligas</SelectItem>
            {(leagues.data ?? []).map((l) => (
              <SelectItem key={l.id} value={String(l.id)}>{l.name} ({l.country})</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {matches.loading && <LoadingState label="Carregando jogos..." />}
      {matches.error && <ErrorState message={matches.error} onRetry={matches.reload} />}
      {matches.data && days.length === 0 && <EmptyState message="Nenhum jogo encontrado neste período." />}

      <div className="flex flex-col gap-6">
        {days.map((bucket) => <DayGroup key={bucket.date} bucket={bucket} />)}
      </div>
    </div>
  )
}
