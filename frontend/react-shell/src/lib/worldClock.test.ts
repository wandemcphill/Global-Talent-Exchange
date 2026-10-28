declare const describe: any;
declare const test: any;
declare const expect: any;
declare const require: any;
declare const __dirname: string;

process.env.REACT_APP_BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:8000";

import {
  parseWorldClock,
  formatWorldDate,
  formatWorldTime,
  formatProgressionRate,
  WORLD_CLOCK_PATH,
  WorldClockContractError,
} from "./worldClock";
import {
  parseOwnerBriefing,
  briefingTargetPath,
  OWNER_BRIEFING_ENDPOINT,
} from "./ownerBriefing";

const valid = {
  clock_id: "global",
  world_time: "2031-03-14T09:05:00+00:00",
  world_date: "2031-03-14",
  is_paused: false,
  progression_rate: 6,
  virtual_months_per_season: 12,
};

describe("world clock client contract (GET /api/world/clock)", () => {
  test("uses the published endpoint path", () => {
    expect(WORLD_CLOCK_PATH).toBe("/world/clock");
  });

  test("parses the PR #347 response shape", () => {
    expect(parseWorldClock(valid)).toEqual({
      clockId: "global",
      worldTime: "2031-03-14T09:05:00+00:00",
      worldDate: "2031-03-14",
      isPaused: false,
      progressionRate: 6,
      virtualMonthsPerSeason: 12,
    });
    expect(parseWorldClock({ ...valid, world_time: "2031-03-14T09:05:00.123456Z" }).worldDate).toBe("2031-03-14");
  });

  test.each([
    ["non-object", null],
    ["missing clock_id", { ...valid, clock_id: "" }],
    ["timezone-less world_time", { ...valid, world_time: "2031-03-14T09:05:00" }],
    ["bad world_date", { ...valid, world_date: "14/03/2031" }],
    ["date/time mismatch", { ...valid, world_date: "2031-03-15" }],
    ["string pause flag", { ...valid, is_paused: "false" }],
    ["zero rate", { ...valid, progression_rate: 0 }],
    ["fractional months", { ...valid, virtual_months_per_season: 1.5 }],
  ])("rejects %s", (_name: string, raw: unknown) => {
    expect(() => parseWorldClock(raw)).toThrow(WorldClockContractError);
  });

  test("formats in UTC regardless of viewer timezone", () => {
    expect(formatWorldDate("2031-03-14")).toBe("Fri, 14 March 2031");
    expect(formatWorldTime("2031-03-14T23:30:00-02:00")).toBe("01:30 UTC");
    expect(formatProgressionRate(6)).toBe("6x");
  });

  test("no season label is derived anywhere in the client", () => {
    expect(Object.keys(parseWorldClock(valid))).not.toContain("season");
  });
});

describe("clock/briefing sources never use device time or client timers", () => {
  const fs = require("fs");
  const path = require("path");
  const files = [
    "../lib/worldClock.ts",
    "../lib/ownerBriefing.ts",
    "../components/gtex/WorldClockCard.tsx",
    "../components/gtex/OwnerBriefingPanel.tsx",
  ];
  test.each(files)("%s", (rel: string) => {
    const src = fs.readFileSync(path.join(__dirname, rel), "utf8");
    const code = src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
    expect(code).not.toMatch(/Date\.now|new Date\(\)|setInterval|setTimeout|performance\.now/);
  });
});

describe("owner briefing typed boundary", () => {
  test("is honestly unavailable: no endpoint is published", () => {
    expect(OWNER_BRIEFING_ENDPOINT).toBeNull();
  });

  test("keeps only verified persisted events and counts the rest", () => {
    const b = parseOwnerBriefing({
      briefing_id: "b1",
      club_id: "c1",
      world_date: "2031-03-14",
      explanation: "Context only.",
      events: [
        { event_id: "e1", headline: "Won 2-1", occurred_at: "2031-03-13T20:00:00Z", target: { type: "match_result", match_id: "m9" } },
        { headline: "No id", occurred_at: "2031-03-13T20:00:00Z" },
        { event_id: "e3", headline: "", occurred_at: "2031-03-13T20:00:00Z" },
        { event_id: "e4", headline: "Odd link", occurred_at: "2031-03-13T20:00:00Z", target: { type: "wallet", id: "x" } },
      ],
    });
    expect(b.events.map((e: any) => e.eventId)).toEqual(["e1", "e4"]);
    expect(b.rejectedEventCount).toBe(2);
    expect(b.events[1].target).toBeNull();
  });

  test("rejects a briefing without persisted identity", () => {
    expect(() => parseOwnerBriefing({ club_id: "c1", world_date: "2031-03-14", events: [] })).toThrow();
  });

  test("routes to decision, club history and match result", () => {
    expect(briefingTargetPath({ type: "decision", inboxItemId: "i1" })).toBe("/app/inbox");
    expect(briefingTargetPath({ type: "club_history", clubId: "c 1" })).toBe("/app/clubs/c%201/story");
    expect(briefingTargetPath({ type: "match_result", matchId: "m9" })).toBe("/app/match/m9");
    expect(briefingTargetPath(null)).toBeNull();
  });
});
