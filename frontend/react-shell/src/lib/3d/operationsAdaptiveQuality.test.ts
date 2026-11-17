import { stepOperationsQuality } from "./operationsAdaptiveQuality";

describe("operations adaptive quality", () => {
  const base = {
    slowFrameThreshold: 24,
    fastFrameThreshold: 18,
    pixelRatio: 1.5,
    maxPixelRatio: 1.5,
    shadowsEnabled: true,
    profileAllowsShadows: true,
    slowWindows: 0,
    fastWindows: 0,
  };

  it("leaves a 60fps desktop frame on the current quality", () => {
    const next = stepOperationsQuality({ ...base, averageFrameMs: 16 });
    expect(next.shadowsEnabled).toBe(true);
    expect(next.pixelRatio).toBe(1.5);
    expect(next.severeStall).toBe(false);
  });

  it("drops shadows on the first sustained stall under 10fps", () => {
    const next = stepOperationsQuality({ ...base, averageFrameMs: 250 });
    expect(next.severeStall).toBe(true);
    expect(next.shadowsEnabled).toBe(false);
    expect(next.pixelRatio).toBe(1);
  });

  it("waits for two slow windows before a mild downgrade", () => {
    const first = stepOperationsQuality({ ...base, averageFrameMs: 40 });
    expect(first.shadowsEnabled).toBe(true);
    expect(first.slowWindows).toBe(1);
    const second = stepOperationsQuality({ ...base, ...first, averageFrameMs: 40 });
    expect(second.shadowsEnabled).toBe(false);
    expect(second.pixelRatio).toBeCloseTo(1.275);
  });
});
