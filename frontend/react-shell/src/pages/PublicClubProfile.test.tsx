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
import PublicClubProfile from "./PublicClubProfile";

var mockToastSuccess = jest.fn();
var mockToastError = jest.fn();

jest.mock("react-router-dom", () => {
  const ReactModule = require("react");
  return {
    useParams: () => ({ clubSlug: "lagos-athletic" }),
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

const mockPublicDossier = {
  club: {
    id: "c-100",
    name: "Lagos Athletic FC",
    short_name: "Lagos Ath",
    slug: "lagos-athletic",
    description: "A premier football powerhouse in the heart of West Africa.",
    crest_url: "https://example.com/crest.png",
    primary_color: "#0F766E",
    secondary_color: "#F8FAFC",
    accent_color: "#F59E0B",
    country_code: "NG",
    region_name: "Lagos State",
    city_name: "Lagos",
    founded_year: 2021,
    home_venue_name: "Cathedral of Excellence",
  },
  owner: {
    id: "owner-1",
    display_name: "Adekunle Bello",
    title: "Executive Chairman",
    persona: "visionary_tycoon",
    club_count: 2,
    net_worth_tier: "Tier 1: Global Superclub",
    reputation_score: 95,
    public_clubs: [],
    luxury_asset_count: 3,
  },
  stadium: {
    name: "Cathedral of Excellence",
    level: 3,
    capacity: 45000,
    theme_key: "cathedral",
    pitch: "Hybrid Grass",
  },
  facilities: {
    training_level: 4,
    academy_level: 4,
    medical_level: 3,
    branding_level: 3,
    youth_recruitment_level: 3,
  },
  academy: {
    level: 4,
    capacity: 24,
    prospect_count: 14,
    prospects: [
      { id: "p-rec-1", name: "Ibrahim Sani", position: "AM", age: 17, rating: 74, potential: 88, is_regen: true },
    ],
  },
  squad: {
    player_count: 5,
    best_player: {
      id: "p-best-1",
      name: "Victor Osimhen",
      position: "ST",
      age: 26,
      rating: 88,
      potential: 91,
      is_regen: false,
    },
    most_promising_player: {
      id: "p-prom-1",
      name: "Tunde Adeyemi",
      position: "RW",
      age: 18,
      rating: 76,
      potential: 92,
      is_regen: true,
    },
    players: [
      { id: "s-1", name: "Victor Osimhen", position: "ST", squad_number: 9, nationality: "NG", age: 26, rating: 88, is_regen: false },
      { id: "s-2", name: "Tunde Adeyemi", position: "RW", squad_number: 11, nationality: "NG", age: 18, rating: 76, is_regen: true },
      { id: "s-3", name: "Wilfred Ndidi", position: "DM", squad_number: 4, nationality: "NG", age: 28, rating: 84, is_regen: false },
      { id: "s-4", name: "Stanley Nwabali", position: "GK", squad_number: 1, nationality: "NG", age: 27, rating: 81, is_regen: false },
      { id: "s-5", name: "Calvin Bassey", position: "CB", squad_number: 3, nationality: "NG", age: 25, rating: 82, is_regen: false },
    ],
  },
  staff: [
    { role: "manager", title: "Manager", name: "Finidi George", appointed: true, rating: 82 },
    { role: "general_manager", title: "General Manager", name: "Sunday Oliseh", appointed: true, rating: 84 },
    { role: "head_of_youth_development", title: "Head of Youth Development", name: "Emmanuel Amuneke", appointed: true, rating: 86 },
    { role: "coach", title: "First-Team Coach", name: "Daniel Amokachi", appointed: true, rating: 80 },
  ],
  coach_buses: [
    {
      id: "bus-1",
      name: "Mercedez Travego Elite",
      model: "Travego VIP Coach",
      prestige_tier: 1,
      image_url: "https://example.com/bus.png",
      acquired_at: "2024-03-01",
    },
  ],
  trophies: [
    { id: "t-1", name: "GTEX Super Cup", season: "2025/26", position: 1, icon_url: "https://example.com/cup.png" },
  ],
};

describe("PublicClubProfile Component", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    jest.spyOn(api, "get").mockReset();
  });

  afterEach(async () => {
    await act(async () => {
      root.unmount();
    });
    container.remove();
  });

  test("renders all 11 public club profile sections and privacy disclaimer", async () => {
    (api.get as any).mockResolvedValue({ data: mockPublicDossier });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <PublicClubProfile />
        </QueryClientProvider>,
      );
    });

    // Allow query promise to resolve in microtask queue
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(container.querySelector('[data-testid="public-club-profile-view"]')).not.toBeNull();

    // 1. Identity & Hero
    expect(container.textContent).toContain("Lagos Athletic FC");
    expect(container.textContent).toContain("A premier football powerhouse");
    expect(container.textContent).toContain("Founded 2021");

    // 2. Privacy Disclaimer
    expect(container.textContent).toContain("Internal wages, ledgers and confidential notes remain sealed");

    // 3. Stadium information
    expect(container.textContent).toContain("Cathedral of Excellence");
    expect(container.textContent).toContain("45,000");

    // 4. Standout player cards
    expect(container.textContent).toContain("Best Player");
    expect(container.textContent).toContain("MARQUEE");
    expect(container.textContent).toContain("Victor Osimhen");
    expect(container.textContent).toContain("Most Promising");
    expect(container.textContent).toContain("PROSPECT");
    expect(container.textContent).toContain("Tunde Adeyemi");

    // 5. Public squad roster
    expect(container.textContent).toContain("Stanley Nwabali");
    expect(container.textContent).toContain("Wilfred Ndidi");
    expect(container.textContent).toContain("Calvin Bassey");

    // 6. Club leadership & executive staff
    expect(container.textContent).toContain("Finidi George");
    expect(container.textContent).toContain("Sunday Oliseh");
    expect(container.textContent).toContain("Emmanuel Amuneke");
    expect(container.textContent).toContain("Daniel Amokachi");

    // 7. Academy & performance complex
    expect(container.textContent).toContain("Academy & Performance Facilities");
    expect(container.textContent).toContain("Youth Development Complex");
    expect(container.textContent).toContain("Active In Pipeline: 14 prospects");

    // 8. Transport & coach fleet
    expect(container.textContent).toContain("Club Coach Fleet & Assets");
    expect(container.textContent).toContain("Mercedez Travego Elite");

    // 9. Owner spotlight
    expect(container.textContent).toContain("Adekunle Bello");
    expect(container.textContent).toContain("Controls 2 verified GTEX clubs");

    // 10. Silverware & honours
    expect(container.textContent).toContain("Silverware Cabinet");
    expect(container.textContent).toContain("GTEX Super Cup");

    // 11. 3D Preview Stage
    expect(container.querySelector('[data-testid="mock-cinema-3d-stage"]')).not.toBeNull();
  });

  test("renders 404 unlisted state when profile does not exist", async () => {
    (api.get as any).mockRejectedValue({
      response: { status: 404, data: { detail: "Club profile not found" } },
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <PublicClubProfile />
        </QueryClientProvider>,
      );
    });

    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(container.textContent).toContain("This public profile isn't published");
    expect(container.textContent).toContain("This club may be set to private by its owner");
  });
});
