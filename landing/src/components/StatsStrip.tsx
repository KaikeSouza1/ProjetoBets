const STATS = [
  { value: "30+", label: "mercados analisados por partida" },
  { value: "4", label: "modelos estatísticos independentes" },
  { value: "multi-casa", label: "odd real comparada entre bookmakers" },
]

export function StatsStrip() {
  return (
    <section className="border-y border-border bg-surface">
      <div className="mx-auto grid max-w-5xl grid-cols-3 gap-4 px-4 py-8 sm:px-6">
        {STATS.map((s) => (
          <div key={s.label} className="text-center">
            <p className="text-3xl font-black text-brand-600 sm:text-4xl">{s.value}</p>
            <p className="mt-1 text-xs text-text-muted sm:text-sm">{s.label}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
