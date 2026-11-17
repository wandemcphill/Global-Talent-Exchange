import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MatchCenter from "../MatchCenter";

const mockGet = jest.fn();
const mockPost = jest.fn();
const mockToastSuccess = jest.fn();
const mockToastError = jest.fn();
const mockToastInfo = jest.fn();

jest.mock("react-router-dom", () => ({
  __esModule: true,
  Link: ({ children, to, ...rest }: any) => (
    <a href={to} {...rest}>
      {children}
    </a>
  ),
  useParams: () => ({ id: "match-live-1" }),
  useSearchParams: () => [new URLSearchParams("live=1&dismissWalkout=1"), jest.fn()],
}));

jest.mock("sonner", () => ({
  __esModule: true,
  toast: {
    success: (...args: any[]) => mockToastSuccess(...args),
    error: (...args: any[]) => mockToastError(...args),
    info: (...args: any[]) => mockToastInfo(...args),
  },
}));

jest.mock("@/lib/api", () => ({
  __esModule: true,
  API: "http://127.0.0.1:8000/api",
  api: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
  },
  errMsg: (e: any) => String(e?.message || e || "Error"),
  tokens: {
    get: () => "jwt-manager-token",
  },
}));

jest.mock("@/lib/owner", () => ({
  __esModule: true,
  useActiveClub: () => ({ active: { club_id: "club-home" } }),
  useRefreshOwner: () => jest.fn(),
}));

jest.mock("@/lib/skin-engine", () => ({
  __esModule: true,
  useSkin: () => ({
    getModuleView: () => ({}),
    setModuleView: jest.fn(),
  }),
}));

jest.mock("@/components/gtex/ui", () => ({
  __esModule: true,
  Btn: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  Chip: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  Loading: ({ label }: any) => <div data-testid="loading">{label}</div>,
  Panel: ({ title, right, children }: any) => (
    <section>
      {title && <h2>{title}</h2>}
      {right}
      {children}
    </section>
  ),
}));

jest.mock("@/lib/3d/broadcast/useMatchSpectatorStream", () => ({
  __esModule: true,
  useMatchSpectatorStream: () => ({
    connectionStatus: "connected",
    viewerCount: 42,
    matchMetadata: {
      canonical_execution: {
        execution_revision: 3,
        pause_replay_enabled: false,
      },
    },
    lastFrame: {
      frame_id: "frame-live-45",
      time_seconds: 180,
      clock_minute: 45,
      home_score: 1,
      away_score: 0,
      ball: { position: { x: 52, y: 50 }, height: 0, state: "rolling", owner_player_id: "p1" },
      players: [
        {
          player_id: "p1",
          team_id: "club-home",
          side: "home",
          label: "B. Starter",
          shirt_number: 9,
          role: "ST",
          active: true,
          position: { x: 70, y: 50 },
        },
        {
          player_id: "p2",
          team_id: "club-away",
          side: "away",
          label: "A. Defender",
          shirt_number: 4,
          role: "CB",
          active: true,
          position: { x: 30, y: 50 },
        },
      ],
    },
    recentEvents: [],
    latestScore: { home_score: 1, away_score: 0, minute: 45, status: "half_time" },
    latencyMs: 18,
    reconnectAttempts: 0,
    sendReaction: jest.fn(),
    sendChatMessage: jest.fn(),
    reconnect: jest.fn(),
    disconnect: jest.fn(),
  }),
}));

jest.mock("@/lib/3d/broadcast/useMatchFullTimeGovernance", () => ({
  __esModule: true,
  useMatchFullTimeGovernance: () => undefined,
}));

jest.mock("@/components/gtex/Cinema3DStage", () => ({
  __esModule: true,
  Cinema3DStage: () => null,
}));

jest.mock("@/components/gtex/PressRoomStage", () => ({
  __esModule: true,
  PressRoomStage: () => null,
}));

jest.mock("@/components/gtex/MatchdayLineupBroadcast", () => ({
  __esModule: true,
  MatchdayLineupBroadcast: () => null,
}));

jest.mock("@/components/gtex/ApexWidgets", () => ({
  __esModule: true,
  HolographicPlayerCard: () => null,
}));

jest.mock("@/components/advertising/GtexMatchBroadcastAds", () => ({
  __esModule: true,
  MatchSponsorIdentificationBadge: () => null,
  SilentMatchBroadcastPanel: () => null,
  useMatchCommercialInventory: () => ({ placements: [] }),
}));

jest.mock("@/lib/3d/gifting/CinematicGiftingEngine", () => ({
  __esModule: true,
  CinematicGiftingEngine: () => null,
}));

jest.mock("@/match2d/matchAudio", () => ({
  __esModule: true,
  sharedMatchAudio: {
    setEnabled: jest.fn(),
    setMuted: jest.fn(),
    updateAtmosphere: jest.fn(),
    playEventCue: jest.fn(),
  },
}));

jest.mock("../../match2d/OrthographicPitch", () => ({
  __esModule: true,
  OrthographicPitch: () => <div data-testid="mock-orthographic-pitch" />,
}));

async function flushRender(cycles = 6): Promise<void> {
  for (let i = 0; i < cycles; i += 1) {
    await act(async () => {
      await Promise.resolve();
      await new Promise((resolve) => setTimeout(resolve, 5));
    });
  }
}

function buildStatePayload(revision: number, subCount = 0) {
  return {
    match_id: "match-live-1",
    phase: "half_time",
    minute: 45,
    time_seconds: 180,
    snapshot_version: revision,
    execution_revision: revision,
    pause_replay_enabled: false,
    assigned_duration_seconds: 600,
    broadcast_session: {
      broadcast_id: "bc-match-live-1",
      broadcast_status: "live",
      sync_strategy: "canonical_live_execution",
      pause_replay_enabled: false,
      assigned_duration_seconds: 600,
      execution_revision: revision,
      current_minute: 45,
    },
    home: {
      team_id: "club-home",
      team_name: "Lagos United",
      short_name: "LAG",
      formation: "4-3-3",
      score: 1,
      players: [
        {
          player_id: "p1",
          name: "B. Starter",
          shirt_number: 9,
          role: "ST",
          active: true,
          x: 70,
          y: 50,
        },
      ],
      bench: [
        {
          player_id: "b1",
          name: "S. Impact",
          shirt_number: 18,
          role: "ST",
        },
      ],
    },
    away: {
      team_id: "club-away",
      team_name: "Abuja FC",
      short_name: "ABJ",
      formation: "4-4-2",
      score: 0,
      players: [
        {
          player_id: "p2",
          name: "A. Defender",
          shirt_number: 4,
          role: "CB",
          active: true,
          x: 30,
          y: 50,
        },
      ],
      bench: [],
    },
    ball: { x: 52, y: 50, z: 0 },
    events: [],
    stats: {
      home_shots: 6,
      away_shots: 2,
      home_possession: 58,
      away_possession: 42,
      home_expected_goals: 1.24,
      away_expected_goals: 0.31,
      home_yellow_cards: 1,
      away_yellow_cards: 1,
      home_red_cards: 0,
      away_red_cards: 0,
    },
    applied_substitution_count: subCount,
  };
}

function buildTacticsPayload({
  canEdit,
  revision,
  subCount = 0,
  pendingEffectiveMinute = null,
}: {
  canEdit: boolean;
  revision: number;
  subCount?: number;
  pendingEffectiveMinute?: number | null;
}) {
  return {
    match_id: "match-live-1",
    execution_revision: revision,
    current_minute: 45,
    pause_replay_enabled: false,
    authorized_tactical_side: canEdit ? "home" : null,
    authorized_sides: canEdit ? ["home"] : [],
    can_edit_tactics: canEdit,
    home: {
      team_id: "club-home",
      formation: revision > 3 ? "4-2-3-1" : "4-3-3",
      mentality: revision > 3 ? "attacking" : "balanced",
      press_intensity: revision > 3 ? 80 : 65,
      defensive_line: 68,
      tempo: 52,
      risk_level: 45,
      substitution_count: subCount,
      instructions: revision > 3 ? ["high_press"] : [],
      pending_substitutions: [],
      pending_effective_minute: pendingEffectiveMinute,
    },
    away: {
      team_id: "club-away",
      formation: "4-4-2",
      mentality: "balanced",
      press_intensity: 50,
      defensive_line: 50,
      tempo: 50,
      risk_level: 50,
      substitution_count: 0,
      instructions: [],
      pending_substitutions: [],
      pending_effective_minute: null,
    },
  };
}

function setFormValue(element: HTMLInputElement | HTMLSelectElement, value: string) {
  const proto =
    element instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
  const descriptor = Object.getOwnPropertyDescriptor(proto, "value");
  descriptor?.set?.call(element, value);
  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
}

describe("Canonical live manager tactics & conflict governance in MatchCenter", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    mockGet.mockReset();
    mockPost.mockReset();
    mockToastSuccess.mockReset();
    mockToastError.mockReset();
    mockToastInfo.mockReset();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  function renderMatchCenter() {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <MatchCenter />
        </QueryClientProvider>,
      );
    });
  }

  it("submits manager tactical order & substitution with expected_revision and idempotency_key, while hiding playback controls", async () => {
    let revision = 3;
    let subCount = 0;

    mockGet.mockImplementation(async (url: string) => {
      if (url === "/match-viewer/match-live-1") {
        return {
          data: {
            match_id: "match-live-1",
            duration_seconds: 600,
            pause_replay_enabled: false,
            broadcast_session: {
              broadcast_status: "live",
              sync_strategy: "canonical_live_execution",
              pause_replay_enabled: false,
              assigned_duration_seconds: 600,
            },
            home_team: { team_id: "club-home", team_name: "Lagos United", formation: "4-3-3" },
            away_team: { team_id: "club-away", team_name: "Abuja FC", formation: "4-4-2" },
            events: [],
            frames: [],
          },
        };
      }
      if (url === "/owner/matches/match-live-1") {
        throw new Error("Fallback to /match-viewer");
      }
      if (url === "/matches/match-live-1/state") {
        return { data: buildStatePayload(revision, subCount) };
      }
      if (url === "/matches/match-live-1/tactics") {
        return {
          data: buildTacticsPayload({
            canEdit: true,
            revision,
            subCount,
            pendingEffectiveMinute: revision > 3 ? 46 : null,
          }),
        };
      }
      if (url === "/matches/match-live-1/predictions") {
        return { data: { home: 0, draw: 0, away: 0 } };
      }
      return { data: null };
    });

    mockPost.mockImplementation(async (url: string, body: any) => {
      if (url === "/matches/match-live-1/tactics") {
        revision += 1;
        if (Array.isArray(body?.substitutions) && body.substitutions.length > 0) {
          subCount += body.substitutions.length;
        }
        return {
          data: {
            status: "applied",
            match_id: "match-live-1",
            side: "home",
            execution_revision: revision,
            effective_minute: 46,
            applied_immediately: true,
          },
        };
      }
      return { data: {} };
    });

    renderMatchCenter();
    await flushRender(10);

    // No viewer pause/speed controls on canonical live broadcast
    expect(container.querySelector('[data-testid="match-pause-toggle"]')).toBeNull();
    expect(container.querySelector('[data-testid="match-speed-toggle"]')).toBeNull();

    // Manager editor is active with canonical revision & sub allowance
    const editor = container.querySelector('[data-testid="manager-tactics-editor"]');
    expect(editor).not.toBeNull();
    expect(container.querySelector('[data-testid="tactics-execution-revision"]')?.textContent).toContain(
      "Rev #3",
    );
    expect(container.querySelector('[data-testid="tactics-subs-remaining"]')?.textContent).toContain(
      "Subs: 0/5",
    );

    const formationSelect = container.querySelector('[data-testid="tactics-formation-select"]') as HTMLSelectElement;
    const mentalitySelect = container.querySelector('[data-testid="tactics-mentality-select"]') as HTMLSelectElement;
    const highPressBtn = container.querySelector('[data-testid="tactics-instruction-high_press"]') as HTMLButtonElement;
    const applyBtn = container.querySelector('[data-testid="apply-tactics-btn"]') as HTMLButtonElement;

    await act(async () => {
      setFormValue(formationSelect, "4-2-3-1");
      setFormValue(mentalitySelect, "attacking");
      highPressBtn.click();
    });

    await act(async () => {
      applyBtn.click();
    });
    await flushRender(8);

    const firstPost = mockPost.mock.calls.find(([u]) => u === "/matches/match-live-1/tactics");
    expect(firstPost).toBeDefined();
    expect(firstPost?.[1]).toEqual(
      expect.objectContaining({
        side: "home",
        formation: "4-2-3-1",
        mentality: "attacking",
        instructions: ["high_press"],
        expected_revision: 3,
      }),
    );
    expect(typeof firstPost?.[1]?.idempotency_key).toBe("string");
    expect(firstPost?.[1]?.idempotency_key.length).toBeGreaterThan(5);
    expect(container.querySelector('[data-testid="tactics-execution-revision"]')?.textContent).toContain(
      "Rev #4",
    );
    expect(container.querySelector('[data-testid="tactics-effective-minute"]')?.textContent).toContain(
      "46'",
    );

    // Execute live substitution
    const subOutSelect = container.querySelector('[data-testid="sub-out-select"]') as HTMLSelectElement;
    const subInSelect = container.querySelector('[data-testid="sub-in-select"]') as HTMLSelectElement;
    const subBtn = container.querySelector('[data-testid="apply-substitution-btn"]') as HTMLButtonElement;

    await act(async () => {
      setFormValue(subOutSelect, "p1");
      setFormValue(subInSelect, "b1");
    });

    await act(async () => {
      subBtn.click();
    });
    await flushRender(8);

    const subPost = mockPost.mock.calls.filter(([u]) => u === "/matches/match-live-1/tactics")[1];
    expect(subPost?.[1]).toEqual(
      expect.objectContaining({
        side: "home",
        expected_revision: 4,
        substitutions: [
          expect.objectContaining({
            out_player_id: "p1",
            in_player_id: "b1",
          }),
        ],
      }),
    );
    expect(container.querySelector('[data-testid="tactics-subs-remaining"]')?.textContent).toContain(
      "Subs: 1/5",
    );
  });

  it("refreshes canonical tactics and state when server rejects stale expected_revision with HTTP 409", async () => {
    let revision = 3;

    mockGet.mockImplementation(async (url: string) => {
      if (url === "/match-viewer/match-live-1") {
        return {
          data: {
            match_id: "match-live-1",
            duration_seconds: 600,
            pause_replay_enabled: false,
            home_team: { team_id: "club-home", team_name: "Lagos United", formation: "4-3-3" },
            away_team: { team_id: "club-away", team_name: "Abuja FC", formation: "4-4-2" },
            events: [],
            frames: [],
          },
        };
      }
      if (url === "/owner/matches/match-live-1") {
        throw new Error("Fallback to /match-viewer");
      }
      if (url === "/matches/match-live-1/state") {
        return { data: buildStatePayload(revision) };
      }
      if (url === "/matches/match-live-1/tactics") {
        return { data: buildTacticsPayload({ canEdit: true, revision }) };
      }
      if (url === "/matches/match-live-1/predictions") {
        return { data: { home: 0, draw: 0, away: 0 } };
      }
      return { data: null };
    });

    mockPost.mockImplementation(async (url: string) => {
      if (url === "/matches/match-live-1/tactics") {
        revision = 5;
        throw {
          response: {
            status: 409,
            data: { detail: "Stale expected_revision 3; current revision is 5." },
          },
        };
      }
      return { data: {} };
    });

    renderMatchCenter();
    await flushRender(10);

    const applyBtn = container.querySelector('[data-testid="apply-tactics-btn"]') as HTMLButtonElement;
    await act(async () => {
      applyBtn.click();
    });
    await flushRender(10);

    expect(container.querySelector('[data-testid="tactics-error"]')?.textContent).toContain(
      "Stale expected_revision 3; current revision is 5.",
    );
    expect(container.querySelector('[data-testid="tactics-execution-revision"]')?.textContent).toContain(
      "Rev #5",
    );
  });

  it("enforces read-only dugout telemetry for Club Owners and disables playback controls on canonical broadcast", async () => {
    mockGet.mockImplementation(async (url: string) => {
      if (url === "/match-viewer/match-live-1") {
        return {
          data: {
            match_id: "match-live-1",
            duration_seconds: 600,
            pause_replay_enabled: false,
            broadcast_session: {
              broadcast_status: "live",
              sync_strategy: "canonical_live_execution",
              pause_replay_enabled: false,
              assigned_duration_seconds: 600,
            },
            home_team: { team_id: "club-home", team_name: "Lagos United", formation: "4-3-3" },
            away_team: { team_id: "club-away", team_name: "Abuja FC", formation: "4-4-2" },
            events: [],
            frames: [],
          },
        };
      }
      if (url === "/owner/matches/match-live-1") {
        throw new Error("Fallback to /match-viewer");
      }
      if (url === "/matches/match-live-1/state") {
        return { data: buildStatePayload(3) };
      }
      if (url === "/matches/match-live-1/tactics") {
        return { data: buildTacticsPayload({ canEdit: false, revision: 3 }) };
      }
      return { data: null };
    });

    renderMatchCenter();
    await flushRender(10);

    expect(container.textContent).toContain("READ-ONLY DUGOUT TELEMETRY");
    expect(container.querySelector('[data-testid="manager-tactics-editor"]')).toBeNull();
    expect(container.querySelector('[data-testid="match-pause-toggle"]')).toBeNull();
    expect(container.querySelector('[data-testid="match-speed-toggle"]')).toBeNull();
    expect(mockPost).not.toHaveBeenCalled();
  });
});
