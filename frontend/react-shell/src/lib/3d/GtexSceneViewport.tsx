/**
 * GTEX Living Football Ecosystem — Shared WebGL 3D Experience Framework
 * GtexSceneViewport: Central presentation viewport with automatic device quality tiering,
 * scene registry lookup, WebGL context lifecycle management, and conventional 2D fallback.
 */

import React, { useMemo, useState, useEffect, useRef } from "react";
import { GtexSceneRegistry, QUALITY_PROFILES } from "./GtexSceneRegistry";
import { DeviceQualityTier, GtexSceneViewportProps } from "./GtexSceneTypes";
import { useQualityTelemetry } from "./qualityTelemetry";
import { Cinema3DStage, Cinema3DSceneType } from "@/components/gtex/Cinema3DStage";
import {
  Sparkles,
  Layers,
  Cpu,
  Monitor,
  Eye,
  AlertCircle,
  ShieldCheck,
  ChevronRight,
  Activity,
} from "lucide-react";

/**
 * Utility to test whether WebGL context creation is supported in the current environment.
 */
export function isWebGLSupported(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    return Boolean(
      window.WebGLRenderingContext &&
        (canvas.getContext("webgl") || canvas.getContext("experimental-webgl"))
    );
  } catch {
    return false;
  }
}

export const GtexSceneViewport: React.FC<GtexSceneViewportProps> = ({
  sceneId,
  qualityTier: explicitQualityTier,
  forceFallback2D = false,
  forceWebGL = false,
  className = "",
  testId = "gtex-scene-viewport",
  fallbackHeadline,
  fallbackDescription,
  onQualityTelemetryUpdate,
  onQualityTierChange,
  children,
  ...cinemaProps
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hasWebGL, setHasWebGL] = useState<boolean>(true);
  const [selectedTier, setSelectedTier] = useState<DeviceQualityTier>(
    explicitQualityTier || GtexSceneRegistry.detectDeviceQuality().tier
  );

  useEffect(() => {
    setHasWebGL(isWebGLSupported());
  }, []);

  useEffect(() => {
    if (explicitQualityTier) {
      setSelectedTier(explicitQualityTier);
    }
  }, [explicitQualityTier]);

  const descriptor = useMemo(() => {
    return (
      GtexSceneRegistry.getScene(sceneId) || {
        id: sceneId,
        title: cinemaProps.title || "GTEX 3D Environment",
        category: "cinema" as const,
        description: "Authoritative GTEX Football Ecosystem 3D Viewport",
        renderBackend: "cinema_volumetric" as const,
        requiredModels: [],
        fallbackMode: "2d_diorama" as const,
        supportsInteraction: true,
        tags: ["general"],
      }
    );
  }, [sceneId, cinemaProps.title]);

  const activeQuality = QUALITY_PROFILES[selectedTier] || QUALITY_PROFILES.high;

  // Real-time quality telemetry passive monitoring loop
  const telemetry = useQualityTelemetry({
    activeProfile: activeQuality,
    qualityTier: selectedTier,
    enabled: hasWebGL && !forceFallback2D,
    containerRef,
    onTelemetryUpdate: onQualityTelemetryUpdate,
    onAdaptiveTierChange: (newTier) => {
      setSelectedTier(newTier);
      onQualityTierChange?.(newTier);
    },
  });

  const shouldRenderFallback = forceFallback2D || (!hasWebGL && !forceWebGL);

  // Helper to render conventional 2D fallback presentation
  const renderFallbackView = (badgeLabel: string, explanationNote?: string) => (
    <div
      data-testid={`${testId}-fallback-2d`}
      className={`relative overflow-hidden rounded-xl border border-emerald-500/20 bg-gradient-to-b from-[#090f1d] via-[#060a14] to-[#04060c] p-6 text-white shadow-2xl ${className}`}
    >
      {/* Subtle Pitch Background Grid */}
      <div
        className="pointer-events-none absolute inset-0 opacity-10"
        style={{
          backgroundImage:
            "linear-gradient(#10b981 1px, transparent 1px), linear-gradient(90deg, #10b981 1px, transparent 1px)",
          backgroundSize: "32px 32px",
        }}
      />

      <div className="relative z-10 flex flex-col gap-4">
        {/* Header Row */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-4">
          <div className="flex items-center gap-2">
            <span className="flex h-7 items-center rounded-full bg-emerald-500/10 px-3 py-0.5 text-xs font-semibold text-emerald-400 ring-1 ring-emerald-500/30">
              <Sparkles className="mr-1.5 h-3.5 w-3.5" />
              {cinemaProps.badgeText || descriptor.category.toUpperCase()}
            </span>
            <span className="rounded bg-amber-500/10 px-2 py-0.5 text-[11px] font-mono font-medium text-amber-400 ring-1 ring-amber-500/20">
              {badgeLabel}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Cpu className="h-3.5 w-3.5 text-emerald-400" />
            <span className="font-mono uppercase">{selectedTier} TIER</span>
          </div>
        </div>

        {/* Title & Subject */}
        <div>
          <h3 className="text-xl font-bold tracking-tight text-slate-100">
            {fallbackHeadline || cinemaProps.title || descriptor.title}
          </h3>
          <p className="mt-1 text-xs text-slate-400">
            {fallbackDescription || cinemaProps.subtitle || descriptor.description}
          </p>
          {explanationNote && (
            <p className="mt-2 rounded border border-amber-500/20 bg-amber-500/10 px-2.5 py-1 text-[11px] text-amber-300">
              {explanationNote}
            </p>
          )}
        </div>

        {/* Subject Badge / Details */}
        {(cinemaProps.subjectName || cinemaProps.clubName) && (
          <div className="flex flex-wrap items-center gap-3 rounded-lg border border-white/5 bg-white/[0.02] p-3 text-xs">
            {cinemaProps.clubName && (
              <div>
                <span className="text-[10px] uppercase tracking-wider text-slate-400">Club</span>
                <p className="font-semibold text-emerald-300">{cinemaProps.clubName}</p>
              </div>
            )}
            {cinemaProps.subjectName && (
              <div className="border-l border-white/10 pl-3">
                <span className="text-[10px] uppercase tracking-wider text-slate-400">
                  {cinemaProps.subjectRole || "Subject"}
                </span>
                <p className="font-semibold text-white">{cinemaProps.subjectName}</p>
              </div>
            )}
            {cinemaProps.overallRating && (
              <div className="border-l border-white/10 pl-3">
                <span className="text-[10px] uppercase tracking-wider text-slate-400">Rating</span>
                <p className="font-bold text-amber-400 font-mono">{cinemaProps.overallRating} OVR</p>
              </div>
            )}
          </div>
        )}

        {/* Key Stats Grid */}
        {cinemaProps.stats && cinemaProps.stats.length > 0 && (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {cinemaProps.stats.map((stat, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-white/5 bg-white/[0.03] p-2.5 text-center"
              >
                <p className="text-[10px] uppercase text-slate-400">{stat.label}</p>
                <p
                  className="mt-0.5 text-sm font-bold font-mono"
                  style={{ color: stat.accent || "#34d399" }}
                >
                  {stat.value}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Quote / Narrative */}
        {cinemaProps.quote && (
          <blockquote className="border-l-2 border-emerald-500/40 pl-3 italic text-xs text-slate-300">
            "{cinemaProps.quote}"
          </blockquote>
        )}

        {/* Action Row */}
        {cinemaProps.onActionClick && cinemaProps.actionLabel && (
          <div className="pt-2">
            <button
              type="button"
              onClick={cinemaProps.onActionClick}
              className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-emerald-500 px-4 py-2 text-xs font-semibold text-slate-950 transition-colors hover:bg-emerald-400"
            >
              <span>{cinemaProps.actionLabel}</span>
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );

  // -------------------------------------------------------------------------
  // 1. CONVENTIONAL 2D FALLBACK PRESENTATION
  // -------------------------------------------------------------------------
  if (shouldRenderFallback) {
    return renderFallbackView("2D COMPANION MODE");
  }

  // -------------------------------------------------------------------------
  // 2. WEBGL HARDWARE-ACCELERATED PRESENTATION
  // -------------------------------------------------------------------------
  const resolvedSceneType: Cinema3DSceneType =
    descriptor.cinemaSceneType || (sceneId as Cinema3DSceneType);

  const CustomRenderer = GtexSceneRegistry.getRenderer(descriptor.id);

  return (
    <div
      ref={containerRef}
      data-testid={testId}
      className={`relative w-full ${className}`}
      data-quality-tier={selectedTier}
      data-target-fps={activeQuality.targetFps}
      data-measured-fps={telemetry.measuredFps}
      data-frame-time-ms={telemetry.frameTimeMs}
      data-average-frame-time-ms={telemetry.averageFrameTimeMs}
      data-p50-frame-time-ms={telemetry.p50FrameTimeMs}
      data-p95-frame-time-ms={telemetry.p95FrameTimeMs}
      data-pixel-ratio={activeQuality.pixelRatio}
      data-context-lost={telemetry.isContextLost ? "true" : "false"}
    >
      {/* Context Loss Overlay Banner */}
      {telemetry.isContextLost && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center rounded-xl bg-slate-950/90 p-6 text-center backdrop-blur-sm">
          <AlertCircle className="h-10 w-10 text-amber-400 mb-2 animate-pulse" />
          <h4 className="text-sm font-bold text-white uppercase tracking-wider">
            WebGL Graphics Context Interrupted
          </h4>
          <p className="mt-1 text-xs text-slate-400 max-w-sm">
            Device graphics context was lost or reset by the browser. Waiting for automatic GPU recovery...
          </p>
        </div>
      )}

      {/* Underlying 3D Stage Delegation via Registry or Props */}
      {(() => {
        // Priority 1: Registered Custom Renderer (Matchday or Non-Matchday)
        if (CustomRenderer) {
          if (descriptor.id === "stadium_match_broadcast" || cinemaProps.matchViewState) {
            return (
              <CustomRenderer
                matchViewState={cinemaProps.matchViewState}
                qualityTier={selectedTier}
                activeQuality={activeQuality}
                telemetry={telemetry}
                sceneId={descriptor.id}
                {...cinemaProps}
              />
            );
          }
          return (
            <CustomRenderer
              sceneId={descriptor.id}
              qualityTier={selectedTier}
              activeQuality={activeQuality}
              telemetry={telemetry}
              sceneProps={cinemaProps.sceneProps}
              {...cinemaProps}
            />
          );
        }

        // Priority 2: Direct custom 3D children
        if (children) {
          return (
            <div className="relative overflow-hidden rounded-xl bg-slate-950">
              {children}
            </div>
          );
        }

        // Priority 3: Authentic Volumetric Cinema Scenes (17 scenes)
        if (descriptor.renderBackend === "cinema_volumetric" || descriptor.cinemaSceneType) {
          return (
            <Cinema3DStage
              scene={resolvedSceneType}
              title={cinemaProps.title || descriptor.title}
              subtitle={cinemaProps.subtitle || descriptor.description}
              {...cinemaProps}
            />
          );
        }

        // Priority 4: Three.js scene without registered renderer — Honest fallback
        // Never pretend it's genuine Three.js by routing to stadium_sponsor
        return renderFallbackView(
          "3D COMPANION MODE (RENDERER PENDING)",
          `A dedicated Three.js renderer is not yet registered for "${descriptor.title}". Operating in companion mode.`
        );
      })()}
    </div>
  );
};
