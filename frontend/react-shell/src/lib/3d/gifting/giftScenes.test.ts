import * as THREE from "three";
import { createGiftDirector, frameGiftShot } from "./giftScenes";
import { detectGiftQuality } from "./giftQuality";

describe("asset-led cinematic gifting scenes", () => {
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

  function meshes(root: THREE.Object3D): THREE.Mesh[] {
    const found: THREE.Mesh[] = [];
    root.traverse((child) => {
      const mesh = child as THREE.Mesh;
      if (mesh.isMesh) found.push(mesh);
    });
    return found;
  }

  test("unsupported city landmarks use a clean cinematic atmosphere, not a penthouse substitute", () => {
    const city = stage("city", "paris_skyline");
    expect(city.root.getObjectByName("gift-city-hero")).toBeFalsy();
    expect(city.root.getObjectByName("gift-penthouse-hero")).toBeFalsy();
    expect(city.root.getObjectByName("eiffel-lattice")).toBeFalsy();
    expect(city.root.getObjectByName("gift-cinematic-particles")).toBeTruthy();
    expect(meshes(city.root)).toHaveLength(0);

    const start = frameGiftShot("city", 0);
    const finish = frameGiftShot("city", 1);
    expect(finish.position[2]).toBeLessThan(start.position[2]);

    const bicycle = frameGiftShot("bicycle", 0.4);
    const winner = frameGiftShot("last_minute", 0.4);
    expect(bicycle.position[0]).not.toBeCloseTo(winner.position[0], 0);
    city.dispose();
  });

  test("a penthouse gift uses the matching existing architecture asset", () => {
    const penthouse = stage("city", "royal_penthouse");
    expect(penthouse.root.getObjectByName("gift-penthouse-hero")?.userData.assetPath)
      .toBe("/assets/showroom/royal_penthouse_box.glb");
    penthouse.dispose();
  });

  test("stadium scenes resolve to licensed authored GLB models", () => {
    const maracana = stage("stadium", "maracana_stadium");
    const golden = stage("stadium", "golden_stadium");
    expect(maracana.root.getObjectByName("gift-stadium-hero")?.userData.assetPath)
      .toBe("/assets/showroom/arena_imperiale_stadium.glb");
    expect(golden.root.getObjectByName("gift-stadium-hero")?.userData.assetPath)
      .toBe("/assets/showroom/golden_stadium.glb");
    expect(meshes(maracana.root)).toHaveLength(0);
    expect(meshes(golden.root)).toHaveLength(0);
    maracana.dispose();
    golden.dispose();
  });

  test("jet and yacht scenes contain their authored hero assets, not primitive props", () => {
    const jet = stage("jet", "private_jet");
    const gulfstream = stage("jet", "gulfstream_g700_exec_jet");
    const yacht = stage("yacht", "superyacht");
    expect(jet.root.getObjectByName("gift-aircraft")?.userData.assetPath)
      .toBe("/assets/showroom/sovereign_900x_jet.glb");
    expect(jet.root.getObjectByName("runway")).toBeFalsy();
    expect(jet.root.getObjectByName("jet-primitive")).toBeFalsy();
    expect(meshes(jet.root)).toHaveLength(0);
    expect(gulfstream.root.getObjectByName("gift-aircraft")?.userData.assetPath)
      .toBe("/assets/showroom/gulfstream_g700_exec_jet.glb");
    expect(meshes(gulfstream.root)).toHaveLength(0);

    expect(yacht.root.getObjectByName("gift-yacht")?.userData.assetPath)
      .toBe("/assets/showroom/superyacht.glb");
    expect(yacht.root.getObjectByName("gift-ocean-surface")).toBeTruthy();
    expect(meshes(yacht.root)).toHaveLength(1);
    jet.dispose();
    gulfstream.dispose();
    yacht.dispose();
  });

  test("coach, vehicle and facility gifts use their exact showroom GLBs", () => {
    const coach = stage("coach", "vanguard_xii_coach");
    const vehicle = stage("vehicle", "veloce_gt9_hypercar");
    const facility = stage("facility", "apex_performance_campus");
    expect(coach.root.getObjectByName("gift-coach")?.userData.assetPath)
      .toBe("/assets/showroom/vanguard_xii_coach.glb");
    expect(vehicle.root.getObjectByName("gift-vehicle")?.userData.assetPath)
      .toBe("/assets/showroom/veloce_gt9_hypercar.glb");
    expect(facility.root.getObjectByName("gift-facility")?.userData.assetPath)
      .toBe("/assets/showroom/apex_performance_campus.glb");
    expect(meshes(coach.root)).toHaveLength(0);
    expect(meshes(vehicle.root)).toHaveLength(0);
    expect(meshes(facility.root)).toHaveLength(0);
    coach.update(0.6, 1 / 60, new THREE.PerspectiveCamera(38, 1, 0.1, 400));
    vehicle.update(0.6, 1 / 60, new THREE.PerspectiveCamera(38, 1, 0.1, 400));
    facility.update(0.6, 1 / 60, new THREE.PerspectiveCamera(38, 1, 0.1, 400));
    coach.dispose();
    vehicle.dispose();
    facility.dispose();
  });

  test("bicycle and last-minute winner use the real animated footballer pipeline", () => {
    const kick = stage("bicycle", "bicycle_kick");
    const winner = stage("last_minute", "last_minute_winner");
    expect(kick.root.getObjectByName("gift-match-stadium")?.userData.assetPath)
      .toBe("/models/match/football-stadium.glb");
    expect(kick.root.getObjectByName("match-goal")?.userData.assetPath)
      .toBe("/models/match/goal_frame.glb");
    expect(kick.root.getObjectByName("gift-ball")?.userData.assetPath)
      .toBe("/models/match/football_pbr.glb");
    expect(kick.root.getObjectByName("gift-player")).toBeTruthy();
    expect(winner.root.getObjectByName("gift-player")).toBeTruthy();
    expect(winner.root.getObjectByName("gift-celebrant")).toBeTruthy();

    // Streaming is deliberately disabled in this unit test, so no fake mesh
    // fallback is permitted to appear in place of the licensed scene assets.
    expect(meshes(kick.root)).toHaveLength(0);
    expect(meshes(winner.root)).toHaveLength(0);
    kick.update(0.84, 1 / 60, new THREE.PerspectiveCamera(38, 1, 0.1, 400));
    winner.update(0.84, 1 / 60, new THREE.PerspectiveCamera(38, 1, 0.1, 400));
    kick.dispose();
    winner.dispose();
  });

  test("football gift impact beats add a small camera punch on contact", () => {
    const kick = stage("bicycle", "bicycle_kick");
    const winner = stage("last_minute", "last_minute_winner");
    const kickCamera = new THREE.PerspectiveCamera(38, 1, 0.1, 400);
    const winnerCamera = new THREE.PerspectiveCamera(38, 1, 0.1, 400);
    kick.update(0.8, 1 / 60, kickCamera);
    winner.update(0.74, 1 / 60, winnerCamera);
    expect(kickCamera.fov).toBeLessThan(frameGiftShot("bicycle", 0.8).fov);
    expect(winnerCamera.fov).toBeLessThan(frameGiftShot("last_minute", 0.74).fov);
    kick.dispose();
    winner.dispose();
  });

  test("rarity is expressed through lighting rather than floating geometric ornaments", () => {
    const common = stage("stadium", "maracana_stadium", "common");
    const mythic = stage("stadium", "golden_stadium", "mythic");
    const commonLight = common.root.getObjectByName("gift-rarity-light") as THREE.PointLight;
    const mythicLight = mythic.root.getObjectByName("gift-rarity-light") as THREE.PointLight;
    expect(commonLight).toBeTruthy();
    expect(mythicLight).toBeTruthy();
    expect(mythicLight.color.getHex()).not.toBe(commonLight.color.getHex());
    expect(mythic.root.getObjectByName("gift-rarity-ring-1")).toBeFalsy();
    expect(mythic.root.getObjectByName("gift-rarity-gem-1")).toBeFalsy();

    mythic.update(0.5, 1 / 60, new THREE.PerspectiveCamera(38, 1, 0.1, 400));
    common.dispose();
    mythic.dispose();
  });

  test("missing boot, glove, crown, card and tactics assets never borrow another gift model", () => {
    const boot = stage("boot", "golden_boot_king");
    const glove = stage("glove", "safe_hands_award");
    const crown = stage("crown", "king_of_tactics");
    const card = stage("card", "player_of_the_match");
    const tactics = stage("tactics", "tactical_masterclass");
    [boot, glove, crown, card, tactics].forEach((scene) => {
      expect(scene.root.getObjectByName("gift-award-stage")).toBeFalsy();
      expect(scene.root.getObjectByName("ballon-dor-stage")).toBeFalsy();
      expect(meshes(scene.root)).toHaveLength(0);
      expect(scene.root.getObjectByName("gift-cinematic-particles")).toBeTruthy();
      scene.update(0.55, 1 / 60, new THREE.PerspectiveCamera(38, 1, 0.1, 400));
      scene.dispose();
    });
  });

  test("an actual Chronos watch gift uses the authored watch model, not a crown substitute", () => {
    const watch = stage("crown", "chronos_tourbillon_watch");
    const hero = watch.root.getObjectByName("gift-watch-stage");
    expect(hero?.userData.assetPath).toBe("/assets/showroom/chronos_tourbillon_watch.glb");
    expect(watch.root.getObjectByName("gift-award-stage")).toBeFalsy();
    expect(meshes(watch.root)).toHaveLength(0);
    watch.dispose();
  });

  test("awards use the real trophy plinth and gold match-ball assets", () => {
    const trophy = stage("trophy", "ballon_dor");
    const award = trophy.root.getObjectByName("ballon-dor-stage");
    expect(award?.userData.assetPath).toBe("/assets/showroom/trophy_plinth.glb");
    expect(trophy.root.getObjectByName("ballon-dor-ball")).toBeTruthy();
    expect(trophy.root.getObjectByName("ballon-dor-support")).toBeFalsy();
    expect(trophy.root.getObjectByName("ballon-dor-orbit")).toBeFalsy();
    expect(meshes(trophy.root)).toHaveLength(0);
    trophy.dispose();
  });
});
