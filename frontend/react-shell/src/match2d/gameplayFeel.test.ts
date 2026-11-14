import { RIG_ACTIONS, ATLAS_ROWS, poseFor, presentationAction, cellUv, footSpread } from "./playerRig";
import {
  animationFor,
  computeLiveXgTotals,
  deriveDirectorShot,
  deriveDuelOutcomeOverlay,
  isWoodworkPosition,
  momentumAt,
  passArcColor,
  predictPassReceiver,
  progressivePassMeters,
  staminaWarning,
  type PitchPlayer,
} from "./matchStateAdapter";
import { crowdTargetFor, MatchAudioEngine } from "./matchAudio";

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

describe("gameplay feel: broadcast director camera AI", () => {
  test("wide establishing shot on kickoff", () => {
    const shot = deriveDirectorShot({ eventType: "kickoff", eventAgeMs: 400 });
    expect(shot.kind).toBe("kickoff_wide");
    expect(shot.zoomMultiplier).toBeCloseTo(0.8);
    expect(shot.focus).toEqual({ x: 0.5, y: 0.5 });
  });

  test("split-second scorer zoom cut on goal within 800ms", () => {
    const scorer = { x: 0.88, y: 0.44 };
    const early = deriveDirectorShot({ eventType: "goal", eventAgeMs: 350, scorer });
    expect(early.kind).toBe("goal_cut");
    expect(early.zoomMultiplier).toBeCloseTo(1.8);
    expect(early.focus).toEqual(scorer);

    const afterCut = deriveDirectorShot({ eventType: "goal", eventAgeMs: 1100, scorer });
    expect(afterCut.kind).toBe("none");
  });

  test("set-piece zoom frames attacking box", () => {
    const corner = deriveDirectorShot({ eventType: "corner", ball: { x: 0.98, y: 0.05 } });
    expect(corner.kind).toBe("set_piece");
    expect(corner.zoomMultiplier).toBeCloseTo(1.32);
    expect(corner.focus).toEqual({ x: 0.86, y: 0.5 });
  });

  test("injury time drifts toward trailing side's attacking goal", () => {
    const shot = deriveDirectorShot({ minute: 92, leadingSide: "home", homeAttacksRight: true });
    expect(shot.kind).toBe("injury_time");
    expect(shot.focus).toEqual({ x: 0.3, y: 0.5 });
  });
});

describe("gameplay feel: pass presentation & stamina warnings", () => {
  test("progressivePassMeters measures forward territory gain per side", () => {
    expect(progressivePassMeters({ x: 0.3, y: 0.5 }, { x: 0.5, y: 0.5 }, "home", true)).toBeCloseTo(21);
    expect(progressivePassMeters({ x: 0.7, y: 0.5 }, { x: 0.5, y: 0.5 }, "away", true)).toBeCloseTo(21);
  });

  test("predictPassReceiver identifies teammate nearest trajectory endpoint", () => {
    const passer = player({ playerId: "p1", side: "home", x: 0.4, y: 0.5 });
    const targetMate = player({ playerId: "p2", side: "home", x: 0.68, y: 0.42, shirtNumber: 10 });
    const opp = player({ playerId: "o1", side: "away", x: 0.69, y: 0.42 });
    const traj = [
      { x: 0.4, y: 0.5 },
      { x: 0.7, y: 0.4 },
    ];
    const res = predictPassReceiver(traj, [passer, targetMate, opp], passer);
    expect(res?.player.playerId).toBe("p2");
    expect(res?.target).toEqual({ x: 0.7, y: 0.4 });
  });

  test("passArcColor differentiates pass flight types", () => {
    expect(passArcColor("through_ball")).toBe("#34d399");
    expect(passArcColor("long_pass")).toBe("#fbbf24");
    expect(passArcColor("cross")).toBe("#fb7185");
    expect(passArcColor("ground_pass")).toBe("#67e8f9");
  });

  test("staminaWarning flags low (<50%) and critical (<25%) players", () => {
    expect(staminaWarning(82)).toBeNull();
    expect(staminaWarning(44)).toBe("low");
    expect(staminaWarning(19)).toBe("critical");
    expect(staminaWarning(null)).toBeNull();
  });
});

describe("gameplay feel: momentum crowd & woodwork/tackle audio", () => {
  test("isWoodworkPosition detects near-post goal-line coordinates", () => {
    expect(isWoodworkPosition(0.96, 0.4)).toBe(true);
    expect(isWoodworkPosition(0.5, 0.4)).toBe(false);
  });

  test("momentumAt normalizes 5-minute narrative buckets to [-1, 1]", () => {
    expect(momentumAt([50, 75, 25], 6)).toBeCloseTo(0.5);
    expect(momentumAt([50, 75, 25], 11)).toBeCloseTo(-0.5);
  });

  test("crowdTargetFor swells with momentum magnitude", () => {
    const calm = crowdTargetFor({ ballX: 0.5, momentum: 0 });
    const surging = crowdTargetFor({ ballX: 0.5, momentum: 0.9 });
    expect(surging.gain).toBeGreaterThan(calm.gain);
    expect(surging.freq).toBeGreaterThan(calm.freq);
  });

  test("MatchAudioEngine safely handles woodwork and clatter cues", () => {
    const engine = new MatchAudioEngine();
    engine.setEnabled(true);
    expect(() => engine.triggerCue("woodwork")).not.toThrow();
    expect(() => engine.triggerCue("clatter")).not.toThrow();
    engine.dispose();
  });
});
