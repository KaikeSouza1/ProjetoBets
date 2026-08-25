import { FAQ } from "@/components/FAQ"
import { FinalCTA } from "@/components/FinalCTA"
import { Footer } from "@/components/Footer"
import { ForWho } from "@/components/ForWho"
import { Header } from "@/components/Header"
import { Hero } from "@/components/Hero"
import { HowItWorks } from "@/components/HowItWorks"
import { Pipeline } from "@/components/Pipeline"
import { Plans } from "@/components/Plans"
import { ProductInPractice } from "@/components/ProductInPractice"
import { StatsStrip } from "@/components/StatsStrip"
import { WhyWhatsApp } from "@/components/WhyWhatsApp"

export default function App() {
  return (
    <div className="min-h-screen bg-bg text-text">
      <Header />
      <Hero />
      <Pipeline />
      <ProductInPractice />
      <WhyWhatsApp />
      <ForWho />
      <StatsStrip />
      <HowItWorks />
      <Plans />
      <FAQ />
      <FinalCTA />
      <Footer />
    </div>
  )
}
