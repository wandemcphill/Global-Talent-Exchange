import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import * as THREE from "three";
import { BroadcastPostProcessingPipeline } from "../BroadcastPostProcessingPipeline";
import { PbrTurfShaderMaterial } from "../PbrTurfShaderMaterial";
import { AssetStreamingCache } from "../AssetStreamingCache";
import { CrowdChoreographyAndImpactSystem } from "../CrowdChoreographyAndImpactSystem";
import { WebGpuCapabilityBridge } from "../WebGpuCapabilityBridge";
import { BroadcastOverlayHUD } from "../BroadcastOverlayHUD";
import { SpatialInterpolator } from "../SpatialInterpolator";
import { sanitizeForSpectator } from "../spectatorContract";
import { buildFiveMinuteHumanoidMatchFixture } from "../HumanoidMatchPrototypeFixture";

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

/**
 * Creates a robust mock WebGLRenderer for jsdom testing that fulfills
 * Three.js WebGLRenderer runtime contracts.
 */
function createMockRenderer(customGl?: Partial<Record<string, any>>) {
  const gl = {
    VERSION: 7938,
    MAX_TEXTURE_SIZE: 3379,
    getParameter: jest.fn((p) => {
      if (p === 7938 /* VERSION */) return "WebGL 2.0 (GTEX Mock GPU)";
      if (p === 35724 /* SHADING_LANGUAGE_VERSION */) return "WebGL GLSL ES 3.00";
      if (p === 3379 /* MAX_TEXTURE_SIZE */) return 8192;
      return 1;
    }),
    getExtension: jest.fn((name) => {
      if (name === "EXT_color_buffer_float") return {};
      if (name === "WEBGL_compressed_texture_astc") return {};
      return null;
    }),
    createShader: jest.fn().mockReturnValue({}),
    createProgram: jest.fn().mockReturnValue({}),
    getShaderPrecisionFormat: jest.fn().mockReturnValue({ precision: 23, rangeMin: 127, rangeMax: 127 }),
    ...customGl,
  };

  const mockRenderer = {
    domElement: document.createElement("canvas"),
    getContext: jest.fn().mockReturnValue(gl),
    getSize: jest.fn((target: THREE.Vector2) => {
      target.set(1920, 1080);
      return target;
    }),
    setSize: jest.fn(),
    setPixelRatio: jest.fn(),
    getPixelRatio: jest.fn().mockReturnValue(1),
    setRenderTarget: jest.fn(),
    render: jest.fn(),
    dispose: jest.fn(),
    toneMapping: THREE.NoToneMapping,
    toneMappingExposure: 1.0,
    capabilities: {
      getMaxAnisotropy: jest.fn().mockReturnValue(16),
      isWebGL2: true,
    },
    info: {
      render: { calls: 0, triangles: 0 },
      memory: { geometries: 0, textures: 0 },
    },
  } as unknown as THREE.WebGLRenderer;

  return { mockRenderer, gl };
}

describe("GTEX React WebGL 3D Upgrades — Cinematic Post-Processing, PBR Turf, Asset Cache, Crowd Choreo & WebGPU", () => {
  describe("1. Cinematic Post-Processing Pipeline (BroadcastPostProcessingPipeline)", () => {
    test("initializes with ACES tone mapping, handles bloom toggles, resize, and tiered quality scalability", () => {
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(45, 16 / 9, 0.1, 1000);

      const { mockRenderer } = createMockRenderer();
      const pipeline = new BroadcastPostProcessingPipeline(mockRenderer, scene, camera, {
        qualityTier: "high",
        bloomEnabled: true,
      });

      const summary = pipeline.getSummary();
      expect(summary.qualityTier).toBe("high");
      expect(summary.isSupported).toBe(true);
      expect(typeof summary.bloomStrength).toBe("number");
      expect(typeof summary.bloomRadius).toBe("number");

      // Set bloom enabled / disabled
      pipeline.setBloomEnabled(false);
      expect(pipeline.isBloomEnabled()).toBe(false);

      // Set quality tier to ultra and medium
      pipeline.setQualityTier("ultra");
      expect(pipeline.getSummary().qualityTier).toBe("ultra");

      pipeline.setQualityTier("medium");
      expect(pipeline.getSummary().qualityTier).toBe("medium");

      // Handle resize and render
      pipeline.setSize(1280, 720);
      expect(() => pipeline.render(0.016)).not.toThrow();
      expect(mockRenderer.render).toHaveBeenCalled();

      pipeline.dispose();
      mockRenderer.dispose();
    });
  });

  describe("2. PBR Pitch Turf Shader & Anisotropic Sheen (PbrTurfShaderMaterial)", () => {
    test("compiles custom anisotropic mowing shader, modulates moisture and high-traffic wear", () => {
      const turfMat = new PbrTurfShaderMaterial({
        baseColorHex: "#1a5e28",
        stripeColorHex: "#236d33",
        moisture: 0.2,
        wearFactor: 0.15,
        stripeWidthMeters: 5.5,
      });

      expect(turfMat.material).toBeInstanceOf(THREE.MeshStandardMaterial);
      const initialSummary = turfMat.getSummary();
      expect(initialSummary.stripeWidthMeters).toBe(5.5);
      expect(initialSummary.moisture).toBe(0.2);
      expect(initialSummary.wearFactor).toBe(0.15);

      // Modulate moisture (rain soaked condition lowers roughness)
      turfMat.setMoisture(0.85);
      expect(turfMat.getSummary().moisture).toBe(0.85);
      expect(turfMat.getSummary().roughness).toBeLessThan(0.7);

      // Modulate wear factor
      turfMat.setWearFactor(0.9);
      expect(turfMat.getSummary().wearFactor).toBe(0.9);

      // Advance update with light direction
      const lightDir = new THREE.Vector3(1, 2, 1);
      expect(() => turfMat.update(0.016, lightDir)).not.toThrow();

      turfMat.dispose();
    });
  });

  describe("3. Progressive Asset Streaming & IndexedDB Cache (AssetStreamingCache)", () => {
    test("caches loaded ArrayBuffers in memory, tracks cache hits, and clears cache on demand", async () => {
      const cache = AssetStreamingCache.getInstance();

      const initialSummary = cache.getSummary();
      expect(typeof initialSummary.cachedAssetCount).toBe("number");
      expect(typeof initialSummary.memoryCacheHits).toBe("number");

      // Mock fetch response for reliable jsdom environment execution
      const mockBuffer = new Uint8Array([1, 2, 3, 4]).buffer;
      const fetchSpy = jest.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        arrayBuffer: async () => mockBuffer,
      } as any);

      // Load a test asset
      const testUrl = "/assets/3d/footballers/gtex_humanoid_footballer.glb";
      const buffer = await cache.loadAsset(testUrl);
      expect(buffer).toBeInstanceOf(ArrayBuffer);
      expect(cache.has(testUrl)).toBe(true);

      // Subsequent load should hit memory cache without calling fetch again
      const buffer2 = await cache.loadAsset(testUrl);
      expect(buffer2).toBe(buffer);
      expect(cache.getSummary().memoryCacheHits).toBeGreaterThanOrEqual(1);

      // Clear cache
      await cache.clearCache();
      expect(cache.has(testUrl)).toBe(false);

      fetchSpy.mockRestore();
    });
  });

  describe("4. Stadium Crowd Wave & Camera Trauma Shake (CrowdChoreographyAndImpactSystem)", () => {
    test("evaluates circular La Ola wave propagation and quadratic camera trauma decay", () => {
      const choreo = new CrowdChoreographyAndImpactSystem({
        traumaDecayRate: 1.5,
        maxShakeOffsetMeters: 0.5,
      });

      expect(choreo.getTrauma()).toBe(0.0);
      expect(choreo.getSummary().waveType).toBe("calm");

      // Trigger camera trauma from a goal or crossbar strike
      choreo.triggerCameraTrauma(0.75);
      expect(choreo.getTrauma()).toBe(0.75);
      expect(choreo.getSummary().shakeMagnitude).toBeCloseTo(0.5625, 2);

      // Trigger circular Mexican wave ("la_ola")
      choreo.triggerCrowdWave("la_ola", 12);
      expect(choreo.getSummary().waveType).toBe("la_ola");
      expect(choreo.getSummary().waveActive).toBe(true);

      // Compute crowd section offsets around stadium
      const offsetNorth = choreo.getCrowdSectionOffset(0, -45);
      const offsetSouth = choreo.getCrowdSectionOffset(0, 45);
      expect(Number.isFinite(offsetNorth)).toBe(true);
      expect(Number.isFinite(offsetSouth)).toBe(true);

      // Advance update to observe trauma decay and non-zero camera shake offset
      const updateResult = choreo.update(0.1);
      expect(updateResult.trauma).toBeLessThan(0.75);
      expect(Number.isFinite(updateResult.cameraShakeOffset[0])).toBe(true);
      expect(Number.isFinite(updateResult.cameraShakeOffset[1])).toBe(true);
      expect(Number.isFinite(updateResult.cameraShakeOffset[2])).toBe(true);

      choreo.dispose();
      expect(choreo.getTrauma()).toBe(0.0);
      expect(choreo.getSummary().waveActive).toBe(false);
    });
  });

  describe("5. Next-Gen WebGPU Capabilities Bridge (WebGpuCapabilityBridge)", () => {
    test("detects hardware limits and preferred backend fallback", async () => {
      const bridge = new WebGpuCapabilityBridge();
      const initialReport = bridge.getReport();

      expect(typeof initialReport.isWebGpuSupported).toBe("boolean");
      expect(["webgpu", "webgl2", "webgl1", "headless"]).toContain(initialReport.preferredBackend);
      expect(typeof initialReport.maxAnisotropy).toBe("number");
      expect(typeof initialReport.maxTextureSize).toBe("number");

      // Inspect mock renderer
      const { mockRenderer } = createMockRenderer();
      const report = await bridge.inspectRenderer(mockRenderer);

      expect(report.maxTextureSize).toBe(8192);
      expect(report.maxAnisotropy).toBe(16);
      expect(report.supportsHalfFloatTargets).toBe(true);
      expect(report.supportsAstc).toBe(true);

      mockRenderer.dispose();
    });
  });

  describe("6. BroadcastOverlayHUD Post-FX Bloom Control", () => {
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

    test("renders toggle-bloom-button in top controls and fires callback on click", () => {
      const fixture = buildFiveMinuteHumanoidMatchFixture(60);
      const safeView = sanitizeForSpectator(fixture, false);
      const interpolator = new SpatialInterpolator(safeView.frames);
      const state = interpolator.interpolate(20.0)!;

      const onToggleBloomMock = jest.fn();

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
            bloomEnabled={true}
            onToggleBloom={onToggleBloomMock}
          />
        );
      });

      const bloomBtn = container!.querySelector("[data-testid='toggle-bloom-button']") as HTMLButtonElement;
      expect(bloomBtn).not.toBeNull();
      expect(bloomBtn.textContent).toContain("BLOOM");

      act(() => {
        bloomBtn.click();
      });
      expect(onToggleBloomMock).toHaveBeenCalledTimes(1);
    });
  });
});
