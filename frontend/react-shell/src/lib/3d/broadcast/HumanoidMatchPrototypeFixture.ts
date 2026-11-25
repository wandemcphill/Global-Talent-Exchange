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

/** Move the ball toward an aim point without skipping ahead of a real pass. */
function stepToward(
  fromX: number,
  fromY: number,
  toX: number,
  toY: number,
  maxStep: number,
): { x: number; y: number; left: number } {
  const dx = toX - fromX;
  const dy = toY - fromY;
  const dist = Math.hypot(dx, dy);
  if (dist <= maxStep || dist < 0.001) return { x: toX, y: toY, left: 0 };
  const scale = maxStep / dist;
  return { x: fromX + dx * scale, y: fromY + dy * scale, left: dist - maxStep };
}

/**
 * Continuous, high-tempo, zero-pause football timeline covering tau in [0, 300].
 * Passes zip 15-35m in 1-2s, carries surge dynamically at 5-9 m/s, and possession
 * flows end-to-end with frequent Home <-> Away transitions so attack vs defense
 * is unmistakable at every second.
 */
const CONTINUOUS_SEGMENTS: readonly BallSegment[] = [
  // 0..24: Snappy kickoff -> rapid one-touch passing progression -> Away interception & counter -> Home regains!
  { t0: 0, t1: 2, x0: 50, y0: 50, x1: 40, y1: 52, owner: null, passer: "home_9", passState: "pass", heightPeak: 0.14, possession: "home", stage: "reset", eventId: "ev_kickoff" },
  { t0: 2, t1: 4, x0: 40, y0: 52, x1: 32, y1: 76, owner: null, passer: "home_6", passState: "pass", heightPeak: 0.18, possession: "home", stage: "event", eventId: "ev_kickoff" },
  { t0: 4, t1: 7, x0: 32, y0: 76, x1: 48, y1: 82, owner: "home_3", possession: "home", stage: "pre", eventId: "ev_short_pass_1" },
  { t0: 7, t1: 9, x0: 48, y0: 82, x1: 60, y1: 66, owner: null, passer: "home_3", passState: "pass", heightPeak: 0.22, possession: "home", camera: "attack_push", danger: "final_third", stage: "pre", eventId: "ev_short_pass_1" },
  { t0: 9, t1: 12, x0: 60, y0: 66, x1: 72, y1: 74, owner: "home_10", possession: "home", camera: "attack_push", danger: "final_third", stage: "pre", eventId: "ev_short_pass_1" },
  { t0: 12, t1: 14, x0: 72, y0: 74, x1: 84, y1: 68, owner: null, passer: "home_10", passState: "pass", heightPeak: 0.22, possession: "home", camera: "attack_push", danger: "final_third", stage: "event", eventId: "ev_short_pass_1", overrides: { home_6: "pass" } },
  { t0: 14, t1: 16, x0: 64, y0: 42, x1: 50, y1: 54, owner: null, passer: "away_6", passState: "pass", heightPeak: 0.2, possession: "away", transition: "away_break", stage: "post", eventId: "ev_short_pass_1" },
  { t0: 16, t1: 20, x0: 50, y0: 54, x1: 12, y1: 80, owner: "away_7", possession: "away", camera: "attack_push", transition: "away_break", danger: "final_third" },
  { t0: 20, t1: 22, x0: 12, y0: 80, x1: 18, y1: 42, owner: null, passer: "away_7", passState: "pass", heightPeak: 1.8, possession: "away", camera: "box_zoom", danger: "wide_box" },
  { t0: 22, t1: 24, x0: 18, y0: 42, x1: 16, y1: 44, owner: "away_9", possession: "away", camera: "box_zoom", danger: "central_box" },
  { t0: 24, t1: 26, x0: 16, y0: 44, x1: 40, y1: 18, owner: "home_4", possession: "home", transition: "home_break" },

  // 26..48: Incisive through-ball -> blistering wing surge -> rapid switch & counter-press -> overlap to cross!
  { t0: 26, t1: 29, x0: 40, y0: 18, x1: 90, y1: 14, owner: null, passer: "home_8", passState: "pass", heightPeak: 0.7, possession: "home", camera: "attack_push", danger: "final_third", transition: "home_break", stage: "event", eventId: "ev_through_ball_2", overrides: { home_8: "pass" } },
  { t0: 29, t1: 33, x0: 84, y0: 18, x1: 92, y1: 29, owner: "home_7", possession: "home", camera: "box_zoom", danger: "wide_box", transition: "home_break", stage: "post", eventId: "ev_through_ball_2", overrides: { home_7: "sprint" } },
  { t0: 33, t1: 36, x0: 92, y0: 18, x1: 86, y1: 50, owner: null, passer: "home_7", passState: "pass", heightPeak: 1.7, possession: "home", camera: "box_zoom", danger: "wide_box", stage: "post", eventId: "ev_through_ball_2" },
  { t0: 36, t1: 38, x0: 86, y0: 50, x1: 88, y1: 49, owner: "home_9", possession: "home", camera: "box_zoom", danger: "central_box", stage: "post", eventId: "ev_through_ball_2" },
  { t0: 38, t1: 41, x0: 89, y0: 47, x1: 62, y1: 58, owner: null, passer: "away_5", passState: "pass", heightPeak: 1.25, possession: "away", transition: "away_break" },
  { t0: 41, t1: 43, x0: 62, y0: 58, x1: 48, y1: 64, owner: "away_10", possession: "away", camera: "attack_push", transition: "away_break" },
  { t0: 43, t1: 46, x0: 48, y0: 64, x1: 66, y1: 78, owner: "home_10", possession: "home", camera: "attack_push", transition: "home_break", danger: "final_third" },
  { t0: 46, t1: 48, x0: 66, y0: 78, x1: 82, y1: 84, owner: null, passer: "home_10", passState: "pass", heightPeak: 0.22, possession: "home", camera: "box_zoom", danger: "wide_box", stage: "pre", eventId: "ev_wing_cross_3" },
  { t0: 48, t1: 51, x0: 82, y0: 84, x1: 90, y1: 80, owner: "home_11", possession: "home", camera: "box_zoom", danger: "wide_box", stage: "pre", eventId: "ev_wing_cross_3", overrides: { home_11: "sprint" } },

  // 51..72: Whipped aerial cross -> header duel -> fast second-ball switch -> Away break -> Home counter!
  { t0: 51, t1: 56, x0: 90, y0: 80, x1: 84, y1: 50, owner: null, passer: "home_11", passState: "pass", heightPeak: 2.25, possession: "home", camera: "box_zoom", danger: "wide_box", stage: "event", eventId: "ev_wing_cross_3", overrides: { home_11: "pass" } },
  { t0: 56, t1: 58, x0: 86, y0: 50, x1: 84, y1: 50, owner: "home_9", possession: "home", camera: "box_zoom", danger: "central_box", stage: "post", eventId: "ev_wing_cross_3" },
  { t0: 58, t1: 62, x0: 75, y0: 78, x1: 90, y1: 68, owner: "home_11", possession: "home", camera: "attack_push", danger: "final_third", stage: "post", eventId: "ev_wing_cross_3" },
  { t0: 62, t1: 64, x0: 86, y0: 62, x1: 62, y1: 46, owner: null, passer: "away_4", passState: "pass", heightPeak: 1.25, possession: "away", transition: "away_break" },
  { t0: 64, t1: 68, x0: 62, y0: 46, x1: 40, y1: 30, owner: "away_8", possession: "away", camera: "attack_push", transition: "away_break" },
  { t0: 68, t1: 70, x0: 40, y0: 30, x1: 60, y1: 48, owner: null, passer: "home_6", passState: "pass", heightPeak: 1.25, possession: "home", transition: "home_break" },
  { t0: 70, t1: 73, x0: 60, y0: 48, x1: 74, y1: 62, owner: "home_10", possession: "home", camera: "attack_push", danger: "final_third" },

  // 73..100: Rapid one-two around the box -> #10 curling strike -> full-stretch high GK save -> quick sweep
  { t0: 73, t1: 75, x0: 74, y0: 62, x1: 84, y1: 76, owner: null, passer: "home_10", passState: "pass", heightPeak: 0.14, possession: "home", camera: "box_zoom", danger: "wide_box" },
  { t0: 75, t1: 79, x0: 84, y0: 76, x1: 88, y1: 60, owner: "home_11", possession: "home", camera: "box_zoom", danger: "central_box" },
  { t0: 79, t1: 81, x0: 88, y0: 60, x1: 72, y1: 46, owner: null, passer: "home_11", passState: "pass", heightPeak: 0.3, possession: "home", camera: "box_zoom", danger: "final_third", stage: "pre", eventId: "ev_shot_save_4" },
  { t0: 81, t1: 86, x0: 72, y0: 46, x1: 70, y1: 48, owner: "home_10", possession: "home", camera: "box_zoom", danger: "final_third", stage: "pre", eventId: "ev_shot_save_4", banner: "SHOT FROM OUTSIDE THE BOX!" },
  { t0: 86, t1: 91, x0: 70, y0: 48, x1: 93, y1: 50, owner: null, passer: "home_10", passState: "shoot", heightPeak: 1.25, possession: "home", camera: "box_zoom", danger: "final_third", stage: "event", eventId: "ev_shot_save_4", banner: "SHOT FROM OUTSIDE THE BOX!", overrides: { home_10: "shoot", away_1: "save" } },
  { t0: 91, t1: 95, x0: 95, y0: 49, x1: 90, y1: 52, owner: "away_1", possession: "away", camera: "broadcast", stage: "post", eventId: "ev_shot_save_4", overrides: { away_1: "save" } },
  { t0: 95, t1: 100, x0: 90, y0: 52, x1: 84, y1: 46, owner: "away_1", possession: "away", camera: "broadcast", stage: "post", eventId: "ev_shot_save_4" },

  // 100..115: Goalkeeper drop-kick distribution & rapid Away transition down the left flank
  { t0: 100, t1: 103, x0: 84, y0: 46, x1: 88, y1: 50, owner: "away_1", possession: "away", camera: "broadcast", stage: "pre", eventId: "ev_gk_dist_5" },
  { t0: 103, t1: 108, x0: 88, y0: 50, x1: 50, y1: 30, owner: null, passer: "away_1", passState: "pass", heightPeak: 2.4, possession: "away", camera: "broadcast", stage: "event", eventId: "ev_gk_dist_5", overrides: { away_1: "pass" } },
  { t0: 108, t1: 112, x0: 50, y0: 30, x1: 38, y1: 42, owner: "away_10", possession: "away", camera: "attack_push", transition: "away_break", stage: "post", eventId: "ev_gk_dist_5" },
  { t0: 112, t1: 115, x0: 38, y0: 42, x1: 24, y1: 78, owner: null, passer: "away_10", passState: "pass", heightPeak: 0.24, possession: "away", camera: "attack_push", transition: "away_break", danger: "final_third", stage: "post", eventId: "ev_gk_dist_5" },

  // 115..175: Relentless end-to-end transitions, wing raids, interception, sliding tackle & rapid breaks
  { t0: 115, t1: 119, x0: 42, y0: 74, x1: 22, y1: 76, owner: "away_7", possession: "away", camera: "attack_push", transition: "away_break", danger: "final_third" },
  { t0: 119, t1: 122, x0: 36, y0: 70, x1: 16, y1: 50, owner: null, passer: "away_7", passState: "pass", heightPeak: 0.4, possession: "away", camera: "box_zoom", transition: "away_break", danger: "final_third", banner: "OFFSIDE" },
  { t0: 122, t1: 125, x0: 28, y0: 52, x1: 46, y1: 48, owner: null, passer: "home_5", passState: "pass", heightPeak: 0.3, possession: "home", transition: "home_break" },
  { t0: 125, t1: 129, x0: 52, y0: 38, x1: 78, y1: 22, owner: "home_7", possession: "home", camera: "attack_push", transition: "home_break", danger: "final_third" },
  { t0: 129, t1: 132, x0: 78, y0: 22, x1: 82, y1: 46, owner: null, passer: "home_7", passState: "pass", heightPeak: 0.32, possession: "home", camera: "box_zoom", danger: "central_box" },
  { t0: 132, t1: 135, x0: 82, y0: 46, x1: 84, y1: 50, owner: "home_10", possession: "home", camera: "box_zoom", danger: "central_box" },
  { t0: 135, t1: 137, x0: 80, y0: 48, x1: 52, y1: 46, owner: null, passer: "away_5", passState: "pass", heightPeak: 1.3, possession: "away", camera: "broadcast", transition: "away_break" },
  { t0: 137, t1: 141, x0: 42, y0: 52, x1: 62, y1: 60, owner: "home_6", possession: "home", camera: "attack_push", transition: "home_break" },
  { t0: 141, t1: 144, x0: 62, y0: 60, x1: 40, y1: 28, owner: null, passer: "away_6", passState: "pass", heightPeak: 1.2, possession: "away", transition: "away_break" },
  { t0: 144, t1: 149, x0: 46, y0: 32, x1: 22, y1: 34, owner: "away_10", possession: "away", camera: "attack_push", transition: "away_break", danger: "final_third" },
  { t0: 149, t1: 152, x0: 32, y0: 44, x1: 24, y1: 50, owner: null, passer: "away_10", passState: "pass", heightPeak: 0.14, possession: "away", camera: "box_zoom", transition: "away_break" },
  { t0: 152, t1: 159, x0: 24, y0: 50, x1: 18, y1: 54, owner: "away_9", possession: "away", camera: "box_zoom", stage: "event", eventId: "ev_tackle_foul_6", banner: "TACKLE!", overrides: { home_4: "press" } },
  { t0: 159, t1: 162, x0: 18, y0: 54, x1: 38, y1: 66, owner: null, passer: "home_4", passState: "pass", heightPeak: 0.2, possession: "home", camera: "broadcast", stage: "post", eventId: "ev_tackle_foul_6" },
  { t0: 162, t1: 167, x0: 38, y0: 66, x1: 54, y1: 52, owner: "home_6", possession: "home", camera: "broadcast", transition: "home_break" },
  { t0: 167, t1: 170, x0: 58, y0: 46, x1: 74, y1: 50, owner: null, passer: "home_8", passState: "pass", heightPeak: 0.35, possession: "home", camera: "attack_push", danger: "final_third", banner: "OFFSIDE" },
  { t0: 170, t1: 173, x0: 72, y0: 50, x1: 54, y1: 42, owner: null, passer: "away_4", passState: "pass", heightPeak: 1.3, possession: "away", camera: "broadcast" },
  { t0: 173, t1: 176, x0: 52, y0: 40, x1: 58, y1: 44, owner: "home_8", possession: "home", camera: "attack_push" },

  // 176..240: Midfield thrust -> 40m diagonal switch -> wing burst -> lofted cross -> VOLLEY GOAL! -> immediate Away reply!
  { t0: 176, t1: 182, x0: 58, y0: 44, x1: 74, y1: 28, owner: "home_8", possession: "home", camera: "attack_push", danger: "final_third", stage: "pre", eventId: "ev_long_pass_7" },
  { t0: 182, t1: 188, x0: 56, y0: 36, x1: 82, y1: 82, owner: null, passer: "home_8", passState: "pass", heightPeak: 1.75, possession: "home", camera: "attack_push", danger: "final_third", stage: "event", eventId: "ev_long_pass_7", overrides: { home_8: "pass" } },
  { t0: 188, t1: 194, x0: 82, y0: 82, x1: 93, y1: 64, owner: "home_11", possession: "home", camera: "box_zoom", danger: "wide_box", stage: "post", eventId: "ev_long_pass_7", overrides: { home_11: "sprint" } },
  { t0: 194, t1: 198, x0: 93, y0: 64, x1: 94, y1: 72, owner: "home_11", possession: "home", camera: "box_zoom", danger: "wide_box", stage: "post", eventId: "ev_long_pass_7" },
  { t0: 198, t1: 202, x0: 94, y0: 72, x1: 86, y1: 50, owner: null, passer: "home_11", passState: "pass", heightPeak: 1.45, possession: "home", camera: "box_zoom", danger: "central_box", stage: "pre", eventId: "ev_goal_8" },
  { t0: 202, t1: 206, x0: 84, y0: 44, x1: 84, y1: 44, owner: "home_9", possession: "home", camera: "box_zoom", danger: "central_box", stage: "pre", eventId: "ev_goal_8" },
  { t0: 206, t1: 210, x0: 86, y0: 50, x1: 98, y1: 50, owner: null, passer: "home_9", passState: "shoot", heightPeak: 0.95, possession: "home", camera: "box_zoom", danger: "central_box", stage: "event", eventId: "ev_goal_8", overrides: { home_9: "shoot" } },
  { t0: 210, t1: 216, x0: 98, y0: 50, x1: 98, y1: 50, owner: null, heightPeak: 0.1, possession: "home", camera: "goal_celebration", danger: "central_box", stage: "decision", eventId: "ev_goal_8", banner: "GOAL! LAGOS ATLAS LIONS 1 - 0", celebration: "home_lions", overrides: { home_9: "celebrate" } },
  // Crisp restart straight back into end-to-end football
  { t0: 216, t1: 220, x0: 50, y0: 50, x1: 50, y1: 50, owner: "away_9", passer: "away_9", possession: "away", camera: "broadcast", stage: "reset", banner: "KICKOFF" },
  { t0: 220, t1: 222, x0: 50, y0: 50, x1: 58, y1: 48, owner: null, passer: "away_9", passState: "pass", heightPeak: 0.14, possession: "away", camera: "broadcast", banner: "KICKOFF" },
  { t0: 222, t1: 223, x0: 58, y0: 48, x1: 50, y1: 46, owner: "away_6", possession: "away", camera: "attack_push", transition: "away_break" },
  { t0: 223, t1: 226, x0: 50, y0: 46, x1: 16, y1: 14, owner: null, passer: "away_6", passState: "pass", heightPeak: 1.15, possession: "away", camera: "attack_push", transition: "away_break", danger: "final_third" },
  { t0: 226, t1: 228, x0: 16, y0: 14, x1: 12, y1: 26, owner: "away_11", possession: "away", camera: "box_zoom", transition: "away_break", danger: "wide_box" },
  { t0: 228, t1: 230, x0: 12, y0: 26, x1: 4, y1: 32, owner: null, passer: "away_11", passState: "shoot", heightPeak: 0.5, possession: "away", camera: "box_zoom", danger: "wide_box" },
  { t0: 230, t1: 234, x0: 4, y0: 32, x1: 5, y1: 34, owner: "home_1", possession: "home", camera: "broadcast", transition: "home_break" },
  { t0: 234, t1: 240, x0: 20, y0: 40, x1: 48, y1: 42, owner: "home_6", possession: "home", camera: "broadcast", transition: "home_break" },

  // 240..300: Active play through substitution, rapid Away counter & low diving GK stop, final sprint!
  { t0: 240, t1: 245, x0: 56, y0: 40, x1: 70, y1: 58, owner: "home_8", possession: "home", camera: "attack_push", danger: "final_third" },
  { t0: 245, t1: 251, x0: 70, y0: 58, x1: 70, y1: 14, owner: "home_8", possession: "home", camera: "broadcast", stage: "event", eventId: "ev_sub_9", banner: "TACTICAL SUBSTITUTION" },
  { t0: 251, t1: 256, x0: 70, y0: 14, x1: 58, y1: 36, owner: null, passer: "home_6", passState: "pass", heightPeak: 0.25, possession: "home", camera: "broadcast", stage: "event", eventId: "ev_sub_9", banner: "TACTICAL SUBSTITUTION" },
  { t0: 256, t1: 261, x0: 58, y0: 36, x1: 36, y1: 28, owner: "away_10", possession: "away", camera: "attack_push", transition: "away_break", danger: "final_third" },
  { t0: 261, t1: 266, x0: 36, y0: 28, x1: 28, y1: 48, owner: null, passer: "away_10", passState: "pass", heightPeak: 1.15, possession: "away", camera: "attack_push", transition: "away_break", danger: "final_third" },
  { t0: 266, t1: 272, x0: 28, y0: 48, x1: 18, y1: 38, owner: "away_9", possession: "away", camera: "box_zoom", danger: "central_box", stage: "pre", eventId: "ev_late_save_10" },
  { t0: 272, t1: 275, x0: 18, y0: 38, x1: 16, y1: 46, owner: "away_9", possession: "away", camera: "box_zoom", danger: "central_box", stage: "pre", eventId: "ev_late_save_10" },
  { t0: 275, t1: 280, x0: 19, y0: 50, x1: 6, y1: 53, owner: null, passer: "away_9", passState: "shoot", heightPeak: 0.45, possession: "away", camera: "box_zoom", danger: "central_box", stage: "event", eventId: "ev_late_save_10", banner: "LOW DIVING STOP!", overrides: { away_9: "shoot", home_1: "save" } },
  { t0: 280, t1: 284, x0: 6, y0: 53, x1: 12, y1: 44, owner: "home_1", possession: "home", camera: "broadcast", stage: "post", eventId: "ev_late_save_10" },
  { t0: 284, t1: 287, x0: 12, y0: 44, x1: 36, y1: 20, owner: null, passer: "home_1", passState: "pass", heightPeak: 0.6, possession: "home", camera: "broadcast", transition: "home_break" },
  { t0: 287, t1: 292, x0: 36, y0: 20, x1: 60, y1: 24, owner: "home_2", possession: "home", camera: "attack_push", transition: "home_break" },
  { t0: 292, t1: 295, x0: 60, y0: 24, x1: 82, y1: 48, owner: null, passer: "home_2", passState: "pass", heightPeak: 0.24, possession: "home", camera: "attack_push", transition: "home_break", danger: "final_third" },
  { t0: 295, t1: 301, x0: 82, y0: 48, x1: 78, y1: 32, owner: "home_9", possession: "home", camera: "box_zoom", transition: "home_break", danger: "central_box" },
];

function findBallSegment(tau: number): BallSegment {
  for (let i = 0; i < CONTINUOUS_SEGMENTS.length; i += 1) {
    const seg = CONTINUOUS_SEGMENTS[i];
    if (tau >= seg.t0 && tau < seg.t1) return seg;
  }
  return CONTINUOUS_SEGMENTS[CONTINUOUS_SEGMENTS.length - 1];
}

function segmentBefore(seg: BallSegment): BallSegment | null {
  let prev: BallSegment | null = null;
  for (let i = 0; i < CONTINUOUS_SEGMENTS.length; i += 1) {
    const item = CONTINUOUS_SEGMENTS[i];
    if (item.t0 >= seg.t0 - 0.01) break;
    prev = item;
  }
  return prev;
}

function attackingZone(seg: BallSegment): boolean {
  return seg.danger === "final_third" || seg.danger === "wide_box" || seg.danger === "central_box" ||
    (seg.possession === "home" ? seg.x0 >= 68 : seg.x0 <= 32);
}

type OffsideWindow = {
  t0: number;
  t1: number;
  attack: "home" | "away";
  attackerId: string;
  defenderId: string;
  lineX: number;
  attackerX: number;
};

/** Two traps in the match. The line steps up and one runner is left behind it. */
const OFFSIDE_WINDOWS: readonly OffsideWindow[] = [
  { t0: 119, t1: 122, attack: "away", attackerId: "away_9", defenderId: "home_5", lineX: 28, attackerX: 14 },
  { t0: 167, t1: 171, attack: "home", attackerId: "home_9", defenderId: "away_4", lineX: 72, attackerX: 88 },
];

function offsideWindow(tau: number): OffsideWindow | null {
  return OFFSIDE_WINDOWS.find((item) => tau >= item.t0 && tau < item.t1 - 0.05) ?? null;
}

function boxAttack(seg: BallSegment | null): { side: "home" | "away"; spotX: number } | null {
  if (!seg || seg.passState === "shoot" || seg.celebration) return null;
  if (seg.passer?.endsWith("_1")) return null;
  const inBox = seg.danger === "wide_box" || seg.danger === "central_box";
  if (!inBox) return null;
  const wingerCarryingWide = Boolean(seg.owner) && seg.danger === "wide_box" && !seg.owner.endsWith("_9");
  if (wingerCarryingWide) return null;
  return { side: seg.possession, spotX: seg.possession === "home" ? 86 : 14 };
}

function centreForward(side: "home" | "away"): string {
  return side === "home" ? "home_9" : "away_9";
}

function segmentAfter(seg: BallSegment): BallSegment | null {
  for (let i = 0; i < CONTINUOUS_SEGMENTS.length; i += 1) {
    if (CONTINUOUS_SEGMENTS[i].t0 >= seg.t1 - 0.01) return CONTINUOUS_SEGMENTS[i];
  }
  return null;
}

/** Who the ball is travelling to. A pass continues to the next touch, including a turnover. */
function upcomingReceiver(seg: BallSegment): string | null {
  if (seg.celebration) return null;
  if (seg.owner) return seg.owner;
  if (seg.passState === "shoot") return null;
  if ((seg.heightPeak ?? 0) > 1.2 && (seg.danger === "wide_box" || seg.danger === "central_box")) {
    return centreForward(seg.possession);
  }

  const trap = OFFSIDE_WINDOWS.find((item) => item.attack === seg.possession && seg.t1 > item.t0 && seg.t0 < item.t1);
  if (trap) return trap.attackerId;

  const next = segmentAfter(seg);
  if (next?.possession === seg.possession) {
    if (next.owner && next.owner !== seg.passer) return next.owner;
    if (next.passer && next.passer !== seg.passer) return next.passer;
  } else if (next) {
    if (next.owner) return next.owner;
    if (next.passer) return next.passer;
  }

  const boxDelivery = seg.danger === "wide_box" || seg.danger === "central_box" ||
    (seg.possession === "home" ? seg.x0 >= 78 : seg.x0 <= 22);
  if (boxDelivery) return centreForward(seg.possession);

  const options = seg.possession === "home" ? ["home_8", "home_10", "home_6"] : ["away_8", "away_10", "away_6"];
  return options.find((id) => id !== seg.passer) || options[0];
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
      commentary: "Danladi whips an inviting cross in from the left for Okwuosa!",
      team_id: "home_lions",
      team_name: "Lagos Atlas Lions",
      primary_player_id: "home_11",
      primary_player_name: "Danladi #11",
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
      banner_text: "SHOT FROM OUTSIDE THE BOX!",
      commentary: "Ibekwe lets fly from outside the box and Akpan saves at full stretch!",
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
      banner_text: "TACKLE!",
      commentary: "Umeadi steps across Garba and tackles him as the run is closed down.",
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
  const metresRun = new Array(allTemplates.length).fill(0);

  for (let t = 0; t <= durationSeconds; t += 1) {
    const tau = (t / durationSeconds) * 300;
    const clockMinute = Number(((t / durationSeconds) * 90).toFixed(2));
    const homeScore = tau >= 206 ? 1 : 0;
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
    const prevLive = frames[frames.length - 1]?.ball.position;
    const liveX = prevLive?.x ?? seg.x0;
    const liveY = prevLive?.y ?? seg.y0;
    let ballState: "in_goal" | "in_flight" | "controlled" = celebrationTeamId ? "in_goal" : "controlled";
    let ballX = liveX;
    let ballY = liveY;
    let ballHeight = 0.05;

    const receiverId = upcomingReceiver(seg);
    const carrierTpl = allTemplates.find((tpl) => tpl.playerId === (ballOwnerId || seg.passer)) || null;
    const prevSeg = segmentBefore(seg);
    const prevWasAttack = Boolean(prevSeg && prevSeg.possession !== seg.possession && attackingZone(prevSeg));
    const offside = offsideWindow(tau);
    const carriedBox = prevSeg && tau < prevSeg.t1 + 0.8 ? boxAttack(prevSeg) : null;
    const box = offside || seg.passState === "shoot"
      ? null
      : boxAttack(seg) || (carriedBox && carriedBox.side === possessionSide ? carriedBox : null);
    const shapeX = liveX;
    const intentXFrame = shapeX;
    const ballLane = liveY;
    const wideChase = Math.abs(liveY - 50) > 16 && (possessionSide === "home" ? liveX > 62 : liveX < 38);
    const defLineX = offside
      ? offside.lineX
      : box
        ? box.side === "home" ? box.spotX + 4 : box.spotX - 4
        : possessionSide === "home"
          ? wideChase ? 92 : clampPitch(Math.max(liveX + 9, 58), 36, 91)
          : wideChase ? 8 : clampPitch(Math.min(liveX - 9, 42), 9, 64);
    const wideFinal =
      !celebrationTeamId &&
      !offside &&
      (possessionSide === "home" ? liveX > 66 : liveX < 34) &&
      Math.abs(liveY - 50) > 14;
    const farWingerId = !wideFinal
      ? null
      : possessionSide === "home"
        ? liveY < 50 ? "home_11" : "home_7"
        : liveY < 50 ? "away_7" : "away_11";
    const boxStrikerId = wideFinal ? centreForward(possessionSide) : null;
    const deepBox =
      !celebrationTeamId &&
      !offside &&
      (possessionSide === "home" ? liveX > 76 : liveX < 24) &&
      (wideFinal || seg.danger === "wide_box" || seg.danger === "central_box" || Boolean(box));

    // In the final third a centre-back steps off the line. Otherwise the nearest midfielder presses.
    let presserId: string | null = null;
    if (carrierTpl && !celebrationTeamId && !offside && seg.passState !== "shoot") {
      let bestPressDist = Infinity;
      const wantDefender = Boolean(box) || attackingZone(seg);
      const wideBall = Math.abs(ballLane - 50) > 16;
      for (const tpl of allTemplates) {
        if (tpl.side === carrierTpl.side || tpl.role === "GK") continue;
        if (wantDefender && tpl.line !== "defense") continue;
        if (wantDefender && wideBall && Math.abs(tpl.anchorY - 50) < 18) continue;
        const d = Math.abs(tpl.anchorY - ballLane) + Math.abs(tpl.anchorX - intentXFrame) * 0.15;
        if (d < bestPressDist) {
          bestPressDist = d;
          presserId = tpl.playerId;
        }
      }
    }

    // The nearest teammate behind the ball shows for the short pass.
    let offerId: string | null = null;
    if (ballOwnerId && !celebrationTeamId && !offside && !box && !wideFinal) {
      let bestOffer = Infinity;
      for (const tpl of allTemplates) {
        if (tpl.side !== possessionSide || tpl.role === "GK" || tpl.line === "attack" || tpl.playerId === ballOwnerId) continue;
        const d = Math.hypot(tpl.anchorX - liveX, tpl.anchorY - liveY);
        if (d < bestOffer) {
          bestOffer = d;
          offerId = tpl.playerId;
        }
      }
    }

    // The far attacker runs ahead of the ball. A second opponent covers that run.
    let runnerId: string | null = null;
    if (ballOwnerId && !celebrationTeamId && !offside && !box && !deepBox) {
      let bestLane = Infinity;
      for (const tpl of allTemplates) {
        if (tpl.side !== possessionSide || tpl.line !== "attack" || tpl.playerId === ballOwnerId) continue;
        const lane = Math.abs(tpl.anchorY - liveY);
        if (lane < bestLane) {
          bestLane = lane;
          runnerId = tpl.playerId;
        }
      }
    }
    let coverId: string | null = null;
    const markedRunner = runnerId ? allTemplates.find((tpl) => tpl.playerId === runnerId) : null;
    if (markedRunner && !celebrationTeamId && !offside && !box) {
      let bestCover = Infinity;
      for (const tpl of allTemplates) {
        if (tpl.side === markedRunner.side || tpl.role === "GK" || tpl.line !== "defense" || tpl.playerId === presserId) continue;
        const d = Math.abs(tpl.anchorY - markedRunner.anchorY);
        if (d < bestCover) {
          bestCover = d;
          coverId = tpl.playerId;
        }
      }
    }

    const rawPos: Array<{ x: number; y: number; pinned: boolean }> = allTemplates.map((tpl, idx) => {
      const kickoffShape = seg.stage === "reset" || (tau >= 220 && tau < 222 && tpl.playerId !== "away_6");
      if (kickoffShape) {
        if (tpl.playerId === "away_9" || tpl.playerId === seg.passer || tpl.playerId === seg.owner) {
          return { x: seg.x0, y: seg.y0, pinned: true };
        }
        const sideSign = tpl.side === "home" ? -1 : 1;
        const depth = tpl.role === "GK" ? 42 : tpl.line === "defense" ? 30 : tpl.line === "midfield" ? 20 : 16;
        return {
          x: clampPitch(50 + sideSign * depth, 6, 94),
          y: clampPitch(tpl.anchorY, 14, 86),
          pinned: true,
        };
      }
      const isHome = tpl.side === "home";
      const isAttacking = tpl.side === possessionSide;
      const attackDir = isHome ? 1 : -1;
      const phaseShift = idx * 0.67;
      const intentX = lerp(seg.x0, seg.x1, 0.35);
      const intentNormX = (intentX - 50) / 50;

      if (tpl.role === "GK") {
        if (tpl.playerId === ballOwnerId) {
          const aimX = clampPitch(seg.x1, isHome ? 4 : 74, isHome ? 26 : 96);
          const aimY = clampPitch(seg.y1, 34, 66);
          return { x: aimX, y: aimY, pinned: true };
        }
        if (seg.eventId === "ev_goal_8" && tpl.side !== possessionSide) {
          return { x: isHome ? 10 : 90, y: 62, pinned: true };
        }
        const facingSave = seg.passState === "shoot"
          && tpl.side !== possessionSide
          && (seg.eventId === "ev_shot_save_4" || seg.eventId === "ev_late_save_10");
        if (facingSave) {
          return { x: isHome ? 7.2 : 92.8, y: 50, pinned: true };
        }
        if (!isAttacking && box) {
          const centralCross = Math.abs(ballLane - 50) < 16;
          const gkClaimX = isHome ? (centralCross ? 8 : 6) : centralCross ? 92 : 94;
          const gkClaimY = centralCross ? (ballLane >= 50 ? 58 : 42) : 50;
          return { x: gkClaimX, y: gkClaimY, pinned: true };
        }
        const gkBaseX = isHome ? 6 : 94;
        const highLine = !isAttacking && (isHome ? defLineX > 40 : defLineX < 60);
        const gkX = highLine
          ? (isHome ? clampPitch(Math.min(defLineX - 16, 16), 5, 16) : clampPitch(Math.max(defLineX + 16, 84), 84, 95))
          : clampPitch(gkBaseX + (isAttacking ? attackDir * Math.max(0, intentNormX * attackDir) * 4 : 0), 4, 96);
        const gkY = clampPitch(tpl.anchorY + (ballLane - tpl.anchorY) * (box || seg.passState === "shoot" ? 0.55 : 0.12), 36, 64);
        return { x: gkX, y: gkY, pinned: true };
      }

      let targetX: number;
      let targetY: number;

      if (isAttacking) {
        if (tpl.line === "defense") {
          targetX = isHome
            ? clampPitch(Math.max(tpl.anchorX, intentXFrame - 26), 18, 64)
            : clampPitch(Math.min(tpl.anchorX, intentXFrame + 26), 36, 82);
          targetY = 50 + (tpl.anchorY - 50) * 1.06;
          const carrierWide = carrierTpl && Math.abs(carrierTpl.anchorY - 50) > 18;
          const sameWing = carrierWide && Math.sign(carrierTpl.anchorY - 50) === Math.sign(tpl.anchorY - 50);
          const farWing = carrierWide && Math.sign(carrierTpl.anchorY - 50) !== Math.sign(tpl.anchorY - 50);
          if (Math.abs(tpl.anchorY - 50) > 20 && sameWing && attackingZone(seg)) {
            targetX = isHome ? clampPitch(intentXFrame - 12, 52, 80) : clampPitch(intentXFrame + 12, 20, 48);
          } else if (Math.abs(tpl.anchorY - 50) > 20 && farWing) {
            targetX = isHome ? clampPitch(intentXFrame - 32, 20, 56) : clampPitch(intentXFrame + 32, 44, 80);
            targetY = lerp(tpl.anchorY, 50 + (tpl.anchorY - 50) * 0.7, 0.35);
          }
        } else if (tpl.line === "midfield") {
          const central = Math.abs(tpl.anchorY - 50) < 16;
          const sameSide = (tpl.anchorY - 50) * (ballLane - 50) > 40;
          const drop = central ? 20 : sameSide ? 8 : 16;
          targetX = isHome
            ? clampPitch(intentXFrame - drop, 32, 80)
            : clampPitch(intentXFrame + drop, 20, 68);
          targetY = central ? tpl.anchorY : tpl.anchorY + (ballLane - tpl.anchorY) * (sameSide ? 0.16 : 0.04);
        } else {
          targetX = tpl.anchorX + attackDir * 4 + intentNormX * 4;
          targetY = 50 + (tpl.anchorY - 50) * 1.12;
          if (intentNormX * attackDir > 0.28) {
            targetX += attackDir * 8;
            targetY = tpl.anchorY + (seg.y1 - tpl.anchorY) * 0.1;
          }
        }
      } else if (tpl.line === "defense") {
        targetX = defLineX;
        targetY = 50 + (tpl.anchorY - 50) * 0.88 + (ballLane - 50) * 0.2;
        const ballSideCentreBack = Math.abs(tpl.anchorY - 50) < 18 && Math.abs(tpl.anchorY - ballLane) < 20;
        const farFullback = Math.abs(tpl.anchorY - 50) > 20 && (tpl.anchorY - 50) * (ballLane - 50) < 0;
        if (ballSideCentreBack && !box && Math.abs(ballLane - 50) < 10) {
          targetX = isHome ? defLineX + 4 : defLineX - 4;
          targetY = lerp(targetY, ballLane, 0.35);
        } else if (farFullback) {
          targetY = lerp(targetY, 50, 0.28);
        }
      } else if (tpl.line === "midfield") {
        if (box && tpl.side !== box.side) {
          targetX = box.side === "home" ? 74 : 26;
          targetY = tpl.anchorY;
        } else {
          const central = Math.abs(tpl.anchorY - 50) < 16;
          const nearest = Math.abs(tpl.anchorY - ballLane) < 16;
          const screen = nearest ? 12 : central ? 5 : 8;
          targetX = isHome
            ? Math.max(defLineX + 3, Math.min(defLineX + screen, intentXFrame - 4))
            : Math.min(defLineX - 3, Math.max(defLineX - screen, intentXFrame + 4));
          targetY = 50 + (tpl.anchorY - 50) * (nearest ? 0.82 : 0.94);
        }
      } else {
        targetX = isHome
          ? clampPitch(Math.max(defLineX + 18, 50), 30, 78)
          : clampPitch(Math.min(defLineX - 18, 50), 22, 70);
        targetY = 50 + (tpl.anchorY - 50) * 0.92;
      }

      const inOwnHalf = isHome ? liveX < 58 : liveX > 42;
      if (isAttacking && tpl.line === "defense" && Math.abs(tpl.anchorY - 50) < 18 && tpl.playerId !== ballOwnerId) {
        targetX = isHome ? Math.min(targetX, liveX - 14) : Math.max(targetX, liveX + 14);
      }
      if (isAttacking && inOwnHalf && tpl.line === "attack" && tpl.playerId !== ballOwnerId && tpl.playerId !== receiverId) {
        targetX = isHome ? clampPitch(liveX + 18, 34, 60) : clampPitch(liveX - 18, 40, 66);
      }
      if (isAttacking && inOwnHalf && tpl.playerId.endsWith("_6") && tpl.playerId !== ballOwnerId) {
        targetX = isHome ? clampPitch(liveX - 8, 18, 48) : clampPitch(liveX + 8, 52, 82);
        targetY = 50;
      }

      const recovering = !isAttacking && prevSeg && prevSeg.possession === tpl.side && !offside && !box;
      if (recovering) {
        const behind = tpl.line === "defense" ? 24 : tpl.line === "midfield" ? 12 : 3;
        const oldX = isHome ? prevSeg.x1 - behind : prevSeg.x1 + behind;
        targetX = lerp(clampPitch(oldX, 10, 90), targetX, Math.min(1, segAlpha * 0.85 + 0.25));
      }

      targetX += Math.sin(tau * 0.35 + phaseShift) * 0.12;
      targetY += Math.cos(tau * 0.28 + phaseShift) * 0.12;

      let pinned = false;
      const onsideLimit = isHome ? defLineX - 1.2 : defLineX + 1.2;
      const freeToRun = tpl.playerId === ballOwnerId || tpl.playerId === receiverId || (seg.passState === "shoot" && tpl.playerId === seg.passer);
      if (isAttacking && tpl.line === "attack" && !freeToRun && !(offside && tpl.playerId === offside.attackerId)) {
        if (isHome && targetX > onsideLimit) targetX = onsideLimit;
        if (!isHome && targetX < onsideLimit) targetX = onsideLimit;
      }

      const wideAttacker = tpl.line === "attack" && Math.abs(tpl.anchorY - 50) > 22;
      const carryingWide = ballOwnerId === tpl.playerId && wideAttacker && attackingZone(seg);
      const deliveringCross =
        !ballOwnerId && tpl.playerId === seg.passer && wideAttacker &&
        (seg.danger === "wide_box" || (seg.heightPeak ?? 0) > 1.2);
      if (carryingWide || deliveringCross) {
        const byline = attackDir > 0 ? 91 : 9;
        targetX = lerp(targetX, byline, 0.72);
        targetY = lerp(targetY, tpl.anchorY, 0.7);
        pinned = true;
      }
      const receiving = !ballOwnerId && tpl.playerId === receiverId;
      const longReception = receiving && ((seg.heightPeak ?? 0) > 1.05 || Math.hypot(seg.x1 - (prevLive?.x ?? seg.x0), seg.y1 - (prevLive?.y ?? seg.y0)) > 28);
      if (receiving && !offside) {
        const centreForwardRun = tpl.line === "attack" && Math.abs(tpl.anchorY - 50) < 22;
        const cutBack = seg.danger === "central_box" && tpl.line === "midfield";
        if (cutBack) {
          targetX = seg.x1;
          targetY = seg.y1;
        } else if (longReception && !(centreForwardRun && (seg.danger === "wide_box" || seg.danger === "central_box"))) {
          const remain = Math.max(0.35, seg.t1 - tau);
          const toX = seg.x1;
          const toY = seg.y1;
          const dx = toX - liveX;
          const dy = toY - liveY;
          const dist = Math.hypot(dx, dy) || 1;
          const pace = Math.min(15, Math.max(8, dist / remain));
          const step = Math.min(pace, dist);
          const nextBallX = liveX + (dx / dist) * step;
          const nextBallY = liveY + (dy / dist) * step;
          const behind = nextBallX - attackDir * 2;
          targetX = attackDir > 0
            ? Math.min(toX, Math.max(tpl.anchorX, behind))
            : Math.max(toX, Math.min(tpl.anchorX, behind));
          targetY = lerp(tpl.anchorY, nextBallY, 0.8);
        } else if (attackingZone(seg) && centreForwardRun) {
          const spotX = attackDir > 0 ? 86 : 14;
          const whipped = (seg.heightPeak ?? 0) > 1.2;
          targetX = lerp(targetX, spotX, 0.8);
          targetY = lerp(targetY, whipped ? seg.y1 : 50, 0.74);
        } else {
          const ahead = (seg.x1 - targetX) * attackDir;
          if (ahead > 1) {
            const run = Math.min(ahead, 9) * Math.min(1, segAlpha + 0.2);
            targetX += run * attackDir;
            targetY = lerp(targetY, seg.y1, 0.22);
          }
        }
        pinned = true;
      }
      if (box && tpl.playerId === (box.side === "home" ? "home_9" : "away_9")) {
        targetX = lerp(targetX, box.side === "home" ? 82 : 18, 0.9);
        targetY = lerp(targetY, box.side === "home" ? 44 : 56, 0.82);
        pinned = true;
      } else if (box && tpl.playerId === (box.side === "home" ? "away_5" : "home_5") && tpl.line === "defense") {
        targetX = box.side === "home" ? 94 : 6;
        targetY = 40;
        pinned = true;
      } else if (offside && tpl.line === "defense" && tpl.side !== offside.attack) {
        targetX = offside.lineX;
        targetY = 50 + (tpl.anchorY - 50) * 0.9;
        pinned = true;
      } else if (offside && tpl.playerId === offside.attackerId) {
        targetX = offside.attackerX;
        targetY = 50;
        pinned = true;
      } else if (offside && tpl.side === offside.attack && tpl.line === "attack") {
        targetX = offside.attack === "home" ? offside.lineX - 2 : offside.lineX + 2;
        targetY = tpl.anchorY;
        pinned = true;
      } else if (prevWasAttack && tpl.playerId === seg.passer && tpl.line === "defense" && prevSeg && !box) {
        const boxX = prevSeg.possession === "home" ? 88 : 12;
        targetX = lerp(targetX, boxX, 0.84);
        targetY = lerp(targetY, 48, 0.55);
        pinned = true;
      } else if (tpl.playerId === presserId && !box) {
        const wideBall = Math.abs(liveY - 50) > 16;
        const inside = wideBall ? (liveY > 50 ? -12 : 12) : (tpl.anchorY >= liveY ? 7 : -7);
        targetX = tpl.side === "home" ? liveX - 7 : liveX + 7;
        targetY = clampPitch(liveY + inside, 8, 92);
      }

      if (tau >= 204 && tau <= 212 && tpl.playerId === "home_9") {
        targetX = lerp(targetX, 84, 0.8);
        targetY = lerp(targetY, 44, 0.7);
        pinned = true;
      } else if (tau >= 51 && tau <= 56 && tpl.playerId === "home_9") {
        targetX = lerp(targetX, 84, 0.6);
        targetY = lerp(targetY, 52, 0.45);
        pinned = true;
      } else if (tau >= 152 && tau <= 159 && (tpl.playerId === "home_4" || tpl.playerId === "away_9")) {
        targetX = lerp(targetX, 18, 0.55);
        targetY = lerp(targetY, tpl.playerId === "home_4" ? 48 : 54, 0.55);
        pinned = true;
      }

      if (tau < 2 && tpl.playerId === "home_9") {
        targetX = 54;
        targetY = 50;
        pinned = true;
      }
      if (wideFinal && isAttacking && tpl.playerId === farWingerId && tpl.playerId !== ballOwnerId) {
        targetX = possessionSide === "home" ? 84 : 16;
        targetY = liveY < 50 ? 68 : 32;
        pinned = true;
      } else if (wideFinal && isAttacking && tpl.playerId === boxStrikerId && tpl.playerId !== ballOwnerId) {
        targetX = possessionSide === "home" ? 84 : 16;
        targetY = 50;
        pinned = true;
      } else if (
        wideFinal &&
        isAttacking &&
        tpl.line === "midfield" &&
        Math.abs(tpl.anchorY - liveY) < 22 &&
        tpl.playerId !== ballOwnerId
      ) {
        targetX = possessionSide === "home" ? 74 : 26;
        targetY = lerp(tpl.anchorY, liveY, 0.4);
        pinned = true;
      }
      if (box && tpl.line === "defense" && tpl.side !== box.side && tpl.playerId !== (box.side === "home" ? "away_5" : "home_5")) {
        const centre = Math.abs(tpl.anchorY - 50) < 22;
        targetX = box.side === "home" ? 94 : 6;
        targetY = centre ? (tpl.anchorY < 50 ? 42 : 58) : (tpl.anchorY < 50 ? 32 : 68);
        pinned = true;
      }
      if (seg.passState === "shoot" && !seg.eventId && tpl.line === "defense" && tpl.side !== possessionSide) {
        targetX = possessionSide === "home" ? 78 : 22;
        targetY = tpl.anchorY;
        pinned = true;
      }
      if (deepBox && isAttacking && tpl.line === "attack" && tpl.playerId !== ballOwnerId) {
        targetX = possessionSide === "home" ? 84 : 16;
        targetY = Math.abs(tpl.anchorY - 50) < 18 ? 50 : tpl.anchorY < 50 ? 34 : 66;
        pinned = true;
      } else if (deepBox && isAttacking && tpl.playerId.endsWith("_8") && tpl.playerId !== ballOwnerId) {
        targetX = possessionSide === "home" ? 74 : 26;
        targetY = lerp(tpl.anchorY, 48, 0.45);
        pinned = true;
      }
      const tackling = tau >= 152 && tau <= 159;
      if (tpl.playerId === ballOwnerId && !celebrationTeamId && !offside && !tackling && !(tau < 2 && tpl.playerId === "home_9")) {
        const facing = possessionSide === "home" ? 1 : -1;
        const endAhead = (seg.x1 - liveX) * facing;
        const endDist = Math.hypot(seg.x1 - liveX, seg.y1 - liveY);
        if (endDist < 2.5 || endAhead < -1) {
          targetX = liveX;
          targetY = liveY;
        } else {
          const dx = seg.x1 - liveX;
          const dy = seg.y1 - liveY;
          const dist = Math.hypot(dx, dy) || 1;
          const step = Math.min(8, dist);
          targetX = liveX + (dx / dist) * step;
          targetY = liveY + (dy / dist) * step;
        }
        pinned = true;
      }
      if (
        ballOwnerId?.endsWith("_1") &&
        tpl.playerId !== ballOwnerId &&
        tpl.line === "defense" &&
        tpl.side === possessionSide &&
        ((tpl.side === "home" && liveX < 18) || (tpl.side === "away" && liveX > 82))
      ) {
        targetX = tpl.side === "home" ? 24 : 76;
        targetY = tpl.anchorY;
        pinned = true;
      }
      const nextPass = segmentAfter(seg);
      const nextRun = nextPass ? segmentAfter(nextPass) : null;
      if (
        nextPass &&
        !nextPass.owner &&
        nextRun?.owner === tpl.playerId &&
        tpl.line === "attack" &&
        tpl.side === possessionSide &&
        !offside &&
        Math.hypot(nextPass.x1 - nextPass.x0, nextPass.y1 - nextPass.y0) > 24
      ) {
        const runDir = tpl.side === "home" ? 1 : -1;
        targetX = clampPitch(tpl.anchorX + runDir * 4, 12, 90);
        targetY = lerp(tpl.anchorY, nextPass.y1, 0.55);
        pinned = true;
      }
      const keeperPlaying = Boolean(ballOwnerId?.endsWith("_1"));
      const kickTarget = keeperPlaying ? segmentAfter(seg) : null;
      if (
        kickTarget &&
        kickTarget.possession === seg.possession &&
        tpl.playerId === (kickTarget.owner || kickTarget.passer) &&
        tpl.playerId !== ballOwnerId
      ) {
        targetX = kickTarget.x1;
        targetY = kickTarget.y1;
        pinned = true;
      }
      if (tau >= 152 && tau <= 159 && tpl.playerId === "home_4") {
        targetX = 16;
        targetY = 52;
        pinned = true;
      }
      if (tau >= 152 && tau <= 159 && tpl.playerId === "away_9") {
        targetX = 18;
        targetY = 54;
        pinned = true;
      }
      if (tpl.playerId === offerId && !deepBox) {
        const dir = possessionSide === "home" ? 1 : -1;
        const show = tpl.anchorY >= 50 ? 12 : -12;
        targetX = clampPitch(liveX - dir * 6, 12, 88);
        targetY = clampPitch(liveY + show, 14, 86);
      }
        if (tpl.playerId === runnerId && tpl.playerId !== receiverId) {
          const dir = possessionSide === "home" ? 1 : -1;
          targetX = clampPitch(liveX + dir * 12, 12, 88);
          targetY = tpl.anchorY;
        }
        if (tpl.playerId === coverId && markedRunner && !deepBox && !box) {
          const runnerDir = markedRunner.side === "home" ? 1 : -1;
          const runX = clampPitch(liveX + runnerDir * 10, 14, 86);
          targetX = clampPitch(runX + runnerDir * 8, 8, 94);
          targetY = markedRunner.anchorY;
        }
      const releasing =
        !ballOwnerId &&
        tpl.playerId === seg.passer &&
        tpl.playerId !== receiverId &&
        !offside &&
        (seg.heightPeak ?? 0) < 1.05 &&
        seg.danger !== "wide_box" &&
        seg.passState !== "shoot";
      if (releasing) {
        const dir = tpl.side === "home" ? 1 : -1;
        targetX = clampPitch(liveX + dir * 8, 8, 92);
        targetY = clampPitch(50 + (tpl.anchorY - 50) * 0.85, 10, 90);
        pinned = true;
      }
      if (tau >= 148 && tau <= 159 && tpl.playerId === "home_6") {
        targetX = 32;
        targetY = 58;
        pinned = true;
      }
      if (tau >= 81 && tau <= 91 && tpl.playerId === "home_10") {
        targetX = 70;
        targetY = 48;
        pinned = true;
      }
      if (tau >= 275 && tau <= 280 && tpl.playerId === "away_9") {
        targetX = 20;
        targetY = 46;
        pinned = true;
      }
      if (tau >= 245 && tau <= 256 && tpl.playerId === "home_8") {
        targetX = 70;
        targetY = 12;
        pinned = true;
      }
      if (tau >= 295 && tau <= 301 && tpl.playerId === "home_9") {
        targetX = 78;
        targetY = 32;
        pinned = true;
      }
      if (tau >= 249 && tau <= 255 && tpl.playerId === "home_6") {
        targetX = 64;
        targetY = 22;
        pinned = true;
      }
      if (tau >= 218 && tau <= 227 && tpl.playerId === "home_2") {
        targetX = 30;
        targetY = 48;
        pinned = true;
      }
      const filedLane = 50 + (tpl.anchorY - 50) * 0.96;
      const onAJob = pinned
        || tpl.playerId === presserId
        || tpl.playerId === ballOwnerId
        || tpl.playerId === receiverId
        || tpl.playerId === offerId
        || tpl.playerId === runnerId
        || tpl.playerId === coverId;
      if (!onAJob && !celebrationTeamId && !offside) {
        targetY = lerp(targetY, filedLane, 0.86);
      }
      const nextDelivery = segmentAfter(seg);
      const crossComing = Boolean(
        nextDelivery &&
        !nextDelivery.owner &&
        (nextDelivery.heightPeak ?? 0) > 1.2 &&
        (nextDelivery.danger === "wide_box" || nextDelivery.danger === "central_box")
      );
      const posts = box?.side ?? (crossComing ? possessionSide : null);
      if (posts && tpl.line === "defense" && tpl.side !== posts) {
        const marker = posts === "home" ? "away_5" : "home_5";
        const centre = Math.abs(tpl.anchorY - 50) < 22;
        const nearPost = liveY >= 50 ? 66 : 34;
        const farPost = nearPost === 66 ? 30 : 70;
        const attackingRight = posts === "home";
        if (tpl.playerId === marker) {
          targetX = attackingRight ? 88 : 12;
          targetY = nearPost;
        } else if (centre) {
          targetX = attackingRight ? 92 : 8;
          targetY = farPost;
        } else {
          targetX = attackingRight ? 90 : 10;
          targetY = tpl.anchorY < 50 ? 24 : 76;
        }
        pinned = true;
      }
      if (celebrationTeamId === "home_lions" && tpl.side === "home") {
        const fan = (tpl.anchorY - 50) * 0.08;
        targetX = tpl.playerId === "home_9" ? 93 : clampPitch(90 - Math.abs(fan) * 0.2, 86, 93);
        targetY = tpl.playerId === "home_9" ? 93 : clampPitch(91 - fan, 84, 94);
        pinned = true;
      } else if (celebrationTeamId && tpl.side !== "home") {
        targetX = 48;
        targetY = tpl.anchorY;
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

    const prevFrame = frames[frames.length - 1];
    if (prevFrame) {
      for (let i = 0; i < rawPos.length; i += 1) {
        const tpl = allTemplates[i];
        const prev = prevFrame.players[i]?.position;
        if (!prev) continue;
        const coverX = lerp(seg.x0, seg.x1, segAlpha);
        const lineRetreating =
          tpl.line === "defense" &&
          tpl.side !== seg.possession &&
          (seg.possession === "home" ? coverX > 66 : coverX < 34);
        const sprinting =
          tpl.playerId === ballOwnerId ||
          tpl.playerId === receiverId ||
          tpl.playerId === presserId ||
          tpl.playerId === offerId ||
          tpl.playerId === runnerId ||
          tpl.playerId === coverId ||
          tpl.playerId === seg.passer ||
          (Boolean(prevSeg) && tpl.side === prevSeg?.possession && tpl.side !== seg.possession && !offside && !box) ||
          tpl.playerId === farWingerId ||
          tpl.playerId === boxStrikerId ||
          (deepBox && tpl.side === possessionSide && (tpl.line === "attack" || tpl.playerId.endsWith("_8")) && tpl.playerId !== ballOwnerId) ||
          (tau >= 152 && tau <= 159 && (tpl.playerId === "home_4" || tpl.playerId === "away_9")) ||
          (Boolean(ballOwnerId?.endsWith("_1")) && tpl.playerId === (segmentAfter(seg)?.owner || segmentAfter(seg)?.passer)) ||
          lineRetreating ||
          (offside && (tpl.playerId === offside.attackerId || (tpl.line === "defense" && tpl.side !== offside.attack))) ||
          (Boolean(celebrationTeamId) && tpl.side === "home");
        const maxStep = tpl.role === "GK" ? 3.4 : sprinting ? 8.2 : 5.6;
        const dx = rawPos[i].x - prev.x;
        const dy = rawPos[i].y - prev.y;
        const step = Math.hypot(dx, dy);
        if (seg.stage !== "reset" && step > maxStep) {
          rawPos[i].x = clampPitch(prev.x + (dx / step) * maxStep, 5, 95);
          rawPos[i].y = clampPitch(prev.y + (dy / step) * maxStep, 5, 95);
        }
      }
      for (let i = 0; i < rawPos.length; i += 1) {
        const prev = prevFrame.players[i]?.position;
        if (!prev) continue;
        const dx = rawPos[i].x - prev.x;
        const dy = rawPos[i].y - prev.y;
        const step = Math.hypot(dx, dy);
        const maxStep = allTemplates[i].role === "GK" ? 3.4 : 8.2;
        if (seg.stage !== "reset" && step > maxStep) {
          rawPos[i].x = clampPitch(prev.x + (dx / step) * maxStep, 5, 95);
          rawPos[i].y = clampPitch(prev.y + (dy / step) * maxStep, 5, 95);
        }
      }
      if (!offside && !celebrationTeamId) {
        const defenderX = rawPos
          .map((pos, index) => ({ x: pos.x, tpl: allTemplates[index] }))
          .filter((item) => item.tpl.line === "defense" && item.tpl.side !== seg.possession)
          .map((item) => item.x)
          .sort((a, b) => a - b);
        if (defenderX.length >= 2) {
          const lineX = seg.possession === "home" ? defenderX[defenderX.length - 2] : defenderX[1];
          for (let i = 0; i < rawPos.length; i += 1) {
            const tpl = allTemplates[i];
            if (tpl.side !== seg.possession || tpl.role === "GK") continue;
            if (seg.possession === "home" && rawPos[i].x > lineX - 1) rawPos[i].x = lineX - 1.2;
            if (seg.possession === "away" && rawPos[i].x < lineX + 1) rawPos[i].x = lineX + 1.2;
          }
        }
      }
      const focusId = ballOwnerId || (seg.passState === "shoot" ? null : receiverId);
      if (focusId && !(tau >= 152 && tau <= 159)) {
        const ownerIndex = allTemplates.findIndex((tpl) => tpl.playerId === focusId);
        const owner = ownerIndex >= 0 ? rawPos[ownerIndex] : null;
        const defenderX = rawPos
          .map((pos, index) => ({ x: pos.x, tpl: allTemplates[index] }))
          .filter((item) => item.tpl.line === "defense" && item.tpl.side !== seg.possession)
          .map((item) => item.x)
          .sort((a, b) => a - b);
        const lineX = defenderX.length >= 2
          ? (seg.possession === "home" ? defenderX[defenderX.length - 2] : defenderX[1])
          : null;
        if (owner) {
          for (let i = 0; i < rawPos.length; i += 1) {
            if (i === ownerIndex) continue;
            const tpl = allTemplates[i];
            if (tpl.playerId === presserId) continue;
            if (box && tpl.line === "defense" && tpl.side !== box.side) continue;
            const gap = Math.hypot(rawPos[i].x - owner.x, rawPos[i].y - owner.y);
            const room = tpl.role === "GK" ? 6 : 12;
            if (gap >= room) continue;
            const dx = rawPos[i].x - owner.x;
            const dy = rawPos[i].y - owner.y || (tpl.anchorY >= owner.y ? 1 : -1);
            const len = Math.hypot(dx, dy) || 1;
            let nx = owner.x + (dx / len) * room;
            let ny = owner.y + (dy / len) * room;
            const teammate = tpl.side === seg.possession && tpl.role !== "GK" && tpl.playerId !== focusId;
            const pastLine = !offside && lineX !== null && teammate && (seg.possession === "home" ? nx > lineX - 1.2 : nx < lineX + 1.2);
            if (pastLine) {
              nx = seg.possession === "home" ? Math.min(nx, lineX - 1.2) : Math.max(nx, lineX + 1.2);
              ny = owner.y + Math.sign(dy) * room;
            }
            rawPos[i].x = clampPitch(nx, 5, 95);
            rawPos[i].y = clampPitch(ny, 6, 94);
          }
        }
      }
    }

    if (celebrationTeamId) {
      ballX = 96.2;
      ballY = 46;
      ballHeight = 0.08;
      ballState = "in_goal";
    } else {
      const restart = Boolean(prevSeg?.celebration);
      const fromX = restart ? seg.x0 : (prevLive?.x ?? 50);
      const fromY = restart ? seg.y0 : (prevLive?.y ?? 50);
      const feet = (id: string | null | undefined) => {
        if (!id) return null;
        const index = allTemplates.findIndex((tpl) => tpl.playerId === id);
        return index >= 0 ? rawPos[index] : null;
      };
      const ownerFeet = feet(ballOwnerId);
      const receiverFeet = feet(receiverId);
      const gapTo = (x: number, y: number) => Math.hypot(fromX - x, fromY - y);
      const fly = (toX: number, toY: number, speed: number, peak: number) => {
        const remain = Math.max(0.35, seg.t1 - tau);
        const dist = Math.hypot(toX - fromX, toY - fromY);
        const paced = speed >= 18 ? speed : Math.min(speed, Math.max(8, dist / remain));
        const step = stepToward(fromX, fromY, toX, toY, paced);
        ballX = clampPitch(step.x, 2, 98);
        ballY = clampPitch(step.y, 4, 96);
        const along = paced / Math.max(0.01, paced + step.left);
        ballHeight = peak > 0.35 ? Math.sin(along * Math.PI) * peak : 0.08;
        ballState = step.left < 1.2 ? "controlled" : "in_flight";
        if (step.left < 1.2 && peak > 0.8) ballHeight = 0.35;
      };

      const dir = possessionSide === "home" ? 1 : -1;
      const lead = (seg.x1 - fromX) * dir > 2 ? 1.15 : 0;
      const creep = (toX: number, toY: number, peak: number) => {
        const dx = toX - fromX;
        const dy = toY - fromY;
        const len = Math.hypot(dx, dy) || 1;
        const step = Math.min(10, len);
        fly(fromX + (dx / len) * step, fromY + (dy / len) * step, 10, peak);
      };
      const playInFront = (feetX: number) => {
        const ahead = (feetX - fromX) * dir;
        if (ahead >= -3) return false;
        ballX = fromX;
        ballY = fromY;
        ballHeight = 0.05;
        ballState = "controlled";
        return true;
      };
      const tackling = tau >= 152 && tau <= 159;
      const lateSave = tau >= 276 && tau <= 281 && seg.eventId === "ev_late_save_10";
      const goalInNet = tau >= 207 && tau < 210 && seg.eventId === "ev_goal_8";
      if (goalInNet) {
        ballX = 96.2;
        ballY = 46;
        ballHeight = 0.12;
        ballState = "in_goal";
      } else if (lateSave) {
        ballX = 7.2;
        ballY = 50;
        ballHeight = 0.2;
        ballState = "controlled";
      } else if (offside) {
        const holdX = offside.attack === "home" ? offside.lineX - 6 : offside.lineX + 6;
        fly(holdX, 50, 13, 0.9);
      } else if (tackling) {
        ballX = 17;
        ballY = 52;
        ballHeight = 0.05;
        ballState = "controlled";
      } else if (ownerFeet && ballOwnerId?.endsWith("_1") && gapTo(ownerFeet.x, ownerFeet.y) >= 4) {
        ballX = fromX;
        ballY = fromY;
        ballHeight = 0.05;
        ballState = "controlled";
      } else if (ownerFeet && gapTo(ownerFeet.x, ownerFeet.y) < 11) {
        if (!playInFront(ownerFeet.x)) {
          ballX = clampPitch(ownerFeet.x + dir * lead, 2, 98);
          ballY = ownerFeet.y;
          ballHeight = 0.05;
          ballState = "controlled";
        }
      } else if (seg.passState === "shoot") {
        const scoring = seg.eventId === "ev_goal_8";
        const saved = seg.eventId === "ev_shot_save_4" || seg.eventId === "ev_late_save_10";
        if (scoring) {
          fly(96.2, 46, 22, Math.max(0.7, seg.heightPeak ?? 0.9));
          if (ballX > 94.5) {
            ballState = "in_goal";
            ballHeight = 0.12;
          }
        } else if (saved) {
          const highSave = seg.eventId === "ev_shot_save_4";
          fly(
            possessionSide === "home" ? 92.8 : 7.2,
            50,
            highSave ? 12 : 6,
            Math.max(highSave ? 1.25 : 0.45, seg.heightPeak ?? 0.8),
          );
          if (highSave && ballState === "in_flight") ballHeight = Math.max(ballHeight, 1.2);
          if (Math.hypot(ballX - (possessionSide === "home" ? 92.8 : 7.2), ballY - 50) < 1.4) {
            ballState = "controlled";
            ballHeight = 0.05;
          }
        }
        else fly(seg.x1, seg.y1, 20, Math.max(0.35, seg.heightPeak ?? 0.4));
      } else if (ownerFeet) {
        if (!playInFront(ownerFeet.x)) {
          const gap = gapTo(ownerFeet.x, ownerFeet.y);
          if (gap < 16) {
            ballX = clampPitch(ownerFeet.x + dir * lead, 2, 98);
            ballY = ownerFeet.y;
            ballHeight = 0.05;
            ballState = "controlled";
          } else if (ballOwnerId?.endsWith("_1")) {
            ballX = fromX;
            ballY = fromY;
            ballHeight = 0.05;
            ballState = "controlled";
          } else {
            fly(ownerFeet.x, ownerFeet.y, 12, 0.3);
          }
        }
      } else if (receiverFeet) {
        const cross =
          (seg.heightPeak ?? 0) > 1.05 &&
          (seg.danger === "wide_box" || seg.danger === "central_box");
        const long = !cross && ((seg.heightPeak ?? 0) > 1.05 || gapTo(seg.x1, seg.y1) > 30);
        const cutBack = seg.danger === "central_box" && (seg.heightPeak ?? 0) < 1.05 && receiverId !== centreForward(possessionSide);
        if (cutBack) {
          fly(seg.x1, seg.y1, 14, 0.4);
        } else if (cross) {
          const homeAttack = possessionSide === "home";
          const spotX = homeAttack ? 82 : 18;
          const spotY = homeAttack ? 44 : 56;
          const aimX = lerp(receiverFeet.x, spotX, 0.75);
          const aimY = lerp(receiverFeet.y, spotY, 0.75);
          fly(aimX, aimY, 12, Math.max(1.5, seg.heightPeak ?? 1.5));
          if (Math.hypot(ballX - receiverFeet.x, ballY - receiverFeet.y) > 7) ballHeight = Math.max(ballHeight, 0.85);
        } else if (long) {
          const throughBall = (seg.heightPeak ?? 0) >= 0.45 && Math.hypot(seg.x1 - seg.x0, seg.y1 - seg.y0) > 28;
          const runnerAhead = (receiverFeet.x - fromX) * dir;
          if (throughBall) fly(seg.x1, seg.y1, 15, Math.max(0.55, seg.heightPeak ?? 0.6));
          else if (runnerAhead < 8 && (seg.heightPeak ?? 0) < 1.05) creep(seg.x1, seg.y1, Math.max(0.45, seg.heightPeak ?? 0.45));
          else fly(seg.x1, seg.y1, 15, Math.max(1.3, seg.heightPeak ?? 1.3));
        } else {
          const dir = possessionSide === "home" ? 1 : -1;
          const feetAhead = (receiverFeet.x - fromX) * dir;
          const spaceAhead = (seg.x1 - fromX) * dir;
          // A forward who is still behind the ball does not get the ball played back to him.
          if (feetAhead < 8 && spaceAhead > 6) {
            creep(seg.x1, seg.y1, Math.max(0.45, seg.heightPeak ?? 0.45));
          } else {
            fly(receiverFeet.x + dir * 2.2, receiverFeet.y, 17, 0.12);
          }
        }
      } else {
        fly(seg.x1, seg.y1, 16, Math.max(0.2, seg.heightPeak ?? 0.2));
      }
    }

    const focusId = ballOwnerId || (seg.passState === "shoot" ? null : receiverId);
    const tackling = tau >= 152 && tau <= 159;
    if (!celebrationTeamId) {
      const defenderX = rawPos
        .map((pos, index) => ({ x: pos.x, tpl: allTemplates[index] }))
        .filter((item) => item.tpl.line === "defense" && item.tpl.side !== seg.possession)
        .map((item) => item.x)
        .sort((a, b) => a - b);
      const lineX = defenderX.length >= 2
        ? (seg.possession === "home" ? defenderX[defenderX.length - 2] : defenderX[1])
        : null;
      for (let i = 0; i < rawPos.length; i += 1) {
        const tpl = allTemplates[i];
        if (tpl.playerId === focusId) continue;
        if (box && tpl.line === "defense" && tpl.side !== box.side) continue;
        if (tau >= 223 && tau <= 227 && tpl.playerId === "home_2") continue;
        if (tackling && (tpl.playerId === "home_4" || tpl.playerId === "away_9")) continue;
        if (offside && (tpl.playerId === offside.attackerId || tpl.playerId === offside.defenderId)) continue;
        if (tpl.role === "GK" && seg.passState === "shoot") continue;
        const gap = Math.hypot(rawPos[i].x - ballX, rawPos[i].y - ballY);
        const pressing = tpl.playerId === presserId;
        const room = tpl.role === "GK" ? 6 : pressing ? 9 : 12;
        if (gap >= room) continue;
        const attackDir = possessionSide === "home" ? 1 : -1;
        const shapeX = tpl.anchorX - ballX;
        const shapeY = tpl.anchorY - ballY;
        let dx = rawPos[i].x - ballX;
        let dy = rawPos[i].y - ballY || (tpl.anchorY >= ballY ? 4 : -4);
        if (tpl.playerId === runnerId) {
          dx = attackDir * 10;
          dy = shapeY || 8;
        } else if (tpl.playerId === offerId) {
          dx = -attackDir * 12;
          dy = shapeY || -8;
        } else if (!pressing && (ballX > 90 || ballX < 10)) {
          dx = ballX > 50 ? -14 : 14;
          dy = tpl.anchorY - 50 || 8;
        } else if (!pressing && tpl.line === "defense" && tpl.side !== possessionSide) {
          dx = tpl.side === "home" ? -14 : 14;
          dy = (tpl.anchorY - ballY) * 0.35 || (tpl.anchorY < 50 ? -8 : 8);
        } else if (!pressing && Math.hypot(shapeX, shapeY) > room) {
          dx = shapeX;
          dy = shapeY;
        }
        const len = Math.hypot(dx, dy) || 1;
        let nx = ballX + (dx / len) * room;
        let ny = ballY + (dy / len) * room;
        const teammate = tpl.side === seg.possession && tpl.role !== "GK";
        const pastLine = !offside && lineX !== null && teammate && (seg.possession === "home" ? nx > lineX - 1.2 : nx < lineX + 1.2);
        if (pastLine) {
          nx = seg.possession === "home" ? Math.min(rawPos[i].x, lineX - 1.2) : Math.max(rawPos[i].x, lineX + 1.2);
          ny = ballY + Math.sign(dy) * room;
        }
        rawPos[i].x = clampPitch(nx, 5, 95);
        rawPos[i].y = clampPitch(ny, 6, 94);
      }
      const prevPlayers = frames[frames.length - 1]?.players;
      if (prevPlayers) {
        for (let i = 0; i < rawPos.length; i += 1) {
          const prev = prevPlayers[i]?.position;
          if (!prev) continue;
          const dx = rawPos[i].x - prev.x;
          const dy = rawPos[i].y - prev.y;
          const step = Math.hypot(dx, dy);
          const maxStep = allTemplates[i].role === "GK" ? 3.4 : 8.2;
          if (seg.stage !== "reset" && step > maxStep) {
            rawPos[i].x = clampPitch(prev.x + (dx / step) * maxStep, 5, 95);
            rawPos[i].y = clampPitch(prev.y + (dy / step) * maxStep, 6, 94);
          }
        }
      }
    }

    if (tau >= 206 && tau <= 216 && seg.eventId === "ev_goal_8") {
      for (let i = 0; i < rawPos.length; i += 1) {
        if (allTemplates[i].playerId === "away_1") {
          rawPos[i].x = 90;
          rawPos[i].y = 62;
        }
      }
    }

    if (tau >= 276 && tau <= 281 && seg.eventId === "ev_late_save_10") {
      for (let i = 0; i < rawPos.length; i += 1) {
        const tpl = allTemplates[i];
        if (tpl.playerId === "home_1") {
          rawPos[i].x = 7.2;
          rawPos[i].y = 50;
          continue;
        }
        if (tpl.playerId === "home_4") {
          rawPos[i].x = 30;
          rawPos[i].y = 64;
          continue;
        }
        if (tpl.playerId === "away_9") {
          rawPos[i].x = 22;
          rawPos[i].y = 46;
          continue;
        }
        const gap = Math.hypot(rawPos[i].x - 7.2, rawPos[i].y - 50);
        if (gap >= 11) continue;
        const away = Math.max(11, gap);
        const dx = rawPos[i].x - 7.2 || 8;
        const dy = rawPos[i].y - 50 || (tpl.anchorY >= 50 ? 8 : -8);
        const len = Math.hypot(dx, dy) || 1;
        rawPos[i].x = clampPitch(7.2 + (dx / len) * away, 8, 40);
        rawPos[i].y = clampPitch(50 + (dy / len) * away, 16, 84);
      }
    }

    const primaryActorOverrideState: Record<string, string> = { ...(seg.overrides || {}) };
    if (seg.passer && segAlpha < 0.45 && !primaryActorOverrideState[seg.passer]) {
      primaryActorOverrideState[seg.passer] = seg.passState || "pass";
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
      if (prevPlayer) metresRun[idx] += Math.hypot(vx, vy);
      const fatiguePerMetre = tpl.role === "GK" ? 0.012 : tpl.role === "DEF" ? 0.03 : tpl.role === "MID" ? 0.04 : 0.034;
      const staminaPct = Math.max(38, Math.min(100, Math.round(100 - metresRun[idx] * fatiguePerMetre)));
      const rawSpeed = Math.hypot(vx, vy) / 4.8;
      let speedRatio = Math.max(0, Math.min(1, Number(rawSpeed.toFixed(3))));
      if (ballOwnerId === tpl.playerId) speedRatio = Math.max(speedRatio, 0.16);

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
        stamina_pct: staminaPct,
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
      offside_snapshot: offside
        ? {
            offside_line_x: Number((offside.lineX / 100).toFixed(3)),
            attacker_line_x: Number((offside.attackerX / 100).toFixed(3)),
            margin_meters: Number((Math.abs(offside.attackerX - offside.lineX) * 1.05).toFixed(2)),
            attacker_id: offside.attackerId,
            attacker_name: (() => {
              const attacker = allTemplates.find((tpl) => tpl.playerId === offside.attackerId);
              return attacker ? `${attacker.label} #${attacker.shirtNumber}` : null;
            })(),
            attacker_body_part: "torso",
            second_last_defender_id: offside.defenderId,
            second_last_defender_name: (() => {
              const defender = allTemplates.find((tpl) => tpl.playerId === offside.defenderId);
              return defender ? `${defender.label} #${defender.shirtNumber}` : null;
            })(),
            second_last_defender_body_part: "torso",
            is_offside_position: true,
            is_penalised: true,
            attacking_direction: offside.attack === "home" ? 1 : -1,
            reason: "beyond the second-last defender",
          }
        : null,
      players,
      ball: {
        position: { x: Number(ballX.toFixed(2)), y: Number(ballY.toFixed(2)) },
        height: Number(ballHeight.toFixed(3)),
        state: ballState,
        owner_player_id:
          tau >= 276 && tau <= 281 && seg.eventId === "ev_late_save_10" ? "home_1" : ballOwnerId,
        spin: ballHeight > 0.2 ? { x: 0.2, y: 0.5, z: 0.8 } : null,
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
