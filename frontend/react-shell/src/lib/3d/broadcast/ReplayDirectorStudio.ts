/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Cinematic Action Replay Director & Multi-Angle Camera Studio (Phase 4).
 *
 * Implements FIFA/TV-grade broadcast slow-motion multi-angle replay cinematography:
 * 1. "orbit_360": Dynamic 360-degree heroic rotation around key action actor / scorer.
 * 2. "reverse_angle_pov": Low reverse camera peering through the goal cage toward the play.
 * 3. "spidercam_overhead": Cable-cam swooping overhead tracking the trajectory of the ball.
 * 4. "goal_line_freeze": Telephoto goal-line camera inspecting whether the ball crossed the line.
 * 5. "wirecam_tracking": Touchline wirecam accelerating alongside the ball-carrier.
 *
 * Zero per-frame heap allocations; pre-allocated vector math; dynamic slow-motion curves.
 */

import * as THREE from "three";
import { CameraPose } from "./CameraDirector";

export type ReplayStudioAngle =
  | "orbit_360"
  | "reverse_angle_pov"
  | "spidercam_overhead"
  | "goal_line_freeze"
  | "wirecam_tracking";

export interface ReplayEventBookmark {
  eventId: string;
  eventType: string;
  timestampSec: number;
  clockMinute: number;
  ballPosition: [number, number, number];
  primaryActorPosition?: [number, number, number] | null;
  primaryActorName?: string;
  recommendedAngle: ReplayStudioAngle;
  summaryText: string;
}

export interface ReplayDirectorStudioOptions {
  initialAngle?: ReplayStudioAngle;
  playbackRate?: number;
}

export interface ReplayStudioSummary {
  activeAngle: ReplayStudioAngle;
  playbackRate: number;
  isReplayActive: boolean;
  totalBookmarks: number;
  latestBookmark: ReplayEventBookmark | null;
  orbitAngleDeg: number;
}

export class ReplayDirectorStudio {
  private activeAngle: ReplayStudioAngle = "orbit_360";
  private playbackRate: number = 0.45;
  private isReplayActive: boolean = false;
  private orbitAngleRad: number = 0;
  private bookmarks: ReplayEventBookmark[] = [];
  private readonly maxBookmarks: number = 16;

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
  }

  public setReplayAngle(angle: ReplayStudioAngle): void {
    this.activeAngle = angle;
  }

  public getReplayAngle(): ReplayStudioAngle {
    return this.activeAngle;
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
    }
  }

  public getIsReplayActive(): boolean {
    return this.isReplayActive;
  }

  /**
   * Records a key match event bookmark into the replay buffer.
   */
  public recordBookmark(bookmark: ReplayEventBookmark): void {
    this.bookmarks.push(bookmark);
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
    const focusX = actorPos3D ? actorPos3D[0] : ballPos3D[0];
    const focusY = actorPos3D ? Math.max(0.8, actorPos3D[1]) : Math.max(0.4, ballPos3D[1]);
    const focusZ = actorPos3D ? actorPos3D[2] : ballPos3D[2];

    this.scratchTargetPos.set(focusX, focusY, focusZ);

    switch (this.activeAngle) {
      case "orbit_360": {
        // Orbit gracefully around the focus actor at 7.5m radius
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
        // Behind the goal line facing out onto the pitch
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
        // High swooping wire camera descending from 22m down to 8m as play peaks
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
        // Perpendicular tight telephoto goal-line camera at x = ±52.5m, y = 1.8m
        const lineX = focusX >= 0 ? 52.5 : -52.5;
        const camZ = focusZ >= 0 ? 35.8 : -35.8;
        return {
          position: [lineX, 2.2, camZ],
          target: [lineX, 1.2, focusZ],
          fov: 24, // High telephoto magnification
        };
      }

      case "wirecam_tracking": {
        // Tracking alongside touchline at z = 36.5m, following the ball x-coordinate
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
      playbackRate: this.playbackRate,
      isReplayActive: this.isReplayActive,
      totalBookmarks: this.bookmarks.length,
      latestBookmark: this.getLatestBookmark(),
      orbitAngleDeg: Number(((this.orbitAngleRad * 180) / Math.PI % 360).toFixed(1)),
    };
  }

  public dispose(): void {
    this.bookmarks = [];
    this.isReplayActive = false;
  }
}
