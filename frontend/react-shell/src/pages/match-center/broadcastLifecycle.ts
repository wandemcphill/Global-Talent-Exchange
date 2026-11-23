/** One broadcast lifecycle for every Match Center presentation. */

const TERMINAL_STATUSES = new Set([
  "ft",
  "full_time",
  "fulltime",
  "completed",
  "played",
  "settled",
  "cancelled",
  "canceled",
  "abandoned",
]);

const ACTIVE_CANONICAL_STATUSES = new Set([
  "scheduled",
  "pre_match",
  "live",
  "in_progress",
  "halftime",
  "paused",
  "halted",
]);

export interface BroadcastLifecycleInput {
  status?: unknown;
  phase?: unknown;
}

export function canonicalStatus(live: BroadcastLifecycleInput | null | undefined): string {
  return String(live?.status || "")
    .trim()
    .toLowerCase();
}

export function isTerminalBroadcastStatus(status: string): boolean {
  return TERMINAL_STATUSES.has(status);
}

export function isActiveCanonicalBroadcast(status: string): boolean {
  return ACTIVE_CANONICAL_STATUSES.has(status);
}

export function canonicalBroadcastPhase(live: BroadcastLifecycleInput | null | undefined): string {
  const status = canonicalStatus(live);
  const phase = String(live?.phase || "")
    .trim()
    .toLowerCase();
  if (status === "scheduled" || status === "pre_match" || phase === "pre_match") return "pre_match";
  if (status === "halftime" || phase === "halftime" || phase === "half_time") return "halftime";
  if (status === "paused") return phase === "halftime" ? "halftime" : "paused";
  if (isTerminalBroadcastStatus(status) && status !== "cancelled" && status !== "canceled" && status !== "abandoned") {
    return "full_time";
  }
  if (status === "cancelled" || status === "canceled") return "cancelled";
  if (status === "abandoned") return "abandoned";
  if (status === "halted" || phase === "halted") return "halted";
  if (phase === "full_time" || phase === "fulltime" || phase === "completed") return "full_time";
  return phase || status;
}

/** Keep watching a fixture until the canonical execution is actually terminal. */
export function shouldPollMatchState(live: BroadcastLifecycleInput | null | undefined): boolean {
  if (!live) return true;
  const phase = canonicalBroadcastPhase(live);
  return phase !== "full_time" && phase !== "cancelled" && phase !== "abandoned";
}
