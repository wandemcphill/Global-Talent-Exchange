import React from "react";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { Pitch2DView } from "./Pitch2DView";
import type { PitchBall, PitchPlayer } from "../../match2d/matchStateAdapter";

type CapturedPitchProps = {
  players: PitchPlayer[];
  ball: PitchBall | null;
  eventType?: string | null;
  unavailable?: boolean;
  demo?: boolean;
  selectedKey?: string | null;
  onSelect?: (key: string) => void;
};

let lastPitchProps: CapturedPitchProps | null = null;

jest.mock("../../match2d/OrthographicPitch", () => ({
  __esModule: true,
  OrthographicPitch: (props: CapturedPitchProps) => {
    lastPitchProps = props;
    return (
      <div
        data-testid="mock-orthographic-pitch"
        data-player-count={props.players.length}
        data-event-type={props.eventType || ""}
        data-unavailable={props.unavailable ? "true" : "false"}
      >
        {props.players.map((p) => (
          <button
            key={p.renderKey || `${p.side}:${p.id}`}
            type="button"
            data-testid={`select-${p.side}-${p.id}`}
            onClick={() => props.onSelect?.(`${p.side}:${p.id}`)}
          >
            {p.name}
          </button>
        ))}
      </div>
    );
  },
}));

describe("Pitch2DView broadcast HUD, honesty states, and live frame ingestion", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    lastPitchProps = null;
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

  it("shows honest FEED UNAVAILABLE state when no live or recorded data exists and demo is false", () => {
    act(() => {
      root.render(
        <Pitch2DView
          matchId="live-match-missing-feed"
          frames={[]}
          demo={false}
          connectionStatus="error"
          homeName="Lagos Stars"
          awayName="Abuja City"
        />,
      );
    });

    const badge = container.querySelector('[data-testid="pitch-feed-status"]');
    expect(badge?.textContent).toBe("FEED UNAVAILABLE");
    expect(container.querySelector('[data-testid="pitch-demo-badge"]')).toBeNull();
    expect(lastPitchProps?.unavailable).toBe(true);
    expect(lastPitchProps?.players.length).toBe(0);
  });

  it("renders DEMO badge only when matchId is an explicit showcase/demo match", () => {
    act(() => {
      root.render(
        <Pitch2DView
          matchId="u2a-006-showcase"
          frames={[]}
          demo={true}
          timeSeconds={12}
          homeName="Lagos Stars"
          awayName="Abuja City"
        />,
      );
    });

    const demoBadge = container.querySelector('[data-testid="pitch-demo-badge"]');
    expect(demoBadge?.textContent).toBe("DEMO");
    expect(lastPitchProps?.unavailable).toBe(false);
    expect(lastPitchProps?.demo).toBe(true);
  });

  it("renders television-style broadcast banner for goal and half-time states", () => {
    const baseFrames = [
      {
        frame_id: "f-goal",
        time_seconds: 1380,
        clock_minute: 23,
        phase: "open_play",
        home_score: 2,
        away_score: 1,
        event_type: "goal",
        primary_player_id: "h9",
        possession_side: "home",
        players: [
          {
            player_id: "h9",
            name: "V. Osimhen",
            side: "home",
            shirt_number: 9,
            role: "ST",
            x: 92,
            y: 49,
            has_ball: true,
          },
        ],
        ball: { x: 99, y: 50, z: 0.4, owner_player_id: "h9", state: "shot" },
      },
      {
        frame_id: "f-ht",
        time_seconds: 2700,
        clock_minute: 45,
        phase: "halftime",
        home_score: 2,
        away_score: 1,
        event_type: "halftime",
        players: [
          {
            player_id: "h9",
            name: "V. Osimhen",
            side: "home",
            shirt_number: 9,
            role: "ST",
            x: 50,
            y: 50,
          },
        ],
        ball: { x: 50, y: 50, z: 0, state: "stopped" },
      },
    ];

    act(() => {
      root.render(
        <Pitch2DView
          matchId="match-banner-test"
          frames={baseFrames}
          timeSeconds={1380}
          homeScore={2}
          awayScore={1}
          homeName="Lagos Stars"
          awayName="Abuja City"
          events={[
            {
              type: "goal",
              time_seconds: 1380,
              minute: 23,
              banner_text: "Clinical low finish inside the near post",
            },
          ]}
        />,
      );
    });

    const goalBanner = container.querySelector('[data-testid="pitch-broadcast-banner"]');
    expect(goalBanner).not.toBeNull();
    expect(goalBanner?.getAttribute("data-banner-tone")).toBe("goal");
    expect(goalBanner?.textContent).toContain("GOAL");
    expect(goalBanner?.textContent).toContain("2 - 1");
    expect(goalBanner?.textContent).toContain("Clinical low finish inside the near post");

    act(() => {
      root.render(
        <Pitch2DView
          matchId="match-banner-test"
          frames={baseFrames}
          timeSeconds={2700}
          homeScore={2}
          awayScore={1}
          homeName="Lagos Stars"
          awayName="Abuja City"
        />,
      );
    });

    const htBanner = container.querySelector('[data-testid="pitch-broadcast-banner"]');
    expect(htBanner).not.toBeNull();
    expect(htBanner?.getAttribute("data-banner-tone")).toBe("phase");
    expect(htBanner?.textContent).toContain("HALF-TIME");
    expect(htBanner?.textContent).toContain("2 - 1");
  });

  it("renders selected player card with match event tallies and forwards telemetry across live socket frames", () => {
    act(() => {
      root.render(
        <Pitch2DView
          matchId="live-match-1"
          timeSeconds={600}
          connectionStatus="connected"
          homeName="Lagos Stars"
          awayName="Abuja City"
          selectedKey="home:h9"
          events={[
            { type: "goal", player_id: "h9", minute: 10 },
            { type: "yellow_card", player_id: "h9", minute: 14 },
          ]}
          socketFrame={{
            frame_id: "live-1",
            sequence: 10,
            time_seconds: 600,
            clock_minute: 10,
            phase: "open_play",
            event_type: "pass",
            players: [
              {
                player_id: "h9",
                name: "V. Osimhen",
                side: "home",
                shirt_number: 9,
                role: "ST",
                x: 68,
                y: 44,
                vx: 4.2,
                vy: -0.5,
                speed_ratio: 0.78,
                stamina_pct: 89,
                has_ball: true,
              } as any,
            ],
            ball: { x: 69, y: 44, z: 0, owner_player_id: "h9" },
          }}
        />,
      );
    });

    const card = container.querySelector('[data-testid="selected-player-card"]');
    expect(card).not.toBeNull();
    expect(card?.textContent).toContain("V. Osimhen");
    expect(card?.textContent).toContain("Goals 1");
    expect(card?.textContent).toContain("Cards 1/0");

    expect(lastPitchProps?.players[0]?.speedRatio).toBeCloseTo(0.78, 2);
    expect(lastPitchProps?.players[0]?.staminaPct).toBeCloseTo(89, 1);
  });
});
