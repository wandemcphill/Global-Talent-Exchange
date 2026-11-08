import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { ManagerArrivalScene } from "./ManagerArrivalScene";
import { GtexSceneRegistry } from "../GtexSceneRegistry";
import { type CinematicEventPayload } from "@/lib/ownerBriefing";

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
    post: jest.fn().mockResolvedValue({
      data: {
        media_headline: "Official Statement Registered: Immediate Silverware",
        quote: "We brought elite leadership because this club belongs at the summit.",
        political_impact: { supporter_confidence: "+5", board_ambition: "+4" },
      },
    }),
  },
  errMsg: (err: any, fallback: string) => fallback,
}));

const mockArrivalEvent: CinematicEventPayload = {
  event_id: "evt_mgr_arrival_1",
  event_type: "manager_arrival",
  category: "staff_arrival",
  scene_type: "manager_arrival",
  camera_preset: "convoy_tunnel_walkout",
  lighting_preset: "stadium_floodlight_unveiling",
  render_mode: "3d_webgl",
  fallback_available: true,
  fallback_label: "2D Broadcast Fallback Ready",
  verified_source: true,
  title: "Official Manager Unveiling: Jose Mourinho Appointed",
  subtitle: "First-Team Manager • 3-Year Contract • ₦420,000 GTEX/yr",
  club_branding: {
    club_id: "c_lagos",
    club_name: "Lagos Atlantic FC",
    primary_color: "#10b981",
    secondary_color: "#f59e0b",
    accent_color: "#0f172a",
    stadium_name: "Atlantic Arena",
  },
  metadata: {
    staff_name: "Jose Mourinho",
    role_key: "first_team_manager",
    role_label: "First-Team Manager",
    rating: 91,
    reputation: 95,
    annual_salary_gtex: 420000,
    contract_years: 3,
    signing_fee_gtex: 63000,
    style: "Pragmatic Counter-Attack",
    temperament: "Charismatic",
  },
  created_at: "2026-11-08T18:00:00Z",
};

describe("ManagerArrivalScene", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    jest.clearAllMocks();
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  test("is registered as the authoritative custom renderer for manager_arrival in GtexSceneRegistry", () => {
    const renderer = GtexSceneRegistry.getRenderer("manager_arrival");
    expect(renderer).toBeDefined();
    expect(renderer).toBe(ManagerArrivalScene);
  });

  test("renders manager arrival unveiling with verified contract dossier and honest render badge", async () => {
    const onComplete = jest.fn();
    await act(async () => {
      root.render(
        <ManagerArrivalScene cinematicEvent={mockArrivalEvent} onComplete={onComplete} />
      );
    });

    expect(container.querySelector('[data-testid="manager-arrival-3d-scene"]')).not.toBeNull();
    expect(container.textContent).toContain("Official Manager Unveiling: Jose Mourinho Appointed");
    expect(container.textContent).toContain("420,000 GTEX");
    expect(container.textContent).toContain("OVR 91");
    expect(container.querySelector('[data-testid="arrival-render-mode-badge"]')).not.toBeNull();

    // Test Snapshot capture button
    const snapshotBtn = container.querySelector(
      '[data-testid="capture-arrival-snapshot-btn"]'
    ) as HTMLButtonElement;
    expect(snapshotBtn).not.toBeNull();
    await act(async () => {
      snapshotBtn.click();
    });

    // Switch camera preset to press_flashbulbs
    const pressStageBtn = container.querySelector(
      '[data-testid="arrival-camera-press_flashbulbs"]'
    ) as HTMLButtonElement;
    expect(pressStageBtn).not.toBeNull();
    await act(async () => {
      pressStageBtn.click();
    });
    expect(pressStageBtn.className).toContain("bg-emerald-500");

    // Interactive 3D Press Conference Q&A overlay is active
    expect(container.querySelector('[data-testid="arrival-press-qa-overlay"]')).not.toBeNull();
    const winNowStanceBtn = container.querySelector(
      '[data-testid="press-stance-championship_ambition"]'
    ) as HTMLButtonElement;
    expect(winNowStanceBtn).not.toBeNull();
    await act(async () => {
      winNowStanceBtn.click();
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(container.textContent).toContain("Official Statement Registered");

    // Click complete button
    const completeBtn = container.querySelector(
      '[data-testid="complete-arrival-cinematic-btn"]'
    ) as HTMLButtonElement;
    expect(completeBtn).not.toBeNull();
    await act(async () => {
      completeBtn.click();
    });
    expect(onComplete).toHaveBeenCalledTimes(1);
  });
});
