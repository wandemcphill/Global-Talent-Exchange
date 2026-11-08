/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * TV-Grade Broadcast Overlay HUD.
 *
 * Provides:
 * 1. Top-left Scorebug (scores, clock, stoppage time, phase, live indicator).
 * 2. Event Toast & Commentary Ticker (goals, cards, VAR alerts, commentary).
 * 3. 2D Tactical Minimap (real-time player dots and ball radar).
 * 4. Camera Mode Switcher & 2D Tactical Fallback Toggle.
 */

import React, { useMemo } from "react";
import {
  Layers,
  Tv,
  Eye,
  Volume2,
  VolumeX,
  Sparkles,
  Maximize2,
  Minimize2,
  RotateCcw,
  Sliders,
} from "lucide-react";
import { ManualCameraMode } from "./CameraDirector";
import {
  InterpolatedMatchState,
} from "./SpatialInterpolator";
import { SpectatorSafeTeamView } from "./spectatorContract";
import type { DeviceQualityTier } from "../GtexSceneTypes";

export interface BroadcastOverlayHUDProps {
  matchState: InterpolatedMatchState | null;
  homeTeam: SpectatorSafeTeamView;
  awayTeam: SpectatorSafeTeamView;
  matchLabel: string;
  liveEventBanner?: string;
  isLive?: boolean;
  viewerCount?: number;
  cameraMode: ManualCameraMode;
  onSelectCameraMode: (mode: ManualCameraMode) => void;
  onToggle2DFallback: () => void;
  is2DActive?: boolean;
  audioMuted?: boolean;
  onToggleAudio?: () => void;
  qualityTier?: DeviceQualityTier;
  onSelectQualityTier?: (tier: "high" | "medium" | "low") => void;
  isTheatreMode?: boolean;
  onToggleTheatreMode?: () => void;
  minimalHud?: boolean;
  onToggleMinimalHud?: () => void;
  isReplayActive?: boolean;
  onTriggerReplay?: () => void;
  className?: string;
}

export const BroadcastOverlayHUD: React.FC<BroadcastOverlayHUDProps> = ({
  matchState,
  homeTeam,
  awayTeam,
  matchLabel,
  liveEventBanner,
  isLive = true,
  viewerCount,
  cameraMode,
  onSelectCameraMode,
  onToggle2DFallback,
  is2DActive = false,
  audioMuted = false,
  onToggleAudio,
  qualityTier = "high",
  onSelectQualityTier,
  isTheatreMode = false,
  onToggleTheatreMode,
  minimalHud = false,
  onToggleMinimalHud,
  isReplayActive = false,
  onTriggerReplay,
  className = "",
}) => {
  const clockDisplay = useMemo(() => {
    if (!matchState) return "0'";
    if (typeof matchState.clock_minute === "number") {
      const min = Math.max(0, Math.floor(matchState.clock_minute));
      return `${min}'`;
    }
    return "0'";
  }, [matchState?.clock_minute]);

  const phaseLabel = useMemo(() => {
    const raw = (matchState?.phase || "open_play").toLowerCase();
    if (raw === "halftime") return "HALF TIME";
    if (raw === "fulltime" || raw === "full_time") return "FULL TIME";
    if (matchState?.clock_minute && matchState.clock_minute > 45) return "2ND HALF";
    return "1ST HALF";
  }, [matchState?.phase, matchState?.clock_minute]);

  return (
    <div
      data-testid="broadcast-overlay-hud"
      className={`pointer-events-none absolute inset-0 z-20 flex flex-col justify-between p-4 ${className}`}
    >
      {/* =====================================================================
          1. TOP ROW: Scorebug & Match Status
          ===================================================================== */}
      <div className="flex items-start justify-between gap-3">
        {/* TV Scorebug */}
        <div className="pointer-events-auto flex items-stretch overflow-hidden rounded-xl border border-white/15 bg-slate-950/85 shadow-2xl backdrop-blur-md">
          {/* Home Team Cell */}
          <div className="flex items-center gap-2 px-3 py-2 border-r border-white/10">
            <span
              className="size-3 rounded-full border border-white/40 shadow-sm"
              style={{ backgroundColor: homeTeam.primary_color }}
            />
            <span className="font-mono text-sm font-black tracking-wider text-white">
              {homeTeam.short_name || "HOM"}
            </span>
            <span className="ml-1 text-base font-black text-emerald-400">
              {matchState?.home_score ?? 0}
            </span>
          </div>

          {/* Score Divider / Clock Cell */}
          <div className="flex flex-col items-center justify-center bg-white/[0.04] px-3.5 py-1 text-center">
            <div className="flex items-center gap-1.5">
              {isLive ? (
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-red-500" />
                </span>
              ) : (
                <Tv className="size-3 text-cyan-400" />
              )}
              <span
                data-testid="authoritative-match-clock"
                className="font-mono text-xs font-bold tracking-tight text-white"
              >
                {clockDisplay}
              </span>
            </div>
            <div className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider text-slate-400">
              <span>{phaseLabel}</span>
              {matchState && typeof matchState.time_seconds === "number" && (
                <span
                  data-testid="local-animation-clock"
                  className="text-slate-500 font-mono text-[8px]"
                  title="Local render interpolation timeline"
                >
                  ({Math.floor(matchState.time_seconds / 60)}:{String(Math.floor(matchState.time_seconds % 60)).padStart(2, "0")})
                </span>
              )}
            </div>
          </div>

          {/* Away Team Cell */}
          <div className="flex items-center gap-2 px-3 py-2 border-l border-white/10">
            <span className="mr-1 text-base font-black text-cyan-400">
              {matchState?.away_score ?? 0}
            </span>
            <span className="font-mono text-sm font-black tracking-wider text-white">
              {awayTeam.short_name || "AWY"}
            </span>
            <span
              className="size-3 rounded-full border border-white/40 shadow-sm"
              style={{ backgroundColor: awayTeam.primary_color }}
            />
          </div>
        </div>

        {/* Audio, Quality Tier, Replay & Match Theatre Controls */}
        <div className="pointer-events-auto flex flex-wrap items-center gap-2">
          {isReplayActive && (
            <div
              data-testid="broadcast-replay-badge"
              className="flex items-center gap-1.5 rounded-lg border border-amber-400/60 bg-amber-500/20 px-2.5 py-1.5 text-xs font-black uppercase tracking-wider text-amber-300 shadow-lg backdrop-blur-md animate-pulse"
            >
              <RotateCcw className="size-3.5 text-amber-400" />
              <span>INSTANT REPLAY</span>
            </div>
          )}
          {typeof viewerCount === "number" && viewerCount > 0 && !minimalHud && (
            <div className="hidden md:flex items-center gap-1.5 rounded-lg border border-white/10 bg-slate-950/80 px-2.5 py-1.5 text-xs font-mono text-slate-300 backdrop-blur-md">
              <Eye className="size-3.5 text-emerald-400" />
              <span>{viewerCount >= 1000 ? `${(viewerCount / 1000).toFixed(1)}k` : viewerCount}</span>
            </div>
          )}
          {!minimalHud && (
            <div className="hidden sm:block rounded-lg border border-white/10 bg-slate-950/80 px-3 py-1.5 text-xs font-semibold text-slate-300 backdrop-blur-md">
              <span className="text-emerald-400 font-bold">GTEX ARENA</span> · {matchLabel}
            </div>
          )}
          {onSelectQualityTier && !minimalHud && (
            <div
              data-testid="quality-profile-selector"
              className="hidden sm:flex items-center gap-0.5 rounded-lg border border-white/15 bg-slate-950/85 p-0.5 text-[10px] font-bold uppercase backdrop-blur-md"
              title="Graphics Quality Profile"
            >
              <Sliders className="size-3 text-slate-400 mx-1" />
              {(["high", "medium", "low"] as const).map((tier) => (
                <button
                  key={tier}
                  type="button"
                  data-testid={`quality-tier-${tier}`}
                  onClick={() => onSelectQualityTier(tier)}
                  className={`rounded px-1.5 py-0.5 transition-colors ${
                    qualityTier === tier
                      ? "bg-emerald-500 text-slate-950 font-black"
                      : "text-slate-300 hover:bg-white/10"
                  }`}
                >
                  {tier === "medium" ? "MED" : tier.toUpperCase()}
                </button>
              ))}
            </div>
          )}
          {onTriggerReplay && (
            <button
              type="button"
              data-testid="trigger-replay-button"
              onClick={onTriggerReplay}
              className={`flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-[11px] font-bold uppercase tracking-wider transition-colors backdrop-blur-md ${
                isReplayActive
                  ? "border-amber-400 bg-amber-500 text-slate-950"
                  : "border-white/15 bg-slate-950/80 text-amber-300 hover:bg-white/10"
              }`}
              title="Instant 8s Action Replay"
            >
              <RotateCcw className="size-3.5" />
              <span className="hidden md:inline">{isReplayActive ? "LIVE" : "REPLAY"}</span>
            </button>
          )}
          {onToggleMinimalHud && (
            <button
              type="button"
              data-testid="toggle-minimal-hud-button"
              onClick={onToggleMinimalHud}
              className={`rounded-lg border px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider transition-colors backdrop-blur-md ${
                minimalHud
                  ? "border-cyan-400/60 bg-cyan-500/20 text-cyan-300"
                  : "border-white/10 bg-slate-950/80 text-slate-300 hover:bg-white/10"
              }`}
              title="Toggle Clean Broadcast HUD"
            >
              {minimalHud ? "FULL HUD" : "CLEAN HUD"}
            </button>
          )}
          {onToggleTheatreMode && (
            <button
              type="button"
              data-testid="toggle-theatre-mode-button"
              onClick={onToggleTheatreMode}
              className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11px] font-bold uppercase tracking-wider transition-colors backdrop-blur-md ${
                isTheatreMode
                  ? "border-emerald-400 bg-emerald-500 text-slate-950"
                  : "border-white/15 bg-slate-950/80 text-white hover:bg-white/10"
              }`}
              title={isTheatreMode ? "Exit Full-Screen Match Theatre" : "Enter Full-Screen 16:9 Match Theatre"}
            >
              {isTheatreMode ? <Minimize2 className="size-3.5" /> : <Maximize2 className="size-3.5 text-emerald-400" />}
              <span>{isTheatreMode ? "EXIT THEATRE" : "THEATRE"}</span>
            </button>
          )}
          {onToggleAudio && (
            <button
              type="button"
              onClick={onToggleAudio}
              className="flex size-8 items-center justify-center rounded-lg border border-white/10 bg-slate-950/80 text-white hover:bg-white/10 transition-colors"
              title={audioMuted ? "Unmute Match Audio" : "Mute Match Audio"}
            >
              {audioMuted ? <VolumeX className="size-4 text-red-400" /> : <Volume2 className="size-4 text-emerald-400" />}
            </button>
          )}
        </div>
      </div>

      {/* =====================================================================
          2. CENTER / LOWER-THIRD: Event Toast / Commentary Ticker
          ===================================================================== */}
      {(liveEventBanner?.trim() || matchState?.event_banner) && (
        <div
          data-testid="broadcast-event-banner"
          className="pointer-events-none mx-auto max-w-lg transform transition-all animate-bounce"
        >
          <div className="flex items-center gap-3 rounded-full border border-amber-400/50 bg-gradient-to-r from-amber-950/95 via-slate-900/95 to-amber-950/95 px-5 py-2.5 shadow-2xl backdrop-blur-md text-white">
            <Sparkles className="size-5 text-amber-400 shrink-0" />
            <div className="text-xs font-bold uppercase tracking-wider text-amber-300">
              {liveEventBanner?.trim() || matchState?.event_banner}
            </div>
          </div>
        </div>
      )}

      {/* =====================================================================
          3. BOTTOM ROW: Minimap & Camera / 2D Toggles
          ===================================================================== */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        {/* Tactical Minimap Radar (105m x 68m pitch miniature) */}
        <div
          data-testid="tactical-minimap-radar"
          className={`pointer-events-auto relative h-20 w-32 overflow-hidden rounded-lg border border-white/20 bg-emerald-950/80 shadow-2xl backdrop-blur-md transition-opacity ${
            minimalHud ? "opacity-45 hover:opacity-100" : "opacity-100"
          }`}
        >
          {/* Halfway line & center circle */}
          <div className="absolute inset-y-0 left-1/2 w-px bg-white/30" />
          <div className="absolute left-1/2 top-1/2 size-6 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/30" />

          {/* 22 Player Dots */}
          {matchState?.players.map((p) => {
            // Map 3D metric coords [-52.5..52.5, -34.0..34.0] to minimap percentages [0..100%]
            const leftPct = ((p.position3D[0] + 52.5) / 105.0) * 100;
            const topPct = ((p.position3D[2] + 34.0) / 68.0) * 100;
            const color = p.side === "home" ? homeTeam.primary_color : awayTeam.primary_color;

            return (
              <div
                key={p.player_id}
                className="absolute size-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full shadow-sm"
                style={{
                  left: `${leftPct}%`,
                  top: `${topPct}%`,
                  backgroundColor: color,
                }}
              />
            );
          })}

          {/* Ball Marker */}
          {matchState?.ball && (
            <div
              className="absolute size-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white ring-1 ring-amber-400"
              style={{
                left: `${((matchState.ball.position3D[0] + 52.5) / 105.0) * 100}%`,
                top: `${((matchState.ball.position3D[2] + 34.0) / 68.0) * 100}%`,
              }}
            />
          )}

          <div className="absolute bottom-1 right-1 text-[8px] font-mono font-bold uppercase tracking-wider text-emerald-300/80">
            RADAR
          </div>
        </div>

        {/* Camera Selector & 2D Tactical View Switcher */}
        <div className="pointer-events-auto flex flex-wrap items-center gap-1.5 rounded-xl border border-white/10 bg-slate-950/90 p-1.5 shadow-2xl backdrop-blur-md">
          {/* Camera Presets Switcher */}
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => onSelectCameraMode("director_auto")}
              className={`rounded-lg px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider transition-colors ${
                cameraMode === "director_auto"
                  ? "bg-emerald-500 text-slate-950 shadow-sm"
                  : "text-slate-300 hover:bg-white/10"
              }`}
            >
              DIRECTOR
            </button>
            <button
              type="button"
              onClick={() => onSelectCameraMode("closeup_action")}
              className={`rounded-lg px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider transition-colors ${
                cameraMode === "closeup_action"
                  ? "bg-emerald-500 text-slate-950 shadow-sm"
                  : "text-slate-300 hover:bg-white/10"
              }`}
            >
              ACTION CAM
            </button>
            <button
              type="button"
              onClick={() => onSelectCameraMode("tactical_high")}
              className={`rounded-lg px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider transition-colors ${
                cameraMode === "tactical_high"
                  ? "bg-emerald-500 text-slate-950 shadow-sm"
                  : "text-slate-300 hover:bg-white/10"
              }`}
            >
              TACTICAL
            </button>
            <button
              type="button"
              onClick={() => onSelectCameraMode("endzone_home")}
              className={`rounded-lg px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider transition-colors ${
                cameraMode === "endzone_home"
                  ? "bg-emerald-500 text-slate-950 shadow-sm"
                  : "text-slate-300 hover:bg-white/10"
              }`}
            >
              ENDZONE
            </button>
          </div>

          <div className="h-4 w-px bg-white/20 mx-1" />

          {/* 2D Companion Switcher */}
          <button
            type="button"
            data-testid="toggle-2d-companion-button"
            onClick={onToggle2DFallback}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1 text-[11px] font-bold uppercase tracking-wider transition-colors ${
              is2DActive
                ? "bg-cyan-500 text-slate-950"
                : "bg-white/10 text-white hover:bg-white/20"
            }`}
          >
            <Layers className="size-3.5" />
            <span>{is2DActive ? "3D BROADCAST" : "2D PITCH"}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
