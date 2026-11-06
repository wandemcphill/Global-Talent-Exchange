import React, { useState } from "react";
import {
  DelegatedDecision,
  resolveDelegatedDecision,
} from "@/lib/clubAuthority";
import {
  AlertCircle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  TrendingUp,
  AlertTriangle,
  Zap,
} from "lucide-react";
import { toast } from "sonner";

interface PendingEscalationsCardProps {
  clubId: string;
  escalations: DelegatedDecision[];
  onDecisionResolved: (decisionId: string) => void;
}

const RECOMMENDATION_STYLES: Record<string, { label: string; bg: string; text: string; border: string }> = {
  strongly_recommended: {
    label: "Strongly Recommended",
    bg: "bg-emerald-500/20",
    text: "text-emerald-300",
    border: "border-emerald-500/40",
  },
  recommended: {
    label: "Staff Backed",
    bg: "bg-teal-500/20",
    text: "text-teal-300",
    border: "border-teal-500/40",
  },
  neutral: {
    label: "Neutral Alignment",
    bg: "bg-blue-500/20",
    text: "text-blue-300",
    border: "border-blue-500/40",
  },
  caution: {
    label: "Proceed with Caution",
    bg: "bg-amber-500/20",
    text: "text-amber-300",
    border: "border-amber-500/40",
  },
  risky: {
    label: "High Strategic Risk",
    bg: "bg-rose-500/20",
    text: "text-rose-300",
    border: "border-rose-500/40",
  },
};

export const PendingEscalationsCard: React.FC<PendingEscalationsCardProps> = ({
  clubId,
  escalations,
  onDecisionResolved,
}) => {
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});

  const handleResolve = async (
    decisionId: string,
    action: "approve" | "reject" | "override"
  ) => {
    setResolvingId(decisionId);
    try {
      const note = notes[decisionId];
      await resolveDelegatedDecision(clubId, decisionId, action, note);
      toast.success(
        action === "approve"
          ? "Decision Approved and Committed."
          : action === "reject"
          ? "Proposal Rejected and Archived."
          : "Owner Override Executed."
      );
      onDecisionResolved(decisionId);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || `Failed to ${action} decision`);
    } finally {
      setResolvingId(null);
    }
  };

  if (!escalations || escalations.length === 0) {
    return (
      <div
        className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 text-center shadow-lg"
        data-testid="no-escalations-card"
      >
        <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mx-auto mb-3">
          <CheckCircle2 className="w-6 h-6 text-emerald-400" />
        </div>
        <h4 className="text-sm font-bold text-white">Delegated Operations Running Smoothly</h4>
        <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
          All staff decisions are operating within authorized financial thresholds and jurisdictional autonomy. No owner sign-offs are pending.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="pending-escalations-card">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span>
          </span>
          <h3 className="text-sm font-black uppercase tracking-wider text-amber-300">
            Pending Owner Escalations ({escalations.length})
          </h3>
        </div>
        <span className="text-xs text-slate-400">Action Required Before Execution</span>
      </div>

      <div className="space-y-4">
        {escalations.map((item) => {
          const impact = item.staff_competence_impact;
          const recStyle = impact
            ? RECOMMENDATION_STYLES[impact.recommendation] || RECOMMENDATION_STYLES.neutral
            : null;
          const isBusy = resolvingId === item.id;

          return (
            <div
              key={item.id}
              className="rounded-2xl border-2 border-amber-500/30 bg-gradient-to-br from-slate-900 via-slate-950 to-black p-5 shadow-xl space-y-4"
              data-testid={`escalation-item-${item.id}`}
            >
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-white/10 pb-3">
                <div>
                  <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                    <span className="text-xs font-black uppercase tracking-wider px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                      {item.proposed_by_role.replace(/_/g, " ")}
                    </span>
                    <span className="text-xs font-mono text-slate-400">
                      Activity: {item.activity_key}
                    </span>
                  </div>
                  <h4 className="text-base font-bold text-white mt-1.5">{item.title}</h4>
                </div>

                <div className="text-right shrink-0">
                  <span className="text-xs text-slate-400 block font-mono">Financial Commitment</span>
                  <span className="text-base font-black text-amber-400 font-mono">
                    {item.financial_amount_gtex.toLocaleString()} GTX
                  </span>
                </div>
              </div>

              {/* Summary & Reason */}
              <div className="space-y-2 text-xs">
                <p className="text-slate-300 leading-relaxed">{item.summary}</p>
                {item.escalation_reason && (
                  <div className="flex items-start space-x-2 bg-amber-500/10 border border-amber-500/20 rounded-lg p-2.5 text-amber-200">
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
                    <span>
                      <strong>Escalation Trigger:</strong> {item.escalation_reason}
                    </span>
                  </div>
                )}
              </div>

              {/* Staff Competence Impact Preview */}
              {impact && (
                <div className="rounded-xl border border-white/10 bg-black/40 p-3.5 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <TrendingUp className="w-4 h-4 text-purple-400" />
                      <span className="text-[11px] font-black uppercase tracking-wider text-slate-300">
                        Staff Competence Intelligence
                      </span>
                    </div>
                    {recStyle && (
                      <span
                        className={`text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full border ${recStyle.bg} ${recStyle.text} ${recStyle.border}`}
                      >
                        {recStyle.label}
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-slate-300 italic">{impact.evaluation_summary}</p>

                  <div className="grid grid-cols-3 gap-2 pt-1 text-[11px]">
                    <div className="bg-white/5 rounded p-1.5 text-center">
                      <span className="text-slate-400 block text-[10px]">Staff Competence</span>
                      <span className="font-bold text-white">{impact.competence_score}/100</span>
                    </div>
                    <div className="bg-white/5 rounded p-1.5 text-center">
                      <span className="text-slate-400 block text-[10px]">Success Probability</span>
                      <span className="font-bold text-emerald-400">
                        {Math.round(impact.success_probability * 100)}%
                      </span>
                    </div>
                    <div className="bg-white/5 rounded p-1.5 text-center">
                      <span className="text-slate-400 block text-[10px]">Staff Ambition</span>
                      <span className="font-bold text-purple-400">{impact.ambition}/100</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Decision Note & Actions */}
              <div className="space-y-3 pt-2">
                <input
                  type="text"
                  placeholder="Optional owner reasoning or executive directive..."
                  value={notes[item.id] || ""}
                  onChange={(e) => setNotes({ ...notes, [item.id]: e.target.value })}
                  className="w-full bg-black/50 border border-white/10 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-400"
                />

                <div className="flex flex-wrap items-center justify-end gap-2.5">
                  <button
                    type="button"
                    disabled={isBusy}
                    onClick={() => handleResolve(item.id, "reject")}
                    className="px-4 py-2 rounded-xl text-xs font-bold text-rose-300 bg-rose-950/40 border border-rose-500/40 hover:bg-rose-900/60 transition flex items-center space-x-1.5"
                    data-testid={`btn-reject-${item.id}`}
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    <span>Reject</span>
                  </button>

                  <button
                    type="button"
                    disabled={isBusy}
                    onClick={() => handleResolve(item.id, "override")}
                    className="px-4 py-2 rounded-xl text-xs font-bold text-amber-300 bg-amber-950/40 border border-amber-500/40 hover:bg-amber-900/60 transition flex items-center space-x-1.5"
                    data-testid={`btn-override-${item.id}`}
                  >
                    <Zap className="w-3.5 h-3.5" />
                    <span>Owner Override</span>
                  </button>

                  <button
                    type="button"
                    disabled={isBusy}
                    onClick={() => handleResolve(item.id, "approve")}
                    className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-900/30 transition flex items-center space-x-1.5"
                    data-testid={`btn-approve-${item.id}`}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Approve & Authorise</span>
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
