/**
 * Automated Test Suite: qualityTelemetry
 * Validates real frame timing measurement, percentile computation (p50, p95),
 * WebGL context lifecycle (loss/restored), tab visibility changes, cleanup,
 * and conservative bounded adaptation with hysteresis and recovery.
 * Uses native React 19 createRoot + act pattern consistent with react-shell.
 */

declare const describe: any;
declare const test: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act, useEffect } from "react";
import { createRoot, Root } from "react-dom/client";
import { useQualityTelemetry, UseQualityTelemetryOptions } from "./qualityTelemetry";
import { QUALITY_PROFILES } from "./GtexSceneRegistry";
import { QualityTelemetry } from "./GtexSceneTypes";

describe("useQualityTelemetry Unit Test Suite", () => {
  let container: HTMLDivElement;
  let root: Root;
  let originalPerformanceNow: typeof performance.now;
  let originalRequestAnimationFrame: typeof requestAnimationFrame;
  let originalCancelAnimationFrame: typeof cancelAnimationFrame;
  let currentTime = 1000;
  let rafCallback: ((time: number) => void) | null = null;
  let rafIdCounter = 1;
  const activeRafIds = new Set<number>();

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);

    currentTime = 1000;
    rafCallback = null;
    activeRafIds.clear();

    originalPerformanceNow = window.performance.now;
    originalRequestAnimationFrame = window.requestAnimationFrame;
    originalCancelAnimationFrame = window.cancelAnimationFrame;

    window.performance.now = jest.fn(() => currentTime);
    window.requestAnimationFrame = jest.fn((cb: FrameRequestCallback) => {
      const id = rafIdCounter++;
      activeRafIds.add(id);
      rafCallback = (t: number) => {
        if (activeRafIds.has(id)) {
          activeRafIds.delete(id);
          cb(t);
        }
      };
      return id;
    });

    window.cancelAnimationFrame = jest.fn((id: number) => {
      activeRafIds.delete(id);
      if (rafCallback) {
        rafCallback = null;
      }
    });

    Object.defineProperty(document, "hidden", {
      writable: true,
      configurable: true,
      value: false,
    });
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    if (container.parentElement) {
      document.body.removeChild(container);
    }
    window.performance.now = originalPerformanceNow;
    window.requestAnimationFrame = originalRequestAnimationFrame;
    window.cancelAnimationFrame = originalCancelAnimationFrame;
    jest.restoreAllMocks();
  });

  const stepFrames = (frameCount: number, deltaMs: number) => {
    for (let i = 0; i < frameCount; i++) {
      currentTime += deltaMs;
      if (rafCallback) {
        const cb = rafCallback;
        rafCallback = null;
        act(() => {
          cb(currentTime);
        });
      }
    }
  };

  const TestHarness: React.FC<{
    options: UseQualityTelemetryOptions;
    onUpdate: (t: QualityTelemetry) => void;
  }> = ({ options, onUpdate }) => {
    const telemetry = useQualityTelemetry(options);
    useEffect(() => {
      onUpdate(telemetry);
    }, [telemetry, onUpdate]);
    return <div data-testid="telemetry-node" data-measured-fps={telemetry.measuredFps} />;
  };

  test("initial telemetry does not report configured target FPS as measured FPS", () => {
    const profile = QUALITY_PROFILES.ultra;
    expect(profile.targetFps).toBe(60);

    let latest: QualityTelemetry | null = null;
    act(() => {
      root.render(
        <TestHarness
          options={{
            activeProfile: profile,
            qualityTier: "ultra",
            enabled: true,
          }}
          onUpdate={(t) => {
            latest = t;
          }}
        />
      );
    });

    expect(latest).not.toBeNull();
    // Initial measured FPS must be 0 before the first sample window completes
    expect(latest!.measuredFps).toBe(0);
    expect(latest!.sampleCount).toBe(0);
    expect(latest!.isContextLost).toBe(false);
    expect(latest!.qualityTier).toBe("ultra");
  });

  test("calculates accurate measured FPS, average, p50, and p95 frame times over sample window", () => {
    const profile = QUALITY_PROFILES.high;
    let latest: QualityTelemetry | null = null;

    act(() => {
      root.render(
        <TestHarness
          options={{
            activeProfile: profile,
            qualityTier: "high",
            enabled: true,
            sampleWindowMs: 500,
          }}
          onUpdate={(t) => {
            latest = t;
          }}
        />
      );
    });

    // Step 30 frames at 16.67ms each (~500ms total = ~60 FPS)
    stepFrames(30, 16.67);

    expect(latest).not.toBeNull();
    expect(latest!.measuredFps).toBeGreaterThanOrEqual(58);
    expect(latest!.measuredFps).toBeLessThanOrEqual(62);
    expect(latest!.averageFrameTimeMs).toBeCloseTo(16.67, 1);
    expect(latest!.p50FrameTimeMs).toBeCloseTo(16.67, 1);
    expect(latest!.p95FrameTimeMs).toBeCloseTo(16.67, 1);
    expect(latest!.sampleCount).toBe(30);
  });

  test("handles document visibility changes by ignoring background frames and resetting baseline", () => {
    const profile = QUALITY_PROFILES.high;
    let latest: QualityTelemetry | null = null;

    act(() => {
      root.render(
        <TestHarness
          options={{
            activeProfile: profile,
            qualityTier: "high",
            enabled: true,
            sampleWindowMs: 500,
          }}
          onUpdate={(t) => {
            latest = t;
          }}
        />
      );
    });

    // Simulate tab backgrounding
    act(() => {
      Object.defineProperty(document, "hidden", { value: true, configurable: true });
      document.dispatchEvent(new Event("visibilitychange"));
    });

    // Simulate throttled frames in background
    stepFrames(5, 500);
    expect(latest!.sampleCount).toBe(0);

    // Simulate tab foregrounding
    act(() => {
      Object.defineProperty(document, "hidden", { value: false, configurable: true });
      document.dispatchEvent(new Event("visibilitychange"));
    });

    // Fresh 30 frames at 16.67ms
    stepFrames(30, 16.67);
    expect(latest!.measuredFps).toBeGreaterThanOrEqual(58);
  });

  test("monitors WebGL context loss (with preventDefault) and context restoration", () => {
    let latest: QualityTelemetry | null = null;
    const canvas = document.createElement("canvas");
    container.appendChild(canvas);

    act(() => {
      root.render(
        <TestHarness
          options={{
            activeProfile: QUALITY_PROFILES.high,
            qualityTier: "high",
            enabled: true,
            containerRef: { current: canvas },
          }}
          onUpdate={(t) => {
            latest = t;
          }}
        />
      );
    });

    expect(latest!.isContextLost).toBe(false);

    // Dispatch context lost
    let defaultPrevented = false;
    act(() => {
      const lostEvent = new Event("webglcontextlost", { cancelable: true });
      canvas.dispatchEvent(lostEvent);
      defaultPrevented = lostEvent.defaultPrevented;
    });

    expect(defaultPrevented).toBe(true);
    expect(latest!.isContextLost).toBe(true);

    // Dispatch context restored
    act(() => {
      canvas.dispatchEvent(new Event("webglcontextrestored"));
    });

    expect(latest!.isContextLost).toBe(false);
  });

  test("properly cleans up RAF and event listeners on unmount", () => {
    const canvas = document.createElement("canvas");
    const removeEventListenerSpy = jest.spyOn(canvas, "removeEventListener");

    act(() => {
      root.render(
        <TestHarness
          options={{
            activeProfile: QUALITY_PROFILES.high,
            qualityTier: "high",
            enabled: true,
            containerRef: { current: canvas },
          }}
          onUpdate={() => {}}
        />
      );
    });

    expect(window.requestAnimationFrame).toHaveBeenCalled();

    act(() => {
      root.unmount();
    });

    expect(window.cancelAnimationFrame).toHaveBeenCalled();
    expect(removeEventListenerSpy).toHaveBeenCalledWith(
      "webglcontextlost",
      expect.any(Function)
    );
    expect(removeEventListenerSpy).toHaveBeenCalledWith(
      "webglcontextrestored",
      expect.any(Function)
    );
  });

  test("conservative adaptation: degrades tier after sustained low FPS (3 consecutive windows)", () => {
    const onAdaptiveTierChange = jest.fn();

    act(() => {
      root.render(
        <TestHarness
          options={{
            activeProfile: QUALITY_PROFILES.high,
            qualityTier: "high",
            enabled: true,
            sampleWindowMs: 500,
            enableAdaptation: true,
            onAdaptiveTierChange,
          }}
          onUpdate={() => {}}
        />
      );
    });

    // Window 1: 8 frames at 65ms each (~15 FPS) -> lowFpsStreak = 1
    stepFrames(8, 65);
    expect(onAdaptiveTierChange).not.toHaveBeenCalled();

    // Window 2: 8 frames at 65ms each -> lowFpsStreak = 2
    stepFrames(8, 65);
    expect(onAdaptiveTierChange).not.toHaveBeenCalled();

    // Window 3: 8 frames at 65ms each -> lowFpsStreak = 3 -> triggers downgrade to 'medium'
    stepFrames(8, 65);
    expect(onAdaptiveTierChange).toHaveBeenCalledTimes(1);
    expect(onAdaptiveTierChange).toHaveBeenCalledWith("medium");
  });

  test("hysteresis: blocks rapid oscillating adaptation during cooldown windows", () => {
    const onAdaptiveTierChange = jest.fn();

    act(() => {
      root.render(
        <TestHarness
          options={{
            activeProfile: QUALITY_PROFILES.high,
            qualityTier: "high",
            enabled: true,
            sampleWindowMs: 500,
            enableAdaptation: true,
            onAdaptiveTierChange,
          }}
          onUpdate={() => {}}
        />
      );
    });

    // Trigger downgrade with 3 degraded windows
    stepFrames(8, 65);
    stepFrames(8, 65);
    stepFrames(8, 65);
    expect(onAdaptiveTierChange).toHaveBeenCalledWith("medium");
    expect(onAdaptiveTierChange).toHaveBeenCalledTimes(1);

    // Windows 4 & 5: low FPS continues, but cooldown is active (cooldownWindowsRemaining > 0)
    stepFrames(8, 65);
    stepFrames(8, 65);
    // No second downgrade triggered immediately
    expect(onAdaptiveTierChange).toHaveBeenCalledTimes(1);
  });

  test("recovery path: upgrades tier after sustained high FPS (8 consecutive windows)", () => {
    const onAdaptiveTierChange = jest.fn();

    act(() => {
      root.render(
        <TestHarness
          options={{
            activeProfile: QUALITY_PROFILES.low,
            qualityTier: "medium",
            maxTier: "ultra",
            enabled: true,
            sampleWindowMs: 500,
            enableAdaptation: true,
            onAdaptiveTierChange,
          }}
          onUpdate={() => {}}
        />
      );
    });

    // Provide 7 windows of 60 FPS (16.67ms per frame, 30 frames per window)
    for (let w = 0; w < 7; w++) {
      stepFrames(30, 16.67);
      expect(onAdaptiveTierChange).not.toHaveBeenCalled();
    }

    // Window 8: 8th consecutive high FPS window -> triggers upgrade to 'high'
    stepFrames(30, 16.67);
    expect(onAdaptiveTierChange).toHaveBeenCalledTimes(1);
    expect(onAdaptiveTierChange).toHaveBeenCalledWith("high");
  });
});
