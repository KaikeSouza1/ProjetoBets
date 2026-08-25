import { Zap } from "lucide-react"

import { BRAND_NAME } from "@/config"

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-bg/90 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3 sm:px-6">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand">
            <Zap className="h-4.5 w-4.5 fill-brand-ink text-brand-ink" />
          </div>
          <span className="text-base font-extrabold tracking-tight">{BRAND_NAME}</span>
        </div>
        <a
          href="#planos"
          className="rounded-full bg-brand px-4 py-2 text-sm font-bold text-brand-ink transition-transform hover:-translate-y-0.5"
        >
          Quero receber
        </a>
      </div>
    </header>
  )
}
