import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StaffEmploymentModal } from "./StaffEmploymentModal";
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
            cinematic_event: {
              event_id: "evt_arrival_chidi_1",
              event_type: "staff_signing",
              category: "staff_arrival",
              scene_type: "manager_arrival",
              camera_preset: "convoy_tunnel_walkout",
              lighting_preset: "stadium_floodlight_unveiling",
              render_mode: "3d_webgl",
              fallback_available: true,
              fallback_label: "2D Broadcast Fallback Ready",
              verified_source: true,
              title: "Executive Appointment: Chidi Eze Joins as Head of Youth Development",
              subtitle: "Head of Youth Development • 2-Year Contract • ₦85,000 GTEX/yr",
              club_branding: {
                club_id: "club-1",
                club_name: "Lagos Atlantic FC",
                primary_color: "#10b981",
                secondary_color: "#f59e0b",
                accent_color: "#0f172a",
                stadium_name: "Atlantic Arena",
              },
              metadata: {
                staff_name: "Chidi Eze",
                role_key: "head_of_youth_development",
                role_label: "Head of Youth Development",
                rating: 78,
                reputation: 74,
                annual_salary_gtex: 85000,
                contract_years: 2,
                signing_fee_gtex: 12750,
              },
            },
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
    expect(cand1?.textContent).toContain("85,000 FAN");
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

    // Stage 7: Verify 3D Staff Arrival Cinematic Overlay is launched after confirmed appointment
    expect(container.querySelector('[data-testid="staff-arrival-cinematic-overlay"]')).not.toBeNull();
    expect(container.textContent).toContain(
      "Executive Appointment: Chidi Eze Joins as Head of Youth Development"
    );

    const completeArrivalBtn = container.querySelector(
      '[data-testid="complete-arrival-cinematic-btn"]'
    ) as HTMLButtonElement;
    expect(completeArrivalBtn).not.toBeNull();
    act(() => {
      completeArrivalBtn.click();
    });
    expect(container.querySelector('[data-testid="staff-arrival-cinematic-overlay"]')).toBeNull();
  });

  it("never triggers 3D arrival cinematic overlay when a contract offer is rejected", async () => {
    (api.post as jest.Mock).mockImplementationOnce(() =>
      Promise.resolve({
        data: {
          status: "rejected_salary",
          success: false,
          message: "Candidate rejected the wage package.",
          counter_salary_gtex: 420000,
          cinematic_event: null,
        },
      })
    );

    renderModal({ initialTab: "market" });
    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="negotiate-offer-btn-prof-cand-2"]'))
    );

    const negotiateBtn = container.querySelector(
      '[data-testid="negotiate-offer-btn-prof-cand-2"]'
    ) as HTMLButtonElement;
    act(() => {
      negotiateBtn.click();
    });

    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="submit-contract-offer-btn"]'))
    );

    const submitBtn = container.querySelector(
      '[data-testid="submit-contract-offer-btn"]'
    ) as HTMLButtonElement;
    act(() => {
      submitBtn.click();
    });

    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="offer-result-banner"]'))
    );
    expect(container.querySelector('[data-testid="staff-arrival-cinematic-overlay"]')).toBeNull();
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
    expect(dialog?.textContent).toContain("60,000 FAN"); // 50% of 120,000

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
