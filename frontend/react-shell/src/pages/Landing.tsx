import React, { useState, useEffect } from "react";
import axios from "axios";
import { API } from "@/lib/api";
import { Link } from "react-router-dom";
import { GtexHomeNav } from "@/components/landing/GtexHomeNav";
import { HeroSection } from "@/components/landing/HeroSection";
import { ClarityStrip } from "@/components/landing/ClarityStrip";
import { PlatformMapSection } from "@/components/landing/PlatformMapSection";
import { LivingWorldSection } from "@/components/landing/LivingWorldSection";
import { ClubOwnershipSection } from "@/components/landing/ClubOwnershipSection";
import { TvFinanceSection } from "@/components/landing/TvFinanceSection";
import { RegenEconomySection } from "@/components/landing/RegenEconomySection";
import { CompetitionsJackpotSection } from "@/components/landing/CompetitionsJackpotSection";
import { WiderUniverseSection } from "@/components/landing/WiderUniverseSection";
import { ClubValuationSection } from "@/components/landing/ClubValuationSection";
import { HowItWorksSection } from "@/components/landing/HowItWorksSection";
import { TrustAndIntegritySection } from "@/components/landing/TrustAndIntegritySection";
import { ConversionAndFooterSection } from "@/components/landing/ConversionAndFooterSection";
import { GtexTopAdvertisingRail, GtexHomepageAdvertising } from "@/components/advertising/GtexAdvertising";
import { PublicTrafficStatsStrip } from "@/components/landing/PublicTrafficStatsStrip";
import { useLiveWorldPulse } from "@/components/landing/useLiveWorldPulse";
import { NigeriaPlaySection } from "@/components/landing/NigeriaPlaySection";
import { DocumentHead } from "@/components/seo/DocumentHead";

export default function Landing() {
  const pulse = useLiveWorldPulse();
  const [jackpotLabel, setJackpotLabel] = useState<string | null>(null);
  const [jackpotBalance, setJackpotBalance] = useState<string | null>(null);
  const [failsafeAt, setFailsafeAt] = useState<string | null>(null);

  const loadJackpot = async () => {
    try {
      const res = await axios.get(`${API}/jackpot/state`, { timeout: 3000 });
      const state = res.data?.data || res.data;
      if (!state) return;

      const balance = state.balance ?? state.current_balance;
      const rawFailsafe = state.failsafe_at ?? state.failsafeAt;
      let label = "Jackpot";
      let balanceStr: string | null = null;

      if (balance != null) {
        balanceStr = `${balance} GTC`;
        label = `Jackpot ${balance}`;
      }

      let due: Date | null = null;
      if (rawFailsafe) {
        due = new Date(rawFailsafe);
        if (!isNaN(due.getTime())) {
          const remainingMs = due.getTime() - Date.now();
          if (remainingMs > 0) {
            const remainingHours = Math.floor(remainingMs / (1000 * 60 * 60));
            const remainingMins = Math.floor((remainingMs % (1000 * 60 * 60)) / (1000 * 60));
            const remainingSecs = Math.floor((remainingMs % (1000 * 60)) / 1000);
            const hh = String(remainingHours).padStart(2, "0");
            const mm = String(remainingMins).padStart(2, "0");
            const ss = String(remainingSecs).padStart(2, "0");
            label = `Drop ${hh}:${mm}:${ss}`;
          }
        }
      }

      setJackpotLabel(label);
      setJackpotBalance(balanceStr);
      setFailsafeAt(due ? due.toISOString() : null);
    } catch {
      // Fallback: local 6-hr drop calculation for banner
      const now = new Date();
      const utcHours = now.getUTCHours();
      const nextDropHour = (Math.floor(utcHours / 6) + 1) * 6;
      const nextDrop = new Date(
        Date.UTC(
          now.getUTCFullYear(),
          now.getUTCMonth(),
          now.getUTCDate(),
          nextDropHour >= 24 ? 0 : nextDropHour,
          0,
          0,
          0
        )
      );
      if (nextDropHour >= 24) {
        nextDrop.setUTCDate(nextDrop.getUTCDate() + 1);
      }
      const remainingMs = nextDrop.getTime() - now.getTime();
      const remainingHours = Math.floor(remainingMs / (1000 * 60 * 60));
      const remainingMins = Math.floor((remainingMs % (1000 * 60 * 60)) / (1000 * 60));
      const remainingSecs = Math.floor((remainingMs % (1000 * 60)) / 1000);
      const hh = String(remainingHours).padStart(2, "0");
      const mm = String(remainingMins).padStart(2, "0");
      const ss = String(remainingSecs).padStart(2, "0");
      setJackpotLabel(`Drop ${hh}:${mm}:${ss}`);
      setJackpotBalance("125,000 GTC");
      setFailsafeAt(nextDrop.toISOString());
    }
  };

  useEffect(() => {
    loadJackpot();
    const interval = setInterval(() => {
      loadJackpot();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div data-testid="landing-page" className="min-h-screen bg-[#0B1626] text-[#F2F4F8] selection:bg-emerald-500/30 selection:text-white">
      <DocumentHead
        title="GTEX Nigeria | Create a club, trade coins in naira, play football"
        description="GTEX is the Lagos football universe. Create a club in foundation, buy and sell coins in naira, run a 3D operations centre, develop academy regens, and enter national team competitions for free."
        path="/"
      />
      {/* 1. World-Class Sticky Nav */}
      <GtexHomeNav
        pulse={pulse}
        jackpotLabel={jackpotLabel}
        onScrollToSection={scrollToSection}
      />
      <GtexTopAdvertisingRail />
      <div aria-hidden="true" className="h-[148px] md:h-[158px]" />

      {/* 2. Cinematic Hero & Live Pulse */}
      <HeroSection
        pulse={pulse}
        onExplore={() => scrollToSection("platform")}
      />
      <PublicTrafficStatsStrip pulse={pulse} />
      <NigeriaPlaySection />

      <section
        className="mx-auto my-6 max-w-7xl px-4 sm:px-6 lg:px-8"
        data-testid="first-500-founding-club-banner"
        aria-labelledby="first-500-founding-club-title"
      >
        <div className="flex flex-col gap-5 rounded-2xl border border-emerald-400/30 bg-gradient-to-r from-emerald-500/15 via-slate-900 to-cyan-500/10 p-5 shadow-xl md:flex-row md:items-center md:justify-between md:p-7">
          <div className="max-w-3xl">
            <p className="text-xs font-black uppercase tracking-[0.22em] text-emerald-300">Limited founding-owner campaign · First 500 clubs</p>
            <h2 id="first-500-founding-club-title" className="mt-2 text-2xl font-black uppercase tracking-tight text-white md:text-3xl">
              Start your club with 2,500 GTX
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-300">
              The first 500 eligible club owners receive a 2,500 GTX squad-signing grant plus 1,000 FAN for gifting. Build a minimum 22-player squad. At an average 200 GTX per player, plan for about 4,400 GTX; you can buy the balance from GTEX or verified Coin Traders during squad setup.
            </p>
            <p className="mt-2 text-xs text-slate-400">
              The launch grant is promotional, non-withdrawable and reserved for eligible player signings.
            </p>
          </div>
          <Link
            to="/signup"
            className="inline-flex shrink-0 items-center justify-center rounded-lg bg-emerald-400 px-6 py-3 text-sm font-black uppercase tracking-wider text-slate-950 transition hover:bg-emerald-300"
            data-testid="first-500-founding-club-cta"
          >
            Create your club
          </Link>
        </div>
      </section>

      {/* 3. Premium brand placement */}
      <GtexHomepageAdvertising />

      {/* 4. Clarity Strip */}
      <ClarityStrip />

      {/* 4. Platform Map Section */}
      <PlatformMapSection />

      {/* 5. Living GTEX World (Ticker & Newsroom Concept) */}
      <LivingWorldSection />

      {/* 6. Club Ownership & Simulation Life (5 Stages & Luxury Showroom) */}
      <ClubOwnershipSection />

      {/* 7. The Business of Owning a Club: TV Revenue & Financial Stories */}
      <TvFinanceSection />

      {/* 8. Regen Discovery, Development & Marketplace */}
      <RegenEconomySection />

      {/* 9. Competitions, Prize Pools & 4 Scheduled Daily Jackpots */}
      <CompetitionsJackpotSection
        initialJackpotBalance={jackpotBalance}
        initialFailsafeAt={failsafeAt}
      />

      {/* 10. Wider Football Universe (National Teams, Managers & Tribes) */}
      <WiderUniverseSection />

      {/* 11. Club Valuations, Eligible Ownership Sales & Commercial Rights */}
      <ClubValuationSection />

      {/* 12. Platform Architecture & How GTEX Works (GTC/GTX, Ledgers) */}
      <HowItWorksSection />

      {/* 13. Trust, Regulatory Compliance & Fair-Play Architecture */}
      <TrustAndIntegritySection />

      {/* 14. Conversion Pathways & Editorial Footer */}
      <ConversionAndFooterSection />
    </div>
  );
}
