/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Dynamic Broadcast Shadow Rig.
 *
 * Replaces the static, hard-edged full-pitch shadow map with a tight shadow frustum
 * that follows the ball (where the camera is looking), giving far higher texel
 * density on nearby players. Uses PCF soft shadows on high/ultra and refreshes the
 * shadow map at a throttled rate so moving players actually cast moving shadows.
 */

import * as THREE from "three";
import type { DeviceQualityTier } from "../GtexSceneTypes";

export interface DynamicShadowSummary {
  enabled: boolean;
  mapSize: number;
  frustumHalfExtent: number;
  updatesPerSecond: number;
  shadowUpdates: number;
}

const TIER_SETTINGS: Record<DeviceQualityTier, { enabled: boolean; mapSize: number; halfExtent: number; hz: number }> = {
  low: { enabled: false, mapSize: 512, halfExtent: 30, hz: 0 },
  medium: { enabled: false, mapSize: 1024, halfExtent: 30, hz: 0 },
  high: { enabled: true, mapSize: 2048, halfExtent: 28, hz: 30 },
  ultra: { enabled: true, mapSize: 4096, halfExtent: 34, hz: 60 },
};

export class DynamicShadowRig {
  private readonly settings: (typeof TIER_SETTINGS)[DeviceQualityTier];
  private readonly lightOffset: THREE.Vector3;
  private readonly focus = new THREE.Vector3();
  private accumulatorSec = 0;
  private shadowUpdates = 0;

  constructor(
    private readonly renderer: THREE.WebGLRenderer,
    private readonly keyLight: THREE.DirectionalLight,
    qualityTier: DeviceQualityTier
  ) {
    this.settings = TIER_SETTINGS[qualityTier] ?? TIER_SETTINGS.high;
    this.lightOffset = keyLight.position.clone();
    if (!this.settings.enabled || !renderer.shadowMap) return;

    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.shadowMap.autoUpdate = false;
    renderer.shadowMap.needsUpdate = true;

    keyLight.castShadow = true;
    keyLight.shadow.mapSize.set(this.settings.mapSize, this.settings.mapSize);
    keyLight.shadow.bias = -0.0004;
    keyLight.shadow.normalBias = 0.02;
    keyLight.shadow.radius = 3;
    const cam = keyLight.shadow.camera;
    const e = this.settings.halfExtent;
    cam.left = -e;
    cam.right = e;
    cam.top = e;
    cam.bottom = -e;
    cam.near = 5;
    cam.far = 140;
    cam.updateProjectionMatrix();
    if (keyLight.target.parent == null && keyLight.parent) {
      keyLight.parent.add(keyLight.target);
    }
    // Discard any shadow map allocated with the old size
    keyLight.shadow.map?.dispose();
    (keyLight.shadow as { map: THREE.WebGLRenderTarget | null }).map = null;
  }

  /** Marks meshes (e.g. player skinned meshes) as shadow casters when shadows are on. */
  public registerCaster(object: THREE.Object3D): void {
    if (!this.settings.enabled) return;
    object.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) child.castShadow = true;
    });
  }

  public update(deltaSec: number, focusPoint: [number, number, number]): void {
    if (!this.settings.enabled) return;
    // Snap the focus to shadow texels to avoid shimmering as the frustum slides
    const texel = (this.settings.halfExtent * 2) / this.settings.mapSize;
    this.focus.set(
      Math.round(focusPoint[0] / texel) * texel,
      0,
      Math.round(focusPoint[2] / texel) * texel
    );
    this.keyLight.position.copy(this.focus).add(this.lightOffset);
    this.keyLight.target.position.copy(this.focus);
    this.keyLight.target.updateMatrixWorld();

    this.accumulatorSec += Math.max(0, deltaSec);
    const interval = 1 / this.settings.hz;
    if (this.accumulatorSec >= interval) {
      this.accumulatorSec %= interval;
      this.renderer.shadowMap.needsUpdate = true;
      this.shadowUpdates++;
    }
  }

  public getSummary(): DynamicShadowSummary {
    return {
      enabled: this.settings.enabled,
      mapSize: this.settings.mapSize,
      frustumHalfExtent: this.settings.halfExtent,
      updatesPerSecond: this.settings.hz,
      shadowUpdates: this.shadowUpdates,
    };
  }
}
