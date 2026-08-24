import type { RecentResult } from "@/types/api"

interface Stats {
  avgScored: number
  avgConceded: number
  bttsPct: number
  over15Pct: number
  over25Pct: number
  cleanSheetPct: number
}

function computeStats(form: RecentResult[]): Stats | null {
  if (form.length === 0) return null
  const n = form.length
  const scored = form.reduce((s, m) => s + m.goals_for, 0)
  const conceded = form.reduce((s, m) => s + m.goals_against, 0)
  const btts = form.filter((m) => m.goals_for > 0 && m.goals_against > 0).length
  const over15 = form.filter((m) => m.goals_for + m.goals_against > 1.5).length
  const over25 = form.filter((m) => m.goals_for + m.goals_against > 2.5).length
  const cleanSheets = form.filter((m) => m.goals_against === 0).length
  return {
    avgScored: scored / n,
    avgConceded: conceded / n,
    bttsPct: (btts / n) * 100,
    over15Pct: (over15 / n) * 100,
    over25Pct: (over25 / n) * 100,
    cleanSheetPct: (cleanSheets / n) * 100,
  }
}

function Row({ label, home, away, format }: { label: string; home: number; away: number; format: (v: number) => string }) {
  const total = home + away || 1
  const homePct = (home / total) * 100
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span className="font-medium text-foreground">{format(home)}</span>
        <span>{label}</span>
        <span className="font-medium text-foreground">{format(away)}</span>
      </div>
      <div className="flex h-1.5 overflow-hidden rounded-full bg-muted">
        <div className="h-full bg-foreground/70" style={{ width: `${homePct}%` }} />
        <div className="h-full bg-foreground/25" style={{ width: `${100 - homePct}%` }} />
      </div>
    </div>
  )
}

export function StatComparison({
  homeName, awayName, homeForm, awayForm,
}: { homeName: string; awayName: string; homeForm: RecentResult[]; awayForm: RecentResult[] }) {
  const home = computeStats(homeForm)
  const away = computeStats(awayForm)
  if (!home || !away) return null

  return (
    <div className="rounded-md border border-border bg-card p-4">
      <p className="mb-3 text-xs text-muted-foreground">
        Baseado nos últimos {homeForm.length} jogos de {homeName} e {awayForm.length} de {awayName}
      </p>
      <div className="flex flex-col gap-3">
        <Row label="Gols marcados (média)" home={home.avgScored} away={away.avgScored} format={(v) => v.toFixed(1)} />
        <Row label="Gols sofridos (média)" home={home.avgConceded} away={away.avgConceded} format={(v) => v.toFixed(1)} />
        <Row label="Ambas marcam" home={home.bttsPct} away={away.bttsPct} format={(v) => `${v.toFixed(0)}%`} />
        <Row label="Mais de 1.5 gols" home={home.over15Pct} away={away.over15Pct} format={(v) => `${v.toFixed(0)}%`} />
        <Row label="Mais de 2.5 gols" home={home.over25Pct} away={away.over25Pct} format={(v) => `${v.toFixed(0)}%`} />
        <Row label="Jogos sem sofrer gol" home={home.cleanSheetPct} away={away.cleanSheetPct} format={(v) => `${v.toFixed(0)}%`} />
      </div>
    </div>
  )
}
