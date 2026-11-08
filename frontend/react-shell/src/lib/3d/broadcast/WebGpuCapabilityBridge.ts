/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Next-Gen WebGPU Capabilities & Hardware Detection Bridge (Track 5 Upgrade).
 *
 * Implements:
 * 1. Hardware WebGPU API availability detection (navigator.gpu).
 * 2. Feature querying: ASTC/BC texture compression, compute shaders, bind groups.
 * 3. WebGL2 fallback extension interrogation (anisotropic filtering, half-float targets).
 * 4. Runtime telemetry generation for graphics quality auto-negotiation.
 */

import * as THREE from "three";

export interface WebGpuCapabilityReport {
  isWebGpuSupported: boolean;
  adapterName: string | null;
  preferredBackend: "webgpu" | "webgl2" | "webgl1" | "headless";
  maxAnisotropy: number;
  supportsAstc: boolean;
  supportsBc: boolean;
  supportsHalfFloatTargets: boolean;
  maxTextureSize: number;
}

export class WebGpuCapabilityBridge {
  private report: WebGpuCapabilityReport = {
    isWebGpuSupported: false,
    adapterName: null,
    preferredBackend: "webgl2",
    maxAnisotropy: 1,
    supportsAstc: false,
    supportsBc: false,
    supportsHalfFloatTargets: false,
    maxTextureSize: 4096,
  };

  private isInspected: boolean = false;

  constructor() {
    this.detectStaticCapabilities();
  }

  private detectStaticCapabilities(): void {
    if (typeof navigator !== "undefined" && "gpu" in navigator) {
      this.report.isWebGpuSupported = true;
      this.report.preferredBackend = "webgpu";
    }
  }

  /**
   * Interrogates the active Three.js WebGL renderer for hardware GPU limits.
   */
  public async inspectRenderer(renderer: THREE.WebGLRenderer): Promise<WebGpuCapabilityReport> {
    if (this.isInspected) return this.report;

    try {
      const gl = renderer.getContext();
      if (gl) {
        const isWebGL2 =
          Boolean(renderer.capabilities?.isWebGL2) ||
          (typeof WebGL2RenderingContext !== "undefined" && gl instanceof WebGL2RenderingContext) ||
          String(gl.getParameter?.(gl.VERSION ?? 0x1f02) || "").includes("WebGL 2.0");
        if (isWebGL2) {
          this.report.preferredBackend = this.report.isWebGpuSupported ? "webgpu" : "webgl2";
        } else {
          this.report.preferredBackend = "webgl1";
        }

        // Anisotropic filtering extension
        const maxAniso = renderer.capabilities?.getMaxAnisotropy?.() ?? 1;
        this.report.maxAnisotropy = maxAniso;

        // Max texture dimension
        const maxTex = gl.getParameter(gl.MAX_TEXTURE_SIZE);
        if (typeof maxTex === "number") {
          this.report.maxTextureSize = maxTex;
        }

        // Check half-float texture support for post-processing bloom
        const extHalfFloat =
          gl.getExtension("EXT_color_buffer_float") ||
          gl.getExtension("EXT_color_buffer_half_float") ||
          gl.getExtension("OES_texture_half_float");
        this.report.supportsHalfFloatTargets = !!extHalfFloat;

        // Check compressed texture formats
        const extAstc = gl.getExtension("WEBGL_compressed_texture_astc");
        const extBc = gl.getExtension("WEBGL_compressed_texture_s3tc");
        this.report.supportsAstc = !!extAstc;
        this.report.supportsBc = !!extBc;
      }
    } catch {
      this.report.preferredBackend = "headless";
    }

    // Attempt to query real WebGPU adapter name if available
    if (typeof navigator !== "undefined" && "gpu" in navigator) {
      try {
        const gpu = (navigator as unknown as { gpu: { requestAdapter: () => Promise<{ info?: { device?: string; description?: string } } | null> } }).gpu;
        const adapter = await gpu.requestAdapter();
        if (adapter && adapter.info) {
          this.report.adapterName = adapter.info.device || adapter.info.description || "WebGPU Hardware Device";
        }
      } catch {
        // Safe ignore
      }
    }

    this.isInspected = true;
    return this.report;
  }

  public getReport(): WebGpuCapabilityReport {
    return { ...this.report };
  }
}
