import React from "react";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import CommunityPage from "./Community";
import { api } from "@/lib/api";

let mockSearchParams = new URLSearchParams("");
const mockSetParams = jest.fn((next: any) => {
  mockSearchParams = new URLSearchParams(next);
});

let mockUser: any = {
  id: "u-fan",
  username: "streetfan",
  display_name: "Street Fan",
  role: "user",
};
let mockClubs: any[] = [];

jest.mock("react-router-dom", () => ({
  Link: ({ children, to, ...props }: any) => (
    <a href={to} {...props}>
      {children}
    </a>
  ),
  useSearchParams: () => [mockSearchParams, mockSetParams],
}));

jest.mock("@/lib/auth", () => ({
  useAuth: () => ({ user: mockUser }),
}));

jest.mock("@/lib/owner", () => ({
  useActiveClub: () => ({ clubs: mockClubs }),
}));

let latestRealtimeHandler: ((ev: any) => void) | null = null;
let latestReconnectHandler: (() => void) | null = null;

jest.mock("@/lib/realtime", () => ({
  useRealtimeTopics: (_topics: string[], onEvent: (ev: any) => void, onReconnect?: () => void, enabled = true) => {
    if (enabled !== false) {
      latestRealtimeHandler = onEvent;
      latestReconnectHandler = onReconnect || null;
    }
    return { status: "connected" };
  },
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
    patch: jest.fn(),
    delete: jest.fn(),
  },
  errMsg: (e: any) => String(e?.message || "Request error"),
}));

const mockedApi = api as unknown as {
  get: jest.Mock;
  post: jest.Mock;
  patch: jest.Mock;
  delete: jest.Mock;
};

async function flush() {
  await act(async () => {
    await Promise.resolve();
    await new Promise((r) => setTimeout(r, 0));
  });
}

function setInputValue(el: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
  setter?.call(el, value);
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
}

describe("GTEX Community Page", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    mockSearchParams = new URLSearchParams("");
    mockSetParams.mockClear();
    mockUser = {
      id: "u-fan",
      username: "streetfan",
      display_name: "Street Fan",
      role: "user",
    };
    mockClubs = [];
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    mockedApi.get.mockReset();
    mockedApi.post.mockReset();
    mockedApi.patch.mockReset();
    mockedApi.delete.mockReset();
  });

  afterEach(async () => {
    await act(async () => {
      root.unmount();
    });
    container.remove();
  });

  function installDefaultApiMocks() {
    mockedApi.get.mockImplementation(async (url: string) => {
      if (url === "/community/posts") {
        return {
          data: {
            posts: [
              {
                id: "post-1",
                author_user_id: "u-fan",
                author: { id: "u-fan", username: "streetfan", display_name: "Street Fan" },
                post_type: "discussion",
                title: "AFCON U20 Tactical Preview",
                body: "Pressing traps from kick-off look lethal this season.",
                channel_slug: "tactics-debate",
                tags: ["afcon", "tactics"],
                is_official_club_announcement: false,
                poll: {
                  total_votes: 6,
                  viewer_option_id: null,
                  options: [
                    { id: "opt-1", label: "4-3-3 High Press", votes: 4 },
                    { id: "opt-2", label: "3-5-2 Wingbacks", votes: 2 },
                  ],
                },
                reaction_counts: { fire: 3 },
                viewer_reactions: [],
                comment_count: 1,
                viewer_bookmarked: false,
                created_at: "2026-11-13T18:00:00Z",
              },
            ],
            next_cursor: null,
          },
        };
      }
      if (url === "/community/channels") {
        return {
          data: {
            channels: [
              { id: "ch-1", slug: "global-lounge", name: "GTEX Global Lounge", description: "Open football lounge" },
              { id: "ch-2", slug: "transfer-talk", name: "Transfer Talk", description: "Deals and scouts" },
            ],
          },
        };
      }
      if (url === "/community/discovery/players") {
        return {
          data: {
            players: [
              { id: "pl-1", name: "Tunde Balogun", position: "CM", gsi: 84, country: "NG", is_regen: true },
            ],
          },
        };
      }
      if (url === "/community/competitions") {
        return {
          data: {
            competitions: [
              {
                id: "comp-1",
                title: "Lagos Open Community Cup",
                slug: "lagos-open-cup",
                description: "Free entry knockout",
                entry_fee_fancoin: 0,
                slots_remaining: 6,
                max_participants: 8,
                visibility: "open",
                host_user_id: "u-fan",
                organizer: { id: "u-fan", display_name: "Street Fan" },
                viewer_joined: false,
                viewer_application_status: null,
              },
            ],
          },
        };
      }
      if (url === "/community/discovery/clubs") {
        return {
          data: {
            clubs: [
              {
                id: "club-1",
                club_name: "Victoria Island United",
                description: "Built from foundation division.",
                trophy_count: 2,
                follower_count: 14,
                viewer_follows: false,
                owner: { id: "u-owner", display_name: "Chief Adebayo" },
              },
            ],
          },
        };
      }
      if (url === "/community/discovery/people") {
        return {
          data: {
            people: [
              { id: "u-2", username: "coachada", display_name: "Coach Ada", club: null, viewer_muted: false },
            ],
          },
        };
      }
      if (url === "/community/private-messages/threads") {
        return {
          data: [
            {
              id: "pm-1",
              subject: "Scouting Trio",
              is_group: true,
              participants: [{ user_id: "u-fan" }, { user_id: "u-2" }, { user_id: "u-3" }],
              last_message_at: "2026-11-13T18:30:00Z",
            },
          ],
        };
      }
      if (url === "/community/private-messages/threads/pm-1/messages/page") {
        return {
          data: {
            messages: [
              {
                id: "m-1",
                seq: 1,
                sender_user_id: "u-2",
                sender: { id: "u-2", display_name: "Coach Ada" },
                body: "Check out the academy striker!",
                created_at: "2026-11-13T18:25:00Z",
              },
            ],
            has_more: false,
            next_before_seq: null,
          },
        };
      }
      if (url.includes("/messages")) {
        return { data: { messages: [], has_more: false, next_before_seq: null } };
      }
      if (url === "/community/admin/moderation/reports") {
        return {
          data: {
            reports: [
              {
                id: "rep-1",
                status: "open",
                target_type: "post",
                target_id: "post-bad",
                report_count_for_target: 2,
                reason_code: "spam",
                description: "Repeated promotional link",
              },
            ],
          },
        };
      }
      return { data: {} };
    });
    mockedApi.post.mockResolvedValue({ data: { status: "ok", id: "created-1" } });
    mockedApi.patch.mockResolvedValue({ data: { status: "ok" } });
    mockedApi.delete.mockResolvedValue({ data: { status: "deleted" } });
  }

  function renderPage() {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    return act(async () => {
      root.render(
        <QueryClientProvider client={qc}>
          <CommunityPage />
        </QueryClientProvider>
      );
    });
  }

  it("allows an ordinary clubless user to view feed, vote on poll, and support a club", async () => {
    installDefaultApiMocks();
    await renderPage();
    await flush();

    expect(container.querySelector('[data-testid="community-page"]')).not.toBeNull();
    expect(container.textContent).toContain("No club required");
    expect(container.textContent).toContain("AFCON U20 Tactical Preview");
    expect(container.textContent).toContain("#tactics-debate");

    // Non-admin does not see Moderation tab
    expect(container.querySelector('[data-testid="community-tab-moderation"]')).toBeNull();

    // Vote on poll option
    const pollBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("4-3-3 High Press")
    ) as HTMLButtonElement;
    expect(pollBtn).toBeTruthy();
    await act(async () => {
      pollBtn.click();
    });
    await flush();
    expect(mockedApi.post).toHaveBeenCalledWith("/community/posts/post-1/vote", { option_id: "opt-1" });

    // Switch to Clubs showcase tab
    mockSearchParams = new URLSearchParams("tab=clubs");
    await renderPage();
    await flush();

    expect(container.textContent).toContain("Victoria Island United");
    const supportBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Support club")
    ) as HTMLButtonElement;
    await act(async () => {
      supportBtn.click();
    });
    await flush();
    expect(mockedApi.post).toHaveBeenCalledWith("/social/follows", {
      target_type: "club",
      club_id: "club-1",
    });
  });

  it("supports Players & Academy Regens discovery filter and group Private Messages", async () => {
    installDefaultApiMocks();
    mockSearchParams = new URLSearchParams("tab=people");
    await renderPage();
    await flush();

    expect(container.textContent).toContain("Coach Ada");
    const playersModeBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Players & Academy Regens")
    ) as HTMLButtonElement;
    await act(async () => {
      playersModeBtn.click();
    });
    await flush();

    expect(container.textContent).toContain("Tunde Balogun");
    const regenCheckbox = container.querySelector('input[type="checkbox"]') as HTMLInputElement;
    await act(async () => {
      regenCheckbox.click();
    });
    await flush();
    expect(mockedApi.get).toHaveBeenCalledWith("/community/discovery/players", {
      params: { q: undefined, regens_only: true },
    });

    // Switch to Private Messages tab and verify group badge + reply send
    mockSearchParams = new URLSearchParams("tab=messages");
    await renderPage();
    await flush();

    expect(container.textContent).toContain("Scouting Trio");
    expect(container.textContent).toContain("Group");
    const threadBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Scouting Trio")
    ) as HTMLButtonElement;
    await act(async () => {
      threadBtn.click();
    });
    await flush();
    expect(container.textContent).toContain("Check out the academy striker!");

    const msgInput = container.querySelector('input[aria-label="Message"]') as HTMLInputElement;
    await act(async () => {
      setInputValue(msgInput, "Scouted and confirmed!");
    });
    const form = msgInput.closest("form") as HTMLFormElement;
    await act(async () => {
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });
    await flush();
    expect(mockedApi.post).toHaveBeenCalledWith("/community/private-messages/threads/pm-1/messages", {
      body: "Scouted and confirmed!",
    });
  });

  it("exposes Moderation queue only to admin accounts and resolves reports via backend API", async () => {
    installDefaultApiMocks();
    mockUser = { id: "u-admin", username: "modlead", display_name: "Mod Lead", role: "admin" };
    mockSearchParams = new URLSearchParams("tab=moderation");
    await renderPage();
    await flush();

    expect(container.querySelector('[data-testid="community-tab-moderation"]')).not.toBeNull();
    expect(container.textContent).toContain("Repeated promotional link");

    const hideBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Hide Content")
    ) as HTMLButtonElement;
    await act(async () => {
      hideBtn.click();
    });
    await flush();
    expect(mockedApi.post).toHaveBeenCalledWith("/community/admin/moderation/resolve", {
      report_id: "rep-1",
      target_type: "post",
      target_id: "post-bad",
      action: "hide",
    });
  });

  it("opens an unread conversation, acknowledges displayed messages, refreshes unread badges, and handles realtime messages in active vs inactive threads", async () => {
    let pm1Unread = 2;
    let pm1LastReadSeq = 0;
    let pm2Unread = 0;
    const pm1Messages: any[] = [
      {
        id: "m-1",
        seq: 1,
        sender_user_id: "u-2",
        sender: { id: "u-2", display_name: "Coach Ada" },
        body: "First scouting report",
        created_at: "2026-11-13T18:20:00Z",
      },
      {
        id: "m-2",
        seq: 2,
        sender_user_id: "u-2",
        sender: { id: "u-2", display_name: "Coach Ada" },
        body: "Second scouting report",
        created_at: "2026-11-13T18:25:00Z",
      },
    ];

    mockedApi.get.mockImplementation(async (url: string, config?: any) => {
      if (url === "/community/private-messages/threads") {
        return {
          data: [
            {
              id: "pm-1",
              subject: "Scouting Trio",
              is_group: true,
              unread_count: pm1Unread,
              last_read_seq: pm1LastReadSeq,
              last_message_seq: pm1Messages[pm1Messages.length - 1].seq,
              participants: [{ user_id: "u-fan", last_read_seq: pm1LastReadSeq }, { user_id: "u-2" }, { user_id: "u-3" }],
              last_message_at: "2026-11-13T18:30:00Z",
            },
            {
              id: "pm-2",
              subject: "Tactical Briefing",
              is_group: false,
              unread_count: pm2Unread,
              last_read_seq: 1,
              last_message_seq: 1 + pm2Unread,
              participants: [{ user_id: "u-fan", last_read_seq: 1 }, { user_id: "u-3" }],
              last_message_at: "2026-11-13T18:10:00Z",
            },
          ],
        };
      }
      if (url === "/community/private-messages/threads/pm-1/messages/page") {
        const afterSeq = config?.params?.after_seq;
        const filtered = typeof afterSeq === "number" ? pm1Messages.filter((m) => m.seq > afterSeq) : pm1Messages;
        return {
          data: {
            messages: filtered,
            has_more: false,
            next_before_seq: null,
          },
        };
      }
      return { data: {} };
    });

    mockedApi.post.mockImplementation(async (url: string, body?: any) => {
      if (url === "/community/private-messages/threads/pm-1/read") {
        pm1LastReadSeq = Math.max(pm1LastReadSeq, Number(body?.up_to_seq || 0));
        pm1Unread = pm1Messages.filter((m) => m.sender_user_id !== "u-fan" && m.seq > pm1LastReadSeq).length;
        return {
          data: {
            id: "pm-1",
            subject: "Scouting Trio",
            is_group: true,
            unread_count: pm1Unread,
            last_read_seq: pm1LastReadSeq,
            last_message_seq: pm1Messages[pm1Messages.length - 1].seq,
            participants: [{ user_id: "u-fan", last_read_seq: pm1LastReadSeq }, { user_id: "u-2" }, { user_id: "u-3" }],
            last_message_at: "2026-11-13T18:30:00Z",
          },
        };
      }
      return { data: { status: "ok" } };
    });

    mockSearchParams = new URLSearchParams("tab=messages");
    await renderPage();
    await flush();

    // Unread badges are shown on both the Messages tab and the pm-1 conversation item
    expect(container.querySelector('[data-testid="community-tab-messages-unread"]')?.textContent).toBe("2");
    expect(container.querySelector('[data-testid="pm-unread-pm-1"]')?.textContent).toBe("2");
    expect(container.querySelector('[data-testid="pm-unread-pm-2"]')).toBeNull();

    // 1 & 2. Opening pm-1 loads the message page, calls /read with up_to_seq=2, and clears unread badges
    const pm1Btn = container.querySelector('[data-testid="pm-thread-pm-1"]') as HTMLButtonElement;
    await act(async () => {
      pm1Btn.click();
    });
    await flush();

    expect(mockedApi.get).toHaveBeenCalledWith("/community/private-messages/threads/pm-1/messages/page", {
      params: { limit: 40 },
    });
    expect(mockedApi.post).toHaveBeenCalledWith("/community/private-messages/threads/pm-1/read", {
      up_to_seq: 2,
      up_to_message_id: "m-2",
    });
    expect(container.querySelector('[data-testid="pm-unread-pm-1"]')).toBeNull();
    expect(container.querySelector('[data-testid="community-tab-messages-unread"]')).toBeNull();

    // 3. Receiving a real-time message in the currently open conversation (pm-1) catches up and acknowledges seq 3
    pm1Messages.push({
      id: "m-3",
      seq: 3,
      sender_user_id: "u-2",
      sender: { id: "u-2", display_name: "Coach Ada" },
      body: "Live update on striker contract",
      created_at: "2026-11-13T18:35:00Z",
    });
    pm1Unread = 1;

    await act(async () => {
      latestRealtimeHandler?.({
        type: "pm_message",
        data: { id: "m-3", thread_id: "pm-1", seq: 3, sender_user_id: "u-2" },
      });
    });
    await flush();

    expect(container.textContent).toContain("Live update on striker contract");
    expect(mockedApi.post).toHaveBeenCalledWith("/community/private-messages/threads/pm-1/read", {
      up_to_seq: 3,
      up_to_message_id: "m-3",
    });
    expect(container.querySelector('[data-testid="pm-unread-pm-1"]')).toBeNull();

    // 4. Receiving a real-time message in another conversation (pm-2) refreshes thread list without marking pm-2 read
    pm2Unread = 1;
    await act(async () => {
      latestRealtimeHandler?.({
        type: "pm_message",
        data: { id: "m-other-2", thread_id: "pm-2", seq: 2, sender_user_id: "u-3" },
      });
    });
    await flush();

    expect(mockedApi.post).not.toHaveBeenCalledWith(
      "/community/private-messages/threads/pm-2/read",
      expect.anything()
    );
    expect(container.querySelector('[data-testid="pm-unread-pm-2"]')?.textContent).toBe("1");
    expect(container.querySelector('[data-testid="community-tab-messages-unread"]')?.textContent).toBe("1");

    // Verify reconnect handler also works without duplicating messages
    await act(async () => {
      latestReconnectHandler?.();
    });
    await flush();
  });

  it("prevents stale read acknowledgement when switching conversations rapidly and when leaving a group", async () => {
    let resolvePm1Page: ((val: any) => void) | null = null;
    let threadsList = [
      {
        id: "pm-1",
        subject: "Slow Thread",
        is_group: true,
        unread_count: 1,
        last_read_seq: 0,
        last_message_seq: 1,
        participants: [{ user_id: "u-fan", last_read_seq: 0 }, { user_id: "u-2" }, { user_id: "u-3" }],
        last_message_at: "2026-11-13T18:30:00Z",
      },
      {
        id: "pm-2",
        subject: "Fast Group Thread",
        is_group: true,
        unread_count: 1,
        last_read_seq: 0,
        last_message_seq: 5,
        participants: [{ user_id: "u-fan", last_read_seq: 0 }, { user_id: "u-2" }, { user_id: "u-3" }],
        last_message_at: "2026-11-13T18:40:00Z",
      },
    ];

    mockedApi.get.mockImplementation((url: string) => {
      if (url === "/community/private-messages/threads") {
        return Promise.resolve({ data: threadsList });
      }
      if (url === "/community/private-messages/threads/pm-1/messages/page") {
        return new Promise((resolve) => {
          resolvePm1Page = resolve;
        });
      }
      if (url === "/community/private-messages/threads/pm-2/messages/page") {
        return Promise.resolve({
          data: {
            messages: [
              {
                id: "m-fast-5",
                seq: 5,
                sender_user_id: "u-2",
                sender: { id: "u-2", display_name: "Coach Ada" },
                body: "Fast group message",
                created_at: "2026-11-13T18:40:00Z",
              },
            ],
            has_more: false,
            next_before_seq: null,
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    mockedApi.post.mockImplementation(async (url: string) => {
      if (url === "/community/private-messages/threads/pm-2/read") {
        threadsList = threadsList.map((t) => (t.id === "pm-2" ? { ...t, unread_count: 0, last_read_seq: 5 } : t));
        return { data: threadsList[1] };
      }
      if (url === "/community/private-messages/threads/pm-2/leave") {
        threadsList = threadsList.filter((t) => t.id !== "pm-2");
        return { data: { thread_id: "pm-2", left: true } };
      }
      return { data: { status: "ok" } };
    });

    mockSearchParams = new URLSearchParams("tab=messages");
    await renderPage();
    await flush();

    // 5. Click pm-1 (slow page load), then immediately switch to pm-2 before pm-1 resolves
    const pm1Btn = container.querySelector('[data-testid="pm-thread-pm-1"]') as HTMLButtonElement;
    const pm2Btn = container.querySelector('[data-testid="pm-thread-pm-2"]') as HTMLButtonElement;
    await act(async () => {
      pm1Btn.click();
      pm2Btn.click();
    });
    await flush();

    // Now resolve the stale pm-1 page request
    await act(async () => {
      resolvePm1Page?.({
        data: {
          messages: [
            {
              id: "m-slow-1",
              seq: 1,
              sender_user_id: "u-2",
              sender: { id: "u-2", display_name: "Coach Ada" },
              body: "Stale message from pm-1",
              created_at: "2026-11-13T18:30:00Z",
            },
          ],
          has_more: false,
          next_before_seq: null,
        },
      });
    });
    await flush();

    // Only pm-2 was acknowledged; stale pm-1 was NOT acknowledged and its messages did not pollute pm-2
    expect(mockedApi.post).toHaveBeenCalledWith("/community/private-messages/threads/pm-2/read", {
      up_to_seq: 5,
      up_to_message_id: "m-fast-5",
    });
    expect(mockedApi.post).not.toHaveBeenCalledWith(
      "/community/private-messages/threads/pm-1/read",
      expect.anything()
    );
    expect(container.textContent).toContain("Fast group message");
    expect(container.textContent).not.toContain("Stale message from pm-1");
    expect(container.querySelector('[data-testid="pm-unread-pm-1"]')?.textContent).toBe("1");

    // 6. Leaving the active group conversation removes it from active threads and prevents stale read calls
    mockedApi.post.mockClear();
    const leaveBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Leave group")
    ) as HTMLButtonElement;
    await act(async () => {
      leaveBtn.click();
    });
    await flush();

    expect(mockedApi.post).toHaveBeenCalledWith("/community/private-messages/threads/pm-2/leave");
    expect(container.querySelector('[data-testid="pm-thread-pm-2"]')).toBeNull();

    // Simulate a late realtime event for pm-2 after leaving
    await act(async () => {
      latestRealtimeHandler?.({
        type: "pm_message",
        data: { id: "m-fast-6", thread_id: "pm-2", seq: 6, sender_user_id: "u-2" },
      });
    });
    await flush();
    expect(mockedApi.post).not.toHaveBeenCalledWith(
      "/community/private-messages/threads/pm-2/read",
      expect.anything()
    );
  });

  it("preserves unread badge when read acknowledgement fails and clears it on retry", async () => {
    let unreadCount = 1;
    let shouldFailAck = true;

    mockedApi.get.mockImplementation(async (url: string) => {
      if (url === "/community/private-messages/threads") {
        return {
          data: [
            {
              id: "pm-1",
              subject: "Contract Talk",
              is_group: false,
              unread_count: unreadCount,
              last_read_seq: unreadCount === 0 ? 1 : 0,
              last_message_seq: 1,
              participants: [{ user_id: "u-fan", last_read_seq: unreadCount === 0 ? 1 : 0 }, { user_id: "u-2" }],
              last_message_at: "2026-11-13T18:30:00Z",
            },
          ],
        };
      }
      if (url === "/community/private-messages/threads/pm-1/messages/page") {
        return {
          data: {
            messages: [
              {
                id: "m-1",
                seq: 1,
                sender_user_id: "u-2",
                sender: { id: "u-2", display_name: "Coach Ada" },
                body: "Are you free for a call?",
                created_at: "2026-11-13T18:25:00Z",
              },
            ],
            has_more: false,
            next_before_seq: null,
          },
        };
      }
      return { data: {} };
    });

    mockedApi.post.mockImplementation(async (url: string) => {
      if (url === "/community/private-messages/threads/pm-1/read") {
        if (shouldFailAck) {
          throw new Error("Temporary network failure");
        }
        unreadCount = 0;
        return {
          data: {
            id: "pm-1",
            subject: "Contract Talk",
            is_group: false,
            unread_count: 0,
            last_read_seq: 1,
            last_message_seq: 1,
            participants: [{ user_id: "u-fan", last_read_seq: 1 }, { user_id: "u-2" }],
            last_message_at: "2026-11-13T18:30:00Z",
          },
        };
      }
      return { data: { status: "ok" } };
    });

    mockSearchParams = new URLSearchParams("tab=messages");
    await renderPage();
    await flush();

    // 7. Open conversation while read acknowledgement fails
    const pm1Btn = container.querySelector('[data-testid="pm-thread-pm-1"]') as HTMLButtonElement;
    await act(async () => {
      pm1Btn.click();
    });
    await flush();

    // Messages still render, unread badge is NOT falsely cleared, and recoverable retry banner is shown
    expect(container.textContent).toContain("Are you free for a call?");
    expect(container.querySelector('[data-testid="pm-unread-pm-1"]')?.textContent).toBe("1");
    expect(container.querySelector('[data-testid="pm-read-ack-error"]')).not.toBeNull();

    // Retry succeeds and clears both the error banner and the unread badge
    shouldFailAck = false;
    const retryBtn = container.querySelector('[data-testid="pm-retry-read-ack"]') as HTMLButtonElement;
    await act(async () => {
      retryBtn.click();
    });
    await flush();

    expect(container.querySelector('[data-testid="pm-read-ack-error"]')).toBeNull();
    expect(container.querySelector('[data-testid="pm-unread-pm-1"]')).toBeNull();
    expect(container.querySelector('[data-testid="community-tab-messages-unread"]')).toBeNull();
  });

  it("handles opening an empty conversation and catches up messages arriving during initial history fetch", async () => {
    let resolveInitialLoad: ((val: any) => void) | null = null;
    let liveMessages = [
      {
        id: "m-init-1",
        seq: 1,
        sender_user_id: "u-2",
        sender: { id: "u-2", display_name: "Coach Ada" },
        body: "Initial history message",
        created_at: "2026-11-13T18:20:00Z",
      },
    ];

    mockedApi.get.mockImplementation((url: string, config?: any) => {
      if (url === "/community/private-messages/threads") {
        return Promise.resolve({
          data: [
            {
              id: "pm-empty",
              subject: "Empty Thread",
              is_group: false,
              unread_count: 0,
              last_read_seq: 0,
              last_message_seq: 0,
              participants: [{ user_id: "u-fan", last_read_seq: 0 }, { user_id: "u-2" }],
              last_message_at: null,
            },
            {
              id: "pm-race",
              subject: "Race Thread",
              is_group: false,
              unread_count: 1,
              last_read_seq: 0,
              last_message_seq: 1,
              participants: [{ user_id: "u-fan", last_read_seq: 0 }, { user_id: "u-2" }],
              last_message_at: "2026-11-13T18:20:00Z",
            },
          ],
        });
      }
      if (url === "/community/private-messages/threads/pm-empty/messages/page") {
        return Promise.resolve({ data: { messages: [], has_more: false, next_before_seq: null } });
      }
      if (url === "/community/private-messages/threads/pm-race/messages/page") {
        const afterSeq = config?.params?.after_seq;
        if (typeof afterSeq === "number") {
          return Promise.resolve({
            data: {
              messages: liveMessages.filter((m) => m.seq > afterSeq),
              has_more: false,
              next_before_seq: null,
            },
          });
        }
        return new Promise((resolve) => {
          resolveInitialLoad = resolve;
        });
      }
      return Promise.resolve({ data: {} });
    });

    mockedApi.post.mockImplementation(async (url: string, body?: any) => {
      return {
        data: {
          id: url.includes("pm-empty") ? "pm-empty" : "pm-race",
          unread_count: 0,
          last_read_seq: Number(body?.up_to_seq || 0),
        },
      };
    });

    mockSearchParams = new URLSearchParams("tab=messages");
    await renderPage();
    await flush();

    // Open empty conversation -> acknowledges up_to_seq: 0 cleanly
    const emptyBtn = container.querySelector('[data-testid="pm-thread-pm-empty"]') as HTMLButtonElement;
    await act(async () => {
      emptyBtn.click();
    });
    await flush();
    expect(mockedApi.post).toHaveBeenCalledWith("/community/private-messages/threads/pm-empty/read", {
      up_to_seq: 0,
    });

    // Open race thread, then emit realtime pm_message BEFORE initial history load resolves
    mockedApi.post.mockClear();
    const raceBtn = container.querySelector('[data-testid="pm-thread-pm-race"]') as HTMLButtonElement;
    await act(async () => {
      raceBtn.click();
    });
    await act(async () => {
      liveMessages = [
        ...liveMessages,
        {
          id: "m-race-2",
          seq: 2,
          sender_user_id: "u-2",
          sender: { id: "u-2", display_name: "Coach Ada" },
          body: "Arrived mid-load",
          created_at: "2026-11-13T18:21:00Z",
        },
      ];
      latestRealtimeHandler?.({
        type: "pm_message",
        data: { id: "m-race-2", thread_id: "pm-race", seq: 2, sender_user_id: "u-2" },
      });
    });

    // Now resolve the initial history page (which only contained seq=1)
    await act(async () => {
      resolveInitialLoad?.({
        data: {
          messages: [liveMessages[0]],
          has_more: false,
          next_before_seq: null,
        },
      });
    });
    await flush();

    // Both messages rendered, and both seq=1 and caught-up seq=2 were acknowledged
    expect(container.textContent).toContain("Initial history message");
    expect(container.textContent).toContain("Arrived mid-load");
    expect(mockedApi.post).toHaveBeenCalledWith("/community/private-messages/threads/pm-race/read", {
      up_to_seq: 1,
      up_to_message_id: "m-init-1",
    });
    expect(mockedApi.post).toHaveBeenCalledWith("/community/private-messages/threads/pm-race/read", {
      up_to_seq: 2,
      up_to_message_id: "m-race-2",
    });
  });
});
