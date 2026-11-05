import {
  pitchTo3D,
  threeDToPitch,
  FIFA_PITCH_DIMENSIONS,
  PITCH_LANDMARKS,
  PITCH_BOUNDS,
} from "./matchCoordinates";

describe("matchCoordinates", () => {
  test("transforms pitch center (50, 50) to (0, 0, 0)", () => {
    const [x, y, z] = pitchTo3D({ x: 50, y: 50 }, 0);
    expect(x).toBeCloseTo(0, 4);
    expect(y).toBeCloseTo(0, 4);
    expect(z).toBeCloseTo(0, 4);
  });

  test("transforms left goal center (0, 50) to (-52.5, 0, 0)", () => {
    const [x, y, z] = pitchTo3D({ x: 0, y: 50 }, 0);
    expect(x).toBeCloseTo(-52.5, 4);
    expect(y).toBeCloseTo(0, 4);
    expect(z).toBeCloseTo(0, 4);
  });

  test("transforms right goal center (100, 50) to (+52.5, 0, 0)", () => {
    const [x, y, z] = pitchTo3D({ x: 100, y: 50 }, 0);
    expect(x).toBeCloseTo(52.5, 4);
    expect(y).toBeCloseTo(0, 4);
    expect(z).toBeCloseTo(0, 4);
  });

  test("transforms four corners correctly", () => {
    // Top-left: x=0, y=0 -> (-52.5, 0, -34.0)
    const [tlX, tlY, tlZ] = pitchTo3D({ x: 0, y: 0 }, 0);
    expect(tlX).toBeCloseTo(-52.5, 4);
    expect(tlZ).toBeCloseTo(-34.0, 4);

    // Bottom-right: x=100, y=100 -> (+52.5, 0, +34.0)
    const [brX, brY, brZ] = pitchTo3D({ x: 100, y: 100 }, 0);
    expect(brX).toBeCloseTo(52.5, 4);
    expect(brZ).toBeCloseTo(34.0, 4);
  });

  test("preserves ball elevation height", () => {
    const [x, y, z] = pitchTo3D({ x: 50, y: 50 }, 4.5);
    expect(y).toBeCloseTo(4.5, 4);
  });

  test("clamps negative and out-of-bounds inputs safely", () => {
    const [x1, y1, z1] = pitchTo3D({ x: -20, y: -50 }, -5);
    expect(x1).toBeCloseTo(-52.5, 4);
    expect(z1).toBeCloseTo(-34.0, 4);
    expect(y1).toBe(0);

    const [x2, y2, z2] = pitchTo3D({ x: 140, y: 200 }, 55);
    expect(x2).toBeCloseTo(52.5, 4);
    expect(z2).toBeCloseTo(34.0, 4);
    expect(y2).toBe(PITCH_BOUNDS.maxY);
  });

  test("round-trips normalized coordinates through 3D and back", () => {
    const testPoints = [
      { x: 10, y: 20 },
      { x: 50, y: 50 },
      { x: 85, y: 72.5 },
      { x: 2.3, y: 98.1 },
    ];

    for (const pt of testPoints) {
      const [x3d, , z3d] = pitchTo3D(pt, 0);
      const roundTripped = threeDToPitch(x3d, z3d);
      expect(roundTripped.x).toBeCloseTo(pt.x, 3);
      expect(roundTripped.y).toBeCloseTo(pt.y, 3);
    }
  });

  test("verifies key pitch landmarks match expected FIFA geometry", () => {
    expect(PITCH_LANDMARKS.leftGoalCenter).toEqual([-52.5, 0, 0]);
    expect(PITCH_LANDMARKS.rightGoalCenter).toEqual([52.5, 0, 0]);
    expect(PITCH_LANDMARKS.leftPenaltySpot).toEqual([-41.5, 0, 0]); // -52.5 + 11.0 = -41.5
    expect(PITCH_LANDMARKS.rightPenaltySpot).toEqual([41.5, 0, 0]); // 52.5 - 11.0 = 41.5
  });
});
