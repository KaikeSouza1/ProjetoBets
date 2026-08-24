import type { RecentResult } from "@/types/api"

const RESULT_STYLE: Record<RecentResult["result"], string> = {
  V: "bg-positive-bg text-positive",
  E: "bg-muted text-muted-foreground",
  D: "bg-negative-bg text-negative",
}

export function TeamForm({ teamName, form }: { teamName: string; form: RecentResult[] }) {
  return (
    <div>
      <p className="mb-2 text-sm font-semibold">{teamName}</p>
      {form.length === 0 ? (
        <p className="text-xs text-muted-foreground">Sem jogos capturados ainda para este time.</p>
      ) : (
        <div className="flex flex-col gap-1.5">
          <div className="flex gap-1">
            {form.map((m, i) => (
              <span key={i} className={`flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-bold ${RESULT_STYLE[m.result]}`}>
                {m.result}
              </span>
            ))}
          </div>
          <div className="flex flex-col gap-0.5">
            {form.slice(0, 5).map((m, i) => (
              <p key={i} className="text-xs text-muted-foreground">
                {m.goals_for}-{m.goals_against} vs {m.opponent} ({m.home_away})
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
