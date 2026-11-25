import { ballPlaneVelocity, classicEventTicks, classicLineupStat, classicMatchFacts, clubCode, matchClockLabel } from "./classicMatchMarkers";

describe("classic match bar", () => {
  test("abbreviates clubs and formats the match clock", () => {
    expect(clubCode("Coventry")).toBe("COV");
    expect(clubCode("Nottingham Forest")).toBe("NOT");
    expect(matchClockLabel(517, 8)).toBe("08:37");
    expect(matchClockLabel(null, 12)).toBe("12'");
  });

  test("reads ball width from z and keeps a 2D y when z is absent", () => {
    expect(ballPlaneVelocity({ x: 4, y: 1.2, z: -6 })).toEqual({ x: 4, y: -6 });
    expect(ballPlaneVelocity({ x: 2, y: 3 })).toEqual({ x: 2, y: 3 });
  });

  test("counts filed events and leaves an empty feed unfiled", () => {
    expect(classicMatchFacts([])).toBeNull();
    expect(
      classicMatchFacts([
        { type: "goal", minute: 16 },
        { type: "shot", minute: 20 },
        { event_type: "save", minute: 22 },
        { type: "corner", minute: 30 },
        { type: "foul", minute: 40 },
        { type: "yellow_card", minute: 41 },
        { type: "pass", minute: 12 },
      ]),
    ).toEqual({ shots: 3, onTarget: 2, corners: 1, fouls: 1, yellow: 1, red: 0 });
  });

  test("places goals, cards, and substitutions on the rail", () => {
    expect(
      classicEventTicks([
        { type: "goal", minute: 16, side: "away" },
        { event_type: "yellow_card", time_seconds: 600 },
        { type: "pass", minute: 4 },
      ]),
    ).toEqual([
      { minute: 16, kind: "goal", side: "away" },
      { minute: 10, kind: "card", side: null },
    ]);
  });

  test("builds a lineup line from goals, assists, and cards already played", () => {
    const events = [
      { event_type: "kickoff", time_seconds: 0, primary_player_id: "home_9" },
      { event_type: "goal", time_seconds: 210, primary_player_id: "home_9", secondary_player_id: "home_11" },
      { event_type: "yellow_card", time_seconds: 240, primary_player_id: "away_4" },
      { event_type: "goal", time_seconds: 280, primary_player_id: "away_9" },
    ];
    expect(classicLineupStat(events, "home_9", 200)).toMatchObject({ goals: 0, assists: 0, rating: 6.4 });
    expect(classicLineupStat(events, "home_9", 220)).toMatchObject({ goals: 1, assists: 0 });
    expect(classicLineupStat(events, "home_11", 220)).toMatchObject({ goals: 0, assists: 1 });
    expect(classicLineupStat(events, "away_4", 250)).toMatchObject({ yellow: 1, red: 0 });
    expect(classicLineupStat(events, "away_9", 250).goals).toBe(0);
    expect(classicLineupStat(events, "home_9", 220).rating).toBeGreaterThan(7);
  });
});
