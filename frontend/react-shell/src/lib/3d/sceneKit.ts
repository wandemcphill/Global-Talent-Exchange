/**
 * Shared stadium, campus, and ceremony assembly for GTEX presentation scenes.
 * Each scene kind supplies its own models, camera, and lighting. Callers do not share one shot.
 */

import * as THREE from "three";
import { AssetStreamingCache } from "./broadcast/AssetStreamingCache";
import { StadiumEnvironmentLighting } from "./broadcast/StadiumEnvironmentLighting";
import type { GtexSceneController, GtexWebGLContext } from "./GtexWebGLHost";

/** CC0 Innerscene bowl, real-world metres. The live match keeps its own broadcast stadium. */
export const STADIUM_GLB = "/models/presentation/cc0_football_stadium.glb";
/** CC0 3DAssets club ground: marked pitch, stands, and training pieces at human scale. */
export const CLUB_GROUND_GLB = "/models/presentation/cc0_club_ground.glb";
export const TRAINING_CORNER_GLB = "/models/presentation/cc0_training_corner.glb";
export const CLUB_HQ_GLB = "/models/campus/club_hq.glb";
export const ACADEMY_GLB = "/models/campus/elite_academy_complex.glb";
export const YOUTH_PITCH_GLB = "/models/campus/academy_youth_pitch.glb";
export const TRAINING_PITCH_GLB = "/models/campus/training_pitch.glb";
export const TROPHY_GLB = "/assets/showroom/trophy_plinth.glb";
export const KIT_GLB = "/models/footballer/gtex_gt_mixamo_kit.glb";
export const KIT_CLIPS_GLB = "/models/footballer/gtex_mixamo_clips.glb";

export type PresentationKind =
  | "takeover"
  | "campus"
  | "walkout"
  | "academy"
  | "ceremony"
  | "gala"
  | "sponsorship";

export interface PresentationIdentity {
  clubName: string;
  primaryColor?: string;
  secondaryColor?: string;
  crestUrl?: string;
  subjectLabel?: string;
  sponsorName?: string;
  shot?: string;
}

interface CameraKey {
  t: number;
  position: [number, number, number];
  target: [number, number, number];
}

export function paintIdentityBoard(options: {
  clubName: string;
  headline?: string;
  primary?: string;
  secondary?: string;
  width?: number;
  height?: number;
}): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  const width = options.width || 1024;
  const height = options.height || 256;
  canvas.width = width;
  canvas.height = height;
  canvas.setAttribute("data-club-name", options.clubName || "GTEX");
  if (typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent || "")) return canvas;
  const g = canvas.getContext("2d");
  if (!g) return canvas;
  g.fillStyle = "#0c3f36";
  g.fillRect(0, 0, width, height);
  g.fillStyle = options.primary || "#0f766e";
  g.fillRect(0, 0, 18, height);
  g.fillStyle = options.secondary || "#d4a24c";
  g.fillRect(18, 0, 8, height);
  g.fillRect(0, height - 10, width, 10);
  g.fillStyle = "#f8fafc";
  g.font = "700 68px sans-serif";
  const title = (options.clubName || "GTEX").slice(0, 28);
  g.fillText(title, 48, 118);
  g.font = "500 28px sans-serif";
  g.fillStyle = options.secondary || "#d4a24c";
  g.fillText(options.headline || "THE CLUB IS YOURS", 48, 176);
  return canvas;
}

export function drawCrestOnBoard(
  canvas: HTMLCanvasElement,
  crestUrl: string | undefined,
  texture?: THREE.CanvasTexture
): void {
  if (!crestUrl || typeof Image === "undefined") return;
  const image = new Image();
  image.crossOrigin = "anonymous";
  image.onload = () => {
    const g = canvas.getContext("2d");
    if (!g) return;
    g.drawImage(image, canvas.width - 188, 48, 140, 160);
    if (texture) texture.needsUpdate = true;
  };
  image.src = crestUrl;
}

export function frameObject(object: THREE.Object3D, targetSize: number): void {
  object.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(object);
  const size = box.getSize(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z, 0.001);
  object.scale.multiplyScalar(targetSize / maxDim);
  object.updateMatrixWorld(true);
  const fitted = new THREE.Box3().setFromObject(object);
  const center = fitted.getCenter(new THREE.Vector3());
  object.position.x -= center.x;
  object.position.z -= center.z;
  object.position.y -= fitted.min.y;
}

export async function loadFramedModel(
  url: string,
  renderer: THREE.WebGLRenderer,
  targetSize: number
): Promise<THREE.Group> {
  const gltf = await AssetStreamingCache.getInstance().loadGltf(url, renderer);
  const source = gltf?.scene;
  if (!source) throw new Error(`Empty glTF at ${url}`);
  const group = new THREE.Group();
  group.add(source);
  frameObject(group, targetSize);
  group.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (mesh.isMesh) {
      mesh.castShadow = false;
      mesh.receiveShadow = true;
    }
  });
  return group;
}

export async function loadPresentationFigure(
  renderer: THREE.WebGLRenderer
): Promise<{ object: THREE.Object3D; mixer: THREE.AnimationMixer | null }> {
  const cache = AssetStreamingCache.getInstance();
  const kit = await cache.loadGltf(KIT_GLB, renderer);
  let clips: { animations?: THREE.AnimationClip[] } = { animations: kit.animations };
  try {
    const clipFile = await cache.loadGltf(KIT_CLIPS_GLB, renderer);
    if (clipFile.animations?.length) clips = clipFile;
  } catch {
    // The kit file's own clips are enough for an idle presentation.
  }
  const { clone } = await import("three/examples/jsm/utils/SkeletonUtils.js");
  const object = clone(kit.scene) as THREE.Object3D;
  frameObject(object, 1.9);
  const mixer = new THREE.AnimationMixer(object);
  const clip = clips.animations?.[0];
  if (clip) mixer.clipAction(clip).play();
  return { object, mixer };
}

function sampleCamera(keys: CameraKey[], elapsed: number, camera: THREE.PerspectiveCamera): void {
  const duration = keys[keys.length - 1].t;
  const time = elapsed % duration;
  let index = 0;
  while (index < keys.length - 1 && keys[index + 1].t < time) index += 1;
  const from = keys[index];
  const to = keys[Math.min(index + 1, keys.length - 1)];
  const span = Math.max(0.001, to.t - from.t);
  const linear = THREE.MathUtils.clamp((time - from.t) / span, 0, 1);
  const eased = linear * linear * (3 - 2 * linear);
  camera.position.set(
    THREE.MathUtils.lerp(from.position[0], to.position[0], eased),
    THREE.MathUtils.lerp(from.position[1], to.position[1], eased),
    THREE.MathUtils.lerp(from.position[2], to.position[2], eased)
  );
  camera.lookAt(
    THREE.MathUtils.lerp(from.target[0], to.target[0], eased),
    THREE.MathUtils.lerp(from.target[1], to.target[1], eased),
    THREE.MathUtils.lerp(from.target[2], to.target[2], eased)
  );
}

function addNightRig(scene: THREE.Scene, qualityShadows: boolean, emerald: number, gold: number): void {
  scene.add(new THREE.HemisphereLight(0xb7c7d6, 0x10241c, 0.55));
  const key = new THREE.DirectionalLight(0xfff4e5, 1.35);
  key.position.set(40, 70, 24);
  key.castShadow = qualityShadows;
  if (qualityShadows) key.shadow.mapSize.set(1024, 1024);
  scene.add(key);
  const wash = new THREE.PointLight(emerald, 8, 80);
  wash.position.set(-18, 14, 16);
  scene.add(wash);
  const warm = new THREE.PointLight(gold, 6, 70);
  warm.position.set(22, 12, 10);
  scene.add(warm);
}

function boardMesh(canvas: HTMLCanvasElement, width: number, height: number): THREE.Mesh {
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(width, height),
    new THREE.MeshStandardMaterial({
      map: texture,
      emissive: new THREE.Color("#ffffff"),
      emissiveMap: texture,
      emissiveIntensity: 1,
      roughness: 0.4,
      metalness: 0.15,
    })
  );
  return mesh;
}

function humanScaleFog(kind: PresentationKind): number {
  if (kind === "academy") return 0.008;
  if (kind === "walkout" || kind === "gala" || kind === "ceremony" || kind === "sponsorship") return 0.012;
  return 0.0016;
}

function keysFor(kind: PresentationKind, shot?: string): CameraKey[] {
  if (kind === "campus") {
    return [
      { t: 0, position: [90, 42, 70], target: [0, 8, 0] },
      { t: 7, position: [20, 18, 78], target: [10, 6, 0] },
      { t: 14, position: [-36, 16, 48], target: [0, 8, 0] },
      { t: 20, position: [90, 42, 70], target: [0, 8, 0] },
    ];
  }
  if (kind === "walkout") {
    return [
      { t: 0, position: [0, 2.2, 16], target: [0, 1.6, 0] },
      { t: 6, position: [6, 3.4, 12], target: [0, 1.7, 2] },
      { t: 12, position: [0, 2.2, 16], target: [0, 1.6, 0] },
    ];
  }
  if (kind === "academy") {
    if (shot === "emergence") {
      return [
        { t: 0, position: [8, 2.4, 10], target: [0, 1.4, 0] },
        { t: 8, position: [3, 2.2, 7], target: [0, 1.5, 0] },
        { t: 14, position: [8, 2.4, 10], target: [0, 1.4, 0] },
      ];
    }
    if (shot === "bloodline") {
      return [
        { t: 0, position: [12, 6, 14], target: [0, 1.2, 0] },
        { t: 8, position: [-6, 4, 12], target: [0, 1.2, 0] },
        { t: 14, position: [12, 6, 14], target: [0, 1.2, 0] },
      ];
    }
    return [
      { t: 0, position: [40, 22, 36], target: [0, 4, 0] },
      { t: 8, position: [-24, 12, 28], target: [0, 3, 0] },
      { t: 16, position: [40, 22, 36], target: [0, 4, 0] },
    ];
  }
  if (kind === "gala") {
    return [
      { t: 0, position: [16, 6, 22], target: [0, 2.2, 0] },
      { t: 8, position: [4, 3.2, 12], target: [0, 2.4, 0] },
      { t: 14, position: [16, 6, 22], target: [0, 2.2, 0] },
    ];
  }
  if (kind === "ceremony") {
    return [
      { t: 0, position: [28, 14, 36], target: [0, 3, 0] },
      { t: 7, position: [8, 5, 16], target: [0, 2.5, 0] },
      { t: 14, position: [28, 14, 36], target: [0, 3, 0] },
    ];
  }
  if (kind === "sponsorship") {
    return [
      { t: 0, position: [24, 8, 22], target: [0, 4, 8] },
      { t: 6, position: [0, 5, 18], target: [0, 4, 6] },
      { t: 12, position: [24, 8, 22], target: [0, 4, 8] },
    ];
  }
  return [
    { t: 0, position: [0, 128, 206], target: [0, 16, 0] },
    { t: 14, position: [0, 128, 206], target: [0, 16, 0] },
    { t: 22, position: [36, 108, 176], target: [0, 18, 0] },
    { t: 30, position: [0, 128, 206], target: [0, 16, 0] },
  ];
}

export function createPresentationController(
  kind: PresentationKind,
  identity: PresentationIdentity
): GtexSceneController {
  const mixers: THREE.AnimationMixer[] = [];
  const keys = keysFor(kind, identity.shot);
  let camera: THREE.PerspectiveCamera | null = null;
  let nameBoard: THREE.Object3D | null = null;
  let lighting: StadiumEnvironmentLighting | null = null;

  return {
    async mount(ctx: GtexWebGLContext) {
      camera = ctx.camera;
      const primary = new THREE.Color(identity.primaryColor || "#0f766e");
      const secondary = new THREE.Color(identity.secondaryColor || "#d4a24c");
      const night = kind !== "academy";
      ctx.scene.background = new THREE.Color(kind === "gala" ? 0x07060d : night ? 0x07101a : 0x9eb4c4);
      ctx.scene.fog = new THREE.FogExp2(
        kind === "gala" ? 0x07060d : night ? 0x07101a : 0xb7c6d2,
        humanScaleFog(kind)
      );
      ctx.renderer.toneMappingExposure = kind === "gala" ? 1.05 : 1.28;
      addNightRig(ctx.scene, ctx.quality.shadowsEnabled, primary.getHex(), secondary.getHex());
      if (ctx.quality.tier !== "low") {
        lighting = new StadiumEnvironmentLighting(ctx.renderer, ctx.scene, ctx.quality.tier);
        void lighting.loadPolyHaven(
          night ? "/textures/env/modern_buildings_night_2k.hdr" : "/textures/env/kloofendal_43d_clear_puresky_2k.hdr",
          { background: false }
        );
      }
      if (kind === "academy") {
        const sun = ctx.scene.children.find((child) => child instanceof THREE.DirectionalLight) as THREE.DirectionalLight | undefined;
        if (sun) sun.intensity = 1.8;
      }
      if (kind === "gala") {
        ctx.renderer.toneMappingExposure = 1.05;
      }

      const humanScale = kind === "academy" || kind === "walkout";
      const required = humanScale ? (kind === "academy" && identity.shot ? TRAINING_CORNER_GLB : CLUB_GROUND_GLB) : STADIUM_GLB;
      const heroSize = humanScale ? 72 : 200;
      const hero = await loadFramedModel(required, ctx.renderer, heroSize);
      if (ctx.aborted()) return;
      ctx.scene.add(hero);

      const extras: Array<{ url: string; size: number; position: [number, number, number] }> = [];
      if (kind === "campus") {
        extras.push({ url: CLUB_HQ_GLB, size: 36, position: [150, 0, 30] });
      }
      if (kind === "academy") {
        extras.push({ url: YOUTH_PITCH_GLB, size: 36, position: [0, 0, 8] });
      }
      if (kind === "ceremony" || kind === "gala") {
        extras.push({ url: TROPHY_GLB, size: kind === "gala" ? 3.2 : 4.2, position: [0, 0, 6] });
      }
      if (kind === "walkout" || kind === "academy") {
        try {
          const figure = await loadPresentationFigure(ctx.renderer);
          if (!ctx.aborted()) {
            figure.object.position.set(0, 0, kind === "walkout" ? 4 : 2);
            ctx.scene.add(figure.object);
            if (figure.mixer) mixers.push(figure.mixer);
          }
        } catch {
          // A missing kit still leaves the ground.
        }
      }

      for (const extra of extras) {
        try {
          const model = await loadFramedModel(extra.url, ctx.renderer, extra.size);
          if (ctx.aborted()) return;
          model.position.set(extra.position[0], extra.position[1], extra.position[2]);
          ctx.scene.add(model);
        } catch {
          // Optional campus and trophy models must not blank the required environment.
        }
      }

      const headline =
        kind === "sponsorship"
          ? identity.sponsorName || identity.subjectLabel || "MATCHDAY PARTNER"
          : kind === "ceremony" || kind === "gala"
            ? identity.subjectLabel || "HONOURS NIGHT"
            : kind === "walkout"
              ? identity.subjectLabel || "NEW SIGNING"
              : "THE CLUB IS YOURS";
      const canvas = paintIdentityBoard({
        clubName: identity.clubName,
        headline,
        primary: identity.primaryColor,
        secondary: identity.secondaryColor,
      });
      const board = boardMesh(
        canvas,
        kind === "takeover" ? 90 : kind === "sponsorship" ? 22 : 28,
        kind === "takeover" ? 24 : kind === "sponsorship" ? 6 : 7
      );
      (board.material as THREE.MeshStandardMaterial).side = THREE.DoubleSide;
      if (kind === "sponsorship") board.position.set(0, 8, 22);
      else if (kind === "academy") board.position.set(0, 8, 16);
      else if (kind === "walkout") board.position.set(0, 6, 8);
      else if (kind === "takeover") {
        board.position.set(0, 72, 0);
        nameBoard = board;
      }
      else board.position.set(0, 12, 18);
      ctx.scene.add(board);
      const texture = (board.material as THREE.MeshStandardMaterial).map as THREE.CanvasTexture;
      drawCrestOnBoard(canvas, identity.crestUrl, texture);

      if (!humanScale) {
        const flood = new THREE.DirectionalLight(0xfff6e8, 1.6);
        flood.position.set(-30, 120, 40);
        ctx.scene.add(flood);
      }

      const ground = new THREE.Mesh(
        new THREE.CircleGeometry(humanScale ? 50 : 160, 48),
        new THREE.MeshStandardMaterial({ color: 0x102218, roughness: 0.9, metalness: 0 })
      );
      ground.rotation.x = -Math.PI / 2;
      ground.position.y = -0.02;
      ground.receiveShadow = true;
      ctx.scene.add(ground);
      lighting?.setIntensity(kind === "gala" ? 0.85 : 1.15);
      sampleCamera(keys, 0, ctx.camera);
    },
    update(dt, elapsed) {
      mixers.forEach((mixer) => mixer.update(dt));
      if (camera) {
        camera.up.set(0, 1, 0);
        sampleCamera(keys, elapsed, camera);
        if (nameBoard) {
          const dx = camera.position.x - nameBoard.position.x;
          const dy = camera.position.y - nameBoard.position.y;
          const dz = camera.position.z - nameBoard.position.z;
          const horiz = Math.hypot(dx, dz) || 1;
          nameBoard.rotation.set(-Math.atan2(dy, horiz), Math.atan2(dx, dz), 0);
        }
      }
    },
    dispose() {
      lighting?.dispose();
      lighting = null;
    },
  };
}
