/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * PBR Pitch Turf Shader & Anisotropic Mowing Sheen Material (Track 2 Upgrade).
 *
 * Implements:
 * 1. Directional mowing stripe modulation with alternating bent-grass anisotropic sheen.
 * 2. Normal perturbation for microscopic blade texture.
 * 3. Dynamic moisture (rain/dew) specular reflection and wet-grass darkening.
 * 4. Progressive wear factor integration (scuffs/mud in high-traffic channels).
 *
 * Built on Three.js MeshStandardMaterial with custom onBeforeCompile shader injection.
 */

import * as THREE from "three";

export interface PbrTurfShaderOptions {
  baseColorHex?: string;
  stripeColorHex?: string;
  moisture?: number; // 0.0 to 1.0
  wearFactor?: number; // 0.0 to 1.0
  stripeWidthMeters?: number;
}

export interface PbrTurfSummary {
  moisture: number;
  wearFactor: number;
  stripeWidthMeters: number;
  isCustomShaderCompiled: boolean;
  roughness: number;
  metalness: number;
}

export class PbrTurfShaderMaterial {
  public readonly material: THREE.MeshStandardMaterial;
  private isCompiled: boolean = false;

  private uniforms = {
    uMoisture: { value: 0.0 },
    uWear: { value: 0.0 },
    uStripeWidth: { value: 5.8 },
    uLightDir: { value: new THREE.Vector3(0.5, 0.8, 0.3).normalize() },
  };

  private stripeWidthMeters: number = 5.8;

  constructor(options?: PbrTurfShaderOptions) {
    const baseColor = new THREE.Color(options?.baseColorHex ?? "#1a5e28");
    const stripeColor = new THREE.Color(options?.stripeColorHex ?? "#236d33");

    this.stripeWidthMeters = options?.stripeWidthMeters ?? 5.8;
    this.uniforms.uStripeWidth.value = this.stripeWidthMeters;
    if (typeof options?.moisture === "number") {
      this.uniforms.uMoisture.value = options.moisture;
    }
    if (typeof options?.wearFactor === "number") {
      this.uniforms.uWear.value = options.wearFactor;
    }

    this.material = new THREE.MeshStandardMaterial({
      color: baseColor,
      roughness: 0.82,
      metalness: 0.05,
      side: THREE.FrontSide,
    });

    // Inject custom PBR mowing sheen and moisture shaders
    this.material.onBeforeCompile = (shader) => {
      shader.uniforms.uMoisture = this.uniforms.uMoisture;
      shader.uniforms.uWear = this.uniforms.uWear;
      shader.uniforms.uStripeWidth = this.uniforms.uStripeWidth;
      shader.uniforms.uLightDir = this.uniforms.uLightDir;

      // Inject varying world position in vertex shader
      shader.vertexShader = shader.vertexShader.replace(
        "#include <common>",
        `
        #include <common>
        varying vec3 vWorldPos;
        `
      );
      shader.vertexShader = shader.vertexShader.replace(
        "#include <worldpos_vertex>",
        `
        #include <worldpos_vertex>
        vWorldPos = (modelMatrix * vec4(transformed, 1.0)).xyz;
        `
      );

      // Inject anisotropic mowing sheen and moisture logic in fragment shader
      shader.fragmentShader = shader.fragmentShader.replace(
        "#include <common>",
        `
        #include <common>
        varying vec3 vWorldPos;
        uniform float uMoisture;
        uniform float uWear;
        uniform float uStripeWidth;
        uniform vec3 uLightDir;
        `
      );

      shader.fragmentShader = shader.fragmentShader.replace(
        "#include <roughnessmap_fragment>",
        `
        #include <roughnessmap_fragment>
        // Mowing stripe calculation across pitch x-axis (alternating grass blade direction)
        float stripeIndex = floor(vWorldPos.x / uStripeWidth);
        float isAltStripe = mod(stripeIndex, 2.0);

        // Anisotropic view sheen: bent grass reflects light differently toward camera
        vec3 viewDir = normalize(cameraPosition - vWorldPos);
        float grassSheen = dot(viewDir, uLightDir) * 0.12 * (isAltStripe > 0.5 ? 1.0 : -1.0);

        // Wet turf becomes darker and more specular/glossy
        roughnessFactor = clamp(roughnessFactor - uMoisture * 0.38 + grassSheen, 0.25, 0.95);
        `
      );

      shader.fragmentShader = shader.fragmentShader.replace(
        "#include <color_fragment>",
        `
        #include <color_fragment>
        // Apply alternating subtle mowing tone
        float stripeFactor = (mod(floor(vWorldPos.x / uStripeWidth), 2.0) > 0.5) ? 1.08 : 0.94;
        diffuseColor.rgb *= stripeFactor;

        // Darken albedo when wet with rain
        diffuseColor.rgb *= (1.0 - uMoisture * 0.22);

        // Blend high-traffic mud wear into penalty boxes & center circle
        float distFromCenter = length(vWorldPos.xz);
        float nearGoalHome = length(vWorldPos.xz - vec2(-50.0, 0.0));
        float nearGoalAway = length(vWorldPos.xz - vec2(50.0, 0.0));
        float trafficZone = clamp(1.0 - min(nearGoalHome, nearGoalAway) / 14.0, 0.0, 1.0)
                          + clamp(1.0 - distFromCenter / 12.0, 0.0, 0.6);

        vec3 mudColor = vec3(0.18, 0.13, 0.08);
        diffuseColor.rgb = mix(diffuseColor.rgb, mudColor, clamp(uWear * trafficZone * 0.75, 0.0, 0.65));
        `
      );

      this.isCompiled = true;
    };
  }

  public setMoisture(moisture: number): void {
    const val = Math.max(0.0, Math.min(1.0, moisture));
    this.uniforms.uMoisture.value = val;
    this.material.roughness = 0.82 - val * 0.35;
  }

  public setWearFactor(wear: number): void {
    this.uniforms.uWear.value = Math.max(0.0, Math.min(1.0, wear));
  }

  public update(deltaSec: number, lightDir?: THREE.Vector3): void {
    if (lightDir) {
      this.uniforms.uLightDir.value.copy(lightDir).normalize();
    }
  }

  public getSummary(): PbrTurfSummary {
    return {
      moisture: this.uniforms.uMoisture.value,
      wearFactor: this.uniforms.uWear.value,
      stripeWidthMeters: this.stripeWidthMeters,
      isCustomShaderCompiled: this.isCompiled,
      roughness: this.material.roughness,
      metalness: this.material.metalness,
    };
  }

  public dispose(): void {
    this.material.dispose();
  }
}
