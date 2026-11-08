import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { PrestigeShowroomScene } from "./PrestigeShowroomScene";
import { GtexSceneRegistry } from "../GtexSceneRegistry";

jest.mock("three/examples/jsm/controls/OrbitControls.js", () => {
  return {
    OrbitControls: class {
      enableDamping = true;
      dampingFactor = 0.05;
      maxPolarAngle = 1;
      minDistance = 1;
      maxDistance = 100;
      target = {
        x: 0,
        y: 0,
        z: 0,
        set: jest.fn(),
        copy: jest.fn(),
        lerp: jest.fn(),
        distanceTo: jest.fn().mockReturnValue(0),
      };
      update = jest.fn();
      dispose = jest.fn();
      addEventListener = jest.fn();
      removeEventListener = jest.fn();
    },
  };
});

describe("PrestigeShowroomScene", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    jest.clearAllMocks();
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  test("is registered as the authoritative custom renderer for luxury_inspection_turntable in GtexSceneRegistry", () => {
    const renderer = GtexSceneRegistry.getRenderer("luxury_inspection_turntable");
    expect(renderer).toBeDefined();
    expect(renderer).toBe(PrestigeShowroomScene);
  });

  test("renders 3D showroom scene with verified ownership badge and honest render mode badge", async () => {
    await act(async () => {
      root.render(
        <PrestigeShowroomScene
          assetName="Sovereign Gulfstream G700"
          assetCategory="jet"
          modelName="Gulfstream G700 Executive"
          priceGtex={850000}
          isOwned={true}
          clubName="Lagos Atlantic FC"
        />
      );
    });

    expect(container.querySelector('[data-testid="prestige-showroom-3d-scene"]')).not.toBeNull();
    expect(container.textContent).toContain("Sovereign Gulfstream G700");
    expect(container.textContent).toContain("850,000 GTEX");
    expect(container.querySelector('[data-testid="showroom-ownership-badge"]')?.textContent).toContain(
      "Verified Owned"
    );
    expect(container.querySelector('[data-testid="showroom-perk-active-badge"]')?.textContent).toContain(
      "Perk Yield Active"
    );
    expect(container.querySelector('[data-testid="showroom-render-mode-badge"]')).not.toBeNull();

    const snapshotBtn = container.querySelector(
      '[data-testid="capture-showroom-snapshot-btn"]'
    ) as HTMLButtonElement;
    expect(snapshotBtn).not.toBeNull();
    await act(async () => {
      snapshotBtn.click();
    });
  });

  test("allows switching camera presets, livery finishes, and turntable rotation", async () => {
    await act(async () => {
      root.render(
        <PrestigeShowroomScene
          assetName="GTEX Sovereign Hypercar"
          assetCategory="vehicle"
          modelName="V12 Carbon Edition"
          priceGtex={420000}
          isOwned={false}
        />
      );
    });

    const profileBtn = container.querySelector(
      '[data-testid="showroom-camera-profile_side"]'
    ) as HTMLButtonElement;
    expect(profileBtn).not.toBeNull();
    await act(async () => {
      profileBtn.click();
    });
    expect(profileBtn.className).toContain("bg-amber-400");

    const carbonLiveryBtn = container.querySelector(
      '[data-testid="showroom-livery-stealth_carbon"]'
    ) as HTMLButtonElement;
    expect(carbonLiveryBtn).not.toBeNull();
    await act(async () => {
      carbonLiveryBtn.click();
    });
    expect(carbonLiveryBtn.className).toContain("border-amber-400");

    const spinToggleBtn = container.querySelector(
      '[data-testid="toggle-turntable-rotation-btn"]'
    ) as HTMLButtonElement;
    expect(spinToggleBtn.textContent).toContain("Pause Spin");
    await act(async () => {
      spinToggleBtn.click();
    });
    expect(spinToggleBtn.textContent).toContain("Auto Spin");
  });

  test("unmounts cleanly without errors", async () => {
    await act(async () => {
      root.render(
        <PrestigeShowroomScene
          assetName="Continental Team Coach"
          assetCategory="coach"
          isOwned={true}
        />
      );
    });

    expect(container.querySelector('[data-testid="prestige-showroom-3d-scene"]')).not.toBeNull();
    act(() => {
      root.unmount();
    });
    expect(container.querySelector('[data-testid="prestige-showroom-3d-scene"]')).toBeNull();
  });
});
