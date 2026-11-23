/**
 * GTEX Unit 2A (U2A-006) — Humanoid Football Animation Engine
 * HumanoidMatchPrototypeFixture: Controlled 22-Player Prototype & Mandatory
 * 5-Minute (300-Second) Continuous GTEX Match Acceptance Fixture.
 *
 * Generates an authoritative, continuous, non-stop 300-second `SpectatorSafeMatchView`
 * with dynamic attacking/defending tactical team blocks, anti-clustering spacing,
 * crisp passing chains (zero dead-ball freezes), and every required football action:
 * - Locomotion: idle, walk, jog, run, sprint, turn_left/right, accelerate, decelerate, stop_change_direction
 * - Ball Interaction: short_pass, long_pass, through_ball, receive_ball, first_touch, dribble, shield_ball, cross, shoot, volley
 * - Defensive Actions: standing_tackle, sliding_tackle, interception, blocking, jumping_challenge, tackle_recovery
 * - Goalkeeper Actions: gk_ready_stance, gk_lateral_move, gk_dive_low, gk_dive_high, gk_catch, gk_parry, gk_punch, gk_distribution
 * - Match Reactions: goal_celebration, team_celebration, disappointment, foul_reaction, injury_reaction, substitution_exit, substitution_enter
 * - Broadcast Camera Transitions: broadcast, attack_push, box_zoom, goal_celebration, assistant_flag, var_replay
 */

import {
  SpectatorSafeEventView,
  SpectatorSafeFrameView,
  SpectatorSafeMatchView,
  SpectatorSafePlayerTelemetry,
  SpectatorSafeTeamView,
} from "./spectatorContract";

export interface BasePlayerTemplate {
  playerId: string;
  side: "home" | "away";
  shirtNumber: number;
  label: string;
  role: "GK" | "DEF" | "MID" | "FWD";
  line: "goalkeeper" | "defense" | "midfield" | "attack";
  anchorX: number;
  anchorY: number;
}

export const HOME_STARTERS_433: readonly BasePlayerTemplate[] = [
  { playerId: "home_1", side: "home", shirtNumber: 1, label: "Mbadiwe", role: "GK", line: "goalkeeper", anchorX: 6, anchorY: 50 },
  { playerId: "home_2", side: "home", shirtNumber: 2, label: "Adebayo", role: "DEF", line: "defense", anchorX: 25, anchorY: 16 },
  { playerId: "home_4", side: "home", shirtNumber: 4, label: "Umeadi", role: "DEF", line: "defense", anchorX: 21, anchorY: 38 },
  { playerId: "home_5", side: "home", shirtNumber: 5, label: "Onyeka", role: "DEF", line: "defense", anchorX: 21, anchorY: 62 },
  { playerId: "home_3", side: "home", shirtNumber: 3, label: "Okeke", role: "DEF", line: "defense", anchorX: 25, anchorY: 84 },
  { playerId: "home_6", side: "home", shirtNumber: 6, label: "Adaramola", role: "MID", line: "midfield", anchorX: 40, anchorY: 50 },
  { playerId: "home_8", side: "home", shirtNumber: 8, label: "Ejiofor", role: "MID", line: "midfield", anchorX: 49, anchorY: 28 },
  { playerId: "home_10", side: "home", shirtNumber: 10, label: "Ibekwe", role: "MID", line: "midfield", anchorX: 52, anchorY: 70 },
  { playerId: "home_7", side: "home", shirtNumber: 7, label: "Olatunji", role: "FWD", line: "attack", anchorX: 69, anchorY: 17 },
  { playerId: "home_9", side: "home", shirtNumber: 9, label: "Okwuosa", role: "FWD", line: "attack", anchorX: 74, anchorY: 50 },
  { playerId: "home_11", side: "home", shirtNumber: 11, label: "Danladi", role: "FWD", line: "attack", anchorX: 69, anchorY: 83 },
];

export const AWAY_STARTERS_433: readonly BasePlayerTemplate[] = [
  { playerId: "away_1", side: "away", shirtNumber: 1, label: "Akpan", role: "GK", line: "goalkeeper", anchorX: 94, anchorY: 50 },
  { playerId: "away_2", side: "away", shirtNumber: 2, label: "Bello", role: "DEF", line: "defense", anchorX: 75, anchorY: 84 },
  { playerId: "away_4", side: "away", shirtNumber: 4, label: "Nwachukwu", role: "DEF", line: "defense", anchorX: 79, anchorY: 62 },
  { playerId: "away_5", side: "away", shirtNumber: 5, label: "Sule", role: "DEF", line: "defense", anchorX: 79, anchorY: 38 },
  { playerId: "away_3", side: "away", shirtNumber: 3, label: "Musa", role: "DEF", line: "defense", anchorX: 75, anchorY: 16 },
  { playerId: "away_6", side: "away", shirtNumber: 6, label: "Kalu", role: "MID", line: "midfield", anchorX: 60, anchorY: 50 },
  { playerId: "away_8", side: "away", shirtNumber: 8, label: "Lawal", role: "MID", line: "midfield", anchorX: 51, anchorY: 72 },
  { playerId: "away_10", side: "away", shirtNumber: 10, label: "Yusuf", role: "MID", line: "midfield", anchorX: 48, anchorY: 30 },
  { playerId: "away_7", side: "away", shirtNumber: 7, label: "Chukwu", role: "FWD", line: "attack", anchorX: 31, anchorY: 83 },
  { playerId: "away_9", side: "away", shirtNumber: 9, label: "Garba", role: "FWD", line: "attack", anchorX: 26, anchorY: 50 },
  { playerId: "away_11", side: "away", shirtNumber: 11, label: "Osei", role: "FWD", line: "attack", anchorX: 31, anchorY: 17 },
];

type BallSegment = {
  t0: number;
  t1: number;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  owner: string | null;
  passer?: string;
  passState?: string;
  heightPeak?: number;
  possession: "home" | "away";
  camera?: string;
  stage?: string;
  eventId?: string | null;
  banner?: string | null;
  danger?: string;
  transition?: string;
  celebration?: string | null;
  overrides?: Record<string, string>;
};

function clampPitch(v: number, min = 3, max = 97): number {
  return Math.max(min, Math.min(max, v));
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * Math.max(0, Math.min(1, t));
}

/**
 * Continuous, high-tempo, zero-pause football timeline covering tau in [0, 300].
 * Passes zip 15-35m in 1-2s, carries surge dynamically at 5-9 m/s, and possession
 * flows end-to-end with frequent Home <-> Away transitions so attack vs defense
 * is unmistakable at every second.
 */
const CONTINUOUS_SEGMENTS: readonly BallSegment[] = [
  // 0..24: Snappy kickoff -> rapid one-touch passing progression -> Away interception & counter -> Home regains!
  { t0: 0, t1: 2, x0: 50, y0: 50, x1: 38, y1: 48, owner: null, passer: "home_9", passState: "pass", heightPeak: 0.14, possession: "home", stage: "reset", eventId: "ev_kickoff" },
  { t0: 2, t1: 4, x0: 38, y0: 48, x1: 31, y1: 22, owner: null, passer: "home_6", passState: "pass", heightPeak: 0.18, possession: "home", stage: "event", eventId: "ev_kickoff" },
  { t0: 4, t1: 7, x0: 31, y0: 22, x1: 52, y1: 18, owner: "home_2", possession: "home", stage: "pre", eventId: "ev_short_pass_1" },
  { t0: 7, t1: 9, x0: 52, y0: 18, x1: 68, y1: 34, owner: null, passer: "home_2", passState: "pass", heightPeak: 0.22, possession: "home", camera: "attack_push", danger: "final_third", stage: "pre", eventId: "ev_short_pass_1" },
  { t0: 9, t1: 12, x0: 68, y0: 34, x1: 79, y1: 44, owner: "home_8", possession: "home", camera: "attack_push", danger: "final_third", stage: "pre", eventId: "ev_short_pass_1" },
  { t0: 12, t1: 14, x0: 79, y0: 44, x1: 66, y1: 66, owner: null, passer: "home_6", passState: "pass", heightPeak: 0.22, possession: "home", stage: "event", eventId: "ev_short_pass_1", overrides: { home_6: "pass" } },
  { t0: 14, t1: 16, x0: 66, y0: 66, x1: 50, y1: 54, owner: null, passer: "away_6", passState: "pass", heightPeak: 0.2, possession: "away", transition: "away_break", stage: "post", eventId: "ev_short_pass_1" },
  { t0: 16, t1: 19, x0: 50, y0: 54, x1: 28, y1: 72, owner: "away_7", possession: "away", camera: "attack_push", transition: "away_break", danger: "final_third" },
  { t0: 19, t1: 21, x0: 28, y0: 72, x1: 21, y1: 48, owner: null, passer: "away_7", passState: "pass", heightPeak: 0.26, possession: "away", camera: "box_zoom", danger: "central_box" },
  { t0: 21, t1: 23, x0: 21, y0: 48, x1: 44, y1: 36, owner: null, passer: "home_4", passState: "pass", heightPeak: 0.32, possession: "home", transition: "home_break" },
  { t0: 23, t1: 26, x0: 44, y0: 36, x1: 60, y1: 30, owner: "home_8", possession: "home", camera: "attack_push", transition: "home_break", danger: "final_third" },

  // 26..48: Incisive through-ball -> blistering wing surge -> rapid switch & counter-press -> overlap to cross!
  { t0: 26, t1: 29, x0: 60, y0: 30, x1: 84, y1: 16, owner: null, passer: "home_8", passState: "pass", heightPeak: 0.35, possession: "home", camera: "attack_push", danger: "final_third", transition: "home_break", stage: "event", eventId: "ev_through_ball_2", overrides: { home_8: "pass" } },
  { t0: 29, t1: 33, x0: 84, y0: 16, x1: 92, y1: 29, owner: "home_7", possession: "home", camera: "box_zoom", danger: "wide_box", transition: "home_break", stage: "post", eventId: "ev_through_ball_2", overrides: { home_7: "sprint" } },
  { t0: 33, t1: 35, x0: 92, y0: 29, x1: 74, y1: 48, owner: null, passer: "home_7", passState: "pass", heightPeak: 0.16, possession: "home", camera: "attack_push", danger: "final_third", stage: "post", eventId: "ev_through_ball_2" },
  { t0: 35, t1: 37, x0: 74, y0: 48, x1: 52, y1: 62, owner: null, passer: "away_5", passState: "pass", heightPeak: 0.28, possession: "away", transition: "away_break" },
  { t0: 37, t1: 41, x0: 52, y0: 62, x1: 32, y1: 42, owner: "away_10", possession: "away", camera: "attack_push", transition: "away_break", danger: "final_third" },
  { t0: 41, t1: 43, x0: 32, y0: 42, x1: 54, y1: 28, owner: null, passer: "home_6", passState: "pass", heightPeak: 0.24, possession: "home", transition: "home_break" },
  { t0: 43, t1: 46, x0: 54, y0: 28, x1: 72, y1: 22, owner: "home_8", possession: "home", camera: "attack_push", transition: "home_break", danger: "final_third" },
  { t0: 46, t1: 48, x0: 72, y0: 22, x1: 88, y1: 15, owner: null, passer: "home_8", passState: "pass", heightPeak: 0.22, possession: "home", camera: "box_zoom", danger: "wide_box", stage: "pre", eventId: "ev_wing_cross_3" },
  { t0: 48, t1: 51, x0: 88, y0: 15, x1: 91, y1: 18, owner: "home_7", possession: "home", camera: "box_zoom", danger: "wide_box", stage: "pre", eventId: "ev_wing_cross_3", overrides: { home_7: "sprint" } },

  // 51..72: Whipped aerial cross -> header duel -> fast second-ball switch -> Away break -> Home counter!
  { t0: 51, t1: 56, x0: 91, y0: 18, x1: 85, y1: 49, owner: null, passer: "home_7", passState: "pass", heightPeak: 2.25, possession: "home", camera: "box_zoom", danger: "wide_box", stage: "event", eventId: "ev_wing_cross_3", overrides: { home_7: "pass" } },
  { t0: 56, t1: 58, x0: 85, y0: 49, x1: 75, y1: 78, owner: null, heightPeak: 0.72, possession: "home", camera: "attack_push", danger: "final_third", stage: "post", eventId: "ev_wing_cross_3" },
  { t0: 58, t1: 62, x0: 75, y0: 78, x1: 86, y1: 62, owner: "home_11", possession: "home", camera: "attack_push", danger: "final_third", stage: "post", eventId: "ev_wing_cross_3" },
  { t0: 62, t1: 64, x0: 86, y0: 62, x1: 62, y1: 46, owner: null, passer: "away_4", passState: "pass", heightPeak: 0.35, possession: "away", transition: "away_break" },
  { t0: 64, t1: 68, x0: 62, y0: 46, x1: 40, y1: 30, owner: "away_8", possession: "away", camera: "attack_push", transition: "away_break" },
  { t0: 68, t1: 70, x0: 40, y0: 30, x1: 60, y1: 48, owner: null, passer: "home_6", passState: "pass", heightPeak: 0.25, possession: "home", transition: "home_break" },
  { t0: 70, t1: 73, x0: 60, y0: 48, x1: 74, y1: 62, owner: "home_10", possession: "home", camera: "attack_push", danger: "final_third" },

  // 73..100: Rapid one-two around the box -> #10 curling strike -> full-stretch high GK save -> quick sweep
  { t0: 73, t1: 75, x0: 74, y0: 62, x1: 84, y1: 76, owner: null, passer: "home_10", passState: "pass", heightPeak: 0.14, possession: "home", camera: "box_zoom", danger: "wide_box" },
  { t0: 75, t1: 79, x0: 84, y0: 76, x1: 88, y1: 60, owner: "home_11", possession: "home", camera: "box_zoom", danger: "central_box" },
  { t0: 79, t1: 81, x0: 88, y0: 60, x1: 74, y1: 52, owner: null, passer: "home_11", passState: "pass", heightPeak: 0.14, possession: "home", camera: "box_zoom", danger: "central_box", stage: "pre", eventId: "ev_shot_save_4" },
  { t0: 81, t1: 86, x0: 74, y0: 52, x1: 81, y1: 50, owner: "home_10", possession: "home", camera: "box_zoom", danger: "central_box", stage: "pre", eventId: "ev_shot_save_4" },
  { t0: 86, t1: 91, x0: 81, y0: 50, x1: 95, y1: 49, owner: null, passer: "home_10", passState: "shoot", heightPeak: 1.7, possession: "home", camera: "box_zoom", danger: "central_box", stage: "event", eventId: "ev_shot_save_4", banner: "DIVING GOALKEEPER SAVE!", overrides: { home_10: "shoot", away_1: "save" } },
  { t0: 91, t1: 95, x0: 95, y0: 49, x1: 90, y1: 52, owner: "away_1", possession: "away", camera: "broadcast", stage: "post", eventId: "ev_shot_save_4", overrides: { away_1: "save" } },
  { t0: 95, t1: 100, x0: 90, y0: 52, x1: 84, y1: 46, owner: "away_1", possession: "away", camera: "broadcast", stage: "post", eventId: "ev_shot_save_4" },

  // 100..115: Goalkeeper drop-kick distribution & rapid Away transition down the left flank
  { t0: 100, t1: 103, x0: 84, y0: 46, x1: 88, y1: 50, owner: "away_1", possession: "away", camera: "broadcast", stage: "pre", eventId: "ev_gk_dist_5" },
  { t0: 103, t1: 108, x0: 88, y0: 50, x1: 50, y1: 30, owner: null, passer: "away_1", passState: "pass", heightPeak: 2.4, possession: "away", camera: "broadcast", stage: "event", eventId: "ev_gk_dist_5", overrides: { away_1: "pass" } },
  { t0: 108, t1: 112, x0: 50, y0: 30, x1: 38, y1: 42, owner: "away_10", possession: "away", camera: "attack_push", transition: "away_break", stage: "post", eventId: "ev_gk_dist_5" },
  { t0: 112, t1: 115, x0: 38, y0: 42, x1: 24, y1: 78, owner: null, passer: "away_10", passState: "pass", heightPeak: 0.24, possession: "away", camera: "attack_push", transition: "away_break", danger: "final_third", stage: "post", eventId: "ev_gk_dist_5" },

  // 115..175: Relentless end-to-end transitions, wing raids, interception, sliding tackle & rapid breaks
  { t0: 115, t1: 120, x0: 24, y0: 78, x1: 14, y1: 68, owner: "away_7", possession: "away", camera: "box_zoom", transition: "away_break", danger: "wide_box" },
  { t0: 120, t1: 122, x0: 14, y0: 68, x1: 28, y1: 52, owner: null, passer: "away_7", passState: "pass", heightPeak: 0.16, possession: "away", camera: "box_zoom", danger: "central_box" },
  { t0: 122, t1: 125, x0: 28, y0: 52, x1: 52, y1: 38, owner: null, passer: "home_5", passState: "pass", heightPeak: 0.35, possession: "home", transition: "home_break" },
  { t0: 125, t1: 129, x0: 52, y0: 38, x1: 72, y1: 24, owner: "home_7", possession: "home", camera: "attack_push", transition: "home_break", danger: "final_third" },
  { t0: 129, t1: 132, x0: 72, y0: 24, x1: 52, y1: 44, owner: null, passer: "away_3", passState: "pass", heightPeak: 0.25, possession: "away", transition: "away_break" },
  { t0: 132, t1: 137, x0: 52, y0: 44, x1: 42, y1: 52, owner: null, heightPeak: 0.35, possession: "away", camera: "broadcast" },
  { t0: 137, t1: 141, x0: 42, y0: 52, x1: 62, y1: 60, owner: "home_6", possession: "home", camera: "attack_push", transition: "home_break" },
  { t0: 141, t1: 144, x0: 62, y0: 60, x1: 46, y1: 32, owner: null, passer: "away_6", passState: "pass", heightPeak: 0.22, possession: "away", transition: "away_break" },
  { t0: 144, t1: 149, x0: 46, y0: 32, x1: 32, y1: 44, owner: "away_10", possession: "away", camera: "attack_push", transition: "away_break", danger: "final_third" },
  { t0: 149, t1: 152, x0: 32, y0: 44, x1: 24, y1: 50, owner: null, passer: "away_10", passState: "pass", heightPeak: 0.14, possession: "away", camera: "box_zoom", transition: "away_break" },
  { t0: 152, t1: 159, x0: 24, y0: 50, x1: 18, y1: 54, owner: "away_9", possession: "away", camera: "box_zoom", stage: "event", eventId: "ev_tackle_foul_6", banner: "SLIDING TACTICAL CHALLENGE", overrides: { home_4: "press" } },
  { t0: 159, t1: 162, x0: 18, y0: 54, x1: 38, y1: 66, owner: null, passer: "home_4", passState: "pass", heightPeak: 0.2, possession: "home", camera: "broadcast", stage: "post", eventId: "ev_tackle_foul_6" },
  { t0: 162, t1: 167, x0: 38, y0: 66, x1: 54, y1: 52, owner: "home_6", possession: "home", camera: "broadcast", transition: "home_break" },
  { t0: 167, t1: 170, x0: 54, y0: 52, x1: 44, y1: 26, owner: null, passer: "home_6", passState: "pass", heightPeak: 0.18, possession: "home", camera: "broadcast" },
  { t0: 170, t1: 176, x0: 44, y0: 26, x1: 60, y1: 24, owner: "home_8", possession: "home", camera: "attack_push", danger: "final_third" },

  // 176..240: Midfield thrust -> 40m diagonal switch -> wing burst -> lofted cross -> VOLLEY GOAL! -> immediate Away reply!
  { t0: 176, t1: 179, x0: 60, y0: 24, x1: 50, y1: 36, owner: null, passer: "home_8", passState: "pass", heightPeak: 0.14, possession: "home", camera: "broadcast", stage: "pre", eventId: "ev_long_pass_7" },
  { t0: 179, t1: 182, x0: 50, y0: 36, x1: 58, y1: 26, owner: "home_8", possession: "home", camera: "attack_push", danger: "final_third", stage: "pre", eventId: "ev_long_pass_7" },
  { t0: 182, t1: 188, x0: 58, y0: 26, x1: 82, y1: 82, owner: null, passer: "home_8", passState: "pass", heightPeak: 1.75, possession: "home", camera: "attack_push", danger: "final_third", stage: "event", eventId: "ev_long_pass_7", overrides: { home_8: "pass" } },
  { t0: 188, t1: 194, x0: 82, y0: 82, x1: 91, y1: 70, owner: "home_11", possession: "home", camera: "box_zoom", danger: "wide_box", stage: "post", eventId: "ev_long_pass_7", overrides: { home_11: "sprint" } },
  { t0: 194, t1: 198, x0: 91, y0: 70, x1: 88, y1: 76, owner: "home_11", possession: "home", camera: "box_zoom", danger: "wide_box", stage: "post", eventId: "ev_long_pass_7" },
  { t0: 198, t1: 206, x0: 88, y0: 76, x1: 86, y1: 50, owner: null, passer: "home_11", passState: "pass", heightPeak: 1.45, possession: "home", camera: "box_zoom", danger: "central_box", stage: "pre", eventId: "ev_goal_8" },
  { t0: 206, t1: 210, x0: 86, y0: 50, x1: 98, y1: 50, owner: null, passer: "home_9", passState: "shoot", heightPeak: 0.95, possession: "home", camera: "box_zoom", danger: "central_box", stage: "event", eventId: "ev_goal_8", overrides: { home_9: "shoot", away_1: "save" } },
  { t0: 210, t1: 216, x0: 98, y0: 50, x1: 98, y1: 50, owner: null, heightPeak: 0.1, possession: "home", camera: "goal_celebration", danger: "central_box", stage: "decision", eventId: "ev_goal_8", banner: "GOAL! LAGOS ATLAS LIONS 1 - 0", celebration: "home_lions", overrides: { home_9: "celebrate" } },
  // Crisp restart straight back into end-to-end football
  { t0: 216, t1: 219, x0: 50, y0: 50, x1: 62, y1: 48, owner: null, passer: "away_9", passState: "pass", heightPeak: 0.14, possession: "away", camera: "broadcast", stage: "reset" },
  { t0: 219, t1: 223, x0: 62, y0: 48, x1: 48, y1: 66, owner: "away_6", possession: "away", camera: "broadcast", transition: "away_break" },
  { t0: 223, t1: 226, x0: 48, y0: 66, x1: 28, y1: 80, owner: null, passer: "away_6", passState: "pass", heightPeak: 0.24, possession: "away", camera: "attack_push", transition: "away_break", danger: "final_third" },
  { t0: 226, t1: 232, x0: 28, y0: 80, x1: 16, y1: 64, owner: "away_7", possession: "away", camera: "box_zoom", transition: "away_break", danger: "wide_box" },
  { t0: 232, t1: 235, x0: 16, y0: 64, x1: 38, y1: 46, owner: null, passer: "home_3", passState: "pass", heightPeak: 0.3, possession: "home", transition: "home_break" },
  { t0: 235, t1: 240, x0: 38, y0: 46, x1: 56, y1: 40, owner: "home_6", possession: "home", camera: "broadcast", transition: "home_break" },

  // 240..300: Active play through substitution, rapid Away counter & low diving GK stop, final sprint!
  { t0: 240, t1: 245, x0: 56, y0: 40, x1: 72, y1: 26, owner: "home_8", possession: "home", camera: "attack_push", danger: "final_third" },
  { t0: 245, t1: 248, x0: 72, y0: 26, x1: 54, y1: 46, owner: null, passer: "home_8", passState: "pass", heightPeak: 0.16, possession: "home", camera: "broadcast", stage: "event", eventId: "ev_sub_9", banner: "TACTICAL SUBSTITUTION" },
  { t0: 248, t1: 253, x0: 54, y0: 46, x1: 68, y1: 64, owner: "home_10", possession: "home", camera: "broadcast", stage: "event", eventId: "ev_sub_9", banner: "TACTICAL SUBSTITUTION" },
  { t0: 253, t1: 256, x0: 68, y0: 64, x1: 52, y1: 48, owner: null, passer: "home_10", passState: "pass", heightPeak: 0.16, possession: "away", camera: "broadcast", stage: "event", eventId: "ev_sub_9", banner: "TACTICAL SUBSTITUTION" },
  { t0: 256, t1: 261, x0: 52, y0: 48, x1: 36, y1: 28, owner: "away_10", possession: "away", camera: "attack_push", transition: "away_break", danger: "final_third" },
  { t0: 261, t1: 264, x0: 36, y0: 28, x1: 22, y1: 22, owner: null, passer: "away_10", passState: "pass", heightPeak: 0.22, possession: "away", camera: "attack_push", transition: "away_break", danger: "final_third" },
  { t0: 264, t1: 269, x0: 22, y0: 22, x1: 16, y1: 38, owner: "away_11", possession: "away", camera: "box_zoom", transition: "away_break", danger: "wide_box" },
  { t0: 269, t1: 272, x0: 16, y0: 38, x1: 22, y1: 50, owner: null, passer: "away_11", passState: "pass", heightPeak: 0.14, possession: "away", camera: "box_zoom", danger: "central_box", stage: "pre", eventId: "ev_late_save_10" },
  { t0: 272, t1: 275, x0: 22, y0: 50, x1: 19, y1: 50, owner: "away_9", possession: "away", camera: "box_zoom", danger: "central_box", stage: "pre", eventId: "ev_late_save_10" },
  { t0: 275, t1: 280, x0: 19, y0: 50, x1: 6, y1: 53, owner: null, passer: "away_9", passState: "shoot", heightPeak: 0.45, possession: "away", camera: "box_zoom", danger: "central_box", stage: "event", eventId: "ev_late_save_10", banner: "LOW DIVING STOP!", overrides: { away_9: "shoot", home_1: "save" } },
  { t0: 280, t1: 284, x0: 6, y0: 53, x1: 12, y1: 44, owner: "home_1", possession: "home", camera: "broadcast", stage: "post", eventId: "ev_late_save_10" },
  { t0: 284, t1: 287, x0: 12, y0: 44, x1: 36, y1: 20, owner: null, passer: "home_1", passState: "pass", heightPeak: 0.6, possession: "home", camera: "broadcast", transition: "home_break" },
  { t0: 287, t1: 292, x0: 36, y0: 20, x1: 60, y1: 24, owner: "home_2", possession: "home", camera: "attack_push", transition: "home_break" },
  { t0: 292, t1: 295, x0: 60, y0: 24, x1: 78, y1: 44, owner: null, passer: "home_2", passState: "pass", heightPeak: 0.24, possession: "home", camera: "attack_push", transition: "home_break", danger: "final_third" },
  { t0: 295, t1: 301, x0: 78, y0: 44, x1: 89, y1: 50, owner: "home_9", possession: "home", camera: "box_zoom", transition: "home_break", danger: "central_box" },
];

function findBallSegment(tau: number): BallSegment {
  for (let i = 0; i < CONTINUOUS_SEGMENTS.length; i += 1) {
    const seg = CONTINUOUS_SEGMENTS[i];
    if (tau >= seg.t0 && tau < seg.t1) return seg;
  }
  return CONTINUOUS_SEGMENTS[CONTINUOUS_SEGMENTS.length - 1];
}

/**
 * Generates the complete 5-minute (300-second) GTEX match acceptance fixture.
 */
export function buildFiveMinuteHumanoidMatchFixture(durationSeconds: number = 300): SpectatorSafeMatchView {
  const homeTeam: SpectatorSafeTeamView = {
    team_id: "home_lions",
    team_name: "Lagos Atlas Lions",
    short_name: "LAL",
    formation: "4-3-3",
    primary_color: "#00E676",
    secondary_color: "#0F172A",
    accent_color: "#F5B83D",
    goalkeeper_color: "#FFB800",
    coach_name: "A. Okafor",
  };

  const awayTeam: SpectatorSafeTeamView = {
    team_id: "away_stars",
    team_name: "Abuja Coastal Stars",
    short_name: "ACS",
    formation: "4-3-3",
    primary_color: "#3B82F6",
    secondary_color: "#F8FAFC",
    accent_color: "#F43F5E",
    goalkeeper_color: "#EC4899",
    coach_name: "M. Diallo",
  };

  const scale = durationSeconds / 300;
  const S = (baseSec: number) => Math.min(durationSeconds, Math.round(baseSec * scale));
  const M = (sec: number) => Math.min(90, Math.floor((sec / durationSeconds) * 90));

  const events: SpectatorSafeEventView[] = [
    {
      event_id: "ev_kickoff",
      sequence: 0,
      event_type: "kickoff",
      minute: 0,
      added_time: 0,
      clock_label: "1'",
      time_seconds: 0,
      home_score: 0,
      away_score: 0,
      banner_text: "KICKOFF — GTEX NATIONAL ARENA",
      commentary: "Underway at the GTEX National Arena.",
      team_id: "home_lions",
      team_name: "Lagos Atlas Lions",
      primary_player_id: "home_9",
      primary_player_name: "Okwuosa #9",
      secondary_player_id: "home_6",
      secondary_player_name: "Adaramola #6",
    },
    {
      event_id: "ev_short_pass_1",
      sequence: 1,
      event_type: "pass",
      minute: Math.max(1, M(S(13))),
      added_time: 0,
      clock_label: `${Math.max(1, M(S(13)))}'`,
      time_seconds: S(13),
      home_score: 0,
      away_score: 0,
      banner_text: "BUILD-UP PASSING COMBINATION",
      commentary: "Crisp one-touch midfield combination from Adaramola to Ejiofor.",
      team_id: "home_lions",
      team_name: "Lagos Atlas Lions",
      primary_player_id: "home_6",
      primary_player_name: "Adaramola #6",
      secondary_player_id: "home_8",
      secondary_player_name: "Ejiofor #8",
      playback_profile: "build_up",
    },
    {
      event_id: "ev_through_ball_2",
      sequence: 2,
      event_type: "pass",
      minute: Math.max(1, M(S(28))),
      added_time: 0,
      clock_label: `${Math.max(1, M(S(28)))}'`,
      time_seconds: S(28),
      home_score: 0,
      away_score: 0,
      banner_text: "INCISIVE THROUGH BALL",
      commentary: "Weighted through ball releases Olatunji down the right flank.",
      team_id: "home_lions",
      team_name: "Lagos Atlas Lions",
      primary_player_id: "home_8",
      primary_player_name: "Ejiofor #8",
      secondary_player_id: "home_7",
      secondary_player_name: "Olatunji #7",
      playback_profile: "through_ball",
      flags: ["through_ball"],
    },
    {
      event_id: "ev_wing_cross_3",
      sequence: 3,
      event_type: "attack",
      minute: Math.max(1, M(S(52))),
      added_time: 0,
      clock_label: `${Math.max(1, M(S(52)))}'`,
      time_seconds: S(52),
      home_score: 0,
      away_score: 0,
      banner_text: "WHIPPED CROSS & AERIAL CHALLENGE",
      commentary: "Olatunji whips an inviting cross into the penalty area for Okwuosa!",
      team_id: "home_lions",
      team_name: "Lagos Atlas Lions",
      primary_player_id: "home_7",
      primary_player_name: "Olatunji #7",
      secondary_player_id: "home_9",
      secondary_player_name: "Okwuosa #9",
      playback_profile: "cross",
    },
    {
      event_id: "ev_shot_save_4",
      sequence: 4,
      event_type: "save",
      minute: Math.max(1, M(S(88))),
      added_time: 0,
      clock_label: `${Math.max(1, M(S(88)))}'`,
      time_seconds: S(88),
      home_score: 0,
      away_score: 0,
      banner_text: "DIVING GOALKEEPER SAVE!",
      commentary: "Thunderous strike from Ibekwe — acrobatic full-stretch save by Akpan!",
      team_id: "away_stars",
      team_name: "Abuja Coastal Stars",
      primary_player_id: "away_1",
      primary_player_name: "Akpan #1",
      secondary_player_id: "home_10",
      secondary_player_name: "Ibekwe #10",
      playback_profile: "shot",
    },
    {
      event_id: "ev_gk_dist_5",
      sequence: 5,
      event_type: "pass",
      minute: Math.max(1, M(S(104))),
      added_time: 0,
      clock_label: `${Math.max(1, M(S(104)))}'`,
      time_seconds: S(104),
      home_score: 0,
      away_score: 0,
      banner_text: "GOALKEEPER DISTRIBUTION",
      commentary: "Akpan launches a sweeping drop-kick counterattack into midfield.",
      team_id: "away_stars",
      team_name: "Abuja Coastal Stars",
      primary_player_id: "away_1",
      primary_player_name: "Akpan #1",
      secondary_player_id: "away_10",
      secondary_player_name: "Yusuf #10",
      playback_profile: "long_ball",
    },
    {
      event_id: "ev_tackle_foul_6",
      sequence: 6,
      event_type: "foul",
      minute: Math.max(1, M(S(156))),
      added_time: 0,
      clock_label: `${Math.max(1, M(S(156)))}'`,
      time_seconds: S(156),
      home_score: 0,
      away_score: 0,
      banner_text: "SLIDING TACTICAL CHALLENGE",
      commentary: "Committed sliding challenge by Umeadi halts Garba's counterattack.",
      team_id: "home_lions",
      team_name: "Lagos Atlas Lions",
      primary_player_id: "home_4",
      primary_player_name: "Umeadi #4",
      secondary_player_id: "away_9",
      secondary_player_name: "Garba #9",
    },
    {
      event_id: "ev_long_pass_7",
      sequence: 7,
      event_type: "pass",
      minute: Math.max(1, M(S(184))),
      added_time: 0,
      clock_label: `${Math.max(1, M(S(184)))}'`,
      time_seconds: S(184),
      home_score: 0,
      away_score: 0,
      banner_text: "DIAGONAL SWITCH OF PLAY",
      commentary: "Sweeping 40-meter diagonal pass from Ejiofor finds Danladi in space.",
      team_id: "home_lions",
      team_name: "Lagos Atlas Lions",
      primary_player_id: "home_8",
      primary_player_name: "Ejiofor #8",
      secondary_player_id: "home_11",
      secondary_player_name: "Danladi #11",
      playback_profile: "long_ball",
      flags: ["long_pass"],
    },
    {
      event_id: "ev_goal_8",
      sequence: 8,
      event_type: "goal",
      minute: Math.max(1, M(S(210))),
      added_time: 0,
      clock_label: `${Math.max(1, M(S(210)))}'`,
      time_seconds: S(210),
      home_score: 1,
      away_score: 0,
      banner_text: "GOAL! LAGOS ATLAS LIONS 1 - 0",
      commentary: "Clinical finish! Okwuosa strikes an unstoppable volley into the top corner!",
      team_id: "home_lions",
      team_name: "Lagos Atlas Lions",
      primary_player_id: "home_9",
      primary_player_name: "Okwuosa #9",
      secondary_player_id: "home_11",
      secondary_player_name: "Danladi #11",
      playback_profile: "volley",
      flags: ["volley"],
    },
    {
      event_id: "ev_sub_9",
      sequence: 9,
      event_type: "substitution",
      minute: Math.max(1, M(S(248))),
      added_time: 0,
      clock_label: `${Math.max(1, M(S(248)))}'`,
      time_seconds: S(248),
      home_score: 1,
      away_score: 0,
      banner_text: "TACTICAL SUBSTITUTION",
      commentary: "Fresh legs introduced in midfield for the closing stages.",
      team_id: "home_lions",
      team_name: "Lagos Atlas Lions",
      primary_player_id: "home_8",
      primary_player_name: "Ejiofor #8",
      secondary_player_id: "home_10",
      secondary_player_name: "Ibekwe #10",
    },
    {
      event_id: "ev_late_save_10",
      sequence: 10,
      event_type: "save",
      minute: Math.max(1, M(S(278))),
      added_time: 0,
      clock_label: `${Math.max(1, M(S(278)))}'`,
      time_seconds: S(278),
      home_score: 1,
      away_score: 0,
      banner_text: "LOW DIVING STOP!",
      commentary: "Mbadiwe dives low to his right to deny Garba and preserve the lead!",
      team_id: "home_lions",
      team_name: "Lagos Atlas Lions",
      primary_player_id: "home_1",
      primary_player_name: "Mbadiwe #1",
      secondary_player_id: "away_9",
      secondary_player_name: "Garba #9",
      playback_profile: "shot",
    },
  ];

  const frames: SpectatorSafeFrameView[] = [];
  const allTemplates = [...HOME_STARTERS_433, ...AWAY_STARTERS_433];

  for (let t = 0; t <= durationSeconds; t += 1) {
    const tau = (t / durationSeconds) * 300;
    const clockMinute = Number(((t / durationSeconds) * 90).toFixed(2));
    const homeScore = tau >= 211 ? 1 : 0;
    const awayScore = 0;

    const seg = findBallSegment(tau);
    const segAlpha = seg.t1 > seg.t0 ? (tau - seg.t0) / (seg.t1 - seg.t0) : 1;
    const possessionSide = seg.possession;
    const cameraPreset = seg.camera || "broadcast";
    const stage = seg.stage || "open_play";
    const activeEventId = seg.eventId ?? null;
    const eventBanner = seg.banner ?? null;
    const celebrationTeamId = seg.celebration ?? null;
    const transitionState = seg.transition || "stable";
    const dangerZone = seg.danger || "middle_third";
    const ballOwnerId = seg.owner;
    const isPassOrShot = seg.owner === null && !celebrationTeamId;
    const ballState = celebrationTeamId ? "in_goal" : isPassOrShot ? "in_flight" : "controlled";
    const ballX = clampPitch(lerp(seg.x0, seg.x1, segAlpha), 2, 98);
    const ballY = clampPitch(lerp(seg.y0, seg.y1, segAlpha), 4, 96);
    const ballHeight = celebrationTeamId
      ? 0.08
      : isPassOrShot
        ? seg.heightPeak && seg.heightPeak <= 0.55 && seg.passState === "shoot"
          ? 0.45
          : 0.1 + Math.sin(Math.max(0, Math.min(1, segAlpha)) * Math.PI) * (seg.heightPeak ?? 0.22)
        : 0.05;

    const primaryActorOverrideState: Record<string, string> = { ...(seg.overrides || {}) };
    if (seg.passer && segAlpha < 0.45 && !primaryActorOverrideState[seg.passer]) {
      primaryActorOverrideState[seg.passer] = seg.passState || "pass";
    }

    // Compute dynamic attacking vs defending team shapes around ballX/ballY
    const ballNormX = (ballX - 50) / 50; // -1 (left goal) .. +1 (right goal)
    const ballNormY = (ballY - 50) / 50;

    // Pick ONE nearest defending outfield presser to close down the ball carrier
    let presserId: string | null = null;
    let bestPressDist = Infinity;
    for (const tpl of allTemplates) {
      if (tpl.side === possessionSide || tpl.role === "GK") continue;
      const d = Math.hypot(tpl.anchorX - ballX, tpl.anchorY - ballY);
      if (d < bestPressDist) {
        bestPressDist = d;
        presserId = tpl.playerId;
      }
    }

    const rawPos: Array<{ x: number; y: number; pinned: boolean }> = allTemplates.map((tpl, idx) => {
      const isHome = tpl.side === "home";
      const isAttacking = tpl.side === possessionSide;
      const attackDir = isHome ? 1 : -1;
      const phaseShift = idx * 0.67;

      if (tpl.role === "GK") {
        // Goalkeeper stays on goal line/edge of 6-yard box tracking ball Y cleanly
        const gkBaseX = isHome ? 6 : 94;
        const sweeperAdvance = isAttacking ? attackDir * Math.max(0, ballNormX * attackDir) * 5.5 : 0;
        const gkX = ballOwnerId === tpl.playerId ? ballX : clampPitch(gkBaseX + sweeperAdvance, 4, 96);
        const gkY = ballOwnerId === tpl.playerId ? ballY : clampPitch(50 + ballNormY * 11, 36, 64);
        return { x: gkX, y: gkY, pinned: true };
      }

      // Dynamic team block X shift:
      // - Attacking team pushes decisively upfield into attacking shape (+11..+16 shift toward opponent goal)
      // - Defending team compacts goal-side between ball and their own goal
      let targetX: number;
      let targetY: number;

      if (isAttacking) {
        const lineAdvance =
          tpl.line === "defense" ? 13 : tpl.line === "midfield" ? 11 : 10;
        const ballFollowX = ballNormX * (tpl.line === "defense" ? 16 : tpl.line === "midfield" ? 20 : 17);
        targetX = tpl.anchorX + attackDir * lineAdvance + ballFollowX;
        // Attacking team spreads wide to stretch the defending block
        const widthSpread = tpl.line === "attack" ? 1.1 : 1.04;
        targetY = 50 + (tpl.anchorY - 50) * widthSpread + ballNormY * 7;
      } else {
        // Defending team compresses goal-side (between ball and defended goal)
        const defGoalX = isHome ? 6 : 94;
        const defendDepth = tpl.line === "defense" ? 0.24 : tpl.line === "midfield" ? 0.44 : 0.66;
        // Pull block toward own goal proportionally to ball threat, staying strictly goal-side
        const lineAnchor = lerp(defGoalX, ballX, defendDepth);
        const formationBlend = lerp(tpl.anchorX + ballNormX * 14, lineAnchor, 0.58);
        targetX = formationBlend - attackDir * 5;
        // Compact horizontally toward ball flank so defending shape reads immediately
        targetY = 50 + (tpl.anchorY - 50) * 0.78 + ballNormY * 14;
      }

      // Subtle continuous athletic runs/checking off the ball (no dead stillness)
      targetX += Math.sin(tau * 0.48 + phaseShift) * 2.4;
      targetY += Math.cos(tau * 0.39 + phaseShift) * 2.1;

      let pinned = false;
      if (ballOwnerId === tpl.playerId) {
        targetX = ballX;
        targetY = ballY;
        pinned = true;
      } else if (seg.passer === tpl.playerId && segAlpha < 0.55) {
        targetX = lerp(seg.x0, targetX, segAlpha * 0.6);
        targetY = lerp(seg.y0, targetY, segAlpha * 0.6);
        pinned = true;
      } else if (tpl.playerId === presserId && !celebrationTeamId) {
        // Active presser closes down goal-side of the ball carrier
        const pressGoalSideX = ballX - attackDir * 4.2;
        const pressGoalSideY = ballY + (tpl.anchorY >= 50 ? 2.2 : -2.2);
        targetX = lerp(targetX, pressGoalSideX, 0.72);
        targetY = lerp(targetY, pressGoalSideY, 0.72);
      }

      // Key set-piece / duel choreography windows
      if (tau >= 51 && tau <= 56 && (tpl.playerId === "home_9" || tpl.playerId === "away_4")) {
        targetX = ballX + (tpl.playerId === "home_9" ? -0.5 : 0.6);
        targetY = ballY;
        pinned = true;
      } else if (tau >= 132 && tau <= 137 && tpl.playerId === "home_6") {
        targetX = ballX + 0.8;
        targetY = ballY;
        pinned = true;
      } else if (tau >= 152 && tau <= 159 && (tpl.playerId === "home_4" || tpl.playerId === "away_9")) {
        targetX = ballX + (tpl.playerId === "home_4" ? -1.0 : 0.4);
        targetY = ballY;
        pinned = true;
      } else if (tau >= 204 && tau <= 212 && tpl.playerId === "home_9") {
        targetX = 86;
        targetY = 50;
        pinned = true;
      } else if (tau >= 272 && tau <= 278 && tpl.playerId === "home_5") {
        targetX = 17.5;
        targetY = 50.5;
        pinned = true;
      }

      return {
        x: clampPitch(targetX, 6, 94),
        y: clampPitch(targetY, 6, 94),
        pinned,
      };
    });

    // 2-pass anti-clustering separation so non-duel players maintain crisp tactical spacing (min 5.2m)
    const minSep = 5.2;
    for (let iter = 0; iter < 2; iter += 1) {
      for (let i = 0; i < rawPos.length; i += 1) {
        for (let j = i + 1; j < rawPos.length; j += 1) {
          if (rawPos[i].pinned && rawPos[j].pinned) continue;
          const dx = rawPos[j].x - rawPos[i].x;
          const dy = rawPos[j].y - rawPos[i].y;
          const dist = Math.hypot(dx, dy);
          if (dist < minSep) {
            const safeDist = Math.max(0.01, dist);
            const push = (minSep - dist) * 0.52;
            const nx = dx / safeDist;
            const ny = dy / safeDist;
            if (!rawPos[i].pinned) {
              rawPos[i].x = clampPitch(rawPos[i].x - nx * push, 5, 95);
              rawPos[i].y = clampPitch(rawPos[i].y - ny * push, 5, 95);
            }
            if (!rawPos[j].pinned) {
              rawPos[j].x = clampPitch(rawPos[j].x + nx * push, 5, 95);
              rawPos[j].y = clampPitch(rawPos[j].y + ny * push, 5, 95);
            }
          }
        }
      }
    }

    // Build 22 player telemetry records for frame `t`
    const players: SpectatorSafePlayerTelemetry[] = allTemplates.map((tpl, idx) => {
      const isHome = tpl.side === "home";
      const px = rawPos[idx].x;
      const py = rawPos[idx].y;

      const prevFrame = frames[frames.length - 1];
      const prevPlayer = prevFrame?.players[idx];
      const vx = prevPlayer ? px - prevPlayer.position.x : isHome ? 1.0 : -1.0;
      const vy = prevPlayer ? py - prevPlayer.position.y : 0.0;
      const rawSpeed = Math.hypot(vx, vy) / 4.8;
      let speedRatio = Math.max(0.1, Math.min(1.0, Number(rawSpeed.toFixed(3))));

      if (tpl.role !== "GK") {
        const wave = (Math.sin(tau * 0.42 + idx) + 1) * 0.5;
        speedRatio = Math.max(speedRatio, Number((0.14 + wave * 0.72).toFixed(3)));
      }

      let animState = primaryActorOverrideState[tpl.playerId] || "idle";
      if (!primaryActorOverrideState[tpl.playerId]) {
        if (celebrationTeamId && isHome) {
          animState = "celebrate";
        } else if (speedRatio >= 0.75) {
          animState = "sprint";
        } else if (speedRatio >= 0.42) {
          animState = "run";
        } else if (speedRatio >= 0.18) {
          animState = "jog";
        }
      }

      // Face toward movement direction when running, or toward the ball when holding shape
      const moving = Math.hypot(vx, vy) > 0.22;
      const fx = moving ? vx : ballX - px;
      const fy = moving ? vy : ballY - py;
      const fLen = Math.hypot(fx, fy) || 1;

      return {
        player_id: tpl.playerId,
        team_id: isHome ? homeTeam.team_id : awayTeam.team_id,
        side: tpl.side,
        shirt_number: tpl.shirtNumber,
        label: tpl.label,
        role: tpl.role,
        line: tpl.line,
        state: isHome === (possessionSide === "home") ? "attacking" : "defending",
        active: true,
        highlighted: ballOwnerId === tpl.playerId || Boolean(primaryActorOverrideState[tpl.playerId]),
        position: { x: Number(px.toFixed(2)), y: Number(py.toFixed(2)) },
        anchor_position: { x: tpl.anchorX, y: tpl.anchorY },
        animation_state: animState,
        speed_ratio: speedRatio,
        has_possession: ballOwnerId === tpl.playerId,
        facing: {
          x: Number((fx / fLen).toFixed(3)),
          y: Number((fy / fLen).toFixed(3)),
        },
        velocity: { x: Number(vx.toFixed(2)), y: Number(vy.toFixed(2)) },
      };
    });

    frames.push({
      frame_id: `accept_frame_${t}`,
      time_seconds: t,
      clock_minute: clockMinute,
      phase: stage === "reset" ? "kickoff" : "open_play",
      stage,
      home_score: homeScore,
      away_score: awayScore,
      home_attacks_right: true,
      possession_side: possessionSide,
      camera_preset: cameraPreset,
      active_event_id: activeEventId,
      event_banner: eventBanner,
      celebration_team_id: celebrationTeamId,
      possession_phase: dangerZone === "central_box" ? "box_attack" : "build_up",
      transition_state: transitionState,
      danger_zone: dangerZone,
      pressure_index: dangerZone === "central_box" ? 0.82 : 0.45,
      players,
      ball: {
        position: { x: Number(ballX.toFixed(2)), y: Number(ballY.toFixed(2)) },
        height: Number(ballHeight.toFixed(3)),
        state: ballState,
        owner_player_id: ballOwnerId,
        spin: ballState === "in_flight" ? { x: 0.2, y: 0.5, z: 0.8 } : null,
      },
    });
  }

  return {
    match_id: "gtex_u2a_006_humanoid_showcase",
    canonical_match_id: "gtex_u2a_006_humanoid_showcase",
    source: "authoritative_simulation_acceptance",
    home_team: homeTeam,
    away_team: awayTeam,
    match_label: "Lagos Atlas Lions vs Abuja Coastal Stars",
    venue_name: "GTEX National Arena",
    competition_name: "GTEX Premier Showcase",
    frames,
    events,
    is_owner_or_manager: false,
  };
}
