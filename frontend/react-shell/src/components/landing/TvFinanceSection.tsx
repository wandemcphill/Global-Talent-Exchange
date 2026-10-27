import React, { useState } from "react";
import { Tv, ShieldCheck, TrendingUp, BarChart3, HelpCircle } from "lucide-react";

interface TierFinancialBreakdown {
  tierName: string;
  chipLabel: string;
  developmentScore: string;
  tvRatePercentage: number;
  annualRevenueEstimate: string;
  tvRevenue: number;
  sponsorshipRevenue: number;
  matchdayRevenue: number;
  playerTradingRevenue: number;
  hostCutPercentage: number;
  summary: string;
}

const TIERS: TierFinancialBreakdown[] = [
  {
    tierName: "Foundation Tier",
    chipLabel: "Foundation Tier (30%)",
    developmentScore: "< 20 Pts",
    tvRatePercentage: 30,
    annualRevenueEstimate: "180,000 GTC",
    tvRevenue: 54000,
    sponsorshipRevenue: 45000,
    matchdayRevenue: 36000,
    playerTradingRevenue: 45000,
    hostCutPercentage: 40,
    summary:
      "At foundation level, 30% television shares provide initial operating capital to maintain wages and conduct academy trials.",
  },
  {
    tierName: "Growing Contender",
    chipLabel: "Growing Contender (40%)",
    developmentScore: "20–39 Pts",
    tvRatePercentage: 40,
    annualRevenueEstimate: "520,000 GTC",
    tvRevenue: 208000,
    sponsorshipRevenue: 130000,
    matchdayRevenue: 78000,
    playerTradingRevenue: 104000,
    hostCutPercentage: 40,
    summary:
      "With 40% TV share and regional sponsors, contenders reinvest broadcast income into hybrid training pitches and sports science.",
  },
  {
    tierName: "Established Club",
    chipLabel: "Established Club (50%)",
    developmentScore: "40–59 Pts",
    tvRatePercentage: 50,
    annualRevenueEstimate: "1,650,000 GTC",
    tvRevenue: 825000,
    sponsorshipRevenue: 412500,
    matchdayRevenue: 165000,
    playerTradingRevenue: 247500,
    hostCutPercentage: 40,
    summary:
      "At 50% TV share, broadcast cashflows match commercial partnerships, financing top-tier manager appointments and stadium maintenance.",
  },
  {
    tierName: "Elite Contender",
    chipLabel: "Elite Contender (60%)",
    developmentScore: "60–79 Pts",
    tvRatePercentage: 60,
    annualRevenueEstimate: "5,400,000 GTC",
    tvRevenue: 3240000,
    sponsorshipRevenue: 1080000,
    matchdayRevenue: 432000,
    playerTradingRevenue: 648000,
    hostCutPercentage: 40,
    summary:
      "Elite clubs capture 60% TV distribution across continental cups, funding Apex Campus upgrades and Vanguard XII team coaches.",
  },
  {
    tierName: "Legacy Institution",
    chipLabel: "Legacy Institution (70%)",
    developmentScore: "80+ Pts",
    tvRatePercentage: 70,
    annualRevenueEstimate: "18,500,000 GTC",
    tvRevenue: 12950000,
    sponsorshipRevenue: 2775000,
    matchdayRevenue: 1110000,
    playerTradingRevenue: 1665000,
    hostCutPercentage: 40,
    summary:
      "Legacy giants retain 70% of broadcast distributions. Broadcast revenue powers global scouting satellites and Sovereign 900X aviation.",
  },
];

export const TvFinanceSection: React.FC = () => {
  // Default to Established Club (index 2) as in Flutter
  const [selectedTierIndex, setSelectedTierIndex] = useState<number>(2);
  const activeTier = TIERS[selectedTierIndex];

  const totalRev =
    activeTier.tvRevenue +
    activeTier.sponsorshipRevenue +
    activeTier.matchdayRevenue +
    activeTier.playerTradingRevenue;

  const tvPct = Math.round((activeTier.tvRevenue / totalRev) * 100);
  const spPct = Math.round((activeTier.sponsorshipRevenue / totalRev) * 100);
  const mdPct = Math.round((activeTier.matchdayRevenue / totalRev) * 100);
  const trPct = 100 - (tvPct + spPct + mdPct);

  return (
    <section id="finance" className="border-b border-[#22385A] bg-[#081120] py-20 sm:py-28">
      <div className="mx-auto max-w-[1440px] px-6 sm:px-12">
        {/* Section Masthead */}
        <div>
          <div className="flex items-center gap-2.5">
            <span className="h-2 w-2 rounded-full bg-[#36E38A] shadow-[0_0_8px_#36E38A]"></span>
            <p className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-[0.2em] text-[#36E38A]">
              The Business of Owning a Club
            </p>
          </div>
          <h2 className="mt-3 font-['Barlow_Condensed'] text-4xl font-black uppercase tracking-tight text-[#F2F4F8] sm:text-5xl">
            Television Revenue & Club Financial Engine
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-[#9AA7BD] sm:text-base">
            Broadcast rights are not an afterthought — they are the economic core of GTEX club ownership. Clubs capture progressively higher television distribution percentages as their development stage expands, funding facilities, squad payroll, and global ambition.
          </p>
        </div>

        {/* Verified Distribution Formula Callout */}
        <div className="mt-10 rounded-2xl border border-emerald-500/30 bg-[#13233A] p-6 shadow-xl">
          <div className="flex items-center gap-2">
            <ShieldCheck size={20} className="text-[#36E38A]" />
            <span className="font-['Barlow_Condensed'] text-sm font-extrabold uppercase tracking-wider text-[#36E38A]">
              VERIFIED GTEX TELEVISION DISTRIBUTION FORMULA
            </span>
          </div>

          <p className="mt-3 text-sm leading-relaxed text-[#F2F4F8]">
            GTEX broadcast revenue is governed by authoritative platform contracts. Foundation clubs retain 30% of television income, scaling to 40% (Growing), 50% (Established), 60% (Elite), and 70% (Legacy). In tournament fixtures, the host club receives 40% of the clubs' pool, and participants share the remaining 60%, with the platform retaining the balance.
          </p>

          <div className="mt-4 flex flex-wrap gap-2">
            {[
              { label: "Foundation: 30% TV Cut", color: "#6B7A93" },
              { label: "Growing: 40% TV Cut", color: "#3B82F6" },
              { label: "Established: 50% TV Cut", color: "#10B981" },
              { label: "Elite: 60% TV Cut", color: "#8B5CF6" },
              { label: "Legacy: 70% TV Cut", color: "#D4AF37" },
            ].map((pill) => (
              <span
                key={pill.label}
                className="rounded-full px-3 py-1 font-['JetBrains_Mono'] text-xs font-bold"
                style={{
                  color: pill.color,
                  backgroundColor: `${pill.color}15`,
                  border: `1px solid ${pill.color}40`,
                }}
              >
                {pill.label}
              </span>
            ))}
          </div>
        </div>

        {/* Interactive Breakdown Simulator */}
        <div className="mt-14">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#22385A] pb-4">
            <div className="flex items-center gap-2">
              <BarChart3 size={20} className="text-[#D4AF37]" />
              <h3 className="font-['Barlow_Condensed'] text-base font-extrabold uppercase tracking-widest text-[#D4AF37]">
                INTERACTIVE CLUB REVENUE BREAKDOWN
              </h3>
            </div>
            <span className="text-xs text-[#6B7A93]">
              Based on active tier calculations
            </span>
          </div>

          {/* Tier Selector Chips */}
          <div className="mt-6 flex flex-wrap gap-2">
            {TIERS.map((tier, idx) => {
              const isSelected = idx === selectedTierIndex;
              return (
                <button
                  key={tier.tierName}
                  onClick={() => setSelectedTierIndex(idx)}
                  className={`rounded-xl border px-4 py-2.5 font-['Barlow_Condensed'] text-sm font-bold uppercase tracking-wider transition-all ${
                    isSelected
                      ? "border-[#36E38A] bg-emerald-500/20 text-[#36E38A] shadow-[0_0_16px_rgba(54,227,138,0.2)]"
                      : "border-[#22385A] bg-[#13233A] text-[#9AA7BD] hover:border-[#2F4C75]"
                  }`}
                >
                  {tier.chipLabel}
                </button>
              );
            })}
          </div>

          {/* Financial Breakdown Panel */}
          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-12">
            {/* Turnover Summary Card */}
            <div className="rounded-2xl border border-[#22385A] bg-[#13233A] p-6 lg:col-span-4">
              <span className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-wider text-[#6B7A93]">
                INDICATIVE ANNUAL TURNOVER
              </span>
              <p className="mt-2 font-['JetBrains_Mono'] text-3xl font-black text-[#D4AF37]">
                {activeTier.annualRevenueEstimate}
              </p>
              <div className="mt-3 flex items-center gap-2">
                <span className="rounded bg-emerald-500/20 px-2 py-0.5 font-['JetBrains_Mono'] text-xs font-bold text-[#36E38A]">
                  {activeTier.tvRatePercentage}% TV Rate
                </span>
                <span className="rounded bg-[#0B1626] px-2 py-0.5 text-xs text-[#9AA7BD]">
                  Score: {activeTier.developmentScore}
                </span>
              </div>
              <p className="mt-4 text-xs leading-relaxed text-[#9AA7BD]">
                {activeTier.summary}
              </p>
            </div>

            {/* Income Streams Progress Visual */}
            <div className="rounded-2xl border border-[#22385A] bg-[#13233A] p-6 lg:col-span-8">
              <span className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-wider text-[#6B7A93]">
                ANNUAL REVENUE STREAMS
              </span>

              {/* Stacked Progress Bar */}
              <div className="mt-3 flex h-4 w-full overflow-hidden rounded-full bg-[#0B1626]">
                <div style={{ width: `${tvPct}%` }} className="bg-[#36E38A]" title={`TV: ${tvPct}%`}></div>
                <div style={{ width: `${spPct}%` }} className="bg-[#38BDF8]" title={`Sponsorship: ${spPct}%`}></div>
                <div style={{ width: `${mdPct}%` }} className="bg-[#D4AF37]" title={`Matchday: ${mdPct}%`}></div>
                <div style={{ width: `${trPct}%` }} className="bg-[#A855F7]" title={`Trading: ${trPct}%`}></div>
              </div>

              <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="rounded-lg border border-[#22385A] bg-[#0B1626]/60 p-3">
                  <div className="flex items-center gap-1.5 text-xs text-[#36E38A]">
                    <span className="h-2 w-2 rounded-full bg-[#36E38A]"></span>
                    <span>TV Broadcast ({tvPct}%)</span>
                  </div>
                  <p className="mt-1 font-['JetBrains_Mono'] text-sm font-bold text-[#F2F4F8]">
                    {activeTier.tvRevenue.toLocaleString()} GTC
                  </p>
                </div>

                <div className="rounded-lg border border-[#22385A] bg-[#0B1626]/60 p-3">
                  <div className="flex items-center gap-1.5 text-xs text-[#38BDF8]">
                    <span className="h-2 w-2 rounded-full bg-[#38BDF8]"></span>
                    <span>Sponsors ({spPct}%)</span>
                  </div>
                  <p className="mt-1 font-['JetBrains_Mono'] text-sm font-bold text-[#F2F4F8]">
                    {activeTier.sponsorshipRevenue.toLocaleString()} GTC
                  </p>
                </div>

                <div className="rounded-lg border border-[#22385A] bg-[#0B1626]/60 p-3">
                  <div className="flex items-center gap-1.5 text-xs text-[#D4AF37]">
                    <span className="h-2 w-2 rounded-full bg-[#D4AF37]"></span>
                    <span>Matchday ({mdPct}%)</span>
                  </div>
                  <p className="mt-1 font-['JetBrains_Mono'] text-sm font-bold text-[#F2F4F8]">
                    {activeTier.matchdayRevenue.toLocaleString()} GTC
                  </p>
                </div>

                <div className="rounded-lg border border-[#22385A] bg-[#0B1626]/60 p-3">
                  <div className="flex items-center gap-1.5 text-xs text-[#A855F7]">
                    <span className="h-2 w-2 rounded-full bg-[#A855F7]"></span>
                    <span>Trading ({trPct}%)</span>
                  </div>
                  <p className="mt-1 font-['JetBrains_Mono'] text-sm font-bold text-[#F2F4F8]">
                    {activeTier.playerTradingRevenue.toLocaleString()} GTC
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
