import { CircleCheck, Plus } from "lucide-react"

import { Button } from "@/components/ui/button"
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge"
import { DataQualityBar } from "@/components/shared/DataQualityBadge"
import { EmptyState } from "@/components/shared/EmptyState"
import { useBetSlip } from "@/context/BetSlipContext"
import { formatOdd, formatPercent, formatSignedPercent } from "@/lib/utils"
import type { MatchAnalysis } from "@/types/api"

// STALE vem de analysis.stale_notice (texto vindo do backend, com o limiar configurável
// embutido) — nunca hardcoded aqui, pra não descombinar se DATA_STALE_THRESHOLD_HOURS mudar.
const PARTIAL_NOTE = "Modelo disponível, mas 1 ou mais mercados desta partida ainda não têm dado suficiente."

interface MatchContext {
  fdMatchId: number
  homeTeam: string
  awayTeam: string
}

export function BestOpportunityPanel({ analysis, match }: { analysis: MatchAnalysis; match: MatchContext }) {
  const { add, has } = useBetSlip()
  const opp = analysis.best_opportunity
  const note = analysis.state === "STALE" ? analysis.stale_notice : analysis.state === "PARTIAL" ? PARTIAL_NOTE : null
  if (!opp) {
    return <EmptyState message={analysis.empty_message ?? "Dados insuficientes para uma estimativa."} />
  }
  const positive = (opp.edge ?? 0) >= 0
  const hasOdd = opp.odd !== null
  const slipId = `${match.fdMatchId}:${opp.market_key}`

  return (
    <div className="rounded-md border border-accent/40 bg-card p-6">
      <div className="flex items-start justify-between gap-3">
        <span className="text-xs font-semibold uppercase tracking-wide text-accent">
          {hasOdd ? "Melhor oportunidade desta partida" : "Estimativa do modelo (sem odd pra comparar ainda)"}
        </span>
        {hasOdd && (
          <Button
            size="sm"
            variant={has(slipId) ? "secondary" : "outline"}
            disabled={has(slipId)}
            onClick={() =>
              add({ id: slipId, fdMatchId: match.fdMatchId, homeTeam: match.homeTeam, awayTeam: match.awayTeam, marketLabel: opp.label, odd: opp.odd! })
            }
          >
            <Plus className="h-3.5 w-3.5" />
            {has(slipId) ? "No carrinho" : "Adicionar"}
          </Button>
        )}
      </div>
      <h2 className="mt-1 text-xl font-semibold">
        {opp.label} — {formatPercent(opp.probability)} de probabilidade estimada
      </h2>
      {note && <p className="mt-1 text-xs text-warning">{note}</p>}

      {hasOdd && (
        <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Metric label="Odd" value={formatOdd(opp.odd)} sub={opp.bookmaker_name ?? undefined} />
          <Metric label="Probabilidade implícita" value={formatPercent(opp.implied_probability)} />
          <Metric label="Edge estimado" value={formatSignedPercent(opp.edge)} valueClassName={positive ? "text-positive" : "text-negative"} />
          <Metric label="Opportunity score" value={opp.opportunity_score?.toFixed(3) ?? "—"} />
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <ConfidenceBadge confidence={opp.confidence} />
        <DataQualityBar value={opp.data_quality} />
      </div>

      {analysis.reasons.length > 0 && (
        <div className="mt-5 border-t border-border pt-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Por que o modelo gosta</p>
          <ul className="flex flex-col gap-1.5">
            {analysis.reasons.map((reason, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <CircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
                {reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function Metric({ label, value, sub, valueClassName }: { label: string; value: string; sub?: string; valueClassName?: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`mt-1 text-lg font-semibold ${valueClassName ?? ""}`}>{value}</p>
      {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
    </div>
  )
}
