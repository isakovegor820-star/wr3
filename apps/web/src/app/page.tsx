import { Navbar } from "@/components/wr3/navbar";
import { Hero } from "@/components/wr3/hero";
import { TrustBar } from "@/components/wr3/trust-bar";
import { WhatYouGet } from "@/components/wr3/what-you-get";
import { HowItWorks } from "@/components/wr3/how-it-works";
import { ScoutSection } from "@/components/wr3/scout-section";
import { NotWr3Section } from "@/components/wr3/not-wr3-section";
import { FinalCta } from "@/components/wr3/final-cta";
import { Footer } from "@/components/wr3/footer";

export default function HomePage() {
  return (
    <div className="wr3-landing">
      <Navbar />
      <main>
        <Hero />
        <TrustBar />
        <WhatYouGet />
        <HowItWorks />
        <ScoutSection />
        <NotWr3Section />
        <FinalCta />
      </main>
      <Footer />
    </div>
  );
}
