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
  line?: string;
  state?: string;
  animationState?: string;
  hasBall?: boolean;
  isGoalkeeper?: boolean;
  highlighted?: boolean;
  speedRatio?: number | null;
  staminaPct?: number | null;
  anchorX?: number | null;
  anchorY?: number | null;
  velocity?: { x: number; y: number } | null;
  facing?: { x: number; y: number } | null;
};

export type PitchBall = {
  x: number;
  y: number;
  height?: number | null;
  state?: string | null;
  ownerPlayerId?: string | null;
  velocity?: { x: number; y: number; z?: number } | null;
};

export type PitchFrame = {
  timeSeconds: number;
  clockMinute?: number;
  phase?: string | null;
  stage?: string | null;
  cameraPreset?: string | null;
  homeScore?: number;
  awayScore?: number;
  homeAttacksRight?: boolean;
  possessionSide?: PitchSide | null;
  possessionPhase?: string | null;
  transitionState?: string | null;
  dangerZone?: string | null;
  pressureIndex?: number | null;
  compactnessHome?: number | null;
  compactnessAway?: number | null;
  eventBanner?: string | null;
  activeEventId?: string | null;
  celebrationTeamId?: string | null;
  primaryPlayerId?: string | null;
  secondaryPlayerId?: string | null;
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
  const anchorX = raw.anchorX != null && Number.isFinite(raw.anchorX) ? clampUnit(raw.anchorX) : null;
  const anchorY = raw.anchorY != null && Number.isFinite(raw.anchorY) ? clampUnit(raw.anchorY) : null;
  const speedRatio =
    raw.speedRatio != null && Number.isFinite(raw.speedRatio) ? Math.min(1, Math.max(0, raw.speedRatio)) : null;
  return {
    ...raw,
    playerId,
    side,
    x: clampUnit(raw.x),
    y: clampUnit(raw.y),
    anchorX,
    anchorY,
    speedRatio,
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
      ? {
          ...sample.ball,
          x: clampUnit(sample.ball.x),
          y: clampUnit(sample.ball.y),
          height:
            sample.ball.height != null && Number.isFinite(sample.ball.height)
              ? Math.max(0, sample.ball.height)
              : null,
        }
      : null;
  const ballTrajectory = Array.isArray(sample.ballTrajectory)
    ? sample.ballTrajectory
        .filter((pt) => pt && Number.isFinite(pt.x) && Number.isFinite(pt.y))
        .map((pt) => ({
          ...pt,
          x: clampUnit(pt.x),
          y: clampUnit(pt.y),
          height: pt.height != null && Number.isFinite(pt.height) ? Math.max(0, pt.height) : null,
        }))
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

export type HighlightPlaybackMode = "full" | "extended" | "key";

const KEY_HIGHLIGHT_TYPES = new Set([
  "goal",
  "penalty_goal",
  "own_goal",
  "penalty",
  "red_card",
  "save",
  "shot",
]);

const EXTENDED_HIGHLIGHT_TYPES = new Set([
  ...Array.from(KEY_HIGHLIGHT_TYPES),
  "miss",
  "corner",
  "free_kick",
  "yellow_card",
  "substitution",
  "foul",
  "header",
  "through_ball",
  "cross",
]);

/**
 * Determines whether `timeSeconds` falls within the build-up or aftermath window `[-7s, +5s]`
 * of an authoritative match event for the selected highlight mode (`full`, `extended`, or `key`).
 */
export function isHighlightMoment(
  timeSeconds: number,
  events: ReadonlyArray<Record<string, any>> | null | undefined,
  mode: HighlightPlaybackMode = "full",
): boolean {
  if (mode === "full") return true;
  if (!Array.isArray(events) || events.length === 0) return true;
  const allowed = mode === "key" ? KEY_HIGHLIGHT_TYPES : EXTENDED_HIGHLIGHT_TYPES;
  // Opening kickoff (0..8s) is always shown
  if (timeSeconds <= 8) return true;
  for (const ev of events) {
    if (!ev) continue;
    const rawType = String(ev.type || ev.event_type || "").toLowerCase();
    if (!allowed.has(rawType)) continue;
    const evSec = Number.isFinite(Number(ev.time_seconds))
      ? Number(ev.time_seconds)
      : Number.isFinite(Number(ev.minute ?? ev.clock_minute))
        ? Number(ev.minute ?? ev.clock_minute) * 60
        : NaN;
    if (!Number.isFinite(evSec)) continue;
    if (timeSeconds >= evSec - 7 && timeSeconds <= evSec + 5) {
      return true;
    }
  }
  return false;
}

/**
 * Steps a recorded replay cursor forward monotonically, respecting pause/resume,
 * playback speed changes, highlight mode fast-forwarding between dead phases,
 * and clamping at the authoritative end-of-replay timestamp.
 */
export function stepReplayClock(input: {
  currentTimeSeconds: number;
  deltaMs: number;
  durationSeconds: number;
  paused?: boolean;
  speed?: number;
  highlightMode?: HighlightPlaybackMode;
  events?: ReadonlyArray<Record<string, any>> | null;
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
  const baseSpeed = Number.isFinite(input.speed) && (input.speed as number) > 0 ? (input.speed as number) : 1;
  const mode = input.highlightMode || "full";
  const inHighlight = isHighlightMoment(current, input.events, mode);
  const effectiveSpeed = mode === "full" || inHighlight ? baseSpeed : Math.max(baseSpeed * 3.5, 4.2);
  const deltaSeconds = Math.max(0, Number.isFinite(input.deltaMs) ? input.deltaMs / 1000 : 0);
  return Math.min(maxDuration, current + deltaSeconds * effectiveSpeed);
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
  const fromPlayers = Array.isArray(from?.players)
    ? from.players.map(sanitizePitchPlayer).filter((p): p is PitchPlayer => p !== null)
    : [];
  const toPlayers = Array.isArray(to?.players)
    ? to.players.map(sanitizePitchPlayer).filter((p): p is PitchPlayer => p !== null)
    : [];

  const fromByKey = new Map<string, PitchPlayer>();
  for (const player of fromPlayers) {
    fromByKey.set(playerIdentityKey(player), player);
  }
  const toByKey = new Map<string, PitchPlayer>();
  for (const player of toPlayers) {
    toByKey.set(playerIdentityKey(player), player);
  }

  const blendPlayerPair = (origin: PitchPlayer, target: PitchPlayer, useOriginIdentity: boolean): PitchPlayer => {
    const base = useOriginIdentity ? origin : target;
    const anchorX =
      origin.anchorX != null && target.anchorX != null
        ? origin.anchorX + (target.anchorX - origin.anchorX) * t
        : target.anchorX ?? origin.anchorX ?? null;
    const anchorY =
      origin.anchorY != null && target.anchorY != null
        ? origin.anchorY + (target.anchorY - origin.anchorY) * t
        : target.anchorY ?? origin.anchorY ?? null;
    const speedRatio =
      origin.speedRatio != null && target.speedRatio != null
        ? origin.speedRatio + (target.speedRatio - origin.speedRatio) * t
        : target.speedRatio ?? origin.speedRatio ?? null;
    const staminaPct =
      origin.staminaPct != null && target.staminaPct != null
        ? origin.staminaPct + (target.staminaPct - origin.staminaPct) * t
        : target.staminaPct ?? origin.staminaPct ?? null;
    const velocity =
      origin.velocity && target.velocity
        ? {
            x: origin.velocity.x + (target.velocity.x - origin.velocity.x) * t,
            y: origin.velocity.y + (target.velocity.y - origin.velocity.y) * t,
          }
        : target.velocity ?? origin.velocity ?? null;
    const facing =
      origin.facing && target.facing
        ? {
            x: origin.facing.x + (target.facing.x - origin.facing.x) * t,
            y: origin.facing.y + (target.facing.y - origin.facing.y) * t,
          }
        : target.facing ?? origin.facing ?? null;

    return {
      ...base,
      x: origin.x + (target.x - origin.x) * t,
      y: origin.y + (target.y - origin.y) * t,
      anchorX,
      anchorY,
      speedRatio,
      staminaPct,
      velocity,
      facing,
      hasBall: useOriginIdentity ? Boolean(origin.hasBall) : Boolean(target.hasBall),
      state: useOriginIdentity ? origin.state || target.state : target.state || origin.state,
      animationState: useOriginIdentity
        ? origin.animationState || target.animationState
        : target.animationState || origin.animationState,
      highlighted: useOriginIdentity ? Boolean(origin.highlighted) : Boolean(target.highlighted),
    };
  };

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
        players.push(blendPlayerPair(fromPlayer, target, true));
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
        players.push(blendPlayerPair(origin, toPlayer, false));
      }
    }
  }

  const fromBall =
    from?.ball && Number.isFinite(from.ball.x) && Number.isFinite(from.ball.y)
      ? {
          ...from.ball,
          x: clampUnit(from.ball.x),
          y: clampUnit(from.ball.y),
          height: from.ball.height != null && Number.isFinite(from.ball.height) ? Math.max(0, from.ball.height) : null,
        }
      : null;
  const toBall =
    to?.ball && Number.isFinite(to.ball.x) && Number.isFinite(to.ball.y)
      ? {
          ...to.ball,
          x: clampUnit(to.ball.x),
          y: clampUnit(to.ball.y),
          height: to.ball.height != null && Number.isFinite(to.ball.height) ? Math.max(0, to.ball.height) : null,
        }
      : null;

  const ball =
    fromBall && toBall
      ? {
          ...(t < 0.5 ? fromBall : toBall),
          x: fromBall.x + (toBall.x - fromBall.x) * t,
          y: fromBall.y + (toBall.y - fromBall.y) * t,
          height:
            fromBall.height != null && toBall.height != null
              ? fromBall.height + (toBall.height - fromBall.height) * t
              : (t < 0.5 ? fromBall.height : toBall.height) ?? null,
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
    stage: t < 0.5 ? from?.stage ?? to?.stage : to?.stage ?? from?.stage,
    cameraPreset: t < 0.5 ? from?.cameraPreset ?? to?.cameraPreset : to?.cameraPreset ?? from?.cameraPreset,
    homeScore: t < 0.5 ? from?.homeScore ?? to?.homeScore : to?.homeScore ?? from?.homeScore,
    awayScore: t < 0.5 ? from?.awayScore ?? to?.awayScore : to?.awayScore ?? from?.awayScore,
    homeAttacksRight:
      t < 0.5 ? from?.homeAttacksRight ?? to?.homeAttacksRight : to?.homeAttacksRight ?? from?.homeAttacksRight,
    possessionSide: t < 0.5 ? from?.possessionSide ?? to?.possessionSide : to?.possessionSide ?? from?.possessionSide,
    possessionPhase:
      t < 0.5 ? from?.possessionPhase ?? to?.possessionPhase : to?.possessionPhase ?? from?.possessionPhase,
    transitionState:
      t < 0.5 ? from?.transitionState ?? to?.transitionState : to?.transitionState ?? from?.transitionState,
    dangerZone: t < 0.5 ? from?.dangerZone ?? to?.dangerZone : to?.dangerZone ?? from?.dangerZone,
    pressureIndex:
      from?.pressureIndex != null && to?.pressureIndex != null
        ? from.pressureIndex + (to.pressureIndex - from.pressureIndex) * t
        : (t < 0.5 ? from?.pressureIndex : to?.pressureIndex) ?? null,
    compactnessHome:
      from?.compactnessHome != null && to?.compactnessHome != null
        ? from.compactnessHome + (to.compactnessHome - from.compactnessHome) * t
        : (t < 0.5 ? from?.compactnessHome : to?.compactnessHome) ?? null,
    compactnessAway:
      from?.compactnessAway != null && to?.compactnessAway != null
        ? from.compactnessAway + (to.compactnessAway - from.compactnessAway) * t
        : (t < 0.5 ? from?.compactnessAway : to?.compactnessAway) ?? null,
    eventBanner: t < 0.5 ? from?.eventBanner ?? to?.eventBanner : to?.eventBanner ?? from?.eventBanner,
    activeEventId: t < 0.5 ? from?.activeEventId ?? to?.activeEventId : to?.activeEventId ?? from?.activeEventId,
    celebrationTeamId:
      t < 0.5 ? from?.celebrationTeamId ?? to?.celebrationTeamId : to?.celebrationTeamId ?? from?.celebrationTeamId,
    primaryPlayerId:
      t < 0.5 ? from?.primaryPlayerId ?? to?.primaryPlayerId : to?.primaryPlayerId ?? from?.primaryPlayerId,
    secondaryPlayerId:
      t < 0.5 ? from?.secondaryPlayerId ?? to?.secondaryPlayerId : to?.secondaryPlayerId ?? from?.secondaryPlayerId,
    players,
    ball,
    eventType: t < 0.5 ? from?.eventType : to?.eventType,
    ballTrajectory:
      t < 0.5 ? from?.ballTrajectory || to?.ballTrajectory || null : to?.ballTrajectory || from?.ballTrajectory || null,
  };
}

export type AnimationResolutionContext = {
  ball?: PitchBall | null;
  possessionSide?: PitchSide | null;
  primaryPlayerId?: string | null;
  secondaryPlayerId?: string | null;
  celebrationSide?: PitchSide | null;
  stage?: string | null;
  homeAttacksRight?: boolean;
};

function resolveIndividualMovementAction(player: {
  animationState?: string;
  state?: string;
  hasBall?: boolean;
  role?: string;
  speedRatio?: number | null;
  velocity?: { x: number; y: number } | null;
}): PlayerAction {
  const combinedState = `${player.animationState || ""} ${player.state || ""}`.toLowerCase();
  if (combinedState.includes("header")) return "header";
  if (combinedState.includes("celebrat")) return "celebrate";
  if (combinedState.includes("save")) return "save";
  if (combinedState.includes("dive")) return "dive";
  if (combinedState.includes("slide")) return "slide_tackle";
  if (combinedState.includes("shoot") || combinedState.includes("shot")) return "shoot";
  if (combinedState.includes("pass")) return "pass";
  if (combinedState.includes("tackle") || combinedState.includes("foul")) return "tackle";
  if (combinedState.includes("feint") || combinedState.includes("skill")) return "feint";
  if (combinedState.includes("control") || combinedState.includes("first_touch") || combinedState.includes("cushion")) return "control";
  if (combinedState.includes("jump") || combinedState.includes("aerial")) return "jump";
  if (combinedState.includes("turn")) return "turn";
  if (combinedState.includes("accel")) return "accelerate";
  if (combinedState.includes("dribble") || player.hasBall) return "dribble";
  if (combinedState.includes("sprint") || combinedState.includes("attacking") || combinedState.includes("counter")) {
    return "sprint";
  }
  if (combinedState.includes("press")) {
    return (player.speedRatio ?? 0) > 0.65 ? "sprint" : "jog";
  }
  if (combinedState.includes("walk") || combinedState.includes("recover") || combinedState.includes("rest")) {
    return "walk";
  }
  if (
    combinedState.includes("run") ||
    combinedState.includes("jog") ||
    combinedState.includes("move") ||
    combinedState.includes("support") ||
    combinedState.includes("track")
  ) {
    return "jog";
  }
  if (player.velocity) {
    const vMag = Math.hypot(player.velocity.x, player.velocity.y);
    if (vMag > 0.08) return "sprint";
    if (vMag > 0.03) return "jog";
    if (vMag > 0.008) return "walk";
  }
  if (typeof player.speedRatio === "number" && Number.isFinite(player.speedRatio)) {
    if (player.speedRatio >= 0.72) return "sprint";
    if (player.speedRatio >= 0.36) return "jog";
    if (player.speedRatio >= 0.14) return "walk";
  }
  return "idle";
}

export function animationFor(
  player: {
    playerId?: string;
    side?: PitchSide;
    x?: number;
    y?: number;
    animationState?: string;
    state?: string;
    hasBall?: boolean;
    highlighted?: boolean;
    role?: string;
    isGoalkeeper?: boolean;
    speedRatio?: number | null;
    velocity?: { x: number; y: number } | null;
  },
  eventType?: string | null,
  context?: AnimationResolutionContext,
): PlayerAction {
  const event = String(eventType || "").toLowerCase();
  const state = `${player.animationState || ""} ${player.state || ""}`.toLowerCase();
  const keeper =
    Boolean(player.isGoalkeeper) ||
    String(player.role || "").toLowerCase().includes("gk") ||
    String(player.role || "").toLowerCase().includes("goal");

  const hasSpatialContext =
    Boolean(context) ||
    (typeof player.x === "number" && Number.isFinite(player.x) && typeof player.y === "number" && Number.isFinite(player.y));

  // If called without spatial/frame context (e.g. direct single-player unit test), preserve direct event mapping
  if (!hasSpatialContext) {
    if (event === "goal" && player.hasBall) return "celebrate";
    if ((event === "save" || event === "shot") && keeper) return event === "save" ? "save" : "dive";
    if (event === "goal" || event === "shot" || event === "miss") return keeper ? "dive" : "shoot";
    if (event === "pass" || event === "attack") return player.hasBall ? "pass" : "jog";
    if (event === "foul" || event === "tackle") return "tackle";
    if (event === "substitution") return "idle";
    return resolveIndividualMovementAction(player);
  }

  const ball = context?.ball ?? null;
  const distToBall =
    ball && typeof player.x === "number" && typeof player.y === "number"
      ? Math.hypot(player.x - ball.x, player.y - ball.y)
      : Number.POSITIVE_INFINITY;
  const isPrimaryActor =
    Boolean(player.hasBall) ||
    Boolean(context?.primaryPlayerId && player.playerId === context.primaryPlayerId) ||
    Boolean(ball?.ownerPlayerId && player.playerId === ball.ownerPlayerId) ||
    distToBall <= 0.042;
  const isSecondaryActor = Boolean(context?.secondaryPlayerId && player.playerId === context.secondaryPlayerId);

  const scoringSide: PitchSide | null =
    context?.celebrationSide ??
    context?.possessionSide ??
    (ball ? (ball.x >= 0.5 ? "home" : "away") : player.side ?? null);

  // Determine whether this goalkeeper is at the active goal end where the shot/save/goal is happening
  const isDefendingKeeperNearBall =
    keeper &&
    (!ball ||
      distToBall <= 0.28 ||
      (ball.x < 0.35 && player.side === (context?.homeAttacksRight === false ? "away" : "home")) ||
      (ball.x > 0.65 && player.side === (context?.homeAttacksRight === false ? "home" : "away")));

  if (event === "goal") {
    if (player.side && scoringSide && player.side === scoringSide) {
      if (keeper) return "idle";
      if (isPrimaryActor || player.highlighted || distToBall <= 0.36) {
        return "celebrate";
      }
      return "jog";
    }
    if (isDefendingKeeperNearBall && context?.stage !== "post_event" && context?.stage !== "reset") {
      return "dive";
    }
    return resolveIndividualMovementAction(player);
  }

  if (event === "save") {
    if (keeper) {
      return isDefendingKeeperNearBall ? "save" : "idle";
    }
    if (isPrimaryActor) return "shoot";
    return resolveIndividualMovementAction(player);
  }

  if (event === "shot" || event === "miss" || event === "penalty") {
    if (keeper) {
      return isDefendingKeeperNearBall ? "dive" : "idle";
    }
    if (isPrimaryActor) {
      if (state.includes("header") || (ball?.height && ball.height >= 1.35)) {
        return "header";
      }
      return "shoot";
    }
    return resolveIndividualMovementAction(player);
  }

  if (
    event === "pass" ||
    event === "attack" ||
    event === "through_ball" ||
    event === "cross" ||
    event === "corner" ||
    event === "free_kick" ||
    event === "goal_kick" ||
    event === "kickoff"
  ) {
    if (isPrimaryActor) {
      if (state.includes("header")) return "header";
      return "pass";
    }
    return resolveIndividualMovementAction(player);
  }

  if (event === "header") {
    if (isPrimaryActor || distToBall <= 0.08) return "header";
    return resolveIndividualMovementAction(player);
  }

  if (event === "foul" || event === "tackle" || event === "yellow_card" || event === "red_card") {
    if (isPrimaryActor || isSecondaryActor || distToBall <= 0.065) {
      // Distinguish sliding vs standing tackle from state string
      if (state.includes("slide")) return "slide_tackle";
      return "tackle";
    }
    return resolveIndividualMovementAction(player);
  }

  if (event === "substitution" || event === "halftime" || event === "fulltime") {
    return "idle";
  }

  // First-touch / ball-control: receiver cushioning an incoming pass or cross
  if ((event === "pass" || event === "cross" || event === "through_ball") && !isPrimaryActor && distToBall <= 0.045) {
    if (state.includes("control") || state.includes("first_touch") || state.includes("receive")) {
      return "control";
    }
  }

  // Feint: dribbler performing a skill move against a close defender
  if (isPrimaryActor && player.hasBall && (state.includes("feint") || state.includes("skill") || state.includes("dribble"))) {
    if ((player.speedRatio ?? 0) > 0.4) return "feint";
  }

  return resolveIndividualMovementAction(player);
}

export type BallFlightKind =
  | "dribble"
  | "ground_pass"
  | "through_ball"
  | "long_pass"
  | "cross"
  | "header"
  | "shot"
  | "save_rebound"
  | "set_piece"
  | "loose_ball"
  | "in_goal";

export type ResolvedBallPresentation = {
  x: number;
  y: number;
  shadowX: number;
  shadowY: number;
  heightMeters: number;
  flightKind: BallFlightKind;
  carrier: PitchPlayer | null;
  inFlight: boolean;
  speedNorm: number;
};

/**
 * Ensures the ball has a coherent physical and visual relationship with the active player and match event:
 * - Anchors the ball at the ball-carrier's feet (offset slightly in their facing direction) when controlled.
 * - Releases the ball immediately during passes, crosses, shots, saves, rebounds, set pieces, and loose balls.
 * - Computes elevation (`heightMeters`) from authoritative `ball.height` or legitimate trajectory span so aerial
 *   balls separate cleanly from their ground shadow.
 */
export function resolveBallPresentation(
  frame: PitchFrame | null | undefined,
  trajectoryAlpha = 1,
  sampledBall?: { x: number; y: number } | null,
): ResolvedBallPresentation | null {
  if (!frame || (!frame.ball && !sampledBall)) return null;
  const rawBall = sampledBall || frame.ball!;
  const event = String(frame.eventType || "").toLowerCase();
  const ballState = String(frame.ball?.state || "").toLowerCase();
  const traj = frame.ballTrajectory && frame.ballTrajectory.length >= 2 ? frame.ballTrajectory : null;
  const alpha = Math.min(1, Math.max(0, Number.isFinite(trajectoryAlpha) ? trajectoryAlpha : 1));

  const carrier =
    frame.players.find((p) => p.hasBall) ||
    (frame.ball?.ownerPlayerId ? frame.players.find((p) => p.playerId === frame.ball?.ownerPlayerId) : null) ||
    null;

  const trajStart = traj ? traj[0] : null;
  const trajEnd = traj ? traj[traj.length - 1] : null;
  const trajSpan = trajStart && trajEnd ? Math.hypot(trajEnd.x - trajStart.x, trajEnd.y - trajStart.y) : 0;

  let flightKind: BallFlightKind = "loose_ball";
  if (event === "goal" || ballState === "in_goal") {
    flightKind = "in_goal";
  } else if (event === "save" || ballState === "saved" || ballState === "rebound") {
    flightKind = "save_rebound";
  } else if (event === "shot" || event === "miss" || ballState === "shot" || ballState === "shooting") {
    flightKind = "shot";
  } else if (event === "header" || ballState === "header") {
    flightKind = "header";
  } else if (
    event === "corner" ||
    event === "free_kick" ||
    event === "penalty" ||
    event === "goal_kick" ||
    event === "kickoff" ||
    ballState === "set_piece" ||
    ballState === "placed"
  ) {
    flightKind = "set_piece";
  } else if (
    event === "cross" ||
    ballState === "crossed" ||
    (trajStart && trajEnd && Math.abs(trajStart.y - 0.5) > 0.26 && Math.abs(trajEnd.y - 0.5) < 0.22 && (trajEnd.x < 0.22 || trajEnd.x > 0.78))
  ) {
    flightKind = "cross";
  } else if (event === "through_ball") {
    flightKind = "through_ball";
  } else if (traj && alpha < 0.96 && trajSpan > 0.025) {
    flightKind = trajSpan > 0.24 ? "long_pass" : "ground_pass";
  } else if (event === "pass" || ballState === "passing") {
    flightKind = trajSpan > 0.24 ? "long_pass" : "ground_pass";
  } else if (carrier) {
    flightKind = "dribble";
  }

  const inFlight =
    flightKind === "ground_pass" ||
    flightKind === "through_ball" ||
    flightKind === "long_pass" ||
    flightKind === "cross" ||
    flightKind === "header" ||
    flightKind === "shot" ||
    flightKind === "save_rebound" ||
    (flightKind === "set_piece" && Boolean(traj && alpha > 0.04 && alpha < 0.96));

  let x = clampUnit(rawBall.x);
  let y = clampUnit(rawBall.y);

  // When a player is actively dribbling/controlling the ball (and it isn't mid-flight on a pass/shot),
  // keep the ball cleanly at the carrier's feet in their facing direction.
  if (carrier && !inFlight && flightKind === "dribble") {
    const distFromCarrier = Math.hypot(x - carrier.x, y - carrier.y);
    if (distFromCarrier < 0.065) {
      const defaultDirX = carrier.side === "home" ? (frame.homeAttacksRight === false ? -1 : 1) : frame.homeAttacksRight === false ? 1 : -1;
      const fx = carrier.facing?.x ?? carrier.velocity?.x ?? defaultDirX;
      const fy = carrier.facing?.y ?? carrier.velocity?.y ?? 0;
      const fLen = Math.hypot(fx, fy) || 1;
      const footX = clampUnit(carrier.x + (fx / fLen) * 0.011);
      const footY = clampUnit(carrier.y + (fy / fLen) * 0.008);
      x = footX * 0.72 + x * 0.28;
      y = footY * 0.72 + y * 0.28;
    }
  }

  let heightMeters =
    frame.ball?.height != null && Number.isFinite(frame.ball.height) ? Math.max(0, frame.ball.height) : 0;

  if (heightMeters <= 0.05 && inFlight) {
    const arc = Math.max(0, 4 * alpha * (1 - alpha));
    if (flightKind === "cross") {
      heightMeters = arc * 2.4;
    } else if (flightKind === "long_pass") {
      heightMeters = arc * 1.8;
    } else if (flightKind === "set_piece") {
      heightMeters = arc * (event === "penalty" ? 0.9 : 2.1);
    } else if (flightKind === "shot") {
      heightMeters = Math.sin(Math.min(1, alpha) * Math.PI * 0.85) * 1.35;
    } else if (flightKind === "header") {
      heightMeters = 1.6 * (1 - alpha * 0.65);
    } else if (flightKind === "save_rebound") {
      heightMeters = Math.abs(Math.sin(alpha * Math.PI * 2)) * 0.85;
    }
  }

  const vel = frame.ball?.velocity;
  const speedNorm = vel
    ? Math.min(1, Math.hypot(vel.x, vel.y) / 28)
    : inFlight
      ? Math.min(1, Math.max(0.25, trajSpan * 2.6))
      : carrier
        ? Math.min(0.6, carrier.speedRatio ?? 0.32)
        : 0.1;

  return {
    x,
    y,
    shadowX: x,
    shadowY: y,
    heightMeters,
    flightKind,
    carrier: inFlight ? null : carrier,
    inFlight,
    speedNorm,
  };
}

export type BroadcastBannerTone = "goal" | "chance" | "card_yellow" | "card_red" | "set_piece" | "phase" | "tactical";

export type BroadcastBannerState = {
  kind: string;
  tone: BroadcastBannerTone;
  badge: string;
  headline: string;
  subline: string;
  minuteLabel: string;
  teamSide: PitchSide | null;
  scoreline: string | null;
};

/**
 * Derives a television-style broadcast lower-third/banner state from authoritative frame & event data.
 * Never fabricates goals, cards, or outcomes not present in the authoritative frame.
 */
export function deriveBroadcastBanner(
  frame: PitchFrame | null | undefined,
  options?: {
    homeName?: string;
    awayName?: string;
    activeEventSummary?: string | null;
    activeEventPlayerName?: string | null;
    activeEventTeamSide?: PitchSide | null;
  },
): BroadcastBannerState | null {
  if (!frame) return null;
  const homeName = options?.homeName || "Home";
  const awayName = options?.awayName || "Away";
  const event = String(frame.eventType || "").toLowerCase();
  const phase = String(frame.phase || "").toLowerCase();
  const minute = Number.isFinite(frame.clockMinute)
    ? Math.max(0, Math.round(frame.clockMinute as number))
    : Math.max(0, Math.floor((frame.timeSeconds || 0) / 60));
  const minuteLabel = `${minute}'`;
  const scoreline =
    frame.homeScore != null && frame.awayScore != null ? `${frame.homeScore} - ${frame.awayScore}` : null;

  const primaryPlayer =
    (frame.primaryPlayerId ? frame.players.find((p) => p.playerId === frame.primaryPlayerId) : null) ||
    frame.players.find((p) => p.hasBall) ||
    frame.players.find((p) => p.highlighted) ||
    null;
  const teamSide: PitchSide | null =
    options?.activeEventTeamSide || primaryPlayer?.side || frame.possessionSide || null;
  const teamName = teamSide === "away" ? awayName : teamSide === "home" ? homeName : null;
  const playerLabel =
    options?.activeEventPlayerName ||
    (primaryPlayer
      ? `${primaryPlayer.shirtNumber ? `#${primaryPlayer.shirtNumber} ` : ""}${primaryPlayer.name}`
      : null);

  if (event === "goal") {
    return {
      kind: "goal",
      tone: "goal",
      badge: "GOAL!",
      headline: playerLabel ? `${playerLabel}${teamName ? ` · ${teamName}` : ""}` : frame.eventBanner || `${teamName || "Match"} Goal`,
      subline: options?.activeEventSummary || frame.eventBanner || "Clinical finish into the back of the net",
      minuteLabel,
      teamSide,
      scoreline,
    };
  }

  if (event === "penalty") {
    return {
      kind: "penalty",
      tone: "chance",
      badge: "PENALTY",
      headline: frame.eventBanner || (teamName ? `Penalty to ${teamName}` : "Spot Kick Awarded"),
      subline: options?.activeEventSummary || (playerLabel ? `${playerLabel} steps up to the spot` : "High-pressure moment from 12 yards"),
      minuteLabel,
      teamSide,
      scoreline,
    };
  }

  if (event === "save") {
    const primaryIsKeeper = Boolean(
      primaryPlayer &&
        (primaryPlayer.isGoalkeeper || String(primaryPlayer.role || "").toLowerCase().includes("gk")),
    );
    const keeper = primaryIsKeeper
      ? primaryPlayer
      : frame.players.find(
          (p) =>
            (p.isGoalkeeper || String(p.role || "").toLowerCase().includes("gk")) &&
            (!teamSide || p.side !== teamSide),
        ) || primaryPlayer;
    const keeperLabel = keeper ? `${keeper.shirtNumber ? `#${keeper.shirtNumber} ` : ""}${keeper.name}` : playerLabel;
    return {
      kind: "save",
      tone: "chance",
      badge: "GREAT SAVE",
      headline: keeperLabel || frame.eventBanner || "Goalkeeper Intervention",
      subline: options?.activeEventSummary || "Strong hands to deny the effort on goal",
      minuteLabel,
      teamSide: keeper?.side || teamSide,
      scoreline,
    };
  }

  if (event === "shot" || event === "miss") {
    return {
      kind: event,
      tone: "chance",
      badge: event === "shot" ? "SHOT ON TARGET" : "CLOSE EFFORT",
      headline: playerLabel ? `${playerLabel}${teamName ? ` · ${teamName}` : ""}` : frame.eventBanner || "Goal Attempt",
      subline: options?.activeEventSummary || (event === "shot" ? "Testing the goalkeeper from range" : "Effort flashes just past the woodwork"),
      minuteLabel,
      teamSide,
      scoreline,
    };
  }

  if (event === "red_card" || event === "yellow_card") {
    const isRed = event === "red_card";
    return {
      kind: event,
      tone: isRed ? "card_red" : "card_yellow",
      badge: isRed ? "RED CARD" : "YELLOW CARD",
      headline: playerLabel ? `${playerLabel}${teamName ? ` · ${teamName}` : ""}` : frame.eventBanner || "Disciplinary Action",
      subline: options?.activeEventSummary || (isRed ? "Dismissed by the referee" : "Caution issued by the referee"),
      minuteLabel,
      teamSide,
      scoreline,
    };
  }

  if (event === "foul") {
    return {
      kind: "foul",
      tone: "set_piece",
      badge: "FOUL",
      headline: frame.eventBanner || (teamName ? `Free Kick · ${teamName}` : "Play Stopped for a Foul"),
      subline: options?.activeEventSummary || (playerLabel ? `Infringement involving ${playerLabel}` : "Referee blows for a free kick"),
      minuteLabel,
      teamSide,
      scoreline,
    };
  }

  if (event === "substitution") {
    return {
      kind: "substitution",
      tone: "tactical",
      badge: "SUBSTITUTION",
      headline: frame.eventBanner || (teamName ? `Tactical Change · ${teamName}` : "Tactical Substitution"),
      subline: options?.activeEventSummary || (playerLabel ? `${playerLabel} enters the pitch` : "Fresh legs introduced from the touchline"),
      minuteLabel,
      teamSide,
      scoreline,
    };
  }

  if (event === "corner" || event === "free_kick") {
    return {
      kind: event,
      tone: "set_piece",
      badge: event === "corner" ? "CORNER KICK" : "FREE KICK",
      headline: frame.eventBanner || (teamName ? `Set Piece · ${teamName}` : "Attacking Set Piece"),
      subline: options?.activeEventSummary || "Players pack the penalty area for the delivery",
      minuteLabel,
      teamSide,
      scoreline,
    };
  }

  if (event === "kickoff" || (minute <= 1 && (frame.timeSeconds || 0) <= 4 && phase === "first_half")) {
    return {
      kind: "kickoff",
      tone: "phase",
      badge: "KICK-OFF",
      headline: `${homeName} vs ${awayName}`,
      subline: frame.eventBanner || options?.activeEventSummary || "We are underway on the broadcast pitch",
      minuteLabel,
      teamSide,
      scoreline,
    };
  }

  if (event === "halftime" || phase === "halftime" || phase === "half_time") {
    return {
      kind: "halftime",
      tone: "phase",
      badge: "HALF-TIME",
      headline: `${homeName} ${frame.homeScore ?? 0} - ${frame.awayScore ?? 0} ${awayName}`,
      subline: frame.eventBanner || options?.activeEventSummary || "End of the first 45 minutes",
      minuteLabel: "HT",
      teamSide: null,
      scoreline,
    };
  }

  if (event === "fulltime" || phase === "fulltime" || phase === "full_time" || phase === "completed") {
    return {
      kind: "fulltime",
      tone: "phase",
      badge: "FULL-TIME",
      headline: `${homeName} ${frame.homeScore ?? 0} - ${frame.awayScore ?? 0} ${awayName}`,
      subline: frame.eventBanner || options?.activeEventSummary || "Final whistle confirms the result",
      minuteLabel: "FT",
      teamSide: null,
      scoreline,
    };
  }

  if (frame.eventBanner) {
    return {
      kind: event || "banner",
      tone: frame.dangerZone === "box" ? "chance" : "tactical",
      badge: frame.dangerZone === "box" ? "BOX DANGER" : "MATCH EVENT",
      headline: frame.eventBanner,
      subline: options?.activeEventSummary || (teamName ? `${teamName} in possession` : "Live broadcast update"),
      minuteLabel,
      teamSide,
      scoreline,
    };
  }

  return null;
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
  if (event === "shot" || event === "miss" || event === "penalty") return "shot";
  if (event === "pass" || event === "attack" || event === "through_ball" || event === "cross") return "pass";
  if (event === "save") return "save";
  if (event === "yellow_card" || event === "red_card" || event === "foul") return "card";
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

export type PitchShotMarker = {
  id: string;
  x: number;
  y: number;
  side: PitchSide;
  outcome: "goal" | "saved" | "missed";
  xg: number;
  minute: number;
  playerName?: string;
};

/**
 * Extracts normalized on-pitch shot markers from authoritative match events and/or recorded frames
 * so the interactive Shot Map overlay can render cumulative xG shot circles and goal trajectories.
 */
export function extractShotMarkers(
  events: ReadonlyArray<Record<string, any>> | null | undefined,
  frames?: ReadonlyArray<PitchFrame> | null,
): PitchShotMarker[] {
  if (!Array.isArray(events) || events.length === 0) return [];
  const markers: PitchShotMarker[] = [];
  const seen = new Set<string>();

  for (let i = 0; i < events.length; i += 1) {
    const ev = events[i];
    if (!ev) continue;
    const rawType = String(ev.type || ev.event_type || "").toLowerCase();
    if (!["goal", "penalty_goal", "shot", "save", "miss"].includes(rawType)) continue;

    const minute = Number.isFinite(Number(ev.minute ?? ev.clock_minute))
      ? Math.max(0, Math.round(Number(ev.minute ?? ev.clock_minute)))
      : Number.isFinite(Number(ev.time_seconds))
        ? Math.max(0, Math.floor(Number(ev.time_seconds) / 60))
        : 0;
    const sec = Number.isFinite(Number(ev.time_seconds)) ? Number(ev.time_seconds) : minute * 60;
    const rawSide = String(ev.team || ev.side || "").toLowerCase();
    // Note: on a "save" event, if the event team is the defending team, the shot was taken by the opposite side
    let side: PitchSide = rawSide === "away" ? "away" : "home";
    const id = String(ev.event_id || ev.id || `${rawType}:${Math.round(sec)}:${i}`);
    if (seen.has(id)) continue;
    seen.add(id);

    // Check explicit coordinates on the event first, or look up the frame near `sec`
    let x = Number(ev.x ?? ev.position?.x);
    let y = Number(ev.y ?? ev.position?.y);
    if ((!Number.isFinite(x) || !Number.isFinite(y)) && Array.isArray(frames) && frames.length > 0) {
      const pair = seekTime(frames as PitchFrame[], Math.max(0, sec - 0.5));
      const refFrame = pair.left;
      if (refFrame) {
        const shooter =
          (ev.player_id || ev.primary_player_id
            ? refFrame.players.find((p) => p.playerId === String(ev.player_id || ev.primary_player_id))
            : null) ||
          refFrame.players.find((p) => p.hasBall) ||
          null;
        if (shooter) {
          x = shooter.x;
          y = shooter.y;
          side = shooter.side;
        } else if (refFrame.ball) {
          x = refFrame.ball.x;
          y = refFrame.ball.y;
        }
      }
    }

    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      // Deterministic box/edge-of-box fallback coordinate based on side when event lacks spatial coords
      x = side === "home" ? 0.84 : 0.16;
      y = 0.5 + (((i % 5) - 2) * 0.06);
    } else {
      x = x > 1.5 ? x / 100 : x;
      y = y > 1.5 ? y / 100 : y;
    }

    const clampedX = clampUnit(x, side === "home" ? 0.84 : 0.16);
    const clampedY = clampUnit(y, 0.5);
    const goalX = side === "home" ? 1 : 0;
    const distToGoal = Math.hypot(goalX - clampedX, 0.5 - clampedY);
    const rawXg = Number(ev.xg ?? ev.expected_goals);
    const xg =
      Number.isFinite(rawXg) && rawXg > 0
        ? Math.min(0.95, Math.max(0.03, rawXg))
        : rawType === "penalty_goal"
          ? 0.78
          : Math.min(0.68, Math.max(0.05, Number((0.52 * Math.exp(-distToGoal * 4.2)).toFixed(2))));

    const outcome: PitchShotMarker["outcome"] =
      rawType === "goal" || rawType === "penalty_goal"
        ? "goal"
        : rawType === "save"
          ? "saved"
          : "missed";

    markers.push({
      id,
      x: clampedX,
      y: clampedY,
      side,
      outcome,
      xg,
      minute,
      playerName: String(ev.player_name || ev.primary_player_name || "").trim() || undefined,
    });
  }

  return markers;
}

export type TouchlineNudge = {
  id: string;
  kind: "fatigue" | "discipline" | "deficit" | "protect_lead" | "momentum";
  title: string;
  detail: string;
  actionLabel: string;
  presetName?: "GEGENPRESS" | "LOW BLOCK" | "COUNTER" | "TIKI-TAKA";
  playerId?: string;
};

/**
 * Computes a contextual Assistant Manager touchline nudge strictly from authoritative live/replay state
 * (player stamina, yellow cards, or second-half scoreline). Returns null when no intervention is warranted.
 */
export function deriveTouchlineNudge(input: {
  players: ReadonlyArray<PitchPlayer>;
  events?: ReadonlyArray<Record<string, any>> | null;
  side: PitchSide;
  minute: number;
  homeScore: number;
  awayScore: number;
}): TouchlineNudge | null {
  const { players, events, side, minute, homeScore, awayScore } = input;
  const myPlayers = players.filter((p) => p.side === side);
  if (myPlayers.length === 0) return null;

  // 1. Fatigued player alert (< 48% stamina)
  const fatigued = [...myPlayers]
    .filter((p) => typeof p.staminaPct === "number" && Number.isFinite(p.staminaPct) && p.staminaPct < 48)
    .sort((a, b) => (a.staminaPct ?? 100) - (b.staminaPct ?? 100))[0];
  if (fatigued) {
    const pct = Math.round(fatigued.staminaPct ?? 45);
    return {
      id: `fatigue:${fatigued.playerId}`,
      kind: "fatigue",
      title: `FATIGUE ALERT · #${fatigued.shirtNumber} ${fatigued.name} (${pct}% Stamina)`,
      detail: "Work rate is dropping in transition. Consider a fresh substitution or slower tempo.",
      actionLabel: "SHIFT TO TIKI-TAKA CONTROL",
      presetName: "TIKI-TAKA",
      playerId: fatigued.playerId,
    };
  }

  // 2. Cautioned player on a yellow card
  if (Array.isArray(events) && events.length > 0) {
    const bookedIds = new Set<string>();
    for (const ev of events) {
      if (!ev) continue;
      const t = String(ev.type || ev.event_type || "").toLowerCase();
      if (t === "yellow_card") {
        const pid = String(ev.player_id || ev.primary_player_id || "");
        if (pid) bookedIds.add(pid);
      }
    }
    const bookedOnPitch = myPlayers.find((p) => bookedIds.has(p.playerId));
    if (bookedOnPitch) {
      return {
        id: `discipline:${bookedOnPitch.playerId}`,
        kind: "discipline",
        title: `DISCIPLINE RISK · #${bookedOnPitch.shirtNumber} ${bookedOnPitch.name} on a Yellow Card`,
        detail: "One mistimed challenge away from a dismissal. Ease pressing intensity or prepare a sub.",
        actionLabel: "EASE PRESS (TIKI-TAKA)",
        presetName: "TIKI-TAKA",
        playerId: bookedOnPitch.playerId,
      };
    }
  }

  const myScore = side === "away" ? awayScore : homeScore;
  const theirScore = side === "away" ? homeScore : awayScore;

  // 3. Second-half deficit
  if (minute >= 55 && myScore < theirScore) {
    return {
      id: `deficit:${minute >= 75 ? "late" : "mid"}:${myScore}-${theirScore}`,
      kind: "deficit",
      title: `TOUCHLINE NUDGE · Trailing ${myScore}-${theirScore} (${minute}')`,
      detail: "Push the defensive line +14m and trigger aggressive counter-pressing in the final third.",
      actionLabel: "APPLY GEGENPRESS OVERLOAD",
      presetName: "GEGENPRESS",
    };
  }

  // 4. Late lead protection
  if (minute >= 72 && myScore > theirScore) {
    return {
      id: `protect:${myScore}-${theirScore}`,
      kind: "protect_lead",
      title: `LEAD PROTECTION · Leading ${myScore}-${theirScore} (${minute}')`,
      detail: "Compact the central block into a 5-3-2 Low Block to deny space in behind.",
      actionLabel: "LOCK DOWN LOW BLOCK",
      presetName: "LOW BLOCK",
    };
  }

  return null;
}

// ---------------------------------------------------------------------------
// Duel outcome overlay — "WON BALL" pill shown above tackling player
// ---------------------------------------------------------------------------

export type DuelOutcomeOverlay = {
  /** Player who won the ball */
  playerId: string;
  side: PitchSide;
  /** Canvas-normalised pitch position (0-1) */
  x: number;
  y: number;
  /** Ms timestamp when the overlay was triggered */
  triggeredAtMs: number;
  /** Display duration in ms */
  durationMs: number;
};

/**
 * Derives a temporary "WON BALL" duel-outcome overlay from the current event frame.
 * Returns null when the event is not a successful tackle/foul won by the primary actor.
 */
export function deriveDuelOutcomeOverlay(
  frame: Pick<PitchFrame, "eventType" | "primaryPlayerId" | "secondaryPlayerId" | "players">,
  nowMs: number,
): DuelOutcomeOverlay | null {
  const event = String(frame.eventType || "").toLowerCase();
  if (event !== "tackle") return null;
  if (!frame.primaryPlayerId) return null;
  const winner = frame.players.find((p) => p.playerId === frame.primaryPlayerId);
  if (!winner) return null;
  return {
    playerId: winner.playerId,
    side: winner.side,
    x: winner.x,
    y: winner.y,
    triggeredAtMs: nowMs,
    durationMs: 1200,
  };
}

// ---------------------------------------------------------------------------
// Live xG running totals — computed from accumulated PitchShotMarker list
// ---------------------------------------------------------------------------

export type LiveXgTotals = {
  home: number;
  away: number;
  homeShots: number;
  awayShots: number;
};

/**
 * Aggregates expected goals from an accumulated shot-marker list produced by extractShotMarkers().
 * Safe to call on every render frame — O(n) over shot count which is always small.
 */
export function computeLiveXgTotals(markers: Array<{ side: PitchSide; xg: number }>): LiveXgTotals {
  let home = 0;
  let away = 0;
  let homeShots = 0;
  let awayShots = 0;
  for (const m of markers) {
    if (m.side === "home") {
      home += m.xg;
      homeShots += 1;
    } else {
      away += m.xg;
      awayShots += 1;
    }
  }
  return { home, away, homeShots, awayShots };
}


// ---------------------------------------------------------------------------
// Woodwork detection — ball on the goal line just outside the goalmouth
// ---------------------------------------------------------------------------

/** True when a normalised ball position sits on a goal line next to a post/crossbar. */
export function isWoodworkPosition(x: number | null | undefined, y: number | null | undefined): boolean {
  if (typeof x !== "number" || typeof y !== "number" || !Number.isFinite(x) || !Number.isFinite(y)) return false;
  const nearGoalLine = x < 0.07 || x > 0.93;
  const offCentre = Math.abs(y - 0.5);
  return nearGoalLine && offCentre > 0.07 && offCentre < 0.16;
}

// ---------------------------------------------------------------------------
// Match momentum — narrative momentum buckets (0-100 per 5 minutes, 50 = level)
// ---------------------------------------------------------------------------

/** Momentum in [-1, 1] at the given minute (positive = home pressure). */
export function momentumAt(values: ReadonlyArray<number> | null | undefined, minute: number): number {
  if (!Array.isArray(values) || values.length === 0 || !Number.isFinite(minute)) return 0;
  const idx = Math.min(values.length - 1, Math.max(0, Math.floor(minute / 5)));
  const v = Number(values[idx]);
  if (!Number.isFinite(v)) return 0;
  return Math.max(-1, Math.min(1, (v - 50) / 50));
}

// ---------------------------------------------------------------------------
// Broadcast director — event-driven camera framing
// ---------------------------------------------------------------------------

export type DirectorShot = {
  kind: "kickoff_wide" | "goal_cut" | "set_piece" | "injury_time" | "none";
  /** Multiplier applied on top of the camera mode's base zoom. */
  zoomMultiplier: number;
  /** Optional normalised focus point (0-1) the camera should drift toward. */
  focus: { x: number; y: number } | null;
};

/**
 * Picks a TV-director camera shot from the authoritative frame. Pure and stateless:
 * `eventAgeMs` is how long the current event has been on screen (supplied by the renderer).
 */
export function deriveDirectorShot(input: {
  eventType?: string | null;
  phase?: string | null;
  timeSeconds?: number | null;
  minute?: number | null;
  eventAgeMs?: number;
  ball?: { x: number; y: number } | null;
  scorer?: { x: number; y: number } | null;
  leadingSide?: PitchSide | null;
  homeAttacksRight?: boolean;
}): DirectorShot {
  const ev = String(input.eventType || "").toLowerCase();
  const age = input.eventAgeMs ?? 0;
  const t = input.timeSeconds ?? null;

  if (ev === "goal" || ev === "penalty_goal") {
    if (age < 800 && input.scorer) {
      return { kind: "goal_cut", zoomMultiplier: 1.8, focus: input.scorer };
    }
    return { kind: "none", zoomMultiplier: 1, focus: null };
  }
  if (ev === "corner" || ev === "free_kick" || ev === "penalty") {
    const bx = input.ball?.x ?? 0.5;
    // Frame the box the ball is attacking: both penalty spots stay in shot
    const boxX = bx >= 0.5 ? 0.86 : 0.14;
    return { kind: "set_piece", zoomMultiplier: ev === "penalty" ? 1.5 : 1.32, focus: { x: boxX, y: 0.5 } };
  }
  if (ev === "kickoff" || (String(input.phase || "").toLowerCase() === "first_half" && t !== null && t < 3)) {
    if (ev !== "kickoff" || age < 1500) {
      return { kind: "kickoff_wide", zoomMultiplier: 0.8, focus: { x: 0.5, y: 0.5 } };
    }
  }
  if ((input.minute ?? 0) >= 90 && input.leadingSide) {
    const homeRight = input.homeAttacksRight !== false;
    // Drift toward the goal the trailing side is attacking — that is where the tension is
    const trailingAttacksRight = input.leadingSide === "home" ? !homeRight : homeRight;
    return { kind: "injury_time", zoomMultiplier: 1.06, focus: { x: trailingAttacksRight ? 0.7 : 0.3, y: 0.5 } };
  }
  return { kind: "none", zoomMultiplier: 1, focus: null };
}

// ---------------------------------------------------------------------------
// Pass presentation helpers
// ---------------------------------------------------------------------------

/** Pitch metres a pass advanced the ball toward the passing side's attacking goal (negative = backward). */
export function progressivePassMeters(
  from: { x: number; y: number },
  to: { x: number; y: number },
  side: PitchSide,
  homeAttacksRight = true,
): number {
  const attacksRight = side === "home" ? homeAttacksRight : !homeAttacksRight;
  return (to.x - from.x) * (attacksRight ? 1 : -1) * 105;
}

/** Predicted receiver: passing side's player nearest the trajectory end point (excluding the passer). */
export function predictPassReceiver(
  trajectory: ReadonlyArray<{ x: number; y: number }> | null | undefined,
  players: ReadonlyArray<PitchPlayer>,
  passer: PitchPlayer | null | undefined,
): { player: PitchPlayer; target: { x: number; y: number } } | null {
  if (!passer || !Array.isArray(trajectory) || trajectory.length < 2) return null;
  const end = trajectory[trajectory.length - 1];
  let best: PitchPlayer | null = null;
  let bestD = Infinity;
  for (const p of players) {
    if (p.side !== passer.side || p.playerId === passer.playerId) continue;
    const d = Math.hypot(p.x - end.x, p.y - end.y);
    if (d < bestD) {
      bestD = d;
      best = p;
    }
  }
  if (!best || bestD > 0.15) return null;
  return { player: best, target: { x: end.x, y: end.y } };
}

/** Type-coloured pass arc: ground = cyan, through = emerald, long = amber, cross = rose. */
export function passArcColor(flightKind: string | null | undefined): string {
  switch (flightKind) {
    case "through_ball":
      return "#34d399";
    case "long_pass":
      return "#fbbf24";
    case "cross":
      return "#fb7185";
    default:
      return "#67e8f9";
  }
}

// ---------------------------------------------------------------------------
// Stamina warnings
// ---------------------------------------------------------------------------

export type StaminaWarning = "critical" | "low" | null;

/** Lineup badge level: < 25% critical, < 50% low. Unknown stamina yields no badge. */
export function staminaWarning(staminaPct: number | null | undefined): StaminaWarning {
  if (staminaPct == null || !Number.isFinite(Number(staminaPct))) return null;
  const v = Number(staminaPct);
  if (v < 25) return "critical";
  if (v < 50) return "low";
  return null;
}
