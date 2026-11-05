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
  /** Direct custom 3D children if rendered in custom canvas mode */
  children?: React.ReactNode;
}
