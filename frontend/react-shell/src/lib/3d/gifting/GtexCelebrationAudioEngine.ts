/**
 * GTEX World of Football — Procedural Web Audio Celebration Synthesizer
 *
 * Synthesizes zero-latency broadcast soundscapes for the canonical gift catalog
 * using the browser's native Web Audio API. Requires no external audio files.
 */

const SOUND_CUES: Record<string, string> = {
  whistle_pop: "whistle",
  training_whistle_rise: "whistle",
  crowd_chant: "chant",
  san_siro_curva_chant: "chant",
  crowd_roar: "chant",
  crowd_cheer: "chant",
  goal_roar: "goal_roar",
  net_ripple_roar: "goal_roar",
  stadium_award_roar: "goal_roar",
  wembley_arch_roar: "goal_roar",
  card_reveal_riser: "card_reveal",
  mvp_card_hit: "card_reveal",
  tactics_board_ping: "board_ping",
  tactics_crown_hit: "crown_hit",
  dugout_spotlight: "swell",
  passing_lines_swell: "swell",
  bicycle_kick_whoosh: "whoosh",
  keeper_save_snap: "snap",
  golden_goal_explosion: "explosion",
  hat_trick_fireworks: "fireworks",
  maracana_samba_cheer: "drums",
  rio_carnival_beat: "drums",
  lagos_afrobeats_pulse: "drums",
  camp_nou_hymn_swell: "ceremony",
  celestial_stadium_choir: "ceremony",
  stadium_ceremony_roar: "ceremony",
  paris_lights_twinkle: "twinkle",
  nyc_harbor_horn: "harbor_horn",
  yacht_harbor_chime: "harbor_chime",
  jet_turbine_flyby: "jet",
};

const CODE_CUES: Record<string, string> = {
  private_jet: "jet",
  superyacht: "harbor_chime",
  ballon_dor: "ceremony",
  whistle_blow: "whistle",
  maracana_stadium: "drums",
  rio_skyline: "drums",
  lagos_skyline: "drums",
  paris_skyline: "twinkle",
  new_york_skyline: "harbor_horn",
};

export function resolveCelebrationCue(soundKey?: string, giftCode?: string, _rarity?: string): string {
  const sound = (soundKey || "").trim().toLowerCase();
  const code = (giftCode || "").trim().toLowerCase();
  if (sound && SOUND_CUES[sound]) return SOUND_CUES[sound];
  if (!sound && CODE_CUES[code]) return CODE_CUES[code];
  return "fallback";
}

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
   * Plays a procedural celebration soundscape tailored to the gift's sound_key.
   */
  public static playCelebrationCue(soundKey?: string, giftCode?: string, rarity?: string): void {
    const ctx = this.getContext();
    if (!ctx) return;
    const cue = resolveCelebrationCue(soundKey, giftCode, rarity);
    const now = ctx.currentTime;

    try {
      this.playCue(ctx, now, cue);
      if ((rarity || "").toLowerCase() === "mythic" && cue !== "ceremony") {
        this.playCeremony(ctx, now + 0.05);
      }
    } catch {
      // Ignore Web Audio autoplay restriction errors
    }
  }

  private static playCue(ctx: AudioContext, startTime: number, cue: string): void {
    switch (cue) {
      case "whistle":
        this.playRefereeWhistle(ctx, startTime);
        break;
      case "chant":
        this.playStadiumRoar(ctx, startTime, 2.4);
        break;
      case "goal_roar":
        this.playStadiumHorn(ctx, startTime);
        this.playStadiumRoar(ctx, startTime + 0.12, 2.6);
        break;
      case "card_reveal":
        this.playCardReveal(ctx, startTime);
        break;
      case "board_ping":
        this.playElectronicVarChime(ctx, startTime);
        break;
      case "crown_hit":
        this.playCrownHit(ctx, startTime);
        break;
      case "swell":
        this.playBrassFanfare(ctx, startTime, false);
        break;
      case "whoosh":
        this.playWhoosh(ctx, startTime);
        break;
      case "snap":
        this.playSnap(ctx, startTime);
        break;
      case "explosion":
        this.playPyroFireworkBurst(ctx, startTime);
        this.playStadiumRoar(ctx, startTime + 0.08, 1.8);
        break;
      case "fireworks":
        this.playPyroFireworkBurst(ctx, startTime);
        this.playPyroFireworkBurst(ctx, startTime + 0.7);
        break;
      case "drums":
        this.playRhythmicDrums(ctx, startTime);
        this.playStadiumRoar(ctx, startTime + 0.15, 2.2);
        break;
      case "ceremony":
        this.playCeremony(ctx, startTime);
        break;
      case "twinkle":
        this.playTwinkle(ctx, startTime);
        break;
      case "harbor_horn":
        this.playStadiumHorn(ctx, startTime);
        break;
      case "harbor_chime":
        this.playHarborChime(ctx, startTime);
        break;
      case "jet":
        this.playJetFlyby(ctx, startTime);
        break;
      default:
        this.playBrassFanfare(ctx, startTime, false);
        this.playStadiumRoar(ctx, startTime, 1.6);
        break;
    }
  }

  private static playCeremony(ctx: AudioContext, startTime: number): void {
    this.playBrassFanfare(ctx, startTime, true);
    this.playStadiumRoar(ctx, startTime, 3.0);
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

  private static playWhoosh(ctx: AudioContext, startTime: number): void {
    const duration = 0.9;
    const sampleRate = ctx.sampleRate || 44100;
    const buffer = ctx.createBuffer(1, Math.floor(sampleRate * duration), sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
    const noise = ctx.createBufferSource();
    noise.buffer = buffer;
    const filter = ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.Q.value = 0.8;
    filter.frequency.setValueAtTime(240, startTime);
    filter.frequency.exponentialRampToValueAtTime(1800, startTime + duration);
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.001, startTime);
    gain.gain.linearRampToValueAtTime(0.16, startTime + 0.08);
    gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
    noise.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);
    noise.start(startTime);
    noise.stop(startTime + duration);
  }

  private static playSnap(ctx: AudioContext, startTime: number): void {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "square";
    osc.frequency.setValueAtTime(980, startTime);
    osc.frequency.exponentialRampToValueAtTime(180, startTime + 0.08);
    gain.gain.setValueAtTime(0.12, startTime);
    gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.09);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(startTime);
    osc.stop(startTime + 0.1);
  }

  private static playCardReveal(ctx: AudioContext, startTime: number): void {
    [392, 523.25, 659.25, 783.99].forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const t = startTime + idx * 0.09;
      osc.type = "triangle";
      osc.frequency.setValueAtTime(freq, t);
      gain.gain.setValueAtTime(0.001, t);
      gain.gain.linearRampToValueAtTime(0.07, t + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.35);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(t);
      osc.stop(t + 0.36);
    });
  }

  private static playCrownHit(ctx: AudioContext, startTime: number): void {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "triangle";
    osc.frequency.setValueAtTime(220, startTime);
    osc.frequency.exponentialRampToValueAtTime(880, startTime + 0.12);
    gain.gain.setValueAtTime(0.1, startTime);
    gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.28);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(startTime);
    osc.stop(startTime + 0.3);
    this.playElectronicVarChime(ctx, startTime + 0.16);
  }

  private static playTwinkle(ctx: AudioContext, startTime: number): void {
    [1046, 1318, 1568, 2093].forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const t = startTime + idx * 0.18;
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, t);
      gain.gain.setValueAtTime(0.001, t);
      gain.gain.linearRampToValueAtTime(0.05, t + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.4);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(t);
      osc.stop(t + 0.42);
    });
  }

  private static playHarborChime(ctx: AudioContext, startTime: number): void {
    [523.25, 659.25, 783.99].forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const t = startTime + idx * 0.22;
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, t);
      gain.gain.setValueAtTime(0.001, t);
      gain.gain.linearRampToValueAtTime(0.06, t + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 1.1);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(t);
      osc.stop(t + 1.15);
    });
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
