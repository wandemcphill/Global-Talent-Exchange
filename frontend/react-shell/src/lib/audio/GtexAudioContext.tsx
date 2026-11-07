/**
 * GTEX Living Football Ecosystem — React Audio Session Context & Hooks
 * Connects React UI components to the central GtexAudioManager singleton.
 */

import React, { createContext, useContext, useEffect, useState, useMemo, useCallback } from "react";
import { gtexAudio, GtexAudioManager } from "./GtexAudioManager";
import { AudioChannelType, AudioSessionSnapshot, SponsoredTrackView } from "./GtexAudioTypes";

interface GtexAudioContextValue {
  snapshot: AudioSessionSnapshot;
  audioManager: GtexAudioManager;
  setMasterVolume: (vol: number) => void;
  setMasterMute: (muted: boolean) => void;
  setChannelVolume: (ch: AudioChannelType, vol: number) => void;
  setChannelMute: (ch: AudioChannelType, muted: boolean) => void;
  unlockAutoplay: () => Promise<void>;
  playSponsoredTrack: (track: SponsoredTrackView) => Promise<void>;
  pauseSponsoredMusic: () => void;
  resumeSponsoredMusic: () => void;
  stopSponsoredMusic: () => void;
}

const GtexAudioContext = createContext<GtexAudioContextValue | null>(null);

export const GtexAudioProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [snapshot, setSnapshot] = useState<AudioSessionSnapshot>(() => gtexAudio.getSnapshot());

  useEffect(() => {
    return gtexAudio.subscribe(setSnapshot);
  }, []);

  const value = useMemo<GtexAudioContextValue>(
    () => ({
      snapshot,
      audioManager: gtexAudio,
      setMasterVolume: (v) => gtexAudio.setMasterVolume(v),
      setMasterMute: (m) => gtexAudio.setMasterMute(m),
      setChannelVolume: (ch, v) => gtexAudio.setChannelVolume(ch, v),
      setChannelMute: (ch, m) => gtexAudio.setChannelMute(ch, m),
      unlockAutoplay: () => gtexAudio.unlockAutoplay(),
      playSponsoredTrack: (t) => gtexAudio.playSponsoredTrack(t),
      pauseSponsoredMusic: () => gtexAudio.pauseSponsoredMusic(),
      resumeSponsoredMusic: () => gtexAudio.resumeSponsoredMusic(),
      stopSponsoredMusic: () => gtexAudio.stopSponsoredMusic(true),
    }),
    [snapshot]
  );

  return <GtexAudioContext.Provider value={value}>{children}</GtexAudioContext.Provider>;
};

export function useGtexAudio() {
  const ctx = useContext(GtexAudioContext);
  if (!ctx) {
    // Graceful fallback for tests or outside provider
    return {
      snapshot: gtexAudio.getSnapshot(),
      audioManager: gtexAudio,
      setMasterVolume: (v: number) => gtexAudio.setMasterVolume(v),
      setMasterMute: (m: boolean) => gtexAudio.setMasterMute(m),
      setChannelVolume: (ch: AudioChannelType, v: number) => gtexAudio.setChannelVolume(ch, v),
      setChannelMute: (ch: AudioChannelType, m: boolean) => gtexAudio.setChannelMute(ch, m),
      unlockAutoplay: () => gtexAudio.unlockAutoplay(),
      playSponsoredTrack: (t: SponsoredTrackView) => gtexAudio.playSponsoredTrack(t),
      pauseSponsoredMusic: () => gtexAudio.pauseSponsoredMusic(),
      resumeSponsoredMusic: () => gtexAudio.resumeSponsoredMusic(),
      stopSponsoredMusic: () => gtexAudio.stopSponsoredMusic(true),
    };
  }
  return ctx;
}

export function useAudioChannel(channel: AudioChannelType) {
  const { snapshot, setChannelVolume, setChannelMute, audioManager } = useGtexAudio();
  const volume = snapshot.channelVolumes[channel] ?? 1.0;
  const isMuted = snapshot.channelMuted[channel] ?? false;
  const isActive = snapshot.activeChannels.includes(channel);

  const registerActive = useCallback(
    (sourceId: string) => audioManager.registerActiveChannelSource(channel, sourceId),
    [channel, audioManager]
  );

  const unregisterActive = useCallback(
    (sourceId: string) => audioManager.unregisterActiveChannelSource(channel, sourceId),
    [channel, audioManager]
  );

  return {
    volume,
    isMuted,
    isActive,
    setVolume: (v: number) => setChannelVolume(channel, v),
    setMute: (m: boolean) => setChannelMute(channel, m),
    registerActive,
    unregisterActive,
  };
}

export function useSponsoredMusic() {
  const {
    snapshot,
    playSponsoredTrack,
    pauseSponsoredMusic,
    resumeSponsoredMusic,
    stopSponsoredMusic,
    unlockAutoplay,
  } = useGtexAudio();

  return {
    track: snapshot.currentSponsoredTrack,
    status: snapshot.sponsoredPlaybackStatus,
    isAutoplayBlocked: snapshot.isAutoplayBlocked,
    progressMs: snapshot.playbackProgressMs,
    durationMs: snapshot.playbackDurationMs,
    progressPercent: Math.min(100, (snapshot.playbackProgressMs / Math.max(1, snapshot.playbackDurationMs)) * 100),
    foregroundAudibleSeconds: snapshot.foregroundAudibleSeconds,
    play: playSponsoredTrack,
    pause: pauseSponsoredMusic,
    resume: resumeSponsoredMusic,
    stop: stopSponsoredMusic,
    unlockAutoplay,
  };
}
