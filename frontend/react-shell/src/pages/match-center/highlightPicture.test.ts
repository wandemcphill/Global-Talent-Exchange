import {
  highlightPictureKey,
  highlightPlaySeconds,
  highlightReel,
  isMatchHighlight,
  rememberPitchSample,
  serverHighlightSamples,
} from "./highlightPicture";

describe("match highlight picture", () => {
  test("a chance brings the pitch on and open play does not", () => {
    expect(isMatchHighlight("shot")).toBe(true);
    expect(isMatchHighlight("goal")).toBe(true);
    expect(isMatchHighlight("save")).toBe(true);
    expect(isMatchHighlight("miss")).toBe(true);
    expect(isMatchHighlight("yellow_card")).toBe(true);
    expect(isMatchHighlight("var_review")).toBe(true);
    expect(isMatchHighlight("pass")).toBe(false);
    expect(isMatchHighlight("open_play")).toBe(false);
    expect(isMatchHighlight("substitution")).toBe(false);
    expect(isMatchHighlight("")).toBe(false);
  });

  test("a chance replays the pictures that led into it", () => {
    let buffer = rememberPitchSample([], {
      matchSeconds: 40,
      players: [{ x: 0.2, y: 0.5 }],
      ball: { x: 0.2, y: 0.5 },
    });
    buffer = rememberPitchSample(buffer, {
      matchSeconds: 42,
      players: [{ x: 0.4, y: 0.5 }],
      ball: { x: 0.4, y: 0.5 },
    });
    buffer = rememberPitchSample(buffer, {
      matchSeconds: 42,
      players: [{ x: 0.55, y: 0.48 }],
      ball: { x: 0.55, y: 0.48 },
    });
    buffer = rememberPitchSample(buffer, {
      matchSeconds: 46,
      players: [{ x: 0.8, y: 0.5 }],
      ball: { x: 0.82, y: 0.5 },
    });
    const same = rememberPitchSample(buffer, {
      matchSeconds: 47,
      players: [{ x: 0.8, y: 0.5 }],
      ball: { x: 0.82, y: 0.5 },
    });
    expect(same).toHaveLength(buffer.length);
    const reel = highlightReel(buffer);
    expect(reel[0].timeSeconds).toBe(40);
    expect(reel[reel.length - 1].players[0].x).toBe(0.8);
    expect(highlightPlaySeconds(reel)).toBeGreaterThanOrEqual(4);
    expect(highlightPlaySeconds(reel)).toBeLessThanOrEqual(8);
    const restarted = rememberPitchSample(buffer, {
      matchSeconds: 5,
      players: [{ x: 0.1, y: 0.5 }],
      ball: { x: 0.1, y: 0.5 },
    });
    expect(restarted).toHaveLength(1);
    expect(restarted[0].timeSeconds).toBe(5);
  });

  test("a served chance is the attack in the order it was played", () => {
    const samples = serverHighlightSamples([
      { time_seconds: 38, players: [{ x: 0.3 }], ball: { x: 0.3 } },
      { time_seconds: 41.5, players: [{ x: 0.62 }], ball: { x: 0.66 } },
      { time_seconds: 44, players: [{ x: 0.86 }], ball: { x: 0.9 } },
      { time_seconds: 50, players: [] },
    ]);
    expect(samples.map((sample) => sample.timeSeconds)).toEqual([38, 41.5, 44]);
    expect(samples[2].ball).toEqual({ x: 0.9 });
  });

  test("a chance the match is still holding plays after open play has resumed", () => {
    expect(
      highlightPictureKey({
        serverEventId: "shot-1",
        serverFrameCount: 3,
        liveActionType: "pass",
        latestIsHighlight: false,
      }),
    ).toBe("served:shot-1");
    expect(
      highlightPictureKey({
        liveActionType: "shot",
        latestEventId: "shot-1",
      }),
    ).toBe("live:shot-1");
    expect(highlightPictureKey({ liveActionType: "pass", latestIsHighlight: false })).toBe("");
  });
});
