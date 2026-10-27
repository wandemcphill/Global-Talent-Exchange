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
import { toast } from "sonner";
import InboxPage from "./Inbox";

var mockSearchParams = new URLSearchParams("");
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
    useNavigate: () => () => {},
    useSearchParams: () => [mockSearchParams, () => {}],
  };
});

jest.mock("@/lib/owner", () => ({
  useActiveClub: () => ({
    clubs: [
      { club_id: "c1", club_name: "Lagos City FC" },
      { club_id: "c2", club_name: "Abuja Athletic" },
    ],
    active: { club_id: "c1", club_name: "Lagos City FC" },
    select: () => {},
  }),
  useRefreshOwner: () => () => {},
  label: (val: string) => val,
}));

jest.mock("sonner", () => ({
  toast: {
    success: (...args: any[]) => mockToastSuccess(...args),
    error: (...args: any[]) => mockToastError(...args),
  },
}));

const mockInboxItems = [
  {
    id: "item-101",
    club_id: "c1",
    category: "staff_recommendations",
    kind: "facility_request",
    title: "Upgrade Medical Bay",
    what: "Invest 8,000 GTX into medical wing to reduce injury time.",
    why: "Two key regens suffered recurrence.",
    sender: "Head Physio Danladi",
    status: "open",
    priority: "high",
    is_decision: true,
    is_read: false,
    body: "We need updated scanning machinery before round 10.",
    actions: [
      { key: "approve", label: "Approve 8,000 GTX", style: "primary" },
      { key: "reject", label: "Reject request", style: "ghost" },
    ],
  },
  {
    id: "item-102",
    club_id: "c1",
    category: "deadlines",
    kind: "transfer_bid",
    title: "Transfer Bid for Wonderkid",
    what: "Real Madrid offered 45,000 GTX.",
    status: "open",
    priority: "standard",
    is_decision: true,
    is_read: true,
    deadline_at: "2026-11-01T00:00:00Z",
    actions: [
      { key: "accept", label: "Accept offer", style: "primary" },
    ],
  },
];

describe("React Owner Decision Inbox", () => {
  let container: HTMLDivElement;
  let root: Root;
  let queryClient: QueryClient;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    mockSearchParams = new URLSearchParams("");
    mockToastSuccess.mockClear();
    mockToastError.mockClear();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
    });
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    queryClient.clear();
    container.remove();
    jest.restoreAllMocks();
  });

  async function renderInbox() {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <InboxPage />
        </QueryClientProvider>,
      );
    });
    for (let i = 0; i < 5; i += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    }
  }

  test("renders owner inbox header, categories, club selector, and real item IDs", async () => {
    jest.spyOn(api, "get").mockImplementation(((url: string, config: any) => {
      if (url === "/owner/inbox") {
        return Promise.resolve({
          data: {
            items: mockInboxItems,
            counts: { open: 2, deadlines: 1, unread: 1 },
          },
        });
      }
      return Promise.reject(new Error("Unexpected GET " + url));
    }) as any);

    await renderInbox();

    expect(container.textContent).toContain("Personal Owner Inbox");
    expect(container.textContent).toContain("Command & Decisions");
    expect(container.querySelector('[data-testid="inbox-page"]')).not.toBeNull();

    // Club selector renders clubs
    expect(container.textContent).toContain("Lagos City FC");
    expect(container.textContent).toContain("Abuja Athletic");

    // Item IDs are rendered in data-testid
    expect(container.querySelector('[data-testid="inbox-item-item-101"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="inbox-item-item-102"]')).not.toBeNull();
    expect(container.textContent).toContain("Upgrade Medical Bay");
    expect(container.textContent).toContain("Transfer Bid for Wonderkid");

    // Action buttons rendered
    expect(container.querySelector('[data-testid="inbox-action-approve-item-101"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="inbox-action-reject-item-101"]')).not.toBeNull();
  });

  test("honors deep link query parameters (?status=resolved&category=deadlines&club_id=c2)", async () => {
    mockSearchParams = new URLSearchParams("status=resolved&category=deadlines&club_id=c2");

    let capturedParams: any = null;
    jest.spyOn(api, "get").mockImplementation(((url: string, config: any) => {
      if (url === "/owner/inbox") {
        capturedParams = config?.params;
        return Promise.resolve({
          data: {
            items: [],
            counts: { resolved: 0, deadlines: 0, unread: 0 },
          },
        });
      }
      return Promise.reject(new Error("Unexpected GET " + url));
    }) as any);

    await renderInbox();

    expect(capturedParams).not.toBeNull();
    expect(capturedParams.status).toBe("resolved");
    expect(capturedParams.category).toBe("deadlines");
    expect(capturedParams.club_id).toBe("c2");
  });

  test("renders honest empty state when server returns no items", async () => {
    jest.spyOn(api, "get").mockImplementation(((url: string) => {
      if (url === "/owner/inbox") {
        return Promise.resolve({
          data: { items: [], counts: { open: 0 } },
        });
      }
      return Promise.reject(new Error("Unexpected GET " + url));
    }) as any);

    await renderInbox();

    expect(container.textContent).toContain("No Messages");
    expect(container.querySelector('[data-testid="inbox-item-item-101"]')).toBeNull();
  });

  test("renders honest error state with retry when server fails", async () => {
    jest.spyOn(api, "get").mockImplementation(((url: string) => {
      if (url === "/owner/inbox") {
        return Promise.reject(new Error("Server 503 Service Unavailable"));
      }
      return Promise.reject(new Error("Unexpected GET " + url));
    }) as any);

    await renderInbox();

    const errorState = container.querySelector('[data-testid="inbox-error-state"]');
    expect(errorState).not.toBeNull();
    expect(errorState?.textContent).toContain("Unable to load owner inbox");
    expect(errorState?.textContent).toContain("Server 503");
  });

  test("executes decision with server confirmation and does not confirm before server responds", async () => {
    jest.spyOn(api, "get").mockImplementation(((url: string) => {
      if (url === "/owner/inbox") {
        return Promise.resolve({
          data: {
            items: [mockInboxItems[0]],
            counts: { open: 1, unread: 1 },
          },
        });
      }
      return Promise.reject(new Error("Unexpected GET " + url));
    }) as any);

    let decidePromiseResolve: any;
    const decidePromise = new Promise((resolve) => {
      decidePromiseResolve = resolve;
    });

    jest.spyOn(api, "post").mockImplementation(((url: string, body: any) => {
      if (url === "/owner/inbox/item-101/decide") {
        return decidePromise;
      }
      return Promise.reject(new Error("Unexpected POST " + url));
    }) as any);

    await renderInbox();

    const approveBtn = container.querySelector(
      '[data-testid="inbox-action-approve-item-101"]',
    ) as HTMLButtonElement;
    expect(approveBtn).not.toBeNull();

    // Trigger decide action
    await act(async () => {
      approveBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    // In flight: shows busy indicator "…" and api was called
    expect(api.post).toHaveBeenCalledTimes(1);
    expect(api.post).toHaveBeenCalledWith("/owner/inbox/item-101/decide", { action: "approve" });

    // Server has NOT resolved yet: outcome must not be displayed prematurely
    expect(container.querySelector('[data-testid="inbox-item-outcome"]')).toBeNull();

    // Server responds with outcome
    await act(async () => {
      decidePromiseResolve({ data: { success: true, outcome: "Medical Bay upgrade queued for 8,000 GTX." } });
    });

    expect(mockToastSuccess).toHaveBeenCalledWith("Medical Bay upgrade queued for 8,000 GTX.");
  });

  test("handles read/unread and archive/restore status toggles against server API", async () => {
    jest.spyOn(api, "get").mockImplementation(((url: string) => {
      if (url === "/owner/inbox") {
        return Promise.resolve({
          data: {
            items: [mockInboxItems[0]],
            counts: { open: 1, unread: 1 },
          },
        });
      }
      return Promise.reject(new Error("Unexpected GET " + url));
    }) as any);

    jest.spyOn(api, "post").mockImplementation(((url: string, body: any) => {
      if (url.includes("/read") || url.includes("/archive")) {
        return Promise.resolve({ data: { ok: true } });
      }
      return Promise.reject(new Error("Unexpected POST " + url));
    }) as any);

    await renderInbox();

    // Toggle read
    const readBtn = container.querySelector('button[title="Mark read"]') as HTMLButtonElement;
    expect(readBtn).not.toBeNull();
    await act(async () => {
      readBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    expect(api.post).toHaveBeenCalledWith("/owner/inbox/item-101/read", { is_read: true });

    // Toggle archive
    const archiveBtn = container.querySelector('button[title="Archive item"]') as HTMLButtonElement;
    expect(archiveBtn).not.toBeNull();
    await act(async () => {
      archiveBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    expect(api.post).toHaveBeenCalledWith("/owner/inbox/item-101/archive", { archive: true });
  });
});
