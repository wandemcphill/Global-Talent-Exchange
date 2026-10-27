import React from "react";
import {
  Users,
  Layers,
  Sparkles,
  Building2,
  ArrowUpCircle,
  Coins,
  BadgeDollarSign,
  TrendingUp,
  ShieldCheck,
  CheckCircle2,
} from "lucide-react";

export const ClubValuationSection: React.FC = () => {
  const pillars = [
    {
      num: "01",
      title: "First-Team Squad",
      description: "Aggregated market reference value of all active registered senior contracts.",
      accent: "#38BDF8",
      icon: Users,
    },
    {
      num: "02",
      title: "Reserve Squad",
      description: "Second-tier squad depth and loanable squad members under active contract.",
      accent: "#36E38A",
      icon: Layers,
    },
    {
      num: "03",
      title: "U19 Squad Assets",
      description: "Competitive youth players competing in regional and continental cups.",
      accent: "#D4AF37",
      icon: Sparkles,
    },
    {
      num: "04",
      title: "Academy & Regens",
      description: "Unpromoted intake candidates evaluated on scouted potential ceiling.",
      accent: "#A855F7",
      icon: Sparkles,
    },
    {
      num: "05",
      title: "Stadium Infrastructure",
      description: "Tiered venue evaluation based on capacity, hospitality boxes, and lighting.",
      accent: "#F59E0B",
      icon: Building2,
    },
    {
      num: "06",
      title: "Paid Enhancements",
      description: "Performance campuses, medical suites, analytics labs, and fleet assets.",
      accent: "#EC4899",
      icon: Coins,
    },
  ];

  return (
    <section className="border-b border-[#22385A] bg-[#081120] py-20 sm:py-28">
      <div className="mx-auto max-w-[1440px] px-6 sm:px-12">
        {/* Section Masthead */}
        <div>
          <div className="flex items-center gap-2.5">
            <span className="h-2 w-2 rounded-full bg-[#D4AF37] shadow-[0_0_8px_#D4AF37]"></span>
            <p className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-[0.2em] text-[#D4AF37]">
              Commercial Football & Equity
            </p>
          </div>
          <h2 className="mt-3 font-['Barlow_Condensed'] text-4xl font-black uppercase tracking-tight text-[#F2F4F8] sm:text-5xl">
            Club Valuations, Eligible Sales & Sponsorships
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-[#9AA7BD] sm:text-base">
            Operate your club as a professional football enterprise. The GTEX valuation engine calculates club enterprise value using a verified six-pillar asset breakdown. Owners can list equity, trade clubs, and unlock commercial sponsorships.
          </p>
        </div>

        {/* 6-Pillar Formula Visual Panel */}
        <div className="mt-10 rounded-2xl border border-[#2F4C75] bg-[#13233A] p-6 sm:p-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="rounded bg-[#D4AF37]/15 px-3 py-1 font-['Barlow_Condensed'] text-xs font-bold uppercase text-[#D4AF37] border border-[#D4AF37]/30">
              OFFICIAL SIX-PILLAR VALUATION AUDIT
            </span>
            <span className="font-['JetBrains_Mono'] text-xs text-[#6B7A93]">
              ALGORITHM VERSION 2.0
            </span>
          </div>

          <div className="mt-4 rounded-xl border border-[#22385A] bg-[#0B1626] p-4 text-center">
            <p className="font-['Barlow_Condensed'] text-xs sm:text-sm font-black tracking-wider text-[#E8C766]">
              TOTAL CLUB VALUATION = 1st TEAM + RESERVES + U19 + ACADEMY + STADIUM + ENHANCEMENTS
            </p>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {pillars.map((pillar) => {
              const Icon = pillar.icon;
              return (
                <div
                  key={pillar.num}
                  className="rounded-xl border border-[#22385A] bg-[#0B1626]/60 p-4 transition-colors hover:border-[#2F4C75]"
                >
                  <div className="flex items-center justify-between">
                    <span
                      className="font-['JetBrains_Mono'] text-sm font-bold"
                      style={{ color: pillar.accent }}
                    >
                      {pillar.num}
                    </span>
                    <Icon size={16} style={{ color: pillar.accent }} />
                  </div>
                  <h4 className="mt-2 font-['Barlow_Condensed'] text-base font-bold uppercase text-[#F2F4F8]">
                    {pillar.title}
                  </h4>
                  <p className="mt-1 text-xs text-[#9AA7BD] leading-relaxed">
                    {pillar.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Commercial Sponsorships & Secondary Market */}
        <div className="mt-10 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Commercial Sponsorship Inventory */}
          <div className="rounded-2xl border border-[#22385A] bg-[#13233A] p-6 sm:p-8">
            <span className="rounded bg-[#38BDF8]/15 px-2.5 py-1 font-['Barlow_Condensed'] text-xs font-bold uppercase text-[#38BDF8] border border-[#38BDF8]/30">
              COMMERCIAL INVENTORY
            </span>
            <h3 className="mt-4 font-['Barlow_Condensed'] text-2xl font-bold uppercase text-[#F2F4F8]">
              Sponsorship Deals & Commercial Rights
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-[#9AA7BD]">
              Monetize club branding by unlocking real and virtual sponsorships. Front-of-shirt sponsors, LED perimeter boards, stadium naming rights, and sleeve patches contribute non-matchday income directly to your balance sheet.
            </p>

            <div className="mt-6 space-y-2.5 text-xs text-[#9AA7BD]">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={14} className="text-[#36E38A]" />
                <span>Front-of-Shirt headline brand partnerships</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 size={14} className="text-[#36E38A]" />
                <span>Stadium naming rights commercial contracts</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 size={14} className="text-[#36E38A]" />
                <span>Perimeter LED matchday broadcast impressions</span>
              </div>
            </div>
          </div>

          {/* Secondary Market */}
          <div className="rounded-2xl border border-[#22385A] bg-[#13233A] p-6 sm:p-8">
            <span className="rounded bg-[#D4AF37]/15 px-2.5 py-1 font-['Barlow_Condensed'] text-xs font-bold uppercase text-[#D4AF37] border border-[#D4AF37]/30">
              SECONDARY MARKET
            </span>
            <h3 className="mt-4 font-['Barlow_Condensed'] text-2xl font-bold uppercase text-[#F2F4F8]">
              Club Acquisitions & Ownership Liquidity
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-[#9AA7BD]">
              Eligible club owners who have developed their institutions to Established level (40+ score) can list ownership on the verified Secondary Ownership Exchange, transferring infrastructure, squad assets, and trophies to incoming owners.
            </p>

            <div className="mt-6 space-y-2.5 text-xs text-[#9AA7BD]">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={14} className="text-[#D4AF37]" />
                <span>Verified escrow settlement between owners</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 size={14} className="text-[#D4AF37]" />
                <span>All infrastructure and trophies transfer intact</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 size={14} className="text-[#D4AF37]" />
                <span>Fair-value validation band protects ecosystem integrity</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
