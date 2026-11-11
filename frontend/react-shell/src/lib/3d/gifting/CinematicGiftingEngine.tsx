import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { Trophy } from "lucide-react";
import { GtexCelebrationAudioEngine } from "./GtexCelebrationAudioEngine";
import { createGiftDirector } from "./giftScenes";
import { detectGiftQuality } from "./giftQuality";
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

  const [visualReady, setVisualReady] = useState(false);
  const [muted, setMuted] = useState(false);
  const mutedRef = useRef(false);
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
    const quality = detectGiftQuality(width, navigator.hardwareConcurrency || 8);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x07111f);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 400);
    camera.position.set(0, 6.2, 16);
    camera.lookAt(0, 3.2, 0);
    cameraRef.current = camera;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        alpha: false,
        antialias: quality.antialias,
        powerPreference: "high-performance",
        preserveDrawingBuffer: false,
      });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, quality.pixelRatioCap));
      renderer.setClearColor(0x07111f, 1);
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.12;
      renderer.shadowMap.enabled = quality.shadows;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
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

    scene.add(new THREE.AmbientLight(0xffffff, 0.18));
    const dirLight = new THREE.DirectionalLight(0xfff3d6, 0.85);
    dirLight.name = "gift-key";
    dirLight.position.set(12, 24, 14);
    dirLight.castShadow = quality.shadows;
    dirLight.shadow.mapSize.set(1024, 1024);
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 80;
    const shadowCam = dirLight.shadow.camera as THREE.OrthographicCamera;
    shadowCam.left = -18;
    shadowCam.right = 18;
    shadowCam.top = 18;
    shadowCam.bottom = -18;
    scene.add(dirLight);
    keyLightRef.current = dirLight;
    try {
      void import("three/examples/jsm/environments/RoomEnvironment.js").then(({ RoomEnvironment }) => {
        if (!rendererRef.current || rendererRef.current !== renderer) return;
        const pmrem = new THREE.PMREMGenerator(renderer);
        const envTarget = pmrem.fromScene(new RoomEnvironment(), 0.04);
        pmrem.dispose();
        scene.environment = envTarget.texture;
        scene.userData.giftEnv = envTarget;
      });
    } catch {
      // Headless contexts keep the hemisphere and key light.
    }

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
      const envTarget = scene.userData.giftEnv as THREE.WebGLRenderTarget | undefined;
      if (envTarget) {
        if (scene.environment === envTarget.texture) scene.environment = null;
        envTarget.dispose();
      }
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
    if (soundEnabled && !mutedRef.current && !isReducedMotion) {
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
    setVisualReady(false);

    const width = mountRef.current?.clientWidth || 1280;
    const quality = detectGiftQuality(width, navigator.hardwareConcurrency || 8);
    const canStream = typeof window !== "undefined" && !/jsdom/i.test(window.navigator?.userAgent || "");
    let assetsReady = false;
    const openedAt = performance.now();
    const startTime = { value: 0 };
    let prevTime = openedAt;
    let animate: ((time: number) => void) | null = null;
    const director = createGiftDirector({
      shot,
      giftCode,
      rarity: activeGift.rarity || "common",
      quality,
      canStream,
      resolveUrl: resolvePublicAssetPath,
      isCancelled: () => cancelled,
      onReady: () => {
        assetsReady = true;
        startTime.value = 0;
        const shell = mountRef.current?.parentElement;
        if (shell) shell.setAttribute("data-gift-progress", "0.000");
        if (!cancelled && animate && animationFrameRef.current == null) {
          prevTime = performance.now();
          animationFrameRef.current = requestAnimationFrame(animate);
        }
        if (!cancelled) setVisualReady(true);
      },
    });
    scene.add(director.root);
    scene.background = director.background;
    if (rendererRef.current) {
      rendererRef.current.setClearColor(director.background, 1);
      rendererRef.current.toneMappingExposure = director.exposure;
    }
    const dramatic = shot === "trophy" || shot === "jet" || shot === "yacht" || shot === "bicycle" || shot === "last_minute";
    if (keyLightRef.current) keyLightRef.current.castShadow = Boolean(quality.shadows && dramatic);

    const animateFrame = (time: number) => {
      if (cancelled) return;
      const deltaSec = Math.min(Math.max((time - prevTime) / 1000, 0.001), 0.1);
      prevTime = time;
      if (!startTime.value) {
        const waiting = !assetsReady && time - openedAt < 70000;
        if (waiting) {
          if (cameraRef.current) director.update(0, deltaSec, cameraRef.current);
          if (rendererRef.current && cameraRef.current) rendererRef.current.render(scene, cameraRef.current);
          animationFrameRef.current = requestAnimationFrame(animateFrame);
          return;
        }
        startTime.value = time;
      }
      const holdAt = Number(new URLSearchParams(window.location.search).get("at"));
      let progress = Math.min((time - startTime.value) / duration, 1);
      const holding = Number.isFinite(holdAt) && holdAt > 0 && holdAt < 1;
      if (holding && progress > holdAt) progress = holdAt;
      if (cameraRef.current) director.update(progress, deltaSec, cameraRef.current);
      const shell = mountRef.current?.parentElement;
      if (shell) shell.setAttribute("data-gift-progress", progress.toFixed(3));
      if (rendererRef.current && cameraRef.current) rendererRef.current.render(scene, cameraRef.current);
      if (progress < 1 || holding) animationFrameRef.current = requestAnimationFrame(animateFrame);
      else {
        animationFrameRef.current = null;
        onCompleteRef.current?.();
      }
    };
    animate = animateFrame;
    animationFrameRef.current = requestAnimationFrame(animateFrame);

    return () => {
      cancelled = true;
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
      scene.remove(director.root);
      director.dispose();
    };

  }, [giftInstanceKey, prefersReducedMotion, soundEnabled]);

  if (!activeGift) return null;

  const rarity = String(activeGift.rarity || "common").toUpperCase();
  const rarityAccent =
    activeGift.rarity === "mythic" || activeGift.rarity === "legendary"
      ? "#f5cd83"
      : activeGift.rarity === "epic"
        ? "#b8a6ff"
        : activeGift.rarity === "rare"
          ? "#8de0e8"
          : "#e7edf5";
  const combo = Number(activeGift.combo_count || 1);

  return (
    <div
      data-testid="on-pitch-gift-animation"
      data-webgl-context={contextLost ? "lost" : "ready"}
      data-gift-visual={visualReady ? "ready" : "loading"}
      data-gift-shot={resolveGiftShot(activeGift.animation_key, activeGift.gift_code)}
      className={\`absolute inset-0 z-30 pointer-events-none flex flex-col items-center justify-end overflow-hidden \${className}\`}
    >
      <style>{\`
        @keyframes gtex-gift-caption-in {
          from { opacity: 0; transform: translate3d(0, 18px, 0); filter: blur(8px); }
          to { opacity: 1; transform: translate3d(0, 0, 0); filter: blur(0); }
        }
        @keyframes gtex-gift-rule-in {
          from { transform: scaleX(.15); opacity: 0; }
          to { transform: scaleX(1); opacity: .9; }
        }
        @keyframes gtex-gift-lens-breathe {
          0%, 100% { opacity: .3; }
          50% { opacity: .52; }
        }
        .gtex-gift-caption {
          animation: gtex-gift-caption-in 680ms cubic-bezier(.18,.72,.2,1) both;
          text-shadow: 0 2px 24px rgba(0,0,0,.62), 0 1px 3px rgba(0,0,0,.85);
        }
        .gtex-gift-caption-rule {
          transform-origin: center;
          animation: gtex-gift-rule-in 900ms cubic-bezier(.18,.72,.2,1) 140ms both;
        }
        .gtex-gift-lens {
          animation: gtex-gift-lens-breathe 4.8s ease-in-out infinite;
          mix-blend-mode: screen;
        }
        @media (prefers-reduced-motion: reduce) {
          .gtex-gift-caption, .gtex-gift-caption-rule, .gtex-gift-lens { animation: none; }
        }
      \`}</style>
      <div ref={mountRef} className="absolute inset-0 pointer-events-none" />
      <div
        aria-hidden
        className="gtex-gift-lens absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at 50% 42%, transparent 34%, rgba(2,6,14,.22) 72%, rgba(2,6,14,.52) 100%)",
        }}
      />
      <div
        aria-hidden
        className="absolute inset-x-0 bottom-0 h-[48%]"
        style={{
          background:
            "linear-gradient(180deg, rgba(3,7,15,0) 0%, rgba(3,7,15,.14) 30%, rgba(3,7,15,.72) 100%)",
        }}
      />
      <button
        type="button"
        data-testid="gift-mute"
        aria-label={muted ? "Turn gift sound on" : "Turn gift sound off"}
        className="pointer-events-auto absolute right-4 top-4 z-50 rounded-full bg-black/30 px-3 py-2 text-[10px] font-semibold tracking-wide text-white/80 backdrop-blur-md transition hover:bg-black/55 hover:text-white"
        onClick={() => {
          mutedRef.current = !mutedRef.current;
          setMuted(mutedRef.current);
          GtexCelebrationAudioEngine.setMuted(mutedRef.current);
        }}
      >
        {muted ? "SOUND OFF" : "SOUND ON"}
      </button>
      <div className="gtex-gift-caption relative z-40 mb-[7vh] flex w-full justify-center px-5 sm:px-8">
        <div className="w-full max-w-2xl text-center">
          <div className="flex items-center justify-center gap-3">
            <span
              aria-hidden
              className="gtex-gift-caption-rule h-px w-8 sm:w-12"
              style={{ background: \`linear-gradient(90deg, transparent, \${rarityAccent})\` }}
            />
            <span
              className="text-[10px] font-semibold uppercase tracking-[.34em] sm:text-xs"
              style={{ color: rarityAccent }}
            >
              {rarity} GIFT
            </span>
            <span
              aria-hidden
              className="gtex-gift-caption-rule h-px w-8 sm:w-12"
              style={{ background: \`linear-gradient(90deg, \${rarityAccent}, transparent)\` }}
            />
          </div>
          <div className="mt-3 text-2xl font-black leading-tight tracking-[-.035em] text-white sm:mt-4 sm:text-4xl">
            {activeGift.gift_name}
          </div>
          <div className="mt-2 text-xs font-medium tracking-wide text-white/80 sm:text-sm">
            <span className="font-semibold text-white">{activeGift.sender}</span>
            <span className="mx-2 text-white/45">SENT TO</span>
            <span className="font-semibold text-white">{activeGift.recipient || "the club"}</span>
          </div>
          <div className="mt-2 flex items-center justify-center gap-3 text-[10px] font-medium tracking-[.18em] text-white/60 sm:text-xs">
            <span>{activeGift.amount} FAN</span>
            {combo > 1 ? (
              <>
                <span aria-hidden className="h-1 w-1 rounded-full bg-white/40" />
                <span data-testid="gift-combo-count">{\`COMBO ×\${combo}\`}</span>
              </>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
};
