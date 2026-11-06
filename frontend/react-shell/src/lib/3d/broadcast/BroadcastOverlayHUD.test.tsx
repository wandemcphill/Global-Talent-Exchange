import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { BroadcastOverlayHUD } from "./BroadcastOverlayHUD";
import { InterpolatedMatchState } from "./SpatialInterpolator";

describe("BroadcastOverlayHUD", () => {
  let container: HTMLDivElement;
  let root: Root;

  const mockHome = {
    team_id: "h1",
    team_name: "Apex Lagos",
    short_name: "APX",
    formation: "4-3-3",
    primary_color: "#00E676",
    secondary_color: "#F5B83D",
    accent_color: "#FFFFFF",
    goalkeeper_color: "#FFB800",
  };

  const mockAway = {
    team_id: "a1",
    team_name: "Nairobi Stars",
    short_name: "NST",
    formation: "4-4-2",
    primary_color: "#3B82F6",
    secondary_color: "#1E40AF",
    accent_color: "#FFFFFF",
    goalkeeper_color: "#EC4899",
  };

  const mockState: InterpolatedMatchState = {
    time_seconds: 135.0, // 02:15
    clock_minute: 2,
    phase: "open_play",
    home_score: 1,
    away_score: 0,
    home_attacks_right: true,
    possession_side: "home",
    camera_preset: "broadcast",
    event_banner: "GOAL! Osimhen breaks the deadlock!",
    players: [
      {
        player_id: "p1",
        team_id: "h1",
        side: "home",
        label: "Osimhen",
        role: "ST",
        position3D: [10, 0, 5],
        facingAngleRad: 0,
        animation_state: "celebrate",
        speed_ratio: 0.5,
        has_possession: true,
      },
    ],
    ball: {
      position3D: [12, 0.2, 5],
      height: 0.2,
      state: "rolling",
    },
  };

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
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

  test("renders scorebug with team abbreviations, scores, and formatted clock", async () => {
    await act(async () => {
      root.render(
        <BroadcastOverlayHUD
          matchState={mockState}
          homeTeam={mockHome}
          awayTeam={mockAway}
          matchLabel="Apex Lagos vs Nairobi Stars"
          cameraMode="director_auto"
          onSelectCameraMode={jest.fn()}
          onToggle2DFallback={jest.fn()}
        />
      );
    });

    expect(container.textContent).toContain("APX");
    expect(container.textContent).toContain("NST");
    expect(container.textContent).toContain("02:15");
    expect(container.textContent).toContain("1ST HALF");
  });

  test("renders event banner when event is active", async () => {
    await act(async () => {
      root.render(
        <BroadcastOverlayHUD
          matchState={mockState}
          homeTeam={mockHome}
          awayTeam={mockAway}
          matchLabel="Apex Lagos vs Nairobi Stars"
          cameraMode="director_auto"
          onSelectCameraMode={jest.fn()}
          onToggle2DFallback={jest.fn()}
        />
      );
    });

    const banner = container.querySelector("[data-testid='broadcast-event-banner']");
    expect(banner).not.toBeNull();
    expect(banner?.textContent).toContain("GOAL! Osimhen breaks the deadlock!");
  });

  test("renders 2D radar minimap and fires camera and 2D mode toggles", async () => {
    const handleCamera = jest.fn();
    const handle2D = jest.fn();

    await act(async () => {
      root.render(
        <BroadcastOverlayHUD
          matchState={mockState}
          homeTeam={mockHome}
          awayTeam={mockAway}
          matchLabel="Apex Lagos vs Nairobi Stars"
          cameraMode="director_auto"
          onSelectCameraMode={handleCamera}
          onToggle2DFallback={handle2D}
        />
      );
    });

    const radar = container.querySelector("[data-testid='tactical-minimap-radar']");
    expect(radar).not.toBeNull();

    // Click tactical button
    const buttons = Array.from(container.querySelectorAll("button"));
    const tacticalBtn = buttons.find((b) => b.textContent?.includes("TACTICAL"));
    expect(tacticalBtn).toBeDefined();

    await act(async () => {
      tacticalBtn?.click();
    });
    expect(handleCamera).toHaveBeenCalledWith("tactical_high");

    // Click 2D companion toggle button
    const toggle2DBtn = container.querySelector("[data-testid='toggle-2d-companion-button']") as HTMLButtonElement;
    expect(toggle2DBtn).not.toBeNull();

    await act(async () => {
      toggle2DBtn?.click();
    });
    expect(handle2D).toHaveBeenCalled();
  });
});
