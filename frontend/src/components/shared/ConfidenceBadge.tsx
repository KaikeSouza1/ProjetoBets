import { Badge } from "@/components/ui/badge"
import type { Confidence } from "@/types/api"

const LABELS: Record<Confidence, string> = { alta: "Confiança alta", média: "Confiança média", baixa: "Confiança baixa" }
const VARIANTS: Record<Confidence, "positive" | "warning" | "neutral"> = {
  alta: "positive",
  média: "warning",
  baixa: "neutral",
}

export function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  return <Badge variant={VARIANTS[confidence]}>{LABELS[confidence]}</Badge>
}
