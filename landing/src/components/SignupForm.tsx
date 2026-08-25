import { Check, Loader2, MessageCircle } from "lucide-react"
import { useState } from "react"

import { PLANS, type PlanId, whatsappLink } from "@/config"
import { ApiError, submitLead } from "@/services/api"

function formatPhoneInput(raw: string): string {
  const digits = raw.replace(/\D/g, "").slice(0, 11)
  if (digits.length <= 2) return digits
  if (digits.length <= 7) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`
  return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`
}

export function SignupForm({ selectedPlan }: { selectedPlan: PlanId }) {
  const [name, setName] = useState("")
  const [phone, setPhone] = useState("")
  const [plan, setPlan] = useState<PlanId>(selectedPlan)
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle")
  const [error, setError] = useState<string | null>(null)

  const phoneDigits = phone.replace(/\D/g, "")
  const canSubmit = name.trim().length >= 2 && phoneDigits.length >= 10

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit || status === "loading") return
    setStatus("loading")
    setError(null)
    try {
      await submitLead({ name: name.trim(), phone: `55${phoneDigits}`, plan })
      setStatus("done")
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Não deu pra completar o cadastro agora, tenta de novo em instantes.")
      setStatus("error")
    }
  }

  if (status === "done") {
    return (
      <div className="mx-auto max-w-md rounded-lg border border-whatsapp/30 bg-surface p-6 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-whatsapp text-black">
          <Check className="h-6 w-6" />
        </div>
        <h3 className="mt-3 font-bold">Cadastro feito</h3>
        <p className="mt-1.5 text-sm text-text-muted">
          Falta 1 passo: manda a mensagem abaixo no WhatsApp pra gente ativar seu envio (é assim
          que garantimos que a mensagem não cai em spam).
        </p>
        <a
          href={whatsappLink()}
          target="_blank"
          rel="noreferrer"
          className="mt-4 inline-flex items-center gap-2 rounded-md bg-whatsapp px-5 py-2.5 font-mono text-sm font-bold text-black transition-transform hover:-translate-y-0.5"
        >
          <MessageCircle className="h-4 w-4" />
          Abrir WhatsApp
        </a>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="mx-auto flex max-w-md flex-col gap-3">
      <div className="flex gap-2 rounded-md border border-border bg-surface p-1">
        {PLANS.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => setPlan(p.id)}
            className={`flex-1 rounded px-3 py-2 font-mono text-xs font-bold uppercase transition-colors ${
              plan === p.id ? "bg-brand text-brand-ink" : "text-text-muted hover:text-text"
            }`}
          >
            {p.name}
          </button>
        ))}
      </div>

      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Seu nome"
        className="rounded-md border border-border bg-surface px-4 py-3 text-sm text-text outline-none placeholder:text-text-subtle focus-visible:border-brand"
      />
      <input
        value={phone}
        onChange={(e) => setPhone(formatPhoneInput(e.target.value))}
        placeholder="(00) 00000-0000"
        inputMode="numeric"
        className="rounded-md border border-border bg-surface px-4 py-3 text-sm text-text outline-none placeholder:text-text-subtle focus-visible:border-brand"
      />

      {error && <p className="text-sm text-negative">{error}</p>}

      <button
        type="submit"
        disabled={!canSubmit || status === "loading"}
        className="mt-1 inline-flex items-center justify-center gap-2 rounded-md bg-brand px-5 py-3 font-mono text-sm font-bold uppercase tracking-wide text-brand-ink transition-transform hover:-translate-y-0.5 disabled:pointer-events-none disabled:opacity-40"
      >
        {status === "loading" ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
        {status === "loading" ? "Cadastrando" : "Quero receber"}
      </button>
      <p className="text-center text-[11px] text-text-subtle">
        Seu número só é usado pra te mandar as odds no WhatsApp. Sem spam.
      </p>
    </form>
  )
}
