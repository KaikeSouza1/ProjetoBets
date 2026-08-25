import { Footer } from "@/components/Footer"
import { Header } from "@/components/Header"
import { Hero } from "@/components/Hero"
import { HowItWorks } from "@/components/HowItWorks"
import { Plans } from "@/components/Plans"

export default function App() {
  return (
    <div className="min-h-screen bg-bg text-text">
      <Header />
      <Hero />
      <HowItWorks />
      <Plans />
      <Footer />
    </div>
  )
}
