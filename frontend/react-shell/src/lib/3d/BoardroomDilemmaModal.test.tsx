import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BoardroomDilemmaModal } from "./BoardroomDilemmaModal";
import { api } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
  },
  errMsg: (err: any, fallback: string) => fallback,
}));

jest.mock("sonner", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

const waitForCondition = async (predicate: () => boolean, timeout = 2500) => {
  const start = Date.now();
  while (!predicate()) {
    if (Date.now() - start > timeout) {
      throw new Error("Timed out waiting for condition");
    }
    await act(async () => {
      await new Promise((r) => setTimeout(r, 25));
    });
  }
};

const mockDilemma = {
  dilemma_id: "dil_101",
  title: "Transfer Ambition vs Wage Budget Discipline",
  conflict_summary:
    "First-Team Manager demands budget expansion for dynamic playmaker, while General Manager insists on fiscal discipline.",
  role_a: "first_team_manager",
  role_a_label: "First-Team Manager",
  role_a_name: "Emmanuel Amuneke",
  role_b: "general_manager",
  role_b_label: "General Manager",
  role_b_name: "Dayo Adeleke",
  urgency: "critical",
  status: "open",
  world_day: 14,
  choices: [
    {
      choice_id: "back_manager_recruitment",
      label: "Ratify ₦240,000 GTEX Budget Expansion",
      summary: "Back the manager's recruitment drive.",
      backed_role: "Backs First-Team Manager",
      cost_gtex: 240000,
      delta_role_a: { delta_trust: 12, delta_tension: -10 },
      delta_role_b: { delta_tension: 8, delta_alignment: -5 },
      projected_effects: ["Squad morale rises +6%", "Treasury decreases ₦240,000"],
    },
    {
      choice_id: "enforce_gm_wage_discipline",
      label: "Enforce Fiscal Discipline & Freeze Targets",
      summary: "Uphold the General Manager's wage cap.",
      backed_role: "Backs General Manager",
      cost_gtex: 0,
      delta_role_a: { delta_tension: 10, delta_trust: -8 },
      delta_role_b: { delta_trust: 10, delta_alignment: 8 },
      projected_effects: ["Preserves ₦240,000 GTEX", "Manager relationship strained"],
    },
    {
      choice_id: "ratify_performance_compromise",
      label: "Condition Budget on Incentive Milestones",
      summary: "Balanced performance-contingent milestone release.",
      backed_role: "Balanced Compromise",
      cost_gtex: 120000,
      delta_role_a: { delta_trust: 6, delta_alignment: 5 },
      delta_role_b: { delta_trust: 6, delta_alignment: 5 },
      projected_effects: ["₦120,000 GTEX milestone allocation", "Both leads accept compromise"],
    },
  ],
};

describe("BoardroomDilemmaModal", () => {
  let container: HTMLDivElement;
  let root: Root;
  let queryClient: QueryClient;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    jest.clearAllMocks();
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  test("renders nothing when isOpen is false", () => {
    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <BoardroomDilemmaModal clubId="c_lagos" isOpen={false} onClose={jest.fn()} />
        </QueryClientProvider>
      );
    });

    expect(container.querySelector('[data-testid="boardroom-dilemma-modal"]')).toBeNull();
  });

  test("fetches and renders active dilemma details and choice cards", async () => {
    (api.get as jest.Mock).mockResolvedValue({ data: mockDilemma });

    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <BoardroomDilemmaModal clubId="c_lagos" isOpen={true} onClose={jest.fn()} />
        </QueryClientProvider>
      );
    });

    await waitForCondition(() => container.textContent?.includes("CRITICAL STANDOFF") ?? false);

    expect(container.querySelector('[data-testid="boardroom-dilemma-modal"]')).not.toBeNull();
    expect(container.textContent).toContain("Boardroom Strategic Dilemma");
    expect(container.textContent).toContain("First-Team Manager");
    expect(container.textContent).toContain("Emmanuel Amuneke");
    expect(container.textContent).toContain("General Manager");
    expect(container.textContent).toContain("Dayo Adeleke");
    expect(container.textContent).toContain("Transfer Ambition vs Wage Budget Discipline");

    // All 3 choices rendered
    expect(container.querySelector('[data-testid="dilemma-choice-back_manager_recruitment"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="dilemma-choice-enforce_gm_wage_discipline"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="dilemma-choice-ratify_performance_compromise"]')).not.toBeNull();
  });

  test("selects a choice, enters owner note, and ratifies the resolution", async () => {
    (api.get as jest.Mock).mockResolvedValue({ data: mockDilemma });
    (api.post as jest.Mock).mockResolvedValue({
      data: {
        success: true,
        dilemma_id: "dil_101",
        choice_id: "back_manager_recruitment",
        selected_choice: mockDilemma.choices[0],
        narrative_outcome: "The Owner authoritatively backed Emmanuel Amuneke.",
        club_id: "c_lagos",
        world_day: 14,
        updated_relationships: { role_a: null, role_b: null },
      },
    });

    const onResolveComplete = jest.fn();

    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <BoardroomDilemmaModal
            clubId="c_lagos"
            isOpen={true}
            onClose={jest.fn()}
            onResolveComplete={onResolveComplete}
          />
        </QueryClientProvider>
      );
    });

    await waitForCondition(() => container.querySelector('[data-testid="ratify-dilemma-btn"]') !== null);

    // Ratify button disabled initially
    const ratifyBtn = container.querySelector('[data-testid="ratify-dilemma-btn"]') as HTMLButtonElement;
    expect(ratifyBtn.disabled).toBe(true);

    // Select choice A
    const choiceA = container.querySelector(
      '[data-testid="dilemma-choice-back_manager_recruitment"]'
    ) as HTMLDivElement;
    await act(async () => {
      choiceA.click();
    });

    expect(ratifyBtn.disabled).toBe(false);

    // Enter note
    const noteInput = container.querySelector('[data-testid="dilemma-note-input"]') as HTMLTextAreaElement;
    await act(async () => {
      noteInput.value = "We need this playmaker to secure continental qualification.";
      noteInput.dispatchEvent(new Event("change", { bubbles: true }));
    });

    // Click ratify
    await act(async () => {
      ratifyBtn.click();
    });

    await waitForCondition(() => container.textContent?.includes("Strategic Directive Ratified") ?? false);

    expect(api.post).toHaveBeenCalledWith(
      "/owner/clubs/c_lagos/living-world/dilemmas/dil_101/resolve",
      expect.objectContaining({
        choice_id: "back_manager_recruitment",
      })
    );

    expect(onResolveComplete).toHaveBeenCalled();
    expect(container.textContent).toContain("The Owner authoritatively backed Emmanuel Amuneke.");
  });

  test("invokes onClose when clicking close button", async () => {
    (api.get as jest.Mock).mockResolvedValueOnce({ data: mockDilemma });
    const onClose = jest.fn();

    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <BoardroomDilemmaModal clubId="c_lagos" isOpen={true} onClose={onClose} />
        </QueryClientProvider>
      );
    });

    await waitForCondition(() => container.querySelector('[data-testid="close-dilemma-modal-btn"]') !== null);

    const closeBtn = container.querySelector('[data-testid="close-dilemma-modal-btn"]') as HTMLButtonElement;
    await act(async () => {
      closeBtn.click();
    });

    expect(onClose).toHaveBeenCalled();
  });
});
