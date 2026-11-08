/**
 * GTEX Living Football Ecosystem — Stage 5 General Manager Delegation & Owner Control
 * GmDelegationModal: Strategic Governance HUD, Authority Matrix & Executive Proposal Queue.
 *
 * Surfaced from the Executive Boardroom Suite or Persona Dialogue with the General Manager.
 * Facilitates:
 *   - 3 Authoritative Modes: Owner-Managed, Balanced Delegation, GM-Led Management
 *   - 12 Canonical Activities Authority Matrix with per-activity toggle controls
 *   - Macro Financial Controls & Unapproved Spending Thresholds
 *   - Real-time GM Operational Evaluation Cycle Trigger
 *   - Escalated Proposals Queue with Ratification / Veto Actions & Bilateral Feedback
 *   - Durable Audit Trail of Autonomous Decisions
 */

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  X,
  Shield,
  Sliders,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  History,
  TrendingUp,
  TrendingDown,
  Coins,
  Users,
  Briefcase,
  FileText,
  Lock,
  Unlock,
  Building2,
  Sparkles,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import {
  clubGmDelegationEndpoint,
  clubGmDelegationModeEndpoint,
  clubGmDelegationMatrixEndpoint,
  clubGmEvaluateOperationsEndpoint,
  clubGmResolveProposalEndpoint,
  type GmDelegationOverviewResponse,
  type GmDelegationFinancialControls,
  type GmProposalItem,
  type GmEvaluateOperationsResponse,
  type GmProposalResolveResponse,
} from "@/lib/ownerBriefing";

export interface GmDelegationModalProps {
  clubId: string;
  isOpen: boolean;
  onClose: () => void;
  initialTab?: "modes" | "matrix" | "proposals" | "audit";
}

type TabType = "modes" | "matrix" | "proposals" | "audit";

const MODES = [
  {
    key: "owner_managed",
    title: "Owner-Managed",
    badge: "Direct Control",
    badgeColor: "border-amber-500/40 text-amber-300 bg-amber-500/10",
    description: "Maximum owner oversight. All sporting, staffing, and financial actions require explicit owner ratification.",
    limits: "Zero unapproved spend. GM escalates all proposals to owner queue.",
  },
  {
    key: "balanced",
    title: "Balanced Delegation",
    badge: "Recommended",
    badgeColor: "border-sky-500/40 text-sky-300 bg-sky-500/10",
    description: "Structured partnership. GM operates autonomously within moderate spending caps; high-stakes actions escalate.",
    limits: "Cap: 10,000 GTEX unapproved, max staff salary 1,500 GTEX, 2-yr contracts.",
  },
  {
    key: "gm_led",
    title: "GM-Led Management",
    badge: "High Autonomy",
    badgeColor: "border-emerald-500/40 text-emerald-300 bg-emerald-500/10",
    description: "Full operational delegation. GM exercises sporting and administrative discretion within macro seasonal budgets.",
    limits: "Cap: 50,000 GTEX unapproved, max staff salary 3,500 GTEX, 4-yr contracts.",
  },
];

export const GmDelegationModal: React.FC<GmDelegationModalProps> = ({
  clubId,
  isOpen,
  onClose,
  initialTab = "modes",
}) => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabType>(initialTab);
  const [decisionNotes, setDecisionNotes] = useState<Record<string, string>>({});

  // Local financial controls editing state
  const [localControls, setLocalControls] = useState<Partial<GmDelegationFinancialControls>>({});
  const [controlsDirty, setControlsDirty] = useState(false);

  // Fetch overview data
  const {
    data: overview,
    isLoading,
    refetch,
  } = useQuery<GmDelegationOverviewResponse | null>({
    queryKey: ["club-gm-delegation", clubId],
    queryFn: async () => {
      try {
        const res = await api.get<GmDelegationOverviewResponse>(clubGmDelegationEndpoint(clubId));
        return res.data;
      } catch (err) {
        console.warn("Failed to fetch GM delegation overview:", err);
        return null;
      }
    },
    enabled: isOpen && !!clubId,
  });

  // Switch Delegation Mode
  const modeMutation = useMutation({
    mutationFn: async (mode: string) => {
      const res = await api.post(clubGmDelegationModeEndpoint(clubId), { mode });
      return res.data;
    },
    onSuccess: (_, mode) => {
      toast.success(`Delegation policy transitioned to ${mode.replace("_", " ").toUpperCase()}`);
      queryClient.invalidateQueries({ queryKey: ["club-gm-delegation", clubId] });
      setControlsDirty(false);
    },
    onError: (err) => {
      toast.error(errMsg(err));
    },
  });

  // Update Matrix / Financial Controls
  const matrixMutation = useMutation({
    mutationFn: async (payload: {
      activity_assignments?: Record<string, { requires_owner_approval: boolean }>;
      financial_controls?: Partial<GmDelegationFinancialControls>;
    }) => {
      const res = await api.put(clubGmDelegationMatrixEndpoint(clubId), payload);
      return res.data;
    },
    onSuccess: () => {
      toast.success("Authority matrix & financial controls saved successfully!");
      queryClient.invalidateQueries({ queryKey: ["club-gm-delegation", clubId] });
      setControlsDirty(false);
    },
    onError: (err) => {
      toast.error(errMsg(err));
    },
  });

  // Run GM Operational Evaluation Cycle
  const evaluateMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post<GmEvaluateOperationsResponse>(
        clubGmEvaluateOperationsEndpoint(clubId)
      );
      return res.data;
    },
    onSuccess: (data) => {
      const execCount = data.executed_actions?.length || 0;
      const escCount = data.escalated_proposals?.length || 0;
      const blockedCount = data.blocked_actions?.length || 0;
      toast.success(
        `GM Operational Cycle: ${execCount} executed, ${escCount} escalated, ${blockedCount} blocked.`
      );
      queryClient.invalidateQueries({ queryKey: ["club-gm-delegation", clubId] });
    },
    onError: (err) => {
      toast.error(errMsg(err));
    },
  });

  // Resolve Proposal (Approve / Reject)
  const resolveMutation = useMutation({
    mutationFn: async ({
      proposalId,
      approved,
      note,
    }: {
      proposalId: string;
      approved: boolean;
      note?: string;
    }) => {
      const res = await api.post<GmProposalResolveResponse>(
        clubGmResolveProposalEndpoint(clubId, proposalId),
        { action: approved ? "approve" : "reject", decision_note: note || undefined }
      );
      return res.data;
    },
    onSuccess: (data) => {
      if (data.status === "approved") {
        toast.success(`Proposal approved and ratified: ${data.action_taken}`);
      } else {
        toast.info(`Proposal rejected: ${data.action_taken}`);
      }
      queryClient.invalidateQueries({ queryKey: ["club-gm-delegation", clubId] });
    },
    onError: (err) => {
      toast.error(errMsg(err));
    },
  });

  if (!isOpen) return null;

  const gm = overview?.gm_staff;
  const currentMode = overview?.canonical_mode || overview?.delegation_mode || "balanced";
  const controls: GmDelegationFinancialControls = {
    ...(overview?.financial_controls || {
      max_expenditure_unapproved_gtex: 15000,
      max_staff_salary_unapproved_gtex: 1500,
      max_contract_years_unapproved: 2,
      recruitment_budget_gtex: 100000,
      wage_budget_gtex: 40000,
      min_sale_value_gtex: 20000,
      allow_emergency_spending: true,
    }),
    ...localControls,
  };

  const pendingProposals = overview?.pending_proposals || [];
  const activities = overview?.activities || [];
  const auditTrail = overview?.recent_audit_trail || [];

  const handleToggleActivityApproval = (activityKey: string, currentVal: boolean) => {
    matrixMutation.mutate({
      activity_assignments: {
        [activityKey]: { requires_owner_approval: !currentVal },
      },
    });
  };

  const handleSaveFinancialLimits = (e: React.FormEvent) => {
    e.preventDefault();
    matrixMutation.mutate({
      financial_controls: controls,
    });
  };

  return (
    <div
      data-testid="gm-delegation-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/85 backdrop-blur-md p-4 sm:p-6"
    >
      <div className="relative flex h-[92vh] max-h-[880px] w-full max-w-5xl flex-col rounded-2xl border border-sky-500/30 bg-slate-900/95 shadow-2xl shadow-sky-950/60 overflow-hidden text-slate-100">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 bg-slate-950/70 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/20 text-sky-400 border border-sky-500/30">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-wide">
                  General Manager Delegation & Authority Matrix
                </h2>
                <span className="rounded bg-sky-500/20 px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider text-sky-300 border border-sky-500/30">
                  {currentMode.replace("_", " ").toUpperCase()}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Authoritative governance HUD • Operational discretion & financial caps
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Run Operational Evaluation */}
            <button
              type="button"
              data-testid="run-gm-evaluation-btn"
              onClick={() => evaluateMutation.mutate()}
              disabled={evaluateMutation.isPending}
              className="flex items-center gap-1.5 rounded-xl border border-emerald-500/40 bg-emerald-500/20 px-3 py-1.5 text-xs font-semibold text-emerald-300 transition-all hover:bg-emerald-500/30 disabled:opacity-50"
            >
              <Play className="h-3.5 w-3.5 fill-current" />
              <span>{evaluateMutation.isPending ? "Simulating..." : "Run GM Cycle"}</span>
            </button>

            <button
              type="button"
              data-testid="close-gm-delegation-modal-btn"
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-slate-800 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* GM Executive Persona Banner */}
        <div className="border-b border-white/10 bg-slate-950/40 px-6 py-3">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-800 text-sm font-bold text-sky-300 border border-white/10">
                {gm?.name ? gm.name.split(" ").map((n) => n[0]).join("") : "GM"}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-white">{gm?.name || "Dayo Adeleke"}</span>
                  <span className="text-xs text-slate-400">({gm?.role || "General Manager"})</span>
                  <span className="rounded bg-sky-500/10 px-1.5 py-0.5 text-[10px] font-mono text-sky-400">
                    OVR {gm?.rating || 84}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Annual Remuneration: <span className="text-emerald-400 font-mono">{(gm?.salary_gtex || 1800).toLocaleString()} GTEX</span>
                </div>
              </div>
            </div>

            {/* Bilateral Dimension Meters */}
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-1.5" title="Bilateral Trust Level">
                <span className="text-slate-400 text-[11px]">Trust:</span>
                <span className="font-mono font-bold text-emerald-400">{gm?.trust ?? 60}%</span>
              </div>
              <div className="flex items-center gap-1.5" title="Bilateral Tension (Lower is better)">
                <span className="text-slate-400 text-[11px]">Tension:</span>
                <span className="font-mono font-bold text-amber-400">{gm?.tension ?? 20}%</span>
              </div>
              <div className="flex items-center gap-1.5" title="Strategic Alignment">
                <span className="text-slate-400 text-[11px]">Alignment:</span>
                <span className="font-mono font-bold text-sky-400">{gm?.alignment ?? 65}%</span>
              </div>
              <div className="flex items-center gap-1.5" title="Executive Loyalty">
                <span className="text-slate-400 text-[11px]">Loyalty:</span>
                <span className="font-mono font-bold text-purple-400">{gm?.loyalty ?? 70}%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-white/10 bg-slate-950/60 px-6">
          <button
            type="button"
            data-testid="gm-tab-modes"
            onClick={() => setActiveTab("modes")}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-semibold transition-all ${
              activeTab === "modes"
                ? "border-sky-400 text-sky-300 bg-sky-500/5"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Sliders className="h-3.5 w-3.5" />
            <span>Delegation Modes & Limits</span>
          </button>
          <button
            type="button"
            data-testid="gm-tab-matrix"
            onClick={() => setActiveTab("matrix")}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-semibold transition-all ${
              activeTab === "matrix"
                ? "border-sky-400 text-sky-300 bg-sky-500/5"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Shield className="h-3.5 w-3.5" />
            <span>Authority Matrix (12 Activities)</span>
          </button>
          <button
            type="button"
            data-testid="gm-tab-proposals"
            onClick={() => setActiveTab("proposals")}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-semibold transition-all relative ${
              activeTab === "proposals"
                ? "border-sky-400 text-sky-300 bg-sky-500/5"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
            <span>Escalated Proposals</span>
            {pendingProposals.length > 0 && (
              <span className="rounded-full bg-amber-500/20 px-1.5 py-0.2 text-[10px] font-mono text-amber-300 border border-amber-500/40">
                {pendingProposals.length}
              </span>
            )}
          </button>
          <button
            type="button"
            data-testid="gm-tab-audit"
            onClick={() => setActiveTab("audit")}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-semibold transition-all ${
              activeTab === "audit"
                ? "border-sky-400 text-sky-300 bg-sky-500/5"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <History className="h-3.5 w-3.5" />
            <span>Audit Trail & Statistics</span>
          </button>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex h-64 items-center justify-center text-sm text-slate-400">
              Loading GM delegation architecture...
            </div>
          ) : activeTab === "modes" ? (
            /* TAB 1: MODES & FINANCIAL LIMITS */
            <div className="space-y-6">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-3">
                  Management Delegation Mode
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {MODES.map((m) => {
                    const isSelected = currentMode === m.key;
                    return (
                      <div
                        key={m.key}
                        data-testid={`mode-card-${m.key}`}
                        onClick={() => modeMutation.mutate(m.key)}
                        className={`cursor-pointer rounded-xl border p-4 transition-all relative flex flex-col justify-between ${
                          isSelected
                            ? "border-sky-500 bg-sky-500/15 shadow-lg shadow-sky-500/10 ring-1 ring-sky-400"
                            : "border-white/10 bg-slate-950/50 hover:border-white/20 hover:bg-white/5"
                        }`}
                      >
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-bold text-white">{m.title}</span>
                            <span
                              className={`rounded px-1.5 py-0.5 text-[10px] font-semibold border ${m.badgeColor}`}
                            >
                              {m.badge}
                            </span>
                          </div>
                          <p className="text-xs text-slate-300 mb-3">{m.description}</p>
                        </div>
                        <div className="border-t border-white/5 pt-2 text-[11px] text-slate-400">
                          {m.limits}
                        </div>
                        {isSelected && (
                          <div className="absolute top-2 right-2 flex h-2 w-2 rounded-full bg-sky-400 animate-ping" />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Financial Controls & Spending Thresholds */}
              <div className="rounded-xl border border-white/10 bg-slate-950/60 p-5">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                      Financial Controls & Expenditure Thresholds
                    </h3>
                    <p className="text-xs text-slate-400">
                      Expenditures or salaries exceeding these authorized ceilings trigger mandatory owner ratification.
                    </p>
                  </div>
                  {controlsDirty && (
                    <button
                      type="button"
                      data-testid="save-financial-limits-btn"
                      onClick={handleSaveFinancialLimits}
                      disabled={matrixMutation.isPending}
                      className="rounded-xl border border-sky-500/40 bg-sky-500/20 px-4 py-1.5 text-xs font-bold text-sky-300 transition-all hover:bg-sky-500/30"
                    >
                      {matrixMutation.isPending ? "Saving..." : "Save Limits"}
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div>
                    <label className="block text-slate-400 mb-1 font-semibold">
                      Max Unapproved Expenditure (GTEX)
                    </label>
                    <input
                      type="number"
                      data-testid="input-max-expenditure"
                      value={controls.max_expenditure_unapproved_gtex}
                      onChange={(e) => {
                        setLocalControls((prev) => ({
                          ...prev,
                          max_expenditure_unapproved_gtex: Number(e.target.value),
                        }));
                        setControlsDirty(true);
                      }}
                      className="w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-white font-mono focus:border-sky-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 mb-1 font-semibold">
                      Max Unapproved Staff Salary (GTEX)
                    </label>
                    <input
                      type="number"
                      data-testid="input-max-staff-salary"
                      value={controls.max_staff_salary_unapproved_gtex}
                      onChange={(e) => {
                        setLocalControls((prev) => ({
                          ...prev,
                          max_staff_salary_unapproved_gtex: Number(e.target.value),
                        }));
                        setControlsDirty(true);
                      }}
                      className="w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-white font-mono focus:border-sky-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 mb-1 font-semibold">
                      Max Unapproved Contract Duration (Years)
                    </label>
                    <input
                      type="number"
                      data-testid="input-max-contract-years"
                      value={controls.max_contract_years_unapproved}
                      onChange={(e) => {
                        setLocalControls((prev) => ({
                          ...prev,
                          max_contract_years_unapproved: Number(e.target.value),
                        }));
                        setControlsDirty(true);
                      }}
                      className="w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-white font-mono focus:border-sky-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 mb-1 font-semibold">
                      Annual Recruitment Budget (GTEX)
                    </label>
                    <input
                      type="number"
                      data-testid="input-recruitment-budget"
                      value={controls.recruitment_budget_gtex}
                      onChange={(e) => {
                        setLocalControls((prev) => ({
                          ...prev,
                          recruitment_budget_gtex: Number(e.target.value),
                        }));
                        setControlsDirty(true);
                      }}
                      className="w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-white font-mono focus:border-sky-500 focus:outline-none"
                    />
                  </div>

                  <div className="md:col-span-2 flex items-center justify-between border-t border-white/5 pt-3">
                    <div>
                      <span className="text-white font-semibold">Emergency Operational Spending</span>
                      <p className="text-[11px] text-slate-400">
                        Allow GM to disburse emergency funds for urgent medical treatments or fixture readiness.
                      </p>
                    </div>
                    <button
                      type="button"
                      data-testid="toggle-emergency-spending-btn"
                      onClick={() => {
                        setLocalControls((prev) => ({
                          ...prev,
                          allow_emergency_spending: !controls.allow_emergency_spending,
                        }));
                        setControlsDirty(true);
                      }}
                      className={`flex h-6 w-11 items-center rounded-full transition-colors ${
                        controls.allow_emergency_spending ? "bg-emerald-500" : "bg-slate-700"
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          controls.allow_emergency_spending ? "translate-x-6" : "translate-x-1"
                        }`}
                      />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ) : activeTab === "matrix" ? (
            /* TAB 2: AUTHORITY MATRIX (12 ACTIVITIES) */
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Authoritative Responsibility Matrix
                  </h3>
                  <p className="text-xs text-slate-400">
                    Fine-tune operational authority across 12 canonical club governance activities.
                  </p>
                </div>
                <div className="text-xs text-slate-400">
                  Total Activities: <span className="text-sky-400 font-bold">{activities.length}</span>
                </div>
              </div>

              <div className="rounded-xl border border-white/10 bg-slate-950/60 overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-white/10 bg-slate-900/80 text-slate-400 uppercase font-mono text-[10px]">
                    <tr>
                      <th className="px-4 py-3">Activity</th>
                      <th className="px-4 py-3">Department</th>
                      <th className="px-4 py-3">GM Authority</th>
                      <th className="px-4 py-3 text-right">Owner Control</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {activities.map((act) => {
                      const requiresApproval = act.requires_owner_approval;
                      return (
                        <tr
                          key={act.activity_key}
                          data-testid={`activity-row-${act.activity_key}`}
                          className="hover:bg-white/5 transition-colors"
                        >
                          <td className="px-4 py-3">
                            <div className="font-bold text-white">{act.label}</div>
                            <div className="text-[11px] text-slate-400">{act.description}</div>
                          </td>
                          <td className="px-4 py-3">
                            <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-semibold text-slate-300 uppercase">
                              {act.department}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            {requiresApproval ? (
                              <span className="flex items-center gap-1.5 text-amber-300 font-semibold">
                                <Lock className="h-3.5 w-3.5" />
                                <span>Escalates to Owner</span>
                              </span>
                            ) : (
                              <span className="flex items-center gap-1.5 text-emerald-300 font-semibold">
                                <Unlock className="h-3.5 w-3.5" />
                                <span>GM May Execute</span>
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <button
                              type="button"
                              data-testid={`toggle-activity-${act.activity_key}`}
                              onClick={() =>
                                handleToggleActivityApproval(act.activity_key, requiresApproval)
                              }
                              disabled={act.execution_supported === false}
                              title={
                                act.execution_supported === false
                                  ? "GM execution is not implemented for this activity yet."
                                  : undefined
                              }
                              className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold border transition-all disabled:cursor-not-allowed disabled:opacity-40 ${
                                requiresApproval
                                  ? "border-amber-500/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20"
                                  : "border-emerald-500/40 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20"
                              }`}
                            >
                              {act.execution_supported === false
                                ? "Owner Only"
                                : requiresApproval ? "Require Approval" : "Autonomous"}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ) : activeTab === "proposals" ? (
            /* TAB 3: ESCALATED PROPOSALS QUEUE */
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Pending GM Proposals Awaiting Ratification
                  </h3>
                  <p className="text-xs text-slate-400">
                    Proposals escalated because they exceed financial limits or require owner sign-off.
                  </p>
                </div>
                <div className="text-xs text-slate-400">
                  Pending: <span className="text-amber-400 font-bold">{pendingProposals.length}</span>
                </div>
              </div>

              {pendingProposals.length === 0 ? (
                <div className="flex flex-col items-center justify-center rounded-xl border border-white/10 bg-slate-950/40 py-12 text-center">
                  <CheckCircle2 className="h-10 w-10 text-emerald-400/60 mb-2" />
                  <span className="text-sm font-semibold text-white">No Pending Proposals</span>
                  <p className="text-xs text-slate-400 mt-1 max-w-sm">
                    GM Dayo Adeleke has resolved all active operational matters within authorized policy.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {pendingProposals.map((prop) => {
                    const note = decisionNotes[prop.id] || "";
                    return (
                      <div
                        key={prop.id}
                        data-testid={`proposal-card-${prop.id}`}
                        className="rounded-xl border border-amber-500/30 bg-slate-950/70 p-4 transition-all"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                          <div className="flex items-center gap-2">
                            <span className="rounded bg-amber-500/20 px-2 py-0.5 text-[10px] font-mono uppercase font-bold text-amber-300 border border-amber-500/30">
                              {prop.domain}
                            </span>
                            <h4 className="text-sm font-bold text-white">{prop.title}</h4>
                          </div>
                          <div className="flex items-center gap-1.5 text-xs font-mono text-emerald-400">
                            <Coins className="h-3.5 w-3.5" />
                            <span>{(prop.financial_amount_gtex || 0).toLocaleString()} GTEX</span>
                          </div>
                        </div>

                        <p className="text-xs text-slate-300 mb-3">{prop.summary}</p>

                        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-white/5 pt-3">
                          <div className="flex-1 min-w-[200px]">
                            <input
                              type="text"
                              placeholder="Owner deliberation note / instruction (optional)..."
                              value={note}
                              onChange={(e) =>
                                setDecisionNotes((prev) => ({
                                  ...prev,
                                  [prop.id]: e.target.value,
                                }))
                              }
                              className="w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none"
                            />
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              data-testid={`reject-proposal-${prop.id}-btn`}
                              onClick={() =>
                                resolveMutation.mutate({
                                  proposalId: prop.id,
                                  approved: false,
                                  note,
                                })
                              }
                              disabled={resolveMutation.isPending}
                              className="flex items-center gap-1.5 rounded-lg border border-rose-500/40 bg-rose-500/20 px-3 py-1.5 text-xs font-bold text-rose-300 transition-all hover:bg-rose-500/30 disabled:opacity-50"
                            >
                              <XCircle className="h-3.5 w-3.5" />
                              <span>Reject & Veto</span>
                            </button>

                            <button
                              type="button"
                              data-testid={`approve-proposal-${prop.id}-btn`}
                              onClick={() =>
                                resolveMutation.mutate({
                                  proposalId: prop.id,
                                  approved: true,
                                  note,
                                })
                              }
                              disabled={resolveMutation.isPending}
                              className="flex items-center gap-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/20 px-4 py-1.5 text-xs font-bold text-emerald-300 transition-all hover:bg-emerald-500/30 disabled:opacity-50"
                            >
                              <CheckCircle2 className="h-3.5 w-3.5" />
                              <span>Approve & Disburse</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            /* TAB 4: AUDIT TRAIL & STATISTICS */
            <div className="space-y-6">
              {/* Statistics Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4">
                  <span className="text-[10px] font-mono uppercase text-slate-400">Total Executed</span>
                  <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
                    {overview?.statistics?.total_executed ?? 0}
                  </div>
                </div>
                <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4">
                  <span className="text-[10px] font-mono uppercase text-slate-400">Pending Approvals</span>
                  <div className="text-xl font-bold font-mono text-amber-400 mt-1">
                    {overview?.statistics?.pending_approval_count ?? 0}
                  </div>
                </div>
                <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4">
                  <span className="text-[10px] font-mono uppercase text-slate-400">Approved Spend</span>
                  <div className="text-xl font-bold font-mono text-sky-400 mt-1">
                    {(overview?.statistics?.total_expenditure_approved_gtex ?? 0).toLocaleString()} GTEX
                  </div>
                </div>
              </div>

              {/* Audit Log Table */}
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-3">
                  Historical Decision Audit Log
                </h3>
                <div className="rounded-xl border border-white/10 bg-slate-950/60 overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b border-white/10 bg-slate-900/80 text-slate-400 uppercase font-mono text-[10px]">
                      <tr>
                        <th className="px-4 py-3">Timestamp</th>
                        <th className="px-4 py-3">Actor</th>
                        <th className="px-4 py-3">Action</th>
                        <th className="px-4 py-3">Reason / Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {auditTrail.length === 0 ? (
                        <tr>
                          <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                            No governance audit entries recorded yet.
                          </td>
                        </tr>
                      ) : (
                        auditTrail.map((entry) => (
                          <tr key={entry.id} className="hover:bg-white/5 transition-colors">
                            <td className="px-4 py-3 font-mono text-slate-400">
                              {new Date(entry.occurred_at).toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </td>
                            <td className="px-4 py-3 font-semibold text-slate-300 uppercase">
                              {entry.actor_role}
                            </td>
                            <td className="px-4 py-3">
                              <span
                                className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                                  entry.action === "approved"
                                    ? "bg-emerald-500/20 text-emerald-300"
                                    : entry.action === "rejected"
                                    ? "bg-rose-500/20 text-rose-300"
                                    : "bg-sky-500/20 text-sky-300"
                                }`}
                              >
                                {entry.action}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-slate-300">
                              <div>{entry.reason}</div>
                              {entry.note && (
                                <div className="text-[10px] text-slate-400 italic">
                                  Note: &quot;{entry.note}&quot;
                                </div>
                              )}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
