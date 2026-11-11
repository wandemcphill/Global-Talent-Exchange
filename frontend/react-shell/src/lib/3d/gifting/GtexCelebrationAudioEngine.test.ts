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
  });
});
