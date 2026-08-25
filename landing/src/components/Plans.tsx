import { Check } from "lucide-react"
import { useState } from "react"

import { PLANS, type PlanId } from "@/config"
import { SignupForm } from "@/components/SignupForm"

export function Plans() {
  const [selected, setSelected] = useState<PlanId>("gratis")

  return (
    <section id="planos" className="bg-bg-subtle py-16">
      <div className="mx-auto max-w-5xl px-4 sm:px-6">
        <div className="mx-auto max-w-xl text-center">
          <h2 className="text-2xl font-extrabold tracking-tight sm:text-3xl">Planos</h2>
          <p className="mt-2 text-text-muted">Começa grátis. Sobe pra PRO quando fizer sentido.</p>
        </div>

        <div className="mx-auto mt-10 grid max-w-2xl grid-cols-1 gap-6 sm:grid-cols-2">
          {PLANS.map((plan) => (
            <button
              key={plan.id}
              type="button"
              onClick={() => setSelected(plan.id)}
              className={`text-left rounded-2xl border p-6 transition-all ${
                plan.highlight ? "border-brand bg-surface shadow-[0_20px_40px_-20px_rgba(194,255,11,0.5)]" : "border-border bg-surface"
              } ${selected === plan.id ? "ring-2 ring-brand" : ""}`}
            >
              {plan.highlight && (
                <span className="mb-3 inline-block rounded-full bg-brand px-3 py-1 text-[11px] font-bold text-brand-ink">
                  MAIS ESCOLHIDO
                </span>
              )}
              <h3 className="text-lg font-bold">{plan.name}</h3>
              <p className="mt-1">
                <span className="text-3xl font-black">{plan.price}</span>
                <span className="text-sm text-text-muted"> {plan.priceNote}</span>
              </p>
              <ul className="mt-4 flex flex-col gap-2">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-text-muted">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-positive" />
                    {f}
                  </li>
                ))}
              </ul>
            </button>
          ))}
        </div>

        <div className="mt-10">
          <SignupForm selectedPlan={selected} />
        </div>
      </div>
    </section>
  )
}
