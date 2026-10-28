import React from "react";
import { Link } from "react-router-dom";
import { Newspaper, AlertTriangle, ArrowRight } from "lucide-react";
import {
  briefingTargetLabel,
  briefingTargetPath,
  useOwnerBriefing,
  type BriefingViewState,
} from "@/lib/ownerBriefing";

const SHELL =
  "rounded-2xl border border-sky-400/20 bg-gradient-to-br from-[#0b1a33] via-[#0a1428] to-[#060d1a] p-5 sm:p-6 shadow-xl";

/**
 * Daily owner briefing. Cards are rendered only from persisted, verified events; where the backend
 * contract is missing or empty the panel says so instead of showing invented stories.
 */
export function OwnerBriefingView({ state, onRetry }: { state: BriefingViewState; onRetry?: () => void }) {
  return (
    <section
      className={SHELL}
      data-testid="owner-briefing"
      aria-labelledby="owner-briefing-heading"
      aria-busy={state.status === "loading"}
    >
      <div className="flex items-center gap-2">
        <Newspaper size={16} className="text-amber-300" aria-hidden="true" />
        <h2 id="owner-briefing-heading" className="gx-eyebrow !m-0">
          Owner daily briefing
        </h2>
      </div>

      {state.status === "loading" && (
        <p role="status" data-testid="owner-briefing-loading" className="mt-4 text-sm text-slate-300">
          Loading your briefing…
        </p>
      )}

      {state.status === "unavailable" && (
        <div data-testid="owner-briefing-unavailable" className="mt-4 rounded-xl border border-dashed border-white/15 p-4">
          <p className="text-sm font-bold uppercase text-slate-100">Daily briefing not available yet</p>
          <p className="mt-1 text-sm text-slate-400">
            Briefings are built from verified, persisted GTEX events. That service has not been published, so no
            stories are shown.
          </p>
        </div>
      )}

      {state.status === "error" && (
        <div role="alert" data-testid="owner-briefing-error" className="mt-4 space-y-3">
          <p className="flex items-start gap-2 text-sm text-red-300">
            <AlertTriangle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
            <span>We could not load your briefing.</span>
          </p>
          {onRetry && (
            <button type="button" onClick={onRetry} className="gx-btn gx-btn-secondary text-xs">
              Retry
            </button>
          )}
        </div>
      )}

      {state.status === "empty" && (
        <div data-testid="owner-briefing-empty" className="mt-4 rounded-xl border border-dashed border-white/15 p-4">
          <p className="text-sm font-bold uppercase text-slate-100">Nothing to report</p>
          <p className="mt-1 text-sm text-slate-400">
            No verified events were recorded for your club{state.worldDate ? ` on ${state.worldDate}` : ""}.
          </p>
        </div>
      )}

      {state.status === "ready" && (
        <div className="mt-4 space-y-3">
          {state.stale && (
            <p role="status" data-testid="owner-briefing-stale" className="flex items-center gap-2 text-xs text-amber-300">
              <AlertTriangle size={14} aria-hidden="true" />
              Showing the last saved briefing; the latest refresh failed.
            </p>
          )}
          <ul className="space-y-3" aria-label="Verified events">
            {state.briefing.events.map((event) => {
              const path = briefingTargetPath(event.target);
              const linkLabel = briefingTargetLabel(event.target);
              return (
                <li
                  key={event.eventId}
                  data-testid="owner-briefing-card"
                  data-event-id={event.eventId}
                  className="rounded-xl border border-white/10 bg-black/30 p-4"
                >
                  <p className="text-sm font-bold text-white">{event.headline}</p>
                  {event.detail && <p className="mt-1 text-sm text-slate-300">{event.detail}</p>}
                  <p className="gx-mono mt-1 text-[11px] text-slate-500">
                    <time dateTime={event.occurredAt}>{event.occurredAt}</time>
                  </p>
                  {path && linkLabel && (
                    <Link
                      to={path}
                      className="mt-3 inline-flex min-h-[44px] items-center gap-1 text-xs font-bold uppercase tracking-wider text-sky-300 hover:text-sky-200"
                    >
                      {linkLabel} <ArrowRight size={12} aria-hidden="true" />
                    </Link>
                  )}
                </li>
              );
            })}
          </ul>
          {state.briefing.rejectedEventCount > 0 && (
            <p data-testid="owner-briefing-rejected" className="text-xs text-slate-500">
              {state.briefing.rejectedEventCount} event(s) were hidden because they could not be verified.
            </p>
          )}
          {state.briefing.explanation && (
            <p data-testid="owner-briefing-explanation" className="border-t border-white/10 pt-3 text-xs italic text-slate-400">
              Commentary (explanatory only): {state.briefing.explanation}
            </p>
          )}
        </div>
      )}
    </section>
  );
}

export function OwnerBriefingPanel() {
  return <OwnerBriefingView state={useOwnerBriefing()} />;
}

export default OwnerBriefingPanel;
