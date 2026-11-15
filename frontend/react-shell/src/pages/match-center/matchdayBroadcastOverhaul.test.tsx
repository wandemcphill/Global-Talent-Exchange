import React from "react";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MatchCenter from "../MatchCenter";
import type {
  CardDetailSummary,
  OffsideSnapshot,
  PitchPlayer,
  VarReviewSummary,
} from "../../match2d/matchStateAdapter";

const mockSearchParams = new URLSearchParams();

jest.mock("react-router-dom", () => ({
  __esModule: true,
  Link: ({ children, to, ...rest }: any) => (
    <a href={typeof to === "string" ? to : "#"} {...rest}>
      {children}
    </a>
  ),
  useParams: () => ({ id: "match-overhaul-1" }),
  useSearchParams: () => [mockSearchParams, jest.fn()],
}));

jest.mock("sonner", () => ({
  __esModule: true,
  toast: {
    info: jest.fn(),
    success: jest.fn(),
    error: jest.fn(),
  },
}));

let lastOrthographicProps: {
  players: PitchPlayer[];
  homeColor?: string;
  awayColor?: string;
  homeKitPattern?: string;
  cameraMode?: string;
  offsideSnapshot?: OffsideSnapshot | null;
  varReview?: VarReviewSummary | null;
  cardDetail?: CardDetailSummary | null;
} | null = null;

const mockApiGet = jest.fn();
const mockApiPost = jest.fn();

jest.mock("@/lib/api", () => ({
  __esModule: true,
  api: {
    get: (...args: any[]) => mockApiGet(...args),
    post: (...args: any[]) => mockApiPost(...args),
  },
  errMsg: (err: any) => String(err?.message || err || "error"),
  tokens: {
    get: () => null,
  },
}));

jest.mock("@/lib/owner", () => ({
  __esModule: true,
  useActiveClub: () => ({ active: { club_id: "club-home" } }),
  useRefreshOwner: () => jest.fn(),
}));

jest.mock("@/lib/skin-engine", () => ({
  __esModule: true,
  useSkin: () => ({
    getModuleView: () => "broadcast",
    setModuleView: jest.fn(),
  }),
}));

jest.mock("@/lib/3d/broadcast/useMatchSpectatorStream", () => ({
  __esModule: true,
  useMatchSpectatorStream: () => ({
    connectionStatus: "disconnected",
    lastFrame: null,
    latestScore: null,
    recentEvents: [],
    error: null,
    spectatorCount: 0,
  }),
}));

jest.mock("@/lib/3d/broadcast/useMatchFullTimeGovernance", () => ({
  __esModule: true,
  useMatchFullTimeGovernance: () => undefined,
}));

jest.mock("@/components/gtex/Cinema3DStage", () => ({
  __esModule: true,
  Cinema3DStage: () => <div data-testid="mock-cinema-3d-stage" />,
}));

jest.mock("@/components/gtex/PressRoomStage", () => ({
  __esModule: true,
  PressRoomStage: () => <div data-testid="mock-press-room" />,
}));

jest.mock("@/components/gtex/MatchdayLineupBroadcast", () => ({
  __esModule: true,
  MatchdayLineupBroadcast: () => <div data-testid="mock-lineup-broadcast" />,
}));

jest.mock("@/components/gtex/ApexWidgets", () => ({
  __esModule: true,
  HolographicPlayerCard: () => <div data-testid="mock-holo-card" />,
}));

jest.mock("@/components/advertising/GtexMatchBroadcastAds", () => ({
  __esModule: true,
  MatchSponsorIdentificationBadge: () => <div data-testid="mock-sponsor-badge" />,
  SilentMatchBroadcastPanel: () => <div data-testid="mock-silent-ad-panel" />,
  useMatchCommercialInventory: () => ({
    sponsorAd: null,
    bannerAds: [],
    boardAds: [],
  }),
}));

jest.mock("@/lib/3d/gifting/CinematicGiftingEngine", () => ({
  __esModule: true,
  CinematicGiftingEngine: () => null,
}));

jest.mock("@/match2d/matchAudio", () => ({
  __esModule: true,
  sharedMatchAudio: {
    setEnabled: jest.fn(),
    updateAtmosphere: jest.fn(),
  },
}));

jest.mock("../../match2d/OrthographicPitch", () => ({
  __esModule: true,
  OrthographicPitch: (props: any) => {
    lastOrthographicProps = props;
    return (
      <div
        data-testid="mock-orthographic-pitch"
        data-player-count={props.players.length}
        data-camera-mode={props.cameraMode || ""}
        data-home-pattern={props.homeKitPattern || ""}
        data-home-color={props.homeColor || ""}
      />
    );
  },
}));

async function flushUi(ticks = 6): Promise<void> {
  for (let i = 0; i < ticks; i += 1) {
    await act(async () => {
      await Promise.resolve();
      await new Promise<void>((resolve) => setTimeout(resolve, 0));
    });
  }
}

async function waitForDomCondition(
  predicate: () => boolean,
  container: HTMLElement,
  description: string,
  timeoutMs = 5000,
): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() <= deadline) {
    if (predicate()) {
      return;
    }
    await act(async () => {
      await Promise.resolve();
      await new Promise<void>((resolve) => setTimeout(resolve, 10));
    });
    if (predicate()) {
      return;
    }
  }
  throw new Error(
    `Timed out waiting for ${description} after ${timeoutMs}ms. DOM preview: ${
      (container.textContent || "").slice(0, 400) || "<empty>"
    }`,
  );
}

describe("MatchCenter universal broadcast overhaul integration", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    lastOrthographicProps = null;
    mockApiGet.mockReset();
    mockApiPost.mockReset();
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

  it("syncs shared server timeline, kit identity, authoritative xG, VAR/offside/card/sub overlays, and removes playback/tactic controls", async () => {
    const viewerPayload = {
      match_id: "match-overhaul-1",
      venue_name: "Lagos Broadcast Arena",
      duration_seconds: 900,
      broadcast_session: {
        match_id: "match-overhaul-1",
        competition_category: "major_knockout",
        assigned_duration_seconds: 900,
        current_broadcast_position_seconds: 240,
        broadcast_status: "live",
      },
      home_team: {
        team_id: "club-home",
        team_name: "Lagos Titans",
        primary_color: "#006633",
        secondary_color: "#ffffff",
        accent_color: "#facc15",
        shorts_color: "#004422",
        socks_color: "#ffffff",
        kit_pattern: "stripes",
        crest_url: "https://cdn.example.com/home-crest.png",
        formation: "4-2-3-1",
      },
      away_team: {
        team_id: "club-away",
        team_name: "Cairo Royals",
        primary_color: "#cc1122",
        secondary_color: "#111827",
        accent_color: "#f8fafc",
        shorts_color: "#111827",
        socks_color: "#cc1122",
        kit_pattern: "halves",
        crest_url: "https://cdn.example.com/away-crest.png",
        formation: "4-3-3",
      },
      stats: {
        home_shots: 9,
        away_shots: 4,
        home_possession: 58,
        away_possession: 42,
        home_expected_goals: 1.84,
        away_expected_goals: 0.92,
        home_yellow_cards: 1,
        home_red_cards: 0,
        away_yellow_cards: 2,
        away_red_cards: 1,
        home_pass_accuracy: 86,
        away_pass_accuracy: 79,
        home_expected_threat: 2.1,
        away_expected_threat: 1.05,
        home_ppda: 8.4,
        away_ppda: 12.1,
      },
      events: [
        {
          id: "ev-sub-1",
          minute: 38,
          time_seconds: 235,
          type: "substitution",
          team: "home",
          player_name: "A. Musa",
          text: "Musa replaces injured winger Okoro",
        },
        {
          id: "ev-var-1",
          minute: 39,
          time_seconds: 240,
          type: "goal",
          team: "home",
          xg: 0.45,
          text: "VAR confirms goal stands after offside check",
        },
      ],
      frames: [
        {
          frame_id: "frame-0",
          time_seconds: 0,
          clock_minute: 1,
          phase: "first_half",
          home_score: 0,
          away_score: 0,
          ball: { x: 0.5, y: 0.5, height: 0, state: "in_play" },
          players: [
            { player_id: "h1", side: "home", x: 0.25, y: 0.5, shirt_number: 9, name: "Home 9", active: true },
            { player_id: "a1", side: "away", x: 0.72, y: 0.5, shirt_number: 5, name: "Away 5", active: true },
          ],
        },
        {
          frame_id: "frame-240",
          time_seconds: 240,
          clock_minute: 39,
          phase: "first_half",
          event_type: "var_review",
          home_score: 1,
          away_score: 0,
          ball: { x: 0.88, y: 0.5, height: 0.2, state: "shot" },
          offside_snapshot: {
            offside_line_x: 0.82,
            attacker_line_x: 0.8,
            margin_meters: -0.45,
            attacker_body_part: "torso",
            is_offside_position: false,
            is_penalised: false,
            reason: "Defender played onside by trailing foot",
          },
          var_review: {
            review_id: "var-check-1",
            category: "goal_no_goal",
            original_decision: "On-field offside flag",
            final_decision: "Goal awarded (onside)",
            decision_outcome: "overturned",
            reason: "Attacker torso behind second-last defender",
          },
          card_detail: {
            card_type: "red",
            reason: "Denial of an obvious goalscoring opportunity",
            player_id: "a1",
            player_name: "Away 5",
            second_yellow: false,
            dismissed: true,
          },
          players: [
            { player_id: "h1", side: "home", x: 0.8, y: 0.48, shirt_number: 9, name: "Home 9", active: true },
            { player_id: "h2", side: "home", x: 0.76, y: 0.55, shirt_number: 10, name: "A. Musa", active: true },
            { player_id: "a1", side: "away", x: 0.82, y: 0.52, shirt_number: 5, name: "Away 5", active: false, state: "sent_off" },
          ],
        },
        {
          frame_id: "frame-900",
          time_seconds: 900,
          clock_minute: 90,
          phase: "full_time",
          home_score: 1,
          away_score: 0,
          ball: { x: 0.5, y: 0.5, height: 0, state: "dead_ball" },
          players: [
            { player_id: "h1", side: "home", x: 0.5, y: 0.5, shirt_number: 9, name: "Home 9", active: true },
          ],
        },
      ],
    };

    mockApiGet.mockImplementation(async (url: string) => {
      if (url === "/match-viewer/match-overhaul-1") {
        return { data: viewerPayload };
      }
      if (url === "/owner/matches/match-overhaul-1") {
        throw new Error("Fallback to /match-viewer");
      }
      if (url === "/matches/match-overhaul-1/state") {
        return { data: null };
      }
      if (url === "/matches/match-overhaul-1/tactics") {
        return {
          data: {
            home: {
              formation: "4-2-3-1",
              press_intensity: 82,
              defensive_line: 74,
              tempo: 78,
              risk_level: 61,
            },
            away: {
              formation: "4-3-3",
              press_intensity: 45,
              defensive_line: 40,
              tempo: 50,
              risk_level: 40,
            },
          },
        };
      }
      if (url === "/matches/match-overhaul-1/predictions") {
        return { data: null };
      }
      return { data: null };
    });

    jest.useRealTimers();
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <MatchCenter />
        </QueryClientProvider>,
      );
    });

    await waitForDomCondition(
      () =>
        Boolean(
          container
            .querySelector('[data-testid="broadcast-category-badge"]')
            ?.textContent?.includes("major knockout · 15m") &&
            container.querySelector('[data-testid="tactics-panel"]')?.textContent?.includes("82%"),
        ),
      container,
      "MatchCenter broadcast badge and tactics telemetry",
    );

    // 1. Category badge + kit swatches + authoritative xG
    expect(container.querySelector('[data-testid="broadcast-category-badge"]')?.textContent).toContain(
      "major knockout · 15m",
    );
    expect(container.querySelector('[data-testid="home-kit-swatch"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="away-kit-swatch"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="live-xg-totals"]')?.textContent).toBe("xG 1.84 – 0.92");

    // 2. Shared server position synced without seek controls
    const scrubber = container.querySelector('[role="progressbar"]');
    expect(scrubber).not.toBeNull();
    expect(Number(scrubber?.getAttribute("aria-valuenow"))).toBeGreaterThanOrEqual(240);
    expect(container.querySelector('input[type="range"]')).toBeNull();

    // 3. No viewer-controlled playback controls remain anywhere
    expect(container.querySelector('[data-testid="match-pause-toggle"]')).toBeNull();
    expect(container.querySelector('[data-testid="match-speed-toggle"]')).toBeNull();
    expect(container.querySelector('[data-testid="highlight-mode-selector"]')).toBeNull();
    expect(container.querySelector('[data-testid="watch-instant-replay-btn"]')).toBeNull();
    expect(container.querySelector('[data-testid="exit-instant-replay-btn"]')).toBeNull();
    expect(container.querySelector('[data-testid="toggle-3d-broadcast-mode"]')).toBeNull();
    expect(container.querySelector('[data-testid="enter-match-theatre-button"]')).toBeNull();

    // 4. Pitch2DView + OrthographicPitch receive active-only players (red-carded player excluded), kits, and VAR/offside/card overlays
    expect(lastOrthographicProps).not.toBeNull();
    expect(lastOrthographicProps?.homeColor).toBe("#006633");
    expect(lastOrthographicProps?.homeKitPattern).toBe("stripes");
    expect(lastOrthographicProps?.cameraMode).toBe("2.5d");
    expect(lastOrthographicProps?.players.map((p) => p.playerId)).toEqual(["h1", "h2"]);

    expect(container.querySelector('[data-testid="pitch-feed-status"]')?.textContent).toBe("FINAL");
    expect(container.querySelector('[data-testid="auto-var-replay-badge"]')?.textContent).toContain(
      "AUTOMATIC VAR / BROADCAST REPLAY",
    );
    expect(container.querySelector('[data-testid="pitch-var-monitor"]')?.textContent).toContain("Goal awarded");
    expect(container.querySelector('[data-testid="pitch-offside-banner"]')?.textContent).toContain(
      "LAW 11 OFFSIDE · ONSIDE",
    );
    expect(container.querySelector('[data-testid="pitch-card-detail-banner"]')?.textContent).toContain(
      "Denial of an obvious goalscoring opportunity",
    );
    expect(container.querySelector('[data-testid="substitution-lower-third"]')?.textContent).toContain(
      "Musa replaces injured winger Okoro",
    );

    // 4B. Camera mode switch updates OrthographicPitch perspective preset
    const cam2dBtn = container.querySelector('[data-testid="cam-mode-2d"]') as HTMLButtonElement | null;
    expect(cam2dBtn).not.toBeNull();
    act(() => {
      cam2dBtn?.click();
    });
    expect(lastOrthographicProps?.cameraMode).toBe("2d");

    // 5. Read-only manager authority in TacticalHUD — reflects authoritative backend values, zero POST mutations
    const tacticsBanner = container.querySelector('[data-testid="manager-matchday-authority-banner"]');
    expect(tacticsBanner?.textContent).toContain("READ-ONLY DUGOUT TELEMETRY");
    const tacticsPanel = container.querySelector('[data-testid="tactics-panel"]');
    expect(tacticsPanel?.textContent).toContain("4-2-3-1");
    expect(tacticsPanel?.textContent).toContain("82%");
    expect(tacticsPanel?.textContent).toContain("74%");
    expect(mockApiPost).not.toHaveBeenCalled();

    queryClient.clear();
  });
});
