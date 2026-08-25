const STEPS = ["JOGOS", "ANÁLISE", "ODDS", "OPORTUNIDADE", "WHATSAPP"]

export function Pipeline() {
  return (
    <section className="border-b border-border bg-bg py-16 sm:py-20">
      <div className="mx-auto max-w-5xl px-4 sm:px-6">
        <p className="font-mono text-xs uppercase tracking-widest text-text-subtle">Como isso chega até você</p>
        <h2 className="mt-2 max-w-lg text-2xl font-black tracking-tight sm:text-3xl">
          Um sistema rodando o dia inteiro, não uma pessoa procurando jogo.
        </h2>

        <div className="mt-12 flex flex-col gap-0 sm:flex-row sm:items-center sm:justify-between">
          {STEPS.map((step, i) => (
            <div key={step} className="flex items-center sm:contents">
              <div className="flex items-center gap-3 py-3 sm:flex-col sm:items-center sm:py-0 sm:text-center">
                <span className="font-mono text-xs text-text-subtle">{String(i + 1).padStart(2, "0")}</span>
                <span
                  className={`font-mono text-sm font-bold tracking-wide sm:mt-2 ${
                    i === STEPS.length - 1 ? "text-whatsapp" : "text-text"
                  }`}
                >
                  {step}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className="mx-3 h-px flex-1 bg-border-strong sm:mx-2 sm:mt-[-1.4rem] sm:w-full" />
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
