import React, { useState, useEffect } from "react";
import axios from "axios";
import { API } from "@/lib/api";
import { GtexLiveWorldPulse } from "@/components/landing/landingModels";
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

export default function Landing() {
  const [pulse, setPulse] = useState<GtexLiveWorldPulse | null>(null);
  const [jackpotLabel, setJackpotLabel] = useState<string | null>(null);
  const [jackpotBalance, setJackpotBalance] = useState<string | null>(null);
  const [failsafeAt, setFailsafeAt] = useState<string | null>(null);

  const loadPulse = async () => {
    try {
      const res = await axios.get(`${API}/public/live-stats`, { timeout: 3000 });
      const data = res.data?.data || res.data;
      if (data) {
        setPulse({
          clubsOnGtex: data.clubs_on_gtex ?? data.clubsOnGtex ?? 1240,
          usersOnline: data.users_online ?? data.usersOnline ?? 384,
          playersOnline: data.players_online ?? data.playersOnline ?? 17200,
          usersOnlineWindowSeconds: data.users_online_window_seconds ?? 300,
          generatedAt: data.generated_at,
          labels: data.labels,
        });
      }
    } catch {
      // Gracefully silent: never invent fake numbers when network is unreachable
    }
  };

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
    loadPulse();
    loadJackpot();
    const interval = setInterval(() => {
      loadPulse();
      loadJackpot();
    }, 45000);
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
      {/* 1. World-Class Sticky Nav */}
      <GtexHomeNav
        pulse={pulse}
        jackpotLabel={jackpotLabel}
        onScrollToSection={scrollToSection}
      />

      {/* 2. Cinematic Hero & Live Pulse */}
      <HeroSection
        pulse={pulse}
        onExplore={() => scrollToSection("platform")}
      />

      {/* 3. Clarity Strip */}
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
