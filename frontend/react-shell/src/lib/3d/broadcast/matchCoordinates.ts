/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Authoritative Pitch Coordinate Transformations & Landmark Geometry.
 *
 * Maps server-authoritative normalized 2D coordinates [0..100, 0..100]
 * to FIFA standard Three.js metric 3D coordinates [-52.5..+52.5, -34.0..+34.0].
 */

export interface PitchDimensions {
  length: number; // 105.0 meters
  width: number;  // 68.0 meters
  goalWidth: number; // 7.32 meters
  goalHeight: number; // 2.44 meters
  penaltySpotDistance: number; // 11.0 meters
  penaltyAreaLength: number; // 16.5 meters
  penaltyAreaWidth: number; // 40.32 meters
  centerCircleRadius: number; // 9.15 meters
}

export const FIFA_PITCH_DIMENSIONS: PitchDimensions = {
  length: 105.0,
  width: 68.0,
  goalWidth: 7.32,
  goalHeight: 2.44,
  penaltySpotDistance: 11.0,
  penaltyAreaLength: 16.5,
  penaltyAreaWidth: 40.32,
  centerCircleRadius: 9.15,
};

export interface NormalizedPoint {
  x: number; // 0..100
  y: number; // 0..100
}

export interface Metric3DPoint {
  x: number; // -52.5..+52.5 (length along touchline)
  y: number; // 0..elevation (height above pitch)
  z: number; // -34.0..+34.0 (width along goal line)
}

/**
 * Hard physical pitch boundaries with generous runoff buffer (meters).
 */
export const PITCH_BOUNDS = {
  minX: -55.0,
  maxX: 55.0,
  minZ: -36.0,
  maxZ: 36.0,
  minY: 0.0,
  maxY: 30.0, // Maximum reasonable ball flight height
};

/**
 * Transforms server normalized coordinates (0..100) into 3D metric coordinates.
 *
 * @param pt Normalized point where x in [0, 100] (0 = left goal, 100 = right goal)
 *           and y in [0, 100] (0 = top touchline, 100 = bottom touchline).
 * @param heightMeters Authoritative ball/player elevation in meters above pitch (default 0).
 * @param homeAttacksRight Authoritative attack orientation (default true).
 * @returns 3D vector [X, Y, Z] in meters with (0,0,0) at pitch center.
 */
export function pitchTo3D(
  pt: NormalizedPoint,
  heightMeters: number = 0,
  homeAttacksRight: boolean = true
): [number, number, number] {
  // Use strict number check so 0 is not treated as falsy
  const numX = typeof pt.x === "number" && !isNaN(pt.x) ? pt.x : 50;
  const numY = typeof pt.y === "number" && !isNaN(pt.y) ? pt.y : 50;
  const numH = typeof heightMeters === "number" && !isNaN(heightMeters) ? heightMeters : 0;

  const clampedX = Math.max(0, Math.min(100, numX));
  const clampedY = Math.max(0, Math.min(100, numY));
  const clampedH = Math.max(0, Math.min(PITCH_BOUNDS.maxY, numH));

  // Server coordinates:
  // x: 0% = left goal (-52.5m), 50% = center line (0m), 100% = right goal (+52.5m)
  // y: 0% = top touchline (-34.0m), 50% = center line (0m), 100% = bottom touchline (+34.0m)
  const metricX = (clampedX - 50.0) * (FIFA_PITCH_DIMENSIONS.length / 100.0);
  const metricZ = (clampedY - 50.0) * (FIFA_PITCH_DIMENSIONS.width / 100.0);

  // Apply pitch bounds clamping
  const finalX = Math.max(PITCH_BOUNDS.minX, Math.min(PITCH_BOUNDS.maxX, metricX));
  const finalZ = Math.max(PITCH_BOUNDS.minZ, Math.min(PITCH_BOUNDS.maxZ, metricZ));

  return [finalX, clampedH, finalZ];
}

/**
 * Reverse transform from Three.js 3D metric coordinates back to normalized (0..100).
 */
export function threeDToPitch(x: number, z: number): NormalizedPoint {
  const normX = (x / (FIFA_PITCH_DIMENSIONS.length / 100.0)) + 50.0;
  const normY = (z / (FIFA_PITCH_DIMENSIONS.width / 100.0)) + 50.0;
  return {
    x: Math.max(0, Math.min(100, normX)),
    y: Math.max(0, Math.min(100, normY)),
  };
}

/**
 * Key pitch landmarks in 3D metric coordinates.
 */
export const PITCH_LANDMARKS = {
  center: [0, 0, 0] as [number, number, number],
  leftGoalCenter: [-FIFA_PITCH_DIMENSIONS.length / 2, 0, 0] as [number, number, number],
  rightGoalCenter: [FIFA_PITCH_DIMENSIONS.length / 2, 0, 0] as [number, number, number],
  leftPenaltySpot: [-FIFA_PITCH_DIMENSIONS.length / 2 + FIFA_PITCH_DIMENSIONS.penaltySpotDistance, 0, 0] as [number, number, number],
  rightPenaltySpot: [FIFA_PITCH_DIMENSIONS.length / 2 - FIFA_PITCH_DIMENSIONS.penaltySpotDistance, 0, 0] as [number, number, number],
  cornerTopLeft: [-FIFA_PITCH_DIMENSIONS.length / 2, 0, -FIFA_PITCH_DIMENSIONS.width / 2] as [number, number, number],
  cornerTopRight: [FIFA_PITCH_DIMENSIONS.length / 2, 0, -FIFA_PITCH_DIMENSIONS.width / 2] as [number, number, number],
  cornerBottomLeft: [-FIFA_PITCH_DIMENSIONS.length / 2, 0, FIFA_PITCH_DIMENSIONS.width / 2] as [number, number, number],
  cornerBottomRight: [FIFA_PITCH_DIMENSIONS.length / 2, 0, FIFA_PITCH_DIMENSIONS.width / 2] as [number, number, number],
};
