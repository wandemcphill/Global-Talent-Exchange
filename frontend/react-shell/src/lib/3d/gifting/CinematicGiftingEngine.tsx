import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { Sparkles, Trophy, Volume2, VolumeX } from "lucide-react";
import { GtexCelebrationAudioEngine } from "./GtexCelebrationAudioEngine";
import { AssetStreamingCache } from "../broadcast/AssetStreamingCache";
import { resolvePublicAssetPath } from "@/lib/publicPath";

function disposeObjectTree(objects: THREE.Object3D[], scene?: THREE.Scene | null): void {
  objects.forEach((root) => {
    if (scene) {
      scene.remove(root);
    }
    root.traverse((child) => {
      const mesh = child as THREE.Mesh;
      if (mesh.geometry && typeof mesh.geometry.dispose === "function") {
        mesh.geometry.dispose();
      }
      const mat = (mesh as any).material;
      if (Array.isArray(mat)) {
        mat.forEach((m) => m && typeof m.dispose === "function" && m.dispose());
      } else if (mat && typeof mat.dispose === "function") {
        mat.dispose();
      }
    });
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
  const animationFrameRef = useRef<number | null>(null);
  const activeObjectsRef = useRef<THREE.Object3D[]>([]);
  const particleSystemRef = useRef<THREE.Points | null>(null);
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

  // Check reduced motion preference
  useEffect(() => {
    if (typeof window !== "undefined" && window.matchMedia) {
      const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
      setPrefersReducedMotion(mediaQuery.matches);
      const listener = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
      mediaQuery.addEventListener("change", listener);
      return () => mediaQuery.removeEventListener("change", listener);
    }
  }, []);

  // Initialize Three.js scene
  useEffect(() => {
    if (!mountRef.current || prefersReducedMotion) return;

    const width = mountRef.current.clientWidth || 800;
    const height = mountRef.current.clientHeight || 450;

    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 15, 35);
    camera.lookAt(0, 4, 0);
    cameraRef.current = camera;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: "high-performance" });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.shadowMap.enabled = false;
      rendererRef.current = renderer;
      mountRef.current.appendChild(renderer.domElement);
    } catch {
      setContextLost(true);
      return;
    }

    // Context loss listeners
    const handleContextLost = (e: Event) => {
      e.preventDefault();
      setContextLost(true);
    };
    const handleContextRestored = () => {
      setContextLost(false);
    };
    renderer.domElement.addEventListener("webglcontextlost", handleContextLost, false);
    renderer.domElement.addEventListener("webglcontextrestored", handleContextRestored, false);

    // Global ambient and key lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xfff3d6, 1.6);
    dirLight.position.set(15, 30, 20);
    scene.add(dirLight);

    const rimLight = new THREE.DirectionalLight(0x38bdf8, 1.2);
    rimLight.position.set(-20, 10, -15);
    scene.add(rimLight);

    const handleResize = () => {
      if (!mountRef.current || !rendererRef.current || !cameraRef.current) return;
      const w = mountRef.current.clientWidth;
      const h = mountRef.current.clientHeight;
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(w, h);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
      disposeObjectTree(activeObjectsRef.current, sceneRef.current);
      activeObjectsRef.current = [];
      if (rendererRef.current?.domElement) {
        rendererRef.current.domElement.removeEventListener("webglcontextlost", handleContextLost);
        rendererRef.current.domElement.removeEventListener("webglcontextrestored", handleContextRestored);
        rendererRef.current.dispose();
        mountRef.current?.removeChild(rendererRef.current.domElement);
      }
    };
  }, [prefersReducedMotion]);

  // Build 3D Gift Animation Stage based on activeGift (keyed by giftInstanceKey to prevent parent re-render restarts)
  useEffect(() => {
    if (!activeGift || !giftInstanceKey) return;
    const duration = activeGift.duration_ms || 4500;
    const isReducedMotion =
      prefersReducedMotion ||
      (typeof window !== "undefined" &&
        typeof window.matchMedia === "function" &&
        Boolean(window.matchMedia("(prefers-reduced-motion: reduce)")?.matches));
    if (soundEnabled && !isReducedMotion) {
      GtexCelebrationAudioEngine.playCelebrationCue(
        activeGift.sound_key,
        activeGift.gift_code || activeGift.animation_key,
        activeGift.rarity
      );
    }
    if (!sceneRef.current || isReducedMotion) {
      const fallbackTimer = setTimeout(() => {
        onCompleteRef.current?.();
      }, duration);
      return () => clearTimeout(fallbackTimer);
    }

    let cancelled = false;
    const scene = sceneRef.current;
    // Clear and dispose previous active objects
    disposeObjectTree(activeObjectsRef.current, scene);
    activeObjectsRef.current = [];

    const giftCode = (activeGift.gift_code || activeGift.animation_key || "").toLowerCase();
    const rarity = (activeGift.rarity || "common").toLowerCase();

    // 1. Particle Confetti / Starburst Emitter
    const particleCount = rarity === "mythic" ? 350 : rarity === "legendary" ? 220 : 120;
    const particleGeo = new THREE.BufferGeometry();
    const pos = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const vels: THREE.Vector3[] = [];

    const paletteColors = [
      new THREE.Color(0xf59e0b), // Gold
      new THREE.Color(0x10b981), // Emerald
      new THREE.Color(0x38bdf8), // Cyan
      new THREE.Color(0xf43f5e), // Rose
      new THREE.Color(0xffffff), // White
    ];

    for (let i = 0; i < particleCount; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 8;
      pos[i * 3 + 1] = Math.random() * 4 + 2;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 8;

      const c = paletteColors[i % paletteColors.length];
      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;

      vels.push(
        new THREE.Vector3(
          (Math.random() - 0.5) * 0.28,
          Math.random() * 0.35 + 0.12,
          (Math.random() - 0.5) * 0.28
        )
      );
    }

    particleGeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    particleGeo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    const particleMat = new THREE.PointsMaterial({
      size: 0.65,
      vertexColors: true,
      transparent: true,
      opacity: 0.95,
      blending: THREE.AdditiveBlending,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);
    particleSystemRef.current = particles;
    activeObjectsRef.current.push(particles);

    // 2. Specialty 3D Models covering all 31 World of Football gift archetypes
    const stageGroup = new THREE.Group();

    if (
      giftCode.includes("maracana") ||
      giftCode.includes("wembley") ||
      giftCode.includes("camp_nou") ||
      giftCode.includes("stadium") ||
      giftCode.includes("san_siro")
    ) {
      // 3D Stadium Colosseum & Pitch Reveal (with gold/tifo/flare theme variants)
      const isGoldStadium = giftCode.includes("golden_stadium");
      const isFlares = giftCode.includes("san_siro") || giftCode.includes("flare");
      const bowlColor = isGoldStadium ? 0xd97706 : isFlares ? 0x7f1d1d : 0x1e293b;
      const bowlGeo = new THREE.CylinderGeometry(14, 11, 4, 32, 1, true);
      const bowlMat = new THREE.MeshStandardMaterial({
        color: bowlColor,
        metalness: isGoldStadium ? 0.9 : 0.6,
        roughness: isGoldStadium ? 0.2 : 0.3,
        side: THREE.DoubleSide,
      });
      const bowl = new THREE.Mesh(bowlGeo, bowlMat);
      bowl.position.y = 2;
      stageGroup.add(bowl);

      const pitchGeo = new THREE.PlaneGeometry(16, 11);
      const pitchMat = new THREE.MeshStandardMaterial({
        color: isGoldStadium ? 0xf59e0b : 0x059669,
        roughness: 0.6,
      });
      const pitch = new THREE.Mesh(pitchGeo, pitchMat);
      pitch.rotation.x = -Math.PI / 2;
      pitch.position.y = 0.1;
      stageGroup.add(pitch);

      const beamColor = isFlares ? 0xef4444 : isGoldStadium ? 0xfde047 : 0xfef08a;
      const beamGeo = new THREE.CylinderGeometry(0.2, 4.5, 24, 16);
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
        const beam = new THREE.Mesh(beamGeo, beamMat);
        beam.position.set(bx, 10, bz);
        beam.rotation.x = bz > 0 ? -0.25 : 0.25;
        stageGroup.add(beam);
      });
    } else if (
      giftCode.includes("paris") ||
      giftCode.includes("new_york") ||
      giftCode.includes("rio") ||
      giftCode.includes("lagos") ||
      giftCode.includes("tokyo") ||
      giftCode.includes("dubai") ||
      giftCode.includes("skyline")
    ) {
      // World Skyline Architectural Silhouette & City Beacon
      const isTokyo = giftCode.includes("tokyo");
      const isDubai = giftCode.includes("dubai");
      const isRio = giftCode.includes("rio");
      const isLagos = giftCode.includes("lagos");
      const primaryTowerHex = isTokyo
        ? 0xd946ef
        : isDubai
        ? 0xf59e0b
        : isRio
        ? 0x10b981
        : isLagos
        ? 0x22c55e
        : 0xb45309;
      const beaconHex = isTokyo ? 0x38bdf8 : isDubai ? 0xfde047 : 0x38bdf8;

      const towerBaseGeo = new THREE.CylinderGeometry(2, 5.5, 8, 6);
      const towerBaseMat = new THREE.MeshStandardMaterial({
        color: primaryTowerHex,
        metalness: 0.8,
        roughness: 0.22,
      });
      const towerBase = new THREE.Mesh(towerBaseGeo, towerBaseMat);
      towerBase.position.y = 4;
      stageGroup.add(towerBase);

      const spireGeo = new THREE.ConeGeometry(1.4, 11, 6);
      const spire = new THREE.Mesh(spireGeo, towerBaseMat);
      spire.position.y = 12.5;
      stageGroup.add(spire);

      // Flanking skyline towers
      [-5.5, 5.5].forEach((tx, idx) => {
        const subTower = new THREE.Mesh(
          new THREE.BoxGeometry(2.2, 6 + idx * 1.5, 2.2),
          towerBaseMat
        );
        subTower.position.set(tx, 3 + idx * 0.75, -1.5);
        stageGroup.add(subTower);
      });

      const beaconGeo = new THREE.ConeGeometry(6, 28, 16);
      const beaconMat = new THREE.MeshBasicMaterial({
        color: beaconHex,
        transparent: true,
        opacity: 0.45,
        blending: THREE.AdditiveBlending,
      });
      const beacon = new THREE.Mesh(beaconGeo, beaconMat);
      beacon.position.set(0, 16, 0);
      beacon.rotation.z = Math.PI / 2.3;
      stageGroup.add(beacon);
    } else if (giftCode.includes("jet") || giftCode.includes("flyby")) {
      // 3D Supersonic Private Jet
      const fuselageGeo = new THREE.ConeGeometry(1.6, 16, 16);
      const fuselageMat = new THREE.MeshStandardMaterial({ color: 0xf8fafc, metalness: 0.9, roughness: 0.1 });
      const fuselage = new THREE.Mesh(fuselageGeo, fuselageMat);
      fuselage.rotation.x = Math.PI / 2;
      fuselage.position.y = 6;
      stageGroup.add(fuselage);

      const wingGeo = new THREE.BoxGeometry(18, 0.2, 4);
      const wing = new THREE.Mesh(wingGeo, fuselageMat);
      wing.position.set(0, 6, -1);
      stageGroup.add(wing);
    } else if (giftCode.includes("yacht")) {
      // 3D Superyacht over illuminated marina water plane
      const water = new THREE.Mesh(
        new THREE.CylinderGeometry(11, 11, 0.4, 32),
        new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.75, roughness: 0.18 })
      );
      water.position.y = 0.2;
      stageGroup.add(water);

      const hull = new THREE.Mesh(
        new THREE.BoxGeometry(13, 2.2, 4.2),
        new THREE.MeshStandardMaterial({ color: 0xf8fafc, metalness: 0.65, roughness: 0.22 })
      );
      hull.position.y = 1.6;
      stageGroup.add(hull);

      const deck = new THREE.Mesh(
        new THREE.BoxGeometry(8.5, 1.8, 3.4),
        new THREE.MeshStandardMaterial({ color: 0x38bdf8, metalness: 0.85, roughness: 0.15 })
      );
      deck.position.set(-0.5, 3.4, 0);
      stageGroup.add(deck);
    } else if (giftCode.includes("crown")) {
      // 3D Sovereign Royal Crown with Gem Spires
      const goldMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, metalness: 0.95, roughness: 0.14 });
      const rubyMat = new THREE.MeshStandardMaterial({ color: 0xe11d48, metalness: 0.5, roughness: 0.15 });
      const band = new THREE.Mesh(new THREE.CylinderGeometry(4.8, 4.4, 2.4, 24, 1, true), goldMat);
      band.position.y = 5.0;
      stageGroup.add(band);

      for (let i = 0; i < 6; i++) {
        const angle = (i / 6) * Math.PI * 2;
        const spire = new THREE.Mesh(new THREE.ConeGeometry(0.85, 3.2, 8), goldMat);
        spire.position.set(Math.cos(angle) * 4.5, 7.6, Math.sin(angle) * 4.5);
        stageGroup.add(spire);

        const gem = new THREE.Mesh(new THREE.OctahedronGeometry(0.55, 0), rubyMat);
        gem.position.set(Math.cos(angle) * 4.6, 5.0, Math.sin(angle) * 4.6);
        stageGroup.add(gem);
      }
    } else if (
      giftCode.includes("trophy") ||
      giftCode.includes("winner") ||
      giftCode.includes("ballon") ||
      giftCode.includes("boot") ||
      giftCode.includes("glove") ||
      giftCode.includes("puskas") ||
      giftCode.includes("man_of_the_match") ||
      giftCode.includes("manager_of_the_month")
    ) {
      // 3D Champion Trophy / Golden Boot / Golden Glove / Individual Award Pedestal
      const goldMat = new THREE.MeshStandardMaterial({
        color: 0xf59e0b,
        metalness: 0.95,
        roughness: 0.15,
      });
      const pedestalGeo = new THREE.CylinderGeometry(5.5, 6.0, 3, 24);
      const marbleMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.4 });
      const pedestal = new THREE.Mesh(pedestalGeo, marbleMat);
      pedestal.position.y = 1.5;
      stageGroup.add(pedestal);

      if (giftCode.includes("boot")) {
        const bootShaft = new THREE.Mesh(new THREE.CylinderGeometry(1.4, 1.6, 4.8, 16), goldMat);
        bootShaft.position.set(-0.8, 5.4, 0);
        stageGroup.add(bootShaft);
        const bootFoot = new THREE.Mesh(new THREE.BoxGeometry(5.2, 1.8, 2.4), goldMat);
        bootFoot.position.set(0.8, 3.9, 0);
        stageGroup.add(bootFoot);
      } else if (giftCode.includes("glove")) {
        const palm = new THREE.Mesh(new THREE.BoxGeometry(3.8, 4.4, 1.2), goldMat);
        palm.position.set(0, 5.5, 0);
        stageGroup.add(palm);
        [-1.4, -0.5, 0.5, 1.4].forEach((fx) => {
          const finger = new THREE.Mesh(new THREE.CylinderGeometry(0.38, 0.38, 2.8, 12), goldMat);
          finger.position.set(fx, 8.8, 0);
          stageGroup.add(finger);
        });
      } else {
        const cupGeo = new THREE.CylinderGeometry(4.5, 2.0, 7, 24);
        const cup = new THREE.Mesh(cupGeo, goldMat);
        cup.position.y = 7;
        stageGroup.add(cup);

        const ballGeo = new THREE.SphereGeometry(2.4, 24, 24);
        const ball = new THREE.Mesh(ballGeo, goldMat);
        ball.position.y = 12.5;
        stageGroup.add(ball);
      }
    } else if (
      giftCode.includes("yellow_card") ||
      giftCode.includes("red_card") ||
      giftCode.includes("var") ||
      giftCode.includes("subs") ||
      giftCode.includes("tactical")
    ) {
      // Match Official & Tactical Props (Cards, VAR Monitor, LED Substitution Board, Tactical Board)
      const isRed = giftCode.includes("red_card");
      const isYellow = giftCode.includes("yellow_card");
      const cardColor = isRed ? 0xef4444 : isYellow ? 0xfacc15 : 0x0ea5e9;
      const frameMat = new THREE.MeshStandardMaterial({
        color: cardColor,
        metalness: 0.7,
        roughness: 0.2,
      });
      const boardGeo =
         isRed || isYellow
          ? new THREE.BoxGeometry(5.5, 8.2, 0.45)
          : new THREE.BoxGeometry(9.0, 5.8, 0.65);
      const board = new THREE.Mesh(boardGeo, frameMat);
      board.position.y = 6.5;
      stageGroup.add(board);
    } else {
      // Pitch & Supporter Atmosphere (Goal Horn, Stadium Roar, Corner Flag, Captain's Armband, Home Banner, Floodlights)
      const accentColor = giftCode.includes("horn") || giftCode.includes("roar") ? 0xf59e0b : 0x10b981;
      const ringMat = new THREE.MeshStandardMaterial({
        color: accentColor,
        metalness: 0.85,
        roughness: 0.2,
      });
      const torus = new THREE.Mesh(new THREE.TorusGeometry(4.2, 0.75, 16, 48), ringMat);
      torus.position.y = 6.5;
      stageGroup.add(torus);

      const core = new THREE.Mesh(new THREE.OctahedronGeometry(2.6, 0), ringMat);
      core.position.y = 6.5;
      stageGroup.add(core);
    }

    scene.add(stageGroup);
    activeObjectsRef.current.push(stageGroup);

    // Stream CC0 GLB upgrade when available (private_jet, superyacht, golden_stadium, trophy plinth)
    const glbAssetPath =
      giftCode.includes("jet") || giftCode.includes("flyby")
        ? "/assets/showroom/sovereign_900x_jet.glb"
        : giftCode.includes("yacht")
        ? "/assets/showroom/superyacht.glb"
        : giftCode.includes("golden_stadium")
        ? "/assets/showroom/golden_stadium.glb"
        : giftCode.includes("trophy") || giftCode.includes("winner") || giftCode.includes("ballon")
        ? "/assets/showroom/trophy_plinth.glb"
        : null;

    if (glbAssetPath && typeof window !== "undefined" && !/jsdom/i.test(window.navigator?.userAgent || "")) {
      const resolvedUrl = resolvePublicAssetPath(glbAssetPath);
      AssetStreamingCache.getInstance()
        .loadGltf(resolvedUrl, rendererRef.current || undefined)
        .then((gltf) => {
          if (cancelled || !gltf?.scene) return;
          const imported = gltf.scene.clone(true);
          const bbox = new THREE.Box3().setFromObject(imported);
          const size = new THREE.Vector3();
          const center = new THREE.Vector3();
          bbox.getSize(size);
          bbox.getCenter(center);
          const maxDim = Math.max(size.x, size.y, size.z, 0.001);
          const targetExtent = giftCode.includes("trophy") || giftCode.includes("ballon") ? 6.0 : 16.0;
          const scale = targetExtent / maxDim;
          imported.scale.setScalar(scale);
          imported.position.set(-center.x * scale, -bbox.min.y * scale + 2.0, -center.z * scale);

          if (giftCode.includes("golden_stadium")) {
            const goldOverride = new THREE.MeshStandardMaterial({
              color: 0xf59e0b,
              metalness: 0.9,
              roughness: 0.2,
            });
            imported.traverse((child) => {
              const mesh = child as THREE.Mesh;
              if (mesh.isMesh) {
                mesh.material = goldOverride;
              }
            });
          }

          if (!(giftCode.includes("trophy") || giftCode.includes("winner") || giftCode.includes("ballon"))) {
            while (stageGroup.children.length > 0) {
              const old = stageGroup.children[0];
              stageGroup.remove(old);
            }
          }
          stageGroup.add(imported);
        })
        .catch(() => {
          // Retain procedural fallback silently
        });
    }

    // Animation Loop (frame-rate independent via deltaSec)
    const startTime = performance.now();
    let prevTime = startTime;

    const animate = (time: number) => {
      if (cancelled) return;
      const elapsed = time - startTime;
      const deltaSec = Math.min(Math.max((time - prevTime) / 1000, 0.001), 0.1);
      prevTime = time;
      const dtScale = deltaSec * 60;
      const progress = Math.min(elapsed / duration, 1.0);

      // Rotate stage group
      stageGroup.rotation.y = elapsed * 0.0012;

      // Animate particles with frame-rate independent velocity & gravity
      const posAttr = particleGeo.attributes.position as THREE.BufferAttribute;
      const pArr = posAttr.array as Float32Array;
      for (let i = 0; i < particleCount; i++) {
        pArr[i * 3] += vels[i].x * dtScale;
        pArr[i * 3 + 1] += vels[i].y * dtScale;
        pArr[i * 3 + 2] += vels[i].z * dtScale;
        vels[i].y -= 0.006 * dtScale; // gravity

        if (pArr[i * 3 + 1] < 0) {
          pArr[i * 3 + 1] = 0;
          vels[i].y = -vels[i].y * 0.4; // bounce
        }
      }
      posAttr.needsUpdate = true;

      // Camera gentle dynamic pan
      if (cameraRef.current) {
        cameraRef.current.position.x = Math.sin(elapsed * 0.0008) * 6;
        cameraRef.current.position.y = 12 + Math.cos(elapsed * 0.0008) * 3;
        cameraRef.current.lookAt(0, 5, 0);
      }

      if (rendererRef.current && sceneRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current);
      }

      if (progress < 1.0) {
        animationFrameRef.current = requestAnimationFrame(animate);
      } else {
        onCompleteRef.current?.();
      }
    };

    animationFrameRef.current = requestAnimationFrame(animate);

    return () => {
      cancelled = true;
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, [giftInstanceKey, prefersReducedMotion, soundEnabled]);

  if (!activeGift) return null;

  const rarityColor =
    activeGift.rarity === "mythic"
      ? "from-amber-500 via-purple-600 to-rose-600 border-amber-300"
      : activeGift.rarity === "legendary"
      ? "from-amber-600 via-amber-500 to-yellow-400 border-amber-400"
      : activeGift.rarity === "epic"
      ? "from-purple-900 via-indigo-800 to-purple-950 border-purple-400"
      : "from-emerald-950 via-slate-900 to-emerald-950 border-emerald-400";

  return (
    <div
      data-testid="on-pitch-gift-animation"
      className={`absolute inset-0 z-30 pointer-events-none flex flex-col items-center justify-between overflow-hidden p-6 ${className}`}
    >
      {/* 3D WebGL Canvas Layer */}
      <div ref={mountRef} className="absolute inset-0 pointer-events-none" />

      {/* Top Floating Broadcast Ribbon */}
      <div className="relative z-40 mt-2 flex flex-col items-center animate-in fade-in slide-in-from-top-4 duration-500">
        <div
          className={`flex items-center gap-4 rounded-full border bg-gradient-to-r ${rarityColor} px-6 py-2.5 shadow-2xl backdrop-blur-md`}
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-black/40 text-amber-300 shadow-inner">
            <Trophy size={20} className="animate-pulse" />
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-black uppercase tracking-widest text-amber-300">
                {activeGift.gift_name} Delivered!
              </span>
              <span className="rounded bg-black/50 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white">
                {activeGift.rarity || "Legendary"}
              </span>
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

      {/* Bottom Subtitle / Stadium Audio Indicator */}
      <div className="relative z-40 mb-3 flex items-center gap-2 rounded-full border border-white/10 bg-slate-950/80 px-4 py-1 text-[11px] text-slate-300 backdrop-blur-md">
        <Sparkles size={12} className="text-amber-400" />
        <span>GTEX World of Football Celebration Engine</span>
        {soundEnabled ? <Volume2 size={12} className="text-emerald-400" /> : <VolumeX size={12} className="text-slate-500" />}
      </div>
    </div>
  );
};
