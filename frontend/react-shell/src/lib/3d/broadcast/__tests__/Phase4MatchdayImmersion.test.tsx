import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import * as THREE from "three";
import {
  ReplayDirectorStudio,
  ReplayStudioAngle,
} from "../ReplayDirectorStudio";
import { PitchTurfDegradationSystem } from "../PitchTurfDegradationSystem";
import { StadiumTifoAndJumbotronSystem } from "../StadiumTifoAndJumbotronSystem";
import { SpectatorImmersionLayer } from "../SpectatorImmersionLayer";
import { BroadcastOverlayHUD } from "../BroadcastOverlayHUD";
import { SpatialInterpolator } from "../SpatialInterpolator";
import { sanitizeForSpectator } from "../spectatorContract";
import { buildFiveMinuteHumanoidMatchFixture } from "../HumanoidMatchPrototypeFixture";

describe("GTEX 3D Matchday Phase 4 — Cinematic Replay Studio, Dynamic Turf Wear & Spectator Immersion", () => {
  describe("1. Action Replay Director & Multi-Angle Camera Studio (ReplayDirectorStudio)", () => {
    test("computes camera poses across all 5 replay angles with smooth orbit and slow-mo rate control", () => {
      const studio = new ReplayDirectorStudio({
        initialAngle: "orbit_360",
        playbackRate: 0.5,
      });

      expect(studio.getReplayAngle()).toBe("orbit_360");
      expect(studio.getPlaybackRate()).toBe(0.5);
      expect(studio.getIsReplayActive()).toBe(false);

      studio.setReplayActive(true);
      expect(studio.getIsReplayActive()).toBe(true);

      const angles: ReplayStudioAngle[] = [
        "orbit_360",
        "reverse_angle_pov",
        "spidercam_overhead",
        "goal_line_freeze",
        "wirecam_tracking",
      ];

      for (const angle of angles) {
        studio.setReplayAngle(angle);
        expect(studio.getReplayAngle()).toBe(angle);

        const pose = studio.computeReplayPose(
          0.016,
          0.5,
          [48.0, 1.2, 8.0],
          [46.5, 0.0, 7.5]
        );

        expect(Number.isFinite(pose.position[0])).toBe(true);
        expect(Number.isFinite(pose.position[1])).toBe(true);
        expect(Number.isFinite(pose.position[2])).toBe(true);
        expect(Number.isFinite(pose.target[0])).toBe(true);
        expect(Number.isFinite(pose.fov)).toBe(true);
        expect(pose.fov).toBeGreaterThan(15);
        expect(pose.fov).toBeLessThan(75);
      }

      // Record bookmarks
      studio.recordBookmark({
        eventId: "evt_test_goal",
        eventType: "goal",
        timestampSec: 72.5,
        clockMinute: 48,
        ballPosition: [52.0, 1.8, 0.2],
        primaryActorPosition: [46.0, 0.0, 1.0],
        primaryActorName: "Player 9",
        recommendedAngle: "orbit_360",
        summaryText: "GOAL! Sensational strike!",
      });

      expect(studio.getBookmarks().length).toBe(1);
      expect(studio.getLatestBookmark()?.eventType).toBe("goal");

      const summary = studio.getSummary();
      expect(summary.totalBookmarks).toBe(1);
      expect(summary.isReplayActive).toBe(true);

      studio.dispose();
      expect(studio.getBookmarks().length).toBe(0);
    });

    test("retains a rolling 22-player spatial transform buffer, offers two alternate angles, and computes tactical freeze-frames", () => {
      const studio = new ReplayDirectorStudio({ maxSpatialFrames: 60 });

      for (let step = 0; step < 5; step++) {
        studio.recordSpatialFrame({
          timestampSec: 10 + step * 0.5,
          clockMinute: 12,
          possessionSide: "home",
          ball: {
            position3D: [20 + step * 5, 0.2 * step, -2],
            height: 0.2 * step,
            state: "pass",
            owner_player_id: "h-10",
          },
          players: [
            {
              player_id: "h-10",
              team_id: "home",
              side: "home",
              shirt_number: 10,
              label: "Bellingham",
              role: "AM",
              position3D: [20 + step * 4, 0, -2],
              facingAngleRad: 0,
              animation_state: "pass",
              speed_ratio: 0.6,
              has_possession: true,
            },
            {
              player_id: "h-9",
              team_id: "home",
              side: "home",
              shirt_number: 9,
              label: "Osimhen",
              role: "ST",
              position3D: [32 + step * 3, 0, 4],
              facingAngleRad: 0,
              animation_state: "run",
              speed_ratio: 0.8,
              has_possession: false,
            },
            {
              player_id: "a-4",
              team_id: "away",
              side: "away",
              shirt_number: 4,
              label: "Van Dijk",
              role: "CB",
              position3D: [38, 0, -4],
              facingAngleRad: Math.PI,
              animation_state: "jog",
              speed_ratio: 0.4,
              has_possession: false,
            },
            {
              player_id: "a-5",
              team_id: "away",
              side: "away",
              shirt_number: 5,
              label: "Araujo",
              role: "CB",
              position3D: [39, 0, 6],
              facingAngleRad: Math.PI,
              animation_state: "jog",
              speed_ratio: 0.4,
              has_possession: false,
            },
          ],
        });
      }

      expect(studio.getSpatialBufferLength()).toBe(5);

      const sampledMid = studio.sampleReplayFrame(0.5);
      expect(sampledMid).not.toBeNull();
      expect(sampledMid?.ball.position3D[0]).toBeCloseTo(30, 1);
      expect(sampledMid?.players.length).toBe(4);

      const angleSelection = studio.selectAnglesForEvent("goal");
      expect(angleSelection.primaryAngle).toBe("reverse_angle_pov");
      expect(angleSelection.alternateAngles).toHaveLength(2);

      const freeze = studio.computeTacticalFreezeFrame();
      expect(freeze).not.toBeNull();
      expect(freeze?.offsideLineX).toBeCloseTo(38.5, 1);
      expect(freeze?.passLane?.recipientId).toBe("h-9");
      expect(freeze?.shotVector?.estimatedXg).toBeGreaterThan(0);
      expect(freeze?.defensiveShapePolygon).toHaveLength(2);
    });
  });

  describe("2. Dynamic Pitch Turf Degradation & Ball Water Spray (PitchTurfDegradationSystem)", () => {
    test("accumulates 90-minute goalmouth wear, records slide-tackle divots, and emits wet-turf spray particles", () => {
      const scene = new THREE.Scene();
      const turf = new PitchTurfDegradationSystem(scene, {
        maxDivots: 16,
        maxSprayParticles: 32,
      });

      const initialSummary = turf.getSummary();
      expect(initialSummary.activeDivotCount).toBe(0);
      expect(initialSummary.accumulatedWearFactor).toBe(0.0);
      expect(initialSummary.goalmouthWearOpacity).toBe(0.0);

      // Add slide-tackle divots
      turf.addSlideTackleDivot(-14.2, 8.5, Math.PI / 4);
      turf.addSlideTackleDivot(22.0, -12.4, -Math.PI / 3);
      expect(turf.getDivotCount()).toBe(2);
      expect(turf.getSummary().activeDivotCount).toBe(2);

      // Advance clock to 75 minutes in rainy conditions
      turf.update({
        deltaSec: 0.1,
        clockMinute: 75,
        weatherPreset: "rain",
        ballPosition3D: [12.0, 0.1, -4.0],
        ballVelocity: [8.5, 0.0, 2.0],
      });

      const rainSummary = turf.getSummary();
      expect(rainSummary.accumulatedWearFactor).toBeGreaterThan(0.5);
      expect(rainSummary.goalmouthWearOpacity).toBeGreaterThan(0.0);
      expect(rainSummary.isWetTurfActive).toBe(true);
      expect(rainSummary.activeSprayParticleCount).toBeGreaterThanOrEqual(1);

      // Advance clock in dry weather
      turf.update({
        deltaSec: 0.5,
        clockMinute: 90,
        weatherPreset: "clear_day",
        ballPosition3D: [0.0, 0.0, 0.0],
        ballVelocity: [0.0, 0.0, 0.0],
      });

      const drySummary = turf.getSummary();
      expect(drySummary.isWetTurfActive).toBe(false);
      expect(drySummary.accumulatedWearFactor).toBe(1.0);

      turf.dispose();
    });
  });

  describe("3. Stadium Jumbotrons & Ultras Supporter Tifo (StadiumTifoAndJumbotronSystem)", () => {
    test("renders jumbotron displays with score/clock, flashes alerts, and animates supporter tifo choreography", () => {
      const scene = new THREE.Scene();
      const tifoSystem = new StadiumTifoAndJumbotronSystem(scene, {
        homeShortName: "HOM",
        awayShortName: "AWY",
        homeColorHex: "#10b981",
        awayColorHex: "#06b6d4",
        competitionName: "GTEX CUP FINAL",
      });

      const initialSummary = tifoSystem.getSummary();
      expect(initialSummary.tifoState).toBe("hidden");
      expect(initialSummary.tifoProgress).toBe(0.0);
      expect(initialSummary.jumbotronAlertActive).toBe(false);

      // Trigger jumbotron alert
      tifoSystem.triggerJumbotronFlash("GOAL!", "#10b981", 6);
      expect(tifoSystem.getSummary().jumbotronAlertActive).toBe(true);
      expect(tifoSystem.getSummary().jumbotronAlertText).toBe("GOAL!");

      // Trigger supporter tifo banner unfurling
      tifoSystem.triggerTifo("VICTORY AND HONOR", 5);
      expect(tifoSystem.getSummary().tifoState).toBe("unfurling");

      // Advance animation through unfurling to displayed
      tifoSystem.update(1.2, {
        homeScore: 1,
        awayScore: 0,
        clockMinute: 52,
      });

      expect(tifoSystem.getSummary().tifoState).toBe("displayed");
      expect(tifoSystem.getSummary().tifoProgress).toBe(1.0);
      expect(tifoSystem.getSummary().scoreText).toBe("1 - 0");
      expect(tifoSystem.getSummary().clockText).toBe("52'");

      // Advance past tifo hold duration to trigger furling
      tifoSystem.update(5.5, {
        homeScore: 1,
        awayScore: 0,
        clockMinute: 53,
      });
      expect(tifoSystem.getSummary().tifoState).toBe("furling");

      tifoSystem.dispose();
    });
  });

  describe("4. Spectator Immersion Layer (SpectatorImmersionLayer)", () => {
    test("handles match events with commentary cues, watch-party emoji reaction bursts, and haptic feedback", () => {
      const immersion = new SpectatorImmersionLayer({
        hapticsEnabled: true,
        watchPartyRoomSize: 48,
      });

      expect(immersion.isHapticsEnabled()).toBe(true);
      expect(immersion.getSummary().watchPartyRoomSize).toBe(48);
      expect(immersion.getCurrentCommentaryCue()).toBeNull();

      // Goal event triggers celebratory commentary and reactions
      immersion.handleMatchEvent("goal", "home", { playerName: "Player 9" });
      const cue = immersion.getCurrentCommentaryCue();
      expect(cue).not.toBeNull();
      expect(cue?.tone).toBe("celebratory");
      expect(cue?.intensity).toBe(1.0);
      expect(cue?.text).toContain("Player 9");

      // Spectator reaction items
      expect(immersion.getRecentReactions().length).toBeGreaterThanOrEqual(2);
      expect(immersion.getSummary().cheerMeter).toBe(100);

      // User sends a reaction
      immersion.sendReaction("🔥", "Alex");
      const recent = immersion.getRecentReactions();
      expect(recent.some((r) => r.emoji === "🔥")).toBe(true);

      // Toggle haptics
      immersion.setHapticsEnabled(false);
      expect(immersion.isHapticsEnabled()).toBe(false);

      // Advance time to decay reactions
      immersion.update(3.0);
      expect(immersion.getRecentReactions().length).toBe(0);

      immersion.dispose();
      expect(immersion.getCurrentCommentaryCue()).toBeNull();
    });
  });

  describe("5. BroadcastOverlayHUD Phase 4 Integration", () => {
    let container: HTMLDivElement | null = null;
    let root: Root | null = null;

    beforeEach(() => {
      container = document.createElement("div");
      document.body.appendChild(container);
      root = createRoot(container);
    });

    afterEach(() => {
      if (root) {
        act(() => {
          root?.unmount();
        });
      }
      if (container && container.parentNode) {
        container.parentNode.removeChild(container);
      }
    });

    test("renders Replay Studio angle selector, commentary subtitle ticker, watch-party cheer meter, and reaction bar", () => {
      const fixture = buildFiveMinuteHumanoidMatchFixture(60);
      const safeView = sanitizeForSpectator(fixture, false);
      const interpolator = new SpatialInterpolator(safeView.frames);
      const state = interpolator.interpolate(25.0)!;

      const onSelectAngleMock = jest.fn();
      const onToggleHapticsMock = jest.fn();
      const onSendReactionMock = jest.fn();

      act(() => {
        root!.render(
          <BroadcastOverlayHUD
            matchState={state}
            homeTeam={safeView.home_team}
            awayTeam={safeView.away_team}
            matchLabel={safeView.match_label}
            competitionName={safeView.competition_name}
            cameraMode="director_auto"
            onSelectCameraMode={() => {}}
            onToggle2DFallback={() => {}}
            isReplayActive={true}
            replayStudioAngle="orbit_360"
            onSelectReplayStudioAngle={onSelectAngleMock}
            commentaryCue={{
              id: "comm_1",
              speaker: "Peter Drury AI",
              text: "Brilliant build-up play slicing through the defense!",
              tone: "celebratory",
              intensity: 0.9,
              remainingSec: 5.0,
            }}
            spectatorReactions={[
              {
                id: "rx_1",
                emoji: "🔥",
                senderName: "User",
                xPct: 50,
                remainingSec: 2.5,
              },
            ]}
            watchPartyCheerMeter={78}
            hapticsEnabled={true}
            onToggleHaptics={onToggleHapticsMock}
            onSendReaction={onSendReactionMock}
          />
        );
      });

      // 1. Replay Studio Angle Selector
      const angleSelector = container!.querySelector("[data-testid='replay-studio-angle-selector']");
      expect(angleSelector).not.toBeNull();
      const orbitBtn = container!.querySelector("[data-testid='replay-angle-orbit_360']") as HTMLButtonElement;
      const spiderBtn = container!.querySelector("[data-testid='replay-angle-spidercam_overhead']") as HTMLButtonElement;
      expect(orbitBtn).not.toBeNull();
      expect(spiderBtn).not.toBeNull();

      act(() => {
        spiderBtn.click();
      });
      expect(onSelectAngleMock).toHaveBeenCalledWith("spidercam_overhead");

      // 2. Commentary Subtitle Ticker
      const commentaryTicker = container!.querySelector("[data-testid='broadcast-commentary-ticker']");
      expect(commentaryTicker).not.toBeNull();
      expect(commentaryTicker!.textContent).toContain("Peter Drury AI");
      expect(commentaryTicker!.textContent).toContain("Brilliant build-up play");

      // 3. Watch-Party Reactions Container & Cheer Meter
      const rxContainer = container!.querySelector("[data-testid='watch-party-reactions-container']");
      expect(rxContainer).not.toBeNull();
      expect(rxContainer!.textContent).toContain("🔥");

      const cheerMeter = container!.querySelector("[data-testid='watch-party-cheer-meter']");
      expect(cheerMeter).not.toBeNull();
      expect(cheerMeter!.textContent).toContain("78%");

      // 4. Watch-Party Quick Reaction Bar
      const reactionBar = container!.querySelector("[data-testid='watch-party-reaction-bar']");
      expect(reactionBar).not.toBeNull();
      const sendFireBtn = container!.querySelector("[data-testid='send-reaction-🔥']") as HTMLButtonElement;
      expect(sendFireBtn).not.toBeNull();

      act(() => {
        sendFireBtn.click();
      });
      expect(onSendReactionMock).toHaveBeenCalledWith("🔥");

      // 5. Haptics Toggle Button
      const hapticsBtn = container!.querySelector("[data-testid='toggle-haptics-button']") as HTMLButtonElement;
      expect(hapticsBtn).not.toBeNull();
      act(() => {
        hapticsBtn.click();
      });
      expect(onToggleHapticsMock).toHaveBeenCalled();
    });
  });
});
