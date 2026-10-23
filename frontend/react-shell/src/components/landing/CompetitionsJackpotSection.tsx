import React, { useState, useEffect } from "react";
import {
  Trophy,
  Clock,
  Coins,
  ShieldCheck,
  Calendar,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import {
  kCompetitionFormatPreviews,
  ActiveCompetitionItem,
} from "./landingModels";

interface CompetitionsJackpotSectionProps {
  initialJackpotBalance?: string | null;
  initialFailsafeAt?: string | null;
}

export const CompetitionsJackpotSection: React.FC<CompetitionsJackpotSectionProps> = ({
  initialJackpotBalance,
  initialFailsafeAt,
}) => {
  const [remainingSeconds, setRemainingSeconds] = useState<number>(0);
  const [balanceStr, setBalanceStr] = useState<string>(
    initialJackpotBalance || "125,000 GTC"
  );

  const getNextScheduledDrop = (): Date => {
    const now = new Date();
    const utcHours = now.getUTCHours();
    const nextDropHour = (Math.floor(utcHours / 6) + 1) * 6;
    const target = new Date(
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
      target.setUTCDate(target.getUTCDate() + 1);
    }
    return target;
  };

  useEffect(() => {
    let target = initialFailsafeAt ? new Date(initialFailsafeAt) : getNextScheduledDrop();
    if (isNaN(target.getTime()) || target.getTime() <= Date.now()) {
      target = getNextScheduledDrop();
    }

    const updateTimer = () => {
      const diff = Math.max(0, Math.floor((target.getTime() - Date.now()) / 1000));
      if (diff <= 0) {
        target = getNextScheduledDrop();
      }
      setRemainingSeconds(diff);
    };

    updateTimer();
    const timer = setInterval(updateTimer, 1000);
    return () => clearInterval(timer);
  }, [initialFailsafeAt]);

  const formatCountdown = (totalSec: number) => {
    const hours = Math.floor(totalSec / 3600);
    const minutes = Math.floor((totalSec % 3600) / 60);
    const seconds = totalSec % 60;
    const hh = String(hours).padStart(2, "0");
    const mm = String(minutes).padStart(2, "0");
    const ss = String(seconds).padStart(2, "0");
    return `${hh}:${mm}:${ss}`;
  };

  return (
    <section id="competitions" className="border-b border-[#22385A] bg-[#081120] py-20 sm:py-28">
      <div className="mx-auto max-w-[1440px] px-6 sm:px-12">
        {/* Section Masthead */}
        <div>
          <div className="flex items-center gap-2.5">
            <span className="h-2 w-2 rounded-full bg-[#D4AF37] shadow-[0_0_8px_#D4AF37]"></span>
            <p className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-[0.2em] text-[#D4AF37]">
              Competitions & Prize Drops
            </p>
          </div>
          <h2 className="mt-3 font-['Barlow_Condensed'] text-4xl font-black uppercase tracking-tight text-[#F2F4F8] sm:text-5xl">
            Continental Glory & 4 Scheduled Daily Jackpots
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-[#9AA7BD] sm:text-base">
            Enter league circuits, knockout tournaments and user-hosted cups. Published event rules define eligibility and prize pools, alongside the four scheduled daily jackpot drops.
          </p>
        </div>

        {/* 4 Scheduled Daily Jackpots Card */}
        <div className="mt-10 rounded-2xl border border-[#D4AF37]/50 bg-[#13233A] p-6 sm:p-10 shadow-[0_4px_32px_rgba(212,175,55,0.12)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="flex items-center gap-2 rounded-full border border-[#D4AF37]/40 bg-[#D4AF37]/15 px-3.5 py-1 font-['Barlow_Condensed'] text-xs font-extrabold uppercase tracking-wider text-[#D4AF37]">
              <Clock size={14} />
              4 SCHEDULED DAILY DROPS • 6-HR CYCLE
            </span>
            <span className="flex items-center gap-1.5 font-['JetBrains_Mono'] text-xs font-bold text-[#38BDF8]">
              <Calendar size={13} />
              UTC SCHEDULE (00:00, 06:00, 12:00, 18:00)
            </span>
          </div>

          <div className="mt-8 grid grid-cols-1 items-center gap-8 lg:grid-cols-12">
            {/* Left: Countdown */}
            <div className="lg:col-span-6">
              <span className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-widest text-[#6B7A93]">
                NEXT SCHEDULED JACKPOT DROP IN
              </span>
              <p className="mt-2 font-['JetBrains_Mono'] text-5xl sm:text-6xl font-black tracking-tight text-[#F2F4F8]">
                {formatCountdown(remainingSeconds)}
              </p>

              <div className="mt-6 flex flex-wrap items-center gap-4">
                <div className="rounded-xl border border-[#22385A] bg-[#0B1626] p-4">
                  <span className="text-[10px] uppercase tracking-wider text-[#6B7A93]">
                    ESTIMATED POOL
                  </span>
                  <p className="font-['JetBrains_Mono'] text-2xl font-bold text-[#E8C766]">
                    {balanceStr}
                  </p>
                </div>
                <div className="rounded-xl border border-[#22385A] bg-[#0B1626] p-4">
                  <span className="text-[10px] uppercase tracking-wider text-[#6B7A93]">
                    DROP CYCLE
                  </span>
                  <p className="font-['JetBrains_Mono'] text-2xl font-bold text-[#36E38A]">
                    Every 6 Hours
                  </p>
                </div>
              </div>
            </div>

            {/* Right: Mechanics */}
            <div className="space-y-4 rounded-xl border border-[#22385A] bg-[#0B1626]/70 p-6 lg:col-span-6">
              <div className="flex items-start gap-3">
                <ShieldCheck size={18} className="mt-0.5 text-[#36E38A]" />
                <div>
                  <h4 className="font-['Barlow_Condensed'] text-base font-bold uppercase text-[#F2F4F8]">
                    Automated 6-Hour Failsafe Cycles
                  </h4>
                  <p className="mt-0.5 text-xs text-[#9AA7BD] leading-relaxed">
                    Jackpot drops trigger unconditionally at 00:00, 06:00, 12:00, and 18:00 UTC. If no winner claims the pool within the 6-hour interval, the failsafe routine awards the balance to top matchday participants.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Coins size={18} className="mt-0.5 text-[#D4AF37]" />
                <div>
                  <h4 className="font-['Barlow_Condensed'] text-base font-bold uppercase text-[#F2F4F8]">
                    Transparent Rules & Equal Odds
                  </h4>
                  <p className="mt-0.5 text-xs text-[#9AA7BD] leading-relaxed">
                    Every active tournament match generates tickets based on competitive goals scored and tactical performance. All probabilities are audited on-chain and deterministically executed.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Sparkles size={18} className="mt-0.5 text-[#38BDF8]" />
                <div>
                  <h4 className="font-['Barlow_Condensed'] text-base font-bold uppercase text-[#F2F4F8]">
                    Instant Ledger Distribution
                  </h4>
                  <p className="mt-0.5 text-xs text-[#9AA7BD] leading-relaxed">
                    Winnings credit immediately to the club owner’s verified sporting ledger, instantly available for stadium expansions or squad reinforcements.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Competition Formats Header */}
        <div className="mt-14 flex flex-wrap items-center justify-between gap-4 border-b border-[#22385A] pb-4">
          <div className="flex items-center gap-2">
            <Trophy size={20} className="text-[#D4AF37]" />
            <h3 className="font-['Barlow_Condensed'] text-base font-extrabold uppercase tracking-widest text-[#D4AF37]">
              COMPETITION FORMAT PREVIEWS
            </h3>
          </div>
          <span className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-wider text-[#6B7A93]">
            GOVERNED BY PUBLISHED EVENT RULES
          </span>
        </div>

        {/* 3 Competition Formats */}
        <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-3">
          {kCompetitionFormatPreviews.map((comp) => (
            <div
              key={comp.name}
              className="flex flex-col justify-between rounded-xl border border-[#22385A] bg-[#13233A] p-6 transition-all hover:border-[#D4AF37]/50"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span
                    className="rounded px-2.5 py-1 font-['Barlow_Condensed'] text-xs font-bold uppercase"
                    style={{
                      color: comp.accentColor,
                      backgroundColor: `${comp.accentColor}15`,
                      border: `1px solid ${comp.accentColor}30`,
                    }}
                  >
                    {comp.type}
                  </span>
                  <span className="rounded bg-[#0B1626] px-2 py-0.5 text-[10px] text-[#6B7A93]">
                    {comp.status}
                  </span>
                </div>

                <h4 className="mt-4 font-['Barlow_Condensed'] text-2xl font-bold uppercase text-[#F2F4F8]">
                  {comp.name}
                </h4>
                <p className="mt-2 text-xs leading-relaxed text-[#9AA7BD]">
                  {comp.format}
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-[#22385A]">
                <p className="text-[11px] text-[#6B7A93] italic">
                  {comp.prizePool}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
