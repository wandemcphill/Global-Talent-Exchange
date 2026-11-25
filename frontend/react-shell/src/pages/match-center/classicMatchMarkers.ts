export type ClassicLineupStat = {
  goals: number;
  assists: number;
  yellow: number;
  red: number;
  rating: number;
};

/** Match line from events already played. Quiet players stay on the opening mark. */
export function classicLineupStat(
  events: ReadonlyArray<Record<string, unknown>> | null | undefined,
  playerId: string,
  timeSeconds: number,
): ClassicLineupStat {
  let goals = 0;
  let assists = 0;
  let yellow = 0;
  let red = 0;
  let rating = 6.4;
  for (const event of events || []) {
    const at = Number(event.time_seconds ?? event.timeSeconds);
    if (Number.isFinite(at) && at > timeSeconds + 0.05) continue;
    const type = String(event.type || event.event_type || "").toLowerCase();
    if (type === "kickoff") continue;
    const primary = String(event.primary_player_id || event.player_id || "");
    const secondary = String(event.secondary_player_id || "");
    const isPrimary = primary === playerId;
    const isSecondary = secondary === playerId && secondary !== primary;
    if (type === "goal" || type === "penalty_goal") {
      if (isPrimary) {
        goals += 1;
        rating += 1.1;
      }
      if (isSecondary) {
        assists += 1;
        rating += 0.6;
      }
      continue;
    }
    if (type === "own_goal" && isPrimary) {
      goals += 1;
      rating -= 0.8;
      continue;
    }
    if (type === "save") {
      if (isPrimary) rating += 0.45;
      if (isSecondary) rating += 0.25;
      continue;
    }
    if (type === "yellow_card" || type === "second_yellow") {
      if (isPrimary) {
        yellow += 1;
        rating -= 0.4;
      }
      continue;
    }
    if (type === "red_card") {
      if (isPrimary) {
        red += 1;
        rating -= 1;
      }
      continue;
    }
    if (isPrimary) rating += 0.15;
    else if (isSecondary) rating += 0.1;
  }
  return {
    goals,
    assists,
    yellow,
    red,
    rating: Math.max(5, Math.min(9.9, Math.round(rating * 10) / 10)),
  };
}

export function clubCode(name: string): string {
  const word = String(name || "").trim().split(/\s+/)[0] || "";
  const letters = word.replace(/[^A-Za-z]/g, "");
  return (letters.slice(0, 3) || "TM").toUpperCase();
}

export function matchClockLabel(timeSeconds: number | null | undefined, minute: number | null | undefined): string {
  if (typeof timeSeconds === "number" && Number.isFinite(timeSeconds)) {
    const total = Math.max(0, Math.floor(timeSeconds));
    const mins = Math.floor(total / 60);
    const secs = total % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }
  if (typeof minute === "number" && Number.isFinite(minute)) {
    return `${Math.max(0, Math.round(minute))}'`;
  }
  return "00:00";
}

export type ClassicTickKind = "goal" | "card" | "sub";

export type ClassicTick = {
  minute: number;
  kind: ClassicTickKind;
  side: "home" | "away" | null;
};

export function classicEventTicks(
  events: ReadonlyArray<Record<string, unknown>> | null | undefined,
): ClassicTick[] {
  if (!Array.isArray(events)) return [];
  const ticks: ClassicTick[] = [];
  for (const event of events) {
    const rawType = String(event.type || event.event_type || "").toLowerCase();
    const kind: ClassicTickKind | null = /goal/.test(rawType)
      ? "goal"
      : /red_card|yellow_card|card/.test(rawType)
        ? "card"
        : /sub/.test(rawType)
          ? "sub"
          : null;
    if (!kind) continue;
    const minute = Number(event.minute ?? event.clock_minute ?? (Number(event.time_seconds) || 0) / 60);
    if (!Number.isFinite(minute)) continue;
    const sideRaw = String(event.side || event.team || "").toLowerCase();
    ticks.push({
      minute: Math.max(0, minute),
      kind,
      side: sideRaw === "home" || sideRaw === "away" ? sideRaw : null,
    });
  }
  return ticks;
}

export type ClassicFacts = {
  shots: number;
  onTarget: number;
  corners: number;
  fouls: number;
  yellow: number;
  red: number;
};

/** Counts only event types present on the feed. An empty feed stays unfiled. */
export function classicMatchFacts(
  events: ReadonlyArray<Record<string, unknown>> | null | undefined,
): ClassicFacts | null {
  if (!Array.isArray(events) || events.length === 0) return null;
  const facts: ClassicFacts = { shots: 0, onTarget: 0, corners: 0, fouls: 0, yellow: 0, red: 0 };
  let counted = false;
  for (const event of events) {
    const type = String(event.type || event.event_type || "").toLowerCase();
    if (!type) continue;
    counted = true;
    if (type === "shot" || type === "goal" || type === "miss" || type === "save" || type === "penalty" || type === "penalty_goal") {
      facts.shots += 1;
    }
    if (type === "goal" || type === "save" || type === "penalty_goal") facts.onTarget += 1;
    if (type === "corner") facts.corners += 1;
    if (type === "foul") facts.fouls += 1;
    if (type === "yellow_card") facts.yellow += 1;
    if (type === "red_card") facts.red += 1;
  }
  return counted ? facts : null;
}

/** Pitch-plane velocity. Authoritative ball payloads store width on `z` and height on `y`. */
export function ballPlaneVelocity(
  raw: { x?: number; y?: number; z?: number } | null | undefined,
): { x: number; y: number } | null {
  if (!raw) return null;
  const x = Number(raw.x);
  const y = Number(raw.y);
  const z = Number(raw.z);
  if (!Number.isFinite(x)) return null;
  const lateral = Number.isFinite(z) ? z : y;
  if (!Number.isFinite(lateral)) return null;
  return { x, y: lateral };
}
