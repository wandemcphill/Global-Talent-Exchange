import React from "react";
import { Activity, Eye, MousePointerClick, UserRound } from "lucide-react";
import { GtexLiveWorldPulse, GtexTrafficTotals } from "./landingModels";

interface PublicTrafficStatsStripProps {
  pulse: GtexLiveWorldPulse | null;
}

const numberLabel = (value: number | null | undefined) =>
  typeof value === "number" ? new Intl.NumberFormat("en").format(value) : "—";

const PERIODS: Array<{ key: keyof GtexTrafficTotals; label: string; slug: string }> = [
  { key: "today", label: "Today", slug: "today" },
  { key: "last7Days", label: "7 days", slug: "7-days" },
  { key: "last30Days", label: "30 days", slug: "30-days" },
  { key: "allTime", label: "All time", slug: "all-time" },
];

const TrafficWindows: React.FC<{
  title: string;
  definition: string;
  totals: GtexTrafficTotals | undefined;
  testId: string;
  Icon: React.ComponentType<{ size?: number; className?: string }>;
  tone: string;
}> = ({ title, definition, totals, testId, Icon, tone }) => (
  <div
    className="rounded-xl border border-[#253B5B] bg-[#13233A]/80 p-4 shadow-lg sm:p-5"
    data-testid={testId}
  >
    <div className="flex items-start justify-between gap-3">
      <div>
        <span className="text-[10px] font-extrabold uppercase tracking-[0.13em] text-[#9AA7BD] sm:text-xs">
          {title}
        </span>
        <p className="mt-1 max-w-md text-[10px] leading-relaxed text-[#71829D] sm:text-xs">{definition}</p>
      </div>
      <Icon size={15} className={tone} />
    </div>
    <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
      {PERIODS.map((period) => (
        <div key={period.key} data-testid={`${testId}-${period.slug}`}>
          <p className="text-[10px] font-extrabold uppercase tracking-[0.14em] text-[#D4AF37]">{period.label}</p>
          <p className="mt-1 font-['Barlow_Condensed'] text-3xl font-black tabular-nums text-white sm:text-4xl">
            {numberLabel(totals?.[period.key])}
          </p>
        </div>
      ))}
    </div>
  </div>
);

export const PublicTrafficStatsStrip: React.FC<PublicTrafficStatsStripProps> = ({ pulse }) => {
  const liveCards = [
    {
      label: "Online now",
      value: numberLabel(pulse?.usersOnline),
      detail: "Signed-in users active now",
      Icon: Activity,
      tone: "text-[#36E38A]",
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
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <TrafficWindows
            title="Visitors"
            definition="Unique browsers. The same person counts once in each period."
            totals={pulse?.visitors}
            testId="public-traffic-visitors"
            Icon={Eye}
            tone="text-[#36E38A]"
          />
          <TrafficWindows
            title="Page views"
            definition="Every page opened. One visitor can create many page views."
            totals={pulse?.pageViews}
            testId="public-traffic-page-views"
            Icon={MousePointerClick}
            tone="text-[#E8C766]"
          />
        </div>
        <div className="mt-3 grid grid-cols-2 gap-3">
          {liveCards.map(({ label, value, detail, Icon, tone }) => (
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
        <p className="mt-3 text-[10px] leading-relaxed text-[#71829D] sm:text-xs">
          Today is the current UTC day. 7 days and 30 days are rolling windows, so they do not reset on Monday or
          the first of the month. All time keeps every visit recorded so far. These windows overlap: do not add them
          together. Counts refresh automatically. Online users are signed-in accounts with a recent active heartbeat.
        </p>
      </div>
    </section>
  );
};
