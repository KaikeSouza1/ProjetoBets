import { ChevronDown } from "lucide-react"
import { useState } from "react"

import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge"
import { EmptyState } from "@/components/shared/EmptyState"
import { formatOdd, formatPercent, formatSignedPercent } from "@/lib/utils"
import type { MarketFamily } from "@/types/api"

const FAMILY_LABEL: Record<string, string> = { gols: "Gols", escanteios: "Escanteios", cartões: "Cartões" }
const FRIENDLY_NO_DATA: Record<string, string> = {
  gols: "Ainda não há histórico suficiente dessa liga/times para estimar gols.",
  escanteios: "Ainda não capturamos estatística de escanteio pra essa liga.",
  cartões: "Ainda não capturamos estatística de cartão pra essa liga.",
}

function FamilySection({ family }: { family: MarketFamily }) {
  const [open, setOpen] = useState(true)

  if (family.error) {
    return (
      <div>
        <h3 className="mb-2 text-sm font-semibold">{FAMILY_LABEL[family.family] ?? family.family}</h3>
        <EmptyState message={FRIENDLY_NO_DATA[family.family] ?? "Dados insuficientes ainda."} />
      </div>
    )
  }

  return (
    <div>
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center justify-between gap-2 text-left">
        <div>
          <h3 className="text-sm font-semibold">{FAMILY_LABEL[family.family] ?? family.family}</h3>
          <p className="text-xs text-muted-foreground">
            λ esperado — casa: {family.lambda_home?.toFixed(2)} · fora: {family.lambda_away?.toFixed(2)} · amostra: {family.n_matches_home_team}/{family.n_matches_away_team}
          </p>
        </div>
        <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="mt-2 overflow-x-auto rounded-md border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-3 py-2 text-left">Mercado</th>
                <th className="px-3 py-2 text-left">Prob.</th>
                <th className="px-3 py-2 text-left">Odd</th>
                <th className="px-3 py-2 text-left">Implícita</th>
                <th className="px-3 py-2 text-left">Edge</th>
                <th className="px-3 py-2 text-left">Confiança</th>
              </tr>
            </thead>
            <tbody>
              {family.opportunities.map((o) => (
                <tr key={o.market_key} className="border-t border-border">
                  <td className="px-3 py-2">{o.label}</td>
                  <td className="px-3 py-2">{formatPercent(o.probability)}</td>
                  <td className="px-3 py-2">{formatOdd(o.odd)}</td>
                  <td className="px-3 py-2">{formatPercent(o.implied_probability)}</td>
                  <td className="px-3 py-2">
                    {o.edge === null ? (
                      <span className="text-muted-foreground">—</span>
                    ) : (
                      <span className={o.edge >= 0 ? "text-positive" : "text-negative"}>{formatSignedPercent(o.edge)}</span>
                    )}
                  </td>
                  <td className="px-3 py-2"><ConfidenceBadge confidence={o.confidence} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export function MarketsPanel({ families }: { families: MarketFamily[] }) {
  return (
    <div className="flex flex-col gap-6">
      {families.map((f) => <FamilySection key={f.family} family={f} />)}
    </div>
  )
}
