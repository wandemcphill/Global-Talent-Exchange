import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import {
  OrthographicPitch,
  PITCH_H,
  PITCH_W,
  clampCameraPan,
  lastRenderProfile,
  pickPlayerAtPoint,
  screenToPitchPoint,
} from "./OrthographicPitch";
import * as matchRenderer from "./createMatchRenderer";
import { PlayerMotionTracker } from "./playerRig";

const mockRender = jest.fn();
const mockDispose = jest.fn();

describe("OrthographicPitch lifecycle, camera transform, selection, and recovery", () => {
  let root: Root;
  let host: HTMLDivElement;

  beforeEach(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    mockDispose.mockClear();
    mockRender.mockClear();
    jest.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(
      () =>
        ({
          clearRect: jest.fn(),
          fillRect: jest.fn(),
          strokeRect: jest.fn(),
          beginPath: jest.fn(),
          moveTo: jest.fn(),
          lineTo: jest.fn(),
          closePath: jest.fn(),
          stroke: jest.fn(),
          fill: jest.fn(),
          save: jest.fn(),
          restore: jest.fn(),
          translate: jest.fn(),
          scale: jest.fn(),
          setLineDash: jest.fn(),
          drawImage: jest.fn(),
          putImageData: jest.fn(),
          createRadialGradient: () => ({ addColorStop: jest.fn() }),
          fillStyle: "",
          strokeStyle: "",
          lineWidth: 1,
        }) as unknown as CanvasRenderingContext2D,
    );
    jest.spyOn(matchRenderer, "createMatchRenderer").mockImplementation(() => ({
      setSize: jest.fn(),
      setPixelRatio: jest.fn(),
      render: mockRender,
      dispose: mockDispose,
      domElement: document.createElement("canvas"),
      info: { render: { calls: 0 } },
    }) as unknown as ReturnType<typeof matchRenderer.createMatchRenderer>);
    host = document.createElement("div");
    document.body.appendChild(host);
    root = createRoot(host);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    jest.restoreAllMocks();
    host.remove();
  });

  test("creates one renderer, renders 22 players even with colliding 1..11 IDs across sides, and disposes cleanly", () => {
    const players = Array.from({ length: 22 }, (_, index) => ({
      playerId: String((index % 11) + 1),
      side: index < 11 ? ("home" as const) : ("away" as const),
      x: ((index % 11) + 0.5) / 11,
      y: index < 11 ? 0.3 : 0.7,
      shirtNumber: (index % 11) + 1,
      name: `P${index}`,
    }));
    act(() => {
      root.render(
        <OrthographicPitch players={players} ball={{ x: 0.5, y: 0.5 }} eventType="pass" />,
      );
    });
    expect(mockRender).toHaveBeenCalled();
    expect(lastRenderProfile.activePlayerSprites).toBe(22);
    expect(lastRenderProfile.rendererMode).toBe("webgl");
    act(() => root.unmount());
    expect(mockDispose).toHaveBeenCalled();
  });

  test("inverse camera transform accurately maps zoomed and panned screen coordinates to pitch world space", () => {
    // Pan in world coordinates (0.2 * PITCH_W, -0.1 * PITCH_H) at zoom=2
    const pan = clampCameraPan(0.2 * PITCH_W, -0.1 * PITCH_H, 2);
    expect(pan.panX).toBeCloseTo(0.2 * PITCH_W);
    expect(pan.panY).toBeCloseTo(-0.1 * PITCH_H);
    expect(pan.zoom).toBe(2);

    // At zoom=2, panX = 0.2 * PITCH_W, panY = -0.1 * PITCH_H, the center of the viewport
    // (clientX=400, clientY=250 in 800x500) maps to pitch x = 0.5 + 0.2 = 0.7, y = 0.5 - (-0.1) = 0.6.
    const point = screenToPitchPoint(
      400,
      250,
      { left: 0, top: 0, width: 800, height: 500 },
      pan,
    );
    expect(point.x).toBeCloseTo(0.7, 4);
    expect(point.y).toBeCloseTo(0.6, 4);

    const homePlayer = {
      playerId: "9",
      side: "home" as const,
      x: 0.71,
      y: 0.59,
      shirtNumber: 9,
      name: "Osimhen",
    };
    const awayPlayer = {
      playerId: "9",
      side: "away" as const,
      x: 0.25,
      y: 0.4,
      shirtNumber: 9,
      name: "Kane",
    };
    const picked = pickPlayerAtPoint([homePlayer, awayPlayer], point, 2);
    expect(picked).toEqual(homePlayer);
  });

  test("selecting a player works after zoom and pan, and dragging pans without selecting a player", () => {
    const onSelect = jest.fn();
    const players = [
      {
        playerId: "10",
        side: "home" as const,
        x: 0.5,
        y: 0.5,
        shirtNumber: 10,
        name: "Playmaker",
      },
      {
        playerId: "10",
        side: "away" as const,
        x: 0.75,
        y: 0.5,
        shirtNumber: 10,
        name: "Rival Ten",
      },
    ];

    act(() => {
      root.render(
        <OrthographicPitch
          players={players}
          ball={{ x: 0.5, y: 0.5 }}
          onSelect={onSelect}
        />,
      );
    });

    const zoomInBtn = host.querySelector('[data-testid="pitch-control-zoom-in"]') as HTMLButtonElement;
    expect(zoomInBtn).not.toBeNull();
    act(() => {
      zoomInBtn.click();
    });

    const stage = host.querySelector('[data-testid="orthographic-pitch-mount"]') as HTMLDivElement;
    expect(stage).not.toBeNull();
    const canvas = stage.querySelector("canvas") as HTMLCanvasElement;
    const mockRect = () =>
      ({
        left: 0,
        top: 0,
        width: 1000,
        height: 600,
        right: 1000,
        bottom: 600,
        x: 0,
        y: 0,
        toJSON: () => ({}),
      }) as DOMRect;
    stage.getBoundingClientRect = mockRect;
    if (canvas) {
      canvas.getBoundingClientRect = mockRect;
    }

    // Simulate a drag gesture: should pan the camera and NOT select the player at (500, 300)
    act(() => {
      stage.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true, clientX: 500, clientY: 300, button: 0 }));
      window.dispatchEvent(new MouseEvent("pointermove", { bubbles: true, clientX: 250, clientY: 300, button: 0 }));
      window.dispatchEvent(new MouseEvent("pointerup", { bubbles: true, clientX: 250, clientY: 300, button: 0 }));
    });
    expect(onSelect).not.toHaveBeenCalled();

    // Reset via Fit button, then click directly on away #10 at x=0.75, y=0.5 -> clientX=750, clientY=300
    const fitBtn = host.querySelector('[data-testid="pitch-control-fit"]') as HTMLButtonElement;
    act(() => {
      fitBtn.click();
    });

    act(() => {
      stage.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true, clientX: 750, clientY: 300, button: 0 }));
      window.dispatchEvent(new MouseEvent("pointerup", { bubbles: true, clientX: 750, clientY: 300, button: 0 }));
    });
    expect(onSelect).toHaveBeenCalledWith("away:10");
  });

  test("PlayerMotionTracker preserves velocity and gait across higher-frequency render frames without flickering to idle", () => {
    const tracker = new PlayerMotionTracker();
    // Sample 1 at t=1000ms
    tracker.update("home:7", 0.2, 0.5, 1000, { baseAction: "idle", hasBall: false, side: "home" });
    // Sample 2 at t=1250ms (initial burst from standstill -> accelerate)
    const burst = tracker.update("home:7", 0.26, 0.5, 1250, { baseAction: "idle", hasBall: false, side: "home" });
    expect(burst.speed).toBeGreaterThan(0.02);
    expect(burst.action).toBe("accelerate");

    // Sample 3 at t=1500ms (continued high speed -> sprint)
    const moved = tracker.update("home:7", 0.32, 0.5, 1500, { baseAction: "idle", hasBall: false, side: "home" });
    expect(moved.speed).toBeGreaterThan(0.02);
    expect(moved.action).toBe("sprint");

    // Intermediate 60fps animation frames (t=1516ms, 1533ms, 1550ms) where network coordinates have not yet updated
    const f1 = tracker.update("home:7", 0.32, 0.5, 1516, { baseAction: "idle", hasBall: false, side: "home" });
    const f2 = tracker.update("home:7", 0.32, 0.5, 1533, { baseAction: "idle", hasBall: false, side: "home" });
    const f3 = tracker.update("home:7", 0.32, 0.5, 1550, { baseAction: "idle", hasBall: false, side: "home" });

    expect(f1.speed).toBeGreaterThan(0.02);
    expect(f2.speed).toBeGreaterThan(0.02);
    expect(f3.speed).toBeGreaterThan(0.02);
    expect(f3.action).toBe("sprint");
  });

  test("handles WebGL context loss by switching to Canvas fallback and recovers on webglcontextrestored", () => {
    const createdCanvases: HTMLCanvasElement[] = [];
    jest.spyOn(matchRenderer, "createMatchRenderer").mockImplementation(() => {
      const canvas = document.createElement("canvas");
      createdCanvases.push(canvas);
      return {
        setSize: jest.fn(),
        setPixelRatio: jest.fn(),
        render: mockRender,
        dispose: mockDispose,
        domElement: canvas,
        info: { render: { calls: 0 } },
      } as unknown as ReturnType<typeof matchRenderer.createMatchRenderer>;
    });

    const players = [
      { playerId: "1", side: "home" as const, x: 0.1, y: 0.5, shirtNumber: 1, name: "GK" },
      { playerId: "9", side: "away" as const, x: 0.8, y: 0.5, shirtNumber: 9, name: "ST" },
    ];

    act(() => {
      root.render(<OrthographicPitch players={players} ball={{ x: 0.5, y: 0.5 }} />);
    });

    expect(createdCanvases.length).toBe(1);
    expect(lastRenderProfile.rendererMode).toBe("webgl");

    // Dispatch webglcontextlost on the active WebGL canvas
    act(() => {
      const lostEvent = new Event("webglcontextlost", { cancelable: true });
      createdCanvases[0].dispatchEvent(lostEvent);
    });

    expect(lastRenderProfile.rendererMode).toBe("canvas-fallback");
    const mount = host.querySelector('[data-testid="orthographic-pitch-mount"]') as HTMLDivElement;
    // Only one visible canvas should be mounted in the pitch container
    expect(mount.querySelectorAll("canvas").length).toBe(1);

    // Dispatch webglcontextrestored on the original WebGL canvas to trigger recovery
    act(() => {
      const restoredEvent = new Event("webglcontextrestored");
      createdCanvases[0].dispatchEvent(restoredEvent);
    });

    expect(lastRenderProfile.rendererMode).toBe("webgl");
    expect(lastRenderProfile.contextRecoveryEvents).toBeGreaterThanOrEqual(1);
    expect(mount.querySelectorAll("canvas").length).toBe(1);
  });

  test("falls back cleanly to Canvas 2D when WebGL initialization throws", () => {
    jest.spyOn(matchRenderer, "createMatchRenderer").mockImplementation(() => {
      throw new Error("WebGL disabled");
    });

    const players = [
      { playerId: "1", side: "home" as const, x: 0.1, y: 0.5, shirtNumber: 1, name: "GK" },
      { playerId: "9", side: "away" as const, x: 0.8, y: 0.5, shirtNumber: 9, name: "ST" },
    ];

    act(() => {
      root.render(
        <OrthographicPitch
          players={players}
          ball={{ x: 0.5, y: 0.5 }}
          showVoronoi
          showHeatmap
          showTactics
          showPassingLanes
        />,
      );
    });

    expect(lastRenderProfile.rendererMode).toBe("canvas-fallback");
    expect(lastRenderProfile.activePlayerSprites).toBe(2);
    const mount = host.querySelector('[data-testid="orthographic-pitch-mount"]') as HTMLDivElement;
    expect(mount.querySelectorAll("canvas").length).toBe(1);
  });

  test("repeated mount/unmount cycles do not leak active renderers or orphan canvases", () => {
    act(() => {
      root.unmount();
    });
    const players = [
      { playerId: "1", side: "home" as const, x: 0.2, y: 0.5, shirtNumber: 1, name: "GK" },
    ];
    for (let i = 0; i < 4; i += 1) {
      const cycleHost = document.createElement("div");
      document.body.appendChild(cycleHost);
      const cycleRoot = createRoot(cycleHost);
      act(() => {
        cycleRoot.render(<OrthographicPitch players={players} ball={{ x: 0.5, y: 0.5 }} />);
      });
      act(() => {
        cycleRoot.unmount();
      });
      expect(cycleHost.querySelectorAll("canvas").length).toBe(0);
      cycleHost.remove();
    }
    expect(lastRenderProfile.activeRenderers).toBe(0);
  });

  test("does not import pixi and exports a memoized pitch", () => {
    const source = require("fs").readFileSync(require("path").join(__dirname, "OrthographicPitch.tsx"), "utf8");
    expect(source).not.toMatch(/pixi/i);
    expect(source).toContain("memo(OrthographicPitchComponent)");
    expect(source).toContain("webglcontextrestored");
  });
});
