import React, { useState, useEffect } from "react";
import {
  Trophy,
  Clock,
  Calendar,
  Timer,
  TrendingUp,
  Dices,
  AlarmClockCheck,
  Info,
} from "lucide-react";
import { kCompetitionFormatPreviews, ActiveCompetitionItem } from "./landingModels";

interface CompetitionsJackpotSectionProps {
  initialJackpotBalance?: string | null;
  initialFailsafeAt?: string | null;
}

export const CompetitionsJackpotSection: React.FC<CompetitionsJackpotSectionProps> = ({
  initialJackpotBalance,
  initialFailsafeAt,
}) => {
  const [remainingSeconds, setRemainingSeconds] = useState<number>(0);
  const balanceStr = initialJackpotBalance || "Pool unavailable";

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
        0,
      ),
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
            Enter league circuits, knockout tournaments and user-hosted cups. Published event rules
            define eligibility and prize pools, alongside the four scheduled daily jackpot drops.
          </p>
        </div>

        {/* 4 Scheduled Daily Jackpots Card */}
        <div className="mt-10 rounded-2xl border border-[#D4AF37]/50 bg-[#13233A] p-6 sm:p-10 shadow-[0_4px_32px_rgba(212,175,55,0.12)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="flex items-center gap-2 rounded-full border border-[#D4AF37]/40 bg-[#D4AF37]/15 px-3.5 py-1 font-['Barlow_Condensed'] text-xs font-extrabold uppercase tracking-wider text-[#D4AF37]">
              <Clock size={14} />4 SCHEDULED DAILY DROPS • 6-HR CYCLE
            </span>
            <span className="flex items-center gap-1.5 font-['JetBrains_Mono'] text-xs font-bold text-[#38BDF8]">
              <Calendar size={13} />
              UTC SCHEDULE
            </span>
          </div>

          <div className="mt-8 grid grid-cols-1 items-center gap-8 lg:grid-cols-12">
            {/* Left: Pool + Countdown */}
            <div className="lg:col-span-6">
              <span className="font-['Barlow_Condensed'] text-[11px] font-extrabold uppercase tracking-[0.15em] text-[#6B7A93]">
                CURRENT JACKPOT ROUND POOL
              </span>
              <p className="mt-1 font-['JetBrains_Mono'] text-3xl font-black tracking-tight text-[#E8C766]">
                {balanceStr}
              </p>

              <span className="mt-4 block font-['Barlow_Condensed'] text-[11px] font-extrabold uppercase tracking-[0.12em] text-[#36E38A]">
                TIME TO NEXT SCHEDULED DROP
              </span>
              <div className="mt-1.5 inline-flex items-center gap-2 rounded-[10px] border border-[#22385A] bg-[#081120] px-3.5 py-2">
                <Timer size={18} className="text-[#36E38A]" />
                <span className="font-['JetBrains_Mono'] text-[22px] font-black tracking-[0.1em] text-[#F2F4F8]">
                  {formatCountdown(remainingSeconds)}
                </span>
                <span className="text-[10px] font-bold text-[#6B7A93]">UTC</span>
              </div>
            </div>

            {/* Right: Mechanics */}
            <div className="space-y-2 lg:col-span-6">
              <p className="font-['Barlow_Condensed'] text-[11px] font-extrabold uppercase tracking-[0.12em] text-[#D4AF37]">
                THREE VERIFIED TRIGGER MECHANISMS
              </p>
              {[
                {
                  Icon: TrendingUp,
                  title: "1. Threshold Trigger (500.00 GTC)",
                  description:
                    "Automatically triggers payout the moment pool hits the verified threshold balance.",
                },
                {
                  Icon: Dices,
                  title: "2. Probability Roll (Scales to 50% Cap)",
                  description:
                    "Every match contribution rolls dynamic win chance capped at 50% maximum limit.",
                },
                {
                  Icon: AlarmClockCheck,
                  title: "3. 6-Hour Failsafe (Guaranteed 4x Daily)",
                  description:
                    "If neither threshold nor roll occurs, round triggers automatically every 6 hours.",
                },
              ].map(({ Icon, title, description }) => (
                <div key={title} className="flex items-start gap-2">
                  <Icon size={14} className="mt-0.5 shrink-0 text-[#D4AF37]" />
                  <div>
                    <h4 className="text-xs font-bold text-[#F2F4F8]">{title}</h4>
                    <p className="text-[11px] leading-snug text-[#6B7A93]">{description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Competition Formats Header */}
        <div className="mt-14 flex flex-wrap items-center justify-between gap-4 border-b border-[#22385A] pb-4">
          <div className="flex items-center gap-2">
            <Trophy size={20} className="text-[#D4AF37]" />
            <h3 className="font-['Barlow_Condensed'] text-base font-extrabold uppercase tracking-widest text-[#D4AF37]">
              FEATURED COMPETITION FORMATS
            </h3>
          </div>
          <span className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-wider text-[#6B7A93]">
            ILLUSTRATIVE • NOT LIVE FIXTURES
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
                <p className="mt-2 text-xs leading-relaxed text-[#9AA7BD]">{comp.format}</p>
              </div>

              <div className="mt-6 flex items-start gap-2 rounded-[10px] border border-[#22385A] bg-[#081120] p-3">
                <Info size={16} className="mt-0.5 shrink-0 text-[#D4AF37]" />
                <p className="text-[11px] leading-snug text-[#9AA7BD]">
                  Format preview. Live entry status, prize pools and broadcast availability must
                  come from the published event data.
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
