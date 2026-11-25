import React from "react";
import { classicEventTicks, classicMatchFacts, clubCode, matchClockLabel } from "./classicMatchMarkers";

type BarEvent = Record<string, unknown>;

export function ClassicMatchBar({
  timeSeconds,
  minute,
  homeName,
  awayName,
  homeScore,
  awayScore,
  events,
  feedStatus,
  feedAgeSeconds,
  demo,
  activeEvent,
}: {
  timeSeconds?: number | null;
  minute?: number | null;
  homeName: string;
  awayName: string;
  homeScore?: number | null;
  awayScore?: number | null;
  events?: BarEvent[] | null;
  feedStatus: string;
  feedAgeSeconds?: number | null;
  demo?: boolean;
  activeEvent?: string | null;
}) {
  const ticks = classicEventTicks(events);
  const span = Math.max(90, minute || 0, ...ticks.map((tick) => tick.minute));
  const playhead = typeof minute === "number" && Number.isFinite(minute) ? Math.min(span, Math.max(0, minute)) : 0;
  const hasScore = typeof homeScore === "number" && typeof awayScore === "number";

  return (
    <div
      data-testid="classic-match-bar"
      className="flex items-center gap-3 rounded-md border border-white/10 bg-[#07111f] px-3 py-1.5 text-white"
    >
      <span className="w-12 font-mono text-sm font-black tabular-nums" data-testid="classic-match-clock">
        {matchClockLabel(timeSeconds, minute)}
      </span>
      <span className="text-xs font-black tracking-wider" title={homeName}>
        {clubCode(homeName)}
      </span>
      <span
        data-testid="pitch-scorebug"
        className="font-mono text-sm font-black tabular-nums"
      >
        {hasScore ? `${homeScore} - ${awayScore}` : "–"}
      </span>
      <span className="text-xs font-black tracking-wider" title={awayName}>
        {clubCode(awayName)}
      </span>
      <div className="relative mx-1 h-2 min-w-0 flex-1 rounded-full bg-white/10" data-testid="classic-event-rail">
        <div
          className="absolute top-0 h-2 w-0.5 bg-white"
          style={{ left: `${(playhead / span) * 100}%` }}
        />
        {ticks.map((tick, index) => (
          <span
            key={`${tick.kind}-${tick.minute}-${index}`}
            title={`${tick.kind} ${Math.round(tick.minute)}'`}
            className={`absolute top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full ${
              tick.kind === "goal" ? "bg-white" : tick.kind === "card" ? "bg-amber-400" : "bg-sky-300"
            }`}
            style={{ left: `${(Math.min(span, tick.minute) / span) * 100}%` }}
          />
        ))}
      </div>
      {demo ? (
        <span
          data-testid="pitch-demo-badge"
          className="rounded border border-amber-400/40 bg-amber-500/15 px-1.5 py-0.5 text-[9px] font-black uppercase tracking-widest text-amber-300"
        >
          DEMO
        </span>
      ) : null}
      <span
        data-testid="pitch-feed-status"
        data-status={feedStatus}
        className="font-mono text-[10px] font-bold uppercase tracking-wider text-slate-300"
      >
        {feedStatus}{feedStatus === "DELAYED" && feedAgeSeconds != null ? ` · ${Math.max(1, Math.round(feedAgeSeconds))}s` : ""}
      </span>
      {activeEvent ? (
        <span
          data-testid="pitch-active-event"
          className="font-mono text-[10px] font-bold uppercase tracking-wider text-cyan-200"
        >
          {activeEvent.replace(/_/g, " ")}
        </span>
      ) : null}
    </div>
  );
}

export function ClassicMatchFacts({ events }: { events?: BarEvent[] | null }) {
  const facts = classicMatchFacts(events);
  if (!facts) return null;
  const cells: Array<[string, number]> = [
    ["Shots", facts.shots],
    ["On target", facts.onTarget],
    ["Corners", facts.corners],
    ["Fouls", facts.fouls],
    ["Yellow", facts.yellow],
    ["Red", facts.red],
  ];
  return (
    <div
      data-testid="classic-match-facts"
      className="mt-2 flex flex-wrap gap-x-4 gap-y-1 rounded-md border border-white/10 bg-[#07111f] px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-slate-300"
    >
      {cells.map(([label, value]) => (
        <span key={label}>
          {label} <span className="text-white">{value}</span>
        </span>
      ))}
    </div>
  );
}
