import React from "react";
import { CheckCircle2, ShieldAlert } from "lucide-react";

export const HowItWorksSection: React.FC = () => {
  const ledgers = [
    {
      title: "Sporting Operations",
      subtitle: "GTC & FNC Ledgers",
      description:
        "Powering on-pitch sporting operations. GTC credits fund player contracts, youth scouting, and transfer fees. FNC coins power matchday fan engagement.",
      badge: "SPORTING LEDGER",
      badgeColor: "#38BDF8",
      points: [
        "GTC Credits for player market trading",
        "FNC Fan Coins for matchday votes",
        "In-game simulation assets",
      ],
    },
    {
      title: "Boardroom Capital",
      subtitle: "GTX & FAN Tokens",
      description:
        "Powers executive owner decisions. GTX funds facility upgrades, Apex Performance Campus construction, Sovereign 900X aviation, and showroom luxury purchases.",
      badge: "EXECUTIVE LEDGER",
      badgeColor: "#D4AF37",
      points: [
        "GTX for luxury asset acquisitions",
        "Prestige point bonuses on purchase",
        "Sister-club capital transfers",
      ],
    },
    {
      title: "Real-Money Transactions",
      subtitle: "Deposits & Withdrawals",
      description:
        "Regulated fiat gateways and withdrawable balances. Gated by strict KYC Tier 2 verification, 48-hour risk-ops review, and anti-collusion fraud prevention.",
      badge: "COMPLIANCE GATE",
      badgeColor: "#36E38A",
      points: [
        "Mandatory KYC Tier 2 identity checks",
        "48-hour risk-ops settlement buffer",
        "Clear virtual vs cash boundaries",
      ],
    },
  ];

  return (
    <section className="border-b border-[#22385A] bg-[#0B1626] py-20 sm:py-28">
      <div className="mx-auto max-w-[1440px] px-6 sm:px-12">
        {/* Section Masthead */}
        <div>
          <div className="flex items-center gap-2.5">
            <span className="h-2 w-2 rounded-full bg-[#38BDF8] shadow-[0_0_8px_#38BDF8]"></span>
            <p className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-[0.2em] text-[#38BDF8]">
              Platform Architecture & Mechanics
            </p>
          </div>
          <h2 className="mt-3 font-['Barlow_Condensed'] text-4xl font-black uppercase tracking-tight text-[#F2F4F8] sm:text-5xl">
            How GTEX Works: Currencies, Ledgers & Withdrawals
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-[#9AA7BD] sm:text-base">
            GTEX maintains complete institutional clarity between in-game sporting assets, executive owner capital, and real-money financial transactions.
          </p>
        </div>

        {/* 3 Ledgers Grid */}
        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
          {ledgers.map((l) => (
            <div
              key={l.badge}
              className="flex flex-col justify-between rounded-2xl border border-[#22385A] bg-[#13233A] p-6 sm:p-8"
            >
              <div>
                <span
                  className="rounded px-2.5 py-1 font-['Barlow_Condensed'] text-xs font-bold uppercase"
                  style={{
                    color: l.badgeColor,
                    backgroundColor: `${l.badgeColor}15`,
                    border: `1px solid ${l.badgeColor}30`,
                  }}
                >
                  {l.badge}
                </span>

                <h3 className="mt-4 font-['Barlow_Condensed'] text-2xl font-bold uppercase text-[#F2F4F8]">
                  {l.title}
                </h3>
                <p
                  className="font-['JetBrains_Mono'] text-xs font-semibold"
                  style={{ color: l.badgeColor }}
                >
                  {l.subtitle}
                </p>

                <p className="mt-3 text-xs leading-relaxed text-[#9AA7BD]">
                  {l.description}
                </p>
              </div>

              <div className="mt-6 space-y-2 border-t border-[#22385A] pt-4 text-xs text-[#9AA7BD]">
                {l.points.map((pt, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <CheckCircle2 size={13} style={{ color: l.badgeColor }} />
                    <span>{pt}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
