import { ArrowRight } from "lucide-react"

import { PhoneMockup } from "@/components/PhoneMockup"
import { SAMPLE_MESSAGES } from "@/config"

export function Hero() {
  return (
    <section className="border-b border-border bg-bg">
      <div className="mx-auto grid max-w-5xl grid-cols-1 items-center gap-14 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-[1.1fr_0.9fr] lg:gap-8">
        <div className="flex flex-col items-center gap-6 text-center lg:items-start lg:text-left">
          <h1 className="max-w-xl text-[2.75rem] font-black leading-[1.03] tracking-tight sm:text-6xl">
            As odds certas.
            <br />
            No seu <span className="text-whatsapp">WhatsApp</span>.
          </h1>

          <p className="max-w-md text-lg text-text-muted">
            O modelo cruza mais de 30 mercados por partida e só te avisa quando a odd vale a
            pena. Sem abrir site, sem procurar jogo.
          </p>

          <a
            href="#planos"
            className="inline-flex items-center gap-2 rounded-md bg-brand px-6 py-3.5 font-mono text-sm font-bold uppercase tracking-wide text-brand-ink transition-transform hover:-translate-y-0.5"
          >
            Quero receber
            <ArrowRight className="h-4 w-4" />
          </a>
          <span className="font-mono text-xs text-text-subtle">grátis pra sempre / sem cartão</span>
        </div>

        <PhoneMockup messages={SAMPLE_MESSAGES.slice(0, 1)} />
      </div>
    </section>
  )
}
