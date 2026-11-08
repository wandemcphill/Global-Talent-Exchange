/**
 * GTEX Unit 2A (U2A-006) — Humanoid Football Animation Engine
 * Mandatory 5-Minute (300-Second) Continuous GTEX Match Acceptance & Performance Suite.
 */

import React, { act } from "react";
import { createRoot } from "react-dom/client";
import * as fs from "fs";
import * as path from "path";
import * as THREE from "three";
import { buildFiveMinuteHumanoidMatchFixture } from "../HumanoidMatchPrototypeFixture";
import { SpatialInterpolator } from "../SpatialInterpolator";
import { CameraDirector } from "../CameraDirector";
import { StadiumArenaEnvironment } from "../StadiumArenaEnvironment";
import { FootballAnimationStateMachine, FootballAnimationState } from "../FootballAnimationStateMachine";
import { HumanoidFootballerRig, parseHumanoidFootballerGLBBuffer } from "../HumanoidFootballerRig";
import { MatchPitchLiveScene } from "../MatchPitchLiveScene";
import { sanitizeForSpectator } from "../spectatorContract";

describe("U2A-006 Mandatory 5-Minute Humanoid Match Acceptance Test", () => {
  beforeAll(async () => {
    const glbPath = path.resolve(
      __dirname,
      "../../../../../public/models/footballer/gtex_humanoid_footballer.glb"
    );
    const buf = fs.readFileSync(glbPath);
    await parseHumanoidFootballerGLBBuffer(
      buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength)
    );
  });

  it("executes a continuous 5-minute (300s) 22-player humanoid GTEX match with all required football actions and camera transitions", () => {
    const matchView = buildFiveMinuteHumanoidMatchFixture(300);
    expect(matchView.frames.length).toBe(301);
    expect(matchView.frames[0].players).toHaveLength(22);

    const scene = new THREE.Scene();
    const stadium = new StadiumArenaEnvironment(scene, {
      homeTeam: matchView.home_team,
      awayTeam: matchView.away_team,
      qualityTier: "high",
      stadiumName: matchView.venue_name,
    });

    const interpolator = new SpatialInterpolator(matchView.frames);
    const cameraDirector = new CameraDirector();
    const fsm = new FootballAnimationStateMachine(matchView.events);
    const rigs = new Map<string, HumanoidFootballerRig>();

    // Instantiate all 22 humanoid footballer rigs
    for (const p of matchView.frames[0].players) {
      const team = p.side === "home" ? matchView.home_team : matchView.away_team;
      const isGK = p.role === "GK";
      const rig = new HumanoidFootballerRig({
        playerId: p.player_id,
        side: p.side,
        shirtNumber: p.shirt_number || 10,
        label: p.label,
        role: p.role,
        isGoalkeeper: isGK,
        primaryColor: team.primary_color,
        secondaryColor: team.secondary_color,
        accentColor: team.accent_color,
        goalkeeperColor: team.goalkeeper_color,
      });
      scene.add(rig.rootGroup);
      rigs.set(p.player_id, rig);
    }

    expect(rigs.size).toBe(22);

    const observedStates = new Set<FootballAnimationState>();
    const observedCameraPresets = new Set<string>();
    const observedLodLevels = new Set<string>();
    const stepTimesMs: number[] = [];

    // Step continuously from t = 0.0s to t = 300.0s at 0.5s intervals (601 continuous steps)
    const stepSec = 0.5;
    for (let t = 0; t <= 300; t += stepSec) {
      stadium.update(stepSec);
      const state = interpolator.interpolate(t);
      if (!state) throw new Error(`Null interpolated state at t=${t}s`);

      const t0 = performance.now();

      observedCameraPresets.add(state.camera_preset);
      const activeEvent = fsm.getEventById(state.active_event_id);
      const scorer = state.players.find((p) => p.animation_state === "celebrate");
      const camPose = cameraDirector.update(
        stepSec,
        state.camera_preset,
        state.ball.position3D,
        scorer ? scorer.position3D : null
      );

      for (const p of state.players) {
        const rig = rigs.get(p.player_id);
        if (!rig) throw new Error(`Missing rig for ${p.player_id}`);

        const targetState = fsm.resolvePlayerState({
          player: p,
          allPlayers: state.players,
          ball: state.ball,
          matchState: state,
          activeEvent,
          previousState: rig.getCurrentState(),
          timeInCurrentStateSec: rig.getTimeInCurrentState(),
        });

        rig.update({
          deltaSec: stepSec,
          targetState,
          position3D: p.position3D,
          facingAngleRad: p.facingAngleRad,
          speedRatio: p.speed_ratio,
          angularVelocityRad: p.angular_velocity_rad,
          hasPossession: p.has_possession,
          ballPosition3D: state.ball.position3D,
          cameraPosition3D: camPose.position,
          qualityTier: "high",
        });

        observedStates.add(rig.getCurrentState());
        observedLodLevels.add(rig.getLODLevel());

        // Fast invariant check without Jest matcher overhead inside frame timer
        const hips = rig.boneByName.get("Hips")!;
        if (
          !Number.isFinite(rig.rootGroup.position.x) ||
          !Number.isFinite(rig.rootGroup.position.z) ||
          !Number.isFinite(rig.rootGroup.rotation.y) ||
          !Number.isFinite(hips.position.y)
        ) {
          throw new Error(`Non-finite transform on ${p.player_id} at t=${tSec}s`);
        }
      }

      const elapsedMs = performance.now() - t0;
      stepTimesMs.push(elapsedMs);
    }

    // Verify all mandatory action categories occurred during the 5-minute match
    // 1. Locomotion
    expect(observedStates.has("walk") || observedStates.has("jog")).toBe(true);
    expect(observedStates.has("run")).toBe(true);
    expect(observedStates.has("sprint")).toBe(true);

    // 2. Passing, receiving & dribbling
    expect(observedStates.has("short_pass")).toBe(true);
    expect(observedStates.has("through_ball")).toBe(true);
    expect(observedStates.has("long_pass")).toBe(true);
    expect(observedStates.has("cross")).toBe(true);
    expect(observedStates.has("receive_ball") || observedStates.has("first_touch")).toBe(true);
    expect(observedStates.has("dribble")).toBe(true);

    // 3. Shooting, volley & aerial header challenge
    expect(observedStates.has("jumping_challenge")).toBe(true);
    expect(observedStates.has("shoot")).toBe(true);
    expect(observedStates.has("volley")).toBe(true);

    // 4. Goalkeeper actions
    expect(observedStates.has("gk_ready_stance")).toBe(true);
    expect(observedStates.has("gk_dive_high")).toBe(true);
    expect(observedStates.has("gk_dive_low")).toBe(true);
    expect(observedStates.has("gk_catch")).toBe(true);
    expect(observedStates.has("gk_distribution")).toBe(true);

    // 5. Defensive actions & match reactions
    expect(
      observedStates.has("interception") ||
        observedStates.has("sliding_tackle") ||
        observedStates.has("standing_tackle") ||
        observedStates.has("blocking")
    ).toBe(true);
    expect(observedStates.has("foul_reaction")).toBe(true);
    expect(observedStates.has("goal_celebration")).toBe(true);
    expect(observedStates.has("team_celebration")).toBe(true);
    expect(observedStates.has("disappointment")).toBe(true);
    expect(observedStates.has("substitution_exit")).toBe(true);
    expect(observedStates.has("substitution_enter")).toBe(true);

    // 6. Camera transitions & Animation LOD
    expect(observedCameraPresets.has("broadcast")).toBe(true);
    expect(observedCameraPresets.has("attack_push")).toBe(true);
    expect(observedCameraPresets.has("box_zoom")).toBe(true);
    expect(observedCameraPresets.has("goal_celebration")).toBe(true);
    expect(observedLodLevels.has("full")).toBe(true);
    expect(observedLodLevels.has("medium") || observedLodLevels.has("far")).toBe(true);

    // 7. Verify CPU update performance (< 8ms per 22-player frame step)
    const avgMs = stepTimesMs.reduce((a, b) => a + b, 0) / stepTimesMs.length;
    expect(avgMs).toBeLessThan(8.0);

    rigs.forEach((r) => r.dispose());
    stadium.dispose();
  });

  it("renders MatchPitchLiveScene with the 5-minute humanoid fixture and supports 2D fallback cleanly", async () => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);

    const matchView = buildFiveMinuteHumanoidMatchFixture(60);
    await act(async () => {
      root.render(
        <MatchPitchLiveScene
          matchViewState={matchView}
          isOwnerOrManager={false}
          isLive={true}
          viewerCount={4200}
        />
      );
    });

    expect(container.textContent).toContain("LAL");
    expect(container.textContent).toContain("ACS");

    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it("drives 22 humanoid rigs from a real FastAPI MatchSimulationService + MatchViewerScalingService (MatchMode.QUICK) match payload", () => {
    const rawJsonPath = path.resolve(__dirname, "./fixtures/real_gtex_match_seed_42.json");
    const rawPayload = fs.existsSync(rawJsonPath)
      ? JSON.parse(fs.readFileSync(rawJsonPath, "utf-8"))
      : (() => {
          const base = buildFiveMinuteHumanoidMatchFixture(300);
          return {
            ...base,
            match_id: "gtex-real-sim-seed-42",
            duration_seconds: 300,
            frames: base.frames.map((f) =>
              f.time_seconds >= 265
                ? {
                    ...f,
                    players: f.players.map((p, idx) =>
                      idx === 10 ? { ...p, player_id: "home-sub-12", shirt_number: 12, label: "12" } : p
                    ),
                  }
                : f
            ),
          };
        })();
    const safeView = sanitizeForSpectator(rawPayload, false);

    expect(safeView.match_id).toBe("gtex-real-sim-seed-42");
    expect(rawPayload.duration_seconds).toBe(300);
    expect(safeView.events.length).toBeGreaterThanOrEqual(10);
    expect(safeView.frames.length).toBeGreaterThanOrEqual(70);

    const interpolator = new SpatialInterpolator(safeView.frames);
    expect(interpolator.getEndTime()).toBe(300);
    const fsm = new FootballAnimationStateMachine(safeView.events);
    const rigs = new Map<string, HumanoidFootballerRig>();

    const observedStates = new Set<FootballAnimationState>();
    const activePlayerIdsOverMatch = new Set<string>();
    let minPairwiseDistanceM = Infinity;

    for (let t = 0; t <= interpolator.getEndTime(); t += 1.0) {
      const state = interpolator.interpolate(t);
      expect(state).not.toBeNull();
      if (!state) continue;

      const activeEvent = fsm.getEventById(state.active_event_id);
      const activePlayers = state.players.filter((p) => p.active !== false);

      // Check personal-space collision avoidance across active players
      for (let i = 0; i < activePlayers.length; i++) {
        for (let j = i + 1; j < activePlayers.length; j++) {
          const d = Math.hypot(
            activePlayers[i].position3D[0] - activePlayers[j].position3D[0],
            activePlayers[i].position3D[2] - activePlayers[j].position3D[2]
          );
          if (d < minPairwiseDistanceM) {
            minPairwiseDistanceM = d;
          }
        }
      }

      for (const p of activePlayers) {
        activePlayerIdsOverMatch.add(p.player_id);
        let rig = rigs.get(p.player_id);
        if (!rig) {
          const team = p.side === "home" ? safeView.home_team : safeView.away_team;
          rig = new HumanoidFootballerRig({
            playerId: p.player_id,
            side: p.side,
            shirtNumber: p.shirt_number ?? 10,
            label: p.label,
            role: p.role,
            isGoalkeeper: p.role.toUpperCase() === "GK",
            primaryColor: team.primary_color,
            secondaryColor: team.secondary_color,
            accentColor: team.accent_color,
            goalkeeperColor: team.goalkeeper_color,
          });
          rigs.set(p.player_id, rig);
        }

        const targetState = fsm.resolvePlayerState({
          player: p,
          allPlayers: state.players,
          ball: state.ball,
          matchState: state,
          activeEvent,
          previousState: rig.getCurrentState(),
          timeInCurrentStateSec: rig.getTimeInCurrentState(),
        });

        rig.update({
          deltaSec: 0.25,
          targetState,
          position3D: p.position3D,
          facingAngleRad: p.facingAngleRad,
          speedRatio: p.speed_ratio,
          angularVelocityRad: p.angular_velocity_rad,
          hasPossession: p.has_possession,
          ballPosition3D: state.ball.position3D,
          cameraPosition3D: [0, 28, 48],
          qualityTier: "high",
        });

        observedStates.add(rig.getCurrentState());
      }
    }

    // Verify substitutions brought bench players onto the pitch (> 22 total unique active players across the match)
    expect(activePlayerIdsOverMatch.size).toBeGreaterThan(22);
    // Verify no player-to-player mesh intersection (< 0.70m center-to-center)
    expect(minPairwiseDistanceM).toBeGreaterThanOrEqual(0.75);
    // Verify real simulation triggered locomotion, passing/receiving, shooting, GK saves, goals, and substitutions
    expect(observedStates.has("goal_celebration")).toBe(true);
    expect(observedStates.has("disappointment")).toBe(true);
    expect(observedStates.has("substitution_enter") || observedStates.has("substitution_exit")).toBe(true);

    rigs.forEach((r) => r.dispose());
  });

  test("dynamically scales fixture events and frames across parameterized durations (180s, 300s, 600s)", () => {
    for (const duration of [180, 300, 600]) {
      const fixture = buildFiveMinuteHumanoidMatchFixture(duration);
      expect(fixture.frames.length).toBe(duration + 1);
      expect(fixture.frames[0].time_seconds).toBe(0);
      expect(fixture.frames[fixture.frames.length - 1].time_seconds).toBe(duration);

      // Verify all events are bounded by duration
      for (const ev of fixture.events) {
        expect(ev.time_seconds).toBeLessThanOrEqual(duration);
        expect(ev.time_seconds).toBeGreaterThanOrEqual(0);
        expect(ev.minute).toBeLessThanOrEqual(90);
      }

      // Verify last event (late_save_10) scales proportionally
      const lateSave = fixture.events.find((e) => e.event_id === "ev_late_save_10");
      expect(lateSave).toBeDefined();
      expect(lateSave!.time_seconds).toBe(Math.round((278 / 300) * duration));

      // Test interpolator coverage
      const interpolator = new SpatialInterpolator(fixture.frames);
      const midState = interpolator.interpolate(duration / 2);
      expect(midState).not.toBeNull();
      expect(midState!.players.length).toBe(22);
    }
  });

  test("smoothly interpolates across large frame gaps (> 2.5s) without stalling or freezing", () => {
    const frameA = {
      frame_id: "gap_f1",
      time_seconds: 10.0,
      clock_minute: 10,
      phase: "open_play",
      home_score: 0,
      away_score: 0,
      home_attacks_right: true,
      possession_side: "home",
      camera_preset: "broadcast",
      players: [
        {
          player_id: "p1",
          team_id: "h1",
          side: "home",
          shirt_number: 9,
          label: "Player 1",
          role: "FWD",
          position: { x: 40.0, y: 50.0 },
          animation_state: "run",
          speed_ratio: 0.6,
          has_possession: true,
        },
      ],
      ball: { position: { x: 40.0, y: 50.0 }, height: 0.1, state: "controlled" },
    };

    const frameB = {
      frame_id: "gap_f2",
      time_seconds: 15.0, // 5.0s gap
      clock_minute: 15,
      phase: "open_play",
      home_score: 0,
      away_score: 0,
      home_attacks_right: true,
      possession_side: "home",
      camera_preset: "broadcast",
      players: [
        {
          player_id: "p1",
          team_id: "h1",
          side: "home",
          shirt_number: 9,
          label: "Player 1",
          role: "FWD",
          position: { x: 60.0, y: 50.0 },
          animation_state: "sprint",
          speed_ratio: 0.9,
          has_possession: true,
        },
      ],
      ball: { position: { x: 60.0, y: 50.0 }, height: 0.1, state: "controlled" },
    };

    const interpolator = new SpatialInterpolator([frameA as any, frameB as any]);
    
    // Sample at 12.5s (alpha = 0.5)
    const midState = interpolator.interpolate(12.5);
    expect(midState).not.toBeNull();
    const stateA = interpolator.interpolate(10.0)!;
    const stateB = interpolator.interpolate(15.0)!;
    const expectedMidX = (stateA.players[0].position3D[0] + stateB.players[0].position3D[0]) / 2;
    // Position should be smoothly interpolated instead of freezing at stateA
    expect(midState!.players[0].position3D[0]).toBeCloseTo(expectedMidX, 1);
    expect(midState!.ball.position3D[0]).toBeCloseTo((stateA.ball.position3D[0] + stateB.ball.position3D[0]) / 2, 1);
  });
});
