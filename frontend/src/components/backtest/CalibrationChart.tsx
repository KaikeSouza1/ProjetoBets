import {
  Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts"

import type { CalibrationRow } from "@/types/api"

function bucketLabel(row: CalibrationRow): string {
  return `${Math.round(row.bucket_low * 100)}–${Math.round(row.bucket_high * 100)}%`
}

export function CalibrationChart({ rows }: { rows: CalibrationRow[] }) {
  const data = rows
    .filter((r) => r.n > 0)
    .map((r) => ({
      bucket: bucketLabel(r),
      previsto: r.mean_predicted !== null ? Math.round(r.mean_predicted * 1000) / 10 : null,
      realizado: r.realized_frequency !== null ? Math.round(r.realized_frequency * 1000) / 10 : null,
      n: r.n,
      confidence: r.confidence,
    }))

  if (data.length === 0) {
    return <p className="text-sm text-muted-foreground">Sem dados suficientes para o gráfico de calibração ainda.</p>
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="bucket" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={{ stroke: "var(--border)" }} tickLine={false} />
          <YAxis
            unit="%" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false}
            width={40}
          />
          <Tooltip
            contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
            formatter={(value, name) => [`${value}%`, name]}
            labelFormatter={(label, items) => `${label} (n=${items?.[0]?.payload?.n ?? "?"})`}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="previsto" name="Probabilidade prevista" fill="var(--muted-foreground)" radius={[3, 3, 0, 0]} maxBarSize={28} />
          <Bar dataKey="realizado" name="Frequência real" fill="var(--accent)" radius={[3, 3, 0, 0]} maxBarSize={28} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
