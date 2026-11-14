import React from "react";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NotificationBell } from "./NotificationBell";
import { api } from "@/lib/api";

const mockNavigate = jest.fn();

jest.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

jest.mock("@/lib/auth", () => ({
  useAuth: () => ({
    user: { id: "user-1", username: "fanzone", display_name: "Fan Zone", role: "user" },
  }),
}));

jest.mock("@/lib/realtime", () => ({
  useRealtimeTopics: () => ({ status: "connected" }),
}));

jest.mock("sonner", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
  },
  errMsg: (e: any) => String(e?.message || "Error"),
}));

const mockedApi = api as unknown as {
  get: jest.Mock;
  post: jest.Mock;
};

async function flush() {
  await act(async () => {
    await Promise.resolve();
    await new Promise((r) => setTimeout(r, 0));
  });
}

describe("NotificationBell", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    mockNavigate.mockReset();
    mockedApi.get.mockReset();
    mockedApi.post.mockReset();
  });

  afterEach(async () => {
    await act(async () => {
      root.unmount();
    });
    container.remove();
  });

  function renderBell(props: { ownerUnreadCount?: number; hasActiveClub?: boolean }) {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    return act(async () => {
      root.render(
        <QueryClientProvider client={qc}>
          <NotificationBell {...props} />
        </QueryClientProvider>
      );
    });
  }

  it("displays combined unread badge for club owners and marks single/all read with deep-link routing", async () => {
    mockedApi.get.mockResolvedValue({
      data: [
        {
          notification_id: "n-1",
          topic: "community_comment",
          message: "Naija FC replied to your transfer thread.",
          metadata: { deep_link_route: "/app/community" },
          created_at: "2026-11-13T18:00:00Z",
          is_read: false,
        },
        {
          notification_id: "n-2",
          topic: "competition_application",
          message: "Your cup application was accepted.",
          metadata: { deep_link_route: "/app/community" },
          created_at: "2026-11-13T17:00:00Z",
          is_read: true,
        },
      ],
    });
    mockedApi.post.mockResolvedValue({ data: { status: "ok" } });

    await renderBell({ ownerUnreadCount: 3, hasActiveClub: true });
    await flush();

    // 1 unread notification + 3 owner inbox unread = 4
    const badge = container.querySelector('[data-testid="notification-badge"]');
    expect(badge?.textContent).toBe("4");

    const bellBtn = container.querySelector('[data-testid="notification-bell-btn"]') as HTMLButtonElement;
    await act(async () => {
      bellBtn.click();
    });
    await flush();

    const popover = container.querySelector('[data-testid="notification-popover"]');
    expect(popover).not.toBeNull();
    expect(popover?.textContent).toContain("Owner Inbox (3 open)");
    expect(popover?.textContent).toContain("Naija FC replied to your transfer thread.");

    const markAllBtn = Array.from(popover!.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Mark all read")
    ) as HTMLButtonElement;
    expect(markAllBtn).toBeTruthy();

    await act(async () => {
      markAllBtn.click();
    });
    await flush();
    expect(mockedApi.post).toHaveBeenCalledWith("/notifications/read-all");

    const itemBtn = Array.from(popover!.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Naija FC replied to your transfer thread.")
    ) as HTMLButtonElement;
    await act(async () => {
      itemBtn.click();
    });
    await flush();

    expect(mockedApi.post).toHaveBeenCalledWith("/notifications/n-1/read");
    expect(mockNavigate).toHaveBeenCalledWith("/app/community");
  });

  it("excludes ownerUnreadCount when user does not have an active club", async () => {
    mockedApi.get.mockResolvedValue({
      data: [
        {
          notification_id: "n-3",
          topic: "community_post",
          message: "Welcome to GTEX Community.",
          metadata: {},
          created_at: "2026-11-13T18:00:00Z",
          is_read: false,
        },
      ],
    });

    await renderBell({ ownerUnreadCount: 5, hasActiveClub: false });
    await flush();

    const badge = container.querySelector('[data-testid="notification-badge"]');
    expect(badge?.textContent).toBe("1");

    const bellBtn = container.querySelector('[data-testid="notification-bell-btn"]') as HTMLButtonElement;
    await act(async () => {
      bellBtn.click();
    });
    await flush();

    const popover = container.querySelector('[data-testid="notification-popover"]');
    expect(popover?.textContent).not.toContain("Owner Inbox");
  });
});
