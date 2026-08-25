import { ArrowRight, MessageCircle } from "lucide-react"

export function Hero() {
  return (
    <section className="bg-bg">
      <div className="mx-auto flex max-w-3xl flex-col items-center gap-6 px-4 py-20 text-center sm:px-6 sm:py-28">
        <span className="inline-block rounded-md bg-brand px-3 py-1 text-xs font-black uppercase tracking-wide text-brand-ink">
          Análise estatística, não achismo
        </span>

        <h1 className="max-w-2xl text-4xl font-black leading-[1.02] tracking-tight sm:text-6xl">
          As melhores odds do dia, direto no seu WhatsApp
        </h1>

        <p className="max-w-lg text-lg text-text-muted">
          Modelo estatístico compara probabilidade real com a odd do mercado e só chega até
          você quando faz sentido. Sem enrolação, sem grupo lotado de spam.
        </p>

        <a
          href="#planos"
          className="inline-flex items-center gap-2 rounded-md bg-green-deep px-6 py-3.5 text-base font-bold text-white transition-transform hover:-translate-y-0.5"
        >
          <MessageCircle className="h-5 w-5 text-brand" />
          Quero receber odds grátis
          <ArrowRight className="h-4 w-4" />
        </a>
        <span className="text-xs text-text-subtle">Plano grátis pra sempre. Sem cartão.</span>
      </div>
    </section>
  )
}
