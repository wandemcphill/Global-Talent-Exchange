import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ClubPoliticsModal } from "./ClubPoliticsModal";
import { api } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
  },
  errMsg: (err: any) => err?.message || "Error occurred",
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

const mockPoliticsOverview = {
  club_id: "c_test_pol",
  world_day: 12,
  board_politics: {
    board_confidence: 78,
    investor_sentiment: 82,
    board_mood: "supportive",
    directors: [
      {
        id: "dir_chairman",
        name: "Sir Adebayo Adeleke",
        role_title: "Board Chairman",
        archetype: "traditionalist",
        influence_weight: 85,
        primary_focus: "Trophies, Club Heritage & Managerial Stability",
        bio: "Long-serving custodian who values silverware, club traditions, and steady leadership.",
        confidence_score: 83,
        stance: "satisfied",
      },
      {
        id: "dir_investor",
        name: "Tariq Al-Mansoor",
        role_title: "Majority Investor Representative",
        archetype: "commercial",
        influence_weight: 80,
        primary_focus: "Financial Sustainability, Global Brand & Valuation",
        bio: "Focused on commercial expansion, broadcast value, and strict payroll ROI.",
        confidence_score: 76,
        stance: "satisfied",
      },
      {
        id: "dir_sporting",
        name: "Babatunde Lawal",
        role_title: "Non-Executive Sporting Director",
        archetype: "visionary",
        influence_weight: 70,
        primary_focus: "Youth Academy Pathway & Modern Tactical Identity",
        bio: "Former international midfielder who champions U-20 regens and high-intensity football.",
        confidence_score: 76,
        stance: "satisfied",
      },
      {
        id: "dir_supporter",
        name: "Ngozi Okafor",
        role_title: "Supporters Trust Representative",
        archetype: "populist",
        influence_weight: 65,
        primary_focus: "Matchday Atmosphere, Ticket Fairness & Local Identity",
        bio: "Elected voice of the terraces who demands passion, home-grown stars, and fan respect.",
        confidence_score: 76,
        stance: "satisfied",
      },
    ],
  },
  dressing_room: {
    squad_size: 3,
    average_morale: 64,
    leadership_group: {
      captain_name: "Ifeanyi Nwachukwu",
      vice_captain_name: "Tunde Bakare",
      influence_rating: 84,
      owner_trust: 74,
    },
    factions: {
      domestic_core: {
        label: "Domestic Core & Club Veterans",
        size: 11,
        cohesion: 80,
        sentiment: "harmonious",
      },
      star_signings: {
        label: "High-Earner Marquee Group",
        size: 6,
        cohesion: 72,
        sentiment: "ambitious",
      },
      academy_graduates: {
        label: "Academy Pathway Graduates",
        size: 8,
        cohesion: 85,
        sentiment: "eager",
      },
    },
    unhappy_players: [
      {
        id: "p_unhappy_1",
        name: "Kingsley Madu",
        position: "LB",
        rating: 74,
        morale: 48,
        issue: "Playing time deficit",
      },
    ],
    injured_players_count: 1,
  },
  medical_department: {
    director: {
      id: "staff_med_default",
      name: "Dr. Chidi Obi",
      role: "Medical Director",
      rating: 82,
      mood: 80,
    },
    injured_players: [
      {
        id: "p_inj_1",
        name: "Victor Onyema",
        position: "CM",
        rating: 79,
        injured_days: 4,
        morale: 70,
        status: "injured",
      },
    ],
    recovery_protocol: 3,
  },
  youth_development: {
    hoyd: {
      id: "staff_hoyd_default",
      name: "Kunle Adeyemi",
      role: "Head of Youth Development",
      rating: 81,
      mood: 78,
    },
    academy_tier: 3,
    prospects_monitored: 1,
  },
  supporter_sentiment: {
    confidence: 76,
    atmosphere_multiplier: 1.1,
    fan_trust_rating: "Optimistic",
  },
  media_and_rumours: {
    active_rumours: [
      {
        id: "rum_1",
        headline: "Owner Issues Official Communiqué: Vote Of Confidence",
        quote: "We have total faith in Emmanuel Amuneke.",
        statement_type: "vote_of_confidence",
        world_day: 12,
        occurred_at: "2026-11-08T12:00:00Z",
      },
    ],
    media_profile: "High Attention",
  },
  active_political_events: [
    {
      id: "ev_med_1",
      club_id: "c_test_pol",
      category: "medical",
      event_type: "medical_clearance_dispute",
      severity: "important",
      status: "awaiting_decision",
      title: "Medical Clearance Dispute: Victor Onyema",
      description:
        "Dr. Chidi Obi insists Victor Onyema needs 4 more days of recovery. Manager Emmanuel Amuneke is pressing to clear the player immediately.",
      world_day: 12,
      actions: [
        {
          action_id: "back_medical",
          label: "Back Medical Protocol",
          description: "Enforce full rehabilitation. Protect player from recurrence.",
          delta_summary: "+5 Medical Trust, -3 Manager Alignment, 0% Reinjury Risk",
        },
        {
          action_id: "rush_player",
          label: "Order Immediate Clearance",
          description: "Risk premature return for competitive advantage.",
          delta_summary: "-10 Medical Trust, +4 Manager Respect, 65% Reinjury Recurrence Risk",
        },
      ],
    },
  ],
  relationships: {},
};

describe("ClubPoliticsModal Component", () => {
  let container: HTMLDivElement;
  let root: Root;
  let queryClient: QueryClient;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    jest.clearAllMocks();
    (api.get as jest.Mock).mockResolvedValue({ data: mockPoliticsOverview });
    (api.post as jest.Mock).mockResolvedValue({
      data: {
        success: true,
        club_id: "c_test_pol",
        world_day: 12,
        events_evaluated: 2,
        outcome_summary: "Owner backed Dr. Chidi Obi's medical protocol.",
        outcome_text: "Owner publicly championed the club's youth academy pathway.",
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

  const renderModal = (
    props?: Partial<React.ComponentProps<typeof ClubPoliticsModal>>
  ) => {
    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ClubPoliticsModal
            clubId="c_test_pol"
            isOpen={true}
            onClose={jest.fn()}
            {...props}
          />
        </QueryClientProvider>
      );
    });
  };

  it("renders boardroom confidence, investor sentiment, and all 4 board directors", async () => {
    renderModal();

    await waitForCondition(
      () =>
        Boolean(container.querySelector('[data-testid="club-politics-modal"]')) &&
        !container.textContent?.includes("Loading club governance")
    );

    expect(
      container.querySelector('[data-testid="board-confidence-value"]')?.textContent
    ).toBe("78%");
    expect(
      container.querySelector('[data-testid="investor-sentiment-value"]')?.textContent
    ).toBe("82%");

    expect(container.textContent).toContain("Sir Adebayo Adeleke");
    expect(container.textContent).toContain("Tariq Al-Mansoor");
    expect(container.textContent).toContain("Babatunde Lawal");
    expect(container.textContent).toContain("Ngozi Okafor");
  });

  it("renders dressing room leadership, factions, medical, youth, and unhappy players", async () => {
    renderModal({ initialTab: "squad" });

    await waitForCondition(
      () =>
        Boolean(container.querySelector('[data-testid="squad-avg-morale"]')) &&
        !container.textContent?.includes("Loading club governance")
    );

    expect(
      container.querySelector('[data-testid="squad-avg-morale"]')?.textContent
    ).toBe("64/100");
    expect(container.textContent).toContain("Ifeanyi Nwachukwu");
    expect(container.textContent).toContain("Dr. Chidi Obi");
    expect(container.textContent).toContain("Kunle Adeyemi");
    expect(container.textContent).toContain("Kingsley Madu");
    expect(container.textContent).toContain("Playing time deficit");
  });

  it("resolves an active medical clearance dispute from the dilemmas tab", async () => {
    renderModal({ initialTab: "events" });

    await waitForCondition(() =>
      Boolean(
        container.querySelector(
          '[data-testid="respond-event-ev_med_1-back_medical-btn"]'
        )
      )
    );

    const backMedBtn = container.querySelector(
      '[data-testid="respond-event-ev_med_1-back_medical-btn"]'
    ) as HTMLButtonElement;
    expect(backMedBtn).toBeTruthy();

    await act(async () => {
      backMedBtn.click();
    });

    expect(api.post).toHaveBeenCalledWith(
      "/owner/clubs/c_test_pol/living-world/politics/events/ev_med_1/respond",
      {
        action_id: "back_medical",
        decision_note: undefined,
      }
    );
  });

  it("triggers a political evaluation cycle when clicking Run Politics Cycle", async () => {
    renderModal();

    await waitForCondition(() =>
      Boolean(container.querySelector('[data-testid="run-politics-cycle-btn"]'))
    );

    const runBtn = container.querySelector(
      '[data-testid="run-politics-cycle-btn"]'
    ) as HTMLButtonElement;
    expect(runBtn).toBeTruthy();

    await act(async () => {
      runBtn.click();
    });

    expect(api.post).toHaveBeenCalledWith(
      "/owner/clubs/c_test_pol/living-world/politics/events/evaluate-cycle",
      {}
    );
  });

  it("dispatches a public media statement from the media tab", async () => {
    renderModal({ initialTab: "media" });

    await waitForCondition(() =>
      Boolean(
        container.querySelector(
          '[data-testid="media-statement-type-praise_youth_academy"]'
        )
      )
    );

    const youthOption = container.querySelector(
      '[data-testid="media-statement-type-praise_youth_academy"]'
    ) as HTMLElement;
    const dispatchBtn = container.querySelector(
      '[data-testid="dispatch-media-statement-btn"]'
    ) as HTMLButtonElement;

    await act(async () => {
      youthOption.click();
    });

    await act(async () => {
      dispatchBtn.click();
    });

    expect(api.post).toHaveBeenCalledWith(
      "/owner/clubs/c_test_pol/living-world/politics/media/statement",
      {
        statement_type: "praise_youth_academy",
        custom_text: undefined,
      }
    );
  });

  it("renders supporter confidence and matchday atmosphere multiplier", async () => {
    renderModal({ initialTab: "supporters" });

    await waitForCondition(() =>
      Boolean(
        container.querySelector('[data-testid="supporter-confidence-value"]')
      )
    );

    expect(
      container.querySelector('[data-testid="supporter-confidence-value"]')
        ?.textContent
    ).toBe("76%");
    expect(
      container.querySelector('[data-testid="atmosphere-multiplier-value"]')
        ?.textContent
    ).toBe("1.1x");
    expect(container.textContent).toContain("Optimistic");
  });
});
