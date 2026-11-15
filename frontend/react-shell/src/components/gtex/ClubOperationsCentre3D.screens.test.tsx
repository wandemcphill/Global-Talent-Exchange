(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as THREE from "three";
import { ClubOperationsCentre3D } from "./ClubOperationsCentre3D";
import {
  buildDepartmentInterior,
  updateDepartmentScreens,
} from "./operationsRoomInteriors";
import { api } from "@/lib/api";
import type { ClubOperationsHubPayload, OperationsHubDestination } from "@/lib/ownerBriefing";

jest.mock("react-router-dom", () => {
  const ReactModule = require("react");
  return {
    Link: ({ to, children, ...props }: any) =>
      ReactModule.createElement(
        "a",
        { href: typeof to === "string" ? to : "#", ...props },
        children,
      ),
  };
});

jest.mock("sonner", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

let mockRendererConstructs = 0;
let mockRendererDisposes = 0;

jest.mock("three", () => {
  const actualThree = jest.requireActual("three");
  class MockWebGLRenderer {
    domElement: HTMLCanvasElement;
    shadowMap: { enabled: boolean; type: unknown };
    toneMapping: unknown;
    toneMappingExposure: number;
    setSize = jest.fn();
    setPixelRatio = jest.fn();
    render = jest.fn();
    dispose = jest.fn(() => {
      mockRendererDisposes += 1;
    });

    constructor() {
      mockRendererConstructs += 1;
      const doc = (globalThis as unknown as { document?: Document }).document;
      this.domElement = doc
        ? doc.createElement("canvas")
        : ({
            addEventListener: jest.fn(),
            removeEventListener: jest.fn(),
            remove: jest.fn(),
            style: {},
            setAttribute: jest.fn(),
          } as unknown as HTMLCanvasElement);
      this.shadowMap = { enabled: false, type: actualThree.PCFSoftShadowMap };
      this.toneMapping = actualThree.ACESFilmicToneMapping;
      this.toneMappingExposure = 1;
    }
  }

  class MockPMREMGenerator {
    fromScene = jest.fn(() => ({ texture: { dispose: jest.fn() } }));
    dispose = jest.fn();
  }

  return {
    ...actualThree,
    WebGLRenderer: MockWebGLRenderer,
    PMREMGenerator: MockPMREMGenerator,
  };
});

jest.mock("three/examples/jsm/controls/OrbitControls.js", () => ({
  OrbitControls: class MockOrbitControls {
    target = {
      x: 0,
      y: 0,
      z: 0,
      set(nx: number, ny: number, nz: number) {
        this.x = nx;
        this.y = ny;
        this.z = nz;
      },
      copy(vec: { x: number; y: number; z: number }) {
        this.x = vec.x;
        this.y = vec.y;
        this.z = vec.z;
      },
      lerp: jest.fn(),
      distanceTo: jest.fn(() => 0),
    };
    enableDamping = true;
    dampingFactor = 0.07;
    maxPolarAngle = 1.5;
    minDistance = 6;
    maxDistance = 85;
    addEventListener = jest.fn();
    removeEventListener = jest.fn();
    update = jest.fn();
    dispose = jest.fn();
  },
}));

jest.mock("three/examples/jsm/loaders/GLTFLoader.js", () => ({
  GLTFLoader: class MockGLTFLoader {
    load(_url: string, onLoad: (gltf: { scene: THREE.Group }) => void) {
      const actualThree = jest.requireActual("three");
      const group = new actualThree.Group();
      const box = new actualThree.Mesh(
        new actualThree.BoxGeometry(1, 1, 1),
        new actualThree.MeshBasicMaterial(),
      );
      group.add(box);
      onLoad({ scene: group });
    }
  },
}));

jest.mock("three/examples/jsm/environments/RoomEnvironment.js", () => ({
  RoomEnvironment: class MockRoomEnvironment {},
}));

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
  },
  errMsg: (error: unknown) =>
    error instanceof Error ? error.message : "Request failed",
}));

function buildHubFixture(overrides?: {
  cash?: number;
  worldDay?: number;
  protocolActive?: boolean;
  effectiveMentality?: string;
}): ClubOperationsHubPayload {
  const cash = overrides?.cash ?? 120000;
  const worldDay = overrides?.worldDay ?? 5;
  const protocolActive = overrides?.protocolActive ?? false;
  const effectiveMentality = overrides?.effectiveMentality ?? "balanced";

  const makeStaff = (roleKey: string, name: string, roleLabel: string, vacant = false) => ({
    role_key: roleKey,
    name,
    role_label: roleLabel,
    style: "balanced_specialist",
    mood: 80,
    loyalty: 75,
    is_vacant: vacant,
    is_appointed: !vacant,
  });

  const destinations: OperationsHubDestination[] = [
    {
      destination_key: "executive_office",
      label: "Executive Office",
      short_label: "Executive",
      subtitle: "Owner briefing and urgent risks",
      lead_role_key: "owner",
      communication_channel_mode: "office_wide",
      staff_lead: makeStaff("owner", "Club Owner", "Owner"),
      glb_model: "/models/campus/club_hq_operations.glb",
      exterior_glb: "/models/campus/club_hq.glb",
      accent_color: "#d6b56d",
      position_3d: [0, 0, -18],
      camera_position: [0, 8, -7],
      camera_target: [0, 1.5, -18],
      hotspots: [
        { id: "exec-brief", label: "Daily Briefing Desk", action: "inspect_briefing", offset: [0, 1.4, 2] },
      ],
      report_section_key: "executive_briefing",
      report: {
        section_key: "executive_briefing",
        financial_position: { cash_gtex: cash, fan_coin: 420 },
        squad_condition_and_availability: { squad_size: 24, available_players: 22, avg_morale: 84 },
        urgent_risks: [{ risk_id: "r1", severity: "high", department: "medical", title: "Hamstring Watch", detail: "Manage load" }],
        outstanding_decisions_count: 3,
      },
      open_decisions: [],
      open_decisions_count: 3,
      recent_messages: [],
      active_events_count: 1,
    },
    {
      destination_key: "managers_office",
      label: "First-Team Manager's Office",
      short_label: "Manager",
      subtitle: "Tactics, squad morale and match preparation",
      lead_role_key: "first_team_manager",
      communication_channel_mode: "direct",
      staff_lead: makeStaff("first_team_manager", "Marco Bellini", "First-Team Manager"),
      tactical_authority: {
        authority_model: "manager_autonomy_v2",
        is_non_binding_preference: true,
        manager_appointed: true,
        manager_name: "Marco Bellini",
        owner_requested_mentality: "attacking",
        manager_preferred_mentality: effectiveMentality,
        effective_mentality: effectiveMentality,
        decision_status: effectiveMentality === "attacking" ? "accepted" : "modified",
        implemented_as_requested: effectiveMentality === "attacking",
        reasoning: "Protecting midfield structure against high press.",
      },
      glb_model: "/models/campus/first_team_pitch_alpha.glb",
      exterior_glb: "/models/campus/first_team_pitch_alpha.glb",
      accent_color: "#38bdf8",
      position_3d: [18, 0, -10],
      camera_position: [18, 8, 1],
      camera_target: [18, 1.5, -10],
      hotspots: [
        { id: "mgr-tactics", label: "Tactical Board", action: "set_mentality", offset: [0, 1.4, 2] },
      ],
      report_section_key: "managers_report",
      report: {
        section_key: "managers_report",
        tactical_and_squad_concerns: { active_mentality: effectiveMentality, formation: "4-2-3-1" },
        fitness_and_selection: { available_count: 22, avg_fitness: 91 },
        player_morale: { avg_morale: 84 },
        upcoming_match_preparation: { pledged_win_bonus_gtex: 600, home_advantage_bonus: 4 },
      },
      open_decisions: [],
      open_decisions_count: 1,
      recent_messages: [],
      active_events_count: 0,
    },
    {
      destination_key: "general_managers_office",
      label: "General Manager's Office",
      short_label: "GM Office",
      subtitle: "Delegation, staffing and campus works",
      lead_role_key: "general_manager",
      communication_channel_mode: "direct",
      staff_lead: makeStaff("general_manager", "Helena Novak", "General Manager"),
      glb_model: "/models/campus/club_hq.glb",
      exterior_glb: "/models/campus/club_hq.glb",
      accent_color: "#a78bfa",
      position_3d: [18, 0, 10],
      camera_position: [18, 8, 21],
      camera_target: [18, 1.5, 10],
      hotspots: [
        { id: "gm-delegation", label: "Delegation Console", action: "configure_delegation", offset: [0, 1.4, 2] },
      ],
      report_section_key: "general_managers_report",
      report: {
        section_key: "general_managers_report",
        administrative_matters: {
          delegation_policy: { mode: "autonomous" },
          scheduled_meetings_count: 2,
        },
        club_operations: {
          operational_modules_count: 5,
          active_construction_projects: [{ id: "build-1", name: "Hydro Wing" }],
        },
        staff_and_organisation: {
          executive_team: [
            makeStaff("general_manager", "Helena Novak", "General Manager"),
            makeStaff("first_team_manager", "Marco Bellini", "First-Team Manager"),
            makeStaff("medical_director", "Dr. Nadia Okafor", "Medical Director"),
          ],
        },
      },
      open_decisions: [],
      open_decisions_count: 0,
      recent_messages: [],
      active_directives_count: 2,
      active_events_count: 1,
    },
    {
      destination_key: "academy_department",
      label: "Academy Department",
      short_label: "Academy",
      subtitle: "Youth intake and regen progression",
      lead_role_key: "head_of_youth_development",
      communication_channel_mode: "direct",
      staff_lead: makeStaff("head_of_youth_development", "Tomasz Kowalski", "HOYD"),
      glb_model: "/models/campus/academy_complex.glb",
      exterior_glb: "/models/campus/academy_complex.glb",
      accent_color: "#f59e0b",
      position_3d: [0, 0, 18],
      camera_position: [0, 8, 29],
      camera_target: [0, 1.5, 18],
      hotspots: [
        { id: "acad-intake", label: "Intake Monitor", action: "commission_intake", offset: [0, 1.4, 2] },
      ],
      report_section_key: "hoyd_report",
      report: {
        section_key: "hoyd_report",
        academy_development: {
          academy_facility_level: 3,
          regen_count: 7,
          ready_for_senior_count: 2,
          campus_development_speed_pct: 15,
        },
        intake_recommendations: { projected_cohort_size: 3, next_intake_cost_gtex: 4500 },
        development_concerns: [],
      },
      open_decisions: [],
      open_decisions_count: 1,
      recent_messages: [],
      active_events_count: 0,
    },
    {
      destination_key: "medical_department",
      label: "Medical & Rehab Lab",
      short_label: "Medical",
      subtitle: "Injury treatment and conditioning",
      lead_role_key: "medical_director",
      communication_channel_mode: "direct",
      staff_lead: makeStaff("medical_director", "Dr. Nadia Okafor", "Medical Director"),
      glb_model: "/models/campus/recovery_hydro_hub.glb",
      exterior_glb: "/models/campus/recovery_hydro_hub.glb",
      accent_color: "#ec4899",
      position_3d: [-18, 0, 10],
      camera_position: [-18, 8, 21],
      camera_target: [-18, 1.5, 10],
      hotspots: [
        { id: "med-rehab", label: "Rehab Ward", action: "run_conditioning", offset: [0, 1.4, 2] },
      ],
      report_section_key: "medical_directors_report",
      report: {
        section_key: "medical_directors_report",
        rehabilitation_status: {
          active_rehab_count: 2,
          daily_injury_heal_days: 2,
          protocol_executed_today: protocolActive,
          protocol_cost_gtex: 800,
        },
        medical_facility_performance: { medical_facility_level: 2, injury_reduction_pct: 14 },
        squad_fitness_concerns: { avg_squad_fitness: 89, below_85_fitness_count: 3 },
        injured_players: [],
        players_requiring_special_attention: [],
      },
      open_decisions: [],
      open_decisions_count: 1,
      recent_messages: [],
      active_events_count: 0,
    },
    {
      destination_key: "finance_commercial_office",
      label: "Finance & Commercial",
      short_label: "Finance",
      subtitle: "Treasury, sponsors and gate receipts",
      lead_role_key: "finance_commercial_director",
      communication_channel_mode: "direct",
      staff_lead: makeStaff("finance_commercial_director", "Claire Vance", "Finance Director"),
      glb_model: "/models/campus/vip_skybox_concourse.glb",
      exterior_glb: "/models/campus/vip_skybox_concourse.glb",
      accent_color: "#22d3ee",
      position_3d: [-18, 0, -10],
      camera_position: [-18, 8, 1],
      camera_target: [-18, 1.5, -10],
      hotspots: [
        { id: "fin-ledger", label: "Treasury Desk", action: "inspect_ledger", offset: [0, 1.4, 2] },
      ],
      report_section_key: "financial_commercial_report",
      report: {
        section_key: "financial_commercial_report",
        balances: { cash_gtex: cash, fan_coin_balance: 420, club_valuation_gtex: 890000 },
        recent_income_and_expenditure: { net_cashflow_gtex: 3400, recent_ledger_events: [] },
        sponsor_income: {
          active_deals: [{ id: "sp-1", sponsor_name: "Aeris Tech", per_match_gross: 1500 }],
          per_match_sponsor_income_gtex: 1500,
          available_offers: [],
        },
        matchday_revenue: { stadium_capacity: 22000, projected_next_home_gate_gtex: 18500 },
      },
      open_decisions: [],
      open_decisions_count: 0,
      recent_messages: [],
      active_events_count: 0,
    },
  ];

  return {
    club: {
      club_id: "club-stage3",
      club_name: "Real Gtex FC",
      owner_name: "Club Owner",
      world_day: worldDay,
      prestige: 62,
      prestige_tier: "Contender",
      fans: 14500,
      mentality: effectiveMentality,
      owner_requested_mentality: "attacking",
      manager_preferred_mentality: effectiveMentality,
      effective_matchday_mentality: effectiveMentality,
      manager_decision_status: effectiveMentality === "attacking" ? "accepted" : "modified",
      manager_tactical_authority: destinations[1].tactical_authority,
      cash_gtex: cash,
      fan_coin: 420,
      club_valuation_gtex: 890000,
    },
    daily_briefing: {
      world_day: worldDay,
      headline: "Full squad operational before weekend fixture",
      summary: "Authoritative treasury and medical telemetry synced.",
      executive_briefing: destinations[0].report as ClubOperationsHubPayload["daily_briefing"]["executive_briefing"],
    },
    destinations,
    actionable_decisions: {
      department_decisions: [],
      inbox_decisions: [],
      boardroom_dilemma: null,
      total_open_count: 3,
    },
    operational_timeline: [],
    decision_history: [],
    recent_communications: [],
    staff: {},
    staff_catalog: [],
  };
}

describe("ClubOperationsCentre3D Stage 3 - Live CanvasTexture Screens & Persistence", () => {
  const originalGetContext = HTMLCanvasElement.prototype.getContext;
  const originalRaf = window.requestAnimationFrame;
  const originalCancelRaf = window.cancelAnimationFrame;

  let drawnTexts: string[];

  beforeEach(() => {
    jest.clearAllMocks();
    mockRendererConstructs = 0;
    mockRendererDisposes = 0;
    drawnTexts = [];

    HTMLCanvasElement.prototype.getContext = function getContext(contextId: string) {
      if (contextId === "2d") {
        return {
          fillStyle: "",
          font: "",
          fillRect: jest.fn(),
          fillText: jest.fn((text: string) => {
            drawnTexts.push(text);
          }),
        } as unknown as CanvasRenderingContext2D;
      }
      if (contextId === "webgl2" || contextId === "webgl" || contextId === "experimental-webgl") {
        return {} as WebGLRenderingContext;
      }
      return null;
    } as typeof HTMLCanvasElement.prototype.getContext;

    window.requestAnimationFrame = ((cb: FrameRequestCallback) =>
      window.setTimeout(() => cb(16), 0)) as typeof window.requestAnimationFrame;
    window.cancelAnimationFrame = ((id: number) =>
      window.clearTimeout(id)) as typeof window.cancelAnimationFrame;
  });

  afterEach(() => {
    HTMLCanvasElement.prototype.getContext = originalGetContext;
    window.requestAnimationFrame = originalRaf;
    window.cancelAnimationFrame = originalCancelRaf;
  });

  test("all 6 rooms render authoritative backend telemetry and fallback honestly when unavailable", () => {
    const hub = buildHubFixture({ cash: 120000, protocolActive: false, effectiveMentality: "balanced" });
    const screensByDest = hub.destinations.map((dest) => buildDepartmentInterior(dest, hub).screens);

    const execTelemetry = screensByDest[0].find((s) => s.kind === "telemetry");
    expect(execTelemetry?.snapshot.dataAvailable).toBe(true);
    expect(execTelemetry?.mesh.userData.screenLines).toEqual(
      expect.arrayContaining([
        expect.stringContaining("120,000 GTX"),
        expect.stringContaining("22/24 FIT"),
        expect.stringContaining("1 HIGH PRIORITY"),
      ]),
    );

    const mgrTelemetry = screensByDest[1].find((s) => s.kind === "telemetry");
    expect(mgrTelemetry?.mesh.userData.screenLines).toEqual(
      expect.arrayContaining([
        expect.stringContaining("OWNER REQUEST: ATTACKING"),
        expect.stringContaining("MODIFIED (Marco Bellini)"),
        expect.stringContaining("BALANCED"),
      ]),
    );

    const gmTelemetry = screensByDest[2].find((s) => s.kind === "telemetry");
    expect(gmTelemetry?.mesh.userData.screenLines).toEqual(
      expect.arrayContaining([
        expect.stringContaining("AUTONOMOUS"),
        expect.stringContaining("3/3 APPOINTED"),
        expect.stringContaining("1 IN BUILD"),
      ]),
    );

    const acadTelemetry = screensByDest[3].find((s) => s.kind === "telemetry");
    expect(acadTelemetry?.mesh.userData.screenLines).toEqual(
      expect.arrayContaining([
        expect.stringContaining("7 PROSPECTS"),
        expect.stringContaining("2 READY FOR CALL-UP"),
      ]),
    );

    const medTelemetry = screensByDest[4].find((s) => s.kind === "telemetry");
    expect(medTelemetry?.mesh.userData.screenLines).toEqual(
      expect.arrayContaining([
        expect.stringContaining("2 IN REHAB"),
        expect.stringContaining("STANDBY (800 GTX)"),
      ]),
    );

    const finTelemetry = screensByDest[5].find((s) => s.kind === "telemetry");
    expect(finTelemetry?.mesh.userData.screenLines).toEqual(
      expect.arrayContaining([
        expect.stringContaining("120,000 GTX"),
        expect.stringContaining("+3,400 GTX"),
        expect.stringContaining("1 ACTIVE"),
      ]),
    );

    // Honest missing-data fallback when backend payload and report are empty
    const emptyMedical = buildDepartmentInterior(
      {
        ...hub.destinations[4],
        report: {},
      },
      null,
    );
    const unavailableScreen = emptyMedical.screens.find((s) => s.kind === "telemetry");
    expect(unavailableScreen?.snapshot.dataAvailable).toBe(false);
    expect(unavailableScreen?.mesh.userData.screenLines).toEqual(
      expect.arrayContaining([expect.stringContaining("DATA UNAVAILABLE")]),
    );
  });

  test("updateDepartmentScreens mutates existing CanvasTextures in-place without reallocating textures", () => {
    const initialHub = buildHubFixture({ cash: 120000, protocolActive: false });
    const allScreens = initialHub.destinations.flatMap((d) => buildDepartmentInterior(d, initialHub).screens);
    const medicalTelemetry = allScreens.find((s) => s.id === "medical_department:telemetry");
    const originalTexture = medicalTelemetry?.texture;

    // Repeated call with unchanged payload performs zero redraws
    expect(updateDepartmentScreens(allScreens, initialHub.destinations, initialHub)).toBe(0);

    drawnTexts = [];
    const updatedHub = buildHubFixture({ cash: 119200, protocolActive: true });
    const updatedCount = updateDepartmentScreens(allScreens, updatedHub.destinations, updatedHub);
    expect(updatedCount).toBeGreaterThan(0);
    expect(medicalTelemetry?.texture).toBe(originalTexture);
    expect(medicalTelemetry?.mesh.userData.screenLines).toEqual(
      expect.arrayContaining([expect.stringContaining("HYDRO & CRYO: ACTIVE TODAY")]),
    );
    expect(drawnTexts).toEqual(expect.arrayContaining(["ACTIVE TODAY", "119,200 GTX"]));
  });

  test("ClubOperationsCentre3D updates 3D screens on live backend refetch without tearing down WebGLRenderer", async () => {
    let currentHub = buildHubFixture({ cash: 120000, protocolActive: false });
    (api.get as jest.Mock).mockImplementation(() => Promise.resolve({ data: currentHub }));
    (api.post as jest.Mock).mockImplementation(() => {
      currentHub = buildHubFixture({ cash: 119200, protocolActive: true });
      return Promise.resolve({
        data: { status: "executed", treasury_cash_gtex: 119200 },
      });
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const container = document.createElement("div");
    document.body.appendChild(container);
    let root: Root | null = createRoot(container);

    const flush = async () => {
      await act(async () => {
        await Promise.resolve();
        await new Promise((resolve) => setTimeout(resolve, 20));
      });
    };

    await act(async () => {
      root?.render(
        <QueryClientProvider client={queryClient}>
          <ClubOperationsCentre3D clubId="club-stage3" />
        </QueryClientProvider>,
      );
    });
    await flush();

    expect(mockRendererConstructs).toBe(1);

    const ops3d = (window as unknown as {
      __GTEX_OPERATIONS_3D__?: {
        roomScreens?: Array<{ id: string; texture: THREE.CanvasTexture; mesh: THREE.Mesh }>;
      };
    }).__GTEX_OPERATIONS_3D__;
    const medScreenBefore = ops3d?.roomScreens?.find((s) => s.id === "medical_department:telemetry");
    const medTextureBefore = medScreenBefore?.texture;
    const disposeSpy = medTextureBefore ? jest.spyOn(medTextureBefore, "dispose") : null;
    expect(medScreenBefore?.mesh.userData.screenLines).toEqual(
      expect.arrayContaining([expect.stringContaining("STANDBY (800 GTX)")]),
    );

    // Navigate to Medical Department and trigger live Recovery Protocol action
    const medTab = container.querySelector('[data-testid="destination-tab-medical_department"]') as HTMLButtonElement | null;
    expect(medTab).not.toBeNull();
    await act(async () => {
      medTab?.click();
    });
    await flush();

    const protocolBtn = container.querySelector(
      '[data-testid="run-medical-recovery-protocol-btn"]',
    ) as HTMLButtonElement | null;
    expect(protocolBtn).not.toBeNull();
    await act(async () => {
      protocolBtn?.click();
    });
    await flush();
    await flush();

    expect(medScreenBefore?.mesh.userData.screenLines).toEqual(
      expect.arrayContaining([expect.stringContaining("HYDRO & CRYO: ACTIVE TODAY")]),
    );

    // Scene and WebGLRenderer were never torn down or recreated across live hub refetch
    expect(mockRendererConstructs).toBe(1);
    expect(mockRendererDisposes).toBe(0);
    expect(medScreenBefore?.texture).toBe(medTextureBefore);
    expect(disposeSpy).not.toHaveBeenCalled();

    // Unmounting releases renderer and CanvasTextures cleanly
    await act(async () => {
      root?.unmount();
    });
    root = null;
    container.remove();
    expect(mockRendererDisposes).toBe(1);
    expect(disposeSpy).toHaveBeenCalled();
    expect((window as unknown as { __GTEX_OPERATIONS_3D__?: unknown }).__GTEX_OPERATIONS_3D__).toBeUndefined();
  });
});
