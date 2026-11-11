import * as THREE from "three";
import { createGiftDirector, frameGiftShot } from "./giftScenes";
import { detectGiftQuality } from "./giftQuality";

describe("gifting 2.0 scenes", () => {
  const quality = detectGiftQuality(1440, 8);

  function stage(shot: string, giftCode: string, rarity = "common") {
    return createGiftDirector({
      shot,
      giftCode,
      rarity,
      quality,
      canStream: false,
      resolveUrl: (path) => path,
      isCancelled: () => false,
      onReady: () => undefined,
    });
  }

  test("paris is a lattice tower and the eight shots do not share one camera", () => {
    const paris = stage("city", "paris_skyline");
    expect(paris.root.getObjectByName("eiffel-lattice")).toBeTruthy();
    paris.dispose();

    const parisStart = frameGiftShot("city", 0);
    const parisEnd = frameGiftShot("city", 1);
    expect(parisEnd.position[2]).toBeGreaterThan(parisStart.position[2]);

    const bicycle = frameGiftShot("bicycle", 0.4);
    const winner = frameGiftShot("last_minute", 0.4);
    expect(bicycle.position[0]).not.toBeCloseTo(winner.position[0], 0);
    expect(frameGiftShot("stadium", 0, [0, 0, 0], "golden_stadium").position[1]).toBeGreaterThan(
      frameGiftShot("stadium", 0, [0, 0, 0], "maracana_stadium").position[1]
    );
  });

  test("bicycle and last-minute winner are different stories", () => {
    const kick = stage("bicycle", "bicycle_kick");
    const winner = stage("last_minute", "last_minute_winner");
    expect(kick.root.getObjectByName("bicycle-pitch")).toBeTruthy();
    expect(kick.root.getObjectByName("winner-clock")).toBeFalsy();
    expect(winner.root.getObjectByName("winner-clock")).toBeTruthy();
    expect(winner.root.getObjectByName("match-goal")).toBeTruthy();
    kick.dispose();
    winner.dispose();
  });

  test("goal scenes orient the net across the mouth and add a visible crowd rig", () => {
    const scene = stage("last_minute", "last_minute_winner");
    const goal = scene.root.getObjectByName("match-goal");
    const net = goal?.getObjectByName("goal-net") as import("three").Mesh | undefined;
    expect(net).toBeTruthy();
    expect(net?.rotation.y).toBeCloseTo(Math.PI / 2);
    expect(scene.root.getObjectByName("stadium-crowd-heads")).toBeTruthy();
    const arms = scene.root.getObjectByName("stadium-crowd-arms") as THREE.InstancedMesh;
    expect(arms).toBeTruthy();

    const beforeNet = new Float32Array((net!.geometry.getAttribute("position") as THREE.BufferAttribute).array as Float32Array);
    const beforeArms = new Float32Array(arms.instanceMatrix.array as Float32Array);
    scene.update(0.84, 1 / 60, new THREE.PerspectiveCamera(38, 1, 0.1, 400));
    const afterNet = net!.geometry.getAttribute("position") as THREE.BufferAttribute;
    expect(Array.from(afterNet.array as Float32Array).some((value, index) => value !== beforeNet[index])).toBe(true);
    expect(Array.from(arms.instanceMatrix.array as Float32Array).some((value, index) => value !== beforeArms[index])).toBe(true);
    scene.dispose();
  });

  test("rarity controls add distinct cinematic staging without affecting common gifts", () => {
    const common = stage("stadium", "maracana_stadium", "common");
    const mythic = stage("stadium", "golden_stadium", "mythic");
    expect(common.root.getObjectByName("gift-rarity-mythic")).toBeFalsy();
    expect(mythic.root.getObjectByName("gift-rarity-mythic")).toBeTruthy();
    expect(mythic.root.getObjectByName("gift-rarity-vertical-gate")).toBeTruthy();
    expect(mythic.root.getObjectByName("gift-rarity-gem-8")).toBeTruthy();
    mythic.update(0.5, 1 / 60, new THREE.PerspectiveCamera(38, 1, 0.1, 400));
    common.dispose();
    mythic.dispose();
  });

  test("ballon d'or is a trophy stage with a ball, and the jet has a runway", () => {
    const trophy = stage("trophy", "ballon_dor");
    const jet = stage("jet", "private_jet");
    const yacht = stage("yacht", "superyacht");
    expect(trophy.root.getObjectByName("ballon-dor-ball")).toBeTruthy();
    expect(trophy.root.getObjectByName("ballon-dor-stage")).toBeTruthy();
    expect(trophy.root.getObjectByName("ballon-dor-support")).toBeTruthy();
    expect(trophy.root.getObjectByName("ballon-dor-orbit")).toBeTruthy();
    expect(jet.root.getObjectByName("runway")).toBeTruthy();
    expect(yacht.root.getObjectByName("ocean")).toBeTruthy();
    trophy.dispose();
    jet.dispose();
    yacht.dispose();
  });
});
