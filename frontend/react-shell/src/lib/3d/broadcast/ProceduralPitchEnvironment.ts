/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * ProceduralPitchEnvironment: Self-Contained FIFA Pitch, Lighting, and Procedural Player Markers.
 *
 * Implements the canonical Milestone 1 presentation layer:
 * 1. Procedural 105m x 68m FIFA pitch with turf stripes and chalk markings.
 * 2. 3D goal frames (posts, crossbars, nets) at both ends.
 * 3. 4 corner floodlight arrays and atmospheric hemisphere lighting.
 * 4. Procedural player marker meshes (torso, head, shorts, ground ring, billboard).
 * 5. Zero dependencies on Milestone 2 files (no humanoid rigs or complex stadium meshes).
 */

import * as THREE from "three";
import { FIFA_PITCH_DIMENSIONS, PITCH_LANDMARKS } from "./matchCoordinates";
import type { DeviceQualityTier } from "../GtexSceneTypes";
import type { SpectatorSafeTeamView } from "./spectatorContract";

export interface ProceduralPitchOptions {
  homeTeam: SpectatorSafeTeamView;
  awayTeam: SpectatorSafeTeamView;
  qualityTier?: DeviceQualityTier;
  stadiumName?: string;
}

export interface PlayerMarkerMesh {
  rootGroup: THREE.Group;
  torsoMesh: THREE.Mesh;
  shortsMesh: THREE.Mesh;
  ringMesh: THREE.Mesh;
  billboardMesh?: THREE.Mesh;
  updatePosition: (position3D: [number, number, number], facingAngleRad: number) => void;
  setVisible: (visible: boolean) => void;
  dispose: () => void;
}

export class ProceduralPitchEnvironment {
  public rootGroup: THREE.Group;
  public playersGroup: THREE.Group;
  private scene: THREE.Scene;
  private options: ProceduralPitchOptions;
  private playerMarkers = new Map<string, PlayerMarkerMesh>();
  private floodlights: THREE.Light[] = [];
  private disposed: boolean = false;

  constructor(scene: THREE.Scene, options: ProceduralPitchOptions) {
    this.scene = scene;
    this.options = options;
    this.rootGroup = new THREE.Group();
    this.rootGroup.name = "ProceduralPitchEnvironment";
    this.playersGroup = new THREE.Group();
    this.playersGroup.name = "ProceduralPlayerMarkersGroup";

    this.scene.add(this.rootGroup);
    this.scene.add(this.playersGroup);

    this.buildPitch();
    this.buildGoals();
    this.buildLighting();
  }

  private buildPitch(): void {
    const pLength = FIFA_PITCH_DIMENSIONS.length; // 105m
    const pWidth = FIFA_PITCH_DIMENSIONS.width;   // 68m

    // 1. Base Turf Plane
    const turfGeo = new THREE.PlaneGeometry(pLength, pWidth);
    const turfMat = new THREE.MeshStandardMaterial({
      color: 0x1b4d2e,
      roughness: 0.85,
      metalness: 0.05,
    });
    const turfMesh = new THREE.Mesh(turfGeo, turfMat);
    turfMesh.rotation.x = -Math.PI / 2;
    turfMesh.receiveShadow = true;
    this.rootGroup.add(turfMesh);

    // 2. Mowing Stripes (10 stripes along length)
    const stripeCount = 10;
    const stripeWidth = pLength / stripeCount;
    for (let i = 0; i < stripeCount; i++) {
      if (i % 2 === 0) continue;
      const stripeGeo = new THREE.PlaneGeometry(stripeWidth, pWidth);
      const stripeMat = new THREE.MeshBasicMaterial({
        color: 0x225c37,
        transparent: true,
        opacity: 0.45,
        depthWrite: false,
      });
      const stripeMesh = new THREE.Mesh(stripeGeo, stripeMat);
      stripeMesh.rotation.x = -Math.PI / 2;
      stripeMesh.position.set(-pLength / 2 + (i + 0.5) * stripeWidth, 0.01, 0);
      this.rootGroup.add(stripeMesh);
    }

    // 3. Chalk Markings
    const lineMat = new THREE.MeshBasicMaterial({
      color: 0xf0fdf4,
      transparent: true,
      opacity: 0.85,
      depthWrite: false,
    });

    const createChalkLine = (w: number, h: number, x: number, z: number) => {
      const geo = new THREE.PlaneGeometry(w, h);
      const mesh = new THREE.Mesh(geo, lineMat);
      mesh.rotation.x = -Math.PI / 2;
      mesh.position.set(x, 0.02, z);
      this.rootGroup.add(mesh);
    };

    const lineThickness = 0.14;
    // Boundary lines
    createChalkLine(pLength, lineThickness, 0, -pWidth / 2); // Top touchline
    createChalkLine(pLength, lineThickness, 0, pWidth / 2);  // Bottom touchline
    createChalkLine(lineThickness, pWidth, -pLength / 2, 0); // Left goal line
    createChalkLine(lineThickness, pWidth, pLength / 2, 0);  // Right goal line
    createChalkLine(lineThickness, pWidth, 0, 0);            // Halfway line

    // Center Circle (radius 9.15m)
    const centerCircleGeo = new THREE.RingGeometry(9.05, 9.20, 48);
    const centerCircleMesh = new THREE.Mesh(centerCircleGeo, lineMat);
    centerCircleMesh.rotation.x = -Math.PI / 2;
    centerCircleMesh.position.set(0, 0.02, 0);
    this.rootGroup.add(centerCircleMesh);

    // Center Spot
    const centerSpotGeo = new THREE.CircleGeometry(0.3, 16);
    const centerSpotMesh = new THREE.Mesh(centerSpotGeo, lineMat);
    centerSpotMesh.rotation.x = -Math.PI / 2;
    centerSpotMesh.position.set(0, 0.02, 0);
    this.rootGroup.add(centerSpotMesh);

    // Penalty Areas (16.5m deep x 40.32m wide)
    const penDepth = FIFA_PITCH_DIMENSIONS.penaltyAreaLength;
    const penWidth = FIFA_PITCH_DIMENSIONS.penaltyAreaWidth;
    for (const sign of [-1, 1]) {
      const goalX = (sign * pLength) / 2;
      const innerX = goalX - sign * penDepth;
      // Front line
      createChalkLine(lineThickness, penWidth, innerX, 0);
      // Top and bottom side lines
      createChalkLine(penDepth, lineThickness, goalX - (sign * penDepth) / 2, -penWidth / 2);
      createChalkLine(penDepth, lineThickness, goalX - (sign * penDepth) / 2, penWidth / 2);

      // Penalty Spot (11m)
      const spotX = goalX - sign * FIFA_PITCH_DIMENSIONS.penaltySpotDistance;
      const spotGeo = new THREE.CircleGeometry(0.22, 16);
      const spotMesh = new THREE.Mesh(spotGeo, lineMat);
      spotMesh.rotation.x = -Math.PI / 2;
      spotMesh.position.set(spotX, 0.02, 0);
      this.rootGroup.add(spotMesh);
    }
  }

  private buildGoals(): void {
    const halfL = FIFA_PITCH_DIMENSIONS.length / 2;
    const gW = FIFA_PITCH_DIMENSIONS.goalWidth;   // 7.32m
    const gH = FIFA_PITCH_DIMENSIONS.goalHeight;  // 2.44m
    const postMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      roughness: 0.3,
      metalness: 0.2,
    });
    const netMat = new THREE.MeshBasicMaterial({
      color: 0xcccccc,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });

    for (const sign of [-1, 1]) {
      const goalGroup = new THREE.Group();
      goalGroup.position.set(sign * halfL, 0, 0);

      const postRadius = 0.06;
      const postGeo = new THREE.CylinderGeometry(postRadius, postRadius, gH, 12);
      const postLeft = new THREE.Mesh(postGeo, postMat);
      postLeft.position.set(0, gH / 2, -gW / 2);
      goalGroup.add(postLeft);

      const postRight = new THREE.Mesh(postGeo, postMat);
      postRight.position.set(0, gH / 2, gW / 2);
      goalGroup.add(postRight);

      const barGeo = new THREE.CylinderGeometry(postRadius, postRadius, gW, 12);
      const crossbar = new THREE.Mesh(barGeo, postMat);
      crossbar.rotation.x = Math.PI / 2;
      crossbar.position.set(0, gH, 0);
      goalGroup.add(crossbar);

      // Net box
      const netDepth = 2.0;
      const netGeo = new THREE.BoxGeometry(netDepth, gH, gW);
      const netMesh = new THREE.Mesh(netGeo, netMat);
      netMesh.position.set(sign * (netDepth / 2), gH / 2, 0);
      goalGroup.add(netMesh);

      this.rootGroup.add(goalGroup);
    }
  }

  private buildLighting(): void {
    // Hemisphere ambient light
    const hemiLight = new THREE.HemisphereLight(0xe2e8f0, 0x1e293b, 0.7);
    this.rootGroup.add(hemiLight);

    // Directional sunlight / main floodlight
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.85);
    dirLight.position.set(20, 50, 40);
    dirLight.castShadow = true;
    this.rootGroup.add(dirLight);

    // 4 Corner floodlights
    const cornerPositions: [number, number, number][] = [
      [-65, 30, -45],
      [65, 30, -45],
      [-65, 30, 45],
      [65, 30, 45],
    ];
    for (const [cx, cy, cz] of cornerPositions) {
      const spot = new THREE.SpotLight(0xf8fafc, 0.45);
      spot.position.set(cx, cy, cz);
      spot.target.position.set(cx * 0.3, 0, cz * 0.3);
      this.rootGroup.add(spot);
      this.rootGroup.add(spot.target);
      this.floodlights.push(spot);
    }
  }

  public getOrCreatePlayerMarker(
    playerId: string,
    side: "home" | "away",
    shirtNumber: number = 10,
    label: string = "Player",
    role: string = "MID",
    isGK: boolean = false
  ): PlayerMarkerMesh {
    if (this.playerMarkers.has(playerId)) {
      return this.playerMarkers.get(playerId)!;
    }

    const teamView = side === "home" ? this.options.homeTeam : this.options.awayTeam;
    const jerseyHex = isGK ? teamView.goalkeeper_color : teamView.primary_color;
    const shortsHex = teamView.secondary_color;

    const pGroup = new THREE.Group();
    pGroup.name = `PlayerMarker_${playerId}`;

    // Torso (Jersey)
    const torsoGeo = new THREE.CylinderGeometry(0.32, 0.28, 0.9, 12);
    const torsoMat = new THREE.MeshLambertMaterial({ color: new THREE.Color(jerseyHex) });
    const torsoMesh = new THREE.Mesh(torsoGeo, torsoMat);
    torsoMesh.position.y = 1.05;
    torsoMesh.castShadow = true;
    pGroup.add(torsoMesh);

    // Head
    const headGeo = new THREE.SphereGeometry(0.2, 10, 10);
    const headMat = new THREE.MeshLambertMaterial({ color: 0xf5d0b5 });
    const headMesh = new THREE.Mesh(headGeo, headMat);
    headMesh.position.y = 1.65;
    pGroup.add(headMesh);

    // Shorts
    const shortsGeo = new THREE.CylinderGeometry(0.28, 0.26, 0.4, 10);
    const shortsMat = new THREE.MeshLambertMaterial({ color: new THREE.Color(shortsHex) });
    const shortsMesh = new THREE.Mesh(shortsGeo, shortsMat);
    shortsMesh.position.y = 0.55;
    pGroup.add(shortsMesh);

    // Ground Marker Ring
    const ringGeo = new THREE.RingGeometry(0.35, 0.45, 16);
    const ringMat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(jerseyHex),
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.7,
    });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.rotation.x = -Math.PI / 2;
    ringMesh.position.y = 0.03;
    pGroup.add(ringMesh);

    this.playersGroup.add(pGroup);

    const marker: PlayerMarkerMesh = {
      rootGroup: pGroup,
      torsoMesh,
      shortsMesh,
      ringMesh,
      updatePosition: (position3D, facingAngleRad) => {
        pGroup.position.set(position3D[0], 0, position3D[2]);
        pGroup.rotation.y = facingAngleRad;
      },
      setVisible: (visible) => {
        pGroup.visible = visible;
      },
      dispose: () => {
        pGroup.removeFromParent();
        torsoGeo.dispose();
        torsoMat.dispose();
        headGeo.dispose();
        headMat.dispose();
        shortsGeo.dispose();
        shortsMat.dispose();
        ringGeo.dispose();
        ringMat.dispose();
      },
    };

    this.playerMarkers.set(playerId, marker);
    return marker;
  }

  public update(_deltaSec: number): void {
    // Procedural pitch dynamics (e.g. subtle turf shimmer)
  }

  public dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.playerMarkers.forEach((marker) => marker.dispose());
    this.playerMarkers.clear();
    this.rootGroup.removeFromParent();
    this.playersGroup.removeFromParent();
  }
}
