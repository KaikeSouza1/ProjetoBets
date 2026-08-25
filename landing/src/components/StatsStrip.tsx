const STATS = [
  { value: "30+", label: "mercados analisados por partida" },
  { value: "4", label: "modelos estatísticos independentes" },
  { value: "multi-casa", label: "odd real comparada entre bookmakers" },
]

export function StatsStrip() {
  return (
    <section className="bg-green-deep">
      <div className="mx-auto grid max-w-5xl grid-cols-1 gap-8 px-4 py-12 sm:grid-cols-3 sm:px-6 sm:py-16">
        {STATS.map((s) => (
          <div key={s.label} className="text-center sm:border-l sm:border-white/10 sm:first:border-l-0">
            <p className="text-4xl font-black text-brand sm:text-5xl">{s.value}</p>
            <p className="mt-2 text-sm text-white/70">{s.label}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
