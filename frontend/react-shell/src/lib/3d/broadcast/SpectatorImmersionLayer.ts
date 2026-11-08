/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Spectator Immersion Layer: AI Commentary Subtitles, Watch-Party Sync & Haptics (Phase 4).
 *
 * Implements:
 * 1. AI Commentary Subtitles with dynamic tone, intensity meter, and multi-speaker cues.
 * 2. Watch-Party Synchronized Reactions (floating emoji cheer bursts, spectator crowd meter).
 * 3. Browser Haptic Vibration Bridge (navigator.vibrate) for goals, woodworks, fouls, and whistle.
 *
 * Safe execution in both browser and test environments; zero memory leaks.
 */

export type CommentaryTone = "dramatic" | "celebratory" | "analytical" | "tactical" | "neutral";

export interface CommentaryCue {
  id: string;
  speaker: string;
  text: string;
  tone: CommentaryTone;
  intensity: number; // 0.0 to 1.0
  remainingSec: number;
}

export interface SpectatorReactionItem {
  id: string;
  emoji: string;
  senderName: string;
  xPct: number; // 0% to 100% horizontal placement
  remainingSec: number;
}

export interface SpectatorImmersionSummary {
  currentCommentary: CommentaryCue | null;
  activeReactionCount: number;
  cheerMeter: number; // 0 to 100
  hapticsEnabled: boolean;
  hapticsSupported: boolean;
  watchPartyRoomSize: number;
  syncLatencyMs: number;
}

export interface SpectatorImmersionOptions {
  hapticsEnabled?: boolean;
  watchPartyRoomSize?: number;
}

export class SpectatorImmersionLayer {
  private currentCommentary: CommentaryCue | null = null;
  private recentReactions: SpectatorReactionItem[] = [];
  private hapticsEnabled: boolean = true;
  private watchPartyRoomSize: number = 24;
  private cheerMeter: number = 15; // Baseline room cheer energy
  private syncLatencyMs: number = 42;
  private commentaryIndex: number = 0;

  constructor(options?: SpectatorImmersionOptions) {
    if (typeof options?.hapticsEnabled === "boolean") {
      this.hapticsEnabled = options.hapticsEnabled;
    }
    if (typeof options?.watchPartyRoomSize === "number") {
      this.watchPartyRoomSize = options.watchPartyRoomSize;
    }
  }

  public isHapticsSupported(): boolean {
    return typeof navigator !== "undefined" && typeof navigator.vibrate === "function";
  }

  public setHapticsEnabled(enabled: boolean): void {
    this.hapticsEnabled = enabled;
  }

  public isHapticsEnabled(): boolean {
    return this.hapticsEnabled;
  }

  /**
   * Triggers a vibration pattern if haptics are enabled and supported.
   */
  public triggerVibration(pattern: number | number[]): boolean {
    if (!this.hapticsEnabled || !this.isHapticsSupported()) {
      return false;
    }
    try {
      return navigator.vibrate(pattern);
    } catch {
      return false;
    }
  }

  /**
   * Adds an emoji reaction burst from a watch-party spectator.
   */
  public sendReaction(emoji: string, senderName: string = "Spectator"): void {
    const reaction: SpectatorReactionItem = {
      id: `rx_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      emoji,
      senderName,
      xPct: 15 + Math.random() * 70, // Spread across middle 70% of screen
      remainingSec: 2.8,
    };
    this.recentReactions.push(reaction);
    this.cheerMeter = Math.min(100, this.cheerMeter + 8);
  }

  /**
   * Dispatches commentary, crowd reaction, and haptic buzz on match events.
   */
  public handleMatchEvent(
    eventType: string,
    side: "home" | "away" | "both" = "both",
    details?: { playerName?: string; clock?: string }
  ): void {
    const ev = (eventType || "").toLowerCase();
    this.commentaryIndex++;

    switch (ev) {
      case "goal": {
        this.triggerVibration([150, 80, 250, 100, 400]);
        this.sendReaction("⚽", "WatchParty");
        this.sendReaction("🔥", "FanZone");
        this.currentCommentary = {
          id: `comm_${this.commentaryIndex}`,
          speaker: "Peter Drury AI",
          text: details?.playerName
            ? `GOAL! What an extraordinary moment for ${details.playerName}! Pure perfection!`
            : "GOAL! Sensational strike! The stadium erupts in utter ecstasy!",
          tone: "celebratory",
          intensity: 1.0,
          remainingSec: 7.0,
        };
        this.cheerMeter = 100;
        break;
      }

      case "save": {
        this.triggerVibration([80, 40, 120]);
        this.sendReaction("🧤", "WatchParty");
        this.currentCommentary = {
          id: `comm_${this.commentaryIndex}`,
          speaker: "Martin Tyler AI",
          text: "What a save! Brilliant agility to keep that out!",
          tone: "dramatic",
          intensity: 0.85,
          remainingSec: 5.0,
        };
        this.cheerMeter = Math.min(100, this.cheerMeter + 25);
        break;
      }

      case "miss":
      case "shot": {
        this.triggerVibration(60);
        this.sendReaction("😱", "WatchParty");
        this.currentCommentary = {
          id: `comm_${this.commentaryIndex}`,
          speaker: "Emma Hayes AI",
          text: "Just inches wide of the upright! That was dangerously close.",
          tone: "analytical",
          intensity: 0.7,
          remainingSec: 4.5,
        };
        this.cheerMeter = Math.min(100, this.cheerMeter + 15);
        break;
      }

      case "red_card": {
        this.triggerVibration([120, 60, 200]);
        this.sendReaction("🟥", "WatchParty");
        this.currentCommentary = {
          id: `comm_${this.commentaryIndex}`,
          speaker: "Peter Drury AI",
          text: "RED CARD! The referee brandishes the ultimate sanction! Down to ten men!",
          tone: "dramatic",
          intensity: 0.95,
          remainingSec: 6.5,
        };
        this.cheerMeter = Math.min(100, this.cheerMeter + 40);
        break;
      }

      case "yellow_card": {
        this.triggerVibration([70, 40, 70]);
        this.sendReaction("🟨", "WatchParty");
        this.currentCommentary = {
          id: `comm_${this.commentaryIndex}`,
          speaker: "Martin Tyler AI",
          text: "Yellow card issued. A firm warning for that challenge.",
          tone: "tactical",
          intensity: 0.6,
          remainingSec: 4.0,
        };
        break;
      }

      case "var":
      case "var_review": {
        this.triggerVibration([90, 50, 90]);
        this.sendReaction("📺", "WatchParty");
        this.currentCommentary = {
          id: `comm_${this.commentaryIndex}`,
          speaker: "Emma Hayes AI",
          text: "VAR check in progress. Tension mounts as the referee consults the monitor.",
          tone: "analytical",
          intensity: 0.8,
          remainingSec: 6.0,
        };
        break;
      }

      case "fulltime": {
        this.triggerVibration([200, 100, 200, 100, 400]);
        this.sendReaction("👏", "WatchParty");
        this.currentCommentary = {
          id: `comm_${this.commentaryIndex}`,
          speaker: "Peter Drury AI",
          text: "FULL TIME! That brings an exhilarating contest to its dramatic close!",
          tone: "celebratory",
          intensity: 0.9,
          remainingSec: 8.0,
        };
        this.cheerMeter = 80;
        break;
      }

      default: {
        break;
      }
    }
  }

  /**
   * Updates timers and decays cheer meter.
   */
  public update(deltaSec: number): void {
    // 1. Commentary countdown
    if (this.currentCommentary) {
      this.currentCommentary.remainingSec -= deltaSec;
      if (this.currentCommentary.remainingSec <= 0) {
        this.currentCommentary = null;
      }
    }

    // 2. Reaction item countdowns
    for (let i = this.recentReactions.length - 1; i >= 0; i--) {
      this.recentReactions[i].remainingSec -= deltaSec;
      if (this.recentReactions[i].remainingSec <= 0) {
        this.recentReactions.splice(i, 1);
      }
    }

    // 3. Decay cheer meter toward baseline 15
    if (this.cheerMeter > 15) {
      this.cheerMeter = Math.max(15, this.cheerMeter - deltaSec * 8);
    }
  }

  public getCurrentCommentaryCue(): CommentaryCue | null {
    return this.currentCommentary;
  }

  public getRecentReactions(): readonly SpectatorReactionItem[] {
    return this.recentReactions;
  }

  public getSummary(): SpectatorImmersionSummary {
    return {
      currentCommentary: this.currentCommentary,
      activeReactionCount: this.recentReactions.length,
      cheerMeter: Math.round(this.cheerMeter),
      hapticsEnabled: this.hapticsEnabled,
      hapticsSupported: this.isHapticsSupported(),
      watchPartyRoomSize: this.watchPartyRoomSize,
      syncLatencyMs: this.syncLatencyMs,
    };
  }

  public dispose(): void {
    this.currentCommentary = null;
    this.recentReactions = [];
  }
}
