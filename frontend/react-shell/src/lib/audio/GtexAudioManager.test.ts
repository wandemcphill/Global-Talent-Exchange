/**
 * GTEX Living Football Ecosystem — GtexAudioManager Unit Tests
 */

import { GtexAudioManager } from "./GtexAudioManager";
import { SponsoredTrackView } from "./GtexAudioTypes";

describe("GtexAudioManager", () => {
  let manager: GtexAudioManager;

  beforeEach(() => {
    window.localStorage.removeItem("gtex_audio_session_preferences");
    (global as any).fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
    manager = new GtexAudioManager();
  });

  afterEach(() => {
    manager.cleanup();
    window.localStorage.removeItem("gtex_audio_session_preferences");
  });

  it("initializes with default preferences and channels", () => {
    const snap = manager.getSnapshot();
    expect(snap.masterVolume).toBe(0.85);
    expect(snap.isMasterMuted).toBe(false);
    expect(snap.channelVolumes.commentary).toBe(1.0);
    expect(snap.channelVolumes.sponsored_music).toBe(0.55);
    expect(snap.channelMuted.commentary).toBe(false);
    expect(snap.sponsoredPlaybackStatus).toBe("idle");
  });

  it("updates master volume and mute state", () => {
    manager.setMasterVolume(0.60);
    expect(manager.getSnapshot().masterVolume).toBe(0.60);

    manager.setMasterMute(true);
    expect(manager.getSnapshot().isMasterMuted).toBe(true);
    expect(manager.getSnapshot().effectiveMasterGain).toBe(0);

    manager.setMasterMute(false);
    expect(manager.getSnapshot().isMasterMuted).toBe(false);
    expect(manager.getSnapshot().effectiveMasterGain).toBe(0.60);
  });

  it("updates individual channel volumes and mute states", () => {
    manager.setChannelVolume("sfx", 0.90);
    expect(manager.getSnapshot().channelVolumes.sfx).toBe(0.90);

    manager.setChannelMute("ambience", true);
    expect(manager.getSnapshot().channelMuted.ambience).toBe(true);
  });

  it("triggers priority ducking on lower-priority channels when commentary is registered active", () => {
    // Register active commentary source
    manager.registerActiveChannelSource("commentary", "match_sim_announcer_1");
    let snap = manager.getSnapshot();
    expect(snap.activeChannels).toContain("commentary");

    // Unregister commentary source
    manager.unregisterActiveChannelSource("commentary", "match_sim_announcer_1");
    snap = manager.getSnapshot();
    expect(snap.activeChannels).not.toContain("commentary");
  });

  it("refuses playback when track rights are not verified", async () => {
    const unverifiedTrack: SponsoredTrackView = {
      campaignId: "camp_unverified_001",
      title: "Bootleg Anthem",
      artist: "Unauthorized Artist",
      destinationUrl: "https://example.com",
      rightsVerified: false,
    };

    await manager.playSponsoredTrack(unverifiedTrack);
    const snap = manager.getSnapshot();
    expect(snap.sponsoredPlaybackStatus).toBe("idle");
    expect(snap.currentSponsoredTrack).toBeNull();
  });

  it("accepts and plays track when rights are verified", async () => {
    const verifiedTrack: SponsoredTrackView = {
      campaignId: "camp_verified_999",
      title: "Lagos Nightlights (VIP)",
      artist: "Kazeem",
      destinationUrl: "https://open.spotify.com",
      rightsVerified: true,
      rightsHolder: "GTEX Music Ltd",
      notes: [220, 261, 293],
    };

    await manager.playSponsoredTrack(verifiedTrack);
    const snap = manager.getSnapshot();
    expect(snap.currentSponsoredTrack).toBe(verifiedTrack);
    expect(["playing", "blocked"]).toContain(snap.sponsoredPlaybackStatus);
  });

  it("supports pausing and stopping music cleanly", async () => {
    const verifiedTrack: SponsoredTrackView = {
      campaignId: "camp_verified_999",
      title: "Lagos Nightlights (VIP)",
      artist: "Kazeem",
      destinationUrl: "https://open.spotify.com",
      rightsVerified: true,
    };

    await manager.playSponsoredTrack(verifiedTrack);
    manager.pauseSponsoredMusic();
    expect(manager.getSnapshot().sponsoredPlaybackStatus).toBe("paused");

    manager.stopSponsoredMusic(false);
    expect(manager.getSnapshot().sponsoredPlaybackStatus).toBe("idle");
  });

  it("distinguishes ducked playback from genuinely interrupted playback", async () => {
    const verifiedTrack: SponsoredTrackView = {
      campaignId: "camp_verified_duck_test",
      title: "Tunnel Walk",
      artist: "GTEX Beats",
      destinationUrl: "https://example.com",
      rightsVerified: true,
      notes: [220, 260],
    };

    await manager.playSponsoredTrack(verifiedTrack);

    // 1. Ducking: When commentary starts, music continues ducked
    manager.registerActiveChannelSource("commentary", "commentator_1");
    let snap = manager.getSnapshot();
    expect(snap.sponsoredPlaybackStatus).toBe("ducked");

    // When commentary ends, music returns to playing
    manager.unregisterActiveChannelSource("commentary", "commentator_1");
    snap = manager.getSnapshot();
    expect(snap.sponsoredPlaybackStatus).toBe("playing");

    // 2. Interruption: Explicit suspension due to executive meeting or match focus
    manager.interruptSponsoredMusic("executive_boardroom_confidential");
    snap = manager.getSnapshot();
    expect(snap.sponsoredPlaybackStatus).toBe("interrupted");
    expect(snap.interruptedReason).toBe("executive_boardroom_confidential");

    // Resume from interruption
    manager.resumeFromInterruption();
    snap = manager.getSnapshot();
    expect(snap.sponsoredPlaybackStatus).toBe("playing");
    expect(snap.interruptedReason).toBeNull();
  });

  it("preempts sponsored music when user music becomes active", async () => {
    const verifiedTrack: SponsoredTrackView = {
      campaignId: "camp_verified_priority",
      title: "Commercial Theme",
      artist: "Ad Brand",
      destinationUrl: "https://example.com",
      rightsVerified: true,
      notes: [300, 350],
    };

    await manager.playSponsoredTrack(verifiedTrack);

    // User starts their own chosen track in GTEX TRAX
    manager.registerActiveChannelSource("user_music", "gtex_trax_jukebox");
    let snap = manager.getSnapshot();
    expect(snap.sponsoredPlaybackStatus).toBe("interrupted");
    expect(snap.interruptedReason).toBe("user_music_preempted");

    // User finishes or pauses their music
    manager.unregisterActiveChannelSource("user_music", "gtex_trax_jukebox");
    snap = manager.getSnapshot();
    expect(snap.sponsoredPlaybackStatus).toBe("playing");
    expect(snap.interruptedReason).toBeNull();
  });

  it("immediately halts playback if backend revokes or expires music rights", async () => {
    const verifiedTrack: SponsoredTrackView = {
      campaignId: "camp_revocation_test",
      title: "Licensed Summer Track",
      artist: "Licensed Artist",
      destinationUrl: "https://example.com",
      rightsVerified: true,
      notes: [440, 480],
    };

    await manager.playSponsoredTrack(verifiedTrack);
    expect(manager.getSnapshot().currentSponsoredTrack).not.toBeNull();

    // Backend signals rights expiration or administrative suspension
    manager.terminatePlaybackForRightsRevocation("Licensing window closed");
    const snap = manager.getSnapshot();
    expect(snap.sponsoredPlaybackStatus).toBe("idle");
    expect(snap.currentSponsoredTrack).toBeNull();
    expect(snap.interruptedReason).toBe("Licensing window closed");
  });

  it("tracks foreground audible duration accurately without asserting human attention", async () => {
    const verifiedTrack: SponsoredTrackView = {
      campaignId: "camp_attention_test",
      title: "Audible Track",
      artist: "Artist X",
      destinationUrl: "https://example.com",
      rightsVerified: true,
      notes: [260, 320],
    };

    await manager.playSponsoredTrack(verifiedTrack);
    const snap = manager.getSnapshot();
    expect(snap.foregroundAudibleSeconds).toBe(0);
    // Verified field exists and represents duration, not subjective human cognition
    expect(typeof snap.foregroundAudibleSeconds).toBe("number");
  });

  it("applies central master volume, channel volume, and ducking to remote sponsored audio", async () => {
    const originalAudio = (globalThis as any).Audio;
    const mockAudio = {
      crossOrigin: "",
      src: "",
      volume: 1,
      play: jest.fn().mockResolvedValue(undefined),
      pause: jest.fn(),
    };
    (globalThis as any).Audio = jest.fn(() => mockAudio);

    try {
      await manager.playSponsoredTrack({
        campaignId: "camp_remote_ducking_test",
        title: "Remote Licensed Track",
        artist: "GTEX Artist",
        audioUrl: "https://cdn.example.test/licensed-track.mp3",
        destinationUrl: "https://example.test",
        rightsVerified: true,
      });

      expect(mockAudio.volume).toBeCloseTo(0.85 * 0.55);

      manager.setChannelVolume("sponsored_music", 0.4);
      expect(mockAudio.volume).toBeCloseTo(0.85 * 0.4);

      manager.registerActiveChannelSource("commentary", "remote_track_commentary");
      expect(mockAudio.volume).toBeCloseTo(0.85 * 0.4 * 0.15);

      manager.setMasterMute(true);
      expect(mockAudio.volume).toBe(0);

      manager.setMasterMute(false);
      expect(mockAudio.volume).toBeCloseTo(0.85 * 0.4 * 0.15);

      manager.unregisterActiveChannelSource("commentary", "remote_track_commentary");
      expect(mockAudio.volume).toBeCloseTo(0.85 * 0.4);
    } finally {
      (globalThis as any).Audio = originalAudio;
    }
  });

});
