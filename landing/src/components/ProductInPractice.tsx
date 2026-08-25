import { PhoneMockup } from "@/components/PhoneMockup"
import { SAMPLE_MESSAGES } from "@/config"

export function ProductInPractice() {
  return (
    <section className="border-b border-border bg-surface py-16 sm:py-24">
      <div className="mx-auto grid max-w-5xl grid-cols-1 items-center gap-14 px-4 sm:px-6 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16">
        <PhoneMockup messages={SAMPLE_MESSAGES} />

        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-text-subtle">Produto na prática</p>
          <h2 className="mt-2 text-2xl font-black tracking-tight sm:text-3xl">
            Jogo, mercado, odd e o motivo. Nunca só o palpite.
          </h2>
          <p className="mt-4 max-w-md text-text-muted">
            Cada mensagem traz o mercado analisado, a odd capturada e o nível de confiança do
            modelo, que cresce com o tamanho da amostra de dados daquele time e liga.
          </p>
          <p className="mt-4 max-w-md text-sm text-text-subtle">
            Exemplo ilustrativo de como a mensagem chega. Não é resultado real nem promessa de
            acerto.
          </p>
        </div>
      </div>
    </section>
  )
}
