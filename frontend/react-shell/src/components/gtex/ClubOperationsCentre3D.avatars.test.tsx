(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as THREE from "three";
import { ClubOperationsCentre3D } from "./ClubOperationsCentre3D";
import {
  buildDepartmentInterior,
  updateDepartmentActors,
} from "./operationsRoomInteriors";
import { api } from "@/lib/api";
import type { ClubOperationsHubPayload, OperationsHubDestination } from "@/lib/ownerBriefing";

let mockRendererConstructs = 0;

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
    dispose = jest.fn();

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
      const mesh = new actualThree.Mesh(
        new actualThree.BoxGeometry(1, 1, 1),
        new actualThree.MeshBasicMaterial(),
      );
      group.add(mesh);
      onLoad({ scene: group });
    }
  },
}));

jest.mock("three/examples/jsm/environments/RoomEnvironment.js", () => ({
  RoomEnvironment: class MockRoomEnvironment {},
}));

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

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
  },
  errMsg: (error: unknown) =>
    error instanceof Error ? error.message : "Request failed",
}));

function buildHub(vacantMedical = false): ClubOperationsHubPayload {
  const makeStaff = (roleKey: string, name: string, roleLabel: string, vacant = false) => ({
    role_key: roleKey,
    name,
    role_label: roleLabel,
    mood: 82,
    loyalty: 78,
    is_vacant: vacant,
    is_appointed: !vacant,
  });

  const destinations: OperationsHubDestination[] = [
    {
      destination_key: "executive_office",
      label: "Executive Office",
      short_label: "Executive",
      subtitle: "Owner briefing",
      lead_role_key: "owner",
      communication_channel_mode: "office_wide",
      staff_lead: makeStaff("owner", "Club Owner", "Club Owner", false),
      glb_model: "/models/campus/club_hq.glb",
      exterior_glb: "/models/campus/club_hq.glb",
      accent_color: "#d6b56d",
      position_3d: [0, 0, 0],
      camera_position: [0, 13, 21],
      camera_target: [0, 2.5, 0],
      hotspots: [{ id: "briefing_desk", label: "Briefing Desk", action: "inspect_briefing", offset: [-1.4, 1.4, 2.2] }],
      report_section_key: "executive_briefing",
      report: { financial_position: { cash_gtex: 90000 } },
      open_decisions: [],
      open_decisions_count: 0,
      recent_messages: [],
    },
    {
      destination_key: "managers_office",
      label: "Manager's Office",
      short_label: "Manager",
      subtitle: "Tactics",
      lead_role_key: "first_team_manager",
      communication_channel_mode: "direct",
      staff_lead: makeStaff("first_team_manager", "Marco Bellini", "First-Team Manager", false),
      glb_model: "/models/campus/stadium_main.glb",
      exterior_glb: "/models/campus/stadium_main.glb",
      accent_color: "#38bdf8",
      position_3d: [18, 0, 0],
      camera_position: [18, 11, 14],
      camera_target: [18, 2, 0],
      hotspots: [{ id: "tactical_board", label: "Tactical Board", action: "set_mentality", offset: [-1.2, 1.4, 2.0] }],
      report_section_key: "managers_report",
      report: {},
      open_decisions: [],
      open_decisions_count: 0,
      recent_messages: [],
    },
    {
      destination_key: "general_managers_office",
      label: "General Manager's Office",
      short_label: "GM Office",
      subtitle: "Operations",
      lead_role_key: "general_manager",
      communication_channel_mode: "direct",
      staff_lead: makeStaff("general_manager", "Helena Novak", "General Manager", false),
      glb_model: "/models/campus/vip_skybox_concourse.glb",
      exterior_glb: "/models/campus/vip_skybox_concourse.glb",
      accent_color: "#a78bfa",
      position_3d: [9, 0, 16],
      camera_position: [9, 11, 28],
      camera_target: [9, 2, 16],
      hotspots: [{ id: "delegation_desk", label: "Delegation Desk", action: "configure_delegation", offset: [0, 1.4, 2.0] }],
      report_section_key: "general_managers_report",
      report: {
        administrative_matters: { delegation_policy: { mode: "balanced" } },
        staff_and_organisation: {
          executive_team: [
            makeStaff("general_manager", "Helena Novak", "General Manager", false),
            makeStaff("medical_director", vacantMedical ? "Vacant Seat" : "Dr. Nadia Okafor", "Medical Director", vacantMedical),
          ],
        },
      },
      open_decisions: [],
      open_decisions_count: 0,
      recent_messages: [],
    },
    {
      destination_key: "academy_department",
      label: "Academy Department",
      short_label: "Academy",
      subtitle: "Youth intake",
      lead_role_key: "head_of_youth_development",
      communication_channel_mode: "direct",
      staff_lead: makeStaff("head_of_youth_development", "Tomasz Kowalski", "HOYD", false),
      glb_model: "/models/campus/elite_academy_complex.glb",
      exterior_glb: "/models/campus/elite_academy_complex.glb",
      accent_color: "#f59e0b",
      position_3d: [-18, 0, 0],
      camera_position: [-18, 11, 14],
      camera_target: [-18, 2, 0],
      hotspots: [{ id: "intake_desk", label: "Intake Desk", action: "commission_intake", offset: [0, 1.4, 2.0] }],
      report_section_key: "hoyd_report",
      report: {},
      open_decisions: [],
      open_decisions_count: 0,
      recent_messages: [],
    },
    {
      destination_key: "medical_department",
      label: "Medical Department",
      short_label: "Medical",
      subtitle: "Rehab lab",
      lead_role_key: "medical_director",
      communication_channel_mode: vacantMedical ? "vacant" : "direct",
      staff_lead: makeStaff("medical_director", vacantMedical ? "Vacant Seat" : "Dr. Nadia Okafor", "Medical Director", vacantMedical),
      glb_model: "/models/campus/recovery_hydro_hub.glb",
      exterior_glb: "/models/campus/recovery_hydro_hub.glb",
      accent_color: "#ec4899",
      position_3d: [-9, 0, 16],
      camera_position: [-9, 11, 28],
      camera_target: [-9, 2, 16],
      hotspots: [{ id: "rehab_ward", label: "Rehab Ward", action: "run_conditioning", offset: [0, 1.4, 2.0] }],
      report_section_key: "medical_directors_report",
      report: {},
      open_decisions: [],
      open_decisions_count: 0,
      recent_messages: [],
    },
    {
      destination_key: "finance_commercial_office",
      label: "Finance & Commercial",
      short_label: "Finance",
      subtitle: "Treasury",
      lead_role_key: "finance_commercial_director",
      communication_channel_mode: "direct",
      staff_lead: makeStaff("finance_commercial_director", "Claire Vance", "Finance Director", false),
      glb_model: "/models/campus/vip_hospitality.glb",
      exterior_glb: "/models/campus/vip_hospitality.glb",
      accent_color: "#22d3ee",
      position_3d: [0, 0, -18],
      camera_position: [0, 11, -4],
      camera_target: [0, 2, -18],
      hotspots: [{ id: "ledger_vault", label: "Treasury Desk", action: "inspect_ledger", offset: [0, 1.4, 2.0] }],
      report_section_key: "financial_commercial_report",
      report: {},
      open_decisions: [],
      open_decisions_count: 0,
      recent_messages: [],
    },
  ];

  return {
    club: {
      club_id: "club-stage4",
      club_name: "Gtex Athletic",
      owner_name: "Club Owner",
      world_day: 9,
      prestige: 60,
      prestige_tier: "Contender",
      fans: 12000,
      mentality: "balanced",
      cash_gtex: 90000,
      fan_coin: 350,
      club_valuation_gtex: 750000,
    },
    daily_briefing: { world_day: 9, headline: "HQ Operational" },
    destinations,
    actionable_decisions: { department_decisions: [], inbox_decisions: [], total_open_count: 0 },
    operational_timeline: [],
    decision_history: [],
    recent_communications: [],
    staff: {},
    staff_catalog: [],
  };
}

describe("ClubOperationsCentre3D Stage 4 - Authority-Aware Staff Avatars & Room Polish", () => {
  const originalGetContext = HTMLCanvasElement.prototype.getContext;
  const originalRaf = window.requestAnimationFrame;
  const originalCancelRaf = window.cancelAnimationFrame;

  let activeRoot: Root | null = null;
  let activeContainer: HTMLDivElement | null = null;

  beforeEach(() => {
    jest.clearAllMocks();
    mockRendererConstructs = 0;

    HTMLCanvasElement.prototype.getContext = function getContext(contextId: string) {
      if (contextId === "2d") {
        return {
          fillStyle: "",
          font: "",
          fillRect: jest.fn(),
          fillText: jest.fn(),
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

  afterEach(async () => {
    if (activeRoot) {
      await act(async () => {
        activeRoot?.unmount();
      });
      activeRoot = null;
    }
    if (activeContainer) {
      activeContainer.remove();
      activeContainer = null;
    }
    HTMLCanvasElement.prototype.getContext = originalGetContext;
    window.requestAnimationFrame = originalRaf;
    window.cancelAnimationFrame = originalCancelRaf;
  });

  test("vacant department hides 3D staff actor while appointed departments expose role props", () => {
    const vacantHub = buildHub(true);
    const medicalBuilt = buildDepartmentInterior(vacantHub.destinations[4], vacantHub);
    expect(medicalBuilt.animatedActors).toHaveLength(1);
    expect(medicalBuilt.animatedActors[0].visible).toBe(false);
    expect(medicalBuilt.animatedActors[0].userData.isVacant).toBe(true);
    expect(medicalBuilt.animatedActors[0].userData.propKind).toBe("medical_scanner");

    const managerBuilt = buildDepartmentInterior(vacantHub.destinations[1], vacantHub);
    expect(managerBuilt.animatedActors[0].visible).toBe(true);
    expect(managerBuilt.animatedActors[0].userData.staffName).toBe("Marco Bellini");
    expect(managerBuilt.animatedActors[0].userData.propKind).toBe("tactical_tablet");

    // Unique GLB paths across all 6 rooms
    const glbPaths = vacantHub.destinations.map((d) => d.glb_model);
    expect(new Set(glbPaths).size).toBe(6);
  });

  test("dismissing a staff lead updates 3D actor visibility in-place without rebuilding WebGLRenderer", async () => {
    let hubState = buildHub(false);
    (api.get as jest.Mock).mockImplementation(() => Promise.resolve({ data: hubState }));
    (api.post as jest.Mock).mockImplementation(() => {
      hubState = buildHub(true);
      return Promise.resolve({ data: { dismissed: true, role_key: "medical_director" } });
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    activeContainer = document.createElement("div");
    document.body.appendChild(activeContainer);
    activeRoot = createRoot(activeContainer);

    const flush = async () => {
      await act(async () => {
        await Promise.resolve();
        await new Promise((resolve) => setTimeout(resolve, 20));
      });
    };

    await act(async () => {
      activeRoot?.render(
        <QueryClientProvider client={queryClient}>
          <ClubOperationsCentre3D clubId="club-stage4" />
        </QueryClientProvider>,
      );
    });
    await flush();

    const ops3d = (window as unknown as {
      __GTEX_OPERATIONS_3D__?: { roomActors?: THREE.Group[] };
    }).__GTEX_OPERATIONS_3D__;
    const medActor = ops3d?.roomActors?.find(
      (actor) => actor.userData.destinationKey === "medical_department",
    );
    expect(medActor?.visible).toBe(true);
    expect(mockRendererConstructs).toBe(1);

    // Switch to GM Office and dismiss Medical Director
    const gmTab = activeContainer.querySelector(
      '[data-testid="destination-tab-general_managers_office"]',
    ) as HTMLButtonElement | null;
    expect(gmTab).not.toBeNull();
    await act(async () => {
      gmTab?.click();
    });
    await flush();

    const dismissBtn = activeContainer.querySelector(
      '[data-testid="dismiss-staff-medical_director"]',
    ) as HTMLButtonElement | null;
    expect(dismissBtn).not.toBeNull();
    await act(async () => {
      dismissBtn?.click();
    });
    await flush();
    await flush();

    expect(medActor?.visible).toBe(false);
    expect(medActor?.userData.isVacant).toBe(true);
    expect(mockRendererConstructs).toBe(1);

    // Direct helper test: re-appointing toggles visibility back on cleanly
    const appointedHub = buildHub(false);
    expect(updateDepartmentActors([medActor!], appointedHub.destinations)).toBe(1);
    expect(medActor?.visible).toBe(true);
  });
});
