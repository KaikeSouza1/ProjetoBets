const POINTS = [
  ["Você não abre cinco sites atrás de odd.", "Chega pronta, comparada entre casas."],
  ["Você não fica catando jogo no calendário.", "Só o que passou pelo filtro de valor aparece."],
  ["Você não precisa lembrar de checar nada.", "A mensagem chega, você decide."],
]

export function WhyWhatsApp() {
  return (
    <section className="border-b border-border bg-bg py-16 sm:py-24">
      <div className="mx-auto max-w-3xl px-4 sm:px-6">
        <p className="font-mono text-xs uppercase tracking-widest text-text-subtle">Por que WhatsApp</p>
        <h2 className="mt-2 text-2xl font-black tracking-tight sm:text-3xl">
          Porque é onde você já está.
        </h2>

        <div className="mt-10 flex flex-col">
          {POINTS.map(([a, b], i) => (
            <div key={a} className={`flex flex-col gap-1 py-5 sm:flex-row sm:gap-8 ${i !== POINTS.length - 1 ? "border-b border-border" : ""}`}>
              <p className="text-text sm:w-2/5">{a}</p>
              <p className="text-text-muted sm:w-3/5">{b}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
