/** Adaptive quality for the Club Operations Centre.

A slow frame is connection-hold time for the GPU, measured as the average
milliseconds between rendered frames. It is not a device benchmark by itself.
Desktop quality stays in place until a window is actually slow. A sustained
stall drops shadows and caps the pixel ratio so the six departments stay usable.
*/

export interface OperationsQualityStep {
  pixelRatio: number;
  shadowsEnabled: boolean;
  slowWindows: number;
  fastWindows: number;
  severeStall: boolean;
}

export function stepOperationsQuality(input: {
  averageFrameMs: number;
  slowFrameThreshold: number;
  fastFrameThreshold: number;
  pixelRatio: number;
  maxPixelRatio: number;
  shadowsEnabled: boolean;
  profileAllowsShadows: boolean;
  slowWindows: number;
  fastWindows: number;
}): OperationsQualityStep {
  const severeStall = input.averageFrameMs >= 100;
  if (severeStall) {
    return {
      pixelRatio: Math.min(input.pixelRatio, 1),
      shadowsEnabled: false,
      slowWindows: 0,
      fastWindows: 0,
      severeStall: true,
    };
  }

  let slowWindows = input.slowWindows;
  let fastWindows = input.fastWindows;
  if (input.averageFrameMs > input.slowFrameThreshold) {
    slowWindows += 1;
    fastWindows = 0;
  } else if (input.averageFrameMs < input.fastFrameThreshold) {
    fastWindows += 1;
    slowWindows = 0;
  } else {
    slowWindows = 0;
    fastWindows = 0;
  }

  let pixelRatio = input.pixelRatio;
  let shadowsEnabled = input.shadowsEnabled;
  if (slowWindows >= 2 && pixelRatio > 0.85) {
    pixelRatio = Math.max(0.85, pixelRatio * 0.85);
    shadowsEnabled = false;
    slowWindows = 0;
  } else if (fastWindows >= 3 && pixelRatio < input.maxPixelRatio) {
    pixelRatio = Math.min(input.maxPixelRatio, pixelRatio / 0.85);
    shadowsEnabled = input.profileAllowsShadows;
    fastWindows = 0;
  }

  return { pixelRatio, shadowsEnabled, slowWindows, fastWindows, severeStall: false };
}
