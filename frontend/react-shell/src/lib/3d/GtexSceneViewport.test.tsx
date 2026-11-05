/**
 * Automated Test Suite: GtexSceneViewport
 * Validates viewport rendering, 2D fallback mode, quality profiling attributes, and user interaction.
 * Uses native React 19 createRoot + act pattern consistent with react-shell test suite.
 */

declare const describe: any;
declare const test: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { GtexSceneViewport } from "./GtexSceneViewport";
import { GtexSceneRegistry } from "./GtexSceneRegistry";

describe("GtexSceneViewport", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    GtexSceneRegistry.resetToDefaults();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  test("renders conventional 2D fallback when forceFallback2D is true", async () => {
    const handleAction = jest.fn();

    await act(async () => {
      root.render(
        <GtexSceneViewport
          sceneId="luxury_turntable"
          forceFallback2D={true}
          title="GTEX Sovereign 900X Private Jet"
          subtitle="Intercontinental executive flagship"
          badgeText="PRESTIGE SHOWROOM"
          clubName="Eko Atlantic FC"
          subjectName="Sovereign 900X"
          subjectRole="Executive Fleet"
          overallRating={92}
          stats={[
            { label: "Range", value: "7,500 nm", accent: "#34d399" },
            { label: "Speed", value: "Mach 0.90", accent: "#f59e0b" },
          ]}
          quote="The premier mobile headquarters for global football executives."
          actionLabel="Inspect Specifications"
          onActionClick={handleAction}
        />
      );
    });

    const fallbackEl = container.querySelector('[data-testid="gtex-scene-viewport-fallback-2d"]');
    expect(fallbackEl).not.toBeNull();
    expect(container.textContent).toContain("2D COMPANION MODE");
    expect(container.textContent).toContain("PRESTIGE SHOWROOM");
    expect(container.textContent).toContain("GTEX Sovereign 900X Private Jet");
    expect(container.textContent).toContain("Eko Atlantic FC");
    expect(container.textContent).toContain("7,500 nm");
    expect(container.textContent).toContain("Mach 0.90");

    // Click action button
    const actionBtn = container.querySelector("button");
    expect(actionBtn).not.toBeNull();
    expect(actionBtn?.textContent).toContain("Inspect Specifications");

    await act(async () => {
      actionBtn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    expect(handleAction).toHaveBeenCalledTimes(1);
  });

  test("applies quality tier attributes on container element in WebGL mode", async () => {
    await act(async () => {
      root.render(
        <GtexSceneViewport
          sceneId="stadium_match_broadcast"
          forceWebGL={true}
          qualityTier="ultra"
          title="Marquee Match Broadcast"
        >
          <div data-testid="mock-webgl-canvas">3D Pitch Content</div>
        </GtexSceneViewport>
      );
    });

    const viewportEl = container.querySelector('[data-testid="gtex-scene-viewport"]');
    expect(viewportEl).not.toBeNull();
    expect(viewportEl?.getAttribute("data-quality-tier")).toBe("ultra");
    expect(viewportEl?.getAttribute("data-target-fps")).toBe("60");
    expect(viewportEl?.getAttribute("data-pixel-ratio")).toBe("2");
    expect(container.textContent).toContain("3D Pitch Content");
  });

  test("delegates to registered scene title and description when props are omitted", async () => {
    await act(async () => {
      root.render(
        <GtexSceneViewport
          sceneId="stadium_sponsor"
          forceFallback2D={true}
        />
      );
    });

    expect(container.textContent).toContain("Stadium Sponsorship & Naming Rights");
    expect(container.textContent).toContain("Immersive stadium floodlight overview");
  });
});
