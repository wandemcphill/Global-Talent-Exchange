/**
 * Automated Test Suite: GtexSceneRegistry
 * Validates scene registration, lookup, category filtering, quality profiling, and asset preload resolution.
 */

import { GtexSceneRegistry, QUALITY_PROFILES } from "./GtexSceneRegistry";
import { GtexSceneDescriptor } from "./GtexSceneTypes";

describe("GtexSceneRegistry", () => {
  beforeEach(() => {
    GtexSceneRegistry.resetToDefaults();
  });

  test("loads initial scene catalog with canonical ecosystem scenes", () => {
    expect(GtexSceneRegistry.hasScene("campus_builder")).toBe(true);
    expect(GtexSceneRegistry.hasScene("signing_walkout")).toBe(true);
    expect(GtexSceneRegistry.hasScene("luxury_turntable")).toBe(true);
    expect(GtexSceneRegistry.hasScene("stadium_sponsor")).toBe(true);
    expect(GtexSceneRegistry.hasScene("competition_final")).toBe(true);
    expect(GtexSceneRegistry.hasScene("stadium_match_broadcast")).toBe(true);
    expect(GtexSceneRegistry.hasScene("boardroom_meeting")).toBe(true);
    expect(GtexSceneRegistry.hasScene("luxury_inspection_turntable")).toBe(true);
  });

  test("retrieves scene by ID with complete descriptor properties", () => {
    const campus = GtexSceneRegistry.getScene("campus_builder");
    expect(campus).toBeDefined();
    expect(campus?.category).toBe("campus");
    expect(campus?.renderBackend).toBe("threejs");
    expect(campus?.fallbackMode).toBe("2d_diorama");
    expect(campus?.requiredModels).toContain("/models/campus/stadium_main.glb");
    expect(campus?.supportsInteraction).toBe(true);
  });

  test("retrieves cinema stage scenes by alias", () => {
    const walkout = GtexSceneRegistry.getScene("signing_walkout");
    expect(walkout).toBeDefined();
    expect(walkout?.cinemaSceneType).toBe("signing_walkout");
    expect(walkout?.category).toBe("cinema");
  });

  test("allows registration of new custom ecosystem scenes", () => {
    const customScene: GtexSceneDescriptor = {
      id: "creator_fan_arena",
      title: "Creator Fan Arena",
      category: "competition",
      description: "Interactive stadium dome with holographic streamer tournament leaderboards",
      renderBackend: "threejs",
      requiredModels: ["/models/campus/stadium_main.glb"],
      fallbackMode: "2d_diorama",
      supportsInteraction: true,
      tags: ["creator", "arena", "streamer"],
    };

    GtexSceneRegistry.registerScene(customScene);
    expect(GtexSceneRegistry.hasScene("creator_fan_arena")).toBe(true);
    const retrieved = GtexSceneRegistry.getScene("creator_fan_arena");
    expect(retrieved?.title).toBe("Creator Fan Arena");
  });

  test("filters scenes by category and tag", () => {
    const campusScenes = GtexSceneRegistry.listScenes({ category: "campus" });
    expect(campusScenes.length).toBeGreaterThan(0);
    expect(campusScenes.every((s) => s.category === "campus")).toBe(true);

    const showroomScenes = GtexSceneRegistry.listScenes({ category: "showroom" });
    expect(showroomScenes.length).toBeGreaterThanOrEqual(2);
    expect(showroomScenes.some((s) => s.id === "luxury_turntable")).toBe(true);

    const trophyScenes = GtexSceneRegistry.listScenes({ tag: "trophy" });
    expect(trophyScenes.some((s) => s.id === "competition_final" || s.id === "trophy_podium")).toBe(true);
  });

  test("aggregates required assets for batch preloading", () => {
    const preload = GtexSceneRegistry.getAssetPreloadList([
      "campus_builder",
      "luxury_turntable",
      "stadium_match_broadcast",
    ]);

    expect(preload.models).toContain("/models/campus/stadium_main.glb");
    expect(preload.models).toContain("/assets/showroom/sovereign_900x_jet.glb");
    expect(preload.models).toContain("/models/campus/stadium_bowl_core.glb");
    expect(preload.audio).toContain("stadium_ambient");
  });

  test("resolves device quality profiles and allows manual override", () => {
    const initialQuality = GtexSceneRegistry.detectDeviceQuality();
    expect(["low", "medium", "high", "ultra"]).toContain(initialQuality.tier);

    // Set manual override
    GtexSceneRegistry.setQualityOverride("ultra");
    expect(GtexSceneRegistry.getQualityOverride()).toBe("ultra");
    expect(GtexSceneRegistry.detectDeviceQuality()).toEqual(QUALITY_PROFILES.ultra);

    // Switch to low quality profile
    GtexSceneRegistry.setQualityOverride("low");
    expect(GtexSceneRegistry.detectDeviceQuality()).toEqual(QUALITY_PROFILES.low);
    expect(GtexSceneRegistry.detectDeviceQuality().targetFps).toBe(30);
    expect(GtexSceneRegistry.detectDeviceQuality().shadowsEnabled).toBe(false);

    // Clear override
    GtexSceneRegistry.setQualityOverride(null);
    expect(GtexSceneRegistry.getQualityOverride()).toBeNull();
  });
});
