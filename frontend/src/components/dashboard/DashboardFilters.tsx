import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { League } from "@/types/api"

export interface Filters {
  leagueId: number | undefined
  minConfidence: string | undefined
  minEdge: number | undefined
}

export function DashboardFilters({
  leagues, filters, onChange,
}: { leagues: League[]; filters: Filters; onChange: (f: Filters) => void }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select
        value={filters.leagueId ? String(filters.leagueId) : "all"}
        onValueChange={(v) => onChange({ ...filters, leagueId: v === "all" ? undefined : Number(v) })}
      >
        <SelectTrigger className="w-48"><SelectValue placeholder="Todas as ligas" /></SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Todas as ligas</SelectItem>
          {leagues.map((l) => (
            <SelectItem key={l.id} value={String(l.id)}>{l.name} ({l.country})</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filters.minConfidence ?? "any"}
        onValueChange={(v) => onChange({ ...filters, minConfidence: v === "any" ? undefined : v })}
      >
        <SelectTrigger className="w-44"><SelectValue placeholder="Confiança mínima" /></SelectTrigger>
        <SelectContent>
          <SelectItem value="any">Qualquer confiança</SelectItem>
          <SelectItem value="baixa">Confiança ≥ baixa</SelectItem>
          <SelectItem value="média">Confiança ≥ média</SelectItem>
          <SelectItem value="alta">Confiança ≥ alta</SelectItem>
        </SelectContent>
      </Select>

      <Select
        value={filters.minEdge !== undefined ? String(filters.minEdge) : "any"}
        onValueChange={(v) => onChange({ ...filters, minEdge: v === "any" ? undefined : Number(v) })}
      >
        <SelectTrigger className="w-40"><SelectValue placeholder="Edge mínimo" /></SelectTrigger>
        <SelectContent>
          <SelectItem value="any">Qualquer edge</SelectItem>
          <SelectItem value="0.03">Edge ≥ 3%</SelectItem>
          <SelectItem value="0.05">Edge ≥ 5%</SelectItem>
          <SelectItem value="0.1">Edge ≥ 10%</SelectItem>
        </SelectContent>
      </Select>
    </div>
  )
}
