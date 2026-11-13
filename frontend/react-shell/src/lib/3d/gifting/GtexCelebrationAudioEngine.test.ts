import { resolveCelebrationCue } from "./GtexCelebrationAudioEngine";

describe("resolveCelebrationCue", () => {
  test("card reveal does not become a referee whistle", () => {
    expect(resolveCelebrationCue("card_reveal_riser", "legend_card_reveal")).toBe("card_reveal");
    expect(resolveCelebrationCue(undefined, "legend_card_reveal")).not.toBe("whistle");
  });

  test("last-minute winner follows the roar key, not the word winner", () => {
    expect(resolveCelebrationCue("net_ripple_roar", "last_minute_winner")).toBe("goal_roar");
  });

  test("catalog keys keep their own cues", () => {
    expect(resolveCelebrationCue("maracana_samba_cheer")).toBe("drums");
    expect(resolveCelebrationCue("yacht_harbor_chime", "superyacht")).toBe("harbor_chime");
    expect(resolveCelebrationCue("jet_turbine_flyby")).toBe("jet");
    expect(resolveCelebrationCue("hat_trick_fireworks")).toBe("fireworks");
    expect(resolveCelebrationCue("goal_roar", "goal_celebration")).toBe("goal_roar");
    expect(resolveCelebrationCue("eagle_scream", "super_eagle")).toBe("eagle");
    expect(resolveCelebrationCue("jaguar_roar", "black_jaguar")).toBe("jaguar");
    expect(resolveCelebrationCue("white_tiger_roar", "white_tiger")).toBe("white_tiger");
    expect(resolveCelebrationCue("polar_bear_roar", "polar_bear")).toBe("polar_bear");
  });
});
