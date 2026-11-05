import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ClubOperationsCentre3D } from "./ClubOperationsCentre3D";
import type { DailyBriefing, LivingWorldTimelineResponse } from "@/lib/ownerBriefing";

var mockToastSuccess = jest.fn();
var mockToastError = jest.fn();

jest.mock("react-router-dom", () => {
  const ReactModule = require("react");
  return {
    Link: ({ to, children, ...props }: any) =>
      ReactModule.createElement(
        "a",
        {
          href: typeof to === "string" ? to : "#",
          ...props,
        },
        children,
      ),
  };
});

jest.mock("sonner", () => ({
  toast: {
    success: (...args: any[]) => mockToastSuccess(...args),
    error: (...args: any[]) => mockToastError(...args),
  },
}));

// Mock Three.js to avoid WebGL context issues in jsdom
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
    distanceTo() {
      return 0;
    }
    lerp() {
      return this;
    }
    add() {
      return this;
    }
    sub() {
      return this;
    }
  }

  const mockThree = {
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
      setSize = () => {};
      setPixelRatio = () => {};
      render = () => {};
      dispose = () => {};
      get domElement() {
        return (globalThis as any).document ? (globalThis as any).document.createElement("canvas") : {};
      }
      shadowMap = { enabled: false, type: 0 };
    },
    AmbientLight: class {},
    DirectionalLight: class {
      position = new MockVector3();
      castShadow = false;
      shadow = {
        mapSize: { set: () => {} },
        camera: { near: 0, far: 0, left: 0, right: 0, top: 0, bottom: 0 },
      };
    },
    HemisphereLight: class {
      position = new MockVector3();
    },
    PointLight: class {
      position = new MockVector3();
    },
    Group: class {
      position = new MockVector3();
      scale = new MockVector3();
      rotation = { set: () => {}, x: 0, y: 0, z: 0 };
      children: any[] = [];
      userData: any = {};
      add() {}
      traverse() {}
      clone() {
        return new (mockThree as any).Group();
      }
    },
    Mesh: class {
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
      getSize(target: any) {
        if (target?.set) target.set(1, 1, 1);
        return target;
      }
      getCenter(target: any) {
        if (target?.set) target.set(0, 0, 0);
        return target;
      }
    },
    Raycaster: class {
      setFromCamera() {}
      intersectObjects() {
        return [];
      }
    },
    Color: class {},
    DoubleSide: 2,
    PCFSoftShadowMap: 2,
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
    MathUtils: {
      lerp: (a: number, b: number, t: number) => a + (b - a) * t,
    },
  };
  return mockThree;
});

// Mock GLTFLoader and Three.js examples ESM
jest.mock("three/examples/jsm/controls/OrbitControls.js", () => {
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
    lerp() {
      return this;
    }
    distanceTo() {
      return 0;
    }
  }

  return {
    OrbitControls: class {
      enableDamping = true;
      dampingFactor = 0.05;
      maxPolarAngle = 1;
      minDistance = 1;
      maxDistance = 100;
      target = new MockVector3();
      addEventListener = () => {};
      removeEventListener = () => {};
      update = () => {};
      dispose = () => {};
    },
  };
});

jest.mock("three/examples/jsm/loaders/GLTFLoader.js", () => ({
  GLTFLoader: class {
    load(url: string, onLoad: any) {
      const THREE = require("three");
      const model = new THREE.Group();
      onLoad({
        scene: {
          clone: () => model,
        },
      });
    }
  },
}));

jest.mock("three/examples/jsm/environments/RoomEnvironment.js", () => ({
  RoomEnvironment: class {},
}));

const mockBriefing: DailyBriefing = {
  id: "briefing-tl-1",
  club_id: "club-tl-1",
  world_day: 15,
  headline: "Living Club Operations",
  summary: "Testing unified timeline drawer integration",
  metrics: {
    cash_gtex: 500000,
    avg_morale: 75,
    avg_fitness: 88,
    injured_players: 1,
    ready_academy_prospects: 2,
    open_decisions: 1,
  },
  sections: [],
  department_decisions: [],
};

const mockDestination: any = {
  destination_key: "executive_office",
  label: "Executive Boardroom",
  short_label: "Executive",
  subtitle: "Executive Suite",
  lead_role_key: "general_manager",
  room_title: "Executive Boardroom",
  department: "executive",
  staff_lead: {
    role: "general_manager",
    title: "General Manager",
    name: "Babatunde Lawal",
    status: "appointed",
    mood: 85,
  },
  glb_model: "/models/campus/club_hq.glb",
  exterior_glb: "/models/campus/club_hq.glb",
  accent_color: "#38bdf8",
  position_3d: [0, 0, 0],
  camera_position: [0, 5, 10],
  camera_target: [0, 0, 0],
  hotspots: [{ id: "hs-1", label: "Executive Desk", action: "inspect", offset: [0, 1, 0] }],
  report_section_key: "executive_summary",
  report: {
    headline: "Operations Stable",
    status: "green",
    metrics: {},
    summary: "All operations on track",
  },
  open_decisions: [],
  open_decisions_count: 0,
  recent_messages: [],
  active_events: [],
  active_events_count: 0,
  active_directives: [],
  active_directives_count: 0,
  relationship: null,
};

const mockHub: any = {
  club_id: "club-tl-1",
  club_name: "Lagos Marine FC",
  club: {
    club_name: "Lagos Marine FC",
  },
  world_day: 15,
  generated_at: "2026-11-05T12:00:00Z",
  destinations: [mockDestination],
  staff_roster: [],
  living_world: {
    active_events_count: 2,
    active_directives_count: 1,
    relationships: [],
  },
};

const mockTimelineResponse: LivingWorldTimelineResponse = {
  club_id: "club-tl-1",
  world_day: 15,
  total_count: 4,
  total_events_count: 4,
  limit: 20,
  offset: 0,
  filters: {
    category: null,
    severity: null,
    status: null,
  },
  items: [
    {
      id: "ev-hist-1",
      kind: "event",
      category: "squad",
      event_type: "squad_morale_dip",
      severity: "routine",
      title: "Historical Morale Dip Resolved",
      description: "Player morale was resolved via chairman pep talk",
      world_day: 12,
      status: "resolved",
      resolution_action: "encourage_player",
      resolved_at: "2026-11-05T10:00:00Z",
      participants: [{ role: "player", name: "Segun Adele" }],
      actions: [],
    },
    {
      id: "dir-active-1",
      kind: "directive",
      category: "medical",
      event_type: "departmental_directive",
      severity: "important",
      title: "Hydrotherapy Recovery Directive",
      description: "Accelerate recovery for injured midfielder",
      world_day: 14,
      status: "active",
      deadline_day: 17,
      acknowledged_by: "Dr. Chidi Obi",
      acknowledgement_text: "Hydrotherapy protocols in full effect",
      actions: [],
    },
    {
      id: "rel-culture-1",
      kind: "relationship_shift",
      category: "culture",
      event_type: "relationship_shift",
      severity: "routine",
      title: "Cultural Trust Shift: First-Team Manager",
      description: "Milestone tactical alignment meeting (+10 Trust)",
      world_day: 13,
      status: "resolved",
      delta_trust: 10,
      delta_respect: 5,
      delta_tension: -4,
      reason: "Milestone tactical alignment meeting",
      participants: [
        { role: "owner", name: "Club Owner" },
        { role: "first_team_manager", name: "Marcus Cole" },
      ],
      actions: [],
    },
    {
      id: "ev-actionable-1",
      kind: "event",
      category: "tactical",
      event_type: "tactical_readiness_briefing",
      severity: "important",
      title: "Pre-Match Tactical Setup",
      description: "Manager awaits board endorsement on high-press transition",
      world_day: 15,
      status: "active",
      actions: [
        { key: "endorse_tactics", label: "Endorse High Press", style: "primary" },
      ],
    },
  ],
};

describe("ClubOperationsCentre3D Living World Timeline Integration", () => {
  let container: HTMLDivElement | null = null;
  let root: Root | null = null;
  let queryClient: QueryClient;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    HTMLCanvasElement.prototype.getContext = jest.fn().mockImplementation((type: string) => {
      if (type === "webgl" || type === "webgl2" || type === "experimental-webgl") {
        return {
          getExtension: () => null,
          getParameter: () => 0,
        };
      }
      return null;
    });
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });
    jest.clearAllMocks();
  });

  afterEach(() => {
    if (root && container) {
      act(() => {
        root!.unmount();
      });
      container.remove();
    }
    container = null;
    root = null;
  });

  test("renders unified timeline with historical events, directives, and relationship shifts", async () => {
    jest.spyOn(api, "get").mockImplementation((url: string) => {
      if (url.includes("/operations-hub")) {
        return Promise.resolve({ data: mockHub });
      }
      if (url.includes("/living-world/timeline")) {
        return Promise.resolve({ data: mockTimelineResponse });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      root!.render(
        <QueryClientProvider client={queryClient}>
          <ClubOperationsCentre3D clubId="club-tl-1" />
        </QueryClientProvider>,
      );
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    // Open timeline drawer
    const toggleBtn = container?.querySelector('[data-testid="toggle-living-world-timeline"]') as HTMLButtonElement;
    expect(toggleBtn).not.toBeNull();
    await act(async () => {
      toggleBtn.click();
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 60));
    });

    // Drawer is rendered
    const drawer = container?.querySelector('[data-testid="living-world-timeline-drawer"]');
    expect(drawer).not.toBeNull();

    // Verify historical/resolved event appears
    expect(container?.textContent).toContain("Historical Morale Dip Resolved");

    // Verify departmental directive appears
    expect(container?.textContent).toContain("Hydrotherapy Recovery Directive");
    expect(container?.textContent).toContain("Dr. Chidi Obi");

    // Verify cultural relationship shift appears
    expect(container?.textContent).toContain("Cultural Trust Shift: First-Team Manager");
    expect(container?.textContent).toContain("Milestone tactical alignment meeting");
  });

  test("supports culture category filter and triggers API with query param", async () => {
    let capturedParams: any = null;
    jest.spyOn(api, "get").mockImplementation((url: string, config?: any) => {
      if (url.includes("/operations-hub")) {
        return Promise.resolve({ data: mockHub });
      }
      if (url.includes("/living-world/timeline")) {
        capturedParams = config?.params;
        return Promise.resolve({ data: mockTimelineResponse });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      root!.render(
        <QueryClientProvider client={queryClient}>
          <ClubOperationsCentre3D clubId="club-tl-1" />
        </QueryClientProvider>,
      );
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    // Open timeline drawer
    const toggleBtn = container?.querySelector('[data-testid="toggle-living-world-timeline"]') as HTMLButtonElement;
    expect(toggleBtn).not.toBeNull();
    await act(async () => {
      toggleBtn.click();
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 60));
    });

    // Click 'culture' filter button
    const cultureBtn = container?.querySelector('[data-testid="timeline-filter-category-culture"]') as HTMLButtonElement;
    expect(cultureBtn).not.toBeNull();
    await act(async () => {
      cultureBtn.click();
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 60));
    });

    expect(capturedParams?.category).toBe("culture");
  });

  test("supports severity and status filters via query params", async () => {
    let capturedParams: any = null;
    jest.spyOn(api, "get").mockImplementation((url: string, config?: any) => {
      if (url.includes("/operations-hub")) {
        return Promise.resolve({ data: mockHub });
      }
      if (url.includes("/living-world/timeline")) {
        capturedParams = config?.params;
        return Promise.resolve({ data: mockTimelineResponse });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      root!.render(
        <QueryClientProvider client={queryClient}>
          <ClubOperationsCentre3D clubId="club-tl-1" />
        </QueryClientProvider>,
      );
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    const toggleBtn = container?.querySelector('[data-testid="toggle-living-world-timeline"]') as HTMLButtonElement;
    expect(toggleBtn).not.toBeNull();
    await act(async () => {
      toggleBtn.click();
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 60));
    });

    const importantBtn = container?.querySelector('[data-testid="timeline-filter-severity-important"]') as HTMLButtonElement;
    expect(importantBtn).not.toBeNull();
    await act(async () => {
      importantBtn.click();
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 60));
    });
    expect(capturedParams?.severity).toBe("important");

    const resolvedStatusBtn = container?.querySelector('[data-testid="timeline-filter-status-resolved"]') as HTMLButtonElement;
    expect(resolvedStatusBtn).not.toBeNull();
    await act(async () => {
      resolvedStatusBtn.click();
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 60));
    });
    expect(capturedParams?.status).toBe("resolved");
  });

  test("supports pagination controls with limit and offset", async () => {
    let capturedParams: any = null;
    const pagedResponse: LivingWorldTimelineResponse = {
      ...mockTimelineResponse,
      total_count: 50,
      total_events_count: 50,
      limit: 8,
      offset: 0,
    };
    jest.spyOn(api, "get").mockImplementation((url: string, config?: any) => {
      if (url.includes("/operations-hub")) {
        return Promise.resolve({ data: mockHub });
      }
      if (url.includes("/living-world/timeline")) {
        capturedParams = config?.params;
        return Promise.resolve({ data: pagedResponse });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      root!.render(
        <QueryClientProvider client={queryClient}>
          <ClubOperationsCentre3D clubId="club-tl-1" />
        </QueryClientProvider>,
      );
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    const toggleBtn = container?.querySelector('[data-testid="toggle-living-world-timeline"]') as HTMLButtonElement;
    expect(toggleBtn).not.toBeNull();
    await act(async () => {
      toggleBtn.click();
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 60));
    });

    const nextBtn = container?.querySelector('[data-testid="timeline-next-page"]') as HTMLButtonElement;
    expect(nextBtn).not.toBeNull();
    expect(nextBtn.disabled).toBe(false);

    await act(async () => {
      nextBtn.click();
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 60));
    });
    expect(capturedParams?.offset).toBe(8);
  });

  test("renders empty and error states with retry support", async () => {
    let shouldFail = true;
    jest.spyOn(api, "get").mockImplementation((url: string) => {
      if (url.includes("/operations-hub")) {
        return Promise.resolve({ data: mockHub });
      }
      if (url.includes("/living-world/timeline")) {
        if (shouldFail) {
          return Promise.reject(new Error("Network Error"));
        }
        return Promise.resolve({
          data: {
            club_id: "club-tl-1",
            world_day: 15,
            total_count: 0,
            total_events_count: 0,
            limit: 8,
            offset: 0,
            items: [],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      root!.render(
        <QueryClientProvider client={queryClient}>
          <ClubOperationsCentre3D clubId="club-tl-1" />
        </QueryClientProvider>,
      );
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    const toggleBtn = container?.querySelector('[data-testid="toggle-living-world-timeline"]') as HTMLButtonElement;
    expect(toggleBtn).not.toBeNull();
    await act(async () => {
      toggleBtn.click();
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 60));
    });

    // Error state is displayed
    const errorContainer = container?.querySelector('[data-testid="living-timeline-error"]');
    expect(errorContainer).not.toBeNull();
    expect(container?.textContent).toContain("Unable to load Living Club World timeline");

    // Click retry
    shouldFail = false;
    const retryBtn = container?.querySelector('[data-testid="living-timeline-retry"]') as HTMLButtonElement;
    expect(retryBtn).not.toBeNull();
    await act(async () => {
      retryBtn.click();
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 60));
    });

    // Empty state is displayed
    const emptyContainer = container?.querySelector('[data-testid="living-timeline-empty"]');
    expect(emptyContainer).not.toBeNull();
    expect(container?.textContent).toContain("No timeline entries match the active filters");
  });

  test("authoritative event action resolution button resolves event via POST endpoint", async () => {
    let resolvedUrl = "";
    let resolvedBody: any = null;

    jest.spyOn(api, "get").mockImplementation((url: string) => {
      if (url.includes("/operations-hub")) {
        return Promise.resolve({ data: mockHub });
      }
      if (url.includes("/living-world/timeline")) {
        return Promise.resolve({ data: mockTimelineResponse });
      }
      return Promise.resolve({ data: {} });
    });

    jest.spyOn(api, "post").mockImplementation((url: string, body: any) => {
      resolvedUrl = url;
      resolvedBody = body;
      return Promise.resolve({
        data: {
          event_id: "ev-actionable-1",
          status: "resolved",
          resolution_action: "endorse_tactics",
        },
      });
    });

    await act(async () => {
      root!.render(
        <QueryClientProvider client={queryClient}>
          <ClubOperationsCentre3D clubId="club-tl-1" />
        </QueryClientProvider>,
      );
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    const toggleBtn = container?.querySelector('[data-testid="toggle-living-world-timeline"]') as HTMLButtonElement;
    expect(toggleBtn).not.toBeNull();
    await act(async () => {
      toggleBtn.click();
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 60));
    });

    // Action button on actionable active event
    const actionBtn = container?.querySelector(
      '[data-testid="timeline-event-action-ev-actionable-1-endorse_tactics"]',
    ) as HTMLButtonElement;
    expect(actionBtn).not.toBeNull();
    expect(actionBtn.textContent).toContain("Endorse High Press");

    // Historical/resolved event must NOT have action buttons
    const resolvedActionBtn = container?.querySelector(
      '[data-testid^="timeline-event-action-ev-hist-1"]',
    );
    expect(resolvedActionBtn).toBeNull();

    // Click action button
    await act(async () => {
      actionBtn.click();
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 60));
    });

    expect(resolvedUrl).toBe("/owner/clubs/club-tl-1/living-world/events/ev-actionable-1/resolve");
    expect(resolvedBody).toEqual({ action: "endorse_tactics" });
  });
});
