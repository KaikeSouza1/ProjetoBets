import { MatchCard } from "@/components/match/MatchCard"
import type { DayBucket } from "@/types/api"

export function DayGroup({ bucket }: { bucket: DayBucket }) {
  return (
    <section>
      <h3 className="mb-2 border-b border-border pb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {bucket.label}
      </h3>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {bucket.matches.map((m) => (
          <MatchCard key={m.fd_match_id} match={m} />
        ))}
      </div>
    </section>
  )
}
