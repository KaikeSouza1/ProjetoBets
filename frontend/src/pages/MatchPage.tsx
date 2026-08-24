import { useParams } from "react-router-dom"

import { BestOpportunityPanel } from "@/components/match/BestOpportunityPanel"
import { MarketsPanel } from "@/components/match/MarketsPanel"
import { MatchHeaderCard } from "@/components/match/MatchHeaderCard"
import { OtherOpportunities } from "@/components/match/OtherOpportunities"
import { PlayersPanel } from "@/components/match/PlayersPanel"
import { StatComparison } from "@/components/match/StatComparison"
import { TeamForm } from "@/components/match/TeamForm"
import { ErrorState } from "@/components/shared/ErrorState"
import { LoadingState } from "@/components/shared/LoadingState"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useMatchAnalysis, useMatchForm, useMatchHeader, useMatchMarkets, useMatchPlayers } from "@/hooks/useMatch"

export function MatchPage() {
  const { id } = useParams<{ id: string }>()
  const matchId = Number(id)

  const header = useMatchHeader(matchId)
  const analysis = useMatchAnalysis(matchId)
  const markets = useMatchMarkets(matchId)
  const form = useMatchForm(matchId)
  const players = useMatchPlayers(matchId)

  if (header.loading) return <LoadingState label="Carregando partida..." />
  if (header.error) return <ErrorState message={header.error} onRetry={header.reload} />
  if (!header.data) return null

  return (
    <div className="flex flex-col gap-6">
      <MatchHeaderCard header={header.data} />

      {analysis.loading && <LoadingState label="Calculando oportunidades..." />}
      {analysis.error && <ErrorState message={analysis.error} onRetry={analysis.reload} />}
      {analysis.data && (
        <>
          <BestOpportunityPanel
            analysis={analysis.data}
            match={{ fdMatchId: header.data.fd_match_id, homeTeam: header.data.home_team, awayTeam: header.data.away_team }}
          />
          <OtherOpportunities
            opportunities={analysis.data.other_opportunities}
            match={{ fdMatchId: header.data.fd_match_id, homeTeam: header.data.home_team, awayTeam: header.data.away_team }}
          />
        </>
      )}

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Visão geral</TabsTrigger>
          <TabsTrigger value="markets">Mercados</TabsTrigger>
          <TabsTrigger value="players">Jogadores</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          {form.loading && <LoadingState label="Carregando forma recente..." />}
          {form.error && <ErrorState message={form.error} onRetry={form.reload} />}
          {form.data && (
            <div className="flex flex-col gap-6">
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <TeamForm teamName={header.data.home_team} form={form.data.home_form} />
                <TeamForm teamName={header.data.away_team} form={form.data.away_form} />
              </div>
              <StatComparison
                homeName={header.data.home_team}
                awayName={header.data.away_team}
                homeForm={form.data.home_form}
                awayForm={form.data.away_form}
              />
            </div>
          )}
        </TabsContent>

        <TabsContent value="markets">
          {markets.loading && <LoadingState label="Carregando mercados..." />}
          {markets.error && <ErrorState message={markets.error} onRetry={markets.reload} />}
          {markets.data && <MarketsPanel families={markets.data.families} />}
        </TabsContent>

        <TabsContent value="players">
          {players.loading && <LoadingState label="Carregando jogadores..." />}
          {players.error && <ErrorState message={players.error} onRetry={players.reload} />}
          {players.data && (
            <PlayersPanel players={players.data} homeName={header.data.home_team} awayName={header.data.away_team} />
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
