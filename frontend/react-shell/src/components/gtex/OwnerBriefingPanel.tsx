import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Newspaper,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  CheckCircle2,
  XCircle,
  HeartPulse,
  Compass,
  Building2,
  Sprout,
  Coins,
  Users,
  ShieldAlert,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt } from "@/lib/owner";
import {
  briefingTargetLabel,
  briefingTargetPath,
  clubBriefingEndpoint,
  clubBriefingGenerateEndpoint,
  clubBriefingResolveDilemmaEndpoint,
  clubExecuteOperationalDecisionEndpoint,
  useOwnerBriefing,
  type BriefingViewState,
  type DailyBriefing,
  type OperationalRecommendation,
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
  if (norm.includes("executive") || norm.includes("owner")) {
    return (
      <span className="rounded bg-amber-900/40 text-amber-300 border border-amber-500/30 px-2 py-0.5 text-[10px] font-black uppercase">
        Executive Briefing
      </span>
    );
  }
  if (norm.includes("gm") || norm.includes("general")) {
    return (
      <span className="rounded bg-purple-900/40 text-purple-300 border border-purple-500/30 px-2 py-0.5 text-[10px] font-black uppercase">
        General Manager
      </span>
    );
  }
  if (norm.includes("hoyd") || norm.includes("youth") || norm.includes("academy")) {
    return (
      <span className="rounded bg-emerald-900/40 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-black uppercase">
        Head of Youth Dev
      </span>
    );
  }
  if (norm.includes("medical") || norm.includes("doctor") || norm.includes("physio")) {
    return (
      <span className="rounded bg-rose-900/40 text-rose-300 border border-rose-500/30 px-2 py-0.5 text-[10px] font-black uppercase">
        Medical Director
      </span>
    );
  }
  if (norm.includes("finance") || norm.includes("commercial") || norm.includes("treasury")) {
    return (
      <span className="rounded bg-cyan-900/40 text-cyan-300 border border-cyan-500/30 px-2 py-0.5 text-[10px] font-black uppercase">
        Finance & Commercial
      </span>
    );
  }
  return (
    <span className="rounded bg-sky-900/40 text-sky-300 border border-sky-500/30 px-2 py-0.5 text-[10px] font-black uppercase">
      First-Team Manager
    </span>
  );
}

export function OwnerBriefingPanel({
  clubId,
  initialData,
  onSelectDestination,
  onDecisionExecuted,
}: {
  clubId?: string;
  initialData?: DailyBriefing | null;
  onSelectDestination?: (destinationKey: string) => void;
  onDecisionExecuted?: () => void;
}) {
  const queryClient = useQueryClient();
  const [busyGenerating, setBusyGenerating] = useState(false);
  const [resolvingChoiceId, setResolvingChoiceId] = useState<string | null>(null);
  const [executingDecisionId, setExecutingDecisionId] = useState<string | null>(null);
  const [activeReportTab, setActiveReportTab] = useState<string>("all");
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
      queryClient.invalidateQueries({ queryKey: ["club-operations-hub", clubId] });
      toast.success("Fresh authoritative daily briefing compiled from all club departments.");
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
      queryClient.invalidateQueries({ queryKey: ["club-operations-hub", activeClubId] });
      await refetch();
      onDecisionExecuted?.();
      toast.success(data?.outcome || "Boardroom dilemma resolved.");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setResolvingChoiceId(null);
    }
  };

  const handleExecuteDecision = async (decision: OperationalRecommendation, action: "approve" | "reject") => {
    if (!activeClubId) return;
    setExecutingDecisionId(`${decision.decision_id}:${action}`);
    try {
      const { data } = await api.post(clubExecuteOperationalDecisionEndpoint(activeClubId, decision.decision_id), {
        action,
        note: `Executed from Owner Daily Briefing (${action})`,
      });
      queryClient.invalidateQueries({ queryKey: ["owner-daily-briefing", activeClubId] });
      queryClient.invalidateQueries({ queryKey: ["club-operations-hub", activeClubId] });
      queryClient.invalidateQueries({ queryKey: ["owner", "control-center"] });
      await refetch();
      onDecisionExecuted?.();
      toast.success(data?.outcome || `Decision ${action}d.`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setExecutingDecisionId(null);
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
  const execBriefing = briefing?.executive_briefing;
  const urgentRisks = execBriefing?.urgent_risks || [];
  const openRecommendations = (briefing?.department_decisions || []).filter((d) => d.status === "open");
  const decisionHistory = briefing?.decision_history || [];

  const filteredSections =
    activeReportTab === "all"
      ? sections
      : sections.filter(
          (s) => s.section_key === activeReportTab || s.destination_key === activeReportTab
        );

  return (
    <section className={SHELL} data-testid="owner-briefing" aria-labelledby="owner-briefing-heading">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-3">
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
            title="Compile a fresh daily briefing from all 6 club departments"
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
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 text-center">
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
          {typeof metrics.avg_fitness === "number" && (
            <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
              <p className="text-[10px] uppercase font-bold text-slate-400">Conditioning</p>
              <p className="gx-mono text-sm font-black text-sky-300 mt-0.5">{metrics.avg_fitness}%</p>
            </div>
          )}
          {typeof metrics.injured_players === "number" && (
            <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
              <p className="text-[10px] uppercase font-bold text-slate-400">Medical Room</p>
              <p className="gx-mono text-sm font-black text-rose-300 mt-0.5">
                {metrics.injured_players === 0 ? "All Fit" : `${metrics.injured_players} Injured`}
              </p>
            </div>
          )}
          {typeof metrics.ready_academy_prospects === "number" && (
            <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
              <p className="text-[10px] uppercase font-bold text-slate-400">Academy Ready</p>
              <p className="gx-mono text-sm font-black text-amber-300 mt-0.5">
                {metrics.ready_academy_prospects} Prospects
              </p>
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

      {urgentRisks.length > 0 && (
        <div
          data-testid="owner-briefing-urgent-risks"
          className="mt-4 rounded-xl border border-rose-500/30 bg-rose-950/20 p-3.5 space-y-2"
        >
          <div className="flex items-center gap-2 text-xs font-black uppercase tracking-wider text-rose-300">
            <ShieldAlert size={14} />
            <span>Operational Watchlist & Risk Flags ({urgentRisks.length})</span>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {urgentRisks.map((risk) => (
              <div
                key={risk.risk_id}
                className="rounded-lg border border-white/10 bg-black/40 p-2.5 flex flex-col justify-between gap-1.5"
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-white">{risk.title}</span>
                    <span
                      className={`text-[9px] font-black uppercase px-1.5 py-0.5 rounded ${
                        risk.severity === "high"
                          ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                          : risk.severity === "medium"
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                          : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                      }`}
                    >
                      {risk.severity}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-300 mt-1">{risk.detail}</p>
                </div>
                {onSelectDestination && risk.department && (
                  <button
                    type="button"
                    onClick={() => onSelectDestination(risk.department)}
                    className="self-start text-[10px] font-bold uppercase tracking-wider text-sky-300 hover:text-sky-200 flex items-center gap-1"
                  >
                    <span>Inspect Department</span>
                    <ArrowRight size={11} />
                  </button>
                )}
              </div>
            ))}
          </div>
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
              <p className="leading-relaxed text-emerald-100">
                {dilemma.resolution_outcome || "Dilemma resolved by owner decree."}
              </p>
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

      {openRecommendations.length > 0 && (
        <div
          data-testid="owner-briefing-department-decisions"
          className="mt-4 rounded-xl border border-sky-500/30 bg-sky-950/20 p-4 space-y-3"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-black uppercase tracking-wider text-sky-300">
              Departmental Sign-Off Queue ({openRecommendations.length})
            </h3>
            <span className="text-[10px] font-semibold text-slate-400">
              Authoritative state & treasury actions
            </span>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {openRecommendations.map((dec) => {
              const busyApprove = executingDecisionId === `${dec.decision_id}:approve`;
              const busyReject = executingDecisionId === `${dec.decision_id}:reject`;
              return (
                <div
                  key={dec.decision_id}
                  data-testid={`operational-decision-${dec.decision_id}`}
                  className="rounded-xl border border-white/10 bg-black/40 p-3.5 flex flex-col justify-between gap-3"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <RoleBadge role={dec.staff_role} />
                      <span className="gx-mono text-[11px] font-bold text-amber-300">
                        {dec.cost_gtex > 0 ? `${fmt(dec.cost_gtex)} GTEX` : "No Fee"}
                      </span>
                    </div>
                    <p className="mt-2 text-sm font-bold text-white">{dec.title}</p>
                    <p className="mt-1 text-xs text-slate-300 leading-relaxed">{dec.summary}</p>
                    <p className="mt-1.5 text-[11px] font-semibold text-emerald-300">{dec.effects_preview}</p>
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-white/10">
                    <span className="text-[10px] text-slate-400">Proposed by {dec.staff_name}</span>
                    <div className="flex items-center gap-2">
                      {onSelectDestination && (
                        <button
                          type="button"
                          onClick={() => onSelectDestination(dec.department)}
                          className="rounded-lg border border-white/15 bg-white/5 px-2.5 py-1 text-[10px] font-bold uppercase text-slate-200 hover:bg-white/10"
                        >
                          3D Room
                        </button>
                      )}
                      <button
                        type="button"
                        data-testid={`reject-decision-${dec.decision_id}`}
                        disabled={Boolean(executingDecisionId)}
                        onClick={() => handleExecuteDecision(dec, "reject")}
                        className="inline-flex items-center gap-1 rounded-lg border border-rose-500/40 bg-rose-950/40 px-2.5 py-1 text-[10px] font-bold uppercase text-rose-200 hover:bg-rose-900/50 disabled:opacity-50"
                      >
                        <XCircle size={12} />
                        <span>{busyReject ? "…" : "Defer"}</span>
                      </button>
                      <button
                        type="button"
                        data-testid={`approve-decision-${dec.decision_id}`}
                        disabled={Boolean(executingDecisionId)}
                        onClick={() => handleExecuteDecision(dec, "approve")}
                        className="inline-flex items-center gap-1 rounded-lg border border-emerald-500/50 bg-emerald-600/30 px-3 py-1 text-[10px] font-black uppercase text-emerald-200 hover:bg-emerald-600/50 disabled:opacity-50"
                      >
                        <CheckCircle2 size={12} />
                        <span>{busyApprove ? "Executing…" : "Approve"}</span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {sections.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1.5 border-b border-white/10 pb-2.5">
          {[
            { key: "all", label: "All 6 Reports" },
            { key: "executive_briefing", label: "Executive" },
            { key: "managers_report", label: "Manager" },
            { key: "general_managers_report", label: "General Manager" },
            { key: "hoyd_report", label: "Academy (HOYD)" },
            { key: "medical_directors_report", label: "Medical" },
            { key: "financial_commercial_report", label: "Finance & Commercial" },
          ].map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveReportTab(tab.key)}
              className={`rounded-lg px-2.5 py-1 text-[11px] font-bold uppercase transition ${
                activeReportTab === tab.key
                  ? "bg-sky-500/30 text-white border border-sky-400/50"
                  : "bg-black/30 text-slate-400 border border-white/10 hover:text-slate-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {filteredSections.length > 0 ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {filteredSections.map((sec, idx) => (
            <div
              key={sec.section_key || idx}
              data-testid={`briefing-section-${sec.section_key || idx}`}
              className="rounded-xl border border-white/10 bg-slate-950/60 p-3.5 flex flex-col justify-between gap-2 hover:border-white/20 transition-colors"
            >
              <div className="space-y-1.5">
                <div className="flex items-center justify-between gap-2">
                  <RoleBadge role={sec.role} />
                  <span className="text-[11px] font-bold text-slate-300">{sec.sender}</span>
                </div>
                <p className="text-sm font-bold text-white">{sec.title}</p>
                <p className="text-xs leading-relaxed text-slate-300">{sec.summary}</p>
              </div>
              {onSelectDestination && sec.destination_key && (
                <div className="pt-2 border-t border-white/5 flex justify-end">
                  <button
                    type="button"
                    onClick={() => onSelectDestination(sec.destination_key!)}
                    className="inline-flex items-center gap-1 text-[11px] font-bold uppercase tracking-wider text-sky-300 hover:text-sky-200"
                  >
                    <span>Visit 3D Office</span>
                    <ArrowRight size={12} />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-4 rounded-xl border border-dashed border-white/15 p-4 text-center text-xs text-slate-400">
          <p className="font-bold text-white uppercase">Daily Briefing Up to Date</p>
          <p className="mt-1 text-slate-400">
            Click Refresh above to compile a fresh boardroom report from your GM, First-Team Manager, Medical Director, and HOYD.
          </p>
        </div>
      )}

      {decisionHistory.length > 0 && (
        <div
          data-testid="owner-briefing-decision-history"
          className="mt-4 rounded-xl border border-white/10 bg-black/30 p-3.5 space-y-2"
        >
          <p className="text-[11px] font-black uppercase tracking-wider text-slate-400">
            Recent Persisted Owner Decisions ({decisionHistory.length})
          </p>
          <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
            {decisionHistory.slice(0, 6).map((h: any) => (
              <div
                key={h.history_id || h.decision_id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/5 bg-slate-950/60 px-3 py-2 text-xs"
              >
                <div>
                  <span className="font-bold text-white">{h.title}</span>
                  <span className="ml-2 text-slate-400">{h.outcome}</span>
                </div>
                <span className="gx-mono text-[10px] text-emerald-300 uppercase">
                  Day {h.world_day} · {h.action_taken}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

export default OwnerBriefingPanel;
