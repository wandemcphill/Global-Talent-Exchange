/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast (Phase 3)
 * BroadcastTacticalAROverlay: On-Pitch 3D Broadcast Augmented Reality (AR)
 * & Telestrator Overlays.
 *
 * Implements:
 * 1. Five canonical AR overlay modes (`BroadcastAROverlayMode`):
 *    - `"off"`: Clean television pitch presentation (auto-reveals Offside Wall during VAR/Offside events).
 *    - `"tactical_lines"`: 3D Home & Away Defensive Block Laser Lines + Ball-Carrier Passing Lane Vectors.
 *    - `"offside_wall"`: Translucent 3D Offside Virtual Curtain & Turf Laser Line across the 68m pitch width.
 *    - `"shot_trails"`: 3D Ballistic Flight Ribbon tracing ball trajectory + Ball-Carrier Territory Ring.
 *    - `"full_ar"`: All 3D broadcast telestrator layers active simultaneously.
 * 2. Zero Per-Frame Heap Allocation:
 *    - Pre-allocates all `Float32Array` geometry vertex buffers once in constructor and updates in-place.
 */

import * as THREE from "three";
import { FIFA_PITCH_DIMENSIONS } from "./matchCoordinates";
import { InterpolatedPlayerState } from "./SpatialInterpolator";

export type BroadcastAROverlayMode =
  | "off"
  | "tactical_lines"
  | "offside_wall"
  | "shot_trails"
  | "full_ar";

export const ALL_BROADCAST_AR_MODES: readonly BroadcastAROverlayMode[] = [
  "off",
  "tactical_lines",
  "offside_wall",
  "shot_trails",
  "full_ar",
] as const;

export interface BroadcastAROverlaySummary {
  mode: BroadcastAROverlayMode;
  isVisible: boolean;
  homeDefensiveLineX: number;
  awayDefensiveLineX: number;
  activeOffsideLineX: number;
  activePassingLaneCount: number;
  shotTrailSampleCount: number;
  activePassRecipientId?: string | null;
  activeTacticalInstruction?: string | null;
}

export interface BroadcastAROverlayOptions {
  initialMode?: BroadcastAROverlayMode;
  homeColorHex?: string;
  awayColorHex?: string;
}

const MAX_DEF_LINE_POINTS = 6;
const MAX_PASS_LANES = 3;
const MAX_TRAIL_POINTS = 24;

export class BroadcastTacticalAROverlay {
  public readonly group: THREE.Group;

  private mode: BroadcastAROverlayMode;
  private eventOffsideFlashTimerSec: number = 0;

  // 1. Defensive Line Laser Buffers (Home & Away)
  private homeDefLineGeo: THREE.BufferGeometry;
  private homeDefLinePositions: Float32Array;
  private homeDefLineMesh: THREE.Line;

  private awayDefLineGeo: THREE.BufferGeometry;
  private awayDefLinePositions: Float32Array;
  private awayDefLineMesh: THREE.Line;

  // 2. Ball-Carrier Passing Lanes (Up to 3 rays = 6 vertices)
  private passLanesGeo: THREE.BufferGeometry;
  private passLanesPositions: Float32Array;
  private passLanesMesh: THREE.LineSegments;

  // 3. 3D Offside Virtual Curtain & Turf Line
  private offsideGroup: THREE.Group;
  private offsideWallMesh: THREE.Mesh;
  private offsideFloorLineMesh: THREE.Mesh;

  // 4. 3D Ballistic Shot / Pass Trail Ribbon + Carrier Ring
  private ballTrailGeo: THREE.BufferGeometry;
  private ballTrailPositions: Float32Array;
  private ballTrailMesh: THREE.Line;
  private ballTrailHistory: Array<[number, number, number]> = [];
  private carrierRingMesh: THREE.Mesh;
  private recipientRingMesh: THREE.Mesh;
  private instructionRingMesh: THREE.Mesh;

  // Telemetry state
  private homeDefensiveLineX: number = -28.0;
  private awayDefensiveLineX: number = 28.0;
  private activeOffsideLineX: number = 28.0;
  private activePassingLaneCount: number = 0;
  private activePassRecipientId: string | null = null;
  private activeTacticalInstruction: string | null = null;

  private disposables: Array<{ dispose: () => void }> = [];

  constructor(scene: THREE.Scene, options: BroadcastAROverlayOptions = {}) {
    this.mode = options.initialMode || "off";

    this.group = new THREE.Group();
    this.group.name = "Phase3BroadcastTacticalAROverlayGroup";
    scene.add(this.group);

    const homeColor = new THREE.Color(options.homeColorHex || "#10b981");
    const awayColor = new THREE.Color(options.awayColorHex || "#38bdf8");

    // 1. Home & Away Defensive Block Laser Lines
    this.homeDefLinePositions = new Float32Array(MAX_DEF_LINE_POINTS * 3);
    this.homeDefLineGeo = new THREE.BufferGeometry();
    this.homeDefLineGeo.setAttribute(
      "position",
      new THREE.BufferAttribute(this.homeDefLinePositions, 3)
    );
    const homeDefMat = new THREE.LineBasicMaterial({
      color: homeColor,
      transparent: true,
      opacity: 0.85,
    });
    this.disposables.push(this.homeDefLineGeo, homeDefMat);
    this.homeDefLineMesh = new THREE.Line(this.homeDefLineGeo, homeDefMat);
    this.homeDefLineMesh.frustumCulled = false;
    this.group.add(this.homeDefLineMesh);

    this.awayDefLinePositions = new Float32Array(MAX_DEF_LINE_POINTS * 3);
    this.awayDefLineGeo = new THREE.BufferGeometry();
    this.awayDefLineGeo.setAttribute(
      "position",
      new THREE.BufferAttribute(this.awayDefLinePositions, 3)
    );
    const awayDefMat = new THREE.LineBasicMaterial({
      color: awayColor,
      transparent: true,
      opacity: 0.85,
    });
    this.disposables.push(this.awayDefLineGeo, awayDefMat);
    this.awayDefLineMesh = new THREE.Line(this.awayDefLineGeo, awayDefMat);
    this.awayDefLineMesh.frustumCulled = false;
    this.group.add(this.awayDefLineMesh);

    // 2. Ball-Carrier Passing Lanes (3 lanes -> 6 vertices)
    this.passLanesPositions = new Float32Array(MAX_PASS_LANES * 2 * 3);
    this.passLanesGeo = new THREE.BufferGeometry();
    this.passLanesGeo.setAttribute(
      "position",
      new THREE.BufferAttribute(this.passLanesPositions, 3)
    );
    const passLanesMat = new THREE.LineBasicMaterial({
      color: 0xfacc15,
      transparent: true,
      opacity: 0.82,
    });
    this.disposables.push(this.passLanesGeo, passLanesMat);
    this.passLanesMesh = new THREE.LineSegments(this.passLanesGeo, passLanesMat);
    this.passLanesMesh.frustumCulled = false;
    this.group.add(this.passLanesMesh);

    // 3. 3D Offside Virtual Curtain & Turf Laser Strip
    this.offsideGroup = new THREE.Group();
    this.offsideGroup.name = "OffsideVirtualWallGroup";
    this.group.add(this.offsideGroup);

    const wallGeo = new THREE.PlaneGeometry(FIFA_PITCH_DIMENSIONS.width, 2.6);
    const wallMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.22,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const floorLineGeo = new THREE.PlaneGeometry(0.28, FIFA_PITCH_DIMENSIONS.width);
    const floorLineMat = new THREE.MeshBasicMaterial({
      color: 0x00f5d4,
      transparent: true,
      opacity: 0.9,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    this.disposables.push(wallGeo, wallMat, floorLineGeo, floorLineMat);

    this.offsideWallMesh = new THREE.Mesh(wallGeo, wallMat);
    this.offsideWallMesh.rotation.y = Math.PI / 2;
    this.offsideWallMesh.position.y = 1.3;
    this.offsideGroup.add(this.offsideWallMesh);

    this.offsideFloorLineMesh = new THREE.Mesh(floorLineGeo, floorLineMat);
    this.offsideFloorLineMesh.rotation.x = -Math.PI / 2;
    this.offsideFloorLineMesh.position.y = 0.045;
    this.offsideGroup.add(this.offsideFloorLineMesh);

    // 4. 3D Ballistic Shot / Pass Trail + Carrier Territory Ring
    this.ballTrailPositions = new Float32Array(MAX_TRAIL_POINTS * 3);
    this.ballTrailGeo = new THREE.BufferGeometry();
    this.ballTrailGeo.setAttribute(
      "position",
      new THREE.BufferAttribute(this.ballTrailPositions, 3)
    );
    const trailMat = new THREE.LineBasicMaterial({
      color: 0xf59e0b,
      transparent: true,
      opacity: 0.92,
    });
    const ringGeo = new THREE.RingGeometry(1.15, 1.45, 24);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x10b981,
      transparent: true,
      opacity: 0.7,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    this.disposables.push(this.ballTrailGeo, trailMat, ringGeo, ringMat);

    this.ballTrailMesh = new THREE.Line(this.ballTrailGeo, trailMat);
    this.ballTrailMesh.frustumCulled = false;
    this.group.add(this.ballTrailMesh);

    this.carrierRingMesh = new THREE.Mesh(ringGeo, ringMat);
    this.carrierRingMesh.rotation.x = -Math.PI / 2;
    this.carrierRingMesh.position.y = 0.04;
    this.group.add(this.carrierRingMesh);

    // 5. Subtle Pass Recipient & Tactical Instruction Readability Markers
    const recipientRingGeo = new THREE.RingGeometry(0.92, 1.16, 24);
    const recipientRingMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.58,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const instructionRingGeo = new THREE.RingGeometry(1.25, 1.48, 24);
    const instructionRingMat = new THREE.MeshBasicMaterial({
      color: 0xfacc15,
      transparent: true,
      opacity: 0.5,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    this.disposables.push(recipientRingGeo, recipientRingMat, instructionRingGeo, instructionRingMat);

    this.recipientRingMesh = new THREE.Mesh(recipientRingGeo, recipientRingMat);
    this.recipientRingMesh.rotation.x = -Math.PI / 2;
    this.recipientRingMesh.position.y = 0.042;
    this.recipientRingMesh.visible = false;
    this.group.add(this.recipientRingMesh);

    this.instructionRingMesh = new THREE.Mesh(instructionRingGeo, instructionRingMat);
    this.instructionRingMesh.rotation.x = -Math.PI / 2;
    this.instructionRingMesh.position.y = 0.038;
    this.instructionRingMesh.visible = false;
    this.group.add(this.instructionRingMesh);

    this.applyModeVisibility();
  }

  public setMode(mode: BroadcastAROverlayMode): void {
    this.mode = mode;
    this.applyModeVisibility();
  }

  public getMode(): BroadcastAROverlayMode {
    return this.mode;
  }

  /**
   * Automatically flashes the 3D Offside Virtual Wall for 4.5s on offside or VAR events.
   */
  public triggerEventFlash(eventType: string): void {
    const type = (eventType || "").toLowerCase();
    if (type.includes("offside") || type.includes("var")) {
      this.eventOffsideFlashTimerSec = 4.5;
      this.applyModeVisibility();
    }
  }

  private applyModeVisibility(): void {
    const showTactical = this.mode === "tactical_lines" || this.mode === "full_ar";
    const showOffside =
      this.mode === "offside_wall" ||
      this.mode === "full_ar" ||
      this.eventOffsideFlashTimerSec > 0;
    const showTrails = this.mode === "shot_trails" || this.mode === "full_ar";

    this.homeDefLineMesh.visible = showTactical;
    this.awayDefLineMesh.visible = showTactical;
    this.passLanesMesh.visible = showTactical;
    this.offsideGroup.visible = showOffside;
    this.ballTrailMesh.visible = showTrails;
    this.carrierRingMesh.visible = showTrails;
  }

  /**
   * Updates all 3D AR telestrator geometries in-place from the current interpolated frame.
   */
  public update(params: {
    deltaSec: number;
    players: InterpolatedPlayerState[];
    ballPosition3D: [number, number, number];
    possessionSide: "home" | "away" | null;
  }): void {
    const { deltaSec, players, ballPosition3D, possessionSide } = params;

    if (this.eventOffsideFlashTimerSec > 0) {
      this.eventOffsideFlashTimerSec = Math.max(0, this.eventOffsideFlashTimerSec - deltaSec);
      if (this.eventOffsideFlashTimerSec === 0) {
        this.applyModeVisibility();
      }
    }

    // 1. Update Ballistic Trail History
    this.ballTrailHistory.push([ballPosition3D[0], ballPosition3D[1] + 0.22, ballPosition3D[2]]);
    if (this.ballTrailHistory.length > MAX_TRAIL_POINTS) {
      this.ballTrailHistory.shift();
    }
    const trailLen = this.ballTrailHistory.length;
    for (let i = 0; i < trailLen; i++) {
      const pt = this.ballTrailHistory[i];
      this.ballTrailPositions[i * 3] = pt[0];
      this.ballTrailPositions[i * 3 + 1] = pt[1];
      this.ballTrailPositions[i * 3 + 2] = pt[2];
    }
    this.ballTrailGeo.setDrawRange(0, trailLen);
    (this.ballTrailGeo.attributes.position as THREE.BufferAttribute).needsUpdate = true;

    // 2. Partition Home & Away Defenders + Locate Ball Carrier
    const homeDefs: InterpolatedPlayerState[] = [];
    const awayDefs: InterpolatedPlayerState[] = [];
    let carrier: InterpolatedPlayerState | null = null;
    this.activePassRecipientId = null;
    this.activeTacticalInstruction = null;
    this.recipientRingMesh.visible = false;
    this.instructionRingMesh.visible = false;

    for (let i = 0; i < players.length; i++) {
      const p = players[i];
      if (p.active === false) continue;
      if (p.has_possession) {
        carrier = p;
      }
      if (p.is_pass_recipient || p.is_receiving_ball) {
        this.activePassRecipientId = p.player_id;
        this.recipientRingMesh.position.set(p.position3D[0], 0.042, p.position3D[2]);
        this.recipientRingMesh.visible = true;
      }
      if (p.tactical_instruction_marker) {
        this.activeTacticalInstruction = p.tactical_instruction_marker;
        this.instructionRingMesh.position.set(p.position3D[0], 0.038, p.position3D[2]);
        this.instructionRingMesh.visible = this.mode !== "off";
      }
      const role = p.role.toUpperCase();
      if (role === "GK") continue;
      if (p.side === "home" && (role.includes("DEF") || role.includes("CB") || role.includes("B"))) {
        homeDefs.push(p);
      } else if (
        p.side === "away" &&
        (role.includes("DEF") || role.includes("CB") || role.includes("B"))
      ) {
        awayDefs.push(p);
      }
    }

    // Update Home Defensive Block Line (sorted along Z from -34 to +34)
    if (homeDefs.length >= 2) {
      homeDefs.sort((a, b) => a.position3D[2] - b.position3D[2]);
      const count = Math.min(MAX_DEF_LINE_POINTS, homeDefs.length);
      let sumX = 0;
      for (let i = 0; i < count; i++) {
        const pos = homeDefs[i].position3D;
        sumX += pos[0];
        this.homeDefLinePositions[i * 3] = pos[0];
        this.homeDefLinePositions[i * 3 + 1] = 0.14;
        this.homeDefLinePositions[i * 3 + 2] = pos[2];
      }
      this.homeDefensiveLineX = Number((sumX / count).toFixed(2));
      this.homeDefLineGeo.setDrawRange(0, count);
      (this.homeDefLineGeo.attributes.position as THREE.BufferAttribute).needsUpdate = true;
    }

    // Update Away Defensive Block Line
    if (awayDefs.length >= 2) {
      awayDefs.sort((a, b) => a.position3D[2] - b.position3D[2]);
      const count = Math.min(MAX_DEF_LINE_POINTS, awayDefs.length);
      let sumX = 0;
      for (let i = 0; i < count; i++) {
        const pos = awayDefs[i].position3D;
        sumX += pos[0];
        this.awayDefLinePositions[i * 3] = pos[0];
        this.awayDefLinePositions[i * 3 + 1] = 0.14;
        this.awayDefLinePositions[i * 3 + 2] = pos[2];
      }
      this.awayDefensiveLineX = Number((sumX / count).toFixed(2));
      this.awayDefLineGeo.setDrawRange(0, count);
      (this.awayDefLineGeo.attributes.position as THREE.BufferAttribute).needsUpdate = true;
    }

    // 3. Update 3D Offside Virtual Wall X Position (at defending backline)
    const defendingAway = (possessionSide || "home") === "home";
    this.activeOffsideLineX = defendingAway ? this.awayDefensiveLineX : this.homeDefensiveLineX;
    this.offsideGroup.position.x = this.activeOffsideLineX;

    // 4. Update Passing Lanes & Carrier Ring
    if (carrier) {
      this.carrierRingMesh.position.set(carrier.position3D[0], 0.04, carrier.position3D[2]);
      const teammates = players
        .filter(
          (p) =>
            p.active !== false &&
            p.side === carrier!.side &&
            p.player_id !== carrier!.player_id &&
            p.role.toUpperCase() !== "GK"
        )
        .sort((a, b) => {
          const da = Math.hypot(
            a.position3D[0] - carrier!.position3D[0],
            a.position3D[2] - carrier!.position3D[2]
          );
          const db = Math.hypot(
            b.position3D[0] - carrier!.position3D[0],
            b.position3D[2] - carrier!.position3D[2]
          );
          return da - db;
        })
        .slice(0, MAX_PASS_LANES);

      this.activePassingLaneCount = teammates.length;
      for (let i = 0; i < teammates.length; i++) {
        const tm = teammates[i];
        const baseIdx = i * 6;
        this.passLanesPositions[baseIdx] = carrier.position3D[0];
        this.passLanesPositions[baseIdx + 1] = 0.16;
        this.passLanesPositions[baseIdx + 2] = carrier.position3D[2];
        this.passLanesPositions[baseIdx + 3] = tm.position3D[0];
        this.passLanesPositions[baseIdx + 4] = 0.16;
        this.passLanesPositions[baseIdx + 5] = tm.position3D[2];
      }
      this.passLanesGeo.setDrawRange(0, teammates.length * 2);
      (this.passLanesGeo.attributes.position as THREE.BufferAttribute).needsUpdate = true;
    } else {
      this.activePassingLaneCount = 0;
      this.passLanesGeo.setDrawRange(0, 0);
    }
  }

  public getSummary(): BroadcastAROverlaySummary {
    return {
      mode: this.mode,
      isVisible: this.mode !== "off" || this.eventOffsideFlashTimerSec > 0,
      homeDefensiveLineX: this.homeDefensiveLineX,
      awayDefensiveLineX: this.awayDefensiveLineX,
      activeOffsideLineX: this.activeOffsideLineX,
      activePassingLaneCount: this.activePassingLaneCount,
      shotTrailSampleCount: this.ballTrailHistory.length,
      activePassRecipientId: this.activePassRecipientId,
      activeTacticalInstruction: this.activeTacticalInstruction,
    };
  }

  public dispose(): void {
    this.disposables.forEach((item) => {
      try {
        item.dispose();
      } catch {
        // Safe disposal
      }
    });
    this.disposables = [];
    this.ballTrailHistory = [];
    this.group.clear();
  }
}
