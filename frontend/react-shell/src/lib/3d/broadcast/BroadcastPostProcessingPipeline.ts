/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Cinematic Broadcast Post-Processing Pipeline.
 *
 * Multi-pass pipeline built on Three.js core only (no examples/jsm imports, so it
 * runs unchanged under Webpack, Vite and Jest):
 *
 *   1. Scene pass        -> HDR (HalfFloat when available) target + DepthTexture
 *   2. Bloom             -> bright-pass extraction at half res, separable 9-tap
 *                           Gaussian blur (H + V) ping-ponged at half res
 *   3. Depth of field    -> half-res blurred scene copy, mixed by circle-of-confusion
 *                           from linearised depth (used for replays / close-ups)
 *   4. Composite         -> bloom add, depth-based SSAO, camera-reprojection motion
 *                           blur, DoF, exposure, ACES filmic, vignette, linear->sRGB
 *   5. FXAA              -> final anti-aliasing pass when MSAA is unavailable/off
 *
 * Every pass is gated by quality tier, and the whole pipeline falls back to a
 * direct `renderer.render` when the context cannot support render targets.
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
  isHdrTarget: boolean;
  ssaoActive: boolean;
  fxaaActive: boolean;
  depthOfFieldActive: boolean;
  motionBlurActive: boolean;
  focusDistance: number;
}

interface TierFeatures {
  bloom: boolean;
  ssao: boolean;
  fxaa: boolean;
  motionBlur: boolean;
  dof: boolean;
}

/** Which effects each tier is allowed to run (user toggles can only turn them off further). */
export const POST_FX_TIER_FEATURES: Record<DeviceQualityTier, TierFeatures> = {
  low: { bloom: false, ssao: false, fxaa: false, motionBlur: false, dof: false },
  medium: { bloom: true, ssao: false, fxaa: true, motionBlur: false, dof: true },
  high: { bloom: true, ssao: true, fxaa: true, motionBlur: true, dof: true },
  ultra: { bloom: true, ssao: true, fxaa: true, motionBlur: true, dof: true },
};

const FULLSCREEN_VERTEX = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position.xy, 0.0, 1.0);
  }
`;

const BRIGHT_PASS_FRAGMENT = `
  uniform sampler2D tDiffuse;
  uniform float uThreshold;
  uniform float uExposure;
  varying vec2 vUv;
  void main() {
    vec3 c = texture2D(tDiffuse, vUv).rgb * uExposure;
    float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
    // Soft knee so highlights fade in instead of popping
    float knee = uThreshold * 0.5;
    float soft = clamp(l - uThreshold + knee, 0.0, 2.0 * knee);
    soft = soft * soft / (4.0 * knee + 1e-4);
    float contrib = max(soft, l - uThreshold) / max(l, 1e-4);
    gl_FragColor = vec4(c * contrib, 1.0);
  }
`;

const BLUR_FRAGMENT = `
  uniform sampler2D tDiffuse;
  uniform vec2 uDirection;   // (1/w, 0) or (0, 1/h), pre-scaled by radius
  varying vec2 vUv;
  void main() {
    // 9-tap Gaussian using linear sampling weights
    vec3 sum = texture2D(tDiffuse, vUv).rgb * 0.2270270270;
    sum += texture2D(tDiffuse, vUv + uDirection * 1.3846153846).rgb * 0.3162162162;
    sum += texture2D(tDiffuse, vUv - uDirection * 1.3846153846).rgb * 0.3162162162;
    sum += texture2D(tDiffuse, vUv + uDirection * 3.2307692308).rgb * 0.0702702703;
    sum += texture2D(tDiffuse, vUv - uDirection * 3.2307692308).rgb * 0.0702702703;
    gl_FragColor = vec4(sum, 1.0);
  }
`;

const COMPOSITE_FRAGMENT = `
  uniform sampler2D tDiffuse;
  uniform sampler2D tDepth;
  uniform sampler2D tBloom;
  uniform sampler2D tDofBlur;
  uniform float uBloomEnabled;
  uniform float uBloomStrength;
  uniform float uSsaoEnabled;
  uniform float uSsaoStrength;
  uniform float uDofEnabled;
  uniform float uFocusDistance;
  uniform float uFocusRange;
  uniform float uMotionBlurEnabled;
  uniform float uMotionBlurStrength;
  uniform float uHasDepth;
  uniform float uCameraNear;
  uniform float uCameraFar;
  uniform mat4 uInvViewProjection;
  uniform mat4 uPrevViewProjection;
  uniform vec2 uTexelSize;
  uniform float uVignetteDarkness;
  uniform float uVignetteOffset;
  uniform float uExposure;
  varying vec2 vUv;

  vec3 acesFilmic(vec3 x) {
    return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0);
  }

  vec3 linearToSRGB(vec3 c) {
    vec3 lo = c * 12.92;
    vec3 hi = 1.055 * pow(max(c, vec3(0.0)), vec3(1.0 / 2.4)) - 0.055;
    return mix(lo, hi, step(vec3(0.0031308), c));
  }

  float linearDepth(float d) {
    float z = d * 2.0 - 1.0;
    return (2.0 * uCameraNear * uCameraFar) / (uCameraFar + uCameraNear - z * (uCameraFar - uCameraNear));
  }

  void main() {
    vec3 color = texture2D(tDiffuse, vUv).rgb;
    float rawDepth = uHasDepth > 0.5 ? texture2D(tDepth, vUv).r : 1.0;

    // 1. Camera motion blur by reprojecting this pixel into last frame's clip space
    if (uMotionBlurEnabled > 0.5 && uHasDepth > 0.5 && rawDepth < 1.0) {
      vec4 ndc = vec4(vUv * 2.0 - 1.0, rawDepth * 2.0 - 1.0, 1.0);
      vec4 world = uInvViewProjection * ndc;
      world /= world.w;
      vec4 prev = uPrevViewProjection * world;
      vec2 prevUv = (prev.xy / prev.w) * 0.5 + 0.5;
      vec2 velocity = clamp((vUv - prevUv) * uMotionBlurStrength, vec2(-0.03), vec2(0.03));
      vec3 acc = color;
      for (int i = 1; i < 6; i++) {
        acc += texture2D(tDiffuse, vUv - velocity * (float(i) / 6.0)).rgb;
      }
      color = acc / 6.0;
    }

    // 2. Depth of field (circle of confusion from linear depth)
    if (uDofEnabled > 0.5 && uHasDepth > 0.5) {
      float viewZ = linearDepth(rawDepth);
      float coc = clamp(abs(viewZ - uFocusDistance) / max(uFocusRange, 0.01), 0.0, 1.0);
      color = mix(color, texture2D(tDofBlur, vUv).rgb, coc);
    }

    // 3. Screen-space ambient occlusion (reconstructed normal gradient + 8-tap rotated hemisphere kernel)
    if (uSsaoEnabled > 0.5 && uHasDepth > 0.5 && rawDepth < 1.0) {
      float centerZ = linearDepth(rawDepth);
      float dzdx = linearDepth(texture2D(tDepth, vUv + vec2(uTexelSize.x, 0.0)).r) - centerZ;
      float dzdy = linearDepth(texture2D(tDepth, vUv + vec2(0.0, uTexelSize.y)).r) - centerZ;
      vec3 surfNormal = normalize(vec3(-dzdx, -dzdy, max(0.05, centerZ * 0.02)));
      float radiusPx = clamp(18.0 / centerZ, 1.5, 14.0);
      float occlusion = 0.0;
      float angle = fract(sin(dot(vUv, vec2(12.9898, 78.233))) * 43758.5453) * 6.2831853;
      for (int i = 0; i < 8; i++) {
        float a = angle + float(i) * 0.7853982;
        float r = radiusPx * (0.5 + 0.5 * float(i) / 8.0);
        vec2 offset = vec2(cos(a), sin(a)) * r * uTexelSize;
        float sampleZ = linearDepth(texture2D(tDepth, vUv + offset).r);
        float diff = centerZ - sampleZ;
        vec3 sampleDir = normalize(vec3(cos(a) * r * 0.02, sin(a) * r * 0.02, max(0.0, diff)));
        float normalWeight = clamp(dot(surfNormal, sampleDir), 0.15, 1.0);
        // Closer neighbours in hemisphere occlude; range check prevents silhouette halos
        occlusion += normalWeight * step(0.05, diff) * (1.0 - smoothstep(0.0, 1.5, diff));
      }
      color *= 1.0 - (occlusion / 8.0) * uSsaoStrength;
    }

    color *= uExposure;

    // 4. Bloom (blurred bright-pass, already exposure-scaled)
    if (uBloomEnabled > 0.5) {
      color += texture2D(tBloom, vUv).rgb * uBloomStrength;
    }

    // 5. ACES filmic tone mapping
    color = acesFilmic(color);

    // 6. Broadcast vignette
    vec2 coord = (vUv - vec2(0.5)) * vec2(uVignetteOffset);
    float vig = pow(clamp(1.0 - dot(coord, coord), 0.0, 1.0), uVignetteDarkness);
    color *= vig;

    // 7. Display encoding (scene targets are linear; canvas expects sRGB)
    gl_FragColor = vec4(linearToSRGB(color), 1.0);
  }
`;

const FXAA_FRAGMENT = `
  uniform sampler2D tDiffuse;
  uniform vec2 uTexelSize;
  varying vec2 vUv;
  float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }
  void main() {
    vec3 rgbNW = texture2D(tDiffuse, vUv + vec2(-1.0, -1.0) * uTexelSize).rgb;
    vec3 rgbNE = texture2D(tDiffuse, vUv + vec2( 1.0, -1.0) * uTexelSize).rgb;
    vec3 rgbSW = texture2D(tDiffuse, vUv + vec2(-1.0,  1.0) * uTexelSize).rgb;
    vec3 rgbSE = texture2D(tDiffuse, vUv + vec2( 1.0,  1.0) * uTexelSize).rgb;
    vec3 rgbM  = texture2D(tDiffuse, vUv).rgb;
    float lNW = luma(rgbNW), lNE = luma(rgbNE), lSW = luma(rgbSW), lSE = luma(rgbSE), lM = luma(rgbM);
    float lMin = min(lM, min(min(lNW, lNE), min(lSW, lSE)));
    float lMax = max(lM, max(max(lNW, lNE), max(lSW, lSE)));
    vec2 dir = vec2(-((lNW + lNE) - (lSW + lSE)), ((lNW + lSW) - (lNE + lSE)));
    float dirReduce = max((lNW + lNE + lSW + lSE) * 0.03125, 1.0 / 128.0);
    float rcpDirMin = 1.0 / (min(abs(dir.x), abs(dir.y)) + dirReduce);
    dir = clamp(dir * rcpDirMin, vec2(-8.0), vec2(8.0)) * uTexelSize;
    vec3 rgbA = 0.5 * (texture2D(tDiffuse, vUv + dir * (1.0 / 3.0 - 0.5)).rgb +
                       texture2D(tDiffuse, vUv + dir * (2.0 / 3.0 - 0.5)).rgb);
    vec3 rgbB = rgbA * 0.5 + 0.25 * (texture2D(tDiffuse, vUv + dir * -0.5).rgb +
                                     texture2D(tDiffuse, vUv + dir * 0.5).rgb);
    float lB = luma(rgbB);
    gl_FragColor = vec4((lB < lMin || lB > lMax) ? rgbA : rgbB, 1.0);
  }
`;

const COPY_FRAGMENT = `
  uniform sampler2D tDiffuse;
  varying vec2 vUv;
  void main() { gl_FragColor = vec4(texture2D(tDiffuse, vUv).rgb, 1.0); }
`;

export class BroadcastPostProcessingPipeline {
  private renderer: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.Camera;

  private sceneTarget: THREE.WebGLRenderTarget | null = null;
  private bloomTargetA: THREE.WebGLRenderTarget | null = null;
  private bloomTargetB: THREE.WebGLRenderTarget | null = null;
  private dofTargetA: THREE.WebGLRenderTarget | null = null;
  private dofTargetB: THREE.WebGLRenderTarget | null = null;
  private ldrTarget: THREE.WebGLRenderTarget | null = null;

  private postScene: THREE.Scene;
  private postCamera: THREE.OrthographicCamera;
  private postQuad: THREE.Mesh;

  private brightMaterial: THREE.ShaderMaterial;
  private blurMaterial: THREE.ShaderMaterial;
  private copyMaterial: THREE.ShaderMaterial;
  private compositeMaterial: THREE.ShaderMaterial;
  private fxaaMaterial: THREE.ShaderMaterial;

  private qualityTier: DeviceQualityTier = "high";
  private bloomEnabled = true;
  private ssaoEnabled = true;
  private fxaaEnabled = true;
  private motionBlurEnabled = true;
  private dofEnabled = false;
  private isSupported = false;
  private isHdr = false;
  private hasDepth = false;

  private bloomStrength = 0.28;
  private bloomRadius = 0.32;
  private bloomThreshold = 0.97;
  private focusDistance = 30;
  private focusRange = 18;
  private motionBlurStrength = 0.6;

  private width = 1280;
  private height = 720;
  private lastPassCount = 1;

  private readonly prevViewProjection = new THREE.Matrix4();
  private readonly currViewProjection = new THREE.Matrix4();
  private hasPrevViewProjection = false;

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

    this.postScene = new THREE.Scene();
    this.postCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    const make = (fragmentShader: string, uniforms: Record<string, THREE.IUniform>) =>
      new THREE.ShaderMaterial({
        uniforms,
        vertexShader: FULLSCREEN_VERTEX,
        fragmentShader,
        depthWrite: false,
        depthTest: false,
      });

    this.brightMaterial = make(BRIGHT_PASS_FRAGMENT, {
      tDiffuse: { value: null },
      uThreshold: { value: this.bloomThreshold },
      uExposure: { value: 1.08 },
    });
    this.blurMaterial = make(BLUR_FRAGMENT, {
      tDiffuse: { value: null },
      uDirection: { value: new THREE.Vector2() },
    });
    this.copyMaterial = make(COPY_FRAGMENT, { tDiffuse: { value: null } });
    this.compositeMaterial = make(COMPOSITE_FRAGMENT, {
      tDiffuse: { value: null },
      tDepth: { value: null },
      tBloom: { value: null },
      tDofBlur: { value: null },
      uBloomEnabled: { value: 1 },
      uBloomStrength: { value: this.bloomStrength },
      uSsaoEnabled: { value: 0 },
      uSsaoStrength: { value: 0.55 },
      uDofEnabled: { value: 0 },
      uFocusDistance: { value: this.focusDistance },
      uFocusRange: { value: this.focusRange },
      uMotionBlurEnabled: { value: 0 },
      uMotionBlurStrength: { value: this.motionBlurStrength },
      uHasDepth: { value: 0 },
      uCameraNear: { value: 0.5 },
      uCameraFar: { value: 300 },
      uInvViewProjection: { value: new THREE.Matrix4() },
      uPrevViewProjection: { value: new THREE.Matrix4() },
      uTexelSize: { value: new THREE.Vector2(1 / 1280, 1 / 720) },
      uVignetteDarkness: { value: 1.2 },
      uVignetteOffset: { value: 1.15 },
      uExposure: { value: 1.08 },
    });
    this.fxaaMaterial = make(FXAA_FRAGMENT, {
      tDiffuse: { value: null },
      uTexelSize: { value: new THREE.Vector2(1 / 1280, 1 / 720) },
    });

    this.postQuad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.compositeMaterial);
    this.postQuad.frustumCulled = false;
    this.postScene.add(this.postQuad);

    this.initPipeline();
  }

  private initPipeline(): void {
    try {
      const gl = this.renderer.getContext?.();
      if (
        !gl ||
        typeof gl.createShader !== "function" ||
        typeof this.renderer.setRenderTarget !== "function" ||
        typeof this.renderer.getSize !== "function"
      ) {
        this.isSupported = false;
        return;
      }

      // Fallback (direct) rendering still gets ACES via the renderer itself.
      this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
      this.renderer.toneMappingExposure = 1.08;

      const size = new THREE.Vector2();
      this.renderer.getSize(size);
      const pr = typeof this.renderer.getPixelRatio === "function" ? this.renderer.getPixelRatio() : 1;
      this.width = Math.max(Math.floor(size.x * pr), 320);
      this.height = Math.max(Math.floor(size.y * pr), 180);

      // HDR needs float colour attachments (core in WebGL2 via EXT_color_buffer_float).
      const canFloat =
        !!gl.getExtension("EXT_color_buffer_float") || !!gl.getExtension("EXT_color_buffer_half_float");
      this.isHdr = canFloat;
      const type = canFloat ? THREE.HalfFloatType : THREE.UnsignedByteType;

      const depthTexture = new THREE.DepthTexture(this.width, this.height);
      depthTexture.type = THREE.UnsignedIntType;
      this.hasDepth = true;

      this.sceneTarget = new THREE.WebGLRenderTarget(this.width, this.height, {
        minFilter: THREE.LinearFilter,
        magFilter: THREE.LinearFilter,
        format: THREE.RGBAFormat,
        type,
        depthTexture,
        samples: this.qualityTier === "ultra" ? 4 : 0,
      });

      const halfW = Math.max(1, Math.floor(this.width / 2));
      const halfH = Math.max(1, Math.floor(this.height / 2));
      const halfOpts = { minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, type, depthBuffer: false };
      this.bloomTargetA = new THREE.WebGLRenderTarget(halfW, halfH, halfOpts);
      this.bloomTargetB = new THREE.WebGLRenderTarget(halfW, halfH, halfOpts);
      this.dofTargetA = new THREE.WebGLRenderTarget(halfW, halfH, halfOpts);
      this.dofTargetB = new THREE.WebGLRenderTarget(halfW, halfH, halfOpts);
      this.ldrTarget = new THREE.WebGLRenderTarget(this.width, this.height, {
        minFilter: THREE.LinearFilter,
        magFilter: THREE.LinearFilter,
        depthBuffer: false,
      });

      this.updateTexelUniforms();
      this.isSupported = true;
    } catch {
      this.isSupported = false;
      this.disposeTargets();
    }
  }

  private updateTexelUniforms(): void {
    const texel = new THREE.Vector2(1 / this.width, 1 / this.height);
    (this.compositeMaterial.uniforms.uTexelSize.value as THREE.Vector2).copy(texel);
    (this.fxaaMaterial.uniforms.uTexelSize.value as THREE.Vector2).copy(texel);
  }

  private features(): TierFeatures {
    return POST_FX_TIER_FEATURES[this.qualityTier] ?? POST_FX_TIER_FEATURES.high;
  }

  // ---------------------------------------------------------------------------
  // Public controls
  // ---------------------------------------------------------------------------
  public setSize(width: number, height: number): void {
    if (!this.sceneTarget) return;
    const pr = typeof this.renderer.getPixelRatio === "function" ? this.renderer.getPixelRatio() : 1;
    this.width = Math.max(1, Math.floor(width * pr));
    this.height = Math.max(1, Math.floor(height * pr));
    const halfW = Math.max(1, Math.floor(this.width / 2));
    const halfH = Math.max(1, Math.floor(this.height / 2));
    this.sceneTarget.setSize(this.width, this.height);
    this.ldrTarget?.setSize(this.width, this.height);
    this.bloomTargetA?.setSize(halfW, halfH);
    this.bloomTargetB?.setSize(halfW, halfH);
    this.dofTargetA?.setSize(halfW, halfH);
    this.dofTargetB?.setSize(halfW, halfH);
    this.updateTexelUniforms();
  }

  public setQualityTier(tier: DeviceQualityTier): void {
    this.qualityTier = tier;
  }

  public setBloomEnabled(enabled: boolean): void {
    this.bloomEnabled = enabled;
  }

  public isBloomEnabled(): boolean {
    return this.bloomEnabled && this.features().bloom;
  }

  public setSsaoEnabled(enabled: boolean): void {
    this.ssaoEnabled = enabled;
  }

  public setFxaaEnabled(enabled: boolean): void {
    this.fxaaEnabled = enabled;
  }

  public setMotionBlur(enabled: boolean, strength?: number): void {
    this.motionBlurEnabled = enabled;
    if (typeof strength === "number") this.motionBlurStrength = Math.max(0, Math.min(2, strength));
    if (!enabled) this.hasPrevViewProjection = false;
  }

  /** Focus distance is in world units from the camera (e.g. distance to the ball). */
  public setDepthOfField(enabled: boolean, focusDistance?: number, focusRange?: number): void {
    this.dofEnabled = enabled;
    if (typeof focusDistance === "number" && Number.isFinite(focusDistance)) {
      this.focusDistance = Math.max(0.5, focusDistance);
    }
    if (typeof focusRange === "number" && Number.isFinite(focusRange)) {
      this.focusRange = Math.max(0.5, focusRange);
    }
  }

  // ---------------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------------
  private drawQuad(material: THREE.ShaderMaterial, target: THREE.WebGLRenderTarget | null): void {
    this.postQuad.material = material;
    this.renderer.setRenderTarget(target);
    this.renderer.render(this.postScene, this.postCamera);
  }

  private blurInto(
    source: THREE.WebGLRenderTarget,
    a: THREE.WebGLRenderTarget,
    b: THREE.WebGLRenderTarget,
    radius: number
  ): void {
    // source -> b (horizontal), b -> a (vertical)
    const dir = this.blurMaterial.uniforms.uDirection.value as THREE.Vector2;
    this.blurMaterial.uniforms.tDiffuse.value = source.texture;
    dir.set(radius / a.width, 0);
    this.drawQuad(this.blurMaterial, b);
    this.blurMaterial.uniforms.tDiffuse.value = b.texture;
    dir.set(0, radius / a.height);
    this.drawQuad(this.blurMaterial, a);
  }

  public render(_deltaSec: number): void {
    const f = this.features();
    if (!this.isSupported || !this.sceneTarget || this.qualityTier === "low") {
      this.renderer.setRenderTarget?.(null);
      this.renderer.render(this.scene, this.camera);
      this.lastPassCount = 1;
      return;
    }

    let passes = 0;
    const bloomOn = this.bloomEnabled && f.bloom;
    const ssaoOn = this.ssaoEnabled && f.ssao && this.hasDepth;
    const dofOn = this.dofEnabled && f.dof && this.hasDepth;
    const motionOn = this.motionBlurEnabled && f.motionBlur && this.hasDepth;
    const fxaaOn = this.fxaaEnabled && f.fxaa && !!this.ldrTarget;

    // 1. Scene -> HDR target (linear, un-tonemapped)
    this.renderer.setRenderTarget(this.sceneTarget);
    this.renderer.render(this.scene, this.camera);
    passes++;

    // 2. Bloom chain
    if (bloomOn && this.bloomTargetA && this.bloomTargetB) {
      this.brightMaterial.uniforms.tDiffuse.value = this.sceneTarget.texture;
      this.brightMaterial.uniforms.uThreshold.value = this.bloomThreshold;
      this.drawQuad(this.brightMaterial, this.bloomTargetA);
      const radius = 1 + this.bloomRadius * 3;
      this.blurInto(this.bloomTargetA, this.bloomTargetA, this.bloomTargetB, radius);
      this.blurInto(this.bloomTargetA, this.bloomTargetA, this.bloomTargetB, radius * 2);
      passes += 5;
    }

    // 3. DoF blurred copy
    if (dofOn && this.dofTargetA && this.dofTargetB) {
      this.copyMaterial.uniforms.tDiffuse.value = this.sceneTarget.texture;
      this.drawQuad(this.copyMaterial, this.dofTargetA);
      this.blurInto(this.dofTargetA, this.dofTargetA, this.dofTargetB, 2.5);
      passes += 3;
    }

    // 4. Camera matrices for motion blur / depth reconstruction
    const cam = this.camera as THREE.PerspectiveCamera;
    const u = this.compositeMaterial.uniforms;
    if (cam.projectionMatrix && cam.matrixWorldInverse) {
      this.currViewProjection.multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse);
      (u.uInvViewProjection.value as THREE.Matrix4).copy(this.currViewProjection).invert();
      (u.uPrevViewProjection.value as THREE.Matrix4).copy(
        this.hasPrevViewProjection ? this.prevViewProjection : this.currViewProjection
      );
    }
    if (typeof cam.near === "number") u.uCameraNear.value = cam.near;
    if (typeof cam.far === "number") u.uCameraFar.value = cam.far;

    // 5. Composite
    u.tDiffuse.value = this.sceneTarget.texture;
    u.tDepth.value = this.sceneTarget.depthTexture;
    u.tBloom.value = this.bloomTargetA?.texture ?? null;
    u.tDofBlur.value = this.dofTargetA?.texture ?? null;
    u.uHasDepth.value = this.hasDepth ? 1 : 0;
    u.uBloomEnabled.value = bloomOn ? 1 : 0;
    u.uBloomStrength.value = this.bloomStrength;
    u.uSsaoEnabled.value = ssaoOn ? 1 : 0;
    u.uDofEnabled.value = dofOn ? 1 : 0;
    u.uFocusDistance.value = this.focusDistance;
    u.uFocusRange.value = this.focusRange;
    u.uMotionBlurEnabled.value = motionOn && this.hasPrevViewProjection ? 1 : 0;
    u.uMotionBlurStrength.value = this.motionBlurStrength;
    this.drawQuad(this.compositeMaterial, fxaaOn ? this.ldrTarget : null);
    passes++;

    // 6. FXAA to screen
    if (fxaaOn && this.ldrTarget) {
      this.fxaaMaterial.uniforms.tDiffuse.value = this.ldrTarget.texture;
      this.drawQuad(this.fxaaMaterial, null);
      passes++;
    }

    this.prevViewProjection.copy(this.currViewProjection);
    this.hasPrevViewProjection = motionOn;
    this.lastPassCount = passes;
  }

  public getSummary(): PostProcessingSummary {
    const f = this.features();
    return {
      isSupported: this.isSupported,
      isBloomActive: this.isBloomEnabled(),
      qualityTier: this.qualityTier,
      bloomStrength: this.bloomStrength,
      bloomRadius: this.bloomRadius,
      bloomThreshold: this.bloomThreshold,
      renderPassCount: this.lastPassCount,
      isHdrTarget: this.isSupported && this.isHdr,
      ssaoActive: this.isSupported && this.ssaoEnabled && f.ssao,
      fxaaActive: this.isSupported && this.fxaaEnabled && f.fxaa,
      depthOfFieldActive: this.isSupported && this.dofEnabled && f.dof,
      motionBlurActive: this.isSupported && this.motionBlurEnabled && f.motionBlur,
      focusDistance: this.focusDistance,
    };
  }

  private disposeTargets(): void {
    [this.sceneTarget, this.bloomTargetA, this.bloomTargetB, this.dofTargetA, this.dofTargetB, this.ldrTarget].forEach(
      (t) => {
        if (t) {
          t.depthTexture?.dispose();
          t.dispose();
        }
      }
    );
    this.sceneTarget = null;
    this.bloomTargetA = null;
    this.bloomTargetB = null;
    this.dofTargetA = null;
    this.dofTargetB = null;
    this.ldrTarget = null;
  }

  public dispose(): void {
    this.disposeTargets();
    [this.brightMaterial, this.blurMaterial, this.copyMaterial, this.compositeMaterial, this.fxaaMaterial].forEach((m) =>
      m.dispose()
    );
    this.postQuad.geometry.dispose();
    this.postScene.clear();
    this.isSupported = false;
  }
}
