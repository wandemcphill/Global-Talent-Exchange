import { RIG_ACTIONS, ATLAS_ROWS, poseFor, presentationAction, cellUv, footSpread } from "./playerRig";
import {
  animationFor,
  computeLiveXgTotals,
  deriveDuelOutcomeOverlay,
  type PitchPlayer,
} from "./matchStateAdapter";

const player = (over: Partial<PitchPlayer> = {}): PitchPlayer => ({
  playerId: "p1",
  side: "home",
  x: 0.5,
  y: 0.5,
  shirtNumber: 4,
  name: "Test Player",
  ...over,
});

describe("gameplay feel: new rig actions", () => {
  test("atlas includes slide_tackle, control and feint rows", () => {
    expect(RIG_ACTIONS).toEqual(expect.arrayContaining(["slide_tackle", "control", "feint"]));
    expect(ATLAS_ROWS).toBe(RIG_ACTIONS.length);
  });

  test("slide tackle pose is near-horizontal with extended leg", () => {
    const pose = poseFor("slide_tackle", 0);
    expect(pose.torsoTilt).toBeGreaterThan(1);
    expect(pose.rightLeg[0]).toBeLessThan(-2);
    expect(footSpread(pose)).toBeGreaterThan(footSpread(poseFor("idle", 0)));
  });

  test("feint pose twists torso in opposite directions across the cycle", () => {
    const a = poseFor("feint", 1).torsoTilt;
    const b = poseFor("feint", 3).torsoTilt;
    expect(Math.sign(a)).not.toBe(Math.sign(b));
  });

  test("shoot has a distinct plant phase before the strike", () => {
    const plant = poseFor("shoot", 0);
    const follow = poseFor("shoot", 3);
    expect(plant.leftLeg[1]).toBeCloseTo(0.42);
    expect(follow.lean).not.toBeCloseTo(plant.lean);
  });

  test("new actions are priority actions and survive motion heuristics", () => {
    const motion = { facingDelta: 1.5, speed: 0.05, previousSpeed: 0, hasBall: true };
    expect(presentationAction("slide_tackle", motion)).toBe("slide_tackle");
    expect(presentationAction("control", motion)).toBe("control");
    expect(presentationAction("feint", motion)).toBe("feint");
  });

  test("cellUv resolves distinct rows for new actions", () => {
    const rows = new Set(["tackle", "slide_tackle", "control", "feint"].map((a) => cellUv(a, 0, 0).offsetY));
    expect(rows.size).toBe(4);
  });
});

describe("gameplay feel: animation routing", () => {
  const ctx = { ball: { x: 0.5, y: 0.5 }, primaryPlayerId: "p1" };

  test("sliding tackle state routes to slide_tackle", () => {
    expect(animationFor(player({ state: "slide" }), "tackle", ctx)).toBe("slide_tackle");
    expect(animationFor(player({ state: "standing" }), "tackle", ctx)).toBe("tackle");
  });

  test("movement state strings map to control and feint", () => {
    expect(animationFor(player({ x: 0.1, y: 0.1, state: "first_touch" }), null, { ball: { x: 0.9, y: 0.9 } })).toBe(
      "control",
    );
    expect(animationFor(player({ x: 0.1, y: 0.1, state: "skill move" }), null, { ball: { x: 0.9, y: 0.9 } })).toBe(
      "feint",
    );
  });
});

describe("gameplay feel: duel + xG helpers", () => {
  test("deriveDuelOutcomeOverlay only fires on tackles with a known winner", () => {
    const players = [player()];
    expect(deriveDuelOutcomeOverlay({ eventType: "pass", primaryPlayerId: "p1", players }, 0)).toBeNull();
    expect(deriveDuelOutcomeOverlay({ eventType: "tackle", primaryPlayerId: "ghost", players }, 0)).toBeNull();
    const overlay = deriveDuelOutcomeOverlay({ eventType: "tackle", primaryPlayerId: "p1", players }, 1000);
    expect(overlay).toMatchObject({ playerId: "p1", side: "home", triggeredAtMs: 1000, durationMs: 1200 });
  });

  test("computeLiveXgTotals sums per side", () => {
    const totals = computeLiveXgTotals([
      { side: "home", xg: 0.4 },
      { side: "home", xg: 0.1 },
      { side: "away", xg: 0.25 },
    ]);
    expect(totals.home).toBeCloseTo(0.5);
    expect(totals.away).toBeCloseTo(0.25);
    expect(totals.homeShots).toBe(2);
    expect(totals.awayShots).toBe(1);
    expect(computeLiveXgTotals([])).toEqual({ home: 0, away: 0, homeShots: 0, awayShots: 0 });
  });
});
