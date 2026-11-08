import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StaffEmploymentModal } from "./StaffEmploymentModal";
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

const mockVacanciesData = {
  club_id: "club-1",
  club_prestige: 68,
  vacancies_count: 1,
  vacancies: [
    {
      role_key: "head_of_youth_development",
      role_label: "Head of Youth Development",
      is_urgent: true,
      provisional_name: "Interim Academy Lead",
      recommended_min_rating: 70,
    },
  ],
  filled_roles: [
    {
      role_key: "first_team_manager",
      role_label: "First-Team Manager",
      incumbent_name: "Emmanuel Amuneke",
      staff_id: "staff-mgr-1",
      appointed_at: "2026-01-01T00:00:00",
      salary_gtex: 120000,
      mood: 82,
    },
  ],
};

const mockMarketData = {
  club_id: "club-1",
  club_prestige: 68,
  total_count: 2,
  candidates: [
    {
      profile_id: "prof-cand-1",
      market_key: "prof-cand-1",
      staff_id: "staff-cand-1",
      name: "Chidi Eze",
      role_key: "head_of_youth_development",
      role_label: "Head of Youth Development",
      rating: 78,
      rarity: "rare",
      skills: ["Talent Identification", "Youth Pathway Development"],
      reputation: 74,
      experience_years: 12,
      temperament: "Nurturing",
      style: "Grassroots Development",
      ambition: 70,
      loyalty: 85,
      expected_salary_gtex: 85000,
      min_prestige: 55,
      employment_status: "unemployed",
      can_attract: true,
      interest_level: "very_high",
      career_history: [
        {
          club_id: "club-lagos",
          club_name: "Lagos Atlantic FC",
          role: "head_of_youth_development",
          tenure_years: 4,
          matches_managed: 96,
          win_rate_pct: 62.5,
          exit_reason: "Contract expiration",
        },
      ],
    },
    {
      profile_id: "prof-cand-2",
      market_key: "prof-cand-2",
      staff_id: "staff-cand-2",
      name: "Tariq Mansoor",
      role_key: "general_manager",
      role_label: "General Manager",
      rating: 88,
      rarity: "legendary",
      skills: ["Continental Commercial Growth", "Elite Talent Arbitrage"],
      reputation: 91,
      experience_years: 18,
      temperament: "Analytical",
      style: "Corporate Expansion",
      ambition: 95,
      loyalty: 60,
      expected_salary_gtex: 350000,
      min_prestige: 80,
      employment_status: "unemployed",
      can_attract: false,
      interest_level: "requires_premium",
      career_history: [],
    },
  ],
};

describe("StaffEmploymentModal", () => {
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

    (api.get as jest.Mock).mockImplementation((url: string) => {
      if (url.includes("/living-world/staff-market/vacancies")) {
        return Promise.resolve({ data: mockVacanciesData });
      }
      if (url.includes("/living-world/staff-market/candidates")) {
        return Promise.resolve({ data: mockMarketData });
      }
      return Promise.reject(new Error(`Unhandled GET url: ${url}`));
    });

    (api.post as jest.Mock).mockImplementation((url: string, payload: any) => {
      if (url.includes("/living-world/staff-market/offers")) {
        return Promise.resolve({
          data: {
            status: "accepted",
            success: true,
            message: "Contract offer ratified. Chidi Eze appointed as Head of Youth Development.",
            contract_id: "contract-new-1",
            assignment_id: "assignment-new-1",
            total_contract_fee: payload.offered_salary_gtex * 0.15,
          },
        });
      }
      if (url.includes("/living-world/staff-market/dismiss")) {
        return Promise.resolve({
          data: {
            status: "dismissed",
            success: true,
            role: payload.role,
            staff_name: "Emmanuel Amuneke",
            severance_paid: 60000,
            entered_free_agency: true,
          },
        });
      }
      return Promise.reject(new Error(`Unhandled POST url: ${url}`));
    });
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  const renderModal = (props: Partial<React.ComponentProps<typeof StaffEmploymentModal>> = {}) => {
    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <StaffEmploymentModal
            clubId="club-1"
            isOpen={true}
            onClose={jest.fn()}
            {...props}
          />
        </QueryClientProvider>
      );
    });
  };

  it("does not render when isOpen is false", () => {
    renderModal({ isOpen: false });
    expect(container.querySelector('[data-testid="staff-employment-modal"]')).toBeNull();
  });

  it("renders vacancies tab with unfilled vacancies and appointed incumbents", async () => {
    renderModal();

    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="vacancy-card-head_of_youth_development"]'))
    );

    // Vacancy rendered
    const vacancyCard = container.querySelector(
      '[data-testid="vacancy-card-head_of_youth_development"]'
    );
    expect(vacancyCard).not.toBeNull();
    expect(vacancyCard?.textContent).toContain("Head of Youth Development");
    expect(vacancyCard?.textContent).toContain("70+ OVR");

    // Filled role rendered
    const filledCard = container.querySelector(
      '[data-testid="filled-role-card-first_team_manager"]'
    );
    expect(filledCard).not.toBeNull();
    expect(filledCard?.textContent).toContain("Emmanuel Amuneke");
    expect(filledCard?.textContent).toContain("120,000");
  });

  it("switches to global market when clicking 'Find Candidates' on vacancy", async () => {
    renderModal();

    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="recruit-btn-head_of_youth_development"]'))
    );

    const recruitBtn = container.querySelector(
      '[data-testid="recruit-btn-head_of_youth_development"]'
    ) as HTMLButtonElement;

    act(() => {
      recruitBtn.click();
    });

    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="market-tab-content"]'))
    );

    const select = container.querySelector(
      '[data-testid="role-filter-select"]'
    ) as HTMLSelectElement;
    expect(select.value).toBe("head_of_youth_development");
  });

  it("browses market candidates, expands career history, and submits contract offer", async () => {
    const onHireComplete = jest.fn();
    renderModal({ initialTab: "market", onHireComplete });

    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="candidate-card-prof-cand-1"]'))
    );

    // Candidate 1 rendered
    const cand1 = container.querySelector('[data-testid="candidate-card-prof-cand-1"]');
    expect(cand1?.textContent).toContain("Chidi Eze");
    expect(cand1?.textContent).toContain("85,000 GTEX");
    expect(cand1?.textContent).toContain("High Interest");

    // Expand Career History
    const historyBtn = container.querySelector(
      '[data-testid="toggle-history-btn-prof-cand-1"]'
    ) as HTMLButtonElement;
    act(() => {
      historyBtn.click();
    });

    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="candidate-history-drawer-prof-cand-1"]'))
    );
    const historyDrawer = container.querySelector(
      '[data-testid="candidate-history-drawer-prof-cand-1"]'
    );
    expect(historyDrawer?.textContent).toContain("Lagos Atlantic FC");
    expect(historyDrawer?.textContent).toContain("62.5% win");

    // Open Negotiation
    const negotiateBtn = container.querySelector(
      '[data-testid="negotiate-offer-btn-prof-cand-1"]'
    ) as HTMLButtonElement;
    act(() => {
      negotiateBtn.click();
    });

    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="contract-negotiation-sheet"]'))
    );

    // Toggle Marquee Premium
    const marqueeToggle = container.querySelector(
      '[data-testid="offer-marquee-premium-toggle"]'
    ) as HTMLInputElement;
    act(() => {
      marqueeToggle.click();
    });
    expect(marqueeToggle.checked).toBe(true);

    // Submit Offer
    const submitBtn = container.querySelector(
      '[data-testid="submit-contract-offer-btn"]'
    ) as HTMLButtonElement;
    act(() => {
      submitBtn.click();
    });

    await waitForCondition(() => onHireComplete.mock.calls.length > 0);
    expect(onHireComplete).toHaveBeenCalledWith(
      expect.objectContaining({
        status: "accepted",
        success: true,
      })
    );
  });

  it("handles dismissal confirmation and dispatches dismissal mutation", async () => {
    const onDismissComplete = jest.fn();
    renderModal({ initialTab: "vacancies", onDismissComplete });

    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="dismiss-btn-first_team_manager"]'))
    );

    // Click Dismiss on manager
    const dismissBtn = container.querySelector(
      '[data-testid="dismiss-btn-first_team_manager"]'
    ) as HTMLButtonElement;
    act(() => {
      dismissBtn.click();
    });

    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="dismissal-confirmation-dialog"]'))
    );

    const dialog = container.querySelector('[data-testid="dismissal-confirmation-dialog"]');
    expect(dialog?.textContent).toContain("Emmanuel Amuneke");
    expect(dialog?.textContent).toContain("60,000 GTEX"); // 50% of 120,000

    // Confirm Dismiss
    const confirmBtn = container.querySelector(
      '[data-testid="confirm-dismiss-btn"]'
    ) as HTMLButtonElement;
    act(() => {
      confirmBtn.click();
    });

    await waitForCondition(() => onDismissComplete.mock.calls.length > 0);
    expect(onDismissComplete).toHaveBeenCalledWith(
      expect.objectContaining({
        status: "dismissed",
        success: true,
        severance_paid: 60000,
      })
    );
  });
});
