import React, { useState } from "react";
import { DelegatedDecision, DecisionStatus } from "@/lib/clubAuthority";
import { FileText, CheckCircle, XCircle, Zap, Clock, ShieldCheck } from "lucide-react";

interface DecisionAuditHistoryProps {
  decisions: DelegatedDecision[];
  isLoading: boolean;
}

const STATUS_BADGES: Record<
  DecisionStatus,
  { label: string; bg: string; text: string; border: string; icon: React.ReactNode }
> = {
  auto_approved: {
    label: "Auto-Approved",
    bg: "bg-blue-500/20",
    text: "text-blue-300",
    border: "border-blue-500/30",
    icon: <ShieldCheck className="w-3 h-3 text-blue-400" />,
  },
  approved: {
    label: "Owner Approved",
    bg: "bg-emerald-500/20",
    text: "text-emerald-300",
    border: "border-emerald-500/30",
    icon: <CheckCircle className="w-3 h-3 text-emerald-400" />,
  },
  rejected: {
    label: "Owner Rejected",
    bg: "bg-rose-500/20",
    text: "text-rose-300",
    border: "border-rose-500/30",
    icon: <XCircle className="w-3 h-3 text-rose-400" />,
  },
  overridden: {
    label: "Owner Overridden",
    bg: "bg-amber-500/20",
    text: "text-amber-300",
    border: "border-amber-500/30",
    icon: <Zap className="w-3 h-3 text-amber-400" />,
  },
  pending_approval: {
    label: "Pending Owner",
    bg: "bg-yellow-500/20",
    text: "text-yellow-300",
    border: "border-yellow-500/30",
    icon: <Clock className="w-3 h-3 text-yellow-400" />,
  },
};

export const DecisionAuditHistory: React.FC<DecisionAuditHistoryProps> = ({
  decisions,
  isLoading,
}) => {
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState<string>("");

  if (isLoading) {
    return (
      <div className="rounded-xl border border-white/10 bg-black/40 p-6 animate-pulse">
        <div className="h-6 w-48 bg-white/10 rounded mb-4" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-white/5 rounded-xl border border-white/5" />
          ))}
        </div>
      </div>
    );
  }

  const filtered = decisions.filter((d) => {
    if (filterStatus !== "all" && d.status !== filterStatus) return false;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      return (
        d.title.toLowerCase().includes(q) ||
        d.summary.toLowerCase().includes(q) ||
        d.activity_key.toLowerCase().includes(q) ||
        d.proposed_by_role.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-4" data-testid="decision-audit-history">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-black uppercase tracking-wider text-slate-300 flex items-center space-x-2">
            <FileText className="w-4 h-4 text-purple-400" />
            <span>Club Authority Decision Audit Log</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Immutable log of delegated decisions, automated approvals, and owner interventions.
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-2">
          <input
            type="text"
            placeholder="Search decisions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-black/60 border border-white/10 rounded-lg px-2.5 py-1 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-400"
          />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-black/60 border border-white/10 rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none focus:border-purple-400"
          >
            <option value="all">All Outcomes</option>
            <option value="auto_approved">Auto-Approved</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="overridden">Overridden</option>
            <option value="pending_approval">Pending</option>
          </select>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-xl border border-white/10 bg-black/30 p-8 text-center text-slate-400 text-xs">
          No delegated decisions recorded matching filter criteria.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-white/10 bg-black/40">
          <table className="w-full text-left text-xs">
            <thead className="bg-white/5 text-[10px] font-black uppercase tracking-wider text-slate-400 border-b border-white/10">
              <tr>
                <th className="p-3">Decision / Activity</th>
                <th className="p-3">Proposer</th>
                <th className="p-3">Commitment</th>
                <th className="p-3">Status</th>
                <th className="p-3">Competence Effect</th>
                <th className="p-3 text-right">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              {filtered.map((d) => {
                const badge = STATUS_BADGES[d.status] || STATUS_BADGES.pending_approval;
                const impact = d.staff_competence_impact;

                return (
                  <tr key={d.id} className="hover:bg-white/[0.02] transition" data-testid={`history-row-${d.id}`}>
                    <td className="p-3">
                      <div className="font-bold text-white">{d.title}</div>
                      <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                        {d.activity_key} · {d.summary.slice(0, 50)}...
                      </div>
                      {d.decision_note && (
                        <div className="text-[10px] text-purple-300 italic mt-0.5">
                          Owner Note: "{d.decision_note}"
                        </div>
                      )}
                    </td>
                    <td className="p-3">
                      <span className="font-semibold text-slate-200">
                        {d.proposed_by_role.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="p-3 font-mono font-semibold text-amber-300">
                      {d.financial_amount_gtex > 0
                        ? `${d.financial_amount_gtex.toLocaleString()} GTX`
                        : "—"}
                    </td>
                    <td className="p-3">
                      <span
                        className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider border ${badge.bg} ${badge.text} ${badge.border}`}
                      >
                        {badge.icon}
                        <span>{badge.label}</span>
                      </span>
                    </td>
                    <td className="p-3 text-[11px]">
                      {impact ? (
                        <div>
                          <span className="font-bold text-slate-200">
                            {impact.competence_score}/100 Rating
                          </span>
                          <span className="text-slate-400 block text-[10px]">
                            {Math.round(impact.success_probability * 100)}% Success Chance
                          </span>
                        </div>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                    <td className="p-3 text-right text-slate-400 font-mono text-[11px]">
                      {d.created_at ? new Date(d.created_at).toLocaleDateString() : "Just now"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
