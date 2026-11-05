import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import {
  Building2,
  Compass,
  Sun,
  Moon,
  Layers,
  Box,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Sparkles,
  Users,
  Briefcase,
  Sprout,
  HeartPulse,
  Coins,
  Send,
  ArrowUpRight,
  ShieldAlert,
  Hammer,
  Award,
  Activity,
  History,
  Sliders,
  AlertTriangle,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt } from "@/lib/owner";
import { publicUrl } from "@/lib/publicPath";
import {
  clubBriefingResolveDilemmaEndpoint,
  clubExecuteOperationalDecisionEndpoint,
  clubOperationsHubEndpoint,
  clubLivingWorldTimelineEndpoint,
  clubCreateDirectiveEndpoint,
  clubResolveEventEndpoint,
  type ClubOperationsHubPayload,
  type OperationalRecommendation,
  type OperationsHubDestination,
  type LivingWorldEvent,
  type LivingWorldDirective,
  type LivingWorldRelationship,
  type LivingWorldTimelineItem,
  type LivingWorldTimelineResponse,
} from "@/lib/ownerBriefing";

function detectWebGLAvailable(): boolean {
  if (typeof window === "undefined" || typeof document === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl2") || canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
    return Boolean(gl);
  } catch {
    return false;
  }
}

const DESTINATION_ICONS: Record<string, React.ReactNode> = {
  executive_office: <Building2 size={15} />,
  managers_office: <Users size={15} />,
  general_managers_office: <Briefcase size={15} />,
  academy_department: <Sprout size={15} />,
  medical_department: <HeartPulse size={15} />,
  finance_commercial_office: <Coins size={15} />,
};

const OVERVIEW_CAMERA_POS: [number, number, number] = [0, 34, 42];
const OVERVIEW_CAMERA_TARGET: [number, number, number] = [0, 1.5, 0];

export function ClubOperationsCentre3D({
  clubId,
  selectedDestinationKey,
  onSelectDestinationKey,
  onHubUpdated,
}: {
  clubId: string;
  selectedDestinationKey?: string;
  onSelectDestinationKey?: (key: string) => void;
  onHubUpdated?: () => void;
}) {
  const queryClient = useQueryClient();
  const [internalDestKey, setInternalDestKey] = useState<string>("executive_office");
  const activeDestKey = selectedDestinationKey || internalDestKey;
  const setActiveDestKey = (key: string) => {
    setInternalDestKey(key);
    onSelectDestinationKey?.(key);
  };

  const [cameraMode, setCameraMode] = useState<"room" | "overview">("room");
  const [activeHotspotId, setActiveHotspotId] = useState<string | null>(null);
  const [lightingMode, setLightingMode] = useState<"day" | "night">("day");
  const [renderMode, setRenderMode] = useState<"3d" | "2d">(() => (detectWebGLAvailable() ? "3d" : "2d"));
  const [webglStatus, setWebglStatus] = useState<"initializing" | "ready" | "fallback">("initializing");
  const [loadedGlbCount, setLoadedGlbCount] = useState<number>(0);
  const [failedGlbModels, setFailedGlbModels] = useState<string[]>([]);

  // Interactive department action states
  const [busyDecisionId, setBusyDecisionId] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [winBonusAmount, setWinBonusAmount] = useState<number>(450);
  const [staffMessageText, setStaffMessageText] = useState<string>("");
  const [sendingChat, setSendingChat] = useState<boolean>(false);

  // Phase 2.4 Living World state
  const [showTimelineDrawer, setShowTimelineDrawer] = useState<boolean>(false);
  const [timelineCategoryFilter, setTimelineCategoryFilter] = useState<string>("all");
  const [timelineSeverityFilter, setTimelineSeverityFilter] = useState<string>("all");
  const [timelineStatusFilter, setTimelineStatusFilter] = useState<string>("all");
  const [timelineLimit] = useState<number>(8);
  const [timelineOffset, setTimelineOffset] = useState<number>(0);
  const [showDirectiveModal, setShowDirectiveModal] = useState<boolean>(false);
  const [directiveTitle, setDirectiveTitle] = useState<string>("");
  const [directiveInstruction, setDirectiveInstruction] = useState<string>("");
  const [directiveDeadline, setDirectiveDeadline] = useState<number>(7);
  const [busyEventId, setBusyEventId] = useState<string | null>(null);

  const {
    data: timelineResponse,
    isLoading: isTimelineLoading,
    isFetching: isTimelineFetching,
    isError: isTimelineError,
    error: timelineErrorObj,
    refetch: refetchTimeline,
  } = useQuery<LivingWorldTimelineResponse | null>({
    queryKey: [
      "club-living-world-timeline",
      clubId,
      timelineCategoryFilter,
      timelineSeverityFilter,
      timelineStatusFilter,
      timelineLimit,
      timelineOffset,
    ],
    queryFn: async () => {
      if (!clubId) return null;
      const params: Record<string, string | number> = {
        limit: timelineLimit,
        offset: timelineOffset,
      };
      if (timelineCategoryFilter !== "all") params.category = timelineCategoryFilter;
      if (timelineSeverityFilter !== "all") params.severity = timelineSeverityFilter;
      if (timelineStatusFilter !== "all") params.status = timelineStatusFilter;
      const { data } = await api.get(clubLivingWorldTimelineEndpoint(clubId), { params });
      return data as LivingWorldTimelineResponse;
    },
    enabled: Boolean(clubId) && showTimelineDrawer,
  });

  const {
    data: hub,
    isLoading,
    refetch,
  } = useQuery<ClubOperationsHubPayload | null>({
    queryKey: ["club-operations-hub", clubId],
    queryFn: async () => {
      if (!clubId) return null;
      const { data } = await api.get(clubOperationsHubEndpoint(clubId));
      return data as ClubOperationsHubPayload;
    },
    enabled: Boolean(clubId),
  });

  const destinations = useMemo(() => hub?.destinations || [], [hub?.destinations]);
  const activeDestination: OperationsHubDestination | undefined = useMemo(
    () => destinations.find((d) => d.destination_key === activeDestKey) || destinations[0],
    [destinations, activeDestKey]
  );

  // Sync hotspot when switching destination
  useEffect(() => {
    if (activeDestination?.hotspots?.length) {
      setActiveHotspotId(activeDestination.hotspots[0].id);
    } else {
      setActiveHotspotId(null);
    }
  }, [activeDestination?.destination_key]);

  // Three.js refs
  const mountRef = useRef<HTMLDivElement | null>(null);
  const cameraGoalPosRef = useRef<THREE.Vector3>(new THREE.Vector3(...OVERVIEW_CAMERA_POS));
  const cameraGoalTargetRef = useRef<THREE.Vector3>(new THREE.Vector3(...OVERVIEW_CAMERA_TARGET));
  const isTransitioningRef = useRef<boolean>(true);
  const roomGroupsRef = useRef<Map<string, THREE.Group>>(new Map());
  const activeDestRef = useRef<string>(activeDestKey);
  activeDestRef.current = activeDestKey;
  const lightingRef = useRef<"day" | "night">(lightingMode);
  lightingRef.current = lightingMode;

  // Update camera target whenever activeDestination or cameraMode changes
  useEffect(() => {
    if (cameraMode === "overview" || !activeDestination) {
      cameraGoalPosRef.current.set(...OVERVIEW_CAMERA_POS);
      cameraGoalTargetRef.current.set(...OVERVIEW_CAMERA_TARGET);
      isTransitioningRef.current = true;
      return;
    }
    const [cx, cy, cz] = activeDestination.camera_position;
    const [tx, ty, tz] = activeDestination.camera_target;
    cameraGoalPosRef.current.set(cx, cy, cz);
    cameraGoalTargetRef.current.set(tx, ty, tz);
    isTransitioningRef.current = true;
  }, [activeDestination, cameraMode]);

  // Build and manage the Three.js 3D Club Operations Headquarters scene
  useEffect(() => {
    if (renderMode !== "3d") {
      setWebglStatus("fallback");
      return;
    }
    const container = mountRef.current;
    if (!container || destinations.length === 0) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        powerPreference: "high-performance",
        preserveDrawingBuffer: true,
      });
    } catch {
      setWebglStatus("fallback");
      setRenderMode("2d");
      return;
    }

    const width = Math.max(320, container.clientWidth || 960);
    const height = Math.max(380, container.clientHeight || 520);
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;

    container.innerHTML = "";
    renderer.domElement.setAttribute("data-testid", "club-operations-3d-canvas");
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.display = "block";
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(lightingRef.current === "day" ? 0x091526 : 0x040914);
    scene.fog = new THREE.FogExp2(lightingRef.current === "day" ? 0x091526 : 0x040914, 0.0085);

    const pmrem = new THREE.PMREMGenerator(renderer);
    const envTex = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environment = envTex;

    const camera = new THREE.PerspectiveCamera(44, width / height, 0.5, 260);
    camera.position.copy(cameraGoalPosRef.current);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.maxPolarAngle = Math.PI / 2 - 0.04;
    controls.minDistance = 6;
    controls.maxDistance = 85;
    controls.target.copy(cameraGoalTargetRef.current);

    const stopAutoTransition = () => {
      isTransitioningRef.current = false;
    };
    controls.addEventListener("start", stopAutoTransition);

    // Lighting rig
    const hemiLight = new THREE.HemisphereLight(0xdbeafe, 0x0f172a, lightingRef.current === "day" ? 1.1 : 0.45);
    scene.add(hemiLight);

    const sunLight = new THREE.DirectionalLight(
      lightingRef.current === "day" ? 0xfffbeb : 0x60a5fa,
      lightingRef.current === "day" ? 2.1 : 0.9
    );
    sunLight.position.set(28, 42, 24);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.set(1024, 1024);
    sunLight.shadow.camera.near = 2;
    sunLight.shadow.camera.far = 120;
    const d = 38;
    sunLight.shadow.camera.left = -d;
    sunLight.shadow.camera.right = d;
    sunLight.shadow.camera.top = d;
    sunLight.shadow.camera.bottom = -d;
    scene.add(sunLight);

    // Architectural HQ Plaza Ground & Central Rotunda
    const plazaGeo = new THREE.CylinderGeometry(34, 36, 0.8, 64);
    const plazaMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      roughness: 0.55,
      metalness: 0.25,
    });
    const plazaMesh = new THREE.Mesh(plazaGeo, plazaMat);
    plazaMesh.position.y = -0.4;
    plazaMesh.receiveShadow = true;
    scene.add(plazaMesh);

    const gridHelper = new THREE.GridHelper(64, 32, 0x1e3a8a, 0x0f2547);
    gridHelper.position.y = 0.02;
    scene.add(gridHelper);

    // Central Club Crest Atrium Ring
    const rotundaRing = new THREE.Mesh(
      new THREE.RingGeometry(4.2, 5.1, 48),
      new THREE.MeshBasicMaterial({ color: 0x38bdf8, side: THREE.DoubleSide, transparent: true, opacity: 0.45 })
    );
    rotundaRing.rotation.x = -Math.PI / 2;
    rotundaRing.position.y = 0.05;
    scene.add(rotundaRing);

    const pickables: THREE.Object3D[] = [];
    const loader = new GLTFLoader();
    let mounted = true;
    let loadedModels = 0;
    roomGroupsRef.current.clear();

    // Build each of the 6 Operational Destination Wings
    destinations.forEach((dest) => {
      const group = new THREE.Group();
      const [rx, ry, rz] = dest.position_3d;
      group.position.set(rx, ry, rz);
      group.userData = { destinationKey: dest.destination_key };
      roomGroupsRef.current.set(dest.destination_key, group);

      const accent = new THREE.Color(dest.accent_color || "#38bdf8");

      // Architectural Room Floor Pad
      const padGeo = new THREE.BoxGeometry(10.5, 0.32, 8.5);
      const padMat = new THREE.MeshStandardMaterial({
        color: 0x111c33,
        roughness: 0.35,
        metalness: 0.4,
      });
      const padMesh = new THREE.Mesh(padGeo, padMat);
      padMesh.position.y = 0.16;
      padMesh.receiveShadow = true;
      padMesh.userData = { destinationKey: dest.destination_key };
      group.add(padMesh);
      pickables.push(padMesh);

      // Luminous Room Perimeter Frame
      const borderGeo = new THREE.EdgesGeometry(new THREE.BoxGeometry(10.6, 0.36, 8.6));
      const borderMat = new THREE.LineBasicMaterial({ color: accent });
      const borderLines = new THREE.LineSegments(borderGeo, borderMat);
      borderLines.position.y = 0.18;
      borderLines.name = "room-border";
      group.add(borderLines);

      // Glass Cutaway Partition Walls (Back & Side)
      const glassMat = new THREE.MeshPhysicalMaterial({
        color: accent,
        transparent: true,
        opacity: 0.16,
        roughness: 0.15,
        metalness: 0.1,
      });
      const backWall = new THREE.Mesh(new THREE.BoxGeometry(10.4, 3.2, 0.14), glassMat);
      backWall.position.set(0, 1.75, -4.15);
      backWall.userData = { destinationKey: dest.destination_key };
      group.add(backWall);
      pickables.push(backWall);

      // Interior Command Desk / Tactical Table
      const deskMesh = new THREE.Mesh(
        new THREE.BoxGeometry(3.2, 0.85, 1.6),
        new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.3, metalness: 0.6 })
      );
      deskMesh.position.set(0, 0.75, 0.3);
      deskMesh.castShadow = true;
      deskMesh.userData = { destinationKey: dest.destination_key };
      group.add(deskMesh);
      pickables.push(deskMesh);

      // Holographic Display Screen above Desk
      const holoMesh = new THREE.Mesh(
        new THREE.PlaneGeometry(2.6, 1.1),
        new THREE.MeshBasicMaterial({
          color: accent,
          transparent: true,
          opacity: 0.42,
          side: THREE.DoubleSide,
        })
      );
      holoMesh.position.set(0, 2.05, 0.3);
      holoMesh.userData = { destinationKey: dest.destination_key };
      group.add(holoMesh);
      pickables.push(holoMesh);

      // Dedicated Room PointLight
      const roomLight = new THREE.PointLight(accent, 2.2, 16);
      roomLight.position.set(0, 4.2, 0);
      group.add(roomLight);

      // Interactive Hotspot Beacons inside the Room
      (dest.hotspots || []).forEach((hs) => {
        const [hx, hy, hz] = hs.offset;
        const beaconGroup = new THREE.Group();
        beaconGroup.position.set(hx, hy, hz);

        const orb = new THREE.Mesh(
          new THREE.SphereGeometry(0.36, 20, 20),
          new THREE.MeshStandardMaterial({
            color: accent,
            emissive: accent,
            emissiveIntensity: 0.85,
            roughness: 0.2,
          })
        );
        orb.userData = {
          destinationKey: dest.destination_key,
          hotspotId: hs.id,
          hotspotLabel: hs.label,
        };
        beaconGroup.add(orb);
        pickables.push(orb);

        const stem = new THREE.Mesh(
          new THREE.CylinderGeometry(0.05, 0.05, Math.max(0.4, hy), 8),
          new THREE.MeshBasicMaterial({ color: accent, transparent: true, opacity: 0.5 })
        );
        stem.position.y = -hy / 2;
        beaconGroup.add(stem);

        group.add(beaconGroup);
      });

      // Corridor Light Path to Central Atrium
      const distToCenter = Math.hypot(rx, rz);
      if (distToCenter > 1) {
        const pathGeo = new THREE.BoxGeometry(0.45, 0.04, distToCenter * 0.65);
        const pathMat = new THREE.MeshBasicMaterial({ color: accent, transparent: true, opacity: 0.35 });
        const pathMesh = new THREE.Mesh(pathGeo, pathMat);
        pathMesh.position.set(-rx * 0.35, 0.05, -rz * 0.35);
        pathMesh.lookAt(new THREE.Vector3(0, 0.05, 0));
        group.add(pathMesh);
      }

      // Load Certified Production GLB Model as Architectural Wing Monument behind/integrated with the Room
      const rawGlbUrl = dest.glb_model || "/models/campus/club_hq.glb";
      const glbUrl = publicUrl(rawGlbUrl);
      loader.load(
        glbUrl,
        (gltf) => {
          if (!mounted) return;
          const model = gltf.scene.clone(true);
          const box = new THREE.Box3().setFromObject(model);
          const size = new THREE.Vector3();
          const center = new THREE.Vector3();
          box.getSize(size);
          box.getCenter(center);

          const maxDim = Math.max(size.x, size.y, size.z, 1);
          const targetSpan = 5.4;
          const scale = targetSpan / maxDim;
          model.scale.setScalar(scale);

          const scaledBox = new THREE.Box3().setFromObject(model);
          const scaledCenter = new THREE.Vector3();
          scaledBox.getCenter(scaledCenter);

          model.position.x = -scaledCenter.x;
          model.position.z = -scaledCenter.z - 1.5;
          model.position.y = -scaledBox.min.y + 0.32;

          model.traverse((child) => {
            if ((child as THREE.Mesh).isMesh) {
              const m = child as THREE.Mesh;
              m.castShadow = true;
              m.receiveShadow = true;
              m.userData = { destinationKey: dest.destination_key };
              pickables.push(m);
            }
          });

          group.add(model);
          loadedModels += 1;
          setLoadedGlbCount(loadedModels);
        },
        undefined,
        (err) => {
          if (!mounted) return;
          console.warn(`[ClubOperationsCentre3D] Failed to load GLB for ${dest.destination_key}: ${glbUrl}`, err);
          setFailedGlbModels((prev) => (prev.includes(dest.destination_key) ? prev : [...prev, dest.destination_key]));

          // Procedural wireframe fallback mesh so destination remains interactive and visible
          const fallbackGeo = new THREE.BoxGeometry(4.2, 2.8, 3.2);
          const fallbackMat = new THREE.MeshStandardMaterial({
            color: accent,
            wireframe: true,
            transparent: true,
            opacity: 0.7,
            emissive: accent,
            emissiveIntensity: 0.2,
          });
          const fallbackMesh = new THREE.Mesh(fallbackGeo, fallbackMat);
          fallbackMesh.name = `fallback-wireframe-${dest.destination_key}`;
          fallbackMesh.position.set(0, 1.4, -1.5);
          fallbackMesh.userData = { destinationKey: dest.destination_key, isFallbackWireframe: true };
          fallbackMesh.castShadow = true;
          fallbackMesh.receiveShadow = true;
          pickables.push(fallbackMesh);
          group.add(fallbackMesh);
        }
      );

      scene.add(group);
    });

    // Raycaster for clicking 3D rooms & hotspots
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let downX = 0;
    let downY = 0;

    const onPointerDown = (ev: MouseEvent) => {
      downX = ev.clientX;
      downY = ev.clientY;
    };

    const onPointerUp = (ev: MouseEvent) => {
      if (Math.hypot(ev.clientX - downX, ev.clientY - downY) > 6) return;
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hits = raycaster.intersectObjects(pickables, true);
      if (hits.length > 0) {
        let obj: THREE.Object3D | null = hits[0].object;
        while (obj && !obj.userData?.destinationKey) {
          obj = obj.parent;
        }
        if (obj?.userData?.destinationKey) {
          const destKey = String(obj.userData.destinationKey);
          setCameraMode("room");
          setActiveDestKey(destKey);
          if (obj.userData.hotspotId) {
            setActiveHotspotId(String(obj.userData.hotspotId));
          }
        }
      }
    };

    renderer.domElement.addEventListener("pointerdown", onPointerDown);
    renderer.domElement.addEventListener("pointerup", onPointerUp);

    const onResize = () => {
      if (!container) return;
      const w = Math.max(320, container.clientWidth || 960);
      const h = Math.max(380, container.clientHeight || 520);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener("resize", onResize);

    setWebglStatus("ready");

    if (typeof window !== "undefined") {
      (window as unknown as { __GTEX_OPERATIONS_3D__?: unknown }).__GTEX_OPERATIONS_3D__ = {
        scene,
        roomGroups: roomGroupsRef.current,
        camera,
        renderer,
      };
    }

    let animFrameId = 0;
    const animate = () => {
      animFrameId = requestAnimationFrame(animate);

      // Smoothly interpolate camera & target during room transitions without reloading scene
      if (isTransitioningRef.current) {
        camera.position.lerp(cameraGoalPosRef.current, 0.08);
        controls.target.lerp(cameraGoalTargetRef.current, 0.08);
        if (
          camera.position.distanceTo(cameraGoalPosRef.current) < 0.15 &&
          controls.target.distanceTo(cameraGoalTargetRef.current) < 0.15
        ) {
          isTransitioningRef.current = false;
        }
      }

      // Highlight selected room wing
      roomGroupsRef.current.forEach((grp, key) => {
        const isSelected = key === activeDestRef.current;
        grp.position.y = THREE.MathUtils.lerp(grp.position.y, isSelected ? 0.35 : 0.0, 0.1);
      });

      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      mounted = false;
      cancelAnimationFrame(animFrameId);
      window.removeEventListener("resize", onResize);
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      renderer.domElement.removeEventListener("pointerup", onPointerUp);
      controls.dispose();
      envTex.dispose();
      pmrem.dispose();
      renderer.dispose();
      if (typeof window !== "undefined") {
        delete (window as unknown as { __GTEX_OPERATIONS_3D__?: unknown }).__GTEX_OPERATIONS_3D__;
      }
    };
  }, [renderMode, destinations.length, lightingMode]);

  const invalidateAll = async () => {
    await refetch();
    queryClient.invalidateQueries({ queryKey: ["club-living-world-timeline", clubId] });
    if (showTimelineDrawer) {
      await refetchTimeline();
    }
    queryClient.invalidateQueries({ queryKey: ["owner-daily-briefing", clubId] });
    queryClient.invalidateQueries({ queryKey: ["owner", "control-center"] });
    onHubUpdated?.();
  };

  // --- Authoritative Owner Actions ---
  const handleExecuteDecision = async (decision: OperationalRecommendation, action: "approve" | "reject") => {
    setBusyDecisionId(`${decision.decision_id}:${action}`);
    try {
      const { data } = await api.post(clubExecuteOperationalDecisionEndpoint(clubId, decision.decision_id), {
        action,
        note: `Executed from ${activeDestination?.label || "Club Operations Centre"}`,
      });
      await invalidateAll();
      toast.success(data?.outcome || `Decision ${action}d.`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyDecisionId(null);
    }
  };

  const handleResolveDilemma = async (choiceId: string) => {
    setBusyAction(`dilemma:${choiceId}`);
    try {
      const { data } = await api.post(clubBriefingResolveDilemmaEndpoint(clubId), { choice_id: choiceId });
      await invalidateAll();
      toast.success(data?.outcome || "Boardroom dilemma resolved.");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyAction(null);
    }
  };

  const handleSetMentality = async (mentality: "defensive" | "balanced" | "attacking") => {
    setBusyAction(`mentality:${mentality}`);
    try {
      await api.put(`/owner/clubs/${encodeURIComponent(clubId)}/mentality`, { mentality });
      await invalidateAll();
      toast.success(`First-team tactical mentality set to '${mentality.toUpperCase()}'.`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyAction(null);
    }
  };

  const handlePledgeWinBonus = async () => {
    setBusyAction("win-bonus");
    try {
      await api.post(`/owner/clubs/${encodeURIComponent(clubId)}/win-bonus`, {
        amount_gtex: winBonusAmount,
        note: "Pledged by Owner in Manager's Office",
      });
      await invalidateAll();
      toast.success(`Pledged ${fmt(winBonusAmount)} GTEX win bonus for the squad.`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyAction(null);
    }
  };

  const handleUpdateDelegation = async (style: "hands_on" | "balanced" | "delegating") => {
    setBusyAction(`delegation:${style}`);
    try {
      await api.put(`/owner/clubs/${encodeURIComponent(clubId)}/delegation`, {
        delegation_style: style,
        auto_renew_contracts: style !== "hands_on",
        auto_scout_youth: true,
        auto_manage_ticket_PR: style === "delegating",
        wage_cap_pct: style === "hands_on" ? 60 : 70,
      });
      await invalidateAll();
      toast.success(`General Manager delegation policy updated to '${style.replace("_", " ")}'.`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyAction(null);
    }
  };

  const handleUpgradeFacility = async (kind: string) => {
    setBusyAction(`facility:${kind}`);
    try {
      await api.post(`/owner/clubs/${encodeURIComponent(clubId)}/facilities/${encodeURIComponent(kind)}/upgrade`);
      await invalidateAll();
      toast.success(`Upgraded ${kind} facility level.`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyAction(null);
    }
  };

  const handleAdvanceCampusStage = async (instanceId: string) => {
    setBusyAction(`campus:${instanceId}`);
    try {
      await api.post(`/owner/clubs/${encodeURIComponent(clubId)}/campus/construct`, {
        operation: "advance_stage",
        instance_id: instanceId,
      });
      await invalidateAll();
      toast.success("Advanced campus construction stage.");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyAction(null);
    }
  };

  const handleAcademyIntake = async () => {
    setBusyAction("academy-intake");
    try {
      await api.post(`/owner/clubs/${encodeURIComponent(clubId)}/academy/intake`);
      await invalidateAll();
      toast.success("Commissioned new youth academy regen intake.");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyAction(null);
    }
  };

  const handlePromoteYouthPlayer = async (playerId: string, playerName: string) => {
    setBusyAction(`promote:${playerId}`);
    try {
      await api.post(
        `/owner/clubs/${encodeURIComponent(clubId)}/players/${encodeURIComponent(playerId)}/squad-status`,
        { status: "first_team" }
      );
      await invalidateAll();
      toast.success(`Promoted ${playerName} to First-Team senior squad.`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyAction(null);
    }
  };

  const handleOfferYouthContract = async (playerId: string, playerName: string, wage: number) => {
    setBusyAction(`contract:${playerId}`);
    try {
      await api.post(
        `/owner/clubs/${encodeURIComponent(clubId)}/players/${encodeURIComponent(playerId)}/contract`,
        {
          wage_gtex: Math.max(50, Math.round(wage * 1.25)),
          years: 4,
          promise_role: "prospect",
        }
      );
      await invalidateAll();
      toast.success(`Signed ${playerName} to improved long-term contract.`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyAction(null);
    }
  };

  const handleSignSponsorOffer = async (offerId: string) => {
    setBusyAction(`sponsor:${offerId}`);
    try {
      await api.post(`/owner/clubs/${encodeURIComponent(clubId)}/sponsors/sign`, { offer_id: offerId });
      await invalidateAll();
      toast.success("Signed commercial sponsorship contract.");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyAction(null);
    }
  };

  const handleSendStaffChat = async (roleKey: string) => {
    if (!staffMessageText.trim()) return;
    setSendingChat(true);
    try {
      await api.post(`/owner/clubs/${encodeURIComponent(clubId)}/staff/chat`, {
        role: roleKey,
        message: staffMessageText.trim(),
        topic: activeHotspotId || "operations",
      });
      setStaffMessageText("");
      await invalidateAll();
      toast.success("Executive directive logged with department lead.");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setSendingChat(false);
    }
  };

  const handleIssueDirective = async () => {
    if (!directiveTitle.trim() || !directiveInstruction.trim()) {
      toast.error("Please enter both title and instruction for the directive.");
      return;
    }
    const deptMap: Record<string, string> = {
      managers_office: "manager",
      medical_department: "medical",
      academy_department: "academy",
      finance_commercial_office: "finance",
      general_managers_office: "scouting",
      executive_office: "executive",
    };
    const targetDept = deptMap[activeDestination.destination_key] || "executive";
    try {
      await api.post(clubCreateDirectiveEndpoint(clubId), {
        department: targetDept,
        directive_key: `dir_${Date.now()}`,
        title: directiveTitle.trim(),
        instruction: directiveInstruction.trim(),
        deadline_days: directiveDeadline,
      });
      setDirectiveTitle("");
      setDirectiveInstruction("");
      setShowDirectiveModal(false);
      await invalidateAll();
      toast.success(`Directive issued to ${activeDestination.staff_lead.name}`);
    } catch (err) {
      toast.error(errMsg(err));
    }
  };

  const handleResolveEvent = async (eventId: string, actionKey: string) => {
    setBusyEventId(`${eventId}:${actionKey}`);
    try {
      await api.post(clubResolveEventEndpoint(clubId, eventId), {
        action: actionKey,
      });
      await invalidateAll();
      toast.success("Living world event action executed");
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusyEventId(null);
    }
  };

  if (isLoading && !hub) {
    return (
      <section
        data-testid="living-club-management-centre-loading"
        className="rounded-2xl border border-sky-400/20 bg-[#060d1a] p-6 text-slate-300"
      >
        <div className="flex items-center gap-2 text-sm font-bold text-sky-300">
          <RefreshCw size={16} className="animate-spin" />
          <span>Initialising 3D Living Club Management Centre…</span>
        </div>
      </section>
    );
  }

  if (!hub || !activeDestination) return null;

  const rpt = activeDestination.report || {};
  const openDeptDecisions = activeDestination.open_decisions || [];
  const allOpenDeptDecisions = hub.actionable_decisions?.department_decisions || [];
  const dilemma = hub.daily_briefing?.boardroom_dilemma;

  return (
    <section
      data-testid="living-club-management-centre"
      className="rounded-2xl border border-sky-500/30 bg-gradient-to-b from-[#071326] via-[#060f1f] to-[#040914] p-4 sm:p-6 shadow-2xl space-y-5"
    >
      {/* Top Command Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="gx-eyebrow !m-0 text-sky-300">
              Living Club Management Centre · 3D Daily Operations Hub
            </span>
            <span className="gx-mono rounded border border-emerald-500/30 bg-emerald-950/60 px-2 py-0.5 text-[10px] font-bold text-emerald-300">
              World Day {hub.club.world_day}
            </span>
          </div>
          <h2 className="mt-1 text-xl sm:text-2xl font-black text-white tracking-tight">
            {hub.club.club_name} · Executive Headquarters
          </h2>
          <p className="text-xs text-slate-400">
            Navigate 6 operational departments in 3D, inspect staff reports, and execute authoritative club decisions.
          </p>
        </div>

        {/* Viewport & Camera Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            data-testid="toggle-camera-overview"
            onClick={() => setCameraMode((m) => (m === "overview" ? "room" : "overview"))}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-bold uppercase transition ${
              cameraMode === "overview"
                ? "border-amber-400/60 bg-amber-500/20 text-amber-200"
                : "border-white/15 bg-white/5 text-slate-200 hover:bg-white/10"
            }`}
          >
            <Compass size={13} />
            <span>{cameraMode === "overview" ? "Room Focus" : "HQ Aerial Cutaway"}</span>
          </button>

          <button
            type="button"
            data-testid="toggle-lighting-mode"
            onClick={() => setLightingMode((l) => (l === "day" ? "night" : "day"))}
            className="inline-flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-bold uppercase text-slate-200 hover:bg-white/10"
          >
            {lightingMode === "day" ? <Moon size={13} /> : <Sun size={13} />}
            <span>{lightingMode === "day" ? "Floodlit Night" : "Daylight"}</span>
          </button>

          <button
            type="button"
            data-testid="toggle-render-mode"
            onClick={() => setRenderMode((r) => (r === "3d" ? "2d" : "3d"))}
            className="inline-flex items-center gap-1.5 rounded-lg border border-sky-400/40 bg-sky-950/50 px-3 py-1.5 text-xs font-bold uppercase text-sky-200 hover:bg-sky-900/60"
          >
            {renderMode === "3d" ? <Layers size={13} /> : <Box size={13} />}
            <span>{renderMode === "3d" ? "2D Floorplan" : "3D WebGL HQ"}</span>
          </button>

          <button
            type="button"
            data-testid="toggle-living-world-timeline"
            onClick={() => setShowTimelineDrawer((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-purple-400/40 bg-purple-950/50 px-3 py-1.5 text-xs font-bold uppercase text-purple-200 hover:bg-purple-900/60"
          >
            <Activity size={13} />
            <span>Living World ({hub?.living_world?.active_events_count || 0})</span>
          </button>

          <Link
            to="/app/campus"
            className="inline-flex items-center gap-1 rounded-lg border border-emerald-500/40 bg-emerald-950/40 px-3 py-1.5 text-xs font-bold uppercase text-emerald-200 hover:bg-emerald-900/50"
          >
            <span>Exterior Campus Grid</span>
            <ArrowUpRight size={13} />
          </Link>
        </div>
      </div>

      {/* 6 Operational Destination Selector Pills */}
      <div
        data-testid="operations-destination-selector"
        className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2"
      >
        {destinations.map((dest) => {
          const isSelected = dest.destination_key === activeDestination.destination_key;
          return (
            <button
              key={dest.destination_key}
              type="button"
              data-testid={`destination-tab-${dest.destination_key}`}
              onClick={() => {
                setCameraMode("room");
                setActiveDestKey(dest.destination_key);
              }}
              className={`group relative flex flex-col justify-between rounded-xl border p-3 text-left transition ${
                isSelected
                  ? "border-sky-400 bg-sky-950/60 shadow-lg shadow-sky-950/50"
                  : "border-white/10 bg-black/40 hover:border-white/25 hover:bg-white/5"
              }`}
            >
              <div className="flex items-center justify-between gap-1">
                <span
                  className="inline-flex items-center gap-1.5 text-xs font-black uppercase tracking-wider"
                  style={{ color: dest.accent_color }}
                >
                  {DESTINATION_ICONS[dest.destination_key] || <Building2 size={14} />}
                  <span className="truncate">{dest.short_label}</span>
                </span>
                <div className="flex items-center gap-1">
                  {((dest.active_events_count || 0) > 0 || (dest.active_directives_count || 0) > 0) && (
                    <span
                      data-testid={`dest-activity-badge-${dest.destination_key}`}
                      className="flex items-center gap-1 rounded-full bg-cyan-500/20 border border-cyan-400/50 px-1.5 py-0.2 text-[9px] font-bold text-cyan-300"
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
                      {(dest.active_events_count || 0) + (dest.active_directives_count || 0)}
                    </span>
                  )}
                  {dest.open_decisions_count > 0 && (
                    <span className="gx-mono rounded-full bg-amber-500/20 border border-amber-400/50 px-1.5 py-0.2 text-[10px] font-black text-amber-300">
                      {dest.open_decisions_count}
                    </span>
                  )}
                </div>
              </div>
              <div className="mt-2">
                <p className="text-[11px] font-bold text-white truncate">{dest.staff_lead.name}</p>
                <p className="text-[10px] text-slate-400 truncate">{dest.staff_lead.role_label}</p>
              </div>
            </button>
          );
        })}
      </div>

      {/* Main Split View: 3D WebGL / 2D Architectural Viewport (Left) + Contextual Department Operations Panel (Right) */}
      <div className="grid gap-5 lg:grid-cols-12">
        {/* Left 7 cols: Interactive 3D Environment or 2D Floorplan */}
        <div className="lg:col-span-7 flex flex-col gap-3">
          <div className="relative h-[430px] sm:h-[500px] w-full overflow-hidden rounded-2xl border border-white/15 bg-[#050b16] shadow-inner">
            {renderMode === "3d" ? (
              <div ref={mountRef} className="h-full w-full" />
            ) : (
              /* Non-WebGL / 2D Interactive Architectural Floorplan Fallback */
              <div
                data-testid="club-operations-2d-floorplan"
                className="flex h-full w-full flex-col justify-between bg-gradient-to-br from-[#071224] via-[#091930] to-[#050c18] p-4 sm:p-6"
              >
                <div className="flex items-center justify-between border-b border-white/10 pb-2.5">
                  <div>
                    <p className="text-xs font-black uppercase tracking-wider text-sky-300">
                      Architectural Blueprint · 2D Interactive HQ Floorplan
                    </p>
                    <p className="text-[11px] text-slate-400">
                      Click any department wing or operational station to inspect live reports and execute decisions.
                    </p>
                  </div>
                  <span className="gx-mono rounded bg-sky-950/80 border border-sky-500/30 px-2 py-0.5 text-[10px] text-sky-300">
                    6 Wings Online
                  </span>
                </div>

                <div className="my-auto grid grid-cols-2 sm:grid-cols-3 gap-3 py-3">
                  {destinations.map((dest) => {
                    const isSelected = dest.destination_key === activeDestination.destination_key;
                    return (
                      <div
                        key={dest.destination_key}
                        data-testid={`floorplan-room-${dest.destination_key}`}
                        onClick={() => setActiveDestKey(dest.destination_key)}
                        className={`cursor-pointer rounded-xl border p-3.5 transition flex flex-col justify-between ${
                          isSelected
                            ? "border-sky-400 bg-sky-950/60 ring-2 ring-sky-400/30"
                            : "border-white/15 bg-black/40 hover:border-white/30"
                        }`}
                      >
                        <div>
                          <div className="flex items-center justify-between">
                            <span
                              className="text-[11px] font-black uppercase"
                              style={{ color: dest.accent_color }}
                            >
                              {dest.label}
                            </span>
                            {dest.open_decisions_count > 0 && (
                              <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[9px] font-black text-amber-300">
                                {dest.open_decisions_count} Action(s)
                              </span>
                            )}
                          </div>
                          <p className="mt-1 text-xs font-bold text-white">{dest.staff_lead.name}</p>
                          <p className="text-[10px] text-slate-400">
                            Mood: {dest.staff_lead.mood ?? 78}% · {dest.staff_lead.role_label}
                          </p>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-1 pt-2 border-t border-white/10">
                          {dest.hotspots.map((hs) => (
                            <button
                              key={hs.id}
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setActiveDestKey(dest.destination_key);
                                setActiveHotspotId(hs.id);
                              }}
                              className="rounded bg-white/10 px-1.5 py-0.5 text-[9px] font-semibold text-slate-200 hover:bg-sky-500/30"
                            >
                              {hs.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="flex items-center justify-between border-t border-white/10 pt-2 text-[11px] text-slate-400">
                  <span>Active Wing: {activeDestination.label}</span>
                  <span>Treasury: {fmt(hub.club.cash_gtex)} GTEX</span>
                </div>
              </div>
            )}

            {/* Overlay HUD inside Viewport */}
            <div className="pointer-events-none absolute inset-x-3 top-3 flex flex-wrap items-center justify-between gap-2">
              <div className="pointer-events-auto flex items-center gap-2 rounded-xl border border-white/15 bg-slate-950/85 px-3 py-1.5 backdrop-blur-md">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: activeDestination.accent_color }}
                />
                <span className="text-xs font-black uppercase tracking-wider text-white">
                  {activeDestination.label}
                </span>
                <span className="text-[11px] text-slate-400">· {activeDestination.staff_lead.name}</span>
              </div>

              <div
                data-testid="glb-asset-status"
                className="pointer-events-auto flex items-center gap-1.5 rounded-xl border border-white/15 bg-slate-950/85 px-2.5 py-1 text-[10px] font-bold text-slate-300 backdrop-blur-md"
              >
                <span>
                  {renderMode === "3d"
                    ? `WebGL ${webglStatus === "ready" ? "Active" : "Init"} · ${loadedGlbCount}/${destinations.length} GLB Assets Loaded`
                    : "2D Blueprint Active"}
                </span>
              </div>
            </div>

            {/* GLB Asset Warning Banner */}
            {failedGlbModels.length > 0 && (
              <div
                data-testid="glb-asset-warning"
                className="pointer-events-auto absolute inset-x-3 top-14 flex items-center gap-2 rounded-xl border border-amber-500/50 bg-amber-950/90 px-3 py-1.5 text-xs text-amber-200 backdrop-blur-md z-10"
              >
                <AlertTriangle size={14} className="text-amber-400 shrink-0" />
                <span>
                  {failedGlbModels.length} 3D model asset(s) unavailable; procedural wireframe fallback active for {failedGlbModels.join(", ")}.
                </span>
              </div>
            )}

            {/* Interactive Room Hotspots Bar at Bottom of Viewport */}
            <div className="pointer-events-none absolute inset-x-3 bottom-3 flex flex-wrap items-center justify-between gap-2">
              <div className="pointer-events-auto flex flex-wrap items-center gap-1.5 rounded-xl border border-white/15 bg-slate-950/90 p-1.5 backdrop-blur-md">
                <span className="px-2 text-[10px] font-black uppercase tracking-wider text-slate-400">
                  Room Stations:
                </span>
                {activeDestination.hotspots.map((hs) => {
                  const isHsActive = activeHotspotId === hs.id;
                  return (
                    <button
                      key={hs.id}
                      type="button"
                      data-testid={`room-hotspot-${hs.id}`}
                      onClick={() => setActiveHotspotId(hs.id)}
                      className={`rounded-lg px-2.5 py-1 text-[11px] font-bold transition ${
                        isHsActive
                          ? "bg-sky-500 text-slate-950 font-black"
                          : "bg-white/5 text-slate-200 hover:bg-white/15"
                      }`}
                    >
                      {hs.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Quick Staff Communication Bar for Active Room Lead */}
          <div className="rounded-xl border border-white/10 bg-black/40 p-3.5 space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-black uppercase tracking-wider text-sky-300">
                  Direct Channel · {activeDestination.staff_lead.name} ({activeDestination.staff_lead.role_label})
                </span>
                <span className="gx-mono rounded bg-emerald-950/70 border border-emerald-500/30 px-2 py-0.5 text-[10px] text-emerald-300">
                  Mood {activeDestination.staff_lead.mood ?? 78}%
                </span>
              </div>
              <span className="text-[10px] text-slate-400">{activeDestination.staff_lead.specialty}</span>
            </div>

            {activeDestination.recent_messages.length > 0 && (
              <div className="max-h-24 overflow-y-auto space-y-1.5 rounded-lg border border-white/5 bg-slate-950/70 p-2.5 text-xs">
                {activeDestination.recent_messages.slice(-2).map((m, idx) => (
                  <p key={m.id || idx} className="text-slate-300">
                    <span className="font-bold text-white">{m.sender}: </span>
                    {m.message}
                  </p>
                ))}
              </div>
            )}

            <div className="flex gap-2">
              <input
                type="text"
                data-testid="department-staff-chat-input"
                value={staffMessageText}
                onChange={(e) => setStaffMessageText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSendStaffChat(activeDestination.lead_role_key);
                }}
                placeholder={`Issue directive or ask ${activeDestination.staff_lead.name} about ${activeDestination.short_label}…`}
                className="flex-1 rounded-lg border border-white/15 bg-slate-950/90 px-3 py-1.5 text-xs text-white placeholder:text-slate-500 focus:border-sky-400 focus:outline-none"
              />
              <button
                type="button"
                data-testid="department-staff-chat-send"
                disabled={sendingChat || !staffMessageText.trim()}
                onClick={() => handleSendStaffChat(activeDestination.lead_role_key)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-sky-400/50 bg-sky-500/20 px-3.5 py-1.5 text-xs font-bold uppercase text-sky-200 hover:bg-sky-500/30 disabled:opacity-50"
              >
                <Send size={12} />
                <span>{sendingChat ? "…" : "Send"}</span>
              </button>
            </div>
          </div>
        </div>

        {/* Right 5 cols: Contextual Department Inspector & Decision Execution Panel */}
        <div
          data-testid={`department-inspector-${activeDestination.destination_key}`}
          className="lg:col-span-5 flex flex-col justify-between rounded-2xl border border-white/15 bg-slate-950/80 p-4 sm:p-5 space-y-4 max-h-[640px] overflow-y-auto"
        >
          <div className="space-y-4">
            {/* Department Header */}
            <div className="border-b border-white/10 pb-3">
              <div className="flex items-center justify-between">
                <span
                  className="text-[11px] font-black uppercase tracking-wider"
                  style={{ color: activeDestination.accent_color }}
                >
                  {activeDestination.label}
                </span>
                <span className="gx-mono text-[11px] text-slate-400">
                  Station: {activeDestination.hotspots.find((h) => h.id === activeHotspotId)?.label || "Overview"}
                </span>
              </div>
              <h3 className="mt-1 text-lg font-black text-white">{rpt.title || activeDestination.subtitle}</h3>
              <p className="mt-1 text-xs leading-relaxed text-slate-300">{rpt.summary}</p>
            </div>

            {/* Phase 2.4 Staff Relationship Health Inspector Card */}
            {activeDestination.relationship && (
              <div
                data-testid={`relationship-card-${activeDestination.destination_key}`}
                className="rounded-xl border border-white/10 bg-black/40 p-3 space-y-2.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Users size={12} className="text-sky-400" />
                    <span className="text-[11px] font-black uppercase tracking-wider text-slate-200">
                      Executive Relationship ·{" "}
                      {activeDestination.relationship.participant_a_type === "owner"
                        ? activeDestination.relationship.participant_b_name
                        : activeDestination.relationship.participant_a_name}
                    </span>
                  </div>
                  <span className="rounded-full bg-sky-950/80 border border-sky-400/40 px-2 py-0.5 text-[10px] font-bold text-sky-300">
                    {activeDestination.relationship.status_label}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[10px]">
                  <div>
                    <div className="flex justify-between text-slate-400 mb-0.5">
                      <span>Trust</span>
                      <span className="text-emerald-300 font-bold">{activeDestination.relationship.trust}%</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                      <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${activeDestination.relationship.trust}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-slate-400 mb-0.5">
                      <span>Respect</span>
                      <span className="text-sky-300 font-bold">{activeDestination.relationship.respect}%</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                      <div className="h-full bg-sky-500 rounded-full" style={{ width: `${activeDestination.relationship.respect}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-slate-400 mb-0.5">
                      <span>Affinity</span>
                      <span className="text-purple-300 font-bold">{activeDestination.relationship.affinity}%</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                      <div className="h-full bg-purple-500 rounded-full" style={{ width: `${activeDestination.relationship.affinity}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-slate-400 mb-0.5">
                      <span>Tension</span>
                      <span className={`font-bold ${activeDestination.relationship.tension >= 50 ? "text-rose-400" : "text-amber-300"}`}>
                        {activeDestination.relationship.tension}%
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${activeDestination.relationship.tension >= 50 ? "bg-rose-500" : "bg-amber-500"}`}
                        style={{ width: `${activeDestination.relationship.tension}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Phase 2.4 Departmental Directives Card */}
            <div
              data-testid={`department-directives-${activeDestination.destination_key}`}
              className="rounded-xl border border-sky-500/20 bg-sky-950/20 p-3 space-y-2.5"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Activity size={12} className="text-sky-400" />
                  <span className="text-[11px] font-black uppercase tracking-wider text-sky-300">
                    Active Directives ({activeDestination.active_directives?.length || 0})
                  </span>
                </div>
                <button
                  type="button"
                  data-testid="open-dispatch-directive-button"
                  onClick={() => setShowDirectiveModal(true)}
                  className="rounded border border-sky-400/40 bg-sky-500/20 px-2 py-0.5 text-[10px] font-bold text-sky-200 hover:bg-sky-500/30"
                >
                  + Issue Directive
                </button>
              </div>
              {(activeDestination.active_directives?.length || 0) === 0 ? (
                <p className="text-[10px] text-slate-400 italic">No active directives for this department.</p>
              ) : (
                <div className="space-y-1.5">
                  {activeDestination.active_directives?.map((dir) => (
                    <div key={dir.id} className="rounded-lg border border-white/10 bg-black/40 p-2 text-[11px] space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white">{dir.title}</span>
                        <span className="rounded bg-sky-900/60 px-1.5 py-0.2 text-[9px] font-bold text-sky-300 uppercase">
                          Target Day {dir.deadline_day}
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-300 leading-snug">{dir.instruction}</p>
                      {dir.acknowledgement_text && (
                        <p className="text-[9px] text-slate-400 italic bg-white/5 rounded p-1">
                          "{dir.acknowledgement_text}"
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Phase 2.4 Living World Department Events */}
            {(activeDestination.active_events?.length || 0) > 0 && (
              <div
                data-testid={`department-events-${activeDestination.destination_key}`}
                className="rounded-xl border border-indigo-500/30 bg-indigo-950/20 p-3 space-y-2.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Sparkles size={12} className="text-indigo-400" />
                    <span className="text-[11px] font-black uppercase tracking-wider text-indigo-300">
                      Living Club Events ({activeDestination.active_events?.length || 0})
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400">Authoritative</span>
                </div>
                <div className="space-y-2">
                  {activeDestination.active_events?.map((ev) => (
                    <div
                      key={ev.id}
                      data-testid={`department-event-${ev.id}`}
                      className="rounded-lg border border-white/10 bg-black/50 p-2.5 space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-white">{ev.title}</span>
                        <span
                          className={`rounded px-1.5 py-0.2 text-[9px] font-black uppercase ${
                            ev.severity === "critical"
                              ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                              : ev.severity === "important"
                              ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                              : "bg-slate-700/40 text-slate-300"
                          }`}
                        >
                          {ev.severity}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-300 leading-relaxed">{ev.description}</p>
                      {ev.actions?.length > 0 && (
                        <div className="flex items-center justify-end gap-1.5 pt-1">
                          {ev.actions.map((act) => (
                            <button
                              key={act.key}
                              type="button"
                              data-testid={`event-action-${ev.id}-${act.key}`}
                              disabled={Boolean(busyEventId)}
                              onClick={() => handleResolveEvent(ev.id, act.key)}
                              className={`rounded px-2.5 py-1 text-[10px] font-bold uppercase transition ${
                                act.style === "primary"
                                  ? "border border-indigo-500/50 bg-indigo-600/30 text-indigo-200 hover:bg-indigo-600/50"
                                  : "border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
                              }`}
                            >
                              {busyEventId === `${ev.id}:${act.key}` ? "…" : act.label}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Department-Specific Actionable Decisions Queue */}
            {openDeptDecisions.length > 0 && (
              <div className="rounded-xl border border-amber-500/40 bg-amber-950/20 p-3.5 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-black uppercase tracking-wider text-amber-300">
                    Pending Owner Sign-Off ({openDeptDecisions.length})
                  </span>
                  <span className="text-[10px] text-slate-400">Persisted World-Day Action</span>
                </div>
                {openDeptDecisions.map((dec) => {
                  const busyApp = busyDecisionId === `${dec.decision_id}:approve`;
                  const busyRej = busyDecisionId === `${dec.decision_id}:reject`;
                  return (
                    <div
                      key={dec.decision_id}
                      data-testid={`room-decision-${dec.decision_id}`}
                      className="rounded-lg border border-white/10 bg-black/50 p-3 space-y-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-bold text-white">{dec.title}</span>
                        <span className="gx-mono text-[11px] font-bold text-amber-300">
                          {dec.cost_gtex > 0 ? `${fmt(dec.cost_gtex)} GTEX` : "0 GTEX"}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-300 leading-relaxed">{dec.summary}</p>
                      <p className="text-[10px] font-semibold text-emerald-300">{dec.effects_preview}</p>
                      <div className="flex items-center justify-end gap-2 pt-1">
                        <button
                          type="button"
                          disabled={Boolean(busyDecisionId)}
                          onClick={() => handleExecuteDecision(dec, "reject")}
                          className="inline-flex items-center gap-1 rounded border border-rose-500/40 bg-rose-950/40 px-2.5 py-1 text-[10px] font-bold uppercase text-rose-200 hover:bg-rose-900/50"
                        >
                          <XCircle size={11} />
                          <span>{busyRej ? "…" : "Reject"}</span>
                        </button>
                        <button
                          type="button"
                          data-testid={`room-approve-${dec.decision_id}`}
                          disabled={Boolean(busyDecisionId)}
                          onClick={() => handleExecuteDecision(dec, "approve")}
                          className="inline-flex items-center gap-1 rounded border border-emerald-500/50 bg-emerald-600/30 px-3 py-1 text-[10px] font-black uppercase text-emerald-200 hover:bg-emerald-600/50"
                        >
                          <CheckCircle2 size={11} />
                          <span>{busyApp ? "Executing…" : "Approve & Execute"}</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* 1. EXECUTIVE OFFICE VIEW */}
            {activeDestination.destination_key === "executive_office" && (
              <div className="space-y-3.5" data-testid="room-panel-executive-office">
                <div className="grid grid-cols-2 gap-2.5">
                  <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
                    <p className="text-[10px] uppercase font-bold text-slate-400">Club Treasury</p>
                    <p className="gx-mono text-sm font-black text-white mt-0.5">
                      {fmt(rpt.financial_position?.cash_gtex ?? hub.club.cash_gtex)} GTEX
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
                    <p className="text-[10px] uppercase font-bold text-slate-400">Squad Availability</p>
                    <p className="gx-mono text-sm font-black text-emerald-300 mt-0.5">
                      {rpt.squad_condition_and_availability?.available_players ?? 0}/
                      {rpt.squad_condition_and_availability?.squad_size ?? 0} Fit
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
                    <p className="text-[10px] uppercase font-bold text-slate-400">Stadium Capacity</p>
                    <p className="gx-mono text-sm font-black text-sky-300 mt-0.5">
                      {fmt(rpt.stadium_and_campus_operations?.operational_stadium_capacity ?? 15000)} Seats
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
                    <p className="text-[10px] uppercase font-bold text-slate-400">Recent Record</p>
                    <p className="gx-mono text-sm font-black text-amber-300 mt-0.5">
                      {rpt.recent_match_performance?.wins ?? 0}W-{rpt.recent_match_performance?.draws ?? 0}D-
                      {rpt.recent_match_performance?.losses ?? 0}L
                    </p>
                  </div>
                </div>

                {/* Urgent Risks */}
                {(rpt.urgent_risks || []).length > 0 && (
                  <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-3 space-y-2">
                    <p className="text-[10px] font-black uppercase tracking-wider text-rose-300 flex items-center gap-1.5">
                      <ShieldAlert size={13} />
                      <span>Executive Risk Watchlist</span>
                    </p>
                    {(rpt.urgent_risks || []).map((r: any) => (
                      <div key={r.risk_id} className="rounded border border-white/10 bg-black/40 p-2 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-white">{r.title}</span>
                          <button
                            type="button"
                            onClick={() => setActiveDestKey(r.department)}
                            className="text-[10px] font-bold uppercase text-sky-300 hover:underline"
                          >
                            Open Wing
                          </button>
                        </div>
                        <p className="text-[11px] text-slate-300 mt-0.5">{r.detail}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Boardroom Dilemma Quick Resolution */}
                {dilemma && dilemma.status === "open" && (
                  <div className="rounded-xl border border-amber-500/40 bg-amber-950/20 p-3 space-y-2">
                    <p className="text-[10px] font-black uppercase tracking-wider text-amber-300">
                      Boardroom Dilemma · {dilemma.title}
                    </p>
                    <p className="text-[11px] text-slate-300">{dilemma.conflict_summary}</p>
                    <div className="space-y-1.5 pt-1">
                      {dilemma.choices.map((ch) => (
                        <button
                          key={ch.choice_id}
                          type="button"
                          disabled={Boolean(busyAction)}
                          onClick={() => handleResolveDilemma(ch.choice_id)}
                          className="w-full rounded-lg border border-white/15 bg-black/50 p-2 text-left hover:border-amber-400/60"
                        >
                          <div className="flex items-center justify-between text-xs font-bold text-white">
                            <span>{ch.label}</span>
                            <span className="text-[10px] text-emerald-300">{ch.effects_preview}</span>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* All-Club Pending Department Decisions */}
                {allOpenDeptDecisions.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-[10px] font-black uppercase tracking-wider text-slate-400">
                      Cross-Departmental Decisions Queue ({allOpenDeptDecisions.length})
                    </p>
                    {allOpenDeptDecisions.map((dec) => (
                      <div
                        key={dec.decision_id}
                        className="rounded-lg border border-white/10 bg-black/40 p-2.5 flex items-center justify-between gap-2"
                      >
                        <div>
                          <p className="text-xs font-bold text-white">{dec.title}</p>
                          <p className="text-[10px] text-slate-400">
                            {dec.staff_name} · {dec.cost_gtex > 0 ? `${fmt(dec.cost_gtex)} GTEX` : "No Fee"}
                          </p>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => setActiveDestKey(dec.department)}
                            className="rounded border border-white/15 px-2 py-1 text-[10px] font-bold text-slate-300 hover:bg-white/10"
                          >
                            Room
                          </button>
                          <button
                            type="button"
                            disabled={Boolean(busyDecisionId)}
                            onClick={() => handleExecuteDecision(dec, "approve")}
                            className="rounded border border-emerald-500/50 bg-emerald-600/30 px-2.5 py-1 text-[10px] font-black uppercase text-emerald-200 hover:bg-emerald-600/50"
                          >
                            Approve
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Persistent Operational Timeline */}
                <div className="space-y-1.5 pt-2 border-t border-white/10">
                  <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 flex items-center gap-1">
                    <History size={12} />
                    <span>Persistent Club Operational Log</span>
                  </p>
                  <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                    {(Array.isArray(hub.operational_timeline) ? hub.operational_timeline : []).slice(0, 8).map((ev) => (
                      <div key={ev.id} className="rounded border border-white/5 bg-black/30 px-2.5 py-1.5 text-[11px]">
                        <div className="flex items-center justify-between text-[10px] text-slate-400">
                          <span className="font-bold text-sky-300 uppercase">{ev.title}</span>
                          <span>Day {ev.world_day}</span>
                        </div>
                        <p className="text-slate-300 mt-0.5">{ev.detail}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 2. MANAGER'S OFFICE VIEW */}
            {activeDestination.destination_key === "managers_office" && (
              <div className="space-y-3.5" data-testid="room-panel-managers-office">
                <div className="grid grid-cols-2 gap-2.5">
                  <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
                    <p className="text-[10px] uppercase font-bold text-slate-400">Team Strength</p>
                    <p className="gx-mono text-sm font-black text-sky-300 mt-0.5">
                      {rpt.first_team_performance?.team_strength ?? 68} OVR
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
                    <p className="text-[10px] uppercase font-bold text-slate-400">Dressing Room Morale</p>
                    <p className="gx-mono text-sm font-black text-emerald-300 mt-0.5">
                      {rpt.player_morale?.avg_morale ?? 75}%
                    </p>
                  </div>
                </div>

                {/* Tactical Mentality Control */}
                <div className="rounded-xl border border-white/10 bg-black/40 p-3 space-y-2">
                  <p className="text-[10px] font-black uppercase tracking-wider text-sky-300">
                    Tactical Mentality Directive (Current: {hub.club.mentality.toUpperCase()})
                  </p>
                  <div className="grid grid-cols-3 gap-2">
                    {(["defensive", "balanced", "attacking"] as const).map((m) => (
                      <button
                        key={m}
                        type="button"
                        data-testid={`set-mentality-${m}`}
                        disabled={Boolean(busyAction)}
                        onClick={() => handleSetMentality(m)}
                        className={`rounded-lg border py-1.5 text-[11px] font-black uppercase transition ${
                          hub.club.mentality === m
                            ? "border-sky-400 bg-sky-500/30 text-white"
                            : "border-white/10 bg-slate-900 text-slate-400 hover:text-white"
                        }`}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Matchday Win Bonus Pledge */}
                <div className="rounded-xl border border-white/10 bg-black/40 p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] font-black uppercase tracking-wider text-amber-300">
                      Pledge Matchday Win Bonus
                    </p>
                    <span className="gx-mono text-[10px] text-emerald-300">
                      Active Pledge: {fmt(rpt.upcoming_match_preparation?.pledged_win_bonus_gtex ?? 0)} GTEX
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min={100}
                      max={10000}
                      step={50}
                      value={winBonusAmount}
                      onChange={(e) => setWinBonusAmount(Math.max(100, Number(e.target.value) || 100))}
                      className="w-28 rounded-lg border border-white/15 bg-slate-950 px-2.5 py-1 text-xs text-white"
                    />
                    <button
                      type="button"
                      data-testid="room-pledge-win-bonus-btn"
                      disabled={busyAction === "win-bonus"}
                      onClick={handlePledgeWinBonus}
                      className="flex-1 rounded-lg border border-amber-400/50 bg-amber-500/20 py-1.5 text-[11px] font-black uppercase text-amber-200 hover:bg-amber-500/30"
                    >
                      {busyAction === "win-bonus" ? "Pledging…" : `Pledge ${fmt(winBonusAmount)} GTEX Bonus`}
                    </button>
                  </div>
                </div>

                {/* Squad Leaders & Low Morale Concerns */}
                <div className="rounded-xl border border-white/10 bg-black/40 p-3 space-y-2">
                  <p className="text-[10px] font-black uppercase tracking-wider text-slate-400">
                    First-Team Dressing Room Leaders
                  </p>
                  <div className="space-y-1.5">
                    {(rpt.player_morale?.dressing_room_leaders || []).map((p: any) => (
                      <div key={p.id} className="flex items-center justify-between text-xs">
                        <span className="font-bold text-white">
                          {p.name} <span className="text-slate-400">({p.position})</span>
                        </span>
                        <span className="gx-mono text-[11px] text-emerald-300">
                          OVR {p.rating} · Morale {p.morale}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 3. GENERAL MANAGER'S OFFICE VIEW */}
            {activeDestination.destination_key === "general_managers_office" && (
              <div className="space-y-3.5" data-testid="room-panel-general-managers-office">
                <div className="rounded-xl border border-white/10 bg-black/40 p-3 space-y-2">
                  <p className="text-[10px] font-black uppercase tracking-wider text-purple-300 flex items-center gap-1.5">
                    <Sliders size={12} />
                    <span>Executive Delegation Policy</span>
                  </p>
                  <div className="grid grid-cols-3 gap-2">
                    {(["hands_on", "balanced", "delegating"] as const).map((style) => {
                      const currentStyle = rpt.administrative_matters?.delegation_policy?.delegation_style || "balanced";
                      return (
                        <button
                          key={style}
                          type="button"
                          data-testid={`set-delegation-${style}`}
                          disabled={Boolean(busyAction)}
                          onClick={() => handleUpdateDelegation(style)}
                          className={`rounded-lg border py-1.5 text-[10px] font-black uppercase transition ${
                            currentStyle === style
                              ? "border-purple-400 bg-purple-500/30 text-white"
                              : "border-white/10 bg-slate-900 text-slate-400 hover:text-white"
                          }`}
                        >
                          {style.replace("_", " ")}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Core Club Facility Upgrades */}
                <div className="rounded-xl border border-white/10 bg-black/40 p-3 space-y-2">
                  <p className="text-[10px] font-black uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                    <Hammer size={12} />
                    <span>Core Club Infrastructure Levels</span>
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(rpt.club_operations?.facility_levels || {}).map(([kind, lvl]) => (
                      <div
                        key={kind}
                        className="flex items-center justify-between rounded-lg border border-white/10 bg-slate-950 p-2"
                      >
                        <div>
                          <p className="text-[11px] font-bold uppercase text-white">{kind}</p>
                          <p className="gx-mono text-[10px] text-purple-300">Level {String(lvl)}/5</p>
                        </div>
                        <button
                          type="button"
                          data-testid={`upgrade-facility-${kind}`}
                          disabled={Number(lvl) >= 5 || Boolean(busyAction)}
                          onClick={() => handleUpgradeFacility(kind)}
                          className="rounded border border-purple-400/40 bg-purple-500/20 px-2 py-1 text-[10px] font-black uppercase text-purple-200 hover:bg-purple-500/30 disabled:opacity-40"
                        >
                          {Number(lvl) >= 5 ? "Max" : "Upgrade"}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Active 3D Campus Construction Projects */}
                {(rpt.club_operations?.active_construction_projects || []).length > 0 && (
                  <div className="rounded-xl border border-white/10 bg-black/40 p-3 space-y-2">
                    <p className="text-[10px] font-black uppercase tracking-wider text-amber-300">
                      Active Campus Construction Projects
                    </p>
                    {(rpt.club_operations?.active_construction_projects || []).map((proj: any) => (
                      <div
                        key={proj.instance_id}
                        className="flex items-center justify-between rounded-lg border border-white/10 bg-slate-950 p-2 text-xs"
                      >
                        <div>
                          <p className="font-bold text-white">{proj.name}</p>
                          <p className="text-[10px] text-slate-400">
                            Stage {proj.stage_index}/{proj.total_stages}: {proj.construction_stage_label}
                          </p>
                        </div>
                        <button
                          type="button"
                          disabled={Boolean(busyAction)}
                          onClick={() => handleAdvanceCampusStage(proj.instance_id)}
                          className="rounded border border-amber-400/50 bg-amber-500/20 px-2.5 py-1 text-[10px] font-black uppercase text-amber-200 hover:bg-amber-500/30"
                        >
                          Advance Stage
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 4. ACADEMY DEPARTMENT VIEW */}
            {activeDestination.destination_key === "academy_department" && (
              <div className="space-y-3.5" data-testid="room-panel-academy-department">
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-lg border border-white/10 bg-black/40 p-2">
                    <p className="text-[9px] uppercase font-bold text-slate-400">Academy Lvl</p>
                    <p className="gx-mono text-sm font-black text-emerald-300">
                      Lvl {rpt.academy_development?.academy_facility_level ?? 1}
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-black/40 p-2">
                    <p className="text-[9px] uppercase font-bold text-slate-400">Ceiling Bonus</p>
                    <p className="gx-mono text-sm font-black text-amber-300">
                      +{rpt.academy_development?.campus_regen_potential_bonus ?? 0} POT
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-black/40 p-2">
                    <p className="text-[9px] uppercase font-bold text-slate-400">Intake Quality</p>
                    <p className="gx-mono text-sm font-black text-sky-300">
                      +{rpt.academy_development?.campus_youth_intake_quality_bonus ?? 0} OVR
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  data-testid="commission-academy-intake-btn"
                  disabled={busyAction === "academy-intake"}
                  onClick={handleAcademyIntake}
                  className="w-full rounded-xl border border-emerald-400/50 bg-emerald-500/20 py-2 text-xs font-black uppercase text-emerald-200 hover:bg-emerald-500/30"
                >
                  {busyAction === "academy-intake"
                    ? "Scouting & Enrolling Regens…"
                    : `Commission New Youth Intake (${fmt(rpt.intake_recommendations?.intake_cost_gtex ?? 400)} GTEX)`}
                </button>

                <div className="space-y-2">
                  <p className="text-[10px] font-black uppercase tracking-wider text-slate-400">
                    Prospective Academy & Regen Pipeline ({(rpt.prospective_youth_players || []).length})
                  </p>
                  <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                    {(rpt.prospective_youth_players || []).map((p: any) => (
                      <div
                        key={p.id}
                        className="rounded-lg border border-white/10 bg-black/40 p-2.5 flex items-center justify-between gap-2"
                      >
                        <div>
                          <p className="text-xs font-bold text-white">
                            {p.name}{" "}
                            <span className="text-[10px] text-slate-400">
                              ({p.position} · Age {p.age})
                            </span>
                          </p>
                          <p className="gx-mono text-[10px] text-emerald-300 mt-0.5">
                            OVR {p.rating} → POT {p.potential} (+{p.headroom} Headroom) · Morale {p.morale}%
                          </p>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <button
                            type="button"
                            disabled={Boolean(busyAction)}
                            onClick={() => handleOfferYouthContract(p.id, p.name, p.contract_wage)}
                            className="rounded border border-sky-400/40 bg-sky-500/20 px-2 py-1 text-[9px] font-bold uppercase text-sky-200 hover:bg-sky-500/30"
                          >
                            Extend
                          </button>
                          {p.squad_status !== "first_team" && (
                            <button
                              type="button"
                              disabled={Boolean(busyAction)}
                              onClick={() => handlePromoteYouthPlayer(p.id, p.name)}
                              className="rounded border border-emerald-400/40 bg-emerald-500/20 px-2 py-1 text-[9px] font-bold uppercase text-emerald-200 hover:bg-emerald-500/30"
                            >
                              Promote
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 5. MEDICAL DEPARTMENT VIEW */}
            {activeDestination.destination_key === "medical_department" && (
              <div className="space-y-3.5" data-testid="room-panel-medical-department">
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-lg border border-white/10 bg-black/40 p-2">
                    <p className="text-[9px] uppercase font-bold text-slate-400">Heal Rate</p>
                    <p className="gx-mono text-sm font-black text-emerald-300">
                      {rpt.rehabilitation_status?.daily_injury_heal_days ?? 1}d / Tick
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-black/40 p-2">
                    <p className="text-[9px] uppercase font-bold text-slate-400">Risk Reduction</p>
                    <p className="gx-mono text-sm font-black text-sky-300">
                      -{rpt.medical_facility_performance?.injury_reduction_pct ?? 0}%
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-black/40 p-2">
                    <p className="text-[9px] uppercase font-bold text-slate-400">Avg Fitness</p>
                    <p className="gx-mono text-sm font-black text-amber-300">
                      {rpt.squad_fitness_concerns?.avg_squad_fitness ?? 95}%
                    </p>
                  </div>
                </div>

                {/* Active Rehabilitation Dossiers */}
                <div className="rounded-xl border border-white/10 bg-black/40 p-3 space-y-2">
                  <p className="text-[10px] font-black uppercase tracking-wider text-rose-300 flex items-center gap-1.5">
                    <Activity size={12} />
                    <span>Active Rehabilitation Ward ({(rpt.injured_players || []).length})</span>
                  </p>
                  {(rpt.injured_players || []).length === 0 ? (
                    <p className="text-xs text-emerald-300">
                      Zero players in the treatment room. All squad members cleared for training.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {(rpt.injured_players || []).map((inj: any) => (
                        <div key={inj.id} className="rounded-lg border border-rose-500/30 bg-rose-950/20 p-2.5 text-xs">
                          <div className="flex items-center justify-between font-bold text-white">
                            <span>
                              {inj.name} ({inj.position})
                            </span>
                            <span className="gx-mono text-rose-300">{inj.injured_days}d Injury</span>
                          </div>
                          <p className="text-[11px] text-slate-300 mt-0.5">
                            {inj.injury_type} · Est. Recovery:{" "}
                            <span className="font-bold text-emerald-300">
                              {inj.estimated_recovery_world_days} World Day(s)
                            </span>
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Players Requiring Special Attention */}
                {(rpt.players_requiring_special_attention || []).length > 0 && (
                  <div className="rounded-xl border border-white/10 bg-black/40 p-3 space-y-2">
                    <p className="text-[10px] font-black uppercase tracking-wider text-amber-300">
                      Workload & Conditioning Watchlist
                    </p>
                    <div className="space-y-1.5 max-h-40 overflow-y-auto">
                      {(rpt.players_requiring_special_attention || []).map((sp: any) => (
                        <div key={sp.id} className="flex items-center justify-between text-xs">
                          <span className="text-white font-semibold">
                            {sp.name} <span className="text-slate-400">({sp.workload_tier})</span>
                          </span>
                          <span className="gx-mono text-[11px] text-amber-300">
                            Fit {sp.fitness}% · {sp.workload_minutes}m
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 6. FINANCE & COMMERCIAL OFFICE VIEW */}
            {activeDestination.destination_key === "finance_commercial_office" && (
              <div className="space-y-3.5" data-testid="room-panel-finance-commercial-office">
                <div className="grid grid-cols-2 gap-2.5">
                  <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
                    <p className="text-[10px] uppercase font-bold text-slate-400">Treasury Balance</p>
                    <p className="gx-mono text-sm font-black text-cyan-300 mt-0.5">
                      {fmt(rpt.current_club_balance?.cash_gtex ?? hub.club.cash_gtex)} GTEX
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
                    <p className="text-[10px] uppercase font-bold text-slate-400">Daily Wage Bill</p>
                    <p className="gx-mono text-sm font-black text-rose-300 mt-0.5">
                      {fmt(rpt.wage_obligations?.total_daily_obligations_gtex ?? 0)} GTEX/d
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
                    <p className="text-[10px] uppercase font-bold text-slate-400">Projected Gate</p>
                    <p className="gx-mono text-sm font-black text-emerald-300 mt-0.5">
                      {fmt(rpt.matchday_revenue?.projected_next_home_gate_gtex ?? 0)} GTEX
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
                    <p className="text-[10px] uppercase font-bold text-slate-400">Projected Attendance</p>
                    <p className="gx-mono text-sm font-black text-amber-300 mt-0.5">
                      {fmt(rpt.matchday_revenue?.projected_next_home_attendance ?? 0)} /{" "}
                      {fmt(rpt.matchday_revenue?.operational_stadium_capacity ?? 15000)}
                    </p>
                  </div>
                </div>

                {/* Signable Sponsor Offers */}
                <div className="rounded-xl border border-white/10 bg-black/40 p-3 space-y-2">
                  <p className="text-[10px] font-black uppercase tracking-wider text-cyan-300 flex items-center gap-1.5">
                    <Award size={12} />
                    <span>Commercial Sponsorship Desk</span>
                  </p>
                  {(rpt.sponsor_income?.available_offers || [])
                    .filter((o: any) => !o.locked)
                    .slice(0, 2)
                    .map((offer: any) => (
                      <div
                        key={offer.offer_id}
                        className="rounded-lg border border-white/10 bg-slate-950 p-2.5 flex items-center justify-between gap-2"
                      >
                        <div>
                          <p className="text-xs font-bold text-white">{offer.sponsor_name}</p>
                          <p className="gx-mono text-[10px] text-emerald-300">
                            +{fmt(offer.upfront_signing_bonus_gtex)} Upfront · +{fmt(offer.per_match_gross_gtex)}/Match
                          </p>
                        </div>
                        <button
                          type="button"
                          data-testid={`sign-sponsor-${offer.offer_id}`}
                          disabled={Boolean(busyAction)}
                          onClick={() => handleSignSponsorOffer(offer.offer_id)}
                          className="rounded border border-cyan-400/50 bg-cyan-500/20 px-2.5 py-1 text-[10px] font-black uppercase text-cyan-200 hover:bg-cyan-500/30"
                        >
                          Sign Deal
                        </button>
                      </div>
                    ))}
                </div>

                {/* Recent Authoritative Ledger Entries */}
                <div className="space-y-1.5">
                  <p className="text-[10px] font-black uppercase tracking-wider text-slate-400">
                    Authoritative Ledger Stream
                  </p>
                  <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
                    {(rpt.recent_income_and_expenditure?.recent_ledger_entries || []).slice(0, 6).map((le: any) => (
                      <div
                        key={le.id}
                        className="flex items-center justify-between rounded border border-white/5 bg-black/30 px-2.5 py-1.5 text-[11px]"
                      >
                        <span className="truncate text-slate-300">{le.memo || le.event_type}</span>
                        <span className="gx-mono font-bold text-white">{fmt(le.net_amount)} GTX</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
      {/* Phase 2.4 Directive Dispatcher Modal */}
      {showDirectiveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div
            data-testid="directive-dispatcher-modal"
            className="w-full max-w-md rounded-2xl border border-sky-400/40 bg-slate-950 p-5 shadow-2xl space-y-4"
          >
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div>
                <h4 className="text-sm font-black uppercase tracking-wider text-white">
                  Dispatch Department Directive
                </h4>
                <p className="text-[11px] text-slate-400">
                  Target: {activeDestination.label} ({activeDestination.staff_lead.name})
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowDirectiveModal(false)}
                className="rounded p-1 text-slate-400 hover:text-white"
              >
                <XCircle size={18} />
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Directive Title
                </label>
                <input
                  type="text"
                  data-testid="directive-title-input"
                  value={directiveTitle}
                  onChange={(e) => setDirectiveTitle(e.target.value)}
                  placeholder="e.g. Prioritize Muscular Rehabilitation"
                  className="mt-1 w-full rounded-lg border border-white/15 bg-slate-900 px-3 py-1.5 text-xs text-white placeholder:text-slate-500 focus:border-sky-400 focus:outline-none"
                />
              </div>
              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Detailed Operational Instruction
                </label>
                <textarea
                  data-testid="directive-instruction-input"
                  value={directiveInstruction}
                  onChange={(e) => setDirectiveInstruction(e.target.value)}
                  rows={3}
                  placeholder="Outline expectations, resources, and specific milestones for this department..."
                  className="mt-1 w-full rounded-lg border border-white/15 bg-slate-900 px-3 py-1.5 text-xs text-white placeholder:text-slate-500 focus:border-sky-400 focus:outline-none"
                />
              </div>
              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Target Deadline (World Days)
                </label>
                <input
                  type="number"
                  min={1}
                  max={30}
                  value={directiveDeadline}
                  onChange={(e) => setDirectiveDeadline(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-white/15 bg-slate-900 px-3 py-1.5 text-xs text-white focus:border-sky-400 focus:outline-none"
                />
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/10">
              <button
                type="button"
                onClick={() => setShowDirectiveModal(false)}
                className="rounded px-3 py-1.5 text-xs font-bold text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                data-testid="submit-directive-button"
                onClick={handleIssueDirective}
                className="rounded-lg border border-sky-400/50 bg-sky-600/30 px-4 py-1.5 text-xs font-black uppercase text-sky-200 hover:bg-sky-600/50"
              >
                Issue Directive
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Phase 2.4 Living World Timeline Slide-Over Drawer */}
      {showTimelineDrawer && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm">
          <div
            data-testid="living-world-timeline-drawer"
            className="h-full w-full max-w-lg border-l border-white/15 bg-slate-950 p-6 shadow-2xl flex flex-col justify-between overflow-y-auto"
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-white/10 pb-3">
                <div className="flex items-center gap-2">
                  <Activity size={16} className="text-purple-400" />
                  <div>
                    <h3 className="text-sm font-black uppercase tracking-wider text-white">
                      Living Club World Timeline
                    </h3>
                    <p className="text-[10px] text-slate-400">
                      Unified events, departmental directives & relationship milestones
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  data-testid="close-timeline-drawer"
                  onClick={() => setShowTimelineDrawer(false)}
                  className="rounded p-1 text-slate-400 hover:text-white"
                >
                  <XCircle size={18} />
                </button>
              </div>

              {/* Category Filter Pills (including culture) */}
              <div className="space-y-2">
                <div className="flex flex-wrap gap-1.5" data-testid="timeline-category-filters">
                  {["all", "executive", "tactical", "squad", "academy", "medical", "financial", "culture"].map(
                    (cat) => (
                      <button
                        key={cat}
                        type="button"
                        data-testid={`timeline-filter-category-${cat}`}
                        onClick={() => {
                          setTimelineCategoryFilter(cat);
                          setTimelineOffset(0);
                        }}
                        className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase transition ${
                          timelineCategoryFilter === cat
                            ? "bg-purple-600/30 border border-purple-400/50 text-purple-200"
                            : "bg-white/5 border border-white/10 text-slate-400 hover:text-white"
                        }`}
                      >
                        {cat}
                      </button>
                    )
                  )}
                </div>

                {/* Severity & Status Filters */}
                <div className="grid grid-cols-2 gap-2 pt-1">
                  <div>
                    <span className="block text-[9px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                      Severity
                    </span>
                    <div className="flex flex-wrap gap-1" data-testid="timeline-severity-filters">
                      {["all", "routine", "important", "critical"].map((sev) => (
                        <button
                          key={sev}
                          type="button"
                          data-testid={`timeline-filter-severity-${sev}`}
                          onClick={() => {
                            setTimelineSeverityFilter(sev);
                            setTimelineOffset(0);
                          }}
                          className={`rounded px-2 py-0.5 text-[9px] font-bold uppercase transition ${
                            timelineSeverityFilter === sev
                              ? "bg-sky-600/30 border border-sky-400/50 text-sky-200"
                              : "bg-white/5 border border-white/10 text-slate-400 hover:text-white"
                          }`}
                        >
                          {sev}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <span className="block text-[9px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                      Status
                    </span>
                    <div className="flex flex-wrap gap-1" data-testid="timeline-status-filters">
                      {["all", "active", "resolved", "completed", "expired"].map((st) => (
                        <button
                          key={st}
                          type="button"
                          data-testid={`timeline-filter-status-${st}`}
                          onClick={() => {
                            setTimelineStatusFilter(st);
                            setTimelineOffset(0);
                          }}
                          className={`rounded px-2 py-0.5 text-[9px] font-bold uppercase transition ${
                            timelineStatusFilter === st
                              ? "bg-emerald-600/30 border border-emerald-400/50 text-emerald-200"
                              : "bg-white/5 border border-white/10 text-slate-400 hover:text-white"
                          }`}
                        >
                          {st}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Unified Timeline Stream States */}
              {isTimelineLoading && !timelineResponse ? (
                <div
                  data-testid="living-timeline-loading"
                  className="rounded-xl border border-white/10 bg-black/40 p-6 text-center space-y-2"
                >
                  <RefreshCw size={16} className="animate-spin mx-auto text-purple-300" />
                  <p className="text-xs font-bold text-slate-300">Loading unified club timeline…</p>
                </div>
              ) : isTimelineError ? (
                <div
                  data-testid="living-timeline-error"
                  className="rounded-xl border border-rose-500/40 bg-rose-950/30 p-4 text-center space-y-2.5"
                >
                  <p className="text-xs font-bold text-rose-200">
                    Unable to load Living Club World timeline: {errMsg(timelineErrorObj)}
                  </p>
                  <button
                    type="button"
                    data-testid="living-timeline-retry"
                    onClick={() => refetchTimeline()}
                    className="rounded-lg border border-rose-400/50 bg-rose-500/20 px-3 py-1 text-[10px] font-black uppercase text-rose-200 hover:bg-rose-500/30"
                  >
                    Retry
                  </button>
                </div>
              ) : (timelineResponse?.items?.length || 0) === 0 ? (
                <div
                  data-testid="living-timeline-empty"
                  className="rounded-xl border border-white/10 bg-black/40 p-6 text-center space-y-1.5"
                >
                  <p className="text-xs font-bold text-slate-300">No timeline entries match the active filters.</p>
                  <p className="text-[11px] text-slate-400">
                    Adjust category, severity, or status filters to inspect historical events, directives, and relationship milestones.
                  </p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1" data-testid="living-timeline-list">
                  {(timelineResponse?.items || []).map((item: LivingWorldTimelineItem) => {
                    const isActionableEvent =
                      item.kind === "event" &&
                      (item.status === "active" || item.status === "awaiting_decision") &&
                      Array.isArray(item.actions) &&
                      item.actions.length > 0;
                    const kindLabel =
                      item.kind === "directive"
                        ? "Directive"
                        : item.kind === "relationship_shift"
                        ? "Relationship Milestone"
                        : "Club Event";
                    return (
                      <div
                        key={`${item.kind}-${item.id}`}
                        data-testid={`timeline-item-${item.id}`}
                        data-timeline-kind={item.kind}
                        className="rounded-xl border border-white/10 bg-black/40 p-3.5 space-y-2"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-1.5">
                          <div className="flex items-center gap-1.5">
                            <span
                              data-testid={`timeline-kind-badge-${item.id}`}
                              className={`rounded px-1.5 py-0.5 text-[9px] font-black uppercase ${
                                item.kind === "directive"
                                  ? "bg-sky-500/20 text-sky-300 border border-sky-500/40"
                                  : item.kind === "relationship_shift"
                                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                                  : "bg-purple-500/20 text-purple-300 border border-purple-500/40"
                              }`}
                            >
                              {kindLabel}
                            </span>
                            <span className="text-[10px] font-bold uppercase text-purple-300">
                              Day {item.world_day} · {item.category}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <span
                              data-testid={`timeline-status-${item.id}`}
                              className={`rounded px-1.5 py-0.2 text-[9px] font-bold uppercase ${
                                item.status === "active" || item.status === "awaiting_decision"
                                  ? "bg-cyan-500/20 text-cyan-300"
                                  : item.status === "expired"
                                  ? "bg-rose-500/20 text-rose-300"
                                  : "bg-slate-800 text-slate-300"
                              }`}
                            >
                              {item.status}
                            </span>
                            <span
                              className={`rounded px-1.5 py-0.2 text-[9px] font-black uppercase ${
                                item.severity === "critical"
                                  ? "bg-rose-500/20 text-rose-300"
                                  : item.severity === "important"
                                  ? "bg-amber-500/20 text-amber-300"
                                  : "bg-slate-700/40 text-slate-300"
                              }`}
                            >
                              {item.severity}
                            </span>
                          </div>
                        </div>
                        <h4 className="text-xs font-bold text-white">{item.title}</h4>
                        <p className="text-[11px] text-slate-300 leading-relaxed">{item.description}</p>
                        {item.acknowledged_by && (
                          <p data-testid={`timeline-lead-${item.id}`} className="text-[10px] text-slate-400">
                            Lead: {item.acknowledged_by}
                          </p>
                        )}
                        {item.resolution_note && item.status !== "active" && (
                          <p
                            data-testid={`timeline-note-${item.id}`}
                            className="text-[10px] text-slate-400 italic bg-white/5 rounded px-2 py-1"
                          >
                            {item.resolution_note}
                          </p>
                        )}
                        {isActionableEvent && (
                          <div className="flex items-center justify-end gap-1.5 pt-1">
                            {item.actions.map((act) => (
                              <button
                                key={act.key}
                                type="button"
                                data-testid={`timeline-event-action-${item.id}-${act.key}`}
                                disabled={Boolean(busyEventId)}
                                onClick={() => handleResolveEvent(item.id, act.key)}
                                className="rounded border border-purple-500/40 bg-purple-600/30 px-2.5 py-1 text-[10px] font-bold uppercase text-purple-200 hover:bg-purple-600/50"
                              >
                                {act.label}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Pagination Footer */}
            <div className="pt-4 border-t border-white/10 space-y-2" data-testid="living-timeline-pagination">
              {timelineResponse && (
                <div className="flex items-center justify-between text-[10px] text-slate-400">
                  <span data-testid="living-timeline-range">
                    Showing{" "}
                    {timelineResponse.total_count === 0
                      ? 0
                      : timelineOffset + 1}
                    –
                    {Math.min(
                      timelineOffset + (timelineResponse.items?.length || 0),
                      timelineResponse.total_count
                    )}{" "}
                    of {timelineResponse.total_count}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      data-testid="timeline-prev-page"
                      disabled={timelineOffset <= 0 || isTimelineFetching}
                      onClick={() => setTimelineOffset((prev) => Math.max(0, prev - timelineLimit))}
                      className="rounded border border-white/15 bg-white/5 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-200 hover:bg-white/10 disabled:opacity-40"
                    >
                      Previous
                    </button>
                    <button
                      type="button"
                      data-testid="timeline-next-page"
                      disabled={
                        timelineOffset + timelineLimit >= (timelineResponse.total_count || 0) ||
                        isTimelineFetching
                      }
                      onClick={() => setTimelineOffset((prev) => prev + timelineLimit)}
                      className="rounded border border-white/15 bg-white/5 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-200 hover:bg-white/10 disabled:opacity-40"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
              <div className="text-center">
                <span className="text-[10px] text-slate-500">
                  Authoritative GTEX Simulation · World Day {hub?.club.world_day || 1}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default ClubOperationsCentre3D;
