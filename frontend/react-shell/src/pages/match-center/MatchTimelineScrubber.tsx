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

export type MomentumPoint = {
  t: number;
  /** Signed momentum in [-1, 1]: positive = Home attacking pressure / xG, negative = Away. */
  value: number;
};

export type TimelineModel = {
  durationSeconds: number;
  segments: TimelineSegment[];
  pins: TimelinePin[];
  momentum?: MomentumPoint[];
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
  frames: ReadonlyArray<{
    timeSeconds: number;
    phase?: string | null;
    possession_side?: string | null;
    possessionSide?: string | null;
    pressure_index?: number | null;
    ball?: { x?: number; position?: { x?: number } } | null;
    home_attacks_right?: boolean;
  }>,
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

  // Build smoothed xG & territorial momentum wave across 48 buckets
  const BUCKETS = 48;
  const rawSum = new Float32Array(BUCKETS);
  const rawCount = new Float32Array(BUCKETS);
  if (duration > 0) {
    for (const frame of sorted) {
      const idx = Math.min(BUCKETS - 1, Math.max(0, Math.floor((frame.timeSeconds / duration) * BUCKETS)));
      const rawBallX = Number(frame.ball?.position?.x ?? frame.ball?.x ?? NaN);
      const ballX = Number.isFinite(rawBallX) ? (rawBallX > 1.5 ? rawBallX / 100 : rawBallX) : 0.5;
      const attacksRight = frame.home_attacks_right !== false;
      const territory = (ballX - 0.5) * 2 * (attacksRight ? 1 : -1); // +1 near away goal, -1 near home goal
      const posSide = String(frame.possession_side || frame.possessionSide || "").toLowerCase();
      const posBias = posSide === "home" ? 0.35 : posSide === "away" ? -0.35 : 0;
      const pressure = Number(frame.pressure_index);
      const pressBoost = Number.isFinite(pressure) ? 0.7 + Math.min(0.6, pressure * 0.5) : 1;
      rawSum[idx] += Math.max(-1, Math.min(1, (territory * 0.75 + posBias) * pressBoost));
      rawCount[idx] += 1;
    }
    for (const ev of events || []) {
      if (!ev) continue;
      const sec = Number.isFinite(Number(ev.time_seconds))
        ? Number(ev.time_seconds)
        : Number.isFinite(Number(ev.minute ?? ev.clock_minute))
          ? Number(ev.minute ?? ev.clock_minute) * 60
          : NaN;
      if (!Number.isFinite(sec) || sec < 0 || sec > duration + 1) continue;
      const idx = Math.min(BUCKETS - 1, Math.max(0, Math.floor((sec / duration) * BUCKETS)));
      const sideRaw = String(ev.side || ev.team || "").toLowerCase();
      const sign = sideRaw === "away" ? -1 : sideRaw === "home" ? 1 : 0;
      if (sign === 0) continue;
      const rawType = String(ev.type || ev.event_type || "").toLowerCase();
      const xg = Number(ev.xg ?? ev.expected_goals ?? 0);
      const weight =
        rawType === "goal" || rawType === "penalty_goal"
          ? 1.0
          : rawType === "shot" || rawType === "save" || rawType === "penalty" || rawType === "miss"
            ? Math.max(0.45, Math.min(0.95, xg > 0 ? xg * 1.4 : 0.55))
            : rawType === "corner" || rawType === "attack" || rawType === "chance"
              ? 0.32
              : 0;
      if (weight > 0) {
        rawSum[idx] += sign * weight * 1.8;
        rawCount[idx] += 1;
      }
    }
  }
  const averaged = new Float32Array(BUCKETS);
  for (let i = 0; i < BUCKETS; i += 1) {
    averaged[i] = rawCount[i] > 0 ? Math.max(-1, Math.min(1, rawSum[i] / rawCount[i])) : 0;
  }
  const momentum: MomentumPoint[] = [];
  for (let i = 0; i < BUCKETS; i += 1) {
    const prev = averaged[Math.max(0, i - 1)];
    const cur = averaged[i];
    const next = averaged[Math.min(BUCKETS - 1, i + 1)];
    momentum.push({
      t: ((i + 0.5) / BUCKETS) * duration,
      value: Math.max(-1, Math.min(1, prev * 0.25 + cur * 0.5 + next * 0.25)),
    });
  }

  return { durationSeconds: duration, segments, pins, momentum };
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
  readOnly = true,
  homeColor = "#10b981",
  awayColor = "#38bdf8",
}: {
  model: TimelineModel;
  currentSeconds: number;
  onSeek?: (seconds: number) => void;
  readOnly?: boolean;
  homeColor?: string;
  awayColor?: string;
}) {
  const [hoveredPinId, setHoveredPinId] = useState<string | null>(null);
  const { durationSeconds, segments, pins, momentum = [] } = model;
  if (durationSeconds <= 0) return null;
  const clamped = Math.min(durationSeconds, Math.max(0, currentSeconds));
  const pct = (sec: number) => `${Math.min(100, Math.max(0, (sec / durationSeconds) * 100))}%`;
  const activeSegment = segments.find((s) => clamped >= s.startSeconds && clamped <= s.endSeconds);
  const hoveredPin = hoveredPinId ? pins.find((p) => p.id === hoveredPinId) || null : null;

  // Build SVG upper (Home) and lower (Away) xG momentum wave paths
  const waveW = 480;
  const waveH = 28;
  const midY = waveH / 2;
  const buildWavePath = (sideSign: 1 | -1) => {
    if (!momentum.length) return "";
    const pts: string[] = [`M 0 ${midY}`];
    for (let i = 0; i < momentum.length; i += 1) {
      const x = ((i + 0.5) / momentum.length) * waveW;
      const v = momentum[i].value * sideSign;
      const mag = v > 0 ? Math.min(1, v) * (midY - 2) : 0;
      const y = sideSign > 0 ? midY - mag : midY + mag;
      pts.push(`L ${x.toFixed(1)} ${y.toFixed(1)}`);
    }
    pts.push(`L ${waveW} ${midY} Z`);
    return pts.join(" ");
  };
  const homeWavePath = buildWavePath(1);
  const awayWavePath = buildWavePath(-1);

  const handlePrevKey = () => {
    if (!onSeek) return;
    const prevPin = [...pins].reverse().find((p) => p.timeSeconds < clamped - 1);
    if (prevPin) {
      onSeek(Math.max(0, prevPin.timeSeconds - 6));
    } else {
      onSeek(0);
    }
  };

  const handleNextKey = () => {
    if (!onSeek) return;
    const nextPin = pins.find((p) => p.timeSeconds > clamped + 1);
    if (nextPin) {
      onSeek(Math.max(0, nextPin.timeSeconds - 6));
    }
  };

  return (
    <div data-testid="match-timeline-scrubber" className="relative mt-2 rounded-md border border-white/10 bg-slate-950/75 px-3 py-2">
      <div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
        <div className="flex items-center gap-2">
          <span data-testid="match-timeline-phase">{activeSegment?.label || (readOnly ? "Broadcast" : "Replay")}</span>
          <span className="rounded border border-emerald-400/25 bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-black text-emerald-300">
            {readOnly ? "Universal Broadcast Timeline" : "Recorded Replay Timeline"}
          </span>
          {!readOnly && onSeek && (
            <div className="flex items-center gap-1">
              <button
                type="button"
                data-testid="timeline-prev-event"
                onClick={handlePrevKey}
                className="rounded border border-white/20 bg-slate-800 px-1.5 py-0.5 text-[9px] font-bold text-slate-300 hover:bg-slate-700 hover:text-white"
              >
                PREV KEY
              </button>
              <button
                type="button"
                data-testid="timeline-next-event"
                onClick={handleNextKey}
                className="rounded border border-white/20 bg-slate-800 px-1.5 py-0.5 text-[9px] font-bold text-slate-300 hover:bg-slate-700 hover:text-white"
              >
                NEXT KEY
              </button>
            </div>
          )}
        </div>
        {hoveredPin && (
          <div
            data-testid="timeline-pin-preview"
            className="pointer-events-none flex min-w-0 max-w-md items-center gap-2 rounded border border-white/15 bg-slate-900/95 px-2 py-0.5 text-[10px] normal-case tracking-normal text-slate-100 shadow"
          >
            <span
              className={`shrink-0 rounded border px-1.5 py-0 text-[9px] font-black uppercase tracking-wider ${PIN_BADGE[hoveredPin.type].tone}`}
            >
              {PIN_BADGE[hoveredPin.type].text}
            </span>
            <span className="truncate font-bold">{hoveredPin.label}</span>
          </div>
        )}
        <span className="font-mono">
          {Math.floor(clamped / 60)}:{String(Math.floor(clamped % 60)).padStart(2, "0")} /{" "}
          {Math.floor(durationSeconds / 60)}:{String(Math.floor(durationSeconds % 60)).padStart(2, "0")}
        </span>
      </div>
      <div className="relative h-9" role="progressbar" aria-label="Universal broadcast progress" aria-valuemin={0} aria-valuemax={Math.round(durationSeconds)} aria-valuenow={Math.round(clamped)}>
        {/* xG & Territorial Momentum Wave */}
        {momentum.length > 0 && (
          <svg
            data-testid="match-momentum-wave"
            role="img"
            aria-label="Match xG momentum wave"
            width="100%"
            height="28"
            viewBox={`0 0 ${waveW} ${waveH}`}
            preserveAspectRatio="none"
            className="pointer-events-none absolute inset-x-0 top-0.5 block h-7 w-full"
          >
            <line x1={0} y1={midY} x2={waveW} y2={midY} stroke="rgba(148,163,184,0.22)" strokeWidth={1} />
            {homeWavePath && <path d={homeWavePath} fill={homeColor} fillOpacity={0.34} />}
            {awayWavePath && <path d={awayWavePath} fill={awayColor} fillOpacity={0.34} />}
          </svg>
        )}
        <div className="absolute inset-x-0 top-4 flex h-1.5 overflow-hidden rounded-full bg-slate-800/80">
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
        {!readOnly && onSeek && (
          <input
            type="range"
            data-testid="match-timeline-range"
            aria-label="Match timeline"
            min={0}
            max={Math.round(durationSeconds)}
            value={Math.round(clamped)}
            onChange={(e) => onSeek(Number(e.target.value))}
            className="absolute inset-x-0 top-0 z-20 h-9 w-full cursor-pointer opacity-0"
          />
        )}
        {pins.map((pin) => {
          const isGoalPin = pin.type === "goal" || pin.type === "penalty";
          const topClass = pin.side === "away" ? "top-5" : "top-0.5";
          return (
            <div
              key={pin.id}
              data-testid="match-timeline-pin"
              data-pin-type={pin.type}
              title={pin.label}
              aria-label={pin.label}
              tabIndex={0}
              onMouseEnter={() => setHoveredPinId(pin.id)}
              onMouseLeave={() => setHoveredPinId((prev) => (prev === pin.id ? null : prev))}
              onFocus={() => setHoveredPinId(pin.id)}
              onBlur={() => setHoveredPinId((prev) => (prev === pin.id ? null : prev))}
              onClick={!readOnly && onSeek ? () => onSeek(Math.max(0, pin.timeSeconds - 6)) : undefined}
              className={`pointer-events-auto absolute ${topClass} z-30 -translate-x-1/2 rounded-full border border-slate-950 shadow-sm transition-transform hover:scale-125 ${
                isGoalPin ? "h-3 w-3" : "h-2.5 w-2"
              } ${PIN_STYLE[pin.type]} ${!readOnly && onSeek ? "cursor-pointer" : ""}`}
              style={{ left: pct(pin.timeSeconds) }}
            />
          );
        })}
        <div
          data-testid="match-timeline-playhead"
          className="pointer-events-none absolute top-0.5 z-20 h-8 w-0.5 -translate-x-1/2 bg-white shadow-[0_0_8px_rgba(255,255,255,0.85)]"
          style={{ left: pct(clamped) }}
        />
      </div>
    </div>
  );
}
