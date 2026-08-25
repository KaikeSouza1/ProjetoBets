import { MessageSquareText, ShieldCheck, TrendingUp, Zap } from "lucide-react"

const STEPS = [
  {
    icon: MessageSquareText,
    title: "1. Manda um oi",
    text: "Você inicia a conversa no WhatsApp — é assim que garantimos que a mensagem sempre chega, sem cair em spam.",
  },
  {
    icon: Zap,
    title: "2. Escolhe o plano",
    text: "Grátis (1 odd/dia) ou PRO (3 odds + 1 múltipla). Sem fidelidade, cancela quando quiser.",
  },
  {
    icon: TrendingUp,
    title: "3. Recebe a análise",
    text: "Toda vez que o modelo encontra valor real — probabilidade calculada vs. odd do mercado — você recebe a explicação, não só o palpite.",
  },
]

export function HowItWorks() {
  return (
    <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
      <div className="mx-auto max-w-xl text-center">
        <h2 className="text-2xl font-extrabold tracking-tight sm:text-3xl">Como funciona</h2>
        <p className="mt-2 text-text-muted">3 passos, nenhum grupo de Telegram lotado.</p>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-3">
        {STEPS.map((step) => (
          <div key={step.title} className="rounded-2xl border border-border bg-surface p-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-positive-bg">
              <step.icon className="h-5 w-5 text-positive" />
            </div>
            <h3 className="mt-4 font-bold">{step.title}</h3>
            <p className="mt-1.5 text-sm text-text-muted">{step.text}</p>
          </div>
        ))}
      </div>

      <div className="mt-8 flex items-center justify-center gap-2 text-xs text-text-subtle">
        <ShieldCheck className="h-4 w-4" />
        Modelo estatístico auditável — nunca inventa dado que não existe.
      </div>
    </section>
  )
}
