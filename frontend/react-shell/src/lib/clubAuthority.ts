import { api } from "./api";

export type ManagementMode = "hands_on" | "balanced" | "delegating" | "custom";
export type AuthorityLevel = "owner_only" | "requires_pre_approval" | "delegated_with_limits" | "full_autonomy";
export type DecisionStatus = "pending_approval" | "auto_approved" | "approved" | "rejected" | "overridden";

export interface ActivityAssignment {
  activity_key: string;
  domain: "sporting" | "club_operations" | "player_staff";
  responsible_role: string;
  authority_level: AuthorityLevel;
  approval_role: string;
}

export interface FinancialThresholds {
  recruitment_max_gtex: number;
  sales_min_gtex: number;
  operational_spend_max_gtex: number;
  contract_renewal_max_weekly_wage_gtex: number;
  facility_spend_max_gtex: number;
  [key: string]: number;
}

export interface AuthorityPolicy {
  club_id: string;
  mode: ManagementMode;
  is_suspended: boolean;
  suspension_reason?: string | null;
  suspended_at?: string | null;
  activity_assignments: Record<string, ActivityAssignment>;
  reserved_decisions: string[];
  financial_thresholds: FinancialThresholds;
  temporary_overrides: Record<string, any>;
  updated_at?: string | null;
}

export interface StaffMember {
  id: string;
  name: string;
  nationality: string;
  age: number;
  rating: number;
  salary_weekly: number;
  tactical_flexibility?: number;
  youth_development?: number;
  scouting_accuracy?: number;
  medical_expertise?: number;
  ambition?: number;
  loyalty?: number;
  specialty_attributes?: Record<string, any>;
  avatar_url?: string;
}

export interface StaffPosition {
  role_key: string;
  role_label: string;
  is_vacant: boolean;
  appointed_staff: StaffMember | null;
  delegated_activities_count: number;
}

export interface OrgStructure {
  club_id: string;
  owner: {
    user_id: string;
    role: string;
    authority: string;
  };
  staff_positions: StaffPosition[];
}

export interface CompetenceImpact {
  competence_score: number;
  ambition: number;
  loyalty: number;
  success_probability: number;
  recommendation: "strongly_recommended" | "recommended" | "neutral" | "caution" | "risky";
  evaluation_summary: string;
}

export interface DelegatedDecision {
  id: string;
  club_id: string;
  activity_key: string;
  domain: "sporting" | "club_operations" | "player_staff";
  proposed_by_role: string;
  proposed_by_user_id?: string | null;
  status: DecisionStatus;
  title: string;
  summary: string;
  financial_amount_gtex: number;
  requires_owner_approval: boolean;
  escalation_reason?: string | null;
  staff_competence_impact?: CompetenceImpact | null;
  resolved_at?: string | null;
  resolved_by_user_id?: string | null;
  resolution_action?: string | null;
  decision_note?: string | null;
  created_at: string;
}

export interface EscalationsResponse {
  club_id: string;
  pending_count: number;
  escalations: DelegatedDecision[];
}

export interface DecisionsResponse {
  club_id: string;
  count: number;
  decisions: DelegatedDecision[];
}

export interface EvaluationResult {
  activity_key: string;
  allowed: boolean;
  requires_approval: boolean;
  reason: string;
  responsible_role: string;
  authority_level: AuthorityLevel;
  approval_role: string;
  policy_status: "active" | "suspended" | "override";
  staff_impact?: CompetenceImpact | null;
}

// -----------------------------------------------------------------------------
// API Helper Methods
// -----------------------------------------------------------------------------

export async function fetchDelegationPolicy(clubId: string): Promise<AuthorityPolicy> {
  const resp = await api.get(`/owner/clubs/${encodeURIComponent(clubId)}/authority/policy`);
  return resp.data;
}

export async function fetchOrgStructure(clubId: string): Promise<OrgStructure> {
  const resp = await api.get(`/owner/clubs/${encodeURIComponent(clubId)}/authority/org-structure`);
  return resp.data;
}

export async function updateManagementMode(clubId: string, mode: ManagementMode): Promise<AuthorityPolicy> {
  const resp = await api.post(`/owner/clubs/${encodeURIComponent(clubId)}/authority/mode`, { mode });
  return resp.data;
}

export async function updateActivityAssignment(
  clubId: string,
  activityKey: string,
  responsibleRole: string,
  authorityLevel: AuthorityLevel,
  approvalRole: string = "owner"
): Promise<AuthorityPolicy> {
  const resp = await api.put(`/owner/clubs/${encodeURIComponent(clubId)}/authority/activity`, {
    activity_key: activityKey,
    responsible_role: responsibleRole,
    authority_level: authorityLevel,
    approval_role: approvalRole,
  });
  return resp.data;
}

export async function updateFinancialThresholds(
  clubId: string,
  thresholds: Partial<FinancialThresholds>
): Promise<AuthorityPolicy> {
  const resp = await api.put(`/owner/clubs/${encodeURIComponent(clubId)}/authority/thresholds`, thresholds);
  return resp.data;
}

export async function toggleSuspension(clubId: string, suspend: boolean, reason?: string): Promise<AuthorityPolicy> {
  const resp = await api.post(`/owner/clubs/${encodeURIComponent(clubId)}/authority/suspension`, {
    suspend,
    reason,
  });
  return resp.data;
}

export async function applyTemporaryOverride(
  clubId: string,
  activityKey: string,
  overrideRole: string = "owner",
  reason?: string
): Promise<AuthorityPolicy> {
  const resp = await api.post(`/owner/clubs/${encodeURIComponent(clubId)}/authority/override`, {
    activity_key: activityKey,
    override_role: overrideRole,
    reason,
  });
  return resp.data;
}

export async function removeTemporaryOverride(clubId: string, activityKey: string): Promise<AuthorityPolicy> {
  const resp = await api.delete(
    `/owner/clubs/${encodeURIComponent(clubId)}/authority/override/${encodeURIComponent(activityKey)}`
  );
  return resp.data;
}

export async function fetchDecisions(clubId: string, limit: number = 30): Promise<DecisionsResponse> {
  const resp = await api.get(`/owner/clubs/${encodeURIComponent(clubId)}/authority/decisions?limit=${limit}`);
  return resp.data;
}

export async function fetchPendingEscalations(clubId: string): Promise<EscalationsResponse> {
  const resp = await api.get(`/owner/clubs/${encodeURIComponent(clubId)}/authority/escalations`);
  return resp.data;
}

export async function resolveDelegatedDecision(
  clubId: string,
  decisionId: string,
  action: "approve" | "reject" | "override",
  decisionNote?: string
): Promise<DelegatedDecision> {
  const resp = await api.post(
    `/owner/clubs/${encodeURIComponent(clubId)}/authority/decisions/${encodeURIComponent(decisionId)}/resolve`,
    {
      action,
      decision_note: decisionNote,
    }
  );
  return resp.data;
}

export async function evaluateAuthority(
  clubId: string,
  activityKey: string,
  proposedByRole?: string,
  financialAmount?: number
): Promise<EvaluationResult> {
  const resp = await api.post(`/owner/clubs/${encodeURIComponent(clubId)}/authority/evaluate`, {
    activity_key: activityKey,
    proposed_by_role: proposedByRole,
    financial_amount_gtex: financialAmount,
  });
  return resp.data;
}
