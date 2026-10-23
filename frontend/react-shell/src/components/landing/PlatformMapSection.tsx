import React from "react";
import { Link } from "react-router-dom";
import {
  UserSearch,
  Building2,
  LineChart,
  Trophy,
  Wallet,
  MessageSquare,
  ArrowRight,
} from "lucide-react";

export const PlatformMapSection: React.FC = () => {
  const pillars = [
    {
      id: "ownership",
      title: "Club Ownership",
      body: "Build a club identity, manage your squad, shape its legacy and compete.",
      icon: Building2,
      accent: "#36E38A",
      featured: true,
      tag: "THE CORE EXPERIENCE",
    },
    {
      id: "talent",
      title: "Talent Exchange",
      body: "Find players, compare profiles, track value and move talent across the world.",
      icon: UserSearch,
      accent: "#38BDF8",
      featured: false,
      tag: "MARKETPLACE",
    },
    {
      id: "intelligence",
      title: "Football Intelligence",
      body: "Player data, scouting signals, performance, reports and market context.",
      icon: LineChart,
      accent: "#38BDF8",
      featured: false,
      tag: "ANALYTICS",
    },
    {
      id: "matches",
      title: "Matches & Competitions",
      body: "Live matchday, leagues, tournaments, awards and progression.",
      icon: Trophy,
      accent: "#D4AF37",
      featured: false,
      tag: "COMPETITION",
    },
    {
      id: "economy",
      title: "Wallet & Economy",
      body: "Wallet funding, P2P activity, withdrawals and football commerce.",
      icon: Wallet,
      accent: "#E8C766",
      featured: false,
      tag: "DUAL LEDGER",
    },
    {
      id: "social",
      title: "Social Football",
      body: "Creators, fans, news, Fan Wars, gifting and a living community.",
      icon: MessageSquare,
      accent: "#22C55E",
      featured: false,
      tag: "COMMUNITY",
    },
  ];

  return (
    <section id="platform" className="border-b border-[#22385A] bg-[#081120] py-20 sm:py-28">
      <div className="mx-auto max-w-[1440px] px-6 sm:px-12">
        {/* Eyebrow */}
        <p className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-[0.2em] text-[#36E38A]">
          ONE PLATFORM. MANY WAYS TO PLAY.
        </p>

        {/* Heading */}
        <h2 className="mt-3 font-['Barlow_Condensed'] text-4xl font-black uppercase tracking-tight text-[#F2F4F8] sm:text-6xl">
          Everything football.
          <br />
          One living system.
        </h2>

        {/* Subhead */}
        <p className="mt-4 max-w-2xl text-base text-[#9AA7BD]">
          GTEX brings talent, clubs, markets, matches, money and community into one connected
          football ecosystem.
        </p>

        {/* Feature Grid */}
        <div className="mt-12 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          {pillars.map((pillar) => {
            const Icon = pillar.icon;
            return (
              <div
                key={pillar.id}
                className={`group relative flex flex-col justify-between rounded-xl border p-6 transition-all duration-300 ${
                  pillar.featured
                    ? "border-emerald-500/40 bg-gradient-to-br from-[#13233A] to-[#0E1C30] md:col-span-2 lg:col-span-1 shadow-[0_4px_24px_rgba(54,227,138,0.08)]"
                    : "border-[#22385A] bg-[#13233A]/70 hover:border-[#D4AF37]/50 hover:bg-[#13233A]"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <div
                      className="flex h-12 w-12 items-center justify-center rounded-lg"
                      style={{ backgroundColor: `${pillar.accent}15` }}
                    >
                      <Icon size={24} style={{ color: pillar.accent }} />
                    </div>
                    <span
                      className="rounded px-2 py-0.5 font-['JetBrains_Mono'] text-[10px] font-bold uppercase tracking-wider"
                      style={{
                        color: pillar.accent,
                        backgroundColor: `${pillar.accent}15`,
                        border: `1px solid ${pillar.accent}30`,
                      }}
                    >
                      {pillar.tag}
                    </span>
                  </div>

                  <h3 className="mt-5 font-['Barlow_Condensed'] text-2xl font-bold uppercase text-[#F2F4F8]">
                    {pillar.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-[#9AA7BD]">{pillar.body}</p>
                </div>

                <div className="mt-6 pt-4 border-t border-[#22385A]/50">
                  <div className="flex items-center text-xs font-bold uppercase tracking-wider text-[#9AA7BD] group-hover:text-white">
                    <span>Explore pillar</span>
                    <ArrowRight
                      size={14}
                      className="ml-1.5 transition-transform group-hover:translate-x-1"
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* CTA */}
        <div className="mt-10">
          <Link
            to="/signup"
            className="inline-flex items-center gap-2 rounded-lg border border-[#22385A] bg-[#13233A] px-6 py-3 font-['Barlow_Condensed'] text-sm font-bold uppercase tracking-wider text-[#F2F4F8] transition-colors hover:border-[#D4AF37] hover:bg-[#1A2E4A]"
          >
            <span>Start your GTEX story</span>
            <ArrowRight size={16} className="text-[#D4AF37]" />
          </Link>
        </div>
      </div>
    </section>
  );
};
