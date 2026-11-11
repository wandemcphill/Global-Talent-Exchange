import { resolveGiftShot, resolveGiftVideoPath } from "./CinematicGiftingEngine";

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

  test("maps supplied cinematic clips to matching gift families and keeps unmatched gifts on WebGL", () => {
    const cases: Array<[string, string, string]> = [
      ["common_whistle", "atmosphere", "/assets/gifting/gtex-gift-atmosphere.mp4"],
      ["bicycle_kick", "bicycle", "/assets/gifting/gtex-gift-bicycle.mp4"],
      ["golden_boot_king", "boot", "/assets/gifting/gtex-gift-boot.mp4"],
      ["apex_performance_campus", "facility", "/assets/gifting/gtex-gift-campus.mp4"],
      ["legend_card_reveal", "card", "/assets/gifting/gtex-gift-card.mp4"],
      ["city_lagos", "city", "/assets/gifting/gtex-gift-city.mp4"],
      ["luxury_team_coach", "coach", "/assets/gifting/gtex-gift-coach.mp4"],
      ["sovereign_crown", "crown", "/assets/gifting/gtex-gift-crown.mp4"],
      ["safe_hands_award", "glove", "/assets/gifting/gtex-gift-glove.mp4"],
      ["goal_celebration", "goal", "/assets/gifting/gtex-gift-goal.mp4"],
      ["golden_goal", "golden_goal", "/assets/gifting/gtex-gift-golden-goal.mp4"],
      ["perfect_hat_trick", "hat_trick", "/assets/gifting/gtex-gift-hat-trick.mp4"],
      ["veloce_gt9_hypercar", "vehicle", "/assets/gifting/gtex-gift-hypercar.mp4"],
      ["private_jet", "jet", "/assets/gifting/gtex-gift-jet.mp4"],
      ["last_minute_winner", "last_minute", "/assets/gifting/gtex-gift-last-minute.mp4"],
      ["world_class_save", "save", "/assets/gifting/gtex-gift-save.mp4"],
      ["king_of_tactics", "tactics", "/assets/gifting/gtex-gift-tactics.mp4"],
      ["ballon_dor", "trophy", "/assets/gifting/gtex-gift-trophy.mp4"],
      ["superyacht", "yacht", "/assets/gifting/gtex-gift-yacht.mp4"],
      ["maracana_stadium", "stadium", "/assets/gifting/gtex-maracana-gift.mp4"],
    ];

    cases.forEach(([giftCode, shot, path]) => {
      expect(resolveGiftVideoPath(giftCode, shot as any)).toBe(path);
    });
    expect(resolveGiftVideoPath("chronos_tourbillon_watch", "crown")).toBe("");
    expect(resolveGiftVideoPath("wembley_stadium", "stadium")).toBe("");
  });
});