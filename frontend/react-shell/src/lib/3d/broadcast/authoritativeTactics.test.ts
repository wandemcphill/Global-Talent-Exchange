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

describe("MatchCenter 3D/2D toolbar contract", () => {
  const src = fs.readFileSync(path.resolve(__dirname, "../../../pages/MatchCenter.tsx"), "utf-8");

  test("2D-only camera and shader toolbars are guarded by !view3DBroadcast", () => {
    const guards = src.match(/\{!view3DBroadcast && \(/g) || [];
    expect(guards.length).toBeGreaterThanOrEqual(2);
    const camIdx = src.indexOf("2D TOP-DOWN");
    expect(src.lastIndexOf("{!view3DBroadcast && (", camIdx)).toBeGreaterThan(src.lastIndexOf("Camera Perspective Switcher", camIdx));
    const vorIdx = src.indexOf("VORONOI");
    expect(src.lastIndexOf("{!view3DBroadcast && (", vorIdx)).toBeGreaterThan(src.lastIndexOf("Spatial Shaders + Event-Driven", vorIdx));
  });

  test("scene receives authoritative tactics, not slider drafts or risk-derived width", () => {
    expect(src).toContain("tacticalConfig={authoritativeTactics}");
    expect(src).not.toContain("homeWidth");
  });
});
