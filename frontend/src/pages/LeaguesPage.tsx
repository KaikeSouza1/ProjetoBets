import { Link } from "react-router-dom"

import { ErrorState } from "@/components/shared/ErrorState"
import { LoadingState } from "@/components/shared/LoadingState"
import { useLeagues } from "@/hooks/useDashboard"

export function LeaguesPage() {
  const leagues = useLeagues()

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Competições</h1>
        <p className="text-sm text-muted-foreground">Ligas acompanhadas pelo motor de análise.</p>
      </div>

      {leagues.loading && <LoadingState label="Carregando competições..." />}
      {leagues.error && <ErrorState message={leagues.error} onRetry={leagues.reload} />}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {(leagues.data ?? []).map((l) => (
          <Link
            key={l.id}
            to={`/matches?league_id=${l.id}`}
            className="rounded-md border border-border bg-card p-4 transition-colors hover:border-foreground/30"
          >
            <p className="text-sm font-semibold">{l.name}</p>
            <p className="text-xs text-muted-foreground">{l.country}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
