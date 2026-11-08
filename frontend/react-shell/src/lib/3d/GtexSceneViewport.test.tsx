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

  test("invokes registered non-matchday custom renderer without requiring matchViewState", async () => {
    const NonMatchdayRenderer: React.FC<any> = (props) => (
      <div data-testid="custom-campus-3d">
        <span>Campus Custom 3D View</span>
        <span data-testid="scene-id">{props.sceneId}</span>
        <span data-testid="quality-tier">{props.qualityTier}</span>
        <span data-testid="target-fps">{props.activeQuality?.targetFps}</span>
      </div>
    );

    GtexSceneRegistry.registerRenderer("campus_builder", NonMatchdayRenderer);

    await act(async () => {
      root.render(
        <GtexSceneViewport
          sceneId="campus_builder"
          forceWebGL={true}
          qualityTier="high"
        />
      );
    });

    const rendered = container.querySelector('[data-testid="custom-campus-3d"]');
    expect(rendered).not.toBeNull();
    expect(container.querySelector('[data-testid="scene-id"]')?.textContent).toBe("campus_builder");
    expect(container.querySelector('[data-testid="quality-tier"]')?.textContent).toBe("high");
    expect(container.querySelector('[data-testid="target-fps"]')?.textContent).toBe("60");
  });

  test("passes scene-specific sceneProps to registered custom renderer", async () => {
    const CustomBoardroomRenderer: React.FC<any> = (props) => (
      <div data-testid="boardroom-3d">
        <span data-testid="room-id">{props.sceneProps?.meetingRoomId}</span>
        <span data-testid="agenda-topic">{props.sceneProps?.agendaTopic}</span>
      </div>
    );

    GtexSceneRegistry.registerRenderer("boardroom_custom_test", CustomBoardroomRenderer);

    await act(async () => {
      root.render(
        <GtexSceneViewport
          sceneId="boardroom_custom_test"
          forceWebGL={true}
          sceneProps={{ meetingRoomId: "exec-suite-1", agendaTopic: "Tactical Review" }}
        />
      );
    });

    expect(container.querySelector('[data-testid="room-id"]')?.textContent).toBe("exec-suite-1");
    expect(container.querySelector('[data-testid="agenda-topic"]')?.textContent).toBe("Tactical Review");
  });

  test("preserves matchday renderer adapter and passes matchViewState when present", async () => {
    const MockMatchdayRenderer: React.FC<any> = (props) => (
      <div data-testid="matchday-broadcast-3d">
        <span>Match Broadcast Running</span>
        <span data-testid="match-id">{props.matchViewState?.matchId}</span>
        <span data-testid="broadcast-tier">{props.qualityTier}</span>
      </div>
    );

    GtexSceneRegistry.registerRenderer("stadium_match_broadcast", MockMatchdayRenderer);

    const mockViewState: any = { matchId: "match-world-99", homeClubName: "Lagos City" };

    await act(async () => {
      root.render(
        <GtexSceneViewport
          sceneId="stadium_match_broadcast"
          forceWebGL={true}
          qualityTier="ultra"
          matchViewState={mockViewState}
        />
      );
    });

    expect(container.querySelector('[data-testid="matchday-broadcast-3d"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="match-id"]')?.textContent).toBe("match-world-99");
    expect(container.querySelector('[data-testid="broadcast-tier"]')?.textContent).toBe("ultra");
  });

  test("renders honest fallback for threejs scene when no renderer is registered", async () => {
    // academy_training_pitch is registered as renderBackend: "threejs" with no CustomRenderer registered
    await act(async () => {
      root.render(
        <GtexSceneViewport
          sceneId="academy_training_pitch"
          forceWebGL={true}
        />
      );
    });

    // Should NOT silently render stadium_sponsor; should render honest fallback
    expect(container.textContent).toContain("Academy Youth Training Ground");
    expect(container.textContent).toContain("3D COMPANION MODE (RENDERER PENDING)");
    expect(container.textContent).toContain("Operating in companion mode");
  });

  test("renders dedicated Three.js renderer for boardroom_meeting when registered in Stage 2", async () => {
    const MockBoardroomRenderer: React.FC<any> = () => (
      <div data-testid="boardroom-3d-scene">Boardroom Suite</div>
    );
    GtexSceneRegistry.registerRenderer("boardroom_meeting", MockBoardroomRenderer);

    await act(async () => {
      root.render(
        <GtexSceneViewport
          sceneId="boardroom_meeting"
          forceWebGL={true}
        />
      );
    });

    // Verify it renders the registered BoardroomScene custom renderer
    expect(container.querySelector('[data-testid="boardroom-3d-scene"]')).not.toBeNull();
  });

  test("populates measured telemetry attributes and invokes onQualityTelemetryUpdate", async () => {
    let telemetryCaptured: any = null;

    await act(async () => {
      root.render(
        <GtexSceneViewport
          sceneId="stadium_sponsor"
          forceWebGL={true}
          qualityTier="high"
          onQualityTelemetryUpdate={(t) => {
            telemetryCaptured = t;
          }}
        />
      );
    });

    const viewportEl = container.querySelector('[data-testid="gtex-scene-viewport"]');
    expect(viewportEl).not.toBeNull();
    expect(viewportEl?.hasAttribute("data-measured-fps")).toBe(true);
    expect(viewportEl?.hasAttribute("data-frame-time-ms")).toBe(true);
    expect(viewportEl?.getAttribute("data-context-lost")).toBe("false");
  });
});
