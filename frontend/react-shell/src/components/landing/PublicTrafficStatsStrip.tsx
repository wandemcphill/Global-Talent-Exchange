import React from "react";
import { Activity, Eye, Users, UserRound } from "lucide-react";
import { GtexLiveWorldPulse } from "./landingModels";

interface PublicTrafficStatsStripProps {
  pulse: GtexLiveWorldPulse | null;
}

const numberLabel = (value: number | undefined) =>
  typeof value === "number" ? new Intl.NumberFormat("en").format(value) : "—";

export const PublicTrafficStatsStrip: React.FC<PublicTrafficStatsStripProps> = ({ pulse }) => {
  const items = [
    {
      label: "Visitors today",
      value: numberLabel(pulse?.visitorsToday),
      detail: "Unique visitors across GTEX",
      Icon: Eye,
      tone: "text-[#36E38A]",
    },
    {
      label: "Online now",
      value: numberLabel(pulse?.usersOnline),
      detail: "Signed-in users active now",
      Icon: Activity,
      tone: "text-[#36E38A]",
    },
    {
      label: "Page views today",
      value: numberLabel(pulse?.pageViewsToday),
      detail: "Pages viewed across the platform",
      Icon: Users,
      tone: "text-[#E8C766]",
    },
    {
      label: "Registered users",
      value: numberLabel(pulse?.registeredUsers),
      detail: "Active registered accounts",
      Icon: UserRound,
      tone: "text-[#E8C766]",
    },
  ];

  return (
    <section
      aria-label="GTEX public platform statistics"
      data-testid="public-traffic-stats"
      className="relative border-y border-[#22385A] bg-[#0D1B2E] py-6 sm:py-8"
    >
      <div className="mx-auto max-w-[1440px] px-4 sm:px-8">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="font-['Barlow_Condensed'] text-xs font-extrabold uppercase tracking-[0.2em] text-[#D4AF37]">
              GTEX in numbers
            </p>
            <h2 className="mt-1 font-['Barlow_Condensed'] text-xl font-black uppercase tracking-wide text-[#F2F4F8] sm:text-2xl">
              The football world is active
            </h2>
          </div>
          <span className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-emerald-300">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
              <span className="relative h-2 w-2 rounded-full bg-[#36E38A]" />
            </span>
            Live platform statistics
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {items.map(({ label, value, detail, Icon, tone }) => (
            <div
              key={label}
              className="rounded-xl border border-[#253B5B] bg-[#13233A]/80 p-4 shadow-lg sm:p-5"
              data-testid={`public-traffic-${label.toLowerCase().replaceAll(" ", "-")}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-[10px] font-extrabold uppercase tracking-[0.13em] text-[#9AA7BD] sm:text-xs">
                  {label}
                </span>
                <Icon size={15} className={tone} />
              </div>
              <p className="mt-3 font-['Barlow_Condensed'] text-3xl font-black tabular-nums text-white sm:text-4xl">
                {value}
              </p>
              <p className="mt-1 text-[10px] leading-relaxed text-[#71829D] sm:text-xs">{detail}</p>
            </div>
          ))}
        </div>
        <p className="mt-3 text-[10px] text-[#71829D]">
          Counts refresh automatically. Online users are signed-in accounts with a recent active heartbeat.
        </p>
      </div>
    </section>
  );
};
