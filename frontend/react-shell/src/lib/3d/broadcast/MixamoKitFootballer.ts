/**
 * Textured 65-bone Mixamo kit used by the live match.
 * The procedural 26-bone rig stays the test fixture. This class is the browser visual.
 */

import * as THREE from "three";
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
  private lodLevel: AnimationLODLevel = "full";
  private shadowCastingEnabled = false;
  private disposed = false;

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
      const visual = shared.template.clone(true);
      tintKitMaterials(visual, this.options);
      fitHeight(visual, 1.78);
      this.modelContainer.add(visual);
      this.modelContainer.remove(placeholder);
      (placeholder as THREE.Mesh).geometry?.dispose();

      this.mixer = new THREE.AnimationMixer(visual);
      for (const state of ALL_FOOTBALL_ANIMATION_STATES) {
        const clip = shared.clips.get(MIXAMO_CLIP_BY_STATE[state]);
        if (!clip) continue;
        const action = this.mixer.clipAction(clip);
        const meta = FOOTBALL_ANIMATION_STATE_META[state];
        action.loop = meta.loop ? THREE.LoopRepeat : THREE.LoopOnce;
        action.clampWhenFinished = !meta.loop;
        this.actions.set(state, action);
      }
      this.play(this.currentState, true);
    } catch {
      // The capsule stays until the kit files are reachable.
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
    const { deltaSec, targetState, position3D, facingAngleRad, speedRatio, cameraPosition3D, hasPossession, qualityTier } = params;
    this.rootGroup.position.set(position3D[0], position3D[1], position3D[2]);
    this.rootGroup.rotation.y = Math.PI / 2 - facingAngleRad;

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
      this.lodLevel = camDist < 38 ? "medium" : "far";
    } else if (isPriorityActor || camDist < 36) {
      this.lodLevel = "full";
    } else if (camDist < 64) {
      this.lodLevel = "medium";
    } else {
      this.lodLevel = "far";
    }
    if (previousLod !== this.lodLevel) this.applyShadowCasting();

    if (targetState !== this.currentState) this.play(targetState, false);
    this.timeInCurrentStateSec += deltaSec;

    const action = this.actions.get(this.currentState);
    if (action) {
      const meta = FOOTBALL_ANIMATION_STATE_META[this.currentState];
      const clamped = Math.min(1, Math.max(0, speedRatio));
      if (meta.category === "locomotion" && this.currentState !== "idle") {
        action.setEffectiveTimeScale(0.85 + clamped * 0.58);
      } else if (this.currentState === "dribble") {
        action.setEffectiveTimeScale(0.92 + clamped * 0.48);
      } else {
        action.setEffectiveTimeScale(1);
      }
    }
    this.mixer?.update(deltaSec);
  }

  private play(state: FootballAnimationState, immediate: boolean): void {
    const next = this.actions.get(state) || this.actions.get("idle");
    const prev = this.actions.get(this.currentState);
    if (prev && prev !== next) {
      if (immediate) prev.stop();
      else prev.fadeOut(0.18);
    }
    if (next && next !== prev) {
      next.reset();
      if (immediate) next.play();
      else next.fadeIn(0.18).play();
    }
    this.currentState = state;
    this.timeInCurrentStateSec = 0;
  }

  public dispose(): void {
    this.disposed = true;
    this.mixer?.stopAllAction();
  }
}

function tintKitMaterials(root: THREE.Object3D, kit: HumanoidKitConfig): void {
  const shirt = new THREE.Color(kit.isGoalkeeper ? kit.goalkeeperColor : kit.primaryColor);
  const shorts = new THREE.Color(kit.shortsColor || kit.secondaryColor || kit.primaryColor);
  const socks = new THREE.Color(kit.socksColor || kit.primaryColor);
  root.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (!mesh.isMesh) return;
    const source = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    mesh.material = source.map((material) => {
      const tinted = material.clone();
      const name = `${material.name} ${mesh.name}`.toLowerCase();
      if (name.includes("tshirt") || name.includes("shirt")) tinted.color = shirt.clone();
      else if (name.includes("short")) tinted.color = shorts.clone();
      else if (name.includes("leg")) tinted.color = socks.clone();
      return tinted;
    });
  });
}

function fitHeight(root: THREE.Object3D, targetMeters: number): void {
  root.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(root);
  const height = box.max.y - box.min.y;
  if (height > 0.4 && height < 3.2) return;
  const scale = targetMeters / Math.max(height, 0.001);
  root.scale.multiplyScalar(scale);
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
    new THREE.PlaneGeometry(0.16, 0.16),
    new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true, depthWrite: false })
  );
  plate.name = "OriginalBadge";
  plate.position.set(0.02, 1.22, 0.14);
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
