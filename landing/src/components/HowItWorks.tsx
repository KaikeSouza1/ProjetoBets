const STEPS = [
  {
    n: "01",
    title: "Manda um oi",
    text: "Você inicia a conversa no WhatsApp. É assim que garantimos que a mensagem sempre chega, sem cair em spam.",
  },
  {
    n: "02",
    title: "Escolhe o plano",
    text: "Grátis (1 odd/dia) ou PRO (3 odds + 1 múltipla). Sem fidelidade, cancela quando quiser.",
  },
  {
    n: "03",
    title: "Recebe a análise",
    text: "Toda vez que o modelo encontra valor real (probabilidade calculada vs. odd do mercado), você recebe a explicação, não só o palpite.",
  },
]

export function HowItWorks() {
  return (
    <section className="border-b border-border bg-surface py-16 sm:py-24">
      <div className="mx-auto max-w-5xl px-4 sm:px-6">
        <p className="font-mono text-xs uppercase tracking-widest text-text-subtle">Como entrar</p>
        <h2 className="mt-2 text-2xl font-black tracking-tight sm:text-3xl">3 passos, sem grupo lotado</h2>

        <div className="mt-10 flex flex-col">
          {STEPS.map((step, i) => (
            <div key={step.n} className={`flex gap-6 py-6 sm:gap-10 ${i !== STEPS.length - 1 ? "border-b border-border" : ""}`}>
              <span className="font-mono text-4xl font-bold text-brand sm:text-5xl">{step.n}</span>
              <div>
                <h3 className="text-lg font-bold sm:text-xl">{step.title}</h3>
                <p className="mt-1.5 max-w-xl text-text-muted">{step.text}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
