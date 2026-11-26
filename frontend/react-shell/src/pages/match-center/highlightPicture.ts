export type HighlightSample = {
  timeSeconds: number;
  players: Array<Record<string, unknown>>;
  ball?: unknown;
};

const SAMPLE_SPAN_SECONDS = 12;
const REEL_SPAN_SECONDS = 8;

function playerPoint(player: Record<string, unknown> | undefined): string {
  const nested = player?.position as { x?: unknown; y?: unknown } | undefined;
  const x = player?.x ?? nested?.x ?? "";
  const y = player?.y ?? nested?.y ?? "";
  return `${x},${y}`;
}

export function sampleKey(sample: { players: Array<Record<string, unknown>>; ball?: unknown }): string {
  const ball = (sample.ball || {}) as { x?: unknown; y?: unknown; position?: { x?: unknown; y?: unknown } };
  const bx = ball.x ?? ball.position?.x ?? "";
  const by = ball.y ?? ball.position?.y ?? "";
  return `${sample.players.length}|${playerPoint(sample.players[0])}|${bx},${by}`;
}

function cloneSample(sample: HighlightSample): HighlightSample {
  return {
    timeSeconds: sample.timeSeconds,
    players: sample.players.map((player) => ({
      ...player,
      position: player.position && typeof player.position === "object" ? { ...(player.position as object) } : player.position,
    })),
    ball: sample.ball && typeof sample.ball === "object" ? { ...(sample.ball as object) } : sample.ball,
  };
}

/** Keep the last 12 seconds of distinct pitch pictures. A stalled match clock still steps forward. */
export function rememberPitchSample(
  buffer: readonly HighlightSample[],
  input: { matchSeconds: number | null; players: Array<Record<string, unknown>>; ball?: unknown },
): HighlightSample[] {
  if (!input.players?.length) return buffer.slice();
  const last = buffer[buffer.length - 1];
  if (last && sampleKey(last) === sampleKey({ players: input.players, ball: input.ball })) {
    return buffer.slice();
  }
  const matchSeconds = input.matchSeconds;
  let timeSeconds: number;
  if (!last) {
    timeSeconds = matchSeconds != null && Number.isFinite(matchSeconds) ? matchSeconds : 0;
  } else if (matchSeconds != null && Number.isFinite(matchSeconds) && matchSeconds + 1 < last.timeSeconds) {
    timeSeconds = matchSeconds;
  } else if (matchSeconds != null && Number.isFinite(matchSeconds) && matchSeconds > last.timeSeconds + 0.15) {
    timeSeconds = matchSeconds;
  } else {
    timeSeconds = last.timeSeconds + 0.45;
  }
  const stored = cloneSample({ timeSeconds, players: input.players, ball: input.ball });
  if (last && stored.timeSeconds < last.timeSeconds - 0.5) return [stored];
  return [...buffer, stored].filter((row) => stored.timeSeconds - row.timeSeconds <= SAMPLE_SPAN_SECONDS);
}

/** The pictures that led into the chance, at most the last eight seconds. */
export function highlightReel(buffer: readonly HighlightSample[]): HighlightSample[] {
  if (buffer.length <= 1) return buffer.slice();
  const end = buffer[buffer.length - 1].timeSeconds;
  const start = end - REEL_SPAN_SECONDS;
  const window = buffer.filter((row) => row.timeSeconds >= start - 0.01);
  return window.length ? window : [buffer[buffer.length - 1]];
}

/** The attack sequence returned with a live chance, in the order it was played. */
export function serverHighlightSamples(frames: unknown): HighlightSample[] {
  if (!Array.isArray(frames)) return [];
  const samples: HighlightSample[] = [];
  for (const row of frames) {
    if (!row || typeof row !== "object") continue;
    const record = row as { time_seconds?: unknown; players?: unknown; ball?: unknown };
    const players = Array.isArray(record.players) ? (record.players as Array<Record<string, unknown>>) : [];
    const timeSeconds = Number(record.time_seconds);
    if (!players.length || !Number.isFinite(timeSeconds)) continue;
    samples.push({ timeSeconds, players, ball: record.ball });
  }
  return samples;
}

/**
 * What should bring the pitch on. A chance the match is still holding wins,
 * even after the live frame has moved on to ordinary play.
 */
export function highlightPictureKey(input: {
  serverEventId?: unknown;
  serverFrameCount?: number;
  liveActionType?: unknown;
  latestIsHighlight?: boolean;
  latestEventId?: unknown;
}): string {
  const serverId = String(input.serverEventId || "").trim();
  if (Number(input.serverFrameCount || 0) >= 2 && serverId) return `served:${serverId}`;
  if (isMatchHighlight(input.liveActionType) || input.latestIsHighlight) {
    return `live:${String(input.latestEventId || input.liveActionType || "chance")}`;
  }
  return "";
}

/** How long the saved move stays on screen, in seconds. */
export function highlightPlaySeconds(reel: readonly HighlightSample[]): number {
  if (reel.length < 2) return 5;
  const span = reel[reel.length - 1].timeSeconds - reel[0].timeSeconds;
  return Math.min(8, Math.max(4, span));
}

export function isMatchHighlight(type: unknown): boolean {
  const value = String(type || "")
    .toLowerCase()
    .replace(/[\s-]+/g, "_");
  if (
    !value ||
    value === "pass" ||
    value === "open_play" ||
    value === "neutral" ||
    value === "kickoff" ||
    value === "substitution" ||
    value === "tactical_change"
  ) {
    return false;
  }
  return (
    value.includes("goal") ||
    value.includes("shot") ||
    value.includes("save") ||
    value.includes("miss") ||
    value.includes("chance") ||
    value.includes("foul") ||
    value.includes("card") ||
    value.includes("penalt") ||
    value.includes("var") ||
    value.includes("offside") ||
    value.includes("injur")
  );
}
