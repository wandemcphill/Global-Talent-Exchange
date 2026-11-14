import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useLocation } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { gtexAudio } from "@/lib/audio";
import { commercialApi, MusicRotationTrack, resolveCommercialMediaUrl } from "@/lib/commercial/api";
import {
  Disc3,
  ExternalLink,
  Headphones,
  Info,
  Pause,
  Play,
  Shuffle,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
  X,
} from "lucide-react";

type PublicMusicPromotion = {
  campaign_id: string;
  brand_name: string;
  headline: string;
  description: string;
  destination_url: string;
  creative_url?: string | null;
  target_type: "track" | "artist" | "playlist";
  target_id: string;
  track_title?: string | null;
  artist_name?: string | null;
  playlist_name?: string | null;
  genre?: string | null;
};

function reportMusicPromotionEvent(
  campaignId: string,
  eventType:
    | "impression"
    | "click"
    | "play_started"
    | "qualified_listen"
    | "completed"
    | "skipped"
    | "muted",
) {
  const key = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  void api.post("/public/ads/events", {
    campaign_id: campaignId,
    event_type: eventType,
    idempotency_key: `trax-${eventType}-${key}`,
    metadata_json: { placement: "music_rotation" },
  }).catch(() => undefined);
}

export type GtexAudioContextType =
  | "home"
  | "club"
  | "market"
  | "competition"
  | "matchday"
  | "world"
  | "celebration";

export interface GtexTraxItem {
  id: string;
  title: string;
  artist: string;
  artistHandle: string;
  album: string;
  genre: string;
  region: string;
  bpm: number;
  duration: string;
  isPromoted: boolean;
  sponsorTier: "Headliner" | "Spotlight" | "Rising Star" | "Official Theme";
  artistBio: string;
  contexts: GtexAudioContextType[];
  spotifyUrl?: string;
  appleMusicUrl?: string;
  audiomackUrl?: string;
  youtubeUrl?: string;
  hypeCount: number;
  streamImpressions: number;
  isGoalAnthem: boolean;
  isWalkoutAnthem: boolean;
  licence: string;
  source: string;
  provenance: string;
  accentColor: string;
  notes: number[];
  audioUrl?: string;
  artworkUrl?: string | null;
  campaignId?: string;
  explicitContent?: boolean;
}

const PUBLIC_DOMAIN_BED = {
  artist: "Kevin MacLeod",
  artistHandle: "incompetech.com",
  album: "GTEX public-domain bed",
  region: "Public domain",
  isPromoted: false,
  sponsorTier: "Official Theme" as const,
  artistBio:
    "Public-domain instrumental cleared for continuous GTEX playback. Advertiser tracks are inserted into this rotation when a campaign is live.",
  contexts: ["home", "club", "market", "competition", "matchday", "world", "celebration"] as GtexAudioContextType[],
  hypeCount: 0,
  streamImpressions: 0,
  isGoalAnthem: false,
  isWalkoutAnthem: false,
  licence: "CC0 1.0 Public Domain",
  source: "Kevin MacLeod (incompetech.com) via the FreePD public-domain archive",
  provenance: "CC0. No attribution required. Not a substitute for a paid artist campaign.",
  notes: [220, 261.63, 293.66, 329.63, 392.0, 329.63, 293.66, 261.63],
};

function bedTrack(
  file: string,
  title: string,
  genre: string,
  bpm: number,
  duration: string,
  accentColor: string,
): GtexTraxItem {
  return {
    ...PUBLIC_DOMAIN_BED,
    id: `gtex-bed-${file.replace(/\.mp3$/, "")}`,
    title,
    genre,
    bpm,
    duration,
    accentColor,
    audioUrl: `/audio/trax/${file}`,
  };
}

export const GTEX_TRAX_CATALOGUE: GtexTraxItem[] = [
  bedTrack("advertime.mp3", "Advertime", "Uplifting", 120, "2:40", "#00E87A"),
  bedTrack("and-just-like-that.mp3", "And Just Like That", "Uplifting", 118, "1:30", "#38BDF8"),
  bedTrack("bar-brawl.mp3", "Bar Brawl", "Uplifting", 140, "1:20", "#FFB800"),
  bedTrack("city-sunshine.mp3", "City Sunshine", "Uplifting", 112, "3:20", "#F59E0B"),
  bedTrack("fresh-focus.mp3", "Fresh Focus", "Uplifting", 108, "2:30", "#10B981"),
  bedTrack("from-page-to-practice.mp3", "From Page to Practice", "Uplifting", 116, "1:40", "#22D3EE"),
  bedTrack("funshine.mp3", "Funshine", "Uplifting", 124, "3:10", "#F97316"),
  bedTrack("happy-whistling-ukulele.mp3", "Happy Whistling Ukulele", "Uplifting", 114, "2:20", "#A3E635"),
  bedTrack("inspiration.mp3", "Inspiration", "Uplifting", 100, "2:45", "#A855F7"),
  bedTrack("inventing-flight.mp3", "Inventing Flight", "Uplifting", 128, "1:35", "#38BDF8"),
  bedTrack("motions.mp3", "Motions", "Uplifting", 122, "2:15", "#00E87A"),
  bedTrack("3-am-west-end.mp3", "3 am West End", "Electronic", 118, "2:50", "#6366F1"),
  bedTrack("arpent.mp3", "Arpent", "Electronic", 110, "3:05", "#8B5CF6"),
  bedTrack("backbeat.mp3", "Backbeat", "Electronic", 126, "1:15", "#EC4899"),
  bedTrack("beat-one.mp3", "Beat One", "Electronic", 120, "2:40", "#14B8A6"),
  bedTrack("bit-bit-loop.mp3", "Bit Bit Loop", "Electronic", 130, "1:45", "#F43F5E"),
  bedTrack("goodnightmare.mp3", "Goodnightmare", "Electronic", 108, "3:30", "#64748B"),
  bedTrack("hear-what-they-say.mp3", "Hear What They Say", "Electronic", 116, "2:35", "#0EA5E9"),
  bedTrack("meditating-beat.mp3", "Meditating Beat", "Electronic", 104, "3:00", "#84CC16"),
];

function inferContextFromPath(pathname: string): GtexAudioContextType {
  if (pathname.includes("/matches/")) return "matchday";
  if (pathname.includes("/market") || pathname.includes("/coin-traders") || pathname.includes("/finance") || pathname.includes("/transfer")) {
    return "market";
  }
  if (pathname.includes("/competitions") || pathname.includes("/national") || pathname.includes("/jackpot")) {
    return "competition";
  }
  if (pathname.includes("/regen-world")) return "world";
  if (pathname.includes("/awards") || pathname.includes("/showroom")) return "celebration";
  if (pathname.includes("/squad") || pathname.includes("/clubs") || pathname.includes("/academy")) {
    return "club";
  }
  return "home";
}

const TRAX_PLAY_STORAGE_KEY = "gtex_trax_is_playing";
const TRAX_MUTE_STORAGE_KEY = "gtex_trax_is_muted";
const TRAX_VOLUME_STORAGE_KEY = "gtex_trax_volume";

function formatTrackTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
}

export function GtexTraxTopBarControl() {
  const { pathname } = useLocation();
  const [isPlaying, setIsPlaying] = useState<boolean>(() => {
    try {
      const saved = typeof window !== "undefined" ? window.localStorage?.getItem(TRAX_PLAY_STORAGE_KEY) : null;
      return saved === null ? true : saved === "true";
    } catch {
      return true;
    }
  });
  const [isMuted, setIsMuted] = useState<boolean>(() => {
    try {
      const saved = typeof window !== "undefined" ? window.localStorage?.getItem(TRAX_MUTE_STORAGE_KEY) : null;
      return saved === "true";
    } catch {
      return false;
    }
  });
  const [volume, setVolume] = useState<number>(() => {
    try {
      const saved = typeof window !== "undefined" ? window.localStorage?.getItem(TRAX_VOLUME_STORAGE_KEY) : null;
      const parsed = saved !== null ? Number(saved) : 0.85;
      return Number.isFinite(parsed) && parsed >= 0 && parsed <= 1 ? parsed : 0.85;
    } catch {
      return 0.85;
    }
  });
  const [modalOpen, setModalOpen] = useState(false);
  const [showCredits, setShowCredits] = useState(false);
  const [showToastChyron, setShowToastChyron] = useState(false);
  const [currentTimeSeconds, setCurrentTimeSeconds] = useState(0);
  const [durationSeconds, setDurationSeconds] = useState(180);
  const [autoplayBlocked, setAutoplayBlocked] = useState(false);
  const [isCommentaryActive, setIsCommentaryActive] = useState(false);
  const [frequencyCapPerSession, setFrequencyCapPerSession] = useState(6);
  const [failedTrackIds, setFailedTrackIds] = useState<string[]>([]);

  const [activeContext, setActiveContext] = useState<GtexAudioContextType>("home");
  const [currentTrackIndex, setCurrentTrackIndex] = useState(0);

  const [hypedIds, setHypedIds] = useState<Record<string, boolean>>({});
  const [tipsByTrack, setTipsByTrack] = useState<Record<string, number>>({});
  const [clicksByTrack, setClicksByTrack] = useState<Record<string, number>>({});
  const [goalAnthemId, setGoalAnthemId] = useState<string>(GTEX_TRAX_CATALOGUE[0].id);
  const [sponsoredPromotions, setSponsoredPromotions] = useState<PublicMusicPromotion[]>([]);
  const [rotationTracks, setRotationTracks] = useState<GtexTraxItem[]>([]);
  const reportedPromotionImpressions = useRef(new Set<string>());
  const promoAudioRef = useRef<HTMLAudioElement | null>(null);
  const qualifiedReportedForPlayRef = useRef<string | null>(null);
  const sessionPlayCountsRef = useRef<Record<string, number>>({});
  const lastAutoplayUnlockAtRef = useRef<number>(0);

  const audioCtxRef = useRef<AudioContext | null>(null);
  const stepRef = useRef(0);

  // Interleave promoted tracks from GTEX Commercial Music Network into fair rotation,
  // filtering out unavailable/deleted tracks and tracks that hit their session frequency cap.
  const combinedCatalogue = React.useMemo(() => {
    const failedSet = new Set(failedTrackIds);
    const activeRotation = rotationTracks.filter((item) => {
      if (failedSet.has(item.id)) return false;
      const key = item.campaignId || item.id;
      const plays = sessionPlayCountsRef.current[key] || 0;
      return plays < frequencyCapPerSession;
    });
    const activeBed = GTEX_TRAX_CATALOGUE.filter((item) => !failedSet.has(item.id));
    const fallbackBed = activeBed.length > 0 ? activeBed : GTEX_TRAX_CATALOGUE;

    if (activeRotation.length === 0) return fallbackBed;
    const merged: GtexTraxItem[] = [];
    const maxLen = Math.max(activeRotation.length, fallbackBed.length);
    for (let i = 0; i < maxLen; i += 1) {
      if (i < activeRotation.length) merged.push(activeRotation[i]);
      if (i < fallbackBed.length) merged.push(fallbackBed[i]);
    }
    return merged;
  }, [rotationTracks, failedTrackIds, frequencyCapPerSession]);

  const currentTrack = combinedCatalogue[currentTrackIndex % combinedCatalogue.length] || GTEX_TRAX_CATALOGUE[0];
  const currentTrackPromotion = sponsoredPromotions.find((promotion) =>
    (promotion.target_type === "track" && promotion.target_id === currentTrack.id) ||
    (promotion.target_type === "artist" && (promotion.artist_name || "").toLowerCase() === currentTrack.artist.toLowerCase()) ||
    (promotion.target_type === "playlist" && (promotion.playlist_name || "").toLowerCase() === currentTrack.album.toLowerCase())
  ) || null;
  const isCurrentSponsored = Boolean(currentTrack.isPromoted || currentTrackPromotion);

  const isMatchdayDucked = activeContext === "matchday" || isCommentaryActive;
  const effectiveGain = isMuted || isCommentaryActive
    ? 0
    : Math.max(0, Math.min(1, volume * (activeContext === "matchday" ? 0.2 : 1.0)));

  // Subscribe to Central Audio Session Manager to pause/duck during active match commentary
  useEffect(() => {
    return gtexAudio.subscribe((snapshot) => {
      setIsCommentaryActive(Boolean(snapshot.activeChannels?.includes("commentary")));
    });
  }, []);

  // Load approved, in-window GTEX TRAX partner promotions & uploaded Music Network rotation tracks.
  useEffect(() => {
    let cancelled = false;
    api.get("/public/ads/music/promotions")
      .then((response) => {
        if (!cancelled) setSponsoredPromotions(Array.isArray(response.data?.promotions) ? response.data.promotions : []);
      })
      .catch(() => {
        if (!cancelled) setSponsoredPromotions([]);
      });

    commercialApi.getMusicRotationFeed(20)
      .then((feed) => {
        if (cancelled || !Array.isArray(feed?.tracks)) return;
        const cap = Number(feed?.rotation_policy?.frequency_cap_per_session);
        if (Number.isFinite(cap) && cap > 0) {
          setFrequencyCapPerSession(cap);
        }
        const mapped: GtexTraxItem[] = feed.tracks.map((t: MusicRotationTrack) => ({
          id: t.track_id,
          title: t.title,
          artist: t.artist,
          artistHandle: `@${t.artist.toLowerCase().replace(/[^a-z0-9]+/g, "") || "gtexartist"}`,
          album: "GTEX Commercial Music Network",
          genre: t.genre || "Afrobeats / Promoted",
          region: "Nigeria · Global",
          bpm: 120,
          duration: "3:00",
          isPromoted: true,
          sponsorTier: "Headliner",
          artistBio: t.sponsored_disclosure || "Promoted on GTEX Music Network",
          contexts: ["home", "club", "market", "competition", "matchday", "world", "celebration"],
          hypeCount: 100,
          streamImpressions: 0,
          isGoalAnthem: false,
          isWalkoutAnthem: true,
          licence: `Verified Artist Rights (${t.rights_holder || t.artist})`,
          source: "GTEX Commercial Music Promotion",
          provenance: "Direct Artist Audio Upload",
          accentColor: "#F59E0B",
          notes: [220, 261.63, 293.66, 329.63, 392.0, 329.63, 293.66, 261.63],
          audioUrl: resolveCommercialMediaUrl(t.audio_url) || undefined,
          artworkUrl: resolveCommercialMediaUrl(t.artwork_url),
          campaignId: t.campaign_id,
          explicitContent: t.explicit_content,
        }));
        setRotationTracks(mapped);
      })
      .catch(() => {
        if (!cancelled) setRotationTracks([]);
      });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!modalOpen) return;
    for (const promotion of sponsoredPromotions) {
      if (!reportedPromotionImpressions.current.has(promotion.campaign_id)) {
        reportedPromotionImpressions.current.add(promotion.campaign_id);
        reportMusicPromotionEvent(promotion.campaign_id, "impression");
      }
    }
  }, [modalOpen, sponsoredPromotions]);

  // Sync route context automatically
  useEffect(() => {
    const nextCtx = inferContextFromPath(pathname);
    setActiveContext(nextCtx);
  }, [pathname]);

  // Coordinate with Central Audio Session Manager (user_music channel priority)
  useEffect(() => {
    if (isPlaying && !isMuted && !isCommentaryActive) {
      gtexAudio.registerActiveChannelSource("user_music", "gtex_trax_player");
    } else {
      gtexAudio.unregisterActiveChannelSource("user_music", "gtex_trax_player");
    }
    return () => {
      gtexAudio.unregisterActiveChannelSource("user_music", "gtex_trax_player");
    };
  }, [isPlaying, isMuted, isCommentaryActive]);

  // Show EA FC Trax-style Now Playing Broadcast Chyron when track changes while playing
  useEffect(() => {
    if (!isPlaying) return;
    setShowToastChyron(true);
    const t = setTimeout(() => setShowToastChyron(false), 5200);
    return () => clearTimeout(t);
  }, [currentTrackIndex, isPlaying]);

  // Keep volume and mute state synchronized in-place without pausing/restarting active playback
  useEffect(() => {
    if (promoAudioRef.current) {
      promoAudioRef.current.volume = Math.max(0, Math.min(1, effectiveGain));
      promoAudioRef.current.muted = isMuted;
    }
  }, [effectiveGain, isMuted]);

  // HTML5 Audio playback for uploaded promotional tracks and MP3 streams
  useEffect(() => {
    if (!currentTrack.audioUrl) return undefined;
    const isJsDom = typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent || "");
    if (!isPlaying || isCommentaryActive) {
      if (promoAudioRef.current && !isJsDom) {
        promoAudioRef.current.pause();
      }
      return undefined;
    }
    if (!promoAudioRef.current) {
      promoAudioRef.current = new Audio();
    }
    const el = promoAudioRef.current;
    if (el.src !== currentTrack.audioUrl) {
      el.src = currentTrack.audioUrl;
      qualifiedReportedForPlayRef.current = null;
      setCurrentTimeSeconds(0);
    }
    el.volume = Math.max(0, Math.min(1, effectiveGain));
    el.muted = isMuted;

    const onLoadedMetadata = () => {
      if (Number.isFinite(el.duration) && el.duration > 0) {
        setDurationSeconds(Math.round(el.duration));
      }
    };
    const onTimeUpdate = () => {
      setCurrentTimeSeconds(Math.floor(el.currentTime || 0));
      if (Number.isFinite(el.duration) && el.duration > 0) {
        setDurationSeconds(Math.round(el.duration));
      }
      if (
        currentTrack.campaignId &&
        qualifiedReportedForPlayRef.current !== currentTrack.campaignId &&
        (el.currentTime >= 30 || (el.duration > 0 && el.currentTime >= el.duration * 0.5))
      ) {
        qualifiedReportedForPlayRef.current = currentTrack.campaignId;
        reportMusicPromotionEvent(currentTrack.campaignId, "qualified_listen");
      }
    };
    const onEnded = () => {
      if (currentTrack.campaignId) {
        reportMusicPromotionEvent(currentTrack.campaignId, "completed");
        sessionPlayCountsRef.current[currentTrack.campaignId] =
          (sessionPlayCountsRef.current[currentTrack.campaignId] || 0) + 1;
      }
      setCurrentTrackIndex((i) => (i + 1) % Math.max(1, combinedCatalogue.length));
    };
    const onError = () => {
      // Gracefully skip unavailable or broken tracks without double-skipping adjacent items
      setCurrentTimeSeconds(0);
      setFailedTrackIds((prev) => (prev.includes(currentTrack.id) ? prev : [...prev, currentTrack.id]));
    };

    el.addEventListener("loadedmetadata", onLoadedMetadata);
    el.addEventListener("timeupdate", onTimeUpdate);
    el.addEventListener("ended", onEnded);
    el.addEventListener("error", onError);
    const markStarted = () => {
      setAutoplayBlocked(false);
      if (currentTrack.campaignId) {
        reportMusicPromotionEvent(currentTrack.campaignId, "play_started");
      }
    };
    const attemptPlay = (): Promise<void> => {
      if (isJsDom) {
        return Promise.resolve();
      }
      try {
        const playResult = el.play();
        return playResult && typeof playResult.then === "function" ? playResult : Promise.resolve();
      } catch (err) {
        return Promise.reject(err);
      }
    };
    let resumeListener: (() => void) | null = null;
    attemptPlay().then(markStarted).catch(() => {
      setAutoplayBlocked(true);
      resumeListener = () => {
        lastAutoplayUnlockAtRef.current = Date.now();
        void gtexAudio.unlockAutoplay();
        attemptPlay().then(markStarted).catch(() => undefined);
      };
      window.addEventListener("pointerdown", resumeListener, { once: true });
      window.addEventListener("keydown", resumeListener, { once: true });
    });

    return () => {
      el.removeEventListener("loadedmetadata", onLoadedMetadata);
      el.removeEventListener("timeupdate", onTimeUpdate);
      el.removeEventListener("ended", onEnded);
      el.removeEventListener("error", onError);
      if (resumeListener) {
        window.removeEventListener("pointerdown", resumeListener);
        window.removeEventListener("keydown", resumeListener);
      }
      if (!isJsDom) {
        el.pause();
      }
    };
  }, [isPlaying, isCommentaryActive, currentTrack, combinedCatalogue.length]);

  // WebAudio synth fallback when a track has no audioUrl
  useEffect(() => {
    if (currentTrack.audioUrl) return undefined;
    if (!isPlaying || isMuted || isCommentaryActive) return undefined;

    const stepMs = Math.max(180, Math.round((60000 / currentTrack.bpm) / 2));
    const timer = setInterval(() => {
      try {
        const Ctx = window.AudioContext || (window as any).webkitAudioContext;
        if (!Ctx) return;
        if (!audioCtxRef.current) {
          audioCtxRef.current = new Ctx();
        }
        const ctx = audioCtxRef.current;
        if (ctx.state === "suspended") {
          ctx.resume();
        }
        const now = ctx.currentTime;
        const step = stepRef.current % 8;
        stepRef.current += 1;

        const freq = currentTrack.notes[step % currentTrack.notes.length];

        // Warm sub-bass + melodic synth pluck
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = step % 2 === 0 ? "triangle" : "sine";
        osc.frequency.setValueAtTime(step % 4 === 0 ? freq * 0.5 : freq, now);

        const noteGain = Math.min(0.18, effectiveGain * 0.16);
        gain.gain.setValueAtTime(0.001, now);
        gain.gain.linearRampToValueAtTime(noteGain, now + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0008, now + stepMs / 1000);

        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + stepMs / 1000);
      } catch {
        // Ignore WebAudio restrictions until user interacts
      }
    }, stepMs);

    return () => clearInterval(timer);
  }, [isPlaying, isMuted, isCommentaryActive, currentTrack, effectiveGain]);

  const togglePlayPause = () => {
    void gtexAudio.unlockAutoplay();
    const justUnlockedFromAutoplayBlock = Date.now() - lastAutoplayUnlockAtRef.current < 400;
    if (autoplayBlocked || (justUnlockedFromAutoplayBlock && isPlaying)) {
      setAutoplayBlocked(false);
      setIsPlaying(true);
      try {
        window.localStorage?.setItem(TRAX_PLAY_STORAGE_KEY, "true");
      } catch {
        // ignore storage errors
      }
      if (promoAudioRef.current && currentTrack.audioUrl && promoAudioRef.current.paused) {
        try {
          const playRes = promoAudioRef.current.play();
          if (playRes && typeof playRes.catch === "function") {
            playRes.catch(() => undefined);
          }
        } catch {
          // ignore play errors
        }
      }
      return;
    }
    setIsPlaying((prev) => {
      const next = !prev;
      try {
        window.localStorage?.setItem(TRAX_PLAY_STORAGE_KEY, String(next));
      } catch {
        // ignore storage errors
      }
      return next;
    });
  };

  const handleVolumeChange = (nextVolume: number) => {
    const clamped = Math.max(0, Math.min(1, nextVolume));
    setVolume(clamped);
    gtexAudio.setChannelVolume("user_music", clamped);
    if (clamped > 0 && isMuted) {
      setIsMuted(false);
      try {
        window.localStorage?.setItem(TRAX_MUTE_STORAGE_KEY, "false");
      } catch {
        // ignore
      }
    }
    try {
      window.localStorage?.setItem(TRAX_VOLUME_STORAGE_KEY, String(clamped));
    } catch {
      // ignore storage errors
    }
  };

  const toggleMute = () => {
    setIsMuted((prev) => {
      const next = !prev;
      try {
        window.localStorage?.setItem(TRAX_MUTE_STORAGE_KEY, String(next));
      } catch {
        // ignore storage errors
      }
      if (next && currentTrack.campaignId) {
        reportMusicPromotionEvent(currentTrack.campaignId, "muted");
      }
      return next;
    });
  };

  const handleSeek = (nextTimeSeconds: number) => {
    const clamped = Math.max(0, Math.min(durationSeconds || 180, nextTimeSeconds));
    setCurrentTimeSeconds(clamped);
    if (promoAudioRef.current) {
      try {
        promoAudioRef.current.currentTime = clamped;
      } catch {
        // ignore seek before metadata loaded
      }
    }
  };

  const prevTrack = () => {
    const len = Math.max(1, combinedCatalogue.length);
    setCurrentTrackIndex((i) => (i - 1 + len) % len);
  };

  const nextTrack = () => {
    if (isPlaying && currentTrack.campaignId) {
      reportMusicPromotionEvent(currentTrack.campaignId, "skipped");
      sessionPlayCountsRef.current[currentTrack.campaignId] =
        (sessionPlayCountsRef.current[currentTrack.campaignId] || 0) + 1;
    }
    setCurrentTrackIndex((i) => (i + 1) % Math.max(1, combinedCatalogue.length));
  };

  const shuffleTrack = () => {
    const next = Math.floor(Math.random() * combinedCatalogue.length);
    setCurrentTrackIndex(next);
  };

  const toggleHype = (track: GtexTraxItem) => {
    const next = !hypedIds[track.id];
    setHypedIds((prev) => ({ ...prev, [track.id]: next }));
    if (next) {
      toast.success(`🔥 Hyped "${track.title}" by ${track.artist}!`);
    }
  };

  const tipArtist = (track: GtexTraxItem) => {
    setTipsByTrack((prev) => ({ ...prev, [track.id]: (prev[track.id] || 0) + 10 }));
    toast.success(`💎 Sent +10 FAN Coin tip to ${track.artist} (${track.artistHandle})!`);
  };

  const handleOutboundStream = (track: GtexTraxItem, platform: string, url?: string) => {
    setClicksByTrack((prev) => ({ ...prev, [track.id]: (prev[track.id] || 0) + 1 }));
    toast.info(`Opening ${track.artist} on ${platform}...`);
    if (url) {
      window.open(url, "_blank", "noopener,noreferrer");
    }
  };

  const hypeTotal = currentTrack.hypeCount + (hypedIds[currentTrack.id] ? 1 : 0);
  const tipTotal = tipsByTrack[currentTrack.id] || 0;
  const clickTotal = clicksByTrack[currentTrack.id] || 0;
  const isActivelyPlaying = isPlaying && !autoplayBlocked;

  const portalsTarget = typeof document !== "undefined" ? document.body : null;
  const overlays = (
    <>
      {/* EA Sports FC Trax-Style Floating "Now Playing · GTEX TRAX" Broadcast Chyron */}
      {showToastChyron && (
        <div className="fixed bottom-5 right-5 z-40 flex w-80 items-center gap-3 rounded-2xl border border-amber-400/50 bg-slate-950/95 p-3.5 shadow-[0_20px_50px_rgba(0,0,0,0.85)] backdrop-blur-xl">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-amber-400/40 bg-gradient-to-br from-emerald-500/25 to-amber-500/25">
            {currentTrack.artworkUrl ? (
              <img
                src={currentTrack.artworkUrl}
                alt={currentTrack.title}
                className="h-full w-full object-cover"
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                }}
              />
            ) : (
              <Disc3 size={24} className="animate-spin text-amber-300" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <span className="rounded bg-amber-400 px-1.5 py-0.2 text-[8px] font-black uppercase tracking-wider text-slate-950">
                {currentTrackPromotion ? "SPONSORED PROMOTION" : "GTEX TRAX · NOW PLAYING"}
              </span>
              <span className="gx-mono text-[9px] text-emerald-300">{currentTrack.bpm} BPM</span>
            </div>
            <p className="mt-1 truncate text-xs font-black text-white">{currentTrack.title}</p>
            <p className="truncate text-[10px] text-slate-400">
              {currentTrack.artist} ({currentTrack.artistHandle})
            </p>
            <div className="mt-1.5 flex items-center gap-2">
              <button
                onClick={() => toggleHype(currentTrack)}
                className="rounded border border-amber-400/40 bg-amber-500/15 px-2 py-0.5 text-[9px] font-black text-amber-300 hover:bg-amber-500/25"
              >
                🔥 HYPE ({hypeTotal})
              </button>
              <button
                onClick={() => setModalOpen(true)}
                className="rounded border border-white/15 bg-white/5 px-2 py-0.5 text-[9px] font-bold text-slate-300 hover:text-white"
              >
                ARTIST CARD ↗
              </button>
            </div>
          </div>
          <button
            onClick={() => setShowToastChyron(false)}
            className="self-start text-slate-500 hover:text-white"
          >
            <X size={13} />
          </button>
        </div>
      )}

      {/* Full GTEX TRAX Artist Promotion & Soundtrack OS Studio Modal */}
      {modalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          data-testid="gtex-trax-modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md"
        >
          <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-emerald-500/35 bg-[#080D16] p-6 text-slate-100 shadow-[0_28px_90px_rgba(0,0,0,0.95)]">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-400">
                  <Headphones size={20} />
                </span>
                <div>
                  <p className="gx-mono text-[10px] font-black uppercase tracking-widest text-emerald-400">
                    GTEX SOUNDTRACK OS & ARTIST PROMOTION ENGINE
                  </p>
                  <h2 className="gx-display text-2xl font-black uppercase text-white">
                    GTEX TRAX · Featured Artist Radio & Mixer
                  </h2>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowCredits(!showCredits)}
                  className="flex items-center gap-1 rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-bold text-slate-300 hover:text-white"
                >
                  <Info size={13} />
                  <span>{showCredits ? "Back to Studio" : "Licensing & Credits"}</span>
                </button>
                <button
                  onClick={() => setModalOpen(false)}
                  aria-label="Close GTEX TRAX"
                  data-testid="gtex-trax-modal-close-btn"
                  className="rounded-lg border border-white/15 bg-white/5 p-1.5 text-slate-400 hover:text-white"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {showCredits ? (
              <div className="mt-5 space-y-3">
                <p className="text-xs text-slate-400">
                  GTEX TRAX catalogue entries retain their provenance, sync-licence and artist-attribution information.
                </p>
                {GTEX_TRAX_CATALOGUE.map((t) => (
                  <div
                    key={t.id}
                    className="rounded-xl border border-white/10 bg-slate-900/70 p-4 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-black text-white">
                        {t.title} — {t.artist} ({t.artistHandle})
                      </span>
                      <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-300">
                        GTEX CATALOGUE
                      </span>
                    </div>
                    <p className="mt-1 text-slate-400">
                      Licence: <strong className="text-slate-200">{t.licence}</strong> · Source:{" "}
                      <strong className="text-slate-200">{t.source}</strong>
                    </p>
                    <p className="mt-0.5 text-[11px] text-slate-500">Provenance: {t.provenance}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-5 space-y-6">
                {/* Featured Artist Spotlight Card */}
                <div className="rounded-2xl border border-amber-400/35 bg-gradient-to-br from-slate-900 via-slate-950 to-emerald-950/35 p-5 shadow-xl">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="flex items-center gap-4">
                      <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-amber-400/50 bg-slate-950 shadow-lg">
                        {currentTrack.artworkUrl ? (
                          <img
                            src={currentTrack.artworkUrl}
                            alt={currentTrack.title}
                            className="h-full w-full object-cover"
                            data-testid="gtex-trax-modal-artwork"
                          />
                        ) : (
                          <Disc3
                            size={34}
                            className={isPlaying && !isMuted ? "animate-spin text-amber-400" : "text-emerald-400"}
                          />
                        )}
                      </div>
                      <div>
                        <div className="flex flex-wrap items-center gap-1.5">
                          {isCurrentSponsored && (
                            <span
                              className="rounded bg-amber-400 px-2 py-0.5 text-[9px] font-black uppercase tracking-wider text-slate-950"
                              data-testid="gtex-trax-modal-sponsored-badge"
                            >
                              ★ SPONSORED · {currentTrackPromotion?.headline || "Promoted on GTEX Music Network"}
                            </span>
                          )}
                          <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[9px] font-bold text-emerald-300">
                            {currentTrack.genre}
                          </span>
                          <span className="gx-mono rounded bg-cyan-500/20 px-2 py-0.5 text-[9px] font-bold text-cyan-300">
                            {currentTrack.bpm} BPM · {currentTrack.duration}
                          </span>
                          <span className="rounded bg-white/10 px-2 py-0.5 text-[9px] font-bold text-slate-300">
                            {currentTrack.region}
                          </span>
                        </div>
                        <h3 className="mt-1.5 text-lg font-black text-white">{currentTrack.title}</h3>
                        <p className="text-xs font-semibold text-amber-300">
                          {currentTrack.artist} · <span className="text-slate-400">{currentTrack.artistHandle}</span> ·{" "}
                          <span className="text-slate-500">{currentTrack.album}</span>
                        </p>
                      </div>
                    </div>

                    {/* Playback Controls */}
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        onClick={prevTrack}
                        title="Previous track"
                        data-testid="gtex-trax-modal-prev-btn"
                        className="rounded-xl border border-white/15 bg-white/5 p-2.5 text-slate-300 hover:text-white"
                      >
                        <SkipBack size={16} />
                      </button>
                      <button
                        type="button"
                        onClick={togglePlayPause}
                        title={isActivelyPlaying ? "Pause" : "Play"}
                        data-testid="gtex-trax-modal-play-pause-btn"
                        className="rounded-xl border border-emerald-400/40 bg-emerald-500/15 p-2.5 text-emerald-300 hover:bg-emerald-500/25"
                      >
                        {isActivelyPlaying ? <Pause size={16} /> : <Play size={16} />}
                      </button>
                      <button
                        type="button"
                        onClick={nextTrack}
                        title="Skip to the next track"
                        data-testid="gtex-trax-modal-skip-btn"
                        className="rounded-xl border border-white/15 bg-white/5 p-2.5 text-slate-300 hover:text-white"
                      >
                        <SkipForward size={16} />
                      </button>
                      <button
                        type="button"
                        onClick={shuffleTrack}
                        title="Shuffle"
                        className="rounded-xl border border-white/15 bg-white/5 p-2.5 text-slate-300 hover:text-white"
                      >
                        <Shuffle size={16} />
                      </button>
                      <div className="flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-2.5 py-1.5">
                        <button
                          type="button"
                          onClick={toggleMute}
                          title={isMuted ? "Unmute" : "Mute"}
                          data-testid="gtex-trax-modal-mute-btn"
                          className="text-slate-300 hover:text-white"
                        >
                          {isMuted ? <VolumeX size={15} /> : <Volume2 size={15} />}
                        </button>
                        <input
                          type="range"
                          min={0}
                          max={1}
                          step={0.05}
                          value={isMuted ? 0 : volume}
                          onChange={(e) => handleVolumeChange(Number(e.target.value))}
                          aria-label="Music volume"
                          data-testid="gtex-trax-volume-slider"
                          className="h-1.5 w-20 cursor-pointer accent-amber-400"
                        />
                        <span className="gx-mono w-8 text-right text-[10px] text-slate-300">
                          {isMuted ? "0%" : `${Math.round(volume * 100)}%`}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Interactive Seek / Progress Bar */}
                  <div className="mt-3 space-y-1">
                    <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                      <span data-testid="gtex-trax-current-time">{formatTrackTime(currentTimeSeconds)}</span>
                      <span data-testid="gtex-trax-playback-status">
                        {isCommentaryActive
                          ? "Paused for live match commentary"
                          : autoplayBlocked
                          ? "Click Play to unlock browser audio"
                          : isCurrentSponsored
                          ? "Promoted on GTEX Music Network"
                          : "GTEX TRAX Rotation"}
                      </span>
                      <span data-testid="gtex-trax-duration">{formatTrackTime(durationSeconds)}</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={Math.max(1, durationSeconds)}
                      value={Math.min(currentTimeSeconds, Math.max(1, durationSeconds))}
                      onChange={(e) => handleSeek(Number(e.target.value))}
                      className="h-1.5 w-full cursor-pointer accent-emerald-400"
                      data-testid="gtex-trax-seek-bar"
                    />
                  </div>

                  <p className="mt-3 text-xs leading-relaxed text-slate-300">{currentTrack.artistBio}</p>

                  {/* Artist Promotion CTAs: Hype, Tip Artist, Set Goal/Walkout Anthem */}
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-3.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        onClick={() => toggleHype(currentTrack)}
                        className={`rounded-lg border px-3 py-1.5 text-xs font-black transition-all ${
                          hypedIds[currentTrack.id]
                            ? "border-amber-400 bg-amber-500/25 text-amber-200"
                            : "border-white/15 bg-white/5 text-slate-200 hover:border-amber-400/50"
                        }`}
                      >
                        🔥 HYPE TRACK ({hypeTotal.toLocaleString()})
                      </button>
                      <button
                        onClick={() => tipArtist(currentTrack)}
                        className="rounded-lg border border-emerald-500/40 bg-emerald-500/15 px-3 py-1.5 text-xs font-black text-emerald-300 hover:bg-emerald-500/25"
                      >
                        {tipTotal > 0 ? `💎 BACKED (+${tipTotal} FAN)` : "💎 TIP ARTIST (+10 FAN)"}
                      </button>
                      <button
                        onClick={() => {
                          setGoalAnthemId(currentTrack.id);
                          toast.success(`⚽ "${currentTrack.title}" set as your Club Goal & 3D Walkout Anthem!`);
                        }}
                        className={`rounded-lg border px-3 py-1.5 text-xs font-black transition-all ${
                          goalAnthemId === currentTrack.id
                            ? "border-cyan-400 bg-cyan-500/20 text-cyan-200"
                            : "border-white/15 bg-white/5 text-slate-300 hover:border-cyan-400/50"
                        }`}
                      >
                        {goalAnthemId === currentTrack.id
                          ? "⚽ ACTIVE GOAL & WALKOUT ANTHEM"
                          : "⚽ SET AS GOAL ANTHEM"}
                      </button>
                    </div>

                    {/* Outbound Artist Streaming Links */}
                    <div className="flex flex-wrap items-center gap-1.5">
                      {currentTrack.spotifyUrl && (
                        <button
                          onClick={() => handleOutboundStream(currentTrack, "Spotify", currentTrack.spotifyUrl)}
                          className="inline-flex items-center gap-1 rounded-md border border-[#1DB954]/50 bg-[#1DB954]/15 px-2.5 py-1 text-[10px] font-black text-[#1DB954] hover:bg-[#1DB954]/25"
                        >
                          <span>Spotify</span>
                          <ExternalLink size={10} />
                        </button>
                      )}
                      {currentTrack.appleMusicUrl && (
                        <button
                          onClick={() => handleOutboundStream(currentTrack, "Apple Music", currentTrack.appleMusicUrl)}
                          className="inline-flex items-center gap-1 rounded-md border border-rose-500/50 bg-rose-500/15 px-2.5 py-1 text-[10px] font-black text-rose-300 hover:bg-rose-500/25"
                        >
                          <span>Apple Music</span>
                          <ExternalLink size={10} />
                        </button>
                      )}
                      {currentTrack.audiomackUrl && (
                        <button
                          onClick={() => handleOutboundStream(currentTrack, "Audiomack", currentTrack.audiomackUrl)}
                          className="inline-flex items-center gap-1 rounded-md border border-amber-500/50 bg-amber-500/15 px-2.5 py-1 text-[10px] font-black text-amber-300 hover:bg-amber-500/25"
                        >
                          <span>Audiomack</span>
                          <ExternalLink size={10} />
                        </button>
                      )}
                      {currentTrack.youtubeUrl && (
                        <button
                          onClick={() => handleOutboundStream(currentTrack, "YouTube", currentTrack.youtubeUrl)}
                          className="inline-flex items-center gap-1 rounded-md border border-sky-400/50 bg-sky-500/15 px-2.5 py-1 text-[10px] font-black text-sky-300 hover:bg-sky-500/25"
                        >
                          <span>YouTube</span>
                          <ExternalLink size={10} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Local catalogue interaction metrics; not billable campaign telemetry. */}
                  <div className="mt-3 grid grid-cols-3 gap-2 rounded-xl border border-white/10 bg-black/40 p-2.5 text-center text-[11px]">
                    <div>
                      <span className="block text-[9px] font-bold uppercase text-slate-400">
                        TRACK HYPE
                      </span>
                      <span className="gx-mono font-black text-white">
                        {hypeTotal.toLocaleString()}
                      </span>
                    </div>
                    <div>
                      <span className="block text-[9px] font-bold uppercase text-slate-400">
                        OUTBOUND LINK CLICKS
                      </span>
                      <span className="gx-mono font-black text-emerald-400">
                        {clickTotal.toLocaleString()}
                      </span>
                    </div>
                    <div>
                      <span className="block text-[9px] font-bold uppercase text-slate-400">
                        CATALOGUE STATUS
                      </span>
                      <span className="gx-mono font-black text-amber-300">
                        {currentTrackPromotion ? "Sponsored item · labelled" : "Organic GTEX TRAX catalogue"}
                      </span>
                    </div>
                  </div>
                </div>

                {sponsoredPromotions.length > 0 && (
                  <section className="rounded-2xl border border-amber-400/30 bg-amber-400/[0.04] p-4">
                    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="gx-label !text-amber-300">GTEX TRAX PARTNERS</p>
                        <h3 className="text-sm font-black uppercase text-white">Sponsored promotions</h3>
                      </div>
                      <span className="rounded bg-amber-400 px-2 py-1 text-[9px] font-black uppercase text-slate-950">Paid placement</span>
                    </div>
                    <div className="grid gap-2 md:grid-cols-2">
                      {sponsoredPromotions.map((promotion) => (
                        <article key={promotion.campaign_id} className="rounded-xl border border-white/10 bg-slate-950/70 p-3">
                          <div className="flex items-center justify-between gap-2">
                            <span className="rounded bg-amber-400/15 px-2 py-0.5 text-[9px] font-black uppercase text-amber-200">Sponsored</span>
                            <span className="text-[9px] uppercase text-slate-500">{promotion.target_type}</span>
                          </div>
                          <p className="mt-2 text-sm font-black text-white">{promotion.headline}</p>
                          <p className="text-[11px] text-emerald-300">{promotion.artist_name || promotion.playlist_name || promotion.brand_name}{promotion.track_title ? " · " + promotion.track_title : ""}</p>
                          {promotion.description && <p className="mt-1 text-xs leading-relaxed text-slate-400">{promotion.description}</p>}
                          <div className="mt-3 flex flex-wrap items-center gap-2">
                            <button
                              type="button"
                              onClick={() => {
                                const idx = combinedCatalogue.findIndex(
                                  (item) => item.campaignId === promotion.campaign_id,
                                );
                                if (idx >= 0) setCurrentTrackIndex(idx);
                                reportMusicPromotionEvent(promotion.campaign_id, "click");
                              }}
                              className="inline-flex rounded-lg border border-emerald-400/40 bg-emerald-400/10 px-2.5 py-1.5 text-[10px] font-black uppercase text-emerald-200 hover:bg-emerald-400/20"
                            >
                              Skip to this track
                            </button>
                            <a
                              href={promotion.destination_url}
                              target="_blank"
                              rel="noopener noreferrer sponsored"
                              onClick={() => reportMusicPromotionEvent(promotion.campaign_id, "click")}
                              className="inline-flex rounded-lg border border-amber-400/40 bg-amber-400/10 px-2.5 py-1.5 text-[10px] font-black uppercase text-amber-200 hover:bg-amber-400/20"
                            >
                              Visit partner ↗
                            </a>
                          </div>
                        </article>
                      ))}
                    </div>
                    <p className="mt-2 text-[9px] text-slate-500">Paid partner placements are labelled. GTEX TRAX playback and organic catalogue selection remain under your control.</p>
                  </section>
                )}

                {/* GTEX TRAX Artist Roster / Jukebox List */}
                <div>
                  <p className="gx-label mb-2">GTEX TRAX · Artist Roster</p>
                  <div className="space-y-2">
                    {combinedCatalogue.map((item, idx) => {
                      const active = idx === currentTrackIndex % combinedCatalogue.length;
                      return (
                        <div
                          key={item.id}
                          onClick={() => {
                            setCurrentTrackIndex(idx);
                          }}
                          className={`flex cursor-pointer items-center justify-between rounded-xl border p-3 transition-all ${
                            active
                              ? "border-emerald-400/60 bg-emerald-500/15"
                              : "border-white/10 bg-white/[0.02] hover:border-white/25"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-xs font-black text-emerald-400">
                              {active && isPlaying ? "▶" : idx + 1}
                            </span>
                            <div>
                              <p className="text-xs font-black text-white">{item.title}</p>
                              <p className="text-[11px] text-slate-400">
                                {item.artist} ({item.artistHandle}) · {item.genre} · {item.region}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {goalAnthemId === item.id && (
                              <span className="rounded bg-cyan-500/20 px-2 py-0.5 text-[9px] font-black text-cyan-300">
                                ⚽ ANTHEM
                              </span>
                            )}
                            <span
                              className={`rounded px-2 py-0.5 text-[9px] font-black uppercase ${
                                item.isPromoted
                                  ? "bg-amber-400/20 text-amber-300"
                                  : "bg-emerald-500/20 text-emerald-300"
                              }`}
                            >
                              {item.isPromoted ? "SPONSORED" : "GTEX CATALOGUE"}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Audio Channel Mixer & Context Switcher */}
                <div className="rounded-xl border border-white/10 bg-slate-900/60 p-4">
                  <p className="gx-label mb-3">Playback &amp; Rotation Policy</p>
                  <p className="text-xs leading-relaxed text-slate-300">
                    Use Play/Pause, Mute, Seek, or Skip at any time. Playback state persists across pages.
                    Promoted tracks rotate fairly with a session frequency cap ({frequencyCapPerSession} plays/session)
                    and automatically pause when live match commentary is active.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );

  return (
    <>
      <audio ref={promoAudioRef} data-testid="gtex-trax-audio" preload="metadata" className="hidden" />
      {/* Top-Bar Compact GTEX TRAX Artist Pill */}
      <div
        data-testid="gtex-trax-pill"
        className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-400/35 bg-slate-950/90 px-2.5 py-1 text-xs shadow-inner"
      >
        <button
          type="button"
          onClick={prevTrack}
          title="Previous GTEX TRAX Track"
          data-testid="gtex-trax-prev-btn"
          className="text-slate-400 hover:text-white"
        >
          <SkipBack size={12} />
        </button>

        <button
          type="button"
          onClick={togglePlayPause}
          title={isActivelyPlaying ? "Pause GTEX TRAX" : "Play GTEX TRAX"}
          data-testid="gtex-trax-play-pause-btn"
          className="text-emerald-400 hover:text-white"
        >
          {isActivelyPlaying ? <Pause size={12} /> : <Play size={12} />}
        </button>

        <button
          type="button"
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-1.5 text-left hover:text-white"
          data-testid="gtex-trax-open-modal-btn"
        >
          {currentTrack.artworkUrl ? (
            <img
              src={currentTrack.artworkUrl}
              alt={currentTrack.title}
              className="h-4 w-4 rounded object-cover"
              data-testid="gtex-trax-pill-artwork"
              onError={(e) => {
                e.currentTarget.style.display = "none";
              }}
            />
          ) : (
            <Disc3
              size={13}
              className={`${isActivelyPlaying && !isMuted ? "animate-spin text-amber-400" : "text-emerald-400"}`}
            />
          )}
          <span
            data-testid="gtex-trax-pill-title"
            className="hidden max-w-[145px] truncate text-[11px] font-bold text-slate-200 md:inline"
          >
            {currentTrack.artist.split(" ")[0]} · {currentTrack.title.split("(")[0]}
          </span>
          {isCurrentSponsored && (
            <span
              className="rounded bg-amber-400 px-1.5 py-0.5 text-[8px] font-black uppercase text-slate-950"
              data-testid="gtex-trax-sponsored-badge"
            >
              SPONSORED
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={toggleMute}
          title={isMuted ? "Unmute GTEX TRAX" : "Mute GTEX TRAX"}
          data-testid="gtex-trax-mute-btn"
          className="text-slate-400 hover:text-white"
        >
          {isMuted ? <VolumeX size={12} /> : <Volume2 size={12} />}
        </button>

        <button
          type="button"
          onClick={nextTrack}
          title="Next GTEX TRAX Track"
          data-testid="gtex-trax-skip-btn"
          className="text-slate-400 hover:text-white"
        >
          <SkipForward size={12} />
        </button>
      </div>
      {portalsTarget ? createPortal(overlays, portalsTarget) : overlays}
    </>
  );
}
