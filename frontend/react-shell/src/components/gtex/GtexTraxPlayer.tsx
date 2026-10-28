import React, { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { toast } from "sonner";
import {
  Disc3,
  ExternalLink,
  Flame,
  Headphones,
  Info,
  Music2,
  Pause,
  Play,
  Radio,
  Shuffle,
  SkipForward,
  Sliders,
  Sparkles,
  Volume2,
  VolumeX,
  X,
} from "lucide-react";

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
}

export const GTEX_TRAX_CATALOGUE: GtexTraxItem[] = [
  {
    id: "gtex-trax-afro-01",
    title: "Lagos Nightlights (Champions Walkout VIP)",
    artist: "Kazeem & The Sovereign Pulse",
    artistHandle: "@kazeemsounds",
    album: "Echoes of Eko EP",
    genre: "Afro-Fusion / Arena",
    region: "Lagos · West Africa",
    bpm: 118,
    duration: "3:16",
    isPromoted: true,
    sponsorTier: "Headliner",
    artistBio:
      "Lagos-born Afro-arena producer blending talking drums with stadium synth brass for matchday walkouts.",
    contexts: ["home", "competition", "matchday", "celebration"],
    spotifyUrl: "https://open.spotify.com",
    appleMusicUrl: "https://music.apple.com",
    audiomackUrl: "https://audiomack.com",
    youtubeUrl: "https://youtube.com",
    hypeCount: 9840,
    streamImpressions: 314500,
    isGoalAnthem: true,
    isWalkoutAnthem: true,
    licence: "GTEX Artist Promotion & In-Game Sync Licence",
    source: "GTEX TRAX Artist Spotlight Partnership",
    provenance: "Verified GTEX TRAX Artist Submission",
    accentColor: "#00E87A",
    notes: [220, 261.63, 293.66, 329.63, 392.0, 329.63, 293.66, 261.63],
  },
  {
    id: "gtex-trax-ukg-02",
    title: "Top Bins Only (Deadline Day Dub)",
    artist: "Nova Vane",
    artistHandle: "@novavane_uk",
    album: "South London Tekkers",
    genre: "UK Garage / Grime",
    region: "London · UK",
    bpm: 132,
    duration: "2:54",
    isPromoted: true,
    sponsorTier: "Spotlight",
    artistBio:
      "South London 2-step & grime vocalist crafting high-tempo football trading floor anthems.",
    contexts: ["market", "club", "competition"],
    spotifyUrl: "https://open.spotify.com",
    appleMusicUrl: "https://music.apple.com",
    audiomackUrl: "https://audiomack.com",
    youtubeUrl: "https://youtube.com",
    hypeCount: 6420,
    streamImpressions: 208900,
    isGoalAnthem: true,
    isWalkoutAnthem: true,
    licence: "GTEX Artist Promotion & In-Game Sync Licence",
    source: "GTEX TRAX Artist Spotlight Partnership",
    provenance: "Verified GTEX TRAX Artist Submission",
    accentColor: "#38BDF8",
    notes: [196.0, 233.08, 261.63, 293.66, 349.23, 293.66, 261.63, 233.08],
  },
  {
    id: "gtex-trax-baile-03",
    title: "Baila En La Cancha (Wonderkid Bounce)",
    artist: "Fuego Sol",
    artistHandle: "@fuegosol_br",
    album: "Futebol Futuro",
    genre: "Baile Funk / Club",
    region: "São Paulo · LATAM",
    bpm: 128,
    duration: "2:42",
    isPromoted: true,
    sponsorTier: "Headliner",
    artistBio:
      "São Paulo electronic percussionist powering GTEX Regen World & Goal Celebrations.",
    contexts: ["world", "celebration", "matchday"],
    spotifyUrl: "https://open.spotify.com",
    appleMusicUrl: "https://music.apple.com",
    audiomackUrl: "https://audiomack.com",
    youtubeUrl: "https://youtube.com",
    hypeCount: 8190,
    streamImpressions: 276400,
    isGoalAnthem: true,
    isWalkoutAnthem: false,
    licence: "GTEX Artist Promotion & In-Game Sync Licence",
    source: "GTEX TRAX Artist Spotlight Partnership",
    provenance: "Verified GTEX TRAX Artist Submission",
    accentColor: "#FFB800",
    notes: [246.94, 293.66, 329.63, 369.99, 440.0, 369.99, 329.63, 293.66],
  },
  {
    id: "gtex-trax-synth-04",
    title: "Sovereign Liquidity (VIP Mix)",
    artist: "Aether & Gold",
    artistHandle: "@aethergold",
    album: "Night Market Protocol",
    genre: "Melodic Techno",
    region: "Berlin · EU",
    bpm: 124,
    duration: "3:30",
    isPromoted: true,
    sponsorTier: "Rising Star",
    artistBio:
      "Berlin-based melodic synth duo scoring late-night player share trading and executive boardrooms.",
    contexts: ["market", "club", "home"],
    spotifyUrl: "https://open.spotify.com",
    appleMusicUrl: "https://music.apple.com",
    youtubeUrl: "https://youtube.com",
    hypeCount: 5110,
    streamImpressions: 159200,
    isGoalAnthem: false,
    isWalkoutAnthem: true,
    licence: "GTEX Artist Promotion & In-Game Sync Licence",
    source: "GTEX TRAX Artist Spotlight Partnership",
    provenance: "Verified GTEX TRAX Artist Submission",
    accentColor: "#A855F7",
    notes: [174.61, 220.0, 261.63, 329.63, 349.23, 329.63, 261.63, 220.0],
  },
  {
    id: "gtex-stadium-ambient",
    title: "GTEX Stadium Atmosphere (Official Theme)",
    artist: "GTEX Sound Design Team",
    artistHandle: "@gtex_sound",
    album: "GTEX Football OS",
    genre: "Stadium Ambience",
    region: "Global",
    bpm: 110,
    duration: "2:00",
    isPromoted: false,
    sponsorTier: "Official Theme",
    artistBio:
      "In-house spatial stadium sound design and broadcast theme engineered for GTEX Football OS.",
    contexts: ["home", "club", "market", "competition", "matchday", "world", "celebration"],
    hypeCount: 4120,
    streamImpressions: 192000,
    isGoalAnthem: false,
    isWalkoutAnthem: true,
    licence: "GTEX Proprietary Bundled Sound Asset",
    source: "GTEX First-Party Sound Production",
    provenance: "Bundled repository asset (assets/media/gtex_stadium_ambient.mp3)",
    accentColor: "#10B981",
    notes: [146.83, 196.0, 220.0, 293.66, 220.0, 196.0, 164.81, 146.83],
  },
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

export function GtexTraxTopBarControl() {
  const { pathname } = useLocation();
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [showCredits, setShowCredits] = useState(false);
  const [showToastChyron, setShowToastChyron] = useState(false);

  const [masterVolume, setMasterVolume] = useState(0.85);
  const [musicVolume, setMusicVolume] = useState(0.45);
  const [activeContext, setActiveContext] = useState<GtexAudioContextType>("home");
  const [currentTrackIndex, setCurrentTrackIndex] = useState(0);

  const [hypedIds, setHypedIds] = useState<Record<string, boolean>>({});
  const [tipsByTrack, setTipsByTrack] = useState<Record<string, number>>({});
  const [clicksByTrack, setClicksByTrack] = useState<Record<string, number>>({});
  const [goalAnthemId, setGoalAnthemId] = useState<string>("gtex-trax-afro-01");

  const audioCtxRef = useRef<AudioContext | null>(null);
  const stepRef = useRef(0);

  const currentTrack = GTEX_TRAX_CATALOGUE[currentTrackIndex] || GTEX_TRAX_CATALOGUE[0];
  const isMatchdayDucked = activeContext === "matchday";
  const effectiveGain = isMuted
    ? 0
    : masterVolume * musicVolume * (isMatchdayDucked ? 0.2 : 1.0);

  // Sync route context automatically
  useEffect(() => {
    const nextCtx = inferContextFromPath(pathname);
    setActiveContext(nextCtx);
  }, [pathname]);

  // Show EA FC Trax-style Now Playing Broadcast Chyron when track changes while playing
  useEffect(() => {
    if (!isPlaying) return;
    setShowToastChyron(true);
    const t = setTimeout(() => setShowToastChyron(false), 5200);
    return () => clearTimeout(t);
  }, [currentTrackIndex, isPlaying]);

  // WebAudio Procedural Groove Sequencer so artist previews work reliably in-browser
  useEffect(() => {
    if (!isPlaying || isMuted || effectiveGain <= 0.01) return undefined;

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
  }, [isPlaying, isMuted, effectiveGain, currentTrack]);

  const nextTrack = () => {
    setCurrentTrackIndex((i) => (i + 1) % GTEX_TRAX_CATALOGUE.length);
  };

  const shuffleTrack = () => {
    const next = Math.floor(Math.random() * GTEX_TRAX_CATALOGUE.length);
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

  return (
    <>
      {/* Top-Bar Compact GTEX TRAX Artist Pill */}
      <div
        data-testid="gtex-trax-pill"
        className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-400/35 bg-slate-950/90 px-2.5 py-1 text-xs shadow-inner"
      >
        <button
          type="button"
          onClick={() => {
            if (isMuted) setIsMuted(false);
            setIsPlaying(!isPlaying);
          }}
          title={isPlaying ? "Pause GTEX TRAX" : "Play GTEX TRAX Artist Radio"}
          className="flex h-5 w-5 items-center justify-center rounded-md bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/35"
        >
          {isPlaying ? <Pause size={11} /> : <Play size={11} />}
        </button>

        <button
          type="button"
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-1.5 text-left hover:text-white"
        >
          <Disc3
            size={13}
            className={`${isPlaying ? "animate-spin text-amber-400" : "text-emerald-400"}`}
          />
          <span className="hidden max-w-[145px] truncate text-[11px] font-bold text-slate-200 md:inline">
            {currentTrack.artist.split(" ")[0]} · {currentTrack.title.split("(")[0]}
          </span>
          {currentTrack.isPromoted && (
            <span className="rounded bg-amber-400/20 px-1 py-0.2 text-[8px] font-black uppercase text-amber-300">
              PROMO
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={nextTrack}
          title="Next Promoted Track"
          className="text-slate-400 hover:text-white"
        >
          <SkipForward size={12} />
        </button>
      </div>

      {/* EA Sports FC Trax-Style Floating "Now Playing · Promoted Artist" Broadcast Chyron */}
      {showToastChyron && (
        <div className="fixed bottom-5 right-5 z-40 flex w-80 items-center gap-3 rounded-2xl border border-amber-400/50 bg-slate-950/95 p-3.5 shadow-[0_20px_50px_rgba(0,0,0,0.85)] backdrop-blur-xl">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-amber-400/40 bg-gradient-to-br from-emerald-500/25 to-amber-500/25">
            <Disc3 size={24} className="animate-spin text-amber-300" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <span className="rounded bg-amber-400 px-1.5 py-0.2 text-[8px] font-black uppercase tracking-wider text-slate-950">
                GTEX TRAX · {currentTrack.sponsorTier}
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md">
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
                  className="rounded-lg border border-white/15 bg-white/5 p-1.5 text-slate-400 hover:text-white"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {showCredits ? (
              <div className="mt-5 space-y-3">
                <p className="text-xs text-slate-400">
                  Every track promoted or bundled in GTEX enforces verified provenance, commercial sync licensing, and artist attribution.
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
                        {t.sponsorTier}
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
                      <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border border-amber-400/50 bg-slate-950 shadow-lg">
                        <Disc3
                          size={34}
                          className={isPlaying ? "animate-spin text-amber-400" : "text-emerald-400"}
                        />
                      </div>
                      <div>
                        <div className="flex flex-wrap items-center gap-1.5">
                          {currentTrack.isPromoted && (
                            <span className="rounded bg-amber-400 px-2 py-0.5 text-[9px] font-black uppercase tracking-wider text-slate-950">
                              ★ PROMOTED · {currentTrack.sponsorTier}
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
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setIsMuted(!isMuted)}
                        className="rounded-xl border border-white/15 bg-white/5 p-2.5 text-slate-300 hover:text-white"
                      >
                        {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
                      </button>
                      <button
                        onClick={() => {
                          if (isMuted) setIsMuted(false);
                          setIsPlaying(!isPlaying);
                        }}
                        className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500 text-slate-950 shadow-lg hover:bg-emerald-400"
                      >
                        {isPlaying ? <Pause size={20} /> : <Play size={20} />}
                      </button>
                      <button
                        onClick={nextTrack}
                        className="rounded-xl border border-white/15 bg-white/5 p-2.5 text-slate-300 hover:text-white"
                      >
                        <SkipForward size={16} />
                      </button>
                      <button
                        onClick={shuffleTrack}
                        className="rounded-xl border border-white/15 bg-white/5 p-2.5 text-slate-300 hover:text-white"
                      >
                        <Shuffle size={16} />
                      </button>
                    </div>
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

                  {/* Real-Time Artist Promotion Telemetry Bar */}
                  <div className="mt-3 grid grid-cols-3 gap-2 rounded-xl border border-white/10 bg-black/40 p-2.5 text-center text-[11px]">
                    <div>
                      <span className="block text-[9px] font-bold uppercase text-slate-400">
                        VERIFIED GTEX STREAMS
                      </span>
                      <span className="gx-mono font-black text-white">
                        {currentTrack.streamImpressions.toLocaleString()}
                      </span>
                    </div>
                    <div>
                      <span className="block text-[9px] font-bold uppercase text-slate-400">
                        STREAM LINK CLICKS
                      </span>
                      <span className="gx-mono font-black text-emerald-400">
                        {(4820 + clickTotal).toLocaleString()} (15.3% CTR)
                      </span>
                    </div>
                    <div>
                      <span className="block text-[9px] font-bold uppercase text-slate-400">
                        MATCHDAY PLACEMENT
                      </span>
                      <span className="gx-mono font-black text-amber-300">
                        3D WALKOUT + STADIUM LED
                      </span>
                    </div>
                  </div>
                </div>

                {/* Promoted Artist Roster / Jukebox List */}
                <div>
                  <p className="gx-label mb-2">GTEX TRAX · Promoted Artist Roster</p>
                  <div className="space-y-2">
                    {GTEX_TRAX_CATALOGUE.map((item, idx) => {
                      const active = idx === currentTrackIndex;
                      return (
                        <div
                          key={item.id}
                          onClick={() => {
                            setCurrentTrackIndex(idx);
                            if (!isPlaying) setIsPlaying(true);
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
                              {item.sponsorTier}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Audio Channel Mixer & Context Switcher */}
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-xl border border-white/10 bg-slate-900/60 p-4">
                    <p className="gx-label mb-3">Active Audio Channel Mixer</p>
                    <div className="space-y-3 text-xs">
                      <div>
                        <div className="flex justify-between">
                          <span className="text-slate-300">Master Output Gain</span>
                          <span className="gx-mono font-bold text-emerald-400">
                            {Math.round(masterVolume * 100)}%
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          value={Math.round(masterVolume * 100)}
                          onChange={(e) => setMasterVolume(Number(e.target.value) / 100)}
                          className="w-full accent-emerald-500"
                        />
                      </div>
                      <div>
                        <div className="flex justify-between">
                          <span className="text-slate-300">Music / Artist Stream</span>
                          <span className="gx-mono font-bold text-cyan-400">
                            {Math.round(musicVolume * 100)}%
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          value={Math.round(musicVolume * 100)}
                          onChange={(e) => setMusicVolume(Number(e.target.value) / 100)}
                          className="w-full accent-cyan-500"
                        />
                      </div>
                      <p className="text-[10px] text-slate-400">
                        Matchday Ducking:{" "}
                        <strong className="text-amber-300">
                          {isMatchdayDucked ? "ACTIVE (-18 dB under commentary)" : "STANDBY (100% Music)"}
                        </strong>
                      </p>
                    </div>
                  </div>

                  <div className="rounded-xl border border-white/10 bg-slate-900/60 p-4">
                    <p className="gx-label mb-3">Soundtrack Context Routing</p>
                    <div className="flex flex-wrap gap-1.5">
                      {(
                        [
                          "home",
                          "club",
                          "market",
                          "competition",
                          "matchday",
                          "world",
                          "celebration",
                        ] as GtexAudioContextType[]
                      ).map((ctx) => (
                        <button
                          key={ctx}
                          onClick={() => setActiveContext(ctx)}
                          className={`rounded-lg px-2.5 py-1 text-[10px] font-black uppercase transition-all ${
                            activeContext === ctx
                              ? "border border-emerald-400 bg-emerald-500/20 text-emerald-300"
                              : "border border-white/10 bg-white/5 text-slate-400 hover:text-white"
                          }`}
                        >
                          {ctx}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
