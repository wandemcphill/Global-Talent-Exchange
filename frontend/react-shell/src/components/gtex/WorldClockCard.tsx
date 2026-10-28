import React from "react";
import { Clock, PauseCircle, PlayCircle, AlertTriangle, CalendarDays } from "lucide-react";
import {
  formatProgressionRate,
  formatWorldDate,
  formatWorldTime,
  useWorldClock,
  type WorldClock,
} from "@/lib/worldClock";

export type WorldClockViewState =
  | { status: "loading" }
  | { status: "error"; onRetry?: () => void }
  | { status: "ready"; clock: WorldClock; /** A later refresh failed; the snapshot shown is the last server value. */ stale?: boolean; onRetry?: () => void };

const SHELL =
  "rounded-2xl border border-sky-400/20 bg-gradient-to-br from-[#0b1a33] via-[#0a1428] to-[#060d1a] p-5 sm:p-6 shadow-xl";

/**
 * Presentational clock. It prints exactly what the server returned; it holds no timers and never
 * reads the device clock, so it cannot drift or invent time.
 */
export function WorldClockView({ state }: { state: WorldClockViewState }) {
  return (
    <section
      className={SHELL}
      data-testid="world-clock-card"
      aria-labelledby="world-clock-heading"
      aria-busy={state.status === "loading"}
    >
      <div className="flex items-center gap-2">
        <Clock size={16} className="text-amber-300" aria-hidden="true" />
        <h2 id="world-clock-heading" className="gx-eyebrow !m-0">
          GTEX world time
        </h2>
      </div>

      {state.status === "loading" && (
        <p role="status" data-testid="world-clock-loading" className="mt-4 text-sm text-slate-300">
          Loading GTEX world time…
        </p>
      )}

      {state.status === "error" && (
        <div role="alert" data-testid="world-clock-error" className="mt-4 space-y-3">
          <p className="flex items-start gap-2 text-sm text-red-300">
            <AlertTriangle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
            <span>GTEX world time is unavailable right now. No time is shown rather than a guess.</span>
          </p>
          {state.onRetry && (
            <button type="button" onClick={state.onRetry} className="gx-btn gx-btn-secondary text-xs">
              Retry
            </button>
          )}
        </div>
      )}

      {state.status === "ready" && (
        <div className="mt-4 space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div role="status" aria-live="polite">
              <p className="gx-display text-3xl font-black uppercase leading-none text-white sm:text-4xl" data-testid="world-clock-date">
                <time dateTime={state.clock.worldDate}>{formatWorldDate(state.clock.worldDate)}</time>
              </p>
              <p className="gx-mono mt-2 text-lg text-sky-200" data-testid="world-clock-time">
                <time dateTime={state.clock.worldTime}>{formatWorldTime(state.clock.worldTime)}</time>
              </p>
            </div>
            <span
              data-testid="world-clock-status"
              className={`inline-flex w-fit items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-black uppercase tracking-wider ${
                state.clock.isPaused
                  ? "border-amber-400/50 bg-amber-400/10 text-amber-300"
                  : "border-emerald-400/40 bg-emerald-400/10 text-emerald-300"
              }`}
            >
              {state.clock.isPaused ? (
                <PauseCircle size={14} aria-hidden="true" />
              ) : (
                <PlayCircle size={14} aria-hidden="true" />
              )}
              {state.clock.isPaused ? "Paused" : "Running"}
            </span>
          </div>

          <dl className="grid grid-cols-1 gap-3 border-t border-white/10 pt-4 text-xs sm:grid-cols-3">
            <div>
              <dt className="uppercase tracking-wider text-slate-400">Progression rate</dt>
              <dd className="gx-mono mt-1 text-sm text-white" data-testid="world-clock-rate">
                {formatProgressionRate(state.clock.progressionRate)}
              </dd>
            </div>
            <div>
              <dt className="uppercase tracking-wider text-slate-400">Season length</dt>
              <dd className="gx-mono mt-1 text-sm text-white" data-testid="world-clock-season-length">
                {state.clock.virtualMonthsPerSeason} virtual months
              </dd>
            </div>
            <div>
              <dt className="uppercase tracking-wider text-slate-400">Current season</dt>
              {state.clock.currentSeasonLabel ? (
                <dd className="gx-mono mt-1 text-sm font-bold text-emerald-400" data-testid="world-clock-season-label">
                  {state.clock.currentSeasonLabel}
                  {typeof state.clock.gtexYearsRunning === "number" && ` (Year ${state.clock.gtexYearsRunning})`}
                </dd>
              ) : (
                <dd className="mt-1 flex items-start gap-1.5 text-sm text-slate-300" data-testid="world-clock-season-unavailable">
                  <CalendarDays size={14} className="mt-0.5 shrink-0 text-slate-400" aria-hidden="true" />
                  <span>Not shown: awaiting the approved season calendar.</span>
                </dd>
              )}
            </div>
          </dl>

          {state.stale && (
            <p role="status" data-testid="world-clock-stale" className="flex items-center gap-2 text-xs text-amber-300">
              <AlertTriangle size={14} aria-hidden="true" />
              Showing the last server snapshot; the latest refresh failed.
              {state.onRetry && (
                <button type="button" onClick={state.onRetry} className="underline underline-offset-2">
                  Retry
                </button>
              )}
            </p>
          )}
        </div>
      )}
    </section>
  );
}

/** Connected card: reads `GET /api/world/clock`. */
export function WorldClockCard() {
  const { data, isLoading, isError, refetch } = useWorldClock();
  const onRetry = () => {
    void refetch();
  };
  if (data) return <WorldClockView state={{ status: "ready", clock: data, stale: isError, onRetry }} />;
  if (isLoading) return <WorldClockView state={{ status: "loading" }} />;
  return <WorldClockView state={{ status: "error", onRetry }} />;
}

export default WorldClockCard;
