import { BRAND_NAME } from "@/config"

export function Footer() {
  return (
    <footer className="bg-bg py-8">
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-3 px-4 text-center sm:px-6">
        <span className="font-mono text-sm font-bold text-text">{BRAND_NAME.toLowerCase()}_</span>
        <p className="max-w-md text-xs text-text-subtle">
          Conteúdo estatístico e informativo, não é recomendação financeira nem garantia de
          resultado. Aposte com responsabilidade. Proibido para menores de 18 anos.
        </p>
      </div>
    </footer>
  )
}
