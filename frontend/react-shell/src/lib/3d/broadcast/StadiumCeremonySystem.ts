/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast (Phase 3)
 * StadiumCeremonySystem: 3D Pre-Match Walkout Carpet, Touchline Pyrotechnic
 * Flame Jets, Trophy Plinth, and Full-Time Championship Podium & Confetti Shower.
 *
 * Implements:
 * 1. Four canonical stadium ceremony states (`StadiumCeremonyState`):
 *    - `"inactive"`: Standard open-play match mode (zero ceremony draw calls).
 *    - `"pre_match_walkout"`: West Stand walkout red carpet, competition center-circle
 *      banner, touchline trophy plinth, and 6 touchline pyrotechnic flame jets.
 *    - `"goal_pyrotechnics"`: 4-second touchline & goal-end pyrotechnic flame burst on goals.
 *    - `"fulltime_trophy_presentation"`: Center-circle championship podium, golden cup,
 *      pyrotechnic jets, and a 600-particle GPU confetti shower.
 * 2. Zero Per-Frame Heap Allocation:
 *    - Confetti `Float32Array` buffer and pyrotechnic cone meshes are pre-allocated once.
 */

import * as THREE from "three";

export type StadiumCeremonyState =
  | "inactive"
  | "pre_match_walkout"
  | "goal_pyrotechnics"
  | "fulltime_trophy_presentation";

export interface StadiumCeremonySummary {
  ceremonyState: StadiumCeremonyState;
  pyroActive: boolean;
  confettiActive: boolean;
  trophyPlinthVisible: boolean;
  podiumVisible: boolean;
}

const CONFETTI_COUNT = 600;

export class StadiumCeremonySystem {
  public readonly group: THREE.Group;
  public readonly walkoutCarpetGroup: THREE.Group;
  public readonly pyroJetsGroup: THREE.Group;
  public readonly podiumGroup: THREE.Group;
  public readonly confettiPoints: THREE.Points;

  private ceremonyState: StadiumCeremonyState = "inactive";
  private stateTimerSec: number = 0;
  private elapsedSec: number = 0;

  private pyroCones: THREE.Mesh[] = [];
  private pyroFlameMat: THREE.MeshBasicMaterial;
  private confettiGeo: THREE.BufferGeometry;
  private confettiPositions: Float32Array;
  private confettiVelocities: Float32Array;
  private disposables: Array<{ dispose: () => void }> = [];

  constructor(scene: THREE.Scene) {
    this.group = new THREE.Group();
    this.group.name = "Phase3StadiumCeremonyGroup";
    scene.add(this.group);

    // 1. Pre-Match Walkout Carpet, Trophy Plinth & Center-Circle Crest Banner
    this.walkoutCarpetGroup = this.buildWalkoutCarpetAndPlinth();
    this.group.add(this.walkoutCarpetGroup);

    // 2. Touchline Pyrotechnic Flame Jets (6 emitters along the walkout corridor)
    const { pyroGroup, flameMat, cones } = this.buildPyroJets();
    this.pyroJetsGroup = pyroGroup;
    this.pyroFlameMat = flameMat;
    this.pyroCones = cones;
    this.group.add(this.pyroJetsGroup);

    // 3. Full-Time Championship Stage Podium & Golden Trophy
    this.podiumGroup = this.buildChampionshipPodium();
    this.group.add(this.podiumGroup);

    // 4. Pre-Allocated GPU Confetti Cannon Particle System (600 particles)
    this.confettiPositions = new Float32Array(CONFETTI_COUNT * 3);
    this.confettiVelocities = new Float32Array(CONFETTI_COUNT * 3);

    for (let i = 0; i < CONFETTI_COUNT; i++) {
      let s = (i * 2654435761) >>> 0;
      const rand = () => {
        s = (s * 1664525 + 1013904223) >>> 0;
        return (s & 0xfffffff) / 0xfffffff;
      };
      this.confettiPositions[i * 3] = (rand() - 0.5) * 28.0;
      this.confettiPositions[i * 3 + 1] = 2.0 + rand() * 18.0;
      this.confettiPositions[i * 3 + 2] = (rand() - 0.5) * 20.0;

      this.confettiVelocities[i * 3] = (rand() - 0.5) * 2.4;
      this.confettiVelocities[i * 3 + 1] = -(1.8 + rand() * 2.5);
      this.confettiVelocities[i * 3 + 2] = (rand() - 0.5) * 2.4;
    }

    this.confettiGeo = new THREE.BufferGeometry();
    this.confettiGeo.setAttribute(
      "position",
      new THREE.BufferAttribute(this.confettiPositions, 3)
    );
    const confettiMat = new THREE.PointsMaterial({
      color: 0xfacc15,
      size: 0.28,
      transparent: true,
      opacity: 0.92,
      depthWrite: false,
    });
    this.disposables.push(this.confettiGeo, confettiMat);

    this.confettiPoints = new THREE.Points(this.confettiGeo, confettiMat);
    this.confettiPoints.name = "ChampionshipConfettiPoints";
    this.confettiPoints.frustumCulled = false;
    this.group.add(this.confettiPoints);

    this.setCeremonyState("inactive");
  }

  private buildWalkoutCarpetAndPlinth(): THREE.Group {
    const g = new THREE.Group();
    g.name = "WalkoutCarpetAndPlinthGroup";

    // Walkout Red/Gold Carpet from West Stand Tunnel (z = 35m -> z = 14m)
    const carpetGeo = new THREE.PlaneGeometry(3.6, 21.0);
    const carpetMat = new THREE.MeshBasicMaterial({
      color: 0x0f172a,
      side: THREE.DoubleSide,
    });
    const goldTrimGeo = new THREE.PlaneGeometry(3.9, 21.0);
    const goldMat = new THREE.MeshBasicMaterial({
      color: 0xf59e0b,
      side: THREE.DoubleSide,
    });
    const centerTarpGeo = new THREE.CircleGeometry(8.5, 32);
    const centerTarpMat = new THREE.MeshBasicMaterial({
      color: 0x10b981,
      transparent: true,
      opacity: 0.78,
      side: THREE.DoubleSide,
    });
    const plinthGeo = new THREE.CylinderGeometry(0.45, 0.55, 1.15, 12);
    const trophyCupGeo = new THREE.CylinderGeometry(0.28, 0.14, 0.68, 12);
    this.disposables.push(
      carpetGeo,
      carpetMat,
      goldTrimGeo,
      goldMat,
      centerTarpGeo,
      centerTarpMat,
      plinthGeo,
      trophyCupGeo
    );

    const trim = new THREE.Mesh(goldTrimGeo, goldMat);
    trim.rotation.x = -Math.PI / 2;
    trim.position.set(0, 0.025, 24.5);
    g.add(trim);

    const carpet = new THREE.Mesh(carpetGeo, carpetMat);
    carpet.rotation.x = -Math.PI / 2;
    carpet.position.set(0, 0.03, 24.5);
    g.add(carpet);

    const centerTarp = new THREE.Mesh(centerTarpGeo, centerTarpMat);
    centerTarp.rotation.x = -Math.PI / 2;
    centerTarp.position.set(0, 0.035, 0);
    g.add(centerTarp);

    const plinth = new THREE.Mesh(plinthGeo, carpetMat);
    plinth.position.set(2.8, 0.575, 29.5);
    g.add(plinth);

    const trophy = new THREE.Mesh(trophyCupGeo, goldMat);
    trophy.position.set(2.8, 1.48, 29.5);
    g.add(trophy);

    return g;
  }

  private buildPyroJets(): {
    pyroGroup: THREE.Group;
    flameMat: THREE.MeshBasicMaterial;
    cones: THREE.Mesh[];
  } {
    const pyroGroup = new THREE.Group();
    pyroGroup.name = "TouchlinePyroJetsGroup";

    const coneGeo = new THREE.ConeGeometry(0.42, 3.4, 8, 1, true);
    const flameMat = new THREE.MeshBasicMaterial({
      color: 0xf97316,
      transparent: true,
      opacity: 0.88,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    this.disposables.push(coneGeo, flameMat);

    const cones: THREE.Mesh[] = [];
    const xOffsets = [-9.0, -4.5, -2.2, 2.2, 4.5, 9.0];
    for (let i = 0; i < xOffsets.length; i++) {
      const cone = new THREE.Mesh(coneGeo, flameMat);
      cone.position.set(xOffsets[i], 1.7, 31.5);
      pyroGroup.add(cone);
      cones.push(cone);
    }

    return { pyroGroup, flameMat, cones };
  }

  private buildChampionshipPodium(): THREE.Group {
    const podiumGroup = new THREE.Group();
    podiumGroup.name = "ChampionshipPodiumGroup";

    const stageGeo = new THREE.BoxGeometry(9.2, 0.45, 4.2);
    const stageMat = new THREE.MeshLambertMaterial({ color: 0x0f172a });
    const archGeo = new THREE.BoxGeometry(9.6, 3.8, 0.35);
    const goldMat = new THREE.MeshBasicMaterial({ color: 0xfacc15 });
    const cupGeo = new THREE.CylinderGeometry(0.34, 0.18, 0.85, 14);
    this.disposables.push(stageGeo, stageMat, archGeo, goldMat, cupGeo);

    const stage = new THREE.Mesh(stageGeo, stageMat);
    stage.position.set(0, 0.225, 0);
    podiumGroup.add(stage);

    const arch = new THREE.Mesh(archGeo, goldMat);
    arch.position.set(0, 2.1, -1.9);
    podiumGroup.add(arch);

    const cup = new THREE.Mesh(cupGeo, goldMat);
    cup.position.set(0, 1.15, 0.8);
    podiumGroup.add(cup);

    return podiumGroup;
  }

  public setCeremonyState(
    state: StadiumCeremonyState,
    durationSec: number = 0
  ): void {
    this.ceremonyState = state;
    this.stateTimerSec = durationSec;

    this.walkoutCarpetGroup.visible = state === "pre_match_walkout";
    this.pyroJetsGroup.visible =
      state === "pre_match_walkout" ||
      state === "goal_pyrotechnics" ||
      state === "fulltime_trophy_presentation";
    this.podiumGroup.visible = state === "fulltime_trophy_presentation";
    this.confettiPoints.visible = state === "fulltime_trophy_presentation";
  }

  public getCeremonyState(): StadiumCeremonyState {
    return this.ceremonyState;
  }

  /**
   * Triggers ceremony transitions from match events (`walkout`, `goal`, `fulltime`).
   */
  public triggerMatchEvent(eventType: string): void {
    const type = (eventType || "").toLowerCase();
    if (type.includes("walkout")) {
      this.setCeremonyState("pre_match_walkout", 10.0);
    } else if (type === "goal") {
      this.setCeremonyState("goal_pyrotechnics", 4.5);
    } else if (type.includes("fulltime") || type.includes("full_time") || type.includes("trophy")) {
      this.setCeremonyState("fulltime_trophy_presentation", 15.0);
    } else if (type.includes("kickoff")) {
      this.setCeremonyState("inactive", 0);
    }
  }

  public update(deltaSec: number): void {
    this.elapsedSec += deltaSec;

    if (this.stateTimerSec > 0) {
      this.stateTimerSec = Math.max(0, this.stateTimerSec - deltaSec);
      if (this.stateTimerSec === 0) {
        this.setCeremonyState("inactive", 0);
        return;
      }
    }

    if (this.ceremonyState === "inactive") {
      return;
    }

    // 1. Animate Pyrotechnic Flame Jets
    if (this.pyroJetsGroup.visible) {
      for (let i = 0; i < this.pyroCones.length; i++) {
        const cone = this.pyroCones[i];
        const flicker = 0.78 + Math.sin(this.elapsedSec * 19.0 + i * 1.3) * 0.28;
        cone.scale.set(1.0, Math.max(0.35, flicker), 1.0);
      }
      this.pyroFlameMat.opacity = 0.72 + Math.sin(this.elapsedSec * 23.0) * 0.18;
    }

    // 2. Animate Confetti Shower in-place
    if (this.confettiPoints.visible) {
      for (let i = 0; i < CONFETTI_COUNT; i++) {
        const idx = i * 3;
        let x =
          this.confettiPositions[idx] +
          this.confettiVelocities[idx] * deltaSec +
          Math.sin(this.elapsedSec * 3.5 + i) * 0.03;
        let y = this.confettiPositions[idx + 1] + this.confettiVelocities[idx + 1] * deltaSec;
        let z =
          this.confettiPositions[idx + 2] +
          this.confettiVelocities[idx + 2] * deltaSec +
          Math.cos(this.elapsedSec * 3.1 + i) * 0.03;

        if (y < 0.1) {
          y = 18.0;
          x = ((i % 29) - 14) * 0.9;
          z = ((i % 19) - 9) * 0.9;
        }

        this.confettiPositions[idx] = x;
        this.confettiPositions[idx + 1] = y;
        this.confettiPositions[idx + 2] = z;
      }
      (this.confettiGeo.attributes.position as THREE.BufferAttribute).needsUpdate = true;
    }
  }

  public getSummary(): StadiumCeremonySummary {
    return {
      ceremonyState: this.ceremonyState,
      pyroActive: this.pyroJetsGroup.visible,
      confettiActive: this.confettiPoints.visible,
      trophyPlinthVisible: this.walkoutCarpetGroup.visible,
      podiumVisible: this.podiumGroup.visible,
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
    this.pyroCones = [];
    this.group.clear();
  }
}
