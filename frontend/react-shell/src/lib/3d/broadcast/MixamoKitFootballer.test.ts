jest.mock("three/examples/jsm/utils/SkeletonUtils.js", () => ({
  clone: (source: unknown) => source,
}));

import * as THREE from "three";
import { everyFootballStateHasMixamoClip, gaitForGroundSpeed, MIXAMO_CLIP_BY_STATE, retargetMixamoClip } from "./MixamoKitFootballer";
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
});
