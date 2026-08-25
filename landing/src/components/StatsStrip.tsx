const STATS = [
  { value: "30+", label: "mercados por partida" },
  { value: "4", label: "modelos estatísticos independentes" },
  { value: "2+", label: "casas de apostas comparadas" },
]

export function StatsStrip() {
  return (
    <section className="border-b border-border bg-bg py-14">
      <div className="mx-auto max-w-5xl px-4 sm:px-6">
        <p className="font-mono text-xs uppercase tracking-widest text-text-subtle">O que roda por trás</p>
        <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-3">
          {STATS.map((s) => (
            <div key={s.label} className="border-t border-border-strong pt-4">
              <p className="font-mono text-3xl font-bold text-brand">{s.value}</p>
              <p className="mt-1 text-sm text-text-muted">{s.label}</p>
            </div>
          ))}
        </div>
        <p className="mt-6 max-w-md text-xs text-text-subtle">
          Ainda não temos histórico público de resultado: o produto é novo. Não prometemos taxa
          de acerto que não medimos.
        </p>
      </div>
    </section>
  )
}
