declare const describe: any;
declare const test: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ControlCenter } from "./ControlCenter";
import { ClubStory } from "./ClubStory";
import { Newsroom } from "./Newsroom";

var mockApiGet = jest.fn();
var mockApiPost = jest.fn();
var mockNavigate = jest.fn();
var mockRouteClubId: string | undefined = undefined;

jest.mock("react-router-dom", () => {
  const ReactModule = require("react");
  return {
    useParams: () => ({ clubId: mockRouteClubId }),
    useLocation: () => ({ pathname: "/app", search: "", hash: "" }),
    useNavigate: () => mockNavigate,
    Link: ({ to, children, ...props }: any) =>
      ReactModule.createElement("a", { href: typeof to === "string" ? to : "#", ...props }, children),
  };
});

jest.mock("@/lib/auth", () => ({
  useAuth: () => ({
    user: { id: "owner-user-1", account_type: "user", display_name: "Test Owner" },
    loading: false,
  }),
}));

jest.mock("sonner", () => ({
  toast: {
    success: () => {},
    error: () => {},
  },
}));

jest.mock("@/components/gtex/Cinema3DStage", () => ({
  Cinema3DStage: ({ title }: any) => {
    const ReactModule = require("react");
    return ReactModule.createElement("div", { "data-testid": "mock-cinema-3d-stage" }, title);
  },
}));

jest.mock("@/components/gtex/ClubOperationsCentre3D", () => ({
  ClubOperationsCentre3D: () => {
    const ReactModule = require("react");
    return ReactModule.createElement("div", { "data-testid": "mock-ops-3d" }, "3D Ops");
  },
}));

jest.mock("@/components/gtex/WorldClockCard", () => ({
  WorldClockCard: () => {
    const ReactModule = require("react");
    return ReactModule.createElement("div", { "data-testid": "mock-world-clock" }, "World Clock");
  },
}));

jest.mock("@/components/gtex/OwnerBriefingPanel", () => ({
  OwnerBriefingPanel: () => {
    const ReactModule = require("react");
    return ReactModule.createElement("div", { "data-testid": "mock-owner-briefing" }, "Briefing");
  },
}));

jest.mock("@/components/gtex/ApexWidgets", () => ({
  HolographicPlayerCard: () => null,
  TacticalPitch25D: () => null,
  TelemetrySparklineCard: () => null,
}));

jest.mock("@/lib/api", () => ({
  API: "http://localhost:8000/api",
  api: {
    get: (...args: any[]) => mockApiGet(...args),
    post: (...args: any[]) => mockApiPost(...args),
  },
  errMsg: (e: any) => String(e?.response?.data?.detail || e?.message || e || "Error"),
}));

async function flushPromises() {
  for (let i = 0; i < 6; i += 1) {
    await act(async () => {
      await Promise.resolve();
      await new Promise((resolve) => setTimeout(resolve, 10));
    });
  }
}

function http500(message = "Internal Server Error") {
  return Object.assign(new Error("Request failed with status code 500"), {
    response: { status: 500, data: { detail: message } },
  });
}

describe("Living Club Pages Error, Empty & Retry Flows (Simulated HTTP 500)", () => {
  let container: HTMLDivElement;
  let root: Root;
  let queryClient: QueryClient;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    localStorage.clear();
    mockRouteClubId = undefined;
    mockApiGet.mockReset();
    mockApiPost.mockReset();
    mockNavigate.mockReset();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          gcTime: 0,
        },
      },
    });
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    queryClient.clear();
    container.remove();
  });

  test("ControlCenter renders HTTP 500 error state, recovers to empty no-club state on retry, and loads active club on subsequent retry", async () => {
    let phase: "error" | "empty" | "active" = "error";
    mockApiGet.mockImplementation(async (url: string) => {
      if (url === "/owner/control-center") {
        if (phase === "error") throw http500("Control Center database unavailable");
        if (phase === "empty") {
          return { data: { clubs: [], economy: { wallet: {} }, fixtures: { upcoming: [], recent: [] }, inbox: [] } };
        }
        return {
          data: {
            clubs: [
              {
                club_id: "club-retry-1",
                club_name: "Atlantic United FC",
                short_name: "AUFC",
                stage: "active",
                world_day: 9,
                prestige: 66,
                fans: 14200,
              },
            ],
            economy: { wallet: { gtex_total: 42000, gtex_earned: 12000, fan_total: 9500 } },
            fixtures: { upcoming: [], recent: [] },
            inbox: [],
            ecosystem_waterfall: {},
          },
        };
      }
      if (url === "/owner/clubs/club-retry-1") {
        return { data: { state: { club_name: "Atlantic United FC", prestige: 66 }, staff: {}, facilities: {} } };
      }
      if (url === "/owner/clubs/club-retry-1/institutional-pulse") {
        return {
          data: {
            club_id: "club-retry-1",
            world_day: 9,
            reputation_dimensions: {},
            supporters: { overall_sentiment: 70, active_protest_stage: "none", matchday_atmosphere_rating: 75 },
            unified_timeline: [],
          },
        };
      }
      return { data: {} };
    });

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ControlCenter />
        </QueryClientProvider>
      );
    });
    await flushPromises();

    const errorState = container.querySelector('[data-testid="control-center-error-state"]');
    expect(errorState).not.toBeNull();
    expect(errorState?.textContent).toContain("GTEX workspace unavailable");

    // Retry while backend returns zero clubs -> renders empty/no-club onboarding state
    phase = "empty";
    const retryBtn = container.querySelector('[data-testid="control-center-retry-btn"]') as HTMLButtonElement;
    expect(retryBtn).not.toBeNull();
    await act(async () => {
      retryBtn.click();
    });
    await flushPromises();

    expect(container.querySelector('[data-testid="control-center-error-state"]')).toBeNull();
    expect(container.querySelector('[data-testid="no-club-home"]')).not.toBeNull();

    // Verify recovery into full active club dashboard after HTTP 500 -> Retry -> populated response
    phase = "error";
    queryClient.clear();
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ControlCenter />
        </QueryClientProvider>
      );
    });
    await flushPromises();
    expect(container.querySelector('[data-testid="control-center-error-state"]')).not.toBeNull();

    phase = "active";
    const retryBtnActive = container.querySelector('[data-testid="control-center-retry-btn"]') as HTMLButtonElement;
    await act(async () => {
      retryBtnActive.click();
    });
    await flushPromises();

    const dashboard = container.querySelector('[data-testid="control-center-screen"]');
    expect(dashboard).not.toBeNull();
    expect(dashboard?.textContent).toContain("Atlantic United FC");
  });

  test("ClubStory renders empty state with no clubId, HTTP 500 error state, and recovers cleanly on Retry Chronicle click", async () => {
    mockRouteClubId = undefined;
    mockApiGet.mockImplementation(async (url: string) => {
      if (url === "/owner/control-center") {
        return { data: { clubs: [] } };
      }
      if (url === "/owner/clubs/club-story-500/story") {
        throw http500("Chronicle store unavailable");
      }
      return { data: {} };
    });

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ClubStory />
        </QueryClientProvider>
      );
    });
    await flushPromises();

    const emptyState = container.querySelector('[data-testid="club-story-empty"]');
    expect(emptyState).not.toBeNull();
    expect(emptyState?.textContent).toContain("No Club Selected");

    // Now navigate to an explicit clubId whose story endpoint returns HTTP 500
    mockRouteClubId = "club-story-500";
    let storyFail = true;
    mockApiGet.mockImplementation(async (url: string) => {
      if (url === "/owner/control-center") {
        return { data: { clubs: [{ club_id: "club-story-500", club_name: "Delta Rovers FC" }] } };
      }
      if (url === "/owner/clubs/club-story-500/story") {
        if (storyFail) throw http500("Chronicle store unavailable");
        return {
          data: {
            club_id: "club-story-500",
            club_name: "Delta Rovers FC",
            is_owner: true,
            chapters: [],
            timeline: [
              {
                id: "h-1",
                type: "club_creation",
                category: "club_creation",
                title: "Delta Rovers Chartered",
                detail: "Founding record restored after retry.",
                is_milestone: true,
                at: "2026-11-14T10:00:00Z",
              },
            ],
            established_facts: { division_level: "division_1", prestige: 62, fans: 12000, matches_played: 5, trophies_count: 0 },
            supporters: { profile: {}, segments: [], matchday_atmosphere: {}, recent_reactions: [] },
            institutional_archive: {
              club_records: {},
              narrative_chapters: [],
              season_archive: [],
              managerial_history: [],
              transfer_history: [],
              academy_legacy: [],
              historic_rivalries: [],
              timeline: [],
            },
          },
        };
      }
      return { data: {} };
    });

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ClubStory />
        </QueryClientProvider>
      );
    });
    await flushPromises();

    const errBanner = container.querySelector('[data-testid="club-story-error"]');
    expect(errBanner).not.toBeNull();
    expect(errBanner?.textContent).toContain("Unable to Load Club Chronicle");

    storyFail = false;
    const retryBtn = container.querySelector('[data-testid="club-story-retry-btn"]') as HTMLButtonElement;
    expect(retryBtn).not.toBeNull();
    await act(async () => {
      retryBtn.click();
    });
    await flushPromises();

    expect(container.querySelector('[data-testid="club-story-error"]')).toBeNull();
    expect(container.textContent).toContain("Delta Rovers Chartered");
  });

  test("Newsroom renders HTTP 500 error state, recovers to empty wire state on retry, and displays verified dispatch when available", async () => {
    let wireMode: "error" | "empty" | "populated" = "error";
    mockApiGet.mockImplementation(async (url: string) => {
      if (url === "/owner/control-center") {
        return { data: { clubs: [{ club_id: "club-news-1", club_name: "Kano Comet FC" }] } };
      }
      if (url.startsWith("/owner/newsroom")) {
        if (wireMode === "error") throw http500("Newsroom feed unavailable");
        if (wireMode === "empty") {
          return { data: { articles: [], established_facts: { club_name: "Kano Comet FC", prestige: 60, fans: 11000 } } };
        }
        return {
          data: {
            articles: [
              {
                id: "art-1",
                category: "match_result",
                headline: "Kano Comet Recover Wire Coverage",
                subheadline: "Verified Full-Time Dispatch",
                body: "Match report confirmed after wire reconnection.",
                source_event_id: "evt-wire-99",
                grounding_report: { valid: true },
                created_at: "2026-11-15T01:00:00Z",
              },
            ],
            established_facts: { club_name: "Kano Comet FC", prestige: 60, fans: 11000 },
          },
        };
      }
      if (url === "/owner/clubs/club-news-1/media") {
        return { data: { outlets: [], stories: [], media_standing: null } };
      }
      if (url === "/owner/clubs/club-news-1/institutional-pulse") {
        return { data: { reputation_dimensions: {} } };
      }
      return { data: {} };
    });

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <Newsroom />
        </QueryClientProvider>
      );
    });
    await flushPromises();

    const newsError = container.querySelector('[data-testid="newsroom-error-state"]');
    expect(newsError).not.toBeNull();
    expect(newsError?.textContent).toContain("News Wire Temporarily Unavailable");

    wireMode = "empty";
    const retryEmptyBtn = container.querySelector('[data-testid="newsroom-retry-btn"]') as HTMLButtonElement;
    expect(retryEmptyBtn).not.toBeNull();
    await act(async () => {
      retryEmptyBtn.click();
    });
    await flushPromises();

    expect(container.querySelector('[data-testid="newsroom-error-state"]')).toBeNull();
    expect(container.textContent).toContain("No Dispatches on this Wire");

    // Simulate second 500 error followed by retry returning a populated dispatch
    wireMode = "error";
    queryClient.clear();
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <Newsroom />
        </QueryClientProvider>
      );
    });
    await flushPromises();
    expect(container.querySelector('[data-testid="newsroom-error-state"]')).not.toBeNull();

    wireMode = "populated";
    const retryPopBtn = container.querySelector('[data-testid="newsroom-retry-btn"]') as HTMLButtonElement;
    await act(async () => {
      retryPopBtn.click();
    });
    await flushPromises();

    expect(container.querySelector('[data-testid="newsroom-error-state"]')).toBeNull();
    const leadCard = container.querySelector('[data-testid="lead-story-card"]');
    expect(leadCard).not.toBeNull();
    expect(leadCard?.textContent).toContain("Kano Comet Recover Wire Coverage");
  });
});
