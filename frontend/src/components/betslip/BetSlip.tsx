import { ShoppingCart, X } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { useBetSlip } from "@/context/BetSlipContext"
import { formatOdd } from "@/lib/utils"

function currency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
}

export function BetSlip() {
  const { selections, remove, clear } = useBetSlip()
  const [open, setOpen] = useState(false)
  const [stake, setStake] = useState(10)
  const [mode, setMode] = useState<"simples" | "multipla">("simples")

  if (selections.length === 0 && !open) return null

  const combinedOdd = selections.reduce((acc, s) => acc * s.odd, 1)
  const stakeValue = Number.isFinite(stake) && stake > 0 ? stake : 0

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-20 right-4 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg md:bottom-6"
        aria-label="Abrir carrinho de apostas"
      >
        <ShoppingCart className="h-5 w-5" />
        {selections.length > 0 && (
          <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-negative text-[11px] font-bold text-white">
            {selections.length}
          </span>
        )}
      </button>

      {open && (
        <div className="fixed inset-x-0 bottom-0 z-50 max-h-[80vh] overflow-y-auto rounded-t-lg border border-border bg-card p-4 shadow-2xl sm:inset-x-auto sm:bottom-6 sm:right-20 sm:w-96 sm:rounded-lg">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">Simulador de aposta</h3>
            <button onClick={() => setOpen(false)} aria-label="Fechar" className="text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          </div>

          {selections.length === 0 ? (
            <p className="mt-4 text-sm text-muted-foreground">
              Nenhuma seleção ainda. Adicione uma oportunidade de uma partida pra simular o retorno.
            </p>
          ) : (
            <>
              <div className="mt-3 flex flex-col gap-2">
                {selections.map((s) => (
                  <div key={s.id} className="flex items-center justify-between gap-2 rounded-md border border-border bg-background px-3 py-2">
                    <div className="min-w-0">
                      <p className="truncate text-xs text-muted-foreground">{s.homeTeam} x {s.awayTeam}</p>
                      <p className="truncate text-sm font-medium">{s.marketLabel}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold">{formatOdd(s.odd)}</span>
                      <button onClick={() => remove(s.id)} aria-label="Remover" className="text-muted-foreground hover:text-negative">
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {selections.length > 1 && (
                <div className="mt-3 flex gap-2">
                  <Button size="sm" variant={mode === "simples" ? "default" : "outline"} onClick={() => setMode("simples")}>
                    Simples
                  </Button>
                  <Button size="sm" variant={mode === "multipla" ? "default" : "outline"} onClick={() => setMode("multipla")}>
                    Múltipla (acumulada)
                  </Button>
                </div>
              )}

              <label className="mt-4 block text-xs text-muted-foreground">Valor da aposta</label>
              <input
                type="number"
                min={0}
                step="0.01"
                value={stake}
                onChange={(e) => setStake(e.target.valueAsNumber)}
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
              />

              <div className="mt-4 rounded-md border border-accent/40 bg-background p-3">
                {mode === "simples" || selections.length === 1 ? (
                  <div className="flex flex-col gap-1.5">
                    {selections.map((s) => (
                      <div key={s.id} className="flex items-center justify-between text-sm">
                        <span className="truncate text-muted-foreground">{s.marketLabel}</span>
                        <span className="font-semibold">{currency(stakeValue * s.odd)}</span>
                      </div>
                    ))}
                    <div className="mt-1 flex items-center justify-between border-t border-border pt-1.5 text-sm font-semibold">
                      <span>Retorno total (se todas ganharem)</span>
                      <span>{currency(selections.reduce((acc, s) => acc + stakeValue * s.odd, 0))}</span>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col gap-1.5 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Odd combinada</span>
                      <span className="font-semibold">{formatOdd(combinedOdd)}</span>
                    </div>
                    <div className="flex items-center justify-between font-semibold">
                      <span>Retorno (se todas ganharem)</span>
                      <span>{currency(stakeValue * combinedOdd)}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Lucro: {currency(stakeValue * combinedOdd - stakeValue)}
                    </p>
                  </div>
                )}
              </div>

              <Button size="sm" variant="ghost" className="mt-3 w-full text-muted-foreground" onClick={clear}>
                Limpar carrinho
              </Button>
              <p className="mt-2 text-[11px] text-muted-foreground">
                Simulação apenas — nenhuma aposta real é feita aqui.
              </p>
            </>
          )}
        </div>
      )}
    </>
  )
}
