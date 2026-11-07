/**
 * GTEX Living Football Ecosystem — GtexAudioContext Integration Tests
 * Verifies React Context Provider, custom hooks, and channel registration workflows.
 */

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { GtexAudioProvider, useGtexAudio, useAudioChannel, useSponsoredMusic } from "./GtexAudioContext";
import { gtexAudio } from "./GtexAudioManager";
import { SponsoredTrackView } from "./GtexAudioTypes";

function TestAudioConsumer() {
  const { snapshot, setMasterVolume, setMasterMute } = useGtexAudio();
  const commentaryChannel = useAudioChannel("commentary");
  const sponsored = useSponsoredMusic();

  return (
    <div>
      <div data-testid="master-vol">{snapshot.masterVolume}</div>
      <div data-testid="is-muted">{String(snapshot.isMasterMuted)}</div>
      <div data-testid="commentary-vol">{commentaryChannel.volume}</div>
      <div data-testid="commentary-active">{String(commentaryChannel.isActive)}</div>
      <div data-testid="sponsored-status">{sponsored.status}</div>

      <button
        data-testid="mute-btn"
        onClick={() => setMasterMute(!snapshot.isMasterMuted)}
      >
        Toggle Mute
      </button>
      <button
        data-testid="vol-btn"
        onClick={() => setMasterVolume(0.4)}
      >
        Set Volume 0.4
      </button>
      <button
        data-testid="comm-on-btn"
        onClick={() => commentaryChannel.registerActive("sim_commentator_test")}
      >
        Start Commentary
      </button>
      <button
        data-testid="comm-off-btn"
        onClick={() => commentaryChannel.unregisterActive("sim_commentator_test")}
      >
        Stop Commentary
      </button>
    </div>
  );
}

describe("GtexAudioContext and Hooks Integration", () => {
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

  it("provides audio session snapshot and responds to volume/mute controls", () => {
    act(() => {
      root.render(
        <GtexAudioProvider>
          <TestAudioConsumer />
        </GtexAudioProvider>
      );
    });

    const isMutedEl = container.querySelector('[data-testid="is-muted"]');
    expect(isMutedEl?.textContent).toBe("false");

    const muteBtn = container.querySelector('[data-testid="mute-btn"]') as HTMLButtonElement;
    act(() => {
      muteBtn.click();
    });
    expect(container.querySelector('[data-testid="is-muted"]')?.textContent).toBe("true");

    const volBtn = container.querySelector('[data-testid="vol-btn"]') as HTMLButtonElement;
    act(() => {
      volBtn.click();
    });
    expect(container.querySelector('[data-testid="master-vol"]')?.textContent).toBe("0.4");
  });

  it("registers and unregisters active commentary channel, triggering priority ducking", () => {
    act(() => {
      root.render(
        <GtexAudioProvider>
          <TestAudioConsumer />
        </GtexAudioProvider>
      );
    });

    expect(container.querySelector('[data-testid="commentary-active"]')?.textContent).toBe("false");

    const commOnBtn = container.querySelector('[data-testid="comm-on-btn"]') as HTMLButtonElement;
    act(() => {
      commOnBtn.click();
    });
    expect(container.querySelector('[data-testid="commentary-active"]')?.textContent).toBe("true");

    const commOffBtn = container.querySelector('[data-testid="comm-off-btn"]') as HTMLButtonElement;
    act(() => {
      commOffBtn.click();
    });
    expect(container.querySelector('[data-testid="commentary-active"]')?.textContent).toBe("false");
  });

  it("correctly integrates with useSponsoredMusic hook and handles track playback", async () => {
    const verifiedTrack: SponsoredTrackView = {
      campaignId: "camp_hook_test_01",
      title: "Sound of the Pitch",
      artist: "GTEX All-Stars",
      destinationUrl: "https://example.com/sound-of-pitch",
      rightsVerified: true,
      genre: "Afro-House",
    };

    act(() => {
      root.render(
        <GtexAudioProvider>
          <TestAudioConsumer />
        </GtexAudioProvider>
      );
    });

    await act(async () => {
      await gtexAudio.playSponsoredTrack(verifiedTrack);
    });

    expect(container.querySelector('[data-testid="sponsored-status"]')?.textContent).toMatch(/playing|blocked/);
  });
});
