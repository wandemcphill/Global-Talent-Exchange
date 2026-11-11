/**
 * Textured 65-bone Mixamo kit used by the live match.
 * The procedural 26-bone rig stays the test fixture. This class is the browser visual.
 */

import * as THREE from "three";
import { clone as cloneSkinned } from "three/examples/jsm/utils/SkeletonUtils.js";
import { AssetStreamingCache } from "./AssetStreamingCache";
import {
  ALL_FOOTBALL_ANIMATION_STATES,
  FOOTBALL_ANIMATION_STATE_META,
  type FootballAnimationState,
} from "./FootballAnimationStateMachine";
import {
  resolvePlayerAppearanceProfile,
  type AnimationLODLevel,
  type HumanoidKitConfig,
  type PlayerAppearanceProfile,
} from "./HumanoidFootballerRig";
import type { DeviceQualityTier } from "../GtexSceneTypes";

export const MIXAMO_KIT_URL = "/models/footballer/gtex_home_kit_mixamo.glb";
export const MIXAMO_CLIP_URL = "/models/footballer/gtex_mixamo_clips.glb";

/** Every match state plays one baked Mixamo clip. Names match the GLB clip names. */
export const MIXAMO_CLIP_BY_STATE: Record<FootballAnimationState, string> = {
  idle: "Breathing_Idle",
  walk: "Walking_Forwards",
  jog: "Soccer_Jog_Forward",
  run: "Running_Forwards",
  sprint: "Running_Forwards",
  turn_left: "Soccer_Strafe_Left",
  turn_right: "Soccer_Strafe_Right",
  accelerate: "Soccer_Jog_Forward",
  decelerate: "Soccer_Jog_Backward",
  stop_change_direction: "Soccer_360_Spin",
  receive_ball: "Receiving_A_Soccerball_And_Playing_With_It",
  first_touch: "Soccer_Idle_Chest_Receive",
  short_pass: "Soccer_Pass_From_Idle_Pose",
  long_pass: "Jogging_And_Kicking_A_Soccerball_Forward",
  through_ball: "Soccer_Chip_Shot_While_Jogging",
  dribble: "Forward_Jog_Dribbling_Soccer_Ball",
  shield_ball: "Playing_With_Ball_Idle",
  cross: "Soccer_Chip_Shot_While_Jogging",
  shoot: "Male_Soccer_Penalty_Kick",
  volley: "Soccer_Scissor_Kick_To_Goal",
  standing_tackle: "Soccer_Slide_Tackle",
  sliding_tackle: "Soccer_Slide_Tackle",
  interception: "Soccer_Strafe_Left",
  blocking: "Goalkeeper_Left_Body_Block",
  jumping_challenge: "Idle_Soccer_Header",
  tackle_recovery: "Standing_Up_From_A_Soccer_Fall",
  gk_ready_stance: "Goalkeeper_Idle_Without_Ball",
  gk_lateral_move: "Goalkeeper_Left_Sidestep",
  gk_dive_low: "Goalkeeper_Left_Diving_Save",
  gk_dive_high: "Goalkeeper_Jump_Catching_Ball_High_Height",
  gk_catch: "Goalkeeper_Catching_Ball_Medium_Height",
  gk_parry: "Goalkeeper_Right_Body_Block",
  gk_punch: "Goalkeeper_Far_Overhand_Throw",
  gk_distribution: "Goalkeeper_Drop_Kicking_Ball",
  goal_celebration: "Soccer_360_Spin",
  disappointment: "Goalkeeper_Jump_And_Miss",
  team_celebration: "Kicking_Up_A_Soccer_Ball",
  injury_reaction: "Hurt_Ground_Idle_From_A_Soccer_Fall",
  foul_reaction: "Tripping_Over_A_Soccer_Tackle",
  substitution_exit: "Walking_Forwards",
  substitution_enter: "Soccer_Jog_Forward",
};

interface SharedMixamoKit {
  template: THREE.Object3D;
  clips: Map<string, THREE.AnimationClip>;
}

let sharedKit: Promise<SharedMixamoKit> | null = null;

function loadSharedKit(): Promise<SharedMixamoKit> {
  if (!sharedKit) {
    sharedKit = (async () => {
      const cache = AssetStreamingCache.getInstance();
      const [kit, anim] = await Promise.all([
        cache.loadGltf(MIXAMO_KIT_URL),
        cache.loadGltf(MIXAMO_CLIP_URL),
      ]);
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

export function everyFootballStateHasMixamoClip(): boolean {
  return ALL_FOOTBALL_ANIMATION_STATES.every((state) => Boolean(MIXAMO_CLIP_BY_STATE[state]));
}

/** These requests describe intent, not how fast the body is actually travelling. */
const GAIT_FROM_TRAVEL = new Set<FootballAnimationState>([
  "idle",
  "walk",
  "jog",
  "run",
  "sprint",
  "turn_left",
  "turn_right",
  "accelerate",
  "decelerate",
  "stop_change_direction",
  "dribble",
  "shield_ball",
  "standing_tackle",
  "interception",
  "blocking",
]);

/** Metres per second a clip looks right at timescale 1. */
const GAIT_NOMINAL_MPS: Partial<Record<FootballAnimationState, number>> = {
  walk: 1.35,
  jog: 3.0,
  run: 5.0,
  sprint: 6.6,
  dribble: 2.6,
  shield_ball: 0.4,
};

/**
 * Pick the clip from measured travel. The fixture's speed_ratio is inflated so a
 * walking body was playing a sprint, which reads as skating.
 */
export function gaitForGroundSpeed(
  metersPerSecond: number,
  hasPossession: boolean
): FootballAnimationState {
  const speed = Math.max(0, metersPerSecond);
  if (speed < 0.45) return hasPossession ? "shield_ball" : "idle";
  if (speed < 1.65) return "walk";
  if (speed < 3.4) return hasPossession ? "dribble" : "jog";
  if (speed < 5.5) return hasPossession ? "dribble" : "run";
  return hasPossession ? "dribble" : "sprint";
}

function boneKey(name: string): string {
  return name.replace(/[^a-z0-9]/gi, "").toLowerCase();
}

/**
 * Mixamo clips and the kit skeleton do not share a node-name spelling
 * (`mixamorigHips` vs `mixamorig:Hips`). GLTFLoader strips the colon, but a
 * clip baked before that still will not bind. Hip tracks are dropped: this
 * rig's rest pose already holds the axis correction, and root motion would
 * fold the body and skate the feet.
 */
export function retargetMixamoClip(clip: THREE.AnimationClip, boneNames: string[]): THREE.AnimationClip {
  const resolved = new Map<string, string>();
  for (const name of boneNames) resolved.set(boneKey(name), name);
  const tracks: THREE.KeyframeTrack[] = [];
  for (const track of clip.tracks) {
    const dot = track.name.lastIndexOf(".");
    if (dot <= 0) continue;
    const key = boneKey(track.name.slice(0, dot));
    if (key.endsWith("hips")) continue;
    const bone = resolved.get(key);
    if (!bone) continue;
    const next = track.clone();
    next.name = `${bone}.${track.name.slice(dot + 1)}`;
    tracks.push(next);
  }
  return new THREE.AnimationClip(clip.name, clip.duration, tracks);
}

function boneNamesOf(root: THREE.Object3D): string[] {
  const names: string[] = [];
  root.traverse((obj) => {
    if (obj.name) names.push(obj.name);
  });
  return names;
}

function clipForThisRig(clip: THREE.AnimationClip, root: THREE.Object3D): THREE.AnimationClip {
  return retargetMixamoClip(clip, boneNamesOf(root));
}

function findBone(root: THREE.Object3D, suffix: string): THREE.Object3D | null {
  const needle = boneKey(suffix);
  let found: THREE.Object3D | null = null;
  root.traverse((obj) => {
    if (found || !obj.name) return;
    if (boneKey(obj.name) === needle) found = obj;
  });
  return found;
}

/** Standing clip for desks and portraits. The caller updates the mixer each frame. */
export async function attachKitIdle(root: THREE.Object3D): Promise<THREE.AnimationMixer | null> {
  const shared = await loadSharedKit();
  const clip = shared.clips.get(MIXAMO_CLIP_BY_STATE.idle);
  if (!clip) return null;
  const mixer = new THREE.AnimationMixer(root);
  mixer.clipAction(clipForThisRig(clip, root)).play();
  return mixer;
}

export class MixamoKitFootballer {
  public readonly playerId: string;
  public readonly rootGroup: THREE.Group;
  public readonly options: HumanoidKitConfig;
  public readonly appearanceProfile: PlayerAppearanceProfile;
  private readonly modelContainer: THREE.Group;
  private mixer: THREE.AnimationMixer | null = null;
  private readonly actions = new Map<FootballAnimationState, THREE.AnimationAction>();
  private currentState: FootballAnimationState = "idle";
  private timeInCurrentStateSec = 0;
  private lastPosition: [number, number, number] | null = null;
  private smoothedSpeed = 0;
  private stillSec = 0;
  private lastMovingGait: FootballAnimationState = "jog";
  private lodLevel: AnimationLODLevel = "full";
  private shadowCastingEnabled = false;
  private disposed = false;
  private leftFoot: THREE.Object3D | null = null;
  private rightFoot: THREE.Object3D | null = null;
  private readonly leftFootWorld = new THREE.Vector3();
  private readonly rightFootWorld = new THREE.Vector3();

  constructor(kitConfig: HumanoidKitConfig) {
    this.playerId = kitConfig.playerId;
    this.options = kitConfig;
    this.appearanceProfile = resolvePlayerAppearanceProfile(kitConfig);
    this.rootGroup = new THREE.Group();
    this.rootGroup.name = `MixamoKit_${kitConfig.playerId}`;
    this.modelContainer = new THREE.Group();
    this.modelContainer.name = "MixamoKitModel";
    this.rootGroup.add(this.modelContainer);

    const shirt = kitConfig.isGoalkeeper ? kitConfig.goalkeeperColor : kitConfig.primaryColor;
    const placeholder = new THREE.Mesh(
      new THREE.CapsuleGeometry(0.26, 1.05, 4, 8),
      new THREE.MeshStandardMaterial({ color: shirt || "#104A3A", roughness: 0.6 })
    );
    placeholder.name = "KitPlaceholder";
    placeholder.position.y = 0.95;
    this.modelContainer.add(placeholder);
    this.modelContainer.add(makeShirtNumber(kitConfig.shirtNumber, kitConfig.accentColor || "#ECE0C4"));
    this.modelContainer.add(makeOriginalBadge());

    void this.attachSharedKit(placeholder);
  }

  private async attachSharedKit(placeholder: THREE.Object3D): Promise<void> {
    try {
      const shared = await loadSharedKit();
      if (this.disposed) return;
      const visual = cloneSkinned(shared.template);
      tintKitMaterials(visual, this.options);
      fitAndGround(visual);
      visual.traverse((obj) => {
        const skinned = obj as THREE.SkinnedMesh;
        if (skinned.isSkinnedMesh) skinned.frustumCulled = false;
      });
      this.modelContainer.add(visual);
      this.modelContainer.remove(placeholder);
      (placeholder as THREE.Mesh).geometry?.dispose();
      this.attachKitIdentity(visual);
      this.leftFoot = findBone(visual, "mixamorigLeftToeBase") || findBone(visual, "mixamorigLeftFoot");
      this.rightFoot = findBone(visual, "mixamorigRightToeBase") || findBone(visual, "mixamorigRightFoot");

      this.mixer = new THREE.AnimationMixer(visual);
      for (const state of ALL_FOOTBALL_ANIMATION_STATES) {
        const clip = shared.clips.get(MIXAMO_CLIP_BY_STATE[state]);
        if (!clip) continue;
        const action = this.mixer.clipAction(clipForThisRig(clip, visual));
        const meta = FOOTBALL_ANIMATION_STATE_META[state];
        action.loop = meta.loop ? THREE.LoopRepeat : THREE.LoopOnce;
        action.clampWhenFinished = !meta.loop;
        this.actions.set(state, action);
      }
      this.play(this.currentState, true);
      this.applyShadowCasting();
    } catch {
      // The capsule stays until the kit files are reachable.
    }
  }

  /** Shirt number and crest follow the chest bone instead of floating in world space. */
  private attachKitIdentity(visual: THREE.Object3D): void {
    const chest = findBone(visual, "mixamorigSpine2") || findBone(visual, "mixamorigSpine1");
    if (!chest) return;
    const number = this.modelContainer.getObjectByName("ShirtNumber");
    const badge = this.modelContainer.getObjectByName("OriginalBadge");
    if (number) {
      chest.add(number);
      number.position.set(0, 0.04, -0.16);
      number.rotation.set(0, Math.PI, 0);
      number.scale.setScalar(0.7);
    }
    if (badge) {
      chest.add(badge);
      badge.position.set(0.07, 0.08, 0.15);
      badge.rotation.set(0, 0, 0);
      badge.scale.setScalar(0.62);
    }
  }

  public getCurrentState(): FootballAnimationState {
    return this.currentState;
  }

  public getTimeInCurrentState(): number {
    return this.timeInCurrentStateSec;
  }

  public get appearance(): PlayerAppearanceProfile {
    return this.appearanceProfile;
  }

  public getLODLevel(): AnimationLODLevel {
    return this.lodLevel;
  }

  public setShadowCasting(enabled: boolean): void {
    this.shadowCastingEnabled = enabled;
    this.applyShadowCasting();
  }

  private applyShadowCasting(): void {
    const enabled = this.shadowCastingEnabled && this.lodLevel !== "far";
    this.rootGroup.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (mesh.isMesh) mesh.castShadow = enabled;
    });
  }

  public update(params: {
    deltaSec: number;
    targetState: FootballAnimationState;
    position3D: [number, number, number];
    facingAngleRad: number;
    speedRatio: number;
    hasPossession: boolean;
    ballPosition3D: [number, number, number];
    cameraPosition3D: [number, number, number];
    qualityTier?: DeviceQualityTier;
    angularVelocityRad?: number;
  }): void {
    const { deltaSec, targetState, position3D, facingAngleRad, cameraPosition3D, hasPossession, qualityTier } = params;
    const angular = params.angularVelocityRad ?? 0;
    this.rootGroup.position.set(position3D[0], position3D[1], position3D[2]);
    const targetYaw = Math.PI / 2 - facingAngleRad;
    let yawDelta = targetYaw - this.rootGroup.rotation.y;
    yawDelta = Math.atan2(Math.sin(yawDelta), Math.cos(yawDelta));
    const turnRate = Math.abs(yawDelta) > 1.1 ? 14 : 8;
    this.rootGroup.rotation.y += yawDelta * (1 - Math.exp(-Math.max(deltaSec, 0) * turnRate));

    let groundSpeed = 0;
    if (this.lastPosition) {
      const step = Math.hypot(
        position3D[0] - this.lastPosition[0],
        position3D[2] - this.lastPosition[2]
      );
      groundSpeed = Math.min(12, step / Math.max(deltaSec, 1 / 120));
    }
    this.lastPosition = [position3D[0], position3D[1], position3D[2]];
    const blend = Math.min(1, deltaSec * 5);
    this.smoothedSpeed += (groundSpeed - this.smoothedSpeed) * blend;

    const camDist = Math.hypot(
      cameraPosition3D[0] - position3D[0],
      cameraPosition3D[1] - position3D[1],
      cameraPosition3D[2] - position3D[2]
    );
    const stateMeta = FOOTBALL_ANIMATION_STATE_META[targetState];
    const isPriorityActor =
      hasPossession ||
      stateMeta.category === "ball_interaction" ||
      stateMeta.category === "goalkeeper_action" ||
      stateMeta.category === "match_reaction";
    const previousLod = this.lodLevel;
    if (qualityTier === "low" && !isPriorityActor) {
      this.lodLevel = camDist < 62 ? "medium" : "far";
    } else if (isPriorityActor || camDist < 72) {
      this.lodLevel = "full";
    } else if (camDist < 115) {
      this.lodLevel = "medium";
    } else {
      this.lodLevel = "far";
    }
    if (previousLod !== this.lodLevel) this.applyShadowCasting();

    let visualState = targetState;
    if (GAIT_FROM_TRAVEL.has(targetState)) {
      if (this.smoothedSpeed >= 0.4) {
        this.stillSec = 0;
        visualState = gaitForGroundSpeed(this.smoothedSpeed, hasPossession);
        this.lastMovingGait = visualState;
      } else {
        this.stillSec += deltaSec;
        // Keep the stride through a short stop so the run does not cut to a statue.
        visualState =
          this.stillSec < 0.22
            ? this.lastMovingGait
            : gaitForGroundSpeed(0, hasPossession);
      }
    }
    if (
      Math.abs(angular) > 1.35 &&
      this.smoothedSpeed > 0.45 &&
      this.smoothedSpeed < 2.6 &&
      (visualState === "walk" || visualState === "jog" || visualState === "dribble")
    ) {
      visualState = angular > 0 ? "turn_right" : "turn_left";
    }
    if (visualState !== this.currentState) this.play(visualState, false);
    this.timeInCurrentStateSec += deltaSec;

    const action = this.actions.get(this.currentState);
    if (action) {
      const nominal = GAIT_NOMINAL_MPS[this.currentState];
      if (nominal) {
        const pace = this.smoothedSpeed / nominal;
        action.setEffectiveTimeScale(Math.min(1.45, Math.max(0.62, pace)));
      } else {
        action.setEffectiveTimeScale(1);
      }
    }
    this.mixer?.update(deltaSec);
    this.plantFeet();
  }

  /** Drops a near-ground stride onto the pitch. Jumps and headers are left in the air. */
  private plantFeet(): void {
    if (!this.leftFoot || !this.rightFoot) return;
    this.leftFoot.getWorldPosition(this.leftFootWorld);
    this.rightFoot.getWorldPosition(this.rightFootWorld);
    const lowest = Math.min(this.leftFootWorld.y, this.rightFootWorld.y);
    const error = this.rootGroup.position.y + 0.02 - lowest;
    if (error > -0.26 && error < 0.2) this.modelContainer.position.y += error;
  }

  private play(state: FootballAnimationState, immediate: boolean): void {
    const next = this.actions.get(state) || this.actions.get("idle");
    const prev = this.actions.get(this.currentState);
    if (!next) {
      this.currentState = state;
      this.timeInCurrentStateSec = 0;
      return;
    }
    const fade = Math.max(FOOTBALL_ANIMATION_STATE_META[state].loop ? 0.26 : 0.12, FOOTBALL_ANIMATION_STATE_META[state].crossFadeSec);
    if (prev && prev !== next) {
      if (immediate) prev.stop();
      else prev.fadeOut(fade);
    }
    // The first call is already "idle", so next and prev are the same action.
    // That action still has to start, or the body stays in the bind pose.
    if (next !== prev || !next.isRunning()) {
      next.reset().setEffectiveWeight(1);
      if (immediate || !prev || prev === next) next.play();
      else next.fadeIn(fade).play();
    }
    this.currentState = state;
    this.timeInCurrentStateSec = 0;
  }

  public dispose(): void {
    this.disposed = true;
    this.mixer?.stopAllAction();
  }
}

function kitTint(source: THREE.Color): THREE.Color {
  const hsl = { h: 0, s: 0, l: 0 };
  source.getHSL(hsl);
  const saturation = hsl.s > 0.82 ? 0.7 : hsl.s;
  const lightness = Math.min(0.58, Math.max(0.24, hsl.l));
  return new THREE.Color().setHSL(hsl.h, saturation, lightness);
}

/**
 * Keeps the authored albedo (fabric weave, seams, boots) and replaces only the hue.
 * Multiplying a saturated texture by the team colour crushes it to a flat blob.
 */
function recolorCloth(material: THREE.MeshStandardMaterial, tint: THREE.Color): void {
  material.color.set(0xffffff);
  material.metalness = 0;
  material.roughness = material.roughnessMap ? material.roughness : 0.72;
  material.envMapIntensity = 0.22;
  material.emissive?.set(0x000000);
  material.userData.gtexFixedEnv = 0.22;
  if (material.map) {
    material.map.anisotropy = Math.max(material.map.anisotropy || 0, 8);
    material.map.colorSpace = THREE.SRGBColorSpace;
  }
  const tintUniform = { value: tint.clone() };
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uKitTint = tintUniform;
    shader.fragmentShader = shader.fragmentShader.replace(
      "#include <map_fragment>",
      `#include <map_fragment>
       float kitLuma = dot(diffuseColor.rgb, vec3(0.299, 0.587, 0.114));
       diffuseColor.rgb = uKitTint * (0.4 + kitLuma * 1.05);`
    );
  };
  material.customProgramCacheKey = () => `gtex-kit-${tint.getHexString()}`;
}

function tintKitMaterials(root: THREE.Object3D, kit: HumanoidKitConfig): void {
  const shirt = kitTint(new THREE.Color(kit.isGoalkeeper ? kit.goalkeeperColor : kit.primaryColor));
  const shorts = kitTint(new THREE.Color(kit.shortsColor || kit.secondaryColor || kit.primaryColor));
  const socks = kitTint(new THREE.Color(kit.socksColor || kit.primaryColor));
  root.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (!mesh.isMesh) return;
    const source = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    const tinted = source.map((material) => {
      const next = material.clone() as THREE.MeshStandardMaterial;
      const name = `${material.name} ${mesh.name}`.toLowerCase();
      if (name.includes("tshirt") || name.includes("shirt")) recolorCloth(next, shirt);
      else if (name.includes("short")) recolorCloth(next, shorts);
      else if (name.includes("leg")) recolorCloth(next, socks);
      else if (name.includes("head")) {
        next.roughness = 0.5;
        next.envMapIntensity = 0.3;
        next.userData.gtexFixedEnv = 0.3;
        if (next.map) next.map.anisotropy = Math.max(next.map.anisotropy || 0, 8);
      } else if (name.includes("hand")) {
        next.roughness = 0.58;
        next.envMapIntensity = 0.22;
        next.userData.gtexFixedEnv = 0.22;
      }
      return next;
    });
    // A one-element material array draws nothing when the geometry has no groups.
    mesh.material = tinted.length === 1 ? tinted[0] : tinted;
  });
}

function fitAndGround(root: THREE.Object3D): void {
  root.updateMatrixWorld(true);
  let box = new THREE.Box3().setFromObject(root);
  const height = box.max.y - box.min.y;
  if (height > 0.2 && (height < 1.65 || height > 1.96)) {
    root.scale.multiplyScalar(1.83 / height);
    root.updateMatrixWorld(true);
    box = new THREE.Box3().setFromObject(root);
  }
  root.position.y -= box.min.y;
}

function makeOriginalBadge(): THREE.Mesh {
  const canvas = document.createElement("canvas");
  canvas.width = 128;
  canvas.height = 128;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.clearRect(0, 0, 128, 128);
    ctx.fillStyle = "#104A3A";
    ctx.beginPath();
    ctx.arc(64, 64, 46, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "#D4A84A";
    ctx.lineWidth = 8;
    ctx.stroke();
    ctx.fillStyle = "#ECE0C4";
    ctx.font = "700 54px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("G", 64, 68);
  }
  const plate = new THREE.Mesh(
    new THREE.PlaneGeometry(0.22, 0.22),
    new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true, depthWrite: false })
  );
  plate.name = "OriginalBadge";
  plate.position.set(0.01, 1.28, 0.18);
  return plate;
}

function makeShirtNumber(shirtNumber: number, ink: string): THREE.Mesh {
  const canvas = document.createElement("canvas");
  canvas.width = 128;
  canvas.height = 128;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.clearRect(0, 0, 128, 128);
    ctx.fillStyle = ink;
    ctx.font = "700 72px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(String(shirtNumber), 64, 68);
  }
  const texture = new THREE.CanvasTexture(canvas);
  const plate = new THREE.Mesh(
    new THREE.PlaneGeometry(0.42, 0.42),
    new THREE.MeshBasicMaterial({ map: texture, transparent: true, depthWrite: false })
  );
  plate.name = "ShirtNumber";
  plate.position.set(0, 1.38, -0.16);
  plate.rotation.y = Math.PI;
  return plate;
}
