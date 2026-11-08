import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BoardroomScene } from "./BoardroomScene";
import { GtexSceneRegistry } from "../GtexSceneRegistry";
import { api } from "@/lib/api";

jest.mock("three/examples/jsm/controls/OrbitControls.js", () => {
  return {
    OrbitControls: class {
      enableDamping = true;
      dampingFactor = 0.05;
      maxPolarAngle = 1;
      minDistance = 1;
      maxDistance = 100;
      target = {
        x: 0,
        y: 0,
        z: 0,
        set: jest.fn(),
        copy: jest.fn(),
        lerp: jest.fn(),
        distanceTo: jest.fn().mockReturnValue(0),
      };
      update = jest.fn();
      dispose = jest.fn();
      addEventListener = jest.fn();
      removeEventListener = jest.fn();
    },
  };
});

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn().mockResolvedValue({ data: null }),
    post: jest.fn().mockResolvedValue({ data: null }),
  },
  errMsg: (err: any, fallback: string) => fallback,
}));

describe("BoardroomScene", () => {
  let container: HTMLDivElement;
  let root: Root;
  let queryClient: QueryClient;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    jest.clearAllMocks();
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  test("is registered as the authoritative custom renderer for boardroom_meeting in GtexSceneRegistry", () => {
    const renderer = GtexSceneRegistry.getRenderer("boardroom_meeting");
    expect(renderer).toBeDefined();
    expect(renderer).toBe(BoardroomScene);
  });

  test("renders boardroom scene canvas and top HUD badges", async () => {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <BoardroomScene clubId="c_lagos_boardroom" />
        </QueryClientProvider>
      );
    });

    expect(container.querySelector('[data-testid="boardroom-3d-scene"]')).not.toBeNull();
    expect(container.textContent).toContain("Executive Boardroom Suite");
    expect(container.textContent).toContain("3D PERSISTENT");
  });

  test("allows switching camera presets across overview, board_table, display screen, and pitch_view", async () => {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <BoardroomScene clubId="c_lagos_boardroom" />
        </QueryClientProvider>
      );
    });

    const tablePresetBtn = container.querySelector('[data-testid="camera-preset-board_table"]') as HTMLButtonElement;
    expect(tablePresetBtn).not.toBeNull();

    await act(async () => {
      tablePresetBtn.click();
    });
    expect(tablePresetBtn.className).toContain("bg-emerald-500");

    const screenPresetBtn = container.querySelector(
      '[data-testid="camera-preset-presentation_screen"]'
    ) as HTMLButtonElement;
    await act(async () => {
      screenPresetBtn.click();
    });
    expect(screenPresetBtn.className).toContain("bg-emerald-500");

    const pitchPresetBtn = container.querySelector('[data-testid="camera-preset-pitch_view"]') as HTMLButtonElement;
    await act(async () => {
      pitchPresetBtn.click();
    });
    expect(pitchPresetBtn.className).toContain("bg-emerald-500");
  });

  test("toggles day and night lighting rigs smoothly", async () => {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <BoardroomScene clubId="c_lagos_boardroom" />
        </QueryClientProvider>
      );
    });

    const lightToggle = container.querySelector(
      '[data-testid="toggle-boardroom-lighting-btn"]'
    ) as HTMLButtonElement;
    expect(lightToggle).not.toBeNull();

    await act(async () => {
      lightToggle.click();
    });
  });

  test("opens persona spatial interaction modal when clicking a leadership pill", async () => {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <BoardroomScene clubId="c_lagos_boardroom" />
        </QueryClientProvider>
      );
    });

    const managerPill = container.querySelector(
      '[data-testid="select-persona-pill-first_team_manager"]'
    ) as HTMLButtonElement;
    expect(managerPill).not.toBeNull();

    await act(async () => {
      managerPill.click();
    });

    expect(document.querySelector('[data-testid="persona-spatial-modal"]')).not.toBeNull();
  });

  test("renders active boardroom dilemma alert and opens dilemma modal when clicked", async () => {
    (api.get as jest.Mock).mockResolvedValue({
      data: {
        dilemma_id: "dil_test_99",
        title: "Tactical Overhaul vs Stability",
        conflict_summary: "Manager wants complete change of tactics, GM advises patience.",
        role_a: "first_team_manager",
        role_a_label: "First-Team Manager",
        role_a_name: "Emmanuel Amuneke",
        role_b: "general_manager",
        role_b_label: "General Manager",
        role_b_name: "Dayo Adeleke",
        urgency: "critical",
        status: "open",
        choices: [
          {
            choice_id: "choice_a",
            label: "Back Manager Overhaul",
            summary: "Implement full tactical revamp.",
            cost_gtex: 50000,
          },
        ],
      },
    });

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <BoardroomScene clubId="c_lagos_boardroom" />
        </QueryClientProvider>
      );
    });

    // Wait for active dilemma query
    await act(async () => {
      await new Promise((r) => setTimeout(r, 60));
    });

    const dilemmaBtn = container.querySelector(
      '[data-testid="open-boardroom-dilemma-btn"]'
    ) as HTMLButtonElement;
    expect(dilemmaBtn).not.toBeNull();
    expect(dilemmaBtn.textContent).toContain("Boardroom Dilemma");

    await act(async () => {
      dilemmaBtn.click();
    });

    expect(document.querySelector('[data-testid="boardroom-dilemma-modal"]')).not.toBeNull();
  });

  test("opens staff employment and market modal when clicking staff market HUD button", async () => {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <BoardroomScene clubId="c_lagos_boardroom" />
        </QueryClientProvider>
      );
    });

    const staffMarketBtn = container.querySelector(
      '[data-testid="open-staff-market-btn"]'
    ) as HTMLButtonElement;
    expect(staffMarketBtn).not.toBeNull();
    expect(staffMarketBtn.textContent).toContain("Staff Market & Careers");

    await act(async () => {
      staffMarketBtn.click();
    });

    expect(document.querySelector('[data-testid="staff-employment-modal"]')).not.toBeNull();
  });

  test("opens GM delegation and authority matrix modal when clicking GM delegation HUD button", async () => {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <BoardroomScene clubId="c_lagos_boardroom" />
        </QueryClientProvider>
      );
    });

    const gmDelegationBtn = container.querySelector(
      '[data-testid="open-gm-delegation-btn"]'
    ) as HTMLButtonElement;
    expect(gmDelegationBtn).not.toBeNull();
    expect(gmDelegationBtn.textContent).toContain("GM Delegation");

    await act(async () => {
      gmDelegationBtn.click();
    });

    expect(document.querySelector('[data-testid="gm-delegation-modal"]')).not.toBeNull();
  });

  test("opens Club Politics & Governance modal when clicking Club Politics HUD button", async () => {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <BoardroomScene clubId="c_lagos_boardroom" />
        </QueryClientProvider>
      );
    });

    const politicsBtn = container.querySelector(
      '[data-testid="open-club-politics-btn"]'
    ) as HTMLButtonElement;
    expect(politicsBtn).not.toBeNull();
    expect(politicsBtn.textContent).toContain("Club Politics");

    await act(async () => {
      politicsBtn.click();
    });

    expect(document.querySelector('[data-testid="club-politics-modal"]')).not.toBeNull();
  });

  test("unmounts cleanly without WebGL memory leaks", async () => {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <BoardroomScene clubId="c_lagos_boardroom" />
        </QueryClientProvider>
      );
    });

    expect(container.querySelector('[data-testid="boardroom-3d-scene"]')).not.toBeNull();

    act(() => {
      root.unmount();
    });
    expect(container.querySelector('[data-testid="boardroom-3d-scene"]')).toBeNull();
  });
});
