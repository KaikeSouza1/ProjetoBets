const TRAITS = [
  "acompanha futebol quase todo dia",
  "já procura odd manualmente antes de apostar",
  "perde jogo bom porque não dá pra acompanhar tudo",
  "prefere decidir com dado, não com achismo",
  "quer a informação organizada, sem precisar caçar",
]

export function ForWho() {
  return (
    <section className="border-b border-border bg-surface py-16 sm:py-24">
      <div className="mx-auto max-w-2xl px-4 text-center sm:px-6">
        <h2 className="text-2xl font-black tracking-tight sm:text-3xl">
          Provavelmente faz sentido pra você se
        </h2>
        <ul className="mx-auto mt-8 flex max-w-md flex-col gap-3 text-left">
          {TRAITS.map((t) => (
            <li key={t} className="flex items-start gap-3 text-text-muted">
              <span className="mt-1 font-mono text-xs text-brand">›</span>
              <span>{t}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
