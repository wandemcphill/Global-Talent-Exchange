declare const describe: any;
declare const test: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AppShell from "./AppShell";

var mockApiGet = jest.fn();
var mockNavigate = jest.fn();
var mockLogout = jest.fn();
var mockPathname = "/app";
var mockUser: any = {
  id: "owner-1",
  username: "owner1",
  display_name: "Club Owner",
  role: "user",
  account_type: "user",
};
var mockAuthLoading = false;

jest.mock("react-router-dom", () => {
  const ReactModule = require("react");
  return {
    NavLink: ({ to, children, className, end: _end, ...rest }: any) => {
      const resolved = typeof className === "function" ? className({ isActive: false }) : className;
      return ReactModule.createElement(
        "a",
        { href: typeof to === "string" ? to : "#", className: resolved, ...rest },
        children,
      );
    },
    Navigate: ({ to }: any) => ReactModule.createElement("div", { "data-testid": "navigate-to" }, to),
    Outlet: () =>
      ReactModule.createElement("div", { "data-testid": "mock-outlet" }, `Route:${mockPathname}`),
    useLocation: () => ({ pathname: mockPathname, search: "", hash: "" }),
    useNavigate: () => mockNavigate,
  };
});

jest.mock("@/lib/auth", () => ({
  useAuth: () => ({
    user: mockUser,
    loading: mockAuthLoading,
    logout: (...args: any[]) => mockLogout(...args),
  }),
}));

jest.mock("@/lib/api", () => ({
  API: "http://localhost:8000/api",
  api: {
    get: (...args: any[]) => mockApiGet(...args),
  },
}));

jest.mock("@/lib/worldClock", () => ({
  useWorldClock: () => ({ data: null }),
  formatWorldDate: (v: string) => v,
  formatWorldTime: (v: string) => v,
}));

jest.mock("@/lib/skin-engine", () => ({
  useSkin: () => ({ skin: "default", sidebarMode: "expanded", dataSaver: false }),
}));

jest.mock("@/lib/audio", () => ({
  GtexSponsoredMusicCard: () => null,
}));

jest.mock("@/components/gtex/GlobalLiveTicker", () => ({
  GlobalLiveTicker: () => null,
}));

jest.mock("@/components/gtex/NotificationBell", () => ({
  NotificationBell: () => null,
}));

jest.mock("@/components/gtex/GtexTraxPlayer", () => ({
  GtexTraxTopBarControl: () => null,
}));

jest.mock("@/components/gtex/ApexWidgets", () => ({
  CommandPaletteModal: () => null,
}));

async function flushPromises() {
  for (let i = 0; i < 6; i += 1) {
    await act(async () => {
      await Promise.resolve();
      await new Promise((resolve) => setTimeout(resolve, 15));
    });
  }
}

describe("AppShell control-center resilience and admin bypass", () => {
  let container: HTMLDivElement;
  let root: Root;
  let queryClient: QueryClient;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    localStorage.clear();
    mockPathname = "/app";
    mockAuthLoading = false;
    mockUser = {
      id: "owner-1",
      username: "owner1",
      display_name: "Club Owner",
      role: "user",
      account_type: "user",
    };
    mockApiGet.mockReset();
    mockNavigate.mockReset();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    // Use production-like QueryClient defaults (no retry: false override) so
    // useControlCenter's own retry policy is exercised directly.
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 60_000,
          refetchOnWindowFocus: false,
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

  test("does not trap users in Loading your clubs when control-center fails with HTTP 500 or CORS network error", async () => {
    // Simulate a CORS-stripped 500 response where axios has no response object.
    mockApiGet.mockRejectedValueOnce(new Error("Network Error"));

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <AppShell />
        </QueryClientProvider>,
      );
    });
    await flushPromises();

    // Should fail fast in 1 attempt instead of looping or hanging on retries.
    expect(mockApiGet).toHaveBeenCalledTimes(1);
    expect(container.querySelector('[data-testid="loading-state"]')).toBeNull();
    const retryBtn = container.querySelector('[data-testid="app-shell-control-center-retry"]') as HTMLButtonElement;
    expect(retryBtn).not.toBeNull();
    expect(container.querySelector('[data-testid="mock-outlet"]')?.textContent).toBe("Route:/app");

    // Clicking Retry recovers cleanly once the backend succeeds.
    mockApiGet.mockResolvedValueOnce({
      data: {
        clubs: [{ club_id: "c1", club_name: "Lagos United", stage: "active" }],
        economy: { naira_per_gtex: 60, naira_per_fan: 4, fan_coin_per_gtex: 15, wallet: {} },
        inbox_open_count: 0,
      },
    });

    await act(async () => {
      retryBtn.click();
    });
    await flushPromises();

    expect(mockApiGet).toHaveBeenCalledTimes(2);
    expect(container.querySelector('[data-testid="app-shell-control-center-retry"]')).toBeNull();
    expect(container.querySelector('[data-testid="club-switcher"]')).not.toBeNull();
  });

  test("renders admin routes immediately without waiting for control-center", async () => {
    mockUser = {
      id: "admin-1",
      username: "admin1",
      display_name: "Super Admin",
      role: "super_admin",
      account_type: "user",
    };
    mockPathname = "/app/admin";
    // Control center stays pending forever.
    mockApiGet.mockImplementation(() => new Promise(() => {}));

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <AppShell />
        </QueryClientProvider>,
      );
    });
    await flushPromises();

    expect(container.querySelector('[data-testid="loading-state"]')).toBeNull();
    expect(container.querySelector('[data-testid="mock-outlet"]')?.textContent).toBe("Route:/app/admin");
  });

  test("an active club shows the eight club-day destinations", async () => {
    mockApiGet.mockResolvedValue({
      data: {
        clubs: [{ club_id: "c1", club_name: "Lagos United", stage: "active" }],
        economy: { naira_per_gtex: 60, naira_per_fan: 4, fan_coin_per_gtex: 15, wallet: {} },
        inbox_open_count: 0,
      },
    });

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <AppShell />
        </QueryClientProvider>,
      );
    });
    await flushPromises();

    const nav = container.querySelector('[data-testid="primary-nav"]');
    const labels = Array.from(nav?.querySelectorAll("a") || []).map((link) =>
      (link.querySelector("span")?.textContent || "").trim(),
    );
    expect(labels).toEqual([
      "Today",
      "Squad",
      "Staff",
      "Academy",
      "Competitions",
      "Inbox",
      "Market",
      "Wallet",
    ]);
    expect(nav?.textContent).not.toContain("Control Centre");
    expect(nav?.textContent).not.toContain("Trophy Cabinet");
  });
});
