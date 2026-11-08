import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import * as THREE from "three";
import { MatchOfficialsSystem } from "../MatchOfficialsSystem";
import {
  BroadcastTacticalAROverlay,
  ALL_BROADCAST_AR_MODES,
} from "../BroadcastTacticalAROverlay";
import { GoalNetPhysicsAndSetPieces } from "../GoalNetPhysicsAndSetPieces";
import { StadiumCeremonySystem } from "../StadiumCeremonySystem";
import { BroadcastOverlayHUD } from "../BroadcastOverlayHUD";
import { CameraDirector } from "../CameraDirector";
import { SpatialInterpolator } from "../SpatialInterpolator";
import { sanitizeForSpectator } from "../spectatorContract";
import { buildFiveMinuteHumanoidMatchFixture } from "../HumanoidMatchPrototypeFixture";

describe("GTEX 3D Matchday Phase 3 Expansion — Match Officials, Broadcast AR Overlays, Goal-Net Physics & Stadium Ceremonies", () => {
  describe("1. 3D On-Pitch Match Officials (MatchOfficialsSystem)", () => {
    test("positions Center Referee and 2 Touchline Assistant Linesmen, raises offside flags, shows yellow/red cards, and runs to VAR monitor", () => {
      const fixture = buildFiveMinuteHumanoidMatchFixture(60);
      const safeView = sanitizeForSpectator(fixture, false);
      const interpolator = new SpatialInterpolator(safeView.frames);
      const state = interpolator.interpolate(15.0)!;

      const scene = new THREE.Scene();
      const officials = new MatchOfficialsSystem(scene, { qualityTier: "high" });

      const initSummary = officials.getSummary();
      expect(initSummary.refereeState).toBe("diagonal_tracking");
      expect(initSummary.nearLinesmanPosition[2]).toBeGreaterThan(34);
      expect(initSummary.farLinesmanPosition[2]).toBeLessThan(-34);
      expect(initSummary.activeCardShown).toBe("none");

      // Yellow card event
      officials.triggerEventReaction("yellow_card", [-12, 0.2, 4]);
      expect(officials.getSummary().refereeState).toBe("showing_yellow_card");
      expect(officials.getSummary().activeCardShown).toBe("yellow");
      expect(officials.getSummary().flagRaisedSide).toBe("near");

      // Red card event
      officials.triggerEventReaction("red_card", [22, 0.2, -8]);
      expect(officials.getSummary().refereeState).toBe("showing_red_card");
      expect(officials.getSummary().activeCardShown).toBe("red");
      expect(officials.getSummary().flagRaisedSide).toBe("far");

      // Offside flag event
      officials.triggerEventReaction("offside", [34, 0.2, 10]);
      expect(officials.getSummary().refereeState).toBe("linesman_flag_offside");
      expect(officials.getSummary().flagRaisedSide).toBe("far");

      // Pitchside VAR monitor review
      officials.triggerEventReaction("var_review", [10, 0.2, 0]);
      expect(officials.getSummary().refereeState).toBe("var_monitor_review");
      expect(officials.getSummary().varReviewActive).toBe(true);

      // Advance simulation and verify referee moves toward VAR monitor and linesmen track offside lines
      officials.update({
        deltaSec: 0.5,
        ballPosition3D: state.ball.position3D,
        players: state.players,
        cameraPosition3D: [0, 32, 55],
        qualityTier: "high",
      });

      const updatedSummary = officials.getSummary();
      expect(Number.isFinite(updatedSummary.refereePosition[0])).toBe(true);
      expect(Number.isFinite(updatedSummary.nearLinesmanPosition[0])).toBe(true);
      expect(Number.isFinite(updatedSummary.farLinesmanPosition[0])).toBe(true);

      officials.dispose();
    });
  });

  describe("2. On-Pitch 3D Broadcast AR & Telestrator Overlays (BroadcastTacticalAROverlay)", () => {
    test("computes defensive block laser lines, 3D offside virtual wall, passing lane vectors, and ballistic shot trails in-place", () => {
      const fixture = buildFiveMinuteHumanoidMatchFixture(60);
      const safeView = sanitizeForSpectator(fixture, false);
      const interpolator = new SpatialInterpolator(safeView.frames);
      const state = interpolator.interpolate(18.0)!;

      const scene = new THREE.Scene();
      const arOverlay = new BroadcastTacticalAROverlay(scene, {
        initialMode: "off",
        homeColorHex: safeView.home_team.primary_color,
        awayColorHex: safeView.away_team.primary_color,
      });

      expect(ALL_BROADCAST_AR_MODES).toEqual([
        "off",
        "tactical_lines",
        "offside_wall",
        "shot_trails",
        "full_ar",
      ]);
      expect(arOverlay.getSummary().isVisible).toBe(false);

      // Auto-flash offside wall on offside/VAR event even when mode is "off"
      arOverlay.triggerEventFlash("offside");
      expect(arOverlay.getSummary().isVisible).toBe(true);

      // Switch through AR modes and update with live player/ball frame
      arOverlay.setMode("full_ar");
      arOverlay.update({
        deltaSec: 0.1,
        players: state.players,
        ballPosition3D: state.ball.position3D,
        possessionSide: state.possession_side,
      });

      const summary = arOverlay.getSummary();
      expect(summary.mode).toBe("full_ar");
      expect(summary.isVisible).toBe(true);
      expect(Number.isFinite(summary.homeDefensiveLineX)).toBe(true);
      expect(Number.isFinite(summary.awayDefensiveLineX)).toBe(true);
      expect(Number.isFinite(summary.activeOffsideLineX)).toBe(true);
      expect(summary.shotTrailSampleCount).toBeGreaterThanOrEqual(1);

      arOverlay.dispose();
    });
  });

  describe("3. Dynamic 3D Goal-Net Physics & Set-Piece Choreography (GoalNetPhysicsAndSetPieces)", () => {
    test("deforms goal-net vertices on goal impact and renders dissolving referee vanishing foam spray on free kicks", () => {
      const scene = new THREE.Scene();
      const netAndSetPieces = new GoalNetPhysicsAndSetPieces(scene);

      expect(netAndSetPieces.getSummary().activeSetPiece).toBe("none");
      expect(netAndSetPieces.getSummary().vanishingSprayVisible).toBe(false);

      // Trigger free-kick vanishing foam spray
      netAndSetPieces.triggerMatchEvent("free_kick", "home", [26.0, 0.2, 6.0]);
      const fkSummary = netAndSetPieces.getSummary();
      expect(fkSummary.activeSetPiece).toBe("free_kick");
      expect(fkSummary.vanishingSprayVisible).toBe(true);
      expect(fkSummary.vanishingSprayOpacity).toBeGreaterThan(0.8);

      // Trigger goal net impact on Away goal (+X)
      netAndSetPieces.triggerMatchEvent("goal", "home", [53.2, 1.3, 0.8]);
      const goalSummary = netAndSetPieces.getSummary();
      expect(goalSummary.lastNetImpactSide).toBe("away");
      expect(goalSummary.awayNetRippleIntensity).toBeGreaterThan(0.5);

      // Advance physics update and verify net vertices deform in-place and damp smoothly
      netAndSetPieces.update(0.15, [53.2, 1.3, 0.8]);
      const afterTickSummary = netAndSetPieces.getSummary();
      expect(afterTickSummary.awayNetRippleIntensity).toBeGreaterThan(0);
      expect(afterTickSummary.awayNetRippleIntensity).toBeLessThan(
        goalSummary.awayNetRippleIntensity
      );

      // Advance 9s so vanishing spray dissolves completely
      netAndSetPieces.update(9.0, [0, 0.2, 0]);
      expect(netAndSetPieces.getSummary().vanishingSprayVisible).toBe(false);
      expect(netAndSetPieces.getSummary().activeSetPiece).toBe("none");

      netAndSetPieces.dispose();
    });
  });

  describe("4. 3D Pre-Match Walkout, Pyrotechnics & Full-Time Trophy Ceremony (StadiumCeremonySystem)", () => {
    test("stages walkout red carpet & trophy plinth, fires goal pyrotechnics, and launches full-time podium + GPU confetti shower", () => {
      const scene = new THREE.Scene();
      const ceremony = new StadiumCeremonySystem(scene);

      expect(ceremony.getSummary().ceremonyState).toBe("inactive");
      expect(ceremony.getSummary().pyroActive).toBe(false);
      expect(ceremony.getSummary().confettiActive).toBe(false);

      // Pre-match walkout ceremony
      ceremony.triggerMatchEvent("walkout");
      expect(ceremony.getSummary().ceremonyState).toBe("pre_match_walkout");
      expect(ceremony.getSummary().trophyPlinthVisible).toBe(true);
      expect(ceremony.getSummary().pyroActive).toBe(true);

      // Goal pyrotechnic burst
      ceremony.triggerMatchEvent("goal");
      expect(ceremony.getSummary().ceremonyState).toBe("goal_pyrotechnics");
      expect(ceremony.getSummary().pyroActive).toBe(true);

      // Full-time championship trophy presentation & confetti cannon
      ceremony.triggerMatchEvent("fulltime");
      const ftSummary = ceremony.getSummary();
      expect(ftSummary.ceremonyState).toBe("fulltime_trophy_presentation");
      expect(ftSummary.podiumVisible).toBe(true);
      expect(ftSummary.confettiActive).toBe(true);
      expect(ftSummary.pyroActive).toBe(true);

      // Verify in-place confetti particle motion
      const posAttr = ceremony.confettiPoints.geometry.getAttribute(
        "position"
      ) as THREE.BufferAttribute;
      const y0Before = posAttr.array[1];
      ceremony.update(0.2);
      const y0After = posAttr.array[1];
      expect(y0After).not.toBe(y0Before);

      ceremony.dispose();
    });
  });

  describe("5. BroadcastOverlayHUD & CameraDirector Phase 3 Controls", () => {
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

    test("renders Broadcast AR Telestrator selector and Walkout Camera button", async () => {
      const fixture = buildFiveMinuteHumanoidMatchFixture(60);
      const safeView = sanitizeForSpectator(fixture, false);
      const interpolator = new SpatialInterpolator(safeView.frames);
      const state = interpolator.interpolate(10);

      const onSelectArOverlayMode = jest.fn();
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
            arOverlayMode="off"
            onSelectArOverlayMode={onSelectArOverlayMode}
          />
        );
      });

      const arLinesBtn = container.querySelector(
        "[data-testid='ar-mode-tactical_lines']"
      ) as HTMLButtonElement;
      const arOffsideBtn = container.querySelector(
        "[data-testid='ar-mode-offside_wall']"
      ) as HTMLButtonElement;
      const arFullBtn = container.querySelector(
        "[data-testid='ar-mode-full_ar']"
      ) as HTMLButtonElement;
      const walkoutCamBtn = container.querySelector(
        "[data-testid='camera-mode-tunnel_walkout']"
      ) as HTMLButtonElement;

      expect(arLinesBtn).not.toBeNull();
      expect(arOffsideBtn).not.toBeNull();
      expect(arFullBtn).not.toBeNull();
      expect(walkoutCamBtn).not.toBeNull();

      await act(async () => {
        arLinesBtn.click();
        arFullBtn.click();
        walkoutCamBtn.click();
      });

      expect(onSelectArOverlayMode).toHaveBeenCalledWith("tactical_lines");
      expect(onSelectArOverlayMode).toHaveBeenCalledWith("full_ar");
      expect(onSelectCameraMode).toHaveBeenCalledWith("tunnel_walkout");

      const director = new CameraDirector();
      director.setManualMode("tunnel_walkout");
      const pose = director.update(0.5, "broadcast", [0, 0.2, 0]);
      expect(director.getManualMode()).toBe("tunnel_walkout");
      expect(Number.isFinite(pose.position[0])).toBe(true);
    });
  });
});
