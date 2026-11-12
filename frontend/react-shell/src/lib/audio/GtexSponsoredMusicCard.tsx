/**
 * GTEX Living Football Ecosystem — Sponsored Artist Music Promotion Presentation
 * Reusable visual presentation layer for sponsored song rotation,
 * autoplay unlock CTA, external discovery links, and playback controls.
 */

import React from "react";
import { useSponsoredMusic } from "./GtexAudioContext";
import {
  Disc3,
  ExternalLink,
  Headphones,
  Music2,
  SkipForward,
  Sparkles,
  X,
} from "lucide-react";

export interface GtexSponsoredMusicCardProps {
  className?: string;
  compact?: boolean;
  onDismiss?: () => void;
}

export const GtexSponsoredMusicCard: React.FC<GtexSponsoredMusicCardProps> = ({
  className = "",
  compact = false,
  onDismiss,
}) => {
  const {
    track,
    status,
    progressPercent,
    stop,
  } = useSponsoredMusic();

  if (!track || status === "idle") {
    return null;
  }

  const isPlaying = status === "playing";
  const accentColor = track.accentColor || "#00E676";

  // Browser autoplay waits for the first tap anywhere in the app. There is no play control.
  if (status === "blocked") {
    return (
      <div
        data-testid="gtex-sponsored-music-blocked"
        className={`relative overflow-hidden rounded-2xl border border-amber-500/30 bg-gradient-to-r from-[#0d1424] via-[#090d18] to-[#060910] p-4 text-white shadow-2xl backdrop-blur-md ${className}`}
      >
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-amber-500/40 bg-amber-500/10 text-amber-400">
            <Headphones className="h-6 w-6 animate-pulse" />
          </div>
          <div>
            <span className="flex items-center rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-400 ring-1 ring-amber-500/30">
              <Sparkles className="mr-1 h-3 w-3" />
              GTEX Music Spotlight
            </span>
            <h4 className="mt-0.5 text-sm font-bold text-slate-100">{track.title}</h4>
            <p className="text-xs text-slate-400">by {track.artist} · starts with your next tap</p>
          </div>
        </div>
      </div>
    );
  }

  // Active playing card
  return (
    <div
      data-testid="gtex-sponsored-music-card"
      className={`relative overflow-hidden rounded-2xl border border-emerald-500/20 bg-gradient-to-r from-[#070b14] via-[#05080f] to-[#03050a] p-3 text-white shadow-2xl backdrop-blur-md ${className}`}
      style={{
        boxShadow: `0 8px 32px -4px rgba(0, 0, 0, 0.7), 0 0 24px -6px ${accentColor}25`,
      }}
    >
      {/* Top Progress Line */}
      <div className="absolute left-0 top-0 h-1 w-full bg-white/5">
        <div
          data-testid="music-progress-bar"
          className="h-full transition-all duration-300"
          style={{ width: `${progressPercent}%`, backgroundColor: accentColor }}
        />
      </div>

      <div className="flex items-center justify-between gap-3 pt-1">
        {/* Left: Artwork / Disc Icon & Meta */}
        <div className="flex items-center gap-3 overflow-hidden">
          <div
            className={`relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-slate-900 ${
              isPlaying ? "animate-[spin_8s_linear_infinite]" : ""
            }`}
            style={{ borderColor: `${accentColor}40` }}
          >
            {track.artworkUrl ? (
              <img
                src={track.artworkUrl}
                alt={track.title}
                className="h-full w-full rounded-xl object-cover"
              />
            ) : (
              <Disc3 className="h-6 w-6 text-emerald-400" style={{ color: accentColor }} />
            )}
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="flex items-center rounded bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-emerald-400 ring-1 ring-emerald-500/20">
                <Music2 className="mr-1 h-2.5 w-2.5" />
                {track.sponsorTier || "Sponsored Artist"}
              </span>
              {track.genre && (
                <span className="text-[10px] text-slate-400">· {track.genre}</span>
              )}
            </div>
            <h4 className="truncate text-xs font-bold text-slate-100">{track.title}</h4>
            <p className="truncate text-[11px] text-slate-400">{track.artist}</p>
          </div>
        </div>

        {/* Right: Controls & Discovery Link */}
        <div className="flex items-center gap-1.5">
          {/* Discovery Links */}
          {track.destinationUrl && (
            <a
              href={track.destinationUrl}
              target="_blank"
              rel="noopener noreferrer"
              data-testid="music-destination-link"
              className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[11px] font-medium text-slate-300 transition-colors hover:bg-white/10 hover:text-white"
            >
              <span>Listen</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          )}

          {/* Skip moves off this placement. It does not pause the station. */}
          <button
            type="button"
            onClick={() => stop()}
            data-testid="music-skip-btn"
            className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            title="Skip track"
          >
            <SkipForward className="h-4 w-4" />
          </button>

          {onDismiss && (
            <button
              type="button"
              onClick={onDismiss}
              className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
