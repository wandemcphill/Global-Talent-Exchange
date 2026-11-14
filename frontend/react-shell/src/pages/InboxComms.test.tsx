import React from "react";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import InboxPage from "./Inbox";
import { api } from "@/lib/api";

let mockSearchParams = new URLSearchParams("");
const mockSetParams = jest.fn((next: any) => {
  mockSearchParams = new URLSearchParams(next);
});
const mockNavigate = jest.fn();
const mockRefresh = jest.fn();
const mockRefetchComms = jest.fn();
const mockUseClubCommunications = jest.fn();
const mockUseActiveClub = jest.fn();

jest.mock("react-router-dom", () => ({
  Link: ({ children, to, ...props }: any) => (
    <a href={to} {...props}>
      {children}
    </a>
  ),
  useNavigate: () => mockNavigate,
  useSearchParams: () => [mockSearchParams, mockSetParams],
}));

jest.mock("@/lib/owner", () => ({
  useActiveClub: () => mockUseActiveClub(),
  useClubCommunications: (...args: any[]) => mockUseClubCommunications(...args),
  useRefreshOwner: () => mockRefresh,
  label: (s: any) => String(s || ""),
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

function setInputValue(el: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement, value: string) {
  const proto =
    el instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype
      : el instanceof HTMLSelectElement
      ? HTMLSelectElement.prototype
      : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
  setter?.call(el, value);
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
}

describe("Owner Club Communications Overhaul (InboxPage)", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    mockSearchParams = new URLSearchParams("");
    mockSetParams.mockClear();
    mockNavigate.mockClear();
    mockRefresh.mockClear();
    mockRefetchComms.mockClear();
    mockUseActiveClub.mockReset();
    mockUseClubCommunications.mockReset();
    mockedApi.get.mockReset();
    mockedApi.post.mockReset();

    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);

    mockedApi.get.mockImplementation(async (url: string) => {
      if (url === "/owner/inbox") {
        return { data: { items: [], counts: { unread: 0, archive: 0 } } };
      }
      if (url.includes("/messages")) {
        return {
          data: {
            messages: [
              {
                id: "old-1",
                seq: 1,
                sender_name: "Manager Cole",
                sender_role: "manager",
                body: "Earlier tactical briefing.",
                world_day: 2,
              },
            ],
            has_more: false,
            next_before_seq: null,
          },
        };
      }
      return { data: {} };
    });
    mockedApi.post.mockResolvedValue({ data: { status: "ok" } });
  });

  afterEach(async () => {
    await act(async () => {
      root.unmount();
    });
    container.remove();
  });

  function renderInbox() {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    return act(async () => {
      root.render(
        <QueryClientProvider client={qc}>
          <InboxPage />
        </QueryClientProvider>
      );
    });
  }

  function makeCommsPayload() {
    return {
      owner_authority: { verified_name: "Chief Adebayo", role: "club_owner" },
      counts: { inbox_unread: 0, direct_unread: 2, scheduled_meetings: 1, open_decisions: 0, announcements: 1, archived: 0 },
      contacts: {
        staff: [
          {
            contact_id: "staff:manager",
            thread_id: "th-1",
            name: "Manager Cole",
            title: "First-Team Manager",
            department: "First Team",
            portrait_url: "/avatar.png",
            mood: 82,
          },
        ],
        players: [],
      },
      direct_threads: [
        {
          thread_id: "th-1",
          thread_key: "staff:manager",
          recipient_name: "Manager Cole",
          recipient_role: "First-Team Manager",
          relationship_score: 82,
          unread_count: 2,
          archived_at: null,
          has_more: true,
          next_before_seq: 11,
          messages: [
            {
              id: "msg-11",
              seq: 11,
              sender_name: "Manager Cole",
              sender_role: "manager",
              body: "Full-back fatigue ahead of quarter-final.",
              world_day: 5,
            },
          ],
        },
      ],
      rooms: { staff_room: [], squad_room: [] },
      meetings: [],
      announcements: [],
      requests_decisions: {},
      search_results: [
        {
          id: "msg-11",
          message_id: "msg-11",
          thread_id: "th-1",
          thread_type: "direct",
          subject: "Manager Cole",
          sender_name: "Manager Cole",
          body: "Full-back fatigue ahead of quarter-final.",
        },
      ],
    };
  }

  it("enforces explicit 'All Clubs' scope and prompts club selection before opening direct comms", async () => {
    mockUseActiveClub.mockReturnValue({
      clubs: [
        { club_id: "c1", club_name: "Victoria Island United" },
        { club_id: "c2", club_name: "Lagos Royals" },
      ],
      activeClub: { club_id: "c1", club_name: "Victoria Island United" },
    });
    mockUseClubCommunications.mockReturnValue({
      data: makeCommsPayload(),
      refetch: mockRefetchComms,
    });
    mockSearchParams = new URLSearchParams("tab=direct");

    await renderInbox();
    await flush();

    // Default club filter in All Clubs scope passes undefined ("all" never falls back silently to c1)
    expect(mockUseClubCommunications).toHaveBeenCalledWith(
      undefined,
      expect.objectContaining({ includeArchived: false })
    );
    expect(container.querySelector('[data-testid="inbox-pick-club"]')).not.toBeNull();

    // Pick a specific club from the prompt
    const clubBtn = Array.from(container.querySelectorAll('[data-testid="inbox-pick-club"] button')).find((b) =>
      b.textContent?.includes("Lagos Royals")
    ) as HTMLButtonElement;
    await act(async () => {
      clubBtn.click();
    });
    await flush();

    expect(mockUseClubCommunications).toHaveBeenLastCalledWith(
      "c2",
      expect.objectContaining({ includeArchived: false })
    );
    expect(container.textContent).toContain("Chief Adebayo · Club Owner (verified)");
  });

  it("handles pagination, mark-read, archive, comms search, and Community cross-post toggle", async () => {
    mockUseActiveClub.mockReturnValue({
      clubs: [{ club_id: "c1", club_name: "Victoria Island United" }],
      activeClub: { club_id: "c1", club_name: "Victoria Island United" },
    });
    mockUseClubCommunications.mockReturnValue({
      data: makeCommsPayload(),
      refetch: mockRefetchComms,
    });
    mockSearchParams = new URLSearchParams("club_id=c1&tab=direct");

    await renderInbox();
    await flush();

    // Verify search input triggers comms search results & Load older / Mark read / Archive actions
    const searchInput = container.querySelector('input[aria-label="Search club communications"]') as HTMLInputElement;
    expect(searchInput).toBeTruthy();
    await act(async () => {
      setInputValue(searchInput, "fatigue");
    });
    await flush();
    expect(mockUseClubCommunications).toHaveBeenLastCalledWith(
      "c1",
      expect.objectContaining({ search: "fatigue", includeArchived: false })
    );
    expect(container.querySelector('[data-testid="comms-search-results"]')).not.toBeNull();
    expect(container.textContent).toContain("Full-back fatigue ahead of quarter-final.");

    const loadOlderBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Load older messages")
    ) as HTMLButtonElement;
    await act(async () => {
      loadOlderBtn.click();
    });
    await flush();
    expect(mockedApi.get).toHaveBeenCalledWith(
      "/owner/clubs/c1/communications/threads/th-1/messages",
      { params: { before_seq: 11, limit: 30 } }
    );
    expect(container.textContent).toContain("Earlier tactical briefing.");

    const markReadBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Mark read")
    ) as HTMLButtonElement;
    await act(async () => {
      markReadBtn.click();
    });
    await flush();
    expect(mockedApi.post).toHaveBeenCalledWith("/owner/clubs/c1/communications/threads/th-1/read");

    const archiveBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.trim() === "Archive"
    ) as HTMLButtonElement;
    await act(async () => {
      archiveBtn.click();
    });
    await flush();
    expect(mockedApi.post).toHaveBeenCalledWith(
      "/owner/clubs/c1/communications/threads/th-1/archive",
      undefined,
      { params: { archived: true } }
    );

    // Switch to 7. Announcements and verify also_post_to_community toggle
    const annTab = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("7. Announcements")
    ) as HTMLButtonElement;
    await act(async () => {
      annTab.click();
    });
    await flush();

    const titleInput = container.querySelector('input[placeholder="Official Club Statement..."]') as HTMLInputElement;
    const bodyInput = container.querySelector('textarea[placeholder="Write the official club announcement..."]') as HTMLTextAreaElement;
    const communityLabel = Array.from(container.querySelectorAll("label")).find((l) =>
      l.textContent?.includes("Also share public club announcement in GTEX Community")
    );
    const communityCheckbox = communityLabel?.querySelector('input[type="checkbox"]') as HTMLInputElement;
    expect(communityCheckbox).toBeTruthy();

    await act(async () => {
      setInputValue(titleInput, "Stadium Floodlight Upgrade");
      setInputValue(bodyInput, "New LED towers ready before Friday kickoff.");
      communityCheckbox.click();
    });
    await flush();

    const form = titleInput.closest("form") as HTMLFormElement;
    await act(async () => {
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });
    await flush();

    expect(mockedApi.post).toHaveBeenCalledWith(
      "/owner/clubs/c1/communications/announcements",
      expect.objectContaining({
        title: "Stadium Floodlight Upgrade",
        body: "New LED towers ready before Friday kickoff.",
        also_post_to_community: true,
      })
    );
  });
});
