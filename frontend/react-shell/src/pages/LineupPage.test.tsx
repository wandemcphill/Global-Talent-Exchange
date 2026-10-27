declare const describe: any;
declare const test: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { api } from "@/lib/api";
import Lineup from "./Lineup";

jest.mock("@/lib/owner", () => ({
  useActiveClub: () => ({
    clubs: [{ club_id: "club-1", club_name: "Test Athletic" }],
    active: { club_id: "club-1", club_name: "Test Athletic" },
  }),
  fmt: (value: unknown) => String(value ?? 0),
}));

const roster = {
  items: [
    { player_id: "gk-1", player_name: "Keeper One", position: "GK", rating: 82 },
    { player_id: "p-1", player_name: "Defender One", position: "CB", rating: 80 },
    { player_id: "p-2", player_name: "Defender Two", position: "LB", rating: 79 },
    { player_id: "p-3", player_name: "Defender Three", position: "RB", rating: 78 },
    { player_id: "p-4", player_name: "Defender Four", position: "CB", rating: 77 },
    { player_id: "p-5", player_name: "Midfielder One", position: "CM", rating: 85 },
    { player_id: "p-6", player_name: "Midfielder Two", position: "CM", rating: 84 },
    { player_id: "p-7", player_name: "Midfielder Three", position: "AM", rating: 83 },
    { player_id: "p-8", player_name: "Forward One", position: "ST", rating: 88 },
    { player_id: "p-9", player_name: "Forward Two", position: "LW", rating: 86 },
    { player_id: "p-10", player_name: "Forward Three", position: "RW", rating: 87 },
    { player_id: "p-11", player_name: "Reserve One", position: "CM", rating: 75 },
  ],
};

describe("React lineup page", () => {
  let container: HTMLDivElement;
  let root: Root;
  let queryClient: QueryClient;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
    });
    jest.spyOn(api, "get").mockImplementation(((url: string) => {
      if (url.includes("/market/clubs/")) return Promise.resolve({ data: roster });
      if (url.includes("/lineup")) {
        return Promise.resolve({
          data: {
            club_id: "club-1",
            formation: "4-3-3",
            starter_player_ids: [],
            bench_player_ids: [],
          },
        });
      }
      return Promise.reject(new Error("Unexpected GET " + url));
    }) as any);
    jest.spyOn(api, "put").mockImplementation(((_url: string, payload: any) =>
      Promise.resolve({ data: { club_id: "club-1", ...payload } })) as any);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    queryClient.clear();
    container.remove();
    jest.restoreAllMocks();
  });

  async function renderPage() {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={["/app/lineup?club_id=club-1"]}>
            <Lineup />
          </MemoryRouter>
        </QueryClientProvider>,
      );
    });
    for (let i = 0; i < 5; i += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    }
  }

  test("renders formation, all starting slots, bench, and manager entry points", async () => {
    await renderPage();

    expect(container.textContent).toContain("Lineup & Tactics");
    expect(container.textContent).toContain("Squad registration");
    expect(container.querySelectorAll('select[id^="lineup-slot-"]')).toHaveLength(11);
    expect(container.querySelector('[data-testid="lineup-bench-panel"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="lineup-manager-panel"]')).not.toBeNull();
  });

  test("auto-fills a goalkeeper and ten outfield players and saves through the lineup API", async () => {
    await renderPage();

    const autoFill = container.querySelector('[data-testid="auto-fill-lineup-button"]') as HTMLButtonElement;
    await act(async () => autoFill.dispatchEvent(new MouseEvent("click", { bubbles: true })));

    const save = container.querySelector('[data-testid="save-lineup-button"]') as HTMLButtonElement;
    await act(async () => save.dispatchEvent(new MouseEvent("click", { bubbles: true })));

    expect(api.put).toHaveBeenCalledTimes(1);
    const [url, payload] = (api.put as any).mock.calls[0];
    expect(url).toBe("/clubs/club-1/lineup");
    expect(payload.formation).toBe("4-3-3");
    expect(payload.starter_player_ids).toHaveLength(11);
    expect(payload.starter_player_ids[0]).toBe("gk-1");
    expect(new Set(payload.starter_player_ids).size).toBe(11);
  });
});
