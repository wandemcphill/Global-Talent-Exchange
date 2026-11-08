import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PersonaSpatialInteractionModal } from "./PersonaSpatialInteractionModal";
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

describe("PersonaSpatialInteractionModal", () => {
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

  const mockDetails = {
    club_id: "c_lagos_test",
    world_day: 5,
    persona: {
      role_key: "first_team_manager",
      role_label: "First-Team Manager",
      name: "Emmanuel Amuneke",
      person_id: "first_team_manager:amuneke",
      is_appointed: true,
      department: "manager",
    },
    relationship: {
      id: "rel_123",
      club_id: "c_lagos_test",
      pairing_key: "c_lagos_test:owner:first_team_manager:amuneke",
      participant_a_type: "owner",
      participant_a_id: "owner",
      participant_a_name: "Club Owner",
      participant_b_type: "staff",
      participant_b_id: "first_team_manager:amuneke",
      participant_b_name: "Emmanuel Amuneke",
      trust: 60,
      respect: 65,
      affinity: 55,
      tension: 12,
      alignment: 72,
      influence: 68,
      loyalty: 65,
      status: "active",
      status_label: "Aligned Collaborator",
    },
    active_directives: [
      {
        id: "dir_1",
        directive_key: "change_formation",
        title: "Deploy 4-3-3 Attack",
        instruction: "Train team in 4-3-3 shape.",
        deadline_day: 9,
      },
    ],
    recent_history: [],
  };

  test("renders persona identity and all 7 relationship dimensions including Stage 1 dimensions", async () => {
    (api.get as jest.Mock).mockResolvedValueOnce({ data: mockDetails });

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <PersonaSpatialInteractionModal
            clubId="c_lagos_test"
            personaRole="first_team_manager"
            isOpen={true}
            onClose={jest.fn()}
          />
        </QueryClientProvider>
      );
    });

    await waitForCondition(() => (container.textContent?.includes("Emmanuel Amuneke") ?? false));

    // Verify modal container exists
    expect(container.querySelector('[data-testid="persona-spatial-modal"]')).not.toBeNull();
    expect(container.textContent).toContain("Emmanuel Amuneke");
    expect(container.textContent).toContain("First-Team Manager");
    expect(container.textContent).toContain("Aligned Collaborator");

    // Verify 7 dimensions rendered
    expect(container.textContent).toContain("Alignment");
    expect(container.textContent).toContain("72%");

    expect(container.textContent).toContain("Influence");
    expect(container.textContent).toContain("68%");

    expect(container.textContent).toContain("Loyalty");
    expect(container.textContent).toContain("65%");

    expect(container.textContent).toContain("Tension");
    expect(container.textContent).toContain("12%");

    expect(container.textContent).toContain("Trust");
    expect(container.textContent).toContain("Respect");
    expect(container.textContent).toContain("Affinity");
  });

  test("dispatches interaction mutation and displays speech reply bubble with delta preview", async () => {
    (api.get as jest.Mock).mockResolvedValue({ data: mockDetails });
    const mockMutationResponse = {
      success: true,
      action_type: "align_strategy",
      action_label: "Align Strategic Vision",
      persona: mockDetails.persona,
      relationship: {
        ...mockDetails.relationship,
        alignment: 78,
        influence: 71,
        tension: 9,
      },
      delta_applied: {
        alignment: 6,
        influence: 3,
        tension: -3,
        trust: 2,
        respect: 2,
        affinity: 1,
        loyalty: 2,
      },
      dialogue_reply: "When we share the same tactical philosophy, the squad executes with conviction on matchday.",
      world_day: 5,
    };
    (api.post as jest.Mock).mockResolvedValueOnce({ data: mockMutationResponse });

    const handleComplete = jest.fn();

    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <PersonaSpatialInteractionModal
            clubId="c_lagos_test"
            personaRole="first_team_manager"
            isOpen={true}
            onClose={jest.fn()}
            onInteractionComplete={handleComplete}
          />
        </QueryClientProvider>
      );
    });

    await waitForCondition(() => (container.textContent?.includes("Emmanuel Amuneke") ?? false));

    const alignBtn = container.querySelector('[data-testid="action-btn-align_strategy"]') as HTMLButtonElement;
    expect(alignBtn).not.toBeNull();

    await act(async () => {
      alignBtn.click();
    });

    await waitForCondition(() => (container.textContent?.includes("When we share the same tactical philosophy") ?? false));

    expect(api.post).toHaveBeenCalledWith(
      "/owner/clubs/c_lagos_test/living-world/personas/first_team_manager/interact",
      { action_type: "align_strategy", dialogue_text: undefined }
    );

    expect(handleComplete).toHaveBeenCalledWith(mockMutationResponse);
  });

  test("does not render when isOpen is false", async () => {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <PersonaSpatialInteractionModal
            clubId="c_lagos_test"
            personaRole="first_team_manager"
            isOpen={false}
            onClose={jest.fn()}
          />
        </QueryClientProvider>
      );
    });

    expect(container.querySelector('[data-testid="persona-spatial-modal"]')).toBeNull();
  });
});
