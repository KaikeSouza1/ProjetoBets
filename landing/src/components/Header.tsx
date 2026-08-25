import { BRAND_NAME } from "@/config"

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-bg/90 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3 sm:px-6">
        <span className="font-mono text-sm font-bold tracking-tight text-text">
          {BRAND_NAME.toLowerCase()}<span className="text-brand">_</span>
        </span>
        <a
          href="#planos"
          className="rounded-md border border-border-strong px-4 py-1.5 font-mono text-xs font-bold uppercase tracking-wide text-text transition-colors hover:border-brand hover:text-brand"
        >
          Quero receber
        </a>
      </div>
    </header>
  )
}
