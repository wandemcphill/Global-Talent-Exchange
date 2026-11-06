declare const describe: any;
declare const test: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { api } from "@/lib/api";
import MyClubs from "./MyClubs";

var mockNavigate = jest.fn();
var mockToastSuccess = jest.fn();
var mockToastError = jest.fn();
var mockSelect = jest.fn();
var mockRefetchStaff = jest.fn();
var mockRefetchNews = jest.fn();
var mockRefreshOwner = jest.fn();

jest.mock("react-router-dom", () => {
  const ReactModule = require("react");
  return {
    useNavigate: () => mockNavigate,
    Link: ({ to, children, ...props }: any) =>
      ReactModule.createElement("a", { href: typeof to === "string" ? to : "#", ...props }, children),
  };
});

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

jest.mock("sonner", () => ({
  toast: {
    success: (...args: any[]) => mockToastSuccess(...args),
    error: (...args: any[]) => mockToastError(...args),
  },
}));

const mockClub = {
  club_id: "c-100",
  club_name: "Lagos Athletic FC",
  slug: "lagos-athletic",
  short_name: "Lagos Ath",
  home_venue_name: "Cathedral of Excellence",
  description: "A premier football powerhouse in the heart of West Africa.",
  primary_color: "#0F766E",
  secondary_color: "#F8FAFC",
  accent_color: "#F59E0B",
  visibility: "public",
  value: 45000000,
  cash: 12500000,
  stage: "active",
  ownership_group: { label: "Atlantic Football Group" },
  health: {
    fans: 240000,
    prestige: 78,
    squad_size: 26,
  },
  manager: { name: "Finidi George" },
  facilities: {
    stadium: { level: 3, next_cost: 50000 },
    training: { level: 4, next_cost: 35000 },
    academy: { level: 3, next_cost: 40000 },
    medical: { level: 3, next_cost: 25000 },
    commercial: { level: 2, next_cost: 20000 },
  },
  economy: {
    cash_gtex: 12500000,
    pending_payouts: 150000,
  },
  sponsors: [
    { id: "sp-1", sponsor: "Apex Global Telecom", slot: "Front of Shirt", matches_remaining: 12, club_share: 5000 },
  ],
  disclosures: [],
};

const mockStaffData = {
  club_id: "c-100",
  appointed: {
    first_team_manager: {
      name: "Finidi George",
      tactical_flexibility: 82,
      personal_agenda: "Win Silverware Now & Demand Tactical Autonomy",
      secret_trait: "Touchline Firebrand",
      poaching_risk: "low",
    },
    general_manager: {
      name: "Sunday Oliseh",
      tactical_flexibility: 84,
      personal_agenda: "Build a Self-Sustaining Trading & Commercial Empire",
      secret_trait: "Ruthless Release-Clause Shark",
      poaching_risk: "low",
    },
    head_of_youth_development: {
      name: "Emmanuel Amuneke",
      tactical_flexibility: 86,
      personal_agenda: "Golden Generation Purist (50%+ Academy XI)",
      secret_trait: "Favorite-Son Wonderkid Bias",
      poaching_risk: "low",
    },
    chief_scout: null,
    medical_director: null,
  },
  staff_effects: {
    tactical_synergy: 14,
    youth_multiplier: 18,
    recovery_bonus: 12,
    commercial_pull: 10,
  },
  delegation_policy: {
    mode: "balanced",
    gm_transfer_autonomy: true,
    hoyd_youth_contracts: true,
    manager_tactics_autonomy: true,
  },
  candidates: [
    {
      id: "cand-cs-1",
      staff_id: "cand-cs-1",
      name: "Nwankwo Kanu",
      role: "chief_scout",
      tactical_flexibility: 85,
      signing_fee_gtex: 3000,
    },
  ],
};

jest.mock("@/lib/owner", () => ({
  fmt: (n: any) => String(n || 0),
  label: (s: string) => (s || "").replace(/_/g, " "),
  useActiveClub: () => ({
    clubs: [{ club_id: "c-100", club_name: "Lagos Athletic FC" }],
    active: { club_id: "c-100", club_name: "Lagos Athletic FC" },
    select: (...args: any[]) => mockSelect(...args),
  }),
  useControlCenter: () => ({
    data: { max_clubs: 3 },
  }),
  useClub: () => ({
    data: mockClub,
    isLoading: false,
  }),
  useClubStaff: () => ({
    data: mockStaffData,
    isLoading: false,
    refetch: (...args: any[]) => mockRefetchStaff(...args),
  }),
  useClubShowroom: () => ({
    data: { catalog: [], owned_assets: [] },
    isLoading: false,
  }),
  useNewsroom: () => ({
    data: { items: [{ id: "news-1", headline: "Pre-Season Tour Approved", summary: "Board signs off on training camp.", created_at: "2026-06-01" }] },
    isLoading: false,
    refetch: (...args: any[]) => mockRefetchNews(...args),
  }),
  useRefreshOwner: () => () => mockRefreshOwner(),
}));

describe("MyClubs HQ Component", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    jest.spyOn(api, "get").mockResolvedValue({ data: { leaderboard: [] } });
    jest.spyOn(api, "put").mockResolvedValue({ data: {} });
    jest.spyOn(api, "patch").mockResolvedValue({ data: {} });
    jest.spyOn(api, "post").mockResolvedValue({ data: {} });
  });

  afterEach(async () => {
    await act(async () => {
      root.unmount();
    });
    container.remove();
  });

  test("renders Club HQ summary, navigation tabs, and operational overview", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <MyClubs />
        </QueryClientProvider>,
      );
    });

    expect(container.querySelector('[data-testid="my-clubs-page"]')).not.toBeNull();
    expect(container.textContent).toContain("Lagos Athletic FC");
    expect(container.textContent).toContain("Finidi George");

    expect(container.querySelector('[data-testid="tab-overview"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="tab-organisation"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="tab-delegation"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="tab-facilities"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="tab-academy"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="tab-treasury"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="tab-identity"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="tab-news"]')).not.toBeNull();

    expect(container.textContent).toContain("Cathedral of Excellence");
    expect(container.textContent).toContain("Active Regen Pipeline");
    expect(container.textContent).toContain("Command Action Launcher");
  });

  test("renders Organisation & Staff panel with executive hierarchy", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <MyClubs />
        </QueryClientProvider>,
      );
    });

    const orgTab = container.querySelector('[data-testid="tab-organisation"]') as HTMLButtonElement;
    await act(async () => {
      orgTab.click();
    });

    expect(container.querySelector('[data-testid="organisational-structure-panel"]')).not.toBeNull();
    expect(container.textContent).toContain("Finidi George");
    expect(container.textContent).toContain("Sunday Oliseh");
    expect(container.textContent).toContain("Emmanuel Amuneke");
    expect(container.textContent).toContain("confidential boardroom records");
  });

  test("renders Delegation & Authority panel with presets and toggles", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <MyClubs />
        </QueryClientProvider>,
      );
    });

    const delTab = container.querySelector('[data-testid="tab-delegation"]') as HTMLButtonElement;
    await act(async () => {
      delTab.click();
    });

    expect(container.querySelector('[data-testid="delegation-authority-panel"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="preset-hands-on"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="preset-balanced"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="preset-executive-led"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="toggle-gm-autonomy"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="toggle-hoyd-autonomy"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="toggle-manager-autonomy"]')).not.toBeNull();
  });

  test("renders Club Identity & Public Profile Publishing panel", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <MyClubs />
        </QueryClientProvider>,
      );
    });

    const idTab = container.querySelector('[data-testid="tab-identity"]') as HTMLButtonElement;
    await act(async () => {
      idTab.click();
    });

    expect(container.querySelector('[data-testid="identity-publishing-panel"]')).not.toBeNull();
    expect(container.textContent).toContain("PUBLIC PROFILE ACTIVE");
    expect(container.querySelector('[data-testid="toggle-visibility-button"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="copy-public-profile-url-button"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="view-public-profile-link"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="save-identity-button"]')).not.toBeNull();
  });
});
