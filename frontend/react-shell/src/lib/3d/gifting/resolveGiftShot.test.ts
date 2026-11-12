import { resolveGiftShot } from "./CinematicGiftingEngine";
import { giftConceptFilm } from "./giftConceptFilms";

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
    expect(resolveGiftShot(undefined, "king_of_tactics")).toBe("tactics");
    expect(resolveGiftShot(undefined, "sovereign_crown")).toBe("crown");
    expect(resolveGiftShot("golden_boot_spark", "golden_boot_king")).toBe("boot");
    expect(resolveGiftShot("last_minute_winner", "last_minute_winner")).toBe("last_minute");
    expect(resolveGiftShot("goal_celebration", "goal_celebration")).toBe("goal");
    expect(resolveGiftShot("luxury_team_coach", "vanguard_xii_coach")).toBe("coach");
    expect(resolveGiftShot("veloce_gt9_hypercar", "veloce_gt9_hypercar")).toBe("vehicle");
    expect(resolveGiftShot("chronos_tourbillon_watch", "chronos_tourbillon_watch")).toBe("crown");
    expect(resolveGiftShot("apex_performance_campus", "apex_performance_campus")).toBe("facility");
  });

  test("plays the generated arrival film for each match gift shot", () => {
    expect(giftConceptFilm("stadium").src).toBe("/assets/gifting/films/gtex-maracana-gift.mp4");
    expect(giftConceptFilm("atmosphere").src).toBe("/assets/gifting/films/gtex-gift-atmosphere.mp4");
    expect(giftConceptFilm("card").src).toBe("/assets/gifting/films/gtex-gift-card.mp4");
    expect(giftConceptFilm("tactics").src).toBe("/assets/gifting/films/gtex-gift-tactics.mp4");
    expect(giftConceptFilm("crown").src).toBe("/assets/gifting/films/gtex-gift-crown.mp4");
    expect(giftConceptFilm("trophy").src).toBe("/assets/gifting/films/gtex-gift-trophy.mp4");
    expect(giftConceptFilm("boot").src).toBe("/assets/gifting/films/gtex-gift-boot.mp4");
    expect(giftConceptFilm("glove").src).toBe("/assets/gifting/films/gtex-gift-glove.mp4");
    expect(giftConceptFilm("city").src).toBe("/assets/gifting/films/gtex-gift-city.mp4");
    expect(giftConceptFilm("goal").src).toBe("/assets/gifting/films/gtex-gift-goal.mp4");
    expect(giftConceptFilm("last_minute").src).toBe("/assets/gifting/films/gtex-gift-last-minute.mp4");
    expect(giftConceptFilm("bicycle").src).toBe("/assets/gifting/films/gtex-gift-bicycle.mp4");
    expect(giftConceptFilm("golden_goal").src).toBe("/assets/gifting/films/gtex-gift-golden-goal.mp4");
    expect(giftConceptFilm("hat_trick").src).toBe("/assets/gifting/films/gtex-gift-hat-trick.mp4");
    expect(giftConceptFilm("save").src).toBe("/assets/gifting/films/gtex-gift-save.mp4");
  });
});
