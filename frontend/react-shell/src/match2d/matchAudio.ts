/**
 * Zero-asset procedural Web Audio API sound engine for 2D Matchday Broadcast.
 * Synthesizes stadium crowd ambiance, final-third excitement swells, referee whistles,
 * ball kick thuds, goalkeeper save impacts, and goal celebration roars.
 *
 * Gracefully no-ops in SSR, Jest, or browsers where AudioContext is unavailable or blocked.
 */

export type MatchSoundCue =
  | "kickoff"
  | "pass"
  | "shot"
  | "save"
  | "goal"
  | "foul"
  | "yellow_card"
  | "red_card"
  | "penalty"
  | "corner"
  | "halftime"
  | "fulltime"
  | "tactical_order";

type AudioContextConstructor = typeof AudioContext;

function resolveAudioContextCtor(): AudioContextConstructor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    AudioContext?: AudioContextConstructor;
    webkitAudioContext?: AudioContextConstructor;
  };
  return w.AudioContext || w.webkitAudioContext || null;
}

export class MatchAudioEngine {
  private ctx: AudioContext | null = null;
  private crowdGain: GainNode | null = null;
  private crowdFilter: BiquadFilterNode | null = null;
  private crowdSource: AudioBufferSourceNode | null = null;
  private enabled = false;
  private lastEventKey = "";
  private lastCueMs = 0;

  isEnabled(): boolean {
    return this.enabled;
  }

  setEnabled(next: boolean): boolean {
    this.enabled = Boolean(next);
    if (!this.enabled) {
      this.stopCrowdBed();
      return false;
    }
    this.ensureContext();
    this.startCrowdBed();
    return this.enabled;
  }

  private ensureContext(): AudioContext | null {
    if (this.ctx) {
      if (this.ctx.state === "suspended" && typeof this.ctx.resume === "function") {
        void this.ctx.resume().catch(() => {});
      }
      return this.ctx;
    }
    const Ctor = resolveAudioContextCtor();
    if (!Ctor) return null;
    try {
      this.ctx = new Ctor();
      return this.ctx;
    } catch {
      this.ctx = null;
      return null;
    }
  }

  private startCrowdBed(): void {
    const ctx = this.ensureContext();
    if (!ctx || this.crowdSource) return;
    try {
      const sampleRate = ctx.sampleRate || 44100;
      const length = sampleRate * 3;
      const buffer = ctx.createBuffer(1, length, sampleRate);
      const data = buffer.getChannelData(0);
      // Pink-ish stadium murmur noise
      let b0 = 0;
      let b1 = 0;
      let b2 = 0;
      for (let i = 0; i < length; i += 1) {
        const white = Math.random() * 2 - 1;
        b0 = 0.997 * b0 + white * 0.029;
        b1 = 0.985 * b1 + white * 0.032;
        b2 = 0.95 * b2 + white * 0.048;
        data[i] = (b0 + b1 + b2 + white * 0.015) * 0.35;
      }

      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.loop = true;

      const filter = ctx.createBiquadFilter();
      filter.type = "bandpass";
      filter.frequency.value = 520;
      filter.Q.value = 0.75;

      const gain = ctx.createGain();
      gain.gain.value = 0.055;

      source.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);
      source.start(0);

      this.crowdSource = source;
      this.crowdFilter = filter;
      this.crowdGain = gain;
    } catch {
      // Ignore audio hardware restrictions
    }
  }

  private stopCrowdBed(): void {
    try {
      this.crowdSource?.stop();
      this.crowdSource?.disconnect();
      this.crowdFilter?.disconnect();
      this.crowdGain?.disconnect();
    } catch {
      // Ignore
    }
    this.crowdSource = null;
    this.crowdFilter = null;
    this.crowdGain = null;
  }

  /**
   * Modulates the ambient crowd murmur based on ball proximity to goal and match pressure.
   */
  updateAtmosphere(input: {
    ballX?: number | null;
    dangerZone?: string | null;
    eventType?: string | null;
    minute?: number;
  }): void {
    if (!this.enabled) return;
    const ctx = this.ensureContext();
    if (!ctx || !this.crowdGain || !this.crowdFilter) return;

    const bx = typeof input.ballX === "number" && Number.isFinite(input.ballX) ? input.ballX : 0.5;
    const distFromCenter = Math.abs(bx - 0.5) * 2; // 0 at midfield, 1 at goal line
    const isBox = input.dangerZone === "box" || distFromCenter > 0.68;
    const isGoal = String(input.eventType || "").toLowerCase() === "goal";

    const targetGain = isGoal ? 0.22 : isBox ? 0.11 : 0.045 + distFromCenter * 0.045;
    const targetFreq = isGoal ? 1150 : isBox ? 820 : 480 + distFromCenter * 240;

    try {
      const now = ctx.currentTime;
      this.crowdGain.gain.setTargetAtTime(targetGain, now, 0.25);
      this.crowdFilter.frequency.setTargetAtTime(targetFreq, now, 0.25);
    } catch {
      // Ignore
    }

    const ev = String(input.eventType || "").toLowerCase();
    if (!ev) return;
    const eventKey = `${ev}:${input.minute ?? 0}`;
    if (eventKey === this.lastEventKey) return;
    this.lastEventKey = eventKey;

    if (ev === "goal" || ev === "penalty_goal") this.triggerCue("goal");
    else if (ev === "save") this.triggerCue("save");
    else if (ev === "shot" || ev === "miss") this.triggerCue("shot");
    else if (ev === "foul") this.triggerCue("foul");
    else if (ev === "yellow_card") this.triggerCue("yellow_card");
    else if (ev === "red_card") this.triggerCue("red_card");
    else if (ev === "penalty") this.triggerCue("penalty");
    else if (ev === "kickoff") this.triggerCue("kickoff");
    else if (ev === "halftime") this.triggerCue("halftime");
    else if (ev === "fulltime") this.triggerCue("fulltime");
  }

  triggerCue(cue: MatchSoundCue): void {
    if (!this.enabled) return;
    const nowMs = typeof performance !== "undefined" ? performance.now() : Date.now();
    if (nowMs - this.lastCueMs < 140 && cue !== "goal") return;
    this.lastCueMs = nowMs;

    const ctx = this.ensureContext();
    if (!ctx) return;

    try {
      switch (cue) {
        case "kickoff":
        case "foul":
        case "yellow_card":
        case "penalty":
          this.playWhistle(ctx, 0.26, 1);
          break;
        case "red_card":
        case "halftime":
          this.playWhistle(ctx, 0.22, 2);
          break;
        case "fulltime":
          this.playWhistle(ctx, 0.25, 3);
          break;
        case "pass":
          this.playKickThud(ctx, 95, 0.08);
          break;
        case "shot":
        case "save":
          this.playKickThud(ctx, 130, 0.16);
          break;
        case "goal":
          this.playKickThud(ctx, 140, 0.18);
          this.playGoalRoar(ctx);
          break;
        case "tactical_order":
          this.playTouchlineChime(ctx);
          break;
        default:
          break;
      }
    } catch {
      // Ignore synthesis errors in restricted environments
    }
  }

  private playWhistle(ctx: AudioContext, durationSec: number, pips: number): void {
    for (let i = 0; i < pips; i += 1) {
      const start = ctx.currentTime + i * (durationSec + 0.09);
      const stop = start + (i === pips - 1 && pips > 1 ? durationSec * 1.45 : durationSec);
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gain = ctx.createGain();

      osc1.type = "sine";
      osc2.type = "triangle";
      osc1.frequency.setValueAtTime(2780, start);
      osc1.frequency.exponentialRampToValueAtTime(2920, start + 0.06);
      osc2.frequency.setValueAtTime(2895, start);

      gain.gain.setValueAtTime(0.001, start);
      gain.gain.exponentialRampToValueAtTime(0.08, start + 0.025);
      gain.gain.exponentialRampToValueAtTime(0.001, stop);

      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(ctx.destination);

      osc1.start(start);
      osc2.start(start);
      osc1.stop(stop);
      osc2.stop(stop);
    }
  }

  private playKickThud(ctx: AudioContext, startFreq: number, peakGain: number): void {
    const start = ctx.currentTime;
    const stop = start + 0.11;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "sine";
    osc.frequency.setValueAtTime(startFreq, start);
    osc.frequency.exponentialRampToValueAtTime(34, stop);

    gain.gain.setValueAtTime(peakGain, start);
    gain.gain.exponentialRampToValueAtTime(0.001, stop);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(start);
    osc.stop(stop);
  }

  private playGoalRoar(ctx: AudioContext): void {
    if (!this.crowdGain || !this.crowdFilter) return;
    const now = ctx.currentTime;
    this.crowdGain.gain.cancelScheduledValues(now);
    this.crowdGain.gain.setValueAtTime(0.09, now);
    this.crowdGain.gain.linearRampToValueAtTime(0.26, now + 0.18);
    this.crowdGain.gain.exponentialRampToValueAtTime(0.065, now + 3.2);

    this.crowdFilter.frequency.cancelScheduledValues(now);
    this.crowdFilter.frequency.setValueAtTime(600, now);
    this.crowdFilter.frequency.linearRampToValueAtTime(1350, now + 0.25);
    this.crowdFilter.frequency.exponentialRampToValueAtTime(520, now + 3.2);
  }

  private playTouchlineChime(ctx: AudioContext): void {
    const start = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(587.33, start); // D5
    osc.frequency.setValueAtTime(880, start + 0.07); // A5
    gain.gain.setValueAtTime(0.05, start);
    gain.gain.exponentialRampToValueAtTime(0.001, start + 0.22);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(start);
    osc.stop(start + 0.22);
  }

  dispose(): void {
    this.stopCrowdBed();
    if (this.ctx && typeof this.ctx.close === "function") {
      void this.ctx.close().catch(() => {});
    }
    this.ctx = null;
    this.enabled = false;
  }
}

export const sharedMatchAudio = new MatchAudioEngine();
