import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge"
import { formatPercent } from "@/lib/utils"
import type { MatchPlayers } from "@/types/api"

function TeamPlayers({ teamName, side }: { teamName: string; side: MatchPlayers["home"] }) {
  return (
    <div>
      <p className="mb-2 text-sm font-semibold">{teamName}</p>
      {side.error ? (
        <p className="text-xs text-muted-foreground">{side.error}</p>
      ) : (
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-3 py-2 text-left">Jogador</th>
                <th className="px-3 py-2 text-left">Marcar</th>
                <th className="px-3 py-2 text-left">Assistir</th>
                <th className="px-3 py-2 text-left">Cartão</th>
                <th className="px-3 py-2 text-left">Confiança</th>
              </tr>
            </thead>
            <tbody>
              {side.players.map((p) => (
                <tr key={p.player_id} className="border-t border-border">
                  <td className="px-3 py-2">{p.name}</td>
                  <td className="px-3 py-2">{formatPercent(p.prob_score)}</td>
                  <td className="px-3 py-2">{formatPercent(p.prob_assist)}</td>
                  <td className="px-3 py-2">{formatPercent(p.prob_card)}</td>
                  <td className="px-3 py-2"><ConfidenceBadge confidence={p.confidence} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export function PlayersPanel({ players, homeName, awayName }: { players: MatchPlayers; homeName: string; awayName: string }) {
  // cada lado já traz seu próprio erro descritivo (fixture fora da janela, dado
  // insuficiente, etc.) — não há um "estado geral" único que resuma os dois times.
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <TeamPlayers teamName={homeName} side={players.home} />
      <TeamPlayers teamName={awayName} side={players.away} />
    </div>
  )
}
