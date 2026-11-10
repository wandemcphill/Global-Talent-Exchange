/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Stadium Image-Based Lighting (IBL).
 *
 * Builds a small procedural "stadium at night" environment (sky dome gradient, bright
 * floodlight banks on four masts, warm stand glow) and prefilters it with
 * PMREMGenerator into `scene.environment`. Every MeshStandardMaterial (kits, ball,
 * PBR turf) then gets physically plausible reflections and ambient fill without
 * The procedural dome is immediate. A Poly Haven HDR replaces it when the file loads.
 */

import * as THREE from "three";
import type { DeviceQualityTier } from "../GtexSceneTypes";

export function polyHavenUrlForWeather(preset: string): string {
  if (preset === "clear_day") return "/textures/env/kloofendal_43d_clear_puresky_2k.hdr";
  if (preset === "snow" || preset === "mist") return "/textures/env/overcast_industrial_courtyard_2k.hdr";
  return "/textures/env/modern_buildings_night_2k.hdr";
}

export interface StadiumEnvironmentSummary {
  isActive: boolean;
  intensity: number;
  floodlightBoost: number;
}

export class StadiumEnvironmentLighting {
  private envTarget: THREE.WebGLRenderTarget | null = null;
  private hdrTexture: THREE.Texture | null = null;
  private hdrRequest = 0;
  private readonly disposables: Array<{ dispose: () => void }> = [];
  private intensity = 1;
  private floodlightBoost = 1;
  private isActive = false;

  constructor(
    private readonly renderer: THREE.WebGLRenderer,
    private readonly scene: THREE.Scene,
    qualityTier: DeviceQualityTier = "high"
  ) {
    if (qualityTier === "low") return;
    try {
      const envScene = this.buildEnvironmentScene();
      const pmrem = new THREE.PMREMGenerator(this.renderer);
      this.envTarget = pmrem.fromScene(envScene, 0.035);
      pmrem.dispose();
      this.scene.environment = this.envTarget.texture;
      this.isActive = true;
      this.setIntensity(qualityTier === "medium" ? 0.7 : 1.0);
    } catch {
      // Headless / mocked contexts cannot run PMREM; materials keep hemisphere lighting.
      this.isActive = false;
    }
  }

  private buildEnvironmentScene(): THREE.Scene {
    const env = new THREE.Scene();

    // Sky dome: deep navy zenith -> lighter haze near the stand rim
    const domeGeo = new THREE.SphereGeometry(50, 32, 16);
    const domeMat = new THREE.ShaderMaterial({
      side: THREE.BackSide,
      depthWrite: false,
      uniforms: {
        uTop: { value: new THREE.Color("#0b1630") },
        uHorizon: { value: new THREE.Color("#3a4a66") },
        uGround: { value: new THREE.Color("#12361f") },
      },
      vertexShader: `varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
      fragmentShader: `
        uniform vec3 uTop; uniform vec3 uHorizon; uniform vec3 uGround; varying vec3 vDir;
        void main(){
          float h = vDir.y;
          vec3 c = h > 0.0 ? mix(uHorizon, uTop, pow(h, 0.6)) : mix(uHorizon, uGround, pow(-h, 0.4));
          gl_FragColor = vec4(c, 1.0);
        }`,
    });
    env.add(new THREE.Mesh(domeGeo, domeMat));
    this.disposables.push(domeGeo, domeMat);

    // Four floodlight banks (HDR-bright emissive panels so highlights exceed 1.0)
    const panelGeo = new THREE.PlaneGeometry(8, 3);
    const panelMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(12, 11.5, 10.5), side: THREE.DoubleSide });
    this.disposables.push(panelGeo, panelMat);
    const corners: Array<[number, number]> = [
      [-30, -22],
      [30, -22],
      [-30, 22],
      [30, 22],
    ];
    corners.forEach(([x, z]) => {
      const panel = new THREE.Mesh(panelGeo, panelMat);
      panel.position.set(x, 24, z);
      panel.lookAt(0, 0, 0);
      env.add(panel);
    });

    // Warm stand glow ring (concourse lighting) for subtle coloured fill
    const ringGeo = new THREE.TorusGeometry(38, 2.5, 8, 48);
    const ringMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(1.4, 1.0, 0.65) });
    this.disposables.push(ringGeo, ringMat);
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = Math.PI / 2;
    ring.position.y = 6;
    env.add(ring);

    return env;
  }

  /** Scales reflection/ambient strength on every standard material in the scene. */
  public setIntensity(intensity: number): void {
    this.intensity = Math.max(0, Math.min(3, intensity));
    if (!this.isActive) return;
    this.scene.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      const mats = Array.isArray(mesh.material) ? mesh.material : mesh.material ? [mesh.material] : [];
      mats.forEach((m) => {
        if ((m as THREE.MeshStandardMaterial).isMeshStandardMaterial) {
          const standard = m as THREE.MeshStandardMaterial;
          // Cloth and the match ball pin their own reflection so the night HDR
          // cannot wash a shirt back to mint or blow the ball out to white.
          const pinned = standard.userData?.gtexFixedEnv;
          standard.envMapIntensity =
            typeof pinned === "number" ? pinned : this.intensity * this.floodlightBoost;
        }
      });
    });
  }

  /** Replaces the procedural dome with a Poly Haven HDR when it loads. */
  public async loadPolyHaven(url = polyHavenUrlForWeather("clear_night")): Promise<boolean> {
    const request = ++this.hdrRequest;
    try {
      const { RGBELoader } = await import("three/examples/jsm/loaders/RGBELoader.js");
      const hdr = await new RGBELoader().loadAsync(url);
      if (request !== this.hdrRequest) {
        hdr.dispose();
        return false;
      }
      hdr.mapping = THREE.EquirectangularReflectionMapping;
      const pmrem = new THREE.PMREMGenerator(this.renderer);
      const next = pmrem.fromEquirectangular(hdr);
      pmrem.dispose();
      if (request !== this.hdrRequest) {
        hdr.dispose();
        next.dispose();
        return false;
      }
      const previous = this.envTarget;
      const previousHdr = this.hdrTexture;
      this.envTarget = next;
      this.hdrTexture = hdr;
      this.scene.environment = next.texture;
      this.scene.background = hdr;
      previous?.dispose();
      previousHdr?.dispose();
      this.isActive = true;
      this.setIntensity(this.intensity);
      return true;
    } catch {
      return false;
    }
  }

  /** Weather hook: rain dims the sky but wet surfaces reflect floodlights harder. */
  public setFloodlightBoost(boost: number): void {
    this.floodlightBoost = Math.max(0.2, Math.min(2.5, boost));
    this.setIntensity(this.intensity);
  }

  public getSummary(): StadiumEnvironmentSummary {
    return { isActive: this.isActive, intensity: this.intensity, floodlightBoost: this.floodlightBoost };
  }

  public dispose(): void {
    if (this.scene.environment === this.envTarget?.texture) {
      this.scene.environment = null;
    }
    if (this.scene.background === this.hdrTexture) {
      this.scene.background = null;
    }
    this.hdrTexture?.dispose();
    this.hdrTexture = null;
    this.envTarget?.dispose();
    this.envTarget = null;
    this.disposables.forEach((d) => d.dispose());
    this.disposables.length = 0;
    this.isActive = false;
  }
}
