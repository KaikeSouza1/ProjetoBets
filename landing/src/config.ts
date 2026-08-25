// ponto único de configuração de marca/contato: trocar nome e número aqui
// atualiza o site inteiro. Nome ainda não definido: placeholder deliberado.
export const BRAND_NAME = "GreenOdds"

// wa.me exige o número SEM "+" e sem espaços/traços, com DDI (55 = Brasil).
// Fluxo: usuário manda a PRIMEIRA mensagem pra esse número (evita ban de conta
// nova por disparo em massa). Depois disso, o robô responde a partir de "/odds".
export const WHATSAPP_NUMBER = "5542998119282"
export const WHATSAPP_DEFAULT_MESSAGE = "Oi! Quero receber as odds do dia."

export function whatsappLink(message: string = WHATSAPP_DEFAULT_MESSAGE): string {
  return `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(message)}`
}

export type PlanId = "gratis" | "pro"

export interface Plan {
  id: PlanId
  name: string
  price: string
  priceNote: string
  highlight: boolean
  features: string[]
}

export const PLANS: Plan[] = [
  {
    id: "gratis",
    name: "Grátis",
    price: "R$ 0",
    priceNote: "sempre",
    highlight: false,
    features: [
      "1 odd de valor por dia",
      "Enviado direto no WhatsApp",
      "Sem cartão, sem pegadinha",
    ],
  },
  {
    id: "pro",
    name: "PRO",
    price: "R$ 14,90",
    priceNote: "/mês",
    highlight: true,
    features: [
      "3 odds de valor por dia",
      "1 múltipla selecionada",
      "Prioridade no envio",
      "Cancele quando quiser",
    ],
  },
]
