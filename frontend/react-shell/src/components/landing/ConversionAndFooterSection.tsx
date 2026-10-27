import React from "react";
import { Link } from "react-router-dom";
import { Building2, UserSearch, Users, ArrowRight, ShieldCheck } from "lucide-react";

export const ConversionAndFooterSection: React.FC = () => {
  return (
    <div className="bg-[#0B1626]">
      {/* Final Conversion Banner */}
      <section className="px-6 py-20 sm:px-12 sm:py-28">
        <div className="mx-auto max-w-[1440px] rounded-3xl border border-[#D4AF37]/40 bg-gradient-to-br from-[#13233A] via-[#0F1E33] to-[#0B1626] p-8 sm:p-14 shadow-[0_8px_40px_rgba(212,175,55,0.08)]">
          <div className="text-center">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[#D4AF37]/40 bg-[#D4AF37]/15 px-3 py-1 font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-wider text-[#D4AF37]">
              YOUR LEGACY BEGINS NOW
            </span>

            <h2 className="mt-4 font-['Barlow_Condensed'] text-4xl font-black uppercase tracking-tight text-[#F2F4F8] sm:text-6xl">
              Step Onto the Pitch in 2027.
            </h2>

            <p className="mx-auto mt-3 max-w-2xl text-sm leading-relaxed text-[#9AA7BD] sm:text-base">
              Whether you aspire to build an institutional football dynasty, scout the next generation of regens, or compete for the four scheduled daily jackpots — GTEX is your stage.
            </p>
          </div>

          {/* 3 Audience Pathways */}
          <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
            {/* Club Owner */}
            <div className="flex flex-col justify-between rounded-2xl border border-[#22385A] bg-[#0B1626]/80 p-6 transition-all hover:border-[#D4AF37]/50">
              <div>
                <div className="flex items-center gap-2">
                  <Building2 size={18} className="text-[#D4AF37]" />
                  <span className="font-['Barlow_Condensed'] text-xs font-extrabold uppercase tracking-wider text-[#D4AF37]">
                    CLUB OWNER
                  </span>
                </div>
                <h3 className="mt-3 font-['Barlow_Condensed'] text-2xl font-bold uppercase text-[#F2F4F8]">
                  Found a Football Club
                </h3>
                <p className="mt-2 text-xs leading-relaxed text-[#9AA7BD]">
                  Own up to 3 clubs, build Arena facilities, capture TV money, and unlock VIP jets.
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-[#22385A]">
                <Link
                  to="/signup"
                  data-testid="landing-footer-cta"
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#D4AF37] py-2.5 font-['Barlow_Condensed'] text-sm font-extrabold uppercase tracking-wider text-[#0B1626] transition-colors hover:bg-[#E8C766]"
                >
                  <span>Found Your Club</span>
                  <ArrowRight size={14} />
                </Link>
              </div>
            </div>

            {/* Talent Scout & Trader */}
            <div className="flex flex-col justify-between rounded-2xl border border-[#22385A] bg-[#0B1626]/80 p-6 transition-all hover:border-[#38BDF8]/50">
              <div>
                <div className="flex items-center gap-2">
                  <UserSearch size={18} className="text-[#38BDF8]" />
                  <span className="font-['Barlow_Condensed'] text-xs font-extrabold uppercase tracking-wider text-[#38BDF8]">
                    TALENT SCOUT & TRADER
                  </span>
                </div>
                <h3 className="mt-3 font-['Barlow_Condensed'] text-2xl font-bold uppercase text-[#F2F4F8]">
                  Enter the Player Exchange
                </h3>
                <p className="mt-2 text-xs leading-relaxed text-[#9AA7BD]">
                  Scout 17,000+ players, recruit breakout regens, and negotiate high-value transfers.
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-[#22385A]">
                <Link
                  to="/signup?role=trader"
                  className="flex w-full items-center justify-center gap-2 rounded-lg border border-[#38BDF8] bg-[#38BDF8]/15 py-2.5 font-['Barlow_Condensed'] text-sm font-extrabold uppercase tracking-wider text-[#38BDF8] transition-colors hover:bg-[#38BDF8]/25"
                >
                  <span>Start Scouting</span>
                  <ArrowRight size={14} />
                </Link>
              </div>
            </div>

            {/* Creator & Fan */}
            <div className="flex flex-col justify-between rounded-2xl border border-[#22385A] bg-[#0B1626]/80 p-6 transition-all hover:border-[#36E38A]/50">
              <div>
                <div className="flex items-center gap-2">
                  <Users size={18} className="text-[#36E38A]" />
                  <span className="font-['Barlow_Condensed'] text-xs font-extrabold uppercase tracking-wider text-[#36E38A]">
                    CREATOR & FAN
                  </span>
                </div>
                <h3 className="mt-3 font-['Barlow_Condensed'] text-2xl font-bold uppercase text-[#F2F4F8]">
                  Join Fan Tribes & Tournaments
                </h3>
                <p className="mt-2 text-xs leading-relaxed text-[#9AA7BD]">
                  Wage matchday Fan Wars, back your clubs, and compete for 4 daily jackpot drops.
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-[#22385A]">
                <Link
                  to="/signup?role=creator"
                  className="flex w-full items-center justify-center gap-2 rounded-lg border border-[#36E38A] bg-[#36E38A]/15 py-2.5 font-['Barlow_Condensed'] text-sm font-extrabold uppercase tracking-wider text-[#36E38A] transition-colors hover:bg-[#36E38A]/25"
                >
                  <span>Join the Universe</span>
                  <ArrowRight size={14} />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Editorial Footer */}
      <footer className="border-t border-[#22385A] py-12 px-6 sm:px-12 text-[#9AA7BD]">
        <div className="mx-auto max-w-[1440px]">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-['Barlow_Condensed'] text-2xl font-black tracking-widest text-[#F2F4F8]">
                  GTEX
                </span>
                <span className="rounded bg-[#D4AF37]/20 px-2 py-0.5 font-['Barlow_Condensed'] text-xs font-bold text-[#D4AF37]">
                  2027
                </span>
              </div>
              <p className="mt-1 text-xs text-[#6B7A93]">
                The Living Football Universe • 2027 Edition
              </p>
            </div>

            <div className="flex flex-wrap gap-6 text-xs font-semibold uppercase tracking-wider text-[#9AA7BD]">
              <a href="#hero" className="hover:text-white">Universe</a>
              <a href="#ownership" className="hover:text-white">Clubs</a>
              <a href="#finance" className="hover:text-white">Broadcast Rights</a>
              <a href="#regens" className="hover:text-white">Regens</a>
              <a href="#competitions" className="hover:text-white">Jackpot Drops</a>
              <a href="#trust" className="hover:text-white">Compliance</a>
            </div>
          </div>

          <div className="mt-8 border-t border-[#22385A]/50 pt-8 text-[11px] leading-relaxed text-[#6B7A93]">
            <p>
              GTEX operates a simulated football universe. Sporting assets, development scores, and player values reflect in-game performance mechanics and do not constitute external securities or speculative investment contracts. Withdrawals require Tier 2 KYC and are subject to regulatory thresholds and anti-collusion fraud reviews.
            </p>
            <p className="mt-2">
              © {new Date().getFullYear()} GTEX · Global Talent Exchange. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};
