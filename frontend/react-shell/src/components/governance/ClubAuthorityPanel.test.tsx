declare const describe: any;
declare const test: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { api } from "@/lib/api";
import { ClubAuthorityPanel } from "./ClubAuthorityPanel";

// Mock 3D Viewport so WebGL / Three.js canvas isn't required in headless jsdom
jest.mock("@/lib/3d/GtexSceneViewport", () => {
  const ReactModule = require("react");
  return {
    GtexSceneViewport: ({ sceneId }: { sceneId: string }) =>
      ReactModule.createElement("div", { "data-testid": `gtex-scene-viewport-${sceneId}` }, `3D Scene: ${sceneId}`),
  };
});

jest.mock("sonner", () => ({
  toast: {
    success: () => {},
    info: () => {},
    warning: () => {},
    error: () => {},
  },
}));

const mockPolicy = {
  club_id: "test-club-123",
  mode: "balanced",
  is_suspended: false,
  suspension_reason: null,
  financial_thresholds: {
    recruitment_max_gtex: 25000,
    sales_min_gtex: 5000,
    operational_spend_max_gtex: 10000,
    contract_renewal_max_weekly_wage_gtex: 5000,
    facility_spend_max_gtex: 15000,
  },
  reserved_decisions: ["staff_recruitment_dismissal", "financial_planning"],
  temporary_overrides: {},
  activity_assignments: {
    first_team_tactics: {
      activity_key: "first_team_tactics",
      domain: "sporting",
      responsible_role: "first_team_manager",
      authority_level: "full_autonomy",
      approval_role: "owner",
    },
    player_recruitment: {
      activity_key: "player_recruitment",
      domain: "sporting",
      responsible_role: "general_manager",
      authority_level: "delegated_with_limits",
      approval_role: "owner",
    },
    staff_recruitment_dismissal: {
      activity_key: "staff_recruitment_dismissal",
      domain: "club_operations",
      responsible_role: "owner",
      authority_level: "owner_only",
      approval_role: "owner",
    },
  },
};

const mockOrgStructure = {
  club_id: "test-club-123",
  owner: {
    user_id: "owner-user-001",
    role: "owner",
    authority: "supreme",
  },
  staff_positions: [
    {
      role_key: "general_manager",
      role_label: "General Manager",
      is_vacant: false,
      delegated_activities_count: 5,
      appointed_staff: {
        id: "staff-gm-01",
        name: "Babajide Adeyemi",
        nationality: "Nigeria",
        age: 48,
        rating: 82,
        salary_weekly: 4500,
        ambition: 75,
        loyalty: 88,
      },
    },
    {
      role_key: "first_team_manager",
      role_label: "First Team Manager",
      is_vacant: false,
      delegated_activities_count: 4,
      appointed_staff: {
        id: "staff-mgr-01",
        name: "Carlos Menendez",
        nationality: "Spain",
        age: 45,
        rating: 84,
        salary_weekly: 6000,
        tactical_flexibility: 85,
        loyalty: 80,
      },
    },
  ],
};

const mockEscalations = {
  club_id: "test-club-123",
  pending_count: 1,
  escalations: [
    {
      id: "esc-001",
      club_id: "test-club-123",
      activity_key: "player_recruitment",
      domain: "sporting",
      proposed_by_role: "general_manager",
      status: "pending_approval",
      title: "Marquee Striker Offer: Victor Okoro",
      summary: "Transfer bid for elite academy striker.",
      financial_amount_gtex: 45000,
      requires_owner_approval: true,
      escalation_reason: "Amount 45,000 GTX exceeds delegated ceiling of 25,000 GTX",
      staff_competence_impact: {
        competence_score: 82,
        ambition: 75,
        loyalty: 88,
        success_probability: 0.78,
        recommendation: "recommended",
        evaluation_summary: "Strong talent evaluation backed by GM scouting network.",
      },
      created_at: "2026-11-04T20:00:00Z",
    },
  ],
};

const mockDecisions = {
  club_id: "test-club-123",
  count: 1,
  decisions: [
    {
      id: "dec-001",
      club_id: "test-club-123",
      activity_key: "scouting_assignments",
      domain: "sporting",
      proposed_by_role: "chief_scout",
      status: "auto_approved",
      title: "West African Combine Scouting Mission",
      summary: "Deploy scouting team to observe 15 prospects.",
      financial_amount_gtex: 1200,
      requires_owner_approval: false,
      created_at: "2026-11-04T18:00:00Z",
    },
  ],
};

describe("ClubAuthorityPanel (Phase 1D UI)", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);

    jest.spyOn(api, "get").mockImplementation((url: string) => {
      if (url.includes("/authority/policy")) {
        return Promise.resolve({ data: mockPolicy });
      }
      if (url.includes("/authority/org-structure")) {
        return Promise.resolve({ data: mockOrgStructure });
      }
      if (url.includes("/authority/escalations")) {
        return Promise.resolve({ data: mockEscalations });
      }
      if (url.includes("/authority/decisions")) {
        return Promise.resolve({ data: mockDecisions });
      }
      return Promise.resolve({ data: {} });
    });

    jest.spyOn(api, "post").mockImplementation((url: string, body: any) => {
      if (url.includes("/authority/mode")) {
        return Promise.resolve({ data: { ...mockPolicy, mode: body.mode } });
      }
      if (url.includes("/authority/suspension")) {
        return Promise.resolve({
          data: {
            ...mockPolicy,
            is_suspended: body.suspend,
            suspension_reason: body.reason || null,
          },
        });
      }
      if (url.includes("/authority/decisions/")) {
        return Promise.resolve({
          data: {
            ...mockEscalations.escalations[0],
            status: body.action === "approve" ? "approved" : "rejected",
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    jest.spyOn(api, "put").mockImplementation((url: string, body: any) => {
      if (url.includes("/authority/thresholds")) {
        return Promise.resolve({
          data: {
            ...mockPolicy,
            financial_thresholds: { ...mockPolicy.financial_thresholds, ...body },
          },
        });
      }
      return Promise.resolve({ data: mockPolicy });
    });
  });

  afterEach(async () => {
    await act(async () => {
      root.unmount();
    });
    container.remove();
    jest.restoreAllMocks();
  });

  test("renders master governance header, mode cards, and 3D boardroom viewport", async () => {
    await act(async () => {
      root.render(React.createElement(ClubAuthorityPanel, { clubId: "test-club-123" }));
    });

    // Header & panel present
    expect(container.querySelector('[data-testid="club-authority-panel"]')).not.toBeNull();
    expect(container.textContent).toContain("Club Authority & Governance");

    // Mode cards
    expect(container.querySelector('[data-testid="mode-card-hands_on"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="mode-card-balanced"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="mode-card-delegating"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="mode-card-custom"]')).not.toBeNull();

    // 3D Scene Viewport mounted
    expect(container.querySelector('[data-testid="gtex-scene-viewport-boardroom_meeting"]')).not.toBeNull();
  });

  test("renders appointed staff cards in organizational hierarchy view", async () => {
    await act(async () => {
      root.render(React.createElement(ClubAuthorityPanel, { clubId: "test-club-123" }));
    });

    expect(container.querySelector('[data-testid="staff-card-general_manager"]')).not.toBeNull();
    expect(container.textContent).toContain("Babajide Adeyemi");
    expect(container.textContent).toContain("82 OVR");

    expect(container.querySelector('[data-testid="staff-card-first_team_manager"]')).not.toBeNull();
    expect(container.textContent).toContain("Carlos Menendez");
    expect(container.textContent).toContain("84 OVR");
  });

  test("switches management configuration mode", async () => {
    await act(async () => {
      root.render(React.createElement(ClubAuthorityPanel, { clubId: "test-club-123" }));
    });

    const delegatingBtn = container.querySelector('[data-testid="mode-card-delegating"]') as HTMLButtonElement;
    expect(delegatingBtn).not.toBeNull();

    await act(async () => {
      delegatingBtn.click();
    });

    expect(api.post).toHaveBeenCalledWith(
      "/owner/clubs/test-club-123/authority/mode",
      { mode: "delegating" }
    );
  });

  test("handles emergency delegation freeze and restore", async () => {
    await act(async () => {
      root.render(React.createElement(ClubAuthorityPanel, { clubId: "test-club-123" }));
    });

    const freezeBtn = container.querySelector('[data-testid="btn-toggle-suspension"]') as HTMLButtonElement;
    expect(freezeBtn).not.toBeNull();
    expect(freezeBtn.textContent).toContain("Emergency Freeze");

    await act(async () => {
      freezeBtn.click();
    });

    expect(api.post).toHaveBeenCalledWith(
      "/owner/clubs/test-club-123/authority/suspension",
      expect.objectContaining({ suspend: true })
    );
  });

  test("switches to pending escalations tab and approves escalated decision", async () => {
    await act(async () => {
      root.render(React.createElement(ClubAuthorityPanel, { clubId: "test-club-123" }));
    });

    // Switch to escalations tab
    const escTab = container.querySelector('[data-testid="tab-pending-escalations"]') as HTMLButtonElement;
    expect(escTab).not.toBeNull();

    await act(async () => {
      escTab.click();
    });

    expect(container.querySelector('[data-testid="escalation-item-esc-001"]')).not.toBeNull();
    expect(container.textContent).toContain("Marquee Striker Offer: Victor Okoro");
    expect(container.textContent).toContain("45,000 GTX");
    expect(container.textContent).toContain("Staff Backed");

    // Click Approve
    const approveBtn = container.querySelector('[data-testid="btn-approve-esc-001"]') as HTMLButtonElement;
    expect(approveBtn).not.toBeNull();

    await act(async () => {
      approveBtn.click();
    });

    expect(api.post).toHaveBeenCalledWith(
      "/owner/clubs/test-club-123/authority/decisions/esc-001/resolve",
      expect.objectContaining({ action: "approve" })
    );
  });
});
