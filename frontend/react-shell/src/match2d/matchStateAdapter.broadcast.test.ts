import {
  animationFor,
  deriveBroadcastBanner,
  interpolate,
  resolveBallPresentation,
  type PitchFrame,
  type PitchPlayer,
} from "./matchStateAdapter";

const player = (over: Partial<PitchPlayer> & { playerId: string }): PitchPlayer => ({
  side: "home",
  x: 0.5,
  y: 0.5,
  shirtNumber: 1,
  name: over.playerId,
  ...over,
});

describe("context-aware animationFor", () => {
  const shooter = player({ playerId: "h9", x: 0.8, y: 0.5, hasBall: true, shirtNumber: 9 });
  const mate = player({ playerId: "h7", x: 0.3, y: 0.2, animationState: "jog" });
  const awayKeeper = player({ playerId: "a1", side: "away", x: 0.95, y: 0.5, role: "GK", isGoalkeeper: true });
  const farKeeper = player({ playerId: "h1", x: 0.04, y: 0.5, role: "GK", isGoalkeeper: true });
  const ctx = { ball: { x: 0.82, y: 0.5 }, possessionSide: "home" as const, homeAttacksRight: true };

  test("on a shot only the shooter shoots; teammates keep their own movement", () => {
    expect(animationFor(shooter, "shot", ctx)).toBe("shoot");
    expect(animationFor(mate, "shot", ctx)).toBe("jog");
    expect(animationFor(mate, "shot", ctx)).not.toBe("shoot");
  });

  test("only the keeper at the active end dives", () => {
    expect(animationFor(awayKeeper, "shot", ctx)).toBe("dive");
    expect(animationFor(farKeeper, "shot", ctx)).toBe("idle");
    expect(animationFor(awayKeeper, "save", ctx)).toBe("save");
  });

  test("on a goal the scoring side celebrates near the ball, not everyone, and not the conceding side", () => {
    const scorerCtx = { ...ctx, ball: { x: 0.99, y: 0.5, state: "in_goal" }, celebrationSide: "home" as const };
    expect(animationFor(shooter, "goal", { ...scorerCtx, primaryPlayerId: "h9" })).toBe("celebrate");
    expect(animationFor(mate, "goal", scorerCtx)).toBe("jog");
    const conceding = player({ playerId: "a5", side: "away", x: 0.9, y: 0.4, animationState: "walk" });
    expect(animationFor(conceding, "goal", scorerCtx)).toBe("walk");
  });

  test("only involved players tackle on a foul", () => {
    const tackler = player({ playerId: "a4", side: "away", x: 0.81, y: 0.51 });
    const bystander = player({ playerId: "h3", x: 0.1, y: 0.9, animationState: "walk" });
    const fctx = { ...ctx, primaryPlayerId: "a4" };
    expect(animationFor(tackler, "foul", fctx)).toBe("tackle");
    expect(animationFor(bystander, "foul", fctx)).toBe("walk");
  });

  test("velocity and speed ratio drive locomotion when no state is supplied", () => {
    const run = player({ playerId: "h2", x: 0.2, y: 0.2, velocity: { x: 0.1, y: 0 } });
    const amble = player({ playerId: "h4", x: 0.2, y: 0.8, speedRatio: 0.2 });
    expect(animationFor(run, null, ctx)).toBe("sprint");
    expect(animationFor(amble, null, ctx)).toBe("walk");
  });
});

describe("resolveBallPresentation", () => {
  const carrier = player({
    playerId: "h10",
    x: 0.4,
    y: 0.5,
    hasBall: true,
    facing: { x: 1, y: 0 },
  });
  const base = (over: Partial<PitchFrame>): PitchFrame => ({
    timeSeconds: 10,
    players: [carrier],
    ball: { x: 0.41, y: 0.5 },
    ...over,
  });

  test("a controlled ball sits at the carrier's feet, ahead of him", () => {
    const res = resolveBallPresentation(base({ eventType: null }), 1)!;
    expect(res.flightKind).toBe("dribble");
    expect(res.inFlight).toBe(false);
    expect(res.carrier?.playerId).toBe("h10");
    expect(Math.hypot(res.x - carrier.x, res.y - carrier.y)).toBeLessThan(0.03);
    expect(res.x).toBeGreaterThan(carrier.x);
  });

  test("a pass releases the ball from the carrier and keeps it near the ground", () => {
    const res = resolveBallPresentation(
      base({
        eventType: "pass",
        ballTrajectory: [
          { x: 0.4, y: 0.5 },
          { x: 0.5, y: 0.5 },
        ],
      }),
      0.5,
      { x: 0.45, y: 0.5 },
    )!;
    expect(res.inFlight).toBe(true);
    expect(res.carrier).toBeNull();
    expect(res.x).toBeCloseTo(0.45);
    expect(res.flightKind).toBe("ground_pass");
    expect(res.heightMeters).toBe(0);
  });

  test("a cross arcs above the turf and authoritative height wins over the synthetic arc", () => {
    const traj = [
      { x: 0.9, y: 0.05 },
      { x: 0.92, y: 0.5 },
    ];
    const synthetic = resolveBallPresentation(base({ eventType: "cross", ballTrajectory: traj }), 0.5, { x: 0.91, y: 0.3 })!;
    expect(synthetic.flightKind).toBe("cross");
    expect(synthetic.heightMeters).toBeGreaterThan(1);
    const real = resolveBallPresentation(
      base({ eventType: "cross", ballTrajectory: traj, ball: { x: 0.91, y: 0.3, height: 0.4 } }),
      0.5,
      { x: 0.91, y: 0.3 },
    )!;
    expect(real.heightMeters).toBeCloseTo(0.4);
  });

  test("a shot and a goal are classified and a missing ball resolves to null", () => {
    expect(resolveBallPresentation(base({ eventType: "shot" }), 0.3)!.flightKind).toBe("shot");
    expect(resolveBallPresentation(base({ eventType: "goal" }), 1)!.flightKind).toBe("in_goal");
    expect(resolveBallPresentation(base({ ball: null }), 1)).toBeNull();
  });
});

describe("interpolate carries telemetry", () => {
  test("blends velocity, anchors and ball height and keeps possession metadata", () => {
    const a: PitchFrame = {
      timeSeconds: 0,
      players: [player({ playerId: "p", x: 0.2, anchorX: 0.2, anchorY: 0.4, velocity: { x: 0, y: 0 } })],
      ball: { x: 0.2, y: 0.5, height: 0 },
      possessionSide: "home",
      pressureIndex: 0,
    };
    const b: PitchFrame = {
      timeSeconds: 2,
      players: [player({ playerId: "p", x: 0.6, anchorX: 0.4, anchorY: 0.6, velocity: { x: 0.2, y: 0 } })],
      ball: { x: 0.6, y: 0.5, height: 2 },
      possessionSide: "away",
      pressureIndex: 1,
    };
    const mid = interpolate(a, b, 0.5);
    expect(mid.players[0].anchorX).toBeCloseTo(0.3);
    expect(mid.players[0].velocity?.x).toBeCloseTo(0.1);
    expect(mid.ball?.height).toBeCloseTo(1);
    expect(mid.pressureIndex).toBeCloseTo(0.5);
    expect(interpolate(a, b, 0.25).possessionSide).toBe("home");
    expect(interpolate(a, b, 0.75).possessionSide).toBe("away");
  });
});

describe("deriveBroadcastBanner", () => {
  const frame = (over: Partial<PitchFrame>): PitchFrame => ({
    timeSeconds: 600,
    clockMinute: 10,
    homeScore: 1,
    awayScore: 0,
    players: [player({ playerId: "h9", shirtNumber: 9, name: "Nine", hasBall: true })],
    ball: { x: 0.9, y: 0.5 },
    ...over,
  });

  test("a goal names the scorer, team, minute and score from the frame", () => {
    const banner = deriveBroadcastBanner(frame({ eventType: "goal", primaryPlayerId: "h9" }), {
      homeName: "Lagos FC",
      awayName: "Accra",
    })!;
    expect(banner.badge).toBe("GOAL!");
    expect(banner.headline).toContain("#9 Nine");
    expect(banner.headline).toContain("Lagos FC");
    expect(banner.minuteLabel).toBe("10'");
    expect(banner.scoreline).toBe("1 - 0");
  });

  test("cards map to their tones and half-time / full-time are phase driven", () => {
    expect(deriveBroadcastBanner(frame({ eventType: "red_card" }))!.tone).toBe("card_red");
    expect(deriveBroadcastBanner(frame({ eventType: "yellow_card" }))!.tone).toBe("card_yellow");
    expect(deriveBroadcastBanner(frame({ phase: "halftime" }))!.badge).toBe("HALF-TIME");
    expect(deriveBroadcastBanner(frame({ phase: "completed" }))!.badge).toBe("FULL-TIME");
  });

  test("ordinary play and first/second half produce no banner", () => {
    expect(deriveBroadcastBanner(frame({ eventType: "pass", phase: "second_half" }))).toBeNull();
    expect(deriveBroadcastBanner(frame({ phase: "first_half", timeSeconds: 900, clockMinute: 15 }))).toBeNull();
    expect(deriveBroadcastBanner(null)).toBeNull();
  });
});
