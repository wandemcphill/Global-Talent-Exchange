/**
 * GTEX Living Football Ecosystem — Shared WebGL 3D Experience Framework
 * Core Types & Descriptors for Scene Registration, Quality Adaptation, and 2D Fallbacks.
 */

import React from "react";
import { Cinema3DSceneType, Cinema3DStageProps } from "@/components/gtex/Cinema3DStage";
import { MatchViewerContractInput } from "./broadcast/spectatorContract";

export type DeviceQualityTier = "low" | "medium" | "high" | "ultra";

export interface QualityProfile {
  tier: DeviceQualityTier;
  targetFps: number;
  pixelRatio: number;
  shadowsEnabled: boolean;
  antialias: boolean;
  maxParticles: number;
  textureResolutionCap: number; // e.g., 512, 1024, 2048
  lodDistanceScale: number;
  description: string;
}

/**
 * Real-time performance and quality telemetry measured from the viewport animation loop.
 * Measured statistics reflect true rendering timing rather than declared quality targets.
 */
export interface QualityTelemetry {
  /** Measured frames per second over the rolling sample window (0 until first sample window completes) */
  measuredFps: number;
  /** Instantaneous frame time in milliseconds (delta time) */
  frameTimeMs: number;
  /** Average frame time over the sample window in milliseconds */
  averageFrameTimeMs: number;
  /** 50th percentile (median) frame time in milliseconds */
  p50FrameTimeMs: number;
  /** 95th percentile frame time in milliseconds */
  p95FrameTimeMs: number;
  /** Number of frames sampled in the current window */
  sampleCount: number;
  /** Total elapsed time in milliseconds */
  elapsedMs: number;
  /** Whether WebGL context is currently lost */
  isContextLost: boolean;
  /** Active quality profile in effect */
  activeProfile: QualityProfile;
  /** Current effective quality tier */
  qualityTier: DeviceQualityTier;
}

/**
 * Standard contract for custom scene renderers registered in GtexSceneRegistry.
 * Decouples individual 3D scene implementations from the viewport container.
 */
export interface GtexSceneRendererProps {
  /** Scene identifier registered in GtexSceneRegistry */
  sceneId: string;
  /** Selected or active quality tier */
  qualityTier: DeviceQualityTier;
  /** Active quality profile settings */
  activeQuality: QualityProfile;
  /** Real-time quality telemetry (measured FPS, frame delta, context status) */
  telemetry?: QualityTelemetry;
  /** Optional auto-rotation flag */
  autoRotate?: boolean;
  /** Optional camera/stage control visibility */
  showControls?: boolean;
  /** Optional match viewer state for matchday broadcast scenes */
  matchViewState?: MatchViewerContractInput;
  /** Custom scene-specific property bag */
  sceneProps?: Record<string, any>;
  /** Container CSS class */
  className?: string;
  /** Test identifier */
  testId?: string;
  /** Quality tier change callback */
  onQualityTierChange?: (tier: DeviceQualityTier) => void;
  [key: string]: any;
}

export type GtexCustomSceneRenderer<P = any> = React.ComponentType<P>;

export type SceneCategory =
  | "campus"
  | "cinema"
  | "broadcast"
  | "club"
  | "academy"
  | "showroom"
  | "competition";

export type RenderBackendType = "threejs" | "cinema_volumetric" | "hybrid";

export type FallbackMode = "2d_diorama" | "static_card" | "simplified_canvas";

export interface CameraPreset {
  position: [number, number, number];
  target: [number, number, number];
  fov: number;
}

export interface GtexSceneDescriptor {
  /** Unique identifier for the scene */
  id: string;
  /** Human-readable display title */
  title: string;
  /** Functional category */
  category: SceneCategory;
  /** Purpose and description of the 3D environment */
  description: string;
  /** Underlying render backend */
  renderBackend: RenderBackendType;
  /** Default camera setup */
  defaultCamera?: CameraPreset;
  /** Pre-configured cinematic camera angles */
  cameraAngles?: Record<string, CameraPreset>;
  /** Required 3D GLB model paths (relative or public URL) */
  requiredModels: string[];
  /** Required audio stems / SFX keys */
  requiredAudio?: string[];
  /** Conventional interface fallback mode when WebGL is unavailable or low-spec tier */
  fallbackMode: FallbackMode;
  /** Whether the scene accepts orbit/pan/zoom or touch gestures */
  supportsInteraction: boolean;
  /** Associated Cinema3DSceneType if backed by Cinema3DStage */
  cinemaSceneType?: Cinema3DSceneType;
  /** Search and classification tags */
  tags: string[];
  /** Metadata and customization flags */
  meta?: Record<string, any>;
}

export interface GtexSceneViewportProps extends Partial<Cinema3DStageProps> {
  /** Scene ID registered in GtexSceneRegistry (or Cinema3DSceneType) */
  sceneId: string;
  /** Optional quality tier override (if omitted, auto-detected from device) */
  qualityTier?: DeviceQualityTier;
  /** Optional quality preset alias */
  qualityPreset?: DeviceQualityTier | string;
  /** Optional auto-rotation toggle for showcase/boardroom stages */
  autoRotate?: boolean;
  /** Optional camera/stage control visibility toggle */
  showControls?: boolean;
  /** Optional custom title override */
  customTitle?: string;
  /** Optional custom subtitle override */
  customSubtitle?: string;
  /** Force conventional 2D fallback interface even when WebGL is available */
  forceFallback2D?: boolean;
  /** Force WebGL container mode (useful for test environments without GPU hardware) */
  forceWebGL?: boolean;
  /** Additional container CSS class */
  className?: string;
  /** Test identifier */
  testId?: string;
  /** Fallback card headline override */
  fallbackHeadline?: string;
  /** Fallback card description override */
  fallbackDescription?: string;
  /** Strongly typed match viewer contract input for live match broadcast scenes */
  matchViewState?: MatchViewerContractInput;
  /** Optional telemetry observer callback reporting true measured FPS and frame timings */
  onQualityTelemetryUpdate?: (telemetry: QualityTelemetry) => void;
  /** Optional callback fired when adaptive quality adjustments trigger */
  onQualityTierChange?: (tier: DeviceQualityTier) => void;
  /** Custom scene-specific property bag forwarded to registered renderers */
  sceneProps?: Record<string, any>;
  /** Direct custom 3D children if rendered in custom canvas mode */
  children?: React.ReactNode;
}
