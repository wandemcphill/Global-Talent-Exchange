declare const describe: any;
declare const it: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;

import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { FormationInventoryAdvert, LegendInventoryReel } from "./InventoryAdvert";
import {
  ShowcasePlayer,
  buildFormationSheet,
  legendWindow,
  mapMarketPlayer,
} from "./inventoryAdvertModel";

jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...rest }: any) => (
    <a href={to} {...rest}>
      {children}
    </a>
  ),
}));

function player(id: string, name: string, position: string, kind: ShowcasePlayer["kind"]): ShowcasePlayer {
  return {
    id,
    name,
    position,
    rating: kind === "legend" ? 94 : kind === "regen" ? 78 : 88,
    image: null,
    nationality: "Nigeria",
    club: "GTEX",
    age: 28,
    kind,
    priority: (kind === "legend" ? 400 : kind === "regen" ? 80 : 250) + (kind === "legend" ? 94 : kind === "regen" ? 78 : 88),
  };
}

function squad(): ShowcasePlayer[] {
  const rows: ShowcasePlayer[] = [];
  const lines = [
    ["GK", "Goalkeeper"],
    ["DEF", "Defender"],
    ["MID", "Midfielder"],
    ["FWD", "Forward"],
  ] as const;
  const kinds: ShowcasePlayer["kind"][] = ["legend", "regen", "active"];
  lines.forEach(([code, position]) => {
    kinds.forEach((kind, kindIndex) => {
      for (let copy = 0; copy < 4; copy += 1) {
        rows.push(player(`${code}-${kind}-${copy}`, `${kind} ${code} ${kindIndex}${copy}`, position, kind));
      }
    });
  });
  return rows;
}

describe("inventory advert", () => {
  it("rotates three legendary cards and files archived duplicates out", () => {
    const legends = squad().filter((item) => item.kind === "legend" && item.position === "Forward");
    expect(legendWindow(legends, 0).map((item) => item.id)).toEqual(["FWD-legend-0", "FWD-legend-1", "FWD-legend-2"]);
    expect(legendWindow(legends, 1).map((item) => item.id)).toEqual(["FWD-legend-3", "FWD-legend-0", "FWD-legend-1"]);
    expect(mapMarketPlayer({ player_id: "dup", player_name: "Copy", real_player_tier: "archived_duplicate" })).toBeNull();
    expect(mapMarketPlayer({ player_id: "pele", player_name: "Pelé", real_player_tier: "legend", rating: 98 })?.kind).toBe(
      "legend",
    );
  });

  it("builds a faced formation and bench under a named tactician", () => {
    const first = buildFormationSheet(squad(), 0);
    const second = buildFormationSheet(squad(), 1);
    expect(first).not.toBeNull();
    expect(first!.manager.name).toBe("Sir Alex Ferguson");
    expect(first!.manager.formation).toBe("4-4-2");
    expect(first!.xi).toHaveLength(11);
    expect(first!.bench.length).toBeGreaterThanOrEqual(5);
    const kinds = new Set(first!.xi.map((row) => row.player.kind));
    expect(kinds.has("legend")).toBe(true);
    expect(kinds.has("regen")).toBe(true);
    expect(kinds.has("active")).toBe(true);
    expect(second!.manager.name).toBe("Arsène Wenger");
    expect(second!.xi.map((row) => row.player.id).join()).not.toBe(first!.xi.map((row) => row.player.id).join());
  });

  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  it("shows three legendary cards and a pitch with faces and a bench", () => {
    const players = squad();
    act(() => {
      root.render(
        <div>
          <LegendInventoryReel players={players} context="signup" />
          <FormationInventoryAdvert players={players} />
        </div>,
      );
    });
    expect(container.querySelectorAll('[data-testid="legend-inventory-card"]').length).toBe(3);
    expect(container.querySelector('[data-testid="legend-inventory-reel"]')?.textContent).toContain("ICON · 1 OF 1");
    expect(container.querySelector('[data-testid="formation-inventory-manager"]')?.textContent).toContain("Sir Alex Ferguson");
    expect(container.querySelectorAll('[data-testid="formation-face"]').length).toBe(11);
    expect(container.querySelectorAll('[data-testid="formation-bench-face"]').length).toBeGreaterThanOrEqual(5);
  });
});
