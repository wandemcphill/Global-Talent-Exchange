import type { RigAction } from "./playerRig";

export type PitchSide = "home" | "away";

export type PitchPlayer = {
  playerId: string;
  side: PitchSide;
  x: number;
  y: number;
  shirtNumber: number;
  name: string;
  role?: string;
  animationState?: string;
  hasBall?: boolean;
  isGoalkeeper?: boolean;
  staminaPct?: number | null;
  velocity?: { x: number; y: number } | null;
  facing?: { x: number; y: number } | null;
};

export type PitchBall = { x: number; y: number };

export type PitchFrame = {
  timeSeconds: number;
  clockMinute?: number;
  phase?: string | null;
  homeScore?: number;
  awayScore?: number;
  players: PitchPlayer[];
  ball: PitchBall | null;
  eventType?: string | null;
  snapshotVersion?: number | null;
  frameId?: string | null;
  ballTrajectory?: PitchBall[] | null;
};

export type SnapshotCursor = { snapshotVersion: number; timeSeconds?: number };

export type LiveSample = PitchFrame & {
  snapshotVersion?: number | null;
  frameId?: string | null;
  sequence?: number | null;
  source?: "snapshot" | "stream";
};
export type LivePitchSample = LiveSample;

export type FeedPresentationStatus =
  | "LIVE"
  | "DELAYED"
  | "RECONNECTING"
  | "FEED UNAVAILABLE"
  | "FINAL";
export type FeedFreshnessStatus = FeedPresentationStatus;

export type FeedFreshnessState = {
  status: FeedPresentationStatus;
  label: string;
  ageMs: number | null;
  ageSeconds: number | null;
  isStale: boolean;
};

export function playerIdentityKey(player: { side: PitchSide; playerId: string }): string {
  return `${player.side}:${player.playerId}`;
}

function clampUnit(value: number, fallback = 0.5): number {
  if (!Number.isFinite(value)) return fallback;
  return Math.min(1, Math.max(0, value));
}

export function sanitizePitchPlayer(raw: PitchPlayer | null | undefined): PitchPlayer | null {
  if (!raw || typeof raw !== "object") return null;
  const playerId = String(raw.playerId ?? "").trim();
  if (!playerId) return null;
  const side: PitchSide = raw.side === "away" ? "away" : "home";
  if (!Number.isFinite(raw.x) || !Number.isFinite(raw.y)) return null;
  return {
    ...raw,
    playerId,
    side,
    x: clampUnit(raw.x),
    y: clampUnit(raw.y),
    shirtNumber: Number.isFinite(Number(raw.shirtNumber)) ? Math.max(0, Math.floor(Number(raw.shirtNumber))) : 0,
    name: String(raw.name ?? ""),
  };
}

export function isValidLiveSample(sample: LiveSample | null | undefined): sample is LiveSample {
  if (!sample || typeof sample !== "object") return false;
  if (!Number.isFinite(sample.timeSeconds) || sample.timeSeconds < 0) return false;
  if (!Array.isArray(sample.players) || sample.players.length === 0) return false;
  const validPlayers = sample.players.map(sanitizePitchPlayer).filter((p): p is PitchPlayer => p !== null);
  return validPlayers.length > 0;
}

function normalizeSample(sample: LiveSample): LiveSample {
  const deduped = new Map<string, PitchPlayer>();
  for (const rawPlayer of sample.players) {
    const clean = sanitizePitchPlayer(rawPlayer);
    if (!clean) continue;
    deduped.set(playerIdentityKey(clean), clean);
  }
  const ball =
    sample.ball && Number.isFinite(sample.ball.x) && Number.isFinite(sample.ball.y)
      ? { x: clampUnit(sample.ball.x), y: clampUnit(sample.ball.y) }
      : null;
  const ballTrajectory = Array.isArray(sample.ballTrajectory)
    ? sample.ballTrajectory
        .filter((pt) => pt && Number.isFinite(pt.x) && Number.isFinite(pt.y))
        .map((pt) => ({ x: clampUnit(pt.x), y: clampUnit(pt.y) }))
    : null;
  return {
    ...sample,
    players: Array.from(deduped.values()),
    ball,
    ballTrajectory: ballTrajectory && ballTrajectory.length > 0 ? ballTrajectory : null,
  };
}

function samplesAreIdentical(a: LiveSample, b: LiveSample): boolean {
  if (a.timeSeconds !== b.timeSeconds) return false;
  if ((a.eventType || null) !== (b.eventType || null)) return false;
  if (a.players.length !== b.players.length) return false;
  for (let i = 0; i < a.players.length; i += 1) {
    const pa = a.players[i];
    const pb = b.players[i];
    if (
      pa.side !== pb.side ||
      pa.playerId !== pb.playerId ||
      Math.abs(pa.x - pb.x) > 1e-5 ||
      Math.abs(pa.y - pb.y) > 1e-5 ||
      pa.shirtNumber !== pb.shirtNumber ||
      Boolean(pa.hasBall) !== Boolean(pb.hasBall)
    ) {
      return false;
    }
  }
  if (Boolean(a.ball) !== Boolean(b.ball)) return false;
  if (a.ball && b.ball && (Math.abs(a.ball.x - b.ball.x) > 1e-5 || Math.abs(a.ball.y - b.ball.y) > 1e-5)) {
    return false;
  }
  return true;
}

/**
 * Previous/next authoritative samples for a monotonic render clock separate from match time.
 * Preserves distinct ordering domains (`snapshotVersion` for backend HTTP snapshots vs
 * `frameId`/`sequence` for live WebSocket frames) and enforces monotonic forward playback.
 */
export class LiveRenderBuffer {
  previous: LiveSample | null = null;
  next: LiveSample | null = null;

  private lastSnapshotVersion: number | null = null;
  private lastStreamSequence: number | null = null;
  private seenFrameIds = new Set<string>();
  private cursorTimeSeconds = 0;
  private lastWallClockMs: number | null = null;
  private lastPushWallMs: number | null = null;
  private estimatedSpanSeconds = 1.0;
  private readonly jitterDelayFactor = 0.92;
  private lastValidReceivedAtMs: number | null = null;

  push(sample: LiveSample, nowMs?: number): boolean {
    if (!isValidLiveSample(sample)) return false;
    const normalized = normalizeSample(sample);

    const hasSnapshotVersion =
      typeof normalized.snapshotVersion === "number" && Number.isFinite(normalized.snapshotVersion);
    const hasFrameId = typeof normalized.frameId === "string" && normalized.frameId.trim().length > 0;
    const hasSequence = typeof normalized.sequence === "number" && Number.isFinite(normalized.sequence);

    // 1. Snapshot version domain check (only compare when both have authoritative snapshotVersion)
    if (hasSnapshotVersion && this.lastSnapshotVersion !== null) {
      if ((normalized.snapshotVersion as number) < this.lastSnapshotVersion) {
        return false;
      }
    }

    // 2. Stream sequence domain check (only compare when both have stream sequence)
    if (hasSequence && this.lastStreamSequence !== null) {
      if ((normalized.sequence as number) < this.lastStreamSequence) {
        return false;
      }
    }

    // 3. Duplicate frameId rejection
    if (hasFrameId) {
      const frameKey = `${normalized.frameId}:${hasSnapshotVersion ? normalized.snapshotVersion : "stream"}`;
      if (this.seenFrameIds.has(frameKey)) {
        return false;
      }
    }

    // 4. Monotonic match timestamp check: never allow an out-of-order or post-snapshot older frame to rewind
    if (this.next) {
      if (normalized.timeSeconds < this.next.timeSeconds - 1e-6) {
        return false;
      }

      if (Math.abs(normalized.timeSeconds - this.next.timeSeconds) <= 1e-6) {
        // Identical timestamp: reject if exact duplicate, otherwise update in-place for same-timestamp events/substitutions
        if (
          hasSnapshotVersion &&
          this.next.snapshotVersion != null &&
          normalized.snapshotVersion === this.next.snapshotVersion &&
          samplesAreIdentical(this.next, normalized)
        ) {
          return false;
        }
        if (!hasSnapshotVersion && samplesAreIdentical(this.next, normalized)) {
          return false;
        }
        if (hasSnapshotVersion) {
          this.lastSnapshotVersion = normalized.snapshotVersion as number;
        }
        if (hasSequence) {
          this.lastStreamSequence = normalized.sequence as number;
        }
        if (hasFrameId) {
          this.recordFrameId(`${normalized.frameId}:${hasSnapshotVersion ? normalized.snapshotVersion : "stream"}`);
        }
        if (nowMs !== undefined && Number.isFinite(nowMs)) {
          this.lastValidReceivedAtMs = nowMs;
        }
        if (!this.previous || this.previous === this.next || Math.abs(this.previous.timeSeconds - normalized.timeSeconds) <= 1e-6) {
          this.previous = normalized;
        }
        this.next = normalized;
        this.cursorTimeSeconds = Math.max(this.cursorTimeSeconds, normalized.timeSeconds);
        return true;
      }
    }

    // Record ordering watermarks
    if (hasSnapshotVersion) {
      this.lastSnapshotVersion = normalized.snapshotVersion as number;
    }
    if (hasSequence) {
      this.lastStreamSequence = normalized.sequence as number;
    }
    if (hasFrameId) {
      this.recordFrameId(`${normalized.frameId}:${hasSnapshotVersion ? normalized.snapshotVersion : "stream"}`);
    }

    if (nowMs !== undefined && Number.isFinite(nowMs)) {
      this.lastValidReceivedAtMs = nowMs;
      if (this.lastPushWallMs !== null) {
        const arrivalDeltaSec = Math.max(0.05, Math.min(10, (nowMs - this.lastPushWallMs) / 1000));
        this.estimatedSpanSeconds = this.estimatedSpanSeconds * 0.4 + arrivalDeltaSec * 0.6;
      }
      this.lastPushWallMs = nowMs;
    }

    if (!this.next) {
      this.previous = normalized;
      this.next = normalized;
      this.cursorTimeSeconds = normalized.timeSeconds;
      if (nowMs !== undefined && Number.isFinite(nowMs)) {
        this.lastWallClockMs = nowMs;
      }
      return true;
    }

    // Anchor `previous` at the current rendered position if wall-clock interpolation is active,
    // so early/late network arrival transitions smoothly without jumping or rewinding.
    if (nowMs !== undefined && this.lastWallClockMs !== null && this.cursorTimeSeconds > this.previous!.timeSeconds) {
      const currentSampled = this.sampleAt(this.cursorTimeSeconds);
      this.previous = currentSampled.frame || this.next;
    } else {
      this.previous = this.next;
    }
    this.next = normalized;
    if (this.cursorTimeSeconds < this.previous.timeSeconds) {
      this.cursorTimeSeconds = this.previous.timeSeconds;
    }
    return true;
  }

  /** Replace both ends after reconnect or explicit seek; do not treat history as new incidents. */
  replace(sample: LiveSample, nowMs?: number): boolean {
    if (!isValidLiveSample(sample)) return false;
    const normalized = normalizeSample(sample);
    this.previous = normalized;
    this.next = normalized;
    this.cursorTimeSeconds = normalized.timeSeconds;
    this.seenFrameIds.clear();
    if (typeof normalized.snapshotVersion === "number" && Number.isFinite(normalized.snapshotVersion)) {
      this.lastSnapshotVersion = normalized.snapshotVersion;
    }
    if (typeof normalized.sequence === "number" && Number.isFinite(normalized.sequence)) {
      this.lastStreamSequence = normalized.sequence;
    }
    if (typeof normalized.frameId === "string" && normalized.frameId.trim().length > 0) {
      this.recordFrameId(`${normalized.frameId}:${this.lastSnapshotVersion ?? "stream"}`);
    }
    if (nowMs !== undefined && Number.isFinite(nowMs)) {
      this.lastWallClockMs = nowMs;
      this.lastPushWallMs = nowMs;
      this.lastValidReceivedAtMs = nowMs;
    }
    return true;
  }

  sampleAt(renderTime: number): { frame: LiveSample | null; trajectoryAlpha: number } {
    if (!this.next) return { frame: null, trajectoryAlpha: 1 };
    if (!this.previous || this.previous === this.next) {
      this.cursorTimeSeconds = Math.max(this.cursorTimeSeconds, this.next.timeSeconds);
      return { frame: this.next, trajectoryAlpha: 1 };
    }
    const span = this.next.timeSeconds - this.previous.timeSeconds;
    if (span <= 0.001) {
      this.cursorTimeSeconds = Math.max(this.cursorTimeSeconds, this.next.timeSeconds);
      return { frame: this.next, trajectoryAlpha: 1 };
    }
    const safeTime = Number.isFinite(renderTime) ? renderTime : this.cursorTimeSeconds;
    const clampedTime = Math.min(this.next.timeSeconds, Math.max(this.previous.timeSeconds, safeTime));
    const alpha = Math.min(1, Math.max(0, (clampedTime - this.previous.timeSeconds) / span));
    const blended = interpolate(this.previous, this.next, alpha);
    return {
      frame: {
        ...blended,
        snapshotVersion: this.next.snapshotVersion ?? this.previous.snapshotVersion ?? 0,
        frameId: this.next.frameId ?? this.previous.frameId ?? null,
        ballTrajectory: this.next.ballTrajectory || this.previous.ballTrajectory || null,
      },
      trajectoryAlpha: alpha,
    };
  }

  /**
   * Advances presentation interpolation monotonically using a wall-clock timestamp (`performance.now()`).
   * Accommodates network jitter, handles variable frame intervals, respects pause/resume and speed multipliers,
   * and never advances past the latest authoritative `next.timeSeconds` or rewinds.
   */
  advanceWallClock(
    nowMs: number,
    options?: { paused?: boolean; speed?: number },
  ): { frame: LiveSample | null; trajectoryAlpha: number; cursorTimeSeconds: number; renderTimeSeconds: number } {
    if (!this.next) {
      this.lastWallClockMs = nowMs;
      return { frame: null, trajectoryAlpha: 1, cursorTimeSeconds: 0, renderTimeSeconds: 0 };
    }

    const paused = Boolean(options?.paused);
    const speed = Number.isFinite(options?.speed) && (options?.speed as number) > 0 ? (options?.speed as number) : 1;

    if (this.lastWallClockMs === null || !Number.isFinite(this.lastWallClockMs)) {
      this.lastWallClockMs = nowMs;
    }

    const dtSec = Math.max(0, Math.min(0.5, (nowMs - this.lastWallClockMs) / 1000));
    this.lastWallClockMs = nowMs;

    if (!paused && this.previous && this.next !== this.previous) {
      const matchSpan = Math.max(0.001, this.next.timeSeconds - this.previous.timeSeconds);
      const networkSpan = Math.max(0.15, Math.min(matchSpan * 1.25, this.estimatedSpanSeconds));
      const rate = (matchSpan / Math.max(0.15, networkSpan / this.jitterDelayFactor)) * speed;
      this.cursorTimeSeconds = Math.min(
        this.next.timeSeconds,
        Math.max(this.cursorTimeSeconds, this.previous.timeSeconds) + dtSec * rate,
      );
    } else if (!paused && (!this.previous || this.previous === this.next)) {
      this.cursorTimeSeconds = Math.max(this.cursorTimeSeconds, this.next.timeSeconds);
    }

    const sampled = this.sampleAt(this.cursorTimeSeconds);
    return {
      ...sampled,
      cursorTimeSeconds: this.cursorTimeSeconds,
      renderTimeSeconds: this.cursorTimeSeconds,
    };
  }

  get lastReceivedAtMs(): number | null {
    return this.lastValidReceivedAtMs;
  }

  clear(): void {
    this.previous = null;
    this.next = null;
    this.lastSnapshotVersion = null;
    this.lastStreamSequence = null;
    this.seenFrameIds.clear();
    this.cursorTimeSeconds = 0;
    this.lastWallClockMs = null;
    this.lastPushWallMs = null;
    this.estimatedSpanSeconds = 1.0;
    this.lastValidReceivedAtMs = null;
  }

  getCursorTimeSeconds(): number {
    return this.cursorTimeSeconds;
  }

  getLastValidReceivedAtMs(): number | null {
    return this.lastValidReceivedAtMs;
  }

  private recordFrameId(key: string): void {
    this.seenFrameIds.add(key);
    if (this.seenFrameIds.size > 256) {
      const iter = this.seenFrameIds.values();
      for (let i = 0; i < 64; i += 1) {
        const next = iter.next();
        if (next.done) break;
        this.seenFrameIds.delete(next.value);
      }
    }
  }
}

export type PlayerAction = RigAction;

export function seekTime<T extends { timeSeconds: number }>(frames: T[], timeSeconds: number) {
  if (!Array.isArray(frames) || !frames.length) {
    return { left: null, right: null, t: 0 };
  }
  const validFrames = frames.filter((frame) => frame && Number.isFinite(frame.timeSeconds));
  if (!validFrames.length) {
    return { left: null, right: null, t: 0 };
  }
  const firstTime = validFrames[0].timeSeconds;
  const lastTime = validFrames[validFrames.length - 1].timeSeconds;
  const rawTime = Number.isFinite(timeSeconds) ? timeSeconds : firstTime;
  const time = Math.min(lastTime, Math.max(firstTime, rawTime));

  let index = 0;
  while (index < validFrames.length - 1 && validFrames[index + 1].timeSeconds <= time) index += 1;
  const left = validFrames[index];
  const right = validFrames[Math.min(index + 1, validFrames.length - 1)];
  if (left.timeSeconds === time || right === left || time >= right.timeSeconds) {
    return { left, right: left, t: 1 };
  }
  const span = right.timeSeconds - left.timeSeconds;
  const t = span <= 0.001 ? 1 : Math.min(1, Math.max(0, (time - left.timeSeconds) / span));
  return { left, right, t };
}

/**
 * Steps a recorded replay cursor forward monotonically, respecting pause/resume,
 * playback speed changes, and clamping at the authoritative end-of-replay timestamp.
 */
export function stepReplayClock(input: {
  currentTimeSeconds: number;
  deltaMs: number;
  durationSeconds: number;
  paused?: boolean;
  speed?: number;
}): number {
  const maxDuration =
    Number.isFinite(input.durationSeconds) && input.durationSeconds > 0
      ? input.durationSeconds
      : Number.POSITIVE_INFINITY;
  const current = Math.min(
    maxDuration,
    Math.max(0, Number.isFinite(input.currentTimeSeconds) ? input.currentTimeSeconds : 0),
  );
  if (input.paused) {
    return current;
  }
  const speed = Number.isFinite(input.speed) && (input.speed as number) > 0 ? (input.speed as number) : 1;
  const deltaSeconds = Math.max(0, Number.isFinite(input.deltaMs) ? input.deltaMs / 1000 : 0);
  return Math.min(maxDuration, current + deltaSeconds * speed);
}

export function acceptSnapshot<T extends SnapshotCursor>(previous: T | null, next: T | null): T | null {
  if (!next || typeof next !== "object") return previous;
  if (!Number.isFinite(next.snapshotVersion)) return previous;
  if (previous && next.snapshotVersion < previous.snapshotVersion) return previous;
  if (
    previous &&
    next.snapshotVersion === previous.snapshotVersion &&
    typeof previous.timeSeconds === "number" &&
    typeof next.timeSeconds === "number" &&
    next.timeSeconds < previous.timeSeconds
  ) {
    return previous;
  }
  return next;
}

/**
 * Interpolates between two PitchFrames using composite `side:playerId` identity.
 * - Players present in both frames interpolate smoothly.
 * - Outgoing players remain at their outgoing position prior to the substitution boundary and disappear at the boundary.
 * - Incoming substitutes appear at the substitution boundary at their own authoritative coordinates without inheriting
 *   any outgoing player's position, shirt number, or animation state.
 * - At the destination frame (`alpha >= 1`), the roster matches `to.players` in exact membership and order.
 */
export function interpolate(from: PitchFrame, to: PitchFrame, alpha: number): PitchFrame {
  const t = Math.min(1, Math.max(0, Number.isFinite(alpha) ? alpha : 1));
  const fromPlayers = Array.isArray(from?.players) ? from.players.map(sanitizePitchPlayer).filter((p): p is PitchPlayer => p !== null) : [];
  const toPlayers = Array.isArray(to?.players) ? to.players.map(sanitizePitchPlayer).filter((p): p is PitchPlayer => p !== null) : [];

  const fromByKey = new Map<string, PitchPlayer>();
  for (const player of fromPlayers) {
    fromByKey.set(playerIdentityKey(player), player);
  }
  const toByKey = new Map<string, PitchPlayer>();
  for (const player of toPlayers) {
    toByKey.set(playerIdentityKey(player), player);
  }

  const atSubstitutionBoundary = t >= 0.5 || fromPlayers.length === 0;
  const players: PitchPlayer[] = [];

  if (!atSubstitutionBoundary) {
    // Before boundary: preserve `from` roster order; interpolate continuing players, keep outgoing players at `from`.
    for (const fromPlayer of fromPlayers) {
      const key = playerIdentityKey(fromPlayer);
      const target = toByKey.get(key);
      if (!target) {
        players.push({ ...fromPlayer });
      } else {
        players.push({
          ...fromPlayer,
          x: fromPlayer.x + (target.x - fromPlayer.x) * t,
          y: fromPlayer.y + (target.y - fromPlayer.y) * t,
          hasBall: Boolean(fromPlayer.hasBall),
          animationState: fromPlayer.animationState || target.animationState,
        });
      }
    }
  } else {
    // At and after boundary: follow authoritative `to` roster order; interpolate continuing players,
    // introduce incoming substitutes at their `to` position, and omit outgoing players.
    const sourceList = toPlayers.length > 0 ? toPlayers : fromPlayers;
    for (const toPlayer of sourceList) {
      const key = playerIdentityKey(toPlayer);
      const origin = fromByKey.get(key);
      if (!origin) {
        players.push({ ...toPlayer });
      } else {
        players.push({
          ...toPlayer,
          x: origin.x + (toPlayer.x - origin.x) * t,
          y: origin.y + (toPlayer.y - origin.y) * t,
        });
      }
    }
  }

  const fromBall =
    from?.ball && Number.isFinite(from.ball.x) && Number.isFinite(from.ball.y)
      ? { x: clampUnit(from.ball.x), y: clampUnit(from.ball.y) }
      : null;
  const toBall =
    to?.ball && Number.isFinite(to.ball.x) && Number.isFinite(to.ball.y)
      ? { x: clampUnit(to.ball.x), y: clampUnit(to.ball.y) }
      : null;

  const ball =
    fromBall && toBall
      ? {
          x: fromBall.x + (toBall.x - fromBall.x) * t,
          y: fromBall.y + (toBall.y - fromBall.y) * t,
        }
      : toBall || fromBall;

  const fromTime = Number.isFinite(from?.timeSeconds) ? from.timeSeconds : 0;
  const toTime = Number.isFinite(to?.timeSeconds) ? to.timeSeconds : fromTime;
  const fromMinute = Number.isFinite(from?.clockMinute) ? (from.clockMinute as number) : undefined;
  const toMinute = Number.isFinite(to?.clockMinute) ? (to.clockMinute as number) : fromMinute;
  const clockMinute =
    fromMinute !== undefined && toMinute !== undefined
      ? Math.round(fromMinute + (toMinute - fromMinute) * t)
      : toMinute ?? fromMinute;

  return {
    timeSeconds: fromTime + (toTime - fromTime) * t,
    clockMinute,
    phase: t < 0.5 ? from?.phase ?? to?.phase : to?.phase ?? from?.phase,
    homeScore: t < 0.5 ? from?.homeScore ?? to?.homeScore : to?.homeScore ?? from?.homeScore,
    awayScore: t < 0.5 ? from?.awayScore ?? to?.awayScore : to?.awayScore ?? from?.awayScore,
    players,
    ball,
    eventType: t < 0.5 ? from?.eventType : to?.eventType,
    ballTrajectory: t < 0.5 ? from?.ballTrajectory || to?.ballTrajectory || null : to?.ballTrajectory || from?.ballTrajectory || null,
  };
}

export function animationFor(
  player: { animationState?: string; hasBall?: boolean; role?: string },
  eventType?: string | null,
): PlayerAction {
  const event = String(eventType || "").toLowerCase();
  const state = String(player.animationState || "").toLowerCase();
  const keeper =
    String(player.role || "").toLowerCase().includes("gk") || String(player.role || "").toLowerCase().includes("goal");
  if (event === "goal" && player.hasBall) return "celebrate";
  if ((event === "save" || event === "shot") && keeper) return event === "save" ? "save" : "dive";
  if (event === "goal" || event === "shot" || event === "miss") return keeper ? "dive" : "shoot";
  if (event === "pass" || event === "attack") return player.hasBall ? "pass" : "jog";
  if (event === "foul" || event === "tackle") return "tackle";
  if (event === "substitution") return "idle";
  if (state.includes("header")) return "header";
  if (state.includes("sprint")) return "sprint";
  if (state.includes("walk")) return "walk";
  if (state.includes("dribble")) return "dribble";
  if (state.includes("jump")) return "jump";
  if (state.includes("turn")) return "turn";
  if (state.includes("accel")) return "accelerate";
  if (state.includes("run") || state.includes("jog")) return "jog";
  if (state.includes("shoot")) return "shoot";
  if (state.includes("pass")) return "pass";
  if (state.includes("press") || state.includes("tackle")) return "tackle";
  if (state.includes("save")) return "save";
  if (state.includes("celebrat")) return "celebrate";
  if (state.includes("dive")) return "dive";
  if (player.hasBall) return "dribble";
  return "idle";
}

export function metricText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

export function suppliedCrest(url: unknown): string | null {
  if (typeof url !== "string") return null;
  const trimmed = url.trim();
  return trimmed ? trimmed : null;
}

export function effectFor(eventType?: string | null): string | null {
  const event = String(eventType || "").toLowerCase();
  if (event === "goal") return "goal";
  if (event === "shot" || event === "miss") return "shot";
  if (event === "pass" || event === "attack") return "pass";
  if (event === "save") return "save";
  if (event === "yellow_card" || event === "red_card") return "card";
  if (event === "substitution") return "substitution";
  return null;
}

export function pitchSource(input: {
  matchId?: string;
  hasSnapshot: boolean;
  hasFrames: boolean;
}): "live" | "demo" | "unavailable" {
  if (input.matchId === "u2a-006-showcase") return "demo";
  if (input.hasSnapshot || input.hasFrames) return "live";
  return "unavailable";
}

export function resolveFeedPresentationStatus(input: {
  matchId?: string;
  demo?: boolean;
  unavailable?: boolean;
  phase?: string | null;
  connectionStatus?: string | null;
  hasValidFrame?: boolean;
  hasRenderableFrame?: boolean;
  lastFrameReceivedAtMs?: number | null;
  nowMs?: number;
  isRecordedReplay?: boolean;
  staleThresholdMs?: number;
}): FeedFreshnessState {
  const phase = String(input.phase || "").trim().toLowerCase();
  const isCompleted = phase === "completed" || phase === "full_time" || phase === "fulltime";
  const now = input.nowMs ?? (typeof performance !== "undefined" ? performance.now() : Date.now());
  const staleThreshold = input.staleThresholdMs ?? 6000;
  const ageMs =
    input.lastFrameReceivedAtMs != null && Number.isFinite(input.lastFrameReceivedAtMs)
      ? Math.max(0, now - input.lastFrameReceivedAtMs)
      : null;
  const ageSeconds = ageMs !== null ? Math.floor(ageMs / 1000) : null;

  if (isCompleted) {
    return {
      status: "FINAL",
      label: "FINAL",
      ageMs,
      ageSeconds,
      isStale: false,
    };
  }

  const isDemo = Boolean(input.demo) || input.matchId === "u2a-006-showcase";
  const conn = String(input.connectionStatus || "").trim().toLowerCase();
  const hasFrame =
    !input.unavailable &&
    (input.hasValidFrame ?? input.hasRenderableFrame ?? true) !== false;

  if (!hasFrame && !isDemo) {
    if (conn === "reconnecting") {
      return {
        status: "RECONNECTING",
        label: "RECONNECTING",
        ageMs,
        ageSeconds,
        isStale: true,
      };
    }
    return {
      status: "FEED UNAVAILABLE",
      label: "FEED UNAVAILABLE",
      ageMs: null,
      ageSeconds: null,
      isStale: true,
    };
  }

  if (
    conn === "reconnecting" ||
    (!isDemo && !input.isRecordedReplay && (conn === "error" || conn === "closed"))
  ) {
    return {
      status: "RECONNECTING",
      label: ageSeconds !== null && ageSeconds > 0 ? `RECONNECTING · ${ageSeconds}s` : "RECONNECTING",
      ageMs,
      ageSeconds,
      isStale: true,
    };
  }

  if (!isDemo && !input.isRecordedReplay && ageMs !== null && ageMs >= staleThreshold) {
    return {
      status: "DELAYED",
      label: `DELAYED · ${ageSeconds}s`,
      ageMs,
      ageSeconds,
      isStale: true,
    };
  }

  return {
    status: "LIVE",
    label: "LIVE",
    ageMs,
    ageSeconds,
    isStale: false,
  };
}

export function sceneObjectCount(playerCount: number, effect: boolean): number {
  return 1 + playerCount + 1 + (effect ? 1 : 0);
}
