import { LeagueBadge } from "@/components/shared/LeagueBadge"
import { formatDateTime } from "@/lib/utils"
import type { MatchHeader } from "@/types/api"

export function MatchHeaderCard({ header }: { header: MatchHeader }) {
  const finished = header.home_goals !== null && header.away_goals !== null
  return (
    <div className="rounded-md border border-border bg-card p-6">
      <div className="flex items-center justify-between gap-2">
        <LeagueBadge name={header.league_name} country={header.league_country} />
        <span className="text-xs text-muted-foreground">{formatDateTime(header.date)}</span>
      </div>

      <div className="mt-4 flex flex-col items-center gap-2 text-center sm:grid sm:grid-cols-3 sm:gap-2">
        <p className="text-lg font-semibold sm:truncate">{header.home_team}</p>
        <div className="text-sm text-muted-foreground">
          {finished ? (
            <span className="text-xl font-bold text-foreground">{header.home_goals} - {header.away_goals}</span>
          ) : (
            "×"
          )}
        </div>
        <p className="text-lg font-semibold sm:truncate">{header.away_team}</p>
      </div>

      <p className="mt-4 text-center text-xs text-muted-foreground">
        Árbitro: {header.referee ?? "não informado"} · Status: {header.status}
      </p>

      {header.league_maturity_notice && (
        <p className="mt-3 rounded-md bg-warning-bg px-3 py-2 text-center text-xs text-warning">
          {header.league_maturity_notice}
        </p>
      )}
    </div>
  )
}
