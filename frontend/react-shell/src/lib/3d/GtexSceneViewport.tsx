/**
 * GTEX Living Football Ecosystem — Shared WebGL 3D Experience Framework
 * GtexSceneViewport: Central presentation viewport with automatic device quality tiering,
 * scene registry lookup, WebGL context lifecycle management, and conventional 2D fallback.
 */

import React, { useMemo, useState, useEffect, useRef } from "react";
import { GtexSceneRegistry, QUALITY_PROFILES } from "./GtexSceneRegistry";
import { DeviceQualityTier, GtexSceneViewportProps } from "./GtexSceneTypes";
import { useQualityTelemetry } from "./qualityTelemetry";
import { EditorialAnnouncement } from "./scenes/EditorialAnnouncement";
import { hasProductSceneLoader, PRODUCT_SCENE_LOADERS } from "./productSceneLoaders";
import type { GtexCustomSceneRenderer } from "./GtexSceneTypes";
import { AlertCircle, ChevronRight, Cpu, Sparkles } from "lucide-react";

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
  qualityPreset,
  forceFallback2D = false,
  forceWebGL = false,
  className = "",
  testId = "gtex-scene-viewport",
  fallbackHeadline,
  fallbackDescription,
  onQualityTelemetryUpdate,
  onQualityTierChange,
  children,
  ...presentation
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hasWebGL, setHasWebGL] = useState<boolean>(true);
  const presetTier = (["low", "medium", "high", "ultra"] as const).includes(qualityPreset as DeviceQualityTier)
    ? (qualityPreset as DeviceQualityTier)
    : undefined;
  const [selectedTier, setSelectedTier] = useState<DeviceQualityTier>(
    explicitQualityTier || presetTier || GtexSceneRegistry.detectDeviceQuality().tier
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
        title: presentation.title || "GTEX 3D Environment",
        category: "club" as const,
        description: "A dedicated renderer is not registered for this scene.",
        renderBackend: "threejs" as const,
        requiredModels: [],
        fallbackMode: "2d_diorama" as const,
        supportsInteraction: false,
        tags: ["general"],
      }
    );
  }, [sceneId, presentation.title]);

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

  const [asyncRenderer, setAsyncRenderer] = useState<GtexCustomSceneRenderer | null>(null);
  const [loaderFailed, setLoaderFailed] = useState(false);
  const [failureSceneId, setFailureSceneId] = useState<string | null>(null);
  const presentationFailed = failureSceneId === descriptor.id;

  useEffect(() => {
    setAsyncRenderer(null);
    setLoaderFailed(false);
    if (GtexSceneRegistry.getRenderer(descriptor.id) || descriptor.renderBackend === "react_editorial") return;
    if (!hasProductSceneLoader(descriptor.id)) return;
    let cancelled = false;
    PRODUCT_SCENE_LOADERS[descriptor.id]()
      .then((renderer) => {
        if (!cancelled) setAsyncRenderer(() => renderer);
      })
      .catch(() => {
        if (!cancelled) setLoaderFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [descriptor.id, descriptor.renderBackend]);

  const editorial = descriptor.renderBackend === "react_editorial";
  const shouldRenderFallback = forceFallback2D || (!hasWebGL && !forceWebGL && !editorial);

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
              {presentation.badgeText || descriptor.category.toUpperCase()}
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
            {fallbackHeadline || presentation.title || descriptor.title}
          </h3>
          <p className="mt-1 text-xs text-slate-400">
            {fallbackDescription || presentation.subtitle || descriptor.description}
          </p>
          {explanationNote && (
            <p className="mt-2 rounded border border-amber-500/20 bg-amber-500/10 px-2.5 py-1 text-[11px] text-amber-300">
              {explanationNote}
            </p>
          )}
        </div>

        {/* Subject Badge / Details */}
        {(presentation.subjectName || presentation.clubName) && (
          <div className="flex flex-wrap items-center gap-3 rounded-lg border border-white/5 bg-white/[0.02] p-3 text-xs">
            {presentation.clubName && (
              <div>
                <span className="text-[10px] uppercase tracking-wider text-slate-400">Club</span>
                <p className="font-semibold text-emerald-300">{presentation.clubName}</p>
              </div>
            )}
            {presentation.subjectName && (
              <div className="border-l border-white/10 pl-3">
                <span className="text-[10px] uppercase tracking-wider text-slate-400">
                  {presentation.subjectRole || "Subject"}
                </span>
                <p className="font-semibold text-white">{presentation.subjectName}</p>
              </div>
            )}
            {presentation.overallRating && (
              <div className="border-l border-white/10 pl-3">
                <span className="text-[10px] uppercase tracking-wider text-slate-400">Rating</span>
                <p className="font-bold text-amber-400 font-mono">{presentation.overallRating} OVR</p>
              </div>
            )}
          </div>
        )}

        {/* Key Stats Grid */}
        {presentation.stats && presentation.stats.length > 0 && (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {presentation.stats.map((stat, idx) => (
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
        {presentation.quote && (
          <blockquote className="border-l-2 border-emerald-500/40 pl-3 italic text-xs text-slate-300">
            "{presentation.quote}"
          </blockquote>
        )}

        {/* Action Row */}
        {presentation.onActionClick && presentation.actionLabel && (
          <div className="pt-2">
            <button
              type="button"
              onClick={presentation.onActionClick}
              className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-emerald-500 px-4 py-2 text-xs font-semibold text-slate-950 transition-colors hover:bg-emerald-400"
            >
              <span>{presentation.actionLabel}</span>
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
  if (editorial) {
    return (
      <div ref={containerRef} data-testid={testId} className={`relative w-full ${className}`} data-render-backend="react_editorial">
        <EditorialAnnouncement
          sceneId={descriptor.id}
          qualityTier={selectedTier}
          activeQuality={activeQuality}
          title={presentation.title || descriptor.title}
          subtitle={presentation.subtitle || descriptor.description}
          {...presentation}
        />
      </div>
    );
  }

  const CustomRenderer = GtexSceneRegistry.getRenderer(descriptor.id) || asyncRenderer;
  const stageHeight = presentation.compact
    ? "min-h-[220px] h-[34vh] md:h-[360px]"
    : "min-h-[280px] h-[42vh] md:h-[480px]";

  return (
    <div
      ref={containerRef}
      data-testid={testId}
      className={`relative w-full ${stageHeight} ${className}`}
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
        if (loaderFailed || presentationFailed) {
          return renderFallbackView(
            "3D COMPANION MODE",
            `The ${descriptor.title} environment could not be loaded. The club record is unchanged.`
          );
        }

        if (CustomRenderer) {
          const failureProps = {
            onPresentationFailure: () => setFailureSceneId(descriptor.id),
          };
          if (descriptor.id === "stadium_match_broadcast" || presentation.matchViewState) {
            return (
              <CustomRenderer
                matchViewState={presentation.matchViewState}
                qualityTier={selectedTier}
                activeQuality={activeQuality}
                telemetry={telemetry}
                sceneId={descriptor.id}
                {...presentation}
                {...failureProps}
              />
            );
          }
          return (
            <CustomRenderer
              sceneId={descriptor.id}
              qualityTier={selectedTier}
              activeQuality={activeQuality}
              telemetry={telemetry}
              sceneProps={presentation.sceneProps}
              {...presentation}
              {...failureProps}
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

        if (!hasProductSceneLoader(descriptor.id)) {
          return renderFallbackView(
            "3D COMPANION MODE (RENDERER PENDING)",
            `A dedicated Three.js renderer is not yet registered for "${descriptor.title}". Operating in companion mode.`
          );
        }

        return (
          <div className="flex h-full min-h-[220px] items-center justify-center rounded-xl border border-white/10 bg-[#07111c] text-xs uppercase tracking-wider text-slate-400">
            Preparing {descriptor.title}
          </div>
        );
      })()}
    </div>
  );
};
