import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import * as THREE from "three";
import { BroadcastPostProcessingPipeline } from "../BroadcastPostProcessingPipeline";
import { PbrTurfShaderMaterial } from "../PbrTurfShaderMaterial";
import { AssetStreamingCache } from "../AssetStreamingCache";
import { CrowdChoreographyAndImpactSystem } from "../CrowdChoreographyAndImpactSystem";
import { WebGpuCapabilityBridge } from "../WebGpuCapabilityBridge";
import { StadiumEnvironmentLighting } from "../StadiumEnvironmentLighting";
import { DynamicShadowRig } from "../DynamicShadowRig";
import { PlayerImpostorLodSystem } from "../PlayerImpostorLodSystem";
import {
  AdaptiveQualityGovernor,
  recommendTierFromCapabilities,
} from "../AdaptiveQualityGovernor";
import { StadiumArenaEnvironment } from "../StadiumArenaEnvironment";
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
    shadowMap: {
      enabled: false,
      type: THREE.BasicShadowMap,
      autoUpdate: true,
      needsUpdate: false,
    },
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

describe("GTEX React WebGL 3D Upgrades — Priority A, B & C Full Verification", () => {
  describe("1. Multi-Pass HDR Post-Processing (BroadcastPostProcessingPipeline)", () => {
    test("executes HDR scene pass, separable Gaussian bloom blur, SSAO, DoF, Motion Blur, ACES + sRGB & FXAA", () => {
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(45, 16 / 9, 0.5, 300);

      const { mockRenderer } = createMockRenderer();
      const pipeline = new BroadcastPostProcessingPipeline(mockRenderer, scene, camera, {
        qualityTier: "high",
        bloomEnabled: true,
      });

      const summary = pipeline.getSummary();
      expect(summary.qualityTier).toBe("high");
      expect(summary.isSupported).toBe(true);
      expect(summary.isHdrTarget).toBe(true);
      expect(summary.ssaoActive).toBe(true);
      expect(summary.fxaaActive).toBe(true);
      expect(summary.motionBlurActive).toBe(true);

      // Render high tier with bloom + composite + FXAA (1 scene + 5 bloom + 1 composite + 1 fxaa = 8 passes)
      pipeline.render(0.016);
      expect(pipeline.getSummary().renderPassCount).toBe(8);

      // Enable Depth of Field for replay close-ups (+3 passes = 11 passes)
      pipeline.setDepthOfField(true, 22.0, 10.0);
      pipeline.setMotionBlur(true, 0.9);
      pipeline.render(0.016);
      expect(pipeline.getSummary().depthOfFieldActive).toBe(true);
      expect(pipeline.getSummary().focusDistance).toBe(22.0);
      expect(pipeline.getSummary().renderPassCount).toBe(11);

      // Set bloom disabled -> drops 5 bloom passes (11 - 5 = 6 passes)
      pipeline.setBloomEnabled(false);
      expect(pipeline.isBloomEnabled()).toBe(false);
      pipeline.render(0.016);
      expect(pipeline.getSummary().renderPassCount).toBe(6);

      // Low quality tier bypasses offscreen post-processing -> 1 direct pass
      pipeline.setQualityTier("low");
      pipeline.render(0.016);
      expect(pipeline.getSummary().renderPassCount).toBe(1);

      // Resize and restore ultra tier
      pipeline.setQualityTier("ultra");
      pipeline.setSize(1280, 720);
      expect(() => pipeline.render(0.016)).not.toThrow();

      pipeline.dispose();
      mockRenderer.dispose();
    });
  });

  describe("2. PBR Pitch Turf Shader & Stadium Surface Integration", () => {
    test("compiles custom anisotropic mowing shader and replaces the stadium pitch mesh material", () => {
      const turfMat = new PbrTurfShaderMaterial({
        baseColorHex: "#1a5e28",
        stripeColorHex: "#236d33",
        moisture: 0.2,
        wearFactor: 0.15,
        stripeWidthMeters: 5.5,
      });

      expect(turfMat.material).toBeInstanceOf(THREE.MeshStandardMaterial);
      expect(turfMat.getSummary().stripeWidthMeters).toBe(5.5);

      // Modulate moisture & wear
      turfMat.setMoisture(0.85);
      expect(turfMat.getSummary().moisture).toBe(0.85);
      expect(turfMat.getSummary().roughness).toBeLessThan(0.7);
      turfMat.setWearFactor(0.9);
      expect(turfMat.getSummary().wearFactor).toBe(0.9);
      turfMat.update(0.016, new THREE.Vector3(1, 2, 1));

      // Verify StadiumArenaEnvironment.applyPitchTurfMaterial swaps the actual pitch surface
      const scene = new THREE.Scene();
      const fixture = buildFiveMinuteHumanoidMatchFixture(30);
      const safeView = sanitizeForSpectator(fixture, false);
      const arena = new StadiumArenaEnvironment(scene, {
        homeTeam: safeView.home_team,
        awayTeam: safeView.away_team,
        qualityTier: "medium",
      });

      arena.applyPitchTurfMaterial(turfMat.material);
      let foundPbrPitchMesh = false;
      scene.traverse((obj) => {
        if ((obj as THREE.Mesh).isMesh && (obj as THREE.Mesh).material === turfMat.material) {
          foundPbrPitchMesh = true;
        }
      });
      expect(foundPbrPitchMesh).toBe(true);

      arena.dispose();
      turfMat.dispose();
    });
  });

  describe("3. Progressive Asset Streaming Cache & Draco/KTX2 glTF Decoding", () => {
    test("caches ArrayBuffers, refuses to cache failed fetches, and decodes glTF via configured loader stack", async () => {
      const cache = AssetStreamingCache.getInstance();
      await cache.clearCache();

      const mockBuffer = new Uint8Array([0x67, 0x6c, 0x54, 0x46, 2, 0, 0, 0]).buffer;
      const fetchSpy = jest.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        status: 200,
        arrayBuffer: async () => mockBuffer,
      } as any);

      const testUrl = "/assets/3d/footballers/gtex_humanoid_footballer.glb";
      const buffer = await cache.loadAsset(testUrl);
      expect(buffer).toBe(mockBuffer);
      expect(cache.has(testUrl)).toBe(true);

      // Second load hits memory cache without network fetch
      const hitsBefore = cache.getSummary().memoryCacheHits;
      const buffer2 = await cache.loadAsset(testUrl);
      expect(buffer2).toBe(mockBuffer);
      expect(cache.getSummary().memoryCacheHits).toBe(hitsBefore + 1);

      // Failed fetch is thrown and NOT cached
      fetchSpy.mockResolvedValueOnce({ ok: false, status: 404 } as any);
      const badUrl = "/assets/3d/missing.glb";
      await expect(cache.loadAsset(badUrl)).rejects.toThrow(/HTTP 404/);
      expect(cache.has(badUrl)).toBe(false);

      // Verify loadGLTF invokes configured Draco/KTX2 factory with decoder paths
      let capturedPaths: any = null;
      cache.setDecoderPaths({
        dracoDecoderPath: "/custom/draco/",
        basisTranscoderPath: "/custom/basis/",
      });
      cache.setGltfLoaderFactory(async (paths) => {
        capturedPaths = paths;
        return async (buf) => ({
          scene: new THREE.Group(),
          animations: [],
          byteLength: buf.byteLength,
        });
      });

      const gltf = await cache.loadGLTF(testUrl);
      expect(capturedPaths).toEqual({
        dracoDecoderPath: "/custom/draco/",
        basisTranscoderPath: "/custom/basis/",
      });
      expect(gltf.byteLength).toBe(mockBuffer.byteLength);
      expect(cache.getSummary().gltfDecodes).toBeGreaterThanOrEqual(1);

      cache.setGltfLoaderFactory(null);
      await cache.clearCache();
      fetchSpy.mockRestore();
    });
  });

  describe("4. Stadium Crowd Wave ('La Ola') Wired to Instanced Crowd & Camera Trauma Shake", () => {
    test("physically displaces StadiumArenaEnvironment instanced supporters during La Ola and decays camera trauma", () => {
      const choreo = new CrowdChoreographyAndImpactSystem({
        traumaDecayRate: 1.5,
        maxShakeOffsetMeters: 0.5,
      });

      choreo.triggerCameraTrauma(0.75);
      expect(choreo.getTrauma()).toBe(0.75);
      expect(choreo.getSummary().shakeMagnitude).toBeCloseTo(0.5625, 2);

      // Wire choreography offset into StadiumArenaEnvironment
      const scene = new THREE.Scene();
      const fixture = buildFiveMinuteHumanoidMatchFixture(30);
      const safeView = sanitizeForSpectator(fixture, false);
      const arena = new StadiumArenaEnvironment(scene, {
        homeTeam: safeView.home_team,
        awayTeam: safeView.away_team,
        qualityTier: "medium",
      });

      const offsetSpy = jest.fn((x: number, z: number) => choreo.getCrowdSectionOffset(x, z));
      arena.setExternalCrowdOffsetFn(offsetSpy);

      choreo.triggerCrowdWave("la_ola", 12);
      choreo.update(0.25);
      arena.update(0.016, 10.0);

      expect(offsetSpy).toHaveBeenCalled();
      // Verify at least some stadium sections received positive vertical La Ola displacement
      const displacements = offsetSpy.mock.results.map((r) => r.value as number);
      expect(Math.max(...displacements)).toBeGreaterThan(0.1);

      arena.dispose();
      choreo.dispose();
    });
  });

  describe("5. WebGPU Bridge & Adaptive Quality Governor", () => {
    test("scores hardware capabilities and dynamically steps resolution & post-FX tier on slow/fast frames", async () => {
      const bridge = new WebGpuCapabilityBridge();
      const { mockRenderer } = createMockRenderer();
      const report = await bridge.inspectRenderer(mockRenderer);

      expect(report.maxTextureSize).toBe(8192);
      expect(report.maxAnisotropy).toBe(16);
      expect(report.supportsHalfFloatTargets).toBe(true);
      expect(recommendTierFromCapabilities(report)).toBe("high");
      expect(
        recommendTierFromCapabilities({
          ...report,
          preferredBackend: "webgpu",
          maxTextureSize: 16384,
        })
      ).toBe("ultra");
      expect(
        recommendTierFromCapabilities({
          ...report,
          preferredBackend: "webgl1",
        })
      ).toBe("low");

      // AdaptiveQualityGovernor steps down when frames exceed budget (>19.2ms)
      const gov = new AdaptiveQualityGovernor("high", 60);
      let decision = gov.applyCapabilities(report);
      expect(decision.postFxTier).toBe("high");

      for (let i = 0; i < 95; i++) {
        decision = gov.recordFrame(28.0, 0.028);
        if (decision.changed) break;
      }
      expect(decision.changed).toBe(true);
      expect(decision.resolutionScale).toBeLessThan(1.0);

      // Manual user lock overrides automatic stepping
      gov.lock("medium");
      expect(gov.getSummary().isLocked).toBe(true);
      expect(gov.getSummary().postFxTier).toBe("medium");
      expect(gov.getSummary().resolutionScale).toBe(1.0);

      mockRenderer.dispose();
    });
  });

  describe("6. Dynamic Soft Shadows, IBL Environment Lighting & Player Impostor LOD", () => {
    test("snaps dynamic shadow frustum to ball, boosts wet IBL intensity, and batches far players into InstancedMesh", () => {
      const scene = new THREE.Scene();
      const { mockRenderer } = createMockRenderer();
      const keyLight = new THREE.DirectionalLight(0xffffff, 1.35);
      keyLight.position.set(20, 55, 42);
      scene.add(keyLight);

      // A. DynamicShadowRig
      const shadowRig = new DynamicShadowRig(mockRenderer, keyLight, "high");
      expect(shadowRig.getSummary().enabled).toBe(true);
      expect(shadowRig.getSummary().mapSize).toBe(2048);
      expect(mockRenderer.shadowMap.type).toBe(THREE.PCFSoftShadowMap);

      const playerMesh = new THREE.Mesh(
        new THREE.BoxGeometry(1, 2, 1),
        new THREE.MeshStandardMaterial()
      );
      scene.add(playerMesh);
      shadowRig.registerCaster(playerMesh);
      expect(playerMesh.castShadow).toBe(true);

      shadowRig.update(0.05, [18.4, 0.2, -9.7]);
      expect(shadowRig.getSummary().shadowUpdates).toBe(1);
      expect(keyLight.target.position.x).toBeCloseTo(18.4, 1);
      expect(keyLight.target.position.z).toBeCloseTo(-9.7, 1);

      // B. StadiumEnvironmentLighting
      const envLighting = new StadiumEnvironmentLighting(mockRenderer, scene, "high");
      expect(() => envLighting.setFloodlightBoost(1.4)).not.toThrow();
      expect(envLighting.getSummary().floodlightBoost).toBe(1.4);

      // C. PlayerImpostorLodSystem
      const camera = new THREE.PerspectiveCamera(45, 16 / 9, 0.5, 300);
      camera.position.set(0, 15, 0);

      const nearPlayer = new THREE.Group();
      nearPlayer.position.set(10, 0, 0);
      nearPlayer.updateMatrixWorld();

      const farPlayer1 = new THREE.Group();
      farPlayer1.position.set(110, 0, 0);
      farPlayer1.updateMatrixWorld();

      const farPlayer2 = new THREE.Group();
      farPlayer2.position.set(115, 0, 5);
      farPlayer2.updateMatrixWorld();

      const impostors = new PlayerImpostorLodSystem(scene, "high");
      impostors.update(camera, [
        { id: "p-near", rootObject: nearPlayer, colorHex: "#00e676" },
        { id: "p-far-1", rootObject: farPlayer1, colorHex: "#ff1744" },
        { id: "p-far-2", rootObject: farPlayer2, colorHex: "#ff1744" },
      ]);

      expect(nearPlayer.visible).toBe(true);
      expect(farPlayer1.visible).toBe(false);
      expect(farPlayer2.visible).toBe(false);
      expect(impostors.getSummary().impostorCount).toBe(2);
      expect(impostors.getSummary().fullRigCount).toBe(1);
      expect(impostors.getSummary().drawCallsSaved).toBe(1);

      impostors.dispose();
      envLighting.dispose();
      mockRenderer.dispose();
    });
  });

  describe("7. BroadcastOverlayHUD Post-FX Bloom Control", () => {
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
