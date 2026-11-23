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
import clipContact from "./clipContact.json";

export const MIXAMO_KIT_URL = "/models/footballer/gtex_gt_mixamo_kit.glb";
export const MIXAMO_CLIP_URL = "/models/footballer/gtex_mixamo_clips.glb";
export const CLIP_CONTACT_PHASE: Record<string, number> = clipContact;

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
  dribble_run: "Gtex_Dribble_Run",
  shield_ball: "Playing_With_Ball_Idle",
  cross: "Soccer_Chip_Shot_While_Jogging",
  shoot: "Gtex_Strike",
  volley: "Soccer_Scissor_Kick_To_Goal",
  standing_tackle: "Gtex_Standing_Tackle",
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
  goal_celebration: "Kicking_Up_A_Soccer_Ball",
  disappointment: "Gtex_Slump",
  team_celebration: "Soccer_360_Spin",
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
  "dribble_run",
  "shield_ball",
  "standing_tackle",
  "interception",
  "blocking",
]);

/** Metres one cycle of the clip should carry the body. */
const STRIDE_METERS: Partial<Record<FootballAnimationState, number>> = {
  walk: 1.35,
  jog: 2.15,
  run: 3.1,
  sprint: 3.7,
  dribble: 1.85,
  dribble_run: 3.05,
  shield_ball: 0.7,
};

/** Locomotion cycles that benefit from phase-warped crossfades and transition hysteresis. */
const LOCOMOTION_LOOP_STATES = new Set<FootballAnimationState>([
  "walk",
  "jog",
  "run",
  "sprint",
  "dribble",
  "dribble_run",
  "turn_left",
  "turn_right",
  "accelerate",
  "decelerate",
  "gk_lateral_move",
]);

/**
 * Target body roll (radians) for athletic turn banking.
 * Scales smoothly with both turn demand and ground speed, capped at ±0.22 rad (~12.6°).
 */
export function computeTurnBankingRad(
  yawDeltaRad: number,
  angularVelocityRad: number,
  groundSpeedMps: number
): number {
  const speedScale = Math.min(1, Math.max(0.22, groundSpeedMps / 5.5));
  const turnSignal = yawDeltaRad * 0.52 + angularVelocityRad * 0.14;
  return Math.max(-0.22, Math.min(0.22, -turnSignal * speedScale));
}

/**
 * Target forward torso pitch lean (radians) during high-speed runs/sprints.
 */
export function computeSprintPitchRad(groundSpeedMps: number): number {
  if (groundSpeedMps <= 2.2) return 0;
  return Math.min(0.09, ((groundSpeedMps - 2.2) / 5.5) * 0.09);
}

/** Play the clip once per stride of travel, so the feet land with the body. */
export function clipTimeScale(metersPerSecond: number, strideMeters: number, clipDurationSec: number): number {
  const duration = Math.max(0.2, clipDurationSec);
  const cyclesPerSec = Math.max(0, metersPerSecond) / Math.max(0.4, strideMeters);
  return Math.min(1.85, Math.max(0.4, cyclesPerSec * duration));
}

const BALL_RELEASE_STATES = new Set<string>([
  "short_pass",
  "long_pass",
  "through_ball",
  "cross",
  "shoot",
  "volley",
  "gk_distribution",
  "penalty_kick",
]);

export const PENALTY_CLIP = "Male_Soccer_Penalty_Kick";

export function contactPhaseFor(clipOrState: string): number {
  const clip =
    clipOrState === "penalty_kick"
      ? PENALTY_CLIP
      : MIXAMO_CLIP_BY_STATE[clipOrState as FootballAnimationState] || clipOrState;
  const phase = CLIP_CONTACT_PHASE[clip];
  return typeof phase === "number" ? phase : 0.45;
}

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
  if (speed < 5.5) return hasPossession ? "dribble_run" : "run";
  return hasPossession ? "dribble_run" : "sprint";
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
  const renamed = retargetMixamoClip(clip, boneNamesOf(root));
  // All non-hip bones in gtex_gt_mixamo_kit.glb share the standard Mixamo local bone axes with
  // gtex_mixamo_clips.glb. Applying the renamed quaternion tracks directly preserves natural
  // athletic poses (arms lowered, running swing, strikes) instead of locking arms in T-pose.
  const tracks = renamed.tracks.filter(
    (track) => !track.name.endsWith(".scale") && !track.name.endsWith(".position"),
  );
  return new THREE.AnimationClip(renamed.name, renamed.duration, tracks);
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
  private readonly actions = new Map<string, THREE.AnimationAction>();
  private currentState: FootballAnimationState = "idle";
  private clipKey: string = "idle";
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
  private readonly forwardScratch = new THREE.Vector3();
  private supportSide: "left" | "right" | null = null;
  private readonly supportLock = new THREE.Vector3();
  private readonly visualSlip = new THREE.Vector3();

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
      const penalty = shared.clips.get(PENALTY_CLIP);
      if (penalty) {
        const action = this.mixer.clipAction(clipForThisRig(penalty, visual));
        action.loop = THREE.LoopOnce;
        action.clampWhenFinished = true;
        this.actions.set("penalty_kick", action);
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
    eventType?: string | null;
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
    const eventName = String(params.eventType || "").toLowerCase();
    const clipId = visualState === "shoot" && eventName === "penalty" ? "penalty_kick" : visualState;
    const bothLocomotion =
      LOCOMOTION_LOOP_STATES.has(this.currentState) && LOCOMOTION_LOOP_STATES.has(visualState);
    const allowTransition =
      clipId !== this.clipKey || visualState !== this.currentState
        ? !bothLocomotion || this.timeInCurrentStateSec >= 0.16
        : false;
    if (allowTransition) {
      this.play(visualState, false, clipId);
    }
    this.timeInCurrentStateSec += deltaSec;

    const action = this.actions.get(this.clipKey);
    if (action) {
      const stride = STRIDE_METERS[this.currentState];
      if (stride) {
        action.setEffectiveTimeScale(clipTimeScale(this.smoothedSpeed, stride, action.getClip().duration));
      } else {
        action.setEffectiveTimeScale(1);
      }
    }
    this.mixer?.update(deltaSec);
    this.leanIntoTurn(yawDelta, deltaSec, angular, this.smoothedSpeed);
    if (this.lodLevel === "full" && this.leftFoot && this.rightFoot) {
      // Sample foot world positions ONCE per frame instead of walking the 65-bone hierarchy twice.
      this.leftFoot.getWorldPosition(this.leftFootWorld);
      this.rightFoot.getWorldPosition(this.rightFootWorld);
      this.plantFeetFromSampled(deltaSec);
      this.settleSupportFootFromSampled();
    } else if (this.supportSide !== null) {
      this.releaseSupport();
    }
  }

  /** Drops a near-ground stride onto the pitch using already-sampled foot world positions. */
  private plantFeetFromSampled(deltaSec = 1 / 60): void {
    const lowest = Math.min(this.leftFootWorld.y, this.rightFootWorld.y);
    const error = this.rootGroup.position.y + 0.02 - lowest;
    if (error > -0.26 && error < 0.2) {
      const alpha = 1 - Math.exp(-Math.max(deltaSec, 0.001) * 18);
      this.modelContainer.position.y += error * alpha;
    }
  }

  /**
   * Banks the torso into turns proportional to running speed and adds subtle
   * forward sprint lean so cuts and accelerations feel athletic rather than rigid.
   */
  private leanIntoTurn(
    yawDelta: number,
    deltaSec: number,
    angularVelocityRad: number,
    groundSpeedMps: number
  ): void {
    const dt = Math.max(deltaSec, 0.001);
    const targetRoll = computeTurnBankingRad(yawDelta, angularVelocityRad, groundSpeedMps);
    const rollAlpha = 1 - Math.exp(-dt * 9.5);
    this.modelContainer.rotation.z += (targetRoll - this.modelContainer.rotation.z) * rollAlpha;

    const targetPitch = computeSprintPitchRad(groundSpeedMps);
    const pitchAlpha = 1 - Math.exp(-dt * 7.5);
    this.modelContainer.rotation.x += (targetPitch - this.modelContainer.rotation.x) * pitchAlpha;
  }

  /**
   * Holds the stance foot where it landed, up to a short slip, so the cycle
   * does not skate under a body the match is moving.
   */
  private settleSupportFootFromSampled(): void {
    const stride = STRIDE_METERS[this.currentState];
    if (!stride) {
      this.releaseSupport();
      return;
    }
    const leftLow = this.leftFootWorld.y < 0.16;
    const rightLow = this.rightFootWorld.y < 0.16;
    let side: "left" | "right" | null = null;
    let foot = this.leftFootWorld;
    if (leftLow || rightLow) {
      side = rightLow && (!leftLow || this.rightFootWorld.y < this.leftFootWorld.y) ? "right" : "left";
      foot = side === "left" ? this.leftFootWorld : this.rightFootWorld;
    }
    if (side && side === this.supportSide) {
      this.visualSlip.x = Math.max(-0.16, Math.min(0.16, this.visualSlip.x + (this.supportLock.x - foot.x)));
      this.visualSlip.z = Math.max(-0.16, Math.min(0.16, this.visualSlip.z + (this.supportLock.z - foot.z)));
      this.modelContainer.position.x = this.visualSlip.x;
      this.modelContainer.position.z = this.visualSlip.z;
      return;
    }
    if (side) {
      this.supportSide = side;
      this.supportLock.set(foot.x, 0, foot.z);
      return;
    }
    this.releaseSupport();
  }

  private releaseSupport(): void {
    this.supportSide = null;
    this.visualSlip.x *= 0.55;
    this.visualSlip.z *= 0.55;
    this.modelContainer.position.x = this.visualSlip.x;
    this.modelContainer.position.z = this.visualSlip.z;
  }

  /** Keeps a controlled ball on the leading foot until a kick's contact frame. */
  public holdsBall(): boolean {
    if (BALL_RELEASE_STATES.has(this.clipKey)) {
      const action = this.actions.get(this.clipKey);
      const duration = action?.getClip().duration || 1;
      return this.timeInCurrentStateSec < contactPhaseFor(this.clipKey) * duration;
    }
    return (
      this.currentState === "dribble" ||
      this.currentState === "dribble_run" ||
      this.currentState === "shield_ball" ||
      this.currentState === "receive_ball" ||
      this.currentState === "first_touch"
    );
  }

  public placeBall(out: THREE.Vector3): boolean {
    if (!this.leftFoot || !this.rightFoot) return false;
    this.leftFoot.getWorldPosition(this.leftFootWorld);
    this.rightFoot.getWorldPosition(this.rightFootWorld);
    this.forwardScratch.set(0, 0, 1).applyQuaternion(this.rootGroup.quaternion);
    const leftLead = this.leftFootWorld.dot(this.forwardScratch);
    const rightLead = this.rightFootWorld.dot(this.forwardScratch);
    const foot = leftLead >= rightLead ? this.leftFootWorld : this.rightFootWorld;
    out.copy(foot);
    out.addScaledVector(this.forwardScratch, 0.11);
    out.y = Math.max(0.1, foot.y);
    return true;
  }

  private play(state: FootballAnimationState, immediate: boolean, clipId: string = state): void {
    const next = this.actions.get(clipId) || this.actions.get(state) || this.actions.get("idle");
    const prev = this.actions.get(this.clipKey);
    const prevState = this.currentState;
    if (!next) {
      this.currentState = state;
      this.clipKey = clipId;
      this.timeInCurrentStateSec = 0;
      return;
    }
    const meta = FOOTBALL_ANIMATION_STATE_META[state];
    const bothLocomotion = LOCOMOTION_LOOP_STATES.has(prevState) && LOCOMOTION_LOOP_STATES.has(state);
    const fade = Math.max(
      meta.loop ? (bothLocomotion ? 0.24 : 0.28) : 0.11,
      meta.crossFadeSec
    );
    // The first call is already "idle", so next and prev are the same action.
    // That action still has to start, or the body stays in the bind pose.
    if (next !== prev || !next.isRunning()) {
      next.enabled = true;
      next.reset().setEffectiveWeight(1);
      if (immediate || !prev || prev === next) {
        if (prev && prev !== next) prev.stop();
        next.play();
      } else {
        next.play();
        prev.crossFadeTo(next, fade, bothLocomotion);
      }
    }
    this.currentState = state;
    this.clipKey = clipId;
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
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nuniform vec3 uKitTint;")
      .replace(
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

/**
 * Measures the true world-space bounds of a skinned footballer hierarchy.
 * `Box3.setFromObject` under-reports `gtex_gt_mixamo_kit.glb` at ~0.28m due to its
 * pre-rotated Armature/bind transform, so we sample skinned vertices directly.
 */
export function measureSkinnedBounds(root: THREE.Object3D): THREE.Box3 {
  root.updateMatrixWorld(true);
  const box = new THREE.Box3();
  const vertex = new THREE.Vector3();
  let sampled = false;
  root.traverse((obj) => {
    const skinned = obj as THREE.SkinnedMesh;
    if (skinned.isSkinnedMesh && skinned.geometry?.attributes?.position && skinned.skeleton) {
      skinned.skeleton.update();
      const pos = skinned.geometry.attributes.position;
      const step = Math.max(1, Math.floor(pos.count / 240));
      for (let i = 0; i < pos.count; i += step) {
        vertex.fromBufferAttribute(pos, i);
        skinned.applyBoneTransform(i, vertex);
        skinned.localToWorld(vertex);
        if (Number.isFinite(vertex.x) && Number.isFinite(vertex.y) && Number.isFinite(vertex.z)) {
          box.expandByPoint(vertex);
          sampled = true;
        }
      }
    }
  });
  if (!sampled || box.isEmpty()) {
    return new THREE.Box3().setFromObject(root);
  }
  return box;
}

export function fitAndGround(root: THREE.Object3D, targetHeight = 1.83): THREE.Box3 {
  let box = measureSkinnedBounds(root);
  const height = box.max.y - box.min.y;
  if (height > 0.2 && (height < targetHeight * 0.9 || height > targetHeight * 1.07)) {
    root.scale.multiplyScalar(targetHeight / height);
    box = measureSkinnedBounds(root);
  }
  const centerX = (box.min.x + box.max.x) * 0.5;
  const centerZ = (box.min.z + box.max.z) * 0.5;
  root.position.x -= centerX;
  root.position.y -= box.min.y;
  root.position.z -= centerZ;
  return measureSkinnedBounds(root);
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
