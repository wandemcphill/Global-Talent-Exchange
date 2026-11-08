export interface LivingWorldRelationship {
  id: string;
  club_id: string;
  pairing_key: string;
  participant_a_type: string;
  participant_a_id: string;
  participant_a_name: string;
  participant_b_type: string;
  participant_b_id: string;
  participant_b_name: string;
  trust: number;
  respect: number;
  affinity: number;
  tension: number;
  alignment?: number;
  influence?: number;
  loyalty?: number;
  status: string;
  status_label: string;
  metadata?: Record<string, any>;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface LivingWorldEvent {
  id: string;
  club_id: string;
  category: "executive" | "tactical" | "squad" | "academy" | "medical" | "financial" | "culture" | string;
  event_type: string;
  severity: "routine" | "important" | "critical" | string;
  status: "created" | "active" | "awaiting_decision" | "resolved" | "expired" | string;
  source_type: string;
  source_id?: string | null;
  title: string;
  description: string;
  participants: Array<{ role: string; name: string; id?: string }>;
  world_day: number;
  consequences: Record<string, any>;
  actions: Array<{ key: string; label: string; style?: string }>;
  idempotency_key?: string | null;
  resolved_at?: string | null;
  resolution_action?: string | null;
  resolution_note?: string | null;
  created_at?: string | null;
}

export interface LivingWorldDirective {
  id: string;
  club_id: string;
  department: "manager" | "medical" | "academy" | "finance" | "scouting" | "executive" | string;
  directive_key: string;
  title: string;
  instruction: string;
  target_scope?: string | null;
  target_scope_id?: string | null;
  status: "active" | "completed" | "failed" | "cancelled" | string;
  issued_day: number;
  deadline_day?: number | null;
  acknowledged_by?: string | null;
  acknowledgement_text?: string | null;
  objective_key?: string | null;
  objective_label?: string | null;
  consequences: Record<string, any>;
  completed_at?: string | null;
  created_at?: string | null;
}

export interface LivingWorldTimelineItem {
  id: string;
  kind: "event" | "directive" | "relationship_shift";
  category: string;
  severity: string;
  title: string;
  description: string;
  world_day: number;
  status: string;
  participants: Array<Record<string, any>>;
  consequences: Record<string, any>;
  actions: Array<{ key: string; label: string; style?: string }>;
  resolved_at?: string | null;
  resolution_action?: string | null;
  resolution_note?: string | null;
  acknowledged_by?: string | null;
  acknowledgement_text?: string | null;
  deadline_day?: number | null;
  delta_trust?: number | null;
  delta_respect?: number | null;
  delta_affinity?: number | null;
  delta_tension?: number | null;
  reason?: string | null;
  created_at?: string | null;
}

export interface LivingWorldTimelineResponse {
  club_id: string;
  total_count: number;
  total_events_count: number;
  counts_by_kind?: {
    event: number;
    directive: number;
    relationship_shift: number;
  };
  limit: number;
  offset: number;
  items: LivingWorldTimelineItem[];
}

export interface LivingWorldPayload {
  active_events_count: number;
  active_events: LivingWorldEvent[];
  active_directives_count: number;
  active_directives: LivingWorldDirective[];
  relationships: LivingWorldRelationship[];
  department_activity: Record<
    string,
    {
      events_count: number;
      directives_count: number;
      activity_score: number;
      has_critical: boolean;
    }
  >;
}

/**
 * Typed boundary for the owner daily briefing.
 *
 * STATUS: BLOCKED ON BACKEND CONTRACT. As of this change no persisted briefing/event endpoint is
 * published (PR #341 tracks it as Agent A work packet A5; cadence decision D7 is unapproved).
 * `OWNER_BRIEFING_ENDPOINT` is therefore `null` and the UI renders an honest "unavailable" state.
 * Nothing here generates, infers or caches stories client-side.
 *
 * The shapes below are the *minimum* a verified event card needs. When the backend publishes the
 * real schema, update `parseOwnerBriefing` and set the endpoint; the UI components do not change.
 */
export const OWNER_BRIEFING_ENDPOINT: string | null = null;

export type BriefingTarget =
  | { type: "decision"; inboxItemId: string }
  | { type: "club_history"; clubId: string }
  | { type: "match_result"; matchId: string };

export type BriefingEvent = {
  /** Persisted event identifier. Cards without one are never rendered. */
  eventId: string;
  headline: string;
  /** Server-issued virtual timestamp of the event. */
  occurredAt: string;
  detail?: string;
  target: BriefingTarget | null;
};

export type OwnerBriefing = {
  briefingId: string;
  clubId: string;
  worldDate: string;
  events: BriefingEvent[];
  /** Events dropped because they failed verification (missing id/headline/timestamp). */
  rejectedEventCount: number;
  /** Optional AI prose. Explanatory only; never the source of game facts. */
  explanation?: string;
  boardroom_dilemma?: BoardroomDilemma | null;
};

export type BriefingViewState =
  | { status: "loading" }
  | { status: "unavailable" }
  | { status: "error"; message?: string }
  | { status: "empty"; worldDate?: string }
  | { status: "ready"; briefing: OwnerBriefing; stale?: boolean };

const str = (v: unknown): string | undefined => (typeof v === "string" && v.trim() ? v.trim() : undefined);

function parseTarget(raw: any): BriefingTarget | null {
  if (!raw || typeof raw !== "object") return null;
  switch (raw.type) {
    case "decision": {
      const id = str(raw.inbox_item_id);
      return id ? { type: "decision", inboxItemId: id } : null;
    }
    case "club_history": {
      const id = str(raw.club_id);
      return id ? { type: "club_history", clubId: id } : null;
    }
    case "match_result": {
      const id = str(raw.match_id);
      return id ? { type: "match_result", matchId: id } : null;
    }
    default:
      return null;
  }
}

export function parseOwnerBriefing(raw: any): OwnerBriefing {
  const briefingId = str(raw?.briefing_id);
  const clubId = str(raw?.club_id);
  const worldDate = str(raw?.world_date);
  if (!briefingId || !clubId || !worldDate) throw new Error("owner_briefing_contract_violation");
  const events: BriefingEvent[] = [];
  let rejected = 0;
  for (const e of Array.isArray(raw.events) ? raw.events : []) {
    const eventId = str(e?.event_id);
    const headline = str(e?.headline);
    const occurredAt = str(e?.occurred_at);
    if (!eventId || !headline || !occurredAt) {
      rejected += 1;
      continue;
    }
    events.push({ eventId, headline, occurredAt, detail: str(e?.detail), target: parseTarget(e?.target) });
  }
  return { briefingId, clubId, worldDate, events, rejectedEventCount: rejected, explanation: str(raw?.explanation) };
}

/** Private decision, club history or match result — each routes to an existing React page. */
export function briefingTargetPath(target: BriefingTarget | null): string | null {
  if (!target) return null;
  switch (target.type) {
    case "decision":
      return "/app/inbox";
    case "club_history":
      return `/app/clubs/${encodeURIComponent(target.clubId)}/story`;
    case "match_result":
      return `/app/match/${encodeURIComponent(target.matchId)}`;
  }
}

export const briefingTargetLabel = (target: BriefingTarget | null): string | null => {
  if (!target) return null;
  return { decision: "Open decision", club_history: "View club history", match_result: "View match result" }[target.type];
};

export interface BoardroomDilemmaChoice {
  choice_id: string;
  label: string;
  summary: string;
  backed_role?: string;
  effects_preview?: string;
  cost_gtex?: number;
  projected_effects?: string[];
  delta_role_a?: Record<string, number>;
  delta_role_b?: Record<string, number>;
}

export interface BoardroomDilemma {
  dilemma_id: string;
  title: string;
  conflict_summary: string;
  role_a: string;
  role_a_label?: string;
  role_a_name?: string;
  role_b: string;
  role_b_label?: string;
  role_b_name?: string;
  urgency?: "routine" | "important" | "critical" | string;
  status: "open" | "resolved";
  selected_choice_id?: string | null;
  resolution_outcome?: string | null;
  choices: BoardroomDilemmaChoice[];
  world_day?: number;
}

export type StaffBriefingSection = {
  section_key?: string;
  role: string;
  sender: string;
  title: string;
  summary: string;
  destination_key?: string;
};

export type BriefingMetrics = {
  cash_gtex?: number;
  fan_coin?: number;
  distributable_gtex?: number;
  club_valuation_gtex?: number;
  prestige?: number;
  prestige_tier?: string | number;
  squad_size?: number;
  available_players?: number;
  injured_players?: number;
  avg_morale?: number;
  avg_fitness?: number;
  ready_academy_prospects?: number;
  academy_prospects_total?: number;
  open_decisions?: number;
  active_campus_projects?: number;
  operational_stadium_capacity?: number;
};

export interface OperationalRecommendation {
  decision_id: string;
  world_day: number;
  department: string;
  staff_role: string;
  staff_name: string;
  title: string;
  summary: string;
  action_type: string;
  cost_gtex: number;
  effects_preview: string;
  payload?: Record<string, unknown>;
  status: "open" | "approved" | "rejected" | "resolved";
  created_at?: string;
  resolved_at?: string | null;
  resolution_outcome?: string | null;
}

export interface DepartmentStaffProfile {
  role_key: string;
  role_label: string;
  name: string;
  style?: string;
  mood?: number;
  loyalty?: number;
  specialty?: string;
}

export interface ExecutiveBriefingSection {
  section_key: "executive_briefing";
  role: string;
  sender: string;
  title: string;
  summary: string;
  financial_position?: {
    cash_gtex: number;
    fan_coin: number;
    distributable_gtex: number;
    club_valuation_gtex: number;
    daily_wage_bill_gtex: number;
    daily_sponsor_income_gtex: number;
    active_sponsor_name?: string | null;
  };
  squad_condition_and_availability?: {
    squad_size: number;
    available_players: number;
    injured_players: number;
    avg_morale: number;
    avg_fitness: number;
    low_morale_count: number;
    team_strength: number;
    mentality: string;
  };
  recent_match_performance?: {
    matches_played: number;
    wins: number;
    draws: number;
    losses: number;
    goals_for: number;
    goals_against: number;
    win_rate_pct: number;
    recent_results: Array<Record<string, unknown>>;
  };
  upcoming_fixtures_and_commitments?: Array<Record<string, unknown>>;
  academy_and_youth_activity?: {
    academy_level: number;
    total_youth_players: number;
    ready_for_first_team: number;
    high_potential_prospects: number;
    intake_quality_bonus: number;
    regen_potential_bonus: number;
  };
  medical_and_rehabilitation?: {
    medical_level: number;
    injured_count: number;
    daily_injury_heal_days: number;
    injury_incidence_reduction_pct: number;
    daily_fitness_recovery_bonus: number;
  };
  stadium_and_campus_operations?: {
    stadium_level: number;
    operational_stadium_capacity: number;
    placed_buildings_count: number;
    active_construction_count: number;
    gate_revenue_bonus_pct: number;
    sponsor_bonus_pct: number;
  };
  outstanding_decisions_count?: number;
  urgent_risks?: Array<{
    risk_id: string;
    severity: "high" | "medium" | "low";
    department: string;
    title: string;
    detail: string;
  }>;
}

export type DailyBriefing = {
  id?: string;
  club_id?: string;
  world_day?: number;
  headline?: string;
  summary?: string;
  body?: string;
  created_at?: string;
  generated_at?: string;
  metrics?: BriefingMetrics;
  sections?: StaffBriefingSection[];
  executive_briefing?: ExecutiveBriefingSection;
  managers_report?: Record<string, any>;
  general_managers_report?: Record<string, any>;
  hoyd_report?: Record<string, any>;
  medical_directors_report?: Record<string, any>;
  financial_commercial_report?: Record<string, any>;
  department_decisions?: OperationalRecommendation[];
  decision_history?: Array<Record<string, any>>;
  boardroom_dilemma?: BoardroomDilemma | null;
};

export interface OperationsHubDestination {
  destination_key:
    | "executive_office"
    | "managers_office"
    | "general_managers_office"
    | "academy_department"
    | "medical_department"
    | "finance_commercial_office";
  label: string;
  short_label: string;
  subtitle: string;
  lead_role_key: string;
  staff_lead: DepartmentStaffProfile;
  glb_model: string;
  exterior_glb: string;
  accent_color: string;
  position_3d: [number, number, number];
  camera_position: [number, number, number];
  camera_target: [number, number, number];
  hotspots: Array<{
    id: string;
    label: string;
    action: string;
    offset: [number, number, number];
  }>;
  report_section_key: string;
  report: Record<string, any>;
  open_decisions: OperationalRecommendation[];
  open_decisions_count: number;
  recent_messages: Array<{
    id?: string;
    role?: string;
    sender?: string;
    message?: string;
    topic?: string;
    created_at?: string;
  }>;
  active_events?: LivingWorldEvent[];
  active_events_count?: number;
  active_directives?: LivingWorldDirective[];
  active_directives_count?: number;
  relationship?: LivingWorldRelationship | null;
  activity_score?: number;
}

export interface ClubOperationsHubPayload {
  club: {
    club_id: string;
    club_name: string;
    world_day: number;
    prestige: number;
    prestige_tier: string;
    fans: number;
    mentality: string;
    cash_gtex: number;
    fan_coin: number;
    club_valuation_gtex: number;
  };
  daily_briefing: DailyBriefing;
  destinations: OperationsHubDestination[];
  actionable_decisions: {
    department_decisions: OperationalRecommendation[];
    inbox_decisions: Array<Record<string, any>>;
    boardroom_dilemma?: BoardroomDilemma | null;
    total_open_count: number;
  };
  operational_timeline: Array<{
    id: string;
    world_day: number;
    department: string;
    title: string;
    detail: string;
    category: string;
    created_at: string;
  }>;
  decision_history: Array<{
    history_id: string;
    decision_id: string;
    world_day: number;
    department: string;
    title: string;
    action_taken: string;
    cost_gtex: number;
    outcome: string;
    resolved_by_user_id: string;
    resolved_at: string;
  }>;
  living_world?: LivingWorldPayload;
}

export const clubBriefingEndpoint = (clubId: string) => `/owner/clubs/${encodeURIComponent(clubId)}/briefing`;
export const clubBriefingGenerateEndpoint = (clubId: string) => `/owner/clubs/${encodeURIComponent(clubId)}/briefing/generate`;
export const clubBriefingResolveDilemmaEndpoint = (clubId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/briefing/resolve-dilemma`;
export const clubOperationsHubEndpoint = (clubId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/operations-hub`;
export const clubExecuteOperationalDecisionEndpoint = (clubId: string, decisionId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/operations/decisions/${encodeURIComponent(decisionId)}/execute`;
export const clubLivingWorldTimelineEndpoint = (clubId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/timeline`;
export const clubLivingWorldRelationshipsEndpoint = (clubId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/relationships`;
export const clubCreateDirectiveEndpoint = (clubId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/directives`;
export const clubResolveEventEndpoint = (clubId: string, eventId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/events/${encodeURIComponent(eventId)}/resolve`;
export const clubPersonaDetailsEndpoint = (clubId: string, personaRole: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/personas/${encodeURIComponent(personaRole)}`;
export const clubPersonaInteractEndpoint = (clubId: string, personaRole: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/personas/${encodeURIComponent(personaRole)}/interact`;

export type PersonaInteractionActionType =
  | "align_strategy"
  | "praise_leadership"
  | "demand_accountability"
  | "request_briefing"
  | "discuss_directive"
  | "general_dialogue";

export interface PersonaProfile {
  role_key: string;
  role_label: string;
  name: string;
  person_id?: string | null;
  is_appointed: boolean;
  department: string;
}

export interface PersonaInteractionPayload {
  action_type: PersonaInteractionActionType;
  dialogue_text?: string;
}

export interface PersonaRelationshipHistoryItem {
  id: string;
  world_day: number;
  reason: string;
  delta_alignment: number;
  delta_influence: number;
  delta_loyalty: number;
  delta_trust: number;
  delta_tension: number;
  created_at?: string;
}

export interface PersonaDetailsResponse {
  club_id: string;
  persona: PersonaProfile;
  relationship: LivingWorldRelationship | null;
  active_directives: LivingWorldDirective[];
  recent_history: PersonaRelationshipHistoryItem[];
  world_day: number;
}

export interface PersonaInteractionResponse {
  success: boolean;
  action_type: PersonaInteractionActionType;
  action_label: string;
  persona: PersonaProfile;
  relationship: LivingWorldRelationship | null;
  delta_applied: {
    trust: number;
    respect: number;
    affinity: number;
    tension: number;
    alignment: number;
    influence: number;
    loyalty: number;
  };
  dialogue_reply: string;
  world_day: number;
}

export interface DelegatedDecisionItem {
  id: string;
  world_day: number;
  authority_level: string;
  staff_role: string;
  staff_name?: string | null;
  category: string;
  action_type: string;
  title: string;
  description: string;
  cost_gtex: number;
  status: string;
  execution_status: string;
  consequences: Record<string, any>;
  escalation_reason?: string | null;
  created_at?: string | null;
  executed_at?: string | null;
}

export interface DelegatedDecisionsResponse {
  club_id: string;
  policy: {
    authority_mode: string;
    is_active: boolean;
    budget_limit_gtex: number;
    thresholds: Record<string, number>;
  };
  decisions: DelegatedDecisionItem[];
  total_count: number;
}

export interface AutonomousSimulationResponse {
  club_id: string;
  world_day: number;
  policy_mode: string;
  decisions_evaluated: number;
  decisions_executed: number;
  decisions_escalated: number;
  decisions_blocked: number;
  results: Array<{
    decision_id: string;
    staff_role: string;
    staff_name: string;
    category: string;
    action_type: string;
    cost_gtex: number;
    status: string;
    execution_status: string;
    consequences: Record<string, any>;
  }>;
}

export interface ResolveDilemmaPayload {
  choice_id: string;
  decision_note?: string;
}

export interface ResolveDilemmaResponse {
  success: boolean;
  dilemma_id: string;
  choice_id: string;
  selected_choice: BoardroomDilemmaChoice;
  narrative_outcome: string;
  club_id: string;
  world_day: number;
  updated_relationships: {
    role_a: LivingWorldRelationship | null;
    role_b: LivingWorldRelationship | null;
  };
}

export const clubActiveDilemmaEndpoint = (clubId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/dilemmas/active`;

export const clubResolveDilemmaEndpoint = (clubId: string, dilemmaId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/dilemmas/${encodeURIComponent(dilemmaId)}/resolve`;

export const clubSimulateAutonomousDecisionsEndpoint = (clubId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/autonomous-decisions/simulate`;

export const clubDelegatedDecisionsEndpoint = (clubId: string, limit = 20) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/delegated-decisions?limit=${encodeURIComponent(limit)}`;

// ---------- Stage 4: Autonomous Staff Career & Professional Employment Market ----------

export interface StaffCareerHistoryItem {
  club_id: string;
  club_name?: string;
  role: string;
  started_at?: string;
  ended_at?: string;
  status: "ongoing" | "dismissed" | "resigned" | "contract_expiry" | string;
  contract_years?: number;
  tenure_years?: number;
  salary_gtex?: number;
  reason_for_leaving?: string;
  exit_reason?: string;
  severance_paid?: number;
  matches_managed?: number;
  win_rate?: number;
  win_rate_pct?: number;
}

export interface StaffMarketCandidate {
  profile_id: string;
  market_key: string;
  staff_id: string;
  name: string;
  role_key: string;
  role_label: string;
  rating: number;
  rarity: string;
  skills: string[];
  reputation: number;
  experience_years: number;
  temperament: string;
  style: string;
  ambition: number;
  loyalty: number;
  expected_salary_gtex: number;
  min_prestige: number;
  employment_status: "employed" | "unemployed" | "retired" | string;
  current_club_id?: string | null;
  can_attract: boolean;
  interest_level: "very_high" | "interested" | "requires_premium" | "unlikely" | string;
  career_history: StaffCareerHistoryItem[];
}

export interface StaffMarketPoolResponse {
  club_id: string;
  club_prestige: number;
  total_count: number;
  candidates: StaffMarketCandidate[];
}

export interface StaffVacancyItem {
  role_key: string;
  role_label: string;
  is_urgent: boolean;
  provisional_name: string;
  recommended_min_rating: number;
}

export interface StaffFilledRoleItem {
  role_key: string;
  role_label: string;
  incumbent_name: string;
  staff_id: string;
  appointed_at?: string;
  salary_gtex: number;
  mood: number;
}

export interface StaffVacanciesResponse {
  club_id: string;
  club_prestige: number;
  vacancies_count: number;
  vacancies: StaffVacancyItem[];
  filled_roles: StaffFilledRoleItem[];
}

export interface StaffOfferSubmitPayload {
  profile_id: string;
  role?: string;
  offered_salary_gtex?: number;
  contract_years: number;
  marquee_wage_premium?: boolean;
  pitch_note?: string;
}

export interface StaffOfferResponse {
  status: "accepted" | "rejected" | "counter_offer";
  success: boolean;
  message: string;
  contract_id?: string;
  assignment_id?: string;
  appointed_staff?: Record<string, any>;
  total_contract_fee?: number;
  reason?: string;
  counter_salary_gtex?: number;
  required_salary_gtex?: number;
}

export interface StaffDismissPayload {
  role: string;
  reason?: string;
}

export interface StaffDismissResponse {
  status: "dismissed";
  success: boolean;
  role: string;
  staff_name: string;
  severance_paid: number;
  entered_free_agency: boolean;
  profile_id?: string;
}

export const clubStaffMarketVacanciesEndpoint = (clubId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/staff-market/vacancies`;

export const clubStaffMarketCandidatesEndpoint = (
  clubId: string,
  role?: string,
  employmentStatus: string = "unemployed",
  limit: number = 50
) => {
  const params = new URLSearchParams();
  if (role) params.set("role", role);
  if (employmentStatus) params.set("employment_status", employmentStatus);
  params.set("limit", String(limit));
  return `/owner/clubs/${encodeURIComponent(clubId)}/living-world/staff-market/candidates?${params.toString()}`;
};

export const clubStaffCandidateDossierEndpoint = (clubId: string, profileId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/staff-market/candidates/${encodeURIComponent(profileId)}`;

export const clubStaffMarketOffersEndpoint = (clubId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/staff-market/offers`;

export const clubStaffMarketDismissEndpoint = (clubId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/staff-market/dismiss`;

// ---------- Stage 5: General Manager Delegation & Owner Control Engine ----------

export interface GmDelegationActivityItem {
  activity_key: string;
  label: string;
  description: string;
  category: string;
  department: string;
  requires_owner_approval: boolean;
  gm_can_execute: boolean;
  execution_supported?: boolean;
  policy_suspended?: boolean;
  expenditure_limit_gtex?: number;
  delegation_level: string;
}

export interface GmDelegationFinancialControls {
  max_expenditure_unapproved_gtex: number;
  max_staff_salary_unapproved_gtex: number;
  max_contract_years_unapproved: number;
  recruitment_budget_gtex: number;
  wage_budget_gtex: number;
  min_sale_value_gtex: number;
  allow_emergency_spending: boolean;
}

export interface GmProposalItem {
  id: string;
  activity_key: string;
  domain: string;
  proposed_by_role: string;
  proposed_by_staff_name: string;
  title: string;
  summary: string;
  financial_amount_gtex: number;
  requires_owner_approval: boolean;
  status: "pending_approval" | "approved" | "rejected" | "executed" | string;
  execution_status: string;
  outcome_text?: string | null;
  payload?: Record<string, any>;
  created_at: string;
}

export interface GmDelegationAuditItem {
  id: string;
  decision_id: string;
  actor_role: string;
  action: string;
  reason: string;
  note?: string | null;
  occurred_at: string;
}

export interface GmDelegationOverviewResponse {
  club_id: string;
  gm_staff: {
    id: string;
    name: string;
    role: string;
    rating: number;
    salary_gtex: number;
    trust: number;
    tension: number;
    alignment: number;
    loyalty: number;
    is_appointed: boolean;
  };
  delegation_mode: "owner_managed" | "balanced" | "gm_led" | "custom" | string;
  canonical_mode: "owner_managed" | "balanced" | "gm_led" | "custom" | string;
  financial_controls: GmDelegationFinancialControls;
  activities: GmDelegationActivityItem[];
  pending_proposals: GmProposalItem[];
  recent_audit_trail: GmDelegationAuditItem[];
  statistics: {
    total_executed: number;
    pending_approval_count: number;
    total_expenditure_approved_gtex: number;
  };
}

export interface GmDelegationModePayload {
  mode: "owner_managed" | "balanced" | "gm_led" | string;
}

export interface GmMatrixUpdatePayload {
  activity_assignments?: Record<string, { requires_owner_approval: boolean }>;
  financial_controls?: Partial<GmDelegationFinancialControls>;
}

export interface GmProposalResolvePayload {
  action: "approve" | "reject";
  decision_note?: string;
}

export interface GmProposalResolveResponse {
  success: boolean;
  decision_id: string;
  proposal_id: string;
  status: "approved" | "rejected";
  execution_status: string;
  outcome_text?: string | null;
  action_taken: string;
  audit_logged: boolean;
  updated_relationships: {
    trust: number;
    tension: number;
    alignment: number;
  };
}

export interface GmEvaluateOperationsResponse {
  club_id: string;
  mode: string;
  evaluated_count: number;
  executed_actions: Array<Record<string, any>>;
  escalated_proposals: Array<Record<string, any>>;
  blocked_actions: Array<Record<string, any>>;
}

export const clubGmDelegationEndpoint = (clubId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/gm-delegation`;

export const clubGmDelegationModeEndpoint = (clubId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/gm-delegation/mode`;

export const clubGmDelegationMatrixEndpoint = (clubId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/gm-delegation/matrix`;

export const clubGmEvaluateOperationsEndpoint = (clubId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/gm-delegation/evaluate-operations`;

export const clubGmResolveProposalEndpoint = (clubId: string, proposalId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/living-world/gm-delegation/proposals/${encodeURIComponent(proposalId)}/resolve`;

/** Resolve what the panel should show. With no published contract this is always `unavailable`. */
export function useOwnerBriefing(): BriefingViewState {
  if (!OWNER_BRIEFING_ENDPOINT) return { status: "unavailable" };
  // Intentionally unreachable until a backend contract exists; see header comment.
  return { status: "unavailable" };
}
