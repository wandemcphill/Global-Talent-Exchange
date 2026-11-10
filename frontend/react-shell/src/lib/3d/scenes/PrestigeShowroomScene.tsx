/**
 * GTEX Living Football World — Stage 7 Cinema 3D & Prestige Showroom
 * PrestigeShowroomScene: Genuine Three.js WebGL 3D Turntable Studio & Object Inspector.
 *
 * Implements:
 * 1. Reflective obsidian 3D showroom turntable with concentric LED rim lighting.
 * 2. Multi-mesh 3D models for Private Jets, Hypercars/SUVs, Club Team Buses, Tourbillon Watches, and VIP Suites.
 * 3. Interactive OrbitControls rotation, zoom controls, camera angle presets, and livery customizer.
 * 4. Honest 3D WebGL vs 2D Fallback mode reporting (never falsely claiming 3D when fallback is active).
 * 5. Full WebGL resource disposal on unmount.
 */

import React, { useEffect, useRef, useState, useCallback } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GtexSceneRegistry } from "../GtexSceneRegistry";
import type { GtexSceneRendererProps } from "../GtexSceneTypes";
import { AssetStreamingCache } from "../broadcast/AssetStreamingCache";
import { StadiumEnvironmentLighting } from "../broadcast/StadiumEnvironmentLighting";

export type ShowroomCameraPreset =
  | "exterior_front"
  | "profile_side"
  | "cockpit_detail"
  | "aerial_showcase";

export type ShowroomLiveryOption =
  | "club_home"
  | "sovereign_gold"
  | "stealth_carbon"
  | "platinum_white";

export interface PrestigeShowroomSceneProps extends Partial<GtexSceneRendererProps> {
  assetName?: string;
  assetCategory?: string;
  meshArchetype?: string;
  modelName?: string;
  modelPath?: string;
  priceGtex?: number | string;
  isOwned?: boolean;
  ownedCount?: number;
  clubName?: string;
  primaryColor?: string;
  secondaryColor?: string;
  specs?: Record<string, any>;
  compact?: boolean;
}

const ARCHETYPE_GLB_PATHS: Record<string, string> = {
  private_jet: "/assets/showroom/sovereign_900x_jet.glb",
  gulfstream_jet: "/assets/showroom/sovereign_900x_jet.glb",
  club_bus: "/assets/showroom/vanguard_xii_coach.glb",
  tourbillon_watch: "/assets/showroom/chronos_tourbillon_watch.glb",
  vip_suite: "/assets/showroom/royal_penthouse_box.glb",
  luxury_suv: "/assets/showroom/executive_suv.glb",
  hypercar: "/assets/showroom/veloce_gt9_hypercar.glb",
  stadium: "/models/match/football-stadium.glb",
  campus: "/assets/showroom/apex_performance_campus.glb",
};

function resolveShowroomGlbPath(
  archetype: string,
  assetName?: string,
  modelName?: string,
  explicitPath?: string
): string {
  if (explicitPath) {
    return explicitPath.startsWith("/") ? explicitPath : `/${explicitPath}`;
  }
  const label = `${assetName || ""} ${modelName || ""}`.toLowerCase();
  if (label.includes("g700") || label.includes("gulfstream")) {
    return ARCHETYPE_GLB_PATHS.private_jet;
  }
  if (label.includes("suv") || label.includes("convoy")) {
    return ARCHETYPE_GLB_PATHS.luxury_suv;
  }
  return ARCHETYPE_GLB_PATHS[archetype] || ARCHETYPE_GLB_PATHS.hypercar;
}

const CAMERA_PRESETS: Record<
  ShowroomCameraPreset,
  { label: string; position: [number, number, number]; target: [number, number, number] }
> = {
  exterior_front: {
    label: "Hero Front",
    position: [6.5, 3.2, 8.5],
    target: [0, 1.1, 0],
  },
  profile_side: {
    label: "Side Profile",
    position: [10.5, 2.4, 0.2],
    target: [0, 1.0, 0],
  },
  cockpit_detail: {
    label: "Detail Close-Up",
    position: [3.2, 2.2, 4.0],
    target: [0, 1.2, 0.5],
  },
  aerial_showcase: {
    label: "Aerial Studio",
    position: [0.2, 9.5, 7.5],
    target: [0, 0.8, 0],
  },
};

const LIVERY_PALETTES: Record<
  ShowroomLiveryOption,
  { label: string; primaryHex: number; accentHex: number; swatch: string }
> = {
  club_home: {
    label: "Club Livery",
    primaryHex: 0x10b981,
    accentHex: 0xf59e0b,
    swatch: "#10B981",
  },
  sovereign_gold: {
    label: "Sovereign Gold",
    primaryHex: 0xd97706,
    accentHex: 0xfef08a,
    swatch: "#F59E0B",
  },
  stealth_carbon: {
    label: "Stealth Carbon",
    primaryHex: 0x1e293b,
    accentHex: 0x38bdf8,
    swatch: "#38BDF8",
  },
  platinum_white: {
    label: "Platinum Edition",
    primaryHex: 0xf1f5f9,
    accentHex: 0x6366f1,
    swatch: "#E2E8F0",
  },
};

function resolveArchetype(category?: string, meshArchetype?: string): string {
  if (meshArchetype) return meshArchetype;
  const cat = (category || "").toLowerCase();
  if (cat.includes("jet") || cat.includes("aviation")) return "private_jet";
  if (cat.includes("coach") || cat.includes("bus")) return "club_bus";
  if (cat.includes("watch") || cat.includes("horology")) return "tourbillon_watch";
  if (cat.includes("suite") || cat.includes("hospitality") || cat.includes("facility"))
    return "vip_suite";
  return "hypercar";
}

function getArchetypeGameplayUtility(archetype: string, specs?: Record<string, any>): {
  prestigeBoost: string;
  commercialPull: string;
  squadImpact: string;
} {
  if (specs?.prestige_boost || specs?.commercial_pull || specs?.squad_impact) {
    return {
      prestigeBoost: String(specs.prestige_boost || "+120 Prestige"),
      commercialPull: String(specs.commercial_pull || "+4.5% Sponsor Yield"),
      squadImpact: String(specs.squad_impact || "+3% Squad Morale"),
    };
  }
  switch (archetype) {
    case "private_jet":
    case "gulfstream_jet":
      return {
        prestigeBoost: "+350 Global Prestige",
        commercialPull: "+8% Marquee Transfer Appeal",
        squadImpact: "-18% Away Travel Fatigue",
      };
    case "club_bus":
      return {
        prestigeBoost: "+140 Club Prestige",
        commercialPull: "+3% Regional Brand Reach",
        squadImpact: "+5% Matchday Readiness",
      };
    case "tourbillon_watch":
      return {
        prestigeBoost: "+95 Executive Prestige",
        commercialPull: "+4% VIP Hospitality Appeal",
        squadImpact: "+2% Contract Renewal Goodwill",
      };
    case "vip_suite":
      return {
        prestigeBoost: "+220 Stadium Prestige",
        commercialPull: "+9% Matchday VIP Box Revenue",
        squadImpact: "+4% Board Confidence",
      };
    default:
      return {
        prestigeBoost: "+180 Sovereign Prestige",
        commercialPull: "+5% Star Signing Aura",
        squadImpact: "+3% Dressing Room Buzz",
      };
  }
}

const showroomTextureCache = new Map<string, Promise<THREE.Texture>>();

function loadShowroomTexture(url: string): Promise<THREE.Texture> {
  const cached = showroomTextureCache.get(url);
  if (cached) return cached;
  const pending = new Promise<THREE.Texture>((resolve, reject) => {
    new THREE.TextureLoader().load(
      url,
      (texture) => {
        texture.colorSpace = url.includes("normal") ? THREE.LinearSRGBColorSpace : THREE.SRGBColorSpace;
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
        resolve(texture);
      },
      undefined,
      reject
    );
  });
  showroomTextureCache.set(url, pending);
  return pending;
}

function projectBoxUvs(geometry: THREE.BufferGeometry): void {
  const position = geometry.getAttribute("position");
  const normal = geometry.getAttribute("normal");
  if (!position || geometry.getAttribute("uv")) return;
  geometry.computeBoundingBox();
  const box = geometry.boundingBox;
  if (!box) return;
  const size = new THREE.Vector3();
  box.getSize(size);
  const uvs = new Float32Array(position.count * 2);
  for (let i = 0; i < position.count; i++) {
    const x = (position.getX(i) - box.min.x) / Math.max(size.x, 0.001);
    const y = (position.getY(i) - box.min.y) / Math.max(size.y, 0.001);
    const z = (position.getZ(i) - box.min.z) / Math.max(size.z, 0.001);
    const nx = normal ? Math.abs(normal.getX(i)) : 0;
    const ny = normal ? Math.abs(normal.getY(i)) : 1;
    const nz = normal ? Math.abs(normal.getZ(i)) : 0;
    if (ny >= nx && ny >= nz) {
      uvs[i * 2] = x;
      uvs[i * 2 + 1] = z;
    } else if (nx >= nz) {
      uvs[i * 2] = z;
      uvs[i * 2 + 1] = y;
    } else {
      uvs[i * 2] = x;
      uvs[i * 2 + 1] = y;
    }
  }
  geometry.setAttribute("uv", new THREE.BufferAttribute(uvs, 2));
}

async function dressShowroomMaterials(root: THREE.Object3D): Promise<void> {
  const [metalColor, metalRough, metalMetal, metalNormal, concreteColor, concreteRough, asphaltColor, asphaltRough] =
    await Promise.all([
      loadShowroomTexture("/textures/showroom/metal_diffuse.jpg"),
      loadShowroomTexture("/textures/showroom/metal_rough.jpg"),
      loadShowroomTexture("/textures/showroom/metal_metal.jpg"),
      loadShowroomTexture("/textures/showroom/metal_normal.jpg"),
      loadShowroomTexture("/textures/showroom/concrete_diffuse.jpg"),
      loadShowroomTexture("/textures/showroom/concrete_rough.jpg"),
      loadShowroomTexture("/textures/showroom/asphalt_diffuse.jpg"),
      loadShowroomTexture("/textures/showroom/asphalt_rough.jpg"),
    ]);
  root.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (!mesh.isMesh) return;
    if (mesh.geometry && !mesh.geometry.getAttribute("uv")) projectBoxUvs(mesh.geometry);
    const list = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    list.forEach((material) => {
      const standard = material as THREE.MeshStandardMaterial;
      if (!standard || !standard.isMeshStandardMaterial || standard.map) return;
      const name = `${standard.name} ${mesh.name}`.toLowerCase();
      if (name.includes("glass") || name.includes("window")) {
        standard.roughness = 0.08;
        standard.metalness = 0.15;
        standard.envMapIntensity = 1.4;
        return;
      }
      const ground = name.includes("grass") || name.includes("ground") || name.includes("road") || name.includes("tire") || name.includes("rubber");
      const stone = name.includes("concrete") || name.includes("campus") || name.includes("wall") || name.includes("building");
      standard.map = ground ? asphaltColor : stone ? concreteColor : metalColor;
      standard.roughnessMap = ground ? asphaltRough : stone ? concreteRough : metalRough;
      if (!ground && !stone) {
        standard.metalnessMap = metalMetal;
        standard.normalMap = metalNormal;
        standard.metalness = 0.85;
      } else {
        standard.metalness = 0.04;
      }
      standard.roughness = ground ? 0.86 : 0.45;
      standard.needsUpdate = true;
    });
  });
}

function buildProceduralAssetMesh(
  archetype: string,
  primaryHex: number,
  accentHex: number
): THREE.Group {
  const group = new THREE.Group();
  group.name = "prestigeAssetRoot";

  const bodyMat = new THREE.MeshStandardMaterial({
    color: primaryHex,
    metalness: 0.72,
    roughness: 0.22,
  });
  const accentMat = new THREE.MeshStandardMaterial({
    color: accentHex,
    metalness: 0.85,
    roughness: 0.18,
  });
  const glassMat = new THREE.MeshStandardMaterial({
    color: 0x0f172a,
    metalness: 0.9,
    roughness: 0.1,
    transparent: true,
    opacity: 0.82,
  });
  const darkMetalMat = new THREE.MeshStandardMaterial({
    color: 0x111827,
    metalness: 0.6,
    roughness: 0.4,
  });

  if (archetype === "private_jet") {
    // Fuselage
    const fuselageGeo = new THREE.CylinderGeometry(0.62, 0.58, 6.6, 24);
    fuselageGeo.rotateZ(Math.PI / 2);
    const fuselage = new THREE.Mesh(fuselageGeo, bodyMat);
    fuselage.position.y = 1.45;
    group.add(fuselage);

    // Livery stripe
    const stripeGeo = new THREE.BoxGeometry(6.65, 0.12, 1.26);
    const stripe = new THREE.Mesh(stripeGeo, accentMat);
    stripe.position.y = 1.45;
    group.add(stripe);

    // Swept Wings
    const wingGeo = new THREE.BoxGeometry(1.8, 0.1, 6.8);
    const wings = new THREE.Mesh(wingGeo, bodyMat);
    wings.position.set(-0.2, 1.25, 0);
    group.add(wings);

    // T-Tail Fin
    const tailFinGeo = new THREE.BoxGeometry(1.1, 1.5, 0.12);
    const tailFin = new THREE.Mesh(tailFinGeo, accentMat);
    tailFin.position.set(-2.8, 2.3, 0);
    group.add(tailFin);

    // Twin Engine Nacelles
    for (const zSide of [-1.05, 1.05]) {
      const engGeo = new THREE.CylinderGeometry(0.26, 0.24, 1.3, 16);
      engGeo.rotateZ(Math.PI / 2);
      const eng = new THREE.Mesh(engGeo, darkMetalMat);
      eng.position.set(-1.9, 1.55, zSide);
      group.add(eng);
    }
  } else if (archetype === "club_bus") {
    // Double-decker touring coach chassis
    const coachBody = new THREE.Mesh(new THREE.BoxGeometry(5.6, 1.85, 2.1), bodyMat);
    coachBody.position.y = 1.35;
    group.add(coachBody);

    // Panoramic upper glass band
    const glassBand = new THREE.Mesh(new THREE.BoxGeometry(5.4, 0.65, 2.14), glassMat);
    glassBand.position.y = 1.75;
    group.add(glassBand);

    // Club accent stripe
    const beltStripe = new THREE.Mesh(new THREE.BoxGeometry(5.64, 0.16, 2.14), accentMat);
    beltStripe.position.y = 1.15;
    group.add(beltStripe);

    // 6 Coach Wheels
    for (const wx of [-1.8, 0.9, 1.85]) {
      for (const wz of [-1.05, 1.05]) {
        const wheelGeo = new THREE.CylinderGeometry(0.42, 0.42, 0.24, 18);
        wheelGeo.rotateX(Math.PI / 2);
        const wheel = new THREE.Mesh(wheelGeo, darkMetalMat);
        wheel.position.set(wx, 0.42, wz);
        group.add(wheel);
      }
    }
  } else if (archetype === "tourbillon_watch") {
    // Outer watch case
    const caseGeo = new THREE.CylinderGeometry(2.1, 2.1, 0.45, 36);
    caseGeo.rotateX(Math.PI / 4);
    const watchCase = new THREE.Mesh(caseGeo, accentMat);
    watchCase.position.y = 1.85;
    group.add(watchCase);

    // Sapphire dial face
    const dialGeo = new THREE.CylinderGeometry(1.75, 1.75, 0.48, 36);
    dialGeo.rotateX(Math.PI / 4);
    const dial = new THREE.Mesh(dialGeo, bodyMat);
    dial.position.y = 1.85;
    group.add(dial);

    // Tourbillon cage ring
    const cageGeo = new THREE.TorusGeometry(0.55, 0.08, 12, 24);
    cageGeo.rotateX(-Math.PI / 4);
    const cage = new THREE.Mesh(cageGeo, accentMat);
    cage.position.set(0, 1.6, 0.4);
    cage.name = "tourbillonCage";
    group.add(cage);
  } else if (archetype === "vip_suite") {
    // Architectural Skybox Suite podium
    const suiteBase = new THREE.Mesh(new THREE.BoxGeometry(4.6, 1.6, 3.4), bodyMat);
    suiteBase.position.y = 1.0;
    group.add(suiteBase);

    const atriumGlass = new THREE.Mesh(new THREE.BoxGeometry(4.4, 1.2, 3.45), glassMat);
    atriumGlass.position.y = 1.15;
    group.add(atriumGlass);

    const roofTruss = new THREE.Mesh(new THREE.BoxGeometry(5.0, 0.2, 3.8), accentMat);
    roofTruss.position.y = 1.9;
    group.add(roofTruss);
  } else {
    // Hypercar / Luxury SUV
    const chassis = new THREE.Mesh(new THREE.BoxGeometry(4.4, 0.68, 2.0), bodyMat);
    chassis.position.y = 0.72;
    group.add(chassis);

    const cabin = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.56, 1.65), glassMat);
    cabin.position.set(-0.15, 1.25, 0);
    group.add(cabin);

    const spoiler = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.1, 1.95), accentMat);
    spoiler.position.set(-2.0, 1.22, 0);
    group.add(spoiler);

    for (const wx of [-1.35, 1.35]) {
      for (const wz of [-1.02, 1.02]) {
        const wheelGeo = new THREE.CylinderGeometry(0.38, 0.38, 0.26, 20);
        wheelGeo.rotateX(Math.PI / 2);
        const wheel = new THREE.Mesh(wheelGeo, darkMetalMat);
        wheel.position.set(wx, 0.38, wz);
        group.add(wheel);
      }
    }
  }

  return group;
}

export const PrestigeShowroomScene: React.FC<PrestigeShowroomSceneProps> = ({
  assetName = "GTEX Sovereign 900X Private Jet",
  assetCategory = "jet",
  meshArchetype,
  modelName = "Flagship Edition",
  modelPath,
  priceGtex,
  isOwned = false,
  ownedCount = 0,
  clubName = "GTEX FC",
  specs,
  compact = false,
  activeQuality,
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const [activePreset, setActivePreset] = useState<ShowroomCameraPreset>("exterior_front");
  const [activeLivery, setActiveLivery] = useState<ShowroomLiveryOption>("club_home");
  const [autoRotate, setAutoRotate] = useState<boolean>(true);
  const [webglActive, setWebglActive] = useState<boolean>(true);

  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const cameraGoalPosRef = useRef<THREE.Vector3>(
    new THREE.Vector3(...CAMERA_PRESETS.exterior_front.position)
  );
  const cameraGoalTargetRef = useRef<THREE.Vector3>(
    new THREE.Vector3(...CAMERA_PRESETS.exterior_front.target)
  );
  const isTransitioningRef = useRef<boolean>(false);

  const resolvedArchetype = resolveArchetype(assetCategory, meshArchetype);
  const gameplayUtility = getArchetypeGameplayUtility(resolvedArchetype, specs);
  const resolvedGlbUrl = resolveShowroomGlbPath(
    resolvedArchetype,
    assetName,
    modelName,
    modelPath
  );

  const handleSelectCameraPreset = useCallback((preset: ShowroomCameraPreset) => {
    setActivePreset(preset);
    const cfg = CAMERA_PRESETS[preset];
    cameraGoalPosRef.current.set(...cfg.position);
    cameraGoalTargetRef.current.set(...cfg.target);
    isTransitioningRef.current = true;
  }, []);

  const handleZoom = useCallback((factor: number) => {
    if (!cameraRef.current) return;
    cameraRef.current.position.multiplyScalar(factor);
    cameraGoalPosRef.current.copy(cameraRef.current.position);
  }, []);

  const handleCaptureSnapshot = useCallback(() => {
    const canvas = mountRef.current?.querySelector("canvas");
    if (!canvas) return;
    try {
      const url = canvas.toDataURL("image/png");
      const a = document.createElement("a");
      a.href = url;
      a.download = `GTEX_Showroom_${(assetName || "asset").replace(/\s+/g, "_")}.png`;
      a.click();
    } catch {
      // test environment without real canvas rendering
    }
  }, [assetName]);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: activeQuality?.antialias ?? true,
        powerPreference: "high-performance",
        preserveDrawingBuffer: true,
      });
      setWebglActive(true);
    } catch {
      setWebglActive(false);
      return;
    }

    const width = Math.max(280, container.clientWidth || 640);
    const height = Math.max(220, container.clientHeight || (compact ? 260 : 380));
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, activeQuality?.pixelRatio || 1.5));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;

    container.innerHTML = "";
    renderer.domElement.setAttribute("data-testid", "prestige-showroom-3d-canvas");
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.display = "block";
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x060b16);

    const camera = new THREE.PerspectiveCamera(38, width / height, 0.3, 120);
    camera.position.copy(cameraGoalPosRef.current);
    cameraRef.current = camera;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 2.5;
    controls.maxDistance = 22;
    controls.target.copy(cameraGoalTargetRef.current);
    controlsRef.current = controls;

    // 3-Point Studio Lighting Rig
    const ambient = new THREE.HemisphereLight(0xe0f2fe, 0x0f172a, 0.9);
    scene.add(ambient);

    const keyLight = new THREE.DirectionalLight(0xffffff, 2.1);
    keyLight.position.set(8, 14, 10);
    scene.add(keyLight);

    const rimLight = new THREE.PointLight(0x38bdf8, 1.6, 22);
    rimLight.position.set(-7, 6, -8);
    scene.add(rimLight);
    const showroomLighting = new StadiumEnvironmentLighting(renderer, scene, "high");
    if (typeof navigator === "undefined" || !/jsdom/i.test(navigator.userAgent || "")) {
      void showroomLighting.loadPolyHaven();
    }

    // Obsidian Turntable Pedestal & Glowing Ring
    const turntableGroup = new THREE.Group();
    const pedestalGeo = new THREE.CylinderGeometry(4.2, 4.5, 0.24, 48);
    const pedestalMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      metalness: 0.75,
      roughness: 0.2,
    });
    const pedestal = new THREE.Mesh(pedestalGeo, pedestalMat);
    pedestal.position.y = 0.12;
    turntableGroup.add(pedestal);

    const palette = LIVERY_PALETTES[activeLivery];
    const ringGeo = new THREE.RingGeometry(4.05, 4.22, 48);
    const ringMat = new THREE.MeshBasicMaterial({
      color: palette.accentHex,
      side: THREE.DoubleSide,
    });
    const ledRing = new THREE.Mesh(ringGeo, ringMat);
    ledRing.rotation.x = -Math.PI / 2;
    ledRing.position.y = 0.25;
    turntableGroup.add(ledRing);

    let activeAssetRoot: THREE.Object3D = buildProceduralAssetMesh(
      resolvedArchetype,
      palette.primaryHex,
      palette.accentHex
    );
    turntableGroup.add(activeAssetRoot);
    scene.add(turntableGroup);

    let cancelled = false;
    const isJsdomTest =
      typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent || "");

    if (!isJsdomTest && typeof fetch === "function" && resolvedGlbUrl) {
      AssetStreamingCache.getInstance()
        .loadGltf(resolvedGlbUrl, renderer)
        .then((gltf) => {
          if (cancelled || !gltf?.scene) return;
          const glbRoot = gltf.scene.clone(true);
          const box = new THREE.Box3().setFromObject(glbRoot);
          const size = new THREE.Vector3();
          const center = new THREE.Vector3();
          box.getSize(size);
          box.getCenter(center);
          const maxDim = Math.max(size.x, size.y, size.z);
          if (maxDim > 0.0001) {
            const targetSpan = resolvedArchetype === "tourbillon_watch" ? 3.4 : 5.4;
            const scale = targetSpan / maxDim;
            glbRoot.scale.multiplyScalar(scale);
            const scaledBox = new THREE.Box3().setFromObject(glbRoot);
            const scaledCenter = new THREE.Vector3();
            scaledBox.getCenter(scaledCenter);
            glbRoot.position.x -= scaledCenter.x;
            glbRoot.position.z -= scaledCenter.z;
            glbRoot.position.y += 0.28 - scaledBox.min.y;
          }
          glbRoot.name = "prestigeAssetGlbRoot";
          void dressShowroomMaterials(glbRoot);
          turntableGroup.remove(activeAssetRoot);
          activeAssetRoot = glbRoot;
          turntableGroup.add(glbRoot);
        })
        .catch(() => {
          // Keep procedural fallback mesh when GLB fetch fails offline
        });
    }

    const handleContextLost = (e: Event) => {
      e.preventDefault();
      setWebglActive(false);
    };
    const handleContextRestored = () => {
      setWebglActive(true);
    };
    renderer.domElement.addEventListener("webglcontextlost", handleContextLost, false);
    renderer.domElement.addEventListener("webglcontextrestored", handleContextRestored, false);

    let animId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);
      if (typeof document !== "undefined" && document.hidden) return;
      const dt = clock.getDelta();

      if (autoRotate) {
        turntableGroup.rotation.y += dt * 0.45;
      }

      if (isTransitioningRef.current) {
        camera.position.lerp(cameraGoalPosRef.current, dt * 4.0);
        controls.target.lerp(cameraGoalTargetRef.current, dt * 4.0);
        if (camera.position.distanceTo(cameraGoalPosRef.current) < 0.08) {
          isTransitioningRef.current = false;
        }
      }

      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelled = true;
      showroomLighting.dispose();
      cancelAnimationFrame(animId);
      renderer.domElement.removeEventListener("webglcontextlost", handleContextLost);
      renderer.domElement.removeEventListener("webglcontextrestored", handleContextRestored);
      controls.dispose();
      scene.traverse((obj) => {
        const mesh = obj as THREE.Mesh;
        if (mesh.geometry) mesh.geometry.dispose();
        const mats = Array.isArray(mesh.material)
          ? mesh.material
          : mesh.material
          ? [mesh.material]
          : [];
        mats.forEach((m) => m.dispose());
      });
      renderer.dispose();
      scene.clear();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [activeQuality, activeLivery, autoRotate, compact, resolvedArchetype, resolvedGlbUrl]);

  return (
    <div
      data-testid="prestige-showroom-3d-scene"
      className={`relative w-full overflow-hidden rounded-2xl border border-amber-400/30 bg-slate-950 ${
        compact ? "h-64" : "h-80"
      }`}
    >
      {/* 3D WebGL Mount */}
      <div ref={mountRef} className="h-full w-full" />

      {/* Honest Fallback Presentation when WebGL context cannot be created */}
      {!webglActive && (
        <div
          data-testid="prestige-showroom-2d-fallback"
          className="absolute inset-0 flex flex-col items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-amber-950/30 p-6 text-center"
        >
          <div className="rounded-full border border-amber-400/40 bg-amber-400/10 px-3 py-1 text-[10px] font-black uppercase tracking-wider text-amber-300">
            2D Showroom Blueprint Fallback • {resolvedArchetype.replace("_", " ").toUpperCase()}
          </div>
          <h4 className="mt-2 text-lg font-black text-white">{assetName}</h4>
          <p className="mt-1 text-xs text-slate-300">
            {clubName} • {modelName} • {LIVERY_PALETTES[activeLivery].label}
          </p>
        </div>
      )}

      {/* Top HUD Overlay */}
      <div className="pointer-events-none absolute inset-x-0 top-0 z-20 flex items-center justify-between p-3">
        <div className="flex items-center gap-2">
          <span
            data-testid="showroom-render-mode-badge"
            className={`rounded-lg px-2.5 py-1 text-[10px] font-black uppercase tracking-wider backdrop-blur-md ${
              webglActive
                ? "border border-emerald-400/40 bg-emerald-500/20 text-emerald-300"
                : "border border-amber-400/40 bg-amber-500/20 text-amber-300"
            }`}
          >
            {webglActive ? "3D WEBGL TURNTABLE" : "2D FALLBACK MODE"}
          </span>

          <span
            data-testid="showroom-ownership-badge"
            className={`rounded-lg px-2.5 py-1 text-[10px] font-bold uppercase backdrop-blur-md ${
              isOwned
                ? "border border-amber-400/50 bg-amber-400/20 text-amber-200"
                : "border border-white/10 bg-slate-900/80 text-slate-300"
            }`}
          >
            {isOwned ? `Verified Owned (${ownedCount || 1})` : "Catalog Inspection"}
          </span>
          {isOwned && (
            <span
              data-testid="showroom-perk-active-badge"
              className="rounded-lg border border-emerald-400/40 bg-emerald-500/20 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-emerald-300 backdrop-blur-md"
            >
              Perk Yield Active
            </span>
          )}
          {priceGtex !== undefined && (
            <span className="rounded-lg border border-amber-400/30 bg-slate-950/80 px-2.5 py-1 font-mono text-[10px] font-bold text-amber-300 backdrop-blur-md">
              {typeof priceGtex === "number" ? priceGtex.toLocaleString() : priceGtex} GTEX
            </span>
          )}
        </div>

        {/* Zoom, Snapshot & Turntable Spin Controls */}
        <div className="pointer-events-auto flex items-center gap-1.5">
          <button
            type="button"
            data-testid="capture-showroom-snapshot-btn"
            onClick={handleCaptureSnapshot}
            className="rounded-lg border border-amber-400/30 bg-slate-950/80 px-2.5 py-1 text-[10px] font-bold text-amber-300 hover:bg-white/10 transition-colors"
            title="Capture 3D Frame Snapshot"
          >
            Snapshot
          </button>
          <button
            type="button"
            data-testid="toggle-turntable-rotation-btn"
            onClick={() => setAutoRotate((r) => !r)}
            className="rounded-lg border border-white/15 bg-slate-950/80 px-2.5 py-1 text-[10px] font-bold text-slate-200 hover:bg-white/10"
          >
            {autoRotate ? "Pause Spin" : "Auto Spin"}
          </button>
          <button
            type="button"
            data-testid="turntable-zoom-in-btn"
            onClick={() => handleZoom(0.85)}
            className="rounded-lg border border-white/15 bg-slate-950/80 px-2 py-1 text-[10px] font-bold text-slate-200 hover:bg-white/10"
          >
            Zoom +
          </button>
          <button
            type="button"
            data-testid="turntable-zoom-out-btn"
            onClick={() => handleZoom(1.18)}
            className="rounded-lg border border-white/15 bg-slate-950/80 px-2 py-1 text-[10px] font-bold text-slate-200 hover:bg-white/10"
          >
            Zoom -
          </button>
        </div>
      </div>

      {/* Gameplay Utility & Club Modifier Strip */}
      <div
        data-testid="showroom-gameplay-utility-bar"
        className="pointer-events-none absolute left-3 top-12 z-20 flex flex-wrap items-center gap-1.5"
      >
        <span className="rounded-md border border-amber-400/30 bg-slate-950/80 px-2 py-0.5 text-[10px] font-semibold text-amber-200 backdrop-blur-md">
          {gameplayUtility.prestigeBoost}
        </span>
        <span className="rounded-md border border-cyan-400/30 bg-slate-950/80 px-2 py-0.5 text-[10px] font-semibold text-cyan-200 backdrop-blur-md">
          {gameplayUtility.commercialPull}
        </span>
        <span className="rounded-md border border-emerald-400/30 bg-slate-950/80 px-2 py-0.5 text-[10px] font-semibold text-emerald-200 backdrop-blur-md">
          {gameplayUtility.squadImpact}
        </span>
      </div>

      {/* Bottom Camera Presets & Livery Customizer Bar */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 z-20 flex flex-wrap items-center justify-between gap-2 bg-gradient-to-t from-slate-950 via-slate-950/85 to-transparent p-3">
        {/* Camera Angle Presets */}
        <div className="pointer-events-auto flex items-center gap-1">
          {(Object.keys(CAMERA_PRESETS) as ShowroomCameraPreset[]).map((preset) => (
            <button
              key={preset}
              type="button"
              data-testid={`showroom-camera-${preset}`}
              onClick={() => handleSelectCameraPreset(preset)}
              className={`rounded-lg px-2 py-1 text-[10px] font-bold transition-all ${
                activePreset === preset
                  ? "bg-amber-400 text-slate-950"
                  : "bg-slate-900/80 text-slate-300 hover:text-white"
              }`}
            >
              {CAMERA_PRESETS[preset].label}
            </button>
          ))}
        </div>

        {/* Livery Customizer */}
        <div className="pointer-events-auto flex items-center gap-1">
          {(Object.keys(LIVERY_PALETTES) as ShowroomLiveryOption[]).map((liv) => (
            <button
              key={liv}
              type="button"
              data-testid={`showroom-livery-${liv}`}
              onClick={() => setActiveLivery(liv)}
              className={`flex items-center gap-1 rounded-lg border px-2 py-1 text-[10px] font-bold transition-all ${
                activeLivery === liv
                  ? "border-amber-400 bg-amber-400/20 text-white"
                  : "border-white/10 bg-slate-900/80 text-slate-400 hover:text-white"
              }`}
            >
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  backgroundColor: LIVERY_PALETTES[liv].swatch,
                  display: "inline-block",
                }}
              />
              <span>{LIVERY_PALETTES[liv].label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

GtexSceneRegistry.registerRenderer("luxury_inspection_turntable", PrestigeShowroomScene);
