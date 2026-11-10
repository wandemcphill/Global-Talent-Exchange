/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast Arena
 * Milestone 2 & Phase 2 — Comprehensive Tiered Stadium, Club Identity & Crowd Wave Expansion
 *
 * Implements:
 * 1. Realistic FIFA Pitch Geometry:
 *    - 105m x 68m FIFA pitch with 10 alternating turf stripes and green runoff buffer.
 *    - Accurate chalk markings: touchlines, goal lines, halfway line, center circle & spot,
 *      penalty areas (16.5m x 40.32m), goal boxes (5.5m x 18.32m), penalty spots (11m),
 *      penalty arcs ("D"), and 4 corner arcs.
 *    - 4 realistic corner flags (1.5m flexible pole with fluttering fabric flags).
 *    - 3D FIFA goal cages with rounded posts, crossbar, net support stanchions, and 3D net mesh.
 * 2. Phase 2 Tiered & Procedural Stadium Stands Architecture (`StadiumTier`: 1 | 2 | 3):
 *    - Tier 1 (Community Municipal Ground — 12,500 cap): Single-tier lower bowl, West cantilever roof, 1 scoreboard.
 *    - Tier 2 (Regional Championship Arena — 36,000 cap): 2-tier East & West stands, 4 stand roofs, 2 jumbotrons.
 *    - Tier 3 (Sovereign Super-Arena — 68,000 cap): Full multi-tier bowl, VIP Panoramic Executive Skyboxes,
 *      4 architectural corner towers, 3 HD jumbotrons, and custom club identity fascia banners.
 * 3. Crowd Presentation & Phase 2 Radial Mexican Wave:
 *    - Tiered spectator seating with multi-colored home and away supporter crowd blocks.
 *    - Instanced 3D supporter crowd with event-driven surge reactions and radial stadium wave propagation.
 * 4. Floodlights & Environmental Lighting:
 *    - 4 corner floodlight towers (36m tall) with 3D steel lattice pylons and 4x4 LED lamp arrays.
 * 5. Touchlines, Technical Areas & Dugouts:
 *    - Home and away dashed chalk technical coaching boxes and curved ergonomic dugouts.
 * 6. Player Tunnel & Stadium Entrances:
 *    - Central walkout tunnel portal embedded into the West Grandstand.
 * 7. Dynamic LED Perimeter Advertising Boards:
 *    - Wrapping pitch perimeter LED boards driven by `StadiumAdvertisingNetwork`.
 */

import * as THREE from "three";
import { FIFA_PITCH_DIMENSIONS } from "./matchCoordinates";
import { SpectatorSafeTeamView } from "./spectatorContract";
import type { DeviceQualityTier } from "../GtexSceneTypes";
import {
  StadiumAdvertisingNetwork,
  type StadiumAdvertisingNetworkOptions,
  type StadiumLedCampaign,
} from "./StadiumAdvertisingNetwork";
import { AssetStreamingCache } from "./AssetStreamingCache";

/**
 * Parts of the downloaded bowl that duplicate the live pitch:
 * turf, markings, goals, dugouts, and the LED perimeter.
 * The bowl keeps the stands, roof shell, floodlights, and concourse.
 * Roof trusses are hidden because the broadcast camera sits inside that steel.
 */
export function isStadiumBowlPitchSurface(name: string): boolean {
  const normalized = name.toLowerCase();
  return (
    normalized.includes("grass") ||
    normalized.includes("pitch") ||
    normalized.includes("goal") ||
    normalized === "dugouts" ||
    normalized.includes("perimeter") ||
    normalized.includes("truss")
  );
}

export type StadiumCrowdReactionType =
  | "calm"
  | "attack"
  | "near_miss"
  | "save"
  | "goal"
  | "red_card"
  | "fulltime";

export type StadiumTier = 1 | 2 | 3;

export interface StadiumTierProfile {
  tier: StadiumTier;
  tierKey: "tier_1_community" | "tier_2_regional" | "tier_3_sovereign";
  label: string;
  shortLabel: string;
  capacity: number;
  hasUpperTiers: boolean;
  hasVipSkyboxes: boolean;
  hasFullRoofCanopy: boolean;
  hasCornerTowers: boolean;
  jumbotronCount: number;
  floodlightHeightM: number;
}

export const STADIUM_TIER_PROFILES: Readonly<Record<StadiumTier, StadiumTierProfile>> = {
  1: {
    tier: 1,
    tierKey: "tier_1_community",
    label: "Tier 1 • Community Municipal Ground",
    shortLabel: "T1 • 12.5K",
    capacity: 12500,
    hasUpperTiers: false,
    hasVipSkyboxes: false,
    hasFullRoofCanopy: false,
    hasCornerTowers: false,
    jumbotronCount: 1,
    floodlightHeightM: 26,
  },
  2: {
    tier: 2,
    tierKey: "tier_2_regional",
    label: "Tier 2 • Regional Championship Arena",
    shortLabel: "T2 • 36K",
    capacity: 36000,
    hasUpperTiers: true,
    hasVipSkyboxes: false,
    hasFullRoofCanopy: true,
    hasCornerTowers: false,
    jumbotronCount: 2,
    floodlightHeightM: 32,
  },
  3: {
    tier: 3,
    tierKey: "tier_3_sovereign",
    label: "Tier 3 • Sovereign Super-Arena",
    shortLabel: "T3 • 68K",
    capacity: 68000,
    hasUpperTiers: true,
    hasVipSkyboxes: true,
    hasFullRoofCanopy: true,
    hasCornerTowers: true,
    jumbotronCount: 3,
    floodlightHeightM: 36,
  },
};

export interface StadiumArenaOptions {
  homeTeam?: SpectatorSafeTeamView;
  awayTeam?: SpectatorSafeTeamView;
  qualityTier?: DeviceQualityTier;
  stadiumTier?: StadiumTier;
  stadiumName?: string;
  competitionName?: string;
  matchId?: string;
  attendancePct?: number; // 0..100
  adNetworkOptions?: StadiumAdvertisingNetworkOptions;
  initialCampaigns?: StadiumLedCampaign[];
}

interface SupporterInstanceMeta {
  baseX: number;
  baseY: number;
  baseZ: number;
  rotY: number;
  phase: number;
  angleRad: number;
  side: "home" | "away" | "neutral";
  scale: number;
}

export class StadiumArenaEnvironment {
  public readonly group: THREE.Group;
  public readonly pitchGroup: THREE.Group;
  public readonly stadiumGroup: THREE.Group;
  public readonly lightingGroup: THREE.Group;
  public readonly adBoardsGroup: THREE.Group;
  public readonly crowdGroup: THREE.Group;

  private qualityTier: DeviceQualityTier;
  private stadiumTier: StadiumTier;
  private stadiumName: string;
  private homeTeam: SpectatorSafeTeamView;
  private awayTeam: SpectatorSafeTeamView;
  private competitionName: string;
  private adNetwork: StadiumAdvertisingNetwork;
  private adTouchlineTexture: THREE.CanvasTexture | null = null;
  private scoreboardCanvas: HTMLCanvasElement | null = null;
  private scoreboardContext: CanvasRenderingContext2D | null = null;
  private scoreboardTexture: THREE.CanvasTexture | null = null;
  private lastScoreboardKey: string = "";
  private clubBannerCanvas: HTMLCanvasElement | null = null;
  private clubBannerContext: CanvasRenderingContext2D | null = null;
  private clubBannerTexture: THREE.CanvasTexture | null = null;
  private pitchTurfMat: THREE.MeshLambertMaterial | null = null;
  private pitchMesh: THREE.Mesh | null = null;
  private externalCrowdOffsetFn: ((x: number, z: number) => number) | null = null;
  private pitchRunoffMat: THREE.MeshLambertMaterial | null = null;
  private homeCrowdMat: THREE.MeshLambertMaterial | null = null;
  private awayCrowdMat: THREE.MeshLambertMaterial | null = null;
  private bannerMat: THREE.MeshBasicMaterial | null = null;
  private supporterMesh: THREE.InstancedMesh | null = null;
  private supporterMeta: SupporterInstanceMeta[] = [];
  private upperTierObjects: THREE.Object3D[] = [];
  private vipSkyboxObjects: THREE.Object3D[] = [];
  private secondaryRoofObjects: THREE.Object3D[] = [];
  private cornerTowerObjects: THREE.Object3D[] = [];
  private secondaryJumbotronObjects: THREE.Object3D[] = [];
  private crowdReactionType: StadiumCrowdReactionType = "calm";
  private crowdReactionSide: "home" | "away" | "both" = "both";
  private crowdReactionIntensity: number = 0.15;
  private crowdReactionTimerSec: number = 0;
  private crowdWaveTimerSec: number = 0;
  private elapsedSec: number = 0;
  private disposables: Array<{ dispose: () => void }> = [];
  private disposed = false;
  private broadcastBowl: THREE.Object3D | null = null;

  constructor(scene: THREE.Scene, options: StadiumArenaOptions = {}) {
    this.qualityTier = options.qualityTier || "high";
    this.stadiumTier = options.stadiumTier || 3;
    this.stadiumName = options.stadiumName || "GTEX National Arena";
    this.competitionName = options.competitionName || "GTEX PREMIER BROADCAST";
    this.homeTeam = options.homeTeam || {
      team_id: "home-default",
      team_name: "Lagos Atlas FC",
      short_name: "LAG",
      formation: "4-3-3",
      primary_color: "#00E676",
      secondary_color: "#1B5E20",
      accent_color: "#FFFFFF",
      goalkeeper_color: "#FFD600",
    };
    this.awayTeam = options.awayTeam || {
      team_id: "away-default",
      team_name: "Abuja Sovereign SC",
      short_name: "ABJ",
      formation: "4-4-2",
      primary_color: "#2979FF",
      secondary_color: "#0D47A1",
      accent_color: "#FFFFFF",
      goalkeeper_color: "#FF3D00",
    };

    this.adNetwork = new StadiumAdvertisingNetwork({
      enableNetworkFetch: false,
      ...options.adNetworkOptions,
    });
    this.adNetwork.setMatchContext({
      matchId: options.matchId,
      homeTeamId: this.homeTeam.team_id,
      homeTeamName: this.homeTeam.team_name,
      homePrimaryColor: this.homeTeam.primary_color,
      awayTeamId: this.awayTeam.team_id,
      awayTeamName: this.awayTeam.team_name,
      awayPrimaryColor: this.awayTeam.primary_color,
      competitionName: this.competitionName,
    });
    if (options.initialCampaigns && options.initialCampaigns.length > 0) {
      this.adNetwork.setCampaigns(options.initialCampaigns);
    }

    this.group = new THREE.Group();
    this.group.name = "GTEX_Stadium_Arena_Environment";

    this.pitchGroup = new THREE.Group();
    this.pitchGroup.name = "Pitch_Markings_Group";

    this.stadiumGroup = new THREE.Group();
    this.stadiumGroup.name = "Stadium_Stands_Architecture";

    this.lightingGroup = new THREE.Group();
    this.lightingGroup.name = "Stadium_Lighting_Group";

    this.adBoardsGroup = new THREE.Group();
    this.adBoardsGroup.name = "LED_Perimeter_Ad_Boards";

    this.crowdGroup = new THREE.Group();
    this.crowdGroup.name = "Crowd_Presentation_Group";

    this.group.add(this.pitchGroup);
    this.group.add(this.stadiumGroup);
    this.group.add(this.lightingGroup);
    this.group.add(this.adBoardsGroup);
    this.group.add(this.crowdGroup);

    scene.add(this.group);

    // Build all subsystem components
    this.buildPitchAndMarkings();
    this.buildGoals();
    this.buildCornerFlags();
    this.buildTechnicalAreasAndDugouts();
    this.buildPlayerTunnelAndDressingAccess();
    this.buildPerimeterAdBoards();
    this.buildGrandstands();
    this.buildCrowd(options.attendancePct ?? 94);
    this.buildFloodlightsAndEnvironment(scene);
    this.applyStadiumTierVisibility(this.stadiumTier);

    // Freeze world matrices on static stadium architecture while keeping animated crowd unlocked
    this.group.updateMatrixWorld(true);
    this.group.traverse((obj) => {
      if (obj !== this.group && obj !== this.crowdGroup && !this.crowdGroup.children.includes(obj)) {
        obj.matrixAutoUpdate = false;
      }
    });
  }

  public getPitchMaterials(): {
    pitchTurfMat: THREE.MeshLambertMaterial | null;
    pitchRunoffMat: THREE.MeshLambertMaterial | null;
  } {
    return {
      pitchTurfMat: this.pitchTurfMat,
      pitchRunoffMat: this.pitchRunoffMat,
    };
  }

  /**
   * Swaps the pitch surface to an externally owned material (e.g. the PBR turf shader).
   * The caller keeps ownership and disposes it; the original Lambert material stays
   * tracked for weather tinting compatibility and disposal.
   */
  public applyPitchTurfMaterial(material: THREE.Material): void {
    if (this.pitchMesh) {
      this.pitchMesh.material = material;
    }
  }

  /**
   * Registers an additional per-supporter vertical offset (metres) evaluated each frame
   * from the supporter's stadium-space (x, z). Used by the crowd choreography system so
   * its La Ola / celebration waves physically move the instanced crowd.
   */
  public setExternalCrowdOffsetFn(fn: ((x: number, z: number) => number) | null): void {
    this.externalCrowdOffsetFn = fn;
  }

  // ---------------------------------------------------------------------------
  // 1. Realistic Football Pitch Geometry & FIFA Markings
  // ---------------------------------------------------------------------------
  private buildPitchAndMarkings(): void {
    const pLength = FIFA_PITCH_DIMENSIONS.length;
    const pWidth = FIFA_PITCH_DIMENSIONS.width;
    const halfL = pLength / 2;
    const halfW = pWidth / 2;

    // A. Pitch Ground Turf (105m x 68m)
    const pitchGeo = new THREE.PlaneGeometry(pLength, pWidth, 1, 1);
    const pitchMat = new THREE.MeshLambertMaterial({
      color: 0x154726,
      side: THREE.DoubleSide,
    });
    this.pitchTurfMat = pitchMat;
    this.disposables.push(pitchGeo, pitchMat);
    const pitchMesh = new THREE.Mesh(pitchGeo, pitchMat);
    this.pitchMesh = pitchMesh;
    pitchMesh.rotation.x = -Math.PI / 2;
    pitchMesh.receiveShadow = true;
    this.pitchGroup.add(pitchMesh);

    // B. Pitch Runoff Buffer Turf (extending 7m beyond touchlines, 9m behind goal lines)
    const runoffGeo = new THREE.PlaneGeometry(pLength + 18, pWidth + 14, 1, 1);
    const runoffMat = new THREE.MeshLambertMaterial({
      color: 0x0e361b,
      side: THREE.DoubleSide,
    });
    this.pitchRunoffMat = runoffMat;
    this.disposables.push(runoffGeo, runoffMat);
    const runoffMesh = new THREE.Mesh(runoffGeo, runoffMat);
    runoffMesh.rotation.x = -Math.PI / 2;
    runoffMesh.position.y = -0.01;
    runoffMesh.receiveShadow = true;
    this.pitchGroup.add(runoffMesh);

    // C. Mowing Stripes (10 alternating turf stripes)
    const stripeCount = 10;
    const stripeWidth = pLength / stripeCount;
    for (let i = 0; i < stripeCount; i++) {
      if (i % 2 === 0) {
        const stripeGeo = new THREE.PlaneGeometry(stripeWidth, pWidth);
        const stripeMat = new THREE.MeshBasicMaterial({
          color: 0x19522c,
          transparent: true,
          opacity: 0.38,
        });
        this.disposables.push(stripeGeo, stripeMat);
        const stripeMesh = new THREE.Mesh(stripeGeo, stripeMat);
        stripeMesh.rotation.x = -Math.PI / 2;
        stripeMesh.position.set(-halfL + stripeWidth * (i + 0.5), 0.008, 0);
        this.pitchGroup.add(stripeMesh);
      }
    }

    // D. White Chalk Lines
    const lineMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    this.disposables.push(lineMat);
    const lineWidth = 0.14;

    const addChalkLine = (w: number, d: number, x: number, z: number) => {
      const g = new THREE.PlaneGeometry(w, d);
      this.disposables.push(g);
      const m = new THREE.Mesh(g, lineMat);
      m.rotation.x = -Math.PI / 2;
      m.position.set(x, 0.015, z);
      this.pitchGroup.add(m);
    };

    // Touchlines & Goal lines
    addChalkLine(pLength, lineWidth, 0, -halfW); // Top touchline
    addChalkLine(pLength, lineWidth, 0, halfW);  // Bottom touchline
    addChalkLine(lineWidth, pWidth, -halfL, 0);  // Left goal line
    addChalkLine(lineWidth, pWidth, halfL, 0);   // Right goal line
    addChalkLine(lineWidth, pWidth, 0, 0);       // Halfway line

    // Center Circle (radius 9.15m) & Center Spot
    const circleCurve = new THREE.EllipseCurve(0, 0, 9.15, 9.15, 0, 2 * Math.PI, false, 0);
    const circlePts = circleCurve.getPoints(64);
    const circleGeo = new THREE.BufferGeometry().setFromPoints(
      circlePts.map((p) => new THREE.Vector3(p.x, 0.016, p.y))
    );
    const circleLineMat = new THREE.LineBasicMaterial({ color: 0xffffff, linewidth: 2 });
    this.disposables.push(circleGeo, circleLineMat);
    const circleLine = new THREE.Line(circleGeo, circleLineMat);
    this.pitchGroup.add(circleLine);

    // Center spot disc
    const spotGeo = new THREE.CircleGeometry(0.24, 16);
    this.disposables.push(spotGeo);
    const centerSpot = new THREE.Mesh(spotGeo, lineMat);
    centerSpot.rotation.x = -Math.PI / 2;
    centerSpot.position.set(0, 0.016, 0);
    this.pitchGroup.add(centerSpot);

    // E. Penalty Areas (16.5m x 40.32m) & Goal Areas (5.5m x 18.32m) on both ends
    const penL = FIFA_PITCH_DIMENSIONS.penaltyAreaLength; // 16.5m
    const penW = FIFA_PITCH_DIMENSIONS.penaltyAreaWidth;  // 40.32m
    const goalAreaL = 5.5;
    const goalAreaW = 18.32;

    const buildBoxMarkings = (isLeft: boolean) => {
      const sign = isLeft ? -1 : 1;
      const goalLineX = sign * halfL;
      const penFrontX = goalLineX - sign * penL;
      const goalFrontX = goalLineX - sign * goalAreaL;

      // Penalty box outer boundary
      addChalkLine(penL, lineWidth, goalLineX - sign * (penL / 2), -penW / 2);
      addChalkLine(penL, lineWidth, goalLineX - sign * (penL / 2), penW / 2);
      addChalkLine(lineWidth, penW, penFrontX, 0);

      // Goal area (6-yard box)
      addChalkLine(goalAreaL, lineWidth, goalLineX - sign * (goalAreaL / 2), -goalAreaW / 2);
      addChalkLine(goalAreaL, lineWidth, goalLineX - sign * (goalAreaL / 2), goalAreaW / 2);
      addChalkLine(lineWidth, goalAreaW, goalFrontX, 0);

      // Penalty Spot (11m from goal line)
      const spotX = goalLineX - sign * FIFA_PITCH_DIMENSIONS.penaltySpotDistance;
      const penSpot = new THREE.Mesh(spotGeo, lineMat);
      penSpot.rotation.x = -Math.PI / 2;
      penSpot.position.set(spotX, 0.016, 0);
      this.pitchGroup.add(penSpot);

      // Penalty Arc (the "D" outside the box, radius 9.15m from spot)
      const startAngle = isLeft ? -Math.PI * 0.29 : Math.PI - Math.PI * 0.29;
      const endAngle = isLeft ? Math.PI * 0.29 : Math.PI + Math.PI * 0.29;
      const arcCurve = new THREE.EllipseCurve(spotX, 0, 9.15, 9.15, startAngle, endAngle, false, 0);
      const arcPts = arcCurve.getPoints(24);
      const arcGeo = new THREE.BufferGeometry().setFromPoints(
        arcPts.map((p) => new THREE.Vector3(p.x, 0.016, p.y))
      );
      this.disposables.push(arcGeo);
      const arcLine = new THREE.Line(arcGeo, circleLineMat);
      this.pitchGroup.add(arcLine);
    };

    buildBoxMarkings(true);
    buildBoxMarkings(false);

    // F. Corner Arcs (1m radius at all 4 corners)
    const cornerCorners: Array<{ x: number; z: number; start: number; end: number }> = [
      { x: -halfL, z: -halfW, start: 0, end: Math.PI / 2 },
      { x: halfL, z: -halfW, start: Math.PI / 2, end: Math.PI },
      { x: halfL, z: halfW, start: Math.PI, end: Math.PI * 1.5 },
      { x: -halfL, z: halfW, start: Math.PI * 1.5, end: Math.PI * 2 },
    ];
    cornerCorners.forEach((c) => {
      const cCurve = new THREE.EllipseCurve(c.x, c.z, 1.0, 1.0, c.start, c.end, false, 0);
      const cPts = cCurve.getPoints(12);
      const cGeo = new THREE.BufferGeometry().setFromPoints(
        cPts.map((p) => new THREE.Vector3(p.x, 0.016, p.y))
      );
      this.disposables.push(cGeo);
      const cLine = new THREE.Line(cGeo, circleLineMat);
      this.pitchGroup.add(cLine);
    });
  }

  // ---------------------------------------------------------------------------
  // 2. 3D FIFA Goal Cages & Nets
  // ---------------------------------------------------------------------------
  private buildGoals(): void {
    const halfL = FIFA_PITCH_DIMENSIONS.length / 2;
    const gW = FIFA_PITCH_DIMENSIONS.goalWidth; // 7.32m
    const gH = FIFA_PITCH_DIMENSIONS.goalHeight; // 2.44m
    const postRadius = 0.06;

    const postMat = new THREE.MeshStandardMaterial({
      color: 0xf8fafc,
      roughness: 0.25,
      metalness: 0.2,
    });
    const netMat = new THREE.MeshBasicMaterial({
      color: 0xf1f5f9,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });
    const stanchionMat = new THREE.MeshStandardMaterial({
      color: 0x94a3b8,
      metalness: 0.5,
    });
    this.disposables.push(postMat, netMat, stanchionMat);

    const createGoalCage = (isLeft: boolean) => {
      const gGroup = new THREE.Group();
      const sign = isLeft ? -1 : 1;
      const gx = sign * halfL;

      // Upright Posts
      const postGeo = new THREE.CylinderGeometry(postRadius, postRadius, gH, 12);
      this.disposables.push(postGeo);
      const p1 = new THREE.Mesh(postGeo, postMat);
      p1.position.set(gx, gH / 2, -gW / 2);
      p1.castShadow = true;
      const p2 = new THREE.Mesh(postGeo, postMat);
      p2.position.set(gx, gH / 2, gW / 2);
      p2.castShadow = true;
      gGroup.add(p1, p2);

      // Horizontal Crossbar
      const barGeo = new THREE.CylinderGeometry(postRadius, postRadius, gW, 12);
      this.disposables.push(barGeo);
      const crossbar = new THREE.Mesh(barGeo, postMat);
      crossbar.rotation.x = Math.PI / 2;
      crossbar.position.set(gx, gH, 0);
      crossbar.castShadow = true;
      gGroup.add(crossbar);

      // Net Box (2.2m depth)
      const netBoxGeo = new THREE.BoxGeometry(2.2, gH, gW);
      this.disposables.push(netBoxGeo);
      const net = new THREE.Mesh(netBoxGeo, netMat);
      net.position.set(gx + sign * 1.1, gH / 2, 0);
      gGroup.add(net);

      // Diagonal Stanchion tension poles behind net
      const stanchionGeo = new THREE.CylinderGeometry(0.04, 0.04, 3.2, 8);
      this.disposables.push(stanchionGeo);
      const s1 = new THREE.Mesh(stanchionGeo, stanchionMat);
      s1.position.set(gx + sign * 1.6, gH * 0.6, -gW / 2);
      s1.rotation.z = sign * 0.45;
      const s2 = new THREE.Mesh(stanchionGeo, stanchionMat);
      s2.position.set(gx + sign * 1.6, gH * 0.6, gW / 2);
      s2.rotation.z = sign * 0.45;
      gGroup.add(s1, s2);

      this.pitchGroup.add(gGroup);
    };

    createGoalCage(true);
    createGoalCage(false);
  }

  // ---------------------------------------------------------------------------
  // 3. Realistic Corner Flags
  // ---------------------------------------------------------------------------
  private buildCornerFlags(): void {
    const halfL = FIFA_PITCH_DIMENSIONS.length / 2;
    const halfW = FIFA_PITCH_DIMENSIONS.width / 2;
    const poleGeo = new THREE.CylinderGeometry(0.02, 0.02, 1.5, 8);
    const poleMat = new THREE.MeshStandardMaterial({ color: 0xfacc15, roughness: 0.4 });
    const flagGeo = new THREE.PlaneGeometry(0.4, 0.28);
    const flagMat = new THREE.MeshLambertMaterial({
      color: 0xef4444,
      side: THREE.DoubleSide,
    });
    this.disposables.push(poleGeo, poleMat, flagGeo, flagMat);

    const corners = [
      [-halfL, -halfW],
      [halfL, -halfW],
      [-halfL, halfW],
      [halfL, halfW],
    ];

    corners.forEach(([cx, cz]) => {
      const flagGroup = new THREE.Group();
      flagGroup.position.set(cx, 0, cz);

      const pole = new THREE.Mesh(poleGeo, poleMat);
      pole.position.y = 0.75;
      flagGroup.add(pole);

      const flag = new THREE.Mesh(flagGeo, flagMat);
      flag.position.set(0.2, 1.35, 0);
      flagGroup.add(flag);

      this.pitchGroup.add(flagGroup);
    });
  }

  // ---------------------------------------------------------------------------
  // 4. Touchlines, Technical Areas & Modern Ergonomic Dugouts
  // ---------------------------------------------------------------------------
  private buildTechnicalAreasAndDugouts(): void {
    const halfW = FIFA_PITCH_DIMENSIONS.width / 2;
    const touchlineZ = halfW + 1.2;
    const dugoutZ = halfW + 4.5;

    // Technical coaching dashed line boxes
    const techAreaMat = new THREE.LineDashedMaterial({
      color: 0xffffff,
      dashSize: 0.5,
      gapSize: 0.3,
    });
    this.disposables.push(techAreaMat);

    const createTechBox = (centerX: number) => {
      const hw = 6.0;
      const pts = [
        new THREE.Vector3(centerX - hw, 0.02, touchlineZ),
        new THREE.Vector3(centerX + hw, 0.02, touchlineZ),
        new THREE.Vector3(centerX + hw, 0.02, touchlineZ + 2.5),
        new THREE.Vector3(centerX - hw, 0.02, touchlineZ + 2.5),
        new THREE.Vector3(centerX - hw, 0.02, touchlineZ),
      ];
      const g = new THREE.BufferGeometry().setFromPoints(pts);
      this.disposables.push(g);
      const line = new THREE.Line(g, techAreaMat);
      line.computeLineDistances();
      this.stadiumGroup.add(line);
    };

    createTechBox(-14); // Home Technical Area
    createTechBox(14);  // Away Technical Area

    // Modern Curved Dugouts
    const createDugout = (centerX: number, isHome: boolean) => {
      const dugoutGroup = new THREE.Group();
      dugoutGroup.position.set(centerX, 0, dugoutZ);

      // Raised rubber platform
      const platGeo = new THREE.BoxGeometry(11, 0.15, 2.5);
      const platMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.8 });
      this.disposables.push(platGeo, platMat);
      const platform = new THREE.Mesh(platGeo, platMat);
      platform.position.y = 0.075;
      dugoutGroup.add(platform);

      const canopySegments = this.qualityTier === "low" ? 8 : 12;
      const canopyGeo = new THREE.CylinderGeometry(1.4, 1.4, 11, canopySegments, 1, true, 0, Math.PI);
      const canopyMat =
        this.qualityTier === "low"
          ? new THREE.MeshLambertMaterial({
              color: 0x0f172a,
              transparent: true,
              opacity: 0.5,
            })
          : new THREE.MeshStandardMaterial({
              color: 0x0f172a,
              transparent: true,
              opacity: 0.48,
              roughness: 0.15,
              metalness: 0.75,
            });
      this.disposables.push(canopyGeo, canopyMat);
      const canopy = new THREE.Mesh(canopyGeo, canopyMat);
      canopy.rotation.z = Math.PI / 2;
      canopy.rotation.y = Math.PI / 2;
      canopy.position.set(0, 1.4, 0);
      dugoutGroup.add(canopy);

      if (this.qualityTier !== "low") {
        const ribMat = new THREE.MeshLambertMaterial({ color: 0x94a3b8 });
        const ribGeo = new THREE.TorusGeometry(1.42, 0.03, 6, 12, Math.PI);
        this.disposables.push(ribMat, ribGeo);
        for (let i = -5; i <= 5; i += 2.5) {
          const rib = new THREE.Mesh(ribGeo, ribMat);
          rib.rotation.y = Math.PI / 2;
          rib.position.set(i, 1.4, 0);
          dugoutGroup.add(rib);
        }
      }

      const seatColor = isHome
        ? new THREE.Color(this.homeTeam.primary_color)
        : new THREE.Color(this.awayTeam.primary_color);
      const seatMat = new THREE.MeshLambertMaterial({ color: seatColor });
      const seatGeo = new THREE.BoxGeometry(0.5, 0.6, 0.45);
      this.disposables.push(seatMat, seatGeo);

      const seatInstanced = new THREE.InstancedMesh(seatGeo, seatMat, 14);
      seatInstanced.castShadow = false;
      seatInstanced.receiveShadow = false;
      const seatMatrix = new THREE.Matrix4();
      for (let s = 0; s < 14; s++) {
        const sx = -4.5 + s * 0.7;
        seatMatrix.makeTranslation(sx, 0.45, -0.2);
        seatInstanced.setMatrixAt(s, seatMatrix);
      }
      seatInstanced.instanceMatrix.needsUpdate = true;
      dugoutGroup.add(seatInstanced);

      this.stadiumGroup.add(dugoutGroup);
    };

    createDugout(-14, true);  // Home Dugout
    createDugout(14, false);  // Away Dugout

    // 4th Official Substitution Desk
    const deskGeo = new THREE.BoxGeometry(2.0, 0.9, 0.8);
    const deskMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.5 });
    this.disposables.push(deskGeo, deskMat);
    const desk = new THREE.Mesh(deskGeo, deskMat);
    desk.position.set(0, 0.45, dugoutZ - 0.5);
    this.stadiumGroup.add(desk);
  }

  // ---------------------------------------------------------------------------
  // 5. Central Player Walkout Tunnel & Dressing Room Entrance
  // ---------------------------------------------------------------------------
  private buildPlayerTunnelAndDressingAccess(): void {
    const halfW = FIFA_PITCH_DIMENSIONS.width / 2;
    const tunnelGroup = new THREE.Group();
    tunnelGroup.position.set(0, 0, halfW + 7.5);

    // Tunnel Arch Portal
    const portalGeo = new THREE.BoxGeometry(7.0, 4.2, 6.0);
    const portalMat = new THREE.MeshStandardMaterial({
      color: 0x090d16,
      roughness: 0.6,
      metalness: 0.2,
    });
    this.disposables.push(portalGeo, portalMat);
    const portal = new THREE.Mesh(portalGeo, portalMat);
    portal.position.set(0, 2.1, 3.0);
    tunnelGroup.add(portal);

    // Red Carpet Walkout Runner to Touchline
    const carpetGeo = new THREE.PlaneGeometry(3.6, 8.5);
    const carpetMat = new THREE.MeshStandardMaterial({
      color: 0x991b1b, // Deep broadcast crimson
      roughness: 0.9,
    });
    this.disposables.push(carpetGeo, carpetMat);
    const carpet = new THREE.Mesh(carpetGeo, carpetMat);
    carpet.rotation.x = -Math.PI / 2;
    carpet.position.set(0, 0.02, -3.2);
    tunnelGroup.add(carpet);

    // Tunnel Retractable Accordion Canopy
    const accGeo = new THREE.CylinderGeometry(2.2, 2.2, 4.0, 16, 1, true, 0, Math.PI);
    const accMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      side: THREE.DoubleSide,
    });
    this.disposables.push(accGeo, accMat);
    const accordion = new THREE.Mesh(accGeo, accMat);
    accordion.rotation.z = Math.PI / 2;
    accordion.rotation.y = Math.PI / 2;
    accordion.position.set(0, 2.0, 0);
    tunnelGroup.add(accordion);

    // Flash Interview Step-and-Repeat Backdrop
    const backdropGeo = new THREE.PlaneGeometry(4.0, 2.4);
    const backdropMat = new THREE.MeshBasicMaterial({
      color: 0x0284c7,
      side: THREE.DoubleSide,
    });
    this.disposables.push(backdropGeo, backdropMat);
    const backdrop = new THREE.Mesh(backdropGeo, backdropMat);
    backdrop.position.set(0, 1.8, 5.8);
    tunnelGroup.add(backdrop);

    this.stadiumGroup.add(tunnelGroup);
  }

  // ---------------------------------------------------------------------------
  // 6. Dynamic LED Perimeter Advertising Boards (GTEX Stadium Advertising Network)
  // ---------------------------------------------------------------------------
  private buildPerimeterAdBoards(): void {
    const halfL = FIFA_PITCH_DIMENSIONS.length / 2;
    const halfW = FIFA_PITCH_DIMENSIONS.width / 2;
    const boardH = 1.38;
    const offsetSide = halfW + 3.2;
    const offsetGoal = halfL + 4.8;

    const baseTexture = this.adNetwork.getTexture();
    this.adTouchlineTexture = baseTexture;
    this.adTouchlineTexture.repeat.set(3, 1);

    const ledScreenMat = new THREE.MeshBasicMaterial({
      map: this.adTouchlineTexture,
      side: THREE.DoubleSide,
    });
    const cabinetFrameMat = new THREE.MeshLambertMaterial({ color: 0x090d16 });
    this.disposables.push(ledScreenMat, cabinetFrameMat);

    // A. Far Touchline Broadcast LED Board (z = -offsetSide, facing +Z toward main broadcast camera at [0, 25, 58])
    const touchlineLen = FIFA_PITCH_DIMENSIONS.length + 8;
    const backingGeo = new THREE.BoxGeometry(touchlineLen, boardH, 0.28);
    const screenGeo = new THREE.PlaneGeometry(touchlineLen, boardH - 0.08);
    this.disposables.push(backingGeo, screenGeo);

    const farBacking = new THREE.Mesh(backingGeo, cabinetFrameMat);
    farBacking.position.set(0, boardH / 2, -offsetSide - 0.16);
    farBacking.rotation.x = -0.22; // 12.6° tilt upward toward broadcast camera
    this.adBoardsGroup.add(farBacking);

    const farScreen = new THREE.Mesh(screenGeo, ledScreenMat);
    farScreen.position.set(0, boardH / 2 + 0.02, -offsetSide);
    farScreen.rotation.x = -0.22;
    this.adBoardsGroup.add(farScreen);

    // B. Near Touchline LED Boards (Left & Right of Dugouts / Walkout Tunnel)
    const nearSegLen = halfL - 8;
    const nearBackingGeo = new THREE.BoxGeometry(nearSegLen, boardH, 0.26);
    const nearScreenGeo = new THREE.PlaneGeometry(nearSegLen, boardH - 0.08);
    this.disposables.push(nearBackingGeo, nearScreenGeo);

    const leftNearBacking = new THREE.Mesh(nearBackingGeo, cabinetFrameMat);
    leftNearBacking.position.set(-halfL / 2 - 4, boardH / 2, offsetSide + 0.14);
    const leftNearScreen = new THREE.Mesh(nearScreenGeo, ledScreenMat);
    leftNearScreen.position.set(-halfL / 2 - 4, boardH / 2, offsetSide);
    leftNearScreen.rotation.y = Math.PI;

    const rightNearBacking = new THREE.Mesh(nearBackingGeo, cabinetFrameMat);
    rightNearBacking.position.set(halfL / 2 + 4, boardH / 2, offsetSide + 0.14);
    const rightNearScreen = new THREE.Mesh(nearScreenGeo, ledScreenMat);
    rightNearScreen.position.set(halfL / 2 + 4, boardH / 2, offsetSide);
    rightNearScreen.rotation.y = Math.PI;
    this.adBoardsGroup.add(leftNearBacking, leftNearScreen, rightNearBacking, rightNearScreen);

    // C. Goal End LED Boards (Behind Left and Right Goal Nets)
    const goalLen = FIFA_PITCH_DIMENSIONS.width + 6;
    const goalBackingGeo = new THREE.BoxGeometry(0.28, boardH, goalLen);
    const goalScreenGeo = new THREE.PlaneGeometry(goalLen, boardH - 0.08);
    this.disposables.push(goalBackingGeo, goalScreenGeo);

    const leftGoalBacking = new THREE.Mesh(goalBackingGeo, cabinetFrameMat);
    leftGoalBacking.position.set(-offsetGoal - 0.16, boardH / 2, 0);
    const leftGoalScreen = new THREE.Mesh(goalScreenGeo, ledScreenMat);
    leftGoalScreen.position.set(-offsetGoal, boardH / 2, 0);
    leftGoalScreen.rotation.y = Math.PI / 2;

    const rightGoalBacking = new THREE.Mesh(goalBackingGeo, cabinetFrameMat);
    rightGoalBacking.position.set(offsetGoal + 0.16, boardH / 2, 0);
    const rightGoalScreen = new THREE.Mesh(goalScreenGeo, ledScreenMat);
    rightGoalScreen.position.set(offsetGoal, boardH / 2, 0);
    rightGoalScreen.rotation.y = -Math.PI / 2;

    this.adBoardsGroup.add(leftGoalBacking, leftGoalScreen, rightGoalBacking, rightGoalScreen);

    // D. East Stand Mid-Tier Broadcast Fascia LED Ribbon (directly visible in TV Wide & Broadcast shots)
    const fasciaRibbonGeo = new THREE.PlaneGeometry(touchlineLen + 4, 1.55);
    this.disposables.push(fasciaRibbonGeo);
    const eastFasciaRibbon = new THREE.Mesh(fasciaRibbonGeo, ledScreenMat);
    eastFasciaRibbon.position.set(0, 6.8, -(halfW + 9.85));
    this.adBoardsGroup.add(eastFasciaRibbon);
  }

  public getAdvertisingNetwork(): StadiumAdvertisingNetwork {
    return this.adNetwork;
  }

  // ---------------------------------------------------------------------------
  // 7. Stadium Grandstands, Club Identity & Live Jumbotron Scoreboards
  // ---------------------------------------------------------------------------
  private buildGrandstands(): void {
    const halfL = FIFA_PITCH_DIMENSIONS.length / 2;
    const halfW = FIFA_PITCH_DIMENSIONS.width / 2;

    const concreteMat =
      this.qualityTier === "low"
        ? new THREE.MeshLambertMaterial({ color: 0x1e293b })
        : new THREE.MeshStandardMaterial({
            color: 0x1e293b,
            roughness: 0.85,
          });
    const vipGlassMat =
      this.qualityTier === "low"
        ? new THREE.MeshLambertMaterial({
            color: 0x0f172a,
            transparent: true,
            opacity: 0.72,
          })
        : new THREE.MeshStandardMaterial({
            color: 0x0f172a,
            roughness: 0.12,
            metalness: 0.85,
            transparent: true,
            opacity: 0.72,
          });
    const roofMat =
      this.qualityTier === "low"
        ? new THREE.MeshLambertMaterial({ color: 0x090d16 })
        : new THREE.MeshStandardMaterial({
            color: 0x090d16,
            metalness: 0.4,
            roughness: 0.5,
          });
    this.disposables.push(concreteMat, vipGlassMat, roofMat);

    // Live Stadium Scoreboard Jumbotron Canvas Texture
    if (typeof document !== "undefined") {
      const sbCanvas = document.createElement("canvas");
      sbCanvas.width = 512;
      sbCanvas.height = 256;
      try {
        const isJsdom =
          typeof navigator !== "undefined" &&
          /jsdom/i.test(navigator.userAgent || "") &&
          !(sbCanvas.getContext as any)?._isMockFunction;
        this.scoreboardContext = isJsdom ? null : sbCanvas.getContext("2d");
      } catch {
        this.scoreboardContext = null;
      }
      this.scoreboardCanvas = sbCanvas;
      this.scoreboardTexture = new THREE.CanvasTexture(sbCanvas);
      this.scoreboardTexture.colorSpace = THREE.SRGBColorSpace;
      this.disposables.push(this.scoreboardTexture);
      this.updateScoreboard(0, 0, "00:00", "LIVE MATCHDAY BROADCAST");
    }

    const jumbotronScreenMat = this.scoreboardTexture
      ? new THREE.MeshBasicMaterial({ map: this.scoreboardTexture, side: THREE.DoubleSide })
      : new THREE.MeshBasicMaterial({ color: 0x0284c7 });
    this.disposables.push(jumbotronScreenMat);

    // A. West Grandstand (Main Stand: positioned behind the TV broadcast camera gantry at z = 56 so it never occludes the pitch)
    const buildWestMainStand = () => {
      const standGroup = new THREE.Group();
      standGroup.name = "Procedural_West_Stand";
      standGroup.position.set(0, 0, halfW + 34);

      const lowerGeo = new THREE.BoxGeometry(FIFA_PITCH_DIMENSIONS.length + 10, 6, 12);
      this.disposables.push(lowerGeo);
      const lower = new THREE.Mesh(lowerGeo, concreteMat);
      lower.position.set(0, 3, 0);
      standGroup.add(lower);

      if (this.qualityTier !== "low") {
        const vipGeo = new THREE.BoxGeometry(FIFA_PITCH_DIMENSIONS.length + 6, 4, 10);
        this.disposables.push(vipGeo);
        const vip = new THREE.Mesh(vipGeo, vipGlassMat);
        vip.position.set(0, 8, 4);
        standGroup.add(vip);
        this.vipSkyboxObjects.push(vip);

        const upperGeo = new THREE.BoxGeometry(FIFA_PITCH_DIMENSIONS.length + 14, 8, 14);
        this.disposables.push(upperGeo);
        const upper = new THREE.Mesh(upperGeo, concreteMat);
        upper.position.set(0, 14, 10);
        standGroup.add(upper);
        this.upperTierObjects.push(upper);
      }

      const roofGeo = new THREE.BoxGeometry(FIFA_PITCH_DIMENSIONS.length + 18, 1.2, 22);
      this.disposables.push(roofGeo);
      const roof = new THREE.Mesh(roofGeo, roofMat);
      roof.position.set(0, 24, 8);
      roof.rotation.x = 0.08;
      standGroup.add(roof);

      this.stadiumGroup.add(standGroup);
    };

    // B. East Stand (Opposite Stand: 2-Tier Rake + Roof + Corner Broadcast Jumbotrons)
    const buildEastStand = () => {
      const standGroup = new THREE.Group();
      standGroup.name = "Procedural_East_Stand";
      standGroup.position.set(0, 0, -(halfW + 16));

      const lowerGeo = new THREE.BoxGeometry(FIFA_PITCH_DIMENSIONS.length + 10, 6, 12);
      this.disposables.push(lowerGeo);
      const lower = new THREE.Mesh(lowerGeo, concreteMat);
      lower.position.set(0, 3, 0);
      standGroup.add(lower);

      if (this.qualityTier !== "low") {
        const upperGeo = new THREE.BoxGeometry(FIFA_PITCH_DIMENSIONS.length + 12, 9, 14);
        this.disposables.push(upperGeo);
        const upper = new THREE.Mesh(upperGeo, concreteMat);
        upper.position.set(0, 10.5, -6);
        standGroup.add(upper);
        this.upperTierObjects.push(upper);
      }

      const roofGeo = new THREE.BoxGeometry(FIFA_PITCH_DIMENSIONS.length + 16, 1.2, 26);
      this.disposables.push(roofGeo);
      const roof = new THREE.Mesh(roofGeo, roofMat);
      roof.position.set(0, 20, -3);
      roof.rotation.x = -0.08;
      standGroup.add(roof);
      this.secondaryRoofObjects.push(roof);

      // Dual Corner Jumbotron Screens angled toward the main broadcast camera
      const jumboScreenGeo = new THREE.PlaneGeometry(11.5, 5.8);
      this.disposables.push(jumboScreenGeo);

      const leftJumbo = new THREE.Mesh(jumboScreenGeo, jumbotronScreenMat);
      leftJumbo.position.set(-halfL + 4, 15.8, 5.5);
      leftJumbo.rotation.y = 0.36;
      standGroup.add(leftJumbo);
      this.secondaryJumbotronObjects.push(leftJumbo);

      const rightJumbo = new THREE.Mesh(jumboScreenGeo, jumbotronScreenMat);
      rightJumbo.position.set(halfL - 4, 15.8, 5.5);
      rightJumbo.rotation.y = -0.36;
      standGroup.add(rightJumbo);
      this.secondaryJumbotronObjects.push(rightJumbo);

      this.stadiumGroup.add(standGroup);
    };

    // C. North Stand (Home End / The Kop)
    const buildNorthKopStand = () => {
      const standGroup = new THREE.Group();
      standGroup.name = "Procedural_North_Stand";
      standGroup.position.set(-(halfL + 16), 0, 0);

      const kopGeo = new THREE.BoxGeometry(14, 12, FIFA_PITCH_DIMENSIONS.width + 12);
      this.disposables.push(kopGeo);
      const kop = new THREE.Mesh(kopGeo, concreteMat);
      kop.position.set(-2, 6, 0);
      standGroup.add(kop);

      const roofGeo = new THREE.BoxGeometry(22, 1.2, FIFA_PITCH_DIMENSIONS.width + 16);
      this.disposables.push(roofGeo);
      const roof = new THREE.Mesh(roofGeo, roofMat);
      roof.position.set(2, 18, 0);
      roof.rotation.z = 0.06;
      standGroup.add(roof);
      this.secondaryRoofObjects.push(roof);

      this.stadiumGroup.add(standGroup);
    };

    // D. South Stand (Away End + Scoreboard Tower)
    const buildSouthAwayStand = () => {
      const standGroup = new THREE.Group();
      standGroup.name = "Procedural_South_Stand";
      standGroup.position.set(halfL + 16, 0, 0);

      const awayGeo = new THREE.BoxGeometry(14, 11, FIFA_PITCH_DIMENSIONS.width + 12);
      this.disposables.push(awayGeo);
      const away = new THREE.Mesh(awayGeo, concreteMat);
      away.position.set(2, 5.5, 0);
      standGroup.add(away);

      // Elevated Digital Scoreboard Jumbotron
      const scoreGeo = new THREE.PlaneGeometry(14.0, 6.0);
      this.disposables.push(scoreGeo);
      const scoreboard = new THREE.Mesh(scoreGeo, jumbotronScreenMat);
      scoreboard.position.set(-5.2, 16, 0);
      scoreboard.rotation.y = -Math.PI / 2;
      standGroup.add(scoreboard);

      const roofGeo = new THREE.BoxGeometry(22, 1.2, FIFA_PITCH_DIMENSIONS.width + 16);
      this.disposables.push(roofGeo);
      const roof = new THREE.Mesh(roofGeo, roofMat);
      roof.position.set(-2, 18, 0);
      roof.rotation.z = -0.06;
      standGroup.add(roof);
      this.secondaryRoofObjects.push(roof);

      this.stadiumGroup.add(standGroup);
    };

    // E. Tier 3 Sovereign Super-Arena Corner Architectural Towers
    const buildCornerTowers = () => {
      const towerGeo = new THREE.CylinderGeometry(5.2, 6.0, 21, 8);
      this.disposables.push(towerGeo);
      const cornerCoords: Array<[number, number]> = [
        [-(halfL + 15), -(halfW + 15)],
        [halfL + 15, -(halfW + 15)],
        [-(halfL + 15), halfW + 24],
        [halfL + 15, halfW + 24],
      ];

      cornerCoords.forEach(([cx, cz]) => {
        const tower = new THREE.Mesh(towerGeo, vipGlassMat);
        tower.name = "Sovereign_Corner_Tower";
        tower.position.set(cx, 10.5, cz);
        this.stadiumGroup.add(tower);
        this.cornerTowerObjects.push(tower);
      });
    };

    buildWestMainStand();
    buildEastStand();
    buildNorthKopStand();
    buildSouthAwayStand();
    buildCornerTowers();
  }

  /**
   * Dynamically switches the 3D stadium architecture tier (Tier 1 Community -> Tier 2 Regional -> Tier 3 Sovereign)
   * without reallocating GPU geometries or textures.
   */
  public setStadiumTier(tier: StadiumTier): void {
    this.stadiumTier = tier;
    this.applyStadiumTierVisibility(tier);
    this.updateClubIdentityBanner();
  }

  public getStadiumTier(): StadiumTier {
    return this.stadiumTier;
  }

  public getStadiumTierProfile(): StadiumTierProfile {
    return STADIUM_TIER_PROFILES[this.stadiumTier] || STADIUM_TIER_PROFILES[3];
  }

  private applyStadiumTierVisibility(tier: StadiumTier): void {
    const profile = STADIUM_TIER_PROFILES[tier] || STADIUM_TIER_PROFILES[3];

    this.upperTierObjects.forEach((obj) => {
      obj.visible = profile.hasUpperTiers;
    });
    this.vipSkyboxObjects.forEach((obj) => {
      obj.visible = profile.hasVipSkyboxes;
    });
    this.secondaryRoofObjects.forEach((obj) => {
      obj.visible = profile.hasFullRoofCanopy;
    });
    this.cornerTowerObjects.forEach((obj) => {
      obj.visible = profile.hasCornerTowers;
    });
    this.secondaryJumbotronObjects.forEach((obj, idx) => {
      obj.visible = idx + 2 <= profile.jumbotronCount;
    });
  }

  private updateClubIdentityBanner(): void {
    const ctx = this.clubBannerContext;
    const canvas = this.clubBannerCanvas;
    if (!ctx || !canvas) return;

    const primary = this.homeTeam.primary_color || "#00E676";
    const secondary = this.homeTeam.secondary_color || "#1B5E20";
    const accent = this.homeTeam.accent_color || "#FFFFFF";
    const profile = this.getStadiumTierProfile();

    ctx.fillStyle = secondary;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = primary;
    ctx.fillRect(0, 0, canvas.width, 14);
    ctx.fillRect(0, canvas.height - 14, canvas.width, 14);

    ctx.fillStyle = accent;
    ctx.font = "900 32px 'Outfit', 'Inter', sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const bannerTitle = `${(this.homeTeam.team_name || "HOME CLUB").toUpperCase()}  •  ${profile.label.toUpperCase()} (${profile.capacity.toLocaleString()} CAP)`;
    ctx.fillText(bannerTitle.slice(0, 64), canvas.width / 2, canvas.height / 2);

    if (this.clubBannerTexture) {
      this.clubBannerTexture.needsUpdate = true;
    }
  }

  /**
   * Updates the stadium jumbotron scoreboard texture only when score, clock minute, or banner changes.
   */
  public updateScoreboard(
    homeScore: number,
    awayScore: number,
    clockLabel: string,
    eventBanner?: string | null
  ): void {
    const key = `${this.homeTeam.short_name}:${homeScore}-${awayScore}:${this.awayTeam.short_name}:${clockLabel}:${eventBanner || ""}:${this.stadiumTier}`;
    if (key === this.lastScoreboardKey) return;
    this.lastScoreboardKey = key;

    const ctx = this.scoreboardContext;
    const canvas = this.scoreboardCanvas;
    if (!ctx || !canvas) return;

    ctx.fillStyle = "#040814";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Header competition bar
    ctx.fillStyle = "#10B981";
    ctx.fillRect(0, 0, canvas.width, 40);
    ctx.fillStyle = "#020617";
    ctx.font = "900 20px 'Outfit', 'Inter', sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(this.competitionName.toUpperCase().slice(0, 32), canvas.width / 2, 21);

    // Home club block
    ctx.fillStyle = this.homeTeam.primary_color || "#00E676";
    ctx.fillRect(24, 58, 148, 108);
    ctx.fillStyle = "#FFFFFF";
    ctx.font = "900 44px 'Outfit', 'Inter', sans-serif";
    ctx.fillText((this.homeTeam.short_name || "HOM").slice(0, 4), 98, 114);

    // Away club block
    ctx.fillStyle = this.awayTeam.primary_color || "#2979FF";
    ctx.fillRect(canvas.width - 172, 58, 148, 108);
    ctx.fillStyle = "#FFFFFF";
    ctx.fillText((this.awayTeam.short_name || "AWY").slice(0, 4), canvas.width - 98, 114);

    // Live Score in Center
    ctx.fillStyle = "#F8FAFC";
    ctx.font = "900 68px 'JetBrains Mono', monospace";
    ctx.fillText(`${homeScore} - ${awayScore}`, canvas.width / 2, 116);

    // Match Clock & Event Strip
    ctx.fillStyle = "#0F172A";
    ctx.fillRect(24, 182, canvas.width - 48, 56);
    ctx.strokeStyle = "#38BDF8";
    ctx.lineWidth = 2;
    ctx.strokeRect(24, 182, canvas.width - 48, 56);

    ctx.fillStyle = "#38BDF8";
    ctx.font = "800 26px 'JetBrains Mono', monospace";
    const bottomLabel = eventBanner
      ? `${clockLabel}  •  ${eventBanner.toUpperCase().slice(0, 22)}`
      : `${clockLabel}  •  ${this.homeTeam.team_name.toUpperCase().slice(0, 12)} v ${this.awayTeam.team_name.toUpperCase().slice(0, 12)}`;
    ctx.fillText(bottomLabel, canvas.width / 2, 211);

    if (this.scoreboardTexture) {
      this.scoreboardTexture.needsUpdate = true;
    }
  }

  /**
   * Updates club colours, banners, scoreboard, and ad network match context dynamically.
   */
  public setTeamIdentity(
    homeTeam: SpectatorSafeTeamView,
    awayTeam: SpectatorSafeTeamView,
    competitionName?: string,
    matchId?: string
  ): void {
    this.homeTeam = homeTeam;
    this.awayTeam = awayTeam;
    if (competitionName) {
      this.competitionName = competitionName;
    }
    if (this.homeCrowdMat) {
      this.homeCrowdMat.color.set(homeTeam.primary_color || "#00E676");
    }
    if (this.awayCrowdMat) {
      this.awayCrowdMat.color.set(awayTeam.primary_color || "#2979FF");
    }
    if (this.bannerMat) {
      this.bannerMat.color.set(homeTeam.accent_color || "#FFFFFF");
    }
    this.updateClubIdentityBanner();
    this.adNetwork.setMatchContext({
      matchId,
      homeTeamId: homeTeam.team_id,
      homeTeamName: homeTeam.team_name,
      homePrimaryColor: homeTeam.primary_color,
      awayTeamId: awayTeam.team_id,
      awayTeamName: awayTeam.team_name,
      awayPrimaryColor: awayTeam.primary_color,
      competitionName: this.competitionName,
    });
    this.lastScoreboardKey = "";
  }

  // ---------------------------------------------------------------------------
  // 8. Crowd Presentation & Instanced Supporter Reactions (Phase 7 & Phase 2 Wave)
  // ---------------------------------------------------------------------------
  private buildCrowd(attendancePct: number): void {
    const halfL = FIFA_PITCH_DIMENSIONS.length / 2;
    const halfW = FIFA_PITCH_DIMENSIONS.width / 2;
    const homeColor = new THREE.Color(this.homeTeam.primary_color);
    const awayColor = new THREE.Color(this.awayTeam.primary_color);
    const accentColor = new THREE.Color(this.homeTeam.accent_color || "#ffffff");

    if (typeof document !== "undefined") {
      const bCanvas = document.createElement("canvas");
      bCanvas.width = 1024;
      bCanvas.height = 96;
      try {
        const isJsdom =
          typeof navigator !== "undefined" &&
          /jsdom/i.test(navigator.userAgent || "") &&
          !(bCanvas.getContext as any)?._isMockFunction;
        this.clubBannerContext = isJsdom ? null : bCanvas.getContext("2d");
      } catch {
        this.clubBannerContext = null;
      }
      this.clubBannerCanvas = bCanvas;
      this.clubBannerTexture = new THREE.CanvasTexture(bCanvas);
      this.clubBannerTexture.colorSpace = THREE.SRGBColorSpace;
      this.disposables.push(this.clubBannerTexture);
      this.updateClubIdentityBanner();
    }

    const homeCrowdMat = new THREE.MeshLambertMaterial({ color: homeColor });
    const awayCrowdMat = new THREE.MeshLambertMaterial({ color: awayColor });
    const neutralCrowdMat = new THREE.MeshLambertMaterial({ color: 0x475569 });
    const bannerMat = new THREE.MeshBasicMaterial({
      color: this.clubBannerTexture ? 0xffffff : accentColor,
      map: this.clubBannerTexture || null,
    });
    this.homeCrowdMat = homeCrowdMat;
    this.awayCrowdMat = awayCrowdMat;
    this.bannerMat = bannerMat;
    this.disposables.push(homeCrowdMat, awayCrowdMat, neutralCrowdMat, bannerMat);

    const crowdBlockGeo = new THREE.BoxGeometry(halfL * 1.8 * Math.max(0.65, attendancePct / 100), 1.6, 2.4);
    this.disposables.push(crowdBlockGeo);

    // West Stand Crowd (Predominantly Home, behind broadcast gantry)
    const westCrowdLower = new THREE.Mesh(crowdBlockGeo, homeCrowdMat);
    westCrowdLower.visible = false;
    westCrowdLower.position.set(0, 5.5, halfW + 30);
    this.crowdGroup.add(westCrowdLower);

    // East Stand Crowd (Home & General Spectators)
    const eastCrowdLower = new THREE.Mesh(crowdBlockGeo, homeCrowdMat);
    eastCrowdLower.visible = false;
    eastCrowdLower.position.set(0, 5.5, -(halfW + 15));
    this.crowdGroup.add(eastCrowdLower);

    if (this.qualityTier !== "low") {
      const westCrowdUpper = new THREE.Mesh(crowdBlockGeo, neutralCrowdMat);
      westCrowdUpper.visible = false;
      westCrowdUpper.position.set(0, 16.5, halfW + 40);
      const eastCrowdUpper = new THREE.Mesh(crowdBlockGeo, homeCrowdMat);
      eastCrowdUpper.visible = false;
      eastCrowdUpper.position.set(0, 13.5, -(halfW + 21));
      this.crowdGroup.add(westCrowdUpper, eastCrowdUpper);
      this.upperTierObjects.push(westCrowdUpper, eastCrowdUpper);
    }

    // North Stand Kop Crowd (100% Home Ultras)
    const kopCrowdGeo = new THREE.BoxGeometry(3.0, 7.0, FIFA_PITCH_DIMENSIONS.width + 4);
    this.disposables.push(kopCrowdGeo);
    const kopCrowd = new THREE.Mesh(kopCrowdGeo, homeCrowdMat);
    kopCrowd.visible = false;
    kopCrowd.position.set(-(halfL + 15), 8, 0);
    this.crowdGroup.add(kopCrowd);

    // South Stand Crowd (Away Supporter Block)
    const awayCrowdGeo = new THREE.BoxGeometry(3.0, 6.0, FIFA_PITCH_DIMENSIONS.width + 4);
    this.disposables.push(awayCrowdGeo);
    const awayCrowd = new THREE.Mesh(awayCrowdGeo, awayCrowdMat);
    awayCrowd.visible = false;
    awayCrowd.position.set(halfL + 15, 7.5, 0);
    this.crowdGroup.add(awayCrowd);

    // Supporter banner tifo strips along the East & Kop fascias
    const tifoGeo = new THREE.BoxGeometry(halfL * 1.4, 0.95, 0.25);
    this.disposables.push(tifoGeo);
    const eastTifo = new THREE.Mesh(tifoGeo, bannerMat);
    eastTifo.name = "Club_Identity_East_Banner";
    eastTifo.position.set(0, 9.2, -(halfW + 10.2));
    this.crowdGroup.add(eastTifo);

    // Instanced 3D Supporter Crowd (1 single GPU draw call for hundreds of reactive supporters)
    const supporterCount = this.qualityTier === "low" ? 240 : 720;
    const supGeo = createSpectatorGeometry();
    const supMat = new THREE.MeshLambertMaterial({ color: 0xffffff, vertexColors: true });
    this.disposables.push(supGeo, supMat);

    const instanced = new THREE.InstancedMesh(supGeo, supMat, supporterCount);
    instanced.name = "Instanced_Supporter_Crowd";
    instanced.castShadow = false;
    instanced.receiveShadow = false;

    const dummyMatrix = new THREE.Matrix4();
    const color = new THREE.Color();
    const homeSecondary = new THREE.Color(this.homeTeam.secondary_color || "#1B5E20");
    const awaySecondary = new THREE.Color(this.awayTeam.secondary_color || "#0D47A1");
    this.supporterMeta = [];

    for (let i = 0; i < supporterCount; i++) {
      let bx = 0;
      let by = 5.5;
      let bz = -(halfW + 13);
      let rotY = 0;
      let side: "home" | "away" | "neutral" = "home";

      if (i < supporterCount * 0.55) {
        // East Stand lower & upper rows (directly visible in TV broadcast camera)
        const row = i % 6;
        const col = Math.floor(i / 6);
        const maxCols = Math.max(1, Math.floor((supporterCount * 0.55) / 6));
        bx = -halfL * 0.92 + (col / maxCols) * (FIFA_PITCH_DIMENSIONS.length * 0.92);
        by = 3.2 + row * 1.45 + (row >= 3 ? 3.2 : 0);
        bz = -(halfW + 11.5 + row * 1.65 + (row >= 3 ? 2.5 : 0));
        rotY = 0;
        side = i % 7 === 0 ? "neutral" : "home";
      } else if (i < supporterCount * 0.8) {
        // North Kop Stand (Home Ultras)
        const idx = i - Math.floor(supporterCount * 0.55);
        const row = idx % 5;
        const col = Math.floor(idx / 5);
        const maxCols = Math.max(1, Math.floor((supporterCount * 0.25) / 5));
        bx = -(halfL + 11.5 + row * 1.5);
        by = 3.5 + row * 1.5;
        bz = -halfW * 0.88 + (col / maxCols) * (FIFA_PITCH_DIMENSIONS.width * 0.88);
        rotY = Math.PI / 2;
        side = "home";
      } else {
        // South Stand (Away Supporters)
        const idx = i - Math.floor(supporterCount * 0.8);
        const row = idx % 5;
        const col = Math.floor(idx / 5);
        const maxCols = Math.max(1, Math.floor((supporterCount * 0.2) / 5));
        bx = halfL + 11.5 + row * 1.5;
        by = 3.5 + row * 1.4;
        bz = -halfW * 0.88 + (col / maxCols) * (FIFA_PITCH_DIMENSIONS.width * 0.88);
        rotY = -Math.PI / 2;
        side = "away";
      }

      const phase = (i * 1.37) % (Math.PI * 2);
      const angleRad = Math.atan2(bz, bx);
      const scale = 0.9 + (i % 6) * 0.035;
      this.supporterMeta.push({ baseX: bx, baseY: by, baseZ: bz, rotY, phase, angleRad, side, scale });

      dummyMatrix.makeRotationY(rotY);
      dummyMatrix.setPosition(bx, by, bz);
      instanced.setMatrixAt(i, dummyMatrix);

      if (side === "home") {
        color.copy(i % 3 === 0 ? homeSecondary : i % 5 === 0 ? accentColor : homeColor);
      } else if (side === "away") {
        color.copy(i % 3 === 0 ? awaySecondary : awayColor);
      } else {
        color.setHex(i % 2 === 0 ? 0xe2e8f0 : 0x64748b);
      }
      instanced.setColorAt(i, color);
    }

    instanced.instanceMatrix.needsUpdate = true;
    if (instanced.instanceColor) {
      instanced.instanceColor.needsUpdate = true;
    }
    this.supporterMesh = instanced;
    this.crowdGroup.add(instanced);
  }

  /**
   * Triggers a stadium-wide radial Mexican Wave around the supporter bowl.
   */
  public triggerCrowdWave(durationSec: number = 8.0): void {
    this.crowdWaveTimerSec = Math.max(this.crowdWaveTimerSec, durationSec);
  }

  public isCrowdWaveActive(): boolean {
    return this.crowdWaveTimerSec > 0;
  }

  /**
   * Triggers an event-driven stadium crowd reaction (goal celebration surge, save cheer,
   * near-miss gasp, attacking roar, red card reaction, or fulltime ovation).
   */
  public triggerCrowdReaction(
    reaction: StadiumCrowdReactionType,
    side: "home" | "away" | "both" = "both"
  ): void {
    this.crowdReactionType = reaction;
    this.crowdReactionSide = side;
    switch (reaction) {
      case "goal":
        this.crowdReactionIntensity = 1.0;
        this.crowdReactionTimerSec = 6.5;
        this.crowdWaveTimerSec = 7.5;
        break;
      case "save":
      case "near_miss":
        this.crowdReactionIntensity = 0.78;
        this.crowdReactionTimerSec = 3.8;
        break;
      case "red_card":
      case "fulltime":
        this.crowdReactionIntensity = 0.88;
        this.crowdReactionTimerSec = 5.0;
        if (reaction === "fulltime") {
          this.crowdWaveTimerSec = 6.0;
        }
        break;
      case "attack":
        this.crowdReactionIntensity = Math.max(this.crowdReactionIntensity, 0.48);
        this.crowdReactionTimerSec = Math.max(this.crowdReactionTimerSec, 2.2);
        break;
      default:
        this.crowdReactionIntensity = 0.15;
        this.crowdReactionTimerSec = 0;
        break;
    }
  }

  public getCrowdReactionState(): {
    type: StadiumCrowdReactionType;
    intensity: number;
    side: "home" | "away" | "both";
    waveActive?: boolean;
  } {
    return {
      type: this.crowdReactionType,
      intensity: this.crowdReactionIntensity,
      side: this.crowdReactionSide,
      waveActive: this.crowdWaveTimerSec > 0,
    };
  }

  // ---------------------------------------------------------------------------
  // 9. 4-Corner Floodlight Pylon Towers & Atmospheric Lighting
  // ---------------------------------------------------------------------------
  private buildFloodlightsAndEnvironment(scene: THREE.Scene): void {
    const pylonDistX = FIFA_PITCH_DIMENSIONS.length / 2 + 18;
    const pylonDistZ = FIFA_PITCH_DIMENSIONS.width / 2 + 18;
    const pylonH = 36;

    const mastMat =
      this.qualityTier === "low"
        ? new THREE.MeshLambertMaterial({ color: 0x334155 })
        : new THREE.MeshStandardMaterial({
            color: 0x334155,
            metalness: 0.6,
            roughness: 0.4,
          });
    const headMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const glowMat = new THREE.MeshBasicMaterial({
      color: 0xe0f2fe,
      transparent: true,
      opacity: this.qualityTier === "low" ? 0.08 : 0.16,
      depthWrite: false,
    });
    const mastGeo = new THREE.CylinderGeometry(0.5, 1.2, pylonH, 6);
    const gantryGeo = new THREE.BoxGeometry(5.0, 3.2, 0.6);
    const haloGeo = new THREE.PlaneGeometry(7.2, 4.6);
    this.disposables.push(mastMat, headMat, glowMat, mastGeo, gantryGeo, haloGeo);

    const corners = [
      [-pylonDistX, -pylonDistZ],
      [pylonDistX, -pylonDistZ],
      [-pylonDistX, pylonDistZ],
      [pylonDistX, pylonDistZ],
    ];

    corners.forEach(([px, pz]) => {
      const pGroup = new THREE.Group();
      pGroup.position.set(px, 0, pz);

      // Steel Lattice Mast
      const mast = new THREE.Mesh(mastGeo, mastMat);
      mast.position.y = pylonH / 2;
      pGroup.add(mast);

      // Light Gantry Bank (4x4 matrix)
      const gantry = new THREE.Mesh(gantryGeo, headMat);
      gantry.position.set(0, pylonH, 0);
      gantry.lookAt(0, 0, 0);
      pGroup.add(gantry);

      this.lightingGroup.add(pGroup);

      // Emissive Floodlight Glare Halo (avoids evaluating 4 extra per-pixel SpotLight shaders across 217k vertices)
      const halo = new THREE.Mesh(haloGeo, glowMat);
      halo.position.set(px * 0.96, pylonH - 0.4, pz * 0.96);
      halo.lookAt(0, 0, 0);
      this.lightingGroup.add(halo);
    });

    // Atmospheric Stadium Skybox Dusk Fog
    scene.fog = new THREE.FogExp2(0x060a14, this.qualityTier === "low" ? 0.005 : 0.0065);
  }

  // ---------------------------------------------------------------------------
  // Real-Time Update Tick (Slot-Boundary LED Rotation & Instanced Crowd Motion)
  // ---------------------------------------------------------------------------
  public update(deltaSec: number, matchTimeSec?: number): void {
    this.elapsedSec += Math.max(0, deltaSec);
    const effectiveMatchSec = typeof matchTimeSec === "number" ? matchTimeSec : this.elapsedSec;

    // 1. Step Stadium LED Advertising Network (rotates only on slot boundaries)
    this.adNetwork.update(deltaSec, this.elapsedSec, effectiveMatchSec);

    // 2. Decay crowd reaction & wave timers smoothly back to ambient open-play pulse
    if (this.crowdReactionTimerSec > 0) {
      this.crowdReactionTimerSec = Math.max(0, this.crowdReactionTimerSec - deltaSec);
      if (this.crowdReactionTimerSec === 0) {
        this.crowdReactionType = "calm";
        this.crowdReactionIntensity = 0.15;
      }
    }
    if (this.crowdWaveTimerSec > 0) {
      this.crowdWaveTimerSec = Math.max(0, this.crowdWaveTimerSec - deltaSec);
    }

    // 3. Animate instanced supporters (jumping wave during excitement, subtle sway in open play)
    if (this.supporterMesh && this.supporterMeta.length > 0) {
      const mat4 = new THREE.Matrix4();
      const freq = this.crowdReactionIntensity > 0.5 ? 11.5 : 4.2;
      const amp = 0.06 + this.crowdReactionIntensity * 0.42;
      const waveActive = this.crowdWaveTimerSec > 0;
      const waveFrontAngle = (this.elapsedSec * 2.8) % (Math.PI * 2);

      for (let i = 0; i < this.supporterMeta.length; i++) {
        const meta = this.supporterMeta[i];
        const isReactingSide =
          this.crowdReactionSide === "both" ||
          meta.side === "neutral" ||
          meta.side === this.crowdReactionSide;
        const localAmp = isReactingSide ? amp : amp * 0.3;
        let bounce =
          Math.abs(Math.sin(this.elapsedSec * freq + meta.phase + meta.baseX * 0.08)) * localAmp;

        if (waveActive) {
          const waveCrest = Math.max(0, Math.cos(meta.angleRad - waveFrontAngle));
          bounce += Math.pow(waveCrest, 4) * 0.52;
        }

        if (this.externalCrowdOffsetFn) {
          const extra = this.externalCrowdOffsetFn(meta.baseX, meta.baseZ);
          if (Number.isFinite(extra)) bounce += Math.max(0, Math.min(1.5, extra));
        }

        spectatorScale.set(meta.scale, meta.scale, meta.scale);
        mat4.makeRotationY(meta.rotY);
        mat4.scale(spectatorScale);
        mat4.setPosition(meta.baseX, meta.baseY + bounce, meta.baseZ);
        this.supporterMesh.setMatrixAt(i, mat4);
      }
      this.supporterMesh.instanceMatrix.needsUpdate = true;
    }
  }

  // ---------------------------------------------------------------------------
  // Resource Cleanup & Memory Management
  // ---------------------------------------------------------------------------
  /**
   * Replaces the box stands and floodlight masts with the downloaded stadium bowl.
   * The GTEX pitch, goals, markings, ad boards, dugouts, and crowd stay in place.
   * Grass and pitch meshes inside the bowl stay hidden so they do not cover the 105×68 pitch.
   */
  public async loadBroadcastBowl(url: string, renderer?: unknown): Promise<boolean> {
    let scene: THREE.Object3D | null = null;
    try {
      const gltf = await AssetStreamingCache.getInstance().loadGltf(url, renderer);
      scene = gltf?.scene ?? null;
    } catch {
      return false;
    }
    if (!scene || this.disposed) {
      if (scene) disposeObject3D(scene);
      return false;
    }

    scene.name = "Broadcast_Stadium_Bowl";
    scene.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (mesh.isMesh) {
        mesh.castShadow = false;
        mesh.receiveShadow = true;
      }
    });

    scene.updateMatrixWorld(true);
    const measured = new THREE.Box3().setFromObject(scene);
    const measuredSize = new THREE.Vector3();
    measured.getSize(measuredSize);
    if (measuredSize.z > measuredSize.x) scene.rotation.y = Math.PI / 2;
    scene.updateMatrixWorld(true);
    const pitchSurface = scene.getObjectByName("Pitch");
    if (pitchSurface) {
      const pitchBounds = new THREE.Box3().setFromObject(pitchSurface);
      const pitchSize = new THREE.Vector3();
      pitchBounds.getSize(pitchSize);
      if (pitchSize.x > 1 && pitchSize.z > 1) {
        const fitX = FIFA_PITCH_DIMENSIONS.length / pitchSize.x;
        scene.scale.set(fitX, fitX, FIFA_PITCH_DIMENSIONS.width / pitchSize.z);
      }
    }
    scene.traverse((obj) => {
      if (isStadiumBowlPitchSurface(obj.name)) obj.visible = false;
    });
    scene.updateMatrixWorld(true);
    const bounds = new THREE.Box3().setFromObject(scene);
    const center = new THREE.Vector3();
    bounds.getCenter(center);
    scene.position.x -= center.x;
    scene.position.z -= center.z;
    scene.position.y -= bounds.min.y;

    if (this.broadcastBowl) {
      this.stadiumGroup.remove(this.broadcastBowl);
      disposeObject3D(this.broadcastBowl);
    }
    this.broadcastBowl = scene;
    this.stadiumGroup.add(scene);
    this.stadiumGroup.updateMatrixWorld(true);
    scene.traverse((obj) => {
      obj.matrixAutoUpdate = false;
    });

    this.stadiumGroup.children.forEach((child) => {
      if (child === scene) return;
      if (child.name.startsWith("Procedural_") || child.name === "Sovereign_Corner_Tower") {
        child.visible = false;
      }
    });
    this.lightingGroup.visible = false;
    this.seatCrowdInBroadcastBowl();
    return true;
  }

  /** Moves the supporter blocks into the lower tier of the loaded bowl. */
  private seatCrowdInBroadcastBowl(): void {
    const halfL = FIFA_PITCH_DIMENSIONS.length / 2;
    const halfW = FIFA_PITCH_DIMENSIONS.width / 2;
    const count = this.supporterMeta.length;
    this.supporterMeta.forEach((meta, i) => {
      if (i < count * 0.4) {
        const row = i % 7;
        const col = Math.floor(i / 7);
        const maxCols = Math.max(1, Math.floor((count * 0.4) / 7));
        meta.baseX = -halfL * 0.86 + (col / maxCols) * (FIFA_PITCH_DIMENSIONS.length * 0.86);
        meta.baseY = 1.8 + row * 1.05;
        meta.baseZ = -(halfW + 7 + row * 1.05);
        meta.rotY = Math.PI;
      } else if (i < count * 0.7) {
        const idx = i - Math.floor(count * 0.4);
        const row = idx % 6;
        const col = Math.floor(idx / 6);
        const maxCols = Math.max(1, Math.floor((count * 0.3) / 6));
        meta.baseX = -halfL * 0.86 + (col / maxCols) * (FIFA_PITCH_DIMENSIONS.length * 0.86);
        meta.baseY = 1.8 + row * 1.05;
        meta.baseZ = halfW + 7 + row * 1.05;
        meta.rotY = 0;
      } else if (i < count * 0.85) {
        const idx = i - Math.floor(count * 0.7);
        const row = idx % 5;
        const col = Math.floor(idx / 5);
        const maxCols = Math.max(1, Math.floor((count * 0.15) / 5));
        meta.baseX = -(halfL + 7 + row * 1.05);
        meta.baseY = 1.8 + row * 1.05;
        meta.baseZ = -halfW * 0.8 + (col / maxCols) * (FIFA_PITCH_DIMENSIONS.width * 0.8);
        meta.rotY = Math.PI / 2;
      } else {
        const idx = i - Math.floor(count * 0.85);
        const row = idx % 5;
        const col = Math.floor(idx / 5);
        const maxCols = Math.max(1, Math.floor((count * 0.15) / 5));
        meta.baseX = halfL + 7 + row * 1.05;
        meta.baseY = 1.8 + row * 1.05;
        meta.baseZ = -halfW * 0.8 + (col / maxCols) * (FIFA_PITCH_DIMENSIONS.width * 0.8);
        meta.rotY = -Math.PI / 2;
      }
    });

    this.crowdGroup.children.forEach((child) => {
      if (child === this.supporterMesh) return;
      const position = child.position;
      if (Math.abs(position.x) > halfL) position.x = Math.sign(position.x) * (halfL + 12);
      if (Math.abs(position.z) > halfW) position.z = Math.sign(position.z) * (halfW + 14);
      position.y = Math.min(position.y, 9);
      child.updateMatrix();
    });
  }

  public dispose(): void {
    this.disposed = true;
    if (this.broadcastBowl) disposeObject3D(this.broadcastBowl);
    this.broadcastBowl = null;
    this.adNetwork.dispose();
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

const spectatorScale = new THREE.Vector3();

function createSpectatorGeometry(): THREE.BufferGeometry {
  const parts: THREE.BufferGeometry[] = [];
  const add = (geo: THREE.BufferGeometry, x: number, y: number, z: number, color: THREE.Color) => {
    const solid = geo.index ? geo.toNonIndexed() : geo;
    if (solid !== geo) geo.dispose();
    solid.translate(x, y, z);
    geo = solid;
    const colors = new Float32Array(geo.getAttribute("position").count * 3);
    for (let i = 0; i < colors.length; i += 3) {
      colors[i] = color.r;
      colors[i + 1] = color.g;
      colors[i + 2] = color.b;
    }
    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    parts.push(geo);
  };
  const skin = new THREE.Color(0xf0c7a4);
  const cloth = new THREE.Color(0xffffff);
  add(new THREE.BoxGeometry(0.34, 0.46, 0.18), 0, 1.08, 0, cloth);
  add(new THREE.SphereGeometry(0.13, 8, 6), 0, 1.46, 0, skin);
  add(new THREE.BoxGeometry(0.11, 0.46, 0.12), -0.09, 0.48, 0, cloth);
  add(new THREE.BoxGeometry(0.11, 0.46, 0.12), 0.09, 0.48, 0, cloth);
  add(new THREE.BoxGeometry(0.09, 0.38, 0.1), -0.24, 1.12, 0, cloth);
  add(new THREE.BoxGeometry(0.09, 0.38, 0.1), 0.24, 1.12, 0, cloth);
  const merged = mergePositionNormalColor(parts);
  parts.forEach((geo) => geo.dispose());
  return merged;
}

function mergePositionNormalColor(parts: THREE.BufferGeometry[]): THREE.BufferGeometry {
  let count = 0;
  parts.forEach((geo) => {
    count += geo.getAttribute("position").count;
  });
  const position = new Float32Array(count * 3);
  const normal = new Float32Array(count * 3);
  const color = new Float32Array(count * 3);
  let offset = 0;
  parts.forEach((geo) => {
    const pos = geo.getAttribute("position");
    const nrm = geo.getAttribute("normal");
    const col = geo.getAttribute("color");
    position.set(pos.array as Float32Array, offset * 3);
    normal.set(nrm.array as Float32Array, offset * 3);
    color.set(col.array as Float32Array, offset * 3);
    offset += pos.count;
  });
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(position, 3));
  geometry.setAttribute("normal", new THREE.BufferAttribute(normal, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(color, 3));
  return geometry;
}

function disposeObject3D(root: THREE.Object3D): void {
  const materials = new Set<THREE.Material>();
  root.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (!mesh.isMesh) return;
    mesh.geometry?.dispose();
    const list = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    list.forEach((material) => {
      if (material && !materials.has(material)) materials.add(material);
    });
  });
  materials.forEach((material) => {
    const textured = material as THREE.Material & { map?: THREE.Texture | null };
    textured.map?.dispose();
    material.dispose();
  });
}
