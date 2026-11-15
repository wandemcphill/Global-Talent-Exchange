import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ClubOperationsCentre3D } from "./ClubOperationsCentre3D";
import { buildDepartmentInterior } from "./operationsRoomInteriors";

var mockToastSuccess = jest.fn();
var mockToastError = jest.fn();
var mockToastWarning = jest.fn();
var mockToastInfo = jest.fn();
var mockRaycasterHits: any[] = [];
var mockLastCanvas: HTMLCanvasElement | null = null;

jest.mock("react-router-dom", () => {
  const ReactModule = require("react");
  return {
    Link: ({ to, children, ...props }: any) =>
      ReactModule.createElement("a", { href: typeof to === "string" ? to : "#", ...props }, children),
  };
});

jest.mock("sonner", () => ({
  toast: {
    success: (...args: any[]) => mockToastSuccess(...args),
    error: (...args: any[]) => mockToastError(...args),
    warning: (...args: any[]) => mockToastWarning(...args),
    info: (...args: any[]) => mockToastInfo(...args),
  },
}));

jest.mock("three", () => {
  class MockVector3 {
    x = 0;
    y = 0;
    z = 0;
    set(x = 0, y = 0, z = 0) {
      this.x = x;
      this.y = y;
      this.z = z;
      return this;
    }
    setScalar(s = 0) {
      this.x = s;
      this.y = s;
      this.z = s;
      return this;
    }
    copy(v: any) {
      if (v) {
        this.x = v.x || 0;
        this.y = v.y || 0;
        this.z = v.z || 0;
      }
      return this;
    }
    clone() {
      return new MockVector3().copy(this);
    }
    add() {
      return this;
    }
    sub() {
      return this;
    }
    lerp() {
      return this;
    }
    distanceTo() {
      return 0;
    }
  }
  const mockThree: any = {
    Scene: class {
      background: any = null;
      fog: any = null;
      environment: any = null;
      add() {}
      remove() {}
      traverse() {}
    },
    PerspectiveCamera: class {
      position = new MockVector3();
      aspect = 1;
      lookAt = () => {};
      updateProjectionMatrix = () => {};
    },
    WebGLRenderer: class {
      domElement: HTMLCanvasElement;
      shadowMap = { enabled: false, type: 0 };
      constructor() {
        this.domElement = (globalThis as any).document.createElement("canvas");
        this.domElement.getBoundingClientRect = () =>
          ({ left: 0, top: 0, width: 800, height: 500, right: 800, bottom: 500, x: 0, y: 0, toJSON: () => ({}) }) as any;
        mockLastCanvas = this.domElement;
      }
      setSize = () => {};
      setPixelRatio = () => {};
      render = () => {};
      dispose = () => {};
    },
    AmbientLight: class {},
    DirectionalLight: class {
      position = new MockVector3();
      color = { setHex: () => {} };
      intensity = 1;
      castShadow = false;
      shadow = { mapSize: { set: () => {} }, camera: { near: 0, far: 0, left: 0, right: 0, top: 0, bottom: 0 } };
    },
    HemisphereLight: class {
      position = new MockVector3();
    },
    PointLight: class {
      position = new MockVector3();
    },
    Group: class {
      name = "";
      position = new MockVector3();
      scale = new MockVector3();
      rotation = { set: () => {}, x: 0, y: 0, z: 0 };
      children: any[] = [];
      userData: any = {};
      add() {}
      traverse() {}
      clone() {
        return new mockThree.Group();
      }
    },
    Mesh: class {
      name = "";
      position = new MockVector3();
      scale = new MockVector3();
      rotation = { set: () => {}, x: 0, y: 0, z: 0 };
      castShadow = false;
      receiveShadow = false;
      userData: any = {};
      lookAt = () => {};
      add() {}
    },
    BoxGeometry: class {},
    CylinderGeometry: class {},
    RingGeometry: class {},
    PlaneGeometry: class {},
    SphereGeometry: class {},
    EdgesGeometry: class {},
    LineSegments: class {
      position = new MockVector3();
      name = "";
    },
    MeshStandardMaterial: class {},
    MeshBasicMaterial: class {},
    MeshPhysicalMaterial: class {},
    LineBasicMaterial: class {},
    CanvasTexture: class {
      colorSpace: any;
      anisotropy = 1;
      dispose = () => {};
    },
    Vector3: MockVector3,
    Vector2: class {
      x = 0;
      y = 0;
      set(x = 0, y = 0) {
        this.x = x;
        this.y = y;
        return this;
      }
    },
    Box3: class {
      min = { x: 0, y: 0, z: 0 };
      max = { x: 1, y: 1, z: 1 };
      setFromObject() {
        return this;
      }
      getSize(t: any) {
        t?.set?.(1, 1, 1);
        return t;
      }
      getCenter(t: any) {
        t?.set?.(0, 0, 0);
        return t;
      }
    },
    Raycaster: class {
      setFromCamera() {}
      intersectObjects() {
        return mockRaycasterHits;
      }
    },
    Color: class {},
    DoubleSide: 2,
    PCFSoftShadowMap: 2,
    ACESFilmicToneMapping: 4,
    GridHelper: class {
      position = new MockVector3();
    },
    FogExp2: class {},
    PMREMGenerator: class {
      fromScene() {
        return { texture: { dispose: () => {} } };
      }
      dispose() {}
    },
    MathUtils: { lerp: (a: number, b: number, t: number) => a + (b - a) * t },
  };
  return mockThree;
});

jest.mock("three/examples/jsm/controls/OrbitControls.js", () => {
  const makeTarget = () => {
    const t: any = {
      x: 0,
      y: 0,
      z: 0,
      set: (x = 0, y = 0, z = 0) => {
        t.x = x;
        t.y = y;
        t.z = z;
        return t;
      },
      copy: (v: any) => {
        if (v) {
          t.x = v.x || 0;
          t.y = v.y || 0;
          t.z = v.z || 0;
        }
        return t;
      },
      clone: () => makeTarget(),
      lerp: () => t,
      distanceTo: () => 0,
    };
    return t;
  };
  return {
    OrbitControls: class {
      enableDamping = true;
      dampingFactor = 0.05;
      maxPolarAngle = 1;
      minDistance = 1;
      maxDistance = 100;
      target = makeTarget();
      addEventListener = () => {};
      removeEventListener = () => {};
      update = () => {};
      dispose = () => {};
    },
  };
});

jest.mock("three/examples/jsm/loaders/GLTFLoader.js", () => ({
  GLTFLoader: class {
    load(_url: string, onLoad: any) {
      const THREE = require("three");
      onLoad({ scene: { clone: () => new THREE.Group() } });
    }
  },
}));

jest.mock("three/examples/jsm/environments/RoomEnvironment.js", () => ({
  RoomEnvironment: class {},
}));

function buildSixDepartmentHub(opts?: { protocolExecutedToday?: boolean; vacantAcademy?: boolean }) {
  const protocolExecutedToday = opts?.protocolExecutedToday ?? false;
  const vacantAcademy = opts?.vacantAcademy ?? false;
  return {
    club: {
      club_id: "club-s2",
      club_name: "Abuja United FC",
      world_day: 24,
      prestige: 68,
      prestige_tier: "Continental Contender",
      cash_gtex: 640000,
      distributable_gtex: 520000,
      club_valuation_gtex: 1900000,
      mentality: "balanced",
      owner_requested_mentality: "balanced",
      effective_matchday_mentality: "balanced",
      manager_decision_status: "aligned",
      manager_decision_reasoning: "Coach approves balanced match preparation.",
    },
    daily_briefing: {
      id: "brief-s2",
      club_id: "club-s2",
      world_day: 24,
      headline: "Daily Briefing",
      summary: "All departments live",
      metrics: {
        cash_gtex: 640000,
        avg_morale: 81,
        avg_fitness: 89,
        injured_players: 1,
        ready_academy_prospects: 1,
        open_decisions: 1,
      },
      sections: [],
      boardroom_dilemma: {
        dilemma_id: "dil-24",
        title: "Sponsor Extension vs Pre-Season Tour",
        conflict_summary: "Commercial urges fixed tour income while manager wants light travel.",
        status: "open",
        choices: [{ choice_id: "approve_light", label: "Prioritize Squad Freshness", effects_preview: "Manager Mood +4" }],
      },
      department_decisions: [],
    },
    actionable_decisions: { department_decisions: [] },
    operational_timeline: [{ id: "ev-1", world_day: 24, department: "executive_office", title: "Briefing Sync", detail: "Synced", category: "system" }],
    destinations: [
      {
        destination_key: "executive_office",
        label: "Executive Office",
        short_label: "Executive",
        subtitle: "Owner's Command",
        lead_role_key: "owner",
        communication_thread_id: "room:staff",
        communication_channel_mode: "office_wide",
        wing_label: "Penthouse",
        glb_model: "/models/campus/club_hq.glb",
        accent_color: "#10b981",
        position_3d: [0, 0, 0],
        camera_position: [0, 13, 21],
        camera_target: [0, 2.5, 0],
        staff_lead: { role_key: "owner", role_label: "Club Owner", name: "Owner Balogun", mood: 100, is_owner_workspace: true, is_appointed: true },
        alert_count: 1,
        status_badge: "1 Pending",
        hotspots: [
          { id: "exec_desk", label: "Owner's Command Briefing Desk", action: "inspect_briefing", offset: [0, 1.2, 0.5] },
          { id: "dilemma_table", label: "Boardroom Dilemma Holo-Table", action: "inspect_decisions", offset: [2.5, 1.2, -1.0] },
          { id: "world_chronometer", label: "World-Clock Timeline Wall", action: "inspect_timeline", offset: [-2.5, 1.5, -2.5] },
        ],
        report_section_key: "executive_briefing",
        report: {
          title: "Executive Briefing",
          summary: "Club finances healthy.",
          financial_position: { cash_gtex: 640000 },
          squad_condition_and_availability: { available_players: 20, squad_size: 22 },
          stadium_and_campus_operations: { operational_stadium_capacity: 22000 },
          recent_match_performance: { wins: 3, draws: 1, losses: 0 },
          urgent_risks: [],
        },
        open_decisions: [],
        open_decisions_count: 0,
        recent_messages: [],
      },
      {
        destination_key: "managers_office",
        label: "Manager's Office",
        short_label: "Manager",
        subtitle: "First-Team Tactics",
        lead_role_key: "first_team_manager",
        communication_thread_id: "staff:first_team_manager",
        communication_channel_mode: "direct",
        wing_label: "West Wing",
        glb_model: "/models/campus/stadium_main.glb",
        accent_color: "#38bdf8",
        position_3d: [-15, 0, 6],
        camera_position: [-19, 10, 18],
        camera_target: [-14, 2, 4],
        staff_lead: { role_key: "first_team_manager", role_label: "First-Team Manager", name: "Finidi George", mood: 82, is_appointed: true },
        alert_count: 0,
        status_badge: "Matchday: Balanced",
        hotspots: [
          { id: "tactical_pitch_table", label: "3D Tactical Formation Table", action: "set_mentality", offset: [0, 1.2, 0.5] },
          { id: "dugout_prep_screen", label: "Matchday Win-Bonus Console", action: "pledge_win_bonus", offset: [2.5, 1.2, -1.0] },
          { id: "manager_desk", label: "Direct Line: Finidi George", action: "chat_manager", offset: [-2.5, 1.5, -2.5] },
        ],
        report_section_key: "managers_report",
        report: {
          title: "First-Team Report",
          summary: "Squad sharp.",
          first_team_performance: { team_strength: 79 },
          player_morale: { avg_morale: 81, dressing_room_leaders: [] },
          tactical_and_squad_concerns: { formation: "4-3-3", thin_positions: [] },
          fitness_and_selection: { available_count: 20, avg_fitness: 89, unavailable_injured_count: 1, starting_xi_count: 11 },
          upcoming_match_preparation: { pledged_win_bonus_gtex: 600, next_fixture: { home_name: "Abuja United FC", away_name: "Kano Pillars" } },
        },
        open_decisions: [],
        open_decisions_count: 0,
        recent_messages: [],
      },
      {
        destination_key: "general_managers_office",
        label: "General Manager's Office",
        short_label: "General Mgr",
        subtitle: "Administration & Campus",
        lead_role_key: "general_manager",
        communication_thread_id: "staff:general_manager",
        communication_channel_mode: "direct",
        wing_label: "East Wing",
        glb_model: "/models/campus/vip_skybox_concourse.glb",
        accent_color: "#a855f7",
        position_3d: [15, 0, 6],
        camera_position: [19, 10, 18],
        camera_target: [14, 2, 4],
        staff_lead: { role_key: "general_manager", role_label: "General Manager", name: "Paul Mitchell", mood: 85, is_appointed: true },
        alert_count: 0,
        status_badge: "Mode: Balanced",
        hotspots: [
          { id: "delegation_console", label: "Authority & Delegation Matrix", action: "configure_delegation", offset: [0, 1.2, 0.5] },
          { id: "campus_blueprint", label: "Campus Construction Blueprint", action: "inspect_campus", offset: [2.5, 1.2, -1.0] },
          { id: "gm_desk", label: "Direct Line: Paul Mitchell", action: "chat_gm", offset: [-2.5, 1.5, -2.5] },
        ],
        report_section_key: "general_managers_report",
        report: {
          title: "General Manager Report",
          summary: "Campus stable.",
          administrative_matters: { delegation_policy: { delegation_style: "balanced" } },
          club_operations: { facility_levels: { training: 3, academy: 3 }, operational_modules_count: 2, active_construction_projects: [] },
          staff_and_organisation: {
            executive_team: [
              { role_key: "general_manager", role_label: "General Manager", name: "Paul Mitchell", mood: 85, is_vacant: false },
              { role_key: "chief_scout", role_label: "Chief Scout", name: "Chief Scout (Vacant)", is_vacant: true },
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
        subtitle: "Youth & Regens",
        lead_role_key: "head_of_youth_development",
        communication_thread_id: "staff:head_of_youth_development",
        communication_channel_mode: vacantAcademy ? "vacant" : "direct",
        wing_label: "North Precinct",
        glb_model: "/models/campus/elite_academy_complex.glb",
        accent_color: "#f59e0b",
        position_3d: [-14, 0, -14],
        camera_position: [-18, 9, -10],
        camera_target: [-13, 2, -14],
        staff_lead: vacantAcademy
          ? { role_key: "head_of_youth_development", role_label: "Head of Youth Development (Vacant)", name: "Head of Youth Development (Vacant)", is_vacant: true, is_appointed: false }
          : { role_key: "head_of_youth_development", role_label: "Head of Youth Development", name: "Neil Bath", mood: 80, is_appointed: true },
        alert_count: 0,
        status_badge: "1 Academy Regen(s)",
        hotspots: [
          { id: "youth_pitch_lab", label: "Youth Intake Commissioning Desk", action: "commission_intake", offset: [0, 1.2, 0.5] },
          { id: "regen_scanner", label: "Scholar Contract & Promotion Terminal", action: "manage_regens", offset: [2.5, 1.2, -1.0] },
          { id: "hoyd_desk", label: "Direct Line: HOYD", action: "chat_hoyd", offset: [-2.5, 1.5, -2.5] },
        ],
        report_section_key: "hoyd_report",
        report: {
          title: "Academy Report",
          summary: "1 high-potential scholar ready.",
          academy_development: { academy_facility_level: 3, campus_ceiling_bonus: 2, campus_intake_quality_pct: 10, ready_for_senior_count: 1 },
          intake_recommendations: { next_intake_cost_gtex: 4500 },
          prospective_youth_players: [{ id: "reg-1", name: "Chidi Nwosu", position: "CAM", age: 17, rating: 61, potential: 88, headroom: 27, morale: 85, squad_status: "academy" }],
        },
        open_decisions: [],
        open_decisions_count: 0,
        recent_messages: [],
      },
      {
        destination_key: "medical_department",
        label: "Medical Department",
        short_label: "Medical",
        subtitle: "Rehab & Workloads",
        lead_role_key: "medical_director",
        communication_thread_id: "staff:medical_director",
        communication_channel_mode: "direct",
        wing_label: "South Lab",
        glb_model: "/models/campus/recovery_hydro_hub.glb",
        accent_color: "#ec4899",
        position_3d: [14, 0, -14],
        camera_position: [18, 9, -10],
        camera_target: [13, 2, -14],
        staff_lead: { role_key: "medical_director", role_label: "Medical Director", name: "Dr. Amaka Obi", mood: 88, is_appointed: true },
        alert_count: 1,
        status_badge: "1 In Rehab",
        hotspots: [
          { id: "hydro_rehab_pods", label: "Hydro & Cryo Rehabilitation Bay", action: "run_conditioning", offset: [0, 1.2, 0.5] },
          { id: "workload_telemetry", label: "Player Strain & Load Monitor", action: "inspect_workloads", offset: [2.5, 1.2, -1.0] },
          { id: "med_desk", label: "Direct Line: Dr. Amaka Obi", action: "chat_med", offset: [-2.5, 1.5, -2.5] },
        ],
        report_section_key: "medical_directors_report",
        report: {
          title: "Medical Report",
          summary: "1 player in rehab.",
          rehabilitation_status: {
            active_rehab_count: 1,
            daily_injury_heal_days: 2,
            protocol_executed_today: protocolExecutedToday,
            protocol_cost_gtex: 800,
          },
          medical_facility_performance: { injury_reduction_pct: 15, fatigue_recovery_pct: 12 },
          squad_fitness_concerns: { avg_squad_fitness: 89 },
          injured_players: [{ id: "inj-1", name: "Tunde Bakare", position: "CM", injured_days: 2, injury_type: "Ankle Sprain", estimated_recovery_world_days: 1 }],
          players_requiring_special_attention: [],
        },
        open_decisions: [],
        open_decisions_count: 0,
        recent_messages: [],
      },
      {
        destination_key: "finance_commercial_office",
        label: "Finance & Commercial Office",
        short_label: "Finance",
        subtitle: "Treasury & Sponsors",
        lead_role_key: "finance_commercial_director",
        communication_thread_id: "staff:finance_commercial_director",
        communication_channel_mode: "direct",
        wing_label: "East Vault",
        glb_model: "/models/campus/club_hq.glb",
        accent_color: "#22d3ee",
        position_3d: [0, 0, -18],
        camera_position: [0, 11, -12],
        camera_target: [0, 2, -18],
        staff_lead: { role_key: "finance_commercial_director", role_label: "Finance & Commercial Director", name: "Toluwani Ade", mood: 84, is_appointed: true },
        alert_count: 0,
        status_badge: "640,000 GTX",
        hotspots: [
          { id: "ledger_vault", label: "Authoritative GTEX Ledger Terminal", action: "inspect_ledger", offset: [0, 1.2, 0.5] },
          { id: "sponsor_wall", label: "Commercial Partnership Board", action: "sign_sponsor", offset: [2.5, 1.2, -1.0] },
          { id: "matchday_econ", label: "Gate & Broadcast Revenue Desk", action: "inspect_matchday_econ", offset: [-2.5, 1.5, -2.5] },
        ],
        report_section_key: "financial_commercial_report",
        report: {
          title: "Treasury & Commercial Report",
          summary: "Positive cashflow.",
          current_club_balance: { cash_gtex: 640000 },
          wage_obligations: { total_daily_obligations_gtex: 4200 },
          matchday_revenue: { projected_next_home_gate_gtex: 18500, projected_next_home_attendance: 19400, operational_stadium_capacity: 22000 },
          sponsor_income: {
            active_deals: [{ deal_id: "d1", sponsor_name: "Lagos Air", per_match_gross: 3200, matches_remaining: 6 }],
            per_match_sponsor_income_gtex: 3200,
            available_offers: [],
          },
          recent_income_and_expenditure: {
            recent_ledger_entries: [{ id: "le-1", memo: "Matchday Gate Receipt", net_amount: 14500 }],
          },
        },
        open_decisions: [],
        open_decisions_count: 0,
        recent_messages: [],
      },
    ],
    living_world: {
      world_day: 24,
      active_events_count: 0,
      active_directives_count: 0,
      active_events: [],
      active_directives: [],
      relationships: [],
    },
  };
}

describe("Stage 2: Physical 3D stations & operational completeness", () => {
  let container: HTMLDivElement | null = null;
  let root: Root | null = null;
  let queryClient: QueryClient;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    mockRaycasterHits = [];
    mockLastCanvas = null;
    jest.clearAllMocks();
    jest.spyOn(window, "requestAnimationFrame").mockImplementation(((cb: FrameRequestCallback) => {
      return setTimeout(() => cb(0), 0) as unknown as number;
    }) as any);
    jest.spyOn(window, "cancelAnimationFrame").mockImplementation(((id: number) => {
      clearTimeout(id);
    }) as any);
    jest.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(((type: string) => {
      if (type === "2d") {
        return {
          fillStyle: "",
          strokeStyle: "",
          lineWidth: 1,
          font: "",
          textAlign: "left",
          fillRect: () => {},
          strokeRect: () => {},
          fillText: () => {},
          measureText: () => ({ width: 40 }),
          createLinearGradient: () => ({ addColorStop: () => {} }),
          beginPath: () => {},
          roundRect: () => {},
          fill: () => {},
          stroke: () => {},
          moveTo: () => {},
          lineTo: () => {},
          clearRect: () => {},
        };
      }
      return {};
    }) as any);
    HTMLElement.prototype.scrollIntoView = jest.fn();
    Element.prototype.scrollIntoView = jest.fn();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  });

  afterEach(() => {
    act(() => {
      root?.unmount();
    });
    container?.remove();
    queryClient.clear();
    jest.restoreAllMocks();
  });

  test("3D Raycaster terminal click preserves non-first station and focuses its control", async () => {
    const hub = buildSixDepartmentHub();
    jest.spyOn(api, "get").mockResolvedValue({ data: hub });

    await act(async () => {
      root!.render(
        <QueryClientProvider client={queryClient}>
          <ClubOperationsCentre3D clubId="club-s2" />
        </QueryClientProvider>,
      );
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 40));
    });

    expect(mockLastCanvas).not.toBeNull();
    // Simulate Raycaster hit on Medical Department's SECOND station (`workload_telemetry`)
    mockRaycasterHits = [
      {
        object: {
          userData: {
            destinationKey: "medical_department",
            hotspotId: "workload_telemetry",
            hotspotAction: "inspect_workloads",
          },
        },
      },
    ];

    await act(async () => {
      mockLastCanvas!.dispatchEvent(new MouseEvent("pointerdown", { clientX: 100, clientY: 100, bubbles: true }));
      mockLastCanvas!.dispatchEvent(new MouseEvent("pointerup", { clientX: 100, clientY: 100, bubbles: true }));
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 20));
    });

    expect(container!.querySelector('[data-testid="room-panel-medical-department"]')).not.toBeNull();
    const wlStationBtn = container!.querySelector('[data-testid="room-hotspot-workload_telemetry"]');
    expect(wlStationBtn?.getAttribute("aria-pressed")).toBe("true");
    expect(document.activeElement?.getAttribute("data-testid")).toBe("medical-workload-watchlist");
  });

  test("2D floorplan keyboard navigation & cross-room station buttons activate all destinations", async () => {
    const hub = buildSixDepartmentHub({ vacantAcademy: true });
    jest.spyOn(api, "get").mockResolvedValue({ data: hub });

    await act(async () => {
      root!.render(
        <QueryClientProvider client={queryClient}>
          <ClubOperationsCentre3D clubId="club-s2" />
        </QueryClientProvider>,
      );
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 40));
    });

    // Switch to 2D Floorplan mode
    const toggle2d = container!.querySelector('[data-testid="toggle-render-mode"]') as HTMLButtonElement;
    await act(async () => {
      toggle2d.click();
    });

    // Keyboard Enter on Manager floorplan card switches to Manager's Office
    const mgrCard = container!.querySelector('[data-testid="floorplan-room-managers_office"]') as HTMLElement;
    await act(async () => {
      mgrCard.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    });
    expect(container!.querySelector('[data-testid="room-panel-managers-office"]')).not.toBeNull();
    expect(container!.querySelector('[data-testid="manager-squad-readiness"]')).not.toBeNull();

    // Direct 2D click on Finance 2nd station (`sponsor_wall`) preserves station without resetting to `ledger_vault`
    const sponsorStationBtn = container!.querySelector(
      '[data-testid="floorplan-hotspot-finance_commercial_office-sponsor_wall"]',
    ) as HTMLButtonElement;
    await act(async () => {
      sponsorStationBtn.click();
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 20));
    });
    expect(container!.querySelector('[data-testid="room-panel-finance-commercial-office"]')).not.toBeNull();
    expect(container!.textContent).toContain("Lagos Air");
    expect(document.activeElement?.getAttribute("data-testid")).toBe("finance-sponsor-offers");

    // Clicking HOYD direct line on a vacant Academy focuses `vacant-staff-channel-notice` without crashing
    const hoydStationBtn = container!.querySelector(
      '[data-testid="floorplan-hotspot-academy_department-hoyd_desk"]',
    ) as HTMLButtonElement;
    await act(async () => {
      hoydStationBtn.click();
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 20));
    });
    expect(document.activeElement?.getAttribute("data-testid")).toBe("vacant-staff-channel-notice");
  });

  test("Medical Hydro & Cryo station triggers backend recovery protocol & updates to Active Today", async () => {
    let executedToday = false;
    jest.spyOn(api, "get").mockImplementation((url: string) => {
      if (url.includes("/operations-hub")) {
        return Promise.resolve({ data: buildSixDepartmentHub({ protocolExecutedToday: executedToday }) });
      }
      return Promise.resolve({ data: {} });
    });
    const postSpy = jest.spyOn(api, "post").mockImplementation((url: string) => {
      if (url.includes("/medical/recovery-protocol")) {
        executedToday = true;
        return Promise.resolve({
          data: { status: "executed", outcome: "Executed Hydro & Cryo Conditioning Protocol (800 GTX)." },
        });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      root!.render(
        <QueryClientProvider client={queryClient}>
          <ClubOperationsCentre3D clubId="club-s2" />
        </QueryClientProvider>,
      );
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 40));
    });

    const medTab = container!.querySelector('[data-testid="destination-tab-medical_department"]') as HTMLButtonElement;
    await act(async () => {
      medTab.click();
    });

    const runBtn = container!.querySelector('[data-testid="run-medical-recovery-protocol-btn"]') as HTMLButtonElement;
    expect(runBtn).not.toBeNull();
    expect(runBtn.disabled).toBe(false);

    await act(async () => {
      runBtn.click();
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 60));
    });

    expect(postSpy).toHaveBeenCalledWith("/owner/clubs/club-s2/medical/recovery-protocol", { cost_gtex: 800 });
    const updatedBtn = container!.querySelector('[data-testid="run-medical-recovery-protocol-btn"]') as HTMLButtonElement;
    expect(updatedBtn.disabled).toBe(true);
    expect(updatedBtn.textContent).toContain("Protocol Active Today");
  });

  test("GM Office shows staffing roster & empty campus card; Executive chronometer opens timeline drawer", async () => {
    const hub = buildSixDepartmentHub();
    jest.spyOn(api, "get").mockImplementation((url: string) => {
      if (url.includes("/operations-hub")) return Promise.resolve({ data: hub });
      if (url.includes("/living-world/timeline")) {
        return Promise.resolve({
          data: { events: [], total_count: 0, total_events_count: 0, limit: 8, offset: 0, has_more: false },
        });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      root!.render(
        <QueryClientProvider client={queryClient}>
          <ClubOperationsCentre3D clubId="club-s2" />
        </QueryClientProvider>,
      );
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 40));
    });

    // Executive station `world_chronometer` opens & focuses timeline drawer, Escape closes it
    const timelineBtn = container!.querySelector('[data-testid="room-hotspot-world_chronometer"]') as HTMLButtonElement;
    await act(async () => {
      timelineBtn.click();
    });
    const drawer = container!.querySelector('[data-testid="living-world-timeline-drawer"]') as HTMLElement;
    expect(drawer).not.toBeNull();
    expect(document.activeElement).toBe(drawer);
    await act(async () => {
      drawer.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    });
    expect(container!.querySelector('[data-testid="living-world-timeline-drawer"]')).toBeNull();

    // GM Office displays Staffing Roster, Admin Directive trigger, and Campus Projects even at 0 active builds
    const gmTab = container!.querySelector('[data-testid="destination-tab-general_managers_office"]') as HTMLButtonElement;
    await act(async () => {
      gmTab.click();
    });
    expect(container!.querySelector('[data-testid="gm-staffing-overview"]')).not.toBeNull();
    expect(container!.querySelector('[data-testid="dismiss-staff-general_manager"]')).not.toBeNull();
    expect(container!.querySelector('[data-testid="appoint-staff-chief_scout"]')).not.toBeNull();
    expect(container!.querySelector('[data-testid="campus-construction-projects"]')).not.toBeNull();
    expect(container!.querySelector('[data-testid="gm-open-directive-btn"]')).not.toBeNull();
  });

  test("interior 3D buildDepartmentInterior exposes all pickable station props", () => {
    const built = buildDepartmentInterior({
      destination_key: "managers_office",
      label: "Manager's Office",
      subtitle: "Tactics",
      accent_color: "#38bdf8",
      hotspots: [
        { id: "tactical_pitch_table", label: "Tactical Table", action: "set_mentality", offset: [0, 1.2, 0.5] },
      ],
    } as any);
    expect(built.pickables).toHaveLength(3);
    expect(built.pickables[0].userData.hotspotId).toBe("tactical_pitch_table");
    expect(built.pickables[0].userData.hotspotAction).toBe("set_mentality");
  });
});
