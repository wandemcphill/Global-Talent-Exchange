/**
 * GTEX Living Football Ecosystem — Central Audio Session Manager
 * Orchestrates multi-channel audio mixing, priority-based ducking,
 * browser autoplay negotiation, artist music promotion, and advertising telemetry.
 */

import {
  AudioChannelType,
  AudioSessionPreferences,
  AudioSessionSnapshot,
  AudioTelemetryEventType,
  CHANNEL_PRIORITIES,
  DUCKING_POLICIES,
  SponsoredTrackView,
} from "./GtexAudioTypes";
import { API } from "@/lib/api";

const PREFERENCES_STORAGE_KEY = "gtex_audio_session_preferences";

const DEFAULT_PREFERENCES: AudioSessionPreferences = {
  masterVolume: 0.85,
  isMasterMuted: false,
  channelVolumes: {
    commentary: 1.0,
    conversations: 0.95,
    sfx: 0.75,
    ambience: 0.45,
    environment: 0.40,
    user_music: 0.50,
    sponsored_music: 0.55,
  },
  channelMuted: {
    commentary: false,
    conversations: false,
    sfx: false,
    ambience: false,
    environment: false,
    user_music: false,
    sponsored_music: false,
  },
  allowSponsoredMusic: true,
};

export class GtexAudioManager {
  private prefs: AudioSessionPreferences;
  private audioCtx: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private channelGains: Map<AudioChannelType, GainNode> = new Map();
  private activeChannelSources: Map<AudioChannelType, Set<string>> = new Map([
    ["commentary", new Set()],
    ["conversations", new Set()],
    ["sfx", new Set()],
    ["ambience", new Set()],
    ["environment", new Set()],
    ["user_music", new Set()],
    ["sponsored_music", new Set()],
  ]);

  // Browser Autoplay State
  private isAutoplayBlocked = false;
  private hasUserInteracted = false;

  // Music Promotion State
  private currentSponsoredTrack: SponsoredTrackView | null = null;
  private sponsoredStatus: "idle" | "playing" | "paused" | "ducked" | "interrupted" | "blocked" | "completed" = "idle";
  private interruptedReason: string | null = null;
  private audioEl: HTMLAudioElement | null = null;
  private synthTimer: any = null;
  private synthStep = 0;
  private playbackProgressMs = 0;
  private playbackDurationMs = 180000; // default 3 mins
  private foregroundAudibleSeconds = 0;
  private reportedMilestones = new Set<string>();
  private progressInterval: any = null;
  private attentionInterval: any = null;

  // Cross-Tab Audio Session Synchronization
  private tabId = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  private tabSyncChannel: BroadcastChannel | null = null;

  // Event Listeners for reactive updates
  private listeners = new Set<(snapshot: AudioSessionSnapshot) => void>();

  constructor() {
    this.prefs = this.loadPreferences();
    this.setupWindowListeners();
    this.setupTabSync();
  }

  private setupTabSync(): void {
    if (typeof window === "undefined" || typeof BroadcastChannel === "undefined") return;
    try {
      this.tabSyncChannel = new BroadcastChannel("gtex_audio_session_bus");
      this.tabSyncChannel.onmessage = (event) => {
        if (event.data?.type === "PLAYBACK_ACQUIRED" && event.data?.tabId !== this.tabId) {
          // Another GTEX tab acquired audio focus; pause local sponsored track to prevent duplicate audio
          if (this.sponsoredStatus === "playing" || this.sponsoredStatus === "ducked") {
            this.pauseSponsoredMusic();
          }
        }
      };
    } catch {
      // BroadcastChannel disabled or sandboxed
    }
  }

  // ---------------------------------------------------------------------------
  // 1. Initialization and WebAudio Context Lifecycle
  // ---------------------------------------------------------------------------
  public getAudioContext(): AudioContext | null {
    if (typeof window === "undefined") return null;
    if (!this.audioCtx) {
      try {
        const CtxClass = window.AudioContext || (window as any).webkitAudioContext;
        if (CtxClass) {
          this.audioCtx = new CtxClass();
          this.initGainGraph();
        }
      } catch {
        // WebAudio unsupported or blocked
      }
    }
    return this.audioCtx;
  }

  private initGainGraph(): void {
    if (!this.audioCtx) return;
    try {
      this.masterGain = this.audioCtx.createGain();
      this.masterGain.connect(this.audioCtx.destination);
      this.masterGain.gain.setValueAtTime(
        this.prefs.isMasterMuted ? 0 : this.prefs.masterVolume,
        this.audioCtx.currentTime
      );

      const channels: AudioChannelType[] = [
        "commentary",
        "conversations",
        "sfx",
        "ambience",
        "environment",
        "user_music",
        "sponsored_music",
      ];

      for (const ch of channels) {
        const gain = this.audioCtx.createGain();
        gain.connect(this.masterGain);
        const effective = this.prefs.channelMuted[ch] ? 0 : this.prefs.channelVolumes[ch];
        gain.gain.setValueAtTime(effective, this.audioCtx.currentTime);
        this.channelGains.set(ch, gain);
        if (!this.activeChannelSources.has(ch)) {
          this.activeChannelSources.set(ch, new Set());
        }
      }
    } catch {
      // Gain node setup fallback
    }
  }

  private setupWindowListeners(): void {
    if (typeof window === "undefined") return;

    // First user interaction unlocks autoplay
    const unlockHandler = () => {
      this.hasUserInteracted = true;
      if (this.audioCtx && this.audioCtx.state === "suspended") {
        this.audioCtx.resume().then(() => {
          this.isAutoplayBlocked = false;
          this.notifySubscribers();
          if (this.currentSponsoredTrack && this.sponsoredStatus === "blocked") {
            this.playSponsoredTrack(this.currentSponsoredTrack);
          }
        }).catch(() => undefined);
      } else {
        this.isAutoplayBlocked = false;
        this.notifySubscribers();
      }
      window.removeEventListener("pointerdown", unlockHandler);
      window.removeEventListener("keydown", unlockHandler);
      window.removeEventListener("touchstart", unlockHandler);
    };

    window.addEventListener("pointerdown", unlockHandler, { once: true });
    window.addEventListener("keydown", unlockHandler, { once: true });
    window.addEventListener("touchstart", unlockHandler, { once: true, passive: true });
  }

  public unlockAutoplay(): Promise<void> {
    this.hasUserInteracted = true;
    const ctx = this.getAudioContext();
    if (ctx && ctx.state === "suspended") {
      return ctx.resume().then(() => {
        this.isAutoplayBlocked = false;
        this.notifySubscribers();
        if (this.currentSponsoredTrack && this.sponsoredStatus === "blocked") {
          return this.playSponsoredTrack(this.currentSponsoredTrack);
        }
      });
    }
    this.isAutoplayBlocked = false;
    this.notifySubscribers();
    if (this.currentSponsoredTrack && this.sponsoredStatus === "blocked") {
      return this.playSponsoredTrack(this.currentSponsoredTrack);
    }
    return Promise.resolve();
  }

  // ---------------------------------------------------------------------------
  // 2. Channel Volume, Priority & Ducking Engine
  // ---------------------------------------------------------------------------
  public setMasterVolume(volume: number): void {
    const clamped = Math.max(0, Math.min(1, volume));
    this.prefs.masterVolume = clamped;
    this.savePreferences();
    if (this.masterGain && this.audioCtx) {
      const target = this.prefs.isMasterMuted ? 0 : clamped;
      this.masterGain.gain.linearRampToValueAtTime(target, this.audioCtx.currentTime + 0.05);
    }
    this.notifySubscribers();
  }

  public setMasterMute(muted: boolean): void {
    this.prefs.isMasterMuted = muted;
    this.savePreferences();
    if (this.masterGain && this.audioCtx) {
      const target = muted ? 0 : this.prefs.masterVolume;
      this.masterGain.gain.linearRampToValueAtTime(target, this.audioCtx.currentTime + 0.05);
    }
    if (muted && this.sponsoredStatus === "playing" && this.currentSponsoredTrack) {
      this.reportTelemetry("muted", this.currentSponsoredTrack.campaignId);
    }
    this.notifySubscribers();
  }

  public setChannelVolume(channel: AudioChannelType, volume: number): void {
    const clamped = Math.max(0, Math.min(1, volume));
    this.prefs.channelVolumes[channel] = clamped;
    this.savePreferences();
    this.recomputeChannelGains();
    this.notifySubscribers();
  }

  public setChannelMute(channel: AudioChannelType, muted: boolean): void {
    this.prefs.channelMuted[channel] = muted;
    this.savePreferences();
    this.recomputeChannelGains();
    if (channel === "sponsored_music" && muted && this.currentSponsoredTrack) {
      this.reportTelemetry("muted", this.currentSponsoredTrack.campaignId);
    }
    this.notifySubscribers();
  }

  /**
   * Register a sound source as actively playing on a channel (e.g. commentary voiceover).
   * Automatically triggers priority ducking on lower-priority channels.
   */
  public registerActiveChannelSource(channel: AudioChannelType, sourceId: string): void {
    const set = this.activeChannelSources.get(channel);
    if (set) {
      set.add(sourceId);

      // Priority Ladder: User-selected music (Priority 20) preempts Sponsored music (Priority 10)
      if (channel === "user_music" && (this.sponsoredStatus === "playing" || this.sponsoredStatus === "ducked")) {
        this.interruptSponsoredMusic("user_music_preempted");
      }

      this.recomputeChannelGains();
      this.notifySubscribers();
    }
  }

  /**
   * Unregister a sound source when it stops playing.
   * Restores ducked channel volumes smoothly.
   */
  public unregisterActiveChannelSource(channel: AudioChannelType, sourceId: string): void {
    const set = this.activeChannelSources.get(channel);
    if (set) {
      set.delete(sourceId);

      // Restore sponsored music if user music finishes and was the cause of interruption
      if (
        channel === "user_music" &&
        !this.isChannelActive("user_music") &&
        this.sponsoredStatus === "interrupted" &&
        this.interruptedReason === "user_music_preempted"
      ) {
        this.resumeFromInterruption();
      }

      this.recomputeChannelGains();
      this.notifySubscribers();
    }
  }

  private isChannelActive(channel: AudioChannelType): boolean {
    const set = this.activeChannelSources.get(channel);
    return Boolean(set && set.size > 0);
  }

  /**
   * Recalculates effective gain for each channel, applying priority ducking rules.
   */
  private recomputeChannelGains(): void {
    const commentaryActive = this.isChannelActive("commentary");
    const conversationsActive = this.isChannelActive("conversations");

    // Update status if sponsored music is currently ducked
    if (this.sponsoredStatus === "playing" && (commentaryActive || conversationsActive)) {
      this.sponsoredStatus = "ducked";
    } else if (this.sponsoredStatus === "ducked" && !commentaryActive && !conversationsActive) {
      this.sponsoredStatus = "playing";
    }

    if (!this.audioCtx) return;
    const now = this.audioCtx.currentTime;

    for (const [channel, gainNode] of this.channelGains.entries()) {
      let baseVolume = this.prefs.channelMuted[channel] ? 0 : this.prefs.channelVolumes[channel];

      // Calculate ducking multiplier
      let duckFactor = 1.0;
      let fadeDuration = 0.4;

      if (commentaryActive) {
        const rule = DUCKING_POLICIES.commentary_active.find((r) => r.targetChannel === channel);
        if (rule) {
          duckFactor = rule.duckVolumeFactor;
          fadeDuration = rule.fadeDurationMs / 1000;
        }
      } else if (conversationsActive) {
        const rule = DUCKING_POLICIES.conversations_active.find((r) => r.targetChannel === channel);
        if (rule) {
          duckFactor = rule.duckVolumeFactor;
          fadeDuration = rule.fadeDurationMs / 1000;
        }
      }

      const targetGain = baseVolume * duckFactor;
      try {
        gainNode.gain.cancelScheduledValues(now);
        gainNode.gain.linearRampToValueAtTime(targetGain, now + fadeDuration);
      } catch {
        gainNode.gain.value = targetGain;
      }
    }
  }

  // ---------------------------------------------------------------------------
  // 3. GTEX Artist Music Promotion Engine
  // ---------------------------------------------------------------------------
  /**
   * Plays a verified sponsored track. Enforces single-track lock, rights checks,
   * browser autoplay compliance, and delivery milestone measurement.
   */
  public async playSponsoredTrack(track: SponsoredTrackView): Promise<void> {
    // 1. Rights clearance invariant check
    if (!track.rightsVerified) {
      console.warn("[GtexAudio] Refusing playback: Music campaign rights are not verified.", track.campaignId);
      return;
    }

    // 2. Stop any existing playback without abrupt pops
    this.stopSponsoredMusic(false);

    this.currentSponsoredTrack = track;
    this.reportedMilestones.clear();
    this.playbackProgressMs = 0;
    this.foregroundAudibleSeconds = 0;
    this.interruptedReason = null;
    this.reportTelemetry("play_requested", track.campaignId);

    // 3. User Music Priority Ladder: If user has active music playing, defer sponsored track
    if (this.isChannelActive("user_music")) {
      console.info("[GtexAudio] User music is active; deferring sponsored music as interrupted.");
      this.sponsoredStatus = "interrupted";
      this.interruptedReason = "user_music_preempted";
      this.reportTelemetry("interrupted", track.campaignId, { reason: "user_music_preempted" });
      this.notifySubscribers();
      return;
    }

    // 4. Check browser autoplay status
    const ctx = this.getAudioContext();
    if (ctx && ctx.state === "suspended" && !this.hasUserInteracted) {
      this.isAutoplayBlocked = true;
      this.sponsoredStatus = "blocked";
      this.reportTelemetry("play_blocked", track.campaignId);
      this.notifySubscribers();
      return;
    }

    // 5. Cross-tab session coordination: notify other tabs to pause
    if (this.tabSyncChannel) {
      try {
        this.tabSyncChannel.postMessage({
          type: "PLAYBACK_ACQUIRED",
          tabId: this.tabId,
          campaignId: track.campaignId,
        });
      } catch {
        // safe broadcast
      }
    }

    // 6. Try HTMLAudioElement if audioUrl is provided
    if (track.audioUrl) {
      try {
        if (!this.audioEl) {
          this.audioEl = new Audio();
          this.audioEl.crossOrigin = "anonymous";
        }
        this.audioEl.src = track.audioUrl;
        this.audioEl.volume = this.prefs.channelMuted.sponsored_music ? 0 : this.prefs.channelVolumes.sponsored_music;

        const playPromise = this.audioEl.play();
        if (playPromise !== undefined) {
          await playPromise;
        }

        this.sponsoredStatus = "playing";
        this.isAutoplayBlocked = false;
        this.reportTelemetry("play_started", track.campaignId);
        this.startProgressTicker();
        this.notifySubscribers();
        return;
      } catch (err: any) {
        if (err?.name === "NotAllowedError") {
          this.isAutoplayBlocked = true;
          this.sponsoredStatus = "blocked";
          this.reportTelemetry("play_blocked", track.campaignId);
          this.notifySubscribers();
          return;
        }
        // Fall back to WebAudio synth preview
      }
    }

    // 7. Procedural WebAudio Synth Preview (zero-asset reliability)
    this.startProceduralSynth(track);
    this.sponsoredStatus = "playing";
    this.isAutoplayBlocked = false;
    this.reportTelemetry("play_started", track.campaignId);
    this.startProgressTicker();
    this.notifySubscribers();
  }

  public pauseSponsoredMusic(): void {
    if (this.audioEl) {
      this.audioEl.pause();
    }
    if (this.synthTimer) {
      clearInterval(this.synthTimer);
      this.synthTimer = null;
    }
    this.sponsoredStatus = "paused";
    this.notifySubscribers();
  }

  public resumeSponsoredMusic(): void {
    if (!this.currentSponsoredTrack) return;
    if (this.isAutoplayBlocked) {
      void this.unlockAutoplay();
      return;
    }
    if (this.audioEl && this.currentSponsoredTrack.audioUrl) {
      this.audioEl.play().catch(() => {
        this.isAutoplayBlocked = true;
        this.sponsoredStatus = "blocked";
      });
    } else {
      this.startProceduralSynth(this.currentSponsoredTrack);
    }
    this.sponsoredStatus = "playing";
    this.interruptedReason = null;
    this.notifySubscribers();
  }

  /**
   * Explicitly interrupts (suspends) sponsored music due to exclusive high-priority events
   * (e.g. executive board conversation, match focus, user track).
   * Distinct from ducking where music continues playing at low volume.
   */
  public interruptSponsoredMusic(reason: string): void {
    if (this.sponsoredStatus !== "playing" && this.sponsoredStatus !== "ducked") return;

    if (this.audioEl) {
      this.audioEl.pause();
    }
    if (this.synthTimer) {
      clearInterval(this.synthTimer);
      this.synthTimer = null;
    }

    this.sponsoredStatus = "interrupted";
    this.interruptedReason = reason;

    if (this.currentSponsoredTrack) {
      this.reportTelemetry("interrupted", this.currentSponsoredTrack.campaignId, { reason });
    }
    this.notifySubscribers();
  }

  /**
   * Resumes sponsored music from an interruption state.
   */
  public resumeFromInterruption(): void {
    if (this.sponsoredStatus !== "interrupted" || !this.currentSponsoredTrack) return;

    this.interruptedReason = null;
    if (this.audioEl && this.currentSponsoredTrack.audioUrl) {
      this.audioEl.play().catch(() => {
        this.isAutoplayBlocked = true;
        this.sponsoredStatus = "blocked";
      });
    } else {
      this.startProceduralSynth(this.currentSponsoredTrack);
    }
    this.sponsoredStatus = "playing";
    this.recomputeChannelGains(); // transitions to ducked if commentary active
    this.notifySubscribers();
  }

  /**
   * Halts active playback immediately when backend reports music rights have expired or been revoked.
   * Frontend never continues playing unlicensed or expired content.
   */
  public terminatePlaybackForRightsRevocation(reason = "Rights expired or revoked"): void {
    if (!this.currentSponsoredTrack) return;
    const campaignId = this.currentSponsoredTrack.campaignId;
    console.warn(`[GtexAudio] Playback terminated: ${reason} (campaign: ${campaignId})`);

    if (this.audioEl) {
      this.audioEl.pause();
      this.audioEl.src = "";
    }
    if (this.synthTimer) {
      clearInterval(this.synthTimer);
      this.synthTimer = null;
    }
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
      this.progressInterval = null;
    }
    if (this.attentionInterval) {
      clearInterval(this.attentionInterval);
      this.attentionInterval = null;
    }

    this.reportTelemetry("interrupted", campaignId, { reason: "rights_revoked_or_expired" });
    this.sponsoredStatus = "idle";
    this.currentSponsoredTrack = null;
    this.playbackProgressMs = 0;
    this.interruptedReason = reason;
    this.notifySubscribers();
  }

  public stopSponsoredMusic(reportSkip = true): void {
    if (reportSkip && this.sponsoredStatus === "playing" && this.currentSponsoredTrack) {
      if (!this.reportedMilestones.has("milestone_50")) {
        this.reportTelemetry("skipped", this.currentSponsoredTrack.campaignId);
      }
    }

    if (this.audioEl) {
      this.audioEl.pause();
      this.audioEl.src = "";
    }
    if (this.synthTimer) {
      clearInterval(this.synthTimer);
      this.synthTimer = null;
    }
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
      this.progressInterval = null;
    }
    if (this.attentionInterval) {
      clearInterval(this.attentionInterval);
      this.attentionInterval = null;
    }

    this.sponsoredStatus = "idle";
    this.playbackProgressMs = 0;
    this.interruptedReason = null;
    this.notifySubscribers();
  }

  public cleanup(): void {
    this.stopSponsoredMusic(false);
    this.listeners.clear();
    if (this.tabSyncChannel) {
      try {
        this.tabSyncChannel.close();
      } catch {
        // safe close
      }
    }
  }

  private startProgressTicker(): void {
    if (this.progressInterval) clearInterval(this.progressInterval);
    if (this.attentionInterval) clearInterval(this.attentionInterval);

    // Track foreground audible playback duration without conflating visibility with verified human attention
    this.attentionInterval = setInterval(() => {
      if (
        typeof document !== "undefined" &&
        !document.hidden &&
        (this.sponsoredStatus === "playing" || this.sponsoredStatus === "ducked") &&
        !this.prefs.isMasterMuted &&
        !this.prefs.channelMuted.sponsored_music
      ) {
        this.foregroundAudibleSeconds += 1;
      }
    }, 1000);

    this.progressInterval = setInterval(() => {
      if (this.sponsoredStatus !== "playing" && this.sponsoredStatus !== "ducked") return;

      this.playbackProgressMs += 250;
      const progressRatio = this.playbackProgressMs / this.playbackDurationMs;

      if (!this.currentSponsoredTrack) return;
      const cid = this.currentSponsoredTrack.campaignId;

      if (progressRatio >= 0.25 && !this.reportedMilestones.has("milestone_25")) {
        this.reportedMilestones.add("milestone_25");
        this.reportTelemetry("milestone_25", cid);
      }
      if (progressRatio >= 0.50 && !this.reportedMilestones.has("milestone_50")) {
        this.reportedMilestones.add("milestone_50");
        this.reportTelemetry("milestone_50", cid);
      }
      if (progressRatio >= 0.75 && !this.reportedMilestones.has("milestone_75")) {
        this.reportedMilestones.add("milestone_75");
        this.reportTelemetry("milestone_75", cid);
      }
      if (progressRatio >= 1.0) {
        this.reportedMilestones.add("completed");
        this.reportTelemetry("completed", cid);
        this.sponsoredStatus = "completed";
        this.stopSponsoredMusic(false);
      }
      this.notifySubscribers();
    }, 250);
  }

  private startProceduralSynth(track: SponsoredTrackView): void {
    const ctx = this.getAudioContext();
    if (!ctx) return;
    if (ctx.state === "suspended") {
      ctx.resume().catch(() => undefined);
    }

    const notes = track.notes && track.notes.length > 0
      ? track.notes
      : [220, 261.63, 293.66, 329.63, 392.0, 329.63, 293.66, 261.63];

    const stepMs = 240;
    if (this.synthTimer) clearInterval(this.synthTimer);

    this.synthTimer = setInterval(() => {
      if (
        this.sponsoredStatus !== "playing" ||
        this.prefs.isMasterMuted ||
        this.prefs.channelMuted.sponsored_music
      ) {
        return;
      }
      try {
        const now = ctx.currentTime;
        const step = this.synthStep % notes.length;
        this.synthStep += 1;

        const freq = notes[step];
        const osc = ctx.createOscillator();
        const noteGain = ctx.createGain();

        osc.type = step % 2 === 0 ? "triangle" : "sine";
        osc.frequency.setValueAtTime(step % 4 === 0 ? freq * 0.5 : freq, now);

        const channelGainNode = this.channelGains.get("sponsored_music") || this.masterGain;
        const eff = this.prefs.channelVolumes.sponsored_music * 0.12;

        noteGain.gain.setValueAtTime(0.001, now);
        noteGain.gain.linearRampToValueAtTime(eff, now + 0.02);
        noteGain.gain.exponentialRampToValueAtTime(0.0008, now + stepMs / 1000);

        osc.connect(noteGain);
        if (channelGainNode) {
          noteGain.connect(channelGainNode);
        } else {
          noteGain.connect(ctx.destination);
        }

        osc.start(now);
        osc.stop(now + stepMs / 1000);
      } catch {
        // Safe procedural audio tick
      }
    }, stepMs);
  }

  // ---------------------------------------------------------------------------
  // 4. Advertising Measurement & Telemetry Integration
  // ---------------------------------------------------------------------------
  private reportTelemetry(
    eventType: AudioTelemetryEventType,
    campaignId: string,
    extraMetadata?: Record<string, any>
  ): void {
    const key = typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;

    const isForeground = typeof document !== "undefined" && !document.hidden;
    const isAudible = !this.prefs.isMasterMuted && !this.prefs.channelMuted.sponsored_music;

    // Dispatch directly to existing advertising telemetry endpoint
    if (typeof fetch !== "undefined") {
      fetch(`${API}/public/ads/events`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          campaign_id: campaignId,
          event_type: eventType,
          idempotency_key: `audio-${eventType}-${key}`,
          metadata_json: {
            source: "gtex_audio_manager",
            foreground_audible_seconds: this.foregroundAudibleSeconds,
            progress_ms: this.playbackProgressMs,
            is_foreground: isForeground,
            is_audible: isAudible,
            ...(extraMetadata || {}),
          },
        }),
      }).catch(() => undefined);
    }
  }

  // ---------------------------------------------------------------------------
  // 5. Subscription and Snapshot APIs
  // ---------------------------------------------------------------------------
  public getSnapshot(): AudioSessionSnapshot {
    const active: AudioChannelType[] = [];
    for (const [ch, set] of this.activeChannelSources.entries()) {
      if (set.size > 0) active.push(ch);
    }

    return {
      masterVolume: this.prefs.masterVolume,
      isMasterMuted: this.prefs.isMasterMuted,
      effectiveMasterGain: this.prefs.isMasterMuted ? 0 : this.prefs.masterVolume,
      channelVolumes: { ...this.prefs.channelVolumes },
      channelMuted: { ...this.prefs.channelMuted },
      activeChannels: active,
      isAutoplayBlocked: this.isAutoplayBlocked,
      hasUserInteracted: this.hasUserInteracted,
      currentSponsoredTrack: this.currentSponsoredTrack,
      sponsoredPlaybackStatus: this.sponsoredStatus,
      playbackProgressMs: this.playbackProgressMs,
      playbackDurationMs: this.playbackDurationMs,
      foregroundAudibleSeconds: this.foregroundAudibleSeconds,
      interruptedReason: this.interruptedReason,
    };
  }

  public subscribe(listener: (snapshot: AudioSessionSnapshot) => void): () => void {
    this.listeners.add(listener);
    listener(this.getSnapshot());
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notifySubscribers(): void {
    const snap = this.getSnapshot();
    for (const listener of this.listeners) {
      try {
        listener(snap);
      } catch {
        // subscriber error isolation
      }
    }
  }

  private loadPreferences(): AudioSessionPreferences {
    if (typeof window === "undefined" || !window.localStorage) {
      return { ...DEFAULT_PREFERENCES };
    }
    try {
      const raw = window.localStorage.getItem(PREFERENCES_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        return {
          ...DEFAULT_PREFERENCES,
          ...parsed,
          channelVolumes: { ...DEFAULT_PREFERENCES.channelVolumes, ...(parsed.channelVolumes || {}) },
          channelMuted: { ...DEFAULT_PREFERENCES.channelMuted, ...(parsed.channelMuted || {}) },
        };
      }
    } catch {
      // Storage unavailable
    }
    return { ...DEFAULT_PREFERENCES };
  }

  private savePreferences(): void {
    if (typeof window === "undefined" || !window.localStorage) return;
    try {
      window.localStorage.setItem(PREFERENCES_STORAGE_KEY, JSON.stringify(this.prefs));
    } catch {
      // Storage quota exceeded or disabled
    }
  }
}

// Global Singleton Export of Central Audio Session Manager
export const gtexAudio = new GtexAudioManager();
