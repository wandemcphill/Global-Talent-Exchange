/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Dynamic Pitch Turf Degradation & Wet-Surface Particle Spray System (Phase 4).
 *
 * Implements:
 * 1. Monotonic 90-minute pitch scuff accumulation in high-traffic zones (goalmouths, center circle).
 * 2. Sliding-tackle divot marks with instanced turf disruption meshes.
 * 3. Ball rooster-tail / water-spray particle system on wet turf (rain / snow conditions).
 *
 * Zero per-frame heap allocations; pre-allocated Three.js geometries and instanced buffers.
 */

import * as THREE from "three";

export interface PitchTurfDegradationOptions {
  maxDivots?: number;
  maxSprayParticles?: number;
}

export interface TurfUpdateOptions {
  deltaSec: number;
  clockMinute: number;
  weatherPreset: string;
  ballPosition3D: [number, number, number];
  ballVelocity?: [number, number, number] | null;
}

export interface PitchTurfDegradationSummary {
  activeDivotCount: number;
  maxDivots: number;
  accumulatedWearFactor: number;
  goalmouthWearOpacity: number;
  activeSprayParticleCount: number;
  isWetTurfActive: boolean;
}

export class PitchTurfDegradationSystem {
  public readonly rootGroup: THREE.Group;

  // Goalmouth & Center Circle Wear Meshes
  private homeGoalmouthWear: THREE.Mesh;
  private awayGoalmouthWear: THREE.Mesh;
  private centerCircleWear: THREE.Mesh;
  private goalmouthWearMaterial: THREE.MeshBasicMaterial;
  private centerCircleWearMaterial: THREE.MeshBasicMaterial;

  // Slide-tackle Divots InstancedMesh
  private divotMesh: THREE.InstancedMesh;
  private maxDivots: number = 32;
  private activeDivotCount: number = 0;
  private nextDivotIndex: number = 0;
  private dummyTransform = new THREE.Object3D();

  // Wet-Turf Ball Spray Particles
  private sprayParticles: THREE.Points;
  private sprayGeometry: THREE.BufferGeometry;
  private sprayMaterial: THREE.PointsMaterial;
  private maxSprayParticles: number = 128;
  private sprayPositions: Float32Array;
  private sprayVelocities: Float32Array;
  private sprayLifetimes: Float32Array; // remaining life in seconds
  private activeSprayCount: number = 0;
  private isWetTurf: boolean = false;

  // Wear factor (0.0 to 1.0 based on match minutes)
  private accumulatedWearFactor: number = 0.0;

  constructor(scene: THREE.Scene, options?: PitchTurfDegradationOptions) {
    this.rootGroup = new THREE.Group();
    this.rootGroup.name = "PitchTurfDegradationSystem";
    this.maxDivots = options?.maxDivots ?? 32;
    this.maxSprayParticles = options?.maxSprayParticles ?? 128;

    // -------------------------------------------------------------------------
    // 1. Goalmouth & Center Circle Wear Patches (y = 0.008)
    // -------------------------------------------------------------------------
    const wearGeo = new THREE.PlaneGeometry(12, 7.5);
    wearGeo.rotateX(-Math.PI / 2);

    this.goalmouthWearMaterial = new THREE.MeshBasicMaterial({
      color: 0x2e2316, // Churned mud/earth brown
      transparent: true,
      opacity: 0.0,
      depthWrite: false,
    });

    this.homeGoalmouthWear = new THREE.Mesh(wearGeo, this.goalmouthWearMaterial);
    this.homeGoalmouthWear.position.set(-50.0, 0.008, 0);
    this.rootGroup.add(this.homeGoalmouthWear);

    this.awayGoalmouthWear = new THREE.Mesh(wearGeo, this.goalmouthWearMaterial);
    this.awayGoalmouthWear.position.set(50.0, 0.008, 0);
    this.rootGroup.add(this.awayGoalmouthWear);

    const circleWearGeo = new THREE.CircleGeometry(8.5, 32);
    circleWearGeo.rotateX(-Math.PI / 2);

    this.centerCircleWearMaterial = new THREE.MeshBasicMaterial({
      color: 0x332a1b,
      transparent: true,
      opacity: 0.0,
      depthWrite: false,
    });
    this.centerCircleWear = new THREE.Mesh(circleWearGeo, this.centerCircleWearMaterial);
    this.centerCircleWear.position.set(0, 0.007, 0);
    this.rootGroup.add(this.centerCircleWear);

    // -------------------------------------------------------------------------
    // 2. Sliding-Tackle Divots (InstancedMesh)
    // -------------------------------------------------------------------------
    const divotGeo = new THREE.PlaneGeometry(0.85, 0.35);
    divotGeo.rotateX(-Math.PI / 2);
    const divotMat = new THREE.MeshBasicMaterial({
      color: 0x291d12, // Dark churned turf earth
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    this.divotMesh = new THREE.InstancedMesh(divotGeo, divotMat, this.maxDivots);
    this.divotMesh.name = "SlideTackleDivots";
    this.divotMesh.count = 0;

    // Hide all instances below pitch until placed
    this.dummyTransform.position.set(0, -999, 0);
    this.dummyTransform.updateMatrix();
    for (let i = 0; i < this.maxDivots; i++) {
      this.divotMesh.setMatrixAt(i, this.dummyTransform.matrix);
    }
    this.divotMesh.instanceMatrix.needsUpdate = true;
    this.rootGroup.add(this.divotMesh);

    // -------------------------------------------------------------------------
    // 3. Wet-Turf Ball Spray / Rooster-Tail Particle System
    // -------------------------------------------------------------------------
    this.sprayGeometry = new THREE.BufferGeometry();
    this.sprayPositions = new Float32Array(this.maxSprayParticles * 3);
    this.sprayVelocities = new Float32Array(this.maxSprayParticles * 3);
    this.sprayLifetimes = new Float32Array(this.maxSprayParticles);

    // Initialize all particles below ground
    for (let i = 0; i < this.maxSprayParticles; i++) {
      this.sprayPositions[i * 3 + 1] = -10;
      this.sprayLifetimes[i] = 0;
    }
    this.sprayGeometry.setAttribute(
      "position",
      new THREE.BufferAttribute(this.sprayPositions, 3)
    );

    this.sprayMaterial = new THREE.PointsMaterial({
      color: 0xdbeafe,
      size: 0.28,
      transparent: true,
      opacity: 0.65,
      depthWrite: false,
    });

    this.sprayParticles = new THREE.Points(this.sprayGeometry, this.sprayMaterial);
    this.sprayParticles.name = "WetTurfBallSpray";
    this.rootGroup.add(this.sprayParticles);

    scene.add(this.rootGroup);
  }

  /**
   * Records a slide-tackle turf divot mark oriented along the slide vector.
   */
  public addSlideTackleDivot(x: number, z: number, angleRad: number): void {
    const idx = this.nextDivotIndex;
    this.nextDivotIndex = (this.nextDivotIndex + 1) % this.maxDivots;
    if (this.activeDivotCount < this.maxDivots) {
      this.activeDivotCount++;
      this.divotMesh.count = this.activeDivotCount;
    }

    this.dummyTransform.position.set(x, 0.012, z);
    this.dummyTransform.rotation.set(0, angleRad, 0);
    this.dummyTransform.scale.set(1.0 + Math.random() * 0.3, 1.0, 1.0 + Math.random() * 0.2);
    this.dummyTransform.updateMatrix();

    this.divotMesh.setMatrixAt(idx, this.dummyTransform.matrix);
    this.divotMesh.instanceMatrix.needsUpdate = true;
  }

  /**
   * Updates wear opacity from match minute and advances spray particles.
   */
  public update(options: TurfUpdateOptions): void {
    const { deltaSec, clockMinute, weatherPreset, ballPosition3D, ballVelocity } = options;

    // 1. Advance high-traffic wear factor (0.0 at 0' to 0.42 at 90'+)
    this.accumulatedWearFactor = Math.min(1.0, Math.max(0.0, clockMinute / 90.0));
    const targetGoalmouthOpacity = this.accumulatedWearFactor * 0.45;
    const targetCenterOpacity = this.accumulatedWearFactor * 0.28;

    this.goalmouthWearMaterial.opacity = THREE.MathUtils.lerp(
      this.goalmouthWearMaterial.opacity,
      targetGoalmouthOpacity,
      deltaSec * 2.0
    );
    this.centerCircleWearMaterial.opacity = THREE.MathUtils.lerp(
      this.centerCircleWearMaterial.opacity,
      targetCenterOpacity,
      deltaSec * 2.0
    );

    // 2. Determine wet turf condition (rain / snow presets)
    this.isWetTurf = weatherPreset === "rain" || weatherPreset === "snow";

    // 3. Emit spray particles when ball is traveling fast on or near turf
    const [bx, by, bz] = ballPosition3D;
    const isBallOnTurf = by <= 0.35;
    let ballSpeed = 0;
    if (ballVelocity) {
      ballSpeed = Math.hypot(ballVelocity[0], ballVelocity[2]);
    }

    if (this.isWetTurf && isBallOnTurf && ballSpeed >= 4.0) {
      // Emit 2-4 droplets per frame
      const emitCount = Math.min(4, Math.floor(ballSpeed * 0.35));
      for (let e = 0; e < emitCount; e++) {
        this.emitSprayParticle(bx, by, bz, ballVelocity!);
      }
    }

    // 4. Update living spray particles
    let liveCount = 0;
    const posAttr = this.sprayGeometry.getAttribute("position") as THREE.BufferAttribute;
    const positions = posAttr.array as Float32Array;

    for (let i = 0; i < this.maxSprayParticles; i++) {
      if (this.sprayLifetimes[i] > 0) {
        this.sprayLifetimes[i] -= deltaSec;
        if (this.sprayLifetimes[i] <= 0) {
          positions[i * 3 + 1] = -10; // Send below ground
        } else {
          liveCount++;
          // Apply velocity and gravity
          positions[i * 3] += this.sprayVelocities[i * 3] * deltaSec;
          this.sprayVelocities[i * 3 + 1] -= 9.81 * deltaSec; // Gravity
          positions[i * 3 + 1] += this.sprayVelocities[i * 3 + 1] * deltaSec;
          positions[i * 3 + 2] += this.sprayVelocities[i * 3 + 2] * deltaSec;

          // Ground bounce damping
          if (positions[i * 3 + 1] < 0.02) {
            positions[i * 3 + 1] = 0.02;
            this.sprayVelocities[i * 3 + 1] *= -0.3;
          }
        }
      }
    }
    this.activeSprayCount = liveCount;
    posAttr.needsUpdate = true;
  }

  private emitSprayParticle(
    bx: number,
    by: number,
    bz: number,
    ballVel: [number, number, number]
  ): void {
    // Find slot with expired lifetime
    for (let i = 0; i < this.maxSprayParticles; i++) {
      if (this.sprayLifetimes[i] <= 0) {
        this.sprayLifetimes[i] = 0.35 + Math.random() * 0.25; // 0.35s - 0.60s life
        const posAttr = this.sprayGeometry.getAttribute("position") as THREE.BufferAttribute;
        const positions = posAttr.array as Float32Array;

        // Position slightly behind ball contact point
        positions[i * 3] = bx - ballVel[0] * 0.04 + (Math.random() - 0.5) * 0.15;
        positions[i * 3 + 1] = Math.max(0.04, by * 0.5);
        positions[i * 3 + 2] = bz - ballVel[2] * 0.04 + (Math.random() - 0.5) * 0.15;

        // Reverse fan velocity
        this.sprayVelocities[i * 3] = -ballVel[0] * 0.22 + (Math.random() - 0.5) * 1.5;
        this.sprayVelocities[i * 3 + 1] = 1.2 + Math.random() * 1.8; // Upward plume
        this.sprayVelocities[i * 3 + 2] = -ballVel[2] * 0.22 + (Math.random() - 0.5) * 1.5;
        break;
      }
    }
  }

  public getDivotCount(): number {
    return this.activeDivotCount;
  }

  public getWearIntensity(): number {
    return this.accumulatedWearFactor;
  }

  public getSummary(): PitchTurfDegradationSummary {
    return {
      activeDivotCount: this.activeDivotCount,
      maxDivots: this.maxDivots,
      accumulatedWearFactor: Number(this.accumulatedWearFactor.toFixed(3)),
      goalmouthWearOpacity: Number(this.goalmouthWearMaterial.opacity.toFixed(3)),
      activeSprayParticleCount: this.activeSprayCount,
      isWetTurfActive: this.isWetTurf,
    };
  }

  public dispose(): void {
    this.homeGoalmouthWear.geometry.dispose();
    this.goalmouthWearMaterial.dispose();
    this.awayGoalmouthWear.geometry.dispose();
    this.centerCircleWear.geometry.dispose();
    this.centerCircleWearMaterial.dispose();
    this.divotMesh.geometry.dispose();
    (this.divotMesh.material as THREE.Material).dispose();
    this.sprayGeometry.dispose();
    this.sprayMaterial.dispose();
    this.rootGroup.clear();
    if (this.rootGroup.parent) {
      this.rootGroup.parent.remove(this.rootGroup);
    }
  }
}
