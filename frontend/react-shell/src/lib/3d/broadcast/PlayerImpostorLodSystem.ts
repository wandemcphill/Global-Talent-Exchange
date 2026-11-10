/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Player Impostor LOD System.
 *
 * Distant footballers are swapped from their 26-bone SkinnedMesh rig to a single
 * InstancedMesh of low-poly kit-coloured capsules (one draw call for every far player).
 * Hidden rigs skip GPU skinning and shadow casting entirely; their animation state keeps
 * ticking so they pop back in seamlessly when the camera moves closer. Hysteresis on the
 * distance threshold prevents flicker at the boundary.
 */

import * as THREE from "three";
import type { DeviceQualityTier } from "../GtexSceneTypes";

export interface ImpostorCandidate {
  id: string;
  rootObject: THREE.Object3D;
  colorHex: string;
}

export interface PlayerImpostorSummary {
  thresholdMeters: number;
  impostorCount: number;
  fullRigCount: number;
  drawCallsSaved: number;
}

/**
 * Camera distance beyond which a player becomes an impostor.
 * High stays at 85 m: the closer broadcast camera is about 38 m away, so those
 * bodies stay real meshes, and a player past 110 m still batches into the impostor.
 */
export const IMPOSTOR_DISTANCE_BY_TIER: Record<DeviceQualityTier, number> = {
  low: 48,
  medium: 78,
  high: 85,
  ultra: Number.POSITIVE_INFINITY,
};

const HYSTERESIS_METERS = 4;

export class PlayerImpostorLodSystem {
  private readonly mesh: THREE.InstancedMesh;
  private readonly geometry: THREE.BufferGeometry;
  private readonly material: THREE.MeshStandardMaterial;
  private readonly impostorState = new Map<string, boolean>();
  private readonly tmpMatrix = new THREE.Matrix4();
  private readonly tmpPos = new THREE.Vector3();
  private readonly tmpColor = new THREE.Color();
  private threshold: number;
  private impostorCount = 0;
  private fullRigCount = 0;

  constructor(private readonly parent: THREE.Object3D, qualityTier: DeviceQualityTier, maxPlayers: number = 32) {
    this.threshold = IMPOSTOR_DISTANCE_BY_TIER[qualityTier] ?? IMPOSTOR_DISTANCE_BY_TIER.high;
    // Capsule ~1.8m tall, base on the ground
    this.geometry = new THREE.CapsuleGeometry(0.28, 1.2, 3, 8);
    this.geometry.translate(0, 0.88, 0);
    this.material = new THREE.MeshStandardMaterial({ roughness: 0.7, metalness: 0.0 });
    this.mesh = new THREE.InstancedMesh(this.geometry, this.material, maxPlayers);
    this.mesh.count = 0;
    this.mesh.frustumCulled = false;
    this.mesh.name = "gtex-player-impostors";
    this.parent.add(this.mesh);
  }

  public setQualityTier(tier: DeviceQualityTier): void {
    this.threshold = IMPOSTOR_DISTANCE_BY_TIER[tier] ?? this.threshold;
  }

  public update(camera: THREE.Camera, players: ImpostorCandidate[]): void {
    let index = 0;
    let full = 0;
    const capacity = this.mesh.instanceMatrix.count;

    for (const p of players) {
      p.rootObject.getWorldPosition(this.tmpPos);
      const dist = this.tmpPos.distanceTo(camera.position);
      const wasImpostor = this.impostorState.get(p.id) ?? false;
      const isImpostor = wasImpostor
        ? dist > this.threshold - HYSTERESIS_METERS
        : dist > this.threshold + HYSTERESIS_METERS;
      this.impostorState.set(p.id, isImpostor);

      if (isImpostor && index < capacity) {
        p.rootObject.visible = false;
        this.tmpMatrix.makeTranslation(this.tmpPos.x, this.tmpPos.y, this.tmpPos.z);
        this.mesh.setMatrixAt(index, this.tmpMatrix);
        this.mesh.setColorAt(index, this.tmpColor.set(p.colorHex));
        index++;
      } else {
        p.rootObject.visible = true;
        full++;
      }
    }

    this.mesh.count = index;
    this.mesh.instanceMatrix.needsUpdate = true;
    if (this.mesh.instanceColor) this.mesh.instanceColor.needsUpdate = true;
    this.impostorCount = index;
    this.fullRigCount = full;
  }

  public isImpostor(id: string): boolean {
    return this.impostorState.get(id) ?? false;
  }

  public getSummary(): PlayerImpostorSummary {
    return {
      thresholdMeters: this.threshold,
      impostorCount: this.impostorCount,
      fullRigCount: this.fullRigCount,
      // Each impostor replaces one skinned draw call; the instanced batch costs one.
      drawCallsSaved: Math.max(0, this.impostorCount - (this.impostorCount > 0 ? 1 : 0)),
    };
  }

  public dispose(): void {
    this.parent.remove(this.mesh);
    this.geometry.dispose();
    this.material.dispose();
    this.mesh.dispose();
    this.impostorState.clear();
  }
}
