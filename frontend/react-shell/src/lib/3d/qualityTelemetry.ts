/**
 * GTEX Living Football Ecosystem — Shared WebGL 3D Experience Framework
 * Reliable shared quality telemetry foundation:
 * - Measures true frame timing (delta time, rolling FPS, average frame time).
 * - Computes p50 (median) and p95 frame-time percentiles over sample windows.
 * - Distinguishes measured FPS (0 until first sample completes) from configured target FPS.
 * - Monitors WebGL context lifecycle (webglcontextlost with preventDefault, webglcontextrestored).
 * - Handles document visibility state and tab switching without artificial frame spikes.
 * - Implements conservative bounded adaptive tiering with hysteresis and recovery paths.
 * - Safely cleans up animation-frame loops and event observers on unmount.
 * - Does NOT compete with or create duplicate scene render loops.
 */

import { useEffect, useRef, useState } from "react";
import {
  DeviceQualityTier,
  QualityProfile,
  QualityTelemetry,
} from "./GtexSceneTypes";

const ORDERED_TIERS: DeviceQualityTier[] = ["low", "medium", "high", "ultra"];

export interface UseQualityTelemetryOptions {
  /** Active quality profile in effect */
  activeProfile: QualityProfile;
  /** Explicit quality tier currently active */
  qualityTier: DeviceQualityTier;
  /** Base/maximum quality tier allowed for recovery upgrade (defaults to qualityTier or "ultra") */
  maxTier?: DeviceQualityTier;
  /** Whether telemetry monitoring is active (e.g., active in WebGL mode) */
  enabled?: boolean;
  /** Optional container or canvas element ref for WebGL context loss monitoring */
  containerRef?: React.RefObject<HTMLElement | null>;
  /** Optional callback fired when telemetry metrics update */
  onTelemetryUpdate?: (telemetry: QualityTelemetry) => void;
  /** Optional callback for conservative adaptive quality tier changes */
  onAdaptiveTierChange?: (suggestedTier: DeviceQualityTier) => void;
  /** Sample window in milliseconds (default: 500ms) */
  sampleWindowMs?: number;
  /** Enable adaptive tier adjustments (default: true) */
  enableAdaptation?: boolean;
}

export function useQualityTelemetry({
  activeProfile,
  qualityTier,
  maxTier,
  enabled = true,
  containerRef,
  onTelemetryUpdate,
  onAdaptiveTierChange,
  sampleWindowMs = 500,
  enableAdaptation = true,
}: UseQualityTelemetryOptions): QualityTelemetry {
  // Never report configured target FPS as measured FPS: start at 0 until first window completes
  const [telemetry, setTelemetry] = useState<QualityTelemetry>(() => ({
    measuredFps: 0,
    frameTimeMs: 0,
    averageFrameTimeMs: 0,
    p50FrameTimeMs: 0,
    p95FrameTimeMs: 0,
    sampleCount: 0,
    elapsedMs: 0,
    isContextLost: false,
    activeProfile,
    qualityTier,
  }));

  // Ref tracking to avoid stale closures in RAF loop
  const telemetryRef = useRef(telemetry);
  telemetryRef.current = telemetry;

  const callbacksRef = useRef({ onTelemetryUpdate, onAdaptiveTierChange });
  callbacksRef.current = { onTelemetryUpdate, onAdaptiveTierChange };

  // Context loss status tracked via ref for immediate event handler updates
  const isContextLostRef = useRef(false);

  // Maximum tier boundary for recovery
  const maxTierBoundary = maxTier || "ultra";

  useEffect(() => {
    if (!enabled || typeof window === "undefined") {
      return;
    }

    let rafId: number | null = null;
    let lastTime = performance.now();
    let windowStartTime = lastTime;
    let frameCount = 0;
    let windowFrameTimes: number[] = [];
    let lowFpsStreak = 0;
    let highFpsStreak = 0;
    let cooldownWindowsRemaining = 0;

    // Visibility change handler to prevent artificial delta spikes from background throttling
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // Tab backgrounded — discard partial sample window
        frameCount = 0;
        windowFrameTimes = [];
      } else {
        // Tab foregrounded — reset time baseline
        lastTime = performance.now();
        windowStartTime = lastTime;
        frameCount = 0;
        windowFrameTimes = [];
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);

    const tick = (now: number) => {
      const delta = now - lastTime;
      lastTime = now;

      // Filter out anomaly delta frames (e.g. debugger pauses, tab wakeups > 1000ms)
      if (delta > 0 && delta < 1000 && !document.hidden) {
        frameCount++;
        windowFrameTimes.push(delta);
      }

      const windowDuration = now - windowStartTime;
      if (windowDuration >= sampleWindowMs) {
        if (frameCount > 0 && !document.hidden && windowFrameTimes.length > 0) {
          const measuredFps = Math.max(
            1,
            Math.round((frameCount * 1000) / windowDuration)
          );

          // Calculate p50 (median), p95, and average frame-time statistics
          const sortedDeltas = [...windowFrameTimes].sort((a, b) => a - b);
          const p50Index = Math.floor(sortedDeltas.length * 0.5);
          const p95Index = Math.min(
            sortedDeltas.length - 1,
            Math.floor(sortedDeltas.length * 0.95)
          );

          const p50FrameTimeMs = Number(sortedDeltas[p50Index].toFixed(2));
          const p95FrameTimeMs = Number(sortedDeltas[p95Index].toFixed(2));
          const sumDeltas = sortedDeltas.reduce((acc, v) => acc + v, 0);
          const averageFrameTimeMs = Number(
            (sumDeltas / sortedDeltas.length).toFixed(2)
          );
          const currentFrameTimeMs = Number(delta.toFixed(2));

          const nextTelemetry: QualityTelemetry = {
            measuredFps,
            frameTimeMs: currentFrameTimeMs,
            averageFrameTimeMs,
            p50FrameTimeMs,
            p95FrameTimeMs,
            sampleCount: frameCount,
            elapsedMs: Math.round(now),
            isContextLost: isContextLostRef.current,
            activeProfile,
            qualityTier,
          };

          telemetryRef.current = nextTelemetry;
          setTelemetry(nextTelemetry);
          callbacksRef.current.onTelemetryUpdate?.(nextTelemetry);

          // -----------------------------------------------------------------
          // Conservative Adaptive Quality Engine with Hysteresis & Recovery
          // -----------------------------------------------------------------
          if (enableAdaptation) {
            const currentTierIndex = ORDERED_TIERS.indexOf(qualityTier);
            const maxTierIndex = ORDERED_TIERS.indexOf(maxTierBoundary);

            if (cooldownWindowsRemaining > 0) {
              cooldownWindowsRemaining--;
            } else {
              // 1. Degradation Path: Sustained low FPS (< 24) across 3 consecutive sample windows
              if (measuredFps < 24 && currentTierIndex > 0) {
                lowFpsStreak++;
                highFpsStreak = 0;
                if (lowFpsStreak >= 3) {
                  lowFpsStreak = 0;
                  const targetTier = ORDERED_TIERS[currentTierIndex - 1];
                  callbacksRef.current.onAdaptiveTierChange?.(targetTier);
                  // Cooldown hysteresis: 6 sample windows (~3 seconds) before any further change
                  cooldownWindowsRemaining = 6;
                }
              }
              // 2. Recovery Path: Sustained high FPS (>= 90% target or >= 55) across 8 consecutive windows
              else if (
                measuredFps >= Math.min(55, Math.round(activeProfile.targetFps * 0.9)) &&
                currentTierIndex < maxTierIndex &&
                currentTierIndex !== -1
              ) {
                highFpsStreak++;
                lowFpsStreak = 0;
                // Requires 8 sample windows of proven headroom to prevent rapid oscillation
                if (highFpsStreak >= 8) {
                  highFpsStreak = 0;
                  const targetTier = ORDERED_TIERS[currentTierIndex + 1];
                  callbacksRef.current.onAdaptiveTierChange?.(targetTier);
                  // Cooldown hysteresis: 6 sample windows (~3 seconds)
                  cooldownWindowsRemaining = 6;
                }
              }
              // 3. Stable mid-range performance: reset streaks
              else {
                lowFpsStreak = 0;
                highFpsStreak = 0;
              }
            }
          }
        }

        windowStartTime = now;
        frameCount = 0;
        windowFrameTimes = [];
      }

      rafId = requestAnimationFrame(tick);
    };

    rafId = requestAnimationFrame(tick);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
      }
    };
  }, [
    enabled,
    activeProfile,
    qualityTier,
    maxTierBoundary,
    sampleWindowMs,
    enableAdaptation,
  ]);

  // Context Loss and Restoration Listeners
  useEffect(() => {
    const element =
      containerRef?.current ||
      (typeof document !== "undefined" ? document : null);
    if (!element) return;

    const handleContextLost = (event: Event) => {
      // Prevent default to allow WebGL context restoration per WebGL spec
      event.preventDefault();
      isContextLostRef.current = true;
      setTelemetry((prev) => ({ ...prev, isContextLost: true }));
    };

    const handleContextRestored = () => {
      isContextLostRef.current = false;
      setTelemetry((prev) => ({ ...prev, isContextLost: false }));
    };

    element.addEventListener("webglcontextlost", handleContextLost as EventListener);
    element.addEventListener("webglcontextrestored", handleContextRestored as EventListener);

    return () => {
      element.removeEventListener(
        "webglcontextlost",
        handleContextLost as EventListener
      );
      element.removeEventListener(
        "webglcontextrestored",
        handleContextRestored as EventListener
      );
    };
  }, [containerRef]);

  return telemetry;
}
