jest.mock("three/examples/jsm/utils/SkeletonUtils.js", () => ({
  clone: (source: unknown) => source,
}));

import * as THREE from "three";
import {
  clipTimeScale,
  computeSprintPitchRad,
  computeTurnBankingRad,
  everyFootballStateHasMixamoClip,
  gaitForGroundSpeed,
  MIXAMO_CLIP_BY_STATE,
  retargetMixamoClip,
} from "./MixamoKitFootballer";
import { ALL_FOOTBALL_ANIMATION_STATES } from "./FootballAnimationStateMachine";

describe("MixamoKitFootballer clip map", () => {
  test("maps all 42 football states onto a baked Mixamo clip", () => {
    expect(ALL_FOOTBALL_ANIMATION_STATES).toHaveLength(42);
    expect(everyFootballStateHasMixamoClip()).toBe(true);
    expect(new Set(Object.keys(MIXAMO_CLIP_BY_STATE)).size).toBe(42);
  });

  test("picks a gait from how fast the body is actually travelling", () => {
    expect(gaitForGroundSpeed(0.1, false)).toBe("idle");
    expect(gaitForGroundSpeed(1.1, false)).toBe("walk");
    expect(gaitForGroundSpeed(2.4, false)).toBe("jog");
    expect(gaitForGroundSpeed(2.4, true)).toBe("dribble");
    expect(gaitForGroundSpeed(4.4, true)).toBe("dribble_run");
    expect(gaitForGroundSpeed(4.4, false)).toBe("run");
    expect(gaitForGroundSpeed(7, true)).toBe("dribble_run");
    expect(gaitForGroundSpeed(7, false)).toBe("sprint");
  });

  test("plays one clip cycle per stride of travel", () => {
    expect(clipTimeScale(1.35, 1.35, 1)).toBeCloseTo(1);
    expect(clipTimeScale(0, 1.35, 1)).toBeCloseTo(0.4);
    expect(clipTimeScale(12, 1.35, 1)).toBeCloseTo(1.85);
  });

  test("keeps the moving strike, standing tackle, and celebration distinct from the set-piece clips", () => {
    expect(MIXAMO_CLIP_BY_STATE.dribble).not.toBe(MIXAMO_CLIP_BY_STATE.dribble_run);
    expect(MIXAMO_CLIP_BY_STATE.shoot).toBe("Gtex_Strike");
    expect(MIXAMO_CLIP_BY_STATE.shoot).not.toBe("Male_Soccer_Penalty_Kick");
    expect(MIXAMO_CLIP_BY_STATE.standing_tackle).toBe("Gtex_Standing_Tackle");
    expect(MIXAMO_CLIP_BY_STATE.standing_tackle).not.toBe(MIXAMO_CLIP_BY_STATE.sliding_tackle);
    expect(MIXAMO_CLIP_BY_STATE.goal_celebration).not.toBe("Soccer_360_Spin");
    expect(MIXAMO_CLIP_BY_STATE.disappointment).not.toBe("Goalkeeper_Jump_And_Miss");
  });

  test("retargets Mixamo tracks onto the kit bone names and drops hip root motion", () => {
    const times = [0, 1];
    const quat = [0, 0, 0, 1, 0, 0, 0, 1];
    const clip = new THREE.AnimationClip("run", 1, [
      new THREE.QuaternionKeyframeTrack("mixamorigHips.quaternion", times, quat),
      new THREE.VectorKeyframeTrack("mixamorigHips.position", times, [0, 1, 0, 0, 1, 0]),
      new THREE.QuaternionKeyframeTrack("mixamorigSpine.quaternion", times, quat),
      new THREE.QuaternionKeyframeTrack("mixamorig:LeftArm.quaternion", times, quat),
    ]);
    const next = retargetMixamoClip(clip, ["mixamorig:Hips", "mixamorig:Spine", "mixamorigLeftArm"]);
    expect(next.tracks.map((track) => track.name)).toEqual([
      "mixamorig:Spine.quaternion",
      "mixamorigLeftArm.quaternion",
    ]);
  });

  test("scales athletic turn banking and forward sprint pitch with ground speed and clamps bounds", () => {
    const slowBank = Math.abs(computeTurnBankingRad(0.5, 1.0, 1.0));
    const fastBank = Math.abs(computeTurnBankingRad(0.5, 1.0, 6.0));
    expect(fastBank).toBeGreaterThan(slowBank);
    expect(Math.abs(computeTurnBankingRad(3.0, 5.0, 9.0))).toBeLessThanOrEqual(0.22);

    expect(computeSprintPitchRad(1.5)).toBe(0);
    expect(computeSprintPitchRad(6.5)).toBeGreaterThan(0.05);
    expect(computeSprintPitchRad(12.0)).toBeLessThanOrEqual(0.09);
  });
});
