import React, { useState } from "react";
import {
  ActivityAssignment,
  AuthorityLevel,
  AuthorityPolicy,
  applyTemporaryOverride,
  removeTemporaryOverride,
  updateActivityAssignment,
} from "@/lib/clubAuthority";
import { Shield, AlertTriangle, CheckCircle, RotateCcw, Lock, ChevronRight } from "lucide-react";
import { toast } from "sonner";

interface DelegationActivityMatrixProps {
  clubId: string;
  policy: AuthorityPolicy | null;
  onPolicyUpdated: (updated: AuthorityPolicy) => void;
}

const DOMAIN_LABELS: Record<string, { title: string; subtitle: string; icon: string }> = {
  sporting: {
    title: "Sporting Operations",
    subtitle: "Tactics, scouting, academy pipeline, transfer bids and contract renewals",
    icon: "⚽",
  },
  club_operations: {
    title: "Club Operations",
    subtitle: "Facilities, budget allocations, commercial deals and executive hiring",
    icon: "🏛️",
  },
  player_staff: {
    title: "Player & Staff Matters",
    subtitle: "Disciplinary matters, player disputes, grievances and staff reviews",
    icon: "🤝",
  },
};

const ACTIVITY_META: Record<string, { label: string; desc: string; thresholdKey?: string }> = {
  // Sporting
  first_team_tactics: { label: "First-Team Tactics & Selection", desc: "Matchday formation, tactical identity, instructions and starting XI." },
  training_and_coaching: { label: "Training & Coaching Regimes", desc: "Weekly microcycles, physical conditioning, and skill development." },
  player_recruitment: { label: "Player Recruitment & Inbound Bids", desc: "Shortlisting, fee negotiations, and purchase offers.", thresholdKey: "recruitment_max_gtex" },
  player_sales: { label: "Player Sales & Loan Departures", desc: "Negotiating outgoing transfer fees and loan agreements.", thresholdKey: "sales_min_gtex" },
  contract_renewals: { label: "Contract Renewals & Extensions", desc: "Weekly wage offers, appearance incentives, and release clauses.", thresholdKey: "contract_renewal_max_weekly_wage_gtex" },
  youth_recruitment: { label: "Youth Recruitment & Intake", desc: "Signing talent combine graduates and regional youth prospects." },
  academy_development: { label: "Academy Development Pipeline", desc: "Youth facilities, age-category promotions, and mentoring." },
  scouting_assignments: { label: "Scouting Assignments & Network", desc: "Deploying scouts to global scouting territories and tournaments." },

  // Club Operations
  staff_recruitment_dismissal: { label: "Staff Recruitment & Dismissal", desc: "Hiring and firing executive staff members and coaches." },
  operational_expenditure: { label: "Operational Expenditure", desc: "General club operating expenses, travel, and logistics.", thresholdKey: "operational_spend_max_gtex" },
  facilities_infrastructure: { label: "Facilities & Infrastructure", desc: "Stadium expansions, pitch maintenance, medical labs, and campus builds.", thresholdKey: "facility_spend_max_gtex" },
  club_administration: { label: "Club Administration & Governance", desc: "Legal filings, federation registrations, and compliance." },
  commercial_partnerships: { label: "Commercial Partnerships", desc: "Merchandising deals, kit licensing, and regional partners." },
  sponsorship_negotiations: { label: "Sponsorship Negotiations", desc: "Stadium naming rights, front-of-shirt sponsors, and perimeter LED deals." },
  financial_planning: { label: "Strategic Financial Planning", desc: "Annual budgeting, capital allocation, dividend policy, and runway." },

  // Player & Staff Matters
  player_complaints: { label: "Player Complaints & Morale", desc: "Handling dressing room unrest, playing-time complaints, and personal issues." },
  disciplinary_incidents: { label: "Disciplinary Incidents", desc: "Fining rule breakers, curfew violations, and conduct hearings." },
  contract_disputes: { label: "Contract Disputes & Agitations", desc: "Addressing transfer requests, wage dissatisfaction, and agent threats." },
  development_reviews: { label: "Player Development Reviews", desc: "Periodic progress assessments, training reports, and loan callbacks." },
  staff_performance: { label: "Staff Performance & Alignment", desc: "Reviewing GM, Manager, and Coach performance KPIs." },
  player_staff_interactions: { label: "Player / Staff Interpersonal Disputes", desc: "Mediating friction between coaching staff and squad members." },
};

const AVAILABLE_ROLES = [
  { value: "owner", label: "Owner (Direct Action)" },
  { value: "general_manager", label: "General Manager" },
  { value: "first_team_manager", label: "First Team Manager" },
  { value: "head_of_youth_development", label: "Head of Youth Development" },
  { value: "chief_scout", label: "Chief Scout" },
  { value: "medical_director", label: "Medical Director" },
];

const AUTHORITY_LEVELS: { value: AuthorityLevel; label: string; desc: string }[] = [
  { value: "owner_only", label: "Owner Only", desc: "Only the owner can propose or execute." },
  { value: "requires_pre_approval", label: "Requires Pre-Approval", desc: "Staff may propose, but Owner must approve before execution." },
  { value: "delegated_with_limits", label: "Delegated with Limits", desc: "Autonomous under financial thresholds; escalates if exceeded." },
  { value: "full_autonomy", label: "Full Autonomy", desc: "Staff decides and executes independently with retrospective logging." },
];

export const DelegationActivityMatrix: React.FC<DelegationActivityMatrixProps> = ({
  clubId,
  policy,
  onPolicyUpdated,
}) => {
  const [activeDomain, setActiveDomain] = useState<"sporting" | "club_operations" | "player_staff">("sporting");
  const [updatingKey, setUpdatingKey] = useState<string | null>(null);

  if (!policy) {
    return (
      <div className="rounded-xl border border-white/10 bg-black/40 p-6 text-center text-slate-400">
        Loading delegation policy matrix...
      </div>
    );
  }

  const activitiesInDomain = Object.values(policy.activity_assignments).filter(
    (a) => a.domain === activeDomain
  );

  const handleRoleChange = async (activityKey: string, newRole: string) => {
    setUpdatingKey(activityKey);
    try {
      const current = policy.activity_assignments[activityKey];
      const updated = await updateActivityAssignment(
        clubId,
        activityKey,
        newRole,
        current.authority_level,
        current.approval_role
      );
      onPolicyUpdated(updated);
      toast.success(`Updated responsible role for ${ACTIVITY_META[activityKey]?.label || activityKey}`);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to update role");
    } finally {
      setUpdatingKey(null);
    }
  };

  const handleLevelChange = async (activityKey: string, newLevel: AuthorityLevel) => {
    setUpdatingKey(activityKey);
    try {
      const current = policy.activity_assignments[activityKey];
      const updated = await updateActivityAssignment(
        clubId,
        activityKey,
        current.responsible_role,
        newLevel,
        current.approval_role
      );
      onPolicyUpdated(updated);
      toast.success(`Updated authority level for ${ACTIVITY_META[activityKey]?.label || activityKey}`);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to update authority level");
    } finally {
      setUpdatingKey(null);
    }
  };

  const handleToggleOverride = async (activityKey: string, isOverridden: boolean) => {
    setUpdatingKey(activityKey);
    try {
      let updated: AuthorityPolicy;
      if (isOverridden) {
        updated = await removeTemporaryOverride(clubId, activityKey);
        toast.info(`Revoked temporary override for ${ACTIVITY_META[activityKey]?.label || activityKey}`);
      } else {
        updated = await applyTemporaryOverride(
          clubId,
          activityKey,
          "owner",
          "Owner temporary operational takeover"
        );
        toast.warning(`Applied temporary override: Owner now directly controls ${ACTIVITY_META[activityKey]?.label || activityKey}`);
      }
      onPolicyUpdated(updated);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to toggle temporary override");
    } finally {
      setUpdatingKey(null);
    }
  };

  return (
    <div className="space-y-6" data-testid="delegation-activity-matrix">
      {/* Domain Navigation Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-white/10 pb-3">
        {(["sporting", "club_operations", "player_staff"] as const).map((domain) => {
          const meta = DOMAIN_LABELS[domain];
          const isActive = activeDomain === domain;
          return (
            <button
              key={domain}
              type="button"
              onClick={() => setActiveDomain(domain)}
              className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-black uppercase tracking-wider transition ${
                isActive
                  ? "bg-purple-600 text-white shadow-lg border border-purple-400"
                  : "bg-white/5 text-slate-300 hover:text-white hover:bg-white/10 border border-white/5"
              }`}
              data-testid={`domain-tab-${domain}`}
            >
              <span>{meta.icon}</span>
              <span>{meta.title}</span>
            </button>
          );
        })}
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-white flex items-center space-x-2">
            <span>{DOMAIN_LABELS[activeDomain].icon}</span>
            <span>{DOMAIN_LABELS[activeDomain].title}</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">{DOMAIN_LABELS[activeDomain].subtitle}</p>
        </div>
        <span className="text-xs text-slate-400 font-mono">
          {activitiesInDomain.length} Activities Configured
        </span>
      </div>

      {/* Activity Cards List */}
      <div className="space-y-3">
        {activitiesInDomain.map((activity: ActivityAssignment) => {
          const meta = ACTIVITY_META[activity.activity_key] || {
            label: activity.activity_key,
            desc: "Custom club activity.",
          };
          const isReserved = policy.reserved_decisions.includes(activity.activity_key);
          const overrideInfo = policy.temporary_overrides[activity.activity_key];
          const isOverridden = Boolean(overrideInfo);
          const isBusy = updatingKey === activity.activity_key;

          const thresholdLimit = meta.thresholdKey
            ? policy.financial_thresholds[meta.thresholdKey]
            : undefined;

          return (
            <div
              key={activity.activity_key}
              className={`rounded-xl border p-4 transition-all duration-200 ${
                isOverridden
                  ? "border-amber-500/40 bg-amber-950/20"
                  : isReserved
                  ? "border-purple-500/30 bg-purple-950/10"
                  : "border-white/10 bg-slate-900/60 hover:bg-slate-900/90"
              }`}
              data-testid={`activity-row-${activity.activity_key}`}
            >
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                {/* Left: Info */}
                <div className="space-y-1 max-w-md">
                  <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                    <span className="text-sm font-bold text-white">{meta.label}</span>
                    {isReserved && (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-black uppercase bg-purple-500/20 text-purple-300 border border-purple-500/30">
                        <Lock className="w-2.5 h-2.5" />
                        <span>Reserved Owner Decision</span>
                      </span>
                    )}
                    {isOverridden && (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-black uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30">
                        <AlertTriangle className="w-2.5 h-2.5" />
                        <span>Owner Override Active</span>
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400">{meta.desc}</p>
                  {thresholdLimit !== undefined && (
                    <p className="text-[11px] text-amber-300/80 font-mono">
                      Delegated Ceiling: {thresholdLimit.toLocaleString()} GTX
                    </p>
                  )}
                </div>

                {/* Right: Controls */}
                <div className="flex flex-wrap items-center gap-3">
                  {/* Responsible Role Selector */}
                  <div className="space-y-1">
                    <label className="text-[10px] font-black uppercase tracking-wider text-slate-400 block">
                      Responsible
                    </label>
                    <select
                      value={activity.responsible_role}
                      disabled={isBusy || policy.is_suspended}
                      onChange={(e) => handleRoleChange(activity.activity_key, e.target.value)}
                      className="bg-black/60 border border-white/20 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-purple-400"
                      data-testid={`select-role-${activity.activity_key}`}
                    >
                      {AVAILABLE_ROLES.map((r) => (
                        <option key={r.value} value={r.value}>
                          {r.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Authority Level Selector */}
                  <div className="space-y-1">
                    <label className="text-[10px] font-black uppercase tracking-wider text-slate-400 block">
                      Authority Level
                    </label>
                    <select
                      value={activity.authority_level}
                      disabled={isBusy || isReserved || policy.is_suspended}
                      onChange={(e) =>
                        handleLevelChange(activity.activity_key, e.target.value as AuthorityLevel)
                      }
                      className="bg-black/60 border border-white/20 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-purple-400"
                      data-testid={`select-authority-${activity.activity_key}`}
                    >
                      {AUTHORITY_LEVELS.map((lvl) => (
                        <option key={lvl.value} value={lvl.value}>
                          {lvl.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Override Toggle Button */}
                  <div className="space-y-1 self-end">
                    <label className="text-[10px] font-black uppercase tracking-wider text-slate-400 block invisible">
                      Action
                    </label>
                    <button
                      type="button"
                      disabled={isBusy || policy.is_suspended}
                      onClick={() => handleToggleOverride(activity.activity_key, isOverridden)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1.5 ${
                        isOverridden
                          ? "bg-amber-600/30 text-amber-200 hover:bg-amber-600/50 border border-amber-500/40"
                          : "bg-white/5 text-slate-300 hover:text-white hover:bg-white/10 border border-white/10"
                      }`}
                      data-testid={`btn-override-${activity.activity_key}`}
                    >
                      <RotateCcw className="w-3 h-3" />
                      <span>{isOverridden ? "Revoke Override" : "Direct Override"}</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
