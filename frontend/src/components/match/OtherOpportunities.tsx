import { Plus } from "lucide-react"

import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge"
import { useBetSlip } from "@/context/BetSlipContext"
import { formatOdd, formatPercent, formatSignedPercent } from "@/lib/utils"
import type { Opportunity } from "@/types/api"

interface MatchContext {
  fdMatchId: number
  homeTeam: string
  awayTeam: string
}

export function OtherOpportunities({ opportunities, match }: { opportunities: Opportunity[]; match: MatchContext }) {
  const { add, has } = useBetSlip()
  if (opportunities.length === 0) return null

  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold">Outras oportunidades</h3>
      <div className="flex flex-col gap-2">
        {opportunities.slice(0, 6).map((o) => {
          const id = `${match.fdMatchId}:${o.market_key}`
          return (
            <div key={o.market_key} className="flex items-center justify-between gap-3 rounded-md border border-border bg-card px-3 py-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{o.label}</p>
                <p className="text-xs text-muted-foreground">{formatPercent(o.probability)} · odd {formatOdd(o.odd)}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs font-semibold ${(o.edge ?? 0) >= 0 ? "text-positive" : "text-negative"}`}>
                  {formatSignedPercent(o.edge)}
                </span>
                <ConfidenceBadge confidence={o.confidence} />
                {o.odd !== null && (
                  <button
                    onClick={() =>
                      add({ id, fdMatchId: match.fdMatchId, homeTeam: match.homeTeam, awayTeam: match.awayTeam, marketLabel: o.label, odd: o.odd! })
                    }
                    disabled={has(id)}
                    aria-label="Adicionar ao carrinho"
                    className="flex h-6 w-6 items-center justify-center rounded-full border border-border text-muted-foreground hover:border-accent hover:text-accent disabled:opacity-40"
                  >
                    <Plus className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
