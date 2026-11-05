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
});
