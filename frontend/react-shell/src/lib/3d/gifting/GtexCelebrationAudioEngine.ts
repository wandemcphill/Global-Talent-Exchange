/**
 * GTEX World of Football — Procedural Web Audio Celebration Synthesizer
 *
 * Synthesizes zero-latency broadcast soundscapes for all 31 canonical World of Football
 * gifts using the browser's native Web Audio API. Requires no external MP3 assets and
 * gracefully degrades in headless/muted environments.
 */

export class GtexCelebrationAudioEngine {
  private static ctx: AudioContext | null = null;

  private static getContext(): AudioContext | null {
    if (typeof window === "undefined") return null;
    const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtx) return null;
    if (!this.ctx || this.ctx.state === "closed") {
      try {
        this.ctx = new AudioCtx();
      } catch {
        return null;
      }
    }
    if (this.ctx.state === "suspended") {
      this.ctx.resume().catch(() => {});
    }
    return this.ctx;
  }

  /**
   * Plays a procedural celebration soundscape tailored to the gift's sound_key or gift_code.
   */
  public static playCelebrationCue(soundKey?: string, giftCode?: string, rarity?: string): void {
    const ctx = this.getContext();
    if (!ctx) return;

    const key = `${soundKey || ""} ${giftCode || ""}`.toLowerCase();
    const now = ctx.currentTime;

    try {
      if (key.includes("jet") || key.includes("flyby")) {
        this.playJetFlyby(ctx, now);
      } else if (key.includes("yacht") || key.includes("horn") || key.includes("goal_horn")) {
        this.playStadiumHorn(ctx, now);
        this.playStadiumRoar(ctx, now + 0.15, 2.8);
      } else if (key.includes("var") || key.includes("subs") || key.includes("tactical")) {
        this.playElectronicVarChime(ctx, now);
      } else if (key.includes("firework") || key.includes("flare") || key.includes("dubai") || key.includes("tokyo")) {
        this.playPyroFireworkBurst(ctx, now);
        this.playStadiumRoar(ctx, now + 0.2, 2.5);
      } else if (
        key.includes("trophy") ||
        key.includes("ballon") ||
        key.includes("anthem") ||
        key.includes("crown") ||
        rarity === "mythic"
      ) {
        this.playBrassFanfare(ctx, now, true);
        this.playStadiumRoar(ctx, now, 3.2);
      } else if (key.includes("whistle") || key.includes("winner") || key.includes("card") || key.includes("penalty")) {
        this.playRefereeWhistle(ctx, now);
        this.playStadiumRoar(ctx, now + 0.35, 2.8);
      } else if (key.includes("samba") || key.includes("rio") || key.includes("lagos") || key.includes("drum")) {
        this.playRhythmicDrums(ctx, now);
        this.playStadiumRoar(ctx, now + 0.2, 2.2);
      } else {
        this.playBrassFanfare(ctx, now, false);
        this.playStadiumRoar(ctx, now, 2.4);
      }
    } catch {
      // Ignore Web Audio autoplay restriction errors
    }
  }

  private static playStadiumRoar(ctx: AudioContext, startTime: number, durationSec: number): void {
    const sampleRate = ctx.sampleRate || 44100;
    const frameCount = Math.floor(sampleRate * durationSec);
    const buffer = ctx.createBuffer(1, frameCount, sampleRate);
    const data = buffer.getChannelData(0);

    for (let i = 0; i < frameCount; i++) {
      data[i] = Math.random() * 2 - 1;
    }

    const noise = ctx.createBufferSource();
    noise.buffer = buffer;

    const filter = ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.setValueAtTime(520, startTime);
    filter.frequency.exponentialRampToValueAtTime(980, startTime + durationSec * 0.4);
    filter.frequency.exponentialRampToValueAtTime(440, startTime + durationSec);
    filter.Q.value = 1.4;

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.001, startTime);
    gain.gain.linearRampToValueAtTime(0.14, startTime + 0.3);
    gain.gain.exponentialRampToValueAtTime(0.001, startTime + durationSec);

    noise.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);

    noise.start(startTime);
    noise.stop(startTime + durationSec);
  }

  private static playBrassFanfare(ctx: AudioContext, startTime: number, grand: boolean): void {
    const notes = grand ? [261.63, 329.63, 392.0, 523.25, 659.25] : [261.63, 329.63, 392.0, 523.25];
    notes.forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sawtooth";
      const noteStart = startTime + idx * 0.14;
      const noteDuration = idx === notes.length - 1 ? 1.1 : 0.25;

      osc.frequency.setValueAtTime(freq, noteStart);

      const filter = ctx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.setValueAtTime(1800, noteStart);

      gain.gain.setValueAtTime(0.001, noteStart);
      gain.gain.linearRampToValueAtTime(0.08, noteStart + 0.04);
      gain.gain.exponentialRampToValueAtTime(0.001, noteStart + noteDuration);

      osc.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);

      osc.start(noteStart);
      osc.stop(noteStart + noteDuration);
    });
  }

  private static playJetFlyby(ctx: AudioContext, startTime: number): void {
    const duration = 2.6;
    const sampleRate = ctx.sampleRate || 44100;
    const buffer = ctx.createBuffer(1, Math.floor(sampleRate * duration), sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < data.length; i++) {
      data[i] = Math.random() * 2 - 1;
    }

    const noise = ctx.createBufferSource();
    noise.buffer = buffer;

    const filter = ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.Q.value = 3.0;
    filter.frequency.setValueAtTime(160, startTime);
    filter.frequency.exponentialRampToValueAtTime(1650, startTime + duration * 0.45);
    filter.frequency.exponentialRampToValueAtTime(110, startTime + duration);

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.001, startTime);
    gain.gain.linearRampToValueAtTime(0.22, startTime + duration * 0.45);
    gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);

    noise.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);

    noise.start(startTime);
    noise.stop(startTime + duration);
  }

  private static playRefereeWhistle(ctx: AudioContext, startTime: number): void {
    [2820, 3140].forEach((freq) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, startTime);
      gain.gain.setValueAtTime(0.001, startTime);
      gain.gain.linearRampToValueAtTime(0.07, startTime + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.32);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(startTime);
      osc.stop(startTime + 0.34);
    });
  }

  private static playRhythmicDrums(ctx: AudioContext, startTime: number): void {
    const beats = [0, 0.22, 0.44, 0.6, 0.78, 1.0];
    beats.forEach((offset, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const t = startTime + offset;
      osc.type = "triangle";
      osc.frequency.setValueAtTime(idx % 2 === 0 ? 130 : 195, t);
      osc.frequency.exponentialRampToValueAtTime(48, t + 0.16);

      gain.gain.setValueAtTime(0.14, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.18);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(t);
      osc.stop(t + 0.19);
    });
  }

  private static playStadiumHorn(ctx: AudioContext, startTime: number): void {
    [110, 164.81, 220].forEach((freq) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(freq, startTime);
      gain.gain.setValueAtTime(0.001, startTime);
      gain.gain.linearRampToValueAtTime(0.09, startTime + 0.08);
      gain.gain.exponentialRampToValueAtTime(0.001, startTime + 1.45);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(startTime);
      osc.stop(startTime + 1.5);
    });
  }

  private static playElectronicVarChime(ctx: AudioContext, startTime: number): void {
    [880, 1174.66, 1318.51].forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const t = startTime + idx * 0.11;
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, t);
      gain.gain.setValueAtTime(0.001, t);
      gain.gain.linearRampToValueAtTime(0.08, t + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.28);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(t);
      osc.stop(t + 0.3);
    });
  }

  private static playPyroFireworkBurst(ctx: AudioContext, startTime: number): void {
    [0, 0.28, 0.55].forEach((offset) => {
      const t = startTime + offset;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "triangle";
      osc.frequency.setValueAtTime(340, t);
      osc.frequency.exponentialRampToValueAtTime(42, t + 0.32);
      gain.gain.setValueAtTime(0.14, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.35);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(t);
      osc.stop(t + 0.36);
    });
  }
}
