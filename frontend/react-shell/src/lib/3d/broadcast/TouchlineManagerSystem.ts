/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast (Phase 2)
 * TouchlineManagerSystem: 3D Technical Area Managers, Fourth Official,
 * and Dugout Bench Substitute Reactions.
 *
 * Implements:
 * 1. Home & Away 3D Manager Humanoid Rigs (`HumanoidFootballerRig`, 26-bone SkinnedMesh)
 *    positioned in their respective FIFA dashed technical areas (`x = -14m` and `x = +14m`, `z = 35.8m`).
 * 2. Six canonical touchline manager behavior states:
 *    - "calm_observing": Standing at the touchline tracking ball play.
 *    - "pacing_touchline": Pacing laterally along the technical area boundary.
 *    - "tactical_instruction": Stepping to the touchline edge shouting/pointing tactical instructions.
 *    - "celebrating_goal": Euphoric touchline sprint & fist-pump celebration on team goals.
 *    - "frustrated_reaction": Head-in-hands / slump reaction on conceding or big missed chances.
 *    - "protesting_decision": Stepping toward the 4th official desk to contest cards, fouls, or VAR.
 * 3. Dugout Bench Substitutes & Coaching Staff (`THREE.InstancedMesh` — 1 draw call for 12 bench figures)
 *    who leap up from the dugout seats during goals and high-intensity moments.
 * 4. Fourth Official with illuminated LED stoppage/substitution board at `x = 0m, z = 36.4m`.
 */

import * as THREE from "three";
import { FIFA_PITCH_DIMENSIONS } from "./matchCoordinates";
import { HumanoidFootballerRig } from "./HumanoidFootballerRig";
import { FootballAnimationState } from "./FootballAnimationStateMachine";
import { SpectatorSafeTeamView } from "./spectatorContract";
import type { DeviceQualityTier } from "../GtexSceneTypes";

export type TouchlineManagerBehaviorState =
  | "calm_observing"
  | "pacing_touchline"
  | "tactical_instruction"
  | "celebrating_goal"
  | "frustrated_reaction"
  | "protesting_decision";

export interface TouchlineManagerSummary {
  homeManagerState: TouchlineManagerBehaviorState;
  awayManagerState: TouchlineManagerBehaviorState;
  homeManagerAnimation: FootballAnimationState;
  awayManagerAnimation: FootballAnimationState;
  homeManagerPosition: [number, number, number];
  awayManagerPosition: [number, number, number];
  benchSubstituteCount: number;
  fourthOfficialBoardActive: boolean;
}

export interface TouchlineManagerOptions {
  homeTeam: SpectatorSafeTeamView;
  awayTeam: SpectatorSafeTeamView;
  qualityTier?: DeviceQualityTier;
}

interface BenchMemberMeta {
  baseX: number;
  baseY: number;
  baseZ: number;
  side: "home" | "away";
  phase: number;
}

const HOME_TECH_CENTER_X = -14.0;
const AWAY_TECH_CENTER_X = 14.0;
const TECH_AREA_BASE_Z = FIFA_PITCH_DIMENSIONS.width / 2 + 1.85; // 35.85m

export class TouchlineManagerSystem {
  public readonly group: THREE.Group;
  public readonly homeManagerRig: HumanoidFootballerRig;
  public readonly awayManagerRig: HumanoidFootballerRig;
  public readonly benchInstancedMesh: THREE.InstancedMesh;
  public readonly fourthOfficialGroup: THREE.Group;

  private homeTeam: SpectatorSafeTeamView;
  private awayTeam: SpectatorSafeTeamView;
  private qualityTier: DeviceQualityTier;

  private homeBehavior: TouchlineManagerBehaviorState = "calm_observing";
  private awayBehavior: TouchlineManagerBehaviorState = "pacing_touchline";
  private homeReactionTimerSec: number = 0;
  private awayReactionTimerSec: number = 0;
  private fourthOfficialBoardTimerSec: number = 0;
  private elapsedSec: number = 0;

  private homePos: [number, number, number] = [HOME_TECH_CENTER_X, 0, TECH_AREA_BASE_Z];
  private awayPos: [number, number, number] = [AWAY_TECH_CENTER_X, 0, TECH_AREA_BASE_Z];
  private homeFacingRad: number = -Math.PI / 2;
  private awayFacingRad: number = -Math.PI / 2;

  private benchMeta: BenchMemberMeta[] = [];
  private fourthOfficialBoardMesh: THREE.Mesh;
  private disposables: Array<{ dispose: () => void }> = [];

  constructor(scene: THREE.Scene, options: TouchlineManagerOptions) {
    this.homeTeam = options.homeTeam;
    this.awayTeam = options.awayTeam;
    this.qualityTier = options.qualityTier || "high";

    this.group = new THREE.Group();
    this.group.name = "GTEX_Touchline_Manager_And_Bench_System";

    // 1. Home Manager Humanoid Rig (Executive dark slate suit + club accent badge)
    this.homeManagerRig = new HumanoidFootballerRig({
      playerId: `mgr-home-${this.homeTeam.team_id}`,
      side: "home",
      shirtNumber: 1,
      label: `${this.homeTeam.short_name} Manager`,
      role: "MGR",
      isGoalkeeper: false,
      primaryColor: "#111827", // Tailored charcoal suit jacket
      secondaryColor: "#0f172a", // Executive trousers
      accentColor: this.homeTeam.primary_color || "#00E676",
      goalkeeperColor: "#111827",
      heightCm: 181,
    });
    this.homeManagerRig.rootGroup.name = "Home_Touchline_Manager_Rig";
    this.homeManagerRig.rootGroup.position.set(this.homePos[0], this.homePos[1], this.homePos[2]);
    this.group.add(this.homeManagerRig.rootGroup);

    // 2. Away Manager Humanoid Rig (Executive navy suit + away club accent badge)
    this.awayManagerRig = new HumanoidFootballerRig({
      playerId: `mgr-away-${this.awayTeam.team_id}`,
      side: "away",
      shirtNumber: 1,
      label: `${this.awayTeam.short_name} Manager`,
      role: "MGR",
      isGoalkeeper: false,
      primaryColor: "#172554", // Tailored midnight navy jacket
      secondaryColor: "#090d16",
      accentColor: this.awayTeam.primary_color || "#3B82F6",
      goalkeeperColor: "#172554",
      heightCm: 180,
    });
    this.awayManagerRig.rootGroup.name = "Away_Touchline_Manager_Rig";
    this.awayManagerRig.rootGroup.position.set(this.awayPos[0], this.awayPos[1], this.awayPos[2]);
    this.group.add(this.awayManagerRig.rootGroup);

    // 3. Seated Dugout Substitutes & Coaching Staff (12 figures in 1 InstancedMesh)
    const benchCount = 12;
    const benchGeo = new THREE.BoxGeometry(0.46, 1.15, 0.42);
    const benchMat = new THREE.MeshLambertMaterial({ color: 0xffffff });
    this.disposables.push(benchGeo, benchMat);

    this.benchInstancedMesh = new THREE.InstancedMesh(benchGeo, benchMat, benchCount);
    this.benchInstancedMesh.name = "Dugout_Bench_Substitutes";
    this.benchInstancedMesh.castShadow = false;
    this.benchInstancedMesh.receiveShadow = false;

    const dugoutSeatZ = FIFA_PITCH_DIMENSIONS.width / 2 + 4.3;
    const dummyMatrix = new THREE.Matrix4();
    const color = new THREE.Color();
    const homeColor = new THREE.Color(this.homeTeam.primary_color || "#00E676");
    const awayColor = new THREE.Color(this.awayTeam.primary_color || "#3B82F6");

    for (let i = 0; i < benchCount; i++) {
      const isHome = i < 6;
      const seatIdx = isHome ? i : i - 6;
      const centerX = isHome ? HOME_TECH_CENTER_X : AWAY_TECH_CENTER_X;
      const bx = centerX - 3.5 + seatIdx * 1.4;
      const by = 0.72;
      const bz = dugoutSeatZ;
      const phase = i * 0.95;

      this.benchMeta.push({
        baseX: bx,
        baseY: by,
        baseZ: bz,
        side: isHome ? "home" : "away",
        phase,
      });

      dummyMatrix.makeRotationY(Math.PI);
      dummyMatrix.setPosition(bx, by, bz);
      this.benchInstancedMesh.setMatrixAt(i, dummyMatrix);

      color.copy(isHome ? homeColor : awayColor);
      this.benchInstancedMesh.setColorAt(i, color);
    }

    this.benchInstancedMesh.instanceMatrix.needsUpdate = true;
    if (this.benchInstancedMesh.instanceColor) {
      this.benchInstancedMesh.instanceColor.needsUpdate = true;
    }
    this.group.add(this.benchInstancedMesh);

    // 4. Fourth Official & Electronic LED Substitution Board at Halfway Touchline
    this.fourthOfficialGroup = new THREE.Group();
    this.fourthOfficialGroup.name = "Fourth_Official_Touchline_Station";
    this.fourthOfficialGroup.position.set(0, 0, TECH_AREA_BASE_Z + 0.65);

    const officialBodyGeo = new THREE.CylinderGeometry(0.22, 0.2, 1.55, 8);
    const officialHeadGeo = new THREE.SphereGeometry(0.14, 8, 8);
    const officialMat = new THREE.MeshLambertMaterial({ color: 0xfacc15 }); // Referee yellow/black kit
    const boardGeo = new THREE.BoxGeometry(0.75, 0.42, 0.06);
    const boardMat = new THREE.MeshBasicMaterial({ color: 0x10b981 });
    this.disposables.push(officialBodyGeo, officialHeadGeo, officialMat, boardGeo, boardMat);

    const officialBody = new THREE.Mesh(officialBodyGeo, officialMat);
    officialBody.position.set(0, 0.78, 0);
    const officialHead = new THREE.Mesh(officialHeadGeo, officialMat);
    officialHead.position.set(0, 1.68, 0);
    this.fourthOfficialGroup.add(officialBody, officialHead);

    this.fourthOfficialBoardMesh = new THREE.Mesh(boardGeo, boardMat);
    this.fourthOfficialBoardMesh.name = "Fourth_Official_LED_Board";
    this.fourthOfficialBoardMesh.position.set(0, 2.05, -0.15);
    this.fourthOfficialBoardMesh.visible = false;
    this.fourthOfficialGroup.add(this.fourthOfficialBoardMesh);

    this.group.add(this.fourthOfficialGroup);
    scene.add(this.group);
  }

  /**
   * Triggers realistic manager and bench reactions when an authoritative match event occurs.
   */
  public triggerEventReaction(
    eventType: string,
    eventSide: "home" | "away" | "both" = "both"
  ): void {
    const normalized = (eventType || "").toLowerCase();

    if (normalized === "goal") {
      if (eventSide === "home") {
        this.homeBehavior = "celebrating_goal";
        this.homeReactionTimerSec = 6.0;
        this.awayBehavior = "frustrated_reaction";
        this.awayReactionTimerSec = 5.0;
      } else if (eventSide === "away") {
        this.awayBehavior = "celebrating_goal";
        this.awayReactionTimerSec = 6.0;
        this.homeBehavior = "frustrated_reaction";
        this.homeReactionTimerSec = 5.0;
      } else {
        this.homeBehavior = "celebrating_goal";
        this.awayBehavior = "celebrating_goal";
        this.homeReactionTimerSec = 5.0;
        this.awayReactionTimerSec = 5.0;
      }
      return;
    }

    if (normalized === "substitution") {
      this.fourthOfficialBoardTimerSec = 5.5;
      this.fourthOfficialBoardMesh.visible = true;
      if (eventSide === "home" || eventSide === "both") {
        this.homeBehavior = "tactical_instruction";
        this.homeReactionTimerSec = 4.2;
      }
      if (eventSide === "away" || eventSide === "both") {
        this.awayBehavior = "tactical_instruction";
        this.awayReactionTimerSec = 4.2;
      }
      return;
    }

    if (
      normalized === "yellow_card" ||
      normalized === "red_card" ||
      normalized === "foul" ||
      normalized === "penalty" ||
      normalized.includes("var")
    ) {
      if (eventSide === "home") {
        this.homeBehavior = "protesting_decision";
        this.homeReactionTimerSec = 4.5;
        this.awayBehavior = "tactical_instruction";
        this.awayReactionTimerSec = 3.2;
      } else if (eventSide === "away") {
        this.awayBehavior = "protesting_decision";
        this.awayReactionTimerSec = 4.5;
        this.homeBehavior = "tactical_instruction";
        this.homeReactionTimerSec = 3.2;
      } else {
        this.homeBehavior = "protesting_decision";
        this.awayBehavior = "protesting_decision";
        this.homeReactionTimerSec = 4.0;
        this.awayReactionTimerSec = 4.0;
      }
      return;
    }

    if (normalized === "miss" || normalized === "save" || normalized === "shot") {
      if (eventSide === "home") {
        this.homeBehavior = "frustrated_reaction";
        this.homeReactionTimerSec = 3.0;
      } else if (eventSide === "away") {
        this.awayBehavior = "frustrated_reaction";
        this.awayReactionTimerSec = 3.0;
      }
      return;
    }

    if (normalized === "fulltime") {
      this.homeBehavior = "celebrating_goal";
      this.awayBehavior = "calm_observing";
      this.homeReactionTimerSec = 5.0;
      this.awayReactionTimerSec = 5.0;
    }
  }

  /**
   * Notifies the touchline manager that live tactical instructions were issued.
   */
  public notifyTacticalChange(side: "home" | "away" | "both" = "both"): void {
    if (side === "home" || side === "both") {
      this.homeBehavior = "tactical_instruction";
      this.homeReactionTimerSec = 4.0;
    }
    if (side === "away" || side === "both") {
      this.awayBehavior = "tactical_instruction";
      this.awayReactionTimerSec = 4.0;
    }
  }

  private resolveAnimationForBehavior(
    behavior: TouchlineManagerBehaviorState
  ): FootballAnimationState {
    switch (behavior) {
      case "celebrating_goal":
        return "goal_celebration";
      case "frustrated_reaction":
        return "disappointment";
      case "protesting_decision":
        return "foul_reaction";
      case "tactical_instruction":
        return "short_pass";
      case "pacing_touchline":
        return "walk";
      case "calm_observing":
      default:
        return "idle";
    }
  }

  public update(params: {
    deltaSec: number;
    ballPosition3D: [number, number, number];
    cameraPosition3D: [number, number, number];
    possessionSide?: "home" | "away" | null;
    qualityTier?: DeviceQualityTier;
  }): void {
    const dt = Math.max(0, Math.min(0.1, params.deltaSec));
    this.elapsedSec += dt;
    if (params.qualityTier) {
      this.qualityTier = params.qualityTier;
    }

    // 1. Step Fourth Official LED Board Timer
    if (this.fourthOfficialBoardTimerSec > 0) {
      this.fourthOfficialBoardTimerSec = Math.max(0, this.fourthOfficialBoardTimerSec - dt);
      this.fourthOfficialBoardMesh.visible = this.fourthOfficialBoardTimerSec > 0;
    }

    // 2. Step Home & Away Reaction Timers & Open-Play Touchline Cadence
    if (this.homeReactionTimerSec > 0) {
      this.homeReactionTimerSec = Math.max(0, this.homeReactionTimerSec - dt);
    } else {
      const cycle = Math.floor(this.elapsedSec / 6.0) % 3;
      if (params.possessionSide === "home" && cycle === 1) {
        this.homeBehavior = "tactical_instruction";
      } else if (cycle === 0) {
        this.homeBehavior = "pacing_touchline";
      } else {
        this.homeBehavior = "calm_observing";
      }
    }

    if (this.awayReactionTimerSec > 0) {
      this.awayReactionTimerSec = Math.max(0, this.awayReactionTimerSec - dt);
    } else {
      const cycle = Math.floor((this.elapsedSec + 3.0) / 6.0) % 3;
      if (params.possessionSide === "away" && cycle === 1) {
        this.awayBehavior = "tactical_instruction";
      } else if (cycle === 0) {
        this.awayBehavior = "pacing_touchline";
      } else {
        this.awayBehavior = "calm_observing";
      }
    }

    // 3. Compute Manager Technical Area Kinematics
    const updateManagerKinematics = (
      isHome: boolean,
      behavior: TouchlineManagerBehaviorState
    ): {
      pos: [number, number, number];
      facingRad: number;
      speedRatio: number;
    } => {
      const centerX = isHome ? HOME_TECH_CENTER_X : AWAY_TECH_CENTER_X;
      const phaseOffset = isHome ? 0 : 1.8;
      let targetX = centerX;
      let targetZ = TECH_AREA_BASE_Z;
      let speedRatio = 0.0;

      if (behavior === "pacing_touchline") {
        targetX = centerX + Math.sin(this.elapsedSec * 1.1 + phaseOffset) * 3.2;
        targetZ = TECH_AREA_BASE_Z;
        speedRatio = 0.28;
      } else if (behavior === "tactical_instruction") {
        targetX = centerX + (isHome ? 1.2 : -1.2);
        targetZ = TECH_AREA_BASE_Z - 0.45; // Step forward to the touchline chalk edge
        speedRatio = 0.15;
      } else if (behavior === "protesting_decision") {
        // Step inward toward the 4th official desk at x = 0
        targetX = isHome ? HOME_TECH_CENTER_X + 4.4 : AWAY_TECH_CENTER_X - 4.4;
        targetZ = TECH_AREA_BASE_Z + 0.15;
        speedRatio = 0.35;
      } else if (behavior === "celebrating_goal") {
        targetX = centerX + Math.sin(this.elapsedSec * 4.2 + phaseOffset) * 3.8;
        targetZ = TECH_AREA_BASE_Z - 0.55;
        speedRatio = 0.78;
      }

      const dxBall = params.ballPosition3D[0] - targetX;
      const dzBall = params.ballPosition3D[2] - targetZ;
      const angleToBall = Math.atan2(dzBall, dxBall);
      // Clamp facing angle so manager generally faces the pitch (-PI/2) while tracking ball
      const facingRad = Math.max(-Math.PI * 0.82, Math.min(-Math.PI * 0.18, angleToBall));

      return {
        pos: [Number(targetX.toFixed(2)), 0, Number(targetZ.toFixed(2))],
        facingRad,
        speedRatio,
      };
    };

    const homeKin = updateManagerKinematics(true, this.homeBehavior);
    this.homePos = homeKin.pos;
    this.homeFacingRad = homeKin.facingRad;

    const awayKin = updateManagerKinematics(false, this.awayBehavior);
    this.awayPos = awayKin.pos;
    this.awayFacingRad = awayKin.facingRad;

    // 4. Update Both Humanoid Manager Rigs
    this.homeManagerRig.update({
      deltaSec: dt,
      targetState: this.resolveAnimationForBehavior(this.homeBehavior),
      position3D: this.homePos,
      facingAngleRad: this.homeFacingRad,
      speedRatio: homeKin.speedRatio,
      hasPossession: false,
      ballPosition3D: params.ballPosition3D,
      cameraPosition3D: params.cameraPosition3D,
      qualityTier: this.qualityTier,
    });

    this.awayManagerRig.update({
      deltaSec: dt,
      targetState: this.resolveAnimationForBehavior(this.awayBehavior),
      position3D: this.awayPos,
      facingAngleRad: this.awayFacingRad,
      speedRatio: awayKin.speedRatio,
      hasPossession: false,
      ballPosition3D: params.ballPosition3D,
      cameraPosition3D: params.cameraPosition3D,
      qualityTier: this.qualityTier,
    });

    // 5. Update Bench Substitutes (leap up when their team manager is celebrating a goal)
    const mat4 = new THREE.Matrix4();
    const homeCelebrating = this.homeBehavior === "celebrating_goal";
    const awayCelebrating = this.awayBehavior === "celebrating_goal";

    for (let i = 0; i < this.benchMeta.length; i++) {
      const meta = this.benchMeta[i];
      const isCeleb = meta.side === "home" ? homeCelebrating : awayCelebrating;
      const bounceY = isCeleb
        ? 0.35 + Math.abs(Math.sin(this.elapsedSec * 9.5 + meta.phase)) * 0.38
        : 0;
      const stepForwardZ = isCeleb ? -0.55 : 0;

      mat4.makeRotationY(Math.PI);
      mat4.setPosition(meta.baseX, meta.baseY + bounceY, meta.baseZ + stepForwardZ);
      this.benchInstancedMesh.setMatrixAt(i, mat4);
    }
    this.benchInstancedMesh.instanceMatrix.needsUpdate = true;
  }

  public getSummary(): TouchlineManagerSummary {
    return {
      homeManagerState: this.homeBehavior,
      awayManagerState: this.awayBehavior,
      homeManagerAnimation: this.homeManagerRig.getCurrentState(),
      awayManagerAnimation: this.awayManagerRig.getCurrentState(),
      homeManagerPosition: [...this.homePos],
      awayManagerPosition: [...this.awayPos],
      benchSubstituteCount: this.benchMeta.length,
      fourthOfficialBoardActive: this.fourthOfficialBoardMesh.visible,
    };
  }

  public dispose(): void {
    this.homeManagerRig.dispose();
    this.awayManagerRig.dispose();
    this.disposables.forEach((d) => {
      try {
        d.dispose();
      } catch {
        // Safe disposal
      }
    });
    this.disposables = [];
    this.group.clear();
  }
}
