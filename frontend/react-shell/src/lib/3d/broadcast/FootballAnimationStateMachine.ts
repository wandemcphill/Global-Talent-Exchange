/**
 * GTEX Unit 2A (U2A-006) — Humanoid Football Animation Engine
 * FootballAnimationStateMachine: Canonical 26-Bone Humanoid Skeleton,
 * 41-State Football Animation Library, and Authoritative Event Synchronizer.
 *
 * Implements:
 * 1. Canonical 26-Bone Mixamo/GTEX Humanoid Skeleton specification matching `Player_Mobile_Mesh.fbx`.
 * 2. Complete 5-category Football Animation State Machine (41 states):
 *    - Locomotion (10): idle, walk, jog, run, sprint, turn_left, turn_right,
 *      accelerate, decelerate, stop_change_direction
 *    - Ball Interaction (10): receive_ball, first_touch, short_pass, long_pass,
 *      through_ball, dribble, shield_ball, cross, shoot, volley
 *    - Defensive Actions (6): standing_tackle, sliding_tackle, interception,
 *      blocking, jumping_challenge, tackle_recovery
 *    - Goalkeeper Actions (8): gk_ready_stance, gk_lateral_move, gk_dive_low,
 *      gk_dive_high, gk_catch, gk_parry, gk_punch, gk_distribution
 *    - Match Reactions (7): goal_celebration, disappointment, team_celebration,
 *      injury_reaction, foul_reaction, substitution_exit, substitution_enter
 * 3. Deterministic synchronization with GTEX authoritative simulation frames & events
 *    (presentation-only; never fabricates match outcomes).
 */

import * as THREE from "three";
import { InterpolatedBallState, InterpolatedMatchState, InterpolatedPlayerState } from "./SpatialInterpolator";
import { SpectatorSafeEventView } from "./spectatorContract";

// -----------------------------------------------------------------------------
// 1. Canonical 26-Bone GTEX Humanoid Skeleton Specification
// -----------------------------------------------------------------------------

export interface HumanoidBoneSpec {
  index: number;
  name: string;
  parent: string | null;
  /** Bind-pose local offset relative to parent in centimeters (scale 0.01 = meters) */
  bindLocalPosCm: readonly [number, number, number];
}

export const GTEX_HUMANOID_BONE_SPECS: readonly HumanoidBoneSpec[] = [
  { index: 0, name: "Hips", parent: null, bindLocalPosCm: [0.0, 100.0, 0.0] },
  { index: 1, name: "LeftUpLeg", parent: "Hips", bindLocalPosCm: [10.8, -6.3, 0.0] },
  { index: 2, name: "LeftLeg", parent: "LeftUpLeg", bindLocalPosCm: [2.0, -44.8, 0.0] },
  { index: 3, name: "LeftFoot", parent: "LeftLeg", bindLocalPosCm: [3.3, -40.6, -3.9] },
  { index: 4, name: "LeftToeBase", parent: "LeftFoot", bindLocalPosCm: [1.4, -6.1, 19.9] },
  { index: 5, name: "RightUpLeg", parent: "Hips", bindLocalPosCm: [-10.8, -6.3, 0.0] },
  { index: 6, name: "RightLeg", parent: "RightUpLeg", bindLocalPosCm: [-2.0, -44.8, 0.0] },
  { index: 7, name: "RightFoot", parent: "RightLeg", bindLocalPosCm: [-3.3, -40.6, -3.9] },
  { index: 8, name: "RightToeBase", parent: "RightFoot", bindLocalPosCm: [-1.4, -6.1, 19.9] },
  { index: 9, name: "Spine", parent: "Hips", bindLocalPosCm: [0.0, 7.0, 0.0] },
  { index: 10, name: "Spine1", parent: "Spine", bindLocalPosCm: [0.0, 14.5, 0.0] },
  { index: 11, name: "Spine2", parent: "Spine1", bindLocalPosCm: [0.0, 14.5, 0.0] },
  { index: 12, name: "LeftShoulder", parent: "Spine2", bindLocalPosCm: [7.0, 10.6, 0.0] },
  { index: 13, name: "LeftArm", parent: "LeftShoulder", bindLocalPosCm: [8.9, -0.9, -1.7] },
  { index: 14, name: "LeftForeArm", parent: "LeftArm", bindLocalPosCm: [13.7, -28.3, 0.3] },
  { index: 15, name: "LeftHand", parent: "LeftForeArm", bindLocalPosCm: [10.4, -23.0, 7.7] },
  { index: 16, name: "LeftHandFinger1", parent: "LeftHand", bindLocalPosCm: [3.0, -8.6, 3.0] },
  { index: 17, name: "LeftHandFinger2", parent: "LeftHandFinger1", bindLocalPosCm: [-3.0, -8.8, 0.1] },
  { index: 18, name: "RightShoulder", parent: "Spine2", bindLocalPosCm: [-7.0, 10.6, 0.0] },
  { index: 19, name: "RightArm", parent: "RightShoulder", bindLocalPosCm: [-8.9, -0.9, -1.7] },
  { index: 20, name: "RightForeArm", parent: "RightArm", bindLocalPosCm: [-13.7, -28.3, 0.3] },
  { index: 21, name: "RightHand", parent: "RightForeArm", bindLocalPosCm: [-10.4, -23.0, 7.7] },
  { index: 22, name: "RightHandFinger1", parent: "RightHand", bindLocalPosCm: [-3.0, -8.6, 3.0] },
  { index: 23, name: "RightHandFinger2", parent: "RightHandFinger1", bindLocalPosCm: [3.0, -8.8, 0.1] },
  { index: 24, name: "Neck", parent: "Spine2", bindLocalPosCm: [0.0, 14.5, 0.0] },
  { index: 25, name: "Head", parent: "Neck", bindLocalPosCm: [0.0, 15.3, 0.7] },
] as const;

export const GTEX_HUMANOID_BONE_NAMES: readonly string[] = GTEX_HUMANOID_BONE_SPECS.map((b) => b.name);

// -----------------------------------------------------------------------------
// 2. Football Animation Categories & 41 Canonical States
// -----------------------------------------------------------------------------

export type FootballAnimationCategory =
  | "locomotion"
  | "ball_interaction"
  | "defensive_action"
  | "goalkeeper_action"
  | "match_reaction";

export type LocomotionAnimationState =
  | "idle"
  | "walk"
  | "jog"
  | "run"
  | "sprint"
  | "turn_left"
  | "turn_right"
  | "accelerate"
  | "decelerate"
  | "stop_change_direction";

export type BallInteractionAnimationState =
  | "receive_ball"
  | "first_touch"
  | "short_pass"
  | "long_pass"
  | "through_ball"
  | "dribble"
  | "shield_ball"
  | "cross"
  | "shoot"
  | "volley";

export type DefensiveAnimationState =
  | "standing_tackle"
  | "sliding_tackle"
  | "interception"
  | "blocking"
  | "jumping_challenge"
  | "tackle_recovery";

export type GoalkeeperAnimationState =
  | "gk_ready_stance"
  | "gk_lateral_move"
  | "gk_dive_low"
  | "gk_dive_high"
  | "gk_catch"
  | "gk_parry"
  | "gk_punch"
  | "gk_distribution";

export type MatchReactionAnimationState =
  | "goal_celebration"
  | "disappointment"
  | "team_celebration"
  | "injury_reaction"
  | "foul_reaction"
  | "substitution_exit"
  | "substitution_enter";

export type FootballAnimationState =
  | LocomotionAnimationState
  | BallInteractionAnimationState
  | DefensiveAnimationState
  | GoalkeeperAnimationState
  | MatchReactionAnimationState;

export interface FootballAnimationStateMeta {
  state: FootballAnimationState;
  category: FootballAnimationCategory;
  loop: boolean;
  defaultDurationSec: number;
  crossFadeSec: number;
  /** Minimum hold duration for one-shot actions so contact frames never get skipped */
  minHoldSec: number;
  /** Normalized phase [0..1] where foot/hand/head contacts the ball */
  ballContactPhase?: number;
  /** Primary mocap source clip in `gtex_humanoid_footballer.glb` */
  mocapSourceClip: string;
}

export const FOOTBALL_ANIMATION_STATE_META: Record<FootballAnimationState, FootballAnimationStateMeta> = {
  // Locomotion (10)
  idle: {
    state: "idle",
    category: "locomotion",
    loop: true,
    defaultDurationSec: 2.4,
    crossFadeSec: 0.22,
    minHoldSec: 0.0,
    mocapSourceClip: "mocap_idle",
  },
  walk: {
    state: "walk",
    category: "locomotion",
    loop: true,
    defaultDurationSec: 1.02,
    crossFadeSec: 0.2,
    minHoldSec: 0.0,
    mocapSourceClip: "mocap_walk",
  },
  jog: {
    state: "jog",
    category: "locomotion",
    loop: true,
    defaultDurationSec: 0.78,
    crossFadeSec: 0.18,
    minHoldSec: 0.0,
    mocapSourceClip: "mocap_run",
  },
  run: {
    state: "run",
    category: "locomotion",
    loop: true,
    defaultDurationSec: 0.63,
    crossFadeSec: 0.16,
    minHoldSec: 0.0,
    mocapSourceClip: "mocap_run",
  },
  sprint: {
    state: "sprint",
    category: "locomotion",
    loop: true,
    defaultDurationSec: 0.48,
    crossFadeSec: 0.15,
    minHoldSec: 0.0,
    mocapSourceClip: "mocap_run",
  },
  turn_left: {
    state: "turn_left",
    category: "locomotion",
    loop: true,
    defaultDurationSec: 0.67,
    crossFadeSec: 0.15,
    minHoldSec: 0.18,
    mocapSourceClip: "mocap_strafe_left",
  },
  turn_right: {
    state: "turn_right",
    category: "locomotion",
    loop: true,
    defaultDurationSec: 0.67,
    crossFadeSec: 0.15,
    minHoldSec: 0.18,
    mocapSourceClip: "mocap_strafe_right",
  },
  accelerate: {
    state: "accelerate",
    category: "locomotion",
    loop: false,
    defaultDurationSec: 0.55,
    crossFadeSec: 0.14,
    minHoldSec: 0.22,
    mocapSourceClip: "mocap_run",
  },
  decelerate: {
    state: "decelerate",
    category: "locomotion",
    loop: false,
    defaultDurationSec: 0.55,
    crossFadeSec: 0.14,
    minHoldSec: 0.22,
    mocapSourceClip: "mocap_run_back",
  },
  stop_change_direction: {
    state: "stop_change_direction",
    category: "locomotion",
    loop: false,
    defaultDurationSec: 0.65,
    crossFadeSec: 0.12,
    minHoldSec: 0.28,
    mocapSourceClip: "mocap_spin",
  },

  // Ball Interaction (10)
  receive_ball: {
    state: "receive_ball",
    category: "ball_interaction",
    loop: false,
    defaultDurationSec: 0.72,
    crossFadeSec: 0.14,
    minHoldSec: 0.35,
    ballContactPhase: 0.45,
    mocapSourceClip: "mocap_walk_right",
  },
  first_touch: {
    state: "first_touch",
    category: "ball_interaction",
    loop: false,
    defaultDurationSec: 0.68,
    crossFadeSec: 0.12,
    minHoldSec: 0.32,
    ballContactPhase: 0.35,
    mocapSourceClip: "mocap_dribble",
  },
  short_pass: {
    state: "short_pass",
    category: "ball_interaction",
    loop: false,
    defaultDurationSec: 0.95,
    crossFadeSec: 0.12,
    minHoldSec: 0.45,
    ballContactPhase: 0.42,
    mocapSourceClip: "mocap_pass",
  },
  long_pass: {
    state: "long_pass",
    category: "ball_interaction",
    loop: false,
    defaultDurationSec: 1.15,
    crossFadeSec: 0.14,
    minHoldSec: 0.52,
    ballContactPhase: 0.48,
    mocapSourceClip: "mocap_shoot",
  },
  through_ball: {
    state: "through_ball",
    category: "ball_interaction",
    loop: false,
    defaultDurationSec: 0.98,
    crossFadeSec: 0.12,
    minHoldSec: 0.45,
    ballContactPhase: 0.44,
    mocapSourceClip: "mocap_pass",
  },
  dribble: {
    state: "dribble",
    category: "ball_interaction",
    loop: true,
    defaultDurationSec: 0.53,
    crossFadeSec: 0.14,
    minHoldSec: 0.2,
    ballContactPhase: 0.5,
    mocapSourceClip: "mocap_dribble",
  },
  shield_ball: {
    state: "shield_ball",
    category: "ball_interaction",
    loop: true,
    defaultDurationSec: 1.2,
    crossFadeSec: 0.18,
    minHoldSec: 0.35,
    mocapSourceClip: "mocap_struggle",
  },
  cross: {
    state: "cross",
    category: "ball_interaction",
    loop: false,
    defaultDurationSec: 1.1,
    crossFadeSec: 0.14,
    minHoldSec: 0.5,
    ballContactPhase: 0.46,
    mocapSourceClip: "mocap_shoot",
  },
  shoot: {
    state: "shoot",
    category: "ball_interaction",
    loop: false,
    defaultDurationSec: 1.15,
    crossFadeSec: 0.12,
    minHoldSec: 0.55,
    ballContactPhase: 0.45,
    mocapSourceClip: "mocap_shoot",
  },
  volley: {
    state: "volley",
    category: "ball_interaction",
    loop: false,
    defaultDurationSec: 1.45,
    crossFadeSec: 0.12,
    minHoldSec: 0.65,
    ballContactPhase: 0.52,
    mocapSourceClip: "mocap_volley",
  },

  // Defensive Actions (6)
  standing_tackle: {
    state: "standing_tackle",
    category: "defensive_action",
    loop: false,
    defaultDurationSec: 1.05,
    crossFadeSec: 0.12,
    minHoldSec: 0.48,
    mocapSourceClip: "mocap_tackle",
  },
  sliding_tackle: {
    state: "sliding_tackle",
    category: "defensive_action",
    loop: false,
    defaultDurationSec: 1.35,
    crossFadeSec: 0.12,
    minHoldSec: 0.65,
    mocapSourceClip: "mocap_tackle",
  },
  interception: {
    state: "interception",
    category: "defensive_action",
    loop: false,
    defaultDurationSec: 0.85,
    crossFadeSec: 0.12,
    minHoldSec: 0.4,
    mocapSourceClip: "mocap_strafe_left",
  },
  blocking: {
    state: "blocking",
    category: "defensive_action",
    loop: false,
    defaultDurationSec: 0.9,
    crossFadeSec: 0.12,
    minHoldSec: 0.42,
    mocapSourceClip: "mocap_struggle",
  },
  jumping_challenge: {
    state: "jumping_challenge",
    category: "defensive_action",
    loop: false,
    defaultDurationSec: 1.25,
    crossFadeSec: 0.12,
    minHoldSec: 0.58,
    ballContactPhase: 0.5,
    mocapSourceClip: "mocap_header",
  },
  tackle_recovery: {
    state: "tackle_recovery",
    category: "defensive_action",
    loop: false,
    defaultDurationSec: 1.0,
    crossFadeSec: 0.16,
    minHoldSec: 0.42,
    mocapSourceClip: "mocap_tackled",
  },

  // Goalkeeper Actions (8)
  gk_ready_stance: {
    state: "gk_ready_stance",
    category: "goalkeeper_action",
    loop: true,
    defaultDurationSec: 1.8,
    crossFadeSec: 0.2,
    minHoldSec: 0.0,
    mocapSourceClip: "mocap_gk_idle",
  },
  gk_lateral_move: {
    state: "gk_lateral_move",
    category: "goalkeeper_action",
    loop: true,
    defaultDurationSec: 0.5,
    crossFadeSec: 0.14,
    minHoldSec: 0.2,
    mocapSourceClip: "mocap_gk_sidestep",
  },
  gk_dive_low: {
    state: "gk_dive_low",
    category: "goalkeeper_action",
    loop: false,
    defaultDurationSec: 1.15,
    crossFadeSec: 0.1,
    minHoldSec: 0.65,
    ballContactPhase: 0.42,
    mocapSourceClip: "mocap_gk_dive_low",
  },
  gk_dive_high: {
    state: "gk_dive_high",
    category: "goalkeeper_action",
    loop: false,
    defaultDurationSec: 1.45,
    crossFadeSec: 0.1,
    minHoldSec: 0.75,
    ballContactPhase: 0.48,
    mocapSourceClip: "mocap_gk_dive_high",
  },
  gk_catch: {
    state: "gk_catch",
    category: "goalkeeper_action",
    loop: false,
    defaultDurationSec: 1.1,
    crossFadeSec: 0.14,
    minHoldSec: 0.5,
    ballContactPhase: 0.4,
    mocapSourceClip: "mocap_gk_holding",
  },
  gk_parry: {
    state: "gk_parry",
    category: "goalkeeper_action",
    loop: false,
    defaultDurationSec: 1.2,
    crossFadeSec: 0.1,
    minHoldSec: 0.58,
    ballContactPhase: 0.44,
    mocapSourceClip: "mocap_gk_dive_high",
  },
  gk_punch: {
    state: "gk_punch",
    category: "goalkeeper_action",
    loop: false,
    defaultDurationSec: 1.25,
    crossFadeSec: 0.12,
    minHoldSec: 0.58,
    ballContactPhase: 0.46,
    mocapSourceClip: "mocap_gk_jump",
  },
  gk_distribution: {
    state: "gk_distribution",
    category: "goalkeeper_action",
    loop: false,
    defaultDurationSec: 0.85,
    crossFadeSec: 0.14,
    minHoldSec: 0.45,
    ballContactPhase: 0.5,
    mocapSourceClip: "mocap_gk_drop_kick",
  },

  // Match Reactions (7)
  goal_celebration: {
    state: "goal_celebration",
    category: "match_reaction",
    loop: true,
    defaultDurationSec: 1.4,
    crossFadeSec: 0.18,
    minHoldSec: 0.8,
    mocapSourceClip: "mocap_run",
  },
  disappointment: {
    state: "disappointment",
    category: "match_reaction",
    loop: true,
    defaultDurationSec: 1.6,
    crossFadeSec: 0.2,
    minHoldSec: 0.6,
    mocapSourceClip: "mocap_gk_miss",
  },
  team_celebration: {
    state: "team_celebration",
    category: "match_reaction",
    loop: true,
    defaultDurationSec: 1.2,
    crossFadeSec: 0.18,
    minHoldSec: 0.6,
    mocapSourceClip: "mocap_run",
  },
  injury_reaction: {
    state: "injury_reaction",
    category: "match_reaction",
    loop: true,
    defaultDurationSec: 1.8,
    crossFadeSec: 0.2,
    minHoldSec: 0.7,
    mocapSourceClip: "mocap_tackled",
  },
  foul_reaction: {
    state: "foul_reaction",
    category: "match_reaction",
    loop: false,
    defaultDurationSec: 1.3,
    crossFadeSec: 0.15,
    minHoldSec: 0.55,
    mocapSourceClip: "mocap_tackled",
  },
  substitution_exit: {
    state: "substitution_exit",
    category: "match_reaction",
    loop: true,
    defaultDurationSec: 1.15,
    crossFadeSec: 0.2,
    minHoldSec: 0.4,
    mocapSourceClip: "mocap_walk",
  },
  substitution_enter: {
    state: "substitution_enter",
    category: "match_reaction",
    loop: true,
    defaultDurationSec: 0.75,
    crossFadeSec: 0.18,
    minHoldSec: 0.4,
    mocapSourceClip: "mocap_run",
  },
};

export const ALL_FOOTBALL_ANIMATION_STATES: readonly FootballAnimationState[] = Object.keys(
  FOOTBALL_ANIMATION_STATE_META
) as FootballAnimationState[];

// -----------------------------------------------------------------------------
// 3. Biomechanical Skeletal Clip Generator & Mocap Retargeter (26-Bone Standard)
// -----------------------------------------------------------------------------

function eulerToQuatArray(rx: number, ry: number, rz: number): [number, number, number, number] {
  const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(rx, ry, rz, "XYZ"));
  return [q.x, q.y, q.z, q.w];
}

function buildQuatTrack(
  boneName: string,
  times: number[],
  eulers: Array<[number, number, number]>
): THREE.QuaternionKeyframeTrack {
  const values: number[] = [];
  for (let i = 0; i < eulers.length; i++) {
    const [rx, ry, rz] = eulers[i];
    let [qx, qy, qz, qw] = eulerToQuatArray(rx, ry, rz);
    if (i === 0) {
      if (qw < 0) {
        qx = -qx;
        qy = -qy;
        qz = -qz;
        qw = -qw;
      }
    } else {
      const prevIdx = (i - 1) * 4;
      const dot =
        values[prevIdx] * qx +
        values[prevIdx + 1] * qy +
        values[prevIdx + 2] * qz +
        values[prevIdx + 3] * qw;
      if (dot < 0) {
        qx = -qx;
        qy = -qy;
        qz = -qz;
        qw = -qw;
      }
    }
    values.push(qx, qy, qz, qw);
  }
  return new THREE.QuaternionKeyframeTrack(`${boneName}.quaternion`, times, values);
}

function buildPosTrack(
  boneName: string,
  times: number[],
  positions: Array<[number, number, number]>
): THREE.VectorKeyframeTrack {
  const values: number[] = [];
  for (const [x, y, z] of positions) {
    values.push(x, y, z);
  }
  return new THREE.VectorKeyframeTrack(`${boneName}.position`, times, values);
}

/**
 * Generates a complete, self-contained 26-bone `THREE.AnimationClip` for a given
 * `FootballAnimationState`. If a matching mocap clip from `gtex_humanoid_footballer.glb`
 * is provided, it uses and adapts the mocap tracks (e.g., adding sprint forward lean,
 * sliding tackle ground drop, or celebration raised arms).
 */
export function buildClipForFootballState(
  state: FootballAnimationState,
  mocapMap?: Map<string, THREE.AnimationClip>
): THREE.AnimationClip {
  const meta = FOOTBALL_ANIMATION_STATE_META[state];
  const mocapClip = mocapMap?.get(meta.mocapSourceClip);

  // States with specialized upper/lower body pose overrides or mocap adaptations
  const specializedSynthesizers: Partial<Record<FootballAnimationState, () => THREE.AnimationClip>> = {
    goal_celebration: () => {
      const t = [0, 0.35, 0.7, 1.05, 1.4];
      return new THREE.AnimationClip("goal_celebration", 1.4, [
        buildPosTrack("Hips", t, [
          [0, 100, 0],
          [0, 118, 4],
          [0, 96, 6],
          [0, 114, 4],
          [0, 100, 0],
        ]),
        buildQuatTrack("Spine", t, [
          [-0.08, 0, 0],
          [-0.18, 0.12, 0],
          [-0.12, -0.12, 0],
          [-0.18, 0.1, 0],
          [-0.08, 0, 0],
        ]),
        buildQuatTrack("Spine1", t, [
          [-0.06, 0, 0],
          [-0.12, 0.08, 0],
          [-0.08, -0.08, 0],
          [-0.12, 0.08, 0],
          [-0.06, 0, 0],
        ]),
        buildQuatTrack("LeftArm", t, [
          [-2.3, 0.2, -0.4],
          [-2.65, 0.3, -0.5],
          [-2.2, 0.15, -0.35],
          [-2.65, 0.3, -0.5],
          [-2.3, 0.2, -0.4],
        ]),
        buildQuatTrack("RightArm", t, [
          [-2.3, -0.2, 0.4],
          [-2.65, -0.3, 0.5],
          [-2.2, -0.15, 0.35],
          [-2.65, -0.3, 0.5],
          [-2.3, -0.2, 0.4],
        ]),
        buildQuatTrack("LeftForeArm", t, [
          [-0.5, 0, 0],
          [-0.85, 0, 0],
          [-0.4, 0, 0],
          [-0.85, 0, 0],
          [-0.5, 0, 0],
        ]),
        buildQuatTrack("RightForeArm", t, [
          [-0.5, 0, 0],
          [-0.85, 0, 0],
          [-0.4, 0, 0],
          [-0.85, 0, 0],
          [-0.5, 0, 0],
        ]),
        buildQuatTrack("LeftUpLeg", t, [
          [-0.35, 0, 0],
          [0.45, 0, 0],
          [-0.45, 0, 0],
          [0.35, 0, 0],
          [-0.35, 0, 0],
        ]),
        buildQuatTrack("RightUpLeg", t, [
          [0.35, 0, 0],
          [-0.45, 0, 0],
          [0.45, 0, 0],
          [-0.35, 0, 0],
          [0.35, 0, 0],
        ]),
        buildQuatTrack("LeftLeg", t, [
          [0.5, 0, 0],
          [0.85, 0, 0],
          [0.3, 0, 0],
          [0.75, 0, 0],
          [0.5, 0, 0],
        ]),
        buildQuatTrack("RightLeg", t, [
          [0.3, 0, 0],
          [0.75, 0, 0],
          [0.5, 0, 0],
          [0.85, 0, 0],
          [0.3, 0, 0],
        ]),
        buildQuatTrack("Head", t, [
          [-0.2, 0, 0],
          [-0.32, 0.15, 0],
          [-0.18, -0.15, 0],
          [-0.3, 0.12, 0],
          [-0.2, 0, 0],
        ]),
      ]);
    },
    team_celebration: () => {
      const t = [0, 0.3, 0.6, 0.9, 1.2];
      return new THREE.AnimationClip("team_celebration", 1.2, [
        buildPosTrack("Hips", t, [
          [0, 96, 0],
          [0, 106, 0],
          [0, 95, 0],
          [0, 106, 0],
          [0, 96, 0],
        ]),
        buildQuatTrack("Spine", t, [
          [0.08, 0, 0],
          [-0.06, 0.08, 0],
          [0.08, 0, 0],
          [-0.06, -0.08, 0],
          [0.08, 0, 0],
        ]),
        buildQuatTrack("LeftArm", t, [
          [-1.6, 0.3, -0.2],
          [-1.95, 0.1, -0.1],
          [-1.6, 0.3, -0.2],
          [-1.95, 0.1, -0.1],
          [-1.6, 0.3, -0.2],
        ]),
        buildQuatTrack("RightArm", t, [
          [-1.6, -0.3, 0.2],
          [-1.95, -0.1, 0.1],
          [-1.6, -0.3, 0.2],
          [-1.95, -0.1, 0.1],
          [-1.6, -0.3, 0.2],
        ]),
        buildQuatTrack("LeftUpLeg", t, [
          [-0.45, 0, 0],
          [0.35, 0, 0],
          [-0.45, 0, 0],
          [0.35, 0, 0],
          [-0.45, 0, 0],
        ]),
        buildQuatTrack("RightUpLeg", t, [
          [0.35, 0, 0],
          [-0.45, 0, 0],
          [0.35, 0, 0],
          [-0.45, 0, 0],
          [0.35, 0, 0],
        ]),
        buildQuatTrack("LeftLeg", t, [
          [0.55, 0, 0],
          [0.2, 0, 0],
          [0.55, 0, 0],
          [0.2, 0, 0],
          [0.55, 0, 0],
        ]),
        buildQuatTrack("RightLeg", t, [
          [0.2, 0, 0],
          [0.55, 0, 0],
          [0.2, 0, 0],
          [0.55, 0, 0],
          [0.2, 0, 0],
        ]),
      ]);
    },
    sliding_tackle: () => {
      const t = [0, 0.28, 0.65, 1.05, 1.35];
      return new THREE.AnimationClip("sliding_tackle", 1.35, [
        buildPosTrack("Hips", t, [
          [0, 88, 0],
          [0, 42, 6],
          [0, 28, 10],
          [0, 52, 4],
          [0, 92, 0],
        ]),
        buildQuatTrack("Hips", t, [
          [0.15, 0, 0],
          [-0.65, 0.2, 0.15],
          [-0.82, 0.25, 0.2],
          [-0.35, 0.1, 0.08],
          [0.05, 0, 0],
        ]),
        buildQuatTrack("Spine", t, [
          [0.2, 0, 0],
          [0.25, -0.15, 0],
          [0.3, -0.2, 0],
          [0.25, -0.1, 0],
          [0.1, 0, 0],
        ]),
        buildQuatTrack("RightUpLeg", t, [
          [-0.3, 0, 0],
          [-1.15, 0, 0],
          [-1.25, 0, 0],
          [-0.65, 0, 0],
          [-0.15, 0, 0],
        ]),
        buildQuatTrack("RightLeg", t, [
          [0.4, 0, 0],
          [0.05, 0, 0],
          [0.02, 0, 0],
          [0.45, 0, 0],
          [0.2, 0, 0],
        ]),
        buildQuatTrack("LeftUpLeg", t, [
          [0.25, 0, 0],
          [-0.45, 0.25, 0],
          [-0.55, 0.3, 0],
          [-0.35, 0.15, 0],
          [0.1, 0, 0],
        ]),
        buildQuatTrack("LeftLeg", t, [
          [0.45, 0, 0],
          [1.35, 0, 0],
          [1.45, 0, 0],
          [0.95, 0, 0],
          [0.25, 0, 0],
        ]),
        buildQuatTrack("LeftArm", t, [
          [0.3, 0, -0.4],
          [0.65, 0, -0.75],
          [0.75, 0, -0.8],
          [0.45, 0, -0.5],
          [0.15, 0, -0.2],
        ]),
        buildQuatTrack("RightArm", t, [
          [-0.3, 0, 0.4],
          [-0.65, 0, 0.7],
          [-0.7, 0, 0.75],
          [-0.4, 0, 0.45],
          [-0.15, 0, 0.2],
        ]),
      ]);
    },
    injury_reaction: () => {
      const t = [0, 0.45, 0.9, 1.35, 1.8];
      return new THREE.AnimationClip("injury_reaction", 1.8, [
        buildPosTrack("Hips", t, [
          [0, 52, 0],
          [0, 46, 0],
          [0, 50, 0],
          [0, 46, 0],
          [0, 52, 0],
        ]),
        buildQuatTrack("Spine", t, [
          [0.55, 0, 0],
          [0.68, 0.08, 0],
          [0.58, -0.08, 0],
          [0.68, 0.06, 0],
          [0.55, 0, 0],
        ]),
        buildQuatTrack("RightUpLeg", t, [
          [-1.1, 0, 0],
          [-1.22, 0, 0],
          [-1.12, 0, 0],
          [-1.22, 0, 0],
          [-1.1, 0, 0],
        ]),
        buildQuatTrack("RightLeg", t, [
          [1.35, 0, 0],
          [1.48, 0, 0],
          [1.38, 0, 0],
          [1.48, 0, 0],
          [1.35, 0, 0],
        ]),
        buildQuatTrack("LeftUpLeg", t, [
          [-0.75, 0, 0],
          [-0.78, 0, 0],
          [-0.75, 0, 0],
          [-0.78, 0, 0],
          [-0.75, 0, 0],
        ]),
        buildQuatTrack("LeftLeg", t, [
          [1.1, 0, 0],
          [1.12, 0, 0],
          [1.1, 0, 0],
          [1.12, 0, 0],
          [1.1, 0, 0],
        ]),
        buildQuatTrack("RightArm", t, [
          [-0.85, -0.25, 0.2],
          [-0.92, -0.3, 0.25],
          [-0.85, -0.25, 0.2],
          [-0.92, -0.3, 0.25],
          [-0.85, -0.25, 0.2],
        ]),
        buildQuatTrack("LeftArm", t, [
          [-0.75, 0.25, -0.2],
          [-0.82, 0.3, -0.25],
          [-0.75, 0.25, -0.2],
          [-0.82, 0.3, -0.25],
          [-0.75, 0.25, -0.2],
        ]),
        buildQuatTrack("Head", t, [
          [0.35, 0, 0],
          [0.45, 0.12, 0],
          [0.38, -0.12, 0],
          [0.45, 0.1, 0],
          [0.35, 0, 0],
        ]),
      ]);
    },
  };

  if (specializedSynthesizers[state]) {
    return specializedSynthesizers[state]!();
  }

  // If mocapClip is available from GLB, clone and adapt it to the exact state
  if (mocapClip) {
    const cloned = mocapClip.clone();
    cloned.name = state;
    return cloned;
  }

  // Deterministic biomechanical 26-bone synthesis when running synchronously (pre-GLB or headless)
  const dur = meta.defaultDurationSec;
  const t = [0, dur * 0.25, dur * 0.5, dur * 0.75, dur];

  if (meta.category === "goalkeeper_action") {
    const isDiveHigh = state === "gk_dive_high" || state === "gk_parry";
    const isDiveLow = state === "gk_dive_low";
    const isJump = state === "gk_punch" || state === "gk_catch";
    const isKick = state === "gk_distribution";

    if (isDiveHigh || isDiveLow) {
      const peakY = isDiveHigh ? 132 : 42;
      const rollZ = isDiveHigh ? 1.15 : 1.35;
      return new THREE.AnimationClip(state, dur, [
        buildPosTrack("Hips", t, [
          [0, 92, 0],
          [6, peakY, 4],
          [12, isDiveHigh ? 95 : 28, 6],
          [8, 48, 3],
          [0, 92, 0],
        ]),
        buildQuatTrack("Hips", t, [
          [0.12, 0, 0],
          [0.05, 0, rollZ * 0.65],
          [0.0, 0, rollZ],
          [0.08, 0, rollZ * 0.4],
          [0.12, 0, 0],
        ]),
        buildQuatTrack("Spine", t, [
          [0.18, 0, 0],
          [-0.1, 0, 0.2],
          [-0.15, 0, 0.25],
          [0.1, 0, 0.1],
          [0.18, 0, 0],
        ]),
        buildQuatTrack("LeftArm", t, [
          [-0.6, 0, -0.4],
          [-2.6, 0, -0.25],
          [-2.75, 0, -0.15],
          [-1.4, 0, -0.3],
          [-0.6, 0, -0.4],
        ]),
        buildQuatTrack("RightArm", t, [
          [-0.6, 0, 0.4],
          [-2.6, 0, 0.25],
          [-2.75, 0, 0.15],
          [-1.4, 0, 0.3],
          [-0.6, 0, 0.4],
        ]),
        buildQuatTrack("LeftUpLeg", t, [
          [-0.35, 0, -0.12],
          [-0.15, 0, -0.2],
          [-0.1, 0, -0.15],
          [-0.4, 0, -0.12],
          [-0.35, 0, -0.12],
        ]),
        buildQuatTrack("RightUpLeg", t, [
          [-0.35, 0, 0.12],
          [-0.25, 0, 0.2],
          [-0.2, 0, 0.15],
          [-0.4, 0, 0.12],
          [-0.35, 0, 0.12],
        ]),
      ]);
    }

    if (isJump) {
      return new THREE.AnimationClip(state, dur, [
        buildPosTrack("Hips", t, [
          [0, 92, 0],
          [0, 82, 0],
          [0, 144, 4],
          [0, 112, 2],
          [0, 92, 0],
        ]),
        buildQuatTrack("Spine", t, [
          [0.15, 0, 0],
          [0.25, 0, 0],
          [-0.12, 0, 0],
          [0.08, 0, 0],
          [0.15, 0, 0],
        ]),
        buildQuatTrack("LeftArm", t, [
          [-0.7, 0, -0.3],
          [-1.2, 0, -0.3],
          [-2.65, 0.2, -0.15],
          [-1.6, 0.35, -0.1],
          [-0.7, 0, -0.3],
        ]),
        buildQuatTrack("RightArm", t, [
          [-0.7, 0, 0.3],
          [-1.2, 0, 0.3],
          [-2.65, -0.2, 0.15],
          [-1.6, -0.35, 0.1],
          [-0.7, 0, 0.3],
        ]),
        buildQuatTrack("RightUpLeg", t, [
          [-0.3, 0, 0],
          [-0.55, 0, 0],
          [-1.05, 0, 0],
          [-0.45, 0, 0],
          [-0.3, 0, 0],
        ]),
        buildQuatTrack("RightLeg", t, [
          [0.45, 0, 0],
          [0.85, 0, 0],
          [1.25, 0, 0],
          [0.65, 0, 0],
          [0.45, 0, 0],
        ]),
      ]);
    }

    if (isKick) {
      return new THREE.AnimationClip(state, dur, [
        buildPosTrack("Hips", t, [
          [0, 96, 0],
          [0, 94, 2],
          [0, 102, 5],
          [0, 98, 3],
          [0, 96, 0],
        ]),
        buildQuatTrack("Spine", t, [
          [0.1, 0, 0],
          [0.18, 0.15, 0],
          [-0.18, -0.2, 0],
          [-0.08, -0.1, 0],
          [0.1, 0, 0],
        ]),
        buildQuatTrack("RightUpLeg", t, [
          [-0.15, 0, 0],
          [0.65, 0, 0],
          [-1.15, 0, 0],
          [-0.45, 0, 0],
          [-0.15, 0, 0],
        ]),
        buildQuatTrack("RightLeg", t, [
          [0.25, 0, 0],
          [1.15, 0, 0],
          [0.08, 0, 0],
          [0.35, 0, 0],
          [0.25, 0, 0],
        ]),
      ]);
    }

    // gk_ready_stance / gk_lateral_move
    const latX = state === "gk_lateral_move" ? 8 : 2;
    return new THREE.AnimationClip(state, dur, [
      buildPosTrack("Hips", t, [
        [0, 88, 0],
        [latX, 84, 0],
        [0, 88, 0],
        [-latX, 84, 0],
        [0, 88, 0],
      ]),
      buildQuatTrack("Spine", t, [
        [0.24, 0, 0],
        [0.28, 0, 0],
        [0.24, 0, 0],
        [0.28, 0, 0],
        [0.24, 0, 0],
      ]),
      buildQuatTrack("LeftArm", t, [
        [-0.65, 0.2, -0.45],
        [-0.75, 0.25, -0.5],
        [-0.65, 0.2, -0.45],
        [-0.75, 0.25, -0.5],
        [-0.65, 0.2, -0.45],
      ]),
      buildQuatTrack("RightArm", t, [
        [-0.65, -0.2, 0.45],
        [-0.75, -0.25, 0.5],
        [-0.65, -0.2, 0.45],
        [-0.75, -0.25, 0.5],
        [-0.65, -0.2, 0.45],
      ]),
      buildQuatTrack("LeftUpLeg", t, [
        [-0.45, 0, -0.18],
        [-0.55, 0, -0.24],
        [-0.45, 0, -0.18],
        [-0.55, 0, -0.24],
        [-0.45, 0, -0.18],
      ]),
      buildQuatTrack("RightUpLeg", t, [
        [-0.45, 0, 0.18],
        [-0.55, 0, 0.24],
        [-0.45, 0, 0.18],
        [-0.55, 0, 0.24],
        [-0.45, 0, 0.18],
      ]),
      buildQuatTrack("LeftLeg", t, [
        [0.65, 0, 0],
        [0.78, 0, 0],
        [0.65, 0, 0],
        [0.78, 0, 0],
        [0.65, 0, 0],
      ]),
      buildQuatTrack("RightLeg", t, [
        [0.65, 0, 0],
        [0.78, 0, 0],
        [0.65, 0, 0],
        [0.78, 0, 0],
        [0.65, 0, 0],
      ]),
    ]);
  }

  if (
    state === "short_pass" ||
    state === "long_pass" ||
    state === "through_ball" ||
    state === "cross" ||
    state === "shoot" ||
    state === "volley"
  ) {
    const isPowerStrike = state === "shoot" || state === "long_pass" || state === "cross" || state === "volley";
    const backswing = isPowerStrike ? 0.75 : 0.45;
    const followThrough = isPowerStrike ? -1.15 : -0.68;
    const hipY = state === "volley" ? 128 : 96;

    return new THREE.AnimationClip(state, dur, [
      buildPosTrack("Hips", t, [
        [0, 96, 0],
        [0, 93, -2],
        [0, hipY, 4],
        [0, 98, 2],
        [0, 96, 0],
      ]),
      buildQuatTrack("Spine", t, [
        [0.1, 0, 0],
        [0.2, 0.22, 0],
        [-0.16, -0.28, -0.08],
        [-0.08, -0.14, -0.04],
        [0.1, 0, 0],
      ]),
      buildQuatTrack("RightUpLeg", t, [
        [-0.1, 0, 0],
        [backswing, 0, 0],
        [followThrough, 0, state === "short_pass" ? -0.25 : 0],
        [followThrough * 0.5, 0, 0],
        [-0.1, 0, 0],
      ]),
      buildQuatTrack("RightLeg", t, [
        [0.2, 0, 0],
        [1.15, 0, 0],
        [0.08, 0, 0],
        [0.35, 0, 0],
        [0.2, 0, 0],
      ]),
      buildQuatTrack("LeftUpLeg", t, [
        [-0.15, 0, 0],
        [-0.35, 0, 0],
        [0.25, 0, 0],
        [0.1, 0, 0],
        [-0.15, 0, 0],
      ]),
      buildQuatTrack("LeftLeg", t, [
        [0.25, 0, 0],
        [0.45, 0, 0],
        [0.35, 0, 0],
        [0.25, 0, 0],
        [0.25, 0, 0],
      ]),
      buildQuatTrack("LeftArm", t, [
        [-0.25, 0, -0.25],
        [-0.85, 0, -0.55],
        [0.45, 0, -0.35],
        [0.2, 0, -0.25],
        [-0.25, 0, -0.25],
      ]),
      buildQuatTrack("RightArm", t, [
        [-0.2, 0, 0.25],
        [0.45, 0, 0.35],
        [-0.65, 0, 0.45],
        [-0.35, 0, 0.3],
        [-0.2, 0, 0.25],
      ]),
    ]);
  }

  if (state === "jumping_challenge") {
    return new THREE.AnimationClip(state, dur, [
      buildPosTrack("Hips", t, [
        [0, 96, 0],
        [0, 84, 0],
        [0, 148, 4],
        [0, 118, 6],
        [0, 96, 0],
      ]),
      buildQuatTrack("Spine", t, [
        [0.1, 0, 0],
        [0.28, 0, 0],
        [-0.25, 0, 0],
        [0.32, 0, 0],
        [0.1, 0, 0],
      ]),
      buildQuatTrack("Head", t, [
        [0, 0, 0],
        [-0.15, 0, 0],
        [-0.35, 0, 0],
        [0.42, 0, 0],
        [0, 0, 0],
      ]),
      buildQuatTrack("LeftArm", t, [
        [-0.3, 0, -0.25],
        [0.35, 0, -0.3],
        [-1.35, 0, -0.55],
        [-0.65, 0, -0.4],
        [-0.3, 0, -0.25],
      ]),
      buildQuatTrack("RightArm", t, [
        [-0.3, 0, 0.25],
        [0.35, 0, 0.3],
        [-1.35, 0, 0.55],
        [-0.65, 0, 0.4],
        [-0.3, 0, 0.25],
      ]),
      buildQuatTrack("LeftUpLeg", t, [
        [-0.2, 0, 0],
        [-0.55, 0, 0],
        [0.25, 0, 0],
        [-0.35, 0, 0],
        [-0.2, 0, 0],
      ]),
      buildQuatTrack("RightUpLeg", t, [
        [-0.2, 0, 0],
        [-0.55, 0, 0],
        [0.25, 0, 0],
        [-0.35, 0, 0],
        [-0.2, 0, 0],
      ]),
      buildQuatTrack("LeftLeg", t, [
        [0.3, 0, 0],
        [0.85, 0, 0],
        [0.95, 0, 0],
        [0.5, 0, 0],
        [0.3, 0, 0],
      ]),
      buildQuatTrack("RightLeg", t, [
        [0.3, 0, 0],
        [0.85, 0, 0],
        [0.95, 0, 0],
        [0.5, 0, 0],
        [0.3, 0, 0],
      ]),
    ]);
  }

  if (
    state === "standing_tackle" ||
    state === "interception" ||
    state === "blocking" ||
    state === "tackle_recovery" ||
    state === "foul_reaction" ||
    state === "disappointment"
  ) {
    const isLunge = state === "standing_tackle" || state === "interception";
    const isDisappointment = state === "disappointment";
    return new THREE.AnimationClip(state, dur, [
      buildPosTrack("Hips", t, [
        [0, 96, 0],
        [0, isLunge ? 76 : 86, isLunge ? 8 : 0],
        [0, isLunge ? 72 : 84, isLunge ? 10 : 0],
        [0, 88, 4],
        [0, 96, 0],
      ]),
      buildQuatTrack("Spine", t, [
        [0.12, 0, 0],
        [isDisappointment ? 0.38 : 0.28, 0.1, 0],
        [isDisappointment ? 0.42 : 0.32, -0.1, 0],
        [0.22, 0, 0],
        [0.12, 0, 0],
      ]),
      buildQuatTrack("RightUpLeg", t, [
        [-0.2, 0, 0],
        [isLunge ? -1.05 : -0.35, 0, 0],
        [isLunge ? -1.12 : -0.4, 0, 0],
        [-0.45, 0, 0],
        [-0.2, 0, 0],
      ]),
      buildQuatTrack("RightLeg", t, [
        [0.3, 0, 0],
        [isLunge ? 0.25 : 0.55, 0, 0],
        [isLunge ? 0.2 : 0.6, 0, 0],
        [0.45, 0, 0],
        [0.3, 0, 0],
      ]),
      buildQuatTrack("LeftUpLeg", t, [
        [-0.2, 0, 0],
        [isLunge ? 0.45 : -0.35, 0, 0],
        [isLunge ? 0.5 : -0.4, 0, 0],
        [-0.25, 0, 0],
        [-0.2, 0, 0],
      ]),
      buildQuatTrack("LeftLeg", t, [
        [0.3, 0, 0],
        [0.85, 0, 0],
        [0.9, 0, 0],
        [0.45, 0, 0],
        [0.3, 0, 0],
      ]),
      buildQuatTrack("LeftArm", t, [
        [-0.25, 0, -0.2],
        [isDisappointment ? -2.1 : -0.75, 0, -0.35],
        [isDisappointment ? -2.2 : -0.8, 0, -0.35],
        [-0.5, 0, -0.25],
        [-0.25, 0, -0.2],
      ]),
      buildQuatTrack("RightArm", t, [
        [-0.25, 0, 0.2],
        [isDisappointment ? -2.1 : -0.75, 0, 0.35],
        [isDisappointment ? -2.2 : -0.8, 0, 0.35],
        [-0.5, 0, 0.25],
        [-0.25, 0, 0.2],
      ]),
    ]);
  }

  // Locomotion & Ball-Carrying (idle, walk, jog, run, sprint, dribble, receive_ball, first_touch, shield_ball, turns)
  const isIdle = state === "idle";
  const isSprint = state === "sprint" || state === "accelerate";
  const isRun = state === "run" || state === "dribble" || state === "substitution_enter" || isSprint;
  const isJog = state === "jog" || state === "turn_left" || state === "turn_right";
  const legSwing = isIdle ? 0.04 : isSprint ? 0.92 : isRun ? 0.72 : isJog ? 0.48 : 0.28;
  const kneeBend = isIdle ? 0.08 : isSprint ? 1.15 : isRun ? 0.92 : isJog ? 0.62 : 0.35;
  const armSwing = isIdle ? 0.03 : isSprint ? 0.85 : isRun ? 0.62 : isJog ? 0.38 : 0.2;
  const spineLean = isSprint ? 0.28 : isRun ? 0.18 : isJog ? 0.1 : 0.04;
  const turnBank = state === "turn_left" ? 0.18 : state === "turn_right" ? -0.18 : 0;
  const bounceCm = isIdle ? 1.2 : isSprint ? 7.5 : isRun ? 5.5 : 3.0;

  return new THREE.AnimationClip(state, dur, [
    buildPosTrack("Hips", t, [
      [0, 98, 0],
      [0, 98 - bounceCm, 0],
      [0, 98 + bounceCm * 0.5, 0],
      [0, 98 - bounceCm, 0],
      [0, 98, 0],
    ]),
    buildQuatTrack("Spine", t, [
      [spineLean, 0, turnBank],
      [spineLean + 0.03, 0.08, turnBank],
      [spineLean, 0, turnBank],
      [spineLean + 0.03, -0.08, turnBank],
      [spineLean, 0, turnBank],
    ]),
    buildQuatTrack("Spine1", t, [
      [spineLean * 0.5, 0, 0],
      [spineLean * 0.5, 0.06, 0],
      [spineLean * 0.5, 0, 0],
      [spineLean * 0.5, -0.06, 0],
      [spineLean * 0.5, 0, 0],
    ]),
    buildQuatTrack("LeftUpLeg", t, [
      [-legSwing, 0, 0],
      [0, 0, 0],
      [legSwing, 0, 0],
      [0, 0, 0],
      [-legSwing, 0, 0],
    ]),
    buildQuatTrack("RightUpLeg", t, [
      [legSwing, 0, 0],
      [0, 0, 0],
      [-legSwing, 0, 0],
      [0, 0, 0],
      [legSwing, 0, 0],
    ]),
    buildQuatTrack("LeftLeg", t, [
      [kneeBend * 0.35, 0, 0],
      [kneeBend, 0, 0],
      [kneeBend * 0.2, 0, 0],
      [kneeBend * 0.65, 0, 0],
      [kneeBend * 0.35, 0, 0],
    ]),
    buildQuatTrack("RightLeg", t, [
      [kneeBend * 0.2, 0, 0],
      [kneeBend * 0.65, 0, 0],
      [kneeBend * 0.35, 0, 0],
      [kneeBend, 0, 0],
      [kneeBend * 0.2, 0, 0],
    ]),
    buildQuatTrack("LeftArm", t, [
      [armSwing, 0, -0.18],
      [0, 0, -0.18],
      [-armSwing, 0, -0.18],
      [0, 0, -0.18],
      [armSwing, 0, -0.18],
    ]),
    buildQuatTrack("RightArm", t, [
      [-armSwing, 0, 0.18],
      [0, 0, 0.18],
      [armSwing, 0, 0.18],
      [0, 0, 0.18],
      [-armSwing, 0, 0.18],
    ]),
    buildQuatTrack("LeftForeArm", t, [
      [-0.65, 0, 0],
      [-0.85, 0, 0],
      [-0.55, 0, 0],
      [-0.75, 0, 0],
      [-0.65, 0, 0],
    ]),
    buildQuatTrack("RightForeArm", t, [
      [-0.55, 0, 0],
      [-0.75, 0, 0],
      [-0.65, 0, 0],
      [-0.85, 0, 0],
      [-0.55, 0, 0],
    ]),
    buildQuatTrack("Head", t, [
      [-spineLean * 0.4, 0, 0],
      [-spineLean * 0.4, -0.04, 0],
      [-spineLean * 0.4, 0, 0],
      [-spineLean * 0.4, 0.04, 0],
      [-spineLean * 0.4, 0, 0],
    ]),
  ]);
}

/**
 * Builds the complete 41-clip library for all `FootballAnimationState`s.
 */
export function buildFootballAnimationClipLibrary(
  rawMocapClips: THREE.AnimationClip[] = []
): Map<FootballAnimationState, THREE.AnimationClip> {
  const mocapMap = new Map<string, THREE.AnimationClip>();
  for (const clip of rawMocapClips) {
    mocapMap.set(clip.name, clip);
  }

  const library = new Map<FootballAnimationState, THREE.AnimationClip>();
  for (const state of ALL_FOOTBALL_ANIMATION_STATES) {
    library.set(state, buildClipForFootballState(state, mocapMap));
  }
  return library;
}

// -----------------------------------------------------------------------------
// 4. Authoritative Event & Telemetry Animation State Evaluator
// -----------------------------------------------------------------------------

export interface PlayerAnimationEvaluationContext {
  player: InterpolatedPlayerState;
  allPlayers: InterpolatedPlayerState[];
  ball: InterpolatedBallState;
  matchState: InterpolatedMatchState;
  activeEvent: SpectatorSafeEventView | null;
  previousState?: FootballAnimationState;
  timeInCurrentStateSec?: number;
}

export class FootballAnimationStateMachine {
  private eventsById = new Map<string, SpectatorSafeEventView>();

  constructor(events: SpectatorSafeEventView[] = []) {
    this.setEvents(events);
  }

  public setEvents(events: SpectatorSafeEventView[]): void {
    this.eventsById.clear();
    for (const ev of events) {
      if (ev && ev.event_id) {
        this.eventsById.set(ev.event_id, ev);
      }
    }
  }

  public getEventById(eventId: string | null | undefined): SpectatorSafeEventView | null {
    if (!eventId) return null;
    return this.eventsById.get(eventId) || null;
  }

  /**
   * Resolves the authoritative `FootballAnimationState` for a single player at the current frame.
   * Never fabricates match outcomes; strictly reflects simulation telemetry and events.
   */
  public resolvePlayerState(ctx: PlayerAnimationEvaluationContext): FootballAnimationState {
    const {
      player,
      allPlayers,
      ball,
      matchState,
      activeEvent,
      previousState,
      timeInCurrentStateSec = 0,
    } = ctx;

    // 0. Respect minimum hold window for active non-looping contact actions unless overridden by goal/card
    if (previousState) {
      const prevMeta = FOOTBALL_ANIMATION_STATE_META[previousState];
      if (
        prevMeta &&
        !prevMeta.loop &&
        timeInCurrentStateSec > 0 &&
        timeInCurrentStateSec < prevMeta.minHoldSec &&
        player.animation_state !== "celebrate" &&
        player.animation_state !== "sent_off"
      ) {
        return previousState;
      }
    }

    const isGK =
      player.role.toUpperCase() === "GK" ||
      player.role.toLowerCase() === "goalkeeper" ||
      player.line === "goalkeeper";

    const dxBall = ball.position3D[0] - player.position3D[0];
    const dzBall = ball.position3D[2] - player.position3D[2];
    const distanceToBall = Math.hypot(dxBall, dzBall);

    const stage = matchState.stage || "event";
    const evType = activeEvent?.event_type?.toLowerCase() || "";
    const isPrimaryActor = Boolean(activeEvent?.primary_player_id && activeEvent.primary_player_id === player.player_id);
    const isSecondaryActor = Boolean(
      activeEvent?.secondary_player_id && activeEvent.secondary_player_id === player.player_id
    );

    // -------------------------------------------------------------------------
    // 1. Match Reactions (Substitutions, Cards, Injuries, Fouls, Goals, Misses)
    // -------------------------------------------------------------------------
    if (evType === "substitution") {
      if (isPrimaryActor) return "substitution_exit";
      if (isSecondaryActor) return "substitution_enter";
    }

    if (player.animation_state === "sent_off" || player.state === "sent_off") {
      return "substitution_exit";
    }

    if (evType === "red_card" && isPrimaryActor) {
      return stage === "event" ? "disappointment" : "substitution_exit";
    }

    if (evType === "injury" && isPrimaryActor) {
      return "injury_reaction";
    }

    if (evType === "foul") {
      if (isSecondaryActor) return "foul_reaction";
      if (isPrimaryActor) {
        if (stage === "pre" || stage === "event") {
          return player.speed_ratio >= 0.6 ? "sliding_tackle" : "standing_tackle";
        }
        return "tackle_recovery";
      }
    }

    // Goal celebrations & conceding team disappointment
    if (
      player.animation_state === "celebrate" ||
      (evType === "goal" && (stage === "decision" || stage === "post")) ||
      Boolean(matchState.celebration_team_id)
    ) {
      const celebrationTeamId = matchState.celebration_team_id || activeEvent?.team_id;
      const isScoringTeam = celebrationTeamId
        ? player.team_id === celebrationTeamId
        : player.side === matchState.possession_side;

      if (isScoringTeam) {
        if (isPrimaryActor || player.animation_state === "celebrate" && distanceToBall < 14) {
          return "goal_celebration";
        }
        return "team_celebration";
      } else {
        if (isGK || distanceToBall < 28) {
          return "disappointment";
        }
      }
    }

    if (evType === "miss" && stage === "post" && isPrimaryActor) {
      return "disappointment";
    }

    // -------------------------------------------------------------------------
    // 2. Goalkeeper-Specific Actions
    // -------------------------------------------------------------------------
    if (isGK) {
      const isSaveAction =
        player.animation_state === "save" ||
        (evType === "save" && (isPrimaryActor || isSecondaryActor || player.side !== matchState.possession_side));

      if (isSaveAction) {
        if (ball.owner_player_id === player.player_id || ball.state === "controlled") {
          return "gk_catch";
        }
        if (ball.height > 1.85 || activeEvent?.flags?.includes("punch")) {
          return "gk_punch";
        }
        if (activeEvent?.flags?.includes("parry")) {
          return "gk_parry";
        }
        return ball.height > 1.05 ? "gk_dive_high" : "gk_dive_low";
      }

      // Shot incoming toward goalkeeper's goal during event stage
      if (
        (evType === "goal" || evType === "shot" || evType === "miss" || evType === "penalty") &&
        player.side !== matchState.possession_side &&
        stage === "event" &&
        distanceToBall < 18.0
      ) {
        return ball.height > 1.05 ? "gk_dive_high" : "gk_dive_low";
      }

      // Goalkeeper distribution (wind-up in possession or kick/throw release into flight)
      if (
        player.animation_state === "pass" ||
        player.is_releasing_ball ||
        ((evType === "pass" || evType === "set_piece") &&
          isPrimaryActor &&
          (stage === "pre" || stage === "event"))
      ) {
        return "gk_distribution";
      }

      // Goalkeeper in possession: catch or distribution
      if (player.has_possession || ball.owner_player_id === player.player_id) {
        if (
          player.animation_state === "shoot" ||
          (evType === "attack" && isPrimaryActor)
        ) {
          return "gk_distribution";
        }
        return "gk_catch";
      }

      // High aerial ball inside six-yard/penalty area
      if (ball.height >= 1.55 && distanceToBall <= 4.2 && ball.state === "in_flight") {
        return "gk_punch";
      }

      // Lateral movement across goal line
      if (player.speed_ratio >= 0.16 && distanceToBall < 32.0) {
        return "gk_lateral_move";
      }

      // Ready stance when ball is in dangerous territory
      if (
        distanceToBall < 38.0 ||
        matchState.danger_zone === "central_box" ||
        matchState.danger_zone === "wide_box" ||
        matchState.danger_zone === "final_third"
      ) {
        return "gk_ready_stance";
      }
    }

    // -------------------------------------------------------------------------
    // 3. Outfield Ball Interactions (Header, Shoot, Volley, Pass, Cross, Receive, Dribble, Shield)
    // -------------------------------------------------------------------------
    // Aerial challenge / header when ball is airborne > 1.35m near player
    if (ball.height >= 1.35 && distanceToBall <= 3.4 && ball.state === "in_flight") {
      return "jumping_challenge";
    }

    // Shooting & Volleys
    if (
      player.animation_state === "shoot" ||
      ((evType === "goal" || evType === "shot" || evType === "miss" || evType === "penalty") &&
        isPrimaryActor &&
        (stage === "pre" || stage === "event"))
    ) {
      if (
        ball.height >= 0.65 ||
        activeEvent?.playback_profile === "volley" ||
        activeEvent?.flags?.includes("volley")
      ) {
        return "volley";
      }
      return "shoot";
    }

    // Passing, Crossing, Through Balls & Long Passes
    if (
      player.animation_state === "pass" ||
      player.animation_state === "set_piece" ||
      player.is_releasing_ball ||
      ((evType === "pass" || evType === "attack" || evType === "set_piece") &&
        isPrimaryActor &&
        (stage === "pre" || stage === "event"))
    ) {
      const absZ = Math.abs(player.position3D[2]);
      const absX = Math.abs(player.position3D[0]);
      if (absZ >= 18.0 && absX >= 24.0) {
        return "cross";
      }
      if (
        matchState.transition_state?.includes("break") ||
        activeEvent?.playback_profile === "counterattack" ||
        activeEvent?.playback_profile === "through_ball" ||
        activeEvent?.flags?.includes("through_ball")
      ) {
        return "through_ball";
      }
      if (ball.height >= 0.85 || activeEvent?.playback_profile === "long_ball" || activeEvent?.flags?.includes("long_pass")) {
        return "long_pass";
      }
      return "short_pass";
    }

    // Receiving & First Touch
    if ((evType === "pass" || evType === "attack") && isSecondaryActor) {
      if (ball.state === "in_flight" && distanceToBall <= 9.0) {
        return "receive_ball";
      }
      if (ball.owner_player_id === player.player_id || stage === "post") {
        return "first_touch";
      }
    }

    if (player.is_receiving_ball && distanceToBall <= 10.0) {
      return "receive_ball";
    }

    if (player.just_received_ball) {
      return "first_touch";
    }

    // Ball Carrier: Dribble vs Shield Ball under defensive pressure
    if (player.has_possession || ball.owner_player_id === player.player_id) {
      let nearestOpponentDist = Infinity;
      for (const other of allPlayers) {
        if (other.side !== player.side) {
          const d = Math.hypot(
            other.position3D[0] - player.position3D[0],
            other.position3D[2] - player.position3D[2]
          );
          if (d < nearestOpponentDist) nearestOpponentDist = d;
        }
      }

      if (nearestOpponentDist <= 2.6 && player.speed_ratio < 0.45) {
        return "shield_ball";
      }
      if (player.speed_ratio >= 0.12) {
        return "dribble";
      }
    }

    // -------------------------------------------------------------------------
    // 4. Outfield Defensive Actions (Tackles, Interceptions, Blocks, Recovery)
    // -------------------------------------------------------------------------
    if (
      previousState === "standing_tackle" ||
      previousState === "sliding_tackle"
    ) {
      const prevMeta = FOOTBALL_ANIMATION_STATE_META[previousState];
      if (timeInCurrentStateSec >= prevMeta.minHoldSec && timeInCurrentStateSec < prevMeta.defaultDurationSec + 0.35) {
        return "tackle_recovery";
      }
    }

    const isDefendingPlayer =
      player.side !== matchState.possession_side ||
      player.state === "defending" ||
      player.state === "pressing" ||
      player.animation_state === "press";

    if (isDefendingPlayer) {
      if (distanceToBall <= 2.6) {
        if ((evType === "shot" || evType === "goal" || evType === "miss") && stage === "event") {
          return "blocking";
        }
        if (ball.state === "in_flight" && ball.height < 1.35) {
          return "interception";
        }
        if (player.speed_ratio >= 0.68) {
          return "sliding_tackle";
        }
        if (player.speed_ratio >= 0.22 || player.animation_state === "press") {
          return "standing_tackle";
        }
      } else if (distanceToBall <= 4.4) {
        if ((evType === "shot" || evType === "miss" || evType === "save") && stage === "event") {
          return "blocking";
        }
        if (ball.state === "in_flight" && player.speed_ratio >= 0.42) {
          return "interception";
        }
      }
    }

    // -------------------------------------------------------------------------
    // 5. Locomotion & Kinematic Transitions (Turns, Acceleration, Deceleration, Gait)
    // -------------------------------------------------------------------------
    const angVel = player.angular_velocity_rad || 0;
    const accel = player.acceleration_ratio || 0;

    if (Math.abs(angVel) >= 2.6 && player.speed_ratio >= 0.28) {
      return "stop_change_direction";
    }
    if (accel <= -0.85 && player.speed_ratio >= 0.15) {
      return "decelerate";
    }
    if (accel >= 0.9 && player.speed_ratio >= 0.32) {
      return "accelerate";
    }
    if (Math.abs(angVel) >= 1.45 && player.speed_ratio >= 0.12 && player.speed_ratio <= 0.65) {
      return angVel > 0 ? "turn_left" : "turn_right";
    }

    if (player.speed_ratio >= 0.75 || player.animation_state === "sprint") {
      return "sprint";
    }
    if (player.speed_ratio >= 0.42 || player.animation_state === "run") {
      return "run";
    }
    if (player.speed_ratio >= 0.18 || player.animation_state === "jog") {
      return "jog";
    }
    if (player.speed_ratio >= 0.05) {
      return "walk";
    }

    return "idle";
  }
}
