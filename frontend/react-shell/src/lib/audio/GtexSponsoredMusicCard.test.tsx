/**
 * GTEX Living Football Ecosystem — GtexSponsoredMusicCard Unit Tests
 */

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { GtexSponsoredMusicCard } from "./GtexSponsoredMusicCard";
import { gtexAudio } from "./GtexAudioManager";
import { SponsoredTrackView } from "./GtexAudioTypes";

describe("GtexSponsoredMusicCard", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    (global as any).fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
    gtexAudio.stopSponsoredMusic(false);
  });

  it("renders null when there is no active sponsored track", () => {
    act(() => {
      root.render(<GtexSponsoredMusicCard />);
    });
    expect(container.querySelector('[data-testid="gtex-sponsored-music-card"]')).toBeNull();
  });

  it("renders active sponsored track card with artist and destination link", async () => {
    const track: SponsoredTrackView = {
      campaignId: "camp-test-1",
      title: "Champions Anthem",
      artist: "Super Eagles Sound",
      destinationUrl: "https://music.apple.com/test",
      rightsVerified: true,
      genre: "Afrobeats",
    };

    await act(async () => {
      await gtexAudio.playSponsoredTrack(track);
    });

    act(() => {
      root.render(<GtexSponsoredMusicCard />);
    });

    const card = container.querySelector('[data-testid="gtex-sponsored-music-card"]');
    expect(card).not.toBeNull();
    expect(container.textContent).toContain("Champions Anthem");
    expect(container.textContent).toContain("Super Eagles Sound");

    const link = container.querySelector('[data-testid="music-destination-link"]');
    expect(link).not.toBeNull();
    expect(link?.getAttribute("href")).toBe("https://music.apple.com/test");
  });

  it("does not offer play, pause, or mute", async () => {
    const track: SponsoredTrackView = {
      campaignId: "camp-test-2",
      title: "Victory Dub",
      artist: "Nova Vane",
      destinationUrl: "https://open.spotify.com",
      rightsVerified: true,
    };

    await act(async () => {
      await gtexAudio.playSponsoredTrack(track);
    });

    act(() => {
      root.render(<GtexSponsoredMusicCard />);
    });

    expect(container.querySelector('[data-testid="music-mute-toggle"]')).toBeNull();
    expect(container.querySelector('[data-testid="music-play-pause-btn"]')).toBeNull();
    expect(container.querySelector('[data-testid="unlock-autoplay-btn"]')).toBeNull();
    expect(gtexAudio.getSnapshot().sponsoredPlaybackStatus).not.toBe("paused");
  });

  it("handles track skipping and dismiss callbacks", async () => {
    const track: SponsoredTrackView = {
      campaignId: "camp-test-skip",
      title: "Fast Break Anthem",
      artist: "Aether & Gold",
      destinationUrl: "https://example.com/fast-break",
      rightsVerified: true,
    };

    const handleDismiss = jest.fn();

    await act(async () => {
      await gtexAudio.playSponsoredTrack(track);
    });

    act(() => {
      root.render(<GtexSponsoredMusicCard onDismiss={handleDismiss} />);
    });

    const skipBtn = container.querySelector('[data-testid="music-skip-btn"]') as HTMLButtonElement;
    expect(skipBtn).not.toBeNull();

    act(() => {
      skipBtn.click();
    });
    expect(gtexAudio.getSnapshot().sponsoredPlaybackStatus).toBe("idle");
  });

  it("renders autoplay blocked UI and unlocks on user action", async () => {
    const track: SponsoredTrackView = {
      campaignId: "camp-test-blocked",
      title: "Night Kickoff",
      artist: "Metro DJ",
      destinationUrl: "https://example.com/metro",
      rightsVerified: true,
    };

    await act(async () => {
      await gtexAudio.playSponsoredTrack(track);
    });

    // Simulate browser autoplay block status in snapshot
    (gtexAudio as any).isAutoplayBlocked = true;
    (gtexAudio as any).sponsoredStatus = "blocked";
    (gtexAudio as any).notifySubscribers();

    act(() => {
      root.render(<GtexSponsoredMusicCard />);
    });

    const blockedCard = container.querySelector('[data-testid="gtex-sponsored-music-blocked"]');
    expect(blockedCard).not.toBeNull();
    expect(container.textContent).toContain("Night Kickoff");
    expect(container.textContent).toContain("starts with your next tap");
    expect(container.querySelector('[data-testid="unlock-autoplay-btn"]')).toBeNull();
    expect(container.textContent).not.toContain("Tap to Listen");
  });
});
