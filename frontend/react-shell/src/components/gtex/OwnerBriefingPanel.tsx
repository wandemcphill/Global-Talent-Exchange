import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Newspaper,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  Sparkles,
  ShieldAlert,
  Users,
  Coins,
  Award,
  Sprout,
  UserCheck,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt } from "@/lib/owner";
import {
  briefingTargetLabel,
  briefingTargetPath,
  clubBriefingEndpoint,
  clubBriefingGenerateEndpoint,
  clubBriefingResolveDilemmaEndpoint,
  useOwnerBriefing,
  type BriefingViewState,
  type DailyBriefing,
  type StaffBriefingSection,
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

function RoleBadge({ role }: { role: string }) {
  const norm = String(role || "").toLowerCase();
  if (norm.includes("gm") || norm.includes("general")) {
    return <span className="rounded bg-purple-900/40 text-purple-300 border border-purple-500/30 px-2 py-0.5 text-[10px] font-black uppercase">General Manager</span>;
  }
  if (norm.includes("hoyd") || norm.includes("youth")) {
    return <span className="rounded bg-emerald-900/40 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-black uppercase">Head of Youth Dev</span>;
  }
  return <span className="rounded bg-sky-900/40 text-sky-300 border border-sky-500/30 px-2 py-0.5 text-[10px] font-black uppercase">First-Team Manager</span>;
}

export function OwnerBriefingPanel({
  clubId,
  initialData,
}: {
  clubId?: string;
  initialData?: DailyBriefing | null;
}) {
  const queryClient = useQueryClient();
  const [busyGenerating, setBusyGenerating] = useState(false);
  const [resolvingChoiceId, setResolvingChoiceId] = useState<string | null>(null);
  const activeClubId = clubId;

  const {
    data: fetchedData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["owner-daily-briefing", clubId],
    queryFn: async () => {
      if (!clubId) return null;
      try {
        const { data } = await api.get(clubBriefingEndpoint(clubId));
        return data as DailyBriefing;
      } catch {
        return null;
      }
    },
    enabled: Boolean(clubId),
    initialData: initialData || undefined,
  });

  const briefing = fetchedData || initialData;

  const handleGenerate = async () => {
    if (!clubId) return;
    setBusyGenerating(true);
    try {
      await api.post(clubBriefingGenerateEndpoint(clubId));
      await refetch();
      toast.success("Fresh AI owner briefing compiled by club staff.");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyGenerating(false);
    }
  };

  const handleResolveDilemma = async (choiceId: string) => {
    if (!activeClubId) return;
    setResolvingChoiceId(choiceId);
    try {
      const { data } = await api.post(clubBriefingResolveDilemmaEndpoint(activeClubId), { choice_id: choiceId });
      queryClient.invalidateQueries({ queryKey: ["owner-briefing", activeClubId] });
      queryClient.invalidateQueries({ queryKey: ["owner-daily-briefing", activeClubId] });
      await refetch();
      toast.success(data?.outcome || "Boardroom dilemma resolved.");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setResolvingChoiceId(null);
    }
  };

  if (!clubId && !briefing) {
    return <OwnerBriefingView state={useOwnerBriefing()} />;
  }

  if (isLoading && !briefing) {
    return (
      <section className={SHELL} data-testid="owner-briefing">
        <div className="flex items-center gap-2">
          <Newspaper size={16} className="text-amber-300" />
          <h2 className="gx-eyebrow !m-0">Owner daily briefing</h2>
        </div>
        <p className="mt-4 text-sm text-slate-300">Loading your executive briefing…</p>
      </section>
    );
  }

  const sections: StaffBriefingSection[] = briefing?.sections || [];
  const metrics = briefing?.metrics;
  const dilemma = briefing?.boardroom_dilemma;

  return (
    <section className={SHELL} data-testid="owner-briefing" aria-labelledby="owner-briefing-heading">
      <div className="flex items-center justify-between border-b border-white/10 pb-3">
        <div className="flex items-center gap-2">
          <Newspaper size={16} className="text-amber-300" />
          <h2 id="owner-briefing-heading" className="gx-eyebrow !m-0">
            Owner Daily Briefing
          </h2>
          {briefing?.world_day && (
            <span className="gx-mono text-[10px] text-emerald-400 bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded">
              Day {briefing.world_day}
            </span>
          )}
        </div>
        {clubId && (
          <button
            type="button"
            onClick={handleGenerate}
            disabled={busyGenerating}
            className="flex items-center gap-1.5 text-xs text-sky-300 hover:text-sky-200 font-bold uppercase transition"
            title="Generate a fresh daily briefing from GM, Manager & HOYD"
          >
            <RefreshCw size={13} className={busyGenerating ? "animate-spin" : ""} />
            <span>{busyGenerating ? "Compiling…" : "Refresh"}</span>
          </button>
        )}
      </div>

      {briefing?.headline && (
        <div className="mt-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-3.5">
          <p className="text-xs uppercase font-black tracking-wider text-emerald-300">Executive Summary</p>
          <p className="text-base font-bold text-white mt-1">{briefing.headline}</p>
          {briefing.summary && <p className="text-xs leading-5 text-slate-300 mt-1">{briefing.summary}</p>}
        </div>
      )}

      {metrics && (
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-center">
          {typeof metrics.cash_gtex === "number" && (
            <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
              <p className="text-[10px] uppercase font-bold text-slate-400">Cash</p>
              <p className="gx-mono text-sm font-black text-white mt-0.5">{fmt(metrics.cash_gtex)} GTX</p>
            </div>
          )}
          {typeof metrics.avg_morale === "number" && (
            <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
              <p className="text-[10px] uppercase font-bold text-slate-400">Squad Morale</p>
              <p className="gx-mono text-sm font-black text-emerald-300 mt-0.5">{metrics.avg_morale}/100</p>
            </div>
          )}
          {typeof metrics.ready_academy_prospects === "number" && (
            <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
              <p className="text-[10px] uppercase font-bold text-slate-400">Academy Ready</p>
              <p className="gx-mono text-sm font-black text-amber-300 mt-0.5">{metrics.ready_academy_prospects} Prospects</p>
            </div>
          )}
          {typeof metrics.open_decisions === "number" && (
            <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
              <p className="text-[10px] uppercase font-bold text-slate-400">Open Actions</p>
              <p className="gx-mono text-sm font-black text-cyan-300 mt-0.5">{metrics.open_decisions} Pending</p>
            </div>
          )}
        </div>
      )}

      {dilemma && (
        <div
          data-testid="owner-briefing-dilemma"
          className="mt-4 rounded-xl border border-amber-500/40 bg-gradient-to-br from-amber-950/40 via-[#0d1627] to-[#070e1c] p-4 sm:p-5 shadow-lg space-y-3.5"
        >
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-2.5">
            <div className="flex items-center gap-2">
              <AlertTriangle size={16} className="text-amber-400" />
              <h3 className="text-xs font-black uppercase tracking-wider text-amber-300">
                Boardroom Dilemma · Executive Disagreement
              </h3>
            </div>
            {dilemma.status === "resolved" ? (
              <span
                data-testid="dilemma-status-resolved"
                className="rounded bg-emerald-950/80 border border-emerald-500/40 px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider text-emerald-300"
              >
                Resolved
              </span>
            ) : (
              <span
                data-testid="dilemma-status-open"
                className="rounded bg-amber-950/80 border border-amber-500/40 px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider text-amber-300 animate-pulse"
              >
                Decision Required
              </span>
            )}
          </div>

          <div>
            <h4 className="text-base font-bold text-white">{dilemma.title}</h4>
            <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs font-semibold">
              <span className="text-amber-200">{dilemma.role_a}</span>
              <span className="text-slate-500 font-black text-[10px] uppercase">vs</span>
              <span className="text-sky-200">{dilemma.role_b}</span>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-slate-300">{dilemma.conflict_summary}</p>
          </div>

          {dilemma.status === "resolved" && (
            <div
              data-testid="dilemma-resolution-outcome"
              className="rounded-lg border border-emerald-500/40 bg-emerald-950/40 p-3 text-xs text-emerald-200"
            >
              <span className="font-black uppercase tracking-wider text-[10px] text-emerald-400 block mb-1">
                Resolution Outcome
              </span>
              <p className="leading-relaxed text-emerald-100">{dilemma.resolution_outcome || "Dilemma resolved by owner decree."}</p>
            </div>
          )}

          {dilemma.status === "open" && (
            <div className="space-y-2 pt-1">
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Owner Decision · Select Executive Path:
              </p>
              <div className="grid gap-2.5 sm:grid-cols-3">
                {dilemma.choices.map((choice) => {
                  const isSelected = resolvingChoiceId === choice.choice_id;
                  return (
                    <button
                      key={choice.choice_id}
                      type="button"
                      data-testid={`dilemma-choice-${choice.choice_id}`}
                      disabled={Boolean(resolvingChoiceId)}
                      onClick={() => handleResolveDilemma(choice.choice_id)}
                      className="group relative flex flex-col justify-between rounded-xl border border-white/10 bg-black/40 p-3.5 text-left transition hover:border-amber-400/60 hover:bg-amber-950/20 disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      <div>
                        <div className="flex items-center justify-between gap-1">
                          <span className="text-xs font-black text-white group-hover:text-amber-300 transition-colors">
                            {choice.label}
                          </span>
                          {isSelected && <RefreshCw size={12} className="animate-spin text-amber-300" />}
                        </div>
                        <p className="mt-1 text-[11px] leading-relaxed text-slate-300">{choice.summary}</p>
                      </div>
                      <div className="mt-3 pt-2 border-t border-white/5 space-y-1">
                        <p className="text-[10px] text-slate-400">
                          Backs: <span className="font-semibold text-slate-200">{choice.backed_role}</span>
                        </p>
                        <p className="text-[10px] font-semibold text-emerald-300">{choice.effects_preview}</p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {sections.length > 0 ? (
        <div className="mt-4 space-y-3">
          {sections.map((sec, idx) => (
            <div
              key={idx}
              className="rounded-xl border border-white/10 bg-slate-950/60 p-3.5 space-y-1.5 hover:border-white/20 transition-colors"
            >
              <div className="flex items-center justify-between">
                <RoleBadge role={sec.role} />
                <span className="text-[11px] font-bold text-slate-300">{sec.sender}</span>
              </div>
              <p className="text-sm font-bold text-white">{sec.title}</p>
              <p className="text-xs leading-relaxed text-slate-300">{sec.summary}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-4 rounded-xl border border-dashed border-white/15 p-4 text-center text-xs text-slate-400">
          <p className="font-bold text-white uppercase">Daily Briefing Up to Date</p>
          <p className="mt-1 text-slate-400">
            Click Refresh above to compile a fresh boardroom report from your GM, First-Team Manager, and HOYD.
          </p>
        </div>
      )}
    </section>
  );
}

export default OwnerBriefingPanel;
