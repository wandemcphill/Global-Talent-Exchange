import React, { useEffect, useState } from "react";
import {
  AuthorityPolicy,
  DelegatedDecision,
  FinancialThresholds,
  ManagementMode,
  OrgStructure,
  fetchDecisions,
  fetchDelegationPolicy,
  fetchOrgStructure,
  fetchPendingEscalations,
  toggleSuspension,
  updateFinancialThresholds,
  updateManagementMode,
} from "@/lib/clubAuthority";
import { OrganizationalStructureView } from "./OrganizationalStructureView";
import { DelegationActivityMatrix } from "./DelegationActivityMatrix";
import { PendingEscalationsCard } from "./PendingEscalationsCard";
import { DecisionAuditHistory } from "./DecisionAuditHistory";
import { GtexSceneViewport } from "@/lib/3d/GtexSceneViewport";
import {
  Shield,
  Sliders,
  AlertOctagon,
  RotateCcw,
  Users,
  FileCheck,
  History,
  Building,
  CheckCircle,
  Eye,
  DollarSign,
  Maximize2,
} from "lucide-react";
import { toast } from "sonner";

interface ClubAuthorityPanelProps {
  clubId: string;
}

const MODES: { mode: ManagementMode; label: string; badge: string; desc: string }[] = [
  {
    mode: "hands_on",
    label: "Hands-On",
    badge: "Owner Micromanagement",
    desc: "Direct owner control. 0 GTX delegation limits. Owner must personally approve every transfer, tactical setting, and expenditure.",
  },
  {
    mode: "balanced",
    label: "Balanced",
    badge: "Standard Hierarchy",
    desc: "Premier League hierarchy. 25,000 GTX recruitment cap, 10,000 GTX ops cap. Executive staff operate autonomously within thresholds.",
  },
  {
    mode: "delegating",
    label: "Delegating",
    badge: "Executive Chairman",
    desc: "Continental European model. High 100,000 GTX recruitment cap. Fully empowered General Manager and Sporting Director.",
  },
  {
    mode: "custom",
    label: "Custom",
    badge: "Bespoke Governance",
    desc: "Fine-grained per-activity authority, custom thresholds, and bespoke approval requirements.",
  },
];

export const ClubAuthorityPanel: React.FC<ClubAuthorityPanelProps> = ({ clubId }) => {
  const [policy, setPolicy] = useState<AuthorityPolicy | null>(null);
  const [orgStructure, setOrgStructure] = useState<OrgStructure | null>(null);
  const [escalations, setEscalations] = useState<DelegatedDecision[]>([]);
  const [decisions, setDecisions] = useState<DelegatedDecision[]>([]);
  const [activeTab, setActiveTab] = useState<"org" | "matrix" | "escalations" | "audit">("org");

  const [loading, setLoading] = useState<boolean>(true);
  const [switchingMode, setSwitchingMode] = useState<boolean>(false);
  const [suspending, setSuspending] = useState<boolean>(false);

  // Financial Thresholds Edit State
  const [thresholds, setThresholds] = useState<FinancialThresholds | null>(null);
  const [savingThresholds, setSavingThresholds] = useState<boolean>(false);

  // 3D Boardroom Scene State
  const [boardroomScene, setBoardroomScene] = useState<"boardroom_meeting" | "boardroom_clash">(
    "boardroom_meeting"
  );
  const [show3DSuite, setShow3DSuite] = useState<boolean>(true);

  const loadAllData = async () => {
    try {
      setLoading(true);
      const [pol, org, esc, dec] = await Promise.all([
        fetchDelegationPolicy(clubId),
        fetchOrgStructure(clubId),
        fetchPendingEscalations(clubId),
        fetchDecisions(clubId, 40),
      ]);
      setPolicy(pol);
      setThresholds(pol.financial_thresholds);
      setOrgStructure(org);
      setEscalations(esc.escalations);
      setDecisions(dec.decisions);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to load club authority data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (clubId) {
      loadAllData();
    }
  }, [clubId]);

  const handleModeSwitch = async (mode: ManagementMode) => {
    if (policy?.is_suspended) {
      toast.error("Cannot change mode while delegation is suspended");
      return;
    }
    setSwitchingMode(true);
    try {
      const updated = await updateManagementMode(clubId, mode);
      setPolicy(updated);
      setThresholds(updated.financial_thresholds);
      toast.success(`Club governance mode switched to ${mode.replace(/_/g, " ")}.`);
      // Refetch org to refresh counts
      const org = await fetchOrgStructure(clubId);
      setOrgStructure(org);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to change governance mode");
    } finally {
      setSwitchingMode(false);
    }
  };

  const handleToggleSuspension = async () => {
    setSuspending(true);
    try {
      const isCurrentlySuspended = Boolean(policy?.is_suspended);
      const updated = await toggleSuspension(
        clubId,
        !isCurrentlySuspended,
        !isCurrentlySuspended ? "Emergency owner intervention: all staff authorities frozen." : undefined
      );
      setPolicy(updated);
      if (isCurrentlySuspended) {
        toast.success("Club delegation restored. Appointed staff powers re-activated.");
      } else {
        toast.warning("EMERGENCY: All staff delegation frozen. Direct owner approval required for all actions.");
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to toggle suspension");
    } finally {
      setSuspending(false);
    }
  };

  const handleSaveThresholds = async () => {
    if (!thresholds) return;
    setSavingThresholds(true);
    try {
      const updated = await updateFinancialThresholds(clubId, thresholds);
      setPolicy(updated);
      toast.success("Financial approval limits updated successfully.");
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to save financial limits");
    } finally {
      setSavingThresholds(false);
    }
  };

  const handleDecisionResolved = (decisionId: string) => {
    setEscalations((prev) => prev.filter((e) => e.id !== decisionId));
    // Refetch history
    fetchDecisions(clubId, 40).then((res) => setDecisions(res.decisions));
  };

  return (
    <div className="space-y-8" data-testid="club-authority-panel">
      {/* 1. Header Banner & Emergency Controls */}
      <div className="relative overflow-hidden rounded-3xl border-2 border-purple-500/30 bg-gradient-to-br from-[#130722] via-[#0b0615] to-[#040208] p-6 sm:p-8 shadow-2xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center space-x-2 rounded-full border border-purple-400/40 bg-purple-950/80 px-3.5 py-1 text-xs font-black uppercase tracking-widest text-purple-300">
              <Shield className="w-3.5 h-3.5 text-purple-400" />
              <span>Phase 1D · Club Authority & Delegation Foundation</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black uppercase tracking-tight text-white gx-display">
              Club Authority & Governance
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 max-w-2xl leading-relaxed">
              Define operational responsibility, financial thresholds, and approval chains. Empower appointed sporting and operational executives while retaining absolute sovereign veto rights.
            </p>
          </div>

          {/* Emergency Suspension Toggle */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
            <button
              type="button"
              disabled={suspending || loading}
              onClick={handleToggleSuspension}
              className={`px-5 py-3 rounded-2xl text-xs font-black uppercase tracking-wider transition-all duration-200 flex items-center justify-center space-x-2 shadow-xl ${
                policy?.is_suspended
                  ? "bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-950/50"
                  : "bg-rose-950/80 hover:bg-rose-900 border-2 border-rose-500/50 text-rose-200 shadow-rose-950/50"
              }`}
              data-testid="btn-toggle-suspension"
            >
              <AlertOctagon className="w-4 h-4" />
              <span>{policy?.is_suspended ? "Restore Delegation" : "Emergency Freeze"}</span>
            </button>
          </div>
        </div>

        {/* Emergency Suspension Alert Banner */}
        {policy?.is_suspended && (
          <div className="mt-6 rounded-2xl border-2 border-rose-500/60 bg-rose-950/40 p-4 flex items-center space-x-3 text-rose-200 animate-pulse">
            <AlertOctagon className="w-6 h-6 text-rose-400 shrink-0" />
            <div className="text-xs">
              <span className="font-bold uppercase tracking-wider block">
                Delegation Jurisdiction Suspended
              </span>
              <span>
                {policy.suspension_reason || "All staff authorities are currently frozen by owner decree. All operational actions require direct owner sign-off."}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 2. Management Mode Selector Strip */}
      <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Sliders className="w-4 h-4 text-purple-400" />
            <h3 className="text-xs font-black uppercase tracking-wider text-slate-300">
              Club Management Configuration
            </h3>
          </div>
          <span className="text-xs font-bold text-purple-300 uppercase">
            Active Mode: {policy?.mode.replace(/_/g, " ")}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {MODES.map((m) => {
            const isSelected = policy?.mode === m.mode;
            return (
              <button
                key={m.mode}
                type="button"
                disabled={switchingMode || policy?.is_suspended}
                onClick={() => handleModeSwitch(m.mode)}
                className={`text-left p-4 rounded-xl border-2 transition-all duration-200 relative ${
                  isSelected
                    ? "border-purple-500 bg-purple-950/40 shadow-lg shadow-purple-950/30"
                    : "border-white/5 bg-black/40 hover:border-white/20 hover:bg-black/60"
                }`}
                data-testid={`mode-card-${m.mode}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-black uppercase tracking-wider text-white">
                    {m.label}
                  </span>
                  {isSelected && (
                    <span className="w-2.5 h-2.5 rounded-full bg-purple-400 shadow-md shadow-purple-400" />
                  )}
                </div>
                <span className="inline-block text-[10px] font-black uppercase px-2 py-0.5 rounded bg-white/10 text-slate-300 mb-2">
                  {m.badge}
                </span>
                <p className="text-[11px] text-slate-400 leading-relaxed">{m.desc}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* 3. 3D Executive Boardroom Presentation Suite */}
      <div className="rounded-2xl border border-amber-500/30 bg-slate-950/90 p-6 shadow-2xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center">
              <Building className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-black uppercase tracking-widest text-amber-400">
                  GTEX Living 3D Suite
                </span>
                <span className="text-[10px] px-2 py-0.2 rounded bg-amber-500/20 text-amber-300 font-mono">
                  Scene: {boardroomScene}
                </span>
              </div>
              <h3 className="text-base font-bold text-white">Executive Boardroom 3D Environment</h3>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={() =>
                setBoardroomScene(
                  boardroomScene === "boardroom_meeting" ? "boardroom_clash" : "boardroom_meeting"
                )
              }
              className="px-3 py-1.5 rounded-lg text-xs font-bold bg-white/5 hover:bg-white/10 border border-white/10 text-slate-200 transition"
              data-testid="btn-toggle-boardroom-lighting"
            >
              Toggle Ambiance ({boardroomScene === "boardroom_meeting" ? "Day Meeting" : "Night Clash"})
            </button>
            <button
              type="button"
              onClick={() => setShow3DSuite(!show3DSuite)}
              className="px-3 py-1.5 rounded-lg text-xs font-bold bg-white/5 hover:bg-white/10 border border-white/10 text-slate-400 hover:text-white transition"
            >
              {show3DSuite ? "Collapse 3D" : "Expand 3D"}
            </button>
          </div>
        </div>

        {show3DSuite && (
          <div className="h-[280px] sm:h-[340px] rounded-xl overflow-hidden border border-white/10 shadow-inner relative">
            <GtexSceneViewport
              sceneId={boardroomScene}
              autoRotate={true}
              qualityPreset="high"
              showControls={true}
              customTitle="Executive Boardroom & High-Stakes Negotiation Suite"
            />
          </div>
        )}
      </div>

      {/* 4. Financial Thresholds Configuration */}
      {thresholds && (
        <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-xs font-black uppercase tracking-wider text-slate-300 flex items-center space-x-2">
                <DollarSign className="w-4 h-4 text-amber-400" />
                <span>Financial Authority Thresholds (GTX)</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Staff proposals exceeding these financial ceilings automatically escalate to the Chairman for approval.
              </p>
            </div>
            <button
              type="button"
              disabled={savingThresholds || policy?.is_suspended}
              onClick={handleSaveThresholds}
              className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-purple-600 hover:bg-purple-500 shadow-md shadow-purple-950/40 transition flex items-center space-x-1.5 self-start sm:self-auto"
              data-testid="btn-save-thresholds"
            >
              <CheckCircle className="w-3.5 h-3.5" />
              <span>Save Approval Limits</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="bg-black/40 border border-white/10 rounded-xl p-3.5 space-y-1">
              <label className="text-[10px] font-black uppercase tracking-wider text-slate-400 block">
                Player Recruitment Ceiling
              </label>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  min="0"
                  step="1000"
                  disabled={policy?.is_suspended}
                  value={thresholds.recruitment_max_gtex}
                  onChange={(e) =>
                    setThresholds({ ...thresholds, recruitment_max_gtex: Number(e.target.value) })
                  }
                  className="w-full bg-slate-950 border border-white/20 rounded-lg px-2.5 py-1.5 text-xs text-amber-300 font-mono font-bold focus:outline-none focus:border-purple-400"
                  data-testid="input-recruitment-threshold"
                />
                <span className="text-xs text-slate-400 font-mono">GTX</span>
              </div>
            </div>

            <div className="bg-black/40 border border-white/10 rounded-xl p-3.5 space-y-1">
              <label className="text-[10px] font-black uppercase tracking-wider text-slate-400 block">
                Minimum Player Sale Floor
              </label>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  min="0"
                  step="1000"
                  disabled={policy?.is_suspended}
                  value={thresholds.sales_min_gtex}
                  onChange={(e) =>
                    setThresholds({ ...thresholds, sales_min_gtex: Number(e.target.value) })
                  }
                  className="w-full bg-slate-950 border border-white/20 rounded-lg px-2.5 py-1.5 text-xs text-amber-300 font-mono font-bold focus:outline-none focus:border-purple-400"
                  data-testid="input-sales-threshold"
                />
                <span className="text-xs text-slate-400 font-mono">GTX</span>
              </div>
            </div>

            <div className="bg-black/40 border border-white/10 rounded-xl p-3.5 space-y-1">
              <label className="text-[10px] font-black uppercase tracking-wider text-slate-400 block">
                Season sales target
              </label>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  min="0"
                  step="1000"
                  disabled={policy?.is_suspended}
                  value={thresholds.sales_target_gtex || 0}
                  onChange={(e) =>
                    setThresholds({ ...thresholds, sales_target_gtex: Number(e.target.value) })
                  }
                  className="w-full bg-slate-950 border border-white/20 rounded-lg px-2.5 py-1.5 text-xs text-amber-300 font-mono font-bold focus:outline-none focus:border-purple-400"
                  data-testid="input-sales-target"
                />
                <span className="text-xs text-slate-400 font-mono">GTX</span>
              </div>
            </div>

            <div className="bg-black/40 border border-white/10 rounded-xl p-3.5 space-y-1">
              <label className="text-[10px] font-black uppercase tracking-wider text-slate-400 block">
                Operational Spend Ceiling
              </label>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  min="0"
                  step="500"
                  disabled={policy?.is_suspended}
                  value={thresholds.operational_spend_max_gtex}
                  onChange={(e) =>
                    setThresholds({
                      ...thresholds,
                      operational_spend_max_gtex: Number(e.target.value),
                    })
                  }
                  className="w-full bg-slate-950 border border-white/20 rounded-lg px-2.5 py-1.5 text-xs text-amber-300 font-mono font-bold focus:outline-none focus:border-purple-400"
                  data-testid="input-operational-threshold"
                />
                <span className="text-xs text-slate-400 font-mono">GTX</span>
              </div>
            </div>

            <div className="bg-black/40 border border-white/10 rounded-xl p-3.5 space-y-1">
              <label className="text-[10px] font-black uppercase tracking-wider text-slate-400 block">
                Contract Renewal Max Wage
              </label>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  min="0"
                  step="500"
                  disabled={policy?.is_suspended}
                  value={thresholds.contract_renewal_max_weekly_wage_gtex}
                  onChange={(e) =>
                    setThresholds({
                      ...thresholds,
                      contract_renewal_max_weekly_wage_gtex: Number(e.target.value),
                    })
                  }
                  className="w-full bg-slate-950 border border-white/20 rounded-lg px-2.5 py-1.5 text-xs text-amber-300 font-mono font-bold focus:outline-none focus:border-purple-400"
                  data-testid="input-contract-threshold"
                />
                <span className="text-xs text-slate-400 font-mono">FAN/wk</span>
              </div>
            </div>

            <div className="bg-black/40 border border-white/10 rounded-xl p-3.5 space-y-1">
              <label className="text-[10px] font-black uppercase tracking-wider text-slate-400 block">
                Campus Facility Spend Ceiling
              </label>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  min="0"
                  step="1000"
                  disabled={policy?.is_suspended}
                  value={thresholds.facility_spend_max_gtex}
                  onChange={(e) =>
                    setThresholds({
                      ...thresholds,
                      facility_spend_max_gtex: Number(e.target.value),
                    })
                  }
                  className="w-full bg-slate-950 border border-white/20 rounded-lg px-2.5 py-1.5 text-xs text-amber-300 font-mono font-bold focus:outline-none focus:border-purple-400"
                  data-testid="input-facility-threshold"
                />
                <span className="text-xs text-slate-400 font-mono">GTX</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5. Main Functional Views Navigation */}
      <div className="space-y-6">
        <div className="flex flex-wrap items-center gap-2 border-b border-white/10 pb-4">
          <button
            type="button"
            onClick={() => setActiveTab("org")}
            className={`flex items-center space-x-2 px-5 py-3 rounded-2xl text-xs font-black uppercase tracking-wider transition ${
              activeTab === "org"
                ? "bg-purple-600 text-white shadow-xl shadow-purple-950/50 border border-purple-400"
                : "bg-white/5 text-slate-300 hover:text-white hover:bg-white/10 border border-white/5"
            }`}
            data-testid="tab-org-hierarchy"
          >
            <Users className="w-4 h-4" />
            <span>Organizational Hierarchy</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("matrix")}
            className={`flex items-center space-x-2 px-5 py-3 rounded-2xl text-xs font-black uppercase tracking-wider transition ${
              activeTab === "matrix"
                ? "bg-purple-600 text-white shadow-xl shadow-purple-950/50 border border-purple-400"
                : "bg-white/5 text-slate-300 hover:text-white hover:bg-white/10 border border-white/5"
            }`}
            data-testid="tab-activity-matrix"
          >
            <Sliders className="w-4 h-4" />
            <span>Activity Delegation Matrix</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("escalations")}
            className={`flex items-center space-x-2 px-5 py-3 rounded-2xl text-xs font-black uppercase tracking-wider transition relative ${
              activeTab === "escalations"
                ? "bg-purple-600 text-white shadow-xl shadow-purple-950/50 border border-purple-400"
                : "bg-white/5 text-slate-300 hover:text-white hover:bg-white/10 border border-white/5"
            }`}
            data-testid="tab-pending-escalations"
          >
            <FileCheck className="w-4 h-4" />
            <span>Pending Escalations</span>
            {escalations.length > 0 && (
              <span className="ml-1.5 px-2 py-0.5 rounded-full text-[10px] font-black bg-amber-400 text-black">
                {escalations.length}
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("audit")}
            className={`flex items-center space-x-2 px-5 py-3 rounded-2xl text-xs font-black uppercase tracking-wider transition ${
              activeTab === "audit"
                ? "bg-purple-600 text-white shadow-xl shadow-purple-950/50 border border-purple-400"
                : "bg-white/5 text-slate-300 hover:text-white hover:bg-white/10 border border-white/5"
            }`}
            data-testid="tab-decision-audit"
          >
            <History className="w-4 h-4" />
            <span>Decision Audit Log</span>
          </button>
        </div>

        {/* Tab Body */}
        <div>
          {activeTab === "org" && (
            <OrganizationalStructureView orgStructure={orgStructure} isLoading={loading} />
          )}

          {activeTab === "matrix" && (
            <DelegationActivityMatrix
              clubId={clubId}
              policy={policy}
              onPolicyUpdated={(up) => {
                setPolicy(up);
                setThresholds(up.financial_thresholds);
              }}
            />
          )}

          {activeTab === "escalations" && (
            <PendingEscalationsCard
              clubId={clubId}
              escalations={escalations}
              onDecisionResolved={handleDecisionResolved}
            />
          )}

          {activeTab === "audit" && (
            <DecisionAuditHistory decisions={decisions} isLoading={loading} />
          )}
        </div>
      </div>
    </div>
  );
};
