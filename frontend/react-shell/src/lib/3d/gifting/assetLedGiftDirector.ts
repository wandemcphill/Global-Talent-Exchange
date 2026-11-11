import * as THREE from "three";
import { clone as cloneSkinned } from "three/examples/jsm/utils/SkeletonUtils.js";
import { AssetStreamingCache } from "../broadcast/AssetStreamingCache";
import type { GiftQuality } from "./giftQuality";

const ASSETS = {
  city: "/assets/showroom/royal_penthouse_box.glb",
  stadium: "/assets/showroom/arena_imperiale_stadium.glb",
  goldenStadium: "/assets/showroom/golden_stadium.glb",
  jet: "/assets/showroom/sovereign_900x_jet.glb",
  yacht: "/assets/showroom/superyacht.glb",
  trophy: "/assets/showroom/trophy_plinth.glb",
  crown: "/assets/showroom/chronos_tourbillon_watch.glb",
  gulfstream: "/assets/showroom/gulfstream_g700_exec_jet.glb",
  coach: "/assets/showroom/vanguard_xii_coach.glb",
  suv: "/assets/showroom/executive_suv.glb",
  hypercar: "/assets/showroom/veloce_gt9_hypercar.glb",
  facility: "/assets/showroom/apex_performance_campus.glb",
  matchStadium: "/models/match/football-stadium.glb",
  goal: "/models/match/goal_frame.glb",
  ball: "/models/match/football_pbr.glb",
  kit: "/models/footballer/gtex_home_kit_mixamo.glb",
  clips: "/models/footballer/gtex_mixamo_clips.glb",
};

const CLIPS = {
  bicycle: "Soccer_Scissor_Kick_To_Goal",
  run: "Running_Forwards",
  penalty: "Male_Soccer_Penalty_Kick",
  celebration: "Soccer_360_Spin",
};

export interface GiftFrame {
  position: [number, number, number];
  lookAt: [number, number, number];
  fov: number;
}

export interface GiftDirector {
  root: THREE.Group;
  background: THREE.Color;
  exposure: number;
  update: (progress: number, delta: number, camera: THREE.PerspectiveCamera) => void;
  dispose: () => void;
}

interface Options {
  shot: string;
  giftCode: string;
  rarity?: string;
  quality: GiftQuality;
  canStream: boolean;
  resolveUrl: (path: string) => string;
  isCancelled: () => boolean;
  onReady: () => void;
}

const RAILS: Record<string, { camera: number[][]; target: number[][]; fov: [number, number] }> = {
  city: { camera: [[22, 9, 30], [16, 8, 24], [10, 7, 17], [7, 6, 13]], target: [[0, 4, 0], [0, 5, 0], [0, 5, 0], [0, 5, 0]], fov: [42, 32] },
  stadium: { camera: [[18, 36, 62], [10, 26, 48], [4, 15, 34], [2, 12, 29]], target: [[0, 2, 0], [0, 3, 0], [0, 2, 0], [0, 2, 0]], fov: [50, 34] },
  jet: { camera: [[22, 8, 34], [14, 9, 27], [7, 8, 21], [5, 7, 18]], target: [[0, 1, 0], [4, 1, 0], [8, 2, 0], [10, 3, 0]], fov: [38, 31] },
  yacht: { camera: [[24, 13, 29], [17, 11, 24], [10, 9, 19], [8, 8, 16]], target: [[0, 1, 0], [0, 1, 0], [2, 1, 0], [2, 1, 0]], fov: [42, 32] },
  coach: { camera: [[16, 6, 24], [10, 6, 18], [6, 5, 14], [5, 4, 12]], target: [[0, 1.5, 0], [0, 1.5, 0], [0, 1.4, 0], [0, 1.4, 0]], fov: [40, 31] },
  vehicle: { camera: [[14, 5, 22], [9, 5, 16], [5, 4.2, 12], [4, 3.5, 10]], target: [[0, 1.1, 0], [0, 1.1, 0], [0, 1.1, 0], [0, 1.1, 0]], fov: [38, 29] },
  facility: { camera: [[22, 12, 28], [17, 10, 23], [11, 8, 18], [8, 7, 15]], target: [[0, 5, 0], [0, 5, 0], [0, 5, 0], [0, 5, 0]], fov: [42, 32] },
  trophy: { camera: [[8, 3.8, 11], [6, 3.2, 8], [4, 2.7, 6], [3.6, 2.4, 5.2]], target: [[0, 1.2, 0], [0, 1.2, 0], [0, 1.3, 0], [0, 1.3, 0]], fov: [34, 27] },
  bicycle: { camera: [[10, 5, 14], [6, 3.8, 11], [3, 2.4, 8], [5, 3.2, 10]], target: [[0, 1.2, 0], [2, 1.3, 0], [7, 1.3, 0], [9, 1.5, 0]], fov: [40, 34] },
  last_minute: { camera: [[12, 7, 18], [7, 4.5, 13], [2.8, 2.5, 8], [5, 3.6, 11]], target: [[0, 1.5, 0], [3, 1.2, 0], [10, 1.1, 0], [11, 1.5, 0]], fov: [44, 34] },
  default: { camera: [[8, 4, 13], [6, 3.6, 10], [4, 2.8, 8], [3.5, 2.5, 7]], target: [[0, 1.2, 0], [0, 1.2, 0], [0, 1.2, 0], [0, 1.2, 0]], fov: [38, 32] },
};

const clamp = (value: number) => Math.min(1, Math.max(0, value));
const smooth = (value: number) => {
  const t = clamp(value);
  return t * t * (3 - 2 * t);
};
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

function bezier(points: number[][], t: number): [number, number, number] {
  const u = 1 - t;
  const value = (axis: number) =>
    u * u * u * points[0][axis] +
    3 * u * u * t * points[1][axis] +
    3 * u * t * t * points[2][axis] +
    t * t * t * points[3][axis];
  return [value(0), value(1), value(2)];
}

export function frameGiftShot(shot: string, progress: number, hero: [number, number, number] = [0, 0, 0]): GiftFrame {
  const rail = RAILS[shot] || RAILS.default;
  const t = smooth(progress);
  const position = bezier(rail.camera, t);
  const lookAt = bezier(rail.target, t);
  if (shot === "jet" && hero.some((item) => item !== 0)) {
    position[0] += hero[0] * 0.12;
    position[1] += hero[1] * 0.12;
    lookAt[0] += hero[0] * 0.72;
    lookAt[1] += hero[1] * 0.5;
  }
  return { position, lookAt, fov: lerp(rail.fov[0], rail.fov[1], t) };
}

class SceneBin {
  readonly root = new THREE.Group();
  readonly resources: Array<{ dispose: () => void }> = [];
  readonly imported: THREE.Object3D[] = [];
  track<T extends { dispose: () => void }>(resource: T): T {
    this.resources.push(resource);
    return resource;
  }
  dispose(): void {
    this.imported.forEach((root) => root.traverse((child) => {
      const mesh = child as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.geometry?.dispose();
      const materials = Array.isArray(mesh.material) ? mesh.material : mesh.material ? [mesh.material] : [];
      materials.forEach((material) => material?.dispose());
    }));
    this.resources.forEach((resource) => resource.dispose());
  }
}

function fitModel(model: THREE.Object3D, extent: number, ground: boolean, landscape = false): void {
  model.updateMatrixWorld(true);
  let bounds = new THREE.Box3().setFromObject(model);
  let size = bounds.getSize(new THREE.Vector3());
  if (landscape && size.z > size.x) {
    model.rotation.y += Math.PI / 2;
    model.updateMatrixWorld(true);
    bounds = new THREE.Box3().setFromObject(model);
    size = bounds.getSize(new THREE.Vector3());
  }
  const scale = extent / Math.max(size.x, size.y, size.z, 0.001);
  model.scale.multiplyScalar(scale);
  model.updateMatrixWorld(true);
  bounds = new THREE.Box3().setFromObject(model);
  const center = bounds.getCenter(new THREE.Vector3());
  model.position.x -= center.x;
  model.position.z -= center.z;
  model.position.y -= ground ? bounds.min.y : center.y;
}

function goldFinish(model: THREE.Object3D): void {
  model.traverse((child) => {
    const mesh = child as THREE.Mesh;
    if (!mesh.isMesh || !mesh.material) return;
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    materials.forEach((original) => {
      const material = original as THREE.MeshStandardMaterial;
      if (material.color) material.color.lerp(new THREE.Color(0xf4c96b), 0.68);
      if ("metalness" in material) material.metalness = Math.max(material.metalness || 0, 0.82);
      if ("roughness" in material) material.roughness = Math.min(material.roughness ?? 0.5, 0.22);
    });
  });
}

async function loadModel(
  bin: SceneBin,
  options: Options,
  path: string,
  name: string,
  parent: THREE.Object3D,
  extent: number,
  ground = false,
  landscape = false,
  gold = false
): Promise<THREE.Object3D | null> {
  if (!options.canStream || options.isCancelled()) return null;
  try {
    const gltf = await AssetStreamingCache.getInstance().loadGltf(options.resolveUrl(path));
    if (!gltf?.scene || options.isCancelled()) return null;
    const model = cloneSkinned(gltf.scene);
    model.traverse((child) => {
      const mesh = child as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.geometry = mesh.geometry.clone();
      mesh.material = Array.isArray(mesh.material)
        ? mesh.material.map((material) => material.clone())
        : mesh.material?.clone() || mesh.material;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      mesh.frustumCulled = false;
    });
    fitModel(model, extent, ground, landscape);
    if (gold) goldFinish(model);
    model.name = name;
    parent.add(model);
    bin.imported.push(model);
    return model;
  } catch (error) {
    console.error("Cinematic gift model failed to load", { name, path, error });
    return null;
  }
}

function addLights(bin: SceneBin, accent: number): THREE.PointLight {
  bin.root.add(new THREE.HemisphereLight(0xeaf2ff, 0x111522, 0.42));
  const key = new THREE.DirectionalLight(0xfff4df, 2.2);
  key.position.set(-8, 16, 10);
  key.castShadow = true;
  bin.root.add(key);
  const rim = new THREE.DirectionalLight(accent, 2.6);
  rim.position.set(8, 7, -10);
  bin.root.add(rim);
  const accentLight = new THREE.PointLight(accent, 2.6, 68, 2);
  accentLight.position.set(0, 5, 0);
  bin.root.add(accentLight);
  return accentLight;
}

function addParticles(bin: SceneBin, quality: GiftQuality, color: number): THREE.Points {
  const count = Math.max(24, Math.floor(quality.particles * 0.62));
  const positions = new Float32Array(count * 3);
  const phases = new Float32Array(count);
  const sizes = new Float32Array(count);
  for (let i = 0; i < count; i++) {
    const angle = i * 2.399963229728653;
    positions[i * 3] = Math.cos(angle) * (1 + (i % 17) / 17) * 18;
    positions[i * 3 + 1] = ((i * 37) % 101) / 101 * 12 - 2;
    positions[i * 3 + 2] = Math.sin(angle) * (1 + (i % 13) / 13) * 18;
    phases[i] = ((i * 19) % 97) / 97;
    sizes[i] = 1.3 + ((i * 11) % 9) * 0.42;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("aPhase", new THREE.BufferAttribute(phases, 1));
  geometry.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
  const material = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    uniforms: { uTime: { value: 0 }, uColor: { value: new THREE.Color(color) }, uIntensity: { value: 0.3 } },
    vertexShader: [
      "attribute float aPhase;",
      "attribute float aSize;",
      "uniform float uTime;",
      "varying float vAlpha;",
      "void main() {",
      "vec3 p = position;",
      "p.y += mod(uTime * 0.72 + aPhase * 8.0, 9.0) - 4.5;",
      "p.x += sin(uTime * 0.35 + aPhase * 6.28318) * 0.18;",
      "vec4 view = modelViewMatrix * vec4(p, 1.0);",
      "gl_PointSize = aSize * (150.0 / max(1.0, -view.z));",
      "gl_Position = projectionMatrix * view;",
      "vAlpha = 0.35 + 0.65 * sin(aPhase * 6.28318 + uTime * 1.8);",
      "}",
    ].join("\n"),
    fragmentShader: [
      "uniform vec3 uColor;",
      "uniform float uIntensity;",
      "varying float vAlpha;",
      "void main() {",
      "float radius = length(gl_PointCoord - vec2(0.5));",
      "float glow = 1.0 - smoothstep(0.05, 0.5, radius);",
      "gl_FragColor = vec4(uColor, glow * vAlpha * uIntensity);",
      "}",
    ].join("\n"),
  });
  const points = new THREE.Points(geometry, material);
  points.name = "gift-cinematic-particles";
  bin.root.add(points);
  bin.track(geometry);
  bin.track(material);
  return points;
}

function updateParticles(points: THREE.Points, progress: number, delta: number, intensity: number): void {
  const material = points.material as THREE.ShaderMaterial;
  material.uniforms.uTime.value += delta;
  material.uniforms.uIntensity.value = intensity * (0.76 + Math.sin(progress * Math.PI * 4) * 0.12);
}

/** Reveal the authored asset wrapper without altering source mesh topology. */
function animateHeroReveal(
  hero: THREE.Group,
  progress: number,
  profile: { startScale?: number; yaw?: number; drift?: number } = {}
): void {
  const reveal = smooth(clamp(progress / 0.2));
  const settle = smooth(clamp((progress - 0.72) / 0.2));
  hero.scale.setScalar(lerp(profile.startScale ?? 0.88, 1, reveal));
  hero.rotation.y = Math.sin(progress * Math.PI * 1.35) * (profile.yaw ?? 0.045) * (1 - settle * 0.65);
  hero.rotation.z = Math.sin(progress * Math.PI * 2) * (profile.drift ?? 0.008) * (1 - settle * 0.7);
}

function addOcean(bin: SceneBin): THREE.ShaderMaterial {
  const geometry = new THREE.PlaneGeometry(220, 220, 48, 48);
  geometry.rotateX(-Math.PI / 2);
  const material = new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 } },
    vertexShader: [
      "uniform float uTime;",
      "varying vec3 vPos;",
      "void main() {",
      "vec3 p = position;",
      "p.y += sin(position.x * 0.075 + uTime * 0.75) * 0.24;",
      "p.y += cos(position.z * 0.09 - uTime * 0.58) * 0.18;",
      "vPos = p;",
      "gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);",
      "}",
    ].join("\n"),
    fragmentShader: [
      "varying vec3 vPos;",
      "void main() {",
      "float glint = pow(max(sin(vPos.x * 0.11 + vPos.z * 0.07), 0.0), 20.0);",
      "vec3 deep = vec3(0.012, 0.095, 0.17);",
      "vec3 blue = vec3(0.025, 0.24, 0.34);",
      "vec3 color = mix(deep, blue, 0.55) + vec3(0.55, 0.72, 0.82) * glint * 0.48;",
      "gl_FragColor = vec4(color, 1.0);",
      "}",
    ].join("\n"),
  });
  const surface = new THREE.Mesh(geometry, material);
  surface.name = "gift-ocean-surface";
  surface.position.y = -0.3;
  bin.root.add(surface);
  bin.track(geometry);
  bin.track(material);
  return material;
}

interface PlayerRig {
  mixer: THREE.AnimationMixer;
  actions: Record<string, THREE.AnimationAction | undefined>;
  pivot: THREE.Group;
  feet: () => THREE.Vector3;
}

let sharedFootballer: Promise<{ model: THREE.Object3D; clips: Map<string, THREE.AnimationClip> }> | null = null;

function loadFootballer(resolveUrl: (path: string) => string) {
  if (!sharedFootballer) {
    sharedFootballer = Promise.all([
      AssetStreamingCache.getInstance().loadGltf(resolveUrl(ASSETS.kit)),
      AssetStreamingCache.getInstance().loadGltf(resolveUrl(ASSETS.clips)),
    ]).then(([kit, animation]) => {
      if (!kit?.scene) throw new Error("GTEX animated footballer model unavailable");
      const clips = new Map<string, THREE.AnimationClip>();
      (animation?.animations || []).forEach((clip) => clips.set(clip.name, clip));
      return { model: kit.scene, clips };
    }).catch((error) => {
      sharedFootballer = null;
      throw error;
    });
  }
  return sharedFootballer;
}

function spawnPlayer(model: THREE.Object3D, clips: Map<string, THREE.AnimationClip>, names: string[]): { pivot: THREE.Group; rig: PlayerRig } {
  const visual = cloneSkinned(model);
  visual.rotation.y = Math.PI / 2;
  visual.traverse((child) => {
    const mesh = child as THREE.Mesh;
    if (mesh.isMesh) {
      mesh.frustumCulled = false;
      mesh.castShadow = true;
    }
  });
  visual.updateMatrixWorld(true);
  const bounds = new THREE.Box3().setFromObject(visual);
  const height = bounds.max.y - bounds.min.y;
  if (height < 0.4 || height > 3.2) visual.scale.multiplyScalar(1.78 / Math.max(height, 0.001));
  visual.updateMatrixWorld(true);
  const grounded = new THREE.Box3().setFromObject(visual);
  visual.position.y -= grounded.min.y + 1.05;
  const pivot = new THREE.Group();
  pivot.position.y = 1.05;
  pivot.add(visual);
  const mixer = new THREE.AnimationMixer(visual);
  const actions: Record<string, THREE.AnimationAction | undefined> = {};
  names.forEach((name) => {
    const source = clips.get(name);
    if (!source) return;
    const tracks = source.tracks.filter((track) => !track.name.startsWith("mixamorigHips."));
    const clip = new THREE.AnimationClip(source.name, source.duration, tracks);
    const action = mixer.clipAction(clip);
    action.clampWhenFinished = true;
    action.loop = name === CLIPS.run || name === CLIPS.celebration ? THREE.LoopRepeat : THREE.LoopOnce;
    actions[name] = action;
  });
  const temp = new THREE.Vector3();
  return {
    pivot,
    rig: {
      mixer,
      actions,
      pivot,
      feet: () => {
        const left = visual.getObjectByName("mixamorigLeftFoot");
        const right = visual.getObjectByName("mixamorigRightFoot");
        let bestY = -Infinity;
        const best = new THREE.Vector3();
        [left, right].forEach((bone) => {
          if (!bone) return;
          bone.getWorldPosition(temp);
          if (temp.y > bestY) {
            bestY = temp.y;
            best.copy(temp);
          }
        });
        return best;
      },
    },
  };
}

function addRarityLight(bin: SceneBin, rarity?: string): { light: THREE.PointLight; amount: number } {
  const grades: Record<string, { color: number; amount: number }> = {
    common: { color: 0xd9e6f5, amount: 0.28 },
    rare: { color: 0x70d8e8, amount: 0.42 },
    epic: { color: 0xa68bff, amount: 0.58 },
    legendary: { color: 0xffc45f, amount: 0.78 },
    mythic: { color: 0xffe5a3, amount: 1 },
  };
  const grade = grades[String(rarity || "common").toLowerCase()] || grades.common;
  const light = new THREE.PointLight(grade.color, grade.amount * 3, 55, 2);
  light.position.set(0, 4.5, 0);
  light.name = "gift-rarity-light";
  bin.root.add(light);
  return { light, amount: grade.amount };
}

function ready(options: Options, tasks: Promise<unknown>[]): void {
  if (!options.canStream) {
    options.onReady();
    return;
  }
  void Promise.all(tasks).finally(() => {
    if (!options.isCancelled()) options.onReady();
  });
}

function finish(
  bin: SceneBin,
  background: number,
  exposure: number,
  update: GiftDirector["update"],
  rarity?: string
): GiftDirector {
  const grade = addRarityLight(bin, rarity);
  return {
    root: bin.root,
    background: new THREE.Color(background),
    exposure,
    update: (progress, delta, camera) => {
      update(progress, delta, camera);
      grade.light.intensity = grade.amount * (2.1 + Math.sin(progress * Math.PI * 4) * 0.38);
    },
    dispose: () => bin.dispose(),
  };
}

export function createGiftDirector(options: Options): GiftDirector {
  const bin = new SceneBin();
  const code = options.giftCode.toLowerCase();
  const shot = options.shot;
  const camera = (target: THREE.PerspectiveCamera, progress: number, hero?: [number, number, number]) => {
    const frame = frameGiftShot(shot, progress, hero);
    const impactAt =
      shot === "bicycle" ? 0.8 :
      shot === "last_minute" ? 0.74 :
      shot === "goal" || shot === "golden_goal" ? 0.68 : null;
    const impact = impactAt === null ? 0 : Math.exp(-Math.pow((progress - impactAt) * 36, 2));
    target.position.set(
      frame.position[0] + Math.sin(progress * 210) * impact * 0.045,
      frame.position[1] + Math.cos(progress * 184) * impact * 0.035,
      frame.position[2]
    );
    target.lookAt(...frame.lookAt);
    const fov = frame.fov - impact * 1.15;
    if (Math.abs(target.fov - fov) > 0.04) {
      target.fov = fov;
      target.updateProjectionMatrix();
    }
  };

  if (shot === "city") {
    const accent = code.includes("tokyo") ? 0xd78aff : code.includes("dubai") ? 0xffc56e : 0x94c8ff;
    const light = addLights(bin, accent);
    const particles = addParticles(bin, options.quality, accent);
    const isPenthouseGift = code.includes("penthouse");
    let hero: THREE.Group | null = null;
    let task: Promise<unknown> = Promise.resolve(null);
    if (isPenthouseGift) {
      hero = new THREE.Group();
      hero.name = "gift-penthouse-hero";
      hero.userData.assetPath = ASSETS.city;
      bin.root.add(hero);
      task = loadModel(bin, options, ASSETS.city, "gift-penthouse-authored-model", hero, 15, true);
    }
    ready(options, [task]);
    return finish(bin, 0x071321, 1.14, (progress, delta, target) => {
      camera(target, progress);
      if (hero) animateHeroReveal(hero, progress, { startScale: 0.9, yaw: 0.065, drift: 0.004 });
      light.intensity = 2.6 + smooth(progress) * 1.4;
      updateParticles(particles, progress, delta, 0.24);
    }, options.rarity);
  }

  if (shot === "stadium") {
    const golden = code.includes("golden");
    const accent = golden ? 0xffc95e : 0x8fc6ff;
    const light = addLights(bin, accent);
    const particles = addParticles(bin, options.quality, accent);
    const hero = new THREE.Group();
    hero.name = "gift-stadium-hero";
    hero.userData.assetPath = code.includes("golden") ? ASSETS.goldenStadium : ASSETS.stadium;
    bin.root.add(hero);
    const path = golden ? ASSETS.goldenStadium : ASSETS.stadium;
    const task = loadModel(bin, options, path, golden ? "gift-golden-stadium-model" : "gift-stadium-model", hero, 86, true);
    ready(options, [task]);
    return finish(bin, golden ? 0x100c08 : 0x07111c, golden ? 1.25 : 1.12, (progress, delta, target) => {
      camera(target, progress);
      animateHeroReveal(hero, progress, { startScale: 0.84, yaw: 0.055, drift: 0.006 });
      light.intensity = (golden ? 4.8 : 3) * smooth(progress);
      updateParticles(particles, progress, delta, golden ? 0.78 : 0.34);
    }, options.rarity);
  }

  if (shot === "jet") {
    const light = addLights(bin, 0xb8dcff);
    const particles = addParticles(bin, options.quality, 0xb8dcff);
    const aircraft = new THREE.Group();
    aircraft.name = "gift-aircraft";
    bin.root.add(aircraft);
    const jetPath = code.includes("gulfstream") ? ASSETS.gulfstream : ASSETS.jet;
    aircraft.userData.assetPath = jetPath;
    const task = loadModel(bin, options, jetPath, "gift-private-jet-model", aircraft, 24, true, true);
    ready(options, [task]);
    return finish(bin, 0x08111e, 1.16, (progress, delta, target) => {
      const glide = smooth(progress);
      const climb = smooth(clamp((progress - 0.62) / 0.38));
      aircraft.position.set(lerp(-5, 5, glide), climb * 3.1, 0);
      animateHeroReveal(aircraft, progress, { startScale: 0.9, yaw: 0.025, drift: 0.018 });
      camera(target, progress, [aircraft.position.x, aircraft.position.y, aircraft.position.z]);
      light.intensity = 2.8 + climb * 1.5;
      updateParticles(particles, progress, delta, 0.24 + climb * 0.32);
    }, options.rarity);
  }

  if (shot === "yacht") {
    const light = addLights(bin, 0xffc48d);
    const particles = addParticles(bin, options.quality, 0xffc48d);
    const water = addOcean(bin);
    const yacht = new THREE.Group();
    yacht.name = "gift-yacht";
    yacht.userData.assetPath = ASSETS.yacht;
    bin.root.add(yacht);
    const task = loadModel(bin, options, ASSETS.yacht, "gift-superyacht-model", yacht, 26, true, true);
    ready(options, [task]);
    return finish(bin, 0x102c46, 1.2, (progress, delta, target) => {
      water.uniforms.uTime.value += delta;
      const glide = smooth(progress);
      yacht.position.set(lerp(-2.5, 3.5, glide), Math.sin(progress * Math.PI * 2) * 0.12, 0);
      animateHeroReveal(yacht, progress, { startScale: 0.88, yaw: 0.035, drift: 0.004 });
      camera(target, progress);
      light.intensity = 3 + Math.sin(progress * Math.PI * 2) * 0.3;
      updateParticles(particles, progress, delta, 0.3);
    }, options.rarity);
  }

  if (shot === "coach" || shot === "vehicle" || shot === "facility") {
    const path =
      shot === "coach"
        ? ASSETS.coach
        : shot === "facility"
          ? ASSETS.facility
          : code.includes("hypercar") || code.includes("veloce")
            ? ASSETS.hypercar
            : ASSETS.suv;
    const extent = shot === "facility" ? 42 : shot === "coach" ? 20 : 14;
    const accent = shot === "facility" ? 0x8fc6ff : shot === "coach" ? 0xffd28b : 0xe5eaf2;
    const light = addLights(bin, accent);
    const particles = addParticles(bin, options.quality, accent);
    const hero = new THREE.Group();
    hero.name = shot === "coach" ? "gift-coach" : shot === "facility" ? "gift-facility" : "gift-vehicle";
    hero.userData.assetPath = path;
    bin.root.add(hero);
    const task = loadModel(bin, options, path, "gift-authored-hero-model", hero, extent, true, true);
    ready(options, [task]);
    return finish(bin, 0x08111d, 1.16, (progress, delta, target) => {
      const reveal = smooth(clamp(progress / 0.22));
      hero.position.x = lerp(shot === "facility" ? 0 : -4.5, 0, reveal);
      animateHeroReveal(hero, progress, {
        startScale: shot === "facility" ? 0.9 : 0.86,
        yaw: shot === "facility" ? 0.035 : 0.025,
        drift: shot === "facility" ? 0.003 : 0.008,
      });
      camera(target, progress);
      light.intensity = (shot === "facility" ? 3.2 : 2.8) + smooth(progress) * 1.1;
      updateParticles(particles, progress, delta, 0.24);
    }, options.rarity);
  }

  const authoredWatch = shot === "crown" && (code.includes("watch") || code.includes("chronos"));
  if (shot === "boot" || shot === "glove" || shot === "card" || shot === "tactics" || (shot === "crown" && !authoredWatch)) {
    // These catalogue families do not yet have an approved hero model. Keep the
    // reveal atmospheric rather than presenting a trophy or watch as the wrong gift.
    const accent = shot === "glove" ? 0x9edcff : shot === "boot" ? 0xe9c36c : 0xb9c9e4;
    const light = addLights(bin, accent);
    const particles = addParticles(bin, options.quality, accent);
    ready(options, []);
    return finish(bin, 0x08090d, 1.12, (progress, delta, target) => {
      camera(target, progress);
      light.intensity = 2.5 + Math.sin(progress * Math.PI * 2) * 0.55;
      updateParticles(particles, progress, delta, 0.32);
    }, options.rarity);
  }

  if (shot === "trophy" || authoredWatch) {
    const light = addLights(bin, authoredWatch ? 0x9edcff : 0xffd16b);
    const particles = addParticles(bin, options.quality, authoredWatch ? 0x9edcff : 0xffd16b);
    const award = new THREE.Group();
    award.name = shot === "trophy" ? "ballon-dor-stage" : "gift-watch-stage";
    const path = authoredWatch ? ASSETS.crown : ASSETS.trophy;
    award.userData.assetPath = path;
    bin.root.add(award);
    const tasks: Promise<unknown>[] = [
      loadModel(bin, options, path, "gift-award-authored-model", award, 5.8, true),
    ];
    if (shot === "trophy") {
      const ball = new THREE.Group();
      ball.name = "ballon-dor-ball";
      ball.position.set(0, 1.2, 0);
      award.add(ball);
      tasks.push(loadModel(bin, options, ASSETS.ball, "gift-gold-football-model", ball, 1.65, false, false, true));
    }
    ready(options, tasks);
    return finish(bin, 0x08090d, 1.18, (progress, delta, target) => {
      camera(target, progress);
      animateHeroReveal(award, progress, { startScale: 0.76, yaw: 0, drift: 0.002 });
      award.rotation.y = progress * Math.PI * 0.16;
      award.position.y = -0.45 + smooth(clamp(progress / 0.24)) * 0.45;
      const ball = award.getObjectByName("ballon-dor-ball");
      if (ball) ball.rotation.y = progress * Math.PI * 0.95;
      light.intensity = 3.1 + Math.sin(progress * Math.PI * 2) * 0.45;
      updateParticles(particles, progress, delta, 0.62);
    }, options.rarity);
  }

  const winner = shot === "last_minute";
  const bicycle = shot === "bicycle";
  const goldenGoal = shot === "golden_goal";
  const accent = goldenGoal ? 0xffd16b : winner ? 0xff536d : 0x8fc6ff;
  const light = addLights(bin, accent);
  const particles = addParticles(bin, options.quality, accent);

  const stadium = new THREE.Group();
  stadium.name = "gift-match-stadium";
  stadium.userData.assetPath = ASSETS.matchStadium;
  bin.root.add(stadium);
  const stadiumTask = loadModel(bin, options, ASSETS.matchStadium, "gift-match-stadium-model", stadium, 88, true);

  const goal = new THREE.Group();
  goal.name = "match-goal";
  goal.userData.assetPath = ASSETS.goal;
  goal.position.set(17, 0, 0);
  bin.root.add(goal);
  const goalTask = loadModel(bin, options, ASSETS.goal, "gift-match-goal-model", goal, 7.2, true, true);

  const ball = new THREE.Group();
  ball.name = "gift-ball";
  ball.userData.assetPath = ASSETS.ball;
  bin.root.add(ball);
  const ballTask = loadModel(bin, options, ASSETS.ball, "gift-match-ball-model", ball, 0.48, false, false, goldenGoal);

  const player = new THREE.Group();
  player.name = "gift-player";
  bin.root.add(player);
  const celebrant = new THREE.Group();
  celebrant.name = "gift-celebrant";
  celebrant.visible = false;
  bin.root.add(celebrant);

  let kicker: PlayerRig | null = null;
  let dancer: PlayerRig | null = null;
  let kicked = false;
  const release = new THREE.Vector3(-0.5, 1.4, 0.2);
  const playerTask = options.canStream
    ? loadFootballer(options.resolveUrl)
        .then((shared) => {
          if (options.isCancelled()) return null;
          const spawned = spawnPlayer(shared.model, shared.clips, bicycle ? [CLIPS.bicycle] : [CLIPS.run, CLIPS.penalty]);
          player.add(spawned.pivot);
          kicker = spawned.rig;
          kicker.actions[bicycle ? CLIPS.bicycle : CLIPS.run]?.reset().play();
          if (winner) {
            const celebration = spawnPlayer(shared.model, shared.clips, [CLIPS.celebration]);
            celebrant.add(celebration.pivot);
            dancer = celebration.rig;
          }
          return spawned;
        })
        .catch((error) => {
          console.error("GTEX animated gifting footballer unavailable", error);
          return null;
        })
    : Promise.resolve(null);
  ready(options, [stadiumTask, goalTask, ballTask, playerTask]);

  return finish(bin, 0x07111d, 1.14, (progress, delta, target) => {
    camera(target, progress);
    kicker?.mixer.update(delta);
    dancer?.mixer.update(delta);

    if (bicycle) {
      const leanIn = smooth(clamp((progress - 0.12) / 0.28));
      const leanOut = smooth(clamp((progress - 0.55) / 0.18));
      if (kicker?.pivot) kicker.pivot.rotation.x = -2.25 * leanIn * (1 - leanOut * 0.82);
      player.position.set(lerp(-1.2, 1.2, smooth(progress)), 0, 0);
      const foot = kicker?.feet() || new THREE.Vector3(0.4, 1.5, 0.2);
      if (progress < 0.3) {
        const amount = smooth(progress / 0.3);
        ball.position.set(lerp(-1.5, foot.x, amount), lerp(2.1, Math.max(foot.y, 0.4), amount), lerp(3.6, foot.z, amount));
      } else if (progress < 0.5) {
        ball.position.lerp(foot, 0.42);
        release.copy(ball.position);
      } else {
        const amount = smooth((progress - 0.5) / 0.32);
        ball.position.set(lerp(release.x, 16.5, amount), lerp(release.y, 2.1, amount), lerp(release.z, -1.5, amount));
      }
    } else if (winner) {
      const approach = smooth(clamp(progress / 0.48));
      player.position.set(lerp(-12, -1.5, approach), 0, lerp(1.2, 0.2, approach));
      if (progress > 0.48 && !kicked) {
        kicked = true;
        kicker?.actions[CLIPS.run]?.fadeOut(0.12);
        kicker?.actions[CLIPS.penalty]?.reset().fadeIn(0.1).play();
      }
      if (progress < 0.5) {
        ball.position.set(player.position.x + 0.45, 0.24, player.position.z);
        release.copy(ball.position);
      } else {
        const amount = smooth((progress - 0.5) / 0.28);
        ball.position.set(lerp(release.x, 16.6, amount), lerp(0.24, 0.85, amount) + Math.sin(amount * Math.PI) * 0.7, lerp(release.z, 1.4, amount));
      }
      if (progress > 0.72) {
        celebrant.visible = true;
        celebrant.position.set(player.position.x - 1.1, 0, 1.3);
        if (dancer && !dancer.actions[CLIPS.celebration]?.isRunning()) dancer.actions[CLIPS.celebration]?.reset().play();
      }
    } else {
      const amount = smooth(clamp(progress / 0.7));
      ball.position.set(lerp(-8, 16.4, amount), 0.8 + Math.sin(amount * Math.PI) * 2.2, lerp(2, 0, amount));
      player.position.set(lerp(-6, -1, amount), 0, 0);
    }

    const impactWindow = winner ? 0.74 : bicycle ? 0.8 : 0.68;
    const impact = Math.exp(-Math.pow((progress - impactWindow) * 22, 2));
    light.intensity = (2.2 + impact * 10) * (goldenGoal ? 1.35 : 1);
    updateParticles(particles, progress, delta, (winner || bicycle ? 0.46 : 0.28) + impact * 0.9);
    if (goldenGoal) stadium.rotation.y = Math.sin(progress * Math.PI) * 0.03;
  }, options.rarity);
}