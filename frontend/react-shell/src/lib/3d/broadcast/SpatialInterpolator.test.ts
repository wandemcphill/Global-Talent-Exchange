import { SpatialInterpolator } from "./SpatialInterpolator";
import { SpectatorSafeFrameView } from "./spectatorContract";
import { PITCH_BOUNDS } from "./matchCoordinates";

describe("SpatialInterpolator", () => {
  const frame0: SpectatorSafeFrameView = {
    frame_id: "f-0",
    time_seconds: 10.0,
    clock_minute: 1,
    phase: "open_play",
    home_score: 0,
    away_score: 0,
    home_attacks_right: true,
    possession_side: "home",
    camera_preset: "broadcast",
    players: [
      {
        player_id: "player-1",
        team_id: "home",
        side: "home",
        shirt_number: 9,
        label: "Osimhen",
        role: "ST",
        position: { x: 40, y: 50 },
        facing: { x: 1, y: 0 },
        speed_ratio: 0.2,
        animation_state: "jog",
      },
    ],
    ball: {
      position: { x: 40, y: 50 },
      height: 0.0,
      state: "rolling",
    },
  };

  const frame1: SpectatorSafeFrameView = {
    frame_id: "f-1",
    time_seconds: 12.0,
    clock_minute: 1,
    phase: "open_play",
    home_score: 0,
    away_score: 0,
    home_attacks_right: true,
    possession_side: "home",
    camera_preset: "broadcast",
    players: [
      {
        player_id: "player-1",
        team_id: "home",
        side: "home",
        shirt_number: 9,
        label: "Osimhen",
        role: "ST",
        position: { x: 60, y: 50 },
        facing: { x: 1, y: 0 },
        speed_ratio: 0.8,
        animation_state: "sprint",
      },
    ],
    ball: {
      position: { x: 60, y: 50 },
      height: 2.0,
      state: "flight",
    },
  };

  test("clamps safely when query time is before first frame or after last frame", () => {
    const interpolator = new SpatialInterpolator([frame0, frame1]);

    const before = interpolator.interpolate(5.0);
    expect(before).not.toBeNull();
    expect(before?.time_seconds).toBe(10.0);
    expect(before?.players[0].position3D[0]).toBeCloseTo(-10.5, 2); // 40% mapped to 3D

    const after = interpolator.interpolate(25.0);
    expect(after).not.toBeNull();
    expect(after?.time_seconds).toBe(12.0);
    expect(after?.players[0].position3D[0]).toBeCloseTo(10.5, 2); // 60% mapped to 3D
  });

  test("smoothly interpolates player position and ball flight at midpoint (alpha = 0.5)", () => {
    const interpolator = new SpatialInterpolator([frame0, frame1]);
    const mid = interpolator.interpolate(11.0); // exactly halfway between 10.0 and 12.0

    expect(mid).not.toBeNull();
    expect(mid?.time_seconds).toBe(11.0);

    // Player position midpoint between x:40 (-10.5m) and x:60 (+10.5m) should be 0.0m
    const p = mid?.players[0];
    expect(p?.position3D[0]).toBeCloseTo(0.0, 3);
    expect(p?.position3D[2]).toBeCloseTo(0.0, 3); // y:50 is 0.0m
    expect(p?.speed_ratio).toBeCloseTo(0.5, 3); // halfway between 0.2 and 0.8

    // Ball height midpoint between 0.0m and 2.0m should be 1.0m
    expect(mid?.ball.height).toBeCloseTo(1.0, 3);
    expect(mid?.ball.position3D[0]).toBeCloseTo(0.0, 3);
    expect(mid?.ball.position3D[1]).toBeCloseTo(1.0, 3);
  });

  test("respects physical pitch bounds during extreme positions", () => {
    const frameExtreme: SpectatorSafeFrameView = {
      ...frame1,
      frame_id: "f-ext",
      time_seconds: 14.0,
      players: [
        {
          ...frame1.players[0],
          position: { x: 100, y: 100 },
        },
      ],
      ball: {
        position: { x: 100, y: 100 },
        height: 25.0,
        state: "flight",
      },
    };

    const interpolator = new SpatialInterpolator([frame1, frameExtreme]);
    const result = interpolator.interpolate(13.0);

    const p = result?.players[0];
    expect(p?.position3D[0]).toBeLessThanOrEqual(PITCH_BOUNDS.maxX);
    expect(p?.position3D[2]).toBeLessThanOrEqual(PITCH_BOUNDS.maxZ);
    expect(result?.ball.height).toBeLessThanOrEqual(PITCH_BOUNDS.maxY);
  });

  test("handles halftime attacking direction change cleanly without cross-pitch flight", () => {
    const frameSecondHalf: SpectatorSafeFrameView = {
      ...frame1,
      frame_id: "f-2",
      time_seconds: 13.0,
      home_attacks_right: false, // Halftime flip
      players: [
        {
          ...frame1.players[0],
          position: { x: 40, y: 50 },
        },
      ],
    };

    const interpolator = new SpatialInterpolator([frame1, frameSecondHalf]);
    const transition = interpolator.interpolate(12.5);

    expect(transition).not.toBeNull();
    // Verify player position stays bounded
    expect(transition?.players[0].position3D[0]).toBeLessThanOrEqual(PITCH_BOUNDS.maxX);
    expect(transition?.players[0].position3D[0]).toBeGreaterThanOrEqual(PITCH_BOUNDS.minX);
  });
});
