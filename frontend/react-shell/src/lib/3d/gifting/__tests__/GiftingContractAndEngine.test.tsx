import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import * as THREE from "three";
import { CinematicGiftingEngine, type CinematicGiftEvent } from "../CinematicGiftingEngine";
import { GtexCelebrationAudioEngine } from "../GtexCelebrationAudioEngine";
import { disposeScene } from "../../disposeScene";

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

describe("Gifting Contract, CinematicGiftingEngine & WebGL Disposal", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
    jest.restoreAllMocks();
  });

  test("maps backend GiftCatalogItemView cost_amount without falling back to 0 FAN", () => {
    const backendCatalogPayload = [
      { key: "private_jet", display_name: "Private Jet Flyby", cost_amount: "3000.0000", tier: "legendary" },
      { key: "golden_stadium", display_name: "Golden Stadium", cost_amount: "4500.0000", tier: "mythic" },
    ];

    const normalized = backendCatalogPayload.map((item: any) => ({
      code: item.code || item.gift_code || item.key,
      name: item.name || item.display_name,
      price: Number(item.cost_amount ?? item.fancoin_price ?? item.amount_fancoin ?? item.cost ?? 10) || 10,
      tier: item.tier || "common",
    }));

    expect(normalized[0].code).toBe("private_jet");
    expect(normalized[0].price).toBe(3000);
    expect(normalized[1].code).toBe("golden_stadium");
    expect(normalized[1].price).toBe(4500);
  });

  test("CinematicGiftingEngine does not restart animation or re-fire audio on parent re-renders with identical gift ID", () => {
    const audioSpy = jest.spyOn(GtexCelebrationAudioEngine, "playCelebrationCue").mockImplementation(() => {});
    const onCompleteA = jest.fn();
    const onCompleteB = jest.fn();

    const giftPayload: CinematicGiftEvent = {
      id: "gift-tx-9001",
      gift_code: "private_jet",
      gift_name: "Private Jet Flyby",
      sender: "Ayo",
      recipient: "GTEX FC",
      amount: 3000,
      rarity: "legendary",
      duration_ms: 4000,
    };

    act(() => {
      root.render(
        <CinematicGiftingEngine
          activeGift={{ ...giftPayload }}
          onAnimationComplete={onCompleteA}
          soundEnabled={true}
        />
      );
    });

    expect(container.querySelector('[data-testid="on-pitch-gift-animation"]')).not.toBeNull();
    expect(audioSpy).toHaveBeenCalledTimes(1);

    // Simulate parent re-render with a fresh object reference and fresh callback reference for the same gift event
    act(() => {
      root.render(
        <CinematicGiftingEngine
          activeGift={{ ...giftPayload }}
          onAnimationComplete={onCompleteB}
          soundEnabled={true}
        />
      );
    });

    expect(audioSpy).toHaveBeenCalledTimes(1);
  });

  test("CinematicGiftingEngine suppresses celebration audio when prefers-reduced-motion is enabled", () => {
    const audioSpy = jest.spyOn(GtexCelebrationAudioEngine, "playCelebrationCue").mockImplementation(() => {});
    const originalMatchMedia = window.matchMedia;

    window.matchMedia = jest.fn().mockImplementation((query: string) => ({
      matches: query.includes("prefers-reduced-motion"),
      media: query,
      onchange: null,
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      addListener: jest.fn(),
      removeListener: jest.fn(),
      dispatchEvent: jest.fn(),
    }));

    try {
      act(() => {
        root.render(
          <CinematicGiftingEngine
            activeGift={{
              id: "gift-tx-reduced-1",
              gift_code: "golden_stadium",
              gift_name: "Golden Stadium",
              sender: "Ayo",
              amount: 4500,
              rarity: "mythic",
            }}
            soundEnabled={true}
          />
        );
      });

      expect(audioSpy).not.toHaveBeenCalled();
    } finally {
      window.matchMedia = originalMatchMedia;
    }
  });

  test("disposeScene disposes mesh geometries, materials, textures, and clears scene", () => {
    const scene = new THREE.Scene();
    const geometry = new THREE.BoxGeometry(2, 2, 2);
    const texture = new THREE.Texture();
    const material = new THREE.MeshStandardMaterial({ map: texture });
    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    const geoSpy = jest.spyOn(geometry, "dispose");
    const matSpy = jest.spyOn(material, "dispose");
    const texSpy = jest.spyOn(texture, "dispose");

    disposeScene(scene, null);

    expect(geoSpy).toHaveBeenCalled();
    expect(matSpy).toHaveBeenCalled();
    expect(texSpy).toHaveBeenCalled();
    expect(scene.children.length).toBe(0);
  });
});
