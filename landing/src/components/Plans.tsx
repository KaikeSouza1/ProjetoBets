import { Check } from "lucide-react"
import { useState } from "react"

import { PLANS, type PlanId } from "@/config"
import { SignupForm } from "@/components/SignupForm"

export function Plans() {
  const [selected, setSelected] = useState<PlanId>("gratis")

  return (
    <section id="planos" className="border-b border-border bg-bg py-16 sm:py-24">
      <div className="mx-auto max-w-5xl px-4 sm:px-6">
        <p className="text-center font-mono text-xs uppercase tracking-widest text-text-subtle">Planos</p>
        <h2 className="mt-2 text-center text-2xl font-black tracking-tight sm:text-3xl">
          Quer receber as oportunidades no WhatsApp?
        </h2>

        <div className="mx-auto mt-10 grid max-w-2xl grid-cols-1 gap-4 sm:grid-cols-2">
          {PLANS.map((plan) => {
            const isPro = plan.highlight
            const isSelected = selected === plan.id
            return (
              <button
                key={plan.id}
                type="button"
                onClick={() => setSelected(plan.id)}
                className={`rounded-lg border p-6 text-left transition-colors ${
                  isSelected ? "border-brand bg-surface" : "border-border bg-surface hover:border-border-strong"
                }`}
              >
                {isPro && (
                  <span className="mb-3 inline-block font-mono text-[11px] font-bold uppercase tracking-wide text-brand">
                    mais escolhido
                  </span>
                )}
                <h3 className="text-lg font-bold text-text">{plan.name}</h3>
                <p className="mt-1">
                  <span className="font-mono text-3xl font-bold text-text">{plan.price}</span>
                  <span className="text-sm text-text-muted"> {plan.priceNote}</span>
                </p>
                <ul className="mt-4 flex flex-col gap-2">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-text-muted">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-whatsapp" />
                      {f}
                    </li>
                  ))}
                </ul>
              </button>
            )
          })}
        </div>

        <div className="mt-10">
          <SignupForm selectedPlan={selected} />
        </div>
      </div>
    </section>
  )
}
