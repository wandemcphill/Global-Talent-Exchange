/**
 * GTEX Living Football Ecosystem — Central Audio Architecture Types
 * Defines audio channels, priority ladder, ducking policies, session state,
 * sponsored track models, and advertising measurement events.
 */

export type AudioChannelType =
  | "commentary"      // Priority 100: Live match commentary (Highest)
  | "conversations"   // Priority 90:  Executive meetings, boardroom, negotiations
  | "sfx"             // Priority 50:  UI sound effects, whistles, celebration bursts
  | "ambience"        // Priority 40:  Stadium crowd roar, training ground ambience
  | "environment"     // Priority 30:  Environmental 3D soundscapes, weather
  | "user_music"      // Priority 20:  User-selected background track
  | "sponsored_music"; // Priority 10:  Sponsored artist music promotion

export const CHANNEL_PRIORITIES: Record<AudioChannelType, number> = {
  commentary: 100,
  conversations: 90,
  sfx: 50,
  ambience: 40,
  environment: 30,
  user_music: 20,
  sponsored_music: 10,
};

export interface DuckingRule {
  targetChannel: AudioChannelType;
  duckVolumeFactor: number; // e.g. 0.15 = drop to 15% volume
  fadeDurationMs: number;   // transition time in ms
}

/** Explicit ducking rules triggered when high-priority channels become active */
export const DUCKING_POLICIES: Record<string, DuckingRule[]> = {
  commentary_active: [
    { targetChannel: "sponsored_music", duckVolumeFactor: 0.15, fadeDurationMs: 350 },
    { targetChannel: "user_music", duckVolumeFactor: 0.20, fadeDurationMs: 350 },
    { targetChannel: "ambience", duckVolumeFactor: 0.25, fadeDurationMs: 400 },
    { targetChannel: "environment", duckVolumeFactor: 0.20, fadeDurationMs: 400 },
  ],
  conversations_active: [
    { targetChannel: "sponsored_music", duckVolumeFactor: 0.10, fadeDurationMs: 300 },
    { targetChannel: "user_music", duckVolumeFactor: 0.15, fadeDurationMs: 300 },
    { targetChannel: "ambience", duckVolumeFactor: 0.10, fadeDurationMs: 300 },
    { targetChannel: "environment", duckVolumeFactor: 0.15, fadeDurationMs: 300 },
  ],
};

export type AudioTelemetryEventType =
  | "play_requested"
  | "play_started"
  | "milestone_25"
  | "milestone_50"
  | "milestone_75"
  | "completed"
  | "skipped"
  | "play_blocked"
  | "interrupted"
  | "muted";

export interface SponsoredTrackView {
  campaignId: string;
  title: string;
  artist: string;
  artistHandle?: string;
  genre?: string;
  album?: string;
  artworkUrl?: string;
  audioUrl?: string;
  destinationUrl: string;
  rightsHolder?: string;
  rightsVerified: boolean;
  sponsorTier?: "Headliner" | "Spotlight" | "Rising Star" | "Official Theme";
  accentColor?: string;
  notes?: number[]; // WebAudio procedural note sequence fallback
  discoveryLinks?: {
    spotify?: string;
    appleMusic?: string;
    audiomack?: string;
    youtube?: string;
  };
}

export interface AudioSessionPreferences {
  masterVolume: number;
  isMasterMuted: boolean;
  channelVolumes: Record<AudioChannelType, number>;
  channelMuted: Record<AudioChannelType, boolean>;
  allowSponsoredMusic: boolean;
}

export interface AudioSessionSnapshot {
  masterVolume: number;
  isMasterMuted: boolean;
  effectiveMasterGain: number;
  channelVolumes: Record<AudioChannelType, number>;
  channelMuted: Record<AudioChannelType, boolean>;
  activeChannels: AudioChannelType[];
  isAutoplayBlocked: boolean;
  hasUserInteracted: boolean;
  currentSponsoredTrack: SponsoredTrackView | null;
  sponsoredPlaybackStatus: "idle" | "playing" | "paused" | "ducked" | "interrupted" | "blocked" | "completed";
  playbackProgressMs: number;
  playbackDurationMs: number;
  foregroundAudibleSeconds: number;
  interruptedReason?: string | null;
}
