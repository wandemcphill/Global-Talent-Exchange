declare const describe: any;
declare const test: any;
declare const it: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { MarketTableView } from "./MarketTableView";
import { SquadCardGridView } from "./SquadCardGridView";
import { CompetitionsTableView } from "./CompetitionsTableView";
import { ScoutingTableView } from "./ScoutingTableView";
import { ScoutingDevelopmentView } from "./ScoutingDevelopmentView";
import { PlayerStatisticalProfileView } from "./PlayerStatisticalProfileView";

jest.mock("react-router-dom", () => {
  const ReactModule = require("react");
  return {
    Link: ({ to, children, ...props }: any) =>
      ReactModule.createElement("a", {
        href: typeof to === "string" ? to : "#",
        ...props,
      }, children),
  };
});

describe("Layer 3 — Football Module Views Component Tests", () => {
  let container: HTMLDivElement;
  let root: Root | null = null;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    if (root) {
      act(() => {
        root?.unmount();
      });
      root = null;
    }
    if (container && container.parentNode) {
      container.parentNode.removeChild(container);
    }
  });

  const samplePlayers = [
    {
      player_id: "p-101",
      canonical_display_name: "Victor Osimhen",
      position: "forward",
      nationality: "Nigeria",
      age: 26,
      overall_rating: 89,
      current_club_name: "Galatasaray",
      real_player_tier: "marquee",
      quote: { price: 14500, rating: 89 },
    },
    {
      player_id: "p-102",
      canonical_display_name: "Diego Maradona",
      position: "midfielder",
      nationality: "Argentina",
      age: 32,
      overall_rating: 94,
      current_club_name: "Napoli",
      real_player_tier: "legend",
      quote: { price: 85000, rating: 94 },
    },
  ];

  const sampleScoutingItems = [
    {
      id: "prospect-1",
      name: "Tariq Lamptey Regen",
      rating: 74,
      potential: 91,
      position: "DEF",
      age: 18,
      nationality: "Ghana",
      club: "GTEX Academy",
      generation: 2,
      archetype: "Inverted Wingback",
      serial: "GTEX-GEN2-0042",
      price: 1200,
      rawItem: {},
    },
    {
      id: "prospect-2",
      name: "Lucas Silva",
      rating: 70,
      potential: 82,
      position: "MID",
      age: 19,
      nationality: "Brazil",
      club: "Santos Academy",
      generation: 1,
      archetype: "Deep Lying Playmaker",
      serial: "GTEX-GEN1-0199",
      price: 650,
      rawItem: {},
    },
  ];

  it("renders MarketTableView with correct columns and player rows", () => {
    root = createRoot(container);
    act(() => {
      root?.render(
        <MarketTableView
          players={samplePlayers}
          signedRefs={["p-101"]}
          clubId="club-1"
          clubCash={200000}
          onSign={() => {}}
          onOpenDossier={() => {}}
        />
      );
    });

    expect(container.querySelector('[data-testid="market-fm-table-view"]')).toBeTruthy();
    expect(container.textContent).toContain("Victor Osimhen");
    expect(container.textContent).toContain("Diego Maradona");
    expect(container.textContent).toContain("FWD");
    expect(container.textContent).toContain("MID");
    expect(container.textContent).toContain("In Squad");
  });

  it("renders SquadCardGridView with player cards", () => {
    root = createRoot(container);
    act(() => {
      root?.render(
        <SquadCardGridView
          squad={samplePlayers}
          onSelectPlayer={() => {}}
          targetPlayerId="p-101"
        />
      );
    });

    expect(container.querySelector('[data-testid="squad-card-grid-view"]')).toBeTruthy();
    expect(container.textContent).toContain("Victor Osimhen");
    expect(container.textContent).toContain("Diego Maradona");
  });

  it("renders CompetitionsTableView with tournament data", () => {
    const sampleComps = [
      {
        id: "comp-1",
        name: "Lagos Premier Derby",
        host_type: "gtex",
        format: "knockout",
        status: "open",
        entry_fee: 500,
        prize_pool: 2000,
        entrants: 4,
        max_clubs: 8,
      },
    ];

    root = createRoot(container);
    act(() => {
      root?.render(
        <CompetitionsTableView competitions={sampleComps} clubId="club-1" />
      );
    });

    expect(container.querySelector('[data-testid="competitions-table-view"]')).toBeTruthy();
    expect(container.textContent).toContain("Lagos Premier Derby");
    expect(container.textContent).toContain("GTEX");
    expect(container.textContent).toContain("knockout");
  });

  it("renders ScoutingTableView with high-density database metrics", () => {
    root = createRoot(container);
    act(() => {
      root?.render(
        <ScoutingTableView
          items={sampleScoutingItems}
          onSelectPlayer={() => {}}
          onAddToWatchlist={() => {}}
        />
      );
    });

    expect(container.querySelector('[data-testid="scouting-table-view"]')).toBeTruthy();
    expect(container.textContent).toContain("Tariq Lamptey Regen");
    expect(container.textContent).toContain("Lucas Silva");
    expect(container.textContent).toContain("Inverted Wingback");
    expect(container.textContent).toContain("1,200 GX");
    expect(container.textContent).toContain("Gen 2");
  });

  it("renders ScoutingDevelopmentView with wonderkid and ascendant cohorts", () => {
    root = createRoot(container);
    act(() => {
      root?.render(
        <ScoutingDevelopmentView
          items={sampleScoutingItems}
          onSelectPlayer={() => {}}
        />
      );
    });

    expect(container.querySelector('[data-testid="scouting-development-view"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="cohort-tier-1-·-elite-wonderkids"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="cohort-tier-2-·-prime-ascendants"]')).toBeTruthy();
    expect(container.textContent).toContain("Tariq Lamptey Regen");
    expect(container.textContent).toContain("91 POT");
  });

  it("renders PlayerStatisticalProfileView with FM attribute categories", () => {
    root = createRoot(container);
    act(() => {
      root?.render(
        <PlayerStatisticalProfileView
          player={{ archetype: "Clinical Finisher" }}
          rating={88}
          potential={94}
          position="FWD"
          age={22}
          nationality="Nigeria"
          club="Napoli"
          careerEntries={[
            { season: "2025/26", club_name: "Napoli", appearances: 34, goals: 28, assists: 9, average_rating: 8.12 },
          ]}
        />
      );
    });

    expect(container.querySelector('[data-testid="player-statistical-profile"]')).toBeTruthy();
    expect(container.textContent).toContain("Technical");
    expect(container.textContent).toContain("Mental");
    expect(container.textContent).toContain("Physical");
    expect(container.textContent).toContain("Finishing");
    expect(container.textContent).toContain("Composure");
    expect(container.textContent).toContain("Pace");
    expect(container.textContent).toContain("Historical Performance Log");
    expect(container.textContent).toContain("8.12");
  });
});
