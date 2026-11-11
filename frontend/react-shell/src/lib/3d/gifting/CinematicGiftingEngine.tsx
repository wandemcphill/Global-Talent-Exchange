import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GtexCelebrationAudioEngine } from "./GtexCelebrationAudioEngine";
import { createGiftDirector } from "./giftScenes";
import { detectGiftQuality } from "./giftQuality";
import { resolvePublicAssetPath } from "@/lib/publicPath";

const VIDEO_GIFT_DURATION_MS = 8042;

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
  if (code.includes("gulfstream")) return "/assets/showroom/gulfstream_g700_exec_jet.glb";
  if (code.includes("jet") || code.includes("flyby")) return "/assets/showroom/sovereign_900x_jet.glb";
  if (code.includes("yacht")) return "/assets/showroom/superyacht.glb";
  if (code.includes("golden_stadium")) return "/assets/showroom/golden_stadium.glb";
  if (
    code.includes("maracana") ||
    code.includes("wembley") ||
    code.includes("san_siro") ||
    code.includes("camp_nou") ||
    code.includes("football_stadium")
  ) {
    return "/assets/showroom/arena_imperiale_stadium.glb";
  }
  if (code.includes("watch") || code.includes("chronos")) return "/assets/showroom/chronos_tourbillon_watch.glb";
  if (code.includes("penthouse")) return "/assets/showroom/royal_penthouse_box.glb";
  if (code.includes("bus") || code.includes("coach")) return "/assets/showroom/vanguard_xii_coach.glb";
  if (code.includes("hypercar") || code.includes("veloce")) return "/assets/showroom/veloce_gt9_hypercar.glb";
  if (code.includes("suv")) return "/assets/showroom/executive_suv.glb";
  if (code.includes("campus") || code.includes("facility")) return "/assets/showroom/apex_performance_campus.glb";
  if (code.includes("trophy") || code.includes("ballon_dor") || code === "ballon_dor") {
    return "/assets/showroom/trophy_plinth.glb";
  }
  // No matching authored hero model: leave the reveal atmospheric instead of
  // returning an unrelated trophy, watch or football-stadium model.
  return "";
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
  | "coach"
  | "vehicle"
  | "facility"
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
  chronos_tourbillon_watch: "crown",
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
  gulfstream_g700: "jet",
  luxury_superyacht: "yacht",
  superyacht: "yacht",
  luxury_team_coach: "coach",
  team_coach: "coach",
  vanguard_xii_coach: "coach",
  executive_suv: "vehicle",
  veloce_gt9_hypercar: "vehicle",
  apex_performance_campus: "facility",
  performance_campus: "facility",
  goal_celebration: "goal",
  last_minute_winner: "last_minute",
  bicycle_kick: "bicycle",
  golden_goal: "golden_goal",
  perfect_hat_trick: "hat_trick",
  world_class_save: "save",
};

const SHOT_NEEDLES: Array<[string, GiftShotId]> = [
  ["vanguard_xii_coach", "coach"],
  ["coach", "coach"],
  ["bus", "coach"],
  ["veloce_gt9_hypercar", "vehicle"],
  ["hypercar", "vehicle"],
  ["executive_suv", "vehicle"],
  ["suv", "vehicle"],
  ["apex_performance_campus", "facility"],
  ["campus", "facility"],
  ["facility", "facility"],
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
  ["gulfstream", "jet"],
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
  ["royal_penthouse", "city"],
  ["penthouse", "city"],
  ["chronos_tourbillon_watch", "crown"],
  ["watch", "crown"],
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

const GIFT_VIDEO_BY_SHOT: Partial<Record<GiftShotId, string>> = {
  atmosphere: "/assets/gifting/gtex-gift-atmosphere.mp4",
  card: "/assets/gifting/gtex-gift-card.mp4",
  tactics: "/assets/gifting/gtex-gift-tactics.mp4",
  trophy: "/assets/gifting/gtex-gift-trophy.mp4",
  boot: "/assets/gifting/gtex-gift-boot.mp4",
  glove: "/assets/gifting/gtex-gift-glove.mp4",
  city: "/assets/gifting/gtex-gift-city.mp4",
  jet: "/assets/gifting/gtex-gift-jet.mp4",
  yacht: "/assets/gifting/gtex-gift-yacht.mp4",
  coach: "/assets/gifting/gtex-gift-coach.mp4",
  vehicle: "/assets/gifting/gtex-gift-hypercar.mp4",
  facility: "/assets/gifting/gtex-gift-campus.mp4",
  goal: "/assets/gifting/gtex-gift-goal.mp4",
  last_minute: "/assets/gifting/gtex-gift-last-minute.mp4",
  bicycle: "/assets/gifting/gtex-gift-bicycle.mp4",
  golden_goal: "/assets/gifting/gtex-gift-golden-goal.mp4",
  hat_trick: "/assets/gifting/gtex-gift-hat-trick.mp4",
  save: "/assets/gifting/gtex-gift-save.mp4",
};

/** Resolve only a clip that matches the gift being sent; unknown matches stay on WebGL. */
export function resolveGiftVideoPath(giftCode: string, shot: GiftShotId): string {
  const code = giftCode.toLowerCase().replace(/-/g, "_");
  if (shot === "stadium") {
    return code.includes("maracana") ? "/assets/gifting/gtex-maracana-gift.mp4" : "";
  }
  // The supplied crown clip is for a crown gift, not the Chronos watch.
  if (shot === "crown" && (code.includes("watch") || code.includes("chronos"))) return "";
  return GIFT_VIDEO_BY_SHOT[shot] || "";
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
  const composerRef = useRef<{
    setSize: (width: number, height: number) => void;
    dispose: () => void;
    render: () => void;
  } | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const keyLightRef = useRef<THREE.DirectionalLight | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const activeObjectsRef = useRef<THREE.Object3D[]>([]);
  const onCompleteRef = useRef(onAnimationComplete);
  const audioGiftKeyRef = useRef("");
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
  const [loadedVideoKey, setLoadedVideoKey] = useState("");
  const [failedVideoKey, setFailedVideoKey] = useState("");
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
      if (quality.tier !== "low") {
        void Promise.all([
          import("three/examples/jsm/postprocessing/EffectComposer.js"),
          import("three/examples/jsm/postprocessing/RenderPass.js"),
          import("three/examples/jsm/postprocessing/UnrealBloomPass.js"),
          import("three/examples/jsm/postprocessing/OutputPass.js"),
        ])
          .then(([composerModule, renderModule, bloomModule, outputModule]) => {
            if (rendererRef.current !== renderer) return;
            const composer = new composerModule.EffectComposer(renderer);
            composer.setPixelRatio(renderer.getPixelRatio());
            composer.setSize(width, height);
            composer.addPass(new renderModule.RenderPass(scene, camera));
            composer.addPass(
              new bloomModule.UnrealBloomPass(
                new THREE.Vector2(width, height),
                quality.tier === "high" ? 0.48 : 0.28,
                0.42,
                0.86
              )
            );
            composer.addPass(new outputModule.OutputPass());
            composerRef.current = composer;
          })
          .catch((error) => {
            console.warn("Gift bloom pipeline unavailable; using direct renderer", error);
          });
      }
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
        if (!rendererRef.current || rendererRef.current !== renderer || scene.environment) return;
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
      composerRef.current?.setSize(nextWidth, nextHeight);
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
      composerRef.current?.dispose();
      composerRef.current = null;
      renderer.dispose();
      renderer.domElement.remove();
      if (rendererRef.current === renderer) rendererRef.current = null;
      sceneRef.current = null;
      keyLightRef.current = null;
    };
  }, [prefersReducedMotion]);

  useEffect(() => {
    if (!activeGift || !giftInstanceKey) return;
    const giftCode = (activeGift.gift_code || activeGift.animation_key || "").toLowerCase();
    const shot = resolveGiftShot(activeGift.animation_key, activeGift.gift_code);
    const videoPath = resolveGiftVideoPath(giftCode, shot);
    const isReducedMotion =
      prefersReducedMotion ||
      (typeof window !== "undefined" &&
        typeof window.matchMedia === "function" &&
        Boolean(window.matchMedia("(prefers-reduced-motion: reduce)")?.matches));
    const baseDuration = activeGift.duration_ms || 4500;
    const duration = videoPath && !isReducedMotion
      ? Math.max(baseDuration, VIDEO_GIFT_DURATION_MS)
      : baseDuration;
    if (soundEnabled && !mutedRef.current && !isReducedMotion && audioGiftKeyRef.current !== giftInstanceKey) {
      GtexCelebrationAudioEngine.playCelebrationCue(activeGift.sound_key, activeGift.gift_code || activeGift.animation_key, activeGift.rarity);
      audioGiftKeyRef.current = giftInstanceKey;
    }
    if (!isReducedMotion && videoPath && loadedVideoKey === giftInstanceKey) {
      setVisualReady(true);
      const videoTimer = window.setTimeout(() => onCompleteRef.current?.(), duration);
      return () => window.clearTimeout(videoTimer);
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

    const environmentPath =
      shot === "city" || shot === "trophy" || shot === "boot" || shot === "glove" || shot === "crown"
        ? "/textures/env/modern_buildings_night_2k.hdr"
        : shot === "jet" || shot === "yacht"
          ? "/textures/env/kloofendal_43d_clear_puresky_2k.hdr"
          : "/textures/env/stadium_01_1k.hdr";
    const activeRenderer = rendererRef.current;
    if (activeRenderer) {
      void import("three/examples/jsm/loaders/RGBELoader.js")
        .then(({ RGBELoader }) => new Promise<THREE.DataTexture>((resolve, reject) => {
          new RGBELoader().load(resolvePublicAssetPath(environmentPath), resolve, undefined, reject);
        }))
        .then((texture) => {
          if (cancelled || rendererRef.current !== activeRenderer) {
            texture.dispose();
            return;
          }
          try {
            const pmrem = new THREE.PMREMGenerator(activeRenderer);
            pmrem.compileEquirectangularShader();
            const envTarget = pmrem.fromEquirectangular(texture);
            pmrem.dispose();
            texture.dispose();
            const previous = scene.userData.giftEnv as THREE.WebGLRenderTarget | undefined;
            if (previous) previous.dispose();
            scene.environment = envTarget.texture;
            scene.userData.giftEnv = envTarget;
          } catch (error) {
            texture.dispose();
            console.warn("Gift HDR environment could not be prepared", error);
          }
        })
        .catch((error) => {
          if (!cancelled) console.warn("Gift HDR environment could not be loaded", error);
        });
    }
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
          if (composerRef.current) composerRef.current.render();
          else if (rendererRef.current && cameraRef.current) rendererRef.current.render(scene, cameraRef.current);
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
      if (composerRef.current) composerRef.current.render();
      else if (rendererRef.current && cameraRef.current) rendererRef.current.render(scene, cameraRef.current);
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

  }, [giftInstanceKey, prefersReducedMotion, soundEnabled, loadedVideoKey, failedVideoKey]);

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
  const giftShot = resolveGiftShot(activeGift.animation_key, activeGift.gift_code);
  const giftVideoPath = resolveGiftVideoPath(activeGift.gift_code, giftShot);
  const showGiftVideo = Boolean(
    giftVideoPath &&
      !prefersReducedMotion &&
      loadedVideoKey === giftInstanceKey &&
      failedVideoKey !== giftInstanceKey
  );

  return (
    <div
      data-testid="on-pitch-gift-animation"
      data-webgl-context={contextLost ? "lost" : "ready"}
      data-gift-visual={visualReady ? "ready" : "loading"}
      data-gift-shot={giftShot}
      data-gift-media={showGiftVideo ? "video" : "webgl"}
      className={`absolute inset-0 z-30 pointer-events-none flex flex-col items-center justify-end overflow-hidden ${className}`}
    >
      <style>{`
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
        .gtex-gift-video { object-fit: cover; }
        @media (max-aspect-ratio: 4/5) { .gtex-gift-video { object-fit: contain; background: #050910; } }
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
      `}</style>
      {giftVideoPath && !prefersReducedMotion && failedVideoKey !== giftInstanceKey ? (
        <video
          key={giftInstanceKey}
          data-testid="gift-cinematic-video"
          data-gift-video={giftVideoPath}
          aria-hidden="true"
          autoPlay
          muted
          playsInline
          preload="auto"
          src={resolvePublicAssetPath(giftVideoPath)}
          onPlaying={() => {
            setLoadedVideoKey(giftInstanceKey);
            setVisualReady(true);
          }}
          onError={() => {
            setFailedVideoKey(giftInstanceKey);
            setLoadedVideoKey("");
          }}
          className={`gtex-gift-video absolute inset-0 z-20 h-full w-full pointer-events-none transition-opacity duration-300 ${showGiftVideo ? "opacity-100" : "opacity-0"}`}
        />
      ) : null}
      <div
        ref={mountRef}
        className={`absolute inset-0 z-10 pointer-events-none transition-opacity duration-300 ${showGiftVideo ? "opacity-0" : "opacity-100"}`}
      />
      <div
        aria-hidden
        className="gtex-gift-lens absolute inset-0 z-30"
        style={{
          background:
            "radial-gradient(ellipse at 50% 42%, transparent 34%, rgba(2,6,14,.22) 72%, rgba(2,6,14,.52) 100%)",
        }}
      />
      <div
        aria-hidden
        className="absolute inset-x-0 bottom-0 z-30 h-[48%]"
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
              style={{ background: `linear-gradient(90deg, transparent, ${rarityAccent})` }}
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
              style={{ background: `linear-gradient(90deg, ${rarityAccent}, transparent)` }}
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
                <span data-testid="gift-combo-count">{`COMBO ×${combo}`}</span>
              </>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
};
