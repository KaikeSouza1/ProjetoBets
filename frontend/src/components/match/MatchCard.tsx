import { Link } from "react-router-dom"

import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge"
import { LeagueBadge } from "@/components/shared/LeagueBadge"
import { formatOdd, formatPercent, formatSignedPercent, formatTime } from "@/lib/utils"
import type { DataState, MatchSummary } from "@/types/api"

const NO_OPPORTUNITY_TEXT: Record<DataState, string> = {
  READY: "Nenhuma oportunidade com valor suficiente.",
  PARTIAL: "Nenhuma oportunidade com valor suficiente.",
  NO_ODDS: "Modelo disponível — odds ainda não coletadas.",
  INSUFFICIENT_DATA: "Dados insuficientes para estimar.",
  STALE: "Dados desatualizados — aguardando nova sincronização.",
}

function EdgeTag({ edge }: { edge: number | null }) {
  if (edge === null) return <span className="text-xs text-muted-foreground">sem odd ainda</span>
  const positive = edge >= 0
  return (
    <span className={`text-xs font-semibold ${positive ? "text-positive" : "text-negative"}`}>
      {formatSignedPercent(edge)}
    </span>
  )
}

export function MatchCard({ match }: { match: MatchSummary }) {
  const opp = match.best_opportunity
  return (
    <Link
      to={`/matches/${match.fd_match_id}`}
      className="flex flex-col gap-2 rounded-md border border-border bg-card p-3 transition-colors hover:border-foreground/30"
    >
      <div className="flex items-center justify-between gap-2">
        <LeagueBadge name={match.league_name} country={match.league_country} />
        <span className="text-xs text-muted-foreground">{formatTime(match.date)}</span>
      </div>

      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium">
          {match.home_team} <span className="text-muted-foreground">×</span> {match.away_team}
        </p>
      </div>

      {opp ? (
        <div className="flex items-center justify-between gap-2 border-t border-border pt-2">
          <div className="min-w-0">
            <p className="truncate text-xs font-medium">{opp.label}</p>
            <p className="text-xs text-muted-foreground">
              {formatPercent(opp.probability)} · odd {formatOdd(opp.odd)}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <EdgeTag edge={opp.edge} />
            <ConfidenceBadge confidence={opp.confidence} />
          </div>
        </div>
      ) : (
        <p className="border-t border-border pt-2 text-xs text-muted-foreground">
          {NO_OPPORTUNITY_TEXT[match.state]}
        </p>
      )}
    </Link>
  )
}
