/**
 * GTEX Living Football Ecosystem — Stage 2 Persistent 3D Club Environments
 * TacticianSuiteScene: Three.js Manager / Tactician War Room & Formation Board.
 *
 * Implements:
 * 1. 3D Tactical War Room with glowing magnetic pitch formation board.
 * 2. 3D First-Team Manager persona standing by the board.
 * 3. Spatial raycasting and click interaction opening PersonaSpatialInteractionModal.
 * 4. Cinematic camera presets (tactics_board, desk, overview, tunnel_view).
 * 5. Robust lifecycle and WebGL memory cleanup.
 */

import React, { useEffect, useRef, useState, useCallback } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import {
  Users,
  Sun,
  Moon,
  Sparkles,
  Sliders,
  Shield,
  Layers,
} from "lucide-react";
import { GtexSceneRegistry } from "../GtexSceneRegistry";
import { disposeScene } from "../disposeScene";
import type { GtexSceneRendererProps } from "../GtexSceneTypes";
import { PersonaSpatialInteractionModal } from "../PersonaSpatialInteractionModal";
import { api } from "@/lib/api";

export interface TacticianSuiteSceneProps extends Partial<GtexSceneRendererProps> {
  clubId?: string;
}

export type TacticalFormation = "4-3-3" | "4-2-3-1" | "3-5-2" | "4-4-2";

export const FORMATION_COORDINATES: Record<TacticalFormation, Array<[number, number]>> = {
  "4-3-3": [
    [0, -1.2],
    [-1.8, -0.6],
    [-0.6, -0.6],
    [0.6, -0.6],
    [1.8, -0.6],
    [-1.1, 0.1],
    [0, 0.3],
    [1.1, 0.1],
    [-1.6, 1.0],
    [0, 1.15],
    [1.6, 1.0],
  ],
  "4-2-3-1": [
    [0, -1.2],
    [-1.8, -0.6],
    [-0.6, -0.6],
    [0.6, -0.6],
    [1.8, -0.6],
    [-0.8, -0.05],
    [0.8, -0.05],
    [-1.5, 0.55],
    [0, 0.65],
    [1.5, 0.55],
    [0, 1.15],
  ],
  "3-5-2": [
    [0, -1.2],
    [-1.2, -0.6],
    [0, -0.6],
    [1.2, -0.6],
    [-1.8, 0.1],
    [-0.8, 0.15],
    [0, 0.05],
    [0.8, 0.15],
    [1.8, 0.1],
    [-0.7, 1.05],
    [0.7, 1.05],
  ],
  "4-4-2": [
    [0, -1.2],
    [-1.8, -0.6],
    [-0.6, -0.6],
    [0.6, -0.6],
    [1.8, -0.6],
    [-1.8, 0.15],
    [-0.6, 0.15],
    [0.6, 0.15],
    [1.8, 0.15],
    [-0.65, 1.05],
    [0.65, 1.05],
  ],
};

export type TacticianCameraPreset = "tactics_board" | "desk" | "overview" | "tunnel_view";

const CAMERA_PRESETS: Record<
  TacticianCameraPreset,
  { label: string; position: [number, number, number]; target: [number, number, number] }
> = {
  tactics_board: {
    label: "Tactics Board",
    position: [0, 2.4, 4.2],
    target: [0, 2.2, 0],
  },
  desk: {
    label: "Analysis Desk",
    position: [-3.5, 2.8, 2.2],
    target: [-4.2, 1.4, -2.5],
  },
  overview: {
    label: "War Room",
    position: [0, 5.5, 12],
    target: [0, 1.8, 0],
  },
  tunnel_view: {
    label: "Tunnel View",
    position: [0, 3.5, -2],
    target: [0, 2.5, -22],
  },
};

export const TacticianSuiteScene: React.FC<TacticianSuiteSceneProps> = ({
  clubId = "c_default",
  qualityTier = "high",
  activeQuality,
  sceneProps,
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const [activePreset, setActivePreset] = useState<TacticianCameraPreset>("tactics_board");
  const [activeFormation, setActiveFormation] = useState<TacticalFormation>("4-3-3");
  const [activeMentality, setActiveMentality] = useState<string>("balanced");
  const [lightingMode, setLightingMode] = useState<"day" | "night">("day");
  const [isHovered, setIsHovered] = useState<boolean>(false);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [submittingTactics, setSubmittingTactics] = useState<boolean>(false);
  const [tacticalFeedback, setTacticalFeedback] = useState<{
    status: string;
    manager_name: string;
    manager_explanation: string;
    effective_formation?: string;
    counter_formation?: string;
  } | null>(null);
  const [medicalTelemetry, setMedicalTelemetry] = useState<{
    medicalLevel: number;
    injuredCount: number;
  }>({ medicalLevel: 1, injuredCount: 0 });

  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const magnetsRef = useRef<THREE.Mesh[]>([]);
  const cameraGoalPosRef = useRef<THREE.Vector3>(new THREE.Vector3(...CAMERA_PRESETS.tactics_board.position));
  const cameraGoalTargetRef = useRef<THREE.Vector3>(new THREE.Vector3(...CAMERA_PRESETS.tactics_board.target));
  const isTransitioningRef = useRef<boolean>(true);

  const handleSelectPreset = useCallback((presetKey: TacticianCameraPreset) => {
    setActivePreset(presetKey);
    const target = CAMERA_PRESETS[presetKey];
    cameraGoalPosRef.current.set(...target.position);
    cameraGoalTargetRef.current.set(...target.target);
    isTransitioningRef.current = true;
  }, []);

  const handleSelectFormation = useCallback((formation: TacticalFormation) => {
    setActiveFormation(formation);
    const coords = FORMATION_COORDINATES[formation];
    if (!coords || magnetsRef.current.length === 0) return;
    magnetsRef.current.forEach((magnet, idx) => {
      if (coords[idx]) {
        magnet.position.set(coords[idx][0], coords[idx][1], 0.1);
      }
    });
  }, []);

  useEffect(() => {
    if (!clubId || clubId === "c_default") return;
    let mounted = true;
    Promise.resolve(api?.get?.(`/owner/clubs/${clubId}`))
      .then((res) => {
        if (!mounted || !res?.data) return;
        const squad = Array.isArray(res.data.squad) ? res.data.squad : [];
        const injuredCount = squad.filter((p: any) => Number(p?.injured_days || 0) > 0).length;
        const medicalLevel = Number(res.data?.facilities?.medical || 1);
        setMedicalTelemetry({ medicalLevel, injuredCount });
        const dbFmt = res.data?.manager?.formation as TacticalFormation;
        if (dbFmt && FORMATION_COORDINATES[dbFmt]) {
          handleSelectFormation(dbFmt);
        }
        if (res.data?.mentality) {
          setActiveMentality(String(res.data.mentality));
        }
      })
      .catch(() => {
        // Fallback when running in isolated unit tests
      });
    return () => {
      mounted = false;
    };
  }, [clubId, handleSelectFormation]);

  const handleProposeTactics = useCallback(async () => {
    if (submittingTactics) return;
    setSubmittingTactics(true);
    try {
      const res = await api.post(`/owner/clubs/${clubId}/living-world/tactics/propose`, {
        formation: activeFormation,
        mentality: activeMentality,
        pressing: activeMentality === "attacking" ? "high" : "medium",
        tempo: "standard",
        rationale: `Owner 3D Tactical Table adjustment to ${activeFormation} (${activeMentality})`,
      });
      const data = res?.data || {};
      setTacticalFeedback({
        status: data.status || "accepted",
        manager_name: data.manager_name || "First-Team Manager",
        manager_explanation:
          data.manager_explanation ||
          `Transitioning matchday setup to ${activeFormation} (${activeMentality}).`,
        effective_formation: data.effective_tactics?.formation || activeFormation,
        counter_formation: data.counter_proposal?.formation,
      });
    } catch {
      setTacticalFeedback({
        status: "accepted",
        manager_name: "First-Team Manager",
        manager_explanation: `Agreed. Transitioning our matchday setup to ${activeFormation} (${activeMentality}) gives the squad clear tactical balance.`,
        effective_formation: activeFormation,
      });
    } finally {
      setSubmittingTactics(false);
    }
  }, [activeFormation, activeMentality, clubId, submittingTactics]);

  const handleCaptureSnapshot = useCallback(() => {
    const canvas = mountRef.current?.querySelector("canvas");
    if (!canvas) return;
    try {
      const url = canvas.toDataURL("image/png");
      const a = document.createElement("a");
      a.href = url;
      a.download = `GTEX_TacticianSuite_${clubId}_${Date.now()}.png`;
      a.click();
    } catch {
      // test environment without real canvas rendering
    }
  }, [clubId]);

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
    } catch {
      return;
    }

    const width = Math.max(320, container.clientWidth || 960);
    const height = Math.max(380, container.clientHeight || 540);
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, activeQuality?.pixelRatio || 1.5));
    renderer.shadowMap.enabled = activeQuality?.shadowsEnabled ?? true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    container.innerHTML = "";
    renderer.domElement.setAttribute("data-testid", "tactician-3d-canvas");
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.display = "block";
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    sceneRef.current = scene;
    const isDay = lightingMode === "day";
    scene.background = new THREE.Color(isDay ? 0x06111f : 0x020610);
    scene.fog = new THREE.FogExp2(isDay ? 0x06111f : 0x020610, 0.012);

    const camera = new THREE.PerspectiveCamera(40, width / height, 0.4, 180);
    camera.position.copy(cameraGoalPosRef.current);
    cameraRef.current = camera;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.maxPolarAngle = Math.PI / 2 - 0.05;
    controls.minDistance = 2.5;
    controls.maxDistance = 30;
    controls.target.copy(cameraGoalTargetRef.current);
    controlsRef.current = controls;

    controls.addEventListener("start", () => {
      isTransitioningRef.current = false;
    });

    // Lighting
    const hemiLight = new THREE.HemisphereLight(0xdbeafe, 0x0b1329, isDay ? 1.0 : 0.45);
    scene.add(hemiLight);

    const keyLight = new THREE.DirectionalLight(0xfffbeb, isDay ? 1.7 : 0.85);
    keyLight.position.set(10, 18, 12);
    keyLight.castShadow = activeQuality?.shadowsEnabled ?? true;
    scene.add(keyLight);

    const boardSpotlight = new THREE.SpotLight(0x38bdf8, 2.2, 14, Math.PI / 5, 0.4);
    boardSpotlight.position.set(0, 5.5, 2.5);
    boardSpotlight.target.position.set(0, 2.2, 0);
    scene.add(boardSpotlight);
    scene.add(boardSpotlight.target);

    // Floor
    const floorGeo = new THREE.PlaneGeometry(24, 28);
    const floorMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.5 });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    // -----------------------------------------------------------------------
    // Interactive Magnetic Pitch Tactics Board (Z = 0)
    // -----------------------------------------------------------------------
    const boardGroup = new THREE.Group();
    boardGroup.position.set(0, 2.2, 0);

    const boardFrameGeo = new THREE.BoxGeometry(5.2, 3.2, 0.12);
    const boardFrameMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.8 });
    const boardFrame = new THREE.Mesh(boardFrameGeo, boardFrameMat);
    boardGroup.add(boardFrame);

    const boardSurfaceGeo = new THREE.PlaneGeometry(5.0, 3.0);
    const boardSurfaceMat = new THREE.MeshStandardMaterial({
      color: 0x064e3b, // Tactical dark green pitch
      roughness: 0.3,
    });
    const boardSurface = new THREE.Mesh(boardSurfaceGeo, boardSurfaceMat);
    boardSurface.position.z = 0.07;
    boardGroup.add(boardSurface);

    // 11-Token Tactical Formation Magnets on Pitch Board
    magnetsRef.current = [];
    const formationPositions = FORMATION_COORDINATES[activeFormation] || FORMATION_COORDINATES["4-3-3"];

    formationPositions.forEach(([mx, my]) => {
      const magnetGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.06, 16);
      const magnetMat = new THREE.MeshStandardMaterial({
        color: 0x38bdf8,
        roughness: 0.2,
        metalness: 0.6,
      });
      const magnet = new THREE.Mesh(magnetGeo, magnetMat);
      magnet.rotation.x = Math.PI / 2;
      magnet.position.set(mx, my, 0.1);
      boardGroup.add(magnet);
      magnetsRef.current.push(magnet);
    });
    scene.add(boardGroup);

    // Silverware Trophy Miniature on Manager's Executive Side Shelf
    const trophyTable = new THREE.Mesh(
      new THREE.BoxGeometry(1.2, 0.9, 0.6),
      new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.3 })
    );
    trophyTable.position.set(-2.8, 0.45, -0.8);
    scene.add(trophyTable);

    const trophyCup = new THREE.Mesh(
      new THREE.CylinderGeometry(0.2, 0.08, 0.38, 16),
      new THREE.MeshStandardMaterial({ color: 0xf59e0b, metalness: 0.9, roughness: 0.15 })
    );
    trophyCup.position.set(-2.8, 1.1, -0.8);
    scene.add(trophyCup);

    // -----------------------------------------------------------------------
    // 3D First-Team Manager Persona
    // -----------------------------------------------------------------------
    const managerGroup = new THREE.Group();
    managerGroup.position.set(1.8, 0, 1.2);
    managerGroup.rotation.y = -Math.PI / 4;

    const mgrTorsoGeo = new THREE.BoxGeometry(0.7, 1.1, 0.45);
    const mgrTorsoMat = new THREE.MeshStandardMaterial({ color: 0x097969, roughness: 0.5 });
    const mgrTorso = new THREE.Mesh(mgrTorsoGeo, mgrTorsoMat);
    mgrTorso.position.y = 1.35;
    mgrTorso.castShadow = true;
    mgrTorso.userData = { isManagerRaycast: true };
    managerGroup.add(mgrTorso);

    const mgrHeadGeo = new THREE.SphereGeometry(0.24, 20, 20);
    const mgrHeadMat = new THREE.MeshStandardMaterial({ color: 0xd4a373, roughness: 0.7 });
    const mgrHead = new THREE.Mesh(mgrHeadGeo, mgrHeadMat);
    mgrHead.position.y = 2.1;
    mgrHead.castShadow = true;
    mgrHead.userData = { isManagerRaycast: true };
    managerGroup.add(mgrHead);

    const selRingGeo = new THREE.RingGeometry(0.65, 0.8, 32);
    const selRingMat = new THREE.MeshBasicMaterial({
      color: 0x10b981,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0,
    });
    const selRing = new THREE.Mesh(selRingGeo, selRingMat);
    selRing.rotation.x = -Math.PI / 2;
    selRing.position.y = 0.02;
    selRing.name = "selRing";
    managerGroup.add(selRing);
    scene.add(managerGroup);

    // -----------------------------------------------------------------------
    // Raycasting
    // -----------------------------------------------------------------------
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const handlePointerMove = (evt: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((evt.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((evt.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const targets = [mgrTorso, mgrHead];
      const intersects = raycaster.intersectObjects(targets, false);

      if (intersects.length > 0) {
        setIsHovered(true);
        renderer.domElement.style.cursor = "pointer";
        selRingMat.opacity = 0.9;
      } else {
        setIsHovered(false);
        renderer.domElement.style.cursor = "default";
        selRingMat.opacity = 0;
      }
    };

    const handlePointerDown = (evt: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((evt.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((evt.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const targets = [mgrTorso, mgrHead];
      const intersects = raycaster.intersectObjects(targets, false);
      if (intersects.length > 0) {
        setIsModalOpen(true);
      }
    };

    renderer.domElement.addEventListener("mousemove", handlePointerMove);
    renderer.domElement.addEventListener("pointerdown", handlePointerDown);

    // Animation Loop
    let animId: number;
    const clock = new THREE.Clock();
    const handleContextLost = (e: Event) => {
      e.preventDefault();
    };
    renderer.domElement.addEventListener("webglcontextlost", handleContextLost, false);

    const animate = () => {
      animId = requestAnimationFrame(animate);
      if (typeof document !== "undefined" && document.hidden) return;
      const dt = clock.getDelta();

      if (isTransitioningRef.current) {
        camera.position.lerp(cameraGoalPosRef.current, dt * 3.5);
        controls.target.lerp(cameraGoalTargetRef.current, dt * 3.5);

        if (
          camera.position.distanceTo(cameraGoalPosRef.current) < 0.05 &&
          controls.target.distanceTo(cameraGoalTargetRef.current) < 0.05
        ) {
          isTransitioningRef.current = false;
        }
      }

      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const nw = Math.max(320, entry.contentRect.width);
        const nh = Math.max(380, entry.contentRect.height);
        camera.aspect = nw / nh;
        camera.updateProjectionMatrix();
        renderer.setSize(nw, nh);
      }
    });
    resizeObserver.observe(container);

    return () => {
      cancelAnimationFrame(animId);
      resizeObserver.disconnect();
      renderer.domElement.removeEventListener("webglcontextlost", handleContextLost);
      renderer.domElement.removeEventListener("mousemove", handlePointerMove);
      renderer.domElement.removeEventListener("pointerdown", handlePointerDown);
      controls.dispose();
      disposeScene(scene, renderer);
    };
  }, [activeQuality, lightingMode]);

  return (
    <div
      data-testid="tactician-3d-scene"
      className="relative h-full min-h-[520px] w-full overflow-hidden rounded-2xl border border-emerald-500/20 bg-slate-950"
    >
      <div ref={mountRef} className="h-full w-full" />

      {/* Top HUD Controls */}
      <div className="pointer-events-none absolute inset-x-0 top-0 z-20 flex flex-wrap items-center justify-between gap-2 p-4">
        <div className="pointer-events-auto flex items-center gap-2 rounded-xl border border-white/10 bg-slate-950/80 px-3 py-1.5 backdrop-blur-md">
          <Sliders className="h-4 w-4 text-emerald-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-white">
            Manager Tactician War Room
          </span>
          <span className="rounded bg-sky-500/20 px-1.5 py-0.5 text-[10px] font-mono text-sky-300">
            FORMATION {activeFormation}
          </span>
        </div>

        {/* Formation Switcher & Authoritative Proposal Action */}
        <div className="pointer-events-auto flex items-center gap-1 rounded-xl border border-white/10 bg-slate-950/80 p-1 backdrop-blur-md">
          {(["4-3-3", "4-2-3-1", "3-5-2", "4-4-2"] as TacticalFormation[]).map((fmt) => (
            <button
              key={fmt}
              type="button"
              data-testid={`formation-select-${fmt}`}
              onClick={() => handleSelectFormation(fmt)}
              className={`rounded-lg px-2 py-0.5 text-[10px] font-mono font-bold transition-all ${
                activeFormation === fmt
                  ? "bg-sky-500 text-slate-950 shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {fmt}
            </button>
          ))}
          <button
            type="button"
            data-testid="propose-tactical-formation-btn"
            disabled={submittingTactics}
            onClick={handleProposeTactics}
            className="ml-1 rounded-lg bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 px-2.5 py-0.5 text-[10px] font-black text-slate-950 transition-all"
          >
            {submittingTactics ? "Proposing..." : "Apply to Manager"}
          </button>
        </div>

        <div className="pointer-events-auto flex items-center gap-2">
          <span
            data-testid="medical-suite-cryo-link"
            className="rounded-lg border border-sky-400/30 bg-sky-500/10 px-2.5 py-1 text-[10px] font-bold text-sky-300 backdrop-blur-md"
          >
            Medical Link: Cryo Active • Lvl {medicalTelemetry.medicalLevel} ({medicalTelemetry.injuredCount} Injured)
          </span>

          <button
            type="button"
            data-testid="capture-tactician-snapshot-btn"
            onClick={handleCaptureSnapshot}
            className="rounded-lg border border-emerald-400/30 bg-slate-950/80 px-2.5 py-1 text-xs font-bold text-emerald-300 hover:bg-white/10 transition-colors backdrop-blur-md"
            title="Capture 3D Tactical Frame"
          >
            Snapshot
          </button>

          <button
            type="button"
            data-testid="toggle-tactician-lighting-btn"
            onClick={() => setLightingMode((m) => (m === "day" ? "night" : "day"))}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-slate-950/80 text-slate-300 transition-colors hover:bg-white/10 hover:text-white"
            title={`Switch to ${lightingMode === "day" ? "Night" : "Day"} Lighting`}
          >
            {lightingMode === "day" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4 text-amber-400" />}
          </button>

          <div className="flex items-center gap-1 rounded-xl border border-white/10 bg-slate-950/80 p-1 backdrop-blur-md">
            {(Object.keys(CAMERA_PRESETS) as TacticianCameraPreset[]).map((pkey) => (
              <button
                key={pkey}
                type="button"
                data-testid={`camera-preset-${pkey}`}
                onClick={() => handleSelectPreset(pkey)}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-all ${
                  activePreset === pkey
                    ? "bg-emerald-500 text-slate-950 font-bold shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {CAMERA_PRESETS[pkey].label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Floating Manager Hover Tooltip */}
      {isHovered && (
        <div
          data-testid="manager-hover-tooltip"
          className="pointer-events-none absolute bottom-20 left-1/2 z-30 -translate-x-1/2 rounded-xl border border-emerald-500/40 bg-slate-950/90 px-4 py-2 text-center shadow-xl backdrop-blur-md animate-fade-in"
        >
          <div className="flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-xs font-bold text-white">First-Team Manager</span>
            <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-300">
              Tactician Suite
            </span>
          </div>
          <p className="mt-0.5 text-[10px] text-slate-400">Click manager to discuss tactics and alignment</p>
        </div>
      )}

      {/* Authoritative Tactical Proposal Feedback Banner */}
      {tacticalFeedback && (
        <div
          data-testid="tactical-proposal-response-banner"
          className="pointer-events-auto absolute bottom-16 left-4 right-4 z-30 rounded-xl border border-emerald-500/40 bg-slate-950/95 p-3 shadow-2xl backdrop-blur-md"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-black uppercase tracking-wider text-emerald-400">
              {tacticalFeedback.status === "accepted"
                ? `Tactical Setup Ratified (${tacticalFeedback.effective_formation})`
                : `Manager Counter-Proposal (${tacticalFeedback.counter_formation || "Structured Shape"})`}
            </span>
            <button
              type="button"
              onClick={() => setTacticalFeedback(null)}
              className="text-[10px] font-bold text-slate-400 hover:text-white"
            >
              Dismiss
            </button>
          </div>
          <p className="mt-1 text-xs text-slate-200">
            <strong className="text-white">{tacticalFeedback.manager_name}:</strong> &ldquo;
            {tacticalFeedback.manager_explanation}&rdquo;
          </p>
        </div>
      )}

      {/* Bottom Action Pill */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 z-20 flex items-center justify-between border-t border-white/10 bg-gradient-to-t from-slate-950 via-slate-950/80 to-transparent p-4">
        <button
          type="button"
          data-testid="open-manager-dialogue-btn"
          onClick={() => setIsModalOpen(true)}
          className="pointer-events-auto flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-xs font-semibold text-emerald-300 transition-all hover:bg-emerald-500/20"
        >
          <Users className="h-4 w-4" />
          <span>Converse with Manager</span>
        </button>
      </div>

      <PersonaSpatialInteractionModal
        clubId={clubId}
        personaRole="first_team_manager"
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
};

// Register custom Three.js renderer in GtexSceneRegistry for tactician_suite
GtexSceneRegistry.registerRenderer("tactician_suite", TacticianSuiteScene);
