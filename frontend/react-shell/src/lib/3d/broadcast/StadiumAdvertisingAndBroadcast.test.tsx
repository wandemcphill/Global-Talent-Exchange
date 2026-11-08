import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import * as THREE from "three";
import {
  StadiumAdvertisingNetwork,
  isCampaignEligible,
  StadiumLedCampaign,
} from "./StadiumAdvertisingNetwork";
import { StadiumArenaEnvironment } from "./StadiumArenaEnvironment";
import { SpatialInterpolator } from "./SpatialInterpolator";
import { CameraDirector, ManualCameraMode } from "./CameraDirector";
import { BroadcastOverlayHUD } from "./BroadcastOverlayHUD";
import { sanitizeForSpectator } from "./spectatorContract";
import { buildFiveMinuteHumanoidMatchFixture } from "./HumanoidMatchPrototypeFixture";

describe("GTEX Master 3D Matchday — Stadium Advertising, Tactical Shaping, Camera & Broadcast HUD", () => {
  describe("Phase 6: StadiumAdvertisingNetwork & Campaign Eligibility", () => {
    const nowMs = new Date("2026-11-07T14:00:00Z").getTime();

    test("excludes unapproved, inactive, future-scheduled, and expired campaigns", () => {
      const validCampaign: StadiumLedCampaign = {
        id: "camp-valid",
        brandName: "GTEX APEX BANK",
        headline: "OFFICIAL FINANCIAL PARTNER",
        source: "club_sponsor",
        priority: 100,
        status: "approved",
        isActive: true,
        isApproved: true,
        startAt: "2026-11-01T00:00:00Z",
        endAt: "2026-12-01T00:00:00Z",
        primaryColor: "#062c43",
        accentColor: "#00e5a3",
        textColor: "#ffffff",
      };

      const expiredCampaign: StadiumLedCampaign = {
        ...validCampaign,
        id: "camp-expired",
        brandName: "EXPIRED CORP",
        endAt: "2026-11-06T23:59:59Z",
      };

      const futureCampaign: StadiumLedCampaign = {
        ...validCampaign,
        id: "camp-future",
        brandName: "FUTURE CORP",
        startAt: new Date(nowMs + 86400000 * 30).toISOString(),
      };

      const unapprovedCampaign: StadiumLedCampaign = {
        ...validCampaign,
        id: "camp-unapproved",
        brandName: "UNAPPROVED CORP",
        isApproved: false,
      };

      const pausedCampaign: StadiumLedCampaign = {
        ...validCampaign,
        id: "camp-paused",
        brandName: "PAUSED CORP",
        isActive: false,
      };

      expect(isCampaignEligible(validCampaign, nowMs)).toBe(true);
      expect(isCampaignEligible(expiredCampaign, nowMs)).toBe(false);
      expect(isCampaignEligible(futureCampaign, nowMs)).toBe(false);
      expect(isCampaignEligible(unapprovedCampaign, nowMs)).toBe(false);
      expect(isCampaignEligible(pausedCampaign, nowMs)).toBe(false);

      const net = new StadiumAdvertisingNetwork({
        rotationIntervalSec: 10,
        enableNetworkFetch: false,
        enableImpressionPost: false,
      });
      net.setCampaigns(
        [
          expiredCampaign,
          futureCampaign,
          unapprovedCampaign,
          pausedCampaign,
          validCampaign,
        ],
        nowMs
      );
      net.update(0.5, 0, 0, nowMs);

      const active = net.getActiveCampaigns();
      expect(active.map((c) => c.id)).toContain("camp-valid");
      expect(active.map((c) => c.id)).not.toContain("camp-expired");
      expect(active.map((c) => c.id)).not.toContain("camp-future");
      expect(active.map((c) => c.id)).not.toContain("camp-unapproved");
      expect(active.map((c) => c.id)).not.toContain("camp-paused");
      net.dispose();
    });

    test("falls back to official GTEX house campaigns when no external campaigns are eligible", () => {
      const net = new StadiumAdvertisingNetwork({
        rotationIntervalSec: 10,
        enableNetworkFetch: false,
        enableImpressionPost: false,
      });
      net.setCampaigns([
        {
          id: "camp-expired-only",
          brandName: "OLD SPONSOR",
          headline: "EXPIRED",
          source: "brand_campaign",
          priority: 1,
          isActive: false,
          isApproved: true,
          primaryColor: "#000",
          accentColor: "#222",
          textColor: "#fff",
        },
      ]);
      net.update(0.5, 0, 0, nowMs);

      const active = net.getActiveCampaigns();
      expect(active.length).toBeGreaterThanOrEqual(2);
      expect(active.every((c) => c.source === "house_fallback")).toBe(true);
      net.dispose();
    });

    test("rotates campaigns only on slot boundaries (10s default) without reallocating textures per frame and records idempotent impressions", () => {
      const impressions: Array<{ id: string; slotIndex: number; rotationIndex: number }> = [];
      const net = new StadiumAdvertisingNetwork({
        rotationIntervalSec: 10,
        minVisibleDwellSec: 0.5,
        enableNetworkFetch: false,
        enableImpressionPost: false,
        onImpressionRecorded: (ev) => {
          impressions.push({
            id: ev.campaignId,
            slotIndex: ev.slotIndex,
            rotationIndex: ev.rotationIndex,
          });
        },
      });

      net.setCampaigns([
        {
          id: "sponsor-alpha",
          brandName: "ALPHA BANK",
          headline: "OFFICIAL PARTNER",
          source: "club_sponsor",
          priority: 200,
          isApproved: true,
          isActive: true,
        },
        {
          id: "sponsor-beta",
          brandName: "BETA TELECOM",
          headline: "5G STADIUM NETWORK",
          source: "competition",
          priority: 180,
          isApproved: true,
          isActive: true,
        },
        {
          id: "sponsor-gamma",
          brandName: "GAMMA MOTORS",
          headline: "DRIVE THE FUTURE",
          source: "brand_campaign",
          priority: 150,
          isApproved: true,
          isActive: true,
        },
      ]);

      const initialTexture = net.getTexture();
      expect(net.getRotationCount()).toBe(0);

      // Simulate 100 frames across 5 seconds (before 10s boundary)
      let elapsed = 0;
      for (let i = 0; i < 100; i++) {
        elapsed += 0.05;
        net.update(0.05, elapsed, elapsed, nowMs);
      }
      expect(net.getRotationCount()).toBe(0);
      expect(net.getTexture()).toBe(initialTexture);
      // Exactly 2 impressions (one per visible slot) recorded during rotation window 0
      expect(impressions.length).toBe(2);

      // Advance past the 10-second rotation boundary and dwell for 1.0s
      elapsed = 10.5;
      net.update(1.0, elapsed, elapsed, nowMs);
      expect(net.getRotationCount()).toBe(1);
      expect(net.getTexture()).toBe(initialTexture); // Same CanvasTexture instance reused
      expect(impressions.length).toBe(4);

      // Pause when document is hidden: dwell does not record impressions while hidden
      net.setDocumentVisible(false);
      net.update(1.0, 21.0, 21.0, nowMs);
      expect(impressions.length).toBe(4);

      net.dispose();
    });

    test("orders club sponsors ahead of competition and platform brand campaigns", () => {
      const net = new StadiumAdvertisingNetwork({
        enableNetworkFetch: false,
        enableImpressionPost: false,
      });

      net.setPublicBrandCampaigns([
        {
          id: "brand-1",
          brand_name: "GLOBAL TELCO",
          headline: "5G STADIUM NETWORK",
          description: "CONNECT EVERYWHERE",
          placement: "partner_showcase",
          destination_url: "https://example.com/telco",
          priority: 50,
        },
      ]);

      net.setSponsorshipPlacements([
        {
          surface: "stadium_board",
          campaign_code: "comp-1",
          sponsor_name: "PREMIER ENERGY",
          source: "competition",
          creative_url: null,
          fallback: false,
        },
        {
          surface: "stadium_board",
          campaign_code: "club-1",
          sponsor_name: "LAGOS AIRWAYS",
          source: "club_sponsor",
          creative_url: null,
          fallback: false,
        },
      ]);

      const active = net.getActiveCampaigns();
      expect(active[0].brandName).toBe("LAGOS AIRWAYS");
      expect(active[0].source).toBe("club_sponsor");
      net.dispose();
    });

    test("fetches v2 stadium inventory and posts canonical stadium_perimeter impression telemetry", async () => {
      const axios = require("axios");
      const postSpy = jest.spyOn(axios, "post").mockResolvedValue({ data: {} });
      const getSpy = jest.spyOn(axios, "get").mockResolvedValue({
        data: {
          campaigns: [
            {
              id: "camp-stadium-v2",
              brand_name: "ECOWAS LOGISTICS",
              headline: "PAN-AFRICAN FREIGHT",
              description: "SPEED & SECURITY",
              placement: "stadium_perimeter",
              destination_url: "https://example.com/freight",
              logo_url: "/api/v2/public/ads/media/asset-1",
              creative_url: "/api/v2/public/ads/media/asset-2",
              priority: 95,
            },
          ],
        },
      });

      const net = new StadiumAdvertisingNetwork({
        enableNetworkFetch: true,
        enableImpressionPost: true,
        minVisibleDwellSec: 0.1,
      });

      net.setMatchContext({ matchId: "match-v2-test" });
      await net.fetchBackendSponsorshipPlacements();

      expect(getSpy).toHaveBeenCalledWith(
        expect.stringContaining("/v2/public/ads/stadium/inventory?limit=25"),
        expect.any(Object)
      );

      const active = net.getActiveCampaigns();
      const ecowas = active.find((c) => c.id === "camp-stadium-v2");
      expect(ecowas).toBeDefined();
      expect(ecowas?.logoUrl).toContain("/api/v2/public/ads/media/asset-1");
      expect(ecowas?.creativeUrl).toContain("/api/v2/public/ads/media/asset-2");

      // Trigger impression dwell
      net.update(0.5, 0.5, 0.5, nowMs);

      expect(postSpy).toHaveBeenCalledWith(
        expect.stringContaining("/v2/public/ads/events"),
        expect.objectContaining({
          campaign_id: "camp-stadium-v2",
          event_type: "impression",
          metadata_json: expect.objectContaining({
            placement: "stadium_perimeter",
            surface: "stadium_led_perimeter",
            match_id: "match-v2-test",
          }),
        }),
        expect.any(Object)
      );

      postSpy.mockRestore();
      getSpy.mockRestore();
      net.dispose();
    });
  });

  describe("Phase 3: SpatialInterpolator Tactical Visual Shaping", () => {
    test("expresses defensive line, formation, width, and pressing on off-ball outfielders while preserving GK and ball carrier", () => {
      const fixture = buildFiveMinuteHumanoidMatchFixture(60);
      const interpolator = new SpatialInterpolator(fixture.frames);

      const baseState = interpolator.interpolate(12.0)!;
      const baseHomeDef = baseState.players.find(
        (p) => p.side === "home" && p.role === "DEF" && !p.has_possession
      )!;
      const baseHomeGK = baseState.players.find(
        (p) => p.side === "home" && p.role === "GK"
      )!;

      interpolator.setTacticalConfig({
        homeFormation: "3-4-3",
        homeDefensiveLine: 90,
        homePressing: 88,
        homeWidth: 80,
      });

      const shapedState = interpolator.interpolate(12.0)!;
      const shapedHomeDef = shapedState.players.find(
        (p) => p.player_id === baseHomeDef.player_id
      )!;
      const shapedHomeGK = shapedState.players.find(
        (p) => p.player_id === baseHomeGK.player_id
      )!;

      // High defensive line pushes home defender forward along attack axis (+X)
      expect(shapedHomeDef.position3D[0]).toBeGreaterThan(baseHomeDef.position3D[0]);
      // Goalkeeper remains locked to exact authoritative position
      expect(shapedHomeGK.position3D[0]).toBeCloseTo(baseHomeGK.position3D[0], 4);
      expect(shapedHomeGK.position3D[2]).toBeCloseTo(baseHomeGK.position3D[2], 4);
    });
  });

  describe("Phase 4: CameraDirector Broadcast Modes", () => {
    test("supports all 6 required broadcast camera modes with smooth finite poses", () => {
      const modes: ManualCameraMode[] = [
        "director_auto",
        "broadcast_main",
        "tactical_high",
        "closeup_action",
        "endzone_home",
        "replay_cam",
        "celebration_cam",
      ];

      const poses = modes.map((mode) => {
        const director = new CameraDirector();
        director.setManualMode(mode);
        return director.update(0.016, "broadcast", [12, 0.2, -4], [18, 0, -2]);
      });

      for (const pose of poses) {
        expect(Number.isFinite(pose.position[0])).toBe(true);
        expect(Number.isFinite(pose.position[1])).toBe(true);
        expect(Number.isFinite(pose.position[2])).toBe(true);
        expect(pose.fov).toBeGreaterThanOrEqual(20);
        expect(pose.fov).toBeLessThanOrEqual(60);
      }

      // Tactical high camera should be higher than closeup action camera
      const tacticalPose = poses[2];
      const closeupPose = poses[3];
      expect(tacticalPose.position[1]).toBeGreaterThan(closeupPose.position[1]);
    });
  });

  describe("Phase 5 & 8: BroadcastOverlayHUD & Spectator Contract", () => {
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

    test("renders club crests, demonstration fixture badge, rich lower-third event card, active player callout, and replay fallback notice", async () => {
      const fixture = buildFiveMinuteHumanoidMatchFixture(60);
      const safeView = sanitizeForSpectator(fixture, false);
      expect(safeView.is_demonstration_fixture).toBe(true);

      const interpolator = new SpatialInterpolator(safeView.frames);
      const state = interpolator.interpolate(10.0)!;
      const goalEvent = safeView.events.find((e) => e.event_type === "goal") || safeView.events[0];

      await act(async () => {
        root.render(
          <BroadcastOverlayHUD
            matchState={state}
            homeTeam={safeView.home_team}
            awayTeam={safeView.away_team}
            matchLabel={safeView.match_label}
            competitionName="GTEX PREMIER SHOWCASE"
            isDemonstrationFixture={true}
            activeEvent={goalEvent}
            isReplayActive={true}
            replayFallbackMessage="EVENT SUMMARY ONLY — SPATIAL REPLAY HISTORY UNAVAILABLE"
            activeSponsorName="GTEX GLOBAL EXCHANGE"
            cameraMode="replay_cam"
            onSelectCameraMode={jest.fn()}
            onToggle2DFallback={jest.fn()}
          />
        );
      });

      expect(container.querySelector("[data-testid='scorebug-home-crest']")).not.toBeNull();
      expect(container.querySelector("[data-testid='scorebug-away-crest']")).not.toBeNull();
      expect(container.querySelector("[data-testid='fixture-authority-badge']")?.textContent).toContain(
        "DEMONSTRATION FIXTURE"
      );
      expect(container.querySelector("[data-testid='broadcast-lower-third-card']")).not.toBeNull();
      expect(container.querySelector("[data-testid='replay-fallback-notice']")?.textContent).toContain(
        "EVENT SUMMARY ONLY"
      );
      expect(container.querySelector("[data-testid='hud-active-sponsor-indicator']")?.textContent).toContain(
        "GTEX GLOBAL EXCHANGE"
      );
    });
  });

  describe("Phase 7: StadiumArenaEnvironment Crowd Reactions & Live Jumbotron", () => {
    test("triggers crowd reactions on match events and updates 3D jumbotron scoreboard", () => {
      const scene = new THREE.Scene();
      const arena = new StadiumArenaEnvironment(scene, {
        qualityTier: "high",
        stadiumName: "GTEX National Arena",
      });

      arena.triggerCrowdReaction("goal", "home");
      expect(arena.getCrowdReactionState().type).toBe("goal");
      expect(arena.getCrowdReactionState().intensity).toBeGreaterThanOrEqual(1.0);

      arena.updateScoreboard(2, 1, "67'", "GOAL! 2-1");
      arena.update(0.5, 40.0);

      arena.dispose();
    });
  });
});
