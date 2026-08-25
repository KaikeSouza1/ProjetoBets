import { ArrowRight, MessageCircle } from "lucide-react"

import { WhatsAppPreview } from "@/components/WhatsAppPreview"

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-bg">
      <div className="relative mx-auto grid max-w-5xl grid-cols-1 items-center gap-12 px-4 py-16 sm:px-6 sm:py-20 lg:grid-cols-2 lg:gap-4">
        <div className="flex flex-col items-center gap-6 text-center lg:items-start lg:text-left">
          <span className="inline-block rounded-md bg-brand px-3 py-1 text-xs font-black uppercase tracking-wide text-brand-ink">
            Análise estatística, não achismo
          </span>

          <h1 className="max-w-xl text-4xl font-black leading-[1.02] tracking-tight sm:text-6xl">
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

        <div className="relative flex justify-center lg:justify-end">
          <div className="absolute -inset-6 -z-10 rotate-3 rounded-[36px] bg-brand lg:-inset-8" />
          <WhatsAppPreview />
        </div>
      </div>
    </section>
  )
}
