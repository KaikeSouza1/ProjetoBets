import { CheckCheck, Target } from "lucide-react"

function ProbabilityBar({ label, value, tone }: { label: string; value: number; tone: "brand" | "muted" }) {
  return (
    <div>
      <div className="flex items-center justify-between text-[11px] text-white/70">
        <span>{label}</span>
        <span className="font-bold text-white">{value}%</span>
      </div>
      <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-white/15">
        <div
          className={`h-full rounded-full ${tone === "brand" ? "bg-brand" : "bg-white/40"}`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  )
}

export function WhatsAppPreview() {
  return (
    <div className="relative mx-auto w-full max-w-sm">
      <div className="rounded-[28px] border border-border bg-[#0b141a] p-4 shadow-[0_30px_60px_-20px_rgba(15,26,20,0.45)]">
        <div className="flex items-center gap-2 border-b border-white/10 pb-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand text-brand-ink">
            <Target className="h-4 w-4" />
          </div>
          <div>
            <p className="text-sm font-bold text-white">Odds do dia</p>
            <p className="text-[11px] text-white/50">online</p>
          </div>
        </div>

        <div className="mt-4 rounded-2xl rounded-tl-sm bg-[#202c33] p-3.5">
          <p className="text-sm font-bold text-brand">Oportunidade de hoje</p>
          <p className="mt-1 text-sm text-white">Time A x Time B</p>
          <p className="text-xs text-white/60">Mais de 2.5 gols</p>

          <div className="mt-3 flex flex-col gap-2">
            <ProbabilityBar label="Modelo estima" value={61} tone="brand" />
            <ProbabilityBar label="Odd do mercado implica" value={52} tone="muted" />
          </div>

          <div className="mt-3 flex items-center justify-between rounded-lg bg-white/5 px-2.5 py-2">
            <span className="text-xs text-white/60">Odd 2.10 · Bet365</span>
            <span className="text-xs font-bold text-brand">edge +9%</span>
          </div>

          <div className="mt-2 flex items-center justify-end gap-1 text-[10px] text-white/40">
            09:14 <CheckCheck className="h-3 w-3 text-brand" />
          </div>
        </div>
      </div>
      <p className="mt-3 text-center text-[11px] text-text-subtle">Exemplo ilustrativo de como a análise chega pra você</p>
    </div>
  )
}
