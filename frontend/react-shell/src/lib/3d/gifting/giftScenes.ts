import * as THREE from "three";
import { clone as cloneSkinned } from "three/examples/jsm/utils/SkeletonUtils.js";
import { AssetStreamingCache } from "../broadcast/AssetStreamingCache";
import type { GiftQuality } from "./giftQuality";

const STADIUM_URL = "/models/match/football-stadium.glb";
const JET_URL = "/assets/showroom/sovereign_900x_jet.glb";
const YACHT_URL = "/assets/showroom/superyacht.glb";
const BALL_URL = "/models/match/football_pbr.glb";
const KIT_URL = "/models/footballer/gtex_home_kit_mixamo.glb";
const CLIP_URL = "/models/footballer/gtex_mixamo_clips.glb";

const SCISSOR_CLIP = "Soccer_Scissor_Kick_To_Goal";
const RUN_CLIP = "Running_Forwards";
const PENALTY_CLIP = "Male_Soccer_Penalty_Kick";
const SPIN_CLIP = "Soccer_360_Spin";

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

interface DirectorOptions {
  shot: string;
  giftCode: string;
  quality: GiftQuality;
  canStream: boolean;
  resolveUrl: (path: string) => string;
  isCancelled: () => boolean;
  onReady: () => void;
}

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function smooth(value: number): number {
  const t = clamp01(value);
  return t * t * (3 - 2 * t);
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function v3(tuple: [number, number, number]): THREE.Vector3 {
  return new THREE.Vector3(tuple[0], tuple[1], tuple[2]);
}

let moteTexture: THREE.Texture | null = null;

function moteMap(): THREE.Texture | null {
  if (moteTexture) return moteTexture;
  if (typeof document === "undefined") return null;
  const canvas = document.createElement("canvas");
  canvas.width = 32;
  canvas.height = 32;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  const glow = ctx.createRadialGradient(16, 16, 1, 16, 16, 16);
  glow.addColorStop(0, "rgba(255,255,255,1)");
  glow.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, 32, 32);
  moteTexture = new THREE.CanvasTexture(canvas);
  return moteTexture;
}

export function frameGiftShot(
  shot: string,
  progress: number,
  hero: [number, number, number] = [0, 0, 0],
  giftCode = ""
): GiftFrame {
  const t = smooth(progress);
  const golden = giftCode.toLowerCase().includes("golden");
  if (shot === "city") {
    return {
      position: [lerp(8, 12, t), lerp(10, 18, t), lerp(24, 48, t)],
      lookAt: [0, lerp(7, 12, t), 0],
      fov: lerp(40, 32, t),
    };
  }
  if (shot === "stadium" && golden) {
    return {
      position: [lerp(28, 16, t), lerp(42, 18, t), lerp(62, 34, t)],
      lookAt: [-4, lerp(4, 1, t), 2],
      fov: lerp(50, 32, t),
    };
  }
  if (shot === "stadium") {
    return {
      position: [lerp(10, 22, t), lerp(36, 16, t), lerp(58, 40, t)],
      lookAt: [0, 3, 0],
      fov: lerp(50, 36, t),
    };
  }
  if (shot === "jet") {
    return {
      position: [hero[0] + 4, hero[1] + 6.5, lerp(34, 22, t)],
      lookAt: [hero[0], hero[1] + 1.2, 0],
      fov: 34,
    };
  }
  if (shot === "yacht") {
    return {
      position: [lerp(20, 28, t), lerp(8, 6, t), lerp(24, 18, t)],
      lookAt: [0, 1.6, 0],
      fov: 36,
    };
  }
  if (shot === "trophy") {
    const orbit = progress * Math.PI * 0.85;
    const radius = lerp(4.6, 3.4, t);
    return {
      position: [Math.sin(orbit) * radius, lerp(2.6, 1.9, t), Math.cos(orbit) * radius],
      lookAt: [0, 1.2, 0],
      fov: 30,
    };
  }
  if (shot === "bicycle") {
    const kick = 1 - smooth(clamp01((progress - 0.52) / 0.22));
    return {
      position: [lerp(7.5, 0.4, kick), lerp(2.8, 1.55, kick), lerp(9, 6.8, kick)],
      lookAt: [lerp(14, 0.2, kick), lerp(1.6, 1.2, kick), 0],
      fov: 36,
    };
  }
  if (shot === "last_minute") {
    const attack = 1 - smooth(clamp01((progress - 0.5) / 0.18));
    return {
      position: [lerp(4, -9, attack), lerp(3.4, 2.1, attack), lerp(8, 8.5, attack)],
      lookAt: [lerp(14, -2.2, attack), 1.25, 0],
      fov: 36,
    };
  }
  return {
    position: [lerp(6, 3, t), lerp(2.2, 3.4, t), lerp(9, 6, t)],
    lookAt: [0, 1.6, 0],
    fov: 36,
  };
}

function skyDome(top: number, horizon: number, ground: number): THREE.Mesh {
  const material = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    uniforms: {
      uTop: { value: new THREE.Color(top) },
      uHorizon: { value: new THREE.Color(horizon) },
      uGround: { value: new THREE.Color(ground) },
    },
    vertexShader: `
      varying vec3 vDir;
      void main() {
        vDir = normalize((modelMatrix * vec4(position, 1.0)).xyz);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform vec3 uTop;
      uniform vec3 uHorizon;
      uniform vec3 uGround;
      varying vec3 vDir;
      void main() {
        float h = normalize(vDir).y;
        vec3 color = h > 0.0
          ? mix(uHorizon, uTop, pow(clamp(h, 0.0, 1.0), 0.62))
          : mix(uHorizon, uGround, pow(clamp(-h, 0.0, 1.0), 0.5));
        gl_FragColor = vec4(color, 1.0);
      }
    `,
  });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(240, 28, 16), material);
  mesh.frustumCulled = false;
  mesh.renderOrder = -2;
  mesh.name = "gift-sky";
  return mesh;
}

function centerOnOrigin(object: THREE.Object3D, targetLongest: number): void {
  object.updateMatrixWorld(true);
  const measured = new THREE.Box3().setFromObject(object).getSize(new THREE.Vector3());
  const longest = Math.max(measured.x, measured.y, measured.z, 0.001);
  object.scale.multiplyScalar(targetLongest / longest);
  object.updateMatrixWorld(true);
  const fitted = new THREE.Box3().setFromObject(object);
  const center = fitted.getCenter(new THREE.Vector3());
  object.position.sub(center);
}

function groundFit(object: THREE.Object3D, targetLongest: number, alignX: boolean): void {
  object.updateMatrixWorld(true);
  if (alignX) {
    const size = new THREE.Box3().setFromObject(object).getSize(new THREE.Vector3());
    if (size.z > size.x) object.rotation.y += Math.PI / 2;
  }
  object.updateMatrixWorld(true);
  const measured = new THREE.Box3().setFromObject(object).getSize(new THREE.Vector3());
  const longest = Math.max(measured.x, measured.y, measured.z, 0.001);
  object.scale.multiplyScalar(targetLongest / longest);
  object.updateMatrixWorld(true);
  const fitted = new THREE.Box3().setFromObject(object);
  const center = fitted.getCenter(new THREE.Vector3());
  object.position.x -= center.x;
  object.position.z -= center.z;
  object.position.y -= fitted.min.y;
}

function revealImported(object: THREE.Object3D): void {
  object.traverse((child) => {
    const mesh = child as THREE.Mesh;
    if (!mesh.isMesh) return;
    mesh.castShadow = true;
    mesh.frustumCulled = false;
    const materials = Array.isArray(mesh.material) ? mesh.material : mesh.material ? [mesh.material] : [];
    materials.forEach((material) => {
      material.side = THREE.DoubleSide;
    });
  });
}

function disposeUnique(root: THREE.Object3D): void {
  root.traverse((child) => {
    const mesh = child as THREE.Mesh;
    if (!mesh.isMesh) return;
    mesh.geometry?.dispose();
    const materials = Array.isArray(mesh.material) ? mesh.material : mesh.material ? [mesh.material] : [];
    materials.forEach((material) => {
      const standard = material as THREE.MeshStandardMaterial;
      standard.map?.dispose();
      standard.normalMap?.dispose();
      standard.roughnessMap?.dispose();
      standard.metalnessMap?.dispose();
      standard.aoMap?.dispose();
      standard.emissiveMap?.dispose();
      material.dispose();
    });
  });
}

class SceneBin {
  readonly root = new THREE.Group();
  readonly owned: Array<{ dispose: () => void }> = [];
  readonly unique: THREE.Object3D[] = [];
  track<T extends { dispose: () => void }>(resource: T): T {
    this.owned.push(resource);
    return resource;
  }
  mesh(geometry: THREE.BufferGeometry, material: THREE.Material, parent: THREE.Object3D = this.root): THREE.Mesh {
    this.track(geometry);
    this.track(material);
    const mesh = new THREE.Mesh(geometry, material);
    parent.add(mesh);
    return mesh;
  }
  dispose(): void {
    this.unique.forEach((object) => disposeUnique(object));
    this.owned.forEach((resource) => resource.dispose());
  }
}

function addMotes(bin: SceneBin, count: number, color: number, spread: number, height: number): THREE.Points {
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    positions[i * 3] = (Math.random() - 0.5) * spread;
    positions[i * 3 + 1] = Math.random() * height;
    positions[i * 3 + 2] = (Math.random() - 0.5) * spread;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const material = new THREE.PointsMaterial({
    color,
    size: 0.09,
    map: moteMap() || undefined,
    transparent: true,
    opacity: 0.85,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    sizeAttenuation: true,
  });
  const points = new THREE.Points(geometry, material);
  points.name = "gift-motes";
  bin.track(geometry);
  bin.track(material);
  bin.root.add(points);
  return points;
}

function driftMotes(points: THREE.Points, delta: number, rise: number): void {
  const attr = points.geometry.getAttribute("position") as THREE.BufferAttribute;
  const array = attr.array as Float32Array;
  for (let i = 0; i < array.length; i += 3) {
    array[i + 1] += rise * delta;
    if (array[i + 1] > 8) array[i + 1] = 0;
  }
  attr.needsUpdate = true;
}

function applyFrame(camera: THREE.PerspectiveCamera, frame: GiftFrame, fovBoost: number): void {
  camera.position.set(frame.position[0], frame.position[1], frame.position[2]);
  camera.lookAt(frame.lookAt[0], frame.lookAt[1], frame.lookAt[2]);
  const fov = frame.fov + fovBoost;
  if (Math.abs(camera.fov - fov) > 0.05) {
    camera.fov = fov;
    camera.updateProjectionMatrix();
  }
}

function addStrut(group: THREE.Group, bin: SceneBin, material: THREE.Material, a: THREE.Vector3, b: THREE.Vector3, radius: number): void {
  const direction = new THREE.Vector3().subVectors(b, a);
  const length = direction.length();
  if (length < 0.04) return;
  direction.multiplyScalar(1 / length);
  const geometry = new THREE.CylinderGeometry(radius, radius, length, 5, 1);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
  mesh.position.copy(a).add(b).multiplyScalar(0.5);
  group.add(mesh);
  bin.track(geometry);
}

function eiffelPoint(t: number, corner: number): THREE.Vector3 {
  const spread = 7.4 * Math.pow(1 - t, 0.82) + 0.22;
  const y = t * 34;
  const angle = Math.PI / 4 + corner * (Math.PI / 2);
  return new THREE.Vector3(Math.cos(angle) * spread, y, Math.sin(angle) * spread);
}

function quadPoint(a: THREE.Vector3, b: THREE.Vector3, c: THREE.Vector3, t: number): THREE.Vector3 {
  return a.clone().lerp(b, t).lerp(b.clone().lerp(c, t), t);
}

function buildEiffel(bin: SceneBin): THREE.Object3D {
  const material = new THREE.MeshStandardMaterial({
    color: 0xc4a574,
    metalness: 0.72,
    roughness: 0.34,
    emissive: 0xffb15a,
    emissiveIntensity: 0.22,
  });
  bin.track(material);
  const group = new THREE.Group();
  group.name = "eiffel-lattice";
  const samples = 16;
  for (let corner = 0; corner < 4; corner++) {
    for (let i = 0; i < samples; i++) {
      const a = eiffelPoint(i / samples, corner);
      const b = eiffelPoint((i + 1) / samples, corner);
      addStrut(group, bin, material, a, b, i < 4 ? 0.13 : 0.07);
      if (i < 12 && i % 2 === 0) {
        const next = (corner + 1) % 4;
        const c = eiffelPoint((i + 1) / samples, next);
        const d = eiffelPoint(i / samples, next);
        addStrut(group, bin, material, a, c, 0.045);
        addStrut(group, bin, material, b, d, 0.04);
      }
    }
  }
  [0.3, 0.56, 0.78].forEach((level) => {
    for (let corner = 0; corner < 4; corner++) {
      addStrut(group, bin, material, eiffelPoint(level, corner), eiffelPoint(level, (corner + 1) % 4), 0.1);
    }
  });
  for (let corner = 0; corner < 4; corner++) {
    const a = eiffelPoint(0.02, corner);
    const b = eiffelPoint(0.02, (corner + 1) % 4);
    const mid = a.clone().add(b).multiplyScalar(0.5);
    mid.y = 6.6;
    const outward = mid.clone();
    outward.y = 0;
    if (outward.lengthSq() > 0.001) mid.add(outward.normalize().multiplyScalar(1.5));
    let previous = a;
    for (let i = 1; i <= 8; i++) {
      const point = quadPoint(a, mid, b, i / 8);
      addStrut(group, bin, material, previous, point, 0.09);
      previous = point;
    }
  }
  addStrut(group, bin, material, eiffelPoint(1, 0), new THREE.Vector3(0, 41, 0), 0.08);
  bin.root.add(group);
  const beacon = bin.mesh(new THREE.SphereGeometry(0.28, 12, 12), new THREE.MeshBasicMaterial({ color: 0xfff1c2 }));
  beacon.position.set(0, 41, 0);
  beacon.name = "eiffel-beacon";
  return group;
}

function windowTexture(): THREE.Texture | null {
  if (typeof document === "undefined") return null;
  const canvas = document.createElement("canvas");
  canvas.width = 64;
  canvas.height = 128;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  ctx.fillStyle = "#1c1917";
  ctx.fillRect(0, 0, 64, 128);
  for (let y = 6; y < 124; y += 12) {
    for (let x = 5; x < 60; x += 10) {
      const on = ((x * 13 + y * 7) % 10) > 2;
      ctx.fillStyle = on ? (x + y) % 18 === 0 ? "#fde68a" : "#fbbf24" : "#0f172a";
      ctx.fillRect(x, y, 5, 7);
    }
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function buildParis(bin: SceneBin, quality: GiftQuality): { beacon: THREE.Mesh | null } {
  bin.root.add(skyDome(0x07101f, 0x1d3a66, 0x120c08));
  bin.root.add(new THREE.HemisphereLight(0x93c5fd, 0x1c1917, 0.55));
  const moon = new THREE.DirectionalLight(0xffe1b0, 1.35);
  moon.position.set(-18, 28, 12);
  bin.root.add(moon);
  buildEiffel(bin);
  const windows = windowTexture();
  const facade = new THREE.MeshStandardMaterial({
    color: 0x292524,
    roughness: 0.82,
    metalness: 0.08,
    map: windows || undefined,
    emissive: 0xfbbf24,
    emissiveMap: windows || undefined,
    emissiveIntensity: 0.55,
  });
  if (windows) bin.track(windows);
  bin.track(facade);
  for (let i = 0; i < 16; i++) {
    const angle = (i / 16) * Math.PI * 2 + 0.2;
    const radius = 14 + (i % 4) * 2.2;
    const height = 3.5 + ((i * 5) % 8);
    const width = 2.4 + (i % 3) * 0.7;
    const block = new THREE.Mesh(new THREE.BoxGeometry(width, height, width), facade);
    block.position.set(Math.cos(angle) * radius, height / 2, Math.sin(angle) * radius);
    bin.root.add(block);
    bin.track(block.geometry);
  }
  const plaza = bin.mesh(
    new THREE.CircleGeometry(12, 32),
    new THREE.MeshStandardMaterial({ color: 0x1c1917, roughness: 0.9 })
  );
  plaza.rotation.x = -Math.PI / 2;
  const river = bin.mesh(
    new THREE.PlaneGeometry(46, 7),
    new THREE.MeshStandardMaterial({ color: 0x0c4a6e, metalness: 0.65, roughness: 0.18 })
  );
  river.rotation.x = -Math.PI / 2;
  river.position.set(0, 0.02, 18);
  [0.3, 0.56, 0.78].forEach((level, index) => {
    const light = new THREE.PointLight(0xffcc88, 4 + index, 22, 2);
    light.position.set(0, level * 34, 0);
    bin.root.add(light);
  });
  addMotes(bin, quality.particles, 0xfde68a, 18, 12);
  const beacon = bin.root.getObjectByName("eiffel-beacon") as THREE.Mesh | null;
  return { beacon };
}

function tintGold(root: THREE.Object3D, strength: number): void {
  root.traverse((child) => {
    const mesh = child as THREE.Mesh;
    if (!mesh.isMesh || !mesh.material) return;
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    materials.forEach((material) => {
      const standard = material as THREE.MeshStandardMaterial;
      if (!standard.color) return;
      standard.color.lerp(new THREE.Color(0xf6c453), strength);
      if ("metalness" in standard) standard.metalness = Math.max(standard.metalness || 0, 0.55);
      if ("roughness" in standard) standard.roughness = Math.min(standard.roughness ?? 0.5, 0.38);
      if ("emissive" in standard) {
        standard.emissive = new THREE.Color(0xf59e0b);
        standard.emissiveIntensity = Math.max(standard.emissiveIntensity || 0, strength * 0.22);
      }
    });
  });
}

function floodMaterials(root: THREE.Object3D): THREE.MeshStandardMaterial[] {
  const found: THREE.MeshStandardMaterial[] = [];
  const bank = root.getObjectByName("Floodlights");
  (bank || root).traverse((child) => {
    const mesh = child as THREE.Mesh;
    if (!mesh.isMesh) return;
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    materials.forEach((material) => {
      const standard = material as THREE.MeshStandardMaterial;
      if (standard && "emissive" in standard && (bank || /flood|light|lamp/i.test(mesh.name))) {
        found.push(standard);
      }
    });
  });
  return found;
}

async function attachStadium(
  bin: SceneBin,
  options: DirectorOptions,
  golden: boolean,
  lightsOut: THREE.MeshStandardMaterial[]
): Promise<void> {
  if (!options.canStream) return;
  let lastError: unknown = null;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      const gltf = await AssetStreamingCache.getInstance().loadGltf(options.resolveUrl(STADIUM_URL));
      if (options.isCancelled() || !gltf?.scene) return;
      const imported = gltf.scene;
      imported.name = golden ? "golden-arena-model" : "maracana-bowl-model";
      groundFit(imported, golden ? 96 : 86, false);
      revealImported(imported);
      if (golden) tintGold(imported, 0.22);
      imported.traverse((child) => {
        const mesh = child as THREE.Mesh;
        if (mesh.isMesh) mesh.receiveShadow = true;
      });
      bin.root.add(imported);
      bin.unique.push(imported);
      const fallback = bin.root.getObjectByName("stadium-fallback");
      if (fallback) fallback.visible = false;
      lightsOut.push(...floodMaterials(imported));
      return;
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 400 * (attempt + 1)));
    }
  }
  console.error("gift stadium load failed", lastError);
}

function buildStadiumBase(bin: SceneBin, golden: boolean, quality: GiftQuality): THREE.SpotLight[] {
  bin.root.add(skyDome(golden ? 0x140c04 : 0x07111f, golden ? 0x7c4a12 : 0x1e3a5f, golden ? 0x3f2a08 : 0x052e16));
  bin.root.add(new THREE.HemisphereLight(golden ? 0xfde68a : 0xdbeafe, 0x052e16, golden ? 0.45 : 0.32));
  const fallback = new THREE.Group();
  fallback.name = "stadium-fallback";
  bin.root.add(fallback);
  const pitch = bin.mesh(
    new THREE.PlaneGeometry(52, 34),
    new THREE.MeshStandardMaterial({ color: golden ? 0xc2410c : 0x15803d, roughness: 0.78 }),
    fallback
  );
  pitch.rotation.x = -Math.PI / 2;
  pitch.name = golden ? "golden-arena" : "maracana-bowl";
  const concrete = new THREE.MeshStandardMaterial({ color: golden ? 0x78350f : 0x1e293b, roughness: 0.78, metalness: 0.12 });
  const seating = new THREE.MeshStandardMaterial({ color: golden ? 0xfbbf24 : 0x1d4ed8, roughness: 0.84 });
  bin.track(concrete);
  bin.track(seating);
  for (let tier = 0; tier < 7; tier += 1) {
    const inner = 30 + tier * 1.35;
    const deck = new THREE.Mesh(new THREE.RingGeometry(inner, inner + 1.7, 56), tier % 2 ? seating : concrete);
    deck.rotation.x = -Math.PI / 2;
    deck.scale.z = 0.74;
    deck.position.y = 0.55 + tier * 0.95;
    fallback.add(deck);
    bin.track(deck.geometry);
  }
  const roof = new THREE.Mesh(
    new THREE.RingGeometry(40, 44, 56),
    new THREE.MeshStandardMaterial({ color: golden ? 0xfcd34d : 0xe2e8f0, metalness: 0.55, roughness: 0.32 })
  );
  roof.rotation.x = -Math.PI / 2;
  roof.scale.z = 0.74;
  roof.position.y = 8.6;
  fallback.add(roof);
  bin.track(roof.geometry);
  const spots: THREE.SpotLight[] = [];
  [
    [-24, -16],
    [24, -16],
    [-24, 16],
    [24, 16],
  ].forEach(([x, z]) => {
    const mast = bin.mesh(
      new THREE.CylinderGeometry(0.25, 0.4, 16, 8),
      new THREE.MeshStandardMaterial({ color: golden ? 0xfbbf24 : 0xe2e8f0, metalness: 0.7, roughness: 0.3 })
    );
    mast.position.set(x, 8, z);
    fallback.add(mast);
    const spot = new THREE.SpotLight(golden ? 0xfde68a : 0xf8fafc, 0, 90, 0.55, 0.35, 1);
    spot.position.set(x, 18, z);
    spot.target.position.set(0, 0, 0);
    bin.root.add(spot);
    bin.root.add(spot.target);
    spots.push(spot);
    const beam = bin.mesh(
      new THREE.CylinderGeometry(0.2, 2.4, 10, 10, 1, true),
      new THREE.MeshBasicMaterial({
        color: golden ? 0xfde047 : 0xfef9c3,
        transparent: true,
        opacity: 0.08,
        depthWrite: false,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending,
      })
    );
    beam.position.set(x * 0.55, 10, z * 0.55);
    beam.name = "flood-beam";
    fallback.add(beam);
  });
  const crowdMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.7 });
  const crowd = new THREE.InstancedMesh(new THREE.CapsuleGeometry(0.22, 0.35, 2, 4), crowdMat, quality.crowd);
  bin.track(crowd.geometry);
  bin.track(crowdMat);
  const dummy = new THREE.Object3D();
  const color = new THREE.Color();
  const palette = golden ? [0xfbbf24, 0xf8fafc, 0xf59e0b, 0xfef3c7] : [0x1d4ed8, 0xf8fafc, 0xfacc15, 0xe2e8f0];
  for (let i = 0; i < quality.crowd; i++) {
    const side = i % 2 === 0 ? -1 : 1;
    const angle = (i / quality.crowd) * Math.PI * 2;
    const radius = 33 + (i % 5) * 1.2;
    dummy.position.set(Math.cos(angle) * radius, 1.1 + (i % 5) * 0.9, Math.sin(angle) * radius * 0.74);
    dummy.rotation.y = side > 0 ? Math.PI : 0;
    dummy.updateMatrix();
    crowd.setMatrixAt(i, dummy.matrix);
    color.setHex(palette[i % palette.length]);
    crowd.setColorAt(i, color);
  }
  if (crowd.instanceColor) crowd.instanceColor.needsUpdate = true;
  crowd.name = "stadium-crowd";
  fallback.add(crowd);
  const nearGoal = addGoal(bin, 22);
  const farGoal = addGoal(bin, -22);
  fallback.add(nearGoal, farGoal);
  const paint = new THREE.MeshBasicMaterial({ color: 0xf8fafc });
  bin.track(paint);
  const marking = (x: number, z: number, w: number, d: number) => {
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, d), paint);
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.set(x, 0.04, z);
    fallback.add(mesh);
    bin.track(mesh.geometry);
  };
  marking(0, 16.2, 48, 0.12);
  marking(0, -16.2, 48, 0.12);
  marking(23.4, 0, 0.12, 32);
  marking(-23.4, 0, 0.12, 32);
  marking(0, 0, 0.12, 32);
  addMotes(bin, Math.floor(quality.particles * 0.5), golden ? 0xfde68a : 0xfef9c3, 30, 10);
  return spots;
}

function buildRunway(bin: SceneBin): THREE.Group {
  bin.root.add(skyDome(0x070b16, 0x1e293b, 0x111827));
  bin.root.add(new THREE.HemisphereLight(0xe2e8f0, 0x0f172a, 0.4));
  const key = new THREE.DirectionalLight(0xf8fafc, 1.5);
  key.position.set(12, 18, 10);
  bin.root.add(key);
  const asphalt = bin.mesh(
    new THREE.BoxGeometry(90, 0.12, 10),
    new THREE.MeshStandardMaterial({ color: 0x1f2937, roughness: 0.92 })
  );
  asphalt.position.set(4, 0.06, 0);
  asphalt.name = "runway";
  const paint = new THREE.MeshBasicMaterial({ color: 0xf8fafc });
  bin.track(paint);
  for (let i = 0; i < 14; i++) {
    const dash = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.04, 0.28), paint);
    dash.position.set(-28 + i * 5, 0.14, 0);
    bin.root.add(dash);
    bin.track(dash.geometry);
  }
  const lampGeo = new THREE.SphereGeometry(0.12, 8, 8);
  const warm = new THREE.MeshBasicMaterial({ color: 0xfbbf24 });
  const cool = new THREE.MeshBasicMaterial({ color: 0xe0f2fe });
  bin.track(lampGeo);
  bin.track(warm);
  bin.track(cool);
  for (let i = 0; i < 18; i++) {
    const left = new THREE.Mesh(lampGeo, i % 4 === 0 ? cool : warm);
    left.position.set(-32 + i * 4, 0.2, -5.2);
    const right = left.clone();
    right.position.z = 5.2;
    bin.root.add(left);
    bin.root.add(right);
  }
  const terminal = bin.mesh(
    new THREE.BoxGeometry(16, 5, 8),
    new THREE.MeshStandardMaterial({
      color: 0x334155,
      metalness: 0.45,
      roughness: 0.25,
      emissive: 0x38bdf8,
      emissiveIntensity: 0.15,
    })
  );
  terminal.position.set(-30, 2.5, 16);
  const aircraft = new THREE.Group();
  aircraft.name = "gift-aircraft";
  bin.root.add(aircraft);
  return aircraft;
}

function buildOcean(bin: SceneBin): { water: THREE.ShaderMaterial; yacht: THREE.Group; wake: THREE.Mesh } {
  bin.root.add(skyDome(0x1e3a5f, 0xf0a05a, 0x0c4a6e));
  bin.root.add(new THREE.HemisphereLight(0xffedd5, 0x0c4a6e, 0.7));
  const sun = new THREE.DirectionalLight(0xffb15a, 2.4);
  sun.position.set(-30, 12, 18);
  bin.root.add(sun);
  const sunDisc = bin.mesh(
    new THREE.SphereGeometry(2.2, 16, 16),
    new THREE.MeshBasicMaterial({ color: 0xffd7a1 })
  );
  sunDisc.position.set(-40, 7, 24);
  const geometry = new THREE.PlaneGeometry(180, 180, 70, 70);
  geometry.rotateX(-Math.PI / 2);
  const material = new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 } },
    vertexShader: `
      uniform float uTime;
      varying vec3 vPos;
      void main() {
        vec3 displaced = position;
        displaced.y += sin(position.x * 0.22 + uTime * 1.3) * 0.22 + cos(position.z * 0.18 - uTime * 0.9) * 0.16;
        vPos = displaced;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(displaced, 1.0);
      }
    `,
    fragmentShader: `
      varying vec3 vPos;
      void main() {
        float spark = pow(max(sin(vPos.x * 0.35 + vPos.z * 0.12), 0.0), 12.0);
        vec3 deep = vec3(0.02, 0.22, 0.38);
        vec3 mid = vec3(0.05, 0.45, 0.58);
        vec3 color = mix(deep, mid, 0.45);
        color += vec3(1.0, 0.62, 0.32) * spark * 0.9;
        gl_FragColor = vec4(color, 1.0);
      }
    `,
  });
  const water = new THREE.Mesh(geometry, material);
  water.name = "ocean";
  bin.track(geometry);
  bin.track(material);
  bin.root.add(water);
  const wake = bin.mesh(
    new THREE.PlaneGeometry(16, 3.2),
    new THREE.MeshBasicMaterial({ color: 0xf8fafc, transparent: true, opacity: 0.35, depthWrite: false })
  );
  wake.rotation.x = -Math.PI / 2;
  wake.position.set(-8, 0.2, 0);
  const yacht = new THREE.Group();
  yacht.name = "gift-yacht";
  bin.root.add(yacht);
  return { water: material, yacht, wake };
}

function buildTrophyStage(bin: SceneBin, quality: GiftQuality, ballon: boolean): THREE.Group {
  bin.root.add(skyDome(0x07060b, 0x1c140c, 0x05040a));
  bin.root.add(new THREE.HemisphereLight(0xfef3c7, 0x0c0a09, 0.2));
  const spot = new THREE.SpotLight(0xfff1c9, ballon ? 18 : 10, 24, 0.42, 0.45, 1);
  spot.position.set(0.4, 7.5, 1.6);
  spot.target.position.set(0, 1.2, 0);
  spot.castShadow = true;
  bin.root.add(spot);
  bin.root.add(spot.target);
  const floor = bin.mesh(
    new THREE.CircleGeometry(4.2, 40),
    new THREE.MeshStandardMaterial({ color: 0x11100e, metalness: 0.72, roughness: 0.28 })
  );
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  const plinth = new THREE.Group();
  plinth.name = ballon ? "ballon-dor-stage" : "trophy-stage";
  const stone = new THREE.MeshStandardMaterial({ color: 0x1c1917, metalness: 0.25, roughness: 0.45 });
  const gold = new THREE.MeshPhysicalMaterial({
    color: 0xffd978,
    metalness: 1,
    roughness: 0.2,
    clearcoat: 0.45,
    emissive: 0x8a5a12,
    emissiveIntensity: 0.12,
  });
  bin.track(stone);
  bin.track(gold);
  const step = new THREE.Mesh(new THREE.CylinderGeometry(1.35, 1.55, 0.28, 28), stone);
  step.position.y = 0.14;
  const drum = new THREE.Mesh(new THREE.CylinderGeometry(0.72, 0.84, 0.7, 24), stone);
  drum.position.y = 0.62;
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.78, 0.045, 10, 28), gold);
  ring.rotation.x = Math.PI / 2;
  ring.position.y = 0.98;
  plinth.add(step, drum, ring);
  bin.track(step.geometry);
  bin.track(drum.geometry);
  bin.track(ring.geometry);
  const award = new THREE.Group();
  award.name = ballon ? "ballon-dor-award" : "trophy-cup";
  award.position.y = ballon ? 1.28 : 1.15;
  if (!ballon) {
    const cup = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.22, 0.7, 20), gold);
    cup.castShadow = true;
    award.add(cup);
    bin.track(cup.geometry);
  }
  plinth.add(award);
  bin.root.add(plinth);
  addMotes(bin, quality.particles, 0xfbbf24, 3.2, 3.5);
  return award;
}

function pitchLines(bin: SceneBin, length: number, width: number): void {
  const paint = new THREE.MeshBasicMaterial({ color: 0xf8fafc });
  bin.track(paint);
  const line = (x: number, z: number, w: number, d: number) => {
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, d), paint);
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.set(x, 0.03, z);
    bin.root.add(mesh);
    bin.track(mesh.geometry);
  };
  line(0, width / 2 - 0.4, length, 0.08);
  line(0, -width / 2 + 0.4, length, 0.08);
  line(length / 2 - 0.4, 0, 0.08, width);
  line(-length / 2 + 0.4, 0, 0.08, width);
  line(0, 0, 0.08, width);
  const circle = new THREE.Mesh(new THREE.RingGeometry(1.55, 1.68, 40), paint);
  circle.rotation.x = -Math.PI / 2;
  circle.position.y = 0.03;
  bin.root.add(circle);
  bin.track(circle.geometry);
}

function addGoal(bin: SceneBin, x: number): THREE.Group {
  const goal = new THREE.Group();
  goal.name = "match-goal";
  goal.position.set(x, 0, 0);
  const white = new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.32, metalness: 0.12 });
  bin.track(white);
  [-3.66, 3.66].forEach((z) => {
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 2.44, 10), white);
    post.position.set(0, 1.22, z);
    goal.add(post);
    bin.track(post.geometry);
  });
  const bar = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 7.32, 10), white);
  bar.rotation.x = Math.PI / 2;
  bar.position.y = 2.44;
  goal.add(bar);
  bin.track(bar.geometry);
  const netMat = new THREE.MeshBasicMaterial({
    color: 0xe2e8f0,
    transparent: true,
    opacity: 0.28,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
  const net = new THREE.Mesh(new THREE.PlaneGeometry(7.32, 2.44, 8, 4), netMat);
  net.position.set(1.35, 1.22, 0);
  net.name = "goal-net";
  goal.add(net);
  bin.track(net.geometry);
  bin.track(netMat);
  bin.root.add(goal);
  return goal;
}

function addStands(bin: SceneBin, length: number, width: number, count: number, wave: boolean): THREE.InstancedMesh {
  const concrete = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.84 });
  const north = bin.mesh(new THREE.BoxGeometry(length, 4.2, 3), concrete);
  north.position.set(0, 2.1, -width / 2 - 2);
  const south = bin.mesh(new THREE.BoxGeometry(length, 4.2, 3), concrete);
  south.position.set(0, 2.1, width / 2 + 2);
  const body = new THREE.CapsuleGeometry(0.16, 0.28, 2, 4);
  const kit = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.65 });
  const crowd = new THREE.InstancedMesh(body, kit, count);
  bin.track(body);
  bin.track(kit);
  const dummy = new THREE.Object3D();
  const color = new THREE.Color();
  const palette = [0xdc2626, 0x1d4ed8, 0xf8fafc, 0xf59e0b, 0x0f172a];
  for (let i = 0; i < count; i++) {
    const side = i % 2 === 0 ? -1 : 1;
    dummy.position.set(-length / 2 + (i * 1.1) % length, 1.15 + (i % 5) * 0.42, side * (width / 2 + 1.1 + (i % 5) * 0.28));
    dummy.updateMatrix();
    crowd.setMatrixAt(i, dummy.matrix);
    color.setHex(palette[i % palette.length]);
    crowd.setColorAt(i, color);
  }
  if (crowd.instanceColor) crowd.instanceColor.needsUpdate = true;
  crowd.name = wave ? "winner-crowd" : "match-crowd";
  crowd.userData.wave = wave;
  bin.root.add(crowd);
  return crowd;
}

function clockBoard(bin: SceneBin, width: number): void {
  const canvas = typeof document !== "undefined" ? document.createElement("canvas") : null;
  const material = new THREE.MeshBasicMaterial({ color: 0xff2d3a });
  if (canvas) {
    canvas.width = 256;
    canvas.height = 96;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.fillStyle = "#1a0a0d";
      ctx.fillRect(0, 0, 256, 96);
      ctx.fillStyle = "#ff3142";
      ctx.font = "700 62px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("90+4", 128, 50);
      const texture = new THREE.CanvasTexture(canvas);
      texture.colorSpace = THREE.SRGBColorSpace;
      material.map = texture;
      material.color.set(0xffffff);
      bin.track(texture);
    }
  }
  const board = new THREE.Mesh(new THREE.PlaneGeometry(4.4, 1.7), material);
  board.position.set(0, 5.4, -width / 2 - 2.05);
  board.name = "winner-clock";
  bin.track(board.geometry);
  bin.track(material);
  bin.root.add(board);
}

interface RigHandle {
  mixer: THREE.AnimationMixer;
  actions: Record<string, THREE.AnimationAction | undefined>;
  pivot: THREE.Group;
  feet: () => THREE.Vector3;
}

let sharedKit: Promise<{ template: THREE.Object3D; clips: Map<string, THREE.AnimationClip> }> | null = null;

function loadSharedKit(resolveUrl: (path: string) => string) {
  if (!sharedKit) {
    sharedKit = (async () => {
      const cache = AssetStreamingCache.getInstance();
      const [kit, anim] = await Promise.all([cache.loadGltf(resolveUrl(KIT_URL)), cache.loadGltf(resolveUrl(CLIP_URL))]);
      const clips = new Map<string, THREE.AnimationClip>();
      for (const clip of anim?.animations || []) clips.set(clip.name, clip);
      return { template: kit.scene, clips };
    })().catch((error) => {
      sharedKit = null;
      throw error;
    });
  }
  return sharedKit;
}

function clipForRig(clip: THREE.AnimationClip): THREE.AnimationClip {
  const tracks = clip.tracks.filter((track) => !track.name.startsWith("mixamorigHips."));
  return new THREE.AnimationClip(clip.name, clip.duration, tracks);
}

function spawnPlayer(template: THREE.Object3D, clips: Map<string, THREE.AnimationClip>, names: string[]): { pivot: THREE.Group; rig: RigHandle } {
  const visual = cloneSkinned(template);
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
    const action = mixer.clipAction(clipForRig(source));
    action.clampWhenFinished = true;
    action.loop = name === RUN_CLIP || name === SPIN_CLIP ? THREE.LoopRepeat : THREE.LoopOnce;
    actions[name] = action;
  });
  const foot = new THREE.Vector3();
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
          bone.getWorldPosition(foot);
          if (foot.y > bestY) {
            bestY = foot.y;
            best.copy(foot);
          }
        });
        return best;
      },
    },
  };
}

function fallbackPlayer(bin: SceneBin, pose: "stand" | "kick" = "stand"): THREE.Group {
  const group = new THREE.Group();
  group.name = "gift-player-standin";
  const kit = new THREE.MeshStandardMaterial({ color: 0x0f766e, roughness: 0.5 });
  const skin = new THREE.MeshStandardMaterial({ color: 0xd2a679, roughness: 0.62 });
  bin.track(kit);
  bin.track(skin);
  if (pose === "kick") {
    const torso = bin.mesh(new THREE.CapsuleGeometry(0.2, 0.5, 4, 8), kit, group);
    torso.rotation.z = Math.PI / 2;
    torso.position.set(0.05, 1.28, 0);
    const head = bin.mesh(new THREE.SphereGeometry(0.16, 12, 12), skin, group);
    head.position.set(0.58, 1.28, 0);
    const striking = bin.mesh(new THREE.CapsuleGeometry(0.08, 0.52, 3, 6), kit, group);
    striking.position.set(-0.08, 1.9, 0.02);
    const plant = bin.mesh(new THREE.CapsuleGeometry(0.08, 0.48, 3, 6), kit, group);
    plant.rotation.z = 0.9;
    plant.position.set(-0.42, 1.02, -0.08);
    return group;
  }
  const torso = bin.mesh(new THREE.CapsuleGeometry(0.22, 0.55, 4, 8), kit, group);
  torso.position.y = 1.15;
  const head = bin.mesh(new THREE.SphereGeometry(0.16, 12, 12), skin, group);
  head.position.y = 1.72;
  const leg = bin.mesh(new THREE.CapsuleGeometry(0.08, 0.55, 3, 6), kit, group);
  leg.position.set(0.12, 0.55, 0.15);
  leg.rotation.x = 0.5;
  return group;
}

function makeMatchBall(bin: SceneBin, gold: boolean, parent: THREE.Object3D = bin.root): THREE.Mesh {
  const ball = bin.mesh(
    new THREE.SphereGeometry(0.22, 18, 14),
    gold
      ? new THREE.MeshPhysicalMaterial({ color: 0xffd978, metalness: 1, roughness: 0.22 })
      : new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.42 }),
    parent
  );
  ball.name = "gift-ball";
  ball.castShadow = true;
  if (gold) {
    const seams = new THREE.Mesh(
      new THREE.IcosahedronGeometry(0.236, 0),
      new THREE.MeshBasicMaterial({ color: 0x6b3a09, wireframe: true })
    );
    seams.name = "ball-seams";
    ball.add(seams);
    bin.track(seams.geometry);
    bin.track(seams.material as THREE.Material);
  }
  return ball;
}

async function dressBall(ball: THREE.Mesh, options: DirectorOptions, gold: boolean): Promise<void> {
  if (!options.canStream) return;
  try {
    const gltf = await AssetStreamingCache.getInstance().loadGltf(options.resolveUrl(BALL_URL));
    if (options.isCancelled() || !gltf?.scene) return;
    const imported = gltf.scene;
    imported.traverse((child) => {
      const mesh = child as THREE.Mesh;
      if (!mesh.isMesh) return;
      if (/deflated/i.test(mesh.name) || /deflated/i.test(child.parent?.name || "")) mesh.visible = false;
      if (!gold) return;
      const source = mesh.material as THREE.MeshStandardMaterial;
      mesh.material = new THREE.MeshPhysicalMaterial({
        color: 0xffd978,
        metalness: 1,
        roughness: 0.18,
        clearcoat: 0.5,
        emissive: 0x8a5a12,
        emissiveIntensity: 0.16,
        normalMap: source?.normalMap || null,
        envMapIntensity: 1.15,
      });
    });
    centerOnOrigin(imported, gold ? 1.05 : 0.44);
    const parentScale = (ball.scale.x || 1);
    imported.scale.multiplyScalar(1 / parentScale);
    const material = ball.material as THREE.Material;
    material.visible = false;
    const seams = ball.getObjectByName("ball-seams");
    if (seams) seams.visible = false;
    ball.add(imported);
  } catch {
    // The sphere stays in frame.
  }
}

function finish(options: DirectorOptions, bin: SceneBin, background: number, exposure: number, update: GiftDirector["update"]): GiftDirector {
  return {
    root: bin.root,
    background: new THREE.Color(background),
    exposure,
    update,
    dispose: () => bin.dispose(),
  };
}

export function createGiftDirector(options: DirectorOptions): GiftDirector {
  const bin = new SceneBin();
  const fovBoost = options.quality.tier === "low" ? 8 : 0;
  const code = options.giftCode.toLowerCase();
  const shot = options.shot;

  const play = (camera: THREE.PerspectiveCamera, progress: number, hero?: [number, number, number]) => {
    applyFrame(camera, frameGiftShot(shot, progress, hero, code), fovBoost);
  };

  if (shot === "city") {
    const paris = buildParis(bin, options.quality);
    options.onReady();
    return finish(options, bin, 0x07101f, 1.15, (progress, delta, camera) => {
      play(camera, progress);
      const beacon = paris.beacon?.material as THREE.MeshBasicMaterial | undefined;
      if (beacon) beacon.color.setScalar(0.7 + Math.sin(progress * 24) * 0.3);
      const motes = bin.root.getObjectByName("gift-motes") as THREE.Points | null;
      if (motes) driftMotes(motes, delta, 0.35);
    });
  }

  if (shot === "stadium") {
    const golden = code.includes("golden");
    const spots = buildStadiumBase(bin, golden, options.quality);
    const lamps: THREE.MeshStandardMaterial[] = [];
    attachStadium(bin, options, golden, lamps).finally(() => {
      if (!options.isCancelled()) options.onReady();
    });
    const fireworks: THREE.Mesh[] = [];
    if (golden) {
      for (let i = 0; i < 8; i++) {
        const puff = bin.mesh(
          new THREE.SphereGeometry(0.45, 8, 8),
          new THREE.MeshBasicMaterial({ color: i % 2 ? 0xfff7d6 : 0xf59e0b, transparent: true, opacity: 0 })
        );
        puff.position.set((i - 3.5) * 6, 14, (i % 2) * 8 - 4);
        fireworks.push(puff);
      }
    }
    return finish(options, bin, golden ? 0x140c04 : 0x07111f, golden ? 1.28 : 1.05, (progress, _delta, camera) => {
      play(camera, progress);
      const power = smooth(clamp01((progress - 0.12) / 0.45));
      spots.forEach((spot) => {
        spot.intensity = power * (golden ? 22 : 12);
      });
      lamps.forEach((material) => {
        material.emissiveIntensity = power * (golden ? 1.4 : 0.8);
      });
      bin.root.traverse((child) => {
        if (child.name !== "flood-beam") return;
        const material = (child as THREE.Mesh).material as THREE.MeshBasicMaterial;
        material.opacity = 0.04 + power * (golden ? 0.22 : 0.12);
      });
      fireworks.forEach((puff, index) => {
        const local = clamp01((progress - 0.58 - index * 0.035) / 0.28);
        puff.scale.setScalar(0.3 + local * 5);
        (puff.material as THREE.MeshBasicMaterial).opacity = (1 - local) * 0.75;
      });
    });
  }

  if (shot === "jet") {
    const aircraft = buildRunway(bin);
    const exhaust = bin.mesh(
      new THREE.ConeGeometry(0.35, 2.4, 10),
      new THREE.MeshBasicMaterial({ color: 0xbfdbfe, transparent: true, opacity: 0.0, depthWrite: false })
    );
    exhaust.rotation.z = Math.PI / 2;
    aircraft.add(exhaust);
    if (options.canStream) {
      AssetStreamingCache.getInstance()
        .loadGltf(options.resolveUrl(JET_URL))
        .then((gltf) => {
          if (options.isCancelled() || !gltf?.scene) return;
          const imported = gltf.scene;
          groundFit(imported, 16, true);
          revealImported(imported);
          aircraft.add(imported);
          bin.unique.push(imported);
        })
        .catch((error) => {
          console.error("gift model load failed", error);
        })
        .finally(() => {
          if (!options.isCancelled()) options.onReady();
        });
    } else options.onReady();
    return finish(options, bin, 0x070b16, 1.12, (progress, _delta, camera) => {
      const glide = smooth(clamp01((progress - 0.08) / 0.9));
      const lift = smooth(clamp01((progress - 0.58) / 0.42));
      aircraft.position.set(lerp(-26, 32, glide), lift * lift * 9, 0);
      aircraft.rotation.z = lift * 0.38;
      exhaust.position.set(-8, 0.4, 0);
      (exhaust.material as THREE.MeshBasicMaterial).opacity = lift * 0.65;
      play(camera, progress, [aircraft.position.x, aircraft.position.y, aircraft.position.z]);
    });
  }

  if (shot === "yacht") {
    const ocean = buildOcean(bin);
    if (options.canStream) {
      AssetStreamingCache.getInstance()
        .loadGltf(options.resolveUrl(YACHT_URL))
        .then((gltf) => {
          if (options.isCancelled() || !gltf?.scene) return;
          const imported = gltf.scene;
          groundFit(imported, 22, true);
          revealImported(imported);
          imported.position.y += 0.35;
          ocean.yacht.add(imported);
          bin.unique.push(imported);
        })
        .catch((error) => {
          console.error("gift model load failed", error);
        })
        .finally(() => {
          if (!options.isCancelled()) options.onReady();
        });
    } else options.onReady();
    let elapsed = 0;
    return finish(options, bin, 0x1e3a5f, 1.18, (progress, delta, camera) => {
      elapsed += delta;
      ocean.water.uniforms.uTime.value = elapsed;
      const sway = Math.sin(elapsed * 1.3);
      ocean.yacht.position.y = sway * 0.18;
      ocean.yacht.rotation.z = sway * 0.04;
      ocean.yacht.position.x = lerp(-2, 4, smooth(progress));
      ocean.wake.position.x = ocean.yacht.position.x - 10;
      play(camera, progress);
    });
  }

  if (shot === "trophy" || shot === "boot" || shot === "glove" || shot === "crown" || shot === "card" || shot === "tactics") {
    const award = buildTrophyStage(bin, options.quality, shot === "trophy");
    if (shot === "trophy") {
      const ball = makeMatchBall(bin, true, award);
      ball.scale.setScalar(2.6);
      ball.position.set(0, 0.2, 0);
      ball.name = "ballon-dor-ball";
      void dressBall(ball, options, true).finally(() => {
        if (!options.isCancelled()) options.onReady();
      });
    } else options.onReady();
    return finish(options, bin, 0x07060b, shot === "trophy" ? 1.2 : 1.05, (progress, delta, camera) => {
      play(camera, progress);
      const pedestal = bin.root.getObjectByName("ballon-dor-stage") || bin.root.getObjectByName("trophy-stage");
      if (pedestal) pedestal.position.y = lerp(-1.3, 0, smooth(Math.min(1, progress / 0.28)));
      const ball = bin.root.getObjectByName("ballon-dor-ball");
      if (ball) ball.rotation.y = progress * Math.PI;
      const motes = bin.root.getObjectByName("gift-motes") as THREE.Points | null;
      if (motes) driftMotes(motes, delta, 0.25);
    });
  }

  const winner = shot === "last_minute";
  const bicycle = shot === "bicycle";
  const length = 36;
  const width = 24;
  bin.root.add(skyDome(0x07111f, 0x1e3a5f, 0x052e16));
  bin.root.add(new THREE.HemisphereLight(0xdbeafe, 0x052e16, 0.45));
  const flood = new THREE.DirectionalLight(0xfff7d6, 1.6);
  flood.position.set(-8, 18, 10);
  bin.root.add(flood);
  const grass = bin.mesh(
    new THREE.PlaneGeometry(length, width),
    new THREE.MeshStandardMaterial({ color: 0x0f7a3a, roughness: 0.9 })
  );
  grass.rotation.x = -Math.PI / 2;
  grass.receiveShadow = true;
  grass.name = bicycle ? "bicycle-pitch" : winner ? "winner-pitch" : "match-pitch";
  pitchLines(bin, length, width);
  const goal = addGoal(bin, length / 2 - 1.2);
  const crowd = addStands(bin, length, width, options.quality.crowd, winner);
  if (winner) clockBoard(bin, width);
  const ball = makeMatchBall(bin, shot === "golden_goal");
  const player = new THREE.Group();
  player.name = "gift-player";
  bin.root.add(player);
  const celebrant = new THREE.Group();
  celebrant.name = "gift-celebrant";
  celebrant.visible = false;
  bin.root.add(celebrant);
  let kicker: RigHandle | null = null;
  let dancer: RigHandle | null = null;
  let kicked = false;
  const standIn = fallbackPlayer(bin, bicycle ? "kick" : "stand");
  player.add(standIn);
  if (!options.canStream) {
    options.onReady();
  } else {
    loadSharedKit(options.resolveUrl)
      .then((shared) => {
        if (options.isCancelled()) return;
        const spawned = spawnPlayer(shared.template, shared.clips, bicycle ? [SCISSOR_CLIP] : [RUN_CLIP, PENALTY_CLIP]);
        player.remove(standIn);
        player.add(spawned.pivot);
        kicker = spawned.rig;
        const run = kicker.actions[bicycle ? SCISSOR_CLIP : RUN_CLIP];
        run?.reset().play();
        if (winner) {
          const dance = spawnPlayer(shared.template, shared.clips, [SPIN_CLIP]);
          celebrant.add(dance.pivot);
          dancer = dance.rig;
        }
      })
      .catch((error) => {
        console.error("gift footballer load failed", error);
      })
      .finally(() => {
        if (!options.isCancelled()) options.onReady();
      });
    void dressBall(ball, options, shot === "golden_goal");
  }

  const release = new THREE.Vector3(0.4, 1.5, 0.2);
  return finish(options, bin, 0x07111f, 1.1, (progress, delta, camera) => {
    play(camera, progress);
    kicker?.mixer.update(delta);
    dancer?.mixer.update(delta);
    if (bicycle) {
      const lean = progress < 0.22 ? 0 : progress < 0.48 ? smooth((progress - 0.22) / 0.26) : 1 - smooth((progress - 0.48) / 0.2);
      const tilt = -2.35 * clamp01(lean);
      if (kicker?.pivot) kicker.pivot.rotation.x = tilt;
      player.position.set(0, 0, 0);
      const foot = kicker?.feet() || v3([0.2, 1.4, 0.2]);
      if (progress < 0.3) {
        const u = smooth(progress / 0.3);
        ball.position.set(lerp(-1.2, foot.x, u), lerp(2.1, Math.max(foot.y, 0.4), u), lerp(4.5, foot.z, u));
      } else if (progress < 0.5) {
        ball.position.lerp(foot, 0.45);
        release.copy(ball.position);
      } else {
        const u = smooth((progress - 0.5) / 0.32);
        ball.position.set(lerp(release.x, goal.position.x - 0.2, u), lerp(release.y, 2.15, u), lerp(release.z, -2.1, u));
      }
    } else if (winner) {
      const approach = smooth(Math.min(1, progress / 0.48));
      player.position.set(lerp(-12, -1.5, approach), 0, lerp(1.2, 0.2, approach));
      if (progress > 0.48 && !kicked) {
        kicked = true;
        kicker?.actions[RUN_CLIP]?.fadeOut(0.12);
        kicker?.actions[PENALTY_CLIP]?.reset().fadeIn(0.1).play();
      }
      if (progress < 0.5) {
        ball.position.set(player.position.x + 0.45, 0.24, player.position.z);
        release.copy(ball.position);
      } else {
        const u = smooth((progress - 0.5) / 0.28);
        ball.position.set(lerp(release.x, goal.position.x - 0.15, u), lerp(0.24, 0.85, u) + Math.sin(u * Math.PI) * 0.7, lerp(release.z, 1.4, u));
      }
      if (progress > 0.72) {
        celebrant.visible = true;
        celebrant.position.set(player.position.x - 1.1, 0, 1.3);
        if (dancer && !dancer.actions[SPIN_CLIP]?.isRunning()) dancer.actions[SPIN_CLIP]?.reset().play();
      }
    } else {
      const u = smooth(Math.min(1, progress / 0.7));
      ball.position.set(lerp(-8, goal.position.x, u), 0.8 + Math.sin(u * Math.PI) * 2.2, lerp(2, 0, u));
      player.position.set(lerp(-6, -1, u), 0, 0);
    }
    const net = goal.getObjectByName("goal-net") as THREE.Mesh | null;
    if (net) {
      const hit = ball.position.x > goal.position.x - 1.5 ? 1 : 0;
      net.scale.z = 1;
      net.position.x = 1.35 + hit * 0.45;
    }
    if (crowd.userData.wave) {
      const dummy = new THREE.Object3D();
      for (let i = 0; i < crowd.count; i++) {
        crowd.getMatrixAt(i, dummy.matrix);
        dummy.matrix.decompose(dummy.position, dummy.quaternion, dummy.scale);
        const base = 1.15 + (i % 5) * 0.42;
        dummy.position.y = base + Math.max(0, Math.sin(dummy.position.x * 0.35 + progress * 14)) * smooth(clamp01((progress - 0.55) / 0.2)) * 0.45;
        dummy.updateMatrix();
        crowd.setMatrixAt(i, dummy.matrix);
      }
      crowd.instanceMatrix.needsUpdate = true;
    }
    ball.rotation.x += delta * 6;
  });
}
