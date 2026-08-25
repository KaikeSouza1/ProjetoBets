import { ArrowRight, MessageCircle, TrendingUp } from "lucide-react"

import { WhatsAppPreview } from "@/components/WhatsAppPreview"

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-bg-subtle">
      <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-brand/30 blur-3xl" />
      <div className="pointer-events-none absolute -left-32 top-40 h-64 w-64 rounded-full bg-positive/15 blur-3xl" />

      <div className="relative mx-auto grid max-w-5xl grid-cols-1 items-center gap-12 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-2 lg:gap-8">
        <div className="flex flex-col items-center gap-6 text-center lg:items-start lg:text-left">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1 text-xs font-semibold text-text-muted">
            <TrendingUp className="h-3.5 w-3.5 text-positive" />
            Análise estatística, não achismo
          </span>

          <h1 className="max-w-xl text-4xl font-black leading-[1.05] tracking-tight sm:text-6xl">
            As melhores odds do dia, direto no seu <span className="text-brand-600">WhatsApp</span>
          </h1>

          <p className="max-w-lg text-lg text-text-muted">
            Modelo estatístico compara probabilidade real com a odd do mercado e só chega até
            você quando faz sentido. Sem enrolação, sem grupo lotado de spam.
          </p>

          <div className="mt-2 flex flex-col items-center gap-3 sm:flex-row">
            <a
              href="#planos"
              className="inline-flex items-center gap-2 rounded-full bg-brand px-6 py-3 text-base font-bold text-brand-ink shadow-[0_8px_24px_-8px_rgba(194,255,11,0.6)] transition-transform hover:-translate-y-0.5"
            >
              <MessageCircle className="h-5 w-5" />
              Quero receber odds grátis
              <ArrowRight className="h-4 w-4" />
            </a>
          </div>
          <span className="text-xs text-text-subtle">Plano grátis pra sempre. Sem cartão.</span>
        </div>

        <WhatsAppPreview />
      </div>
    </section>
  )
}
