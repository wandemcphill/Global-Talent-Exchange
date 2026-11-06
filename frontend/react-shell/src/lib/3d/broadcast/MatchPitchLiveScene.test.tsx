import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { MatchPitchLiveScene } from "./MatchPitchLiveScene";

describe("MatchPitchLiveScene", () => {
  let container: HTMLDivElement;
  let root: Root;

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
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
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

    // In JSDOM without real hardware WebGL, it will render either the WebGL canvas container or fallback
    expect(sceneEl || container.querySelector("[data-testid='test-pitch-scene-fallback-container']")).not.toBeNull();
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
  });
});
