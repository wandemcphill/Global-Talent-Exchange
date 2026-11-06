import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { MatchPitchLiveScene } from "./MatchPitchLiveScene";

jest.mock("three", () => {
  const actualThree = jest.requireActual("three");
  function MockWebGLRenderer(this: any) {
    const mockCanvas = globalThis.document.createElement("canvas");
    mockCanvas.setAttribute("data-testid", "mock-three-canvas");
    this.domElement = mockCanvas;
    this.setSize = jest.fn();
    this.setPixelRatio = jest.fn();
    this.shadowMap = { enabled: false, type: 0, autoUpdate: false, needsUpdate: false };
    this.getContext = jest.fn().mockReturnValue({
      getExtension: jest.fn().mockReturnValue(null),
      getParameter: jest.fn().mockReturnValue("Mock WebGL GPU"),
    });
    this.render = jest.fn();
    this.dispose = jest.fn();
    this.info = {
      render: { calls: 0, triangles: 0 },
      memory: { geometries: 0, textures: 0 },
    };
    this.getPixelRatio = jest.fn().mockReturnValue(1);
  }
  return {
    ...actualThree,
    WebGLRenderer: MockWebGLRenderer,
  };
});

describe("MatchPitchLiveScene", () => {
  let container: HTMLDivElement;
  let root: Root;
  let originalGetContext: any;

  const mockViewState = {
    match_id: "match-test-101",
    canonical_match_id: "canon-comp-101",
    home_team: {
      team_id: "h1",
      team_name: "Apex Lagos",
      short_name: "APX",
      formation: "4-3-3",
      primary_color: "#00E676",
      secondary_color: "#F5B83D",
      accent_color: "#FFFFFF",
      goalkeeper_color: "#FFB800",
    },
    away_team: {
      team_id: "a1",
      team_name: "Nairobi Stars",
      short_name: "NST",
      formation: "4-4-2",
      primary_color: "#3B82F6",
      secondary_color: "#1E40AF",
      accent_color: "#FFFFFF",
      goalkeeper_color: "#EC4899",
    },
    presentation_package: {
      match_label: "Apex Lagos vs Nairobi Stars",
    },
    frames: [
      {
        frame_id: "f1",
        time_seconds: 10.0,
        clock_minute: 1,
        phase: "open_play",
        home_score: 1,
        away_score: 0,
        home_attacks_right: true,
        possession_side: "home",
        camera_preset: "broadcast",
        event_banner: "GOAL! High Press Turnaround",
        players: [
          {
            player_id: "p1",
            team_id: "h1",
            side: "home",
            shirt_number: 9,
            label: "Osimhen",
            role: "ST",
            position: { x: 55, y: 50 },
            animation_state: "celebrate",
            speed_ratio: 0.8,
            has_possession: true,
          },
        ],
        ball: {
          position: { x: 55, y: 50 },
          height: 0.5,
          state: "rolling",
        },
      },
    ],
    events: [],
  };

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    originalGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = jest.fn().mockImplementation((contextId: string) => {
      if (contextId === "webgl" || contextId === "experimental-webgl") {
        return {
          getExtension: jest.fn(),
          getParameter: jest.fn(),
        };
      }
      return null;
    }) as any;
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
    HTMLCanvasElement.prototype.getContext = originalGetContext;
  });

  test("renders 3D match scene container and broadcast overlay HUD", async () => {
    await act(async () => {
      root.render(
        <MatchPitchLiveScene
          matchViewState={mockViewState}
          qualityTier="high"
          testId="test-pitch-scene"
        />
      );
    });

    const sceneEl = container.querySelector("[data-testid='test-pitch-scene']");
    const hudEl = container.querySelector("[data-testid='broadcast-overlay-hud']");

    expect(sceneEl).not.toBeNull();
    expect(hudEl).not.toBeNull();
    expect(container.textContent).toContain("APX");
    expect(container.textContent).toContain("NST");
  });

  test("handles 2D companion mode switch and return", async () => {
    await act(async () => {
      root.render(
        <MatchPitchLiveScene
          matchViewState={mockViewState}
          qualityTier="low"
          testId="test-pitch-scene"
        />
      );
    });

    const toggleBtn = container.querySelector("[data-testid='toggle-2d-companion-button']") as HTMLButtonElement;
    expect(toggleBtn).not.toBeNull();

    await act(async () => {
      toggleBtn.click();
    });

    // Fallback companion mode active
    expect(container.textContent).toContain("2D TACTICAL COMPANION MODE");

    // Return button
    const returnBtn = container.querySelector("[data-testid='return-to-3d-broadcast-button']") as HTMLButtonElement;
    expect(returnBtn).not.toBeNull();

    await act(async () => {
      returnBtn.click();
    });

    // Reconnected 3D
    expect(container.querySelector("[data-testid='test-pitch-scene']")).not.toBeNull();
    expect(container.textContent).not.toContain("2D TACTICAL COMPANION MODE");
  });

  test("reconnects canvas across repeated 3D -> 2D -> 3D transitions", async () => {
    await act(async () => {
      root.render(
        <MatchPitchLiveScene
          matchViewState={mockViewState}
          qualityTier="low"
          testId="test-pitch-scene"
        />
      );
    });

    const toggleBtn1 = container.querySelector("[data-testid='toggle-2d-companion-button']") as HTMLButtonElement;
    expect(toggleBtn1).not.toBeNull();
    expect(container.querySelector("canvas")).not.toBeNull();

    // Transition 1: 3D -> 2D
    await act(async () => {
      toggleBtn1.click();
    });
    expect(container.textContent).toContain("2D TACTICAL COMPANION MODE");

    // Transition 1 return: 2D -> 3D
    const returnBtn1 = container.querySelector("[data-testid='return-to-3d-broadcast-button']") as HTMLButtonElement;
    expect(returnBtn1).not.toBeNull();
    await act(async () => {
      returnBtn1.click();
    });

    // Reconnected 3D
    expect(container.querySelector("[data-testid='test-pitch-scene']")).not.toBeNull();
    expect(container.querySelector("canvas")).not.toBeNull();
    const toggleBtn2 = container.querySelector("[data-testid='toggle-2d-companion-button']") as HTMLButtonElement;
    expect(toggleBtn2).not.toBeNull();

    // Transition 2: 3D -> 2D
    await act(async () => {
      toggleBtn2.click();
    });
    expect(container.textContent).toContain("2D TACTICAL COMPANION MODE");

    // Transition 2 return: 2D -> 3D
    const returnBtn2 = container.querySelector("[data-testid='return-to-3d-broadcast-button']") as HTMLButtonElement;
    expect(returnBtn2).not.toBeNull();
    await act(async () => {
      returnBtn2.click();
    });

    // Reconnected 3D again
    expect(container.querySelector("[data-testid='test-pitch-scene']")).not.toBeNull();
    expect(container.querySelector("canvas")).not.toBeNull();
    expect(container.querySelector("[data-testid='toggle-2d-companion-button']")).not.toBeNull();
    expect(container.textContent).not.toContain("2D TACTICAL COMPANION MODE");
  });
});
