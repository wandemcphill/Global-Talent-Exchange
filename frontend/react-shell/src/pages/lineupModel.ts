export const LINEUP_FORMATIONS = [
  "4-3-3",
  "4-4-2",
  "4-2-3-1",
  "4-1-4-1",
  "3-5-2",
  "3-4-3",
  "5-3-2",
  "5-4-1",
] as const;

export type LineupFormation = (typeof LINEUP_FORMATIONS)[number];

export type LineupPlayer = {
  player_id: string;
  player_name: string;
  position?: string;
  rating?: number | null;
  portrait_url?: string | null;
};

export type LineupPlan = {
  club_id?: string;
  formation: LineupFormation;
  starter_player_ids: string[];
  bench_player_ids: string[];
};

function optionalNumber(value: unknown): number | null | undefined {
  if (value === null) return null;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return undefined;
}

export function normalizeLineupSquad(payload: unknown): LineupPlayer[] {
  const root = payload && typeof payload === "object" ? (payload as any) : {};
  const items = Array.isArray(root.items) ? root.items : [];
  return items
    .map((raw: any) => {
      const playerId = raw?.player_id ?? raw?.playerId ?? raw?.id;
      if (playerId === undefined || playerId === null || String(playerId).trim() === "") return null;
      const rating = optionalNumber(raw.rating ?? raw.overall ?? raw.overall_rating ?? raw.current_rating);
      const position = raw.position ?? raw.normalized_position;
      const portrait = raw.portrait_url ?? raw.portraitUrl ?? raw.image_url ?? raw.avatar_url;
      return {
        player_id: String(playerId),
        player_name: String(raw.player_name ?? raw.playerName ?? raw.name ?? "Player"),
        ...(position ? { position: String(position) } : {}),
        ...(rating !== undefined ? { rating } : {}),
        ...(portrait ? { portrait_url: String(portrait) } : {}),
      } as LineupPlayer;
    })
    .filter((player: LineupPlayer | null): player is LineupPlayer => player !== null);
}

export function normalizeLineupPlan(payload: unknown): LineupPlan {
  const root = payload && typeof payload === "object" ? (payload as any) : {};
  const candidate = String(root.formation ?? "4-3-3");
  const formation = (LINEUP_FORMATIONS as readonly string[]).includes(candidate)
    ? (candidate as LineupFormation)
    : "4-3-3";
  const normalizeIds = (value: unknown) =>
    Array.isArray(value)
      ? value.map((id) => String(id ?? "").trim()).filter(Boolean)
      : [];
  return {
    ...(root.club_id ? { club_id: String(root.club_id) } : {}),
    formation,
    starter_player_ids: normalizeIds(root.starter_player_ids),
    bench_player_ids: normalizeIds(root.bench_player_ids),
  };
}

export function lineupRoleLabels(formation: string): string[] {
  const valid = (LINEUP_FORMATIONS as readonly string[]).includes(formation)
    ? formation
    : "4-3-3";
  const lines = valid.split("-").map((part) => Number(part));
  const labels = ["Goalkeeper"];
  lines.forEach((count, lineIndex) => {
    const role = lineIndex === 0 ? "Defender" : lineIndex === lines.length - 1 ? "Forward" : "Midfielder";
    for (let i = 1; i <= count; i += 1) labels.push(role + " " + i);
  });
  return labels.slice(0, 11);
}

export function lineupFormationRows(formation: string): number[][] {
  const valid = (LINEUP_FORMATIONS as readonly string[]).includes(formation)
    ? formation
    : "4-3-3";
  const rows = [[0]];
  let nextIndex = 1;
  valid.split("-").forEach((part) => {
    const count = Number(part);
    const row = Array.from({ length: count }, (_, offset) => nextIndex + offset);
    rows.push(row);
    nextIndex += count;
  });
  return rows;
}

export function buildLineupPayload(
  formation: string,
  starters: string[],
  bench: string[],
  knownPlayerIds?: string[],
) {
  const seenStarters = new Set<string>();
  const starterPlayerIds = starters.filter((id) => {
    if (!id || seenStarters.has(id)) return false;
    seenStarters.add(id);
    return true;
  });
  const validIds = knownPlayerIds ? new Set(knownPlayerIds) : null;
  const seenBench = new Set<string>();
  const benchPlayerIds = bench.filter((id) => {
    if (!id || seenStarters.has(id) || seenBench.has(id) || (validIds && !validIds.has(id))) return false;
    seenBench.add(id);
    return true;
  });
  return {
    formation: (LINEUP_FORMATIONS as readonly string[]).includes(formation) ? formation : "4-3-3",
    starter_player_ids: starterPlayerIds.slice(0, 11),
    bench_player_ids: benchPlayerIds,
  };
}
