import { resolveGiftModelPath } from "./CinematicGiftingEngine";

describe("resolveGiftModelPath", () => {
  test("every gift family resolves to a real model", () => {
    const cases: Array<[string, string]> = [
      ["private_jet_flyby", "/assets/showroom/sovereign_900x_jet.glb"],
      ["superyacht", "/assets/showroom/superyacht.glb"],
      ["golden_stadium", "/assets/showroom/golden_stadium.glb"],
      ["sovereign_crown", "/assets/showroom/chronos_tourbillon_watch.glb"],
      ["dubai_skyline", "/assets/showroom/royal_penthouse_box.glb"],
      ["club_coach", "/assets/showroom/vanguard_xii_coach.glb"],
      ["gulfstream_g700", "/assets/showroom/gulfstream_g700_exec_jet.glb"],
      ["veloce_gt9_hypercar", "/assets/showroom/veloce_gt9_hypercar.glb"],
      ["executive_suv", "/assets/showroom/executive_suv.glb"],
      ["apex_performance_campus", "/assets/showroom/apex_performance_campus.glb"],
      ["maracana_stadium", "/assets/showroom/arena_imperiale_stadium.glb"],
      ["golden_boot", "/assets/showroom/trophy_plinth.glb"],
      ["red_card", "/models/match/football-stadium.glb"],
      ["stadium_roar", "/models/match/football-stadium.glb"],
      ["captain_armband", "/models/match/football-stadium.glb"],
    ];
    cases.forEach(([code, path]) => {
      expect(resolveGiftModelPath(code)).toBe(path);
    });
  });
});
