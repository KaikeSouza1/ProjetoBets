import { Suspense, lazy } from "react"
import { Route, Routes } from "react-router-dom"

import { AppLayout } from "@/layouts/AppLayout"
import { BetSlip } from "@/components/betslip/BetSlip"
import { LoadingState } from "@/components/shared/LoadingState"
import { BetSlipProvider } from "@/context/BetSlipContext"
import { DashboardPage } from "@/pages/DashboardPage"
import { LeaguesPage } from "@/pages/LeaguesPage"
import { MatchPage } from "@/pages/MatchPage"
import { MatchesPage } from "@/pages/MatchesPage"

// Recharts só é usado aqui — isolado no próprio chunk pra não pesar o carregamento
// inicial do dashboard (era o maior contribuinte pro bundle passar de 500kB)
const BacktestPage = lazy(() => import("@/pages/BacktestPage").then((m) => ({ default: m.BacktestPage })))

export default function App() {
  return (
    <BetSlipProvider>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="matches" element={<MatchesPage />} />
          <Route path="matches/:id" element={<MatchPage />} />
          <Route path="leagues" element={<LeaguesPage />} />
          <Route
            path="backtest"
            element={
              <Suspense fallback={<LoadingState label="Carregando..." />}>
                <BacktestPage />
              </Suspense>
            }
          />
        </Route>
      </Routes>
      <BetSlip />
    </BetSlipProvider>
  )
}
