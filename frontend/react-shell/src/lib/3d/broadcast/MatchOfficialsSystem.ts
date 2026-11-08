/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast (Phase 3)
 * MatchOfficialsSystem: 3D Center Referee, Touchline Assistant Linesmen,
 * Disciplinary Card Brandishing, Offside Flag Signals & Pitchside VAR Monitor.
 *
 * Implements:
 * 1. Center Referee (`HumanoidFootballerRig`, 26-bone SkinnedMesh):
 *    - Moves dynamically along the FIFA diagonal referee corridor tracking the ball
 *      while staying clear of passing lanes.
 *    - Brandishes 3D Yellow (`#FACC15`) and Red (`#EF4444`) cards on disciplinary events.
 *    - Runs to the pitchside RRA (Referee Review Area) VAR monitor (`x = 0m, z = -35.4m`)
 *      during VAR review events.
 * 2. Two Touchline Assistant Referees / Linesmen (`HumanoidFootballerRig`):
 *    - Near Touchline Assistant (`z = +34.9m`, covering `-52.5m .. 0m`) tracks the
 *      defending offside line in the left half.
 *    - Far Touchline Assistant (`z = -34.9m`, covering `0m .. +52.5m`) tracks the
 *      defending offside line in the right half.
 *    - Raise 3D checkered linesman flags on offsides, fouls, corners, and throw-ins.
 * 3. Pitchside VAR Review Monitor Stand:
 *    - 3D broadcast RRA monitor kiosk with illuminated VAR screen on the far touchline.
 */

import * as THREE from "three";
import { FIFA_PITCH_DIMENSIONS } from "./matchCoordinates";
import { HumanoidFootballerRig } from "./HumanoidFootballerRig";
import { FootballAnimationState } from "./FootballAnimationStateMachine";
import { InterpolatedPlayerState } from "./SpatialInterpolator";
import type { DeviceQualityTier } from "../GtexSceneTypes";

export type MatchOfficialBehaviorState =
  | "diagonal_tracking"
  | "signaling_foul"
  | "showing_yellow_card"
  | "showing_red_card"
  | "var_monitor_review"
  | "linesman_flag_offside"
  | "kickoff_ready"
  | "fulltime_whistle";

export interface MatchOfficialsSummary {
  refereeState: MatchOfficialBehaviorState;
  refereePosition: [number, number, number];
  nearLinesmanPosition: [number, number, number];
  farLinesmanPosition: [number, number, number];
  activeCardShown: "none" | "yellow" | "red";
  flagRaisedSide: "none" | "near" | "far" | "both";
  varReviewActive: boolean;
}

export interface MatchOfficialsOptions {
  qualityTier?: DeviceQualityTier;
}

const NEAR_LINESMAN_Z = FIFA_PITCH_DIMENSIONS.width / 2 + 0.9; // +34.9m
const FAR_LINESMAN_Z = -(FIFA_PITCH_DIMENSIONS.width / 2 + 0.9); // -34.9m
const VAR_MONITOR_POS: [number, number, number] = [0, 0, -(FIFA_PITCH_DIMENSIONS.width / 2 + 1.45)];

export class MatchOfficialsSystem {
  public readonly group: THREE.Group;
  public readonly centerRefereeRig: HumanoidFootballerRig;
  public readonly nearLinesmanRig: HumanoidFootballerRig;
  public readonly farLinesmanRig: HumanoidFootballerRig;
  public readonly varMonitorGroup: THREE.Group;

  private qualityTier: DeviceQualityTier;
  private refereeState: MatchOfficialBehaviorState = "diagonal_tracking";
  private stateTimerSec: number = 0;
  private activeCardShown: "none" | "yellow" | "red" = "none";
  private flagRaisedSide: "none" | "near" | "far" | "both" = "none";
  private varReviewActive: boolean = false;
  private elapsedSec: number = 0;

  private refereePos: [number, number, number] = [-4.0, 0, -5.0];
  private refereeFacingRad: number = 0;
  private nearLinesmanX: number = -18.0;
  private farLinesmanX: number = 18.0;

  private cardMesh: THREE.Mesh;
  private cardMaterial: THREE.MeshBasicMaterial;
  private nearFlagGroup: THREE.Group;
  private farFlagGroup: THREE.Group;
  private varScreenMat: THREE.MeshBasicMaterial;
  private disposables: Array<{ dispose: () => void }> = [];

  constructor(scene: THREE.Scene, options: MatchOfficialsOptions = {}) {
    this.qualityTier = options.qualityTier || "high";

    this.group = new THREE.Group();
    this.group.name = "Phase3MatchOfficialsGroup";
    scene.add(this.group);

    // 1. Center Referee Rig (FIFA Volt Yellow / Black Official Kit)
    this.centerRefereeRig = new HumanoidFootballerRig({
      playerId: "official_center_referee",
      side: "home",
      shirtNumber: 1,
      label: "Referee",
      role: "REF",
      isGoalkeeper: false,
      primaryColor: "#EAB308",
      secondaryColor: "#0F172A",
      accentColor: "#0F172A",
      goalkeeperColor: "#EAB308",
    });
    this.centerRefereeRig.rootGroup.position.set(
      this.refereePos[0],
      this.refereePos[1],
      this.refereePos[2]
    );
    this.group.add(this.centerRefereeRig.rootGroup);

    // 3D Disciplinary Card held above referee's right shoulder when brandished
    const cardGeo = new THREE.BoxGeometry(0.14, 0.21, 0.015);
    this.cardMaterial = new THREE.MeshBasicMaterial({
      color: 0xfacc15,
    });
    this.disposables.push(cardGeo, this.cardMaterial);
    this.cardMesh = new THREE.Mesh(cardGeo, this.cardMaterial);
    this.cardMesh.name = "RefereeDisciplinaryCard";
    this.cardMesh.position.set(0.28, 2.05, 0.18);
    this.cardMesh.visible = false;
    this.centerRefereeRig.rootGroup.add(this.cardMesh);

    // 2. Near Touchline Assistant Referee (Linesman 1)
    this.nearLinesmanRig = new HumanoidFootballerRig({
      playerId: "official_near_linesman",
      side: "home",
      shirtNumber: 2,
      label: "AR1",
      role: "REF",
      isGoalkeeper: false,
      primaryColor: "#0F172A",
      secondaryColor: "#EAB308",
      accentColor: "#FACC15",
      goalkeeperColor: "#0F172A",
    });
    this.nearLinesmanRig.rootGroup.position.set(this.nearLinesmanX, 0, NEAR_LINESMAN_Z);
    this.group.add(this.nearLinesmanRig.rootGroup);

    this.nearFlagGroup = this.buildLinesmanFlag("NearLinesmanFlag");
    this.nearLinesmanRig.rootGroup.add(this.nearFlagGroup);

    // 3. Far Touchline Assistant Referee (Linesman 2)
    this.farLinesmanRig = new HumanoidFootballerRig({
      playerId: "official_far_linesman",
      side: "away",
      shirtNumber: 3,
      label: "AR2",
      role: "REF",
      isGoalkeeper: false,
      primaryColor: "#0F172A",
      secondaryColor: "#EAB308",
      accentColor: "#FACC15",
      goalkeeperColor: "#0F172A",
    });
    this.farLinesmanRig.rootGroup.position.set(this.farLinesmanX, 0, FAR_LINESMAN_Z);
    this.group.add(this.farLinesmanRig.rootGroup);

    this.farFlagGroup = this.buildLinesmanFlag("FarLinesmanFlag");
    this.farLinesmanRig.rootGroup.add(this.farFlagGroup);

    // 4. Pitchside VAR Review Monitor Stand (RRA)
    const { monitorGroup, screenMat } = this.buildVarMonitorStand();
    this.varMonitorGroup = monitorGroup;
    this.varScreenMat = screenMat;
    this.group.add(this.varMonitorGroup);
  }

  private buildLinesmanFlag(name: string): THREE.Group {
    const flagGroup = new THREE.Group();
    flagGroup.name = name;
    flagGroup.position.set(0.32, 1.15, 0.15);

    const stickGeo = new THREE.CylinderGeometry(0.015, 0.015, 0.55, 6);
    const stickMat = new THREE.MeshBasicMaterial({ color: 0xe2e8f0 });
    this.disposables.push(stickGeo, stickMat);
    const stick = new THREE.Mesh(stickGeo, stickMat);
    stick.position.y = 0.25;
    flagGroup.add(stick);

    const clothGeo = new THREE.PlaneGeometry(0.34, 0.24);
    const clothMat = new THREE.MeshBasicMaterial({
      color: 0xf97316,
      side: THREE.DoubleSide,
    });
    this.disposables.push(clothGeo, clothMat);
    const cloth = new THREE.Mesh(clothGeo, clothMat);
    cloth.position.set(0.17, 0.42, 0);
    flagGroup.add(cloth);

    // Lowered by default
    flagGroup.rotation.z = -1.1;
    return flagGroup;
  }

  private buildVarMonitorStand(): {
    monitorGroup: THREE.Group;
    screenMat: THREE.MeshBasicMaterial;
  } {
    const monitorGroup = new THREE.Group();
    monitorGroup.name = "PitchsideVarMonitorGroup";
    monitorGroup.position.set(VAR_MONITOR_POS[0], VAR_MONITOR_POS[1], VAR_MONITOR_POS[2]);

    const pedestalGeo = new THREE.CylinderGeometry(0.12, 0.22, 1.35, 8);
    const frameMat = new THREE.MeshLambertMaterial({ color: 0x1e293b });
    const hoodGeo = new THREE.BoxGeometry(0.95, 0.62, 0.22);
    const screenGeo = new THREE.PlaneGeometry(0.82, 0.48);
    const screenMat = new THREE.MeshBasicMaterial({
      color: 0x0ea5e9,
      side: THREE.DoubleSide,
    });
    this.disposables.push(pedestalGeo, frameMat, hoodGeo, screenGeo, screenMat);

    const pedestal = new THREE.Mesh(pedestalGeo, frameMat);
    pedestal.position.y = 0.675;
    monitorGroup.add(pedestal);

    const hood = new THREE.Mesh(hoodGeo, frameMat);
    hood.position.set(0, 1.42, 0);
    monitorGroup.add(hood);

    const screen = new THREE.Mesh(screenGeo, screenMat);
    screen.position.set(0, 1.42, 0.12);
    monitorGroup.add(screen);

    return { monitorGroup, screenMat };
  }

  /**
   * Triggers referee and linesman reactions from authoritative match events.
   */
  public triggerEventReaction(
    eventType: string,
    ballPosition3D: [number, number, number] = [0, 0, 0]
  ): void {
    const type = (eventType || "").toLowerCase();
    const isNearSide = ballPosition3D[0] <= 0;

    if (type.includes("red_card") || type === "red") {
      this.refereeState = "showing_red_card";
      this.activeCardShown = "red";
      this.cardMaterial.color.setHex(0xef4444);
      this.cardMesh.visible = true;
      this.flagRaisedSide = isNearSide ? "near" : "far";
      this.varReviewActive = false;
      this.stateTimerSec = 5.0;
    } else if (type.includes("yellow_card") || type === "yellow" || type === "booking") {
      this.refereeState = "showing_yellow_card";
      this.activeCardShown = "yellow";
      this.cardMaterial.color.setHex(0xfacc15);
      this.cardMesh.visible = true;
      this.flagRaisedSide = isNearSide ? "near" : "far";
      this.varReviewActive = false;
      this.stateTimerSec = 4.5;
    } else if (type.includes("var")) {
      this.refereeState = "var_monitor_review";
      this.activeCardShown = "none";
      this.cardMesh.visible = false;
      this.flagRaisedSide = "none";
      this.varReviewActive = true;
      this.varScreenMat.color.setHex(0x38bdf8);
      this.stateTimerSec = 6.0;
    } else if (type.includes("offside")) {
      this.refereeState = "linesman_flag_offside";
      this.activeCardShown = "none";
      this.cardMesh.visible = false;
      this.flagRaisedSide = isNearSide ? "near" : "far";
      this.varReviewActive = false;
      this.stateTimerSec = 4.0;
    } else if (type.includes("foul") || type.includes("penalty") || type.includes("free_kick")) {
      this.refereeState = "signaling_foul";
      this.activeCardShown = "none";
      this.cardMesh.visible = false;
      this.flagRaisedSide = isNearSide ? "near" : "far";
      this.varReviewActive = false;
      this.stateTimerSec = 3.5;
    } else if (type.includes("corner") || type.includes("throw")) {
      this.refereeState = "diagonal_tracking";
      this.activeCardShown = "none";
      this.cardMesh.visible = false;
      this.flagRaisedSide = isNearSide ? "near" : "far";
      this.varReviewActive = false;
      this.stateTimerSec = 2.8;
    } else if (type.includes("fulltime") || type.includes("full_time")) {
      this.refereeState = "fulltime_whistle";
      this.activeCardShown = "none";
      this.cardMesh.visible = false;
      this.flagRaisedSide = "both";
      this.varReviewActive = false;
      this.stateTimerSec = 6.0;
    } else if (type.includes("kickoff") || type.includes("goal")) {
      this.refereeState = "kickoff_ready";
      this.activeCardShown = "none";
      this.cardMesh.visible = false;
      this.flagRaisedSide = "none";
      this.varReviewActive = false;
      this.stateTimerSec = 3.0;
    }
  }

  /**
   * Updates center referee diagonal positioning, linesmen offside-line tracking,
   * flag angles, and humanoid skeletal animations.
   */
  public update(params: {
    deltaSec: number;
    ballPosition3D: [number, number, number];
    players: InterpolatedPlayerState[];
    cameraPosition3D: [number, number, number];
    qualityTier: DeviceQualityTier;
  }): void {
    const { deltaSec, ballPosition3D, players, cameraPosition3D, qualityTier } = params;
    this.qualityTier = qualityTier;
    this.elapsedSec += deltaSec;

    if (this.stateTimerSec > 0) {
      this.stateTimerSec = Math.max(0, this.stateTimerSec - deltaSec);
      if (this.stateTimerSec === 0) {
        this.refereeState = "diagonal_tracking";
        this.activeCardShown = "none";
        this.cardMesh.visible = false;
        this.flagRaisedSide = "none";
        this.varReviewActive = false;
        this.varScreenMat.color.setHex(0x0ea5e9);
      }
    }

    // 1. Center Referee Target Position (VAR Monitor during VAR review, FIFA diagonal otherwise)
    let targetRefX: number;
    let targetRefZ: number;

    if (this.varReviewActive) {
      targetRefX = VAR_MONITOR_POS[0];
      targetRefZ = VAR_MONITOR_POS[2] + 1.25;
    } else if (this.refereeState === "kickoff_ready") {
      targetRefX = -3.5;
      targetRefZ = -5.5;
    } else {
      const bx = ballPosition3D[0];
      const bz = ballPosition3D[2];
      const offsetSign = bx >= 0 ? -1 : 1;
      targetRefX = Math.max(-44, Math.min(44, bx * 0.78 + offsetSign * 6.5));
      targetRefZ = Math.max(-25, Math.min(25, bz * 0.55 - 7.5));
    }

    const dxRef = targetRefX - this.refereePos[0];
    const dzRef = targetRefZ - this.refereePos[2];
    const distRef = Math.hypot(dxRef, dzRef);
    const maxStep = 6.2 * Math.max(0.001, deltaSec);
    const stepRatio = distRef > maxStep ? maxStep / distRef : 1.0;

    this.refereePos[0] += dxRef * stepRatio;
    this.refereePos[2] += dzRef * stepRatio;

    const refSpeedRatio = Math.min(1.0, (distRef / Math.max(0.016, deltaSec)) / 6.5);
    this.refereeFacingRad = this.varReviewActive
      ? Math.PI
      : Math.atan2(ballPosition3D[2] - this.refereePos[2], ballPosition3D[0] - this.refereePos[0]);

    let refAnim: FootballAnimationState = "idle";
    if (this.activeCardShown !== "none" || this.refereeState === "signaling_foul") {
      refAnim = "foul_reaction";
    } else if (refSpeedRatio > 0.62) {
      refAnim = "sprint";
    } else if (refSpeedRatio > 0.15) {
      refAnim = "jog";
    }

    this.centerRefereeRig.update({
      deltaSec,
      targetState: refAnim,
      position3D: this.refereePos,
      facingAngleRad: this.refereeFacingRad,
      speedRatio: refSpeedRatio,
      angularVelocityRad: 0,
      hasPossession: false,
      ballPosition3D,
      cameraPosition3D,
      qualityTier,
    });

    // 2. Compute Defending Offside Lines for Near (-X half) and Far (+X half) Assistant Referees
    let nearTargetX = Math.max(-50, Math.min(-1, ballPosition3D[0]));
    let farTargetX = Math.max(1, Math.min(50, ballPosition3D[0]));

    if (players.length >= 4) {
      const homeOutfieldX: number[] = [];
      const awayOutfieldX: number[] = [];
      for (let i = 0; i < players.length; i++) {
        const p = players[i];
        if (p.role.toUpperCase() === "GK") continue;
        if (p.side === "home") {
          homeOutfieldX.push(p.position3D[0]);
        } else {
          awayOutfieldX.push(p.position3D[0]);
        }
      }
      if (homeOutfieldX.length > 0) {
        homeOutfieldX.sort((a, b) => a - b);
        nearTargetX = Math.max(-51, Math.min(-1, homeOutfieldX[0]));
      }
      if (awayOutfieldX.length > 0) {
        awayOutfieldX.sort((a, b) => b - a);
        farTargetX = Math.max(1, Math.min(51, awayOutfieldX[0]));
      }
    }

    const nearDx = nearTargetX - this.nearLinesmanX;
    this.nearLinesmanX += nearDx * Math.min(1, deltaSec * 6.0);
    const nearSpeed = Math.min(1.0, Math.abs(nearDx) * 0.4);

    const farDx = farTargetX - this.farLinesmanX;
    this.farLinesmanX += farDx * Math.min(1, deltaSec * 6.0);
    const farSpeed = Math.min(1.0, Math.abs(farDx) * 0.4);

    // Update Linesman Flag Rotations (raised = +0.25 rad, lowered = -1.1 rad)
    const nearRaised = this.flagRaisedSide === "near" || this.flagRaisedSide === "both";
    const farRaised = this.flagRaisedSide === "far" || this.flagRaisedSide === "both";
    this.nearFlagGroup.rotation.z = nearRaised ? 0.25 : -1.1;
    this.farFlagGroup.rotation.z = farRaised ? 0.25 : -1.1;

    this.nearLinesmanRig.update({
      deltaSec,
      targetState: nearRaised ? "foul_reaction" : nearSpeed > 0.2 ? "gk_lateral_move" : "idle",
      position3D: [this.nearLinesmanX, 0, NEAR_LINESMAN_Z],
      facingAngleRad: -Math.PI / 2,
      speedRatio: nearSpeed,
      angularVelocityRad: 0,
      hasPossession: false,
      ballPosition3D,
      cameraPosition3D,
      qualityTier,
    });

    this.farLinesmanRig.update({
      deltaSec,
      targetState: farRaised ? "foul_reaction" : farSpeed > 0.2 ? "gk_lateral_move" : "idle",
      position3D: [this.farLinesmanX, 0, FAR_LINESMAN_Z],
      facingAngleRad: Math.PI / 2,
      speedRatio: farSpeed,
      angularVelocityRad: 0,
      hasPossession: false,
      ballPosition3D,
      cameraPosition3D,
      qualityTier,
    });
  }

  public getSummary(): MatchOfficialsSummary {
    return {
      refereeState: this.refereeState,
      refereePosition: [
        Number(this.refereePos[0].toFixed(2)),
        Number(this.refereePos[1].toFixed(2)),
        Number(this.refereePos[2].toFixed(2)),
      ],
      nearLinesmanPosition: [
        Number(this.nearLinesmanX.toFixed(2)),
        0,
        Number(NEAR_LINESMAN_Z.toFixed(2)),
      ],
      farLinesmanPosition: [
        Number(this.farLinesmanX.toFixed(2)),
        0,
        Number(FAR_LINESMAN_Z.toFixed(2)),
      ],
      activeCardShown: this.activeCardShown,
      flagRaisedSide: this.flagRaisedSide,
      varReviewActive: this.varReviewActive,
    };
  }

  public dispose(): void {
    this.centerRefereeRig.dispose();
    this.nearLinesmanRig.dispose();
    this.farLinesmanRig.dispose();
    this.disposables.forEach((item) => {
      try {
        item.dispose();
      } catch {
        // Safe disposal
      }
    });
    this.disposables = [];
    this.group.clear();
  }
}
