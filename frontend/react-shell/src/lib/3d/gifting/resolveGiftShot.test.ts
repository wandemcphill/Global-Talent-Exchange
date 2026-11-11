import { resolveGiftShot } from "./CinematicGiftingEngine";

describe("resolveGiftShot", () => {
  test("keeps city, jet, stadium, boot, and bicycle on their own shots", () => {
    expect(resolveGiftShot("city_paris", "paris_skyline")).toBe("city");
    expect(resolveGiftShot(undefined, "paris_skyline")).toBe("city");
    expect(resolveGiftShot("luxury_private_jet", "private_jet")).toBe("jet");
    expect(resolveGiftShot(undefined, "private_jet")).toBe("jet");
    expect(resolveGiftShot("gulfstream_g700", "gulfstream_g700_exec_jet")).toBe("jet");
    expect(resolveGiftShot("bicycle_kick", "bicycle_kick")).toBe("bicycle");
    expect(resolveGiftShot("stadium_maracana", "maracana_stadium")).toBe("stadium");
    expect(resolveGiftShot(undefined, "maracana_stadium")).toBe("stadium");
    expect(resolveGiftShot("golden_boot_spark", "golden_boot_king")).toBe("boot");
    expect(resolveGiftShot("last_minute_winner", "last_minute_winner")).toBe("last_minute");
    expect(resolveGiftShot("goal_celebration", "goal_celebration")).toBe("goal");
    expect(resolveGiftShot("luxury_team_coach", "vanguard_xii_coach")).toBe("coach");
    expect(resolveGiftShot("veloce_gt9_hypercar", "veloce_gt9_hypercar")).toBe("vehicle");
    expect(resolveGiftShot("chronos_tourbillon_watch", "chronos_tourbillon_watch")).toBe("crown");
    expect(resolveGiftShot("apex_performance_campus", "apex_performance_campus")).toBe("facility");
  });
});