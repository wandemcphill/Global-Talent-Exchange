import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TacticianSuiteScene } from "./TacticianSuiteScene";
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

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn().mockResolvedValue({ data: null }),
    post: jest.fn().mockResolvedValue({ data: null }),
  },
  errMsg: (err: any, fallback: string) => fallback,
}));

describe("TacticianSuiteScene", () => {
  let container: HTMLDivElement;
  let root: Root;
  let queryClient: QueryClient;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    jest.clearAllMocks();
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  test("is registered as the authoritative custom renderer for tactician_suite in GtexSceneRegistry", () => {
    const renderer = GtexSceneRegistry.getRenderer("tactician_suite");
    expect(renderer).toBeDefined();
    expect(renderer).toBe(TacticianSuiteScene);
  });

  test("renders tactician war room scene with formation badge and camera presets", async () => {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <TacticianSuiteScene clubId="c_lagos_tactician" />
        </QueryClientProvider>
      );
    });

    expect(container.querySelector('[data-testid="tactician-3d-scene"]')).not.toBeNull();
    expect(container.textContent).toContain("Manager Tactician War Room");
    expect(container.textContent).toContain("FORMATION 4-3-3");
    expect(container.querySelector('[data-testid="medical-suite-cryo-link"]')?.textContent).toContain(
      "Medical Link: Cryo Active"
    );

    // Switch tactical formation to 4-2-3-1
    const fmtBtn = container.querySelector(
      '[data-testid="formation-select-4-2-3-1"]'
    ) as HTMLButtonElement;
    expect(fmtBtn).not.toBeNull();
    await act(async () => {
      fmtBtn.click();
    });
    expect(container.textContent).toContain("FORMATION 4-2-3-1");

    // Apply formation proposal to Manager via authoritative backend endpoint
    const proposeBtn = container.querySelector(
      '[data-testid="propose-tactical-formation-btn"]'
    ) as HTMLButtonElement;
    expect(proposeBtn).not.toBeNull();
    await act(async () => {
      proposeBtn.click();
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(container.querySelector('[data-testid="tactical-proposal-response-banner"]')).not.toBeNull();

    // Click Snapshot button
    const snapshotBtn = container.querySelector(
      '[data-testid="capture-tactician-snapshot-btn"]'
    ) as HTMLButtonElement;
    expect(snapshotBtn).not.toBeNull();
    await act(async () => {
      snapshotBtn.click();
    });
  });

  test("switches camera presets smoothly", async () => {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <TacticianSuiteScene clubId="c_lagos_tactician" />
        </QueryClientProvider>
      );
    });

    const deskBtn = container.querySelector('[data-testid="camera-preset-desk"]') as HTMLButtonElement;
    expect(deskBtn).not.toBeNull();

    await act(async () => {
      deskBtn.click();
    });
    expect(deskBtn.className).toContain("bg-emerald-500");

    const tunnelBtn = container.querySelector(
      '[data-testid="camera-preset-tunnel_view"]'
    ) as HTMLButtonElement;
    await act(async () => {
      tunnelBtn.click();
    });
    expect(tunnelBtn.className).toContain("bg-emerald-500");
  });

  test("opens dialogue modal when clicking Converse with Manager button", async () => {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <TacticianSuiteScene clubId="c_lagos_tactician" />
        </QueryClientProvider>
      );
    });

    const converseBtn = container.querySelector(
      '[data-testid="open-manager-dialogue-btn"]'
    ) as HTMLButtonElement;
    expect(converseBtn).not.toBeNull();

    await act(async () => {
      converseBtn.click();
    });

    expect(document.querySelector('[data-testid="persona-spatial-modal"]')).not.toBeNull();
  });

  test("unmounts cleanly", async () => {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <TacticianSuiteScene clubId="c_lagos_tactician" />
        </QueryClientProvider>
      );
    });

    expect(container.querySelector('[data-testid="tactician-3d-scene"]')).not.toBeNull();

    act(() => {
      root.unmount();
    });
    expect(container.querySelector('[data-testid="tactician-3d-scene"]')).toBeNull();
  });
});
