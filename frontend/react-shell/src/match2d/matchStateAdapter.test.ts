import {
  acceptSnapshot,
  animationFor,
  effectFor,
  interpolate,
  LiveRenderBuffer,
  metricText,
  pitchSource,
  playerIdentityKey,
  resolveFeedPresentationStatus,
  sceneObjectCount,
  seekTime,
  stepReplayClock,
  suppliedCrest,
  isHighlightMoment,
  extractShotMarkers,
  deriveTouchlineNudge,
  type PitchFrame,
} from "./matchStateAdapter";
import { MatchAudioEngine } from "./matchAudio";

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

  test("interpolation keeps player identity and smoothly interpolates player and ball coordinates", () => {
    const from: PitchFrame = {
      timeSeconds: 10,
      players: [{ playerId: "a", side: "home", x: 0.2, y: 0.4, shirtNumber: 9, name: "A" }],
      ball: { x: 0.2, y: 0.4 },
    };
    const to: PitchFrame = {
      timeSeconds: 12,
      players: [{ playerId: "a", side: "home", x: 0.6, y: 0.8, shirtNumber: 9, name: "A" }],
      ball: { x: 0.6, y: 0.8 },
    };
    const mid = interpolate(from, to, 0.5);
    expect(mid.players).toHaveLength(1);
    expect(mid.players[0].playerId).toBe("a");
    expect(mid.players[0].x).toBeCloseTo(0.4);
    expect(mid.players[0].y).toBeCloseTo(0.6);
    expect(mid.ball?.x).toBeCloseTo(0.4);
    expect(mid.ball?.y).toBeCloseTo(0.6);
  });

  test("handles incoming and outgoing substitutions without omitting substitutes or inheriting outgoing attributes", () => {
    const from: PitchFrame = {
      timeSeconds: 200,
      eventType: "open_play",
      players: [
        { playerId: "home-gk", side: "home", x: 0.06, y: 0.5, shirtNumber: 1, name: "Keeper", role: "GK" },
        { playerId: "home-starter-9", side: "home", x: 0.72, y: 0.48, shirtNumber: 9, name: "Starter Nine", role: "ST", animationState: "jog" },
        { playerId: "away-cb-4", side: "away", x: 0.8, y: 0.5, shirtNumber: 4, name: "Away CB", role: "CB" },
      ],
      ball: { x: 0.5, y: 0.5 },
    };
    const to: PitchFrame = {
      timeSeconds: 202,
      eventType: "substitution",
      players: [
        { playerId: "home-gk", side: "home", x: 0.07, y: 0.5, shirtNumber: 1, name: "Keeper", role: "GK" },
        { playerId: "home-sub-19", side: "home", x: 0.55, y: 0.52, shirtNumber: 19, name: "Super Sub", role: "ST", animationState: "run" },
        { playerId: "away-cb-4", side: "away", x: 0.78, y: 0.5, shirtNumber: 4, name: "Away CB", role: "CB" },
      ],
      ball: { x: 0.52, y: 0.5 },
    };

    // Before substitution boundary (alpha < 0.5): outgoing player still on pitch, incoming not yet introduced
    const beforeBoundary = interpolate(from, to, 0.25);
    expect(beforeBoundary.players.map((p) => p.playerId)).toEqual([
      "home-gk",
      "home-starter-9",
      "away-cb-4",
    ]);

    // At/after substitution boundary (alpha >= 0.5): outgoing player removed, incoming substitute present with own identity/shirt/position
    const atBoundary = interpolate(from, to, 0.5);
    expect(atBoundary.players.map((p) => p.playerId)).toEqual([
      "home-gk",
      "home-sub-19",
      "away-cb-4",
    ]);
    const sub = atBoundary.players.find((p) => p.playerId === "home-sub-19")!;
    expect(sub).toBeDefined();
    expect(sub.shirtNumber).toBe(19);
    expect(sub.name).toBe("Super Sub");
    expect(sub.x).toBeCloseTo(0.55);
    expect(sub.y).toBeCloseTo(0.52);

    // At destination frame (alpha = 1): roster matches authoritative backend roster exactly
    const destination = interpolate(from, to, 1);
    expect(destination.players.map((p) => `${p.side}:${p.playerId}`)).toEqual(
      to.players.map((p) => `${p.side}:${p.playerId}`),
    );
  });

  test("preserves composite side:playerId identity when home and away players share colliding IDs or reordered arrays", () => {
    const from: PitchFrame = {
      timeSeconds: 50,
      players: [
        { playerId: "9", side: "home", x: 0.3, y: 0.3, shirtNumber: 9, name: "Home Nine" },
        { playerId: "9", side: "away", x: 0.7, y: 0.7, shirtNumber: 9, name: "Away Nine" },
        { playerId: "10", side: "home", x: 0.4, y: 0.2, shirtNumber: 10, name: "Home Ten" },
      ],
      ball: { x: 0.5, y: 0.5 },
    };
    // Reordered array in next frame
    const to: PitchFrame = {
      timeSeconds: 52,
      players: [
        { playerId: "9", side: "away", x: 0.6, y: 0.8, shirtNumber: 9, name: "Away Nine" },
        { playerId: "10", side: "home", x: 0.5, y: 0.3, shirtNumber: 10, name: "Home Ten" },
        { playerId: "9", side: "home", x: 0.4, y: 0.4, shirtNumber: 9, name: "Home Nine" },
      ],
      ball: { x: 0.55, y: 0.55 },
    };

    const mid = interpolate(from, to, 0.5);
    expect(mid.players).toHaveLength(3);
    const home9 = mid.players.find((p) => playerIdentityKey(p) === "home:9")!;
    const away9 = mid.players.find((p) => playerIdentityKey(p) === "away:9")!;
    const home10 = mid.players.find((p) => playerIdentityKey(p) === "home:10")!;
    expect(home9.x).toBeCloseTo(0.35);
    expect(home9.y).toBeCloseTo(0.35);
    expect(home9.name).toBe("Home Nine");
    expect(away9.x).toBeCloseTo(0.65);
    expect(away9.y).toBeCloseTo(0.75);
    expect(away9.name).toBe("Away Nine");
    expect(home10.x).toBeCloseTo(0.45);
    expect(home10.y).toBeCloseTo(0.25);
  });

  test("animation and effects follow the event", () => {
    expect(animationFor({ animationState: "run", hasBall: true }, "pass")).toBe("pass");
    expect(animationFor({ role: "GK" }, "save")).toBe("save");
    expect(animationFor({ animationState: "walk" })).toBe("walk");
    expect(animationFor({ animationState: "header" })).toBe("header");
    expect(animationFor({ hasBall: true })).toBe("dribble");
    expect(effectFor("goal")).toBe("goal");
    expect(effectFor("save")).toBe("save");
    expect(effectFor("yellow_card")).toBe("card");
    expect(effectFor("substitution")).toBe("substitution");
    expect(effectFor("unknown")).toBeNull();
  });

  test("live buffer separates snapshotVersion and stream ordering domains, rejects stale/duplicate/malformed frames, and supports reconnect replacement", () => {
    const buffer = new LiveRenderBuffer();
    const basePlayer = { playerId: "a", side: "home" as const, x: 0.2, y: 0.4, shirtNumber: 9, name: "A" };

    // Reject empty/malformed frames
    expect(buffer.push(null as any)).toBe(false);
    expect(buffer.push({ timeSeconds: NaN, players: [basePlayer], ball: null })).toBe(false);
    expect(buffer.push({ timeSeconds: 10, players: [], ball: null })).toBe(false);

    // Accept initial HTTP snapshot with large backend snapshot_version (e.g. 1000200010)
    const snap1 = {
      timeSeconds: 10,
      snapshotVersion: 1_000_200_010,
      source: "snapshot" as const,
      players: [basePlayer],
      ball: { x: 0.2, y: 0.4 },
    };
    expect(buffer.push(snap1, 1000)).toBe(true);

    // Accept subsequent WebSocket stream frame without snapshotVersion (must NOT be rejected by large snapshotVersion!)
    const stream1 = {
      timeSeconds: 11.5,
      frameId: "match-1:23",
      sequence: 23,
      source: "stream" as const,
      players: [{ ...basePlayer, x: 0.4, y: 0.5 }],
      ball: { x: 0.4, y: 0.5 },
    };
    expect(buffer.push(stream1, 1500)).toBe(true);

    // Reject duplicate frameId
    expect(buffer.push({ ...stream1 }, 1550)).toBe(false);

    // Reject out-of-order stream sequence or older timeSeconds
    expect(
      buffer.push(
        {
          timeSeconds: 10.8,
          frameId: "match-1:22",
          sequence: 22,
          source: "stream",
          players: [{ ...basePlayer, x: 0.3, y: 0.45 }],
          ball: { x: 0.3, y: 0.45 },
        },
        1600,
      ),
    ).toBe(false);

    // Reject stale HTTP snapshot with lower snapshotVersion
    expect(
      buffer.push(
        {
          timeSeconds: 12,
          snapshotVersion: 1_000_200_009,
          source: "snapshot",
          players: [{ ...basePlayer, x: 0.5, y: 0.6 }],
          ball: { x: 0.5, y: 0.6 },
        },
        1650,
      ),
    ).toBe(false);

    // Accept identical timestamp when event state updates (e.g. goal or substitution at same timestamp)
    expect(
      buffer.push(
        {
          timeSeconds: 11.5,
          frameId: "match-1:24",
          sequence: 24,
          source: "stream",
          eventType: "goal",
          players: [{ ...basePlayer, x: 0.42, y: 0.52 }],
          ball: { x: 0.98, y: 0.5 },
        },
        1700,
      ),
    ).toBe(true);

    // Reconnection snapshot replacement resets interpolation baseline without rewinding
    buffer.replace(
      {
        timeSeconds: 18,
        snapshotVersion: 2_000_300_036,
        source: "snapshot",
        players: [{ ...basePlayer, x: 0.85, y: 0.5 }],
        ball: { x: 0.85, y: 0.5 },
      },
      2000,
    );
    const afterReconnect = buffer.advanceWallClock(2050);
    expect(afterReconnect.frame?.players[0].x).toBeCloseTo(0.85);
    expect(afterReconnect.trajectoryAlpha).toBe(1);
    expect(afterReconnect.renderTimeSeconds).toBeCloseTo(18);
  });

  test("monotonic wall-clock interpolation handles variable intervals, pause/resume, and speed without rewinding", () => {
    const buffer = new LiveRenderBuffer();
    const p = { playerId: "home-8", side: "home" as const, x: 0.2, y: 0.5, shirtNumber: 8, name: "Eight" };

    buffer.push(
      {
        timeSeconds: 100,
        frameId: "f-100",
        sequence: 1,
        source: "stream",
        players: [p],
        ball: { x: 0.2, y: 0.5 },
      },
      1000,
    );
    buffer.push(
      {
        timeSeconds: 102,
        frameId: "f-102",
        sequence: 2,
        source: "stream",
        players: [{ ...p, x: 0.6 }],
        ball: { x: 0.6, y: 0.5 },
      },
      3000,
    );

    const xs: number[] = [];
    for (let wall = 3000; wall <= 5200; wall += 250) {
      const s = buffer.advanceWallClock(wall, { paused: false, speed: 1 });
      xs.push(s.frame!.players[0].x);
    }
    // Positions must never rewind
    for (let i = 1; i < xs.length; i += 1) {
      expect(xs[i]).toBeGreaterThanOrEqual(xs[i - 1] - 1e-6);
    }

    // Push a third frame with a shorter 0.5s interval, test pause and 2x speed
    buffer.push(
      {
        timeSeconds: 102.5,
        frameId: "f-102.5",
        sequence: 3,
        source: "stream",
        players: [{ ...p, x: 0.8 }],
        ball: { x: 0.8, y: 0.5 },
      },
      5500,
    );

    const beforePause = buffer.advanceWallClock(5600, { paused: false, speed: 1 });
    const duringPause1 = buffer.advanceWallClock(6000, { paused: true, speed: 1 });
    const duringPause2 = buffer.advanceWallClock(6500, { paused: true, speed: 1 });
    expect(duringPause1.renderTimeSeconds).toBeCloseTo(beforePause.renderTimeSeconds, 5);
    expect(duringPause2.renderTimeSeconds).toBeCloseTo(beforePause.renderTimeSeconds, 5);

    const resumedFast = buffer.advanceWallClock(6750, { paused: false, speed: 2 });
    expect(resumedFast.renderTimeSeconds).toBeGreaterThan(duringPause2.renderTimeSeconds);
    expect(resumedFast.renderTimeSeconds).toBeLessThanOrEqual(102.5);
  });

  test("stepReplayClock advances monotonically, respects pause and speed, and stops cleanly at end of replay", () => {
    const pausedTime = stepReplayClock({
      currentTimeSeconds: 120,
      deltaMs: 500,
      durationSeconds: 300,
      paused: true,
      speed: 1,
    });
    expect(pausedTime).toBe(120);

    const halfSpeed = stepReplayClock({
      currentTimeSeconds: 120,
      deltaMs: 1000,
      durationSeconds: 300,
      paused: false,
      speed: 0.5,
    });
    expect(halfSpeed).toBeCloseTo(120.5);

    const doubleSpeed = stepReplayClock({
      currentTimeSeconds: 120,
      deltaMs: 1000,
      durationSeconds: 300,
      paused: false,
      speed: 2,
    });
    expect(doubleSpeed).toBeCloseTo(122);

    const clampedEnd = stepReplayClock({
      currentTimeSeconds: 299.5,
      deltaMs: 2000,
      durationSeconds: 300,
      paused: false,
      speed: 2,
    });
    expect(clampedEnd).toBe(300);
  });

  test("resolveFeedPresentationStatus reports LIVE, DELAYED, RECONNECTING, FEED UNAVAILABLE, and FINAL honestly", () => {
    expect(
      resolveFeedPresentationStatus({
        unavailable: false,
        phase: "completed",
        connectionStatus: "connected",
        lastFrameReceivedAtMs: 1000,
        nowMs: 2000,
        hasRenderableFrame: true,
      }).status,
    ).toBe("FINAL");

    expect(
      resolveFeedPresentationStatus({
        unavailable: true,
        phase: "first_half",
        connectionStatus: "unavailable",
        lastFrameReceivedAtMs: null,
        nowMs: 2000,
        hasRenderableFrame: false,
      }).status,
    ).toBe("FEED UNAVAILABLE");

    expect(
      resolveFeedPresentationStatus({
        unavailable: false,
        phase: "second_half",
        connectionStatus: "reconnecting",
        lastFrameReceivedAtMs: 1000,
        nowMs: 3000,
        hasRenderableFrame: true,
      }).status,
    ).toBe("RECONNECTING");

    const delayed = resolveFeedPresentationStatus({
      unavailable: false,
      phase: "second_half",
      connectionStatus: "connected",
      lastFrameReceivedAtMs: 1000,
      nowMs: 7500,
      hasRenderableFrame: true,
      staleThresholdMs: 4500,
    });
    expect(delayed.status).toBe("DELAYED");
    expect(delayed.ageMs).toBe(6500);

    expect(
      resolveFeedPresentationStatus({
        unavailable: false,
        phase: "second_half",
        connectionStatus: "connected",
        lastFrameReceivedAtMs: 5000,
        nowMs: 6000,
        hasRenderableFrame: true,
      }).status,
    ).toBe("LIVE");
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

  test("highlight playback modes fast-forward dead phases and drop to normal speed during key moments", () => {
    const events = [
      { event_id: "g1", type: "goal", time_seconds: 60 },
      { event_id: "c1", type: "corner", time_seconds: 120 },
    ];
    expect(isHighlightMoment(56, events, "key")).toBe(true);
    expect(isHighlightMoment(30, events, "key")).toBe(false);
    expect(isHighlightMoment(118, events, "key")).toBe(false);
    expect(isHighlightMoment(118, events, "extended")).toBe(true);

    const fastStep = stepReplayClock({
      currentTimeSeconds: 30,
      deltaMs: 1000,
      durationSeconds: 300,
      speed: 1,
      highlightMode: "key",
      events,
    });
    const normalStep = stepReplayClock({
      currentTimeSeconds: 56,
      deltaMs: 1000,
      durationSeconds: 300,
      speed: 1,
      highlightMode: "key",
      events,
    });
    expect(fastStep - 30).toBeGreaterThan(3.5);
    expect(normalStep - 56).toBeCloseTo(1, 3);
  });

  test("extractShotMarkers and deriveTouchlineNudge derive accurate spatial & tactical insights", () => {
    const markers = extractShotMarkers([
      { event_id: "s1", type: "goal", time_seconds: 50, minute: 10, team: "home", x: 88, y: 50, xg: 0.42 },
      { event_id: "s2", type: "save", time_seconds: 95, minute: 19, team: "away", x: 14, y: 46, xg: 0.28 },
    ]);
    expect(markers).toHaveLength(2);
    expect(markers[0].outcome).toBe("goal");
    expect(markers[0].xg).toBeCloseTo(0.42, 2);
    expect(markers[1].outcome).toBe("saved");

    const fatigueNudge = deriveTouchlineNudge({
      players: [
        { playerId: "p1", side: "home", x: 0.6, y: 0.4, shirtNumber: 11, name: "El Mala", staminaPct: 41 },
      ],
      events: [],
      side: "home",
      minute: 64,
      homeScore: 1,
      awayScore: 1,
    });
    expect(fatigueNudge?.kind).toBe("fatigue");
    expect(fatigueNudge?.title).toContain("El Mala");

    const deficitNudge = deriveTouchlineNudge({
      players: [
        { playerId: "p1", side: "home", x: 0.6, y: 0.4, shirtNumber: 11, name: "El Mala", staminaPct: 84 },
      ],
      events: [],
      side: "home",
      minute: 68,
      homeScore: 0,
      awayScore: 1,
    });
    expect(deficitNudge?.kind).toBe("deficit");
    expect(deficitNudge?.presetName).toBe("GEGENPRESS");
  });

  test("MatchAudioEngine safely toggles and processes atmosphere updates in headless environments", () => {
    const audio = new MatchAudioEngine();
    expect(audio.isEnabled()).toBe(false);
    audio.setEnabled(true);
    expect(audio.isEnabled()).toBe(true);
    audio.updateAtmosphere({ ballX: 0.88, dangerZone: "box", eventType: "goal", minute: 24 });
    audio.triggerCue("tactical_order");
    audio.dispose();
    expect(audio.isEnabled()).toBe(false);
  });
});

