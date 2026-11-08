/**
 * GTEX Living Football Ecosystem — Stage 3 Autonomous Staff & Boardroom Dilemmas
 * BoardroomDilemmaModal: Executive Dilemma Resolution & Consequence HUD.
 *
 * Surfaced when the owner interacts with the 3D Holographic Dilemma Projector
 * or clicks the Dilemma Alert Pill in the Executive Boardroom Suite.
 *
 * Facilitates selecting between competing strategic proposals (e.g., Manager vs GM),
 * visualizing projected relationship deltas and treasury costs, and ratifying
 * authoritative owner decisions.
 */

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  X,
  AlertTriangle,
  Scale,
  Sparkles,
  Coins,
  CheckCircle2,
  Users,
  Flame,
  ShieldAlert,
  Send,
  ArrowRight,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import {
  clubActiveDilemmaEndpoint,
  clubResolveDilemmaEndpoint,
  type BoardroomDilemma,
  type BoardroomDilemmaChoice,
  type ResolveDilemmaResponse,
} from "@/lib/ownerBriefing";

export interface BoardroomDilemmaModalProps {
  clubId: string;
  isOpen: boolean;
  onClose: () => void;
  onResolveComplete?: (response: ResolveDilemmaResponse) => void;
}

export const BoardroomDilemmaModal: React.FC<BoardroomDilemmaModalProps> = ({
  clubId,
  isOpen,
  onClose,
  onResolveComplete,
}) => {
  const queryClient = useQueryClient();
  const [selectedChoiceId, setSelectedChoiceId] = useState<string | null>(null);
  const [decisionNote, setDecisionNote] = useState<string>("");
  const [resolutionResult, setResolutionResult] = useState<ResolveDilemmaResponse | null>(null);

  const {
    data: dilemma,
    isLoading,
    refetch,
  } = useQuery<BoardroomDilemma | null>({
    queryKey: ["club-active-dilemma", clubId],
    queryFn: async () => {
      try {
        const res = await api.get<BoardroomDilemma>(clubActiveDilemmaEndpoint(clubId));
        return res.data;
      } catch (err) {
        console.warn("Failed to fetch active boardroom dilemma:", err);
        return null;
      }
    },
    enabled: isOpen && !!clubId,
  });

  const resolveMutation = useMutation({
    mutationFn: async (payload: { choiceId: string; note?: string }) => {
      if (!dilemma) throw new Error("No active dilemma to resolve");
      const res = await api.post<ResolveDilemmaResponse>(
        clubResolveDilemmaEndpoint(clubId, dilemma.dilemma_id),
        {
          choice_id: payload.choiceId,
          decision_note: payload.note || undefined,
        }
      );
      return res.data;
    },
    onSuccess: (data) => {
      setResolutionResult(data);
      toast.success("Boardroom resolution ratified successfully!");
      queryClient.invalidateQueries({ queryKey: ["club-active-dilemma", clubId] });
      queryClient.invalidateQueries({ queryKey: ["club-delegated-decisions", clubId] });
      queryClient.invalidateQueries({ queryKey: ["club-persona-details", clubId] });
      queryClient.invalidateQueries({ queryKey: ["club-briefing", clubId] });
      onResolveComplete?.(data);
    },
    onError: (err) => {
      toast.error(errMsg(err) || "Failed to ratify boardroom decision");
    },
  });

  if (!isOpen) return null;

  const handleSelectChoice = (choiceId: string) => {
    setSelectedChoiceId(choiceId);
  };

  const handleRatify = () => {
    if (!selectedChoiceId) return;
    resolveMutation.mutate({
      choiceId: selectedChoiceId,
      note: decisionNote.trim() || undefined,
    });
  };

  const getUrgencyBadge = (urgency?: string) => {
    switch (urgency) {
      case "critical":
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-rose-500/40 bg-rose-500/20 px-2.5 py-0.5 text-xs font-bold text-rose-300">
            <Flame className="h-3.5 w-3.5 animate-pulse text-rose-400" />
            CRITICAL STANDOFF
          </span>
        );
      case "important":
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/40 bg-amber-500/20 px-2.5 py-0.5 text-xs font-bold text-amber-300">
            <ShieldAlert className="h-3.5 w-3.5 text-amber-400" />
            IMPORTANT DISPUTE
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-sky-500/40 bg-sky-500/20 px-2.5 py-0.5 text-xs font-bold text-sky-300">
            <Scale className="h-3.5 w-3.5 text-sky-400" />
            ROUTINE DILEMMA
          </span>
        );
    }
  };

  const renderDeltaPills = (deltas?: Record<string, number>) => {
    if (!deltas || Object.keys(deltas).length === 0) return null;
    return (
      <div className="flex flex-wrap gap-1 mt-1">
        {Object.entries(deltas).map(([k, v]) => {
          const isPositive = v > 0;
          return (
            <span
              key={k}
              className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-mono font-medium ${
                isPositive
                  ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-300"
                  : "bg-rose-500/10 border border-rose-500/30 text-rose-300"
              }`}
            >
              {isPositive ? <TrendingUp className="h-2.5 w-2.5" /> : <TrendingDown className="h-2.5 w-2.5" />}
              {k.replace("delta_", "")}: {isPositive ? `+${v}` : `${v}`}
            </span>
          );
        })}
      </div>
    );
  };

  return (
    <div
      data-testid="boardroom-dilemma-modal"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in"
    >
      <div className="relative w-full max-w-3xl overflow-hidden rounded-2xl border border-emerald-500/30 bg-slate-900/95 shadow-2xl backdrop-blur-xl">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-white/10 px-6 py-4 bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-emerald-500/30 bg-emerald-500/10">
              <Scale className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white">Boardroom Strategic Dilemma</h2>
                {dilemma && getUrgencyBadge(dilemma.urgency)}
              </div>
              <p className="text-xs text-slate-400">
                Authoritative executive arbitration & consequence simulation
              </p>
            </div>
          </div>
          <button
            type="button"
            data-testid="close-dilemma-modal-btn"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="max-h-[75vh] overflow-y-auto px-6 py-5 space-y-6">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Sparkles className="h-8 w-8 animate-spin text-emerald-400" />
              <p className="mt-3 text-sm text-slate-300">Convening executive staff & calculating stakes...</p>
            </div>
          ) : !dilemma ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <CheckCircle2 className="h-10 w-10 text-emerald-400" />
              <h3 className="mt-2 text-base font-bold text-white">No Active Dilemma Pending</h3>
              <p className="mt-1 text-xs text-slate-400">
                Executive leadership is aligned. All operational departments are operating smoothly.
              </p>
              <button
                type="button"
                onClick={onClose}
                className="mt-4 rounded-lg bg-emerald-500/20 border border-emerald-500/30 px-4 py-1.5 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/30"
              >
                Return to Suite
              </button>
            </div>
          ) : resolutionResult ? (
            /* Post-Resolution Success State */
            <div className="space-y-4 py-4">
              <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-5 text-center">
                <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-400" />
                <h3 className="mt-3 text-lg font-bold text-white">Strategic Directive Ratified</h3>
                <p className="mt-1 text-xs text-emerald-200">
                  {resolutionResult.narrative_outcome}
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4">
                  <div className="text-xs font-semibold uppercase text-slate-400">Selected Choice</div>
                  <div className="mt-1 text-sm font-bold text-white">{resolutionResult.selected_choice.label}</div>
                  <p className="mt-1 text-xs text-slate-300">{resolutionResult.selected_choice.summary}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4">
                  <div className="text-xs font-semibold uppercase text-slate-400">Financial Impact</div>
                  <div className="mt-1 flex items-center gap-1 text-sm font-bold text-amber-400">
                    <Coins className="h-4 w-4" />
                    <span>
                      {resolutionResult.selected_choice.cost_gtex && resolutionResult.selected_choice.cost_gtex > 0
                        ? `-₦${resolutionResult.selected_choice.cost_gtex.toLocaleString()} GTEX`
                        : "₦0 GTEX (Budget Neutral)"}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] text-slate-400">Recorded authoritatively to club ledger.</p>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-xl bg-emerald-500 px-5 py-2 text-xs font-bold text-slate-950 hover:bg-emerald-400"
                >
                  Close & Refresh Suite
                </button>
              </div>
            </div>
          ) : (
            /* Active Dilemma Resolution Workspace */
            <>
              {/* Conflicting Role Heads Banner */}
              <div className="relative overflow-hidden rounded-xl border border-white/10 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 p-4">
                <div className="grid grid-cols-1 md:grid-cols-5 items-center gap-4 text-center md:text-left">
                  {/* Role A */}
                  <div className="md:col-span-2 space-y-1">
                    <div className="inline-block rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-mono font-bold uppercase text-emerald-300">
                      {dilemma.role_a_label || dilemma.role_a}
                    </div>
                    <div className="text-sm font-bold text-white">{dilemma.role_a_name || "Department Lead"}</div>
                    <p className="text-[11px] text-slate-400">Urges strategic investment & ambition</p>
                  </div>

                  {/* VS Indicator */}
                  <div className="md:col-span-1 flex flex-col items-center justify-center">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full border border-amber-500/40 bg-amber-500/10 text-amber-300 text-xs font-black">
                      VS
                    </div>
                    <span className="mt-1 text-[9px] uppercase tracking-wider text-slate-500">Conflict</span>
                  </div>

                  {/* Role B */}
                  <div className="md:col-span-2 space-y-1 md:text-right">
                    <div className="inline-block rounded bg-sky-500/20 px-2 py-0.5 text-[10px] font-mono font-bold uppercase text-sky-300">
                      {dilemma.role_b_label || dilemma.role_b}
                    </div>
                    <div className="text-sm font-bold text-white">{dilemma.role_b_name || "Executive Lead"}</div>
                    <p className="text-[11px] text-slate-400">Demands fiscal discipline & wage integrity</p>
                  </div>
                </div>
              </div>

              {/* Conflict Summary */}
              <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">Executive Standoff</h4>
                <h3 className="mt-1 text-sm font-bold text-white">{dilemma.title}</h3>
                <p className="mt-1.5 text-xs text-slate-300 leading-relaxed">{dilemma.conflict_summary}</p>
              </div>

              {/* Strategic Choices */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Arbitration Options ({dilemma.choices?.length || 0})
                  </h4>
                  <span className="text-[10px] text-slate-500">Select one option to ratify</span>
                </div>

                <div className="space-y-3">
                  {dilemma.choices?.map((choice) => {
                    const isSelected = selectedChoiceId === choice.choice_id;
                    const hasCost = choice.cost_gtex && choice.cost_gtex > 0;

                    return (
                      <div
                        key={choice.choice_id}
                        data-testid={`dilemma-choice-${choice.choice_id}`}
                        onClick={() => handleSelectChoice(choice.choice_id)}
                        className={`cursor-pointer rounded-xl border p-4 transition-all ${
                          isSelected
                            ? "border-emerald-500 bg-emerald-500/10 ring-1 ring-emerald-500/30"
                            : "border-white/10 bg-slate-950/40 hover:border-white/20 hover:bg-slate-950/80"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-start gap-3">
                            <div
                              className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
                                isSelected
                                  ? "border-emerald-400 bg-emerald-500 text-slate-950"
                                  : "border-slate-600 bg-slate-800"
                              }`}
                            >
                              {isSelected && <CheckCircle2 className="h-4 w-4" />}
                            </div>
                            <div>
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="text-sm font-bold text-white">{choice.label}</span>
                                {choice.backed_role && (
                                  <span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] text-slate-300">
                                    {choice.backed_role}
                                  </span>
                                )}
                              </div>
                              <p className="mt-1 text-xs text-slate-300">{choice.summary}</p>
                            </div>
                          </div>

                          {/* Cost Pill */}
                          <div className="shrink-0 text-right">
                            <span
                              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-mono font-bold ${
                                hasCost
                                  ? "border border-amber-500/30 bg-amber-500/10 text-amber-300"
                                  : "border border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                              }`}
                            >
                              <Coins className="h-3 w-3" />
                              {hasCost ? `₦${choice.cost_gtex?.toLocaleString()} GTEX` : "FREE"}
                            </span>
                          </div>
                        </div>

                        {/* Projected Consequence Deltas */}
                        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2 border-t border-white/5 pt-2">
                          <div>
                            <span className="text-[10px] font-bold text-slate-400 uppercase">
                              {dilemma.role_a_label || "Role A"} Impact:
                            </span>
                            {renderDeltaPills(choice.delta_role_a)}
                          </div>
                          <div>
                            <span className="text-[10px] font-bold text-slate-400 uppercase">
                              {dilemma.role_b_label || "Role B"} Impact:
                            </span>
                            {renderDeltaPills(choice.delta_role_b)}
                          </div>
                        </div>

                        {/* Consequences Bullet List */}
                        {choice.projected_effects && choice.projected_effects.length > 0 && (
                          <div className="mt-2 text-[11px] text-slate-400 space-y-0.5">
                            {choice.projected_effects.map((eff, idx) => (
                              <div key={idx} className="flex items-center gap-1.5">
                                <span className="h-1 w-1 rounded-full bg-slate-500" />
                                <span>{eff}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Owner Directive Note */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">
                  Owner Directive / Boardroom Note (Optional)
                </label>
                <textarea
                  data-testid="dilemma-note-input"
                  rows={2}
                  value={decisionNote}
                  onChange={(e) => setDecisionNote(e.target.value)}
                  placeholder="Record your executive reasoning for the club archive and staff chat..."
                  className="w-full rounded-xl border border-white/10 bg-slate-950/80 px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                />
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between border-t border-white/10 pt-4">
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-xl border border-white/10 bg-slate-950/60 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-white/10 hover:text-white"
                >
                  Defer Decision
                </button>
                <button
                  type="button"
                  data-testid="ratify-dilemma-btn"
                  onClick={handleRatify}
                  disabled={!selectedChoiceId || resolveMutation.isPending}
                  className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-5 py-2 text-xs font-bold text-slate-950 shadow-lg shadow-emerald-500/20 transition-all hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {resolveMutation.isPending ? (
                    <>
                      <Sparkles className="h-3.5 w-3.5 animate-spin" />
                      <span>Ratifying Stance...</span>
                    </>
                  ) : (
                    <>
                      <Send className="h-3.5 w-3.5" />
                      <span>Ratify Boardroom Resolution</span>
                    </>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
