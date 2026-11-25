import React from "react";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Competitions from "../Competitions";
import MatchCenter from "../MatchCenter";

const mockNavigate = jest.fn();
const mockSearchParams = new URLSearchParams();

jest.mock("react-router-dom", () => ({
  __esModule: true,
  Link: ({ children, to, ...rest }: any) => (
    <a href={typeof to === "string" ? to : "#"} {...rest}>
      {children}
    </a>
  ),
  useNavigate: () => mockNavigate,
  useParams: () => ({ id: "sim-match-1" }),
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

const mockApiGet = jest.fn();
const mockApiPost = jest.fn();
const mockApiPut = jest.fn();

jest.mock("@/lib/api", () => ({
  __esModule: true,
  API: "http://127.0.0.1:8000/api",
  api: {
    get: (...args: any[]) => mockApiGet(...args),
    post: (...args: any[]) => mockApiPost(...args),
    put: (...args: any[]) => mockApiPut(...args),
  },
  errMsg: (err: any) => String(err?.message || err || "error"),
  tokens: {
    get: () => null,
  },
}));

jest.mock("@/lib/auth", () => ({
  __esModule: true,
  useAuth: () => ({ user: { id: "user-1", region: "AF-WEST" } }),
}));

jest.mock("@/lib/owner", () => ({
  __esModule: true,
  fmt: (v: any) => String(v ?? 0),
  label: (s: any) => String(s || "").replace(/_/g, " "),
  useActiveClub: () => ({
    active: {
      club_id: "club-home",
      club_name: "Lagos United",
      division_name: "Division 1",
      prestige: 60,
      squad_ovr: 79,
      squad_depth: 72,
      region: "AF-WEST",
    },
  }),
  useRefreshOwner: () => jest.fn(),
}));

jest.mock("@/lib/skin-engine", () => ({
  __esModule: true,
  useSkin: () => ({
    getModuleView: () => "discovery",
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

jest.mock("@/lib/3d/GtexSceneViewport", () => ({
  __esModule: true,
  GtexSceneViewport: () => <div data-testid="mock-gtex-scene-viewport" />,
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
  MatchSponsorIdentificationBadge: () => null,
  SilentMatchBroadcastPanel: () => null,
  useMatchCommercialInventory: () => ({ sponsorAd: null, bannerAds: [], boardAds: [] }),
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
  OrthographicPitch: () => <div data-testid="mock-orthographic-pitch" />,
}));

const SAMPLE_REPORT = {
  match_id: "sim-match-1",
  home_team_id: "club-home",
  away_team_id: "bot-away",
  home_team_name: "Lagos United",
  away_team_name: "Accra Sparks",
  home_score: 2,
  away_score: 1,
  result: "win",
  summary_line: "Lagos United 2 - 1 Accra Sparks",
  is_simulated: true,
  stats: {
    home_possession: 57,
    away_possession: 43,
    home_shots: 11,
    away_shots: 6,
    home_shots_on_target: 5,
    away_shots_on_target: 2,
    home_saves: 1,
    away_saves: 3,
    home_expected_goals: 1.94,
    away_expected_goals: 0.88,
    home_yellow_cards: 1,
    away_yellow_cards: 2,
    home_red_cards: 0,
    away_red_cards: 0,
    home_big_chances: 3,
    away_big_chances: 1,
    home_assists: 2,
    away_assists: 1,
    home_key_passes: 7,
    away_key_passes: 4,
    home_tackles_won: 14,
    away_tackles_won: 11,
    home_interceptions: 9,
    away_interceptions: 6,
  },
  goals: [
    {
      minute: 23,
      clock_label: "23'",
      side: "home" as const,
      team_name: "Lagos United",
      scorer_name: "Victor Osimhen",
      assist_name: "Ademola Lookman",
      is_penalty: false,
      home_score: 1,
      away_score: 0,
    },
    {
      minute: 58,
      clock_label: "58'",
      side: "away" as const,
      team_name: "Accra Sparks",
      scorer_name: "Kwame Mensah",
      assist_name: "Kofi Boateng",
      is_penalty: false,
      home_score: 1,
      away_score: 1,
    },
    {
      minute: 81,
      clock_label: "81'",
      side: "home" as const,
      team_name: "Lagos United",
      scorer_name: "Alex Iwobi",
      assist_name: "Wilfred Ndidi",
      is_penalty: false,
      home_score: 2,
      away_score: 1,
    },
  ],
  cards: [
    {
      minute: 41,
      clock_label: "41'",
      side: "away" as const,
      team_name: "Accra Sparks",
      player_name: "Tariq Lamptey",
      card_type: "yellow_card",
    },
  ],
  motm: {
    available: true,
    player_id: "p-9",
    player_name: "Victor Osimhen",
    team_name: "Lagos United",
    side: "home" as const,
    role: "FW",
    goals: 1,
    assists: 0,
    rating: 8.8,
  },
  player_stats: [
    {
      player_id: "p-9",
      player_name: "Victor Osimhen",
      team_name: "Lagos United",
      side: "home" as const,
      role: "FW",
      goals: 1,
      assists: 0,
      key_passes: 2,
      saves: 0,
      rating: 8.8,
    },
    {
      player_id: "p-11",
      player_name: "Ademola Lookman",
      team_name: "Lagos United",
      side: "home" as const,
      role: "FW",
      goals: 0,
      assists: 1,
      key_passes: 3,
      saves: 0,
      rating: 8.3,
    },
  ],
};

async function waitFor(predicate: () => boolean, timeoutMs = 4000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() <= deadline) {
    if (predicate()) return;
    await act(async () => {
      await Promise.resolve();
      await new Promise<void>((resolve) => setTimeout(resolve, 10));
    });
  }
  throw new Error("Timed out waiting for condition");
}

describe("Simulated match report UX", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    mockNavigate.mockReset();
    mockApiGet.mockReset();
    mockApiPost.mockReset();
    mockApiPut.mockReset();
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

  it("shows scorers, assists, possession, and stats after simulating a quick match and hides Play & Watch Match", async () => {
    mockApiGet.mockImplementation(async (url: string) => {
      if (url === "/owner/competitions") return { data: { competitions: [] } };
      if (url === "/owner/world/clubs") return { data: { clubs: [] } };
      if (url === "/community/discovery/clubs") return { data: { clubs: [] } };
      if (url === "/simulation-matchmaking/fast-match/entitlement") {
        return { data: { wins_count: 2 } };
      }
      return { data: null };
    });
    mockApiPut.mockResolvedValue({ data: {} });
    mockApiPost.mockImplementation(async (url: string) => {
      if (url === "/simulation-matchmaking/quick-game") {
        return {
          data: {
            match_id: "sim-match-1",
            live_session: null,
            is_simulated: true,
            settlement_status: "settled",
            result: "win",
            home_score: 2,
            away_score: 1,
            opponent: { club_name: "Accra Sparks", region: "AF-WEST", is_bot: true },
            match_context: {
              tactical_story: "Instant tactical clash.",
              tactical_compatibility_score: 84,
              expected_difficulty: "medium",
            },
            match_report: SAMPLE_REPORT,
          },
        };
      }
      return { data: {} };
    });

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <Competitions />
        </QueryClientProvider>,
      );
    });

    await waitFor(() => Boolean(container.querySelector('[data-testid="launch-quick-game-btn"]')));

    const launchBtn = container.querySelector('[data-testid="launch-quick-game-btn"]') as HTMLButtonElement;
    await act(async () => {
      launchBtn.click();
    });

    await waitFor(() => Boolean(container.querySelector('[data-testid="simulated-match-report"]')));

    const bannerText = container.querySelector('[data-testid="quick-game-result-banner"]')?.textContent || "";
    expect(bannerText).toContain("Simulated · Full Time");
    expect(bannerText).toContain("Victor Osimhen");
    expect(bannerText).toContain("Ademola Lookman");
    expect(bannerText).toContain("57%");
    expect(bannerText).toContain("43%");
    expect(bannerText).toContain("1.94");
    expect(bannerText).toContain("0.88");
    expect(bannerText).toContain("Alex Iwobi");
    expect(bannerText).toContain("Wilfred Ndidi");

    // Must NOT offer "Play & Watch Match" or "Settle Match Result" once already simulated
    expect(container.querySelector('[data-testid="play-quick-game-btn"]')).toBeNull();
    expect(container.querySelector('[data-testid="settle-quick-game-btn"]')).toBeNull();
    expect(container.querySelector('[data-testid="view-simulated-report-btn"]')).not.toBeNull();

    queryClient.clear();
  });

  it("offers watch or simulate after pairing, and files the result only when simulate is chosen", async () => {
    mockApiGet.mockImplementation(async (url: string) => {
      if (url === "/owner/competitions") return { data: { competitions: [] } };
      if (url === "/owner/world/clubs") return { data: { clubs: [] } };
      if (url === "/community/discovery/clubs") return { data: { clubs: [] } };
      if (url === "/simulation-matchmaking/fast-match/entitlement") {
        return { data: { wins_count: 2 } };
      }
      return { data: null };
    });
    mockApiPut.mockResolvedValue({ data: {} });
    mockApiPost.mockImplementation(async (url: string) => {
      if (url === "/simulation-matchmaking/quick-game") {
        return {
          data: {
            match_id: "choice-match-1",
            is_simulated: false,
            settlement_status: null,
            home_score: null,
            away_score: null,
            opponent: { club_name: "Lagos Titans AI", region: "AF-WEST", is_bot: true },
            match_context: {
              tactical_story: "Instant tactical clash.",
              tactical_compatibility_score: 79,
              expected_difficulty: "high",
            },
          },
        };
      }
      if (url === "/simulation-matchmaking/quick-game/choice-match-1/settle") {
        return {
          data: {
            match_id: "choice-match-1",
            is_simulated: true,
            settlement_status: "settled",
            result: "win",
            home_score: 2,
            away_score: 0,
            match_report: SAMPLE_REPORT,
          },
        };
      }
      return { data: {} };
    });

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <Competitions />
        </QueryClientProvider>,
      );
    });

    await waitFor(() => Boolean(container.querySelector('[data-testid="launch-quick-game-btn"]')));
    const launchBtn = container.querySelector('[data-testid="launch-quick-game-btn"]') as HTMLButtonElement;
    await act(async () => {
      launchBtn.click();
    });

    await waitFor(() => Boolean(container.querySelector('[data-testid="quick-game-choice"]')));
    expect(container.querySelector('[data-testid="simulated-match-report"]')).toBeNull();
    expect(container.querySelector('[data-testid="play-quick-game-btn"]')?.textContent).toContain("Watch the match");
    expect(container.querySelector('[data-testid="settle-quick-game-btn"]')?.textContent).toContain("Simulate the result");

    const settleBtn = container.querySelector('[data-testid="settle-quick-game-btn"]') as HTMLButtonElement;
    await act(async () => {
      settleBtn.click();
    });

    await waitFor(() => Boolean(container.querySelector('[data-testid="simulated-match-report"]')));
    const bannerText = container.querySelector('[data-testid="quick-game-result-banner"]')?.textContent || "";
    expect(bannerText).toContain("Simulated · Full Time");
    expect(container.querySelector('[data-testid="play-quick-game-btn"]')).toBeNull();
    expect(container.querySelector('[data-testid="settle-quick-game-btn"]')).toBeNull();

    queryClient.clear();
  });

  it("renders MatchCenter as a full stats report (not a live watch pitch) for an already-simulated match", async () => {
    mockApiGet.mockImplementation(async (url: string) => {
      if (url === "/owner/matches/sim-match-1") {
        return {
          data: {
            id: "sim-match-1",
            competition_id: "comp-1",
            round: 1,
            home_club_id: "club-home",
            away_club_id: "bot-away",
            home_name: "Lagos United",
            away_name: "Accra Sparks",
            status: "played",
            home_goals: 2,
            away_goals: 1,
            is_simulated: true,
            stats: SAMPLE_REPORT.stats,
            match_report: SAMPLE_REPORT,
            events: [
              { minute: 23, type: "goal", team: "home", scorer: "Victor Osimhen", assist: "Ademola Lookman", text: "Victor Osimhen scores!" },
              { minute: 58, type: "goal", team: "away", scorer: "Kwame Mensah", assist: "Kofi Boateng", text: "Kwame Mensah scores!" },
              { minute: 81, type: "goal", team: "home", scorer: "Alex Iwobi", assist: "Wilfred Ndidi", text: "Alex Iwobi scores!" },
            ],
            narrative: { momentum: [55, 60, 58], match_report: SAMPLE_REPORT },
          },
        };
      }
      if (url === "/match-viewer/sim-match-1") {
        throw new Error("404");
      }
      return { data: null };
    });

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <MatchCenter />
        </QueryClientProvider>,
      );
    });

    await waitFor(() => Boolean(container.querySelector('[data-testid="simulated-match-report"]')));

    expect(container.querySelector('[data-testid="match-score"]')?.textContent).toContain("2 – 1");
    expect(container.querySelector('[data-testid="simulated-match-report-badge"]')?.textContent).toContain(
      "Simulated Match Report",
    );
    const reportText = container.querySelector('[data-testid="simulated-match-report"]')?.textContent || "";
    expect(reportText).toContain("Victor Osimhen");
    expect(reportText).toContain("Ademola Lookman");
    expect(reportText).toContain("57%");
    expect(reportText).toContain("43%");
    expect(reportText).toContain("1.94");
    expect(reportText).toContain("Man of the Match");

    // Must NOT render the live pitch board or camera watch controls
    expect(container.querySelector('[data-testid="mock-orthographic-pitch"]')).toBeNull();
    expect(container.querySelector('[data-testid="cam-mode-2d"]')).toBeNull();
    expect(container.querySelector('[data-testid="match-audio-toggle"]')).toBeNull();
    expect(container.textContent).not.toContain("authoritative match feed unavailable");

    queryClient.clear();
  });
});
