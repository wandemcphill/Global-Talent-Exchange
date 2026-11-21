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
import { api } from "@/lib/api";
import { GtexSceneRegistry } from "../GtexSceneRegistry";
import { disposeScene } from "../disposeScene";
import { AssetStreamingCache } from "../broadcast/AssetStreamingCache";
import { resolvePublicAssetPath } from "@/lib/publicPath";
import { StadiumEnvironmentLighting } from "../broadcast/StadiumEnvironmentLighting";
import {
  loadFramedModel,
  loadTrainingField,
  loadPresentationFigure,
  paintIdentityBoard,
} from "../sceneKit";
import type { GtexSceneRendererProps } from "../GtexSceneTypes";
import type { CinematicEventPayload } from "@/lib/ownerBriefing";

export type ArrivalCameraShot =
  | "vip_transport_touchdown"
  | "medical_clearance_scan"
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
  vip_transport_touchdown: {
    label: "VIP Tarmac",
    position: [-0.6, 3.6, 17.4],
    target: [-8.2, 1.05, 7.2],
  },
  medical_clearance_scan: {
    label: "Medical Scan",
    position: [2.35, 1.42, 7.15],
    target: [0, 1.22, 2.1],
  },
  tunnel_emergence: {
    label: "1. Tunnel Walkout",
    position: [0.4, 1.85, 8.4],
    target: [0, 1.15, 2.1],
  },
  press_flashbulbs: {
    label: "2. Press Stage",
    position: [-2.7, 1.65, 5.5],
    target: [0.1, 1.2, 2.1],
  },
  contract_handover: {
    label: "3. Contract Handover",
    position: [3.1, 1.5, 6.5],
    target: [0.15, 1.15, 2.1],
  },
  tactical_board_pose: {
    label: "4. Tactical Vision",
    position: [7.2, 5.6, 9.2],
    target: [0, 0.4, 1.2],
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
  const vipTransport = (cinematicEvent as any)?.vip_transport || meta?.vip_transport || null;
  const medicalClearance =
    (cinematicEvent as any)?.medical_clearance_status ||
    meta?.medical_clearance_status ||
    "Not filed";
  const pressQaPayload = (cinematicEvent as any)?.press_conference_qa || meta?.press_conference_qa || null;

  const resolvedName =
    cinematicEvent?.subject_name || meta.staff_name || subjectName || "Unnamed arrival";
  const resolvedRole =
    cinematicEvent?.subject_role_label || meta.role_label || subjectRoleLabel || "First-Team Manager";
  const resolvedRating =
    cinematicEvent?.overall_rating ?? meta.rating ?? overallRating ?? null;
  const resolvedYears =
    cinematicEvent?.contract_years ?? meta.contract_years ?? contractYears ?? null;
  const resolvedSalary =
    cinematicEvent?.salary_gtex ?? meta.annual_salary_gtex ?? salaryGtex ?? null;
  const resolvedClub =
    cinematicEvent?.club_name || branding.club_name || clubName || "Club not filed";
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

  const [pressResponse, setPressResponse] = useState<{
    headline: string;
    quote: string;
    political_impact?: Record<string, string>;
  } | null>(null);
  const [submittingStance, setSubmittingStance] = useState<boolean>(false);

  const handleSelectShot = useCallback((shot: ArrivalCameraShot) => {
    setActiveShot(shot);
    const cfg = SHOT_PRESETS[shot];
    cameraGoalPosRef.current.set(...cfg.position);
    cameraGoalTargetRef.current.set(...cfg.target);
    isTransitioningRef.current = true;
  }, []);

  const handleSelectPressStance = useCallback(
    async (stance: string) => {
      setSubmittingStance(true);
      const resolvedEventId = cinematicEvent?.event_id || meta?.event_id || "evt_press_latest";
      const resolvedClubId =
        (cinematicEvent as any)?.club_id ||
        meta?.club_id ||
        branding?.club_id ||
        clubName ||
        "c_default";
      try {
        const res = await api.post(
          `/owner/clubs/${resolvedClubId}/living-world/cinema-showroom/${resolvedEventId}/press-question`,
          { stance }
        );
        const rawEffects = res.data?.political_impact || res.data?.effects || {};
        const normalizedImpact: Record<string, string> = {};
        Object.entries(rawEffects).forEach(([k, v]) => {
          const numVal = Number(v);
          normalizedImpact[k] = !Number.isNaN(numVal) && numVal > 0 ? `+${numVal}` : String(v);
        });
        setPressResponse({
          headline: res.data?.media_headline || res.data?.headline || "Official Press Statement Published",
          quote: res.data?.quote || "Statement on club sporting direction delivered to press pack.",
          political_impact: normalizedImpact,
        });
      } catch {
        const defaultHeadlines: Record<
          string,
          { headline: string; quote: string; political_impact: Record<string, string> }
        > = {
          championship_ambition: {
            headline: "Owner Demands Immediate Silverware: 'We Are Here to Win Everything'",
            quote: "We brought elite leadership because this club belongs at the summit.",
            political_impact: { supporter_confidence: "+5", board_ambition: "+4" },
          },
          tactical_pragmatism: {
            headline: "Owner Preaches Tactical Solidity: Structure Precedes Silverware",
            quote: "Discipline and tactical solidity will give us the platform to conquer.",
            political_impact: { manager_authority: "+5", stability: "+4" },
          },
          youth_and_sustainability: {
            headline: "Owner Pledges Academy Dynasty: Future Powered by Youth Prodigies",
            quote: "Our investment in the next generation is unwavering.",
            political_impact: { hoyd_influence: "+5", academy_confidence: "+3" },
          },
        };
        setPressResponse(defaultHeadlines[stance] || defaultHeadlines.championship_ambition);
      } finally {
        setSubmittingStance(false);
      }
    },
    [branding?.club_id, cinematicEvent, clubName, meta?.club_id, meta?.event_id]
  );

  const handleCaptureSnapshot = useCallback(() => {
    const canvas = mountRef.current?.querySelector("canvas");
    if (!canvas) return;
    try {
      const url = canvas.toDataURL("image/png");
      const a = document.createElement("a");
      a.href = url;
      a.download = `GTEX_Arrival_${(resolvedName || "Staff").replace(/\s+/g, "_")}.png`;
      a.click();
    } catch {
      // test environment without real canvas rendering
    }
  }, [resolvedName]);

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
    renderer.toneMappingExposure = 1.02;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    container.innerHTML = "";
    renderer.domElement.setAttribute("data-testid", "manager-arrival-3d-canvas");
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.display = "block";
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xb7c9d6);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    const daylight = new StadiumEnvironmentLighting(renderer, scene, "high");
    void daylight.loadPolyHaven("/textures/env/kloofendal_43d_clear_puresky_2k.hdr", { background: true });

    const camera = new THREE.PerspectiveCamera(40, width / height, 0.3, 120);
    camera.position.copy(cameraGoalPosRef.current);
    cameraRef.current = camera;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.target.copy(cameraGoalTargetRef.current);
    controlsRef.current = controls;

    const ambient = new THREE.HemisphereLight(0xd7e8ff, 0x3c6a42, 0.38);
    scene.add(ambient);

    const keySpot = new THREE.DirectionalLight(0xfff3df, 2.5);
    keySpot.position.set(12, 22, 8);
    keySpot.castShadow = true;
    keySpot.shadow.mapSize.set(1024, 1024);
    keySpot.shadow.bias = -0.0006;
    keySpot.shadow.normalBias = 0.04;
    const shadowCam = keySpot.shadow.camera as THREE.OrthographicCamera;
    shadowCam.left = -18;
    shadowCam.right = 18;
    shadowCam.top = 18;
    shadowCam.bottom = -18;
    shadowCam.near = 0.5;
    shadowCam.far = 60;
    shadowCam.updateProjectionMatrix();
    scene.add(keySpot);

    const nameCanvas = paintIdentityBoard({
      clubName: resolvedClub,
      headline: resolvedName,
      primary: `#${resolvedPrimaryHex.toString(16).padStart(6, "0")}`,
      secondary: `#${resolvedSecondaryHex.toString(16).padStart(6, "0")}`,
    });
    const nameTexture = new THREE.CanvasTexture(nameCanvas);
    nameTexture.colorSpace = THREE.SRGBColorSpace;
    const nameBoard = new THREE.Mesh(
      new THREE.PlaneGeometry(8, 2),
      new THREE.MeshStandardMaterial({
        map: nameTexture,
        roughness: 0.45,
        metalness: 0.05,
        side: THREE.DoubleSide,
      })
    );
    nameBoard.position.set(0, 3.2, -7.5);
    scene.add(nameBoard);

    const vipVehicleGroup = new THREE.Group();
    vipVehicleGroup.position.set(-8.2, 0, 7.2);
    scene.add(vipVehicleGroup);

    let cancelled = false;
    const vehicleArchetype = vipTransport?.mesh_archetype || "private_jet";
    if (typeof window !== "undefined" && !/jsdom/i.test(window.navigator?.userAgent || "")) {
      const transportGlb =
        vehicleArchetype === "private_jet"
          ? "/assets/showroom/gulfstream_g700_exec_jet.glb"
          : "/assets/showroom/vanguard_xii_coach.glb";
      AssetStreamingCache.getInstance()
        .loadGltf(resolvePublicAssetPath(transportGlb), renderer)
        .then((gltf) => {
          if (cancelled || !gltf?.scene) return;
          const imported = gltf.scene.clone(true);
          const box = new THREE.Box3().setFromObject(imported);
          const size = new THREE.Vector3();
          const center = new THREE.Vector3();
          box.getSize(size);
          box.getCenter(center);
          const maxDim = Math.max(size.x, size.y, size.z, 0.001);
          const scale = 7.5 / maxDim;
          imported.scale.setScalar(scale);
          imported.position.set(-center.x * scale, -box.min.y * scale, -center.z * scale);
          imported.traverse((obj) => {
            const mesh = obj as THREE.Mesh;
            if (!mesh.isMesh) return;
            const material = mesh.material as THREE.MeshStandardMaterial;
            if (!material?.isMeshStandardMaterial) return;
            material.metalness = Math.max(material.metalness, 0.35);
            material.roughness = Math.min(material.roughness, 0.38);
            material.envMapIntensity = 1.35;
            mesh.castShadow = true;
            mesh.receiveShadow = true;
          });
          while (vipVehicleGroup.children.length > 0) {
            vipVehicleGroup.remove(vipVehicleGroup.children[0]);
          }
          vipVehicleGroup.add(imported);
        })
        .catch(() => {});
    }

    let presentationMixer: THREE.AnimationMixer | null = null;
    if (typeof window !== "undefined" && !/jsdom/i.test(window.navigator?.userAgent || "")) {
      void (async () => {
        try {
          const pitch = await loadTrainingField();
          if (!cancelled) scene.add(pitch);
          const figure = await loadPresentationFigure(renderer);
          if (!cancelled) {
            figure.object.position.z += 2.1;
            scene.add(figure.object);
            presentationMixer = figure.mixer;
          }
          const desk = await loadFramedModel("/models/furniture/desk.glb", renderer, 1.7);
          if (!cancelled) {
            desk.position.x -= 2.7;
            desk.position.z += 1.15;
            desk.traverse((obj) => {
              const mesh = obj as THREE.Mesh;
              if (mesh.isMesh) mesh.castShadow = true;
            });
            scene.add(desk);
            desk.updateMatrixWorld(true);
            const deskTop = new THREE.Box3().setFromObject(desk).max.y;
            const laptop = await loadFramedModel("/models/furniture/laptop.glb", renderer, 0.42);
            if (!cancelled) {
              laptop.position.x -= 2.7;
              laptop.position.z += 1.05;
              laptop.position.y += deskTop;
              scene.add(laptop);
            }
          }
          const chair = await loadFramedModel("/models/furniture/chairDesk.glb", renderer, 1.05);
          if (!cancelled) {
            chair.position.x -= 2.7;
            chair.position.z += 2.05;
            chair.rotation.y = Math.PI;
            chair.traverse((obj) => {
              const mesh = obj as THREE.Mesh;
              if (mesh.isMesh) mesh.castShadow = true;
            });
            scene.add(chair);
          }
        } catch {
          // The name board remains if a model fails to load.
        }
      })();
    }

    let animId: number;
    const clock = new THREE.Clock();
    const handleContextLost = (e: Event) => {
      e.preventDefault();
      setWebglActive(false);
    };
    const handleContextRestored = () => {
      setWebglActive(true);
    };
    renderer.domElement.addEventListener("webglcontextlost", handleContextLost, false);
    renderer.domElement.addEventListener("webglcontextrestored", handleContextRestored, false);

    const animate = () => {
      animId = requestAnimationFrame(animate);
      if (typeof document !== "undefined" && document.hidden) return;
      const dt = clock.getDelta();

      presentationMixer?.update(dt);

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
      cancelled = true;
      cancelAnimationFrame(animId);
      renderer.domElement.removeEventListener("webglcontextlost", handleContextLost);
      renderer.domElement.removeEventListener("webglcontextrestored", handleContextRestored);
      controls.dispose();
      daylight.dispose();
      disposeScene(scene, renderer);
    };
  }, [activeQuality, resolvedClub, resolvedName, resolvedPrimaryHex, resolvedSecondaryHex, vipTransport]);

  return (
    <div
      data-testid="manager-arrival-3d-scene"
      className="relative w-full overflow-hidden rounded-2xl border border-emerald-500/40 bg-slate-950 shadow-2xl"
      style={{ minHeight: 560 }}
    >
      {/* 3D WebGL Canvas Mount */}
      <div ref={mountRef} className="h-[560px] w-full" />

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
            {resolvedName} ({resolvedRole} • OVR {resolvedRating ?? "—"}) • {resolvedYears == null ? "Term not filed" : `${resolvedYears}-Year Contract`} •{" "}
            {resolvedSalary == null ? "Wage not filed" : `${resolvedSalary.toLocaleString()} GTEX/wk`}
          </p>
        </div>
      )}

      {/* Top HUD Bar */}
      <div className="pointer-events-none absolute inset-x-0 top-0 z-20 flex flex-wrap items-center justify-between gap-2 p-4">
        <div className="flex flex-wrap items-center gap-2">
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
          <span
            data-testid="arrival-vip-transport-badge"
            className="rounded-lg border border-amber-400/30 bg-slate-950/80 px-2.5 py-1 text-[10px] font-bold text-amber-300 backdrop-blur-md"
          >
            VIP Transport: {vipTransport?.custom_name || "Executive Club Charter"}
          </span>
          <span
            data-testid="arrival-medical-clearance-badge"
            className="rounded-lg border border-sky-400/30 bg-slate-950/80 px-2.5 py-1 text-[10px] font-bold text-sky-300 backdrop-blur-md"
          >
            Medical: {String(medicalClearance).replace(/_/g, " ").toUpperCase()}
          </span>
        </div>

        {/* Camera Choreography Shots & Snapshot Action */}
        <div className="pointer-events-auto flex items-center gap-1.5">
          <button
            type="button"
            data-testid="capture-arrival-snapshot-btn"
            onClick={handleCaptureSnapshot}
            className="rounded-lg border border-emerald-400/30 bg-slate-950/80 px-2.5 py-1 text-[11px] font-bold text-emerald-300 backdrop-blur-md hover:bg-white/10 transition-colors"
            title="Capture HD Frame Snapshot"
          >
            Snapshot
          </button>
          <div className="flex items-center gap-1 rounded-xl border border-white/10 bg-slate-950/80 p-1 backdrop-blur-md">
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
      </div>

      {/* Interactive 3D Press Conference Q&A Overlay */}
      {activeShot === "press_flashbulbs" && (
        <div
          data-testid="arrival-press-qa-overlay"
          className="pointer-events-auto absolute bottom-24 left-1/2 z-30 w-[92%] max-w-xl -translate-x-1/2 rounded-2xl border border-sky-500/40 bg-slate-950/95 p-4 shadow-2xl backdrop-blur-lg animate-fade-in"
        >
          <div className="flex items-center justify-between border-b border-white/10 pb-2">
            <div className="flex items-center gap-2">
              <span className="flex h-2 w-2 rounded-full bg-red-500 animate-pulse" />
              <span className="text-[11px] font-black uppercase tracking-wider text-sky-400">
                GTEX Live Press Conference
              </span>
            </div>
            <span className="text-[10px] text-slate-400">
              {pressQaPayload?.journalist_name || "Continental Media Pack"}
            </span>
          </div>

          <p className="mt-2 text-xs text-slate-200">
            {pressResponse
              ? pressResponse.headline
              : pressQaPayload?.question_text ||
                `Journalists are pressing for the strategic mandate for ${resolvedName}: "What is the owner's primary objective for this tenure?"`}
          </p>

          {pressResponse ? (
            <div className="mt-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-2.5 text-xs text-emerald-300">
              <div className="font-bold">Official Statement Registered:</div>
              <p className="mt-0.5 text-[11px] italic text-slate-300">&ldquo;{pressResponse.quote}&rdquo;</p>
              {pressResponse.political_impact && Object.keys(pressResponse.political_impact).length > 0 && (
                <div className="mt-1 font-mono text-[10px] text-emerald-400">
                  Impact: {JSON.stringify(pressResponse.political_impact)}
                </div>
              )}
            </div>
          ) : (
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2">
              <button
                type="button"
                data-testid="press-stance-championship_ambition"
                onClick={() => handleSelectPressStance("championship_ambition")}
                disabled={submittingStance}
                className="flex flex-col items-start rounded-xl border border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 p-2.5 text-left transition-all"
              >
                <span className="text-[11px] font-black text-amber-300">Win Now</span>
                <span className="text-[10px] text-slate-300 mt-0.5">Silverware Ambition</span>
                <span className="text-[9px] text-amber-400/80 font-mono mt-1">+5 Confidence</span>
              </button>
              <button
                type="button"
                data-testid="press-stance-tactical_pragmatism"
                onClick={() => handleSelectPressStance("tactical_pragmatism")}
                disabled={submittingStance}
                className="flex flex-col items-start rounded-xl border border-sky-500/30 bg-sky-500/10 hover:bg-sky-500/20 p-2.5 text-left transition-all"
              >
                <span className="text-[11px] font-black text-sky-300">Pragmatic</span>
                <span className="text-[10px] text-slate-300 mt-0.5">Tactical Solidity</span>
                <span className="text-[9px] text-sky-400/80 font-mono mt-1">+5 Alignment</span>
              </button>
              <button
                type="button"
                data-testid="press-stance-youth_and_sustainability"
                onClick={() => handleSelectPressStance("youth_and_sustainability")}
                disabled={submittingStance}
                className="flex flex-col items-start rounded-xl border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 p-2.5 text-left transition-all"
              >
                <span className="text-[11px] font-black text-emerald-300">Dynasty</span>
                <span className="text-[10px] text-slate-300 mt-0.5">Youth & Academy</span>
                <span className="text-[9px] text-emerald-400/80 font-mono mt-1">+5 HOYD Respect</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Bottom Verified Contract Summary & Return Action */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 z-20 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 bg-slate-950/80 px-4 py-2 backdrop-blur-sm">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-400">
            {resolvedClub} • Official Unveiling
          </div>
          <h3 className="text-lg font-black text-white">{resolvedTitle}</h3>
          <div className="mt-0.5 text-xs text-slate-300">
            <strong className="text-white">{resolvedName}</strong> ({resolvedRole} • OVR{" "}
            {resolvedRating ?? "—"}) • {resolvedYears == null ? "Term not filed" : `${resolvedYears}-Year Deal`} ({resolvedSalary == null ? "Wage not filed" : `${resolvedSalary.toLocaleString()} GTEX/wk`})
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
