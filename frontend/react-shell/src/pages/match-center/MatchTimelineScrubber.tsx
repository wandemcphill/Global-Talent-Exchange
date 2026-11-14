import React, { useState } from "react";

export type TimelinePin = {
  id: string;
  timeSeconds: number;
  type: "goal" | "yellow_card" | "red_card" | "substitution" | "penalty" | "shot" | "save";
  label: string;
  side: "home" | "away" | null;
};

export type TimelineSegment = {
  phase: string;
  label: string;
  startSeconds: number;
  endSeconds: number;
};

export type TimelineModel = {
  durationSeconds: number;
  segments: TimelineSegment[];
  pins: TimelinePin[];
};

const PIN_TYPES: Record<string, TimelinePin["type"]> = {
  goal: "goal",
  penalty_goal: "goal",
  own_goal: "goal",
  yellow_card: "yellow_card",
  red_card: "red_card",
  substitution: "substitution",
  penalty: "penalty",
  save: "save",
};

export function phaseLabel(phase: string): string {
  const p = phase.toLowerCase().replace(/[\s-]+/g, "_");
  if (p === "pre_match" || p === "prematch" || p === "scheduled") return "Pre-Match";
  if (p === "first_half" || p === "1h") return "1st Half";
  if (p === "halftime" || p === "half_time" || p === "ht") return "Half-Time";
  if (p === "second_half" || p === "2h") return "2nd Half";
  if (p === "extra_time" || p === "et") return "Extra Time";
  if (p === "penalties" || p === "shootout") return "Shootout";
  if (p === "full_time" || p === "fulltime" || p === "completed" || p === "ft") return "Full-Time";
  return p.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Builds the scrubber model strictly from recorded data: phase segments from the frames' own `phase`
 * field and pins from supplied events. Nothing is synthesised (no assumed 45' half-time).
 */
export function buildTimelineModel(
  frames: ReadonlyArray<{ timeSeconds: number; phase?: string | null }>,
  events: ReadonlyArray<Record<string, any>>,
  durationSeconds: number,
): TimelineModel {
  const duration = Number.isFinite(durationSeconds) && durationSeconds > 0 ? durationSeconds : 0;
  const segments: TimelineSegment[] = [];
  const sorted = [...frames]
    .filter((f) => f && Number.isFinite(f.timeSeconds))
    .sort((a, b) => a.timeSeconds - b.timeSeconds);
  for (const frame of sorted) {
    const phase = String(frame.phase || "").trim();
    if (!phase) continue;
    const last = segments[segments.length - 1];
    if (last && last.phase === phase) {
      last.endSeconds = frame.timeSeconds;
    } else {
      if (last) last.endSeconds = frame.timeSeconds;
      segments.push({
        phase,
        label: phaseLabel(phase),
        startSeconds: frame.timeSeconds,
        endSeconds: frame.timeSeconds,
      });
    }
  }
  if (segments.length) {
    segments[segments.length - 1].endSeconds = Math.max(segments[segments.length - 1].endSeconds, duration);
  }

  const pins: TimelinePin[] = [];
  const seen = new Set<string>();
  for (const ev of events || []) {
    if (!ev) continue;
    const rawType = String(ev.type || ev.event_type || "").toLowerCase();
    const type = PIN_TYPES[rawType];
    if (!type) continue;
    const sec = Number.isFinite(Number(ev.time_seconds))
      ? Number(ev.time_seconds)
      : Number.isFinite(Number(ev.minute ?? ev.clock_minute))
        ? Number(ev.minute ?? ev.clock_minute) * 60
        : NaN;
    if (!Number.isFinite(sec) || sec < 0) continue;
    if (duration > 0 && sec > duration + 1) continue;
    const id = String(ev.event_id || ev.id || `${rawType}:${Math.round(sec)}:${ev.team || ev.side || ""}`);
    if (seen.has(id)) continue;
    seen.add(id);
    const side = ev.team === "home" || ev.side === "home" ? "home" : ev.team === "away" || ev.side === "away" ? "away" : null;
    const who = String(ev.player_name || ev.player || ev.text || ev.description || "").trim();
    pins.push({
      id,
      timeSeconds: sec,
      type,
      side,
      label: `${Math.floor(sec / 60)}' ${rawType.replace(/_/g, " ")}${who ? ` — ${who}` : ""}`,
    });
  }
  pins.sort((a, b) => a.timeSeconds - b.timeSeconds);
  return { durationSeconds: duration, segments, pins };
}

const PIN_STYLE: Record<TimelinePin["type"], string> = {
  goal: "bg-emerald-400",
  penalty: "bg-cyan-300",
  yellow_card: "bg-yellow-400",
  red_card: "bg-rose-500",
  substitution: "bg-violet-400",
  shot: "bg-orange-300",
  save: "bg-sky-400",
};

const PIN_BADGE: Record<TimelinePin["type"], { text: string; tone: string }> = {
  goal: { text: "⚽ GOAL", tone: "border-emerald-400/60 bg-emerald-500/20 text-emerald-200" },
  penalty: { text: "PENALTY", tone: "border-cyan-400/60 bg-cyan-500/20 text-cyan-200" },
  yellow_card: { text: "YELLOW CARD", tone: "border-yellow-400/60 bg-yellow-500/20 text-yellow-200" },
  red_card: { text: "RED CARD", tone: "border-rose-400/60 bg-rose-500/20 text-rose-200" },
  substitution: { text: "SUB", tone: "border-violet-400/60 bg-violet-500/20 text-violet-200" },
  shot: { text: "SHOT", tone: "border-orange-400/60 bg-orange-500/20 text-orange-200" },
  save: { text: "GREAT SAVE", tone: "border-sky-400/60 bg-sky-500/20 text-sky-200" },
};

export function MatchTimelineScrubber({
  model,
  currentSeconds,
  onSeek,
}: {
  model: TimelineModel;
  currentSeconds: number;
  onSeek: (seconds: number) => void;
}) {
  const [hoveredPinId, setHoveredPinId] = useState<string | null>(null);
  const { durationSeconds, segments, pins } = model;
  if (durationSeconds <= 0) return null;
  const clamped = Math.min(durationSeconds, Math.max(0, currentSeconds));
  const pct = (sec: number) => `${Math.min(100, Math.max(0, (sec / durationSeconds) * 100))}%`;
  const activeSegment = segments.find((s) => clamped >= s.startSeconds && clamped <= s.endSeconds);
  const hoveredPin = hoveredPinId ? pins.find((p) => p.id === hoveredPinId) || null : null;

  const prevPin = [...pins].reverse().find((p) => p.timeSeconds < clamped - 2) || null;
  const nextPin = pins.find((p) => p.timeSeconds > clamped + 2) || null;

  return (
    <div data-testid="match-timeline-scrubber" className="relative mt-2 rounded-md border border-white/10 bg-slate-950/75 px-3 py-2">
      <div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
        <div className="flex items-center gap-2">
          <span data-testid="match-timeline-phase">{activeSegment?.label || "Replay"}</span>
          {pins.length > 0 && (
            <div className="flex items-center gap-1">
              <button
                type="button"
                data-testid="timeline-prev-event"
                disabled={!prevPin}
                onClick={() => prevPin && onSeek(Math.max(0, prevPin.timeSeconds - 6))}
                title={prevPin ? `Previous: ${prevPin.label}` : "No earlier key moment"}
                className="rounded border border-white/15 bg-white/5 px-1.5 py-0.5 text-[9px] font-black text-slate-300 transition hover:border-emerald-400/50 hover:text-white disabled:opacity-35"
              >
                ⏮ PREV KEY
              </button>
              <button
                type="button"
                data-testid="timeline-next-event"
                disabled={!nextPin}
                onClick={() => nextPin && onSeek(Math.max(0, nextPin.timeSeconds - 6))}
                title={nextPin ? `Next: ${nextPin.label}` : "No later key moment"}
                className="rounded border border-white/15 bg-white/5 px-1.5 py-0.5 text-[9px] font-black text-slate-300 transition hover:border-emerald-400/50 hover:text-white disabled:opacity-35"
              >
                NEXT KEY ⏭
              </button>
            </div>
          )}
        </div>
        <span className="font-mono">
          {Math.floor(clamped / 60)}:{String(Math.floor(clamped % 60)).padStart(2, "0")} /{" "}
          {Math.floor(durationSeconds / 60)}:{String(Math.floor(durationSeconds % 60)).padStart(2, "0")}
        </span>
      </div>
      {hoveredPin && (
        <div
          data-testid="timeline-pin-preview"
          className="mb-1.5 flex items-center justify-between gap-2 rounded border border-white/15 bg-slate-900/95 px-2.5 py-1 text-[11px] text-slate-100 shadow-lg"
        >
          <div className="flex min-w-0 items-center gap-2">
            <span
              className={`shrink-0 rounded border px-1.5 py-0.5 text-[9px] font-black uppercase tracking-wider ${PIN_BADGE[hoveredPin.type].tone}`}
            >
              {PIN_BADGE[hoveredPin.type].text}
            </span>
            <span className="truncate font-bold">{hoveredPin.label}</span>
          </div>
          <span className="shrink-0 font-mono text-[10px] text-emerald-300">Click to watch build-up (-6s)</span>
        </div>
      )}
      <div className="relative h-6">
        <div className="absolute inset-x-0 top-2.5 flex h-1.5 overflow-hidden rounded-full bg-slate-800">
          {segments.map((s) => (
            <div
              key={`${s.phase}:${s.startSeconds}`}
              data-testid="match-timeline-segment"
              title={s.label}
              className={`h-full border-r border-slate-950 ${activeSegment === s ? "bg-emerald-500/60" : "bg-slate-600/60"}`}
              style={{ width: `${((s.endSeconds - s.startSeconds) / durationSeconds) * 100}%` }}
            />
          ))}
        </div>
        {pins.map((pin) => (
          <button
            key={pin.id}
            type="button"
            data-testid="match-timeline-pin"
            data-pin-type={pin.type}
            title={pin.label}
            aria-label={pin.label}
            onMouseEnter={() => setHoveredPinId(pin.id)}
            onMouseLeave={() => setHoveredPinId((prev) => (prev === pin.id ? null : prev))}
            onFocus={() => setHoveredPinId(pin.id)}
            onBlur={() => setHoveredPinId((prev) => (prev === pin.id ? null : prev))}
            onClick={() => onSeek(Math.max(0, pin.timeSeconds - 6))}
            className={`absolute top-0 z-10 h-3 w-1.5 -translate-x-1/2 rounded-sm transition-transform ${PIN_STYLE[pin.type]} hover:scale-150`}
            style={{ left: pct(pin.timeSeconds) }}
          />
        ))}
        <input
          type="range"
          data-testid="match-timeline-range"
          aria-label="Match timeline"
          min={0}
          max={durationSeconds}
          step={1}
          value={clamped}
          onChange={(event) => onSeek(Number(event.target.value))}
          className="absolute inset-x-0 top-1.5 h-4 w-full cursor-pointer opacity-0"
        />
        <div
          className="pointer-events-none absolute top-1.5 h-4 w-0.5 -translate-x-1/2 bg-white"
          style={{ left: pct(clamped) }}
        />
      </div>
    </div>
  );
}
