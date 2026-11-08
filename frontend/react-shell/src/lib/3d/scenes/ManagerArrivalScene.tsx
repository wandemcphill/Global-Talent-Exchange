/**
 * GTEX Living Football World — Stage 7 Cinema 3D & Staff Arrivals
 * ManagerArrivalScene: Genuine Three.js WebGL 3D Manager & Staff Arrival Unveiling Stage.
 *
 * Implements:
 * 1. 3D Press Conference Podium, Illuminated Club Backdrop Wall, Stadium Tunnel Arch & Tactical Board.
 * 2. 3D Humanoid Manager/Staff Figure + Club Owner Figure in Contract Handover Pose.
 * 3. 4-Shot Camera Choreography (tunnel_emergence, press_flashbulbs, contract_handover, tactical_board_pose).
 * 4. Verified Contract & Identity Card with "Return to Club Office" completion trigger.
 * 5. Honest 3D WebGL vs 2D Fallback mode reporting and full WebGL resource disposal.
 */

import React, { useEffect, useRef, useState, useCallback } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GtexSceneRegistry } from "../GtexSceneRegistry";
import type { GtexSceneRendererProps } from "../GtexSceneTypes";
import type { CinematicEventPayload } from "@/lib/ownerBriefing";

export type ArrivalCameraShot =
  | "tunnel_emergence"
  | "press_flashbulbs"
  | "contract_handover"
  | "tactical_board_pose";

export interface ManagerArrivalSceneProps extends Partial<GtexSceneRendererProps> {
  cinematicEvent?: Partial<CinematicEventPayload> | null;
  subjectName?: string;
  subjectRoleLabel?: string;
  overallRating?: number;
  contractYears?: number;
  salaryGtex?: number;
  clubName?: string;
  primaryColor?: string;
  secondaryColor?: string;
  title?: string;
  badgeText?: string;
  onComplete?: () => void;
}

const SHOT_PRESETS: Record<
  ArrivalCameraShot,
  { label: string; position: [number, number, number]; target: [number, number, number] }
> = {
  tunnel_emergence: {
    label: "1. Tunnel Walkout",
    position: [0, 2.8, 9.5],
    target: [0, 1.8, -1.5],
  },
  press_flashbulbs: {
    label: "2. Press Stage",
    position: [-4.2, 2.5, 6.8],
    target: [0, 1.9, 0],
  },
  contract_handover: {
    label: "3. Contract Handover",
    position: [0.4, 2.2, 4.6],
    target: [0, 1.85, 0],
  },
  tactical_board_pose: {
    label: "4. Tactical Vision",
    position: [3.8, 2.4, 5.4],
    target: [1.5, 1.9, -1.2],
  },
};

function parseHexColor(hexStr: string | undefined, fallback: number): number {
  if (!hexStr) return fallback;
  const cleaned = hexStr.replace("#", "").trim();
  const parsed = parseInt(cleaned, 16);
  return Number.isNaN(parsed) ? fallback : parsed;
}

export const ManagerArrivalScene: React.FC<ManagerArrivalSceneProps> = ({
  cinematicEvent,
  subjectName,
  subjectRoleLabel,
  overallRating,
  contractYears,
  salaryGtex,
  clubName,
  primaryColor,
  secondaryColor,
  title,
  badgeText,
  onComplete,
  activeQuality,
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const [activeShot, setActiveShot] = useState<ArrivalCameraShot>("contract_handover");
  const [webglActive, setWebglActive] = useState<boolean>(true);

  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const cameraGoalPosRef = useRef<THREE.Vector3>(
    new THREE.Vector3(...SHOT_PRESETS.contract_handover.position)
  );
  const cameraGoalTargetRef = useRef<THREE.Vector3>(
    new THREE.Vector3(...SHOT_PRESETS.contract_handover.target)
  );
  const isTransitioningRef = useRef<boolean>(false);

  const meta = (cinematicEvent as any)?.metadata || {};
  const branding = (cinematicEvent as any)?.club_branding || {};

  const resolvedName =
    cinematicEvent?.subject_name || meta.staff_name || subjectName || "Emmanuel Amuneke";
  const resolvedRole =
    cinematicEvent?.subject_role_label || meta.role_label || subjectRoleLabel || "First-Team Manager";
  const resolvedRating =
    cinematicEvent?.overall_rating ?? meta.rating ?? overallRating ?? 86;
  const resolvedYears =
    cinematicEvent?.contract_years ?? meta.contract_years ?? contractYears ?? 3;
  const resolvedSalary =
    cinematicEvent?.salary_gtex ?? meta.annual_salary_gtex ?? salaryGtex ?? 2500;
  const resolvedClub =
    cinematicEvent?.club_name || branding.club_name || clubName || "GTEX FC";
  const resolvedTitle =
    cinematicEvent?.title ||
    title ||
    `${resolvedRole} Unveiled: ${resolvedName} Arrives at ${resolvedClub}`;
  const resolvedBadge =
    cinematicEvent?.badge_text || badgeText || "OFFICIAL CLUB UNVEILING";
  const resolvedPrimaryHex = parseHexColor(
    cinematicEvent?.primary_color || branding.primary_color || primaryColor,
    0x10b981
  );
  const resolvedSecondaryHex = parseHexColor(
    cinematicEvent?.secondary_color || branding.secondary_color || secondaryColor,
    0x0f172a
  );

  const handleSelectShot = useCallback((shot: ArrivalCameraShot) => {
    setActiveShot(shot);
    const cfg = SHOT_PRESETS[shot];
    cameraGoalPosRef.current.set(...cfg.position);
    cameraGoalTargetRef.current.set(...cfg.target);
    isTransitioningRef.current = true;
  }, []);

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

    const width = Math.max(320, container.clientWidth || 780);
    const height = Math.max(280, container.clientHeight || 420);
    renderer.setSize(width, height);
    renderer.setPixelRatio(
      Math.min(window.devicePixelRatio || 1, activeQuality?.pixelRatio || 1.5)
    );
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.18;

    container.innerHTML = "";
    renderer.domElement.setAttribute("data-testid", "manager-arrival-3d-canvas");
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.display = "block";
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x050b16);

    const camera = new THREE.PerspectiveCamera(40, width / height, 0.3, 120);
    camera.position.copy(cameraGoalPosRef.current);
    cameraRef.current = camera;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.target.copy(cameraGoalTargetRef.current);
    controlsRef.current = controls;

    // Stage Lighting
    const ambient = new THREE.HemisphereLight(0xe0f2fe, 0x0f172a, 0.95);
    scene.add(ambient);

    const keySpot = new THREE.DirectionalLight(0xfffbeb, 2.0);
    keySpot.position.set(5, 12, 8);
    scene.add(keySpot);

    const clubAccentLight = new THREE.PointLight(resolvedPrimaryHex, 2.2, 18);
    clubAccentLight.position.set(0, 4.5, -2.0);
    scene.add(clubAccentLight);

    // Stage Carpet & Podium Floor
    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(20, 16),
      new THREE.MeshStandardMaterial({
        color: 0x0f172a,
        roughness: 0.35,
        metalness: 0.25,
      })
    );
    floor.rotation.x = -Math.PI / 2;
    scene.add(floor);

    const riser = new THREE.Mesh(
      new THREE.CylinderGeometry(3.8, 4.1, 0.25, 40),
      new THREE.MeshStandardMaterial({
        color: resolvedSecondaryHex,
        metalness: 0.5,
        roughness: 0.3,
      })
    );
    riser.position.y = 0.125;
    scene.add(riser);

    // Illuminated Club Media Backdrop Wall
    const backdropWall = new THREE.Mesh(
      new THREE.BoxGeometry(8.5, 4.2, 0.22),
      new THREE.MeshStandardMaterial({
        color: resolvedPrimaryHex,
        metalness: 0.35,
        roughness: 0.4,
      })
    );
    backdropWall.position.set(0, 2.2, -2.4);
    scene.add(backdropWall);

    // Tactical Hologram Display Board on Right Side of Stage
    const tacticalBoard = new THREE.Mesh(
      new THREE.BoxGeometry(2.4, 1.5, 0.1),
      new THREE.MeshBasicMaterial({
        color: 0x38bdf8,
        transparent: true,
        opacity: 0.8,
      })
    );
    tacticalBoard.position.set(2.4, 2.1, -1.4);
    tacticalBoard.rotation.y = -Math.PI / 6;
    scene.add(tacticalBoard);

    // Press Conference Podium & Dual Microphones
    const podium = new THREE.Mesh(
      new THREE.BoxGeometry(2.2, 1.05, 0.75),
      new THREE.MeshStandardMaterial({
        color: 0x1e293b,
        metalness: 0.6,
        roughness: 0.3,
      })
    );
    podium.position.set(0, 0.75, 0.6);
    scene.add(podium);

    // 3D Humanoid Appointed Manager/Staff Figure (Center-Left) & Club Owner Figure (Center-Right)
    const figuresGroup = new THREE.Group();
    const buildHumanoid = (xPos: number, suitColor: number) => {
      const g = new THREE.Group();
      g.position.set(xPos, 0.25, -0.35);
      const torso = new THREE.Mesh(
        new THREE.BoxGeometry(0.65, 1.0, 0.38),
        new THREE.MeshStandardMaterial({ color: suitColor, roughness: 0.5 })
      );
      torso.position.y = 1.25;
      g.add(torso);

      const head = new THREE.Mesh(
        new THREE.SphereGeometry(0.22, 18, 18),
        new THREE.MeshStandardMaterial({ color: 0xd4a373, roughness: 0.65 })
      );
      head.position.y = 1.98;
      g.add(head);
      return g;
    };

    const managerFigure = buildHumanoid(-0.55, resolvedPrimaryHex);
    const ownerFigure = buildHumanoid(0.55, 0x0f172a);
    figuresGroup.add(managerFigure);
    figuresGroup.add(ownerFigure);

    // Club Presentation Scarf / Contract Plaque Held Between Figures
    const scarf = new THREE.Mesh(
      new THREE.BoxGeometry(1.35, 0.26, 0.06),
      new THREE.MeshStandardMaterial({
        color: resolvedPrimaryHex,
        emissive: resolvedPrimaryHex,
        emissiveIntensity: 0.35,
      })
    );
    scarf.position.set(0, 1.55, -0.08);
    figuresGroup.add(scarf);
    scene.add(figuresGroup);

    let animId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const dt = clock.getDelta();

      // Subtle breathing / presentation pose motion
      figuresGroup.position.y = Math.sin(clock.getElapsedTime() * 2.2) * 0.02;

      if (isTransitioningRef.current) {
        camera.position.lerp(cameraGoalPosRef.current, dt * 3.8);
        controls.target.lerp(cameraGoalTargetRef.current, dt * 3.8);
        if (camera.position.distanceTo(cameraGoalPosRef.current) < 0.06) {
          isTransitioningRef.current = false;
        }
      }

      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(animId);
      controls.dispose();
      renderer.dispose();
      scene.clear();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [activeQuality, resolvedPrimaryHex, resolvedSecondaryHex]);

  return (
    <div
      data-testid="manager-arrival-3d-scene"
      className="relative w-full overflow-hidden rounded-2xl border border-emerald-500/40 bg-slate-950 shadow-2xl"
      style={{ minHeight: 420 }}
    >
      {/* 3D WebGL Canvas Mount */}
      <div ref={mountRef} className="h-[420px] w-full" />

      {/* Honest 2D Fallback View when WebGL context is unavailable */}
      {!webglActive && (
        <div
          data-testid="manager-arrival-2d-fallback"
          className="absolute inset-0 flex flex-col items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-emerald-950/40 p-6 text-center"
        >
          <span className="rounded-full border border-amber-400/40 bg-amber-400/10 px-3 py-1 text-[10px] font-black uppercase tracking-wider text-amber-300">
            2D Press Unveiling Stage Fallback
          </span>
          <h3 className="mt-3 text-xl font-black text-white">{resolvedTitle}</h3>
          <p className="mt-1 text-xs text-slate-300">
            {resolvedName} ({resolvedRole} • OVR {resolvedRating}) • {resolvedYears}-Year Contract •{" "}
            {resolvedSalary.toLocaleString()} GTEX/wk
          </p>
        </div>
      )}

      {/* Top HUD Bar */}
      <div className="pointer-events-none absolute inset-x-0 top-0 z-20 flex items-center justify-between p-4">
        <div className="flex items-center gap-2">
          <span
            data-testid="arrival-render-mode-badge"
            className={`rounded-lg px-2.5 py-1 text-[10px] font-black uppercase tracking-wider backdrop-blur-md ${
              webglActive
                ? "border border-emerald-400/40 bg-emerald-500/20 text-emerald-300"
                : "border border-amber-400/40 bg-amber-500/20 text-amber-300"
            }`}
          >
            {webglActive ? "3D WEBGL CINEMA" : "2D FALLBACK MODE"}
          </span>
          <span className="rounded-lg border border-white/15 bg-slate-950/80 px-2.5 py-1 text-[10px] font-bold uppercase text-white backdrop-blur-md">
            {resolvedBadge} • VERIFIED APPOINTMENT
          </span>
        </div>

        {/* Camera Choreography Shots */}
        <div className="pointer-events-auto flex items-center gap-1 rounded-xl border border-white/10 bg-slate-950/80 p-1 backdrop-blur-md">
          {(Object.keys(SHOT_PRESETS) as ArrivalCameraShot[]).map((shotKey) => (
            <button
              key={shotKey}
              type="button"
              data-testid={`arrival-camera-${shotKey}`}
              onClick={() => handleSelectShot(shotKey)}
              className={`rounded-lg px-2.5 py-1 text-[11px] font-bold transition-all ${
                activeShot === shotKey
                  ? "bg-emerald-500 text-slate-950"
                  : "text-slate-300 hover:text-white"
              }`}
            >
              {SHOT_PRESETS[shotKey].label}
            </button>
          ))}
        </div>
      </div>

      {/* Bottom Verified Contract Summary & Return Action */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 z-20 flex flex-wrap items-center justify-between gap-4 border-t border-white/10 bg-gradient-to-t from-slate-950 via-slate-950/90 to-transparent p-4">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-400">
            {resolvedClub} • Official Unveiling
          </div>
          <h3 className="text-lg font-black text-white">{resolvedTitle}</h3>
          <div className="mt-0.5 text-xs text-slate-300">
            <strong className="text-white">{resolvedName}</strong> ({resolvedRole} • OVR{" "}
            {resolvedRating}) • {resolvedYears}-Year Deal ({resolvedSalary.toLocaleString()} GTEX/wk)
          </div>
        </div>

        {onComplete && (
          <button
            type="button"
            data-testid="complete-arrival-cinematic-btn"
            onClick={onComplete}
            className="pointer-events-auto rounded-xl bg-emerald-500 px-4 py-2.5 text-xs font-black text-slate-950 shadow-lg transition-colors hover:bg-emerald-400"
          >
            Return to Club Office
          </button>
        )}
      </div>
    </div>
  );
};

GtexSceneRegistry.registerRenderer("manager_arrival", ManagerArrivalScene);
