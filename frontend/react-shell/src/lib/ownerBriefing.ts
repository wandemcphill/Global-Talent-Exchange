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
  backed_role: string;
  effects_preview: string;
}

export interface BoardroomDilemma {
  dilemma_id: string;
  title: string;
  conflict_summary: string;
  role_a: string;
  role_b: string;
  status: "open" | "resolved";
  selected_choice_id?: string | null;
  resolution_outcome?: string | null;
  choices: BoardroomDilemmaChoice[];
}

export type StaffBriefingSection = {
  role: string;
  sender: string;
  title: string;
  summary: string;
};

export type BriefingMetrics = {
  cash_gtex?: number;
  prestige?: number;
  prestige_tier?: number;
  squad_size?: number;
  avg_morale?: number;
  ready_academy_prospects?: number;
  open_decisions?: number;
};

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
  boardroom_dilemma?: BoardroomDilemma | null;
};

export const clubBriefingEndpoint = (clubId: string) => `/owner/clubs/${encodeURIComponent(clubId)}/briefing`;
export const clubBriefingGenerateEndpoint = (clubId: string) => `/owner/clubs/${encodeURIComponent(clubId)}/briefing/generate`;
export const clubBriefingResolveDilemmaEndpoint = (clubId: string) =>
  `/owner/clubs/${encodeURIComponent(clubId)}/briefing/resolve-dilemma`;

/** Resolve what the panel should show. With no published contract this is always `unavailable`. */
export function useOwnerBriefing(): BriefingViewState {
  if (!OWNER_BRIEFING_ENDPOINT) return { status: "unavailable" };
  // Intentionally unreachable until a backend contract exists; see header comment.
  return { status: "unavailable" };
}
