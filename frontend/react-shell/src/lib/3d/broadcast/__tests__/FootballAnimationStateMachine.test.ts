/**
 * GTEX Unit 2A (U2A-006) — Humanoid Football Animation Engine
 * Unit & Synchronization Tests for FootballAnimationStateMachine.
 */

import {
  ALL_FOOTBALL_ANIMATION_STATES,
  buildFootballAnimationClipLibrary,
  FOOTBALL_ANIMATION_STATE_META,
  FootballAnimationStateMachine,
  GTEX_HUMANOID_BONE_NAMES,
  GTEX_HUMANOID_BONE_SPECS,
} from "../FootballAnimationStateMachine";
import { InterpolatedBallState, InterpolatedMatchState, InterpolatedPlayerState } from "../SpatialInterpolator";
import { SpectatorSafeEventView } from "../spectatorContract";

function makePlayer(overrides: Partial<InterpolatedPlayerState> = {}): InterpolatedPlayerState {
  return {
    player_id: "home_10",
    team_id: "home_lions",
    side: "home",
    shirt_number: 10,
    label: "10",
    role: "MID",
    line: "midfield",
    state: "moving",
    active: true,
    highlighted: false,
    position3D: [0, 0, 0],
    facingAngleRad: 0,
    animation_state: "idle",
    speed_ratio: 0,
    has_possession: false,
    angular_velocity_rad: 0,
    acceleration_ratio: 0,
    just_received_ball: false,
    ...overrides,
  };
}

function makeBall(overrides: Partial<InterpolatedBallState> = {}): InterpolatedBallState {
  return {
    position3D: [0, 0.05, 0],
    height: 0.05,
    state: "controlled",
    owner_player_id: "home_10",
    ...overrides,
  };
}

function makeMatchState(
  players: InterpolatedPlayerState[],
  ball: InterpolatedBallState,
  overrides: Partial<InterpolatedMatchState> = {}
): InterpolatedMatchState {
  return {
    time_seconds: 10,
    clock_minute: 15,
    phase: "open_play",
    stage: "event",
    home_score: 0,
    away_score: 0,
    home_attacks_right: true,
    possession_side: "home",
    camera_preset: "broadcast",
    active_event_id: null,
    event_banner: null,
    players,
    ball,
    ...overrides,
  };
}

describe("FootballAnimationStateMachine", () => {
  it("defines the canonical 26-bone GTEX Humanoid Skeleton hierarchy", () => {
    expect(GTEX_HUMANOID_BONE_SPECS).toHaveLength(26);
    expect(GTEX_HUMANOID_BONE_NAMES[0]).toBe("Hips");
    expect(GTEX_HUMANOID_BONE_NAMES).toContain("Spine");
    expect(GTEX_HUMANOID_BONE_NAMES).toContain("Spine1");
    expect(GTEX_HUMANOID_BONE_NAMES).toContain("Spine2");
    expect(GTEX_HUMANOID_BONE_NAMES).toContain("Neck");
    expect(GTEX_HUMANOID_BONE_NAMES).toContain("Head");
    expect(GTEX_HUMANOID_BONE_NAMES).toContain("LeftUpLeg");
    expect(GTEX_HUMANOID_BONE_NAMES).toContain("LeftLeg");
    expect(GTEX_HUMANOID_BONE_NAMES).toContain("LeftFoot");
    expect(GTEX_HUMANOID_BONE_NAMES).toContain("RightUpLeg");
    expect(GTEX_HUMANOID_BONE_NAMES).toContain("RightLeg");
    expect(GTEX_HUMANOID_BONE_NAMES).toContain("RightFoot");
    expect(GTEX_HUMANOID_BONE_NAMES).toContain("LeftArm");
    expect(GTEX_HUMANOID_BONE_NAMES).toContain("LeftForeArm");
    expect(GTEX_HUMANOID_BONE_NAMES).toContain("LeftHand");
    expect(GTEX_HUMANOID_BONE_NAMES).toContain("RightArm");
    expect(GTEX_HUMANOID_BONE_NAMES).toContain("RightForeArm");
    expect(GTEX_HUMANOID_BONE_NAMES).toContain("RightHand");
  });

  it("builds valid 26-bone AnimationClips for all 41 football animation states across all 5 categories", () => {
    expect(ALL_FOOTBALL_ANIMATION_STATES).toHaveLength(41);
    const clipLib = buildFootballAnimationClipLibrary([]);
    expect(clipLib.size).toBe(41);

    const validBoneSet = new Set(GTEX_HUMANOID_BONE_NAMES);
    for (const state of ALL_FOOTBALL_ANIMATION_STATES) {
      const clip = clipLib.get(state);
      expect(clip).toBeDefined();
      expect(clip!.duration).toBeGreaterThan(0.3);
      expect(clip!.tracks.length).toBeGreaterThanOrEqual(4);
      for (const track of clip!.tracks) {
        const boneName = track.name.split(".")[0];
        expect(validBoneSet.has(boneName)).toBe(true);
      }
      expect(FOOTBALL_ANIMATION_STATE_META[state]).toBeDefined();
    }
  });

  it("resolves all locomotion states (idle, walk, jog, run, sprint, turns, accelerate, decelerate, stop_change_direction)", () => {
    const fsm = new FootballAnimationStateMachine();
    const ball = makeBall({ position3D: [30, 0.05, 20], owner_player_id: "away_6" });

    const evalLocomotion = (overrides: Partial<InterpolatedPlayerState>) => {
      const p = makePlayer(overrides);
      const ms = makeMatchState([p], ball);
      return fsm.resolvePlayerState({
        player: p,
        allPlayers: [p],
        ball,
        matchState: ms,
        activeEvent: null,
      });
    };

    expect(evalLocomotion({ speed_ratio: 0.01 })).toBe("idle");
    expect(evalLocomotion({ speed_ratio: 0.10 })).toBe("walk");
    expect(evalLocomotion({ speed_ratio: 0.25 })).toBe("jog");
    expect(evalLocomotion({ speed_ratio: 0.55 })).toBe("run");
    expect(evalLocomotion({ speed_ratio: 0.85 })).toBe("sprint");
    expect(evalLocomotion({ speed_ratio: 0.35, angular_velocity_rad: 1.8 })).toBe("turn_left");
    expect(evalLocomotion({ speed_ratio: 0.35, angular_velocity_rad: -1.8 })).toBe("turn_right");
    expect(evalLocomotion({ speed_ratio: 0.45, acceleration_ratio: 1.2 })).toBe("accelerate");
    expect(evalLocomotion({ speed_ratio: 0.30, acceleration_ratio: -1.1 })).toBe("decelerate");
    expect(evalLocomotion({ speed_ratio: 0.40, angular_velocity_rad: 3.1 })).toBe("stop_change_direction");
  });

  it("synchronizes ball interaction states (short_pass, long_pass, through_ball, cross, receive_ball, first_touch, dribble, shield_ball, shoot, volley)", () => {
    const passEvent: SpectatorSafeEventView = {
      event_id: "ev_pass",
      sequence: 1,
      event_type: "pass",
      minute: 10,
      added_time: 0,
      clock_label: "10'",
      home_score: 0,
      away_score: 0,
      banner_text: "Pass",
      commentary: "Pass",
      primary_player_id: "home_10",
      secondary_player_id: "home_9",
    };

    const fsm = new FootballAnimationStateMachine([passEvent]);
    const passer = makePlayer({ player_id: "home_10", animation_state: "pass", has_possession: true });
    const receiver = makePlayer({ player_id: "home_9", position3D: [12, 0, 0] });
    const ballInFlight = makeBall({ position3D: [9, 0.2, 0], state: "in_flight", owner_player_id: null });
    const ms = makeMatchState([passer, receiver], ballInFlight, { active_event_id: "ev_pass" });

    // Short pass & Receive ball
    expect(
      fsm.resolvePlayerState({
        player: passer,
        allPlayers: [passer, receiver],
        ball: ballInFlight,
        matchState: ms,
        activeEvent: passEvent,
      })
    ).toBe("short_pass");

    expect(
      fsm.resolvePlayerState({
        player: receiver,
        allPlayers: [passer, receiver],
        ball: ballInFlight,
        matchState: ms,
        activeEvent: passEvent,
      })
    ).toBe("receive_ball");

    // First touch upon receiving ownership
    const ballControlled = makeBall({ position3D: [12, 0.05, 0], state: "controlled", owner_player_id: "home_9" });
    expect(
      fsm.resolvePlayerState({
        player: { ...receiver, has_possession: true, just_received_ball: true },
        allPlayers: [passer, receiver],
        ball: ballControlled,
        matchState: { ...ms, stage: "post" },
        activeEvent: passEvent,
      })
    ).toBe("first_touch");

    // Through ball on transition break
    expect(
      fsm.resolvePlayerState({
        player: passer,
        allPlayers: [passer, receiver],
        ball: ballInFlight,
        matchState: { ...ms, transition_state: "home_break" },
        activeEvent: passEvent,
      })
    ).toBe("through_ball");

    // Long pass when aerial
    expect(
      fsm.resolvePlayerState({
        player: passer,
        allPlayers: [passer, receiver],
        ball: { ...ballInFlight, height: 1.4 },
        matchState: ms,
        activeEvent: passEvent,
      })
    ).toBe("long_pass");

    // Wide cross from flank
    expect(
      fsm.resolvePlayerState({
        player: { ...passer, position3D: [35, 0, 24] },
        allPlayers: [passer, receiver],
        ball: ballInFlight,
        matchState: ms,
        activeEvent: passEvent,
      })
    ).toBe("cross");

    // Dribble vs Shield ball
    const dribbler = makePlayer({ player_id: "home_10", has_possession: true, speed_ratio: 0.55 });
    expect(
      fsm.resolvePlayerState({
        player: dribbler,
        allPlayers: [dribbler],
        ball: makeBall({ owner_player_id: "home_10" }),
        matchState: ms,
        activeEvent: null,
      })
    ).toBe("dribble");

    const tightDefender = makePlayer({ player_id: "away_4", side: "away", position3D: [1.2, 0, 0] });
    expect(
      fsm.resolvePlayerState({
        player: { ...dribbler, speed_ratio: 0.2 },
        allPlayers: [dribbler, tightDefender],
        ball: makeBall({ owner_player_id: "home_10" }),
        matchState: ms,
        activeEvent: null,
      })
    ).toBe("shield_ball");

    // Shoot & Volley
    const shooter = makePlayer({ player_id: "home_9", animation_state: "shoot" });
    expect(
      fsm.resolvePlayerState({
        player: shooter,
        allPlayers: [shooter],
        ball: makeBall({ height: 0.1 }),
        matchState: ms,
        activeEvent: null,
      })
    ).toBe("shoot");

    expect(
      fsm.resolvePlayerState({
        player: shooter,
        allPlayers: [shooter],
        ball: makeBall({ height: 0.95 }),
        matchState: ms,
        activeEvent: null,
      })
    ).toBe("volley");
  });

  it("synchronizes defensive, goalkeeper, and match reaction states with authoritative events", () => {
    const saveEv: SpectatorSafeEventView = {
      event_id: "ev_save",
      sequence: 2,
      event_type: "save",
      minute: 25,
      added_time: 0,
      clock_label: "25'",
      home_score: 0,
      away_score: 0,
      banner_text: "Save",
      commentary: "Save",
      primary_player_id: "away_1",
      secondary_player_id: "home_9",
    };
    const goalEv: SpectatorSafeEventView = {
      event_id: "ev_goal",
      sequence: 3,
      event_type: "goal",
      minute: 60,
      added_time: 0,
      clock_label: "60'",
      home_score: 1,
      away_score: 0,
      banner_text: "Goal",
      commentary: "Goal",
      team_id: "home_lions",
      primary_player_id: "home_9",
    };

    const fsm = new FootballAnimationStateMachine([saveEv, goalEv]);
    const gk = makePlayer({ player_id: "away_1", team_id: "away_stars", side: "away", role: "GK", position3D: [48, 0, 0] });

    // Goalkeeper high dive vs low dive vs catch
    expect(
      fsm.resolvePlayerState({
        player: { ...gk, animation_state: "save" },
        allPlayers: [gk],
        ball: makeBall({ position3D: [47, 1.45, 1], height: 1.45, state: "in_flight", owner_player_id: null }),
        matchState: makeMatchState([gk], makeBall(), { active_event_id: "ev_save" }),
        activeEvent: saveEv,
      })
    ).toBe("gk_dive_high");

    expect(
      fsm.resolvePlayerState({
        player: { ...gk, animation_state: "save" },
        allPlayers: [gk],
        ball: makeBall({ position3D: [47, 0.35, 1], height: 0.35, state: "in_flight", owner_player_id: null }),
        matchState: makeMatchState([gk], makeBall(), { active_event_id: "ev_save" }),
        activeEvent: saveEv,
      })
    ).toBe("gk_dive_low");

    expect(
      fsm.resolvePlayerState({
        player: { ...gk, animation_state: "save", has_possession: true },
        allPlayers: [gk],
        ball: makeBall({ position3D: [48, 0.8, 0], height: 0.8, state: "controlled", owner_player_id: "away_1" }),
        matchState: makeMatchState([gk], makeBall(), { active_event_id: "ev_save" }),
        activeEvent: saveEv,
      })
    ).toBe("gk_catch");

    // Aerial header challenge
    const defender = makePlayer({ player_id: "away_4", side: "away", role: "DEF", position3D: [40, 0, 0] });
    expect(
      fsm.resolvePlayerState({
        player: defender,
        allPlayers: [defender],
        ball: makeBall({ position3D: [40.5, 1.9, 0], height: 1.9, state: "in_flight", owner_player_id: null }),
        matchState: makeMatchState([defender], makeBall()),
        activeEvent: null,
      })
    ).toBe("jumping_challenge");

    // Goal celebration (scorer) + Team celebration (teammate) + Disappointment (opponent)
    const scorer = makePlayer({ player_id: "home_9", team_id: "home_lions", side: "home", animation_state: "celebrate" });
    const teammate = makePlayer({ player_id: "home_8", team_id: "home_lions", side: "home", animation_state: "celebrate", position3D: [20, 0, 10] });
    const goalMs = makeMatchState([scorer, teammate, gk], makeBall({ position3D: [50, 0, 0] }), {
      stage: "decision",
      celebration_team_id: "home_lions",
      active_event_id: "ev_goal",
    });

    expect(
      fsm.resolvePlayerState({
        player: scorer,
        allPlayers: [scorer, teammate, gk],
        ball: goalMs.ball,
        matchState: goalMs,
        activeEvent: goalEv,
      })
    ).toBe("goal_celebration");

    expect(
      fsm.resolvePlayerState({
        player: teammate,
        allPlayers: [scorer, teammate, gk],
        ball: goalMs.ball,
        matchState: goalMs,
        activeEvent: goalEv,
      })
    ).toBe("team_celebration");

    expect(
      fsm.resolvePlayerState({
        player: gk,
        allPlayers: [scorer, teammate, gk],
        ball: goalMs.ball,
        matchState: goalMs,
        activeEvent: goalEv,
      })
    ).toBe("disappointment");
  });
});
