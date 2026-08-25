import { ArrowRight } from "lucide-react"

export function FinalCTA() {
  return (
    <section className="bg-bg py-16 text-center sm:py-20">
      <div className="mx-auto max-w-lg px-4 sm:px-6">
        <h2 className="text-2xl font-black tracking-tight sm:text-3xl">
          Quer receber a oportunidade direto no WhatsApp?
        </h2>
        <a
          href="#planos"
          className="mt-6 inline-flex items-center gap-2 rounded-md bg-brand px-6 py-3.5 font-mono text-sm font-bold uppercase tracking-wide text-brand-ink transition-transform hover:-translate-y-0.5"
        >
          Quero receber
          <ArrowRight className="h-4 w-4" />
        </a>
      </div>
    </section>
  )
}
