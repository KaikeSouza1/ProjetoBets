import { Check, CheckCheck, Signal, Wifi } from "lucide-react"

import { BRAND_NAME, WHATSAPP_DEFAULT_MESSAGE, type SampleMessage } from "@/config"

function OpportunityBubble({ msg, delay }: { msg: SampleMessage; delay: number }) {
  return (
    <div
      className="animate-fade-up max-w-[85%] rounded-lg rounded-tl-sm bg-[#202c33] px-3 py-2.5"
      style={{ animationDelay: `${delay}ms` }}
    >
      <p className="font-mono text-[13px] font-bold text-white">{msg.match}</p>
      <p className="mt-0.5 text-[12px] text-white/70">{msg.market}</p>

      <div className="mt-2 flex items-center gap-2">
        <span className="rounded bg-black/30 px-1.5 py-0.5 font-mono text-[13px] font-bold text-brand">
          {msg.odd}
        </span>
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
            msg.confidence === "alta" ? "bg-whatsapp/20 text-whatsapp" : "bg-white/10 text-white/60"
          }`}
        >
          confiança {msg.confidence}
        </span>
      </div>

      <p className="mt-1.5 text-[11px] leading-snug text-white/50">{msg.note}</p>

      <div className="mt-1 flex items-center justify-end gap-1">
        <span className="text-[10px] text-white/40">{msg.time}</span>
      </div>
    </div>
  )
}

export function PhoneMockup({ messages }: { messages: SampleMessage[] }) {
  return (
    <div className="mx-auto w-full max-w-[300px]">
      <div className="overflow-hidden rounded-[2.25rem] border-4 border-surface-2 bg-black shadow-[0_40px_80px_-30px_rgba(0,0,0,0.8)]">
        {/* status bar */}
        <div className="flex items-center justify-between bg-[#0b141a] px-5 pb-1 pt-2.5 text-white">
          <span className="font-mono text-[11px] font-medium">21:04</span>
          <div className="flex items-center gap-1">
            <Signal className="h-3 w-3" />
            <Wifi className="h-3 w-3" />
          </div>
        </div>

        {/* whatsapp header */}
        <div className="flex items-center gap-2.5 bg-[#0b141a] px-3 pb-2.5 pt-1">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-whatsapp text-black">
            <span className="font-mono text-sm font-black">$</span>
          </div>
          <div>
            <p className="text-[13px] font-bold text-white">{BRAND_NAME}</p>
            <p className="text-[10px] text-white/40">online</p>
          </div>
        </div>

        {/* chat area */}
        <div className="flex min-h-[380px] flex-col gap-2.5 bg-[#0a0e0c] bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.03)_1px,transparent_0)] bg-[size:16px_16px] p-3">
          <div className="flex justify-end">
            <div className="animate-fade-up max-w-[80%] rounded-lg rounded-tr-sm bg-[#005c4b] px-3 py-2">
              <p className="text-[13px] text-white">{WHATSAPP_DEFAULT_MESSAGE}</p>
              <div className="mt-1 flex items-center justify-end gap-1">
                <span className="text-[10px] text-white/50">21:03</span>
                <CheckCheck className="h-3 w-3 text-[#53bdeb]" />
              </div>
            </div>
          </div>

          <div className="flex justify-start">
            <div className="animate-fade-up max-w-[75%] rounded-lg rounded-tl-sm bg-[#202c33] px-3 py-2" style={{ animationDelay: "150ms" }}>
              <p className="text-[13px] text-white/90">Fechado. Aqui está a oportunidade de hoje:</p>
              <div className="mt-1 flex items-center justify-end">
                <span className="text-[10px] text-white/40">21:03</span>
              </div>
            </div>
          </div>

          {messages.map((msg, i) => (
            <div key={msg.match} className="flex justify-start">
              <OpportunityBubble msg={msg} delay={300 + i * 150} />
            </div>
          ))}

          <div className="flex items-center gap-1.5 self-start rounded-full bg-white/5 px-2 py-1">
            <Check className="h-3 w-3 text-white/30" />
            <span className="text-[10px] text-white/30">enviado automaticamente</span>
          </div>
        </div>
      </div>
    </div>
  )
}
