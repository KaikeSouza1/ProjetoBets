import { BRAND_NAME } from "@/config"

export function Footer() {
  return (
    <footer className="bg-green-deep py-8">
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-3 px-4 text-center sm:px-6">
        <span className="text-sm font-bold text-white">{BRAND_NAME}</span>
        <p className="max-w-md text-xs text-white/50">
          Conteúdo estatístico e informativo, não é recomendação financeira nem garantia de
          resultado. Aposte com responsabilidade. Proibido para menores de 18 anos.
        </p>
      </div>
    </footer>
  )
}
