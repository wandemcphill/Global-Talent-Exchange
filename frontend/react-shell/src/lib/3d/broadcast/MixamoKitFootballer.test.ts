jest.mock("three/examples/jsm/utils/SkeletonUtils.js", () => ({
  clone: (source: unknown) => source,
}));

import { everyFootballStateHasMixamoClip, gaitForGroundSpeed, MIXAMO_CLIP_BY_STATE } from "./MixamoKitFootballer";
import { ALL_FOOTBALL_ANIMATION_STATES } from "./FootballAnimationStateMachine";

describe("MixamoKitFootballer clip map", () => {
  test("maps all 41 football states onto a baked Mixamo clip", () => {
    expect(ALL_FOOTBALL_ANIMATION_STATES).toHaveLength(41);
    expect(everyFootballStateHasMixamoClip()).toBe(true);
    expect(new Set(Object.keys(MIXAMO_CLIP_BY_STATE)).size).toBe(41);
  });

  test("picks a gait from how fast the body is actually travelling", () => {
    expect(gaitForGroundSpeed(0.1, false)).toBe("idle");
    expect(gaitForGroundSpeed(1.1, false)).toBe("walk");
    expect(gaitForGroundSpeed(2.4, false)).toBe("jog");
    expect(gaitForGroundSpeed(2.4, true)).toBe("dribble");
    expect(gaitForGroundSpeed(4.4, false)).toBe("run");
    expect(gaitForGroundSpeed(7, false)).toBe("sprint");
  });
});
