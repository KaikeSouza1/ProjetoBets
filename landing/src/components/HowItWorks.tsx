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
    <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6 sm:py-24">
      <h2 className="text-3xl font-black tracking-tight sm:text-4xl">Como funciona</h2>

      <div className="mt-10 flex flex-col">
        {STEPS.map((step, i) => (
          <div key={step.n} className={`flex gap-6 py-6 sm:gap-10 ${i !== STEPS.length - 1 ? "border-b border-border" : ""}`}>
            <span className="text-4xl font-black text-brand-600 sm:text-5xl">{step.n}</span>
            <div>
              <h3 className="text-lg font-bold sm:text-xl">{step.title}</h3>
              <p className="mt-1.5 max-w-xl text-text-muted">{step.text}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
