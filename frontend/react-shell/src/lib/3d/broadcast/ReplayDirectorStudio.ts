/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Cinematic Action Replay Director, Rolling 22-Player Spatial Buffer & Tactical Freeze-Frame Studio.
 *
 * Implements FM/TV-grade broadcast slow-motion multi-angle replay cinematography:
 * 1. Rolling spatial transform ring buffer (`ReplaySpatialFrame`) retaining the ball
 *    and all 22 players so replays reconstruct the actual historical spatial sequence.
 * 2. Auto-selected primary replay angle + two curated alternate angles for every
 *    goal, major save, red card, and VAR event.
 * 3. Tactical freeze-frame snapshot (`TacticalFreezeFrame`) with pass lane,
 *    offside line X, xG/shot map vector, and defensive-shape polygon.
 * 4. Five broadcast camera angles: "orbit_360", "reverse_angle_pov",
 *    "spidercam_overhead", "goal_line_freeze", and "wirecam_tracking".
 */

import * as THREE from "three";
import { CameraPose } from "./CameraDirector";
import { InterpolatedBallState, InterpolatedPlayerState } from "./SpatialInterpolator";

export type ReplayStudioAngle =
  | "orbit_360"
  | "reverse_angle_pov"
  | "spidercam_overhead"
  | "goal_line_freeze"
  | "wirecam_tracking";

export interface ReplayPlayerTransform {
  player_id: string;
  side: "home" | "away";
  role: string;
  shirt_number?: number;
  label?: string;
  position3D: [number, number, number];
  facingAngleRad: number;
  animation_state: string;
  speed_ratio: number;
  has_possession: boolean;
}

export interface ReplaySpatialFrame {
  timestampSec: number;
  clockMinute: number;
  possessionSide: "home" | "away";
  ball: {
    position3D: [number, number, number];
    height: number;
    state: string;
    velocity?: [number, number, number];
    spin?: [number, number, number];
    owner_player_id?: string | null;
  };
  players: ReplayPlayerTransform[];
}

export interface TacticalFreezeFrame {
  timestampSec: number;
  offsideLineX: number;
  passLane: {
    from: [number, number, number];
    to: [number, number, number];
    recipientId: string | null;
  } | null;
  shotVector: {
    origin: [number, number, number];
    targetGoalMouth: [number, number, number];
    estimatedXg: number;
  } | null;
  defensiveShapePolygon: Array<[number, number, number]>;
}

export interface ReplayEventBookmark {
  eventId: string;
  eventType: string;
  timestampSec: number;
  clockMinute: number;
  ballPosition: [number, number, number];
  primaryActorPosition?: [number, number, number] | null;
  primaryActorName?: string;
  recommendedAngle: ReplayStudioAngle;
  alternateAngles?: [ReplayStudioAngle, ReplayStudioAngle];
  freezeFrame?: TacticalFreezeFrame | null;
  summaryText: string;
}

export interface ReplayDirectorStudioOptions {
  initialAngle?: ReplayStudioAngle;
  playbackRate?: number;
  maxSpatialFrames?: number;
}

export interface ReplayStudioSummary {
  activeAngle: ReplayStudioAngle;
  alternateAngles: [ReplayStudioAngle, ReplayStudioAngle];
  playbackRate: number;
  isReplayActive: boolean;
  totalBookmarks: number;
  latestBookmark: ReplayEventBookmark | null;
  orbitAngleDeg: number;
  bufferedSpatialFrames: number;
  hasTacticalFreezeFrame: boolean;
}

export class ReplayDirectorStudio {
  private activeAngle: ReplayStudioAngle = "orbit_360";
  private alternateAngles: [ReplayStudioAngle, ReplayStudioAngle] = [
    "reverse_angle_pov",
    "spidercam_overhead",
  ];
  private playbackRate: number = 0.45;
  private isReplayActive: boolean = false;
  private orbitAngleRad: number = 0;
  private bookmarks: ReplayEventBookmark[] = [];
  private readonly maxBookmarks: number = 16;

  // Rolling spatial transform ring buffer for ball + 22 players
  private spatialBuffer: ReplaySpatialFrame[] = [];
  private readonly maxSpatialFrames: number;
  private activeReplaySlice: ReplaySpatialFrame[] = [];
  private latestFreezeFrame: TacticalFreezeFrame | null = null;

  // Scratch objects for zero per-frame garbage
  private scratchTargetPos = new THREE.Vector3();
  private scratchCamPos = new THREE.Vector3();

  constructor(options?: ReplayDirectorStudioOptions) {
    if (options?.initialAngle) {
      this.activeAngle = options.initialAngle;
    }
    if (typeof options?.playbackRate === "number") {
      this.playbackRate = options.playbackRate;
    }
    this.maxSpatialFrames = options?.maxSpatialFrames ?? 300;
  }

  public setReplayAngle(angle: ReplayStudioAngle): void {
    this.activeAngle = angle;
  }

  public getReplayAngle(): ReplayStudioAngle {
    return this.activeAngle;
  }

  public getAlternateAngles(): [ReplayStudioAngle, ReplayStudioAngle] {
    return [...this.alternateAngles];
  }

  /**
   * Selects one primary replay angle and two alternate angles for a dramatic match event.
   */
  public selectAnglesForEvent(eventType: string): {
    primaryAngle: ReplayStudioAngle;
    alternateAngles: [ReplayStudioAngle, ReplayStudioAngle];
  } {
    const normalized = (eventType || "").trim().toLowerCase();
    if (normalized === "goal" || normalized === "penalty") {
      return {
        primaryAngle: "reverse_angle_pov",
        alternateAngles: ["spidercam_overhead", "orbit_360"],
      };
    }
    if (normalized === "save" || normalized === "major_save" || normalized === "woodwork") {
      return {
        primaryAngle: "goal_line_freeze",
        alternateAngles: ["reverse_angle_pov", "spidercam_overhead"],
      };
    }
    if (normalized === "var" || normalized === "offside") {
      return {
        primaryAngle: "goal_line_freeze",
        alternateAngles: ["wirecam_tracking", "spidercam_overhead"],
      };
    }
    if (normalized === "red_card" || normalized === "foul") {
      return {
        primaryAngle: "orbit_360",
        alternateAngles: ["wirecam_tracking", "spidercam_overhead"],
      };
    }
    return {
      primaryAngle: "orbit_360",
      alternateAngles: ["reverse_angle_pov", "spidercam_overhead"],
    };
  }

  public setPlaybackRate(rate: number): void {
    this.playbackRate = Math.max(0.1, Math.min(1.5, rate));
  }

  public getPlaybackRate(): number {
    return this.playbackRate;
  }

  public setReplayActive(active: boolean): void {
    this.isReplayActive = active;
    if (active) {
      this.orbitAngleRad = 0;
      if (this.activeReplaySlice.length === 0 && this.spatialBuffer.length > 0) {
        this.activeReplaySlice = this.spatialBuffer.slice(-Math.min(120, this.spatialBuffer.length));
      }
    }
  }

  public getIsReplayActive(): boolean {
    return this.isReplayActive;
  }

  /**
   * Appends a spatial snapshot of the ball and all 22 players into the rolling ring buffer.
   */
  public recordSpatialFrame(frame: {
    timestampSec: number;
    clockMinute: number;
    possessionSide?: "home" | "away";
    ball: InterpolatedBallState;
    players: InterpolatedPlayerState[];
  }): void {
    const last = this.spatialBuffer[this.spatialBuffer.length - 1];
    if (last && Math.abs(frame.timestampSec - last.timestampSec) < 0.015) {
      return;
    }

    const snapshot: ReplaySpatialFrame = {
      timestampSec: frame.timestampSec,
      clockMinute: frame.clockMinute,
      possessionSide: frame.possessionSide || "home",
      ball: {
        position3D: [...frame.ball.position3D],
        height: frame.ball.height,
        state: frame.ball.state,
        velocity: frame.ball.velocity ? [...frame.ball.velocity] : undefined,
        spin: frame.ball.spin ? [...frame.ball.spin] : undefined,
        owner_player_id: frame.ball.owner_player_id,
      },
      players: frame.players.map((p) => ({
        player_id: p.player_id,
        side: p.side,
        role: p.role,
        shirt_number: p.shirt_number,
        label: p.label,
        position3D: [...p.position3D],
        facingAngleRad: p.facingAngleRad,
        animation_state: p.animation_state,
        speed_ratio: p.speed_ratio,
        has_possession: p.has_possession,
      })),
    };

    this.spatialBuffer.push(snapshot);
    if (this.spatialBuffer.length > this.maxSpatialFrames) {
      this.spatialBuffer.shift();
    }
  }

  public getSpatialBufferLength(): number {
    return this.spatialBuffer.length;
  }

  /**
   * Samples and interpolates the historical ball + 22-player spatial sequence at progressRatio [0..1].
   */
  public sampleReplayFrame(progressRatio: number): ReplaySpatialFrame | null {
    const source = this.activeReplaySlice.length > 0 ? this.activeReplaySlice : this.spatialBuffer;
    if (source.length === 0) return null;
    if (source.length === 1) return source[0];

    const clamped = Math.max(0, Math.min(1, progressRatio));
    const exactIndex = clamped * (source.length - 1);
    const idxA = Math.floor(exactIndex);
    const idxB = Math.min(source.length - 1, idxA + 1);
    const alpha = exactIndex - idxA;

    const frameA = source[idxA];
    const frameB = source[idxB];
    if (idxA === idxB || alpha <= 0.001) return frameA;

    const mapB = new Map<string, ReplayPlayerTransform>();
    for (const p of frameB.players) {
      mapB.set(p.player_id, p);
    }

    const players: ReplayPlayerTransform[] = frameA.players.map((pA) => {
      const pB = mapB.get(pA.player_id);
      if (!pB) return pA;
      return {
        ...pA,
        position3D: [
          pA.position3D[0] + (pB.position3D[0] - pA.position3D[0]) * alpha,
          pA.position3D[1] + (pB.position3D[1] - pA.position3D[1]) * alpha,
          pA.position3D[2] + (pB.position3D[2] - pA.position3D[2]) * alpha,
        ],
        facingAngleRad: pA.facingAngleRad + (pB.facingAngleRad - pA.facingAngleRad) * alpha,
        animation_state: alpha >= 0.5 ? pB.animation_state : pA.animation_state,
        speed_ratio: pA.speed_ratio + (pB.speed_ratio - pA.speed_ratio) * alpha,
        has_possession: alpha >= 0.5 ? pB.has_possession : pA.has_possession,
      };
    });

    return {
      timestampSec: frameA.timestampSec + (frameB.timestampSec - frameA.timestampSec) * alpha,
      clockMinute: alpha >= 0.5 ? frameB.clockMinute : frameA.clockMinute,
      possessionSide: alpha >= 0.5 ? frameB.possessionSide : frameA.possessionSide,
      ball: {
        position3D: [
          frameA.ball.position3D[0] + (frameB.ball.position3D[0] - frameA.ball.position3D[0]) * alpha,
          frameA.ball.position3D[1] + (frameB.ball.position3D[1] - frameA.ball.position3D[1]) * alpha,
          frameA.ball.position3D[2] + (frameB.ball.position3D[2] - frameA.ball.position3D[2]) * alpha,
        ],
        height: frameA.ball.height + (frameB.ball.height - frameA.ball.height) * alpha,
        state: alpha >= 0.5 ? frameB.ball.state : frameA.ball.state,
        velocity: frameB.ball.velocity || frameA.ball.velocity,
        spin: frameB.ball.spin || frameA.ball.spin,
        owner_player_id: alpha >= 0.5 ? frameB.ball.owner_player_id : frameA.ball.owner_player_id,
      },
      players,
    };
  }

  /**
   * Builds a tactical freeze-frame overlay containing pass lane, offside line X,
   * xG/shot vector, and defending backline shape polygon.
   */
  public computeTacticalFreezeFrame(frame?: ReplaySpatialFrame | null): TacticalFreezeFrame | null {
    const targetFrame =
      frame ||
      (this.spatialBuffer.length > 0 ? this.spatialBuffer[this.spatialBuffer.length - 1] : null);
    if (!targetFrame) return null;

    const attackingSide = targetFrame.possessionSide;
    const defendingPlayers = targetFrame.players.filter(
      (p) => p.side !== attackingSide && p.role.toUpperCase() !== "GK"
    );

    const defPolygons: Array<[number, number, number]> = defendingPlayers
      .filter((p) => {
        const r = p.role.toUpperCase();
        return r.includes("DEF") || r.includes("CB") || r.includes("B");
      })
      .sort((a, b) => a.position3D[2] - b.position3D[2])
      .map((p) => [...p.position3D]);

    let offsideLineX = attackingSide === "home" ? 28.0 : -28.0;
    if (defPolygons.length > 0) {
      const sumX = defPolygons.reduce((acc, pt) => acc + pt[0], 0);
      offsideLineX = Number((sumX / defPolygons.length).toFixed(2));
    }

    const carrier =
      targetFrame.players.find(
        (p) => p.has_possession || p.player_id === targetFrame.ball.owner_player_id
      ) || null;

    let passLane: TacticalFreezeFrame["passLane"] = null;
    if (carrier) {
      const nearestTeammate = targetFrame.players
        .filter(
          (p) =>
            p.side === carrier.side &&
            p.player_id !== carrier.player_id &&
            p.role.toUpperCase() !== "GK"
        )
        .sort((a, b) => {
          const da = Math.hypot(
            a.position3D[0] - carrier.position3D[0],
            a.position3D[2] - carrier.position3D[2]
          );
          const db = Math.hypot(
            b.position3D[0] - carrier.position3D[0],
            b.position3D[2] - carrier.position3D[2]
          );
          return da - db;
        })[0];
      if (nearestTeammate) {
        passLane = {
          from: [...carrier.position3D],
          to: [...nearestTeammate.position3D],
          recipientId: nearestTeammate.player_id,
        };
      }
    }

    const bx = targetFrame.ball.position3D[0];
    const bz = targetFrame.ball.position3D[2];
    const goalX = bx >= 0 ? 52.5 : -52.5;
    const distToGoal = Math.max(1.0, Math.hypot(goalX - bx, 0 - bz));
    const angleFactor = Math.max(0.15, 1 - Math.abs(bz) / 36);
    const estimatedXg = Number(
      Math.max(0.02, Math.min(0.92, Math.exp(-distToGoal * 0.085) * angleFactor)).toFixed(2)
    );

    const freeze: TacticalFreezeFrame = {
      timestampSec: targetFrame.timestampSec,
      offsideLineX,
      passLane,
      shotVector: {
        origin: [...targetFrame.ball.position3D],
        targetGoalMouth: [goalX, 1.2, Math.max(-3.2, Math.min(3.2, bz * 0.25))],
        estimatedXg,
      },
      defensiveShapePolygon: defPolygons,
    };
    this.latestFreezeFrame = freeze;
    return freeze;
  }

  public getLatestFreezeFrame(): TacticalFreezeFrame | null {
    return this.latestFreezeFrame;
  }

  /**
   * Records a key match event bookmark into the replay buffer, freezing the rolling
   * spatial slice and auto-selecting primary + two alternate camera angles.
   */
  public recordBookmark(bookmark: ReplayEventBookmark): void {
    const selection = this.selectAnglesForEvent(bookmark.eventType);
    const primary = bookmark.recommendedAngle || selection.primaryAngle;
    const alternates = bookmark.alternateAngles || selection.alternateAngles;
    this.activeAngle = primary;
    this.alternateAngles = alternates;

    if (this.spatialBuffer.length > 0) {
      this.activeReplaySlice = this.spatialBuffer.slice(-Math.min(120, this.spatialBuffer.length));
    }
    const freezeFrame = bookmark.freezeFrame ?? this.computeTacticalFreezeFrame();

    this.bookmarks.push({
      ...bookmark,
      recommendedAngle: primary,
      alternateAngles: alternates,
      freezeFrame,
    });
    if (this.bookmarks.length > this.maxBookmarks) {
      this.bookmarks.shift();
    }
  }

  public getBookmarks(): readonly ReplayEventBookmark[] {
    return this.bookmarks;
  }

  public getLatestBookmark(): ReplayEventBookmark | null {
    return this.bookmarks.length > 0 ? this.bookmarks[this.bookmarks.length - 1] : null;
  }

  /**
   * Computes a TV broadcast camera pose for the active replay angle.
   */
  public computeReplayPose(
    deltaSec: number,
    progressRatio: number, // 0.0 at replay start to 1.0 at replay end
    ballPos3D: [number, number, number],
    actorPos3D?: [number, number, number] | null
  ): CameraPose {
    const sampled = this.isReplayActive ? this.sampleReplayFrame(progressRatio) : null;
    const effectiveBall = sampled ? sampled.ball.position3D : ballPos3D;

    const focusX = actorPos3D ? actorPos3D[0] : effectiveBall[0];
    const focusY = actorPos3D ? Math.max(0.8, actorPos3D[1]) : Math.max(0.4, effectiveBall[1]);
    const focusZ = actorPos3D ? actorPos3D[2] : effectiveBall[2];

    this.scratchTargetPos.set(focusX, focusY, focusZ);

    switch (this.activeAngle) {
      case "orbit_360": {
        this.orbitAngleRad += deltaSec * 1.8 * this.playbackRate;
        const orbitRadius = 8.5;
        const camX = focusX + Math.cos(this.orbitAngleRad) * orbitRadius;
        const camY = Math.max(2.5, focusY + 2.2 + Math.sin(this.orbitAngleRad * 0.5) * 0.8);
        const camZ = focusZ + Math.sin(this.orbitAngleRad) * orbitRadius;
        this.scratchCamPos.set(camX, camY, camZ);
        return {
          position: [camX, camY, camZ],
          target: [focusX, focusY + 0.9, focusZ],
          fov: 34,
        };
      }

      case "reverse_angle_pov": {
        const goalEnd = focusX >= 0 ? 55.5 : -55.5;
        const lookDir = focusX >= 0 ? -1 : 1;
        const camX = goalEnd + lookDir * 1.5;
        const camY = 1.95;
        const camZ = Math.max(-10, Math.min(10, focusZ * 0.65));
        return {
          position: [camX, camY, camZ],
          target: [focusX, focusY + 0.6, focusZ],
          fov: 32,
        };
      }

      case "spidercam_overhead": {
        const altitude = 20.0 - Math.sin(progressRatio * Math.PI) * 11.0;
        const offsetX = Math.cos(progressRatio * 2.2) * 4.5;
        const offsetZ = 12.0 - progressRatio * 6.0;
        return {
          position: [focusX + offsetX, altitude, focusZ + offsetZ],
          target: [focusX, 0.4, focusZ],
          fov: 44,
        };
      }

      case "goal_line_freeze": {
        const lineX = focusX >= 0 ? 52.5 : -52.5;
        const camZ = focusZ >= 0 ? 35.8 : -35.8;
        return {
          position: [lineX, 2.2, camZ],
          target: [lineX, 1.2, focusZ],
          fov: 24,
        };
      }

      case "wirecam_tracking": {
        const touchlineZ = 36.2;
        const leadX = focusX + 2.5;
        return {
          position: [leadX, 4.2, touchlineZ],
          target: [focusX, focusY + 0.7, focusZ],
          fov: 36,
        };
      }

      default: {
        return {
          position: [focusX, 12, focusZ + 20],
          target: [focusX, focusY, focusZ],
          fov: 38,
        };
      }
    }
  }

  public getSummary(): ReplayStudioSummary {
    return {
      activeAngle: this.activeAngle,
      alternateAngles: [...this.alternateAngles],
      playbackRate: this.playbackRate,
      isReplayActive: this.isReplayActive,
      totalBookmarks: this.bookmarks.length,
      latestBookmark: this.getLatestBookmark(),
      orbitAngleDeg: Number((((this.orbitAngleRad * 180) / Math.PI) % 360).toFixed(1)),
      bufferedSpatialFrames: this.spatialBuffer.length,
      hasTacticalFreezeFrame: Boolean(this.latestFreezeFrame),
    };
  }

  public dispose(): void {
    this.bookmarks = [];
    this.spatialBuffer = [];
    this.activeReplaySlice = [];
    this.latestFreezeFrame = null;
    this.isReplayActive = false;
  }
}
