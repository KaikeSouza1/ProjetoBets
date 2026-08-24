import { ArrowRight } from "lucide-react"
import { Link } from "react-router-dom"

import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge"
import { DataQualityBar } from "@/components/shared/DataQualityBadge"
import { LeagueBadge } from "@/components/shared/LeagueBadge"
import { Button } from "@/components/ui/button"
import { formatDateTime, formatOdd, formatPercent, formatSignedPercent } from "@/lib/utils"
import type { MatchSummary } from "@/types/api"

export function BestOpportunityHero({ match }: { match: MatchSummary }) {
  const opp = match.best_opportunity
  if (!opp) return null
  const positive = (opp.edge ?? 0) >= 0

  return (
    <section className="rounded-md border border-border bg-card p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Melhor oportunidade do dia
        </span>
        <LeagueBadge name={match.league_name} country={match.league_country} />
      </div>

      <div className="mt-3 flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <p className="text-lg font-semibold">
            {match.home_team} <span className="text-muted-foreground">×</span> {match.away_team}
          </p>
          <p className="text-sm text-muted-foreground">{formatDateTime(match.date)}</p>
        </div>
        <Link to={`/matches/${match.fd_match_id}`}>
          <Button variant="outline" size="sm">
            Ver análise <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </Link>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Metric label="Mercado" value={opp.label} />
        <Metric label="Probabilidade estimada" value={formatPercent(opp.probability)} />
        <Metric label="Odd" value={formatOdd(opp.odd)} sub={opp.implied_probability ? `implícita ${formatPercent(opp.implied_probability)}` : undefined} />
        <Metric
          label="Edge estimado"
          value={formatSignedPercent(opp.edge)}
          valueClassName={positive ? "text-positive" : "text-negative"}
        />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <ConfidenceBadge confidence={opp.confidence} />
        <DataQualityBar value={opp.data_quality} />
      </div>
    </section>
  )
}

function Metric({
  label, value, sub, valueClassName,
}: { label: string; value: string; sub?: string; valueClassName?: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`mt-1 text-xl font-semibold ${valueClassName ?? ""}`}>{value}</p>
      {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
    </div>
  )
}
