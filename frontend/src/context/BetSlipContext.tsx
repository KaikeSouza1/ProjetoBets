import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react"

export interface BetSlipSelection {
  id: string
  fdMatchId: number
  homeTeam: string
  awayTeam: string
  marketLabel: string
  odd: number
}

interface BetSlipContextValue {
  selections: BetSlipSelection[]
  add: (selection: BetSlipSelection) => void
  remove: (id: string) => void
  clear: () => void
  has: (id: string) => boolean
}

const BetSlipContext = createContext<BetSlipContextValue | null>(null)

const STORAGE_KEY = "bet-slip:selections"

function loadInitial(): BetSlipSelection[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function BetSlipProvider({ children }: { children: ReactNode }) {
  const [selections, setSelections] = useState<BetSlipSelection[]>(loadInitial)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(selections))
    } catch {
      // armazenamento indisponível (modo privado, etc.) — carrinho só não persiste entre sessões
    }
  }, [selections])

  const value = useMemo<BetSlipContextValue>(
    () => ({
      selections,
      add: (selection) =>
        setSelections((prev) => (prev.some((s) => s.id === selection.id) ? prev : [...prev, selection])),
      remove: (id) => setSelections((prev) => prev.filter((s) => s.id !== id)),
      clear: () => setSelections([]),
      has: (id) => selections.some((s) => s.id === id),
    }),
    [selections],
  )

  return <BetSlipContext.Provider value={value}>{children}</BetSlipContext.Provider>
}

export function useBetSlip() {
  const ctx = useContext(BetSlipContext)
  if (!ctx) throw new Error("useBetSlip precisa estar dentro de BetSlipProvider")
  return ctx
}
