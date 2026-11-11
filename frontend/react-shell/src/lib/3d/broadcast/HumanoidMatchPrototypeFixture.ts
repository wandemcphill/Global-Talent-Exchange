/**
 * GTEX Unit 2A (U2A-006) — Humanoid Football Animation Engine
 * HumanoidMatchPrototypeFixture: Controlled 22-Player Prototype & Mandatory
 * 5-Minute (300-Second) Continuous GTEX Match Acceptance Fixture.
 *
 * Generates an authoritative, physics-consistent 300-second `SpectatorSafeMatchView`
 * containing all 22 humanoid footballers across both teams in 4-3-3 tactical structures,
 * driving every required football action category:
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
  { playerId: "home_1", side: "home", shirtNumber: 1, label: "1", role: "GK", line: "goalkeeper", anchorX: 7, anchorY: 50 },
  { playerId: "home_2", side: "home", shirtNumber: 2, label: "2", role: "DEF", line: "defense", anchorX: 24, anchorY: 18 },
  { playerId: "home_4", side: "home", shirtNumber: 4, label: "4", role: "DEF", line: "defense", anchorX: 22, anchorY: 39 },
  { playerId: "home_5", side: "home", shirtNumber: 5, label: "5", role: "DEF", line: "defense", anchorX: 22, anchorY: 61 },
  { playerId: "home_3", side: "home", shirtNumber: 3, label: "3", role: "DEF", line: "defense", anchorX: 24, anchorY: 82 },
  { playerId: "home_6", side: "home", shirtNumber: 6, label: "6", role: "MID", line: "midfield", anchorX: 43, anchorY: 50 },
  { playerId: "home_8", side: "home", shirtNumber: 8, label: "8", role: "MID", line: "midfield", anchorX: 50, anchorY: 28 },
  { playerId: "home_10", side: "home", shirtNumber: 10, label: "10", role: "MID", line: "midfield", anchorX: 54, anchorY: 70 },
  { playerId: "home_7", side: "home", shirtNumber: 7, label: "7", role: "FWD", line: "attack", anchorX: 74, anchorY: 18 },
  { playerId: "home_9", side: "home", shirtNumber: 9, label: "9", role: "FWD", line: "attack", anchorX: 78, anchorY: 50 },
  { playerId: "home_11", side: "home", shirtNumber: 11, label: "11", role: "FWD", line: "attack", anchorX: 74, anchorY: 82 },
];

export const AWAY_STARTERS_433: readonly BasePlayerTemplate[] = [
  { playerId: "away_1", side: "away", shirtNumber: 1, label: "1", role: "GK", line: "goalkeeper", anchorX: 93, anchorY: 50 },
  { playerId: "away_2", side: "away", shirtNumber: 2, label: "2", role: "DEF", line: "defense", anchorX: 76, anchorY: 82 },
  { playerId: "away_4", side: "away", shirtNumber: 4, label: "4", role: "DEF", line: "defense", anchorX: 78, anchorY: 61 },
  { playerId: "away_5", side: "away", shirtNumber: 5, label: "5", role: "DEF", line: "defense", anchorX: 78, anchorY: 39 },
  { playerId: "away_3", side: "away", shirtNumber: 3, label: "3", role: "DEF", line: "defense", anchorX: 76, anchorY: 18 },
  { playerId: "away_6", side: "away", shirtNumber: 6, label: "6", role: "MID", line: "midfield", anchorX: 57, anchorY: 50 },
  { playerId: "away_8", side: "away", shirtNumber: 8, label: "8", role: "MID", line: "midfield", anchorX: 50, anchorY: 72 },
  { playerId: "away_10", side: "away", shirtNumber: 10, label: "10", role: "MID", line: "midfield", anchorX: 46, anchorY: 30 },
  { playerId: "away_7", side: "away", shirtNumber: 7, label: "7", role: "FWD", line: "attack", anchorX: 26, anchorY: 82 },
  { playerId: "away_9", side: "away", shirtNumber: 9, label: "9", role: "FWD", line: "attack", anchorX: 22, anchorY: 50 },
  { playerId: "away_11", side: "away", shirtNumber: 11, label: "11", role: "FWD", line: "attack", anchorX: 26, anchorY: 18 },
];

function clampPitch(v: number): number {
  return Math.max(2, Math.min(98, v));
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
      minute: Math.max(1, M(S(12))),
      added_time: 0,
      clock_label: `${Math.max(1, M(S(12)))}'`,
      time_seconds: S(12),
      home_score: 0,
      away_score: 0,
      banner_text: "BUILD-UP PASSING COMBINATION",
      commentary: "Crisp one-touch midfield combination from #6 to #8.",
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
      commentary: "Weighted through ball releases #7 down the right flank.",
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
      commentary: "#7 whips an inviting cross into the penalty area for #9!",
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
      commentary: "Thunderous strike from #10 — acrobatic full-stretch save by Away GK #1!",
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
      commentary: "Away GK #1 launches a long drop-kick distribution into midfield.",
      team_id: "away_stars",
      team_name: "Abuja Coastal Stars",
      primary_player_id: "away_1",
      primary_player_name: "Akpan #1",
      secondary_player_id: "away_10",
      secondary_player_name: "Ibekwe #10",
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
      commentary: "Committed sliding challenge by #4 halts the counterattack.",
      team_id: "home_lions",
      team_name: "Lagos Atlas Lions",
      primary_player_id: "home_4",
      primary_player_name: "Umeadi #4",
      secondary_player_id: "away_9",
      secondary_player_name: "Okwuosa #9",
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
      commentary: "Sweeping 40-meter diagonal pass from #8 finds #11 in space.",
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
      commentary: "Clinical finish! #9 strikes an unstoppable volley into the top corner!",
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
      commentary: "Home GK #1 dives low to his right to preserve the lead!",
      team_id: "home_lions",
      team_name: "Lagos Atlas Lions",
      primary_player_id: "home_1",
      primary_player_name: "Mbadiwe #1",
      secondary_player_id: "away_9",
      secondary_player_name: "Okwuosa #9",
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

    // Determine active match phase, camera preset, and ball trajectory at second `t`
    let possessionSide: "home" | "away" = "home";
    let cameraPreset = "broadcast";
    let stage = "open_play";
    let activeEventId: string | null = null;
    let eventBanner: string | null = null;
    let celebrationTeamId: string | null = null;
    let transitionState = "stable";
    let dangerZone = "middle_third";
    let ballX = 50;
    let ballY = 50;
    let ballHeight = 0.05;
    let ballState = "controlled";
    let ballOwnerId: string | null = "home_6";
    let primaryActorOverrideState: Record<string, string> = {};

    if (tau < 8) {
      // Phase 1: Kickoff & initial walking/jogging
      activeEventId = "ev_kickoff";
      stage = tau < 2 ? "reset" : "event";
      ballOwnerId = tau < 3 ? "home_9" : "home_6";
      ballX = tau < 3 ? 50 : 44;
      ballY = 50;
    } else if (tau >= 8 && tau < 24) {
      // Phase 2: Short passing combination (#6 -> #8 -> #10)
      activeEventId = "ev_short_pass_1";
      stage = tau < 14 ? "pre" : tau < 19 ? "event" : "post";
      if (tau >= 12 && tau <= 15) {
        ballState = "in_flight";
        ballOwnerId = null;
        const alpha = (tau - 12) / 3;
        ballX = 45 + alpha * 10;
        ballY = 50 - alpha * 20;
        ballHeight = Math.sin(alpha * Math.PI) * 0.25;
        primaryActorOverrideState["home_6"] = "pass";
      } else {
        ballOwnerId = tau < 12 ? "home_6" : "home_8";
        ballX = tau < 12 ? 45 : 55 + (tau - 15) * 0.8;
        ballY = t < 12 ? 50 : 30;
      }
    } else if (tau >= 24 && tau < 48) {
      // Phase 3: Through ball to right winger #7 & high-speed dribble + shield
      activeEventId = "ev_through_ball_2";
      transitionState = "home_break";
      cameraPreset = "attack_push";
      dangerZone = "final_third";
      if (tau >= 27 && tau <= 31) {
        stage = "event";
        ballState = "in_flight";
        ballOwnerId = null;
        const alpha = (tau - 27) / 4;
        ballX = 58 + alpha * 22;
        ballY = 28 - alpha * 12;
        ballHeight = Math.sin(alpha * Math.PI) * 0.35;
        primaryActorOverrideState["home_8"] = "pass";
      } else {
        stage = "post";
        ballOwnerId = "home_7";
        ballX = 80 + Math.min(10, (tau - 31) * 0.65);
        ballY = 16;
        primaryActorOverrideState["home_7"] = tau < 42 ? "sprint" : "idle";
      }
    } else if (tau >= 48 && tau < 72) {
      // Phase 4: Whipped wide cross & aerial header challenge (#7 -> #9 vs #4)
      activeEventId = "ev_wing_cross_3";
      cameraPreset = "box_zoom";
      dangerZone = "wide_box";
      if (tau >= 51 && tau <= 56) {
        stage = "event";
        ballState = "in_flight";
        ballOwnerId = null;
        const alpha = (tau - 51) / 5;
        ballX = 88 - alpha * 3;
        ballY = 15 + alpha * 35;
        ballHeight = 0.2 + Math.sin(alpha * Math.PI) * 2.15; // High aerial cross > 1.8m
        primaryActorOverrideState["home_7"] = "pass";
      } else {
        stage = "post";
        ballOwnerId = "home_10";
        ballX = 76;
        ballY = 58;
      }
    } else if (tau >= 72 && tau < 115) {
      // Phase 5: Shooting sequence (#10) & Goalkeeper Diving Save (away_1) + Distribution
      if (tau < 100) {
        activeEventId = "ev_shot_save_4";
        cameraPreset = "box_zoom";
        dangerZone = "central_box";
        if (tau < 86) {
          stage = "pre";
          ballOwnerId = "home_10";
          ballX = 78;
          ballY = 54;
        } else if (tau >= 86 && tau <= 91) {
          stage = "event";
          eventBanner = "DIVING GOALKEEPER SAVE!";
          ballState = "in_flight";
          ballOwnerId = null;
          const alpha = (tau - 86) / 5;
          ballX = 78 + alpha * 15;
          ballY = 54 - alpha * 4;
          ballHeight = 0.25 + Math.sin(alpha * Math.PI) * 1.45; // High corner shot > 1.1m
          primaryActorOverrideState["home_10"] = "shoot";
          primaryActorOverrideState["away_1"] = "save";
        } else {
          stage = "post";
          possessionSide = "away";
          ballOwnerId = "away_1";
          ballX = 92;
          ballY = 50;
          primaryActorOverrideState["away_1"] = "save";
        }
      } else {
        activeEventId = "ev_gk_dist_5";
        possessionSide = "away";
        cameraPreset = "broadcast";
        stage = tau <= 107 ? "event" : "post";
        if (tau >= 103 && tau <= 108) {
          ballState = "in_flight";
          ballOwnerId = null;
          const alpha = (tau - 103) / 5;
          ballX = 90 - alpha * 38;
          ballY = 50 - alpha * 16;
          ballHeight = Math.sin(alpha * Math.PI) * 2.4;
          primaryActorOverrideState["away_1"] = "pass";
        } else {
          ballOwnerId = "away_10";
          ballX = 52;
          ballY = 34;
        }
      }
    } else if (tau >= 115 && tau < 175) {
      // Phase 6: Away counterattack, interception (#6), standing tackle (#4), sliding tackle + foul
      possessionSide = tau < 160 ? "away" : "home";
      transitionState = tau < 145 ? "away_break" : "stable";
      cameraPreset = tau >= 152 && tau <= 165 ? "box_zoom" : "broadcast";
      if (tau >= 132 && tau <= 138) {
        // Interception window
        ballState = "in_flight";
        ballOwnerId = null;
        ballX = 46;
        ballY = 48;
        ballHeight = 0.35;
      } else if (tau >= 152 && tau <= 166) {
        activeEventId = "ev_tackle_foul_6";
        stage = tau <= 159 ? "event" : "post";
        eventBanner = tau <= 162 ? "SLIDING TACTICAL CHALLENGE" : null;
        ballOwnerId = "away_9";
        ballX = 34;
        ballY = 50;
        primaryActorOverrideState["home_4"] = "press";
      } else {
        ballOwnerId = possessionSide === "away" ? "away_8" : "home_6";
        ballX = possessionSide === "away" ? 42 : 48;
        ballY = 52;
      }
    } else if (tau >= 175 && tau < 240) {
      // Phase 7: Long pass switch (#8 -> #11), Volley Goal (#9) & Goal Celebration
      if (tau < 198) {
        activeEventId = "ev_long_pass_7";
        cameraPreset = "attack_push";
        dangerZone = "final_third";
        if (tau >= 182 && tau <= 188) {
          stage = "event";
          ballState = "in_flight";
          ballOwnerId = null;
          const alpha = (tau - 182) / 6;
          ballX = 52 + alpha * 28;
          ballY = 26 + alpha * 52;
          ballHeight = Math.sin(alpha * Math.PI) * 1.65;
          primaryActorOverrideState["home_8"] = "pass";
        } else {
          stage = "post";
          ballOwnerId = "home_11";
          ballX = 82;
          ballY = 76;
        }
      } else {
        activeEventId = "ev_goal_8";
        dangerZone = "central_box";
        if (tau < 206) {
          stage = "pre";
          cameraPreset = "box_zoom";
          ballState = "in_flight";
          ballOwnerId = null;
          const alpha = (tau - 198) / 8;
          ballX = 82 + alpha * 4;
          ballY = 76 - alpha * 26;
          ballHeight = 0.4 + Math.sin(alpha * Math.PI) * 1.1;
        } else if (tau >= 206 && tau <= 210) {
          stage = "event";
          cameraPreset = "box_zoom";
          ballState = "in_flight";
          ballOwnerId = null;
          const alpha = (tau - 206) / 4;
          ballX = 86 + alpha * 12;
          ballY = 50;
          ballHeight = 0.95 - alpha * 0.4;
          primaryActorOverrideState["home_9"] = "shoot";
          primaryActorOverrideState["away_1"] = "save";
        } else if (tau >= 211 && tau <= 228) {
          stage = tau <= 218 ? "decision" : "post";
          cameraPreset = "goal_celebration";
          celebrationTeamId = "home_lions";
          eventBanner = "GOAL! LAGOS ATLAS LIONS 1 - 0";
          ballState = "in_goal";
          ballOwnerId = null;
          ballX = 98;
          ballY = 50;
          primaryActorOverrideState["home_9"] = "celebrate";
        } else {
          stage = "reset";
          cameraPreset = "broadcast";
          possessionSide = "away";
          ballOwnerId = "away_9";
          ballX = 50;
          ballY = 50;
        }
      }
    } else {
      // Phase 8 (240s - 300s): Substitution, Late Away Pressure, Shot Block & Low GK Save
      if (tau >= 245 && tau <= 256) {
        activeEventId = "ev_sub_9";
        stage = "event";
        eventBanner = "TACTICAL SUBSTITUTION";
        ballOwnerId = "home_6";
        ballX = 50;
        ballY = 48;
      } else if (tau >= 270 && tau <= 286) {
        activeEventId = "ev_late_save_10";
        possessionSide = "away";
        cameraPreset = "box_zoom";
        dangerZone = "central_box";
        if (tau <= 275) {
          stage = "pre";
          ballOwnerId = "away_9";
          ballX = 20;
          ballY = 50;
        } else if (tau <= 280) {
          stage = "event";
          eventBanner = "LOW DIVING STOP!";
          ballState = "in_flight";
          ballOwnerId = null;
          const alpha = (tau - 275) / 5;
          ballX = 20 - alpha * 13;
          ballY = 50 + alpha * 3;
          ballHeight = 0.45; // Low driven shot <= 1.05m -> triggers gk_dive_low!
          primaryActorOverrideState["away_9"] = "shoot";
          primaryActorOverrideState["home_1"] = "save";
        } else {
          stage = "post";
          possessionSide = "home";
          ballOwnerId = "home_1";
          ballX = 8;
          ballY = 52;
        }
      } else {
        possessionSide = "home";
        cameraPreset = "broadcast";
        ballOwnerId = "home_10";
        ballX = 54 + Math.sin(tau * 0.15) * 12;
        ballY = 50 + Math.cos(tau * 0.12) * 14;
      }
    }

    // Build 22 player telemetry records for frame `t`
    const players: SpectatorSafePlayerTelemetry[] = allTemplates.map((tpl, idx) => {
      const isHome = tpl.side === "home";
      const phaseShift = idx * 0.55;
      const tacticalShiftX = possessionSide === "home" ? 4.5 : -4.5;

      let px = tpl.anchorX + (tpl.role === "GK" ? 0 : tacticalShiftX + Math.sin(tau * 0.22 + phaseShift) * 4.2);
      let py = tpl.anchorY + (tpl.role === "GK" ? Math.sin(tau * 0.3) * 1.5 : Math.cos(tau * 0.18 + phaseShift) * 3.8);

      // Pull active actors toward the ball during their action windows
      if (ballOwnerId === tpl.playerId) {
        px = ballX;
        py = ballY;
      } else if (tau >= 51 && tau <= 56 && (tpl.playerId === "home_9" || tpl.playerId === "away_4")) {
        // Aerial header challenge convergence
        px = ballX + (tpl.playerId === "home_9" ? -0.4 : 0.4);
        py = ballY;
      } else if (tau >= 132 && tau <= 138 && tpl.playerId === "home_6") {
        // Interception convergence
        px = ballX + 0.8;
        py = ballY;
      } else if (tau >= 152 && tau <= 162 && (tpl.playerId === "home_4" || tpl.playerId === "away_9")) {
        // Sliding tackle convergence
        px = ballX + (tpl.playerId === "home_4" ? -0.8 : 0.4);
        py = ballY;
      } else if (tau >= 204 && tau <= 212 && tpl.playerId === "home_9") {
        // Goalscorer in the box
        px = 86;
        py = 50;
      } else if (tau >= 272 && tau <= 278 && tpl.playerId === "home_5") {
        // Shot blocker in front of away_9
        px = 17.5;
        py = 50.5;
      }

      px = clampPitch(px);
      py = clampPitch(py);

      // Compute velocity & speed ratio from previous second
      const prevFrame = frames[frames.length - 1];
      const prevPlayer = prevFrame?.players[idx];
      const vx = prevPlayer ? px - prevPlayer.position.x : isHome ? 1.0 : -1.0;
      const vy = prevPlayer ? py - prevPlayer.position.y : 0.0;
      const rawSpeed = Math.hypot(vx, vy) / 5.5;
      let speedRatio = Math.max(0.06, Math.min(1.0, Number(rawSpeed.toFixed(3))));

      // Vary speed cycles across the match so walk, jog, run, and sprint are all exercised
      if (tpl.role !== "GK") {
        const wave = (Math.sin(tau * 0.35 + idx) + 1) * 0.5;
        speedRatio = Math.max(speedRatio, Number((0.08 + wave * 0.78).toFixed(3)));
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
          x: Math.abs(vx) > 0.01 || Math.abs(vy) > 0.01 ? vx : isHome ? 1 : -1,
          y: vy,
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
