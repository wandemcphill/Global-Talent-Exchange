/**
 * GTEX Living Football Ecosystem — Stage 2 Persistent 3D Club Environments
 * BoardroomScene: Three.js Executive Boardroom Suite & Spatial Interactions.
 *
 * Implements:
 * 1. High-fidelity 3D architectural boardroom overlooking the stadium pitch.
 * 2. 6 Executive personas with procedural stylized humanoid rigs.
 * 3. Raycast pointer picking, hover halos, and spatial interaction modal triggers.
 * 4. Cinematic camera presets (overview, board_table, presentation_screen, pitch_view).
 * 5. Dynamic day/night ambient lighting rigs and seamless WebGL cleanup.
 */

import React, { useEffect, useRef, useState, useCallback, useMemo } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { useQuery } from "@tanstack/react-query";
import {
  Building2,
  Sun,
  Moon,
  Camera,
  Users,
  Eye,
  Sparkles,
  ChevronRight,
  ShieldAlert,
  Flame,
  Scale,
  Briefcase,
  Sliders,
} from "lucide-react";
import { api } from "@/lib/api";
import { GtexSceneRegistry } from "../GtexSceneRegistry";
import type { GtexSceneRendererProps } from "../GtexSceneTypes";
import { PersonaSpatialInteractionModal } from "../PersonaSpatialInteractionModal";
import { BoardroomDilemmaModal } from "../BoardroomDilemmaModal";
import { StaffEmploymentModal } from "../StaffEmploymentModal";
import { GmDelegationModal } from "../GmDelegationModal";
import {
  clubActiveDilemmaEndpoint,
  type BoardroomDilemma,
  type PersonaInteractionResponse,
} from "@/lib/ownerBriefing";

export interface BoardroomSceneProps extends Partial<GtexSceneRendererProps> {
  clubId?: string;
}

export type BoardroomCameraPreset = "overview" | "board_table" | "presentation_screen" | "pitch_view";

const CAMERA_PRESETS: Record<
  BoardroomCameraPreset,
  { label: string; position: [number, number, number]; target: [number, number, number] }
> = {
  overview: {
    label: "Overview",
    position: [0, 6, 17],
    target: [0, 1.8, 0],
  },
  board_table: {
    label: "Board Table",
    position: [0, 3.6, 7.2],
    target: [0, 1.8, 0],
  },
  presentation_screen: {
    label: "Display Screen",
    position: [-3.8, 3.2, 2.5],
    target: [-7.5, 3.2, -6],
  },
  pitch_view: {
    label: "Pitch View",
    position: [0, 4.2, -4.5],
    target: [0, 3.5, -35],
  },
};

interface BoardroomPersonaConfig {
  roleKey: string;
  roleLabel: string;
  name: string;
  position: [number, number, number];
  rotationY: number;
  suitColor: number;
}

const BOARDROOM_PERSONAS: BoardroomPersonaConfig[] = [
  {
    roleKey: "club_president",
    roleLabel: "Club President",
    name: "Board Representative",
    position: [0, 0, -4.6],
    rotationY: 0,
    suitColor: 0x0f172a, // Deep executive navy
  },
  {
    roleKey: "general_manager",
    roleLabel: "General Manager",
    name: "Dayo Adeleke",
    position: [-2.6, 0, -1.8],
    rotationY: Math.PI / 2,
    suitColor: 0x1e293b, // Charcoal slate
  },
  {
    roleKey: "first_team_manager",
    roleLabel: "First-Team Manager",
    name: "Emmanuel Amuneke",
    position: [2.6, 0, -1.8],
    rotationY: -Math.PI / 2,
    suitColor: 0x097969, // Club-accent dark emerald
  },
  {
    roleKey: "chief_scout",
    roleLabel: "Chief Scout",
    name: "Kofi Mensah",
    position: [-2.6, 0, 1.8],
    rotationY: Math.PI / 2,
    suitColor: 0x334155, // Steel grey
  },
  {
    roleKey: "head_of_youth_development",
    roleLabel: "Head of Youth Development",
    name: "Chidi Eze",
    position: [2.6, 0, 1.8],
    rotationY: -Math.PI / 2,
    suitColor: 0x1e3a8a, // Classic sapphire
  },
];

export const BoardroomScene: React.FC<BoardroomSceneProps> = ({
  clubId = "c_default",
  qualityTier = "high",
  activeQuality,
  sceneProps,
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const [activePreset, setActivePreset] = useState<BoardroomCameraPreset>("overview");
  const [lightingMode, setLightingMode] = useState<"day" | "night">("day");
  const [hoveredPersona, setHoveredPersona] = useState<BoardroomPersonaConfig | null>(null);
  const [isHoveringDilemma, setIsHoveringDilemma] = useState<boolean>(false);
  const [selectedPersonaRole, setSelectedPersonaRole] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [isDilemmaModalOpen, setIsDilemmaModalOpen] = useState<boolean>(false);
  const [isStaffModalOpen, setIsStaffModalOpen] = useState<boolean>(false);
  const [isGmModalOpen, setIsGmModalOpen] = useState<boolean>(false);

  // Active Boardroom Dilemma Query
  const { data: activeDilemma } = useQuery<BoardroomDilemma | null>({
    queryKey: ["club-active-dilemma", clubId],
    queryFn: async () => {
      try {
        const res = await api.get<BoardroomDilemma>(clubActiveDilemmaEndpoint(clubId));
        return res.data;
      } catch {
        return null;
      }
    },
    enabled: !!clubId,
  });

  // Three.js instances
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const personaMeshesRef = useRef<Map<string, THREE.Group>>(new Map());
  const cameraGoalPosRef = useRef<THREE.Vector3>(new THREE.Vector3(...CAMERA_PRESETS.overview.position));
  const cameraGoalTargetRef = useRef<THREE.Vector3>(new THREE.Vector3(...CAMERA_PRESETS.overview.target));
  const isTransitioningRef = useRef<boolean>(true);

  // Switch camera preset
  const handleSelectPreset = useCallback((presetKey: BoardroomCameraPreset) => {
    setActivePreset(presetKey);
    const target = CAMERA_PRESETS[presetKey];
    cameraGoalPosRef.current.set(...target.position);
    cameraGoalTargetRef.current.set(...target.target);
    isTransitioningRef.current = true;
  }, []);

  const handleOpenPersonaInteraction = useCallback((roleKey: string) => {
    setSelectedPersonaRole(roleKey);
    setIsModalOpen(true);
  }, []);

  const handleOpenDilemmaModal = useCallback(() => {
    setIsDilemmaModalOpen(true);
  }, []);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // Renderer
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
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;

    container.innerHTML = "";
    renderer.domElement.setAttribute("data-testid", "boardroom-3d-canvas");
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.display = "block";
    container.appendChild(renderer.domElement);

    // Scene
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    const isDay = lightingMode === "day";
    scene.background = new THREE.Color(isDay ? 0x091526 : 0x030712);
    scene.fog = new THREE.FogExp2(isDay ? 0x091526 : 0x030712, 0.009);

    // Camera
    const camera = new THREE.PerspectiveCamera(40, width / height, 0.4, 200);
    camera.position.copy(cameraGoalPosRef.current);
    cameraRef.current = camera;

    // OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.maxPolarAngle = Math.PI / 2 - 0.05;
    controls.minDistance = 3.5;
    controls.maxDistance = 35;
    controls.target.copy(cameraGoalTargetRef.current);
    controlsRef.current = controls;

    const stopAutoTransition = () => {
      isTransitioningRef.current = false;
    };
    controls.addEventListener("start", stopAutoTransition);

    // -----------------------------------------------------------------------
    // Lighting Rig
    // -----------------------------------------------------------------------
    const hemiLight = new THREE.HemisphereLight(0xe0f2fe, 0x0f172a, isDay ? 1.1 : 0.4);
    scene.add(hemiLight);

    const dirLight = new THREE.DirectionalLight(isDay ? 0xfffbeb : 0x60a5fa, isDay ? 1.8 : 0.8);
    dirLight.position.set(12, 22, 14);
    dirLight.castShadow = activeQuality?.shadowsEnabled ?? true;
    dirLight.shadow.mapSize.set(1024, 1024);
    scene.add(dirLight);

    // Table Chandelier / Overhead Downlight
    const tableLight = new THREE.PointLight(0xffedd5, 1.4, 16);
    tableLight.position.set(0, 5, 0);
    scene.add(tableLight);

    // -----------------------------------------------------------------------
    // Architecture: Boardroom Interior
    // -----------------------------------------------------------------------
    // Floor
    const floorGeo = new THREE.PlaneGeometry(28, 34);
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      roughness: 0.35,
      metalness: 0.2,
    });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    // Ceiling
    const ceilingGeo = new THREE.PlaneGeometry(28, 34);
    const ceilingMat = new THREE.MeshStandardMaterial({
      color: 0x0a1120,
      roughness: 0.8,
    });
    const ceiling = new THREE.Mesh(ceilingGeo, ceilingMat);
    ceiling.position.y = 8;
    ceiling.rotation.x = Math.PI / 2;
    scene.add(ceiling);

    // Panoramic Stadium Glass Window Wall (Z = -16)
    const windowWallGeo = new THREE.PlaneGeometry(28, 8);
    const windowMat = new THREE.MeshPhysicalMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.32,
      roughness: 0.1,
      metalness: 0.1,
      transmission: 0.6,
      ior: 1.5,
    });
    const windowWall = new THREE.Mesh(windowWallGeo, windowMat);
    windowWall.position.set(0, 4, -16);
    scene.add(windowWall);

    // Stadium Pitch Backdrop Vista beyond the glass
    const stadiumPitchGeo = new THREE.PlaneGeometry(64, 48);
    const stadiumPitchMat = new THREE.MeshStandardMaterial({
      color: isDay ? 0x15803d : 0x064e3b,
      roughness: 0.7,
    });
    const stadiumPitch = new THREE.Mesh(stadiumPitchGeo, stadiumPitchMat);
    stadiumPitch.rotation.x = -Math.PI / 2;
    stadiumPitch.position.set(0, -1.8, -42);
    scene.add(stadiumPitch);

    // Floodlight Pylons in the Vista
    for (const fx of [-22, 22]) {
      const pylonGeo = new THREE.CylinderGeometry(0.4, 0.7, 16, 8);
      const pylonMat = new THREE.MeshStandardMaterial({ color: 0x64748b, metalness: 0.8 });
      const pylon = new THREE.Mesh(pylonGeo, pylonMat);
      pylon.position.set(fx, 6, -42);
      scene.add(pylon);

      const flareLight = new THREE.PointLight(0xecfeff, isDay ? 1.5 : 3.2, 35);
      flareLight.position.set(fx, 14, -42);
      scene.add(flareLight);
    }

    // -----------------------------------------------------------------------
    // Executive Mahogany Conference Table & Chairs
    // -----------------------------------------------------------------------
    const tableGroup = new THREE.Group();
    const tableTopGeo = new THREE.CylinderGeometry(4.2, 4.2, 0.28, 48);
    tableTopGeo.scale(0.8, 1, 1.8); // Oval shape
    const tableTopMat = new THREE.MeshStandardMaterial({
      color: 0x451a03, // Rich dark mahogany
      roughness: 0.25,
      metalness: 0.15,
    });
    const tableTop = new THREE.Mesh(tableTopGeo, tableTopMat);
    tableTop.position.y = 1.35;
    tableTop.castShadow = true;
    tableTop.receiveShadow = true;
    tableGroup.add(tableTop);

    // Chrome Pedestal Legs
    for (const lz of [-3.5, 3.5]) {
      const legGeo = new THREE.CylinderGeometry(0.35, 0.55, 1.35, 24);
      const legMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.9, roughness: 0.1 });
      const leg = new THREE.Mesh(legGeo, legMat);
      leg.position.set(0, 0.675, lz);
      leg.castShadow = true;
      tableGroup.add(leg);
    }
    scene.add(tableGroup);

    // -----------------------------------------------------------------------
    // 3D Holographic Dilemma Projector on Mahogany Table
    // -----------------------------------------------------------------------
    const dilemmaProjectorGroup = new THREE.Group();
    dilemmaProjectorGroup.position.set(0, 1.49, 0);

    const holoBaseGeo = new THREE.CylinderGeometry(0.55, 0.65, 0.12, 32);
    const holoBaseMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      metalness: 0.85,
      roughness: 0.25,
    });
    const holoBase = new THREE.Mesh(holoBaseGeo, holoBaseMat);
    holoBase.castShadow = true;
    holoBase.userData = { isRaycastTarget: true, isDilemmaTarget: true };
    dilemmaProjectorGroup.add(holoBase);

    // Emissive projector ring
    const holoRingGeo = new THREE.RingGeometry(0.58, 0.72, 32);
    const holoRingMat = new THREE.MeshBasicMaterial({
      color: 0xf59e0b,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.85,
    });
    const holoRing = new THREE.Mesh(holoRingGeo, holoRingMat);
    holoRing.rotation.x = -Math.PI / 2;
    holoRing.position.y = 0.07;
    dilemmaProjectorGroup.add(holoRing);

    // Pulsing Hologram Beacon / Crystal
    const beaconGeo = new THREE.OctahedronGeometry(0.38, 0);
    const beaconMat = new THREE.MeshStandardMaterial({
      color: 0xf59e0b,
      emissive: 0xd97706,
      emissiveIntensity: 0.7,
      roughness: 0.2,
      metalness: 0.4,
      transparent: true,
      opacity: 0.88,
    });
    const beaconMesh = new THREE.Mesh(beaconGeo, beaconMat);
    beaconMesh.position.y = 0.6;
    beaconMesh.name = "dilemmaBeacon";
    beaconMesh.userData = { isRaycastTarget: true, isDilemmaTarget: true };
    dilemmaProjectorGroup.add(beaconMesh);

    // Downward Projector Light Beam
    const beamGeo = new THREE.CylinderGeometry(0.08, 0.45, 0.6, 16, 1, true);
    const beamMat = new THREE.MeshBasicMaterial({
      color: 0xfbbf24,
      transparent: true,
      opacity: 0.25,
      side: THREE.DoubleSide,
    });
    const beamMesh = new THREE.Mesh(beamGeo, beamMat);
    beamMesh.position.y = 0.3;
    dilemmaProjectorGroup.add(beamMesh);

    scene.add(dilemmaProjectorGroup);

    // -----------------------------------------------------------------------
    // Interactive Wall-Mounted Presentation Holographic Screen
    // -----------------------------------------------------------------------
    const screenGroup = new THREE.Group();
    screenGroup.position.set(-8.5, 3.8, -4);
    screenGroup.rotation.y = Math.PI / 3;

    const screenFrameGeo = new THREE.BoxGeometry(6.4, 3.8, 0.15);
    const screenFrameMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.8 });
    const screenFrame = new THREE.Mesh(screenFrameGeo, screenFrameMat);
    screenGroup.add(screenFrame);

    const screenDisplayGeo = new THREE.PlaneGeometry(6.1, 3.5);
    const screenDisplayMat = new THREE.MeshBasicMaterial({
      color: 0x0284c7,
      transparent: true,
      opacity: 0.85,
    });
    const screenDisplay = new THREE.Mesh(screenDisplayGeo, screenDisplayMat);
    screenDisplay.position.z = 0.09;
    screenGroup.add(screenDisplay);
    scene.add(screenGroup);

    // -----------------------------------------------------------------------
    // 3D Procedural Humanoid Personas
    // -----------------------------------------------------------------------
    const personaGroupMap = new Map<string, THREE.Group>();

    BOARDROOM_PERSONAS.forEach((pConfig) => {
      const persona = new THREE.Group();
      persona.position.set(...pConfig.position);
      persona.rotation.y = pConfig.rotationY;
      persona.userData = {
        personaRole: pConfig.roleKey,
        personaConfig: pConfig,
      };

      // Torso / Suit
      const torsoGeo = new THREE.BoxGeometry(0.75, 1.05, 0.45);
      const torsoMat = new THREE.MeshStandardMaterial({
        color: pConfig.suitColor,
        roughness: 0.6,
      });
      const torso = new THREE.Mesh(torsoGeo, torsoMat);
      torso.position.y = 1.3;
      torso.castShadow = true;
      torso.userData = { isRaycastTarget: true, personaRole: pConfig.roleKey };
      persona.add(torso);

      // Head
      const headGeo = new THREE.SphereGeometry(0.24, 20, 20);
      const headMat = new THREE.MeshStandardMaterial({ color: 0xd4a373, roughness: 0.7 });
      const head = new THREE.Mesh(headGeo, headMat);
      head.position.y = 2.05;
      head.castShadow = true;
      head.userData = { isRaycastTarget: true, personaRole: pConfig.roleKey };
      persona.add(head);

      // Executive Leather Chair
      const chairGroup = new THREE.Group();
      const seatGeo = new THREE.BoxGeometry(0.85, 0.18, 0.85);
      const chairMat = new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.4 });
      const seat = new THREE.Mesh(seatGeo, chairMat);
      seat.position.y = 0.85;
      chairGroup.add(seat);

      const backrestGeo = new THREE.BoxGeometry(0.85, 1.25, 0.15);
      const backrest = new THREE.Mesh(backrestGeo, chairMat);
      backrest.position.set(0, 1.45, -0.4);
      chairGroup.add(backrest);
      persona.add(chairGroup);

      // Floating Selection Bounding Ring (hidden by default)
      const ringGeo = new THREE.RingGeometry(0.65, 0.8, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0x10b981,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0,
      });
      const selectionRing = new THREE.Mesh(ringGeo, ringMat);
      selectionRing.rotation.x = -Math.PI / 2;
      selectionRing.position.y = 0.02;
      selectionRing.name = "selectionRing";
      persona.add(selectionRing);

      scene.add(persona);
      personaGroupMap.set(pConfig.roleKey, persona);
    });
    personaMeshesRef.current = personaGroupMap;

    // -----------------------------------------------------------------------
    // Pointer Raycasting
    // -----------------------------------------------------------------------
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const handlePointerMove = (evt: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((evt.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((evt.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const targets: THREE.Object3D[] = [];
      personaGroupMap.forEach((g) => {
        g.traverse((child) => {
          if (child.userData?.isRaycastTarget) targets.push(child);
        });
      });
      dilemmaProjectorGroup.traverse((child) => {
        if (child.userData?.isRaycastTarget) targets.push(child);
      });

      const intersects = raycaster.intersectObjects(targets, false);
      if (intersects.length > 0) {
        const hitObj = intersects[0].object;
        if (hitObj.userData?.isDilemmaTarget) {
          setIsHoveringDilemma(true);
          setHoveredPersona(null);
          renderer.domElement.style.cursor = "pointer";
          personaGroupMap.forEach((grp) => {
            const ring = grp.getObjectByName("selectionRing") as THREE.Mesh;
            if (ring && ring.material instanceof THREE.MeshBasicMaterial) {
              ring.material.opacity = 0;
            }
          });
        } else {
          setIsHoveringDilemma(false);
          const hitRole = hitObj.userData?.personaRole;
          const cfg = BOARDROOM_PERSONAS.find((p) => p.roleKey === hitRole);
          setHoveredPersona(cfg || null);
          renderer.domElement.style.cursor = "pointer";

          // Highlight ring
          personaGroupMap.forEach((grp, key) => {
            const ring = grp.getObjectByName("selectionRing") as THREE.Mesh;
            if (ring && ring.material instanceof THREE.MeshBasicMaterial) {
              ring.material.opacity = key === hitRole ? 0.9 : 0;
            }
          });
        }
      } else {
        setIsHoveringDilemma(false);
        setHoveredPersona(null);
        renderer.domElement.style.cursor = "default";
        personaGroupMap.forEach((grp) => {
          const ring = grp.getObjectByName("selectionRing") as THREE.Mesh;
          if (ring && ring.material instanceof THREE.MeshBasicMaterial) {
            ring.material.opacity = 0;
          }
        });
      }
    };

    const handlePointerDown = (evt: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((evt.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((evt.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const targets: THREE.Object3D[] = [];
      personaGroupMap.forEach((g) => {
        g.traverse((child) => {
          if (child.userData?.isRaycastTarget) targets.push(child);
        });
      });
      dilemmaProjectorGroup.traverse((child) => {
        if (child.userData?.isRaycastTarget) targets.push(child);
      });

      const intersects = raycaster.intersectObjects(targets, false);
      if (intersects.length > 0) {
        const hitObj = intersects[0].object;
        if (hitObj.userData?.isDilemmaTarget) {
          handleOpenDilemmaModal();
        } else {
          const hitRole = hitObj.userData?.personaRole;
          if (hitRole) {
            handleOpenPersonaInteraction(hitRole);
          }
        }
      }
    };

    renderer.domElement.addEventListener("mousemove", handlePointerMove);
    renderer.domElement.addEventListener("pointerdown", handlePointerDown);

    // -----------------------------------------------------------------------
    // Animation Loop
    // -----------------------------------------------------------------------
    let animId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const dt = clock.getDelta();

      // Pulsing and spinning Dilemma Beacon
      if (beaconMesh) {
        beaconMesh.rotation.y += dt * 1.5;
        beaconMesh.rotation.x += dt * 0.5;
        beaconMesh.position.y = 0.6 + Math.sin(clock.getElapsedTime() * 3.0) * 0.06;
      }

      // Camera interpolation to target preset
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

    // Resize Observer
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

    // Cleanup
    return () => {
      cancelAnimationFrame(animId);
      resizeObserver.disconnect();
      renderer.domElement.removeEventListener("mousemove", handlePointerMove);
      renderer.domElement.removeEventListener("pointerdown", handlePointerDown);
      controls.dispose();
      renderer.dispose();
      scene.clear();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [activeQuality, lightingMode, handleOpenPersonaInteraction, handleOpenDilemmaModal]);

  return (
    <div
      data-testid="boardroom-3d-scene"
      className="relative h-full min-h-[520px] w-full overflow-hidden rounded-2xl border border-emerald-500/20 bg-slate-950"
    >
      {/* 3D Canvas Mount */}
      <div ref={mountRef} className="h-full w-full" />

      {/* Top HUD Controls Bar */}
      <div className="pointer-events-none absolute inset-x-0 top-0 z-20 flex items-center justify-between p-4">
        {/* Title Badge & Dilemma Pending Alert */}
        <div className="flex items-center gap-2">
          <div className="pointer-events-auto flex items-center gap-2 rounded-xl border border-white/10 bg-slate-950/80 px-3 py-1.5 backdrop-blur-md">
            <Building2 className="h-4 w-4 text-emerald-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-white">
              Executive Boardroom Suite
            </span>
            <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-mono text-emerald-300">
              3D PERSISTENT
            </span>
          </div>

          {/* Active Boardroom Dilemma Alert Pill */}
          {activeDilemma && activeDilemma.status === "open" && (
            <button
              type="button"
              data-testid="open-boardroom-dilemma-btn"
              onClick={handleOpenDilemmaModal}
              className="pointer-events-auto flex items-center gap-1.5 rounded-xl border border-amber-500/50 bg-amber-500/20 px-3 py-1.5 text-xs font-bold text-amber-300 backdrop-blur-md transition-all hover:bg-amber-500/30 animate-pulse shadow-lg shadow-amber-500/10"
            >
              <Flame className="h-3.5 w-3.5 text-amber-400" />
              <span>Boardroom Dilemma</span>
              <span className="rounded bg-amber-400/20 px-1.5 py-0.2 text-[9px] uppercase font-mono text-amber-200">
                {activeDilemma.urgency || "ACTIVE"}
              </span>
            </button>
          )}

          {/* Staff Market & Careers Action Button */}
          <button
            type="button"
            data-testid="open-staff-market-btn"
            onClick={() => setIsStaffModalOpen(true)}
            className="pointer-events-auto flex items-center gap-1.5 rounded-xl border border-emerald-500/40 bg-emerald-500/20 px-3 py-1.5 text-xs font-bold text-emerald-300 backdrop-blur-md transition-all hover:bg-emerald-500/30 shadow-lg shadow-emerald-500/10"
          >
            <Briefcase className="h-3.5 w-3.5 text-emerald-400" />
            <span>Staff Market & Careers</span>
          </button>

          {/* GM Delegation & Authority Action Button */}
          <button
            type="button"
            data-testid="open-gm-delegation-btn"
            onClick={() => setIsGmModalOpen(true)}
            className="pointer-events-auto flex items-center gap-1.5 rounded-xl border border-sky-500/40 bg-sky-500/20 px-3 py-1.5 text-xs font-bold text-sky-300 backdrop-blur-md transition-all hover:bg-sky-500/30 shadow-lg shadow-sky-500/10"
          >
            <Sliders className="h-3.5 w-3.5 text-sky-400" />
            <span>GM Delegation</span>
          </button>
        </div>

        {/* Lighting & Camera Presets */}
        <div className="pointer-events-auto flex items-center gap-2">
          {/* Day / Night Toggle */}
          <button
            type="button"
            data-testid="toggle-boardroom-lighting-btn"
            onClick={() => setLightingMode((m) => (m === "day" ? "night" : "day"))}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-slate-950/80 text-slate-300 transition-colors hover:bg-white/10 hover:text-white"
            title={`Switch to ${lightingMode === "day" ? "Night" : "Day"} Lighting`}
          >
            {lightingMode === "day" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4 text-amber-400" />}
          </button>

          {/* Camera Preset Buttons */}
          <div className="flex items-center gap-1 rounded-xl border border-white/10 bg-slate-950/80 p-1 backdrop-blur-md">
            {(Object.keys(CAMERA_PRESETS) as BoardroomCameraPreset[]).map((pkey) => (
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

      {/* Floating Persona Hover Tooltip */}
      {hoveredPersona && (
        <div
          data-testid="persona-hover-tooltip"
          className="pointer-events-none absolute bottom-20 left-1/2 z-30 -translate-x-1/2 rounded-xl border border-emerald-500/40 bg-slate-950/90 px-4 py-2 text-center shadow-xl backdrop-blur-md animate-fade-in"
        >
          <div className="flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-xs font-bold text-white">{hoveredPersona.name}</span>
            <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-300">
              {hoveredPersona.roleLabel}
            </span>
          </div>
          <p className="mt-0.5 text-[10px] text-slate-400">Click avatar to initiate executive dialogue</p>
        </div>
      )}

      {/* Floating Dilemma Projector Hover Tooltip */}
      {isHoveringDilemma && (
        <div
          data-testid="dilemma-hover-tooltip"
          className="pointer-events-none absolute bottom-20 left-1/2 z-30 -translate-x-1/2 rounded-xl border border-amber-500/40 bg-slate-950/90 px-4 py-2 text-center shadow-xl backdrop-blur-md animate-fade-in"
        >
          <div className="flex items-center gap-2">
            <Scale className="h-3.5 w-3.5 text-amber-400" />
            <span className="text-xs font-bold text-white">
              {activeDilemma?.title || "Boardroom Strategic Dilemma"}
            </span>
            <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-amber-300">
              {activeDilemma?.urgency?.toUpperCase() || "PENDING"}
            </span>
          </div>
          <p className="mt-0.5 text-[10px] text-slate-400">
            Click holographic projector to convene emergency boardroom arbitration
          </p>
        </div>
      )}

      {/* Bottom Persona Roster Quick-Select Bar */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 z-20 flex items-center justify-between border-t border-white/10 bg-gradient-to-t from-slate-950 via-slate-950/80 to-transparent p-4">
        <div className="pointer-events-auto flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Convened Leadership:
          </span>
          {BOARDROOM_PERSONAS.map((p) => (
            <button
              key={p.roleKey}
              type="button"
              data-testid={`select-persona-pill-${p.roleKey}`}
              onClick={() => handleOpenPersonaInteraction(p.roleKey)}
              className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-slate-900/80 px-2.5 py-1 text-xs text-slate-200 transition-all hover:border-emerald-500/50 hover:bg-emerald-500/10 hover:text-emerald-300"
            >
              <Users className="h-3.5 w-3.5 text-emerald-400" />
              <span>{p.name}</span>
              <span className="text-[10px] text-slate-400">({p.roleLabel})</span>
            </button>
          ))}
        </div>
      </div>

      {/* Spatial Interaction Modal */}
      <PersonaSpatialInteractionModal
        clubId={clubId}
        personaRole={selectedPersonaRole}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onOpenGmDelegation={() => setIsGmModalOpen(true)}
        onInteractionComplete={(res) => {
          // Additional custom callback handling if required
        }}
      />

      {/* Boardroom Dilemma Modal */}
      <BoardroomDilemmaModal
        clubId={clubId}
        isOpen={isDilemmaModalOpen}
        onClose={() => setIsDilemmaModalOpen(false)}
      />

      {/* Staff Employment & Career Market Modal */}
      <StaffEmploymentModal
        clubId={clubId}
        isOpen={isStaffModalOpen}
        onClose={() => setIsStaffModalOpen(false)}
      />

      {/* GM Delegation & Authority Matrix Modal */}
      <GmDelegationModal
        clubId={clubId}
        isOpen={isGmModalOpen}
        onClose={() => setIsGmModalOpen(false)}
      />
    </div>
  );
};

// Register custom Three.js renderer in GtexSceneRegistry for boardroom_meeting
GtexSceneRegistry.registerRenderer("boardroom_meeting", BoardroomScene);
