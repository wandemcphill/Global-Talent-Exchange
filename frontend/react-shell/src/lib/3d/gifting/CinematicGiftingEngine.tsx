import React, { useEffect, useRef, useState, useCallback } from "react";
import * as THREE from "three";
import { Sparkles, Trophy, Shield, Volume2, VolumeX } from "lucide-react";
import { GtexCelebrationAudioEngine } from "./GtexCelebrationAudioEngine";

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

  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
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
      if (rendererRef.current?.domElement) {
        rendererRef.current.domElement.removeEventListener("webglcontextlost", handleContextLost);
        rendererRef.current.domElement.removeEventListener("webglcontextrestored", handleContextRestored);
        rendererRef.current.dispose();
        mountRef.current?.removeChild(rendererRef.current.domElement);
      }
    };
  }, [prefersReducedMotion]);

  // Build 3D Gift Animation Stage based on activeGift
  useEffect(() => {
    if (!activeGift) return;
    if (soundEnabled) {
      GtexCelebrationAudioEngine.playCelebrationCue(
        activeGift.sound_key,
        activeGift.gift_code || activeGift.animation_key,
        activeGift.rarity
      );
    }
    if (!sceneRef.current || prefersReducedMotion) return;

    const scene = sceneRef.current;
    // Clear previous active objects
    activeObjectsRef.current.forEach((obj) => scene.remove(obj));
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

    // 2. Specialty 3D Models
    const stageGroup = new THREE.Group();

    if (giftCode.includes("maracana") || giftCode.includes("wembley") || giftCode.includes("stadium") || giftCode.includes("san_siro")) {
      // 3D Stadium Colosseum & Pitch Reveal
      const bowlGeo = new THREE.CylinderGeometry(14, 11, 4, 32, 1, true);
      const bowlMat = new THREE.MeshStandardMaterial({
        color: 0x1e293b,
        metalness: 0.6,
        roughness: 0.3,
        side: THREE.DoubleSide,
      });
      const bowl = new THREE.Mesh(bowlGeo, bowlMat);
      bowl.position.y = 2;
      stageGroup.add(bowl);

      // Emerald pitch inside bowl
      const pitchGeo = new THREE.PlaneGeometry(16, 11);
      const pitchMat = new THREE.MeshStandardMaterial({ color: 0x059669, roughness: 0.6 });
      const pitch = new THREE.Mesh(pitchGeo, pitchMat);
      pitch.rotation.x = -Math.PI / 2;
      pitch.position.y = 0.1;
      stageGroup.add(pitch);

      // 4 Corner floodlight beams
      const beamGeo = new THREE.CylinderGeometry(0.2, 4.5, 24, 16);
      const beamMat = new THREE.MeshBasicMaterial({
        color: 0xfef08a,
        transparent: true,
        opacity: 0.35,
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
    } else if (giftCode.includes("paris")) {
      // 3D Miniature Eiffel Tower
      const towerBaseGeo = new THREE.CylinderGeometry(2, 6, 8, 4);
      const towerBaseMat = new THREE.MeshStandardMaterial({ color: 0xb45309, metalness: 0.8, roughness: 0.2 });
      const towerBase = new THREE.Mesh(towerBaseGeo, towerBaseMat);
      towerBase.position.y = 4;
      stageGroup.add(towerBase);

      const spireGeo = new THREE.ConeGeometry(1.2, 10, 4);
      const spire = new THREE.Mesh(spireGeo, towerBaseMat);
      spire.position.y = 12;
      stageGroup.add(spire);

      // Beacon Light Sweeper
      const beaconGeo = new THREE.ConeGeometry(6, 28, 16);
      const beaconMat = new THREE.MeshBasicMaterial({
        color: 0x38bdf8,
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
    } else if (giftCode.includes("trophy") || giftCode.includes("winner") || giftCode.includes("ballon")) {
      // 3D Champion Trophy / Golden Ball
      const cupGeo = new THREE.CylinderGeometry(4.5, 2.0, 7, 24);
      const goldMat = new THREE.MeshStandardMaterial({
        color: 0xf59e0b,
        metalness: 0.95,
        roughness: 0.15,
      });
      const cup = new THREE.Mesh(cupGeo, goldMat);
      cup.position.y = 7;
      stageGroup.add(cup);

      const pedestalGeo = new THREE.CylinderGeometry(5.5, 6.0, 3, 24);
      const marbleMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.4 });
      const pedestal = new THREE.Mesh(pedestalGeo, marbleMat);
      pedestal.position.y = 1.5;
      stageGroup.add(pedestal);

      // Golden Football on top
      const ballGeo = new THREE.SphereGeometry(2.4, 24, 24);
      const ball = new THREE.Mesh(ballGeo, goldMat);
      ball.position.y = 12.5;
      stageGroup.add(ball);
    } else {
      // Classic Diamond Celebration Badge
      const prismGeo = new THREE.OctahedronGeometry(4.5, 0);
      const prismMat = new THREE.MeshStandardMaterial({
        color: 0x10b981,
        metalness: 0.8,
        roughness: 0.2,
        wireframe: false,
      });
      const prism = new THREE.Mesh(prismGeo, prismMat);
      prism.position.y = 6;
      stageGroup.add(prism);
    }

    scene.add(stageGroup);
    activeObjectsRef.current.push(stageGroup);

    // Animation Loop
    const startTime = performance.now();
    const duration = activeGift.duration_ms || 4500;

    const animate = (time: number) => {
      const elapsed = time - startTime;
      const progress = Math.min(elapsed / duration, 1.0);

      // Rotate stage group
      stageGroup.rotation.y = elapsed * 0.0012;

      // Animate particles
      const posAttr = particleGeo.attributes.position as THREE.BufferAttribute;
      const pArr = posAttr.array as Float32Array;
      for (let i = 0; i < particleCount; i++) {
        pArr[i * 3] += vels[i].x;
        pArr[i * 3 + 1] += vels[i].y;
        pArr[i * 3 + 2] += vels[i].z;
        vels[i].y -= 0.006; // gravity

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
        onAnimationComplete?.();
      }
    };

    animationFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, [activeGift, prefersReducedMotion, onAnimationComplete]);

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
