import {
  acceptSnapshot,
  animationFor,
  effectFor,
  interpolate,
  pitchSource,
  sceneObjectCount,
  metricText,
  seekTime,
  suppliedCrest,
} from "./matchStateAdapter";

describe("match state adapter", () => {
  const frames = [
    { timeSeconds: 0, clockMinute: 0 },
    { timeSeconds: 120, clockMinute: 30 },
    { timeSeconds: 268, clockMinute: 67 },
    { timeSeconds: 360, clockMinute: 90 },
  ];

  test("minute 67 seeks to the frame at that time", () => {
    const pair = seekTime(frames, 268);
    expect(pair.left?.clockMinute).toBe(67);
    expect(pair.t).toBe(1);
    expect(pair.left?.timeSeconds).not.toBe(0);
  });

  test("a lower snapshot version is rejected", () => {
    const kept = acceptSnapshot({ snapshotVersion: 8 }, { snapshotVersion: 7 });
    expect(kept?.snapshotVersion).toBe(8);
  });

  test("interpolation keeps player identity and does not invent a player", () => {
    const from = {
      timeSeconds: 10,
      players: [{ playerId: "a", side: "home" as const, x: 0.2, y: 0.4, shirtNumber: 9, name: "A" }],
      ball: { x: 0.2, y: 0.4 },
    };
    const to = {
      timeSeconds: 12,
      players: [{ playerId: "a", side: "home" as const, x: 0.6, y: 0.8, shirtNumber: 9, name: "A" }],
      ball: { x: 0.6, y: 0.8 },
    };
    const mid = interpolate(from, to, 0.5);
    expect(mid.players).toHaveLength(1);
    expect(mid.players[0].playerId).toBe("a");
    expect(mid.players[0].x).toBeCloseTo(0.4);
    expect(mid.ball?.y).toBeCloseTo(0.6);
  });

  test("animation and effects follow the event", () => {
    expect(animationFor({ animationState: "run", hasBall: true }, "pass")).toBe("pass");
    expect(animationFor({ role: "GK" }, "save")).toBe("save");
    expect(animationFor({ animationState: "walk" })).toBe("walk");
    expect(animationFor({ animationState: "header" })).toBe("header");
    expect(animationFor({ hasBall: true })).toBe("dribble");
    expect(effectFor("goal")).toBe("goal");
    expect(effectFor("unknown")).toBeNull();
  });

  test("a competitive match without frames is unavailable and the showcase is the only demo", () => {
    expect(pitchSource({ matchId: "fixture-1", hasSnapshot: false, hasFrames: false })).toBe("unavailable");
    expect(pitchSource({ matchId: "u2a-006-showcase", hasSnapshot: false, hasFrames: false })).toBe("demo");
    expect(pitchSource({ matchId: "fixture-1", hasSnapshot: true, hasFrames: false })).toBe("live");
  });

  test("null possession renders an em dash", () => {
    expect(metricText(null)).toBe("—");
    expect(metricText(undefined)).toBe("—");
    expect(metricText("")).toBe("—");
    expect(`${metricText(null)} – ${metricText(null)}`).toBe("— – —");
  });

  test("a crest is shown only when a real image url was supplied", () => {
    expect(suppliedCrest(" https://cdn.example/crest.png ")).toBe("https://cdn.example/crest.png");
    expect(suppliedCrest("")).toBeNull();
    expect(suppliedCrest(null)).toBeNull();
  });

  test("one frame with 22 players, the ball and one effect is a bounded draw set", () => {
    expect(sceneObjectCount(22, true)).toBe(25);
  });
});
