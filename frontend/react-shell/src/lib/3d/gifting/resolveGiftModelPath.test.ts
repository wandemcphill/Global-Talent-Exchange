import { resolveGiftModelPath } from "./CinematicGiftingEngine";

describe("resolveGiftModelPath", () => {
  test("authored gift hero families resolve to their matching GLB", () => {
    const cases: Array<[string, string]> = [
      ["private_jet_flyby", "/assets/showroom/sovereign_900x_jet.glb"],
      ["gulfstream_g700_exec_jet", "/assets/showroom/gulfstream_g700_exec_jet.glb"],
      ["superyacht", "/assets/showroom/superyacht.glb"],
      ["golden_stadium", "/assets/showroom/golden_stadium.glb"],
      ["chronos_tourbillon_watch", "/assets/showroom/chronos_tourbillon_watch.glb"],
      ["dubai_skyline", "/assets/showroom/royal_penthouse_box.glb"],
      ["club_coach", "/assets/showroom/vanguard_xii_coach.glb"],
      ["gulfstream_g700", "/assets/showroom/gulfstream_g700_exec_jet.glb"],
      ["veloce_gt9_hypercar", "/assets/showroom/veloce_gt9_hypercar.glb"],
      ["executive_suv", "/assets/showroom/executive_suv.glb"],
      ["apex_performance_campus", "/assets/showroom/apex_performance_campus.glb"],
      ["maracana_stadium", "/assets/showroom/arena_imperiale_stadium.glb"],
      ["ballon_dor", "/assets/showroom/trophy_plinth.glb"],
    ];
    cases.forEach(([code, path]) => {
      expect(resolveGiftModelPath(code)).toBe(path);
    });
  });

  test("unsupported hero gifts do not borrow unrelated trophy, watch or stadium models", () => {
    const codes = [
      "sovereign_crown",
      "golden_boot",
      "golden_boot_king",
      "safe_hands_award",
      "red_card",
      "stadium_roar",
      "captain_armband",
      "king_of_tactics",
      "player_of_the_match",
    ];
    codes.forEach((code) => {
      expect(resolveGiftModelPath(code)).toBe("");
    });
  });
});
