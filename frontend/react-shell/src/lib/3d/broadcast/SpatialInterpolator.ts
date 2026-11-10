/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Authoritative Spatial Interpolator.
 *
 * Smoothly interpolates discrete server simulation ticks (MatchTimelineFrameView)
 * into high-fidelity 60fps 3D telemetry without fabricating simulation events.
 *
 * Guarantees:
 * 1. Bounded interpolation: Clamped to [0..1] between adjacent ticks; NO runaway prediction.
 * 2. Pitch boundary enforcement: Players & ball stay within FIFA metric bounds.
 * 3. Halftime / attacking direction flip handling: Clean snap, no warping across the pitch.
 * 4. Missing frame resilience: Clamps gaps > 2.5s to prevent ghost trajectories.
 * 5. Deterministic seeking: Local scrubbing seeks deterministically without mutating server state.
 */

import {
  pitchTo3D,
  PITCH_BOUNDS,
} from "./matchCoordinates";
import {
  SpectatorSafeFrameView,
  SpectatorSafePlayerTelemetry,
} from "./spectatorContract";


/**
 * Advances the local broadcast cursor without jumping over intermediate match
 * frames after a delayed render callback. A short bounded step is used for the
 * delayed callback itself; subsequent live frames may catch up at up to 2x,
 * while preserving a sequence of observable interpolation states.
 */
export function calculateTimelineAdvanceSeconds(args: {
  currentTimeSeconds: number;
  frameDeltaMs: number;
  latestFrameTimeSeconds: number;
  isLive: boolean;
  playbackSpeed?: number;
}): number {
  const {
    currentTimeSeconds,
    frameDeltaMs,
    latestFrameTimeSeconds,
    isLive,
    playbackSpeed = 1,
  } = args;

  if (!Number.isFinite(currentTimeSeconds) || !Number.isFinite(frameDeltaMs)) {
    return 0;
  }

  const elapsedSeconds = Math.min(0.1, Math.max(0, frameDeltaMs) / 1000);
  const speed = Number.isFinite(playbackSpeed) ? Math.max(0, playbackSpeed) : 1;

  // Do not accelerate the same callback that reveals a large frame gap.
  // Catch-up begins on normal subsequent render frames so no large time jump
  // can skip the authoritative frames/events between the old and latest time.
  if (!isLive || frameDeltaMs >= 250 || !Number.isFinite(latestFrameTimeSeconds)) {
    return elapsedSeconds * speed;
  }

  const backlogSeconds = Math.max(0, latestFrameTimeSeconds - currentTimeSeconds);
  const catchUpMultiplier =
    backlogSeconds > 0.5 ? Math.min(2, 1 + backlogSeconds * 0.1) : 1;

  return elapsedSeconds * speed * catchUpMultiplier;
}

export interface InterpolatedPlayerState {
  player_id: string;
  team_id: string;
  side: "home" | "away";
  shirt_number?: number;
  label: string;
  role: string;
  line?: string;
  state?: string;
  active?: boolean;
  highlighted?: boolean;
  position3D: [number, number, number]; // [X, Y, Z] in meters
  facingAngleRad: number; // Rotation around Y axis in radians
  animation_state: string;
  speed_ratio: number;
  has_possession: boolean;
  angular_velocity_rad?: number;
  acceleration_ratio?: number;
  just_received_ball?: boolean;
  is_releasing_ball?: boolean;
  is_receiving_ball?: boolean;
  is_pass_recipient?: boolean;
  anticipation_pose?: "shot_windup" | "save_prep" | "first_touch_prep" | null;
  tactical_instruction_marker?: string | null;
  stamina_pct?: number;
}

export interface InterpolatedBallState {
  position3D: [number, number, number]; // [X, Y, Z] in meters
  height: number;
  state: string;
  owner_player_id?: string | null;
  target_player_id?: string | null;
  contact_foot?: "left" | "right" | null;
  ballistic_apex?: number;
  bounce_offset?: number;
  roll_friction_factor?: number;
  velocity?: [number, number, number];
  spin?: [number, number, number];
}

export interface InterpolatedMatchState {
  time_seconds: number;
  clock_minute: number;
  phase: string;
  stage?: string;
  home_score: number;
  away_score: number;
  home_attacks_right: boolean;
  possession_side: "home" | "away";
  camera_preset: string;
  active_event_id?: string | null;
  event_banner?: string | null;
  celebration_team_id?: string | null;
  possession_phase?: string;
  transition_state?: string;
  danger_zone?: string | null;
  pressure_index?: number;
  compactness_home?: number;
  compactness_away?: number;
  frame_tags?: string[];
  players: InterpolatedPlayerState[];
  ball: InterpolatedBallState;
}

export interface TacticalVisualConfig {
  homeFormation?: string;
  awayFormation?: string;
  homeDefensiveLine?: "low" | "standard" | "high" | string | number;
  awayDefensiveLine?: "low" | "standard" | "high" | string | number;
  homePressing?: "low" | "standard" | "high" | string | number;
  awayPressing?: "low" | "standard" | "high" | string | number;
  homeWidth?: "narrow" | "balanced" | "wide" | string | number;
  awayWidth?: "narrow" | "balanced" | "wide" | string | number;
  homeTempo?: "slow" | "standard" | "fast" | string | number;
  awayTempo?: "slow" | "standard" | "fast" | string | number;
}

/**
 * Normalizes an angle in radians to [-PI, +PI].
 */
function normalizeAngle(rad: number): number {
  let angle = rad % (2 * Math.PI);
  if (angle > Math.PI) angle -= 2 * Math.PI;
  if (angle < -Math.PI) angle += 2 * Math.PI;
  return angle;
}

/**
 * Spherical interpolation of angles along the shortest arc.
 */
function lerpAngle(from: number, to: number, alpha: number): number {
  const normFrom = normalizeAngle(from);
  const normTo = normalizeAngle(to);
  let diff = normTo - normFrom;
  if (diff > Math.PI) diff -= 2 * Math.PI;
  if (diff < -Math.PI) diff += 2 * Math.PI;
  return normalizeAngle(normFrom + diff * alpha);
}

export class SpatialInterpolator {
  private frames: SpectatorSafeFrameView[] = [];
  private tacticalConfig: TacticalVisualConfig | null = null;

  constructor(initialFrames: SpectatorSafeFrameView[] = []) {
    this.setFrames(initialFrames);
  }

  public setTacticalConfig(config: TacticalVisualConfig | null): void {
    this.tacticalConfig = config ? { ...config } : null;
  }

  public getTacticalConfig(): TacticalVisualConfig | null {
    return this.tacticalConfig;
  }

  /**
   * Sets or updates the authoritative frame buffer, keeping it sorted by time_seconds.
   */
  public setFrames(newFrames: SpectatorSafeFrameView[]): void {
    if (!Array.isArray(newFrames) || newFrames.length === 0) {
      this.frames = [];
      return;
    }
    // Deduplicate and sort chronologically
    const unique = new Map<string, SpectatorSafeFrameView>();
    for (const f of newFrames) {
      if (f && typeof f.time_seconds === "number") {
        unique.set(f.frame_id || `t_${f.time_seconds}`, f);
      }
    }
    this.frames = Array.from(unique.values()).sort((a, b) => a.time_seconds - b.time_seconds);
  }

  /**
   * Appends newly streamed frames to the buffer.
   */
  public appendFrame(frame: SpectatorSafeFrameView): void {
    if (!frame || typeof frame.time_seconds !== "number") return;
    const last = this.frames[this.frames.length - 1];
    if (last && frame.frame_id === last.frame_id) return; // Ignore exact duplicate

    if (!last || frame.time_seconds >= last.time_seconds) {
      this.frames.push(frame);
    } else {
      // Out of order: re-insert into sorted array
      this.frames.push(frame);
      this.frames.sort((a, b) => a.time_seconds - b.time_seconds);
    }

    // Retain up to 2,400 frames so full 10-minute (600s) broadcasts can seek & replay across the entire match
    if (this.frames.length > 2400) {
      this.frames.splice(0, this.frames.length - 2400);
    }
  }

  public getFrameCount(): number {
    return this.frames.length;
  }

  public getStartTime(): number {
    return this.frames[0]?.time_seconds || 0;
  }

  public getEndTime(): number {
    return this.frames[this.frames.length - 1]?.time_seconds || 0;
  }

  /**
   * Computes the interpolated match state at exact query time t (seconds).
   */
  public interpolate(
    queryTimeSeconds: number,
    tacticalOverride?: TacticalVisualConfig | null
  ): InterpolatedMatchState | null {
    if (this.frames.length === 0) return null;
    const effectiveTactics = tacticalOverride !== undefined ? tacticalOverride : this.tacticalConfig;

    const firstFrame = this.frames[0];
    const lastFrame = this.frames[this.frames.length - 1];

    // Boundary clamping: NO extrapolation beyond known authoritative bounds
    if (queryTimeSeconds <= firstFrame.time_seconds) {
      const state = this.frameToInterpolated(firstFrame);
      if (effectiveTactics) this.applyTacticalShaping(state, effectiveTactics);
      return state;
    }
    if (queryTimeSeconds >= lastFrame.time_seconds) {
      const state = this.frameToInterpolated(lastFrame);
      if (effectiveTactics) this.applyTacticalShaping(state, effectiveTactics);
      return state;
    }

    // Binary search for bracket [frameA, frameB]
    let low = 0;
    let high = this.frames.length - 1;
    let indexA = 0;

    while (low <= high) {
      const mid = Math.floor((low + high) / 2);
      if (this.frames[mid].time_seconds <= queryTimeSeconds) {
        indexA = mid;
        low = mid + 1;
      } else {
        high = mid - 1;
      }
    }

    const frameA = this.frames[indexA];
    const frameB = this.frames[Math.min(indexA + 1, this.frames.length - 1)];

    if (frameA === frameB || frameB.time_seconds <= frameA.time_seconds) {
      return this.frameToInterpolated(frameA);
    }

    const duration = frameB.time_seconds - frameA.time_seconds;

    // Smoothly interpolate across frames without hard freeze stalls
    // Bounded alpha in [0.0, 1.0]
    const rawAlpha = (queryTimeSeconds - frameA.time_seconds) / duration;
    const alpha = Math.max(0.0, Math.min(1.0, rawAlpha));

    // Handle halftime attacking direction flip: clean snap instead of flight across pitch
    const isDirectionFlip = frameA.home_attacks_right !== frameB.home_attacks_right;
    const activeFrame = alpha >= 0.5 ? frameB : frameA;

    // Interpolate Ball
    const ballA3D = pitchTo3D(frameA.ball.position, frameA.ball.height, frameA.home_attacks_right);
    const ballB3D = pitchTo3D(frameB.ball.position, frameB.ball.height, frameB.home_attacks_right);

    let ballX = isDirectionFlip ? activeFrame.ball.position.x : ballA3D[0] + (ballB3D[0] - ballA3D[0]) * alpha;
    let ballY = ballA3D[1] + (ballB3D[1] - ballA3D[1]) * alpha;
    let ballZ = isDirectionFlip ? activeFrame.ball.position.y : ballA3D[2] + (ballB3D[2] - ballA3D[2]) * alpha;

    // Clamp ball to physical bounds
    ballX = Math.max(PITCH_BOUNDS.minX, Math.min(PITCH_BOUNDS.maxX, ballX));
    ballZ = Math.max(PITCH_BOUNDS.minZ, Math.min(PITCH_BOUNDS.maxZ, ballZ));
    ballY = Math.max(0, Math.min(PITCH_BOUNDS.maxY, ballY));

    // Interpolate Players
    const playerMapB = new Map<string, SpectatorSafePlayerTelemetry>();
    for (const p of frameB.players) {
      playerMapB.set(p.player_id, p);
    }

    const interpolatedPlayers: InterpolatedPlayerState[] = [];

    for (const pA of frameA.players) {
      const pB = playerMapB.get(pA.player_id);
      if (!pB) {
        // Player substituted or not in frameB
        interpolatedPlayers.push(this.playerToInterpolated(pA, frameA.home_attacks_right));
        continue;
      }

      const pA3D = pitchTo3D(pA.position, 0, frameA.home_attacks_right);
      const pB3D = pitchTo3D(pB.position, 0, frameB.home_attacks_right);

      const px = isDirectionFlip ? pB3D[0] : pA3D[0] + (pB3D[0] - pA3D[0]) * alpha;
      const pz = isDirectionFlip ? pB3D[2] : pA3D[2] + (pB3D[2] - pA3D[2]) * alpha;

      // Facing orientation: evaluate velocity direction or facing vector
      let angleA = 0;
      let angleB = 0;
      if (pA.facing) {
        angleA = Math.atan2(pA.facing.y, pA.facing.x);
      } else if (pA.velocity) {
        angleA = Math.atan2(pA.velocity.y, pA.velocity.x);
      }
      if (pB.facing) {
        angleB = Math.atan2(pB.facing.y, pB.facing.x);
      } else if (pB.velocity) {
        angleB = Math.atan2(pB.velocity.y, pB.velocity.x);
      }

      const facing = lerpAngle(angleA, angleB, alpha);
      const speedA = pA.speed_ratio ?? 0;
      const speedB = pB.speed_ratio ?? speedA;
      const speed = pA.speed_ratio !== undefined && pB.speed_ratio !== undefined
        ? speedA + (speedB - speedA) * alpha
        : (pB.speed_ratio ?? pA.speed_ratio ?? 0);

      let angleDiff = normalizeAngle(angleB) - normalizeAngle(angleA);
      if (angleDiff > Math.PI) angleDiff -= 2 * Math.PI;
      if (angleDiff < -Math.PI) angleDiff += 2 * Math.PI;
      const angularVelocity = duration > 0.01 ? angleDiff / duration : 0;
      const accelerationRatio = duration > 0.01 ? (speedB - speedA) / duration : 0;
      const ownedA = Boolean(pA.has_possession || frameA.ball.owner_player_id === pA.player_id);
      const ownedB = Boolean(pB.has_possession || frameB.ball.owner_player_id === pA.player_id);
      const isReleasing = Boolean(ownedA && !ownedB && alpha < 0.55);
      const isReceiving = Boolean(!ownedA && ownedB && alpha >= 0.35 && alpha < 0.8);
      const justReceived = Boolean(!ownedA && ownedB && alpha >= 0.2 && alpha <= 0.9);
      const isPassRecipient = Boolean(
        !ownedA &&
          ownedB &&
          frameB.ball.owner_player_id &&
          pB.player_id === frameB.ball.owner_player_id
      );

      // Short anticipation poses before shots, saves, and pass receptions so outcomes feel caused
      const nextAnim = (pB.animation_state || "").toLowerCase();
      const roleUpper = (pA.role || pB.role || "").toUpperCase();
      let anticipationPose: "shot_windup" | "save_prep" | "first_touch_prep" | null = null;
      if (alpha < 0.45 && (nextAnim === "shoot" || nextAnim === "volley")) {
        anticipationPose = "shot_windup";
      } else if (
        alpha < 0.55 &&
        (roleUpper === "GK" || roleUpper === "GOALKEEPER") &&
        (nextAnim.includes("save") || nextAnim.includes("dive") || Math.abs(ballB3D[0]) >= 38)
      ) {
        anticipationPose = "save_prep";
      } else if (isPassRecipient && alpha >= 0.35 && alpha < 0.82) {
        anticipationPose = "first_touch_prep";
      }

      interpolatedPlayers.push({
        player_id: pA.player_id,
        team_id: pA.team_id,
        side: pA.side,
        shirt_number: pA.shirt_number ?? pB.shirt_number,
        label: pA.label || pB.label,
        role: pA.role || pB.role,
        line: pA.line || pB.line,
        state: alpha >= 0.5 ? (pB.state || pA.state || "idle") : (pA.state || "idle"),
        active: alpha >= 0.5 ? pB.active !== false : pA.active !== false,
        highlighted: Boolean(alpha >= 0.5 ? pB.highlighted : pA.highlighted),
        position3D: [
          Math.max(PITCH_BOUNDS.minX, Math.min(PITCH_BOUNDS.maxX, px)),
          0,
          Math.max(PITCH_BOUNDS.minZ, Math.min(PITCH_BOUNDS.maxZ, pz)),
        ],
        facingAngleRad: facing,
        animation_state: alpha >= 0.5 ? (pB.animation_state || pA.animation_state || "idle") : (pA.animation_state || "idle"),
        speed_ratio: Math.max(0, Math.min(1, speed)),
        has_possession: Boolean(alpha >= 0.5 ? pB.has_possession : pA.has_possession),
        angular_velocity_rad: angularVelocity,
        acceleration_ratio: accelerationRatio,
        just_received_ball: justReceived,
        is_releasing_ball: isReleasing,
        is_receiving_ball: isReceiving,
        is_pass_recipient: isPassRecipient,
        anticipation_pose: anticipationPose,
        stamina_pct: pB.stamina_pct ?? pA.stamina_pct,
      });
    }

    // Keep bodies from occupying the same ground. A carrier stays on the ball
    // and the other player steps around him, instead of both snapping through.
    const MIN_SEPARATION_M = 1.15;
    const carrierId = frameA.ball.owner_player_id || frameB.ball.owner_player_id;
    for (let iter = 0; iter < 5; iter++) {
      for (let i = 0; i < interpolatedPlayers.length; i++) {
        const pi = interpolatedPlayers[i];
        if (pi.active === false) continue;
        for (let j = i + 1; j < interpolatedPlayers.length; j++) {
          const pj = interpolatedPlayers[j];
          if (pj.active === false) continue;
          const dx = pj.position3D[0] - pi.position3D[0];
          const dz = pj.position3D[2] - pi.position3D[2];
          const dist = Math.hypot(dx, dz);
          if (dist >= MIN_SEPARATION_M) continue;
          const overlap = MIN_SEPARATION_M - dist;
          const nx = dist > 0.04 ? dx / dist : Math.cos((i * 2 + j) * 1.7);
          const nz = dist > 0.04 ? dz / dist : Math.sin((i * 2 + j) * 1.7);
          const iCarries = pi.player_id === carrierId;
          const jCarries = pj.player_id === carrierId;
          const pushI = jCarries ? 0.15 : iCarries ? 0.85 : 0.5;
          const pushJ = iCarries ? 0.15 : jCarries ? 0.85 : 0.5;
          pi.position3D[0] = Math.max(PITCH_BOUNDS.minX, Math.min(PITCH_BOUNDS.maxX, pi.position3D[0] - nx * overlap * pushI));
          pi.position3D[2] = Math.max(PITCH_BOUNDS.minZ, Math.min(PITCH_BOUNDS.maxZ, pi.position3D[2] - nz * overlap * pushI));
          pj.position3D[0] = Math.max(PITCH_BOUNDS.minX, Math.min(PITCH_BOUNDS.maxX, pj.position3D[0] + nx * overlap * pushJ));
          pj.position3D[2] = Math.max(PITCH_BOUNDS.minZ, Math.min(PITCH_BOUNDS.maxZ, pj.position3D[2] + nz * overlap * pushJ));
        }
      }
    }

    // Controlled-foot dribble contact & released ballistic trajectory with bounce/friction/spin
    let contactFoot: "left" | "right" | null = null;
    let ballisticApex = 0;
    let bounceOffset = 0;
    let rollFrictionFactor = 1.0;
    const targetPlayerId =
      frameB.ball.owner_player_id && frameB.ball.owner_player_id !== frameA.ball.owner_player_id
        ? frameB.ball.owner_player_id
        : null;

    if (
      !isDirectionFlip &&
      frameA.ball.owner_player_id &&
      frameA.ball.owner_player_id === frameB.ball.owner_player_id &&
      ballY < 0.35
    ) {
      const carrier = interpolatedPlayers.find((p) => p.player_id === frameA.ball.owner_player_id);
      if (carrier) {
        const strideWave = Math.sin(alpha * Math.PI * 2);
        contactFoot = strideWave >= 0 ? "right" : "left";
        const dx = ballX - carrier.position3D[0];
        const dz = ballZ - carrier.position3D[2];
        const distToCarrier = Math.hypot(dx, dz);
        if (distToCarrier < 0.55) {
          const strideTouchLead = 0.28 + strideWave * 0.04;
          const lateralFootOffset = (contactFoot === "right" ? 0.08 : -0.08) * (1 - Math.abs(strideWave) * 0.35);
          const forwardX = Math.cos(carrier.facingAngleRad);
          const forwardZ = Math.sin(carrier.facingAngleRad);
          const rightX = -forwardZ;
          const rightZ = forwardX;
          ballX = Math.max(
            PITCH_BOUNDS.minX,
            Math.min(
              PITCH_BOUNDS.maxX,
              carrier.position3D[0] + forwardX * strideTouchLead + rightX * lateralFootOffset
            )
          );
          ballZ = Math.max(
            PITCH_BOUNDS.minZ,
            Math.min(
              PITCH_BOUNDS.maxZ,
              carrier.position3D[2] + forwardZ * strideTouchLead + rightZ * lateralFootOffset
            )
          );
        }
      }
    } else if (!isDirectionFlip && frameA.ball.owner_player_id && frameA.ball.owner_player_id !== frameB.ball.owner_player_id) {
      // Blend from passer's controlled-foot contact point into a released ballistic trajectory
      const passer = interpolatedPlayers.find((p) => p.player_id === frameA.ball.owner_player_id);
      const passDist = Math.hypot(ballB3D[0] - ballA3D[0], ballB3D[2] - ballA3D[2]);
      if (passer && alpha < 0.16) {
        contactFoot = "right";
        const footX = passer.position3D[0] + Math.cos(passer.facingAngleRad) * 0.42;
        const footZ = passer.position3D[2] + Math.sin(passer.facingAngleRad) * 0.42;
        const releaseBlend = alpha / 0.16;
        ballX = footX * (1 - releaseBlend) + ballX * releaseBlend;
        ballZ = footZ * (1 - releaseBlend) + ballZ * releaseBlend;
      }
      if (passDist > 12.0 && frameA.ball.height === 0 && frameB.ball.height === 0) {
        ballisticApex = Math.min(3.6, (passDist - 12.0) * 0.11);
        const parabola = 4 * alpha * (1 - alpha) * ballisticApex;
        bounceOffset = alpha > 0.78 ? Math.abs(Math.sin(((alpha - 0.78) / 0.22) * Math.PI)) * 0.18 : 0;
        ballY = Math.min(PITCH_BOUNDS.maxY, ballY + parabola + bounceOffset);
      }
    }

    // Grass roll friction deceleration & derived velocity/spin vectors
    if (ballY < 0.18 && (activeFrame.ball.state === "rolling" || activeFrame.ball.state === "pass")) {
      rollFrictionFactor = Number(Math.exp(-0.95 * alpha).toFixed(3));
    }
    const safeDur = Math.max(0.05, duration);
    const derivedVel: [number, number, number] = activeFrame.ball.velocity
      ? [activeFrame.ball.velocity.x, activeFrame.ball.velocity.y, activeFrame.ball.velocity.z]
      : [
          ((ballB3D[0] - ballA3D[0]) / safeDur) * rollFrictionFactor,
          (ballB3D[1] - ballA3D[1]) / safeDur,
          ((ballB3D[2] - ballA3D[2]) / safeDur) * rollFrictionFactor,
        ];
    const horizontalSpeed = Math.hypot(derivedVel[0], derivedVel[2]);
    const derivedSpin: [number, number, number] = activeFrame.ball.spin
      ? [activeFrame.ball.spin.x, activeFrame.ball.spin.y, activeFrame.ball.spin.z]
      : [
          Number((derivedVel[2] * 1.4).toFixed(2)),
          Number(((ballY > 0.6 ? 2.8 : 0.4) * Math.sign(derivedVel[0] || 1)).toFixed(2)),
          Number((-derivedVel[0] * 1.4).toFixed(2)),
        ];
    if (horizontalSpeed < 0.01 && !activeFrame.ball.spin) {
      derivedSpin[0] = 0;
      derivedSpin[1] = 0;
      derivedSpin[2] = 0;
    }

    const resultState: InterpolatedMatchState = {
      time_seconds: queryTimeSeconds,
      clock_minute: activeFrame.clock_minute,
      phase: activeFrame.phase,
      stage: activeFrame.stage || "event",
      home_score: activeFrame.home_score,
      away_score: activeFrame.away_score,
      home_attacks_right: activeFrame.home_attacks_right,
      possession_side: activeFrame.possession_side,
      camera_preset: activeFrame.camera_preset,
      active_event_id: activeFrame.active_event_id,
      event_banner: activeFrame.event_banner,
      celebration_team_id: activeFrame.celebration_team_id,
      possession_phase: activeFrame.possession_phase,
      transition_state: activeFrame.transition_state,
      danger_zone: activeFrame.danger_zone,
      pressure_index: activeFrame.pressure_index,
      compactness_home: activeFrame.compactness_home,
      compactness_away: activeFrame.compactness_away,
      frame_tags: activeFrame.frame_tags,
      players: interpolatedPlayers,
      ball: {
        position3D: [ballX, ballY, ballZ],
        height: ballY,
        state: activeFrame.ball.state,
        owner_player_id: activeFrame.ball.owner_player_id,
        target_player_id: targetPlayerId,
        contact_foot: contactFoot,
        ballistic_apex: ballisticApex,
        bounce_offset: bounceOffset,
        roll_friction_factor: rollFrictionFactor,
        velocity: derivedVel,
        spin: derivedSpin,
      },
    };

    if (effectiveTactics) {
      this.applyTacticalShaping(resultState, effectiveTactics);
    }

    return resultState;
  }

  /**
   * Visually expresses tactical instructions (formation shape, defensive line height,
   * lateral width/compactness, and pressing intensity) on off-ball outfield players
   * while keeping goalkeepers, the ball carrier, and highlighted event actors locked
   * to their exact authoritative coordinates.
   */
  private applyTacticalShaping(
    state: InterpolatedMatchState,
    tactics: TacticalVisualConfig
  ): void {
    const ballX = state.ball.position3D[0];
    const ballZ = state.ball.position3D[2];
    const ownerId = state.ball.owner_player_id;

    for (const p of state.players) {
      if (p.active === false) continue;
      const roleUpper = (p.role || "").toUpperCase();
      const lineLower = (p.line || "").toLowerCase();
      const isGK = roleUpper === "GK" || roleUpper === "GOALKEEPER" || lineLower === "goalkeeper";
      if (isGK || p.has_possession || p.player_id === ownerId || p.highlighted) {
        continue;
      }

      const isHome = p.side === "home";
      const attacksRight = isHome ? state.home_attacks_right : !state.home_attacks_right;
      const attackSign = attacksRight ? 1 : -1;

      const rawLine = isHome ? tactics.homeDefensiveLine : tactics.awayDefensiveLine;
      const lineSetting =
        typeof rawLine === "number"
          ? rawLine >= 65
            ? "high"
            : rawLine <= 35
            ? "low"
            : "standard"
          : String(rawLine || "standard").toLowerCase();


      const rawPress = isHome ? tactics.homePressing : tactics.awayPressing;
      const pressSetting =
        typeof rawPress === "number"
          ? rawPress >= 65
            ? "high"
            : rawPress <= 35
            ? "low"
            : "standard"
          : String(rawPress || "standard").toLowerCase();

      const rawWidth = isHome ? tactics.homeWidth : tactics.awayWidth;
      const widthSetting =
        typeof rawWidth === "number"
          ? rawWidth >= 65
            ? "wide"
            : rawWidth <= 35
            ? "narrow"
            : "balanced"
          : String(rawWidth || "balanced").toLowerCase();

      const formation = String(
        (isHome ? tactics.homeFormation : tactics.awayFormation) || ""
      ).trim();

      // 1. Defensive Line Height & Formation Depth Shift
      let depthOffsetM = 0;
      if (lineSetting === "high" || lineSetting === "aggressive") {
        depthOffsetM += 4.2 * attackSign;
      } else if (lineSetting === "low" || lineSetting === "deep") {
        depthOffsetM -= 4.2 * attackSign;
      }

      // Formation-specific line adjustments
      const isDefender = lineLower.includes("def") || roleUpper.includes("DEF") || roleUpper.includes("CB") || roleUpper.includes("FB") || roleUpper.includes("LB") || roleUpper.includes("RB") || roleUpper.includes("WB");
      const isAttacker = lineLower.includes("att") || lineLower.includes("fw") || roleUpper.includes("FWD") || roleUpper.includes("ST") || roleUpper.includes("CF") || roleUpper.includes("LW") || roleUpper.includes("RW");
      if (formation === "3-5-2" || formation === "5-3-2") {
        if (!isDefender && !isAttacker) {
          depthOffsetM += 1.6 * attackSign;
        }
      } else if (formation === "4-2-3-1") {
        if (isAttacker) {
          depthOffsetM += 1.4 * attackSign;
        }
      } else if (formation === "4-4-2") {
        if (isDefender) {
          depthOffsetM -= 1.0 * attackSign;
        }
      }

      // 2. Lateral Width & Compactness
      let widthScale = 1.0;
      if (widthSetting === "wide") {
        widthScale = 1.14;
      } else if (widthSetting === "narrow" || widthSetting === "compact") {
        widthScale = 0.86;
      }

      let px = p.position3D[0] + depthOffsetM;
      let pz = p.position3D[2] * widthScale;

      // 3. Pressing Intensity & Off-Ball Runs (Counter / Build-from-Back readability)
      const isDefendingTeam = p.side !== state.possession_side;
      if (isDefendingTeam && (pressSetting === "high" || pressSetting === "intense" || (state.pressure_index ?? 0) >= 0.65)) {
        const distToBall = Math.hypot(ballX - px, ballZ - pz);
        if (distToBall > 2.2 && distToBall < 18.5) {
          const pull = pressSetting === "high" || pressSetting === "intense" ? 0.18 : 0.1;
          px += (ballX - px) * pull;
          pz += (ballZ - pz) * pull;
          p.speed_ratio = Math.min(1, p.speed_ratio + 0.12);
          p.tactical_instruction_marker = "high_press";
        }
      } else if (!isDefendingTeam) {
        const rawTempo = isHome ? tactics.homeTempo : tactics.awayTempo;
        const fastTempo =
          (typeof rawTempo === "number" && rawTempo >= 70) ||
          String(rawTempo || "").toLowerCase() === "fast" ||
          Boolean(state.transition_state?.includes("counter") || state.transition_state?.includes("break"));
        const slowTempo =
          (typeof rawTempo === "number" && rawTempo <= 30) ||
          String(rawTempo || "").toLowerCase() === "slow";
        if (fastTempo && isAttacker) {
          px += 2.2 * attackSign;
          p.tactical_instruction_marker = "channel_run";
        } else if (slowTempo && state.possession_phase === "build_up" && !isDefender && !isAttacker) {
          px -= 1.2 * attackSign;
          p.tactical_instruction_marker = "build_up_pivot";
        }
      }

      p.position3D[0] = Math.max(PITCH_BOUNDS.minX + 1.5, Math.min(PITCH_BOUNDS.maxX - 1.5, px));
      p.position3D[2] = Math.max(PITCH_BOUNDS.minZ + 1.2, Math.min(PITCH_BOUNDS.maxZ - 1.2, pz));
    }
  }

  private playerToInterpolated(
    p: SpectatorSafePlayerTelemetry,
    homeAttacksRight: boolean
  ): InterpolatedPlayerState {
    const p3d = pitchTo3D(p.position, 0, homeAttacksRight);
    let angle = 0;
    if (p.facing) {
      angle = Math.atan2(p.facing.y, p.facing.x);
    } else if (p.velocity) {
      angle = Math.atan2(p.velocity.y, p.velocity.x);
    }
    return {
      player_id: p.player_id,
      team_id: p.team_id,
      side: p.side,
      shirt_number: p.shirt_number,
      label: p.label,
      role: p.role,
      line: p.line,
      state: p.state || "idle",
      active: p.active !== false,
      highlighted: Boolean(p.highlighted),
      position3D: p3d,
      facingAngleRad: angle,
      animation_state: p.animation_state || "idle",
      speed_ratio: p.speed_ratio || 0,
      has_possession: Boolean(p.has_possession),
      angular_velocity_rad: 0,
      acceleration_ratio: 0,
      just_received_ball: false,
      stamina_pct: p.stamina_pct,
    };
  }

  private frameToInterpolated(frame: SpectatorSafeFrameView): InterpolatedPlayerState["position3D"] extends unknown ? InterpolatedMatchState : never {
    const ball3D = pitchTo3D(frame.ball.position, frame.ball.height, frame.home_attacks_right);
    return {
      time_seconds: frame.time_seconds,
      clock_minute: frame.clock_minute,
      phase: frame.phase,
      stage: frame.stage || "event",
      home_score: frame.home_score,
      away_score: frame.away_score,
      home_attacks_right: frame.home_attacks_right,
      possession_side: frame.possession_side,
      camera_preset: frame.camera_preset,
      active_event_id: frame.active_event_id,
      event_banner: frame.event_banner,
      celebration_team_id: frame.celebration_team_id,
      possession_phase: frame.possession_phase,
      transition_state: frame.transition_state,
      danger_zone: frame.danger_zone,
      pressure_index: frame.pressure_index,
      frame_tags: frame.frame_tags,
      players: frame.players.map((p) => this.playerToInterpolated(p, frame.home_attacks_right)),
      ball: {
        position3D: ball3D,
        height: ball3D[1],
        state: frame.ball.state,
        owner_player_id: frame.ball.owner_player_id,
        velocity: frame.ball.velocity
          ? [frame.ball.velocity.x, frame.ball.velocity.y, frame.ball.velocity.z]
          : undefined,
        spin: frame.ball.spin
          ? [frame.ball.spin.x, frame.ball.spin.y, frame.ball.spin.z]
          : undefined,
      },
    };
  }
}
