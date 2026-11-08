import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import * as THREE from "three";
import {
  StadiumArenaEnvironment,
  STADIUM_TIER_PROFILES,
  type StadiumTier,
} from "../StadiumArenaEnvironment";
import {
  WeatherAtmosphereSystem,
  ALL_STADIUM_WEATHER_PRESETS,
  STADIUM_WEATHER_PROFILES,
} from "../WeatherAtmosphereSystem";
import { TouchlineManagerSystem } from "../TouchlineManagerSystem";
import {
  StadiumAudioEngine,
  computePitchStereoPan,
} from "../StadiumAudioEngine";
import { BroadcastOverlayHUD } from "../BroadcastOverlayHUD";
import { CameraDirector } from "../CameraDirector";
import { SpatialInterpolator } from "../SpatialInterpolator";
import { sanitizeForSpectator } from "../spectatorContract";
import { buildFiveMinuteHumanoidMatchFixture } from "../HumanoidMatchPrototypeFixture";

describe("GTEX 3D Matchday Phase 2 Expansion — Tiered Stadiums, Weather, Touchline Managers & Spatial Audio", () => {
  describe("1. Tiered & Procedural Club Stadiums (StadiumArenaEnvironment)", () => {
    test("supports dynamic switching across Tier 1 (12.5k), Tier 2 (36k), and Tier 3 (68k) with corner towers and Mexican Wave", () => {
      const scene = new THREE.Scene();
      const arena = new StadiumArenaEnvironment(scene, {
        qualityTier: "high",
        stadiumTier: 3,
        stadiumName: "Lagos Sovereign Arena",
      });

      // Default Tier 3 Sovereign Super-Arena
      expect(arena.getStadiumTier()).toBe(3);
      expect(arena.getStadiumTierProfile().capacity).toBe(68000);
      expect(arena.getStadiumTierProfile().hasCornerTowers).toBe(true);
      expect(arena.getStadiumTierProfile().hasVipSkyboxes).toBe(true);

      // Switch to Tier 1 Community Municipal Ground
      arena.setStadiumTier(1);
      expect(arena.getStadiumTier()).toBe(1);
      expect(arena.getStadiumTierProfile().tierKey).toBe("tier_1_community");
      expect(arena.getStadiumTierProfile().capacity).toBe(12500);
      expect(arena.getStadiumTierProfile().hasUpperTiers).toBe(false);
      expect(arena.getStadiumTierProfile().hasCornerTowers).toBe(false);

      // Switch to Tier 2 Regional Championship Arena
      arena.setStadiumTier(2);
      expect(arena.getStadiumTier()).toBe(2);
      expect(arena.getStadiumTierProfile().tierKey).toBe("tier_2_regional");
      expect(arena.getStadiumTierProfile().capacity).toBe(36000);
      expect(arena.getStadiumTierProfile().hasUpperTiers).toBe(true);
      expect(arena.getStadiumTierProfile().hasVipSkyboxes).toBe(false);

      // Trigger radial Mexican Wave across the supporter stands
      arena.setStadiumTier(3);
      arena.triggerCrowdWave();
      expect(arena.getCrowdReactionState().waveActive).toBe(true);

      // Advance simulation and verify wave remains active then settles cleanly
      arena.update(1.0, 10.0);
      expect(arena.getCrowdReactionState().waveActive).toBe(true);
      arena.update(8.0, 18.0);
      expect(arena.getCrowdReactionState().waveActive).toBe(false);

      // Verify pitch materials are exposed for weather surface binding
      const pitchMats = arena.getPitchMaterials();
      expect(pitchMats.pitchTurfMat).not.toBeNull();
      expect(pitchMats.pitchRunoffMat).not.toBeNull();

      arena.dispose();
    });
  });

  describe("2. Dynamic Weather & Atmospherics (WeatherAtmosphereSystem)", () => {
    test("transitions cleanly across all 6 weather presets, scales particles by quality tier, and updates particles in-place", () => {
      const scene = new THREE.Scene();
      const hemiLight = new THREE.HemisphereLight(0xdbeafe, 0x1e5631, 1.15);
      const keyLight = new THREE.DirectionalLight(0xffffff, 1.35);
      const fillLight = new THREE.DirectionalLight(0xf1f5f9, 0.72);
      const turfMat = new THREE.MeshLambertMaterial({ color: 0x154726 });
      const runoffMat = new THREE.MeshLambertMaterial({ color: 0x0e361b });

      const weather = new WeatherAtmosphereSystem(scene, {
        initialPreset: "clear_night",
        qualityTier: "high",
        hemiLight,
        keyLight,
        fillLight,
      });
      weather.bindPitchMaterials(turfMat, runoffMat);

      expect(ALL_STADIUM_WEATHER_PRESETS).toEqual([
        "clear_night",
        "clear_day",
        "rain",
        "heavy_rain",
        "snow",
        "mist",
      ]);

      // Clear night has 0 active precipitation particles
      expect(weather.getPreset()).toBe("clear_night");
      expect(weather.getTelemetry().activeParticleCount).toBe(0);
      expect(weather.particlePoints.visible).toBe(false);

      // Switch to heavy_rain and verify precipitation particles, wetness, and floodlight cones
      weather.setPreset("heavy_rain");
      const heavyRainTelemetry = weather.getTelemetry();
      expect(heavyRainTelemetry.preset).toBe("heavy_rain");
      expect(heavyRainTelemetry.activeParticleCount).toBe(
        STADIUM_WEATHER_PROFILES.heavy_rain.particleCountHigh
      );
      expect(heavyRainTelemetry.pitchWetness).toBeGreaterThan(0.8);
      expect(weather.particlePoints.visible).toBe(true);

      // Verify in-place particle buffer update on frame tick
      const posAttr = weather.particlePoints.geometry.getAttribute(
        "position"
      ) as THREE.BufferAttribute;
      const initialY0 = posAttr.array[1];
      weather.update(0.1);
      const nextY0 = posAttr.array[1];
      expect(nextY0).not.toBe(initialY0);

      // Verify quality tier scaling (low < medium < high)
      weather.setQualityTier("medium");
      expect(weather.getTelemetry().activeParticleCount).toBe(
        STADIUM_WEATHER_PROFILES.heavy_rain.particleCountMedium
      );
      weather.setQualityTier("low");
      expect(weather.getTelemetry().activeParticleCount).toBe(
        STADIUM_WEATHER_PROFILES.heavy_rain.particleCountLow
      );

      // Switch to snow and verify frost overlay
      weather.setQualityTier("high");
      weather.setPreset("snow");
      expect(weather.getTelemetry().pitchFrost).toBeGreaterThan(0.5);
      weather.update(0.1);

      // Switch to clear_day and mist
      weather.setPreset("clear_day");
      expect(weather.getTelemetry().activeParticleCount).toBe(0);
      weather.setPreset("mist");
      expect(weather.getTelemetry().floodlightConeOpacity).toBeGreaterThan(0.2);

      weather.dispose();
      turfMat.dispose();
      runoffMat.dispose();
    });
  });

  describe("3. 3D Manager & Touchline Bench (TouchlineManagerSystem)", () => {
    test("positions Home and Away 3D humanoid managers in FIFA technical areas and drives event-based touchline reactions", () => {
      const fixture = buildFiveMinuteHumanoidMatchFixture(60);
      const safeView = sanitizeForSpectator(fixture, false);
      const scene = new THREE.Scene();

      const managers = new TouchlineManagerSystem(scene, {
        homeTeam: safeView.home_team,
        awayTeam: safeView.away_team,
        qualityTier: "high",
      });

      const initialSummary = managers.getSummary();
      expect(initialSummary.homeManagerPosition[0]).toBeLessThan(-10);
      expect(initialSummary.awayManagerPosition[0]).toBeGreaterThan(10);
      expect(initialSummary.benchSubstituteCount).toBe(12);
      expect(initialSummary.fourthOfficialBoardActive).toBe(false);

      // Home goal: Home manager celebrates, Away manager reacts with frustration
      managers.triggerEventReaction("goal", "home");
      const homeGoalSummary = managers.getSummary();
      expect(homeGoalSummary.homeManagerState).toBe("celebrating_goal");
      expect(homeGoalSummary.awayManagerState).toBe("frustrated_reaction");

      // Away goal: Away manager celebrates, Home manager reacts with frustration
      managers.triggerEventReaction("goal", "away");
      const awayGoalSummary = managers.getSummary();
      expect(awayGoalSummary.awayManagerState).toBe("celebrating_goal");
      expect(awayGoalSummary.homeManagerState).toBe("frustrated_reaction");

      // Red card / VAR decision: Managers protest toward 4th official
      managers.triggerEventReaction("red_card", "home");
      expect(managers.getSummary().homeManagerState).toBe("protesting_decision");

      // Substitution activates 4th official LED board
      managers.triggerEventReaction("substitution", "both");
      expect(managers.getSummary().fourthOfficialBoardActive).toBe(true);

      // Live tactical config change triggers touchline tactical instruction
      managers.notifyTacticalChange("home");
      expect(managers.getSummary().homeManagerState).toBe("tactical_instruction");

      // Advance frame updates and verify finite positions & skeletal rig updates
      managers.update({
        deltaSec: 0.25,
        ballPosition3D: [12, 0.2, 8],
        cameraPosition3D: [0, 24, 52],
        possessionSide: "home",
        qualityTier: "high",
      });

      const updatedSummary = managers.getSummary();
      expect(Number.isFinite(updatedSummary.homeManagerPosition[0])).toBe(true);
      expect(Number.isFinite(updatedSummary.awayManagerPosition[0])).toBe(true);

      managers.dispose();
    });
  });

  describe("4. Reactive 3D Crowd & Spatial Audio (StadiumAudioEngine)", () => {
    test("computes stereo panning across the 105m pitch and tracks spatial ball kicks, whistles, and crowd roars", () => {
      expect(computePitchStereoPan(-52.5)).toBeCloseTo(-0.88, 2);
      expect(computePitchStereoPan(0)).toBeCloseTo(0, 4);
      expect(computePitchStereoPan(52.5)).toBeCloseTo(0.88, 2);

      const audio = new StadiumAudioEngine({ initialMuted: false });
      expect(audio.isMuted()).toBe(false);

      audio.updateCrowdAmbience(0.75);
      expect(audio.getTelemetry().ambientIntensity).toBeCloseTo(0.705, 2);

      audio.playBallKick([-26.25, 0.2, 10], 0.9);
      expect(audio.getTelemetry().lastTriggeredSound).toBe("ball_kick");
      expect(audio.getTelemetry().lastStereoPan).toBeLessThan(-0.4);

      audio.playRefereeWhistle("kickoff");
      expect(audio.getTelemetry().lastTriggeredSound).toBe("whistle_kickoff");

      audio.handleMatchEvent("goal", "home", [48, 0.5, 0]);
      expect(audio.getTelemetry().lastTriggeredSound).toBe("goal_roar");
      expect(audio.getTelemetry().triggeredSoundCount).toBe(3);

      audio.handleMatchEvent("save", "both", [-49, 1.2, 2]);
      expect(audio.getTelemetry().lastTriggeredSound).toBe("crowd_gasp");

      audio.handleMatchEvent("attack", "away", [25, 0.2, -12]);
      expect(audio.getTelemetry().lastTriggeredSound).toBe("chant_pulse");

      audio.dispose();
    });
  });

  describe("5. BroadcastOverlayHUD & CameraDirector Phase 2 Controls", () => {
    let container: HTMLDivElement;
    let root: Root;

    beforeEach(() => {
      (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
      container = document.createElement("div");
      document.body.appendChild(container);
      root = createRoot(container);
    });

    afterEach(() => {
      act(() => {
        root.unmount();
      });
      container.remove();
    });

    test("renders Stadium Tier selector, Weather Preset selector, and Dugout Camera button", async () => {
      const fixture = buildFiveMinuteHumanoidMatchFixture(60);
      const safeView = sanitizeForSpectator(fixture, false);
      const interpolator = new SpatialInterpolator(safeView.frames);
      const state = interpolator.interpolate(10);

      const onSelectStadiumTier = jest.fn();
      const onSelectWeatherPreset = jest.fn();
      const onSelectCameraMode = jest.fn();

      await act(async () => {
        root.render(
          <BroadcastOverlayHUD
            matchState={state}
            homeTeam={safeView.home_team}
            awayTeam={safeView.away_team}
            matchLabel={safeView.match_label}
            cameraMode="director_auto"
            onSelectCameraMode={onSelectCameraMode}
            onToggle2DFallback={jest.fn()}
            stadiumTier={3}
            onSelectStadiumTier={onSelectStadiumTier}
            weatherPreset="clear_night"
            onSelectWeatherPreset={onSelectWeatherPreset}
          />
        );
      });

      const tier1Btn = container.querySelector(
        "[data-testid='stadium-tier-1']"
      ) as HTMLButtonElement;
      const tier2Btn = container.querySelector(
        "[data-testid='stadium-tier-2']"
      ) as HTMLButtonElement;
      const rainBtn = container.querySelector(
        "[data-testid='weather-preset-rain']"
      ) as HTMLButtonElement;
      const snowBtn = container.querySelector(
        "[data-testid='weather-preset-snow']"
      ) as HTMLButtonElement;
      const dugoutCamBtn = container.querySelector(
        "[data-testid='camera-mode-dugout_cam']"
      ) as HTMLButtonElement;

      expect(tier1Btn).not.toBeNull();
      expect(tier2Btn).not.toBeNull();
      expect(rainBtn).not.toBeNull();
      expect(snowBtn).not.toBeNull();
      expect(dugoutCamBtn).not.toBeNull();

      await act(async () => {
        tier1Btn.click();
        rainBtn.click();
        dugoutCamBtn.click();
      });

      expect(onSelectStadiumTier).toHaveBeenCalledWith(1);
      expect(onSelectWeatherPreset).toHaveBeenCalledWith("rain");
      expect(onSelectCameraMode).toHaveBeenCalledWith("dugout_cam");

      // Verify CameraDirector dugout_cam frames the technical area cleanly
      const director = new CameraDirector();
      director.setManualMode("dugout_cam");
      const pose = director.update(0.5, "broadcast", [0, 0.2, 0]);
      expect(director.getManualMode()).toBe("dugout_cam");
      expect(pose.position[2]).toBeGreaterThan(30);
    });
  });
});
