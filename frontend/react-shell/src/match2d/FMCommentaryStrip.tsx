import React from "react";
import { motion } from "framer-motion";

export type FMCommentaryPhase =
  | "neutral"
  | "chance"
  | "goal"
  | "card_yellow"
  | "card_red"
  | "var"
  | "sub";

export type FMCommentaryStripProps = {
  phase: FMCommentaryPhase;
  badge: string;
  headline: string;
  subline?: string | null;
  minuteLabel?: string | null;
  scoreline?: string | null;
  scorerName?: string | null;
  assistName?: string | null;
  shotXg?: number | null;
  clubColor?: string | null;
  kind?: string;
  tone?: string;
  onWatchReplay?: () => void;
  /** Compact floating mode for bottom-center overlay inside 3D / 2D viewports without blocking penalty boxes. */
  floating?: boolean;
  testId?: string;
};

export function resolveCommentaryPhase(input: {
  kind?: string | null;
  tone?: string | null;
  hasVar?: boolean;
  hasSub?: boolean;
}): FMCommentaryPhase {
  if (input.hasVar) return "var";
  if (input.hasSub) return "sub";
  const k = String(input.kind || "").toLowerCase();
  const t = String(input.tone || "").toLowerCase();
  if (k === "goal" || k === "penalty_goal" || t === "goal") return "goal";
  if (k === "red_card" || t === "card_red") return "card_red";
  if (k === "yellow_card" || t === "card_yellow") return "card_yellow";
  if (k === "substitution" || k === "sub") return "sub";
  if (k === "var" || k === "var_review" || k === "offside") return "var";
  if (k === "shot" || k === "save" || k === "miss" || k === "woodwork" || k === "penalty" || t === "chance") {
    return "chance";
  }
  return "neutral";
}

function transitionForPhase(phase: FMCommentaryPhase) {
  switch (phase) {
    case "goal":
      return { type: "spring" as const, stiffness: 420, damping: 24, mass: 0.7 };
    case "chance":
      return { type: "spring" as const, stiffness: 360, damping: 26, mass: 0.6 };
    case "card_red":
    case "card_yellow":
    case "var":
    case "sub":
      return { duration: 0.28, ease: [0.22, 1, 0.36, 1] as const };
    case "neutral":
    default:
      return { duration: 0.2, ease: "easeOut" as const };
  }
}

function phaseContainerClasses(phase: FMCommentaryPhase): string {
  switch (phase) {
    case "goal":
      return "border-white/55 text-white shadow-[0_0_32px_rgba(16,185,129,0.45)]";
    case "chance":
      return "border-amber-400/80 bg-slate-950/92 text-amber-50 shadow-[0_0_24px_rgba(245,158,11,0.3)]";
    case "card_red":
      return "border-rose-500/80 bg-rose-950/92 text-rose-50 shadow-[0_0_20px_rgba(244,63,94,0.3)]";
    case "card_yellow":
      return "border-yellow-400/80 bg-yellow-950/90 text-yellow-50 shadow-[0_0_18px_rgba(250,204,21,0.24)]";
    case "var":
      return "border-amber-300/80 bg-slate-950/95 text-amber-100 shadow-[0_0_22px_rgba(251,191,36,0.28)]";
    case "sub":
      return "border-sky-400/75 bg-slate-950/92 text-sky-50 shadow-[0_0_18px_rgba(56,189,248,0.24)]";
    case "neutral":
    default:
      return "border-white/15 bg-slate-950/88 text-slate-100 shadow-[0_10px_28px_rgba(2,6,23,0.72)]";
  }
}

function phaseBadgeClasses(phase: FMCommentaryPhase): string {
  switch (phase) {
    case "goal":
      return "bg-white text-slate-950";
    case "chance":
      return "bg-amber-400/20 text-amber-300 border border-amber-400/50";
    case "card_red":
      return "bg-rose-500 text-white";
    case "card_yellow":
      return "bg-yellow-400 text-slate-950";
    case "var":
      return "bg-amber-400 text-slate-950";
    case "sub":
      return "bg-sky-400/20 text-sky-200 border border-sky-400/50";
    case "neutral":
    default:
      return "bg-white/10 text-slate-200 border border-white/15";
  }
}

export function FMCommentaryStrip({
  phase,
  badge,
  headline,
  subline = null,
  minuteLabel = null,
  scoreline = null,
  scorerName = null,
  assistName = null,
  shotXg = null,
  clubColor = "#10b981",
  kind,
  tone,
  onWatchReplay,
  floating = false,
  testId = "pitch-broadcast-banner",
}: FMCommentaryStripProps) {
  const accentHex = clubColor || "#10b981";
  const animKey = `${phase}:${badge}:${headline}:${scoreline || ""}`;
  const isGoal = phase === "goal";
  const isSlideBadge =
    phase === "card_red" || phase === "card_yellow" || phase === "var" || phase === "sub";

  const wrapperClass = floating
    ? "pointer-events-none flex w-full justify-center px-3"
    : "flex w-full justify-center";

  return (
    <div
      data-testid={testId}
      data-banner-kind={kind || phase}
      data-banner-tone={tone || phase}
      data-commentary-phase={phase}
      className={wrapperClass}
    >
      <motion.div
        key={animKey}
        initial={
          isGoal
            ? { opacity: 0, scale: 0.94, y: 10 }
            : isSlideBadge
              ? { opacity: 0, x: -18, y: 4 }
              : { opacity: 0, y: 6 }
        }
        animate={{ opacity: 1, scale: 1, x: 0, y: 0 }}
        transition={transitionForPhase(phase)}
        style={
          isGoal
            ? {
                background: `linear-gradient(95deg, ${accentHex}ee 0%, ${accentHex}cc 52%, rgba(2,6,23,0.95) 100%)`,
              }
            : undefined
        }
        className={`pointer-events-auto relative flex w-full max-w-3xl items-center justify-between gap-3 overflow-hidden rounded-lg border px-3.5 py-2 text-xs backdrop-blur-md ${phaseContainerClasses(phase)}`}
      >
          {/* Left Accent Edge Bar */}
          <span
            aria-hidden="true"
            className="absolute inset-y-0 left-0 w-1"
            style={{
              backgroundColor:
                phase === "chance"
                  ? "#f59e0b"
                  : phase === "card_red"
                    ? "#f43f5e"
                    : phase === "card_yellow"
                      ? "#facc15"
                      : phase === "var"
                        ? "#fbbf24"
                        : phase === "sub"
                          ? "#38bdf8"
                          : accentHex,
            }}
          />

          {/* Goal Flash Sweep */}
          {isGoal && (
            <motion.span
              aria-hidden="true"
              initial={{ x: "-100%", opacity: 0.7 }}
              animate={{ x: "180%", opacity: 0 }}
              transition={{ duration: 0.85, ease: "easeOut" }}
              className="pointer-events-none absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-white/35 to-transparent"
            />
          )}

          {/* Left: Phase Badge + Dynamic Play-by-Play Copy */}
          <div className="flex min-w-0 items-center gap-2.5 pl-1">
            <span
              className={`shrink-0 whitespace-nowrap rounded px-2 py-0.5 text-[10px] font-black uppercase tracking-widest ${phaseBadgeClasses(phase)}`}
            >
              {badge}
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="truncate font-black tracking-tight text-white">
                  {isGoal && scorerName ? `${scorerName} — ${headline}` : headline}
                </span>
                {isGoal && assistName ? (
                  <span
                    data-testid="goal-assist-pill"
                    className="shrink-0 rounded bg-black/35 px-1.5 py-0.5 text-[10px] font-bold text-white/90"
                  >
                    Assist: {assistName}
                  </span>
                ) : null}
                {phase === "chance" && typeof shotXg === "number" && Number.isFinite(shotXg) && shotXg > 0 ? (
                  <span
                    data-testid="live-shot-xg-pill"
                    className="shrink-0 rounded border border-amber-300/60 bg-amber-400/20 px-1.5 py-0.5 font-mono text-[10px] font-black text-amber-200"
                  >
                    {shotXg.toFixed(2)} xG
                  </span>
                ) : null}
              </div>
              {subline && subline !== headline ? (
                <p className="hidden truncate text-[11px] text-slate-200/85 md:block">
                  {subline}
                </p>
              ) : null}
            </div>
          </div>

          {/* Right: Optional Instant Replay Trigger + Score Tick-Up + Minute */}
          <div className="flex shrink-0 items-center gap-2 whitespace-nowrap font-mono font-bold">
            {onWatchReplay ? (
              <button
                type="button"
                data-testid="watch-instant-replay-btn"
                onClick={onWatchReplay}
                className="rounded border border-white/35 bg-black/45 px-2 py-0.5 text-[10px] font-black uppercase tracking-wider text-white transition hover:border-emerald-300 hover:bg-emerald-500 hover:text-slate-950"
              >
                ↺ WATCH REPLAY
              </button>
            ) : null}
            {scoreline ? (
              <motion.span
                key={`score:${scoreline}`}
                initial={isGoal ? { scale: 1.45, y: -4 } : false}
                animate={{ scale: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 450, damping: 18 }}
                data-testid="commentary-score-tick"
                className={`rounded px-2 py-0.5 text-xs font-black ${
                  isGoal ? "bg-black/45 text-white" : "bg-white/10 text-slate-100"
                }`}
              >
                {scoreline}
              </motion.span>
            ) : null}
            {minuteLabel ? (
              <span className="text-[11px] font-black text-emerald-300">{minuteLabel}</span>
            ) : null}
          </div>
      </motion.div>
    </div>
  );
}
