import React from "react";
import { Flag, Brain, Users, Award, TrendingUp, Shield, Flame } from "lucide-react";

export const WiderUniverseSection: React.FC = () => {
  return (
    <section id="universe" className="border-b border-[#22385A] bg-[#0B1626] py-20 sm:py-28">
      <div className="mx-auto max-w-[1440px] px-6 sm:px-12">
        {/* Section Masthead */}
        <div>
          <div className="flex items-center gap-2.5">
            <span className="h-2 w-2 rounded-full bg-[#38BDF8] shadow-[0_0_8px_#38BDF8]"></span>
            <p className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-[0.2em] text-[#38BDF8]">
              The Wider Football Universe
            </p>
          </div>
          <h2 className="mt-3 font-['Barlow_Condensed'] text-4xl font-black uppercase tracking-tight text-[#F2F4F8] sm:text-5xl">
            National Federation Rentals, Tacticians & Living Culture
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-[#9AA7BD] sm:text-base">
            The GTEX football universe is alive 24/7 even when you are away from the dugout. Lease your star regens to national teams for international glory, appoint renowned tacticians, and join fervent fan tribes.
          </p>
        </div>

        {/* 3 Universe Cards */}
        <div className="mt-12 grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Rentals Card */}
          <div className="flex flex-col justify-between rounded-2xl border border-[#22385A] bg-[#13233A] p-6 sm:p-8">
            <div>
              <span className="flex w-fit items-center gap-1.5 rounded bg-[#38BDF8]/15 px-2.5 py-1 font-['Barlow_Condensed'] text-xs font-bold uppercase text-[#38BDF8] border border-[#38BDF8]/30">
                <Flag size={13} />
                NATIONAL TEAM RENTALS
              </span>

              <h3 className="mt-4 font-['Barlow_Condensed'] text-2xl font-bold uppercase text-[#F2F4F8]">
                International Tournament Call-Ups
              </h3>
              <p className="mt-2 text-xs leading-relaxed text-[#9AA7BD]">
                National federations rent eligible domestic and regen superstars for international tournament campaigns. Owners collect verified rental fees while their players earn caps, prestige, and tournament medals.
              </p>
            </div>

            <div className="mt-6 space-y-2 rounded-xl border border-[#22385A] bg-[#0B1626]/70 p-4 text-xs text-[#9AA7BD]">
              <div className="flex items-center gap-2">
                <Award size={14} className="text-[#36E38A]" />
                <span>Direct rental fee credited to owner ledger</span>
              </div>
              <div className="flex items-center gap-2">
                <TrendingUp size={14} className="text-[#38BDF8]" />
                <span>+15% Big-Match Composure on return</span>
              </div>
              <div className="flex items-center gap-2">
                <Shield size={14} className="text-[#D4AF37]" />
                <span>Player global valuation rises with international caps</span>
              </div>
            </div>
          </div>

          {/* Manager Marketplace Card */}
          <div className="flex flex-col justify-between rounded-2xl border border-[#22385A] bg-[#13233A] p-6 sm:p-8">
            <div>
              <span className="flex w-fit items-center gap-1.5 rounded bg-[#D4AF37]/15 px-2.5 py-1 font-['Barlow_Condensed'] text-xs font-bold uppercase text-[#D4AF37] border border-[#D4AF37]/30">
                <Brain size={13} />
                TACTICAL PHILOSOPHIES
              </span>

              <h3 className="mt-4 font-['Barlow_Condensed'] text-2xl font-bold uppercase text-[#F2F4F8]">
                Elite Manager Marketplace
              </h3>
              <p className="mt-2 text-xs leading-relaxed text-[#9AA7BD]">
                Appoint tacticians with distinct doctrines: Gegenpress, Tiki-taka, Low-Block Counter, and Direct Possession. Tactical styles govern spatial simulation behaviors and unlock customized set-piece variants.
              </p>
            </div>

            <div className="mt-6 space-y-2 rounded-xl border border-[#22385A] bg-[#0B1626]/70 p-4 text-xs text-[#9AA7BD]">
              <div className="flex items-center gap-2">
                <Flame size={14} className="text-[#D4AF37]" />
                <span>Gegenpress: +12% high-turnover recoveries</span>
              </div>
              <div className="flex items-center gap-2">
                <TrendingUp size={14} className="text-[#36E38A]" />
                <span>Tiki-taka: +18% sustained matchday ball possession</span>
              </div>
              <div className="flex items-center gap-2">
                <Shield size={14} className="text-[#38BDF8]" />
                <span>Low-Block: 40% reduction in counter-attack concessions</span>
              </div>
            </div>
          </div>

          {/* Living Fan Culture */}
          <div className="flex flex-col justify-between rounded-2xl border border-[#22385A] bg-[#13233A] p-6 sm:p-8">
            <div>
              <span className="flex w-fit items-center gap-1.5 rounded bg-[#36E38A]/15 px-2.5 py-1 font-['Barlow_Condensed'] text-xs font-bold uppercase text-[#36E38A] border border-[#36E38A]/30">
                <Users size={13} />
                COMMUNITY PASSION
              </span>

              <h3 className="mt-4 font-['Barlow_Condensed'] text-2xl font-bold uppercase text-[#F2F4F8]">
                Fan Tribes & Matchday Wars
              </h3>
              <p className="mt-2 text-xs leading-relaxed text-[#9AA7BD]">
                Football is powered by fans. Engage in weekly Fan Wars, gift virtual scarves and flares to your favorite clubs, and rally supporter units to boost matchday home advantage.
              </p>
            </div>

            <div className="mt-6 space-y-2 rounded-xl border border-[#22385A] bg-[#0B1626]/70 p-4 text-xs text-[#9AA7BD]">
              <div className="flex items-center gap-2">
                <Flame size={14} className="text-[#36E38A]" />
                <span>10% stadium atmosphere boost for high tribe activity</span>
              </div>
              <div className="flex items-center gap-2">
                <Award size={14} className="text-[#D4AF37]" />
                <span>Non-withdrawable FNC Fan Coin gifting economy</span>
              </div>
              <div className="flex items-center gap-2">
                <Users size={14} className="text-[#38BDF8]" />
                <span>Club supporter leaderboards and exclusive insignia</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
