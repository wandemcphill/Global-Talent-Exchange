/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Dynamic Stadium Crowd Wave ("La Ola") & Audio-Reactive Camera Trauma Shake (Track 4 Upgrade).
 *
 * Implements:
 * 1. Synchronized circular stadium wave ("La Ola") circulating around North, East, South, West stands.
 * 2. Non-linear camera trauma & impact shake (quadratic trauma decay curve on woodwork, tackles, goals).
 * 3. Zero per-frame allocations; pure mathematical evaluations for 60fps performance.
 */

export type CrowdWaveType = "calm" | "la_ola" | "chant_bounce" | "celebration";

export interface CrowdChoreographyOptions {
  traumaDecayRate?: number;
  maxShakeOffsetMeters?: number;
}

export interface CrowdChoreographySummary {
  waveType: CrowdWaveType;
  wavePhase: number;
  waveActive: boolean;
  cameraTrauma: number;
  shakeMagnitude: number;
}

export class CrowdChoreographyAndImpactSystem {
  private waveType: CrowdWaveType = "calm";
  private wavePhase: number = 0; // Circular phase angle (0 to 2*PI)
  private waveTimerSec: number = 0;
  private waveDurationSec: number = 0;
  private waveSpeed: number = 2.4; // Radians per second around stadium bowl

  // Camera Trauma Shake Model
  private trauma: number = 0; // 0.0 to 1.0
  private traumaDecayRate: number = 1.25; // Decays to 0 in ~0.8s from max
  private maxShakeOffset: number = 0.45; // Max meters of camera displacement
  private shakeTime: number = 0;

  // Pre-allocated scratch return object
  private scratchUpdateResult = {
    cameraShakeOffset: [0, 0, 0] as [number, number, number],
    wavePhase: 0,
    trauma: 0,
  };

  constructor(options?: CrowdChoreographyOptions) {
    if (typeof options?.traumaDecayRate === "number") {
      this.traumaDecayRate = options.traumaDecayRate;
    }
    if (typeof options?.maxShakeOffsetMeters === "number") {
      this.maxShakeOffset = options.maxShakeOffsetMeters;
    }
  }

  /**
   * Triggers an impact shockwave onto the broadcast camera.
   * Uses a quadratic trauma curve: shake = trauma^2
   */
  public triggerCameraTrauma(amount: number): void {
    this.trauma = Math.min(1.0, Math.max(0.0, this.trauma + amount));
  }

  public getTrauma(): number {
    return this.trauma;
  }

  /**
   * Triggers a stadium crowd wave or celebration bounce.
   */
  public triggerCrowdWave(type: CrowdWaveType, durationSec: number = 12): void {
    this.waveType = type;
    this.waveDurationSec = durationSec;
    this.waveTimerSec = 0;
    if (type === "la_ola") {
      this.wavePhase = 0;
    }
  }

  /**
   * Computes the vertical displacement offset for a crowd section at pitch coordinate (x, z).
   */
  public getCrowdSectionOffset(x: number, z: number): number {
    if (this.waveType === "calm") return 0;

    if (this.waveType === "chant_bounce") {
      // All stands bounce synchronously to the rhythm of chants (3Hz)
      return Math.max(0, Math.sin(this.shakeTime * 6.28 * 2.5) * 0.42);
    }

    if (this.waveType === "la_ola") {
      // Circular wave moving around the stadium perimeter
      const theta = Math.atan2(z, x); // -PI to PI
      const diff = Math.sin(theta - this.wavePhase);
      if (diff > 0.65) {
        // High crest of the Mexican wave
        return (diff - 0.65) * 1.8;
      }
      return 0;
    }

    if (this.waveType === "celebration") {
      // Rapid energetic celebratory wave + jumping
      return Math.max(0, Math.sin(this.shakeTime * 14.0 + Math.atan2(z, x) * 2.0) * 0.55);
    }

    return 0;
  }

  /**
   * Updates wave phase and decays camera trauma over time.
   */
  public update(deltaSec: number): {
    cameraShakeOffset: [number, number, number];
    wavePhase: number;
    trauma: number;
  } {
    this.shakeTime += deltaSec;

    // 1. Advance crowd wave
    if (this.waveType !== "calm") {
      this.waveTimerSec += deltaSec;
      this.wavePhase = (this.wavePhase + this.waveSpeed * deltaSec) % (Math.PI * 2);

      if (this.waveTimerSec >= this.waveDurationSec) {
        this.waveType = "calm";
      }
    }

    // 2. Camera trauma decay and quadratic shake calculation
    if (this.trauma > 0) {
      this.trauma = Math.max(0, this.trauma - this.traumaDecayRate * deltaSec);
    }

    const shakeFactor = this.trauma * this.trauma; // Quadratic shake
    const maxOffset = this.maxShakeOffset * shakeFactor;

    if (shakeFactor > 0.001) {
      const dx = Math.sin(this.shakeTime * 38.0) * maxOffset;
      const dy = Math.cos(this.shakeTime * 44.0) * maxOffset * 0.75;
      const dz = Math.sin(this.shakeTime * 31.0) * maxOffset * 0.5;
      this.scratchUpdateResult.cameraShakeOffset[0] = dx;
      this.scratchUpdateResult.cameraShakeOffset[1] = dy;
      this.scratchUpdateResult.cameraShakeOffset[2] = dz;
    } else {
      this.scratchUpdateResult.cameraShakeOffset[0] = 0;
      this.scratchUpdateResult.cameraShakeOffset[1] = 0;
      this.scratchUpdateResult.cameraShakeOffset[2] = 0;
    }

    this.scratchUpdateResult.wavePhase = this.wavePhase;
    this.scratchUpdateResult.trauma = this.trauma;
    return this.scratchUpdateResult;
  }

  public getSummary(): CrowdChoreographySummary {
    return {
      waveType: this.waveType,
      wavePhase: Number(this.wavePhase.toFixed(2)),
      waveActive: this.waveType !== "calm",
      cameraTrauma: Number(this.trauma.toFixed(3)),
      shakeMagnitude: Number((this.trauma * this.trauma).toFixed(3)),
    };
  }

  public dispose(): void {
    this.trauma = 0;
    this.waveType = "calm";
  }
}
