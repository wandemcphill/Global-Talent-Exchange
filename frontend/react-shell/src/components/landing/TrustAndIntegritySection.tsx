import React from "react";
import { Shield, ShieldAlert, CheckCircle2, FileText, Lock } from "lucide-react";

export const TrustAndIntegritySection: React.FC = () => {
  const cards = [
    {
      title: "Authoritative Spatial Match Engine",
      description:
        "All matches run on deterministic server simulation authority. Player physics, spatial coordinates, referee decisions, and scoreline results are cryptographically verified and cannot be manipulated on client devices.",
      tag: "DETERMINISTIC SIMULATION",
      accent: "#36E38A",
      icon: Shield,
    },
    {
      title: "Surveillance & Anti-Collusion Engine",
      description:
        "Automated risk-ops algorithms monitor transfer marketplace activity, match results, and coin trading orders. Unusual pricing spikes or suspicious multi-account collusion trigger immediate review freezes.",
      tag: "REAL-TIME SURVEILLANCE",
      accent: "#38BDF8",
      icon: Lock,
    },
    {
      title: "KYC Tier 2 & AML Regulatory Verification",
      description:
        "Real-money deposits and withdrawals require mandatory government-issued ID identity verification, address proof, and automated sanctions screening before funds can be released.",
      tag: "KYC COMPLIANCE",
      accent: "#D4AF37",
      icon: CheckCircle2,
    },
    {
      title: "Transparent Economic Disclosures",
      description:
        "GTEX strictly distinguishes virtual sporting value from withdrawable cash. Television revenues and tournament prizes are awarded based on actual platform results and active rules; earnings are never guaranteed.",
      tag: "LEGAL ACCURACY",
      accent: "#A855F7",
      icon: FileText,
    },
  ];

  return (
    <section id="trust" className="border-b border-[#22385A] bg-[#081120] py-20 sm:py-28">
      <div className="mx-auto max-w-[1440px] px-6 sm:px-12">
        {/* Section Masthead */}
        <div>
          <div className="flex items-center gap-2.5">
            <span className="h-2 w-2 rounded-full bg-[#36E38A] shadow-[0_0_8px_#36E38A]"></span>
            <p className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-[0.2em] text-[#36E38A]">
              Integrity, Compliance & Security
            </p>
          </div>
          <h2 className="mt-3 font-['Barlow_Condensed'] text-4xl font-black uppercase tracking-tight text-[#F2F4F8] sm:text-5xl">
            Institutional Trust & Competitive Integrity
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-[#9AA7BD] sm:text-base">
            GTEX operates under strict regulatory, mathematical, and sporting integrity standards. All match outcomes, jackpot distributions, and financial settlements are governed by verifiable server-authoritative code.
          </p>
        </div>

        {/* 4 Trust Cards Grid */}
        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-2">
          {cards.map((c) => {
            const Icon = c.icon;
            return (
              <div
                key={c.title}
                className="flex flex-col justify-between rounded-2xl border border-[#22385A] bg-[#13233A] p-6 sm:p-8 transition-colors hover:border-[#2F4C75]"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <Icon size={18} style={{ color: c.accent }} />
                    <span
                      className="rounded px-2.5 py-0.5 font-['Barlow_Condensed'] text-xs font-bold uppercase"
                      style={{
                        color: c.accent,
                        backgroundColor: `${c.accent}15`,
                        border: `1px solid ${c.accent}30`,
                      }}
                    >
                      {c.tag}
                    </span>
                  </div>

                  <h3 className="mt-4 font-['Barlow_Condensed'] text-2xl font-bold uppercase text-[#F2F4F8]">
                    {c.title}
                  </h3>
                  <p className="mt-2 text-xs leading-relaxed text-[#9AA7BD]">
                    {c.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
