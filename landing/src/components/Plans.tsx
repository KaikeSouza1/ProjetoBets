import { Check } from "lucide-react"
import { useState } from "react"

import { PLANS, type PlanId } from "@/config"
import { SignupForm } from "@/components/SignupForm"

export function Plans() {
  const [selected, setSelected] = useState<PlanId>("gratis")

  return (
    <section id="planos" className="bg-bg py-16 sm:py-24">
      <div className="mx-auto max-w-5xl px-4 sm:px-6">
        <h2 className="text-center text-3xl font-black tracking-tight sm:text-4xl">Planos</h2>
        <p className="mt-2 text-center text-text-muted">Começa grátis. Sobe pra PRO quando fizer sentido.</p>

        <div className="mx-auto mt-10 grid max-w-2xl grid-cols-1 gap-6 sm:grid-cols-2">
          {PLANS.map((plan) => {
            const isPro = plan.highlight
            const isSelected = selected === plan.id
            return (
              <button
                key={plan.id}
                type="button"
                onClick={() => setSelected(plan.id)}
                className={`text-left rounded-2xl p-6 transition-all ${
                  isPro ? "bg-green-deep text-white" : "border border-border bg-surface"
                } ${isSelected ? "ring-2 ring-brand ring-offset-2 ring-offset-bg" : ""}`}
              >
                {isPro && (
                  <span className="mb-3 inline-block rounded-md bg-brand px-3 py-1 text-[11px] font-black uppercase text-brand-ink">
                    Mais escolhido
                  </span>
                )}
                <h3 className={`text-lg font-bold ${isPro ? "text-white" : "text-text"}`}>{plan.name}</h3>
                <p className="mt-1">
                  <span className={`text-3xl font-black ${isPro ? "text-brand" : "text-text"}`}>{plan.price}</span>
                  <span className={`text-sm ${isPro ? "text-white/60" : "text-text-muted"}`}> {plan.priceNote}</span>
                </p>
                <ul className="mt-4 flex flex-col gap-2">
                  {plan.features.map((f) => (
                    <li key={f} className={`flex items-start gap-2 text-sm ${isPro ? "text-white/80" : "text-text-muted"}`}>
                      <Check className={`mt-0.5 h-4 w-4 shrink-0 ${isPro ? "text-brand" : "text-positive"}`} />
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
