/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Adaptive Quality Governor.
 *
 * Closes the loop between the WebGPU/WebGL capability report and real frame times:
 *   - Picks a hardware-appropriate starting tier from the capability report.
 *   - Watches a rolling frame-time window and steps dynamic resolution (pixel ratio)
 *     and post-FX tier down when frames are slow, back up when there is headroom.
 *   - Uses hysteresis + cooldowns so it never oscillates.
 * It never remounts the scene: it only drives pixel ratio and post-FX tier, which can
 * change live. A manual user choice locks the governor until `release()` is called.
 */

import type { DeviceQualityTier } from "../GtexSceneTypes";
import type { WebGpuCapabilityReport } from "./WebGpuCapabilityBridge";

export interface AdaptiveQualityDecision {
  postFxTier: DeviceQualityTier;
  resolutionScale: number;
  changed: boolean;
  reason: string;
}

export interface AdaptiveQualitySummary {
  postFxTier: DeviceQualityTier;
  resolutionScale: number;
  averageFrameMs: number;
  targetFrameMs: number;
  adjustments: number;
  isLocked: boolean;
  lastReason: string;
}

const TIER_ORDER: DeviceQualityTier[] = ["low", "medium", "high", "ultra"];
const SCALE_STEPS = [0.75, 0.85, 1.0];

export function recommendTierFromCapabilities(report: WebGpuCapabilityReport): DeviceQualityTier {
  if (report.preferredBackend === "headless" || report.preferredBackend === "webgl1") return "low";
  let score = 0;
  if (report.preferredBackend === "webgpu") score += 2;
  if (report.maxTextureSize >= 16384) score += 2;
  else if (report.maxTextureSize >= 8192) score += 1;
  if (report.maxAnisotropy >= 16) score += 1;
  if (report.supportsHalfFloatTargets) score += 1;
  if (score >= 5) return "ultra";
  if (score >= 3) return "high";
  return "medium";
}

export class AdaptiveQualityGovernor {
  private postFxTier: DeviceQualityTier;
  private maxTier: DeviceQualityTier;
  private scaleIndex = SCALE_STEPS.length - 1;
  private samples: number[] = [];
  private readonly windowSize = 90;
  private readonly targetFrameMs: number;
  private cooldownSec = 0;
  private adjustments = 0;
  private locked = false;
  private lastReason = "initial";

  constructor(initialTier: DeviceQualityTier, targetFps: number = 60) {
    this.postFxTier = initialTier;
    this.maxTier = initialTier;
    this.targetFrameMs = 1000 / targetFps;
  }

  /** Caps the governor to what the hardware report says the device can sustain. */
  public applyCapabilities(report: WebGpuCapabilityReport): AdaptiveQualityDecision {
    const recommended = recommendTierFromCapabilities(report);
    if (TIER_ORDER.indexOf(recommended) < TIER_ORDER.indexOf(this.maxTier)) {
      this.maxTier = recommended;
    }
    if (!this.locked && TIER_ORDER.indexOf(this.postFxTier) > TIER_ORDER.indexOf(this.maxTier)) {
      this.postFxTier = this.maxTier;
      this.adjustments++;
      this.lastReason = `capabilities:${recommended}`;
      return this.decision(true);
    }
    return this.decision(false);
  }

  /** Manual quality choice from the user: obey it and stop auto-adjusting. */
  public lock(tier: DeviceQualityTier): void {
    this.locked = true;
    this.postFxTier = tier;
    this.scaleIndex = SCALE_STEPS.length - 1;
    this.lastReason = "user-locked";
  }

  public release(): void {
    this.locked = false;
  }

  public recordFrame(frameMs: number, deltaSec: number): AdaptiveQualityDecision {
    if (!Number.isFinite(frameMs) || frameMs <= 0) return this.decision(false);
    this.samples.push(Math.min(frameMs, 250));
    if (this.samples.length > this.windowSize) this.samples.shift();
    this.cooldownSec = Math.max(0, this.cooldownSec - deltaSec);

    if (this.locked || this.cooldownSec > 0 || this.samples.length < this.windowSize) {
      return this.decision(false);
    }

    const avg = this.average();
    // Degrade fast (>15% over budget), upgrade slowly (<70% of budget)
    if (avg > this.targetFrameMs * 1.15) {
      if (this.scaleIndex > 0) {
        this.scaleIndex--;
        return this.commit(`slow ${avg.toFixed(1)}ms: resolution ${SCALE_STEPS[this.scaleIndex]}`, 2);
      }
      const t = TIER_ORDER.indexOf(this.postFxTier);
      if (t > 0) {
        this.postFxTier = TIER_ORDER[t - 1];
        return this.commit(`slow ${avg.toFixed(1)}ms: post-fx ${this.postFxTier}`, 3);
      }
      if (this.scaleIndex > 0) {
        this.scaleIndex--;
        return this.commit(`slow ${avg.toFixed(1)}ms: resolution ${SCALE_STEPS[this.scaleIndex]}`, 2);
      }
    } else if (avg < this.targetFrameMs * 0.7) {
      if (this.scaleIndex < SCALE_STEPS.length - 1) {
        this.scaleIndex++;
        return this.commit(`headroom ${avg.toFixed(1)}ms: resolution ${SCALE_STEPS[this.scaleIndex]}`, 6);
      }
      const t = TIER_ORDER.indexOf(this.postFxTier);
      if (t < TIER_ORDER.indexOf(this.maxTier)) {
        this.postFxTier = TIER_ORDER[t + 1];
        return this.commit(`headroom ${avg.toFixed(1)}ms: post-fx ${this.postFxTier}`, 8);
      }
    }
    return this.decision(false);
  }

  private commit(reason: string, cooldownSec: number): AdaptiveQualityDecision {
    this.adjustments++;
    this.lastReason = reason;
    this.cooldownSec = cooldownSec;
    this.samples = [];
    return this.decision(true);
  }

  private average(): number {
    if (this.samples.length === 0) return 0;
    return this.samples.reduce((a, b) => a + b, 0) / this.samples.length;
  }

  private decision(changed: boolean): AdaptiveQualityDecision {
    return {
      postFxTier: this.postFxTier,
      resolutionScale: SCALE_STEPS[this.scaleIndex],
      changed,
      reason: this.lastReason,
    };
  }

  public getSummary(): AdaptiveQualitySummary {
    return {
      postFxTier: this.postFxTier,
      resolutionScale: SCALE_STEPS[this.scaleIndex],
      averageFrameMs: this.average(),
      targetFrameMs: this.targetFrameMs,
      adjustments: this.adjustments,
      isLocked: this.locked,
      lastReason: this.lastReason,
    };
  }
}
