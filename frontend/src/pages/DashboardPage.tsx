import { useState } from "react"

import { BestOpportunityHero } from "@/components/dashboard/BestOpportunityHero"
import { DashboardFilters, type Filters } from "@/components/dashboard/DashboardFilters"
import { DayGroup } from "@/components/dashboard/DayGroup"
import { SummaryStats } from "@/components/dashboard/SummaryStats"
import { EmptyState } from "@/components/shared/EmptyState"
import { ErrorState } from "@/components/shared/ErrorState"
import { LoadingState } from "@/components/shared/LoadingState"
import { useDashboard, useLeagues } from "@/hooks/useDashboard"

export function DashboardPage() {
  const [filters, setFilters] = useState<Filters>({ leagueId: undefined, minConfidence: undefined, minEdge: undefined })
  const leagues = useLeagues()
  const dashboard = useDashboard({
    days_ahead: 14,
    league_id: filters.leagueId,
    min_confidence: filters.minConfidence,
    min_edge: filters.minEdge,
  })

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold">Visão geral</h1>
          <p className="text-sm text-muted-foreground">
            Estimativas de modelo comparadas à odd de mercado — nenhuma probabilidade aqui é certeza.
          </p>
        </div>
        <DashboardFilters leagues={leagues.data ?? []} filters={filters} onChange={setFilters} />
      </div>

      {dashboard.loading && <LoadingState label="Analisando os próximos jogos..." />}
      {dashboard.error && <ErrorState message={dashboard.error} onRetry={dashboard.reload} />}

      {dashboard.data && (
        <>
          <SummaryStats summary={dashboard.data.summary} />

          {dashboard.data.best_opportunity ? (
            <BestOpportunityHero match={dashboard.data.best_opportunity} />
          ) : (
            <EmptyState message={dashboard.data.empty_message ?? "Nenhuma oportunidade de valor encontrada agora."} />
          )}

          <div className="flex flex-col gap-6">
            {dashboard.data.days.map((bucket) => (
              <DayGroup key={bucket.date} bucket={bucket} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
