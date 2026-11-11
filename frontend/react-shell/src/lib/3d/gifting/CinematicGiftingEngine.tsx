import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { Trophy } from "lucide-react";
import { GtexCelebrationAudioEngine } from "./GtexCelebrationAudioEngine";
import { AssetStreamingCache } from "../broadcast/AssetStreamingCache";
import { resolvePublicAssetPath } from "@/lib/publicPath";

function disposeObjectTree(objects: THREE.Object3D[], scene?: THREE.Scene | null): void {
  objects.forEach((root) => {
    if (scene) scene.remove(root);
    root.traverse((child) => {
      const mesh = child as THREE.Mesh;
      if (mesh.geometry && typeof mesh.geometry.dispose === "function") mesh.geometry.dispose();
      const mat = (mesh as THREE.Mesh).material;
      if (Array.isArray(mat)) mat.forEach((m) => m && typeof m.dispose === "function" && m.dispose());
      else if (mat && typeof mat.dispose === "function") mat.dispose();
    });
  });
}

export function resolveGiftModelPath(giftCode: string): string {
  const code = giftCode.toLowerCase();
  if (code.includes("jet") || code.includes("flyby")) return "/assets/showroom/sovereign_900x_jet.glb";
  if (code.includes("yacht")) return "/assets/showroom/superyacht.glb";
  if (code.includes("golden_stadium")) return "/assets/showroom/golden_stadium.glb";
  if (code.includes("crown") || code.includes("watch")) return "/assets/showroom/chronos_tourbillon_watch.glb";
  if (
    code.includes("paris") ||
    code.includes("new_york") ||
    code.includes("rio") ||
    code.includes("lagos") ||
    code.includes("tokyo") ||
    code.includes("dubai") ||
    code.includes("skyline")
  ) {
    return "/assets/showroom/royal_penthouse_box.glb";
  }
  if (code.includes("bus") || code.includes("coach")) return "/assets/showroom/vanguard_xii_coach.glb";
  if (code.includes("suv") || code.includes("hypercar")) return "/assets/showroom/executive_suv.glb";
  if (code.includes("campus") || code.includes("facility")) return "/assets/showroom/apex_performance_campus.glb";
  if (
    code.includes("trophy") ||
    code.includes("winner") ||
    code.includes("ballon") ||
    code.includes("boot") ||
    code.includes("glove") ||
    code.includes("puskas") ||
    code.includes("man_of_the_match") ||
    code.includes("manager_of_the_month")
  ) {
    return "/assets/showroom/trophy_plinth.glb";
  }
  return "/models/match/football-stadium.glb";
}

export type GiftShotId =
  | "atmosphere"
  | "card"
  | "tactics"
  | "crown"
  | "trophy"
  | "boot"
  | "glove"
  | "stadium"
  | "city"
  | "jet"
  | "yacht"
  | "goal"
  | "last_minute"
  | "bicycle"
  | "golden_goal"
  | "hat_trick"
  | "save";

const SHOT_BY_KEY: Record<string, GiftShotId> = {
  common_whistle: "atmosphere",
  whistle_blow: "atmosphere",
  fan_chant: "atmosphere",
  stadium_roar: "atmosphere",
  legend_card_reveal: "card",
  player_of_the_match: "card",
  tactical_masterclass: "tactics",
  midfield_maestro: "tactics",
  king_of_tactics: "crown",
  world_best_award: "trophy",
  golden_manager: "trophy",
  trophy_lift: "trophy",
  ballon_dor: "trophy",
  top_trainer: "trophy",
  golden_boot_spark: "boot",
  golden_boot_king: "boot",
  safe_hands_award: "glove",
  stadium_maracana: "stadium",
  maracana_stadium: "stadium",
  stadium_wembley: "stadium",
  wembley_stadium: "stadium",
  stadium_san_siro: "stadium",
  san_siro_stadium: "stadium",
  stadium_camp_nou: "stadium",
  camp_nou_stadium: "stadium",
  golden_stadium_reveal: "stadium",
  golden_stadium: "stadium",
  city_paris: "city",
  paris_skyline: "city",
  city_new_york: "city",
  new_york_skyline: "city",
  city_rio: "city",
  rio_skyline: "city",
  city_lagos: "city",
  lagos_skyline: "city",
  city_tokyo: "city",
  tokyo_skyline: "city",
  city_dubai: "city",
  dubai_skyline: "city",
  luxury_private_jet: "jet",
  private_jet: "jet",
  luxury_superyacht: "yacht",
  superyacht: "yacht",
  goal_celebration: "goal",
  last_minute_winner: "last_minute",
  bicycle_kick: "bicycle",
  golden_goal: "golden_goal",
  perfect_hat_trick: "hat_trick",
  world_class_save: "save",
};

const SHOT_NEEDLES: Array<[string, GiftShotId]> = [
  ["bicycle", "bicycle"],
  ["hat_trick", "hat_trick"],
  ["world_class_save", "save"],
  ["safe_hands", "glove"],
  ["golden_boot", "boot"],
  ["boot", "boot"],
  ["glove", "glove"],
  ["last_minute", "last_minute"],
  ["golden_goal", "golden_goal"],
  ["golden_stadium", "stadium"],
  ["goal", "goal"],
  ["flyby", "jet"],
  ["jet", "jet"],
  ["yacht", "yacht"],
  ["maracana", "stadium"],
  ["wembley", "stadium"],
  ["san_siro", "stadium"],
  ["camp_nou", "stadium"],
  ["paris", "city"],
  ["new_york", "city"],
  ["rio", "city"],
  ["lagos", "city"],
  ["tokyo", "city"],
  ["dubai", "city"],
  ["skyline", "city"],
  ["stadium", "stadium"],
  ["crown", "crown"],
  ["tactical", "tactics"],
  ["tactics", "tactics"],
  ["ballon", "trophy"],
  ["trophy", "trophy"],
  ["card", "card"],
];

export function resolveGiftShot(animationKey?: string, giftCode?: string): GiftShotId {
  const anim = (animationKey || "").trim().toLowerCase();
  const code = (giftCode || "").trim().toLowerCase();
  if (anim && SHOT_BY_KEY[anim]) return SHOT_BY_KEY[anim];
  if (code && SHOT_BY_KEY[code]) return SHOT_BY_KEY[code];
  const hay = `${anim} ${code}`;
  for (const [needle, shot] of SHOT_NEEDLES) {
    if (hay.includes(needle)) return shot;
  }
  return "atmosphere";
}

function streamedModelFor(shot: GiftShotId, giftCode: string): string | null {
  const code = giftCode.toLowerCase();
  if (shot === "jet" || shot === "yacht") return resolveGiftModelPath(code);
  if (shot === "stadium" && code.includes("golden_stadium")) return resolveGiftModelPath("golden_stadium");
  return null;
}

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function smoothstep(value: number): number {
  const t = clamp01(value);
  return t * t * (3 - 2 * t);
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function metal(color: number, metalness = 0.85, roughness = 0.22): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({ color, metalness, roughness });
}

function addAtmosphere(hero: THREE.Group, accent: number): void {
  const ring = new THREE.Mesh(new THREE.TorusGeometry(4.2, 0.75, 16, 48), metal(accent));
  ring.position.y = 6.5;
  hero.add(ring);
  const core = new THREE.Mesh(new THREE.OctahedronGeometry(2.6, 0), metal(accent));
  core.position.y = 6.5;
  hero.add(core);
}

function addBoard(hero: THREE.Group, color: number, wide: boolean): void {
  const board = new THREE.Mesh(
    wide ? new THREE.BoxGeometry(9, 5.8, 0.65) : new THREE.BoxGeometry(5.5, 8.2, 0.45),
    metal(color, 0.7, 0.2)
  );
  board.position.y = 6.5;
  hero.add(board);
}

function addCrown(hero: THREE.Group): void {
  const gold = metal(0xf59e0b, 0.95, 0.14);
  const ruby = metal(0xe11d48, 0.5, 0.15);
  const band = new THREE.Mesh(new THREE.CylinderGeometry(4.8, 4.4, 2.4, 24, 1, true), gold);
  band.position.y = 5;
  hero.add(band);
  for (let i = 0; i < 6; i++) {
    const angle = (i / 6) * Math.PI * 2;
    const spire = new THREE.Mesh(new THREE.ConeGeometry(0.85, 3.2, 8), gold);
    spire.position.set(Math.cos(angle) * 4.5, 7.6, Math.sin(angle) * 4.5);
    hero.add(spire);
    const gem = new THREE.Mesh(new THREE.OctahedronGeometry(0.55, 0), ruby);
    gem.position.set(Math.cos(angle) * 4.6, 5, Math.sin(angle) * 4.6);
    hero.add(gem);
  }
}

function addTrophy(hero: THREE.Group): void {
  const gold = metal(0xf59e0b, 0.95, 0.15);
  const pedestal = new THREE.Mesh(new THREE.CylinderGeometry(5.5, 6, 3, 24), metal(0x0f172a, 0.2, 0.4));
  pedestal.position.y = 1.5;
  hero.add(pedestal);
  const cup = new THREE.Mesh(new THREE.CylinderGeometry(4.5, 2, 7, 24), gold);
  cup.position.y = 7;
  hero.add(cup);
  const ball = new THREE.Mesh(new THREE.SphereGeometry(2.4, 24, 24), gold);
  ball.position.y = 12.5;
  hero.add(ball);
}

function addBoot(hero: THREE.Group): void {
  const gold = metal(0xf59e0b, 0.95, 0.15);
  const pedestal = new THREE.Mesh(new THREE.CylinderGeometry(5.5, 6, 3, 24), metal(0x0f172a, 0.2, 0.4));
  pedestal.position.y = 1.5;
  hero.add(pedestal);
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(1.4, 1.6, 4.8, 16), gold);
  shaft.position.set(-0.8, 5.4, 0);
  hero.add(shaft);
  const foot = new THREE.Mesh(new THREE.BoxGeometry(5.2, 1.8, 2.4), gold);
  foot.position.set(0.8, 3.9, 0);
  hero.add(foot);
}

function addGlove(hero: THREE.Group): void {
  const gold = metal(0xf59e0b, 0.95, 0.15);
  const palm = new THREE.Mesh(new THREE.BoxGeometry(3.8, 4.4, 1.2), gold);
  palm.position.set(0, 5.5, 0);
  palm.name = "save-glove";
  hero.add(palm);
  [-1.4, -0.5, 0.5, 1.4].forEach((fx) => {
    const finger = new THREE.Mesh(new THREE.CylinderGeometry(0.38, 0.38, 2.8, 12), gold);
    finger.position.set(fx, 8.8, 0);
    hero.add(finger);
  });
}

function addStadium(hero: THREE.Group, giftCode: string): void {
  const code = giftCode.toLowerCase();
  const isGold = code.includes("golden");
  const isFlares = code.includes("san_siro") || code.includes("flare");
  const bowlMat = metal(isGold ? 0xd97706 : isFlares ? 0x7f1d1d : 0x1e293b, isGold ? 0.9 : 0.6, isGold ? 0.2 : 0.3);
  bowlMat.side = THREE.DoubleSide;
  const bowl = new THREE.Mesh(new THREE.CylinderGeometry(14, 11, 4, 32, 1, true), bowlMat);
  bowl.position.y = 2;
  bowl.name = "stadium-shell";
  hero.add(bowl);
  const pitch = new THREE.Mesh(
    new THREE.PlaneGeometry(16, 11),
    new THREE.MeshStandardMaterial({ color: isGold ? 0xf59e0b : 0x059669, roughness: 0.6 })
  );
  pitch.rotation.x = -Math.PI / 2;
  pitch.position.y = 0.1;
  pitch.name = "stadium-shell";
  hero.add(pitch);
  const beamColor = isFlares ? 0xef4444 : isGold ? 0xfde047 : 0xfef08a;
  const beamMat = new THREE.MeshBasicMaterial({
    color: beamColor,
    transparent: true,
    opacity: 0.38,
    blending: THREE.AdditiveBlending,
  });
  [
    [-9, -6],
    [9, -6],
    [-9, 6],
    [9, 6],
  ].forEach(([bx, bz]) => {
    const beam = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 4.5, 24, 16), beamMat);
    beam.position.set(bx, 10, bz);
    beam.rotation.x = bz > 0 ? -0.25 : 0.25;
    beam.name = "flood-beam";
    hero.add(beam);
  });
}

function addCity(hero: THREE.Group, giftCode: string): void {
  const code = giftCode.toLowerCase();
  const primary = code.includes("tokyo")
    ? 0xd946ef
    : code.includes("dubai")
      ? 0xf59e0b
      : code.includes("rio")
        ? 0x10b981
        : code.includes("lagos")
          ? 0x22c55e
          : code.includes("paris")
            ? 0x93c5fd
            : 0xb45309;
  const beaconHex = code.includes("dubai") ? 0xfde047 : 0x38bdf8;
  const towerMat = metal(primary, 0.8, 0.22);
  const base = new THREE.Mesh(new THREE.CylinderGeometry(2, 5.5, 8, 6), towerMat);
  base.position.y = 4;
  hero.add(base);
  const spire = new THREE.Mesh(new THREE.ConeGeometry(1.4, 11, 6), towerMat);
  spire.position.y = 12.5;
  hero.add(spire);
  [-5.5, 5.5].forEach((tx, idx) => {
    const tower = new THREE.Mesh(new THREE.BoxGeometry(2.2, 6 + idx * 1.5, 2.2), towerMat);
    tower.position.set(tx, 3 + idx * 0.75, -1.5);
    hero.add(tower);
  });
  const beacon = new THREE.Mesh(
    new THREE.ConeGeometry(6, 28, 16),
    new THREE.MeshBasicMaterial({ color: beaconHex, transparent: true, opacity: 0.45, blending: THREE.AdditiveBlending })
  );
  beacon.position.set(0, 16, 0);
  beacon.rotation.z = Math.PI / 2.3;
  hero.add(beacon);
}

function addJet(hero: THREE.Group): void {
  const skin = metal(0xf8fafc, 0.9, 0.1);
  const fuselage = new THREE.Mesh(new THREE.ConeGeometry(1.6, 16, 16), skin);
  fuselage.rotation.x = Math.PI / 2;
  fuselage.name = "jet-primitive";
  hero.add(fuselage);
  const wing = new THREE.Mesh(new THREE.BoxGeometry(18, 0.2, 4), skin);
  wing.position.set(0, 0, -1);
  wing.name = "jet-primitive";
  hero.add(wing);
}

function addYacht(hero: THREE.Group): void {
  const water = new THREE.Mesh(
    new THREE.CylinderGeometry(11, 11, 0.4, 32),
    metal(0x0284c7, 0.75, 0.18)
  );
  water.position.y = 0.2;
  water.name = "yacht-water";
  hero.add(water);
  const hull = new THREE.Mesh(new THREE.BoxGeometry(13, 2.2, 4.2), metal(0xf8fafc, 0.65, 0.22));
  hull.position.y = 1.6;
  hull.name = "yacht-primitive";
  hero.add(hull);
  const deck = new THREE.Mesh(new THREE.BoxGeometry(8.5, 1.8, 3.4), metal(0x38bdf8, 0.85, 0.15));
  deck.position.set(-0.5, 3.4, 0);
  deck.name = "yacht-primitive";
  hero.add(deck);
}

function makeBall(color = 0xf8fafc): THREE.Mesh {
  const ball = new THREE.Mesh(new THREE.SphereGeometry(0.7, 24, 24), metal(color, 0.45, 0.35));
  ball.name = "gift-ball";
  return ball;
}

function placeBall(ball: THREE.Object3D, shot: GiftShotId, progress: number): void {
  if (shot === "bicycle") {
    if (progress < 0.45) {
      const t = smoothstep(progress / 0.45);
      ball.position.set(lerp(-4, 0.4, t), lerp(1.5, 10, t), 0);
    } else if (progress < 0.62) {
      ball.position.set(0.4, 10, 0);
    } else {
      const t = smoothstep((progress - 0.62) / 0.38);
      ball.position.set(lerp(0.4, 3.2, t), lerp(10, 2.2, t), 0);
    }
    return;
  }
  if (shot === "hat_trick") {
    ball.position.set(lerp(-4, 4, progress), 4 + Math.sin(progress * Math.PI * 3) * 1.4, 0);
    const marks = [0.25, 0.5, 0.75];
    let scale = 0.55;
    marks.forEach((mark) => {
      const distance = Math.abs(progress - mark);
      if (distance < 0.08) scale = Math.max(scale, 1.5 * (1 - distance / 0.08));
    });
    ball.scale.setScalar(scale);
    return;
  }
  if (shot === "save") {
    const t = smoothstep(Math.min(progress / 0.55, 1));
    ball.position.set(lerp(-7, 0.2, t), lerp(3, 5.6, t), lerp(2, 0.6, t));
    return;
  }
  if (shot === "last_minute") {
    const t = smoothstep(Math.min(progress / 0.7, 1));
    ball.position.set(lerp(-6, 6, t), lerp(1.4, 5.2, t), lerp(1, -2, t));
    return;
  }
  const t = smoothstep(Math.min(progress / 0.62, 1));
  ball.position.set(lerp(-6, 3, t), lerp(1.6, 4.4, t) + Math.sin(t * Math.PI) * 1.8, 0);
}

function placeCamera(camera: THREE.PerspectiveCamera, shot: GiftShotId, progress: number, hero: THREE.Object3D): void {
  const glide = smoothstep(progress);
  let x = 0;
  let y = 6.2;
  let z = 16;
  let lookX = 0;
  let lookY = 3.2;
  let lookZ = 0;
  if (shot === "city") {
    x = lerp(7, 1.2, glide);
    y = lerp(2.4, 14, glide);
    z = lerp(18, 12, glide);
    lookY = lerp(5, 12, glide);
  } else if (shot === "stadium" || shot === "golden_goal") {
    x = lerp(0.5, 2.4, glide);
    y = lerp(22, 7.5, glide);
    z = lerp(28, 16, glide);
    lookY = 4;
  } else if (shot === "jet") {
    x = hero.position.x - 6;
    y = hero.position.y + 3.5;
    z = 14;
    lookX = hero.position.x + 4;
    lookY = hero.position.y;
  } else if (shot === "yacht") {
    x = hero.position.x + 3;
    y = 6;
    z = 16;
    lookX = hero.position.x;
    lookY = 2;
  } else if (shot === "card" || shot === "tactics") {
    y = 6.4;
    z = lerp(18, 9, glide);
    lookY = 6.5;
  } else if (shot === "trophy" || shot === "boot" || shot === "glove" || shot === "crown") {
    x = lerp(10, 3.2, glide);
    y = lerp(3.2, 8.4, glide);
    z = lerp(16, 10, glide);
    lookY = lerp(4, 8, glide);
  } else if (shot === "bicycle") {
    y = lerp(5, 11, Math.min(1, progress / 0.5));
    z = 15;
    lookY = 8;
  } else {
    z = lerp(18, 12, glide);
    y = lerp(5, 7, glide);
    lookY = 4;
  }
  camera.position.set(x, y, z);
  camera.lookAt(lookX, lookY, lookZ);
}

function fadeTree(root: THREE.Object3D, opacity: number): void {
  root.traverse((child) => {
    const mesh = child as THREE.Mesh;
    const materials = Array.isArray(mesh.material) ? mesh.material : mesh.material ? [mesh.material] : [];
    materials.forEach((material) => {
      const tagged = material as THREE.Material & { opacity: number; transparent: boolean; userData: { baseOpacity?: number } };
      if (typeof tagged.opacity !== "number") return;
      if (tagged.userData.baseOpacity === undefined) tagged.userData.baseOpacity = tagged.opacity;
      tagged.transparent = true;
      tagged.opacity = tagged.userData.baseOpacity * opacity;
    });
  });
}

function detachImportedHero(hero: THREE.Group, shot: GiftShotId): void {
  const keep = new Set(shot === "yacht" ? ["yacht-water"] : shot === "stadium" ? ["flood-beam"] : []);
  [...hero.children].forEach((child) => {
    if (shot === "jet" && child.name === "jet-primitive") hero.remove(child);
    else if (shot === "yacht" && !keep.has(child.name)) hero.remove(child);
    else if (shot === "stadium" && child.name === "stadium-shell") hero.remove(child);
  });
}

export interface CinematicGiftEvent {
  id?: string;
  type?: string;
  gift_code: string;
  gift_name: string;
  sender: string;
  sender_id?: string;
  recipient?: string;
  recipient_id?: string;
  club_id?: string;
  match_id?: string;
  amount: number | string;
  rarity?: "common" | "rare" | "epic" | "legendary" | "mythic" | string;
  animation_key?: string;
  sound_key?: string;
  duration_ms?: number;
  combo_count?: number;
  club_crest_url?: string;
}

export interface CinematicGiftingEngineProps {
  activeGift: CinematicGiftEvent | null;
  onAnimationComplete?: () => void;
  soundEnabled?: boolean;
  className?: string;
}

export const CinematicGiftingEngine: React.FC<CinematicGiftingEngineProps> = ({
  activeGift,
  onAnimationComplete,
  soundEnabled = true,
  className = "",
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const keyLightRef = useRef<THREE.DirectionalLight | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const activeObjectsRef = useRef<THREE.Object3D[]>([]);
  const onCompleteRef = useRef(onAnimationComplete);
  useEffect(() => {
    onCompleteRef.current = onAnimationComplete;
  }, [onAnimationComplete]);

  const giftInstanceKey = activeGift
    ? String(
        activeGift.id ||
          `${activeGift.gift_code || ""}-${activeGift.animation_key || ""}-${activeGift.sender || ""}-${activeGift.amount ?? ""}`
      )
    : "";

  const [prefersReducedMotion, setPrefersReducedMotion] = useState(() => {
    if (typeof window !== "undefined" && typeof window.matchMedia === "function") {
      return Boolean(window.matchMedia("(prefers-reduced-motion: reduce)")?.matches);
    }
    return false;
  });
  const [contextLost, setContextLost] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mediaQuery.matches);
    const listener = (event: MediaQueryListEvent) => setPrefersReducedMotion(event.matches);
    mediaQuery.addEventListener("change", listener);
    return () => mediaQuery.removeEventListener("change", listener);
  }, []);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || prefersReducedMotion) return;

    const width = mount.clientWidth || 800;
    const height = mount.clientHeight || 450;
    const scene = new THREE.Scene();
    scene.background = null;
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 1000);
    camera.position.set(0, 6.2, 16);
    camera.lookAt(0, 3.2, 0);
    cameraRef.current = camera;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: "high-performance", preserveDrawingBuffer: false });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
      renderer.setClearColor(0x000000, 0);
      renderer.shadowMap.enabled = false;
      rendererRef.current = renderer;
    } catch {
      setContextLost(true);
      return;
    }

    const handleContextLost = (event: Event) => {
      event.preventDefault();
      setContextLost(true);
    };
    const handleContextRestored = () => setContextLost(false);
    renderer.domElement.addEventListener("webglcontextlost", handleContextLost, false);
    renderer.domElement.addEventListener("webglcontextrestored", handleContextRestored, false);
    mount.querySelectorAll("canvas").forEach((node) => node.remove());
    mount.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0xffffff, 0.72));
    const dirLight = new THREE.DirectionalLight(0xfff3d6, 1.6);
    dirLight.name = "gift-key";
    dirLight.position.set(15, 30, 20);
    scene.add(dirLight);
    keyLightRef.current = dirLight;
    const rimLight = new THREE.DirectionalLight(0x38bdf8, 1.1);
    rimLight.position.set(-20, 10, -15);
    scene.add(rimLight);

    const handleResize = () => {
      if (!mountRef.current || !rendererRef.current || !cameraRef.current) return;
      const nextWidth = mountRef.current.clientWidth;
      const nextHeight = mountRef.current.clientHeight;
      cameraRef.current.aspect = nextWidth / Math.max(nextHeight, 1);
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(nextWidth, nextHeight);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      renderer.domElement.removeEventListener("webglcontextlost", handleContextLost);
      renderer.domElement.removeEventListener("webglcontextrestored", handleContextRestored);
      renderer.dispose();
      renderer.domElement.remove();
      if (rendererRef.current === renderer) rendererRef.current = null;
      sceneRef.current = null;
      keyLightRef.current = null;
    };
  }, [prefersReducedMotion]);

  useEffect(() => {
    if (!activeGift || !giftInstanceKey) return;
    const duration = activeGift.duration_ms || 4500;
    const giftCode = (activeGift.gift_code || activeGift.animation_key || "").toLowerCase();
    const shot = resolveGiftShot(activeGift.animation_key, activeGift.gift_code);
    const isReducedMotion =
      prefersReducedMotion ||
      (typeof window !== "undefined" &&
        typeof window.matchMedia === "function" &&
        Boolean(window.matchMedia("(prefers-reduced-motion: reduce)")?.matches));
    if (soundEnabled && !isReducedMotion) {
      GtexCelebrationAudioEngine.playCelebrationCue(activeGift.sound_key, activeGift.gift_code || activeGift.animation_key, activeGift.rarity);
    }
    if (!sceneRef.current || isReducedMotion) {
      const fallbackTimer = setTimeout(() => onCompleteRef.current?.(), duration);
      return () => clearTimeout(fallbackTimer);
    }

    let cancelled = false;
    const scene = sceneRef.current;
    disposeObjectTree(activeObjectsRef.current, scene);
    activeObjectsRef.current = [];

    const rarity = (activeGift.rarity || "common").toLowerCase();
    const particleCount = rarity === "mythic" ? 350 : rarity === "legendary" ? 220 : 120;
    const particleGeo = new THREE.BufferGeometry();
    const pos = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const vels: THREE.Vector3[] = [];
    const palette =
      shot === "city"
        ? [0x93c5fd, 0xfde047, 0xffffff]
        : shot === "stadium" || shot === "golden_goal"
          ? [0xfde047, 0xf59e0b, 0xffffff]
          : shot === "jet"
            ? [0xe2e8f0, 0x38bdf8, 0xffffff]
            : [0xf59e0b, 0x10b981, 0x38bdf8, 0xffffff];
    for (let i = 0; i < particleCount; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 8;
      pos[i * 3 + 1] = Math.random() * 4 + 2;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 8;
      const color = new THREE.Color(palette[i % palette.length]);
      colors[i * 3] = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;
      vels.push(new THREE.Vector3((Math.random() - 0.5) * 0.28, Math.random() * 0.35 + 0.12, (Math.random() - 0.5) * 0.28));
    }
    particleGeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    particleGeo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    const particles = new THREE.Points(
      particleGeo,
      new THREE.PointsMaterial({ size: 0.45, vertexColors: true, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending })
    );
    scene.add(particles);
    activeObjectsRef.current.push(particles);

    const stageGroup = new THREE.Group();
    const hero = new THREE.Group();
    hero.name = "gift-hero";
    stageGroup.add(hero);
    if (shot === "card") addBoard(hero, 0xf59e0b, false);
    else if (shot === "tactics") addBoard(hero, 0x0ea5e9, true);
    else if (shot === "crown") {
      addBoard(hero, 0x0ea5e9, true);
      addCrown(hero);
    } else if (shot === "trophy") addTrophy(hero);
    else if (shot === "boot") addBoot(hero);
    else if (shot === "glove" || shot === "save") addGlove(hero);
    else if (shot === "stadium" || shot === "golden_goal") addStadium(hero, shot === "golden_goal" ? "golden_goal" : giftCode);
    else if (shot === "city") addCity(hero, giftCode);
    else if (shot === "jet") addJet(hero);
    else if (shot === "yacht") addYacht(hero);
    else if (shot === "goal" || shot === "last_minute" || shot === "bicycle" || shot === "hat_trick") addAtmosphere(hero, 0xf59e0b);
    else addAtmosphere(hero, giftCode.includes("horn") || giftCode.includes("roar") ? 0xf59e0b : 0x10b981);

    const ballShots: GiftShotId[] = ["goal", "last_minute", "bicycle", "golden_goal", "hat_trick", "save"];
    const ball = ballShots.includes(shot) ? makeBall(shot === "golden_goal" ? 0xfde047 : 0xf8fafc) : null;
    if (ball) stageGroup.add(ball);

    scene.add(stageGroup);
    activeObjectsRef.current.push(stageGroup);

    const modelPath = streamedModelFor(shot, giftCode);
    if (modelPath && typeof window !== "undefined" && !/jsdom/i.test(window.navigator?.userAgent || "")) {
      AssetStreamingCache.getInstance()
        .loadGltf(resolvePublicAssetPath(modelPath), rendererRef.current || undefined)
        .then((gltf) => {
          if (cancelled || !gltf?.scene) return;
          const imported = gltf.scene.clone(true);
          imported.traverse((child) => {
            const mesh = child as THREE.Mesh;
            if (!mesh.isMesh) return;
            if (mesh.geometry) mesh.geometry = mesh.geometry.clone();
            if (Array.isArray(mesh.material)) mesh.material = mesh.material.map((material) => material.clone());
            else if (mesh.material) mesh.material = mesh.material.clone();
          });
          const bbox = new THREE.Box3().setFromObject(imported);
          const size = new THREE.Vector3();
          const center = new THREE.Vector3();
          bbox.getSize(size);
          bbox.getCenter(center);
          const maxDim = Math.max(size.x, size.y, size.z, 0.001);
          const scale = (shot === "yacht" ? 14 : 16) / maxDim;
          imported.scale.setScalar(scale);
          imported.position.set(-center.x * scale, -bbox.min.y * scale, -center.z * scale);
          if (shot === "stadium") {
            imported.traverse((child) => {
              const mesh = child as THREE.Mesh;
              const material = mesh.material as THREE.MeshStandardMaterial;
              if (mesh.isMesh && material && "emissive" in material && !Array.isArray(mesh.material)) {
                material.emissive = new THREE.Color(0xf59e0b);
                material.emissiveIntensity = 0.22;
              }
            });
          }
          detachImportedHero(hero, shot);
          hero.add(imported);
        })
        .catch(() => {
          // Keep the procedural sculpture.
        });
    }

    const startTime = performance.now();
    let prevTime = startTime;
    const animate = (time: number) => {
      if (cancelled) return;
      const elapsed = time - startTime;
      const deltaSec = Math.min(Math.max((time - prevTime) / 1000, 0.001), 0.1);
      prevTime = time;
      const dtScale = deltaSec * 60;
      const progress = Math.min(elapsed / duration, 1);

      if (shot === "jet") {
        const glide = smoothstep(progress);
        hero.position.set(lerp(-18, 18, glide), 6 + Math.sin(progress * Math.PI) * 1.4, 0);
        hero.rotation.set(0.08, Math.PI / 2, Math.sin(progress * Math.PI) * -0.35);
      } else if (shot === "yacht") {
        hero.position.set(lerp(-8, 8, smoothstep(progress)), 0, 0);
        hero.rotation.set(0, 0.2, 0);
      } else {
        hero.position.set(0, 0, 0);
        hero.rotation.y = Math.sin(progress * Math.PI) * (shot === "city" || shot === "stadium" ? 0.22 : 0.4);
      }
      if (ball) placeBall(ball, shot, progress);
      if (cameraRef.current) placeCamera(cameraRef.current, shot, progress, hero);
      if (keyLightRef.current) {
        const hit = progress > 0.22 && progress < 0.72 ? Math.sin(((progress - 0.22) / 0.5) * Math.PI) : 0;
        keyLightRef.current.intensity = 1.5 + hit * 2.2;
      }
      const fade = progress < 0.72 ? 1 : 1 - smoothstep((progress - 0.72) / 0.28);
      if (fade < 1) fadeTree(stageGroup, fade);

      const posAttr = particleGeo.attributes.position as THREE.BufferAttribute;
      const positions = posAttr.array as Float32Array;
      for (let i = 0; i < particleCount; i++) {
        positions[i * 3] += vels[i].x * dtScale;
        positions[i * 3 + 1] += vels[i].y * dtScale;
        positions[i * 3 + 2] += vels[i].z * dtScale;
        vels[i].y -= 0.006 * dtScale;
        if (positions[i * 3 + 1] < 0) {
          positions[i * 3 + 1] = 0;
          vels[i].y = -vels[i].y * 0.4;
        }
      }
      posAttr.needsUpdate = true;
      if (rendererRef.current && sceneRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current);
      }
      if (progress < 1) animationFrameRef.current = requestAnimationFrame(animate);
      else onCompleteRef.current?.();
    };
    animationFrameRef.current = requestAnimationFrame(animate);

    return () => {
      cancelled = true;
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
      disposeObjectTree(activeObjectsRef.current, scene);
      activeObjectsRef.current = [];
    };
  }, [giftInstanceKey, prefersReducedMotion, soundEnabled]);

  if (!activeGift) return null;

  const rarityColor =
    activeGift.rarity === "mythic"
      ? "border-amber-300 bg-slate-950/80"
      : activeGift.rarity === "legendary"
        ? "border-amber-400 bg-slate-950/80"
        : activeGift.rarity === "epic"
          ? "border-indigo-300 bg-slate-950/80"
          : "border-emerald-400 bg-slate-950/75";
  const combo = Number(activeGift.combo_count || 1);

  return (
    <div
      data-testid="on-pitch-gift-animation"
      data-webgl-context={contextLost ? "lost" : "ready"}
      className={`absolute inset-0 z-30 pointer-events-none flex flex-col items-center justify-start overflow-hidden p-6 ${className}`}
    >
      <div ref={mountRef} className="absolute inset-0 pointer-events-none" />
      <div className="relative z-40 mt-2 flex flex-col items-center">
        <div className={`flex items-center gap-4 rounded-full border px-6 py-2.5 ${rarityColor}`}>
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-black/40 text-amber-300">
            <Trophy size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-black uppercase tracking-widest text-amber-200">{activeGift.gift_name}</span>
              <span className="rounded bg-black/50 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white">
                {activeGift.rarity || "common"}
              </span>
              {combo > 1 ? (
                <span data-testid="gift-combo-count" className="text-sm font-black text-amber-100">
                  x{combo}
                </span>
              ) : null}
            </div>
            <div className="text-xs text-white/95">
              <span className="font-bold text-emerald-300">{activeGift.sender}</span>
              {" backed "}
              <span className="font-semibold text-white">{activeGift.recipient || "the club"}</span>
              <span className="gx-mono ml-1 font-semibold text-amber-200">({activeGift.amount} FAN)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
