import { useCallback, useState } from "react"

import { BucketTable } from "@/components/backtest/BucketTable"
import { CalibrationChart } from "@/components/backtest/CalibrationChart"
import { SampleConfidenceTag } from "@/components/backtest/SampleConfidenceTag"
import { EmptyState } from "@/components/shared/EmptyState"
import { ErrorState } from "@/components/shared/ErrorState"
import { LoadingState } from "@/components/shared/LoadingState"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useAsync } from "@/hooks/useAsync"
import { useLeagues } from "@/hooks/useDashboard"
import { formatPercent, formatSignedPercent } from "@/lib/utils"
import { api } from "@/services/api"

const MARKET_LABEL: Record<string, string> = {
  home_win: "Vitória da casa", draw: "Empate", away_win: "Vitória do visitante",
  btts_yes: "Ambas marcam — sim", over_2_5: "Mais de 2.5 gols",
  "1x2_multiclass_brier": "1X2 (Brier multiclasse — escala 0–2, não comparável às outras linhas)",
}

export function BacktestPage() {
  const leagues = useLeagues()
  const [leagueId, setLeagueId] = useState<number | undefined>(undefined)
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)
  const [calibrationMarket, setCalibrationMarket] = useState("home_win")

  const calibrationFetcher = useCallback(() => (leagueId ? api.calibration(leagueId) : Promise.resolve(null)), [leagueId])
  const calibration = useAsync(calibrationFetcher, [calibrationFetcher])

  const historicalFetcher = useCallback(() => api.historicalOddsSummary(leagueId), [leagueId])
  const historical = useAsync(historicalFetcher, [historicalFetcher])

  async function handleRunCalibration() {
    if (!leagueId) return
    setRunning(true)
    setRunError(null)
    try {
      await api.runCalibrationBacktest(leagueId)
      calibration.reload()
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "Erro ao rodar backtest")
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="flex flex-col gap-10">
      <div>
        <h1 className="text-xl font-semibold">Desempenho do modelo</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          Quando o modelo identifica uma oportunidade, ele encontra valor de forma consistente? Duas avaliações
          separadas abaixo — nunca misturadas: calibração (sem odd, valida a probabilidade em si) e avaliação com
          odds reais (ROI, edge, opportunity score — exige odd capturada antes do apito inicial).
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Select value={leagueId ? String(leagueId) : undefined} onValueChange={(v) => setLeagueId(Number(v))}>
          <SelectTrigger className="w-56"><SelectValue placeholder="Escolha uma liga" /></SelectTrigger>
          <SelectContent>
            {(leagues.data ?? []).map((l) => (
              <SelectItem key={l.id} value={String(l.id)}>{l.name} ({l.country})</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" disabled={!leagueId || running} onClick={handleRunCalibration}>
          {running ? "Rodando..." : "Rodar calibração desta liga"}
        </Button>
      </div>

      {runError && <ErrorState message={runError} />}

      {/* ==================== calibração ==================== */}
      <section>
        <h2 className="text-base font-semibold">Calibração (walk-forward, sem odd)</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Para cada partida já jogada, a probabilidade que o modelo TERIA dado usando só partidas anteriores —
          nunca ROI, porque não há odd histórica associada a este cálculo.
        </p>

        {!leagueId && <EmptyState message="Escolha uma liga para ver a calibração." />}
        {calibration.loading && leagueId && <LoadingState label="Carregando calibração..." />}
        {calibration.error && <ErrorState message={calibration.error} onRetry={calibration.reload} />}

        {calibration.data && calibration.data.metrics.length > 0 && (
          <div className="mt-4 flex flex-col gap-6">
            <div className="overflow-x-auto rounded-md border border-border">
              <table className="w-full text-sm">
                <thead className="bg-muted text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left">Mercado</th>
                    <th className="px-3 py-2 text-left">Taxa de acerto</th>
                    <th className="px-3 py-2 text-left">Brier score</th>
                    <th className="px-3 py-2 text-left">Amostra</th>
                  </tr>
                </thead>
                <tbody>
                  {calibration.data.metrics.map((m) => (
                    <tr key={m.market_key} className="border-t border-border">
                      <td className="px-3 py-2">{MARKET_LABEL[m.market_key] ?? m.market_key}</td>
                      <td className="px-3 py-2">{m.hit_rate !== null ? formatPercent(m.hit_rate) : "—"}</td>
                      <td className="px-3 py-2">{m.brier_score.toFixed(3)}</td>
                      <td className="px-3 py-2"><SampleConfidenceTag confidence={m.confidence} n={m.n_bets} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="border-t border-border px-3 py-2 text-xs text-muted-foreground">
                Brier score: quanto menor, melhor calibrado — 0.25 é próximo do que dá "sempre chutar 50%" pra um
                evento com base ~50/50. O 1x2_multiclass_brier usa escala 0–2 (soma das 3 classes) — nunca compare
                esse número lado a lado com os Brier binários acima.
              </p>
            </div>

            <div>
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold">Probabilidade prevista vs. frequência real</h3>
                <Select value={calibrationMarket} onValueChange={setCalibrationMarket}>
                  <SelectTrigger className="w-52"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="home_win">Vitória da casa</SelectItem>
                    <SelectItem value="draw">Empate</SelectItem>
                    <SelectItem value="away_win">Vitória do visitante</SelectItem>
                    <SelectItem value="btts_yes">Ambas marcam</SelectItem>
                    <SelectItem value="over_2_5">Mais de 2.5 gols</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <CalibrationCurve leagueId={leagueId} marketKey={calibrationMarket} />
            </div>
          </div>
        )}

        {calibration.data && calibration.data.metrics.length === 0 && (
          <EmptyState message='Nenhum backtest rodado ainda para esta liga — clique em "Rodar calibração desta liga".' />
        )}
      </section>

      {/* ==================== avaliação com odds reais ==================== */}
      <section>
        <h2 className="text-base font-semibold">Avaliação com odds reais (ROI, Edge, Opportunity Score)</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Só entra aqui uma partida com odd capturada ANTES do apito inicial — sem isso, ROI seria uma partida
          antiga recebendo a odd de agora. Nunca calculado a partir de odd inventada ou aproximada.
        </p>

        {historical.loading && <LoadingState label="Avaliando apostas históricas..." />}
        {historical.error && <ErrorState message={historical.error} onRetry={historical.reload} />}

        {historical.data?.insufficient_data && (
          <EmptyState message={historical.data.message ?? "Amostra insuficiente para avaliação com odds reais."} />
        )}

        {historical.data && !historical.data.insufficient_data && (
          <div className="mt-4 flex flex-col gap-6">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-md border border-border bg-card p-4">
                <p className="text-2xl font-semibold">{historical.data.hit_rate?.hit_rate !== null && historical.data.hit_rate ? formatPercent(historical.data.hit_rate.hit_rate) : "—"}</p>
                <p className="text-xs text-muted-foreground">Taxa de acerto</p>
              </div>
              <div className="rounded-md border border-border bg-card p-4">
                <p className={`text-2xl font-semibold ${(historical.data.roi?.roi ?? 0) >= 0 ? "text-positive" : "text-negative"}`}>
                  {historical.data.roi?.roi !== null && historical.data.roi ? formatSignedPercent(historical.data.roi.roi) : "—"}
                </p>
                <p className="text-xs text-muted-foreground">ROI (stake fixa de 1 unidade)</p>
              </div>
              <div className="rounded-md border border-border bg-card p-4">
                <p className="text-2xl font-semibold">{historical.data.n_bets}</p>
                <p className="text-xs text-muted-foreground">Apostas avaliadas</p>
              </div>
            </div>

            <p className="text-xs text-muted-foreground">
              Hit rate e ROI respondem perguntas diferentes — uma estratégia pode acertar menos e ainda lucrar
              mais, dependendo da odd média das apostas que ganhou.
            </p>

            <BucketTable title="Performance por edge previsto" buckets={historical.data.by_edge} isPercent />
            <BucketTable title="Performance por Opportunity Score" buckets={historical.data.by_opportunity_score} isPercent={false} />

            {historical.data.by_market.length > 0 && (
              <div>
                <h3 className="mb-2 text-sm font-semibold">Performance por mercado</h3>
                <div className="overflow-x-auto rounded-md border border-border">
                  <table className="w-full text-sm">
                    <thead className="bg-muted text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2 text-left">Mercado</th>
                        <th className="px-3 py-2 text-left">Apostas</th>
                        <th className="px-3 py-2 text-left">Hit rate</th>
                        <th className="px-3 py-2 text-left">ROI</th>
                        <th className="px-3 py-2 text-left">Amostra</th>
                      </tr>
                    </thead>
                    <tbody>
                      {historical.data.by_market.map((m) => (
                        <tr key={m.market_key} className="border-t border-border">
                          <td className="px-3 py-2">{MARKET_LABEL[m.market_key] ?? m.market_key}</td>
                          <td className="px-3 py-2">{m.n_bets}</td>
                          <td className="px-3 py-2">{m.hit_rate !== null ? formatPercent(m.hit_rate) : "—"}</td>
                          <td className="px-3 py-2">{m.roi !== null ? formatSignedPercent(m.roi) : "—"}</td>
                          <td className="px-3 py-2"><SampleConfidenceTag confidence={m.confidence} n={m.n_bets} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* ==================== evolução temporal (sem dado ainda) ==================== */}
      <section>
        <h2 className="text-base font-semibold">Performance acumulada e ROI ao longo do tempo</h2>
        <EmptyState message="Depende de apostas históricas resolvidas com data — ainda não há nenhuma no banco (ver seção acima). O gráfico aparece automaticamente quando existir amostra." />
      </section>
    </div>
  )
}

function CalibrationCurve({ leagueId, marketKey }: { leagueId: number | undefined; marketKey: string }) {
  const fetcher = useCallback(
    () => (leagueId ? api.calibrationCurve(leagueId, marketKey) : Promise.resolve([])),
    [leagueId, marketKey],
  )
  const curve = useAsync(fetcher, [fetcher])

  if (curve.loading) return <LoadingState label="Carregando curva de calibração..." />
  if (curve.error) return <ErrorState message={curve.error} onRetry={curve.reload} />
  if (!curve.data) return null
  return <CalibrationChart rows={curve.data} />
}
