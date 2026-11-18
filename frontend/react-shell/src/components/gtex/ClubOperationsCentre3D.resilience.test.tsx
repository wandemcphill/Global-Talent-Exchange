(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as THREE from "three";
import { ClubOperationsCentre3D } from "./ClubOperationsCentre3D";
import { api, tokens } from "@/lib/api";
import { useRealtimeTopics } from "@/lib/realtime";
import type { ClubOperationsHubPayload, OperationsHubDestination } from "@/lib/ownerBriefing";

let mockLastDomElement: HTMLCanvasElement | null = null;
let mockFailDestinationKey: string | null = null;
let mockGlbLoadCalls: string[] = [];
let mockFailAlways = false;
let mockRendererRenderCalls = 0;

jest.mock("three", () => {
  const actualThree = jest.requireActual("three");
  class MockWebGLRenderer {
    domElement: HTMLCanvasElement;
    shadowMap: { enabled: boolean; type: unknown };
    toneMapping: unknown;
    toneMappingExposure: number;
    setSize = jest.fn();
    setPixelRatio = jest.fn();
    render = jest.fn(() => {
      mockRendererRenderCalls += 1;
    });
    dispose = jest.fn();

    constructor() {
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
      mockLastDomElement = this.domElement;
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
    load(
      url: string,
      onLoad: (gltf: { scene: THREE.Group }) => void,
      _onProgress?: unknown,
      onError?: (err: Error) => void,
    ) {
      mockGlbLoadCalls.push(url);
      if (mockFailDestinationKey && url.includes(mockFailDestinationKey)) {
        if (!mockFailAlways) {
          // Fail once on initial attempt so retry succeeds unless mockFailAlways is true
          mockFailDestinationKey = null;
        }
        onError?.(new Error("Simulated GLB network 503"));
        return;
      }
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
  API: "http://127.0.0.1:8000/api",
  tokens: {
    get: jest.fn(() => "secret-jwt-token-do-not-leak"),
  },
  api: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
  },
  errMsg: (error: unknown) =>
    error instanceof Error ? error.message : "Request failed",
}));

function buildFixture(): ClubOperationsHubPayload {
  const makeStaff = (roleKey: string, name: string, roleLabel: string) => ({
    role_key: roleKey,
    name,
    role_label: roleLabel,
    mood: 80,
    loyalty: 75,
    is_vacant: false,
    is_appointed: true,
  });

  const defs: Array<[OperationsHubDestination["destination_key"], string, string]> = [
    ["executive_office", "Executive Office", "/models/campus/club_hq.glb"],
    ["managers_office", "Manager's Office", "/models/campus/stadium_main.glb"],
    ["general_managers_office", "GM Office", "/models/campus/vip_skybox_concourse.glb"],
    ["academy_department", "Academy", "/models/campus/elite_academy_complex.glb"],
    ["medical_department", "Medical", "/models/campus/recovery_hydro_hub.glb"],
    ["finance_commercial_office", "Finance", "/models/campus/vip_hospitality.glb"],
  ];

  const destinations: OperationsHubDestination[] = defs.map(([key, label, glb], i) => ({
    destination_key: key,
    label,
    short_label: label,
    subtitle: label,
    lead_role_key: key,
    communication_channel_mode: key === "executive_office" ? "office_wide" : "direct",
    staff_lead: makeStaff(key, `${label} Lead`, label),
    glb_model: glb,
    exterior_glb: glb,
    accent_color: "#38bdf8",
    position_3d: [i * 10, 0, 0],
    camera_position: [i * 10, 10, 12],
    camera_target: [i * 10, 1.5, 0],
    hotspots: [{ id: `${key}_station`, label: `${label} Desk`, action: "inspect_briefing", offset: [0, 1.4, 2] }],
    report_section_key: "executive_briefing",
    report: {},
    open_decisions: [],
    open_decisions_count: 0,
    recent_messages: [],
  }));

  return {
    club: {
      club_id: "club-stage5",
      club_name: "Resilient FC",
      owner_name: "Owner",
      world_day: 12,
      prestige: 65,
      prestige_tier: "Contender",
      fans: 15000,
      mentality: "balanced",
      cash_gtex: 110000,
      fan_coin: 500,
      club_valuation_gtex: 900000,
    },
    daily_briefing: { world_day: 12, headline: "Systems Nominal" },
    destinations,
    actionable_decisions: { department_decisions: [], inbox_decisions: [], total_open_count: 0 },
    operational_timeline: [],
    decision_history: [],
    recent_communications: [],
    staff: {},
    staff_catalog: [],
  };
}

describe("ClubOperationsCentre3D Stage 5 - Resilience, GLB Retry, Telemetry & WS Diagnostics", () => {
  const originalGetContext = HTMLCanvasElement.prototype.getContext;
  const originalRaf = window.requestAnimationFrame;
  const originalCancelRaf = window.cancelAnimationFrame;
  const originalWebSocket = globalThis.WebSocket;

  let activeRoot: Root | null = null;
  let activeContainer: HTMLDivElement | null = null;

  beforeEach(() => {
    jest.clearAllMocks();
    mockLastDomElement = null;
    mockFailDestinationKey = null;
    mockFailAlways = false;
    mockGlbLoadCalls = [];
    mockRendererRenderCalls = 0;
    (tokens.get as jest.Mock).mockReturnValue("secret-jwt-token-do-not-leak");
    (api.get as jest.Mock).mockImplementation(() => Promise.resolve({ data: buildFixture() }));

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

    let frameTick = performance.now();
    window.requestAnimationFrame = ((cb: FrameRequestCallback) =>
      window.setTimeout(() => {
        frameTick = Math.max(frameTick + 40, performance.now() + 40);
        cb(frameTick);
      }, 4)) as typeof window.requestAnimationFrame;
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
    globalThis.WebSocket = originalWebSocket;
  });

  async function renderCentre(): Promise<HTMLDivElement> {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    activeContainer = document.createElement("div");
    document.body.appendChild(activeContainer);
    activeRoot = createRoot(activeContainer);

    await act(async () => {
      activeRoot?.render(
        <QueryClientProvider client={queryClient}>
          <ClubOperationsCentre3D clubId="club-stage5" />
        </QueryClientProvider>,
      );
    });
    for (let step = 0; step < 8; step += 1) {
      await act(async () => {
        await Promise.resolve();
        await new Promise((r) => setTimeout(r, 30));
      });
      if (
        activeContainer.querySelector('[data-testid="webgl-perf-telemetry"]') &&
        (activeContainer.querySelector('[data-testid="glb-asset-status"]')?.textContent || "").includes("6/6 departments")
      ) {
        break;
      }
    }
    return activeContainer;
  }

  test("WebGL context loss pauses renders cleanly, restores gracefully, auto-falls back on repeat loss, and removes listeners", async () => {
    const container = await renderCentre();
    expect(mockLastDomElement).not.toBeNull();
    const removeListenerSpy = jest.spyOn(mockLastDomElement!, "removeEventListener");

    // Performance telemetry warmup should populate FPS HUD pill
    const telemetryBadge = container.querySelector('[data-testid="webgl-perf-telemetry"]');
    expect(telemetryBadge?.textContent).toContain("FPS");

    const ops3d = (window as unknown as {
      __GTEX_OPERATIONS_3D__?: {
        getTelemetry?: () => {
          loadedGlbs: number;
          proceduralRooms: number;
          departmentRoomsReady: number;
          failedGlbs: number;
          contextLossCount: number;
        };
      };
    }).__GTEX_OPERATIONS_3D__;
    const telemetry = ops3d?.getTelemetry?.();
    expect(telemetry?.loadedGlbs).toBe(3);
    expect(telemetry?.proceduralRooms).toBe(3);
    expect(telemetry?.departmentRoomsReady).toBe(6);
    expect(telemetry?.failedGlbs).toBe(0);

    // 1st context loss -> shows context lost status + banner + pauses render calls
    const lostEvent1 = new Event("webglcontextlost", { cancelable: true });
    await act(async () => {
      mockLastDomElement?.dispatchEvent(lostEvent1);
    });
    expect(lostEvent1.defaultPrevented).toBe(true);
    expect(container.querySelector('[data-testid="glb-asset-status"]')?.textContent).toContain("WebGL Context Lost");
    expect(container.querySelector('[data-testid="webgl-context-lost-banner"]')).not.toBeNull();

    const renderCountWhileLost = mockRendererRenderCalls;
    await act(async () => {
      await new Promise((r) => setTimeout(r, 35));
    });
    expect(mockRendererRenderCalls).toBe(renderCountWhileLost);

    // Context restored -> returns to WebGL Active and clears banner
    await act(async () => {
      mockLastDomElement?.dispatchEvent(new Event("webglcontextrestored"));
    });
    expect(container.querySelector('[data-testid="glb-asset-status"]')?.textContent).toContain("WebGL Active");
    expect(container.querySelector('[data-testid="webgl-context-lost-banner"]')).toBeNull();

    // 2nd context loss -> automatically falls back to 2D Blueprint
    await act(async () => {
      mockLastDomElement?.dispatchEvent(new Event("webglcontextlost", { cancelable: true }));
    });
    await act(async () => {
      await Promise.resolve();
    });
    expect(container.querySelector('[data-testid="club-operations-2d-floorplan"]')).not.toBeNull();
    expect(removeListenerSpy).toHaveBeenCalledWith("webglcontextlost", expect.any(Function));
    expect(removeListenerSpy).toHaveBeenCalledWith("webglcontextrestored", expect.any(Function));
  });

  test("bounded GLB retry recovers transient failures and stops after max 2 retries on permanent errors", async () => {
    mockFailDestinationKey = "club_hq.glb";
    mockFailAlways = false;

    const container = await renderCentre();
    expect(container.querySelector('[data-testid="glb-asset-status"]')?.textContent).toContain("2/3 GLB loaded");
    const retryBtn = container.querySelector('[data-testid="retry-failed-glb-btn"]') as HTMLButtonElement | null;
    expect(retryBtn).not.toBeNull();
    expect(retryBtn?.textContent).toContain("Retry Failed Assets (0/2)");

    // Clicking retry reloads ONLY the failed GLB and clears the warning cleanly
    const callsBeforeRetry = mockGlbLoadCalls.length;
    await act(async () => {
      retryBtn?.click();
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 25));
    });
    expect(mockGlbLoadCalls.length).toBe(callsBeforeRetry + 1);
    expect(container.querySelector('[data-testid="glb-asset-status"]')?.textContent).toContain("3/3 GLB loaded");
    expect(container.querySelector('[data-testid="glb-asset-warning"]')).toBeNull();

    // Now test bounded cap when failures persist across max retries
    await act(async () => {
      activeRoot?.unmount();
    });
    activeRoot = null;
    activeContainer?.remove();
    activeContainer = null;

    mockFailDestinationKey = "recovery_hydro_hub.glb";
    mockFailAlways = true;
    const container2 = await renderCentre();
    for (let i = 0; i < 2; i += 1) {
      const btn = container2.querySelector('[data-testid="retry-failed-glb-btn"]') as HTMLButtonElement | null;
      expect(btn?.disabled).toBe(false);
      await act(async () => {
        btn?.click();
      });
    }
    const exhaustedBtn = container2.querySelector('[data-testid="retry-failed-glb-btn"]') as HTMLButtonElement | null;
    expect(exhaustedBtn?.disabled).toBe(true);
    expect(exhaustedBtn?.textContent).toContain("Retry Limit Reached (2/2)");
  });

  test("useRealtimeTopics diagnoses WebSocket auth rejection without infinite reconnect loops or token leakage", async () => {
    const constructedSockets: Array<{
      url: string;
      onopen: (() => void) | null;
      onclose: ((ev: { code?: number; reason?: string }) => void) | null;
      onerror: (() => void) | null;
      close: jest.Mock;
    }> = [];

    globalThis.WebSocket = jest.fn((url: string) => {
      const sock = {
        url,
        onopen: null as (() => void) | null,
        onclose: null as ((ev: { code?: number; reason?: string }) => void) | null,
        onerror: null as (() => void) | null,
        close: jest.fn(),
      };
      constructedSockets.push(sock);
      return sock as unknown as WebSocket;
    }) as unknown as typeof WebSocket;

    let latestState: ReturnType<typeof useRealtimeTopics> | null = null;
    function Probe() {
      latestState = useRealtimeTopics(["club:telemetry"], () => undefined, undefined, true);
      return <div data-testid="ws-state">{latestState.connectionState}</div>;
    }

    activeContainer = document.createElement("div");
    document.body.appendChild(activeContainer);
    activeRoot = createRoot(activeContainer);

    await act(async () => {
      activeRoot?.render(<Probe />);
    });

    expect(constructedSockets).toHaveLength(1);
    await act(async () => {
      constructedSockets[0].onclose?.({ code: 4401, reason: "Unauthorized session" });
    });

    expect(latestState?.connectionState).toBe("auth_error");
    expect(latestState?.lastCloseCode).toBe(4401);
    expect(latestState?.lastError).toContain("authentication rejected");
    expect(latestState?.lastError).not.toContain("secret-jwt-token");
    expect(tokens.get).toHaveBeenCalled();

    // Ensure no runaway reconnect loop was scheduled after auth failure
    await act(async () => {
      await new Promise((r) => setTimeout(r, 900));
    });
    expect(constructedSockets).toHaveLength(1);
  });
});
