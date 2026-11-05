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
  stamina_pct?: number;
}

export interface InterpolatedBallState {
  position3D: [number, number, number]; // [X, Y, Z] in meters
  height: number;
  state: string;
  owner_player_id?: string | null;
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
  frame_tags?: string[];
  players: InterpolatedPlayerState[];
  ball: InterpolatedBallState;
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

  constructor(initialFrames: SpectatorSafeFrameView[] = []) {
    this.setFrames(initialFrames);
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

    // Limit buffer to recent 600 frames (~10 minutes at 1 tick/sec)
    if (this.frames.length > 600) {
      this.frames.splice(0, this.frames.length - 600);
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
  public interpolate(queryTimeSeconds: number): InterpolatedMatchState | null {
    if (this.frames.length === 0) return null;

    const firstFrame = this.frames[0];
    const lastFrame = this.frames[this.frames.length - 1];

    // Boundary clamping: NO extrapolation beyond known authoritative bounds
    if (queryTimeSeconds <= firstFrame.time_seconds) {
      return this.frameToInterpolated(firstFrame);
    }
    if (queryTimeSeconds >= lastFrame.time_seconds) {
      return this.frameToInterpolated(lastFrame);
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

    // Handle large network drop or pause gap (> 2.5s)
    if (duration > 2.5) {
      return this.frameToInterpolated(queryTimeSeconds >= frameB.time_seconds - 0.5 ? frameB : frameA);
    }

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
        stamina_pct: pB.stamina_pct ?? pA.stamina_pct,
      });
    }

    // Personal-space collision avoidance pass: prevent humanoid player meshes from clipping through each other
    const MIN_SEPARATION_M = 0.78;
    for (let iter = 0; iter < 2; iter++) {
      for (let i = 0; i < interpolatedPlayers.length; i++) {
        const pi = interpolatedPlayers[i];
        if (pi.active === false) continue;
        for (let j = i + 1; j < interpolatedPlayers.length; j++) {
          const pj = interpolatedPlayers[j];
          if (pj.active === false) continue;
          const dx = pj.position3D[0] - pi.position3D[0];
          const dz = pj.position3D[2] - pi.position3D[2];
          const dist = Math.hypot(dx, dz);
          if (dist < MIN_SEPARATION_M) {
            const overlap = (MIN_SEPARATION_M - dist) * 0.5;
            const nx = dist > 0.001 ? dx / dist : Math.cos((i + j) * 1.1);
            const nz = dist > 0.001 ? dz / dist : Math.sin((i + j) * 1.1);
            pi.position3D[0] = Math.max(PITCH_BOUNDS.minX, Math.min(PITCH_BOUNDS.maxX, pi.position3D[0] - nx * overlap));
            pi.position3D[2] = Math.max(PITCH_BOUNDS.minZ, Math.min(PITCH_BOUNDS.maxZ, pi.position3D[2] - nz * overlap));
            pj.position3D[0] = Math.max(PITCH_BOUNDS.minX, Math.min(PITCH_BOUNDS.maxX, pj.position3D[0] + nx * overlap));
            pj.position3D[2] = Math.max(PITCH_BOUNDS.minZ, Math.min(PITCH_BOUNDS.maxZ, pj.position3D[2] + nz * overlap));
          }
        }
      }
    }

    return {
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
      frame_tags: activeFrame.frame_tags,
      players: interpolatedPlayers,
      ball: {
        position3D: [ballX, ballY, ballZ],
        height: ballY,
        state: activeFrame.ball.state,
        owner_player_id: activeFrame.ball.owner_player_id,
        velocity: activeFrame.ball.velocity
          ? [activeFrame.ball.velocity.x, activeFrame.ball.velocity.y, activeFrame.ball.velocity.z]
          : undefined,
        spin: activeFrame.ball.spin
          ? [activeFrame.ball.spin.x, activeFrame.ball.spin.y, activeFrame.ball.spin.z]
          : undefined,
      },
    };
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

  private frameToInterpolated(frame: SpectatorSafeFrameView): InterpolatedMatchState {
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
