import { everyFootballStateHasMixamoClip, MIXAMO_CLIP_BY_STATE } from "./MixamoKitFootballer";
import { ALL_FOOTBALL_ANIMATION_STATES } from "./FootballAnimationStateMachine";

describe("MixamoKitFootballer clip map", () => {
  test("maps all 41 football states onto a baked Mixamo clip", () => {
    expect(ALL_FOOTBALL_ANIMATION_STATES).toHaveLength(41);
    expect(everyFootballStateHasMixamoClip()).toBe(true);
    expect(new Set(Object.keys(MIXAMO_CLIP_BY_STATE)).size).toBe(41);
  });
});
