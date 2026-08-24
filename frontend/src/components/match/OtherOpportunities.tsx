import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge"
import { formatOdd, formatPercent, formatSignedPercent } from "@/lib/utils"
import type { Opportunity } from "@/types/api"

export function OtherOpportunities({ opportunities }: { opportunities: Opportunity[] }) {
  if (opportunities.length === 0) return null
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold">Outras oportunidades</h3>
      <div className="flex flex-col gap-2">
        {opportunities.slice(0, 6).map((o) => (
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
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
