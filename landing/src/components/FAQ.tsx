const ITEMS = [
  {
    q: "Preciso pagar pra testar?",
    a: "Não. O plano grátis existe pra sempre: 1 odd por dia, sem cartão.",
  },
  {
    q: "Vocês garantem que eu vou ganhar?",
    a: "Não. É análise estatística comparando probabilidade com a odd do mercado, não garantia de resultado. Aposte com responsabilidade.",
  },
  {
    q: "Por que preciso mandar mensagem antes de receber?",
    a: "É o que evita que a conta seja marcada como spam pelo WhatsApp. Você inicia, o robô responde.",
  },
  {
    q: "De onde vem a odd?",
    a: "De mais de uma casa de apostas, capturada automaticamente e comparada. A que aparece pra você é a melhor entre elas.",
  },
  {
    q: "Posso cancelar quando quiser?",
    a: "Sim. Sem fidelidade, sem multa.",
  },
]

export function FAQ() {
  return (
    <section className="border-b border-border bg-surface py-16 sm:py-24">
      <div className="mx-auto max-w-2xl px-4 sm:px-6">
        <h2 className="text-2xl font-black tracking-tight sm:text-3xl">Perguntas</h2>
        <div className="mt-8 flex flex-col">
          {ITEMS.map((item, i) => (
            <details key={item.q} className={`group py-4 ${i !== ITEMS.length - 1 ? "border-b border-border" : ""}`}>
              <summary className="flex cursor-pointer list-none items-center justify-between font-medium text-text">
                {item.q}
                <span className="ml-4 font-mono text-text-subtle transition-transform group-open:rotate-45">+</span>
              </summary>
              <p className="mt-2 text-sm text-text-muted">{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  )
}
