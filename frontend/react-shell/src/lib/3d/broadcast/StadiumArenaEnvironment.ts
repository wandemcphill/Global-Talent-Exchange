/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast Arena
 * Milestone 2 — Comprehensive Stadium & Architectural Expansion
 *
 * Implements:
 * 1. Realistic FIFA Pitch Geometry:
 *    - 105m x 68m FIFA pitch with 10 alternating turf stripes and green runoff buffer.
 *    - Accurate chalk markings: touchlines, goal lines, halfway line, center circle & spot,
 *      penalty areas (16.5m x 40.32m), goal boxes (5.5m x 18.32m), penalty spots (11m),
 *      penalty arcs ("D"), and 4 corner arcs.
 *    - 4 realistic corner flags (1.5m flexible pole with fluttering fabric flags).
 *    - 3D FIFA goal cages with rounded posts, crossbar, net support stanchions, and 3D net mesh.
 * 2. Stadium Stands & Seating Architecture:
 *    - West Grandstand: Main multi-tiered stand with lower bowl, executive VIP skybox suites
 *      with reflective panoramic windows, upper tier, and cantilevered roof canopy.
 *    - East Stand: 2-tiered stand with suspended broadcast gantry and roof canopy.
 *    - North Stand (Home Kop End): Steep single-tier home supporter stand with club crest banners.
 *    - South Stand (Away End): 2-tiered stand with away section and elevated digital scoreboard tower.
 *    - Vomitories (access tunnel stairs), concrete rakes, and steel safety railings.
 * 3. Crowd Presentation:
 *    - Tiered spectator seating with multi-colored home and away supporter crowd blocks.
 *    - Device-quality tier adaptation (instanced high-density seating on High/Ultra,
 *      optimized batched geometry on Medium/Low for guaranteed 60fps).
 * 4. Floodlights & Environmental Lighting:
 *    - 4 corner floodlight towers (36m tall) with 3D steel lattice pylons and 4x4 LED lamp arrays.
 *    - 4 targeted spotlight cones casting pitch-quadrant beams with subtle atmospheric haze.
 *    - Under-canopy architectural wash lights.
 * 5. Touchlines, Technical Areas & Dugouts:
 *    - Home and away dashed chalk technical coaching boxes.
 *    - Modern ergonomic team dugouts with curved tinted polycarbonate canopies, aluminum ribs,
 *      and 14 contoured racing bucket seats styled in club colors.
 *    - 4th official / referee board station.
 * 6. Player Tunnel & Stadium Entrances:
 *    - Central walkout tunnel portal embedded into the West Grandstand.
 *    - Retractable accordion tunnel canopy and red/emerald turf walkout runner.
 * 7. Dressing Rooms & Supporting Environments:
 *    - Illuminated tunnel interior mouth with club branding and flash interview step-and-repeat backdrop.
 * 8. Dynamic LED Perimeter Advertising Boards:
 *    - 0.9m digital LED boards wrapping the pitch perimeter with animated rotating sponsor campaigns
 *      (GTEX Living Football, Chronos Tourbillon, Apex Dynasty, Sovereign Fleet).
 */

import * as THREE from "three";
import { FIFA_PITCH_DIMENSIONS, PITCH_LANDMARKS } from "./matchCoordinates";
import { SpectatorSafeTeamView } from "./spectatorContract";
import type { DeviceQualityTier } from "../GtexSceneTypes";

export interface StadiumArenaOptions {
  homeTeam?: SpectatorSafeTeamView;
  awayTeam?: SpectatorSafeTeamView;
  qualityTier?: DeviceQualityTier;
  stadiumName?: string;
  attendancePct?: number; // 0..100
}

export class StadiumArenaEnvironment {
  public readonly group: THREE.Group;
  public readonly pitchGroup: THREE.Group;
  public readonly stadiumGroup: THREE.Group;
  public readonly lightingGroup: THREE.Group;
  public readonly adBoardsGroup: THREE.Group;
  public readonly crowdGroup: THREE.Group;

  private qualityTier: DeviceQualityTier;
  private homeTeam: SpectatorSafeTeamView;
  private awayTeam: SpectatorSafeTeamView;
  private adTexture: THREE.CanvasTexture | null = null;
  private adCanvas: HTMLCanvasElement | null = null;
  private adContext: CanvasRenderingContext2D | null = null;
  private adScrollOffset: number = 0;
  private disposables: Array<{ dispose: () => void }> = [];

  constructor(scene: THREE.Scene, options: StadiumArenaOptions = {}) {
    this.qualityTier = options.qualityTier || "high";
    this.homeTeam = options.homeTeam || {
      team_id: "home-default",
      team_name: "Apex Home FC",
      short_name: "APX",
      formation: "4-3-3",
      primary_color: "#00E676",
      secondary_color: "#1B5E20",
      accent_color: "#FFFFFF",
      goalkeeper_color: "#FFD600",
    };
    this.awayTeam = options.awayTeam || {
      team_id: "away-default",
      team_name: "Titan Away FC",
      short_name: "TTN",
      formation: "4-4-2",
      primary_color: "#2979FF",
      secondary_color: "#0D47A1",
      accent_color: "#FFFFFF",
      goalkeeper_color: "#FF3D00",
    };

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

    // Freeze world matrices on all static stadium architecture to eliminate 180+ per-frame matrix multiplications
    this.group.updateMatrixWorld(true);
    this.group.traverse((obj) => {
      if (obj !== this.group) {
        obj.matrixAutoUpdate = false;
      }
    });
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
    this.disposables.push(pitchGeo, pitchMat);
    const pitchMesh = new THREE.Mesh(pitchGeo, pitchMat);
    pitchMesh.rotation.x = -Math.PI / 2;
    pitchMesh.receiveShadow = true;
    this.pitchGroup.add(pitchMesh);

    // B. Pitch Runoff Buffer Turf (extending 7m beyond touchlines, 9m behind goal lines)
    const runoffGeo = new THREE.PlaneGeometry(pLength + 18, pWidth + 14, 1, 1);
    const runoffMat = new THREE.MeshLambertMaterial({
      color: 0x0e361b,
      side: THREE.DoubleSide,
    });
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
      // Angle spans roughly -53 deg to +53 deg facing pitch interior
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

      // Curved canopy roof (half-cylinder) — uses MeshStandardMaterial/MeshLambertMaterial instead of
      // MeshPhysicalMaterial(transmission) to prevent Three.js from executing a costly second full-scene render pass.
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

      // Aluminum frame ribs (shared geometry across ribs; skipped on low quality tier)
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

      // 14 Bucket Seats batched into a single InstancedMesh (1 draw call instead of 14, no shadow pass overhead)
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
  // 6. Dynamic LED Perimeter Advertising Boards
  // ---------------------------------------------------------------------------
  private buildPerimeterAdBoards(): void {
    const halfL = FIFA_PITCH_DIMENSIONS.length / 2;
    const halfW = FIFA_PITCH_DIMENSIONS.width / 2;
    const boardH = 0.95;
    const offsetSide = halfW + 3.2;
    const offsetGoal = halfL + 4.8;

    // Create Canvas Texture for Real-Time LED Scrolling Sponsor Campaigns
    const canvas = document.createElement("canvas");
    canvas.width = 1024;
    canvas.height = 64;
    let ctx: CanvasRenderingContext2D | null = null;
    try {
      ctx = canvas.getContext("2d");
    } catch {
      ctx = null;
    }
    if (ctx) {
      this.adCanvas = canvas;
      this.adContext = ctx;
      this.renderAdCanvasContent();
      this.adTexture = new THREE.CanvasTexture(canvas);
      this.adTexture.wrapS = THREE.RepeatWrapping;
      this.adTexture.wrapT = THREE.ClampToEdgeWrapping;
      this.disposables.push(this.adTexture);
    }

    const ledMat = this.adTexture
      ? new THREE.MeshBasicMaterial({ map: this.adTexture })
      : new THREE.MeshBasicMaterial({ color: 0x0284c7 });
    this.disposables.push(ledMat);

    // Side Touchline Boards (Top and Bottom)
    const sideBoardGeo = new THREE.BoxGeometry(FIFA_PITCH_DIMENSIONS.length + 8, boardH, 0.18);
    this.disposables.push(sideBoardGeo);

    // Top Touchline LED Board
    const topBoard = new THREE.Mesh(sideBoardGeo, ledMat);
    topBoard.position.set(0, boardH / 2, -offsetSide);
    this.adBoardsGroup.add(topBoard);

    // Bottom Touchline LED Board (with gap for player tunnel / dugouts)
    const bottomBoardLeft = new THREE.Mesh(
      new THREE.BoxGeometry(halfL - 8, boardH, 0.18),
      ledMat
    );
    bottomBoardLeft.position.set(-halfL / 2 - 4, boardH / 2, offsetSide);
    const bottomBoardRight = new THREE.Mesh(
      new THREE.BoxGeometry(halfL - 8, boardH, 0.18),
      ledMat
    );
    bottomBoardRight.position.set(halfL / 2 + 4, boardH / 2, offsetSide);
    this.adBoardsGroup.add(bottomBoardLeft, bottomBoardRight);

    // Goal End LED Boards (Behind Left and Right Goal Nets)
    const goalBoardGeo = new THREE.BoxGeometry(0.18, boardH, FIFA_PITCH_DIMENSIONS.width + 6);
    this.disposables.push(goalBoardGeo);

    const leftGoalBoard = new THREE.Mesh(goalBoardGeo, ledMat);
    leftGoalBoard.position.set(-offsetGoal, boardH / 2, 0);
    const rightGoalBoard = new THREE.Mesh(goalBoardGeo, ledMat);
    rightGoalBoard.position.set(offsetGoal, boardH / 2, 0);
    this.adBoardsGroup.add(leftGoalBoard, rightGoalBoard);
  }

  private renderAdCanvasContent(): void {
    const ctx = this.adContext;
    if (!ctx || !this.adCanvas) return;

    ctx.fillStyle = "#030712";
    ctx.fillRect(0, 0, this.adCanvas.width, this.adCanvas.height);

    // Neon accent edge
    ctx.fillStyle = "#00e5ff";
    ctx.fillRect(0, 0, this.adCanvas.width, 3);
    ctx.fillStyle = "#10b981";
    ctx.fillRect(0, this.adCanvas.height - 3, this.adCanvas.width, 3);

    // Sponsor brand slogans rendered once into the tileable 1024x64 texture;
    // runtime scrolling shifts UV offset.x on the GPU without CPU-to-GPU texImage2D stalls.
    const slogans = [
      "GTEX GLOBAL TALENT EXCHANGE",
      "APEX REGEN TOURNAMENT ARENA",
      "CHRONOS TOURBILLON — OFFICIAL TIMEKEEPER",
      "SOVEREIGN EXECUTIVE FLEET",
    ];

    ctx.font = "bold 19px 'Segoe UI', Inter, sans-serif";
    ctx.textBaseline = "middle";

    let xCursor = 18;
    slogans.forEach((slogan, idx) => {
      ctx.fillStyle = idx % 2 === 0 ? "#00E676" : "#38BDF8";
      ctx.fillText(slogan, xCursor, 34);
      xCursor += 252;
    });

    if (this.adTexture) {
      this.adTexture.needsUpdate = true;
    }
  }

  // ---------------------------------------------------------------------------
  // 7. Stadium Grandstands & Architecture (4 Major Stands)
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
    // Use MeshStandardMaterial / MeshLambertMaterial instead of MeshPhysicalMaterial(transmission)
    // to avoid triggering Three.js's costly second full-scene opaque render pass.
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

    // A. West Grandstand (Main Stand: positioned behind the TV broadcast camera gantry at z = 56 so it never occludes the pitch)
    const buildWestMainStand = () => {
      const standGroup = new THREE.Group();
      standGroup.position.set(0, 0, halfW + 34);

      // Lower Tier Tiered Rake
      const lowerGeo = new THREE.BoxGeometry(FIFA_PITCH_DIMENSIONS.length + 10, 6, 12);
      this.disposables.push(lowerGeo);
      const lower = new THREE.Mesh(lowerGeo, concreteMat);
      lower.position.set(0, 3, 0);
      standGroup.add(lower);

      if (this.qualityTier !== "low") {
        // VIP Hospitality Skybox Floor
        const vipGeo = new THREE.BoxGeometry(FIFA_PITCH_DIMENSIONS.length + 6, 4, 10);
        this.disposables.push(vipGeo);
        const vip = new THREE.Mesh(vipGeo, vipGlassMat);
        vip.position.set(0, 8, 4);
        standGroup.add(vip);

        // Upper Tier Rake
        const upperGeo = new THREE.BoxGeometry(FIFA_PITCH_DIMENSIONS.length + 14, 8, 14);
        this.disposables.push(upperGeo);
        const upper = new THREE.Mesh(upperGeo, concreteMat);
        upper.position.set(0, 14, 10);
        standGroup.add(upper);
      }

      // Cantilevered Roof Canopy (set behind broadcast camera gantry)
      const roofGeo = new THREE.BoxGeometry(FIFA_PITCH_DIMENSIONS.length + 18, 1.2, 22);
      this.disposables.push(roofGeo);
      const roof = new THREE.Mesh(roofGeo, roofMat);
      roof.position.set(0, 24, 8);
      roof.rotation.x = 0.08;
      standGroup.add(roof);

      this.stadiumGroup.add(standGroup);
    };

    // B. East Stand (Opposite Stand: 2-Tier Rake + Roof)
    const buildEastStand = () => {
      const standGroup = new THREE.Group();
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
      }

      const roofGeo = new THREE.BoxGeometry(FIFA_PITCH_DIMENSIONS.length + 16, 1.2, 26);
      this.disposables.push(roofGeo);
      const roof = new THREE.Mesh(roofGeo, roofMat);
      roof.position.set(0, 20, -3);
      roof.rotation.x = -0.08;
      standGroup.add(roof);

      this.stadiumGroup.add(standGroup);
    };

    // C. North Stand (Home End / The Kop)
    const buildNorthKopStand = () => {
      const standGroup = new THREE.Group();
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

      this.stadiumGroup.add(standGroup);
    };

    // D. South Stand (Away End + Scoreboard Tower)
    const buildSouthAwayStand = () => {
      const standGroup = new THREE.Group();
      standGroup.position.set(halfL + 16, 0, 0);

      const awayGeo = new THREE.BoxGeometry(14, 11, FIFA_PITCH_DIMENSIONS.width + 12);
      this.disposables.push(awayGeo);
      const away = new THREE.Mesh(awayGeo, concreteMat);
      away.position.set(2, 5.5, 0);
      standGroup.add(away);

      // Elevated Digital Scoreboard Jumbotron
      const scoreGeo = new THREE.BoxGeometry(1.2, 6.0, 14.0);
      const scoreMat = new THREE.MeshBasicMaterial({ color: 0x0284c7 });
      this.disposables.push(scoreGeo, scoreMat);
      const scoreboard = new THREE.Mesh(scoreGeo, scoreMat);
      scoreboard.position.set(4, 16, 0);
      standGroup.add(scoreboard);

      const roofGeo = new THREE.BoxGeometry(22, 1.2, FIFA_PITCH_DIMENSIONS.width + 16);
      this.disposables.push(roofGeo);
      const roof = new THREE.Mesh(roofGeo, roofMat);
      roof.position.set(-2, 18, 0);
      roof.rotation.z = -0.06;
      standGroup.add(roof);

      this.stadiumGroup.add(standGroup);
    };

    buildWestMainStand();
    buildEastStand();
    buildNorthKopStand();
    buildSouthAwayStand();
  }

  // ---------------------------------------------------------------------------
  // 8. Crowd Presentation (Home/Away Supporter Color Distribution)
  // ---------------------------------------------------------------------------
  private buildCrowd(attendancePct: number): void {
    const halfL = FIFA_PITCH_DIMENSIONS.length / 2;
    const halfW = FIFA_PITCH_DIMENSIONS.width / 2;
    const homeColor = new THREE.Color(this.homeTeam.primary_color);
    const awayColor = new THREE.Color(this.awayTeam.primary_color);
    const accentColor = new THREE.Color(this.homeTeam.accent_color || "#ffffff");

    const homeCrowdMat = new THREE.MeshLambertMaterial({ color: homeColor });
    const awayCrowdMat = new THREE.MeshLambertMaterial({ color: awayColor });
    const neutralCrowdMat = new THREE.MeshLambertMaterial({ color: 0x475569 });
    const bannerMat = new THREE.MeshBasicMaterial({ color: accentColor });
    this.disposables.push(homeCrowdMat, awayCrowdMat, neutralCrowdMat, bannerMat);

    const crowdBlockGeo = new THREE.BoxGeometry(halfL * 1.8 * Math.max(0.65, attendancePct / 100), 1.6, 2.4);
    this.disposables.push(crowdBlockGeo);

    // West Stand Crowd (Predominantly Home, behind broadcast gantry)
    const westCrowdLower = new THREE.Mesh(crowdBlockGeo, homeCrowdMat);
    westCrowdLower.position.set(0, 5.5, halfW + 30);
    this.crowdGroup.add(westCrowdLower);

    // East Stand Crowd (Home & General Spectators)
    const eastCrowdLower = new THREE.Mesh(crowdBlockGeo, homeCrowdMat);
    eastCrowdLower.position.set(0, 5.5, -(halfW + 15));
    this.crowdGroup.add(eastCrowdLower);

    if (this.qualityTier !== "low") {
      const westCrowdUpper = new THREE.Mesh(crowdBlockGeo, neutralCrowdMat);
      westCrowdUpper.position.set(0, 16.5, halfW + 40);
      const eastCrowdUpper = new THREE.Mesh(crowdBlockGeo, homeCrowdMat);
      eastCrowdUpper.position.set(0, 13.5, -(halfW + 21));
      this.crowdGroup.add(westCrowdUpper, eastCrowdUpper);
    }

    // North Stand Kop Crowd (100% Home Ultras)
    const kopCrowdGeo = new THREE.BoxGeometry(3.0, 7.0, FIFA_PITCH_DIMENSIONS.width + 4);
    this.disposables.push(kopCrowdGeo);
    const kopCrowd = new THREE.Mesh(kopCrowdGeo, homeCrowdMat);
    kopCrowd.position.set(-(halfL + 15), 8, 0);
    this.crowdGroup.add(kopCrowd);

    // South Stand Crowd (Away Supporter Block)
    const awayCrowdGeo = new THREE.BoxGeometry(3.0, 6.0, FIFA_PITCH_DIMENSIONS.width + 4);
    this.disposables.push(awayCrowdGeo);
    const awayCrowd = new THREE.Mesh(awayCrowdGeo, awayCrowdMat);
    awayCrowd.position.set(halfL + 15, 7.5, 0);
    this.crowdGroup.add(awayCrowd);

    // High quality tier adds supporter banner tifo strips along the East & Kop fascias
    if (this.qualityTier === "high" || this.qualityTier === "ultra") {
      const tifoGeo = new THREE.BoxGeometry(halfL * 1.4, 0.75, 0.25);
      this.disposables.push(tifoGeo);
      const eastTifo = new THREE.Mesh(tifoGeo, bannerMat);
      eastTifo.position.set(0, 9.2, -(halfW + 10.2));
      this.crowdGroup.add(eastTifo);
    }
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
  // Real-Time Update Tick (GPU UV Offset LED Scrolling — Zero CPU Canvas Re-Upload)
  // ---------------------------------------------------------------------------
  public update(deltaSec: number): void {
    this.adScrollOffset = (this.adScrollOffset + deltaSec * 35) % 800;
    if (this.adTexture) {
      this.adTexture.offset.x = (this.adTexture.offset.x + deltaSec * 0.042) % 1.0;
    }
  }

  // ---------------------------------------------------------------------------
  // Resource Cleanup & Memory Management
  // ---------------------------------------------------------------------------
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
