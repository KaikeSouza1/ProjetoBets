import { SampleConfidenceTag } from "@/components/backtest/SampleConfidenceTag"
import { formatPercent, formatSignedPercent } from "@/lib/utils"
import type { PerformanceBucket } from "@/types/api"

export function BucketTable({ title, buckets, isPercent }: { title: string; buckets: PerformanceBucket[]; isPercent: boolean }) {
  const format = (low: number, high: number) =>
    isPercent ? `${Math.round(low * 100)}–${high >= 900 ? "+" : Math.round(high * 100)}%` : `${Math.round(low * 100)}–${high >= 100 ? "100" : Math.round(high * 100)}`

  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold">{title}</h3>
      <div className="overflow-x-auto rounded-md border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-3 py-2 text-left">Faixa</th>
              <th className="px-3 py-2 text-left">Apostas</th>
              <th className="px-3 py-2 text-left">Hit rate</th>
              <th className="px-3 py-2 text-left">ROI</th>
              <th className="px-3 py-2 text-left">Amostra</th>
            </tr>
          </thead>
          <tbody>
            {buckets.map((b) => (
              <tr key={`${b.bucket_low}-${b.bucket_high}`} className="border-t border-border">
                <td className="px-3 py-2 font-mono text-xs">{format(b.bucket_low, b.bucket_high)}</td>
                <td className="px-3 py-2">{b.n_bets}</td>
                <td className="px-3 py-2">{b.hit_rate !== null ? formatPercent(b.hit_rate) : "—"}</td>
                <td className="px-3 py-2">
                  {b.roi !== null ? (
                    <span className={b.roi >= 0 ? "text-positive" : "text-negative"}>{formatSignedPercent(b.roi)}</span>
                  ) : "—"}
                </td>
                <td className="px-3 py-2"><SampleConfidenceTag confidence={b.confidence} n={b.n_bets} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
