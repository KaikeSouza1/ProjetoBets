import type { DashboardSummary } from "@/types/api"

export function SummaryStats({ summary }: { summary: DashboardSummary }) {
  const items = [
    { label: "Jogos analisados", value: summary.matches_analyzed },
    { label: "Oportunidades encontradas", value: summary.opportunities_found },
    { label: "Oportunidades fortes", value: summary.strong_opportunities },
  ]
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {items.map((item) => (
        <div key={item.label} className="rounded-md border border-border bg-card p-4">
          <p className="text-2xl font-semibold">{item.value}</p>
          <p className="text-xs text-muted-foreground">{item.label}</p>
        </div>
      ))}
    </div>
  )
}
