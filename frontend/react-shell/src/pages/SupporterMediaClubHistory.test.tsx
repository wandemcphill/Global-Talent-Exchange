declare const describe: any;
declare const test: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ClubStory } from "./ClubStory";
import { Newsroom } from "./Newsroom";

var mockApiPost = jest.fn();
var mockApiGet = jest.fn();
var mockRefresh = jest.fn();
var mockNavigate = jest.fn();

jest.mock("react-router-dom", () => {
  const ReactModule = require("react");
  return {
    useParams: () => ({ clubId: "club-lagos-1" }),
    useLocation: () => ({ pathname: "/app/story", search: "" }),
    useNavigate: () => mockNavigate,
    Link: ({ to, children, ...props }: any) =>
      ReactModule.createElement("a", { href: typeof to === "string" ? to : "#", ...props }, children),
  };
});

jest.mock("sonner", () => ({
  toast: {
    success: () => {},
    error: () => {},
  },
}));

jest.mock("@/components/gtex/Cinema3DStage", () => ({
  Cinema3DStage: ({ title, badgeText }: any) => {
    const ReactModule = require("react");
    return ReactModule.createElement(
      "div",
      { "data-testid": "mock-cinema-3d-stage" },
      ReactModule.createElement("span", null, title),
      ReactModule.createElement("span", null, badgeText),
    );
  },
}));

jest.mock("@/lib/api", () => ({
  API: "http://localhost:8000/api",
  api: {
    post: (...args: any[]) => mockApiPost(...args),
    get: (...args: any[]) => mockApiGet(...args),
  },
  errMsg: (e: any) => String(e?.message || e || "Error"),
}));

const mockStoryData = {
  club_id: "club-lagos-1",
  club_name: "Lagos Athletic FC",
  is_owner: true,
  philosophy: {
    key: "youth_dynasty",
    label: "Youth Dynasty",
    tagline: "Build from the academy up.",
    bonuses: { academy_boost: "+15%" },
  },
  philosophies_catalog: {
    youth_dynasty: {
      label: "Youth Dynasty",
      tagline: "Build from the academy up.",
      bonuses: { academy_boost: "+15%" },
    },
  },
  established_facts: {
    division_level: "division_1",
    prestige: 64,
    fans: 18500,
    matches_played: 12,
    trophies_count: 1,
    squad_count: 22,
  },
  chapters: [
    {
      chapter: "Chapter I — The Founding Charter",
      narrative: "Lagos Athletic FC was established with a mandate to build a durable football institution.",
    },
  ],
  timeline: [
    {
      id: "hist-1",
      type: "club_creation",
      category: "club_creation",
      title: "Lagos Athletic FC Founded",
      detail: "Club charter registered in GTEX.",
      is_milestone: true,
      at: "2026-11-14T10:00:00Z",
    },
  ],
  watchlist: [],
  supporters: {
    profile: {
      supporter_culture_label: "Passionate Working-Class Traditionalists",
      overall_sentiment: 72,
      confidence_in_owner: 70,
      confidence_in_manager: 74,
      loyalty_index: 81,
      matchday_enthusiasm: 76,
      accumulated_frustration: 5,
      consecutive_disappointments: 0,
      ticket_price_tier: "standard",
      active_protest_stage: "none",
      active_campaign_headline: null,
      attendance_modifier_pct: 6,
      owner_credibility_score: 78,
    },
    segments: [
      {
        segment_key: "loyal_lifelong",
        segment_name: "Loyal Lifelong Supporters",
        population_share_pct: 22,
        member_count: 4070,
        sentiment: 76,
        loyalty: 92,
        enthusiasm: 84,
        owner_approval: 75,
        scar_tissue: 4,
        status_label: "optimistic",
        expectations: { core_demand: "Protect club heritage and crest" },
        recent_memory: [{ headline: "Proud of recent academy debut", delta: 4 }],
      },
      {
        segment_key: "regular_matchgoing",
        segment_name: "Regular Match-Going Supporters",
        population_share_pct: 26,
        member_count: 4810,
        sentiment: 71,
        loyalty: 80,
        enthusiasm: 88,
        owner_approval: 72,
        scar_tissue: 5,
        status_label: "optimistic",
        expectations: { core_demand: "Committed home performances and fair ticket prices" },
        recent_memory: [{ headline: "Strong home turnout", delta: 3 }],
      },
    ],
    matchday_atmosphere: {
      dominant_mood: "electric_belief",
      crowd_intensity: 82,
      chant_volume_db: 98,
      stadium_ambience: "Roaring Fortress — Scarves Held High Across Every Tier",
      attendance_modifier_pct: 6,
      rivalry_intensity: 20,
      banners: ["BUILT IN LAGOS, FEARED ACROSS THE CONTINENT"],
      chants: ["Echoes from the North Stand"],
      visible_reactions: ["Scarves raised across all four stands at kickoff"],
    },
    recent_reactions: [
      {
        id: "sup-ev-1",
        world_day: 12,
        event_type: "academy_pride",
        headline: "Homegrown Prospect Promoted",
        summary: "Supporters celebrated the promotion of a local academy midfielder.",
        overall_sentiment_delta: 4,
        credibility_delta: 2,
        created_at: "2026-11-14T11:00:00Z",
      },
    ],
  },
  institutional_archive: {
    club_records: {
      biggest_victory: { score: "4-0", opponent: "Kano Stars" },
      record_signing: { player_name: "Jay-Jay Okocha II", fee_gtex: 18000 },
      all_time_top_scorer: { player_name: "Jay-Jay Okocha II", goals: 19 },
    },
    narrative_chapters: [
      {
        chapter_key: "founding_charter",
        era_label: "Day 1 · Institutional Genesis",
        title: "The Founding Charter of Lagos Athletic FC",
        narrative: "Lagos Athletic FC began its recorded journey in Division 1.",
      },
    ],
    season_archive: [
      {
        id: "sa-1",
        season_number: 1,
        season_label: "Season 1",
        competition_name: "GTEX Premier Division Champion",
        division_level: 1,
        final_position: 1,
        points: 78,
        played: 30,
        won: 24,
        drawn: 6,
        lost: 0,
        goals_for: 68,
        goals_against: 19,
        trophy_won: true,
        promotion_status: "title_winner",
        narrative_summary: "Finished #1 in GTEX Premier Division Champion.",
      },
    ],
    managerial_history: [
      {
        id: "mgr-ten-1",
        manager_name: "Tunde McPhill",
        tactical_style: "Attacking 4-3-3",
        status: "active",
        matches_managed: 12,
        wins: 9,
        draws: 2,
        losses: 1,
        win_rate_pct: 75,
        trophies_won: 1,
        departure_reason: null,
        tenure_summary: "Appointed First-Team Manager of Lagos Athletic FC.",
      },
    ],
    transfer_history: [
      {
        id: "tx-1",
        player_name: "Jay-Jay Okocha II",
        position: "CAM",
        age: 22,
        overall_rating: 86,
        direction: "arrival",
        transfer_type: "market_signing",
        counterparty_club_name: "Open Market",
        fee_gtex: 18000,
        is_record_signing: true,
        is_record_sale: false,
        narrative_note: "Club-record signing from Open Market for 18,000 GTX.",
      },
    ],
    academy_legacy: [
      {
        id: "grad-1",
        player_name: "Chinedu Eze",
        position: "CM",
        initial_rating: 72,
        current_rating: 75,
        potential_rating: 89,
        first_team_appearances: 5,
        first_team_goals: 2,
        debut_opponent_name: "Abuja United",
        status: "debuted",
      },
    ],
    historic_rivalries: [
      {
        id: "riv-1",
        rival_club_name: "Abuja United",
        rivalry_name: "The Federal Capital Derby",
        rivalry_tier: "fierce_rivalry",
        intensity_score: 68,
        matches_played: 4,
        wins: 3,
        draws: 1,
        losses: 0,
        goals_for: 9,
        goals_against: 3,
      },
    ],
    timeline: [
      {
        id: "hist-1",
        category: "club_creation",
        event_type: "club_founded",
        title: "Lagos Athletic FC Founded",
        narrative_summary: "Club charter registered in GTEX.",
        season_number: 1,
        world_day: 1,
        is_major_milestone: true,
        created_at: "2026-11-14T10:00:00Z",
      },
    ],
  },
};

const mockMediaEcosystem = {
  club_name: "Lagos Athletic FC",
  media_standing: {
    public_reputation: 68,
    supporter_sentiment: 72,
    owner_credibility_score: 78,
    commercial_attractiveness_index: 70,
    sponsorship_interest_index: 69,
    leadership_pressure_index: 18,
    verified_count: 1,
    reported_count: 0,
    rumour_count: 1,
    opinion_count: 0,
  },
  outlets: [
    {
      outlet_key: "local_club_chronicle",
      outlet_name: "The Metropolitan Football Chronicle",
      journalist_name: "Tunde Adebayo",
      journalist_role: "Chief Club Beat Correspondent",
      editorial_focus: "local_club_reporting",
      credibility_tier: "tier_1_authoritative",
      credibility_score: 91,
    },
    {
      outlet_key: "transfer_insider_desk",
      outlet_name: "Transfer Market Insider Wire",
      journalist_name: "Fabrizio Moretti",
      journalist_role: "Recruitment & Market Specialist",
      editorial_focus: "transfer_reporting",
      credibility_tier: "tier_2_reliable",
      credibility_score: 84,
    },
  ],
  stories: [
    {
      id: "story-verified-1",
      outlet_key: "local_club_chronicle",
      outlet_name: "The Metropolitan Football Chronicle",
      journalist_name: "Tunde Adebayo",
      editorial_focus: "local_club_reporting",
      story_type: "match_report",
      classification: "verified_event",
      credibility_score: 91,
      is_confirmed_fact: true,
      headline: "Lagos Athletic FC secure emphatic 4-0 win over Kano Stars",
      subheadline: "Verified Full-Time Match Report",
      body: "Lagos Athletic FC defeated Kano Stars 4-0 in front of a vibrant home crowd.",
      consequences: {
        reputation_delta: 2,
        supporter_sentiment_delta: 4,
      },
      owner_response: null,
      created_at: "2026-11-14T12:00:00Z",
    },
    {
      id: "story-rumour-1",
      outlet_key: "transfer_insider_desk",
      outlet_name: "Transfer Market Insider Wire",
      journalist_name: "Fabrizio Moretti",
      editorial_focus: "transfer_reporting",
      story_type: "transfer_coverage",
      classification: "rumour",
      credibility_score: 84,
      is_confirmed_fact: false,
      headline: "RUMOUR: Lagos Athletic FC scouting Victor Osimhen",
      subheadline: "Unconfirmed scouting link — no formal transfer agreed",
      body: "[UNCONFIRMED RUMOUR — NOT A CONFIRMED TRANSFER] Sources suggest scouting interest.",
      consequences: {
        reputation_delta: 0,
        supporter_sentiment_delta: 1,
      },
      owner_response: null,
      created_at: "2026-11-14T12:30:00Z",
    },
  ],
};

jest.mock("@/lib/owner", () => ({
  fmt: (v: any) => String(v ?? 0),
  label: (s: any) => String(s ?? ""),
  useActiveClub: () => ({ active: { club_id: "club-lagos-1", club_name: "Lagos Athletic FC" } }),
  useClub: () => ({ data: { state: { club_name: "Lagos Athletic FC", prestige: 64 } } }),
  useClubStory: () => ({ data: mockStoryData, isLoading: false }),
  useClubInstitutionalPulse: () => ({
    data: {
      club_id: "club-lagos-1",
      world_day: 14,
      reputation_dimensions: {
        overall_reputation: 68,
        supporter_sentiment: 72,
        owner_credibility: 78,
        leadership_pressure: 18,
      },
      supporters: {
        overall_sentiment: 72,
        active_protest_stage: "none",
        matchday_atmosphere_rating: 78,
      },
      media_standing: mockMediaEcosystem.media_standing,
      unified_timeline: [],
    },
    isLoading: false,
  }),
  useNewsroom: () => ({
    data: {
      articles: [],
      established_facts: {
        club_name: "Lagos Athletic FC",
        division_level: "division_1",
        prestige: 64,
        fans: 18500,
        matches_played: 12,
        trophies_count: 1,
      },
    },
    isLoading: false,
    refetch: () => {},
  }),
  useRefreshOwner: () => mockRefresh,
}));

describe("Supporter, Media & Permanent Club History UI", () => {
  let container: HTMLDivElement;
  let root: Root;
  let queryClient: QueryClient;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    mockApiPost.mockReset();
    mockApiGet.mockReset();
    mockApiGet.mockResolvedValue({ data: mockMediaEcosystem });
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  test("ClubStory switches between Supporters & Atmosphere and Institutional Archive tabs", async () => {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ClubStory />
        </QueryClientProvider>
      );
    });

    // Click Supporters & Atmosphere tab
    const supportersTabBtn = container.querySelector('[data-testid="tab-supporters"]') as HTMLButtonElement;
    expect(supportersTabBtn).not.toBeNull();
    await act(async () => {
      supportersTabBtn.click();
    });

    const supportersContent = container.querySelector('[data-testid="supporters-tab-content"]');
    expect(supportersContent).not.toBeNull();
    expect(supportersContent?.textContent).toContain("Loyal Lifelong Supporters");
    expect(supportersContent?.textContent).toContain("Regular Match-Going Supporters");
    expect(supportersContent?.textContent).toContain("BUILT IN LAGOS, FEARED ACROSS THE CONTINENT");

    // Click Institutional Archive tab
    const archiveTabBtn = container.querySelector('[data-testid="tab-archive"]') as HTMLButtonElement;
    expect(archiveTabBtn).not.toBeNull();
    await act(async () => {
      archiveTabBtn.click();
    });

    const archiveContent = container.querySelector('[data-testid="archive-tab-content"]');
    expect(archiveContent).not.toBeNull();
    expect(archiveContent?.textContent).toContain("Tunde McPhill");
    expect(archiveContent?.textContent).toContain("Jay-Jay Okocha II");
    expect(archiveContent?.textContent).toContain("Chinedu Eze");
    expect(archiveContent?.textContent).toContain("Abuja United");
    expect(archiveContent?.textContent).toContain("GTEX Premier Division Champion");
  });

  test("Newsroom renders Living Football Media Ecosystem and distinguishes verified facts from rumours", async () => {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <Newsroom />
        </QueryClientProvider>
      );
    });

    const mediaPanel = container.querySelector('[data-testid="club-media-ecosystem-panel"]');
    expect(mediaPanel).not.toBeNull();
    expect(mediaPanel?.textContent).toContain("The Metropolitan Football Chronicle");
    expect(mediaPanel?.textContent).toContain("Transfer Market Insider Wire");
    expect(mediaPanel?.textContent).toContain("UNCONFIRMED RUMOUR (NOT FACT)");
    expect(mediaPanel?.textContent).toContain("RUMOUR: Lagos Athletic FC scouting Victor Osimhen");
  });
});
