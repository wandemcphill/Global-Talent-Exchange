import { calculateTimelineAdvanceSeconds, SpatialInterpolator } from "./SpatialInterpolator";
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
  test("catches up after a large render gap without skipping intermediate authoritative event frames", () => {
    const eventFrames: SpectatorSafeFrameView[] = [
      frame0,
      { ...frame0, frame_id: "event-frame-1", time_seconds: 11, active_event_id: "event-1" },
      { ...frame0, frame_id: "event-frame-2", time_seconds: 12, active_event_id: "event-2" },
      { ...frame0, frame_id: "event-frame-3", time_seconds: 13, active_event_id: "event-3" },
    ];
    const interpolator = new SpatialInterpolator(eventFrames);
    const latestFrameTimeSeconds = 13;
    let cursor = 10;

    // The delayed callback itself is deliberately bounded and cannot jump to
    // the end of the newly available authoritative frame buffer.
    const delayedFrameAdvance = calculateTimelineAdvanceSeconds({
      currentTimeSeconds: cursor,
      frameDeltaMs: 5000,
      latestFrameTimeSeconds,
      isLive: true,
    });
    expect(delayedFrameAdvance).toBeLessThanOrEqual(0.1);
    cursor += delayedFrameAdvance;
    expect(cursor).toBeLessThan(11);

    const observedEventIds: string[] = [];
    let previousEventId: string | null | undefined;
    let iterations = 0;

    while (cursor < latestFrameTimeSeconds && iterations < 400) {
      const advance = calculateTimelineAdvanceSeconds({
        currentTimeSeconds: cursor,
        frameDeltaMs: 1000 / 60,
        latestFrameTimeSeconds,
        isLive: true,
      });
      expect(advance).toBeGreaterThan(0);
      expect(advance).toBeLessThanOrEqual(0.034);
      cursor = Math.min(latestFrameTimeSeconds, cursor + advance);

      const eventId = interpolator.interpolate(cursor)?.active_event_id;
      if (eventId && eventId !== previousEventId) {
        observedEventIds.push(eventId);
        previousEventId = eventId;
      }
      iterations += 1;
    }

    expect(cursor).toBe(latestFrameTimeSeconds);
    expect(observedEventIds).toEqual(["event-1", "event-2", "event-3"]);
  });

  test("attaches ball to controlled foot during dribbles and blends into a ballistic trajectory with recipient and anticipation markers on passes", () => {
    const passStart: SpectatorSafeFrameView = {
      ...frame0,
      frame_id: "p-start",
      time_seconds: 20.0,
      players: [
        {
          ...frame0.players[0],
          player_id: "passer-8",
          position: { x: 40, y: 50 },
          has_possession: true,
          animation_state: "pass",
        },
        {
          player_id: "runner-9",
          team_id: "home",
          side: "home",
          shirt_number: 9,
          label: "Osimhen",
          role: "ST",
          position: { x: 65, y: 42 },
          facing: { x: 1, y: 0 },
          speed_ratio: 0.75,
          animation_state: "run",
          has_possession: false,
        },
      ],
      ball: {
        position: { x: 40, y: 50 },
        height: 0.0,
        state: "pass",
        owner_player_id: "passer-8",
      },
    };

    const passEnd: SpectatorSafeFrameView = {
      ...passStart,
      frame_id: "p-end",
      time_seconds: 22.0,
      players: [
        {
          ...passStart.players[0],
          position: { x: 43, y: 50 },
          has_possession: false,
          animation_state: "jog",
        },
        {
          ...passStart.players[1],
          position: { x: 70, y: 40 },
          has_possession: true,
          animation_state: "shoot",
        },
      ],
      ball: {
        position: { x: 70, y: 40 },
        height: 0.0,
        state: "pass",
        owner_player_id: "runner-9",
      },
    };

    const interpolator = new SpatialInterpolator([passStart, passEnd]);
    const earlyRelease = interpolator.interpolate(20.2); // alpha = 0.1
    expect(earlyRelease?.ball.contact_foot).toBe("right");
    expect(earlyRelease?.ball.target_player_id).toBe("runner-9");
    const runnerEarly = earlyRelease?.players.find((p) => p.player_id === "runner-9");
    expect(runnerEarly?.is_pass_recipient).toBe(true);
    expect(runnerEarly?.anticipation_pose).toBe("shot_windup");

    const midFlight = interpolator.interpolate(21.0); // alpha = 0.5
    expect(midFlight?.ball.ballistic_apex).toBeGreaterThan(0);
    expect(midFlight?.ball.height).toBeGreaterThan(0.5);
    expect(midFlight?.ball.spin).toBeDefined();
  });

});
