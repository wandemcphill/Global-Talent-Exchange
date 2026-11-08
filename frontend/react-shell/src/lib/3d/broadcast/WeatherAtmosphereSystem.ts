/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast (Phase 2)
 * WeatherAtmosphereSystem: GPU-Efficient Dynamic Weather Particles,
 * Wet/Frosted Turf Surface Response, and Floodlight Volumetric Atmospherics.
 *
 * Implements:
 * 1. Six canonical matchday weather presets:
 *    - "clear_night": Floodlit prime-time broadcast night sky.
 *    - "clear_day": Bright afternoon sunlight with crisp turf contrast.
 *    - "rain": Steady matchday rainfall with wet turf sheen and wind drift.
 *    - "heavy_rain": Stormy downpour with dense rain streaks, mist, and floodlight beams.
 *    - "snow": Winter snowfall with sinusoidal snowflake flutter and frosted pitch tint.
 *    - "mist": Moody evening stadium fog with prominent volumetric floodlight cones.
 * 2. Zero per-frame heap allocation:
 *    - Pre-allocates a single `THREE.BufferGeometry` (`Float32Array`) and `THREE.PointsMaterial`.
 *    - Dynamically adjusts `geometry.setDrawRange(0, activeParticleCount)` across presets and quality tiers.
 * 3. Volumetric Floodlight Haze Cones:
 *    - 4 corner light beam cones oriented toward the pitch center whose opacity scales with mist/rain/night.
 */

import * as THREE from "three";
import { FIFA_PITCH_DIMENSIONS } from "./matchCoordinates";
import type { DeviceQualityTier } from "../GtexSceneTypes";

export type StadiumWeatherPreset =
  | "clear_night"
  | "clear_day"
  | "rain"
  | "heavy_rain"
  | "snow"
  | "mist";

export interface WeatherPresetProfile {
  preset: StadiumWeatherPreset;
  label: string;
  shortLabel: string;
  skyBackgroundHex: string;
  fogColorHex: string;
  fogDensity: number;
  hemiSkyColorHex: number;
  hemiGroundColorHex: number;
  hemiIntensity: number;
  keyLightColorHex: number;
  keyLightIntensity: number;
  fillLightIntensity: number;
  pitchTurfColorHex: number;
  pitchRunoffColorHex: number;
  pitchWetness: number;
  pitchFrost: number;
  floodlightConeOpacity: number;
  particleCountHigh: number;
  particleCountMedium: number;
  particleCountLow: number;
  particleFallSpeedMps: number;
  particleWindX: number;
  particleFlutterAmp: number;
  particleSize: number;
  particleColorHex: number;
  particleOpacity: number;
}

export const STADIUM_WEATHER_PROFILES: Readonly<Record<StadiumWeatherPreset, WeatherPresetProfile>> = {
  clear_night: {
    preset: "clear_night",
    label: "Clear Night Floodlights",
    shortLabel: "NIGHT",
    skyBackgroundHex: "#060a14",
    fogColorHex: "#060a14",
    fogDensity: 0.0055,
    hemiSkyColorHex: 0xdbeafe,
    hemiGroundColorHex: 0x1e5631,
    hemiIntensity: 1.15,
    keyLightColorHex: 0xffffff,
    keyLightIntensity: 1.35,
    fillLightIntensity: 0.72,
    pitchTurfColorHex: 0x154726,
    pitchRunoffColorHex: 0x0e361b,
    pitchWetness: 0.1,
    pitchFrost: 0.0,
    floodlightConeOpacity: 0.09,
    particleCountHigh: 0,
    particleCountMedium: 0,
    particleCountLow: 0,
    particleFallSpeedMps: 0,
    particleWindX: 0,
    particleFlutterAmp: 0,
    particleSize: 0.15,
    particleColorHex: 0xcbd5e1,
    particleOpacity: 0,
  },
  clear_day: {
    preset: "clear_day",
    label: "Clear Afternoon Sunshine",
    shortLabel: "DAY",
    skyBackgroundHex: "#1e3a5f",
    fogColorHex: "#335c81",
    fogDensity: 0.0024,
    hemiSkyColorHex: 0xfef9c3,
    hemiGroundColorHex: 0x226b38,
    hemiIntensity: 1.48,
    keyLightColorHex: 0xfffbeb,
    keyLightIntensity: 1.75,
    fillLightIntensity: 0.92,
    pitchTurfColorHex: 0x1c6132,
    pitchRunoffColorHex: 0x134623,
    pitchWetness: 0.0,
    pitchFrost: 0.0,
    floodlightConeOpacity: 0.0,
    particleCountHigh: 0,
    particleCountMedium: 0,
    particleCountLow: 0,
    particleFallSpeedMps: 0,
    particleWindX: 0,
    particleFlutterAmp: 0,
    particleSize: 0.15,
    particleColorHex: 0xffffff,
    particleOpacity: 0,
  },
  rain: {
    preset: "rain",
    label: "Matchday Rain & Wet Turf",
    shortLabel: "RAIN",
    skyBackgroundHex: "#091322",
    fogColorHex: "#0f1c2e",
    fogDensity: 0.0078,
    hemiSkyColorHex: 0x94a3b8,
    hemiGroundColorHex: 0x133820,
    hemiIntensity: 0.98,
    keyLightColorHex: 0xe2e8f0,
    keyLightIntensity: 1.15,
    fillLightIntensity: 0.65,
    pitchTurfColorHex: 0x0f3b1e,
    pitchRunoffColorHex: 0x092914,
    pitchWetness: 0.72,
    pitchFrost: 0.0,
    floodlightConeOpacity: 0.18,
    particleCountHigh: 1200,
    particleCountMedium: 750,
    particleCountLow: 360,
    particleFallSpeedMps: 21.0,
    particleWindX: 2.8,
    particleFlutterAmp: 0.12,
    particleSize: 0.34,
    particleColorHex: 0xbae6fd,
    particleOpacity: 0.62,
  },
  heavy_rain: {
    preset: "heavy_rain",
    label: "Torrential Storm Downpour",
    shortLabel: "STORM",
    skyBackgroundHex: "#050b14",
    fogColorHex: "#0b1524",
    fogDensity: 0.0102,
    hemiSkyColorHex: 0x64748b,
    hemiGroundColorHex: 0x0c2916,
    hemiIntensity: 0.86,
    keyLightColorHex: 0xcbd5e1,
    keyLightIntensity: 1.02,
    fillLightIntensity: 0.58,
    pitchTurfColorHex: 0x0b3018,
    pitchRunoffColorHex: 0x072010,
    pitchWetness: 0.95,
    pitchFrost: 0.0,
    floodlightConeOpacity: 0.25,
    particleCountHigh: 2200,
    particleCountMedium: 1300,
    particleCountLow: 600,
    particleFallSpeedMps: 26.5,
    particleWindX: 5.2,
    particleFlutterAmp: 0.22,
    particleSize: 0.38,
    particleColorHex: 0x93c5fd,
    particleOpacity: 0.75,
  },
  snow: {
    preset: "snow",
    label: "Winter Snowfall & Frost",
    shortLabel: "SNOW",
    skyBackgroundHex: "#111b2b",
    fogColorHex: "#1e293b",
    fogDensity: 0.0085,
    hemiSkyColorHex: 0xe2e8f0,
    hemiGroundColorHex: 0x2d5a40,
    hemiIntensity: 1.25,
    keyLightColorHex: 0xf8fafc,
    keyLightIntensity: 1.28,
    fillLightIntensity: 0.85,
    pitchTurfColorHex: 0x24593a,
    pitchRunoffColorHex: 0x1c452d,
    pitchWetness: 0.25,
    pitchFrost: 0.75,
    floodlightConeOpacity: 0.16,
    particleCountHigh: 1500,
    particleCountMedium: 900,
    particleCountLow: 420,
    particleFallSpeedMps: 3.6,
    particleWindX: 1.1,
    particleFlutterAmp: 1.65,
    particleSize: 0.46,
    particleColorHex: 0xf8fafc,
    particleOpacity: 0.86,
  },
  mist: {
    preset: "mist",
    label: "Atmospheric Stadium Mist",
    shortLabel: "MIST",
    skyBackgroundHex: "#0b1320",
    fogColorHex: "#162436",
    fogDensity: 0.0112,
    hemiSkyColorHex: 0xcbd5e1,
    hemiGroundColorHex: 0x194528,
    hemiIntensity: 1.05,
    keyLightColorHex: 0xe0f2fe,
    keyLightIntensity: 1.18,
    fillLightIntensity: 0.7,
    pitchTurfColorHex: 0x134223,
    pitchRunoffColorHex: 0x0c2e18,
    pitchWetness: 0.45,
    pitchFrost: 0.0,
    floodlightConeOpacity: 0.28,
    particleCountHigh: 0,
    particleCountMedium: 0,
    particleCountLow: 0,
    particleFallSpeedMps: 0,
    particleWindX: 0,
    particleFlutterAmp: 0,
    particleSize: 0.2,
    particleColorHex: 0xe2e8f0,
    particleOpacity: 0,
  },
};

export const ALL_STADIUM_WEATHER_PRESETS: readonly StadiumWeatherPreset[] = [
  "clear_night",
  "clear_day",
  "rain",
  "heavy_rain",
  "snow",
  "mist",
] as const;

export interface WeatherAtmosphereTelemetry {
  preset: StadiumWeatherPreset;
  label: string;
  activeParticleCount: number;
  pitchWetness: number;
  pitchFrost: number;
  fogDensity: number;
  floodlightConeOpacity: number;
}

export interface WeatherAtmosphereOptions {
  initialPreset?: StadiumWeatherPreset;
  qualityTier?: DeviceQualityTier;
  hemiLight?: THREE.HemisphereLight | null;
  keyLight?: THREE.DirectionalLight | null;
  fillLight?: THREE.DirectionalLight | null;
}

const MAX_WEATHER_PARTICLES = 2200;
const PARTICLE_VOLUME_HALF_X = 68;
const PARTICLE_VOLUME_HALF_Z = 48;
const PARTICLE_VOLUME_MAX_Y = 38;

export class WeatherAtmosphereSystem {
  public readonly group: THREE.Group;
  public readonly particlePoints: THREE.Points;
  public readonly volumetricConesGroup: THREE.Group;

  private scene: THREE.Scene;
  private currentPreset: StadiumWeatherPreset;
  private qualityTier: DeviceQualityTier;
  private activeParticleCount: number = 0;
  private elapsedSec: number = 0;

  private particleGeometry: THREE.BufferGeometry;
  private particleMaterial: THREE.PointsMaterial;
  private positionBuffer: Float32Array;
  private phaseBuffer: Float32Array;
  private positionAttr: THREE.BufferAttribute;

  private volumetricConeMat: THREE.MeshBasicMaterial;
  private volumetricConeGeo: THREE.ConeGeometry;

  private hemiLight: THREE.HemisphereLight | null = null;
  private keyLight: THREE.DirectionalLight | null = null;
  private fillLight: THREE.DirectionalLight | null = null;
  private pitchTurfMat: THREE.MeshLambertMaterial | null = null;
  private pitchRunoffMat: THREE.MeshLambertMaterial | null = null;
  private wetSheenOverlayMesh: THREE.Mesh | null = null;
  private wetSheenOverlayGeo: THREE.PlaneGeometry | null = null;
  private wetSheenOverlayMat: THREE.MeshBasicMaterial | null = null;

  constructor(scene: THREE.Scene, options: WeatherAtmosphereOptions = {}) {
    this.scene = scene;
    this.currentPreset = options.initialPreset || "clear_night";
    this.qualityTier = options.qualityTier || "high";
    this.hemiLight = options.hemiLight ?? null;
    this.keyLight = options.keyLight ?? null;
    this.fillLight = options.fillLight ?? null;

    this.group = new THREE.Group();
    this.group.name = "GTEX_Weather_Atmosphere_System";

    // 1. Pre-allocate GPU Particle System (single BufferGeometry & PointsMaterial)
    this.positionBuffer = new Float32Array(MAX_WEATHER_PARTICLES * 3);
    this.phaseBuffer = new Float32Array(MAX_WEATHER_PARTICLES);

    // Deterministic initial distribution inside the stadium air volume
    let seed = 133742;
    const nextRand = () => {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      return seed / 0xffffffff;
    };

    for (let i = 0; i < MAX_WEATHER_PARTICLES; i++) {
      const idx = i * 3;
      this.positionBuffer[idx] = (nextRand() * 2 - 1) * PARTICLE_VOLUME_HALF_X;
      this.positionBuffer[idx + 1] = nextRand() * PARTICLE_VOLUME_MAX_Y;
      this.positionBuffer[idx + 2] = (nextRand() * 2 - 1) * PARTICLE_VOLUME_HALF_Z;
      this.phaseBuffer[i] = nextRand() * Math.PI * 2;
    }

    this.particleGeometry = new THREE.BufferGeometry();
    this.positionAttr = new THREE.BufferAttribute(this.positionBuffer, 3);
    this.particleGeometry.setAttribute("position", this.positionAttr);

    this.particleMaterial = new THREE.PointsMaterial({
      color: 0xbae6fd,
      size: 0.34,
      transparent: true,
      opacity: 0.62,
      depthWrite: false,
      sizeAttenuation: true,
    });

    this.particlePoints = new THREE.Points(this.particleGeometry, this.particleMaterial);
    this.particlePoints.name = "Weather_Precipitation_Points";
    this.particlePoints.frustumCulled = false;
    this.group.add(this.particlePoints);

    // 2. Volumetric Floodlight Beams (4 corner light cones angled into the arena bowl)
    this.volumetricConesGroup = new THREE.Group();
    this.volumetricConesGroup.name = "Floodlight_Volumetric_Cones";

    this.volumetricConeGeo = new THREE.ConeGeometry(16, 44, 12, 1, true);
    this.volumetricConeMat = new THREE.MeshBasicMaterial({
      color: 0xe0f2fe,
      transparent: true,
      opacity: 0.09,
      side: THREE.DoubleSide,
      depthWrite: false,
    });

    const pylonDistX = FIFA_PITCH_DIMENSIONS.length / 2 + 18;
    const pylonDistZ = FIFA_PITCH_DIMENSIONS.width / 2 + 18;
    const pylonH = 36;
    const corners = [
      [-pylonDistX, -pylonDistZ],
      [pylonDistX, -pylonDistZ],
      [-pylonDistX, pylonDistZ],
      [pylonDistX, pylonDistZ],
    ];

    corners.forEach(([px, pz]) => {
      const cone = new THREE.Mesh(this.volumetricConeGeo, this.volumetricConeMat);
      cone.position.set(px * 0.68, pylonH * 0.56, pz * 0.68);
      cone.lookAt(0, 0, 0);
      cone.rotateX(Math.PI / 2);
      this.volumetricConesGroup.add(cone);
    });

    this.group.add(this.volumetricConesGroup);

    // 3. Wet / Frosted Turf Specular Overlay Plane
    this.wetSheenOverlayGeo = new THREE.PlaneGeometry(
      FIFA_PITCH_DIMENSIONS.length,
      FIFA_PITCH_DIMENSIONS.width
    );
    this.wetSheenOverlayMat = new THREE.MeshBasicMaterial({
      color: 0xbae6fd,
      transparent: true,
      opacity: 0,
      depthWrite: false,
    });
    this.wetSheenOverlayMesh = new THREE.Mesh(this.wetSheenOverlayGeo, this.wetSheenOverlayMat);
    this.wetSheenOverlayMesh.name = "Weather_Turf_Surface_Sheen";
    this.wetSheenOverlayMesh.rotation.x = -Math.PI / 2;
    this.wetSheenOverlayMesh.position.y = 0.012;
    this.group.add(this.wetSheenOverlayMesh);

    this.scene.add(this.group);
    this.applyPreset(this.currentPreset);
  }

  public bindPitchMaterials(
    turfMat: THREE.MeshLambertMaterial | null,
    runoffMat: THREE.MeshLambertMaterial | null
  ): void {
    this.pitchTurfMat = turfMat;
    this.pitchRunoffMat = runoffMat;
    this.applyPreset(this.currentPreset);
  }

  public bindSceneLights(
    hemiLight: THREE.HemisphereLight | null,
    keyLight: THREE.DirectionalLight | null,
    fillLight: THREE.DirectionalLight | null
  ): void {
    this.hemiLight = hemiLight;
    this.keyLight = keyLight;
    this.fillLight = fillLight;
    this.applyPreset(this.currentPreset);
  }

  public setQualityTier(tier: DeviceQualityTier): void {
    this.qualityTier = tier;
    this.applyPreset(this.currentPreset);
  }

  public setPreset(preset: StadiumWeatherPreset): void {
    this.currentPreset = preset;
    this.applyPreset(preset);
  }

  public getPreset(): StadiumWeatherPreset {
    return this.currentPreset;
  }

  public getProfile(): WeatherPresetProfile {
    return STADIUM_WEATHER_PROFILES[this.currentPreset] || STADIUM_WEATHER_PROFILES.clear_night;
  }

  private applyPreset(preset: StadiumWeatherPreset): void {
    const profile = STADIUM_WEATHER_PROFILES[preset] || STADIUM_WEATHER_PROFILES.clear_night;

    // 1. Update Sky Background & Atmospheric Fog
    this.scene.background = new THREE.Color(profile.skyBackgroundHex);
    const fogDensity =
      this.qualityTier === "low" ? profile.fogDensity * 0.82 : profile.fogDensity;
    this.scene.fog = new THREE.FogExp2(profile.fogColorHex, fogDensity);

    // 2. Update Scene Lighting
    if (this.hemiLight) {
      this.hemiLight.color.setHex(profile.hemiSkyColorHex);
      this.hemiLight.groundColor.setHex(profile.hemiGroundColorHex);
      this.hemiLight.intensity = profile.hemiIntensity;
    }
    if (this.keyLight) {
      this.keyLight.color.setHex(profile.keyLightColorHex);
      this.keyLight.intensity = profile.keyLightIntensity;
    }
    if (this.fillLight) {
      this.fillLight.intensity = profile.fillLightIntensity;
    }

    // 3. Update Pitch Turf & Runoff Wetness / Frost Response
    if (this.pitchTurfMat) {
      this.pitchTurfMat.color.setHex(profile.pitchTurfColorHex);
    }
    if (this.pitchRunoffMat) {
      this.pitchRunoffMat.color.setHex(profile.pitchRunoffColorHex);
    }
    if (this.wetSheenOverlayMat && this.wetSheenOverlayMesh) {
      if (profile.pitchFrost > 0.1) {
        this.wetSheenOverlayMat.color.setHex(0xf1f5f9);
        this.wetSheenOverlayMat.opacity = profile.pitchFrost * 0.22;
        this.wetSheenOverlayMesh.visible = true;
      } else if (profile.pitchWetness > 0.2) {
        this.wetSheenOverlayMat.color.setHex(0x7dd3fc);
        this.wetSheenOverlayMat.opacity = profile.pitchWetness * 0.14;
        this.wetSheenOverlayMesh.visible = true;
      } else {
        this.wetSheenOverlayMat.opacity = 0;
        this.wetSheenOverlayMesh.visible = false;
      }
    }

    // 4. Update Volumetric Floodlight Cones
    const coneOpacity =
      this.qualityTier === "low"
        ? profile.floodlightConeOpacity * 0.5
        : profile.floodlightConeOpacity;
    this.volumetricConeMat.opacity = coneOpacity;
    this.volumetricConesGroup.visible = coneOpacity > 0.01;

    // 5. Configure Active Particle Budget
    let targetParticles = profile.particleCountHigh;
    if (this.qualityTier === "medium") {
      targetParticles = profile.particleCountMedium;
    } else if (this.qualityTier === "low") {
      targetParticles = profile.particleCountLow;
    }
    this.activeParticleCount = Math.min(MAX_WEATHER_PARTICLES, Math.max(0, targetParticles));

    this.particleGeometry.setDrawRange(0, this.activeParticleCount);
    this.particleMaterial.color.setHex(profile.particleColorHex);
    this.particleMaterial.size = profile.particleSize;
    this.particleMaterial.opacity = profile.particleOpacity;
    this.particlePoints.visible = this.activeParticleCount > 0;
  }

  /**
   * Advances precipitation particles in-place without allocating new objects.
   */
  public update(deltaSec: number): void {
    const dt = Math.max(0, Math.min(0.1, deltaSec));
    this.elapsedSec += dt;

    if (this.activeParticleCount <= 0) return;

    const profile = this.getProfile();
    const fallStep = profile.particleFallSpeedMps * dt;
    const windStep = profile.particleWindX * dt;
    const flutterAmp = profile.particleFlutterAmp;
    const positions = this.positionBuffer;
    const phases = this.phaseBuffer;
    const count = this.activeParticleCount;

    for (let i = 0; i < count; i++) {
      const idx = i * 3;
      let px = positions[idx] + windStep;
      let py = positions[idx + 1] - fallStep;
      let pz = positions[idx + 2];

      if (flutterAmp > 0) {
        const flutter = Math.sin(this.elapsedSec * 2.4 + phases[i]) * flutterAmp * dt;
        px += flutter;
        pz += Math.cos(this.elapsedSec * 1.9 + phases[i]) * flutterAmp * 0.6 * dt;
      }

      // Wrap around volume boundaries seamlessly
      if (py < 0.1) {
        py += PARTICLE_VOLUME_MAX_Y;
      }
      if (px > PARTICLE_VOLUME_HALF_X) {
        px -= PARTICLE_VOLUME_HALF_X * 2;
      } else if (px < -PARTICLE_VOLUME_HALF_X) {
        px += PARTICLE_VOLUME_HALF_X * 2;
      }
      if (pz > PARTICLE_VOLUME_HALF_Z) {
        pz -= PARTICLE_VOLUME_HALF_Z * 2;
      } else if (pz < -PARTICLE_VOLUME_HALF_Z) {
        pz += PARTICLE_VOLUME_HALF_Z * 2;
      }

      positions[idx] = px;
      positions[idx + 1] = py;
      positions[idx + 2] = pz;
    }

    this.positionAttr.needsUpdate = true;
  }

  public getTelemetry(): WeatherAtmosphereTelemetry {
    const profile = this.getProfile();
    return {
      preset: this.currentPreset,
      label: profile.label,
      activeParticleCount: this.activeParticleCount,
      pitchWetness: profile.pitchWetness,
      pitchFrost: profile.pitchFrost,
      fogDensity:
        this.qualityTier === "low" ? Number((profile.fogDensity * 0.82).toFixed(5)) : profile.fogDensity,
      floodlightConeOpacity: Number(this.volumetricConeMat.opacity.toFixed(3)),
    };
  }

  public dispose(): void {
    try {
      this.particleGeometry.dispose();
      this.particleMaterial.dispose();
      this.volumetricConeGeo.dispose();
      this.volumetricConeMat.dispose();
      this.wetSheenOverlayGeo?.dispose();
      this.wetSheenOverlayMat?.dispose();
    } catch {
      // Safe disposal
    }
    this.group.clear();
  }
}
