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
import { OwnerBriefingPanel } from "./OwnerBriefingPanel";
import type { DailyBriefing } from "@/lib/ownerBriefing";

var mockToastSuccess = jest.fn();
var mockToastError = jest.fn();

jest.mock("react-router-dom", () => {
  const ReactModule = require("react");
  return {
    Link: ({ to, children, ...props }: any) =>
      ReactModule.createElement(
        "a",
        {
          href: typeof to === "string" ? to : "#",
          ...props,
        },
        children,
      ),
  };
});

jest.mock("sonner", () => ({
  toast: {
    success: (...args: any[]) => mockToastSuccess(...args),
    error: (...args: any[]) => mockToastError(...args),
  },
}));

const mockBriefing: DailyBriefing = {
  id: "briefing-101",
  club_id: "c1",
  world_day: 42,
  headline: "Positive Squad Health and Commercial Growth",
  summary: "The club is operating smoothly with 0 active injuries and healthy cash flow.",
  metrics: {
    cash_gtex: 1250000,
    avg_morale: 85,
    avg_fitness: 92,
    injured_players: 0,
    ready_academy_prospects: 3,
    open_decisions: 2,
  },
  sections: [
    {
      section_key: "executive_summary",
      destination_key: "executive_office",
      role: "executive",
      sender: "Adeyemi Vance",
      title: "Strategic Operations Review",
      summary: "Boardroom governance is stable.",
    },
    {
      section_key: "managers_report",
      destination_key: "managers_office",
      role: "manager",
      sender: "Marcus Cole",
      title: "Squad Tactical Preparedness High",
      summary: "Team fitness is optimal ahead of next fixture.",
    },
  ],
  department_decisions: [
    {
      decision_id: "dec-1",
      department_key: "managers_office",
      title: "Approve Tactical Retreat Drill",
      description: "Spend 2,000 GTX to run specialized defensive transition clinic.",
      action_type: "tactics",
      impact_summary: "+4 defensive positioning",
      cost_gtex: 2000,
      status: "open",
    },
  ],
  decision_history: [],
};

describe("OwnerBriefingPanel Component", () => {
  let container: HTMLDivElement;
  let root: Root;
  let queryClient: QueryClient;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    mockToastSuccess.mockClear();
    mockToastError.mockClear();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          refetchOnWindowFocus: false,
        },
      },
    });
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    queryClient.clear();
    container.remove();
    jest.restoreAllMocks();
  });

  async function renderPanel(clubId?: string, initialData?: DailyBriefing | null) {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <OwnerBriefingPanel clubId={clubId} initialData={initialData} />
        </QueryClientProvider>,
      );
    });
    for (let i = 0; i < 5; i += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    }
  }

  test("renders successful daily briefing with reports and metrics", async () => {
    jest.spyOn(api, "get").mockResolvedValue({ data: mockBriefing } as any);

    await renderPanel("c1");

    expect(container.querySelector('[data-testid="owner-briefing"]')).not.toBeNull();
    expect(container.textContent).toContain("Day 42");
    expect(container.textContent).toContain("Positive Squad Health and Commercial Growth");
    expect(container.textContent).toContain("The club is operating smoothly");
    expect(container.textContent).toContain("1,250,000 GTX");
    expect(container.textContent).toContain("85/100");
    expect(container.textContent).toContain("92%");
    expect(container.textContent).toContain("All Fit");
    expect(container.textContent).toContain("3 Prospects");
    expect(container.textContent).toContain("Strategic Operations Review");
  });

  test("renders empty state when request succeeds with no briefing data", async () => {
    jest.spyOn(api, "get").mockResolvedValue({ data: null } as any);

    await renderPanel("c1");

    expect(container.querySelector('[data-testid="owner-briefing-empty-state"]')).not.toBeNull();
    expect(container.textContent).toContain("No Briefing Compiled Yet");
    expect(container.querySelector('[data-testid="compile-briefing-empty-btn"]')).not.toBeNull();
  });

  test("renders error state when briefing fetch fails and no cache exists", async () => {
    jest.spyOn(api, "get").mockRejectedValue(new Error("Club operations gateway unreachable"));

    await renderPanel("c1");

    expect(container.querySelector('[data-testid="owner-briefing-error-state"]')).not.toBeNull();
    expect(container.textContent).toContain("Failed to load owner daily briefing");
    expect(container.textContent).toContain("Club operations gateway unreachable");
    expect(container.querySelector('[data-testid="briefing-error-retry-btn"]')).not.toBeNull();
  });

  test("retries request when retry button is clicked in error state", async () => {
    const apiGetSpy = jest.spyOn(api, "get");
    apiGetSpy.mockRejectedValueOnce(new Error("Initial network timeout"));

    await renderPanel("c1");

    const retryBtn = container.querySelector('[data-testid="briefing-error-retry-btn"]') as HTMLButtonElement;
    expect(retryBtn).not.toBeNull();

    // Now resolve on subsequent retry call
    apiGetSpy.mockResolvedValueOnce({ data: mockBriefing } as any);

    await act(async () => {
      retryBtn.click();
    });
    for (let i = 0; i < 5; i += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    }

    expect(container.querySelector('[data-testid="owner-briefing-error-state"]')).toBeNull();
    expect(container.textContent).toContain("Positive Squad Health and Commercial Growth");
    expect(container.textContent).toContain("Day 42");
  });

  test("displays stale banner with cached data when update request fails", async () => {
    jest.spyOn(api, "get").mockRejectedValue(new Error("Upstream briefing sync failed"));

    await renderPanel("c1", mockBriefing);

    expect(container.querySelector('[data-testid="owner-briefing-stale-banner"]')).not.toBeNull();
    expect(container.textContent).toContain("Showing cached briefing data; the latest update request failed.");
    expect(container.querySelector('[data-testid="briefing-retry-btn"]')).not.toBeNull();
    expect(container.textContent).toContain("Positive Squad Health and Commercial Growth");
  });
});
