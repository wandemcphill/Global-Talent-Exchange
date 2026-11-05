import React, { useEffect, useRef, useState, useMemo, useCallback } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader";
import {
  RotateCw,
  ZoomIn,
  ZoomOut,
  Compass,
  Grid,
  Layers,
  Trash2,
  Move,
  MousePointer,
  Sun,
  Moon,
  Undo2,
  Redo2,
  Hammer,
  Box,
  Eye,
  RotateCcw,
  Check,
  X,
  Cpu,
} from "lucide-react";
import { publicAssetPath } from "@/lib/publicPath";

export interface CampusZone {
  zone_id: string;
  name: string;
  x: number;
  y: number;
  w: number;
  h: number;
  color: string;
  description: string;
}

export interface CampusModuleInstance {
  instance_id: string;
  module_key: string;
  name?: string;
  category?: string;
  x: number;
  y: number;
  rotation: number;
  footprint_w?: number;
  footprint_h?: number;
  effective_w?: number;
  effective_h?: number;
  level: number;
  condition?: number;
  status: "operational" | "under_construction";
  construction_stage?:
    | "site_prep"
    | "groundworks"
    | "foundations"
    | "structural"
    | "finishing"
    | "completed";
  progress_pct?: number;
  color_hex?: string;
  height_scale?: number;
  roof_style?: string;
  image_url?: string;
  model_glb_url?: string;
  description?: string;
  effects?: Record<string, number>;
  can_demolish?: boolean;
  upgrade_cost_gtex?: number;
  next_upgrade_cost_gtex?: number;
  base_cost_gtex?: number;
  build_days?: number;
  min_prestige?: number;
  max_level?: number;
  upgrade_min_prestige?: number;
  current_effects?: Record<string, number>;
  next_level_effects?: Record<string, number>;
  lifecycle_state?:
    | "under_construction"
    | "ready_for_completion"
    | "eligible_for_upgrade"
    | "completed_max_level";
  ready_for_completion?: boolean;
  upgrade_eligible?: boolean;
  start_world_day?: number;
  duration_days?: number;
  expected_completion_day?: number;
  remaining_days?: number;
  active_project_id?: string;
}

export interface CampusCatalogItem {
  module_key: string;
  name: string;
  category: string;
  linked_facility: string;
  footprint_w: number;
  footprint_h: number;
  base_cost_gtex: number;
  build_days: number;
  min_prestige: number;
  can_demolish: boolean;
  image_url: string;
  model_glb_url?: string;
  color_hex: string;
  height_scale: number;
  roof_style: string;
  description: string;
  effects: Record<string, number>;
  placed_count?: number;
  operational_count?: number;
  under_construction_count?: number;
  availability_status?: "available" | "prestige_locked" | "insufficient_treasury";
}

interface CampusBuilder3DProps {
  gridWidth: number;
  gridHeight: number;
  zones: CampusZone[];
  placedModules: CampusModuleInstance[];
  moduleCatalog: CampusCatalogItem[];
  selectedInstanceId: string | null;
  onSelectInstance: (instanceId: string | null) => void;
  selectedEmptyPlot?: { x: number; y: number } | null;
  onSelectEmptyPlot?: (plot: { x: number; y: number } | null) => void;
  activeBuildModuleKey: string | null;
  onClearBuildMode: () => void;
  onPlaceNewModule: (moduleKey: string, x: number, y: number, rotation: number) => void;
  onMoveModule: (instanceId: string, x: number, y: number, rotation: number) => void;
  onDemolishModule: (instanceId: string) => void;
  busy?: boolean;
}

interface HistorySnapshot {
  instanceId: string;
  x: number;
  y: number;
  rotation: number;
}

type CameraPreset =
  | "isometric"
  | "top_down"
  | "stadium_aerial"
  | "academy_precinct"
  | "ground_level";
type RendererMode = "webgl_3d" | "canvas_fallback";
type QualityTier = "high" | "balanced" | "low";

// ---------------------------------------------------------------------------
// Shared Module-Level Three.js GLTF Cache & Lazy Loader (Zero Redundant Fetches)
// ---------------------------------------------------------------------------
interface CachedGlbEntry {
  scene: THREE.Group;
  vertexCount: number;
  triangleCount: number;
  materialCount: number;
}

const gltfTemplateCache = new Map<string, CachedGlbEntry>();
const gltfPendingPromises = new Map<string, Promise<CachedGlbEntry | null>>();
const sharedGltfLoader = new GLTFLoader();

function countThreeGroupStats(root: THREE.Object3D): {
  vertexCount: number;
  triangleCount: number;
  materialCount: number;
} {
  let vertexCount = 0;
  let triangleCount = 0;
  const materials = new Set<string>();
  root.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (mesh.isMesh && mesh.geometry) {
      const pos = mesh.geometry.getAttribute("position");
      if (pos) vertexCount += pos.count;
      const idx = mesh.geometry.getIndex();
      if (idx) triangleCount += Math.floor(idx.count / 3);
      else if (pos) triangleCount += Math.floor(pos.count / 3);
      if (Array.isArray(mesh.material)) {
        mesh.material.forEach((m) => materials.add(m.uuid));
      } else if (mesh.material) {
        materials.add(mesh.material.uuid);
      }
    }
  });
  return { vertexCount, triangleCount, materialCount: materials.size };
}

function normalizeUrl(rawUrl: string): string {
  const clean = rawUrl.replace(/^\/console\//, "/");
  return publicAssetPath(clean);
}

function loadGlbTemplateLazy(rawUrl: string): Promise<CachedGlbEntry | null> {
  const url = normalizeUrl(rawUrl);
  if (gltfTemplateCache.has(url)) {
    return Promise.resolve(gltfTemplateCache.get(url)!);
  }
  if (gltfPendingPromises.has(url)) {
    return gltfPendingPromises.get(url)!;
  }
  const promise = new Promise<CachedGlbEntry | null>((resolve) => {
    sharedGltfLoader.load(
      url,
      (gltf) => {
        const root = gltf.scene || new THREE.Group();
        root.traverse((child) => {
          const mesh = child as THREE.Mesh;
          if (mesh.isMesh) {
            mesh.castShadow = true;
            mesh.receiveShadow = true;
            mesh.frustumCulled = true;
          }
        });
        const stats = countThreeGroupStats(root);
        const entry: CachedGlbEntry = {
          scene: root,
          vertexCount: stats.vertexCount,
          triangleCount: stats.triangleCount,
          materialCount: stats.materialCount,
        };
        gltfTemplateCache.set(url, entry);
        gltfPendingPromises.delete(url);
        resolve(entry);
      },
      undefined,
      () => {
        gltfPendingPromises.delete(url);
        resolve(null);
      }
    );
  });
  gltfPendingPromises.set(url, promise);
  return promise;
}

function resolveStageGlbUrl(stage?: string, progressPct = 100, fallbackUrl?: string): string {
  if (!stage || stage === "completed" || progressPct >= 100) {
    return fallbackUrl || "/models/campus/high_performance_centre.glb";
  }
  if (stage === "site_prep" || progressPct < 20) return "/models/campus/stage_1_site_prep.glb";
  if (stage === "groundworks" || progressPct < 40) return "/models/campus/stage_2_groundworks.glb";
  if (stage === "foundations" || progressPct < 60) return "/models/campus/stage_3_foundations.glb";
  if (stage === "structural" || progressPct < 80) return "/models/campus/stage_4_structural.glb";
  return "/models/campus/stage_5_finishing.glb";
}

function detectInitialQualityTier(): QualityTier {
  if (typeof navigator !== "undefined") {
    const cores = navigator.hardwareConcurrency || 4;
    if (cores <= 2) return "low";
    if (cores <= 4) return "balanced";
  }
  return "high";
}

export const CampusBuilder3D: React.FC<CampusBuilder3DProps> = ({
  gridWidth = 24,
  gridHeight = 18,
  zones,
  placedModules,
  moduleCatalog,
  selectedInstanceId,
  onSelectInstance,
  selectedEmptyPlot: externalEmptyPlot,
  onSelectEmptyPlot,
  activeBuildModuleKey,
  onClearBuildMode,
  onPlaceNewModule,
  onMoveModule,
  onDemolishModule,
  busy = false,
}) => {
  // Primary renderer is Three.js WebGL; Canvas 2D Isometric preserved as fallback/inspector
  const [rendererMode, setRendererMode] = useState<RendererMode>("webgl_3d");
  const [webglStatus, setWebglStatus] = useState<"active" | "context_lost" | "fallback">("active");
  const [qualityTier, setQualityTier] = useState<QualityTier>(detectInitialQualityTier);
  const [cameraPreset, setCameraPreset] = useState<CameraPreset>("isometric");

  const [cameraAngle, setCameraAngle] = useState<number>(0);
  const [zoom, setZoom] = useState<number>(1.0);
  const [panX, setPanX] = useState<number>(0);
  const [panY, setPanY] = useState<number>(20);
  const [pitchTilt, setPitchTilt] = useState<number>(0.52);
  const [showGrid, setShowGrid] = useState<boolean>(true);
  const [showZones, setShowZones] = useState<boolean>(true);
  const [nightMode, setNightMode] = useState<boolean>(false);

  const [toolMode, setToolMode] = useState<"select" | "build" | "move" | "demolish">("select");
  const [ghostRotation, setGhostRotation] = useState<number>(0);
  const [hoverTile, setHoverTile] = useState<{ x: number; y: number } | null>(null);
  const [pendingPlacementTile, setPendingPlacementTile] = useState<{ x: number; y: number } | null>(null);
  const [internalEmptyPlot, setInternalEmptyPlot] = useState<{ x: number; y: number } | null>(null);
  const selectedEmptyPlot = externalEmptyPlot !== undefined ? externalEmptyPlot : internalEmptyPlot;
  const updateEmptyPlot = useCallback(
    (plot: { x: number; y: number } | null) => {
      setInternalEmptyPlot(plot);
      onSelectEmptyPlot?.(plot);
    },
    [onSelectEmptyPlot]
  );

  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number; panX: number; panY: number }>({
    x: 0,
    y: 0,
    panX: 0,
    panY: 0,
  });

  const [undoStack, setUndoStack] = useState<HistorySnapshot[]>([]);
  const [redoStack, setRedoStack] = useState<HistorySnapshot[]>([]);
  const [loadedStats, setLoadedStats] = useState<{
    meshes: number;
    vertices: number;
    triangles: number;
    materials: number;
  }>({ meshes: 0, vertices: 0, triangles: 0, materials: 0 });
  const [perfStats, setPerfStats] = useState<{ fps: number; frameMs: number }>({
    fps: 60,
    frameMs: 16.6,
  });

  // Refs for Three.js WebGL scene
  const webglMountRef = useRef<HTMLDivElement | null>(null);
  const fallbackCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const groundPlaneRef = useRef<THREE.Mesh | null>(null);
  const gridGroupRef = useRef<THREE.Group | null>(null);
  const zonesGroupRef = useRef<THREE.Group | null>(null);
  const buildingsGroupRef = useRef<THREE.Group | null>(null);
  const ghostGroupRef = useRef<THREE.Group | null>(null);
  const sunLightRef = useRef<THREE.DirectionalLight | null>(null);
  const ambientLightRef = useRef<THREE.HemisphereLight | null>(null);
  const floodLightsGroupRef = useRef<THREE.Group | null>(null);
  const craneAnimRefs = useRef<THREE.Object3D[]>([]);

  useEffect(() => {
    if (activeBuildModuleKey) {
      setToolMode("build");
      if (selectedEmptyPlot) {
        setPendingPlacementTile(selectedEmptyPlot);
      }
    } else if (toolMode === "build") {
      setToolMode("select");
      setPendingPlacementTile(null);
    }
  }, [activeBuildModuleKey, toolMode, selectedEmptyPlot]);

  const catalogMap = useMemo(() => {
    const map: Record<string, CampusCatalogItem> = {};
    moduleCatalog.forEach((c) => {
      map[c.module_key] = c;
    });
    return map;
  }, [moduleCatalog]);

  const selectedModule = useMemo(
    () => placedModules.find((m) => m.instance_id === selectedInstanceId) || null,
    [placedModules, selectedInstanceId]
  );

  const activeCatalogSpec = useMemo(() => {
    if (toolMode === "build" && activeBuildModuleKey) {
      return catalogMap[activeBuildModuleKey] || null;
    }
    if (toolMode === "move" && selectedModule) {
      return catalogMap[selectedModule.module_key] || null;
    }
    return null;
  }, [toolMode, activeBuildModuleKey, selectedModule, catalogMap]);

  // Check if ghost placement at (gx, gy) is valid on the 24x18 authoritative grid
  const validateGhost = useCallback(
    (gx: number, gy: number, rot: number) => {
      let fw = 3;
      let fh = 3;
      let ignoreId: string | null = null;
      if (toolMode === "build" && activeCatalogSpec) {
        fw = activeCatalogSpec.footprint_w;
        fh = activeCatalogSpec.footprint_h;
      } else if (toolMode === "move" && selectedModule) {
        fw = selectedModule.footprint_w || 3;
        fh = selectedModule.footprint_h || 3;
        ignoreId = selectedModule.instance_id;
      } else {
        return { valid: true, w: 1, h: 1, reason: "" };
      }

      const effW = rot === 90 || rot === 270 ? fh : fw;
      const effH = rot === 90 || rot === 270 ? fw : fh;

      if (gx < 0 || gy < 0 || gx + effW > gridWidth || gy + effH > gridHeight) {
        return { valid: false, w: effW, h: effH, reason: "Out of 24×18 campus boundary" };
      }

      for (const m of placedModules) {
        if (ignoreId && m.instance_id === ignoreId) continue;
        const mw = Number(m.effective_w || m.footprint_w || 3);
        const mh = Number(m.effective_h || m.footprint_h || 3);
        const overlap = gx < m.x + mw && gx + effW > m.x && gy < m.y + mh && gy + effH > m.y;
        if (overlap) {
          return { valid: false, w: effW, h: effH, reason: `Collides with ${m.name || m.module_key}` };
        }
      }
      return { valid: true, w: effW, h: effH, reason: "Valid placement footprint" };
    },
    [toolMode, activeCatalogSpec, selectedModule, placedModules, gridWidth, gridHeight]
  );

  // Convert authoritative grid coordinates (x, y, w, h) to Three.js world center (wx, wz)
  const gridToWorld = useCallback(
    (gx: number, gy: number, w = 1, h = 1): { wx: number; wz: number } => {
      const wx = gx + w / 2 - gridWidth / 2;
      const wz = gy + h / 2 - gridHeight / 2;
      return { wx, wz };
    },
    [gridWidth, gridHeight]
  );

  // Convert Three.js world point (wx, wz) to authoritative grid tile (gx, gy)
  const worldToGrid = useCallback(
    (wx: number, wz: number): { x: number; y: number } => {
      const gx = Math.floor(wx + gridWidth / 2);
      const gy = Math.floor(wz + gridHeight / 2);
      return {
        x: Math.max(0, Math.min(gridWidth - 1, gx)),
        y: Math.max(0, Math.min(gridHeight - 1, gy)),
      };
    },
    [gridWidth, gridHeight]
  );

  // Apply Camera Preset to Three.js Camera & OrbitControls
  const applyCameraPreset = useCallback((preset: CameraPreset) => {
    setCameraPreset(preset);
    const cam = cameraRef.current;
    const ctrl = controlsRef.current;
    if (!cam || !ctrl) return;

    if (preset === "isometric") {
      ctrl.target.set(0, 0.5, 0);
      cam.position.set(-16, 15.5, 17.5);
    } else if (preset === "top_down") {
      ctrl.target.set(0, 0, 0);
      cam.position.set(0, 26, 0.01);
    } else if (preset === "stadium_aerial") {
      ctrl.target.set(6.8, 1.1, -4.2);
      cam.position.set(14.5, 9.8, 6.2);
    } else if (preset === "academy_precinct") {
      ctrl.target.set(-8.6, 0.7, -3.5);
      cam.position.set(-15.8, 7.6, 4.8);
    } else if (preset === "ground_level") {
      ctrl.target.set(6.5, 1.15, -4.2);
      cam.position.set(1.8, 2.05, 1.6);
    }
    cam.updateProjectionMatrix();
    ctrl.update();
  }, []);

  const focusSelectedBuilding = useCallback(() => {
    const cam = cameraRef.current;
    const ctrl = controlsRef.current;
    if (!cam || !ctrl) return;
    if (selectedModule) {
      const spec = catalogMap[selectedModule.module_key];
      const rawW = Number(selectedModule.footprint_w || spec?.footprint_w || 3);
      const rawH = Number(selectedModule.footprint_h || spec?.footprint_h || 3);
      const rot = Number(selectedModule.rotation || 0) % 360;
      const effW = Number(selectedModule.effective_w || (rot === 90 || rot === 270 ? rawH : rawW));
      const effH = Number(selectedModule.effective_h || (rot === 90 || rot === 270 ? rawW : rawH));
      const { wx, wz } = gridToWorld(selectedModule.x, selectedModule.y, effW, effH);
      ctrl.target.set(wx, 0.75, wz);
      cam.position.set(wx - 4.8, 4.8, wz + 5.6);
      cam.updateProjectionMatrix();
      ctrl.update();
    } else if (selectedEmptyPlot) {
      const { wx, wz } = gridToWorld(selectedEmptyPlot.x, selectedEmptyPlot.y, 2, 2);
      ctrl.target.set(wx, 0.4, wz);
      cam.position.set(wx - 4.5, 5.0, wz + 5.2);
      cam.updateProjectionMatrix();
      ctrl.update();
    }
  }, [selectedModule, selectedEmptyPlot, catalogMap, gridToWorld]);

  // ---------------------------------------------------------------------------
  // 1. Initialize Three.js WebGL Scene, Terrain, Roads, Landscaping & Controls
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (rendererMode !== "webgl_3d") return;
    const mount = webglMountRef.current;
    if (!mount) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: qualityTier !== "low",
        powerPreference: "high-performance",
        alpha: false,
      });
    } catch {
      setWebglStatus("fallback");
      setRendererMode("canvas_fallback");
      return;
    }

    const width = mount.clientWidth || 960;
    const height = mount.clientHeight || 540;
    const dpr =
      qualityTier === "high"
        ? Math.min(window.devicePixelRatio || 1, 2)
        : qualityTier === "balanced"
        ? 1.25
        : 1.0;

    renderer.setSize(width, height);
    renderer.setPixelRatio(dpr);
    renderer.shadowMap.enabled = qualityTier !== "low";
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.12;
    renderer.domElement.setAttribute("data-testid", "campus-builder-canvas");
    renderer.domElement.setAttribute("data-engine", "three-webgl");
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.display = "block";

    mount.innerHTML = "";
    mount.appendChild(renderer.domElement);
    rendererRef.current = renderer;
    setWebglStatus("active");

    // WebGL Context Loss & Restoration Recovery
    const onContextLost = (e: Event) => {
      e.preventDefault();
      setWebglStatus("context_lost");
    };
    const onContextRestored = () => {
      setWebglStatus("active");
    };
    renderer.domElement.addEventListener("webglcontextlost", onContextLost, false);
    renderer.domElement.addEventListener("webglcontextrestored", onContextRestored, false);

    // Scene & Atmosphere
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#071510");
    scene.fog = new THREE.FogExp2("#071510", 0.014);
    sceneRef.current = scene;

    // Camera & OrbitControls
    const camera = new THREE.PerspectiveCamera(42, width / height, 0.2, 160);
    camera.position.set(-16, 15.5, 17.5);
    cameraRef.current = camera;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0.5, 0);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.maxPolarAngle = Math.PI / 2 - 0.03;
    controls.minDistance = 4.5;
    controls.maxDistance = 44;
    controls.touches = {
      ONE: THREE.TOUCH.ROTATE,
      TWO: THREE.TOUCH.DOLLY_PAN,
    };
    controls.update();
    controlsRef.current = controls;

    // Lighting System (Hemisphere + Shadow-Casting Sun + Night Floodlight Rig)
    const hemiLight = new THREE.HemisphereLight(0xdff6ff, 0x10331f, 0.85);
    hemiLight.position.set(0, 30, 0);
    scene.add(hemiLight);
    ambientLightRef.current = hemiLight;

    const sunLight = new THREE.DirectionalLight(0xfff6e5, 1.65);
    sunLight.position.set(-18, 26, 16);
    sunLight.castShadow = qualityTier !== "low";
    const shadowRes = qualityTier === "high" ? 2048 : 1024;
    sunLight.shadow.mapSize.width = shadowRes;
    sunLight.shadow.mapSize.height = shadowRes;
    sunLight.shadow.camera.near = 2;
    sunLight.shadow.camera.far = 75;
    sunLight.shadow.camera.left = -20;
    sunLight.shadow.camera.right = 20;
    sunLight.shadow.camera.top = 18;
    sunLight.shadow.camera.bottom = -18;
    sunLight.shadow.bias = -0.0005;
    scene.add(sunLight);
    sunLightRef.current = sunLight;

    const floodGroup = new THREE.Group();
    const stadiumSpot1 = new THREE.PointLight(0xe0f2fe, 42, 34, 1.35);
    stadiumSpot1.position.set(6.5, 6.2, -3.5);
    const stadiumSpot2 = new THREE.PointLight(0xfef3c7, 32, 30, 1.35);
    stadiumSpot2.position.set(-4.5, 5.5, -2.5);
    const hqSpot = new THREE.PointLight(0x34d399, 26, 26, 1.35);
    hqSpot.position.set(-2.5, 4.5, 5.0);
    const academySpot = new THREE.PointLight(0xfde68a, 28, 28, 1.35);
    academySpot.position.set(5.5, 5.0, 3.5);
    floodGroup.add(stadiumSpot1, stadiumSpot2, hqSpot, academySpot);
    floodGroup.visible = false;
    scene.add(floodGroup);
    floodLightsGroupRef.current = floodGroup;

    // Ground & Landscaped Terrain Plinth
    const outerGroundGeo = new THREE.PlaneGeometry(72, 60);
    const outerGroundMat = new THREE.MeshStandardMaterial({
      color: 0x0b2619,
      roughness: 0.94,
      metalness: 0.02,
    });
    const outerGround = new THREE.Mesh(outerGroundGeo, outerGroundMat);
    outerGround.rotation.x = -Math.PI / 2;
    outerGround.position.y = -0.12;
    outerGround.receiveShadow = true;
    scene.add(outerGround);

    // Beveled Architectural Estate Plinth (26 x 20 around the 24 x 18 grid)
    const plinthGeo = new THREE.BoxGeometry(gridWidth + 1.6, 0.16, gridHeight + 1.6);
    const plinthMat = new THREE.MeshStandardMaterial({
      color: 0x133824,
      roughness: 0.85,
      metalness: 0.05,
    });
    const plinthMesh = new THREE.Mesh(plinthGeo, plinthMat);
    plinthMesh.position.set(0, -0.08, 0);
    plinthMesh.receiveShadow = true;
    scene.add(plinthMesh);

    // Raycastable Authoritative 24x18 Ground Plane (Y = 0)
    const rayPlaneGeo = new THREE.PlaneGeometry(gridWidth, gridHeight);
    const rayPlaneMat = new THREE.MeshStandardMaterial({
      color: 0x16442b,
      roughness: 0.88,
      metalness: 0.04,
    });
    const rayPlane = new THREE.Mesh(rayPlaneGeo, rayPlaneMat);
    rayPlane.rotation.x = -Math.PI / 2;
    rayPlane.position.y = 0.0;
    rayPlane.receiveShadow = true;
    rayPlane.name = "authoritative_campus_ground";
    scene.add(rayPlane);
    groundPlaneRef.current = rayPlane;

    // Campus Roads, Walkways, Executive Parking & Perimeter Landscaping
    const infraGroup = new THREE.Group();
    const roadMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.72, metalness: 0.12 });
    const curbMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, roughness: 0.6, metalness: 0.1 });
    const goldLineMat = new THREE.MeshStandardMaterial({
      color: 0xeab308,
      roughness: 0.35,
      metalness: 0.8,
      emissive: 0x422006,
    });

    // East-West Grand Campus Boulevard (along grid row y=11.2, separating pitches from HQ/Operations)
    const mainRoad = new THREE.Mesh(new THREE.BoxGeometry(gridWidth - 0.4, 0.025, 0.85), roadMat);
    mainRoad.position.set(0, 0.012, 11.5 - gridHeight / 2);
    mainRoad.receiveShadow = true;
    const roadLine = new THREE.Mesh(new THREE.BoxGeometry(gridWidth - 1.2, 0.03, 0.05), goldLineMat);
    roadLine.position.set(0, 0.015, 11.5 - gridHeight / 2);
    infraGroup.add(mainRoad, roadLine);

    // North-South Avenue Spine (along grid column x=6.3 and x=14.8)
    for (const spineX of [6.5 - gridWidth / 2, 15.0 - gridWidth / 2]) {
      const spine = new THREE.Mesh(new THREE.BoxGeometry(0.65, 0.024, gridHeight - 0.6), roadMat);
      spine.position.set(spineX, 0.011, 0);
      spine.receiveShadow = true;
      const curbL = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.035, gridHeight - 0.6), curbMat);
      curbL.position.set(spineX - 0.34, 0.016, 0);
      const curbR = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.035, gridHeight - 0.6), curbMat);
      curbR.position.set(spineX + 0.34, 0.016, 0);
      infraGroup.add(spine, curbL, curbR);
    }

    // Executive Parking Lot (South-West Corner: grid x=1..5, y=13..16)
    const parkingLot = new THREE.Mesh(new THREE.BoxGeometry(4.2, 0.025, 3.0), roadMat);
    parkingLot.position.set(3.2 - gridWidth / 2, 0.012, 14.8 - gridHeight / 2);
    parkingLot.receiveShadow = true;
    infraGroup.add(parkingLot);
    for (let bay = -1.6; bay <= 1.6; bay += 0.65) {
      const stripe = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.03, 1.1), curbMat);
      stripe.position.set(3.2 - gridWidth / 2 + bay, 0.015, 14.1 - gridHeight / 2);
      infraGroup.add(stripe);
    }

    // Load Perimeter Tree Clusters + Indoor Training Arena Landmark on North-West Terrace
    loadGlbTemplateLazy("/models/campus/campus_tree_cluster.glb").then((treeEntry) => {
      if (!treeEntry || !sceneRef.current) return;
      const treeSpots: [number, number][] = [
        [-13.0, -9.5],
        [-9.0, -9.8],
        [-4.0, -9.8],
        [2.0, -9.8],
        [8.0, -9.8],
        [12.8, -9.5],
        [-13.0, -4.0],
        [-13.0, 2.0],
        [-13.0, 7.5],
        [13.0, -3.0],
        [13.0, 3.5],
        [13.0, 8.5],
        [-10.5, 9.6],
        [-4.5, 9.6],
        [3.5, 9.6],
        [10.5, 9.6],
      ];
      treeSpots.forEach(([tx, tz], idx) => {
        const clone = treeEntry.scene.clone(true);
        clone.position.set(tx, 0, tz);
        clone.rotation.y = (idx * 1.1) % (Math.PI * 2);
        const sc = 0.85 + (idx % 3) * 0.18;
        clone.scale.set(sc, sc, sc);
        infraGroup.add(clone);
      });
    });

    // Load Indoor Training Arena Dome on the North Perimeter Terrace so all 13 mandated scene elements are visible
    loadGlbTemplateLazy("/models/campus/indoor_training_arena.glb").then((domeEntry) => {
      if (!domeEntry || !sceneRef.current) return;
      const domeClone = domeEntry.scene.clone(true);
      domeClone.position.set(-8.5, 0, -10.8);
      domeClone.scale.set(0.9, 0.9, 0.9);
      infraGroup.add(domeClone);
    });

    scene.add(infraGroup);

    // Dynamic Sub-Groups for Grid, Zones, Placed Buildings, and Placement Ghost
    const gridGroup = new THREE.Group();
    scene.add(gridGroup);
    gridGroupRef.current = gridGroup;

    const zonesGroup = new THREE.Group();
    scene.add(zonesGroup);
    zonesGroupRef.current = zonesGroup;

    const buildingsGroup = new THREE.Group();
    scene.add(buildingsGroup);
    buildingsGroupRef.current = buildingsGroup;

    const ghostGroup = new THREE.Group();
    scene.add(ghostGroup);
    ghostGroupRef.current = ghostGroup;

    // Animation Loop with Live FPS & Frame-Time Telemetry
    let animId = 0;
    const clock = new THREE.Clock();
    let frameCount = 0;
    let lastPerfSample = performance.now();
    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();
      controls.update();

      // Gently pulse construction beacon rings without rotating the grid-aligned foundation slab
      craneAnimRefs.current.forEach((beaconObj, idx) => {
        beaconObj.position.y = 0.025 + Math.sin(elapsed * 2.2 + idx) * 0.008;
      });

      renderer.render(scene, camera);

      frameCount += 1;
      const now = performance.now();
      if (now - lastPerfSample >= 1000) {
        const dt = now - lastPerfSample;
        const measuredFps = Math.min(120, Math.max(1, Math.round((frameCount * 1000) / dt)));
        const measuredMs = Number((dt / Math.max(1, frameCount)).toFixed(1));
        setPerfStats({ fps: measuredFps, frameMs: measuredMs });
        frameCount = 0;
        lastPerfSample = now;
      }
    };
    animate();

    // Responsive Resize Observer
    const handleResize = () => {
      if (!webglMountRef.current || !rendererRef.current || !cameraRef.current) return;
      const w = webglMountRef.current.clientWidth || 960;
      const h = webglMountRef.current.clientHeight || 540;
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(w, h);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", handleResize);
      renderer.domElement.removeEventListener("webglcontextlost", onContextLost);
      renderer.domElement.removeEventListener("webglcontextrestored", onContextRestored);
      controls.dispose();
      renderer.dispose();
    };
  }, [rendererMode, qualityTier, gridWidth, gridHeight]);

  // ---------------------------------------------------------------------------
  // 2. Sync Grid Lines, Precinct Zones & Night/Day Lighting
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const gridGroup = gridGroupRef.current;
    if (!gridGroup) return;
    gridGroup.clear();
    gridGroup.visible = showGrid;
    if (showGrid) {
      const points: THREE.Vector3[] = [];
      for (let x = 0; x <= gridWidth; x++) {
        const wx = x - gridWidth / 2;
        points.push(new THREE.Vector3(wx, 0.018, -gridHeight / 2));
        points.push(new THREE.Vector3(wx, 0.018, gridHeight / 2));
      }
      for (let y = 0; y <= gridHeight; y++) {
        const wz = y - gridHeight / 2;
        points.push(new THREE.Vector3(-gridWidth / 2, 0.018, wz));
        points.push(new THREE.Vector3(gridWidth / 2, 0.018, wz));
      }
      const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
      const lineMat = new THREE.LineBasicMaterial({
        color: 0x34d399,
        transparent: true,
        opacity: 0.22,
      });
      gridGroup.add(new THREE.LineSegments(lineGeo, lineMat));
    }
  }, [showGrid, gridWidth, gridHeight, rendererMode]);

  useEffect(() => {
    const zonesGroup = zonesGroupRef.current;
    if (!zonesGroup) return;
    zonesGroup.clear();
    zonesGroup.visible = showZones;
    if (showZones) {
      zones.forEach((z) => {
        const { wx, wz } = gridToWorld(z.x, z.y, z.w, z.h);
        const zoneGeo = new THREE.PlaneGeometry(z.w - 0.12, z.h - 0.12);
        const zoneMat = new THREE.MeshBasicMaterial({
          color: new THREE.Color(z.color || "#10b981"),
          transparent: true,
          opacity: 0.14,
          side: THREE.DoubleSide,
        });
        const zoneMesh = new THREE.Mesh(zoneGeo, zoneMat);
        zoneMesh.rotation.x = -Math.PI / 2;
        zoneMesh.position.set(wx, 0.014, wz);
        zonesGroup.add(zoneMesh);
      });
    }
  }, [showZones, zones, gridToWorld, rendererMode]);

  useEffect(() => {
    const scene = sceneRef.current;
    const sun = sunLightRef.current;
    const hemi = ambientLightRef.current;
    const flood = floodLightsGroupRef.current;
    if (!scene || !sun || !hemi || !flood) return;

    if (nightMode) {
      scene.background = new THREE.Color("#040d1a");
      scene.fog = new THREE.FogExp2("#040d1a", 0.011);
      sun.intensity = 0.72;
      sun.color.setHex(0x93c5fd);
      hemi.intensity = 0.75;
      flood.visible = true;
    } else {
      scene.background = new THREE.Color("#071510");
      scene.fog = new THREE.FogExp2("#071510", 0.014);
      sun.intensity = 1.65;
      sun.color.setHex(0xfff6e5);
      hemi.intensity = 0.85;
      flood.visible = false;
    }
  }, [nightMode, rendererMode]);

  // ---------------------------------------------------------------------------
  // 3. Populate Placed 3D Buildings & Stage-Specific Construction Models
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const buildingsGroup = buildingsGroupRef.current;
    if (!buildingsGroup || rendererMode !== "webgl_3d") return;

    let cancelled = false;
    buildingsGroup.clear();
    craneAnimRefs.current = [];

    const loadAllPlaced = async () => {
      let totalVerts = 0;
      let totalTris = 0;
      let totalMats = 0;
      const uniqueUrls = new Set<string>();

      for (const mod of placedModules) {
        if (cancelled) return;
        const spec = catalogMap[mod.module_key];
        const rawW = Number(mod.footprint_w || spec?.footprint_w || 3);
        const rawH = Number(mod.footprint_h || spec?.footprint_h || 3);
        const rot = Number(mod.rotation || 0) % 360;
        const effW = Number(mod.effective_w || (rot === 90 || rot === 270 ? rawH : rawW));
        const effH = Number(mod.effective_h || (rot === 90 || rot === 270 ? rawW : rawH));
        const { wx, wz } = gridToWorld(mod.x, mod.y, effW, effH);

        const container = new THREE.Group();
        container.position.set(wx, 0, wz);
        container.rotation.y = (-rot * Math.PI) / 180;
        container.userData = { instanceId: mod.instance_id, moduleKey: mod.module_key };

        const isSelected = mod.instance_id === selectedInstanceId;
        const isUnderConstruction =
          mod.status === "under_construction" || Number(mod.progress_pct ?? 100) < 100;
        const progressPct = Number(mod.progress_pct ?? 100);
        const isReadyForCompletion =
          isUnderConstruction && (mod.construction_stage === "finishing" || progressPct >= 80);
        const isUpgradeEligible = !isUnderConstruction && Number(mod.level || 1) < Number(mod.max_level || 5);

        // Architectural Status & Selection Plinth Ring
        if (isSelected || isUnderConstruction || isUpgradeEligible) {
          const ringColor = isSelected
            ? 0xfbbf24
            : isReadyForCompletion
            ? 0x10b981
            : isUnderConstruction
            ? 0xf59e0b
            : 0x38bdf8;
          const ringOpacity = isSelected ? 0.65 : isUnderConstruction ? 0.48 : 0.22;
          const ringGeo = new THREE.BoxGeometry(rawW + 0.14, 0.04, rawH + 0.14);
          const ringMat = new THREE.MeshBasicMaterial({
            color: ringColor,
            transparent: true,
            opacity: ringOpacity,
          });
          const ringMesh = new THREE.Mesh(ringGeo, ringMat);
          ringMesh.position.set(0, 0.02, 0);
          container.add(ringMesh);
          if (isUnderConstruction) {
            craneAnimRefs.current.push(ringMesh);
          }
        }

        const primaryGlbUrl =
          mod.model_glb_url ||
          spec?.model_glb_url ||
          `/models/campus/${mod.module_key}.glb`;

        if (isUnderConstruction) {
          // Load self-contained stage-specific 3D construction model (Zero overlap with completed mesh)
          const stageGlbUrl = resolveStageGlbUrl(
            mod.construction_stage,
            progressPct,
            primaryGlbUrl
          );
          uniqueUrls.add(normalizeUrl(stageGlbUrl));
          const stageEntry = await loadGlbTemplateLazy(stageGlbUrl);
          if (stageEntry && !cancelled) {
            const stageClone = stageEntry.scene.clone(true);
            const sx = rawW / 3.0;
            const sz = rawH / 3.0;
            stageClone.scale.set(sx, 1.0, sz);
            container.add(stageClone);
            totalVerts += stageEntry.vertexCount;
            totalTris += stageEntry.triangleCount;
            totalMats += stageEntry.materialCount;
          }
        } else {
          // Completed Operational Facility: Cleanly replaces construction stage model
          uniqueUrls.add(normalizeUrl(primaryGlbUrl));
          const entry = await loadGlbTemplateLazy(primaryGlbUrl);
          if (entry && !cancelled) {
            const modelClone = entry.scene.clone(true);
            const lvlScale = 1.0 + Math.max(0, (Number(mod.level || 1) - 1) * 0.12);
            modelClone.scale.set(1.0, lvlScale, 1.0);
            container.add(modelClone);
            totalVerts += entry.vertexCount;
            totalTris += entry.triangleCount;
            totalMats += entry.materialCount;
          }
        }

        // Propagate instanceId to all child meshes for 3D raycasting selection
        container.traverse((child) => {
          child.userData = {
            ...child.userData,
            instanceId: mod.instance_id,
            moduleKey: mod.module_key,
          };
        });

        buildingsGroup.add(container);
      }

      if (!cancelled) {
        setLoadedStats({
          meshes: Math.max(uniqueUrls.size, gltfTemplateCache.size),
          vertices: totalVerts,
          triangles: totalTris,
          materials: totalMats,
        });
      }
    };

    loadAllPlaced();
    return () => {
      cancelled = true;
    };
  }, [placedModules, catalogMap, selectedInstanceId, gridToWorld, rendererMode]);

  // ---------------------------------------------------------------------------
  // 4. Update 3D Placement Ghost Preview & Empty Plot Selection Beacon
  // ---------------------------------------------------------------------------
  const activeGhostTile = pendingPlacementTile || hoverTile;
  useEffect(() => {
    const ghostGroup = ghostGroupRef.current;
    if (!ghostGroup || rendererMode !== "webgl_3d") return;
    ghostGroup.clear();

    // In Select Mode, render a glowing 3D plot beacon if an empty plot is selected
    if (toolMode === "select" && selectedEmptyPlot) {
      const { wx, wz } = gridToWorld(selectedEmptyPlot.x, selectedEmptyPlot.y, 1, 1);
      const plotPad = new THREE.Mesh(
        new THREE.BoxGeometry(0.92, 0.06, 0.92),
        new THREE.MeshBasicMaterial({
          color: 0x10b981,
          transparent: true,
          opacity: 0.52,
        })
      );
      plotPad.position.set(wx, 0.03, wz);
      const plotBeacon = new THREE.Mesh(
        new THREE.CylinderGeometry(0.14, 0.14, 0.55, 16),
        new THREE.MeshBasicMaterial({
          color: 0xfbbf24,
          transparent: true,
          opacity: 0.72,
        })
      );
      plotBeacon.position.set(wx, 0.30, wz);
      ghostGroup.add(plotPad, plotBeacon);
      return;
    }

    if ((toolMode !== "build" && toolMode !== "move") || !activeGhostTile) return;

    const check = validateGhost(activeGhostTile.x, activeGhostTile.y, ghostRotation);
    const { wx, wz } = gridToWorld(activeGhostTile.x, activeGhostTile.y, check.w, check.h);

    const ghostColor = check.valid ? 0x10b981 : 0xef4444;
    const padGeo = new THREE.BoxGeometry(check.w - 0.08, 0.08, check.h - 0.08);
    const padMat = new THREE.MeshBasicMaterial({
      color: ghostColor,
      transparent: true,
      opacity: 0.48,
    });
    const padMesh = new THREE.Mesh(padGeo, padMat);
    padMesh.position.set(wx, 0.04, wz);
    ghostGroup.add(padMesh);

    const ghostGlbUrl =
      activeCatalogSpec?.model_glb_url ||
      (activeCatalogSpec ? `/models/campus/${activeCatalogSpec.module_key}.glb` : null);

    if (ghostGlbUrl) {
      let cancelled = false;
      loadGlbTemplateLazy(ghostGlbUrl).then((entry) => {
        if (cancelled || !entry || !ghostGroupRef.current) return;
        const previewClone = entry.scene.clone(true);
        previewClone.position.set(wx, 0.05, wz);
        previewClone.rotation.y = (-ghostRotation * Math.PI) / 180;
        previewClone.traverse((child) => {
          const mesh = child as THREE.Mesh;
          if (mesh.isMesh) {
            mesh.material = new THREE.MeshStandardMaterial({
              color: ghostColor,
              emissive: ghostColor,
              emissiveIntensity: 0.25,
              transparent: true,
              opacity: 0.62,
              roughness: 0.3,
            });
          }
        });
        ghostGroupRef.current.add(previewClone);
      });
      return () => {
        cancelled = true;
      };
    }
  }, [
    toolMode,
    activeGhostTile,
    selectedEmptyPlot,
    ghostRotation,
    validateGhost,
    gridToWorld,
    activeCatalogSpec,
    rendererMode,
  ]);

  // ---------------------------------------------------------------------------
  // 5. Three.js 3D Raycasting for Ground Snapping & Building Selection
  // ---------------------------------------------------------------------------
  const raycastWebGL = useCallback(
    (clientX: number, clientY: number) => {
      const renderer = rendererRef.current;
      const camera = cameraRef.current;
      if (!renderer || !camera) return { tile: null, hitInstanceId: null };

      const rect = renderer.domElement.getBoundingClientRect();
      const ndc = new THREE.Vector2(
        ((clientX - rect.left) / rect.width) * 2 - 1,
        -((clientY - rect.top) / rect.height) * 2 + 1
      );
      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(ndc, camera);

      let hitInstanceId: string | null = null;
      if (buildingsGroupRef.current) {
        const bHits = raycaster.intersectObjects(buildingsGroupRef.current.children, true);
        if (bHits.length > 0) {
          let obj: THREE.Object3D | null = bHits[0].object;
          while (obj && !obj.userData?.instanceId) {
            obj = obj.parent;
          }
          if (obj?.userData?.instanceId) {
            hitInstanceId = String(obj.userData.instanceId);
          }
        }
      }

      let tile: { x: number; y: number } | null = null;
      if (groundPlaneRef.current) {
        const gHits = raycaster.intersectObject(groundPlaneRef.current, false);
        if (gHits.length > 0) {
          const pt = gHits[0].point;
          tile = worldToGrid(pt.x, pt.z);
        }
      }
      return { tile, hitInstanceId };
    },
    [worldToGrid]
  );

  const commitBuildOrMoveAtTile = useCallback(
    (tileX: number, tileY: number) => {
      if (toolMode === "build" && activeBuildModuleKey) {
        const check = validateGhost(tileX, tileY, ghostRotation);
        if (check.valid && !busy) {
          onPlaceNewModule(activeBuildModuleKey, tileX, tileY, ghostRotation);
          setPendingPlacementTile(null);
        }
        return;
      }
      if (toolMode === "move" && selectedModule) {
        const check = validateGhost(tileX, tileY, ghostRotation);
        if (check.valid && !busy) {
          setUndoStack((u) => [
            ...u,
            {
              instanceId: selectedModule.instance_id,
              x: selectedModule.x,
              y: selectedModule.y,
              rotation: selectedModule.rotation,
            },
          ]);
          setRedoStack([]);
          onMoveModule(selectedModule.instance_id, tileX, tileY, ghostRotation);
          setPendingPlacementTile(null);
          setToolMode("select");
        }
      }
    },
    [
      toolMode,
      activeBuildModuleKey,
      selectedModule,
      ghostRotation,
      validateGhost,
      busy,
      onPlaceNewModule,
      onMoveModule,
    ]
  );

  const pointerDownPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  const handleWebGLPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const { tile } = raycastWebGL(e.clientX, e.clientY);
    if (tile) setHoverTile(tile);
  };

  const handleWebGLPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    pointerDownPosRef.current = { x: e.clientX, y: e.clientY };
  };

  const handleWebGLPointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    const dx = Math.abs(e.clientX - pointerDownPosRef.current.x);
    const dy = Math.abs(e.clientY - pointerDownPosRef.current.y);
    // Ignore camera orbit drags (> 6px pointer movement)
    if (dx > 6 || dy > 6) return;

    const { tile, hitInstanceId } = raycastWebGL(e.clientX, e.clientY);

    if ((toolMode === "build" && activeBuildModuleKey) || (toolMode === "move" && selectedModule)) {
      if (tile) {
        if (
          pendingPlacementTile &&
          pendingPlacementTile.x === tile.x &&
          pendingPlacementTile.y === tile.y
        ) {
          commitBuildOrMoveAtTile(tile.x, tile.y);
          updateEmptyPlot(null);
        } else {
          setPendingPlacementTile(tile);
        }
      }
      return;
    }

    if (hitInstanceId) {
      if (toolMode === "demolish") {
        onDemolishModule(hitInstanceId);
        setToolMode("select");
      } else {
        onSelectInstance(hitInstanceId);
        updateEmptyPlot(null);
        const hitMod = placedModules.find((m) => m.instance_id === hitInstanceId);
        if (hitMod) setGhostRotation(hitMod.rotation || 0);
      }
    } else if (tile) {
      const tileHit = placedModules.find((m) => {
        const mw = Number(m.effective_w || m.footprint_w || 3);
        const mh = Number(m.effective_h || m.footprint_h || 3);
        return tile.x >= m.x && tile.x < m.x + mw && tile.y >= m.y && tile.y < m.y + mh;
      });
      if (tileHit) {
        onSelectInstance(tileHit.instance_id);
        updateEmptyPlot(null);
      } else {
        updateEmptyPlot(tile);
      }
    }
  };

  // Keyboard shortcuts (R to rotate, Escape to cancel, WASD to pan)
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (
        document.activeElement &&
        ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)
      ) {
        return;
      }
      if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        setGhostRotation((prev) => (prev + 90) % 360);
      } else if (e.key === "Escape") {
        onClearBuildMode();
        setPendingPlacementTile(null);
        setToolMode("select");
      } else if (e.key === "w" || e.key === "W") {
        setPanY((p) => p + 24);
        if (controlsRef.current && cameraRef.current) {
          controlsRef.current.target.z -= 1.2;
          cameraRef.current.position.z -= 1.2;
        }
      } else if (e.key === "s" || e.key === "S") {
        setPanY((p) => p - 24);
        if (controlsRef.current && cameraRef.current) {
          controlsRef.current.target.z += 1.2;
          cameraRef.current.position.z += 1.2;
        }
      } else if (e.key === "a" || e.key === "A") {
        setPanX((p) => p + 24);
        if (controlsRef.current && cameraRef.current) {
          controlsRef.current.target.x -= 1.2;
          cameraRef.current.position.x -= 1.2;
        }
      } else if (e.key === "d" || e.key === "D") {
        setPanX((p) => p - 24);
        if (controlsRef.current && cameraRef.current) {
          controlsRef.current.target.x += 1.2;
          cameraRef.current.position.x += 1.2;
        }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClearBuildMode]);

  // ---------------------------------------------------------------------------
  // 6. Lightweight 2D Isometric Canvas Fallback / Inspector
  // ---------------------------------------------------------------------------
  const rotateGridCoords = useCallback(
    (gx: number, gy: number): { rx: number; ry: number } => {
      const cx = gridWidth / 2;
      const cy = gridHeight / 2;
      const dx = gx - cx;
      const dy = gy - cy;
      if (cameraAngle === 90) return { rx: cx - dy, ry: cy + dx };
      if (cameraAngle === 180) return { rx: cx - dx, ry: cy - dy };
      if (cameraAngle === 270) return { rx: cx + dy, ry: cy - dx };
      return { rx: gx, ry: gy };
    },
    [cameraAngle, gridWidth, gridHeight]
  );

  const projectIso = useCallback(
    (gx: number, gy: number, gz: number, canvasW: number, canvasH: number) => {
      const { rx, ry } = rotateGridCoords(gx, gy);
      const tileW = 38 * zoom;
      const tileH = 38 * pitchTilt * zoom;
      const originX = canvasW / 2 + panX;
      const originY = canvasH * 0.22 + panY;
      const sx = originX + (rx - ry) * (tileW / 2);
      const sy = originY + (rx + ry) * (tileH / 2) - gz * (26 * zoom);
      return { sx, sy };
    },
    [rotateGridCoords, zoom, pitchTilt, panX, panY]
  );

  const unprojectIso = useCallback(
    (sx: number, sy: number, canvasW: number, canvasH: number): { x: number; y: number } => {
      const tileW = 38 * zoom;
      const tileH = 38 * pitchTilt * zoom;
      const originX = canvasW / 2 + panX;
      const originY = canvasH * 0.22 + panY;
      const dx = (sx - originX) / (tileW / 2);
      const dy = (sy - originY) / (tileH / 2);
      const rx = (dy + dx) / 2;
      const ry = (dy - dx) / 2;
      const cx = gridWidth / 2;
      const cy = gridHeight / 2;
      const rdx = rx - cx;
      const rdy = ry - cy;
      let gx = rx;
      let gy = ry;
      if (cameraAngle === 90) {
        gx = cx + rdy;
        gy = cy - rdx;
      } else if (cameraAngle === 180) {
        gx = cx - rdx;
        gy = cy - rdy;
      } else if (cameraAngle === 270) {
        gx = cx - rdy;
        gy = cy + rdx;
      }
      return { x: Math.floor(gx), y: Math.floor(gy) };
    },
    [zoom, pitchTilt, panX, panY, gridWidth, gridHeight, cameraAngle]
  );

  useEffect(() => {
    if (rendererMode !== "canvas_fallback") return;
    const canvas = fallbackCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    const W = rect.width;
    const H = rect.height;

    ctx.fillStyle = nightMode ? "#030a16" : "#071a12";
    ctx.fillRect(0, 0, W, H);

    // Draw 24x18 isometric grid
    const p00 = projectIso(0, 0, 0, W, H);
    const pW0 = projectIso(gridWidth, 0, 0, W, H);
    const pWH = projectIso(gridWidth, gridHeight, 0, W, H);
    const p0H = projectIso(0, gridHeight, 0, W, H);
    ctx.beginPath();
    ctx.moveTo(p00.sx, p00.sy);
    ctx.lineTo(pW0.sx, pW0.sy);
    ctx.lineTo(pWH.sx, pWH.sy);
    ctx.lineTo(p0H.sx, p0H.sy);
    ctx.closePath();
    ctx.fillStyle = "#0f3822";
    ctx.fill();
    ctx.strokeStyle = "rgba(16,185,129,0.5)";
    ctx.stroke();

    if (showGrid) {
      ctx.strokeStyle = "rgba(255,255,255,0.1)";
      for (let x = 0; x <= gridWidth; x++) {
        const a = projectIso(x, 0, 0, W, H);
        const b = projectIso(x, gridHeight, 0, W, H);
        ctx.beginPath();
        ctx.moveTo(a.sx, a.sy);
        ctx.lineTo(b.sx, b.sy);
        ctx.stroke();
      }
      for (let y = 0; y <= gridHeight; y++) {
        const a = projectIso(0, y, 0, W, H);
        const b = projectIso(gridWidth, y, 0, W, H);
        ctx.beginPath();
        ctx.moveTo(a.sx, a.sy);
        ctx.lineTo(b.sx, b.sy);
        ctx.stroke();
      }
    }

    placedModules.forEach((mod) => {
      const w = Number(mod.effective_w || mod.footprint_w || 3);
      const h = Number(mod.effective_h || mod.footprint_h || 3);
      const a = projectIso(mod.x, mod.y, 0, W, H);
      const b = projectIso(mod.x + w, mod.y, 0, W, H);
      const c = projectIso(mod.x + w, mod.y + h, 0, W, H);
      const d = projectIso(mod.x, mod.y + h, 0, W, H);
      ctx.beginPath();
      ctx.moveTo(a.sx, a.sy);
      ctx.lineTo(b.sx, b.sy);
      ctx.lineTo(c.sx, c.sy);
      ctx.lineTo(d.sx, d.sy);
      ctx.closePath();
      ctx.fillStyle = mod.color_hex || "#10b981";
      ctx.fill();
      ctx.strokeStyle = mod.instance_id === selectedInstanceId ? "#fbbf24" : "#ffffff";
      ctx.lineWidth = mod.instance_id === selectedInstanceId ? 2.5 : 1;
      ctx.stroke();
      const center = projectIso(mod.x + w / 2, mod.y + h / 2, 0.2, W, H);
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 10px Inter, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(`${mod.name || mod.module_key} (L${mod.level})`, center.sx, center.sy);
    });
  }, [
    rendererMode,
    placedModules,
    selectedInstanceId,
    showGrid,
    nightMode,
    projectIso,
    gridWidth,
    gridHeight,
  ]);

  const handleFallbackMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = fallbackCanvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    if (isDragging) {
      setPanX(dragStart.panX + (e.clientX - dragStart.x));
      setPanY(dragStart.panY + (e.clientY - dragStart.y));
      return;
    }
    const tile = unprojectIso(e.clientX - rect.left, e.clientY - rect.top, rect.width, rect.height);
    if (tile.x >= 0 && tile.x < gridWidth && tile.y >= 0 && tile.y < gridHeight) {
      setHoverTile(tile);
    }
  };

  const handleFallbackMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = fallbackCanvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const tile = unprojectIso(e.clientX - rect.left, e.clientY - rect.top, rect.width, rect.height);
    if ((toolMode === "build" && activeBuildModuleKey) || (toolMode === "move" && selectedModule)) {
      commitBuildOrMoveAtTile(tile.x, tile.y);
      return;
    }
    const hit = placedModules.find((m) => {
      const mw = Number(m.effective_w || m.footprint_w || 3);
      const mh = Number(m.effective_h || m.footprint_h || 3);
      return tile.x >= m.x && tile.x < m.x + mw && tile.y >= m.y && tile.y < m.y + mh;
    });
    if (hit) {
      if (toolMode === "demolish") {
        onDemolishModule(hit.instance_id);
        setToolMode("select");
      } else {
        onSelectInstance(hit.instance_id);
      }
    } else {
      setIsDragging(true);
      setDragStart({ x: e.clientX, y: e.clientY, panX, panY });
    }
  };

  const handleUndo = () => {
    if (undoStack.length === 0 || busy) return;
    const last = undoStack[undoStack.length - 1];
    const current = placedModules.find((m) => m.instance_id === last.instanceId);
    if (current) {
      setRedoStack((r) => [
        ...r,
        { instanceId: current.instance_id, x: current.x, y: current.y, rotation: current.rotation },
      ]);
    }
    setUndoStack((u) => u.slice(0, -1));
    onMoveModule(last.instanceId, last.x, last.y, last.rotation);
  };

  const handleRedo = () => {
    if (redoStack.length === 0 || busy) return;
    const next = redoStack[redoStack.length - 1];
    const current = placedModules.find((m) => m.instance_id === next.instanceId);
    if (current) {
      setUndoStack((u) => [
        ...u,
        { instanceId: current.instance_id, x: current.x, y: current.y, rotation: current.rotation },
      ]);
    }
    setRedoStack((r) => r.slice(0, -1));
    onMoveModule(next.instanceId, next.x, next.y, next.rotation);
  };

  const handleZoomStep = (delta: number) => {
    setZoom((z) => Math.max(0.65, Math.min(1.65, Number((z + delta).toFixed(2)))));
    const cam = cameraRef.current;
    const ctrl = controlsRef.current;
    if (cam && ctrl) {
      const dir = new THREE.Vector3().subVectors(cam.position, ctrl.target);
      dir.multiplyScalar(delta > 0 ? 0.84 : 1.18);
      if (dir.length() >= 5 && dir.length() <= 42) {
        cam.position.copy(ctrl.target).add(dir);
        ctrl.update();
      }
    }
  };

  const handleOrbitStep = () => {
    const nextAngle = (cameraAngle + 90) % 360;
    setCameraAngle(nextAngle);
    const cam = cameraRef.current;
    const ctrl = controlsRef.current;
    if (cam && ctrl) {
      const offset = new THREE.Vector3().subVectors(cam.position, ctrl.target);
      offset.applyAxisAngle(new THREE.Vector3(0, 1, 0), Math.PI / 2);
      cam.position.copy(ctrl.target).add(offset);
      ctrl.update();
    }
  };

  const currentGhostCheck = activeGhostTile
    ? validateGhost(activeGhostTile.x, activeGhostTile.y, ghostRotation)
    : null;

  return (
    <div className="relative rounded-2xl border border-emerald-500/25 bg-slate-950 overflow-hidden shadow-2xl">
      {/* Top Sims-Style 3D WebGL Build Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 bg-slate-900/95 border-b border-white/10 backdrop-blur-md">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => {
              onClearBuildMode();
              setPendingPlacementTile(null);
              setToolMode("select");
            }}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
              toolMode === "select"
                ? "bg-emerald-500 text-slate-950 shadow-lg shadow-emerald-500/25"
                : "bg-white/5 text-slate-300 hover:bg-white/10"
            }`}
          >
            <MousePointer className="w-3.5 h-3.5" /> Select / Inspect
          </button>

          <button
            type="button"
            disabled={!selectedModule}
            onClick={() => setToolMode(toolMode === "move" ? "select" : "move")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-40 ${
              toolMode === "move"
                ? "bg-sky-500 text-slate-950 shadow-lg shadow-sky-500/25"
                : "bg-white/5 text-slate-300 hover:bg-white/10"
            }`}
          >
            <Move className="w-3.5 h-3.5" /> Move Module
          </button>

          <button
            type="button"
            data-testid="campus-rotate-btn"
            onClick={() => {
              const nextRot = (ghostRotation + 90) % 360;
              setGhostRotation(nextRot);
              if (selectedModule && toolMode === "select" && !busy) {
                onMoveModule(selectedModule.instance_id, selectedModule.x, selectedModule.y, nextRot);
              }
            }}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 bg-white/5 text-slate-300 hover:bg-white/10 transition"
            title="Shortcut: R"
          >
            <RotateCw className="w-3.5 h-3.5" /> Rotate ({ghostRotation}°)
          </button>

          <button
            type="button"
            onClick={() => setToolMode(toolMode === "demolish" ? "select" : "demolish")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
              toolMode === "demolish"
                ? "bg-rose-500 text-white shadow-lg shadow-rose-500/25"
                : "bg-white/5 text-slate-300 hover:bg-white/10"
            }`}
          >
            <Trash2 className="w-3.5 h-3.5" /> Bulldoze
          </button>

          <div className="h-4 w-px bg-white/10 mx-1" />

          <button
            type="button"
            disabled={undoStack.length === 0 || busy}
            onClick={handleUndo}
            className="p-1.5 rounded-lg bg-white/5 text-slate-300 hover:bg-white/10 disabled:opacity-30"
            title="Undo Move"
          >
            <Undo2 className="w-4 h-4" />
          </button>
          <button
            type="button"
            disabled={redoStack.length === 0 || busy}
            onClick={handleRedo}
            className="p-1.5 rounded-lg bg-white/5 text-slate-300 hover:bg-white/10 disabled:opacity-30"
            title="Redo Move"
          >
            <Redo2 className="w-4 h-4" />
          </button>
        </div>

        {/* Camera Presets, WebGL / 2D Fallback Switcher & Environment Controls */}
        <div className="flex flex-wrap items-center gap-1.5">
          {/* Camera Angle Presets */}
          {(
            [
              { id: "isometric", label: "3D Iso" },
              { id: "top_down", label: "Top-Down" },
              { id: "stadium_aerial", label: "Stadium" },
              { id: "academy_precinct", label: "Academy" },
              { id: "ground_level", label: "Ground" },
            ] as { id: CameraPreset; label: string }[]
          ).map((p) => (
            <button
              key={p.id}
              type="button"
              data-testid={`camera-preset-${p.id}`}
              onClick={() => applyCameraPreset(p.id)}
              className={`px-2 py-1 rounded-lg text-[11px] font-semibold transition ${
                cameraPreset === p.id && rendererMode === "webgl_3d"
                  ? "bg-amber-500/25 text-amber-300 border border-amber-500/40"
                  : "bg-white/5 text-slate-300 hover:bg-white/10"
              }`}
            >
              {p.label}
            </button>
          ))}

          <button
            type="button"
            data-testid="camera-focus-selected-btn"
            onClick={focusSelectedBuilding}
            className="px-2 py-1 rounded-lg text-[11px] font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/25 transition"
            title="Focus 3D Camera on Selected Facility or Plot"
          >
            Focus
          </button>

          <button
            type="button"
            data-testid="camera-reset-btn"
            onClick={() => applyCameraPreset("isometric")}
            className="p-1.5 rounded-lg bg-white/5 text-slate-300 hover:bg-white/10"
            title="Reset 3D Camera"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <div className="h-4 w-px bg-white/10 mx-0.5" />

          <button
            type="button"
            onClick={() => setShowGrid((g) => !g)}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1 ${
              showGrid
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                : "bg-white/5 text-slate-400"
            }`}
          >
            <Grid className="w-3.5 h-3.5" /> Grid
          </button>

          <button
            type="button"
            onClick={() => setShowZones((z) => !z)}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1 ${
              showZones
                ? "bg-purple-500/20 text-purple-300 border border-purple-500/40"
                : "bg-white/5 text-slate-400"
            }`}
          >
            <Layers className="w-3.5 h-3.5" /> Zones
          </button>

          <button
            type="button"
            onClick={handleOrbitStep}
            className="px-2.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1 bg-white/5 text-slate-300 hover:bg-white/10"
          >
            <Compass className="w-3.5 h-3.5 text-amber-400" /> Orbit {cameraAngle}°
          </button>

          <button
            type="button"
            onClick={() => handleZoomStep(0.15)}
            className="p-1.5 rounded-lg bg-white/5 text-slate-300 hover:bg-white/10"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => handleZoomStep(-0.15)}
            className="p-1.5 rounded-lg bg-white/5 text-slate-300 hover:bg-white/10"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => setNightMode((n) => !n)}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1 ${
              nightMode
                ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                : "bg-white/5 text-slate-300"
            }`}
          >
            {nightMode ? <Moon className="w-3.5 h-3.5" /> : <Sun className="w-3.5 h-3.5" />}
            {nightMode ? "Floodlights" : "Daylight"}
          </button>

          {/* Primary WebGL 3D vs 2D Canvas Fallback Switcher */}
          <button
            type="button"
            data-testid="campus-renderer-mode-toggle"
            onClick={() =>
              setRendererMode((m) => (m === "webgl_3d" ? "canvas_fallback" : "webgl_3d"))
            }
            className={`px-2.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1 border transition ${
              rendererMode === "webgl_3d"
                ? "bg-sky-500/20 text-sky-300 border-sky-500/40"
                : "bg-slate-800 text-slate-300 border-white/15"
            }`}
            title="Switch between Three.js WebGL 3D Engine (Primary) and 2D Isometric Canvas Fallback"
          >
            {rendererMode === "webgl_3d" ? (
              <>
                <Box className="w-3.5 h-3.5" /> WebGL 3D
              </>
            ) : (
              <>
                <Eye className="w-3.5 h-3.5" /> 2D Fallback
              </>
            )}
          </button>
        </div>
      </div>

      {/* Active Build / Move Mode Banner with Confirm & Discard Actions */}
      {(toolMode === "build" || toolMode === "move") && activeCatalogSpec && (
        <div className="px-4 py-2.5 bg-emerald-500/15 border-b border-emerald-500/30 flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2 text-emerald-200">
            <Hammer className="w-4 h-4 text-emerald-400 animate-bounce" />
            <span>
              <strong>{toolMode === "build" ? "3D Build Mode:" : "3D Move Mode:"}</strong>{" "}
              <span className="text-white font-bold">{activeCatalogSpec.name}</span> (
              {activeCatalogSpec.footprint_w}×{activeCatalogSpec.footprint_h} tiles ·{" "}
              {activeCatalogSpec.base_cost_gtex.toLocaleString()} GTEX).{" "}
              {currentGhostCheck && (
                <span
                  data-testid="campus-placement-validity"
                  className={
                    currentGhostCheck.valid
                      ? "text-emerald-300 font-bold"
                      : "text-rose-400 font-bold"
                  }
                >
                  [{currentGhostCheck.reason} at ({activeGhostTile?.x}, {activeGhostTile?.y})]
                </span>
              )}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            {activeGhostTile && (
              <div className="flex items-center gap-1 mr-1">
                <button
                  type="button"
                  data-testid="nudge-left-btn"
                  onClick={() =>
                    setPendingPlacementTile({
                      x: Math.max(0, activeGhostTile.x - 1),
                      y: activeGhostTile.y,
                    })
                  }
                  className="px-2 py-1 rounded bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-white/15 font-mono"
                  title="Position West (-1 X)"
                >
                  ←
                </button>
                <button
                  type="button"
                  data-testid="nudge-up-btn"
                  onClick={() =>
                    setPendingPlacementTile({
                      x: activeGhostTile.x,
                      y: Math.max(0, activeGhostTile.y - 1),
                    })
                  }
                  className="px-2 py-1 rounded bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-white/15 font-mono"
                  title="Position North (-1 Y)"
                >
                  ↑
                </button>
                <button
                  type="button"
                  data-testid="nudge-down-btn"
                  onClick={() =>
                    setPendingPlacementTile({
                      x: activeGhostTile.x,
                      y: Math.min(gridHeight - 1, activeGhostTile.y + 1),
                    })
                  }
                  className="px-2 py-1 rounded bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-white/15 font-mono"
                  title="Position South (+1 Y)"
                >
                  ↓
                </button>
                <button
                  type="button"
                  data-testid="nudge-right-btn"
                  onClick={() =>
                    setPendingPlacementTile({
                      x: Math.min(gridWidth - 1, activeGhostTile.x + 1),
                      y: activeGhostTile.y,
                    })
                  }
                  className="px-2 py-1 rounded bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-white/15 font-mono"
                  title="Position East (+1 X)"
                >
                  →
                </button>
              </div>
            )}
            {activeGhostTile && currentGhostCheck?.valid && (
              <button
                type="button"
                data-testid="confirm-placement-btn"
                onClick={() => {
                  commitBuildOrMoveAtTile(activeGhostTile.x, activeGhostTile.y);
                  updateEmptyPlot(null);
                }}
                className="px-3 py-1 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold flex items-center gap-1 shadow-lg shadow-emerald-500/20"
              >
                <Check className="w-3.5 h-3.5" /> Confirm Placement
              </button>
            )}
            <button
              type="button"
              data-testid="discard-placement-btn"
              onClick={() => {
                onClearBuildMode();
                setPendingPlacementTile(null);
                setToolMode("select");
              }}
              className="px-2.5 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-white font-semibold flex items-center gap-1"
            >
              <X className="w-3.5 h-3.5" /> Discard (ESC)
            </button>
          </div>
        </div>
      )}

      {/* Interactive 3D WebGL Viewport (or Lightweight 2D Canvas Fallback) */}
      <div className="relative w-full h-[560px] select-none">
        {rendererMode === "webgl_3d" ? (
          <div
            ref={webglMountRef}
            data-testid="campus-webgl-viewport"
            onPointerMove={handleWebGLPointerMove}
            onPointerDown={handleWebGLPointerDown}
            onPointerUp={handleWebGLPointerUp}
            onContextMenu={(e) => e.preventDefault()}
            className={`w-full h-full ${
              toolMode === "build" || toolMode === "move"
                ? "cursor-crosshair"
                : toolMode === "demolish"
                ? "cursor-not-allowed"
                : "cursor-grab active:cursor-grabbing"
            }`}
          />
        ) : (
          <canvas
            ref={fallbackCanvasRef}
            data-testid="campus-builder-canvas"
            data-engine="canvas-2d-fallback"
            onMouseMove={handleFallbackMouseMove}
            onMouseDown={handleFallbackMouseDown}
            onMouseUp={() => setIsDragging(false)}
            onMouseLeave={() => setIsDragging(false)}
            onContextMenu={(e) => e.preventDefault()}
            className="w-full h-full block cursor-grab"
          />
        )}

        {/* Bottom-Left Controls & WebGL/GLB Telemetry HUD */}
        <div className="absolute bottom-3 left-3 flex flex-wrap items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-950/90 border border-white/15 backdrop-blur-md text-[11px] text-slate-300">
          <span
            data-testid="campus-webgl-status"
            className="px-2 py-0.5 rounded bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 font-mono font-bold flex items-center gap-1"
          >
            <Cpu className="w-3 h-3" />
            {rendererMode === "webgl_3d"
              ? `Three.js WebGL (${qualityTier.toUpperCase()})`
              : "2D Canvas Inspector"}
          </span>
          <span className="text-slate-600">·</span>
          <span className="font-mono text-emerald-400 font-bold">Orbit / Pan / Zoom</span>
          <span className="text-slate-600">·</span>
          <span className="font-mono text-emerald-400 font-bold">R</span> Rotate 90°
          {hoverTile && (
            <>
              <span className="text-slate-600">·</span>
              <span data-testid="campus-hover-coords" className="text-amber-300 font-mono">
                Grid ({hoverTile.x}, {hoverTile.y})
              </span>
            </>
          )}
          {selectedEmptyPlot && (
            <>
              <span className="text-slate-600">·</span>
              <span
                data-testid="selected-empty-plot-badge"
                className="px-1.5 py-0.5 rounded bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 font-mono font-bold"
              >
                Plot ({selectedEmptyPlot.x}, {selectedEmptyPlot.y})
              </span>
            </>
          )}
          <span className="text-slate-600">·</span>
          <span data-testid="campus-glb-mesh-status" className="text-sky-300 font-mono">
            {loadedStats.meshes} GLB Models ({loadedStats.vertices.toLocaleString()} Verts ·{" "}
            {loadedStats.triangles.toLocaleString()} Tris · {loadedStats.materials} PBR Mats)
          </span>
          <span className="text-slate-600">·</span>
          <span data-testid="campus-perf-telemetry" className="text-emerald-300 font-mono">
            {perfStats.fps} FPS ({perfStats.frameMs}ms)
          </span>
        </div>

        {/* Top-Right Precinct Zone Legend & Quality Tier Pill */}
        <div className="absolute top-3 right-3 flex flex-wrap items-center gap-2 bg-slate-950/85 border border-white/10 rounded-xl px-3 py-2 text-[11px] backdrop-blur-md">
          {zones.map((z) => (
            <div key={z.zone_id} className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: z.color }} />
              <span className="text-slate-300 font-medium">{z.name.split("&")[0]}</span>
            </div>
          ))}
          <select
            aria-label="3D Render Quality Tier"
            value={qualityTier}
            onChange={(e) => setQualityTier(e.target.value as QualityTier)}
            className="ml-2 bg-slate-900 text-slate-200 border border-white/15 rounded px-1.5 py-0.5 text-[10px] font-semibold"
          >
            <option value="high">Ultra Shadows (2K)</option>
            <option value="balanced">Balanced (1K)</option>
            <option value="low">Performance (Low)</option>
          </select>
        </div>
      </div>
    </div>
  );
};
