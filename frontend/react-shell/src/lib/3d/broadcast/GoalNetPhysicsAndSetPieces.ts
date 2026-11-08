/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast (Phase 3)
 * GoalNetPhysicsAndSetPieces: Spring-Damped 3D Goal-Net Vertex Ripple Physics
 * & Set-Piece Vanishing Foam Spray / Choreography.
 *
 * Implements:
 * 1. Dynamic 3D Goal-Net Vertex Ripple Physics:
 *    - Subdivided `10 x 6` rear net curtains inside the Home (`x = -53.85m`) and
 *      Away (`x = +53.85m`) FIFA goal cages.
 *    - Spring-damped radial wave deformation when a goal is scored or the ball
 *      strikes the back of the net, updating vertex buffers in-place with zero GC.
 * 2. Referee Vanishing Foam Spray & Set-Piece Staging:
 *    - 3D FIFA vanishing foam circle at the free-kick spot + 9.15m (10-yard)
 *      defensive wall foam line that dissolves gradually over 8 seconds.
 *    - Corner-quadrant and penalty-spot set-piece staging indicators.
 */

import * as THREE from "three";
import { FIFA_PITCH_DIMENSIONS } from "./matchCoordinates";

export type ActiveSetPieceType = "none" | "free_kick" | "corner" | "penalty";

export interface GoalNetAndSetPieceSummary {
  activeSetPiece: ActiveSetPieceType;
  vanishingSprayVisible: boolean;
  vanishingSprayOpacity: number;
  homeNetRippleIntensity: number;
  awayNetRippleIntensity: number;
  lastNetImpactSide: "none" | "home" | "away";
}

const GOAL_WIDTH = 7.32;
const GOAL_HEIGHT = 2.44;
const GOAL_DEPTH = 1.65;
const HALF_PITCH_L = FIFA_PITCH_DIMENSIONS.length / 2; // 52.5m

export class GoalNetPhysicsAndSetPieces {
  public readonly group: THREE.Group;
  public readonly homeDynamicNetMesh: THREE.Mesh;
  public readonly awayDynamicNetMesh: THREE.Mesh;
  public readonly vanishingSprayGroup: THREE.Group;

  private homeNetGeo: THREE.PlaneGeometry;
  private awayNetGeo: THREE.PlaneGeometry;
  private homeBaseVertices: Float32Array;
  private awayBaseVertices: Float32Array;

  private homeRippleAmplitude: number = 0;
  private awayRippleAmplitude: number = 0;
  private homeRipplePhase: number = 0;
  private awayRipplePhase: number = 0;
  private homeImpactLocalZ: number = 0;
  private homeImpactLocalY: number = 1.2;
  private awayImpactLocalZ: number = 0;
  private awayImpactLocalY: number = 1.2;
  private lastNetImpactSide: "none" | "home" | "away" = "none";

  private activeSetPiece: ActiveSetPieceType = "none";
  private setPieceTimerSec: number = 0;
  private sprayMaterial: THREE.MeshBasicMaterial;
  private ballSprayCircleMesh: THREE.Mesh;
  private wallSprayLineMesh: THREE.Mesh;

  private disposables: Array<{ dispose: () => void }> = [];

  constructor(scene: THREE.Scene) {
    this.group = new THREE.Group();
    this.group.name = "Phase3GoalNetPhysicsAndSetPiecesGroup";
    scene.add(this.group);

    const netMat = new THREE.MeshBasicMaterial({
      color: 0xf8fafc,
      wireframe: true,
      transparent: true,
      opacity: 0.45,
      side: THREE.DoubleSide,
    });
    this.disposables.push(netMat);

    // 1. Home Dynamic Rear Goal Net (at x = -54.1m, rotated to face +X)
    this.homeNetGeo = new THREE.PlaneGeometry(GOAL_WIDTH, GOAL_HEIGHT, 10, 6);
    this.disposables.push(this.homeNetGeo);
    const homePosAttr = this.homeNetGeo.attributes.position as THREE.BufferAttribute;
    this.homeBaseVertices = new Float32Array(homePosAttr.array.length);
    this.homeBaseVertices.set(homePosAttr.array as ArrayLike<number>);

    this.homeDynamicNetMesh = new THREE.Mesh(this.homeNetGeo, netMat);
    this.homeDynamicNetMesh.name = "HomeDynamicGoalNet";
    this.homeDynamicNetMesh.rotation.y = Math.PI / 2;
    this.homeDynamicNetMesh.position.set(-(HALF_PITCH_L + GOAL_DEPTH), GOAL_HEIGHT / 2, 0);
    this.group.add(this.homeDynamicNetMesh);

    // 2. Away Dynamic Rear Goal Net (at x = +54.1m, rotated to face -X)
    this.awayNetGeo = new THREE.PlaneGeometry(GOAL_WIDTH, GOAL_HEIGHT, 10, 6);
    this.disposables.push(this.awayNetGeo);
    const awayPosAttr = this.awayNetGeo.attributes.position as THREE.BufferAttribute;
    this.awayBaseVertices = new Float32Array(awayPosAttr.array.length);
    this.awayBaseVertices.set(awayPosAttr.array as ArrayLike<number>);

    this.awayDynamicNetMesh = new THREE.Mesh(this.awayNetGeo, netMat);
    this.awayDynamicNetMesh.name = "AwayDynamicGoalNet";
    this.awayDynamicNetMesh.rotation.y = -Math.PI / 2;
    this.awayDynamicNetMesh.position.set(HALF_PITCH_L + GOAL_DEPTH, GOAL_HEIGHT / 2, 0);
    this.group.add(this.awayDynamicNetMesh);

    // 3. Referee Vanishing Foam Spray (Ball Spot Ring + 9.15m Defensive Wall Line)
    this.vanishingSprayGroup = new THREE.Group();
    this.vanishingSprayGroup.name = "RefereeVanishingSprayGroup";
    this.vanishingSprayGroup.visible = false;
    this.group.add(this.vanishingSprayGroup);

    this.sprayMaterial = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.0,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const spotRingGeo = new THREE.RingGeometry(0.32, 0.44, 20);
    const wallLineGeo = new THREE.PlaneGeometry(0.18, 5.2);
    this.disposables.push(this.sprayMaterial, spotRingGeo, wallLineGeo);

    this.ballSprayCircleMesh = new THREE.Mesh(spotRingGeo, this.sprayMaterial);
    this.ballSprayCircleMesh.rotation.x = -Math.PI / 2;
    this.ballSprayCircleMesh.position.y = 0.035;
    this.vanishingSprayGroup.add(this.ballSprayCircleMesh);

    this.wallSprayLineMesh = new THREE.Mesh(wallLineGeo, this.sprayMaterial);
    this.wallSprayLineMesh.rotation.x = -Math.PI / 2;
    this.wallSprayLineMesh.position.y = 0.035;
    this.vanishingSprayGroup.add(this.wallSprayLineMesh);
  }

  /**
   * Triggers a spring-damped vertex ripple in the target goal net.
   */
  public triggerGoalNetImpact(
    goalSide: "home" | "away",
    impactPosition3D: [number, number, number] = [0, 1.2, 0],
    force: number = 1.0
  ): void {
    const clampedForce = Math.max(0.25, Math.min(1.5, force));
    const clampedZ = Math.max(-GOAL_WIDTH / 2, Math.min(GOAL_WIDTH / 2, impactPosition3D[2]));
    const clampedY = Math.max(0.2, Math.min(GOAL_HEIGHT, impactPosition3D[1]));

    this.lastNetImpactSide = goalSide;
    if (goalSide === "home") {
      this.homeRippleAmplitude = 0.72 * clampedForce;
      this.homeRipplePhase = 0;
      this.homeImpactLocalZ = clampedZ;
      this.homeImpactLocalY = clampedY - GOAL_HEIGHT / 2;
    } else {
      this.awayRippleAmplitude = 0.72 * clampedForce;
      this.awayRipplePhase = 0;
      this.awayImpactLocalZ = clampedZ;
      this.awayImpactLocalY = clampedY - GOAL_HEIGHT / 2;
    }
  }

  /**
   * Activates set-piece vanishing foam spray or goal-net impact from match events.
   */
  public triggerMatchEvent(
    eventType: string,
    scoringOrAttackingSide: "home" | "away" | "both",
    ballPosition3D: [number, number, number]
  ): void {
    const type = (eventType || "").toLowerCase();

    if (type === "goal") {
      // If Home scored, ball went into Away goal (+X), or determine from ball X coordinate
      const targetGoalSide: "home" | "away" =
        Math.abs(ballPosition3D[0]) > 10
          ? ballPosition3D[0] < 0
            ? "home"
            : "away"
          : scoringOrAttackingSide === "home"
          ? "away"
          : "home";
      this.triggerGoalNetImpact(targetGoalSide, ballPosition3D, 1.25);
    } else if (type.includes("free_kick") || type.includes("foul")) {
      this.activeSetPiece = "free_kick";
      this.setPieceTimerSec = 8.0;
      this.vanishingSprayGroup.visible = true;
      this.sprayMaterial.opacity = 0.92;

      const [bx, , bz] = ballPosition3D;
      this.ballSprayCircleMesh.position.set(bx, 0.035, bz);

      // Position 9.15m defensive wall line toward the nearest defended goal
      const goalX = bx >= 0 ? HALF_PITCH_L : -HALF_PITCH_L;
      const dirToGoalX = goalX - bx;
      const dirToGoalZ = 0 - bz;
      const dist = Math.max(0.1, Math.hypot(dirToGoalX, dirToGoalZ));
      const ux = dirToGoalX / dist;
      const uz = dirToGoalZ / dist;
      const wallX = bx + ux * 9.15;
      const wallZ = bz + uz * 9.15;
      this.wallSprayLineMesh.position.set(wallX, 0.035, wallZ);
      this.wallSprayLineMesh.rotation.z = Math.atan2(uz, ux);
    } else if (type.includes("penalty")) {
      this.activeSetPiece = "penalty";
      this.setPieceTimerSec = 6.0;
      this.vanishingSprayGroup.visible = true;
      this.sprayMaterial.opacity = 0.88;
      const penX = ballPosition3D[0] >= 0 ? HALF_PITCH_L - 11.0 : -(HALF_PITCH_L - 11.0);
      this.ballSprayCircleMesh.position.set(penX, 0.035, 0);
      this.wallSprayLineMesh.position.set(penX - Math.sign(penX) * 9.15, 0.035, 0);
    } else if (type.includes("corner")) {
      this.activeSetPiece = "corner";
      this.setPieceTimerSec = 5.0;
      this.vanishingSprayGroup.visible = false;
    }
  }

  /**
   * Advances goal-net spring-wave vertex displacements and vanishing spray decay.
   */
  public update(deltaSec: number, ballPosition3D: [number, number, number]): void {
    // Auto-detect physical ball entry into either goal mouth
    const [bx, by, bz] = ballPosition3D;
    if (Math.abs(bx) > HALF_PITCH_L + 0.15 && Math.abs(bz) < GOAL_WIDTH / 2 && by < GOAL_HEIGHT) {
      const side = bx < 0 ? "home" : "away";
      if (side === "home" && this.homeRippleAmplitude < 0.15) {
        this.triggerGoalNetImpact("home", ballPosition3D, 0.9);
      } else if (side === "away" && this.awayRippleAmplitude < 0.15) {
        this.triggerGoalNetImpact("away", ballPosition3D, 0.9);
      }
    }

    // 1. Update Home Goal Net Vertices in-place
    if (this.homeRippleAmplitude > 0.005) {
      this.homeRipplePhase += deltaSec * 18.0;
      this.homeRippleAmplitude *= Math.exp(-deltaSec * 2.4);
      if (this.homeRippleAmplitude <= 0.005) {
        this.homeRippleAmplitude = 0;
      }
      this.deformNetGeometry(
        this.homeNetGeo,
        this.homeBaseVertices,
        this.homeRippleAmplitude,
        this.homeRipplePhase,
        this.homeImpactLocalZ,
        this.homeImpactLocalY,
        -1
      );
    }

    // 2. Update Away Goal Net Vertices in-place
    if (this.awayRippleAmplitude > 0.005) {
      this.awayRipplePhase += deltaSec * 18.0;
      this.awayRippleAmplitude *= Math.exp(-deltaSec * 2.4);
      if (this.awayRippleAmplitude <= 0.005) {
        this.awayRippleAmplitude = 0;
      }
      this.deformNetGeometry(
        this.awayNetGeo,
        this.awayBaseVertices,
        this.awayRippleAmplitude,
        this.awayRipplePhase,
        this.awayImpactLocalZ,
        this.awayImpactLocalY,
        -1
      );
    }

    // 3. Decay Vanishing Foam Spray
    if (this.setPieceTimerSec > 0) {
      this.setPieceTimerSec = Math.max(0, this.setPieceTimerSec - deltaSec);
      this.sprayMaterial.opacity = Math.min(0.92, (this.setPieceTimerSec / 8.0) * 0.92);
      if (this.setPieceTimerSec === 0) {
        this.activeSetPiece = "none";
        this.vanishingSprayGroup.visible = false;
        this.sprayMaterial.opacity = 0;
      }
    }
  }

  private deformNetGeometry(
    geo: THREE.PlaneGeometry,
    baseVerts: Float32Array,
    amplitude: number,
    phase: number,
    impactLocalX: number,
    impactLocalY: number,
    pushSign: number
  ): void {
    const posAttr = geo.attributes.position as THREE.BufferAttribute;
    const arr = posAttr.array as Float32Array;
    const vertexCount = posAttr.count;

    for (let i = 0; i < vertexCount; i++) {
      const vx = baseVerts[i * 3];
      const vy = baseVerts[i * 3 + 1];
      const vz = baseVerts[i * 3 + 2];

      // Pin the top crossbar edge (`vy >= GOAL_HEIGHT / 2 - 0.05`) and side posts
      const isPinnedEdge =
        vy >= GOAL_HEIGHT / 2 - 0.05 || Math.abs(vx) >= GOAL_WIDTH / 2 - 0.05;

      if (isPinnedEdge || amplitude === 0) {
        arr[i * 3] = vx;
        arr[i * 3 + 1] = vy;
        arr[i * 3 + 2] = vz;
      } else {
        const dist = Math.hypot(vx - impactLocalX, vy - impactLocalY);
        const radialEnvelope = Math.exp(-dist * 0.75);
        const wave = Math.sin(phase - dist * 2.2) * amplitude * radialEnvelope;
        // Bulge outward (away from pitch) + harmonic oscillation
        const bulge = Math.abs(wave) * 0.65 + wave * 0.35;
        arr[i * 3] = vx;
        arr[i * 3 + 1] = vy;
        arr[i * 3 + 2] = vz + pushSign * bulge;
      }
    }
    posAttr.needsUpdate = true;
  }

  public getSummary(): GoalNetAndSetPieceSummary {
    return {
      activeSetPiece: this.activeSetPiece,
      vanishingSprayVisible: this.vanishingSprayGroup.visible,
      vanishingSprayOpacity: Number(this.sprayMaterial.opacity.toFixed(2)),
      homeNetRippleIntensity: Number(this.homeRippleAmplitude.toFixed(3)),
      awayNetRippleIntensity: Number(this.awayRippleAmplitude.toFixed(3)),
      lastNetImpactSide: this.lastNetImpactSide,
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
    this.group.clear();
  }
}
