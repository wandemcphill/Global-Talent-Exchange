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
});
