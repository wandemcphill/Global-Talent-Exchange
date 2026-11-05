/**
 * GTEX Unit 2A (U2A-006) — Humanoid Football Animation Engine
 * HumanoidFootballerRig: Reusable 26-Bone SkinnedMesh Football Player Renderer.
 *
 * Implements:
 * 1. 26-Bone Humanoid `THREE.SkinnedMesh` + `THREE.Skeleton` + `THREE.Bone` hierarchy
 *    matching `gtex_humanoid_footballer.glb` (`Player_Mobile_Mesh.fbx`).
 * 2. Native glTF 2.0 binary (`.glb`) parser & skeletal cloner (zero external loader friction,
 *    supports both async browser fetch and synchronous/buffer parsing).
 * 3. `THREE.AnimationMixer` controller with smooth `crossFadeTo` transitions across all
 *    41 football animation states and velocity-synchronized stride cadence (`timeScale`).
 * 4. Anatomical 8-zone kit & appearance mapping (Jersey Primary, Jersey Trim, Shorts,
 *    Socks, Boots, Skin Tone, Hair Style/Color, Goalkeeper Gloves).
 * 5. Spine-bound 3D Shirt Number badge (`#1`–`#99`) and possession ground indicator ring.
 * 6. Head look-at ball tracking and Spine banking during directional turns.
 * 7. Camera-distance Animation LOD (`full` 60Hz, `medium` 30Hz, `far` 15Hz) for 22 players.
 */

import * as THREE from "three";
import {
  ALL_FOOTBALL_ANIMATION_STATES,
  buildFootballAnimationClipLibrary,
  FOOTBALL_ANIMATION_STATE_META,
  FootballAnimationState,
  GTEX_HUMANOID_BONE_SPECS,
} from "./FootballAnimationStateMachine";
import type { DeviceQualityTier } from "../GtexSceneTypes";

// -----------------------------------------------------------------------------
// 1. Anatomical Kit Zones & Appearance Palettes
// -----------------------------------------------------------------------------

export enum AnatomicalZone {
  SKIN = 0,
  JERSEY_PRIMARY = 1,
  JERSEY_TRIM = 2,
  SHORTS = 3,
  SOCKS = 4,
  BOOTS = 5,
  HAIR = 6,
  GLOVES = 7,
}

const SKIN_TONE_PALETTE = [
  "#F4D0B5", // Light warm
  "#E5B895", // Mediterranean / Olive
  "#C98E65", // Tan / Bronze
  "#8D5534", // Rich brown
  "#54321E", // Deep ebony
] as const;

const HAIR_COLOR_PALETTE = [
  "#141210", // Jet black
  "#2C1E14", // Dark espresso brown
  "#593C24", // Chestnut brown
  "#A67B3D", // Sandy blonde
  "#1E1E22", // Raven black
] as const;

const BOOT_COLOR_PALETTE = [
  "#CCFF00", // Volt neon
  "#FF2A54", // Crimson predator
  "#00E5FF", // Electric cyan
  "#F8FAFC", // Classic white-gold
] as const;

export const HAIR_STYLE_VARIANTS = [
  "buzz_fade",
  "high_top",
  "classic_crop",
  "long_curls",
  "shaved_beard",
] as const;

export type HairStyleVariant = (typeof HAIR_STYLE_VARIANTS)[number];

export interface PlayerAppearanceProfile {
  playerId: string;
  skinToneHex: string;
  hairColorHex: string;
  hairStyle: HairStyleVariant;
  hasFacialHair: boolean;
  bootColorHex: string;
  heightCm: number;
  heightScale: number;
  buildScale: number;
}

export interface HumanoidKitConfig {
  playerId: string;
  side: "home" | "away";
  shirtNumber: number;
  label: string;
  role: string;
  isGoalkeeper: boolean;
  primaryColor: string;
  secondaryColor: string;
  accentColor: string;
  goalkeeperColor: string;
  heightCm?: number;
  skinToneHex?: string;
  hairColorHex?: string;
  hairStyle?: HairStyleVariant;
}

export type AnimationLODLevel = "full" | "medium" | "far";

// -----------------------------------------------------------------------------
// 2. Deterministic Hash & Anatomical Vertex Classifier
// -----------------------------------------------------------------------------

function hashPlayerSeed(playerId: string): number {
  let h = 2166136261;
  for (let i = 0; i < playerId.length; i++) {
    h ^= playerId.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h);
}

export function resolvePlayerAppearanceProfile(config: HumanoidKitConfig): PlayerAppearanceProfile {
  const seed = hashPlayerSeed(config.playerId);
  const skinToneHex = config.skinToneHex || SKIN_TONE_PALETTE[seed % SKIN_TONE_PALETTE.length];
  const hairColorHex = config.hairColorHex || HAIR_COLOR_PALETTE[(seed >> 3) % HAIR_COLOR_PALETTE.length];
  const bootColorHex = BOOT_COLOR_PALETTE[(seed >> 6) % BOOT_COLOR_PALETTE.length];
  const hairStyle = config.hairStyle || HAIR_STYLE_VARIANTS[(seed >> 9) % HAIR_STYLE_VARIANTS.length];
  const hasFacialHair = hairStyle === "shaved_beard" || ((seed >> 12) % 3) === 0;

  // Role-informed stature & physique (base mesh = 178 cm)
  const roleUpper = (config.role || "MID").toUpperCase();
  let baseHeightCm = 179;
  let baseBuild = 1.0;
  if (config.isGoalkeeper || roleUpper === "GK") {
    baseHeightCm = 189 + (seed % 6); // 189 - 194 cm
    baseBuild = 1.04;
  } else if (roleUpper.includes("CB") || roleUpper === "DEF") {
    baseHeightCm = 185 + (seed % 6); // 185 - 190 cm
    baseBuild = 1.05;
  } else if (roleUpper === "ST" || roleUpper === "CF") {
    baseHeightCm = 182 + (seed % 8); // 182 - 189 cm
    baseBuild = 1.03;
  } else if (roleUpper.includes("W") || roleUpper === "AM") {
    baseHeightCm = 172 + (seed % 7); // 172 - 178 cm
    baseBuild = 0.96;
  } else {
    baseHeightCm = 176 + (seed % 8); // 176 - 183 cm
    baseBuild = 0.99 + ((seed % 5) - 2) * 0.015;
  }

  const heightCm = config.heightCm || baseHeightCm;
  const heightScale = Number((heightCm / 178.0).toFixed(3));
  const buildScale = Number(baseBuild.toFixed(3));

  return {
    playerId: config.playerId,
    skinToneHex,
    hairColorHex,
    hairStyle,
    hasFacialHair,
    bootColorHex,
    heightCm,
    heightScale,
    buildScale,
  };
}

/**
 * Classifies a vertex in bind-pose centimeters (`Y in [0..178]`) and bound bone name
 * into one of the 8 anatomical kit/appearance zones, taking hairstyle & beard variation into account.
 */
export function classifyAnatomicalZone(
  boneName: string,
  bindX: number,
  bindY: number,
  bindZ: number,
  hairStyle: HairStyleVariant = "classic_crop",
  hasFacialHair: boolean = false
): AnatomicalZone {
  if (boneName === "Head") {
    // Facial hair / beard / jawline goatee zone on lower front face
    if (hasFacialHair && bindY >= 152.2 && bindY <= 158.0 && bindZ > 3.2 && Math.abs(bindX) < 5.8) {
      return AnatomicalZone.HAIR;
    }
    if (hairStyle === "shaved_beard") {
      if (bindY > 172.5) return AnatomicalZone.HAIR;
      return AnatomicalZone.SKIN;
    }
    if (hairStyle === "high_top") {
      if (bindY > 166.5 || (bindY > 162.0 && bindZ < -2.0)) return AnatomicalZone.HAIR;
      return AnatomicalZone.SKIN;
    }
    if (hairStyle === "long_curls") {
      if (bindY > 165.0 || (bindY > 156.5 && bindZ < -0.5) || (bindY > 161.0 && Math.abs(bindX) > 5.5)) {
        return AnatomicalZone.HAIR;
      }
      return AnatomicalZone.SKIN;
    }
    if (hairStyle === "buzz_fade") {
      if (bindY > 169.5 || (bindY > 163.5 && bindZ < -2.5)) return AnatomicalZone.HAIR;
      return AnatomicalZone.SKIN;
    }
    if (bindY > 168.2 || (bindY > 160.5 && bindZ < -1.2)) {
      return AnatomicalZone.HAIR;
    }
    return AnatomicalZone.SKIN;
  }
  if (boneName === "Neck") {
    return bindY < 151.2 ? AnatomicalZone.JERSEY_TRIM : AnatomicalZone.SKIN;
  }
  if (boneName.includes("Hand") || boneName.includes("Finger")) {
    return AnatomicalZone.GLOVES;
  }
  if (boneName.includes("ForeArm")) {
    return AnatomicalZone.SKIN;
  }
  if (boneName.includes("Arm") && !boneName.includes("ForeArm")) {
    if (bindY < 114.5) return AnatomicalZone.SKIN;
    if (bindY < 117.5) return AnatomicalZone.JERSEY_TRIM;
    return AnatomicalZone.JERSEY_PRIMARY;
  }
  if (boneName === "Spine" || boneName === "Spine1" || boneName === "Spine2" || boneName.includes("Shoulder")) {
    if (bindY > 148.5) return AnatomicalZone.JERSEY_TRIM;
    return AnatomicalZone.JERSEY_PRIMARY;
  }
  if (boneName === "Hips") {
    if (bindY >= 98.5) return AnatomicalZone.JERSEY_PRIMARY;
    if (bindY >= 96.5) return AnatomicalZone.JERSEY_TRIM;
    return AnatomicalZone.SHORTS;
  }
  if (boneName.includes("UpLeg")) {
    if (bindY >= 46.0) return AnatomicalZone.SHORTS;
    return AnatomicalZone.SKIN;
  }
  if (boneName.includes("Leg") && !boneName.includes("UpLeg")) {
    if (bindY > 24.5) return AnatomicalZone.SKIN;
    if (bindY >= 22.2) return AnatomicalZone.JERSEY_TRIM;
    if (bindY >= 6.8) return AnatomicalZone.SOCKS;
    return AnatomicalZone.BOOTS;
  }
  if (boneName.includes("Foot") || boneName.includes("Toe")) {
    return AnatomicalZone.BOOTS;
  }
  return AnatomicalZone.JERSEY_PRIMARY;
}

/**
 * Applies kit and player appearance colors to a `SkinnedMesh` geometry's `color` attribute.
 */
export function applyKitColorsToSkinnedGeometry(
  geometry: THREE.BufferGeometry,
  bones: THREE.Bone[],
  config: HumanoidKitConfig
): void {
  const posAttr = geometry.attributes.position;
  const skinIdxAttr = geometry.attributes.skinIndex;
  if (!posAttr || !skinIdxAttr) return;

  const profile = resolvePlayerAppearanceProfile(config);
  const skinColor = new THREE.Color(profile.skinToneHex);
  const hairColor = new THREE.Color(profile.hairColorHex);
  const bootColor = new THREE.Color(profile.bootColorHex);

  const jerseyPrimary = new THREE.Color(config.isGoalkeeper ? config.goalkeeperColor : config.primaryColor);
  const jerseyTrim = new THREE.Color(config.accentColor || "#FFFFFF");
  const shortsColor = new THREE.Color(
    config.isGoalkeeper ? config.goalkeeperColor : config.secondaryColor || config.primaryColor
  );
  const socksColor = new THREE.Color(config.primaryColor);
  const glovesColor = config.isGoalkeeper ? new THREE.Color(config.accentColor || "#F8FAFC") : skinColor;

  let colorAttr = geometry.attributes.color as THREE.BufferAttribute | undefined;
  if (!colorAttr || colorAttr.count !== posAttr.count) {
    colorAttr = new THREE.BufferAttribute(new Float32Array(posAttr.count * 3), 3);
    geometry.setAttribute("color", colorAttr);
  }

  let bindPosArray = geometry.userData.bindPositionArray as Float32Array | undefined;
  if (!bindPosArray) {
    bindPosArray = new Float32Array(posAttr.array.length);
    bindPosArray.set(posAttr.array as ArrayLike<number>);
    geometry.userData.bindPositionArray = bindPosArray;
  }

  for (let i = 0; i < posAttr.count; i++) {
    const bIdx = skinIdxAttr.getX(i);
    const boneName = bones[bIdx]?.name || "Spine";
    const bx = bindPosArray[i * 3];
    const by = bindPosArray[i * 3 + 1];
    const bz = bindPosArray[i * 3 + 2];

    const zone = classifyAnatomicalZone(boneName, bx, by, bz, profile.hairStyle, profile.hasFacialHair);
    let targetColor = jerseyPrimary;

    switch (zone) {
      case AnatomicalZone.SKIN:
        targetColor = config.isGoalkeeper && boneName.includes("ForeArm") ? jerseyPrimary : skinColor;
        break;
      case AnatomicalZone.JERSEY_PRIMARY:
        targetColor = jerseyPrimary;
        break;
      case AnatomicalZone.JERSEY_TRIM:
        targetColor = jerseyTrim;
        break;
      case AnatomicalZone.SHORTS:
        targetColor = shortsColor;
        break;
      case AnatomicalZone.SOCKS:
        targetColor = socksColor;
        break;
      case AnatomicalZone.BOOTS:
        targetColor = bootColor;
        break;
      case AnatomicalZone.HAIR:
        targetColor = hairColor;
        break;
      case AnatomicalZone.GLOVES:
        targetColor = glovesColor;
        break;
    }

    colorAttr.setXYZ(i, targetColor.r, targetColor.g, targetColor.b);
  }

  colorAttr.needsUpdate = true;
}

// -----------------------------------------------------------------------------
// 3. Canonical 26-Bone Synchronous SkinnedMesh Builder
// -----------------------------------------------------------------------------

interface LimbSegmentDef {
  boneIndex: number;
  startCm: [number, number, number];
  endCm: [number, number, number];
  radiusTopCm: number;
  radiusBottomCm: number;
  radialSegments?: number;
}

const ARTICULATED_HUMANOID_SEGMENTS: readonly LimbSegmentDef[] = [
  { boneIndex: 0, startCm: [0, 88, 0], endCm: [0, 104, 0], radiusTopCm: 15.5, radiusBottomCm: 16.0, radialSegments: 10 },
  { boneIndex: 9, startCm: [0, 103, 0], endCm: [0, 118, 0], radiusTopCm: 15.0, radiusBottomCm: 14.8, radialSegments: 10 },
  { boneIndex: 10, startCm: [0, 117, 0], endCm: [0, 133, 0], radiusTopCm: 16.5, radiusBottomCm: 15.0, radialSegments: 10 },
  { boneIndex: 11, startCm: [0, 132, 0], endCm: [0, 150, 0], radiusTopCm: 18.2, radiusBottomCm: 16.5, radialSegments: 12 },
  { boneIndex: 24, startCm: [0, 149, 0], endCm: [0, 157, 0.3], radiusTopCm: 5.8, radiusBottomCm: 6.2, radialSegments: 8 },
  { boneIndex: 25, startCm: [0, 156, 0.7], endCm: [0, 177.4, 0.7], radiusTopCm: 9.8, radiusBottomCm: 8.5, radialSegments: 12 },
  { boneIndex: 1, startCm: [10.8, 93.7, 0], endCm: [12.8, 48.9, 0], radiusTopCm: 8.8, radiusBottomCm: 6.5, radialSegments: 8 },
  { boneIndex: 2, startCm: [12.8, 48.9, 0], endCm: [16.1, 8.3, -3.9], radiusTopCm: 6.2, radiusBottomCm: 4.4, radialSegments: 8 },
  { boneIndex: 3, startCm: [16.1, 8.3, -5.0], endCm: [17.5, 2.2, 16.0], radiusTopCm: 4.8, radiusBottomCm: 4.2, radialSegments: 8 },
  { boneIndex: 5, startCm: [-10.8, 93.7, 0], endCm: [-12.8, 48.9, 0], radiusTopCm: 8.8, radiusBottomCm: 6.5, radialSegments: 8 },
  { boneIndex: 6, startCm: [-12.8, 48.9, 0], endCm: [-16.1, 8.3, -3.9], radiusTopCm: 6.2, radiusBottomCm: 4.4, radialSegments: 8 },
  { boneIndex: 7, startCm: [-16.1, 8.3, -5.0], endCm: [-17.5, 2.2, 16.0], radiusTopCm: 4.8, radiusBottomCm: 4.2, radialSegments: 8 },
  { boneIndex: 13, startCm: [15.9, 145.7, -1.7], endCm: [29.6, 117.4, -1.4], radiusTopCm: 5.5, radiusBottomCm: 4.5, radialSegments: 8 },
  { boneIndex: 14, startCm: [29.6, 117.4, -1.4], endCm: [40.0, 94.4, 6.3], radiusTopCm: 4.4, radiusBottomCm: 3.6, radialSegments: 8 },
  { boneIndex: 15, startCm: [40.0, 94.4, 6.3], endCm: [43.0, 81.0, 9.3], radiusTopCm: 4.2, radiusBottomCm: 3.8, radialSegments: 8 },
  { boneIndex: 19, startCm: [-15.9, 145.7, -1.7], endCm: [-29.6, 117.4, -1.4], radiusTopCm: 5.5, radiusBottomCm: 4.5, radialSegments: 8 },
  { boneIndex: 20, startCm: [-29.6, 117.4, -1.4], endCm: [-40.0, 94.4, 6.3], radiusTopCm: 4.4, radiusBottomCm: 3.6, radialSegments: 8 },
  { boneIndex: 21, startCm: [-40.0, 94.4, 6.3], endCm: [-43.0, 81.0, 9.3], radiusTopCm: 4.2, radiusBottomCm: 3.8, radialSegments: 8 },
];

/**
 * Builds the canonical 26-bone hierarchy (`THREE.Bone[]`) and `THREE.Skeleton`
 * matching `Player_Mobile_Mesh.fbx`.
 */
export function createCanonical26BoneSkeleton(customBoneInverses?: THREE.Matrix4[]): {
  bones: THREE.Bone[];
  boneByName: Map<string, THREE.Bone>;
  skeleton: THREE.Skeleton;
  rootBone: THREE.Bone;
} {
  const bones: THREE.Bone[] = [];
  const boneByName = new Map<string, THREE.Bone>();

  for (const spec of GTEX_HUMANOID_BONE_SPECS) {
    const bone = new THREE.Bone();
    bone.name = spec.name;
    bone.position.set(spec.bindLocalPosCm[0], spec.bindLocalPosCm[1], spec.bindLocalPosCm[2]);
    bones.push(bone);
    boneByName.set(spec.name, bone);
  }

  for (const spec of GTEX_HUMANOID_BONE_SPECS) {
    if (spec.parent) {
      const parentBone = boneByName.get(spec.parent);
      const childBone = boneByName.get(spec.name);
      if (parentBone && childBone) {
        parentBone.add(childBone);
      }
    }
  }

  const rootBone = bones[0];
  rootBone.updateMatrixWorld(true);
  const skeleton = customBoneInverses
    ? new THREE.Skeleton(bones, customBoneInverses.map((m) => m.clone()))
    : new THREE.Skeleton(bones);
  return { bones, boneByName, skeleton, rootBone };
}

let cachedArticulatedGeometry: THREE.BufferGeometry | null = null;

export function getCanonicalHumanoidBufferGeometry(): THREE.BufferGeometry {
  if (cachedArticulatedGeometry) {
    return cachedArticulatedGeometry.clone();
  }

  const positions: number[] = [];
  const normals: number[] = [];
  const uvs: number[] = [];
  const skinIndices: number[] = [];
  const skinWeights: number[] = [];
  const indices: number[] = [];

  let vertexOffset = 0;
  const up = new THREE.Vector3(0, 1, 0);

  for (const seg of ARTICULATED_HUMANOID_SEGMENTS) {
    const start = new THREE.Vector3(...seg.startCm);
    const end = new THREE.Vector3(...seg.endCm);
    const dir = new THREE.Vector3().subVectors(end, start);
    const length = dir.length();
    const mid = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);

    const cyl = new THREE.CylinderGeometry(
      seg.radiusTopCm,
      seg.radiusBottomCm,
      length,
      seg.radialSegments || 8,
      2,
      false
    );

    const quat = new THREE.Quaternion().setFromUnitVectors(up, dir.clone().normalize());
    const mat = new THREE.Matrix4().compose(mid, quat, new THREE.Vector3(1, 1, 1));
    cyl.applyMatrix4(mat);

    const posAttr = cyl.attributes.position;
    const normAttr = cyl.attributes.normal;
    const uvAttr = cyl.attributes.uv;
    const idxAttr = cyl.index;

    for (let i = 0; i < posAttr.count; i++) {
      positions.push(posAttr.getX(i), posAttr.getY(i), posAttr.getZ(i));
      normals.push(normAttr.getX(i), normAttr.getY(i), normAttr.getZ(i));
      uvs.push(uvAttr ? uvAttr.getX(i) : 0, uvAttr ? uvAttr.getY(i) : 0);
      skinIndices.push(seg.boneIndex, 0, 0, 0);
      skinWeights.push(1.0, 0.0, 0.0, 0.0);
    }

    if (idxAttr) {
      for (let i = 0; i < idxAttr.count; i++) {
        indices.push(vertexOffset + idxAttr.getX(i));
      }
    }

    vertexOffset += posAttr.count;
    cyl.dispose();
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
  geo.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geo.setAttribute("skinIndex", new THREE.Uint16BufferAttribute(skinIndices, 4));
  geo.setAttribute("skinWeight", new THREE.Float32BufferAttribute(skinWeights, 4));
  geo.setIndex(indices);

  cachedArticulatedGeometry = geo;
  return geo.clone();
}

// -----------------------------------------------------------------------------
// 4. Native glTF 2.0 Binary (`.glb`) Parser & Asset Cache
// -----------------------------------------------------------------------------

export interface LoadedHumanoidGLBAsset {
  skinnedMesh: THREE.SkinnedMesh;
  geometry: THREE.BufferGeometry;
  boneInverses: THREE.Matrix4[];
  mocapClips: THREE.AnimationClip[];
  clipLibrary: Map<FootballAnimationState, THREE.AnimationClip>;
}

let cachedGLBAsset: LoadedHumanoidGLBAsset | null = null;
let pendingGLBPromise: Promise<LoadedHumanoidGLBAsset | null> | null = null;
let cachedDefaultClipLibrary: Map<FootballAnimationState, THREE.AnimationClip> | null = null;

export function getDefaultFootballClipLibrary(): Map<FootballAnimationState, THREE.AnimationClip> {
  if (cachedGLBAsset) return cachedGLBAsset.clipLibrary;
  if (!cachedDefaultClipLibrary) {
    cachedDefaultClipLibrary = buildFootballAnimationClipLibrary([]);
  }
  return cachedDefaultClipLibrary;
}

const GLTF_TYPE_COMPONENTS: Record<string, number> = {
  SCALAR: 1,
  VEC2: 2,
  VEC3: 3,
  VEC4: 4,
  MAT4: 16,
};

/**
 * Native glTF 2.0 binary (`.glb`) parser that reconstructs the 9,888-vertex `SkinnedMesh`,
 * 26-bone `Skeleton` (`inverseBindMatrices`), and 29 motion-capture `AnimationClip`s
 * using pure `THREE` primitives.
 */
export function parseHumanoidFootballerGLBBuffer(glbBuffer: ArrayBuffer): Promise<LoadedHumanoidGLBAsset> {
  return new Promise((resolve, reject) => {
    try {
      const view = new DataView(glbBuffer);
      const magic = view.getUint32(0, true);
      if (magic !== 0x46546c67) {
        throw new Error("Invalid GLB magic header");
      }

      const jsonChunkLength = view.getUint32(12, true);
      const jsonChunkType = view.getUint32(16, true);
      if (jsonChunkType !== 0x4e4f534a) {
        throw new Error("Expected JSON chunk at offset 12");
      }

      const jsonBytes = new Uint8Array(glbBuffer, 20, jsonChunkLength);
      let jsonText = "";
      if (typeof TextDecoder !== "undefined") {
        jsonText = new TextDecoder("utf-8").decode(jsonBytes);
      } else if (typeof (globalThis as any).TextDecoder !== "undefined") {
        jsonText = new (globalThis as any).TextDecoder("utf-8").decode(jsonBytes);
      } else {
        for (let i = 0; i < jsonBytes.length; i++) {
          jsonText += String.fromCharCode(jsonBytes[i]);
        }
      }
      const gltf = JSON.parse(jsonText);

      const binChunkHeaderOffset = 20 + jsonChunkLength;
      const binByteOffset = binChunkHeaderOffset + 8;

      const readAccessorArray = (accIndex: number): Float32Array | Uint16Array | Uint32Array | Uint8Array => {
        const acc = gltf.accessors[accIndex];
        const bv = gltf.bufferViews[acc.bufferView];
        const numComponents = GLTF_TYPE_COMPONENTS[acc.type] || 1;
        const elementCount = acc.count * numComponents;
        const byteStart = binByteOffset + (bv.byteOffset || 0) + (acc.byteOffset || 0);
        // Copy slice to guarantee 4-byte alignment
        const componentBytes =
          acc.componentType === 5126 || acc.componentType === 5125
            ? 4
            : acc.componentType === 5123
            ? 2
            : 1;
        const alignedCopy = glbBuffer.slice(byteStart, byteStart + elementCount * componentBytes);

        if (acc.componentType === 5126) return new Float32Array(alignedCopy);
        if (acc.componentType === 5125) return new Uint32Array(alignedCopy);
        if (acc.componentType === 5123) return new Uint16Array(alignedCopy);
        return new Uint8Array(alignedCopy);
      };

      // 1. Reconstruct Geometry from meshes[0].primitives[0]
      const prim = gltf.meshes[0].primitives[0];
      const geometry = new THREE.BufferGeometry();

      if (prim.attributes.POSITION !== undefined) {
        geometry.setAttribute(
          "position",
          new THREE.Float32BufferAttribute(readAccessorArray(prim.attributes.POSITION) as Float32Array, 3)
        );
      }
      if (prim.attributes.NORMAL !== undefined) {
        geometry.setAttribute(
          "normal",
          new THREE.Float32BufferAttribute(readAccessorArray(prim.attributes.NORMAL) as Float32Array, 3)
        );
      }
      if (prim.attributes.TEXCOORD_0 !== undefined) {
        geometry.setAttribute(
          "uv",
          new THREE.Float32BufferAttribute(readAccessorArray(prim.attributes.TEXCOORD_0) as Float32Array, 2)
        );
      }
      if (prim.attributes.JOINTS_0 !== undefined) {
        const jointsArr = readAccessorArray(prim.attributes.JOINTS_0);
        geometry.setAttribute("skinIndex", new THREE.Uint16BufferAttribute( new Uint16Array(jointsArr), 4));
      }
      if (prim.attributes.WEIGHTS_0 !== undefined) {
        geometry.setAttribute(
          "skinWeight",
          new THREE.Float32BufferAttribute(readAccessorArray(prim.attributes.WEIGHTS_0) as Float32Array, 4)
        );
      }
      if (prim.attributes.COLOR_0 !== undefined) {
        const colAcc = gltf.accessors[prim.attributes.COLOR_0];
        const itemSize = GLTF_TYPE_COMPONENTS[colAcc.type] || 3;
        geometry.setAttribute(
          "color",
          new THREE.Float32BufferAttribute(readAccessorArray(prim.attributes.COLOR_0) as Float32Array, itemSize)
        );
      }
      if (prim.indices !== undefined) {
        const idxArr = readAccessorArray(prim.indices);
        geometry.setIndex(new THREE.BufferAttribute(idxArr as Uint16Array | Uint32Array, 1));
      }

      // 2. Reconstruct 26-Bone Skeleton & InverseBindMatrices from skins[0]
      const skin = gltf.skins[0];
      const boneInverses: THREE.Matrix4[] = [];
      if (skin.inverseBindMatrices !== undefined) {
        const ibmFloats = readAccessorArray(skin.inverseBindMatrices) as Float32Array;
        for (let b = 0; b < skin.joints.length; b++) {
          const mat = new THREE.Matrix4().fromArray(ibmFloats, b * 16);
          boneInverses.push(mat);
        }
      }

      const { skeleton, rootBone } = createCanonical26BoneSkeleton(
        boneInverses.length === 26 ? boneInverses : undefined
      );
      const templateMesh = new THREE.SkinnedMesh(
        geometry,
        new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.62, metalness: 0.08 })
      );
      templateMesh.name = gltf.meshes[0].name || "Player";
      templateMesh.add(rootBone);
      templateMesh.bind(skeleton, new THREE.Matrix4());

      // 3. Reconstruct Motion-Capture AnimationClips from animations[]
      const mocapClips: THREE.AnimationClip[] = [];
      for (const rawAnim of gltf.animations || []) {
        const tracks: THREE.KeyframeTrack[] = [];
        let maxTime = 0;

        for (const ch of rawAnim.channels || []) {
          const sampler = rawAnim.samplers[ch.sampler];
          const targetNode = gltf.nodes[ch.target.node];
          if (!targetNode || !targetNode.name) continue;

          const times = Array.from(readAccessorArray(sampler.input) as Float32Array);
          const values = Array.from(readAccessorArray(sampler.output) as Float32Array);
          if (times.length > 0 && times[times.length - 1] > maxTime) {
            maxTime = times[times.length - 1];
          }

          if (ch.target.path === "rotation") {
            tracks.push(new THREE.QuaternionKeyframeTrack(`${targetNode.name}.quaternion`, times, values));
          } else if (ch.target.path === "translation") {
            tracks.push(new THREE.VectorKeyframeTrack(`${targetNode.name}.position`, times, values));
          }
        }

        if (tracks.length > 0) {
          mocapClips.push(new THREE.AnimationClip(rawAnim.name || "clip", maxTime, tracks));
        }
      }

      const clipLibrary = buildFootballAnimationClipLibrary(mocapClips);
      const asset: LoadedHumanoidGLBAsset = {
        skinnedMesh: templateMesh,
        geometry,
        boneInverses,
        mocapClips,
        clipLibrary,
      };
      cachedGLBAsset = asset;
      resolve(asset);
    } catch (err) {
      reject(err);
    }
  });
}

/**
 * Loads `/models/footballer/gtex_humanoid_footballer.glb` asynchronously in browser environments.
 */
export function loadHumanoidFootballerGLB(
  url: string = "/models/footballer/gtex_humanoid_footballer.glb"
): Promise<LoadedHumanoidGLBAsset | null> {
  if (cachedGLBAsset) return Promise.resolve(cachedGLBAsset);
  if (pendingGLBPromise) return pendingGLBPromise;

  if (typeof window === "undefined" || typeof fetch !== "function") {
    return Promise.resolve(null);
  }

  pendingGLBPromise = fetch(url)
    .then((res) => {
      if (!res.ok) return null;
      return res.arrayBuffer();
    })
    .then((buf) => {
      if (!buf) return null;
      return parseHumanoidFootballerGLBBuffer(buf);
    })
    .catch(() => null);

  return pendingGLBPromise;
}

export function getCachedHumanoidGLBAsset(): LoadedHumanoidGLBAsset | null {
  return cachedGLBAsset;
}

// -----------------------------------------------------------------------------
// 5. Shirt Number Texture / Badge Generator
// -----------------------------------------------------------------------------

const shirtNumberTextureCache = new Map<string, THREE.Texture>();

function createShirtNumberTexture(shirtNumber: number, textColorHex: string): THREE.Texture | null {
  const key = `${shirtNumber}_${textColorHex}`;
  if (shirtNumberTextureCache.has(key)) {
    return shirtNumberTextureCache.get(key)!;
  }

  try {
    if (typeof document === "undefined") return null;
    if (typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent || "")) {
      return null;
    }
    const canvas = document.createElement("canvas");
    canvas.width = 128;
    canvas.height = 128;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;

    ctx.clearRect(0, 0, 128, 128);
    ctx.font = "bold 86px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.lineWidth = 8;
    ctx.strokeStyle = "rgba(0, 0, 0, 0.65)";
    ctx.strokeText(String(shirtNumber), 64, 68);
    ctx.fillStyle = textColorHex || "#FFFFFF";
    ctx.fillText(String(shirtNumber), 64, 68);

    const tex = new THREE.CanvasTexture(canvas);
    tex.needsUpdate = true;
    shirtNumberTextureCache.set(key, tex);
    return tex;
  } catch {
    return null;
  }
}

// -----------------------------------------------------------------------------
// 6. HumanoidFootballerRig Class (Per-Player SkinnedMesh + AnimationMixer)
// -----------------------------------------------------------------------------

export class HumanoidFootballerRig {
  public readonly playerId: string;
  public readonly rootGroup: THREE.Group;
  public readonly modelContainer: THREE.Group;
  public skinnedMesh!: THREE.SkinnedMesh;
  public skeleton!: THREE.Skeleton;
  public boneByName = new Map<string, THREE.Bone>();
  public mixer!: THREE.AnimationMixer;

  public readonly appearanceProfile: PlayerAppearanceProfile;
  private kitConfig: HumanoidKitConfig;

  public get options(): HumanoidKitConfig {
    return this.kitConfig;
  }

  public get appearance(): PlayerAppearanceProfile {
    return this.appearanceProfile;
  }
  private clipLibrary: Map<FootballAnimationState, THREE.AnimationClip>;
  private actionsByState = new Map<FootballAnimationState, THREE.AnimationAction>();
  private currentState: FootballAnimationState = "idle";
  private timeInCurrentStateSec: number = 0;
  private lodLevel: AnimationLODLevel = "full";
  private lodFrameCounter: number = 0;
  private accumulatedLodDeltaSec: number = 0;
  private isUsingGLBMesh: boolean = false;
  private groundRingMesh: THREE.Mesh;
  private backNumberMesh: THREE.Mesh | null = null;
  private frontNumberMesh: THREE.Mesh | null = null;

  constructor(kitConfig: HumanoidKitConfig) {
    this.playerId = kitConfig.playerId;
    this.kitConfig = kitConfig;
    this.appearanceProfile = resolvePlayerAppearanceProfile(kitConfig);

    this.rootGroup = new THREE.Group();
    this.rootGroup.name = `HumanoidPlayer_${kitConfig.playerId}`;
    this.rootGroup.userData = {
      playerId: kitConfig.playerId,
      side: kitConfig.side,
      role: kitConfig.role,
      shirtNumber: kitConfig.shirtNumber,
      appearanceProfile: this.appearanceProfile,
      isHumanoidRig: true,
    };

    // Container scaled from centimeters (178cm) to FIFA pitch meters with player-specific stature & physique
    this.modelContainer = new THREE.Group();
    this.modelContainer.name = "HumanoidModelCmScale";
    this.modelContainer.scale.set(
      0.01 * this.appearanceProfile.buildScale,
      0.01 * this.appearanceProfile.heightScale,
      0.01 * this.appearanceProfile.buildScale
    );
    this.rootGroup.add(this.modelContainer);

    this.clipLibrary = getDefaultFootballClipLibrary();

    if (cachedGLBAsset) {
      this.buildFromGLBAsset(cachedGLBAsset);
    } else {
      this.buildCanonicalSynchronousRig();
      loadHumanoidFootballerGLB().then((asset) => {
        if (asset && !this.isUsingGLBMesh && this.rootGroup.parent) {
          this.upgradeToGLBAsset(asset);
        }
      });
    }

    // Subtle ground tactical ring
    const ringGeo = new THREE.RingGeometry(0.34, 0.43, 20);
    const ringColor = new THREE.Color(
      kitConfig.isGoalkeeper ? kitConfig.goalkeeperColor : kitConfig.primaryColor
    );
    const ringMat = new THREE.MeshBasicMaterial({
      color: ringColor,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.55,
    });
    this.groundRingMesh = new THREE.Mesh(ringGeo, ringMat);
    this.groundRingMesh.name = "PlayerGroundRing";
    this.groundRingMesh.rotation.x = -Math.PI / 2;
    this.groundRingMesh.position.y = 0.025;
    this.rootGroup.add(this.groundRingMesh);

    this.transitionToState("idle", true);
  }

  private buildCanonicalSynchronousRig(): void {
    const { bones, boneByName, skeleton, rootBone } = createCanonical26BoneSkeleton();
    this.skeleton = skeleton;
    this.boneByName = boneByName;

    const geo = getCanonicalHumanoidBufferGeometry();
    applyKitColorsToSkinnedGeometry(geo, bones, this.kitConfig);

    const mat = new THREE.MeshStandardMaterial({
      name: `KitMaterial_${this.playerId}`,
      vertexColors: true,
      roughness: 0.62,
      metalness: 0.08,
    });

    this.skinnedMesh = new THREE.SkinnedMesh(geo, mat);
    this.skinnedMesh.name = "HumanoidSkinnedMesh";
    this.skinnedMesh.castShadow = true;
    this.skinnedMesh.receiveShadow = true;
    this.skinnedMesh.frustumCulled = false;

    this.modelContainer.add(rootBone);
    this.modelContainer.add(this.skinnedMesh);
    this.skinnedMesh.bind(this.skeleton, new THREE.Matrix4());

    this.attachShirtNumberBadge();
    this.setupAnimationMixer(this.modelContainer);
  }

  private buildFromGLBAsset(asset: LoadedHumanoidGLBAsset): void {
    const { bones, boneByName, skeleton, rootBone } = createCanonical26BoneSkeleton(
      asset.boneInverses.length === 26 ? asset.boneInverses : undefined
    );
    this.skeleton = skeleton;
    this.boneByName = boneByName;

    const geo = asset.geometry.clone();
    applyKitColorsToSkinnedGeometry(geo, bones, this.kitConfig);

    const mat = new THREE.MeshStandardMaterial({
      name: `KitMaterial_${this.playerId}`,
      vertexColors: true,
      roughness: 0.62,
      metalness: 0.08,
    });

    this.skinnedMesh = new THREE.SkinnedMesh(geo, mat);
    this.skinnedMesh.name = "Player";
    this.skinnedMesh.castShadow = true;
    this.skinnedMesh.receiveShadow = true;
    this.skinnedMesh.frustumCulled = false;

    this.modelContainer.add(rootBone);
    this.modelContainer.add(this.skinnedMesh);
    this.skinnedMesh.bind(this.skeleton, new THREE.Matrix4());

    this.clipLibrary = asset.clipLibrary;
    this.isUsingGLBMesh = true;

    this.attachShirtNumberBadge();
    this.setupAnimationMixer(this.modelContainer);
  }

  public upgradeToGLBAsset(asset: LoadedHumanoidGLBAsset): void {
    if (this.isUsingGLBMesh) return;
    const prevState = this.currentState;
    this.mixer.stopAllAction();
    this.actionsByState.clear();
    this.skinnedMesh.geometry.dispose();
    (this.skinnedMesh.material as THREE.Material).dispose();
    this.modelContainer.clear();

    this.buildFromGLBAsset(asset);
    this.transitionToState(prevState, true);
  }

  private attachShirtNumberBadge(): void {
    const spine2 = this.boneByName.get("Spine2");
    if (!spine2) return;

    const numTex = createShirtNumberTexture(
      this.kitConfig.shirtNumber || 10,
      this.kitConfig.accentColor || "#FFFFFF"
    );

    const badgeGeo = new THREE.PlaneGeometry(22, 22);
    const badgeMat = new THREE.MeshBasicMaterial({
      color: numTex ? 0xffffff : new THREE.Color(this.kitConfig.accentColor || "#FFFFFF"),
      map: numTex || null,
      transparent: true,
      opacity: numTex ? 0.96 : 0.85,
      side: THREE.DoubleSide,
      depthWrite: false,
    });

    this.backNumberMesh = new THREE.Mesh(badgeGeo, badgeMat);
    this.backNumberMesh.name = `ShirtNumberBadge_${this.kitConfig.shirtNumber}`;
    this.backNumberMesh.position.set(0, 4.0, -16.8);
    this.backNumberMesh.rotation.y = Math.PI;
    spine2.add(this.backNumberMesh);

    const frontGeo = new THREE.PlaneGeometry(11, 11);
    this.frontNumberMesh = new THREE.Mesh(frontGeo, badgeMat);
    this.frontNumberMesh.name = `FrontChestNumberBadge_${this.kitConfig.shirtNumber}`;
    this.frontNumberMesh.position.set(0, 5.5, 16.4);
    spine2.add(this.frontNumberMesh);
  }

  private setupAnimationMixer(mixerRoot: THREE.Object3D): void {
    this.mixer = new THREE.AnimationMixer(mixerRoot);
    this.actionsByState.clear();

    for (const state of ALL_FOOTBALL_ANIMATION_STATES) {
      const clip = this.clipLibrary.get(state);
      if (!clip) continue;
      const meta = FOOTBALL_ANIMATION_STATE_META[state];
      const action = this.mixer.clipAction(clip);
      if (meta.loop) {
        action.setLoop(THREE.LoopRepeat, Infinity);
      } else {
        action.setLoop(THREE.LoopOnce, 1);
        action.clampWhenFinished = true;
      }
      this.actionsByState.set(state, action);
    }
  }

  public transitionToState(nextState: FootballAnimationState, immediate: boolean = false): void {
    if (!immediate && nextState === this.currentState && this.actionsByState.get(nextState)?.isRunning()) {
      return;
    }

    const prevAction = this.actionsByState.get(this.currentState);
    const nextAction = this.actionsByState.get(nextState) || this.actionsByState.get("idle");
    if (!nextAction) return;

    const meta = FOOTBALL_ANIMATION_STATE_META[nextState] || FOOTBALL_ANIMATION_STATE_META.idle;

    nextAction.enabled = true;
    nextAction.reset();
    nextAction.setEffectiveTimeScale(1.0);
    nextAction.setEffectiveWeight(1.0);

    if (immediate || !prevAction || prevAction === nextAction) {
      if (prevAction && prevAction !== nextAction) {
        prevAction.stop();
      }
      nextAction.play();
    } else {
      nextAction.play();
      prevAction.crossFadeTo(nextAction, meta.crossFadeSec, false);
    }

    this.currentState = nextState;
    this.timeInCurrentStateSec = 0;
    this.rootGroup.userData.animationState = nextState;
    this.rootGroup.userData.animationCategory = meta.category;
  }

  public getCurrentState(): FootballAnimationState {
    return this.currentState;
  }

  public getTimeInCurrentState(): number {
    return this.timeInCurrentStateSec;
  }

  public getLODLevel(): AnimationLODLevel {
    return this.lodLevel;
  }

  public update(params: {
    deltaSec: number;
    targetState: FootballAnimationState;
    position3D: [number, number, number];
    facingAngleRad: number;
    speedRatio: number;
    angularVelocityRad?: number;
    hasPossession: boolean;
    ballPosition3D: [number, number, number];
    cameraPosition3D: [number, number, number];
    qualityTier?: DeviceQualityTier;
  }): void {
    const {
      deltaSec,
      targetState,
      position3D,
      facingAngleRad,
      speedRatio,
      angularVelocityRad = 0,
      hasPossession,
      ballPosition3D,
      cameraPosition3D,
      qualityTier = "high",
    } = params;

    this.timeInCurrentStateSec += deltaSec;

    if (targetState !== this.currentState) {
      this.transitionToState(targetState, false);
    }

    this.rootGroup.position.set(position3D[0], position3D[1], position3D[2]);
    this.rootGroup.rotation.y = Math.PI / 2 - facingAngleRad;

    const activeAction = this.actionsByState.get(this.currentState);
    if (activeAction) {
      const meta = FOOTBALL_ANIMATION_STATE_META[this.currentState];
      if (meta.category === "locomotion" && this.currentState !== "idle") {
        const cadenceScale = 0.8 + Math.min(1.0, Math.max(0.0, speedRatio)) * 0.55;
        activeAction.setEffectiveTimeScale(cadenceScale);
      } else if (this.currentState === "dribble") {
        const cadenceScale = 0.9 + Math.min(1.0, Math.max(0.0, speedRatio)) * 0.45;
        activeAction.setEffectiveTimeScale(cadenceScale);
      } else {
        activeAction.setEffectiveTimeScale(1.0);
      }
    }

    const ringMat = this.groundRingMesh.material as THREE.MeshBasicMaterial;
    if (hasPossession) {
      ringMat.opacity = 0.92;
      this.groundRingMesh.scale.setScalar(1.22);
    } else {
      ringMat.opacity = 0.48;
      this.groundRingMesh.scale.setScalar(1.0);
    }

    const camDist = Math.hypot(
      cameraPosition3D[0] - position3D[0],
      cameraPosition3D[1] - position3D[1],
      cameraPosition3D[2] - position3D[2]
    );

    const meta = FOOTBALL_ANIMATION_STATE_META[this.currentState];
    const isPriorityActor =
      hasPossession ||
      meta.category === "ball_interaction" ||
      meta.category === "goalkeeper_action" ||
      meta.category === "match_reaction";

    if (qualityTier === "low" && !isPriorityActor) {
      this.lodLevel = camDist < 38 ? "medium" : "far";
    } else if (isPriorityActor || camDist < 36) {
      this.lodLevel = "full";
    } else if (camDist < 64) {
      this.lodLevel = "medium";
    } else {
      this.lodLevel = "far";
    }

    this.lodFrameCounter = (this.lodFrameCounter + 1) % 4;
    this.accumulatedLodDeltaSec += deltaSec;

    const shouldStepMixer =
      this.lodLevel === "full" ||
      (this.lodLevel === "medium" && this.lodFrameCounter % 2 === 0) ||
      (this.lodLevel === "far" && this.lodFrameCounter === 0);

    if (shouldStepMixer) {
      this.mixer.update(this.accumulatedLodDeltaSec);
      this.accumulatedLodDeltaSec = 0;

      if (this.lodLevel !== "far") {
        this.applyProceduralPostureAdjustments(
          position3D,
          facingAngleRad,
          angularVelocityRad,
          ballPosition3D
        );
      }
    }

    this.skinnedMesh.castShadow = this.lodLevel !== "far" && qualityTier !== "low";
  }

  private applyProceduralPostureAdjustments(
    position3D: [number, number, number],
    facingAngleRad: number,
    angularVelocityRad: number,
    ballPosition3D: [number, number, number]
  ): void {
    const hipsBone = this.boneByName.get("Hips");
    const headBone = this.boneByName.get("Head");
    const spine1Bone = this.boneByName.get("Spine1");

    // Directional goalkeeper dive lateral orientation toward incoming shot trajectory
    if (
      hipsBone &&
      (this.currentState === "gk_dive_high" ||
        this.currentState === "gk_dive_low" ||
        this.currentState === "gk_parry")
    ) {
      const dx = ballPosition3D[0] - position3D[0];
      const dz = ballPosition3D[2] - position3D[2];
      // Lateral component perpendicular to goalkeeper facing direction
      const forwardX = Math.cos(facingAngleRad);
      const forwardZ = Math.sin(facingAngleRad);
      const lateralOffset = -dx * forwardZ + dz * forwardX;
      if (Math.abs(lateralOffset) > 0.25) {
        const diveSign = lateralOffset >= 0 ? 1 : -1;
        const diveTilt = Math.min(0.45, Math.abs(lateralOffset) * 0.12) * diveSign;
        const diveQuat = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), diveTilt);
        hipsBone.quaternion.multiply(diveQuat);
      }
    }

    if (spine1Bone && Math.abs(angularVelocityRad) > 0.1) {
      const bankAngle = Math.max(-0.22, Math.min(0.22, angularVelocityRad * 0.08));
      const bankQuat = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), bankAngle);
      spine1Bone.quaternion.multiply(bankQuat);
    }

    if (headBone) {
      const dx = ballPosition3D[0] - position3D[0];
      const dz = ballPosition3D[2] - position3D[2];
      const dist = Math.hypot(dx, dz);
      if (dist > 0.5 && dist < 35.0) {
        const angleToBall = Math.atan2(dz, dx);
        let relYaw = facingAngleRad - angleToBall;
        while (relYaw > Math.PI) relYaw -= 2 * Math.PI;
        while (relYaw < -Math.PI) relYaw += 2 * Math.PI;
        const clampedYaw = Math.max(-0.55, Math.min(0.55, relYaw * 0.45));
        const lookQuat = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), clampedYaw);
        headBone.quaternion.multiply(lookQuat);
      }
    }
  }

  public dispose(): void {
    this.mixer.stopAllAction();
    this.skinnedMesh.geometry.dispose();
    if (Array.isArray(this.skinnedMesh.material)) {
      this.skinnedMesh.material.forEach((m) => m.dispose());
    } else {
      this.skinnedMesh.material.dispose();
    }
    this.groundRingMesh.geometry.dispose();
    (this.groundRingMesh.material as THREE.Material).dispose();
    if (this.backNumberMesh) {
      this.backNumberMesh.geometry.dispose();
      (this.backNumberMesh.material as THREE.Material).dispose();
    }
    if (this.frontNumberMesh) {
      this.frontNumberMesh.geometry.dispose();
    }
  }
}
