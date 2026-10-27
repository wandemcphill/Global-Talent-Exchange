declare const describe: any;
declare const test: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PlayerDossier } from "@/components/gtex/PlayerDossier";
import { api } from "@/lib/api";

(global as any).IS_REACT_ACT_ENVIRONMENT = true;

jest.mock("@/lib/owner", () => ({
  useActiveClub: () => ({
    active: {
      club_id: "test-club-001",
      club_name: "Lagos Sporting Club",
      transfer_budget: 150000,
      wage_budget: 8000,
    },
  }),
  fmt: (n: any) => String(n ?? 0),
  label: (s: string) => String(s || "").replace(/_/g, " "),
}));

describe("Regen Contract Journey - React Dossier & Pipeline Suite", () => {
  let container: HTMLDivElement;
  let root: Root;
  let queryClient: QueryClient;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    // Mock API requests
    jest.spyOn(api, "get").mockImplementation((url: string, config?: any) => {
      if (url.includes("/regen-universe/player/canonical-regen-101")) {
        return Promise.resolve({
          data: {
            player: {
              id: "canonical-regen-101",
              name: "Oluwaseun Adeyemi",
              position: "FWD",
              nationality: "Nigeria",
              age: 18,
              current_rating: 74,
              potential: 91,
              club_id: "academy-club-id",
              current_club_name: "Eko Talent Academy",
            },
            card: {
              generation: 1,
              archetype: "Electric Winger",
              serial_number: "GTX-NG-2026-0091",
            },
            prestige: {
              total_awards: 2,
              peak_rank: 4,
              legacy_score: 87.5,
            },
          },
        });
      }

      if (url.includes("/regen-universe/players/canonical-regen-101/timeline")) {
        return Promise.resolve({
          data: {
            items: [
              {
                id: "story-1",
                title: "Academy Breakthrough",
                summary: "Scored 14 goals in national youth tournament.",
                occurred_at: "2026-05-12T10:00:00Z",
              },
            ],
          },
        });
      }

      if (url.includes("/players/canonical-regen-101/career")) {
        return Promise.resolve({
          data: [
            {
              id: "career-1",
              season_number: 1,
              club_name: "Eko Talent Academy",
              matches: 18,
              goals: 14,
              average_rating: 7.8,
            },
          ],
        });
      }

      if (url.includes("/scout/reports/canonical-regen-101")) {
        return Promise.resolve({
          data: {
            player_id: "canonical-regen-101",
            accuracy: 94,
            rarity_tier: "wonderkid",
            summary_text: "Explosive pace and elite finishing instinct.",
            potential_range: { min: 89, max: 94 },
          },
        });
      }

      if (url.includes("/transfer-market/watchlist")) {
        return Promise.resolve({
          data: [
            {
              id: "watch-1",
              player_id: "canonical-regen-101",
              source: "scouting_dossier",
            },
          ],
        });
      }

      if (url.includes("/transfer-hub/listings")) {
        return Promise.resolve({
          data: [
            {
              id: "listing-101",
              player_id: "canonical-regen-101",
              status: "open",
              base_price: 65000,
            },
          ],
        });
      }

      if (url.includes("/transfer-hub/offers")) {
        return Promise.resolve({
          data: [
            {
              id: "offer-101",
              listing_id: "listing-101",
              status: "open",
              cash_amount: 65000,
            },
          ],
        });
      }

      if (url.includes("/transfer-market/negotiations")) {
        return Promise.resolve({
          data: [
            {
              id: "neg-101",
              listing_id: "listing-101",
              player_id: "canonical-regen-101",
              status: "awaiting_contract_offer",
              bidder_club_id: "test-club-001",
              selling_club_id: "academy-club-id",
              contract_years: 3,
            },
          ],
        });
      }

      if (url.includes("/squad-registration")) {
        return Promise.resolve({
          data: {
            id: "reg-1",
            club_id: "test-club-001",
            status: "draft",
            players: [],
          },
        });
      }

      return Promise.reject(new Error(`Unhandled GET ${url}`));
    });
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    queryClient.clear();
    container.remove();
    jest.restoreAllMocks();
  });

  async function renderDossier(playerId: string = "canonical-regen-101") {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <PlayerDossier
            playerId={playerId}
            onClose={() => {}}
            onMakeOffer={() => {}}
            onAddToWatchlist={() => {}}
          />
        </QueryClientProvider>,
      );
    });

    for (let i = 0; i < 5; i += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    }
  }

  test("carries canonical player ID and displays player identity, cards, and dossier header", async () => {
    await renderDossier();

    expect(container.textContent).toContain("Oluwaseun Adeyemi");
    expect(container.textContent).toContain("Canonical ID: canonical-regen-101");
    expect(container.textContent).toContain("Official Player Dossier");
    expect(container.textContent).toContain("Gen 1-3 Verified Regen");
  });

  test("renders the connected 6-stage journey pipeline with honest intermediate states", async () => {
    await renderDossier();

    const stepper = container.querySelector('[data-testid="dossier-journey-stepper"]');
    expect(stepper).not.toBeNull();

    // 1. Scout report is done
    expect(container.querySelector('[data-testid="journey-step-report"]')).not.toBeNull();
    expect(container.textContent).toContain("Explosive pace and elite finishing instinct");

    // 2. Shortlist is done
    expect(container.querySelector('[data-testid="journey-step-watchlist"]')).not.toBeNull();
    expect(container.textContent).toContain("Saved by your club (source: scouting_dossier)");

    // 3. Market listing is open
    expect(container.querySelector('[data-testid="journey-step-listing"]')).not.toBeNull();
    expect(container.textContent).toContain("Open listing asking 65,000 GTX");

    // 4. Offer is active/open
    expect(container.querySelector('[data-testid="journey-step-offer"]')).not.toBeNull();
    expect(container.textContent).toContain("Offered: Sent. Waiting for the selling club to respond.");

    // 5. Contract negotiation is awaiting contract terms
    expect(container.querySelector('[data-testid="journey-step-contract"]')).not.toBeNull();
    expect(container.textContent).toContain("Awaiting contract terms");

    // 6. Registration is pending because the player has not been confirmed in squad registration!
    expect(container.querySelector('[data-testid="journey-step-registration"]')).not.toBeNull();
    expect(container.textContent).toContain("Available once the player has joined your club");
  });

  test("renders official career history participation table and chronological narrative", async () => {
    await renderDossier();

    expect(container.textContent).toContain("Career Participation Record");
    expect(container.textContent).toContain("Eko Talent Academy");
    expect(container.textContent).toContain("Academy Breakthrough");
    expect(container.textContent).toContain("Scored 14 goals in national youth tournament");
  });
});
