import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { GmDelegationModal } from "./GmDelegationModal";
import { api } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
  },
  errMsg: (err: any) => err?.message || "Error occurred",
}));

jest.mock("sonner", () => ({
  toast: {
    success: jest.fn(),
    info: jest.fn(),
    error: jest.fn(),
  },
}));

const waitForCondition = async (predicate: () => boolean, timeout = 3000) => {
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

const mockOverviewData = {
  club_id: "c_test_gm",
  gm_staff: {
    id: "staff_gm_1",
    name: "Dayo Adeleke",
    role: "General Manager",
    rating: 84,
    salary_gtex: 1800,
    trust: 68,
    tension: 18,
    alignment: 72,
    loyalty: 75,
    is_appointed: true,
  },
  delegation_mode: "balanced",
  canonical_mode: "balanced",
  financial_controls: {
    max_expenditure_unapproved_gtex: 15000,
    max_staff_salary_unapproved_gtex: 1500,
    max_contract_years_unapproved: 2,
    recruitment_budget_gtex: 100000,
    wage_budget_gtex: 40000,
    min_sale_value_gtex: 20000,
    allow_emergency_spending: true,
  },
  activities: [
    {
      activity_key: "staff_hiring",
      label: "Staff Recruitment & Appointments",
      description: "Recruiting technical, medical, and scouting personnel.",
      category: "staffing",
      department: "executive",
      requires_owner_approval: true,
      gm_can_execute: false,
      execution_supported: true,
      policy_suspended: false,
      delegation_level: "review_only",
    },
    {
      activity_key: "academy_recruitment",
      label: "Academy & Youth Scouting Intake",
      description: "Sanctioning trials and signing academy prospects under age 18.",
      category: "academy",
      department: "sporting",
      requires_owner_approval: false,
      gm_can_execute: false,
      execution_supported: true,
      policy_suspended: true,
      delegation_level: "delegated_with_limits",
    },
    {
      activity_key: "player_scouting",
      label: "Player Scouting Missions",
      description: "Owner-managed until the execution workflow is implemented.",
      category: "sporting",
      department: "sporting",
      requires_owner_approval: true,
      gm_can_execute: false,
      execution_supported: false,
      policy_suspended: false,
      delegation_level: "owner_only",
    },
  ],
  pending_proposals: [
    {
      id: "prop_1",
      activity_key: "academy_recruitment",
      domain: "sporting",
      proposed_by_role: "general_manager",
      proposed_by_staff_name: "Dayo Adeleke",
      title: "Grassroots Showcase Trial Sanction",
      summary: "GM Dayo Adeleke requests 2,500 GTEX for academy scout intake.",
      financial_amount_gtex: 2500,
      requires_owner_approval: true,
      status: "pending_approval",
      execution_status: "pending",
      created_at: "2026-11-08T12:00:00Z",
    },
  ],
  recent_audit_trail: [
    {
      id: "audit_1",
      decision_id: "dec_1",
      actor_role: "general_manager",
      action: "executed",
      reason: "Autonomous trial sanction executed within limit",
      note: "Good talent intake",
      occurred_at: "2026-11-08T11:00:00Z",
    },
  ],
  statistics: {
    total_executed: 14,
    pending_approval_count: 1,
    total_expenditure_approved_gtex: 42000,
  },
};

describe("GmDelegationModal Component", () => {
  let container: HTMLDivElement;
  let root: Root;
  let queryClient: QueryClient;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    jest.clearAllMocks();
    (api.get as jest.Mock).mockResolvedValue({ data: mockOverviewData });
    (api.post as jest.Mock).mockResolvedValue({
      data: {
        success: true,
        mode: "gm_led",
        status: "approved",
        action_taken: "Approved proposal",
        audit_logged: true,
        updated_relationships: { trust: 72, tension: 15, alignment: 75 },
      },
    });
    (api.put as jest.Mock).mockResolvedValue({
      data: {
        success: true,
        mode: "balanced",
      },
    });

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });

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

  const renderModal = (props?: Partial<React.ComponentProps<typeof GmDelegationModal>>) => {
    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <GmDelegationModal
            clubId="c_test_gm"
            isOpen={true}
            onClose={jest.fn()}
            {...props}
          />
        </QueryClientProvider>
      );
    });
  };

  it("renders GM persona details and relationship meters", async () => {
    renderModal();

    await waitForCondition(
      () =>
        Boolean(container.querySelector('[data-testid="gm-delegation-modal"]')) &&
        !container.textContent?.includes("Loading GM delegation architecture...")
    );

    expect(container.textContent).toContain("Dayo Adeleke");
    expect(container.textContent).toContain("General Manager");
    expect(container.textContent).toContain("OVR 84");
    expect(container.textContent).toContain("68%"); // Trust
    expect(container.textContent).toContain("18%"); // Tension
    expect(container.textContent).toContain("72%"); // Alignment
    expect(container.textContent).toContain("75%"); // Loyalty
  });

  it("switches delegation modes when clicking mode cards", async () => {
    renderModal();

    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="mode-card-gm_led"]'))
    );

    const gmLedCard = container.querySelector(
      '[data-testid="mode-card-gm_led"]'
    ) as HTMLElement;
    expect(gmLedCard).toBeTruthy();

    await act(async () => {
      gmLedCard.click();
    });

    expect(api.post).toHaveBeenCalledWith(
      "/owner/clubs/c_test_gm/living-world/gm-delegation/mode",
      { mode: "gm_led" }
    );
  });

  it("switches to authority matrix tab and toggles activity approval", async () => {
    renderModal({ initialTab: "matrix" });

    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="toggle-activity-staff_hiring"]'))
    );

    const toggleBtn = container.querySelector(
      '[data-testid="toggle-activity-staff_hiring"]'
    ) as HTMLButtonElement;
    expect(toggleBtn).toBeTruthy();

    await act(async () => {
      toggleBtn.click();
    });

    expect(api.put).toHaveBeenCalledWith(
      "/owner/clubs/c_test_gm/living-world/gm-delegation/matrix",
      {
        activity_assignments: {
          staff_hiring: { requires_owner_approval: false },
        },
      }
    );
  });

  it("allows approving an escalated GM proposal", async () => {
    renderModal({ initialTab: "proposals" });

    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="approve-proposal-prop_1-btn"]'))
    );

    const approveBtn = container.querySelector(
      '[data-testid="approve-proposal-prop_1-btn"]'
    ) as HTMLButtonElement;
    expect(approveBtn).toBeTruthy();

    await act(async () => {
      approveBtn.click();
    });

    expect(api.post).toHaveBeenCalledWith(
      "/owner/clubs/c_test_gm/living-world/gm-delegation/proposals/prop_1/resolve",
      {
        action: "approve",
        decision_note: undefined,
      }
    );
  });

  it("allows rejecting an escalated GM proposal", async () => {
    renderModal({ initialTab: "proposals" });

    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="reject-proposal-prop_1-btn"]'))
    );

    const rejectBtn = container.querySelector(
      '[data-testid="reject-proposal-prop_1-btn"]'
    ) as HTMLButtonElement;
    expect(rejectBtn).toBeTruthy();

    await act(async () => {
      rejectBtn.click();
    });

    expect(api.post).toHaveBeenCalledWith(
      "/owner/clubs/c_test_gm/living-world/gm-delegation/proposals/prop_1/resolve",
      {
        action: "reject",
        decision_note: undefined,
      }
    );
  });

  it("triggers GM operational cycle simulation", async () => {
    renderModal();

    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="run-gm-evaluation-btn"]'))
    );

    const runBtn = container.querySelector(
      '[data-testid="run-gm-evaluation-btn"]'
    ) as HTMLButtonElement;
    expect(runBtn).toBeTruthy();

    await act(async () => {
      runBtn.click();
    });

    expect(api.post).toHaveBeenCalledWith(
      "/owner/clubs/c_test_gm/living-world/gm-delegation/evaluate-operations"
    );
  });

  it("renders audit trail and statistics tab", async () => {
    renderModal({ initialTab: "audit" });

    await waitForCondition(
      () =>
        Boolean(container.querySelector('[data-testid="gm-tab-audit"]')) &&
        !container.textContent?.includes("Loading GM delegation architecture...")
    );

    expect(container.textContent).toContain("14"); // total executed
    expect(container.textContent).toContain("42,000 GTEX"); // total approved spend
    expect(container.textContent).toContain("Autonomous trial sanction executed within limit");
    expect(container.textContent).toContain("Good talent intake");
  });


  it("shows suspended and not-yet-implemented activities as non-executable", async () => {
    renderModal({ initialTab: "matrix" });

    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="toggle-activity-player_scouting"]'))
    );

    const suspendedButton = container.querySelector(
      '[data-testid="toggle-activity-academy_recruitment"]'
    ) as HTMLButtonElement;
    const unsupportedButton = container.querySelector(
      '[data-testid="toggle-activity-player_scouting"]'
    ) as HTMLButtonElement;

    expect(suspendedButton.disabled).toBe(true);
    expect(unsupportedButton.disabled).toBe(true);
    expect(container.textContent).toContain("GM Authority Suspended");
    expect(container.textContent).toContain("Owner Only — Not Implemented");
  });
});
