import { Badge } from "@/components/ui/badge"
import type { SampleConfidence } from "@/types/api"

const LABEL: Record<SampleConfidence, string> = {
  insuficiente: "Amostra insuficiente",
  limitada: "Amostra limitada",
  representativa: "Amostra representativa",
}
const VARIANT: Record<SampleConfidence, "neutral" | "warning" | "positive"> = {
  insuficiente: "neutral",
  limitada: "warning",
  representativa: "positive",
}

export function SampleConfidenceTag({ confidence, n }: { confidence: SampleConfidence; n: number }) {
  return <Badge variant={VARIANT[confidence]}>{LABEL[confidence]} (n={n})</Badge>
}
