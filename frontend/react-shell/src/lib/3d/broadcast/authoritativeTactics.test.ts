import * as fs from "fs";
import * as path from "path";
import { mapAuthoritativeTactics } from "./authoritativeTactics";
import { SpatialInterpolator } from "./SpatialInterpolator";
import { buildFiveMinuteHumanoidMatchFixture } from "./HumanoidMatchPrototypeFixture";

describe("authoritative tactical mapping (GET /matches/{id}/tactics contract)", () => {
  test("maps applied numeric 0..100 fields and valid formations for both sides", () => {
    const cfg = mapAuthoritativeTactics({
      match_id: "m1",
      home: { formation: "4-3-3", press_intensity: 80, defensive_line: 70, tempo: 55, risk_level: 90 },
      away: { formation: "5-3-2", press_intensity: "20", defensive_line: 30, tempo: 40, risk_level: 10 },
    })!;
    expect(cfg.homeFormation).toBe("4-3-3");
    expect(cfg.homePressing).toBe(80);
    expect(cfg.homeDefensiveLine).toBe(70);
    expect(cfg.homeTempo).toBe(55);
    expect(cfg.awayFormation).toBe("5-3-2");
    expect(cfg.awayPressing).toBe(20);
  });

  test("never derives width from risk_level and never emits a width field", () => {
    const cfg = mapAuthoritativeTactics({
      home: { formation: "4-3-3", press_intensity: 50, defensive_line: 50, tempo: 50, risk_level: 100 },
    })!;
    expect((cfg as any).homeWidth).toBeUndefined();
    expect((cfg as any).awayWidth).toBeUndefined();
    expect(JSON.stringify(cfg)).not.toMatch(/risk/i);
  });

  test("rejects invalid formations, clamps range, and returns null for missing data", () => {
    const cfg = mapAuthoritativeTactics({
      home: { formation: "banana", press_intensity: 250, defensive_line: -5, tempo: "x" },
    })!;
    expect(cfg.homeFormation).toBeUndefined();
    expect(cfg.homePressing).toBe(100);
    expect(cfg.homeDefensiveLine).toBe(0);
    expect(cfg.homeTempo).toBeUndefined();
    expect(mapAuthoritativeTactics(null)).toBeNull();
    expect(mapAuthoritativeTactics({})).toBeNull();
  });

  test("neutral backend defaults (50) produce no positional change in the scene", () => {
    const fixture = buildFiveMinuteHumanoidMatchFixture(60);
    const base = new SpatialInterpolator(fixture.frames).interpolate(12)!;
    const shaped = new SpatialInterpolator(fixture.frames);
    shaped.setTacticalConfig(
      mapAuthoritativeTactics({
        home: { press_intensity: 50, defensive_line: 50, tempo: 50 },
        away: { press_intensity: 50, defensive_line: 50, tempo: 50 },
      })
    );
    const s = shaped.interpolate(12)!;
    s.players.forEach((p, i) => {
      expect(p.position3D[0]).toBeCloseTo(base.players[i].position3D[0], 4);
      expect(p.position3D[2]).toBeCloseTo(base.players[i].position3D[2], 4);
    });
  });

  test("high defensive line shifts DEF-role players (role 'DEF' recognised) toward the attack axis", () => {
    const fixture = buildFiveMinuteHumanoidMatchFixture(60);
    const base = new SpatialInterpolator(fixture.frames).interpolate(12)!;
    const it = new SpatialInterpolator(fixture.frames);
    it.setTacticalConfig(mapAuthoritativeTactics({ home: { defensive_line: 90 } }));
    const s = it.interpolate(12)!;
    const idx = base.players.findIndex((p) => p.side === "home" && p.role === "DEF" && !p.has_possession);
    expect(idx).toBeGreaterThanOrEqual(0);
    expect(s.players[idx].position3D[0]).not.toBeCloseTo(base.players[idx].position3D[0], 2);
  });
});

describe("MatchCenter canonical 2D/2.5D broadcast & authoritative tactics contract", () => {
  const src = fs.readFileSync(path.resolve(__dirname, "../../../pages/MatchCenter.tsx"), "utf-8");

  test("2D/2.5D camera and shader toolbars remain active without closed 3D runtime toggles", () => {
    expect(src).toContain("2D TOP-DOWN");
    expect(src).toContain("VORONOI");
    expect(src).not.toContain("view3DBroadcast");
    expect(src).not.toContain("<MatchPitchLiveScene");
  });

  test("tactical HUD consumes authoritative tactics without mutable owner controls or risk-derived width", () => {
    expect(src).toContain("mapAuthoritativeTactics(appliedTactics)");
    expect(src).toContain("authoritativeTactics?.homeFormation");
    expect(src).not.toContain("homeWidth");
    expect(src).not.toContain("setPress(");
  });
});
