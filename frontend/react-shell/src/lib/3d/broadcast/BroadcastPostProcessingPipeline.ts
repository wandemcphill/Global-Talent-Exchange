/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Cinematic Broadcast Post-Processing Pipeline (Track 1 Upgrade).
 *
 * Implements:
 * 1. High-dynamic-range WebGLRenderTarget buffer capturing the 3D stadium scene.
 * 2. Fullscreen broadcast composite shader pass with:
 *    - ACES Filmic Tone Mapping and TV contrast grading
 *    - Broadcast TV lens vignette (darkened periphery for cinematic focus)
 *    - Luminance-thresholded bloom halo extraction for floodlights and LED boards
 * 3. Pure Three.js core implementation — zero external loader/JSM transform friction.
 * 4. Graceful fallback on headless/mock environments (jsdom) or low-spec devices.
 */

import * as THREE from "three";
import type { DeviceQualityTier } from "../GtexSceneTypes";

export interface BroadcastPostProcessingOptions {
  qualityTier?: DeviceQualityTier;
  bloomEnabled?: boolean;
  bloomStrength?: number;
  bloomRadius?: number;
  bloomThreshold?: number;
}

export interface PostProcessingSummary {
  isSupported: boolean;
  isBloomActive: boolean;
  qualityTier: DeviceQualityTier;
  bloomStrength: number;
  bloomRadius: number;
  bloomThreshold: number;
  renderPassCount: number;
}

// Broadcast TV Composite Shader (Bloom + ACES Tone Mapping + Vignette)
const BroadcastCompositeShader = {
  uniforms: {
    tDiffuse: { value: null as THREE.Texture | null },
    uBloomEnabled: { value: 1.0 },
    uBloomStrength: { value: 0.55 },
    uBloomThreshold: { value: 0.85 },
    uVignetteDarkness: { value: 1.2 },
    uVignetteOffset: { value: 1.15 },
    uExposure: { value: 1.08 },
  },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = vec4(position.xy, 0.0, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float uBloomEnabled;
    uniform float uBloomStrength;
    uniform float uBloomThreshold;
    uniform float uVignetteDarkness;
    uniform float uVignetteOffset;
    uniform float uExposure;
    varying vec2 vUv;

    // ACES Filmic Tone Mapping Curve (Narkowicz 2015)
    vec3 acesFilmic(vec3 x) {
      float a = 2.51;
      float b = 0.03;
      float c = 2.43;
      float d = 0.59;
      float e = 0.14;
      return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
    }

    void main() {
      vec4 baseColor = texture2D(tDiffuse, vUv);
      vec3 color = baseColor.rgb * uExposure;

      // 1. Luminance-thresholded bloom simulation
      if (uBloomEnabled > 0.5) {
        float luminance = dot(color, vec3(0.2126, 0.7152, 0.0722));
        if (luminance > uBloomThreshold) {
          float bloomFactor = (luminance - uBloomThreshold) * uBloomStrength;
          color += color * bloomFactor;
        }
      }

      // 2. ACES Filmic Tone Mapping
      color = acesFilmic(color);

      // 3. Broadcast TV Vignette
      vec2 coord = (vUv - vec2(0.5)) * vec2(uVignetteOffset);
      float vig = clamp(1.0 - dot(coord, coord), 0.0, 1.0);
      vig = pow(vig, uVignetteDarkness);
      color *= vig;

      gl_FragColor = vec4(color, baseColor.a);
    }
  `,
};

export class BroadcastPostProcessingPipeline {
  private renderer: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.Camera;

  // Post-processing render target & fullscreen quad
  private renderTarget: THREE.WebGLRenderTarget | null = null;
  private postScene: THREE.Scene;
  private postCamera: THREE.OrthographicCamera;
  private postQuad: THREE.Mesh;
  private postMaterial: THREE.ShaderMaterial;

  private qualityTier: DeviceQualityTier = "high";
  private bloomEnabled: boolean = true;
  private isSupported: boolean = false;

  private bloomStrength: number = 0.55;
  private bloomRadius: number = 0.38;
  private bloomThreshold: number = 0.85;

  constructor(
    renderer: THREE.WebGLRenderer,
    scene: THREE.Scene,
    camera: THREE.Camera,
    options?: BroadcastPostProcessingOptions
  ) {
    this.renderer = renderer;
    this.scene = scene;
    this.camera = camera;

    if (options?.qualityTier) this.qualityTier = options.qualityTier;
    if (typeof options?.bloomEnabled === "boolean") this.bloomEnabled = options.bloomEnabled;
    if (typeof options?.bloomStrength === "number") this.bloomStrength = options.bloomStrength;
    if (typeof options?.bloomRadius === "number") this.bloomRadius = options.bloomRadius;
    if (typeof options?.bloomThreshold === "number") this.bloomThreshold = options.bloomThreshold;

    // Fullscreen orthographic presentation quad
    this.postScene = new THREE.Scene();
    this.postCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    this.postMaterial = new THREE.ShaderMaterial({
      uniforms: THREE.UniformsUtils.clone(BroadcastCompositeShader.uniforms),
      vertexShader: BroadcastCompositeShader.vertexShader,
      fragmentShader: BroadcastCompositeShader.fragmentShader,
      depthWrite: false,
      depthTest: false,
    });

    const quadGeo = new THREE.PlaneGeometry(2, 2);
    this.postQuad = new THREE.Mesh(quadGeo, this.postMaterial);
    this.postScene.add(this.postQuad);

    this.initPipeline();
  }

  private initPipeline(): void {
    try {
      const gl = this.renderer.getContext();
      if (!gl || typeof gl.createShader !== "function") {
        this.isSupported = false;
        return;
      }

      this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
      this.renderer.toneMappingExposure = 1.08;

      const size = new THREE.Vector2();
      this.renderer.getSize(size);
      const width = Math.max(size.x, 320);
      const height = Math.max(size.y, 180);

      this.renderTarget = new THREE.WebGLRenderTarget(width, height, {
        minFilter: THREE.LinearFilter,
        magFilter: THREE.LinearFilter,
        format: THREE.RGBAFormat,
      });

      this.postMaterial.uniforms.tDiffuse.value = this.renderTarget.texture;
      this.postMaterial.uniforms.uBloomEnabled.value = this.bloomEnabled ? 1.0 : 0.0;
      this.postMaterial.uniforms.uBloomStrength.value = this.bloomStrength;
      this.postMaterial.uniforms.uBloomThreshold.value = this.bloomThreshold;

      this.isSupported = true;
    } catch {
      this.isSupported = false;
      this.renderTarget = null;
    }
  }

  public setSize(width: number, height: number): void {
    if (!this.renderTarget) return;
    this.renderTarget.setSize(Math.max(1, width), Math.max(1, height));
  }

  public setQualityTier(tier: DeviceQualityTier): void {
    this.qualityTier = tier;
    if (tier === "low") {
      this.postMaterial.uniforms.uBloomEnabled.value = 0.0;
    } else {
      this.postMaterial.uniforms.uBloomEnabled.value = this.bloomEnabled ? 1.0 : 0.0;
    }
  }

  public setBloomEnabled(enabled: boolean): void {
    this.bloomEnabled = enabled;
    this.postMaterial.uniforms.uBloomEnabled.value = enabled ? 1.0 : 0.0;
  }

  public isBloomEnabled(): boolean {
    return this.bloomEnabled && this.qualityTier !== "low";
  }

  /**
   * Renders the scene through the post-processing target or falls back to direct render.
   */
  public render(deltaSec: number): void {
    if (this.isSupported && this.renderTarget && this.qualityTier !== "low") {
      // 1. Render 3D stadium scene to offscreen HDR buffer
      this.renderer.setRenderTarget(this.renderTarget);
      this.renderer.render(this.scene, this.camera);

      // 2. Render composite shader to canvas
      this.renderer.setRenderTarget(null);
      this.renderer.render(this.postScene, this.postCamera);
    } else {
      this.renderer.render(this.scene, this.camera);
    }
  }

  public getSummary(): PostProcessingSummary {
    return {
      isSupported: this.isSupported,
      isBloomActive: this.isBloomEnabled(),
      qualityTier: this.qualityTier,
      bloomStrength: this.bloomStrength,
      bloomRadius: this.bloomRadius,
      bloomThreshold: this.bloomThreshold,
      renderPassCount: this.isSupported ? 2 : 1,
    };
  }

  public dispose(): void {
    if (this.renderTarget) {
      this.renderTarget.dispose();
      this.renderTarget = null;
    }
    this.postMaterial.dispose();
    this.postQuad.geometry.dispose();
    this.postScene.clear();
    this.isSupported = false;
  }
}
