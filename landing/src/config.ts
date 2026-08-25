// ponto único de configuração de marca/contato: trocar nome e número aqui
// atualiza o site inteiro. Nome ainda não definido: placeholder deliberado.
export const BRAND_NAME = "GreenOdds"

// wa.me exige o número SEM "+" e sem espaços/traços, com DDI (55 = Brasil).
// Fluxo: usuário manda a PRIMEIRA mensagem pra esse número (evita ban de conta
// nova por disparo em massa). Depois disso, o robô responde a partir de "/odds".
export const WHATSAPP_NUMBER = "5542998119282"
export const WHATSAPP_DEFAULT_MESSAGE = "Olá, quero receber odds gratuitas."

export function whatsappLink(message: string = WHATSAPP_DEFAULT_MESSAGE): string {
  return `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(message)}`
}

// mensagens de exemplo pro mockup de WhatsApp (hero e "produto na prática").
// Times reais, resultado fictício, deixado claro na tela como "exemplo ilustrativo",
// nunca como resultado real (não existe track record ainda, ver auditoria do produto)
export interface SampleMessage {
  match: string
  market: string
  odd: string
  confidence: "alta" | "média"
  time: string
  note: string
}

export const SAMPLE_MESSAGES: SampleMessage[] = [
  {
    match: "Flamengo x Palmeiras",
    market: "Mais de 2.5 gols",
    odd: "1.87",
    confidence: "alta",
    time: "19:30",
    note: "Modelo estima probabilidade acima do que a odd implica.",
  },
  {
    match: "Real Madrid x Barcelona",
    market: "Ambas marcam",
    odd: "1.75",
    confidence: "média",
    time: "16:00",
    note: "Amostra ainda crescendo nesta liga.",
  },
  {
    match: "Man City x Liverpool",
    market: "Vitória do mandante",
    odd: "2.10",
    confidence: "alta",
    time: "13:30",
    note: "Odd comparada entre Bet365 e Superbet.",
  },
]

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
