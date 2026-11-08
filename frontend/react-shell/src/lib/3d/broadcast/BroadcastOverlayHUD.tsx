/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * TV-Grade Broadcast Overlay HUD (Phases 4, 5, 8 & 10).
 *
 * Provides:
 * 1. Top-left Scorebug (club crests, team names, authoritative score, authoritative clock_minute,
 *    stoppage time, match phase, competition identity, and honest DEMONSTRATION FIXTURE vs LIVE badge).
 * 2. Rich Television Lower-Third Event Graphics (Goals + Assist, Yellow/Red Cards, Substitutions,
 *    Penalties, Saves, Injury Stoppages, Half-Time, Full-Time, VAR Review).
 * 3. Active On-Pitch Player Identification Callout (Shirt Number, Name, Role, Club, Stamina).
 * 4. 2D Tactical Minimap Radar (real-time 22-player dots and ball radar).
 * 5. Full 6-Mode Broadcast Camera Switcher & 2D Tactical Companion Toggle.
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
  Shield,
  ArrowRightLeft,
  AlertTriangle,
  Activity,
} from "lucide-react";
import { ManualCameraMode } from "./CameraDirector";
import {
  InterpolatedMatchState,
  InterpolatedPlayerState,
} from "./SpatialInterpolator";
import {
  SpectatorSafeEventView,
  SpectatorSafeTeamView,
} from "./spectatorContract";
import type { DeviceQualityTier } from "../GtexSceneTypes";

export interface BroadcastOverlayHUDProps {
  matchState: InterpolatedMatchState | null;
  homeTeam: SpectatorSafeTeamView;
  awayTeam: SpectatorSafeTeamView;
  matchLabel: string;
  competitionName?: string;
  isDemonstrationFixture?: boolean;
  activeEvent?: SpectatorSafeEventView | null;
  liveEventBanner?: string;
  replayFallbackMessage?: string | null;
  activeSponsorName?: string | null;
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

const ClubCrestBadge: React.FC<{
  team: SpectatorSafeTeamView;
  testId: string;
}> = ({ team, testId }) => {
  if (team.crest_url) {
    return (
      <img
        data-testid={testId}
        src={team.crest_url}
        alt={`${team.team_name} crest`}
        className="size-6 rounded-md object-contain border border-white/25 bg-slate-900/80 p-0.5 shadow-sm"
      />
    );
  }
  const initials = (team.short_name || team.team_name || "CLB").slice(0, 3).toUpperCase();
  return (
    <span
      data-testid={testId}
      className="inline-flex size-6 items-center justify-center rounded-md border border-white/35 text-[9px] font-black tracking-tighter text-white shadow-sm"
      style={{
        background: `linear-gradient(135deg, ${team.primary_color || "#10b981"} 0%, ${
          team.secondary_color || "#0f172a"
        } 100%)`,
      }}
      title={team.team_name}
    >
      {initials}
    </span>
  );
};

export const BroadcastOverlayHUD: React.FC<BroadcastOverlayHUDProps> = React.memo(({
  matchState,
  homeTeam,
  awayTeam,
  matchLabel,
  competitionName,
  isDemonstrationFixture = false,
  activeEvent = null,
  liveEventBanner,
  replayFallbackMessage = null,
  activeSponsorName = null,
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
      const added = activeEvent?.added_time && activeEvent.added_time > 0 ? `+${activeEvent.added_time}` : "";
      return `${min}${added}'`;
    }
    return "0'";
  }, [matchState?.clock_minute, activeEvent?.added_time]);

  const phaseLabel = useMemo(() => {
    const raw = (matchState?.phase || "open_play").toLowerCase();
    if (raw === "halftime") return "HALF TIME";
    if (raw === "fulltime" || raw === "full_time") return "FULL TIME";
    if (raw === "kickoff") return "KICKOFF";
    if (raw === "set_piece") return "SET PIECE";
    if (matchState?.clock_minute && matchState.clock_minute > 45) return "2ND HALF";
    return "1ST HALF";
  }, [matchState?.phase, matchState?.clock_minute]);

  // Identify the active on-pitch player (ball carrier or primary event actor)
  const identifiedPlayer = useMemo<InterpolatedPlayerState | null>(() => {
    if (!matchState || !matchState.players || matchState.players.length === 0) return null;
    const ownerId = matchState.ball?.owner_player_id;
    if (ownerId) {
      const owner = matchState.players.find((p) => p.player_id === ownerId);
      if (owner) return owner;
    }
    const possessor = matchState.players.find((p) => p.has_possession);
    if (possessor) return possessor;
    if (activeEvent?.primary_player_id) {
      const actor = matchState.players.find((p) => p.player_id === activeEvent.primary_player_id);
      if (actor) return actor;
    }
    const highlighted = matchState.players.find((p) => p.highlighted);
    return highlighted || null;
  }, [matchState, activeEvent?.primary_player_id]);

  // Determine rich lower-third event card formatting
  const eventPresentation = useMemo(() => {
    const bannerText = liveEventBanner?.trim() || matchState?.event_banner || activeEvent?.banner_text || "";
    if (!bannerText && !activeEvent) return null;

    const evType = (activeEvent?.event_type || "").toLowerCase();
    const upperBanner = bannerText.toUpperCase();

    let category = "MATCH EVENT";
    let accentClass = "border-amber-400/60 from-amber-950/95 via-slate-900/95 to-amber-950/95 text-amber-300";
    let badgeBg = "bg-amber-500 text-slate-950";

    if (evType === "goal" || upperBanner.includes("GOAL")) {
      category = "GOAL SCORED";
      accentClass = "border-emerald-400/80 from-emerald-950/95 via-slate-900/95 to-emerald-950/95 text-emerald-300";
      badgeBg = "bg-emerald-400 text-slate-950";
    } else if (evType === "yellow_card" || upperBanner.includes("YELLOW CARD")) {
      category = "DISCIPLINARY • YELLOW CARD";
      accentClass = "border-yellow-400/80 from-yellow-950/95 via-slate-900/95 to-yellow-950/95 text-yellow-300";
      badgeBg = "bg-yellow-400 text-slate-950";
    } else if (evType === "red_card" || upperBanner.includes("RED CARD")) {
      category = "DISCIPLINARY • RED CARD";
      accentClass = "border-red-500/80 from-red-950/95 via-slate-900/95 to-red-950/95 text-red-300";
      badgeBg = "bg-red-500 text-white";
    } else if (evType === "substitution" || upperBanner.includes("SUBSTITUTION")) {
      category = "TACTICAL SUBSTITUTION";
      accentClass = "border-cyan-400/75 from-cyan-950/95 via-slate-900/95 to-cyan-950/95 text-cyan-300";
      badgeBg = "bg-cyan-400 text-slate-950";
    } else if (evType === "penalty" || upperBanner.includes("PENALTY")) {
      category = "PENALTY DECISION";
      accentClass = "border-purple-400/75 from-purple-950/95 via-slate-900/95 to-purple-950/95 text-purple-300";
      badgeBg = "bg-purple-400 text-slate-950";
    } else if (evType === "save" || upperBanner.includes("SAVE")) {
      category = "GOALKEEPER SAVE";
      accentClass = "border-sky-400/75 from-sky-950/95 via-slate-900/95 to-sky-950/95 text-sky-300";
      badgeBg = "bg-sky-400 text-slate-950";
    } else if (evType === "injury" || upperBanner.includes("INJURY")) {
      category = "MEDICAL STOPPAGE";
      accentClass = "border-rose-400/75 from-rose-950/95 via-slate-900/95 to-rose-950/95 text-rose-300";
      badgeBg = "bg-rose-500 text-white";
    } else if (evType === "halftime" || upperBanner.includes("HALF TIME") || upperBanner.includes("HALFTIME")) {
      category = "HALF-TIME CLASSIFICATION";
      accentClass = "border-slate-400/60 from-slate-900/95 via-slate-950/95 to-slate-900/95 text-slate-200";
      badgeBg = "bg-slate-200 text-slate-950";
    } else if (evType === "fulltime" || upperBanner.includes("FULL TIME") || upperBanner.includes("FULLTIME")) {
      category = "FULL-TIME RESULT";
      accentClass = "border-emerald-400/70 from-slate-900/95 via-emerald-950/95 to-slate-900/95 text-emerald-200";
      badgeBg = "bg-emerald-400 text-slate-950";
    } else if (upperBanner.includes("VAR") || upperBanner.includes("OFFSIDE")) {
      category = "VAR / MATCH OFFICIAL REVIEW";
      accentClass = "border-indigo-400/75 from-indigo-950/95 via-slate-900/95 to-indigo-950/95 text-indigo-300";
      badgeBg = "bg-indigo-400 text-slate-950";
    }

    const primaryPlayer = activeEvent?.primary_player_name || null;
    const secondaryPlayer = activeEvent?.secondary_player_name || null;
    const teamName = activeEvent?.team_name || null;
    const primaryShirt =
      activeEvent?.primary_player_id && matchState?.players
        ? matchState.players.find((p) => p.player_id === activeEvent.primary_player_id)?.shirt_number
        : undefined;

    return {
      category,
      accentClass,
      badgeBg,
      headline: bannerText || activeEvent?.commentary || category,
      commentary: activeEvent?.commentary || null,
      primaryPlayer,
      primaryShirt,
      secondaryPlayer,
      teamName,
      evType,
      clockLabel: activeEvent?.clock_label || clockDisplay,
    };
  }, [liveEventBanner, matchState?.event_banner, matchState?.players, activeEvent, clockDisplay]);

  return (
    <div
      data-testid="broadcast-overlay-hud"
      className={`pointer-events-none absolute inset-0 z-20 flex flex-col justify-between p-4 ${className}`}
    >
      {/* =====================================================================
          1. TOP ROW: Scorebug, Competition Identity & Broadcast Controls
          ===================================================================== */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1.5">
          {/* Competition & Fixture Authority Strap */}
          <div className="pointer-events-auto flex items-center gap-2">
            <span className="rounded-md border border-emerald-500/30 bg-slate-950/90 px-2 py-0.5 text-[10px] font-black uppercase tracking-widest text-emerald-400 shadow backdrop-blur-md">
              {competitionName || "GTEX PREMIER BROADCAST"}
            </span>
            <span
              data-testid="fixture-authority-badge"
              className={`rounded-md border px-2 py-0.5 text-[9px] font-black uppercase tracking-wider shadow backdrop-blur-md ${
                isDemonstrationFixture
                  ? "border-amber-400/50 bg-amber-950/90 text-amber-300"
                  : "border-cyan-400/40 bg-cyan-950/90 text-cyan-300"
              }`}
            >
              {isDemonstrationFixture ? "DEMONSTRATION FIXTURE" : "LIVE COMPETITION FEED"}
            </span>
          </div>

          {/* TV Scorebug */}
          <div
            data-testid="broadcast-scorebug"
            className="pointer-events-auto flex items-stretch overflow-hidden rounded-xl border border-white/15 bg-slate-950/90 shadow-2xl backdrop-blur-md"
          >
            {/* Home Team Cell */}
            <div className="flex items-center gap-2 px-3 py-2 border-r border-white/10">
              <ClubCrestBadge team={homeTeam} testId="scorebug-home-crest" />
              <div className="flex flex-col">
                <span className="font-mono text-sm font-black tracking-wider text-white leading-none">
                  {homeTeam.short_name || "HOM"}
                </span>
                <span className="hidden md:inline text-[9px] font-semibold text-slate-400 truncate max-w-[96px]">
                  {homeTeam.team_name}
                </span>
              </div>
              <span
                data-testid="scorebug-home-score"
                className="ml-1.5 text-lg font-black text-emerald-400 font-mono"
              >
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
                    ({Math.floor(matchState.time_seconds / 60)}:
                    {String(Math.floor(matchState.time_seconds % 60)).padStart(2, "0")})
                  </span>
                )}
              </div>
            </div>

            {/* Away Team Cell */}
            <div className="flex items-center gap-2 px-3 py-2 border-l border-white/10">
              <span
                data-testid="scorebug-away-score"
                className="mr-1.5 text-lg font-black text-cyan-400 font-mono"
              >
                {matchState?.away_score ?? 0}
              </span>
              <div className="flex flex-col text-right">
                <span className="font-mono text-sm font-black tracking-wider text-white leading-none">
                  {awayTeam.short_name || "AWY"}
                </span>
                <span className="hidden md:inline text-[9px] font-semibold text-slate-400 truncate max-w-[96px]">
                  {awayTeam.team_name}
                </span>
              </div>
              <ClubCrestBadge team={awayTeam} testId="scorebug-away-crest" />
            </div>
          </div>
        </div>

        {/* Audio, Quality Tier, Replay & Match Theatre Controls */}
        <div className="pointer-events-auto flex flex-wrap items-center justify-end gap-2">
          {isReplayActive && (
            <div
              data-testid="broadcast-replay-badge"
              className="flex items-center gap-1.5 rounded-lg border border-amber-400/60 bg-amber-500/20 px-2.5 py-1.5 text-xs font-black uppercase tracking-wider text-amber-300 shadow-lg backdrop-blur-md animate-pulse"
            >
              <RotateCcw className="size-3.5 text-amber-400" />
              <span>INSTANT REPLAY (0.85x)</span>
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
              {activeSponsorName && (
                <span
                  data-testid="hud-active-sponsor-indicator"
                  className="ml-2 border-l border-white/15 pl-2 text-[10px] font-mono text-amber-300"
                >
                  LED: {activeSponsorName}
                </span>
              )}
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
              {isTheatreMode ? (
                <Minimize2 className="size-3.5" />
              ) : (
                <Maximize2 className="size-3.5 text-emerald-400" />
              )}
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
              {audioMuted ? (
                <VolumeX className="size-4 text-red-400" />
              ) : (
                <Volume2 className="size-4 text-emerald-400" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* =====================================================================
          2. CENTER / LOWER-THIRD: Broadcast Event Card & Replay Fallback Notice
          ===================================================================== */}
      <div className="flex flex-col items-center gap-2 my-auto">
        {replayFallbackMessage && (
          <div
            data-testid="replay-fallback-notice"
            className="pointer-events-none mx-auto max-w-md rounded-xl border border-amber-400/60 bg-slate-950/90 px-4 py-2 text-center shadow-xl backdrop-blur-md"
          >
            <div className="flex items-center justify-center gap-2 text-xs font-black uppercase text-amber-300">
              <AlertTriangle className="size-4 text-amber-400" />
              <span>{replayFallbackMessage}</span>
            </div>
          </div>
        )}

        {eventPresentation && (
          <div
            data-testid="broadcast-event-banner"
            className="pointer-events-none mx-auto max-w-xl transform transition-all"
          >
            <div
              data-testid="broadcast-lower-third-card"
              className={`flex flex-col gap-1 rounded-2xl border bg-gradient-to-r px-5 py-3 shadow-2xl backdrop-blur-md ${eventPresentation.accentClass}`}
            >
              <div className="flex items-center justify-between gap-4">
                <span
                  className={`rounded px-2 py-0.5 text-[10px] font-black uppercase tracking-widest ${eventPresentation.badgeBg}`}
                >
                  {eventPresentation.category}
                </span>
                <span className="font-mono text-xs font-bold text-white/90">
                  {eventPresentation.clockLabel}
                </span>
              </div>

              <div className="flex items-center gap-2.5 pt-0.5">
                {eventPresentation.evType === "substitution" ? (
                  <ArrowRightLeft className="size-5 text-cyan-400 shrink-0" />
                ) : (
                  <Sparkles className="size-5 shrink-0" />
                )}
                <div className="text-sm font-black uppercase tracking-wider text-white">
                  {eventPresentation.headline}
                </div>
              </div>

              {(eventPresentation.primaryPlayer ||
                eventPresentation.secondaryPlayer ||
                eventPresentation.teamName) && (
                <div
                  data-testid="broadcast-event-player-details"
                  className="flex flex-wrap items-center gap-2 border-t border-white/10 pt-1.5 text-[11px] font-semibold text-slate-200"
                >
                  {eventPresentation.teamName && (
                    <span className="rounded bg-white/10 px-1.5 py-0.5 font-bold uppercase text-white">
                      {eventPresentation.teamName}
                    </span>
                  )}
                  {eventPresentation.primaryPlayer && (
                    <span className="font-bold text-emerald-300">
                      {eventPresentation.primaryShirt ? `#${eventPresentation.primaryShirt} ` : ""}
                      {eventPresentation.primaryPlayer}
                    </span>
                  )}
                  {eventPresentation.secondaryPlayer && (
                    <span className="text-slate-300">
                      {eventPresentation.evType === "substitution"
                        ? `OFF: ${eventPresentation.secondaryPlayer}`
                        : `Assist: ${eventPresentation.secondaryPlayer}`}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* =====================================================================
          3. BOTTOM ROW: Minimap Radar, Player Callout & 6-Mode Camera Switcher
          ===================================================================== */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex items-end gap-3">
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

          {/* Active On-Pitch Player Identification Callout */}
          {identifiedPlayer && !minimalHud && (
            <div
              data-testid="active-player-callout"
              className="pointer-events-auto hidden sm:flex items-center gap-2.5 rounded-xl border border-white/15 bg-slate-950/90 px-3 py-2 shadow-2xl backdrop-blur-md"
            >
              <span
                className="flex size-8 items-center justify-center rounded-lg border border-white/30 font-mono text-xs font-black text-white shadow"
                style={{
                  backgroundColor:
                    identifiedPlayer.side === "home"
                      ? homeTeam.primary_color
                      : awayTeam.primary_color,
                }}
              >
                #{identifiedPlayer.shirt_number ?? 10}
              </span>
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-black uppercase tracking-wide text-white">
                    {identifiedPlayer.label}
                  </span>
                  <span className="rounded bg-white/10 px-1.5 py-0.2 text-[9px] font-mono font-bold uppercase text-emerald-300">
                    {identifiedPlayer.role}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[10px] text-slate-400">
                  <span>
                    {identifiedPlayer.side === "home"
                      ? homeTeam.short_name
                      : awayTeam.short_name}
                  </span>
                  {typeof identifiedPlayer.stamina_pct === "number" && (
                    <span className="inline-flex items-center gap-1 font-mono text-[9px] text-emerald-400">
                      <Activity className="size-2.5" />
                      {Math.round(identifiedPlayer.stamina_pct)}%
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Camera Selector & 2D Tactical View Switcher */}
        <div className="pointer-events-auto flex flex-wrap items-center gap-1.5 rounded-xl border border-white/10 bg-slate-950/90 p-1.5 shadow-2xl backdrop-blur-md">
          {/* 6 Broadcast Camera Modes Switcher */}
          <div className="flex flex-wrap items-center gap-1">
            <button
              type="button"
              data-testid="camera-mode-director_auto"
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
              data-testid="camera-mode-broadcast_main"
              onClick={() => onSelectCameraMode("broadcast_main")}
              className={`rounded-lg px-2 py-1 text-[11px] font-bold uppercase tracking-wider transition-colors ${
                cameraMode === "broadcast_main"
                  ? "bg-emerald-500 text-slate-950 shadow-sm"
                  : "text-slate-300 hover:bg-white/10"
              }`}
            >
              BROADCAST
            </button>
            <button
              type="button"
              data-testid="camera-mode-closeup_action"
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
              data-testid="camera-mode-tactical_high"
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
              data-testid="camera-mode-endzone_home"
              onClick={() => onSelectCameraMode("endzone_home")}
              className={`rounded-lg px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider transition-colors ${
                cameraMode === "endzone_home"
                  ? "bg-emerald-500 text-slate-950 shadow-sm"
                  : "text-slate-300 hover:bg-white/10"
              }`}
            >
              ENDZONE
            </button>
            <button
              type="button"
              data-testid="camera-mode-replay_cam"
              onClick={() => onSelectCameraMode("replay_cam")}
              className={`rounded-lg px-2 py-1 text-[11px] font-bold uppercase tracking-wider transition-colors ${
                cameraMode === "replay_cam"
                  ? "bg-emerald-500 text-slate-950 shadow-sm"
                  : "text-slate-300 hover:bg-white/10"
              }`}
            >
              REPLAY CAM
            </button>
            <button
              type="button"
              data-testid="camera-mode-celebration_cam"
              onClick={() => onSelectCameraMode("celebration_cam")}
              className={`rounded-lg px-2 py-1 text-[11px] font-bold uppercase tracking-wider transition-colors ${
                cameraMode === "celebration_cam"
                  ? "bg-emerald-500 text-slate-950 shadow-sm"
                  : "text-slate-300 hover:bg-white/10"
              }`}
            >
              CELEBRATE
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
});
