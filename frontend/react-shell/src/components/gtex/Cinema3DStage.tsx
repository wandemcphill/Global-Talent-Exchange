import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Camera,
  Film,
  RotateCcw,
  Sparkles,
  Volume2,
  VolumeX,
  Play,
  Pause,
  Shield,
  Award,
  Layers,
  Trophy,
  Radio,
  Tv,
  Crown,
  ThumbsUp,
  RefreshCw,
  Clapperboard,
  Palette,
} from "lucide-react";

export type Cinema3DSceneType =
  | "signing_walkout"
  | "negotiation_table"
  | "luxury_turntable"
  | "world_gala"
  | "build_a_son"
  | "manager_arrival"
  | "stadium_sponsor"
  | "boardroom_clash"
  | "club_takeover"
  | "facility_upgrade"
  | "academy_upgrade"
  | "wonderkid_emergence"
  | "competition_final"
  | "stadium_ad_display"
  | "new_ad_deal"
  | "club_announcement"
  | "private_jet_flex";

export type Cinema3DMode = "motion_3d" | "fm_diorama";

export interface Cinema3DStageProps {
  scene: Cinema3DSceneType;
  title: string;
  subtitle?: string;
  badgeText?: string;
  clubName?: string;
  ownerName?: string;
  primaryColor?: string;
  secondaryColor?: string;
  subjectName?: string;
  subjectRole?: string;
  jerseyNumber?: number | string;
  overallRating?: number | string;
  potentialRating?: number | string;
  sponsorName?: string;
  facilityLevel?: number;
  adSurfaceZone?: string;
  spectacleTier?: "standard_press" | "floodlight_walkout" | "galactico_helicopter";
  assetCategory?: "watch" | "jet" | "car" | "facility" | "trophy" | string;
  quote?: string;
  stats?: Array<{ label: string; value: string; accent?: string }>;
  videoUrl?: string;
  defaultMode?: Cinema3DMode;
  compact?: boolean;
  agentMood?: "calm" | "tense" | "eager" | "hostile";
  enableSocialSalute?: boolean;
  initialSalutes?: number;
  onActionClick?: () => void;
  actionLabel?: string;
}

interface BurstParticle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  color: string;
  alpha: number;
  rot: number;
}

/**
 * GTEX Next-Gen v2.0 Volumetric 3D Presentation, Broadcast & Diorama Engine
 * Features:
 *  1. True Dual-Sided 180° 3D Volumes (Front Face + Extruded Metallic Side Slabs + True Reverse Back Face)
 *  2. `Director Cut` 3-Shot FIFA Walkout Camera Choreography (Macro Close-Up -> 180° Back Reveal -> Hero Wide Orbit)
 *  3. Interactive 60fps Canvas Pyro, Confetti & Paparazzi Flashbulb Physics
 *  4. Zero-Asset Procedural WebAudio Sound Synthesizer (Walkout Sub-Bass Boom, Pyro Pop, Camera Shutter)
 *  5. Interactive 3D Kit / Livery Variant Switcher (Home / Away Gold / Midnight Blackout)
 */
export const Cinema3DStage: React.FC<Cinema3DStageProps> = ({
  scene,
  title,
  subtitle,
  badgeText,
  clubName = "GTEX FC",
  ownerName = "Club Owner",
  primaryColor = "#00E676",
  secondaryColor = "#F5B83D",
  subjectName = "MARQUEE STAR",
  subjectRole = "First-Team Signing",
  jerseyNumber = 9,
  overallRating = 88,
  potentialRating,
  sponsorName = "GTEX GLOBAL AIRWAYS",
  facilityLevel: rawFacilityLevel = 4,
  adSurfaceZone = "360° Pitchside LED & Roof Naming Halo",
  spectacleTier = "floodlight_walkout",
  assetCategory = "watch",
  quote,
  stats = [],
  videoUrl,
  defaultMode = "motion_3d",
  compact = false,
  agentMood = "eager",
  enableSocialSalute = false,
  initialSalutes = 48,
  onActionClick,
  actionLabel,
}) => {
  const facilityLevel = Number(
    typeof rawFacilityLevel === 'object' && rawFacilityLevel !== null
      ? (rawFacilityLevel as any).level ?? 1
      : rawFacilityLevel
  ) || 1;
  const [mode, setMode] = useState<Cinema3DMode>(defaultMode);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [soundEnabled, setSoundEnabled] = useState<boolean>(false);
  const [rotY, setRotY] = useState<number>(-18);
  const [rotX, setRotX] = useState<number>(8);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [cameraAngle, setCameraAngle] = useState<"wide" | "hero" | "closeup">("hero");
  const [directorShotLabel, setDirectorShotLabel] = useState<string | null>(null);
  const [liveryVariant, setLiveryVariant] = useState<"home" | "gold" | "midnight">("home");
  const [saluteCount, setSaluteCount] = useState<number>(initialSalutes);
  const [hasSaluted, setHasSaluted] = useState<boolean>(false);

  const targetRotYRef = useRef<number | null>(null);
  const directorTimerRef = useRef<number | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const burstParticlesRef = useRef<BurstParticle[]>([]);

  const dragStartRef = useRef<{ x: number; y: number; rotY: number; rotX: number }>({
    x: 0,
    y: 0,
    rotY: -18,
    rotX: 8,
  });
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Compute active livery palette based on user customizer toggle
  const activePrimary =
    liveryVariant === "gold"
      ? "#F5B83D"
      : liveryVariant === "midnight"
      ? "#38BDF8"
      : primaryColor;
  const activeSecondary =
    liveryVariant === "gold"
      ? "#FEF08A"
      : liveryVariant === "midnight"
      ? "#A855F7"
      : secondaryColor;

  // Zero-Asset Procedural WebAudio Synthesizer
  const playProceduralSfx = useCallback(
    (kind: "boom" | "pyro" | "flip", forcePlay = false) => {
      if (!soundEnabled && !forcePlay) return;
      try {
        const AudioContextClass =
          window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        if (!AudioContextClass) return;
        if (!audioCtxRef.current) {
          audioCtxRef.current = new AudioContextClass();
        }
        const ctx = audioCtxRef.current;
        const now = ctx.currentTime;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        if (kind === "boom") {
          osc.type = "sine";
          osc.frequency.setValueAtTime(115, now);
          osc.frequency.exponentialRampToValueAtTime(28, now + 0.65);
          gain.gain.setValueAtTime(0.24, now);
          gain.gain.exponentialRampToValueAtTime(0.001, now + 0.7);
        } else if (kind === "pyro") {
          osc.type = "triangle";
          osc.frequency.setValueAtTime(260, now);
          osc.frequency.exponentialRampToValueAtTime(48, now + 0.45);
          gain.gain.setValueAtTime(0.18, now);
          gain.gain.exponentialRampToValueAtTime(0.001, now + 0.5);
        } else {
          osc.type = "sine";
          osc.frequency.setValueAtTime(180, now);
          osc.frequency.exponentialRampToValueAtTime(75, now + 0.25);
          gain.gain.setValueAtTime(0.14, now);
          gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
        }

        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.72);
      } catch {
        // Ignore audio autoplay blocks
      }
    },
    [soundEnabled]
  );

  // Trigger 60fps Pyro & Confetti Fountain Burst
  const triggerPyroBurst = useCallback(() => {
    const palette = [activePrimary, activeSecondary, "#FFFFFF", "#FDE047", "#38BDF8"];
    const nextParticles: BurstParticle[] = [];
    for (let i = 0; i < 56; i++) {
      nextParticles.push({
        x: 200 + Math.random() * 400,
        y: 340,
        vx: (Math.random() - 0.5) * 9,
        vy: -(4.2 + Math.random() * 7.5),
        size: 3.5 + Math.random() * 4.5,
        color: palette[i % palette.length],
        alpha: 1,
        rot: Math.random() * Math.PI,
      });
    }
    burstParticlesRef.current = [...burstParticlesRef.current.slice(-60), ...nextParticles];
    playProceduralSfx("pyro");
  }, [activePrimary, activeSecondary, playProceduralSfx]);

  // Flip 180° between Front Face and True Back Face
  const handleFlip180 = () => {
    const norm = ((rotY % 360) + 360) % 360;
    const isCurrentlyBack = norm > 90 && norm < 270;
    targetRotYRef.current = isCurrentlyBack ? -18 : 165;
    playProceduralSfx("flip");
  };

  // Run 3-Shot FIFA Pack-Walkout Director Cut Choreography
  const handleDirectorCut = () => {
    if (directorTimerRef.current) {
      window.clearTimeout(directorTimerRef.current);
    }
    setMode("motion_3d");
    setIsPlaying(true);
    setDirectorShotLabel("SHOT 1 · MACRO CREST CLOSE-UP");
    setCameraAngle("closeup");
    setRotX(14);
    targetRotYRef.current = -14;
    playProceduralSfx("boom");

    directorTimerRef.current = window.setTimeout(() => {
      setDirectorShotLabel("SHOT 2 · 180° BACK PRINT & PYRO REVEAL");
      setCameraAngle("hero");
      setRotX(6);
      targetRotYRef.current = 172;
      triggerPyroBurst();

      directorTimerRef.current = window.setTimeout(() => {
        setDirectorShotLabel("SHOT 3 · HERO WIDE 360° ORBIT");
        setCameraAngle("hero");
        setRotX(8);
        targetRotYRef.current = -18;
        triggerPyroBurst();

        directorTimerRef.current = window.setTimeout(() => {
          setDirectorShotLabel(null);
          targetRotYRef.current = null;
        }, 1600);
      }, 1700);
    }, 1500);
  };

  useEffect(() => {
    return () => {
      if (directorTimerRef.current) {
        window.clearTimeout(directorTimerRef.current);
      }
    };
  }, []);

  // Smooth orbital oscillation / 360 rotation + target interpolation
  useEffect(() => {
    if (isDragging) return;
    let rafId: number;
    let lastTime = performance.now();
    const animate = (now: number) => {
      const dt = (now - lastTime) / 1000;
      lastTime = now;
      setRotY((prev) => {
        if (targetRotYRef.current !== null) {
          const diff = targetRotYRef.current - prev;
          if (Math.abs(diff) < 0.8) {
            const snapped = targetRotYRef.current;
            targetRotYRef.current = null;
            return snapped;
          }
          return prev + diff * Math.min(1, dt * 7.5);
        }
        if (mode === "motion_3d" && isPlaying) {
          return (prev + dt * 24) % 360;
        }
        return prev;
      });
      rafId = requestAnimationFrame(animate);
    };
    rafId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafId);
  }, [mode, isPlaying, isDragging]);

  // 60fps Volumetric Stadium Lighting, Runway Approach Strobes, Flashbulbs & Pyro Particles
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let tick = 0;

    const isGoldHeavy =
      scene === "world_gala" ||
      scene === "competition_final" ||
      scene === "wonderkid_emergence" ||
      scene === "club_takeover" ||
      scene === "private_jet_flex";

    const particles = Array.from({ length: compact ? 36 : 64 }, (_, i) => ({
      x: (i * 73) % 800,
      y: (i * 47) % 420,
      z: 0.25 + ((i * 19) % 75) / 100,
      vx: (((i * 13) % 10) - 5) * 0.28,
      vy: isGoldHeavy || scene === "signing_walkout" ? 0.65 + (i % 5) * 0.2 : -0.35,
      size: 2 + (i % 4),
      gold: i % 2 === 0,
    }));

    const flashes = Array.from({ length: 7 }, (_, i) => ({
      x: 85 + i * 105,
      y: 55 + (i % 3) * 42,
      phase: i * 0.95,
    }));

    const render = () => {
      if (mode === "motion_3d" && isPlaying) {
        tick += 0.028;
      }
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      // 1. Deep Atmospheric 3D Horizon & Rim Glow
      const bgGrad = ctx.createRadialGradient(w * 0.5, h * 0.28, 12, w * 0.5, h * 0.52, w * 0.78);
      if (isGoldHeavy) {
        bgGrad.addColorStop(0, "rgba(78, 52, 12, 0.94)");
        bgGrad.addColorStop(0.5, "rgba(18, 15, 28, 0.97)");
        bgGrad.addColorStop(1, "rgba(4, 5, 10, 1)");
      } else if (
        scene === "facility_upgrade" ||
        scene === "academy_upgrade" ||
        scene === "stadium_ad_display"
      ) {
        bgGrad.addColorStop(0, "rgba(12, 58, 86, 0.94)");
        bgGrad.addColorStop(0.55, "rgba(8, 18, 34, 0.97)");
        bgGrad.addColorStop(1, "rgba(3, 6, 13, 1)");
      } else if (scene === "club_announcement" || scene === "new_ad_deal") {
        bgGrad.addColorStop(0, "rgba(64, 18, 44, 0.94)");
        bgGrad.addColorStop(0.55, "rgba(12, 14, 28, 0.97)");
        bgGrad.addColorStop(1, "rgba(4, 6, 12, 1)");
      } else {
        bgGrad.addColorStop(0, "rgba(10, 62, 44, 0.92)");
        bgGrad.addColorStop(0.55, "rgba(8, 18, 32, 0.97)");
        bgGrad.addColorStop(1, "rgba(3, 7, 14, 1)");
      }
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, w, h);

      // 2. 3D Perspective Floor Grid & Runway Strobes
      const horizonY = h * 0.62;
      ctx.save();
      ctx.strokeStyle = isGoldHeavy
        ? "rgba(245, 184, 61, 0.2)"
        : scene === "facility_upgrade" || scene === "academy_upgrade"
        ? "rgba(56, 189, 248, 0.24)"
        : "rgba(0, 230, 118, 0.16)";
      ctx.lineWidth = 1;

      const vpX = w * 0.5 + Math.sin(tick * 0.6) * (mode === "motion_3d" ? 20 : 0);
      for (let i = -9; i <= 9; i++) {
        ctx.beginPath();
        ctx.moveTo(vpX, horizonY);
        ctx.lineTo(vpX + i * 92, h);
        ctx.stroke();
      }
      for (let r = 1; r <= 7; r++) {
        const py = horizonY + Math.pow(r / 7, 1.75) * (h - horizonY);
        ctx.beginPath();
        ctx.moveTo(0, py);
        ctx.lineTo(w, py);
        ctx.stroke();

        if (scene === "private_jet_flex" || spectacleTier === "galactico_helicopter") {
          const strobeAlpha = 0.35 + 0.65 * Math.max(0, Math.sin(tick * 5 - r * 0.7));
          ctx.fillStyle = `rgba(245, 184, 61, ${strobeAlpha})`;
          ctx.beginPath();
          ctx.arc(vpX - r * 28, py, 2.5, 0, Math.PI * 2);
          ctx.arc(vpX + r * 28, py, 2.5, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      ctx.restore();

      // 3. Volumetric 3D Floodlight Cones with Lens Flare Source
      const beamCount = 4;
      for (let b = 0; b < beamCount; b++) {
        const bx = (w / (beamCount + 1)) * (b + 1);
        const sway = mode === "motion_3d" ? Math.sin(tick * 1.15 + b * 1.3) * 48 : 0;
        const beamGrad = ctx.createLinearGradient(bx, 0, bx + sway, h * 0.88);
        const beamColor =
          b % 2 === 0
            ? "rgba(245, 184, 61, 0.18)"
            : "rgba(0, 230, 118, 0.14)";
        beamGrad.addColorStop(0, beamColor);
        beamGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

        ctx.save();
        ctx.fillStyle = beamGrad;
        ctx.beginPath();
        ctx.moveTo(bx - 14, 0);
        ctx.lineTo(bx + 14, 0);
        ctx.lineTo(bx + sway + 135, h * 0.9);
        ctx.lineTo(bx + sway - 135, h * 0.9);
        ctx.closePath();
        ctx.fill();

        const bulb = ctx.createRadialGradient(bx, 6, 1, bx, 6, 26);
        bulb.addColorStop(0, "rgba(255,255,255,0.85)");
        bulb.addColorStop(1, "rgba(255,255,255,0)");
        ctx.fillStyle = bulb;
        ctx.beginPath();
        ctx.arc(bx, 6, 26, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }

      // 4. Paparazzi Camera Flashbulbs
      flashes.forEach((f) => {
        const pulse = Math.max(0, Math.sin(tick * 3.9 + f.phase));
        if (pulse > 0.82) {
          const radius = (pulse - 0.82) * 200;
          const fg = ctx.createRadialGradient(f.x, f.y, 1, f.x, f.y, radius);
          fg.addColorStop(0, "rgba(255, 255, 255, 0.92)");
          fg.addColorStop(0.3, "rgba(245, 184, 61, 0.38)");
          fg.addColorStop(1, "rgba(255, 255, 255, 0)");
          ctx.fillStyle = fg;
          ctx.beginPath();
          ctx.arc(f.x, f.y, radius, 0, Math.PI * 2);
          ctx.fill();
        }
      });

      // 5. Ambient Floating 3D Depth Particles
      particles.forEach((p) => {
        if (mode === "motion_3d" && isPlaying) {
          p.x = (p.x + p.vx + w) % w;
          p.y = (p.y + p.vy + h) % h;
        }
        ctx.save();
        ctx.fillStyle = p.gold
          ? `rgba(245, 184, 61, ${0.38 + p.z * 0.5})`
          : `rgba(56, 189, 248, ${0.28 + p.z * 0.45})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * p.z, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      });

      // 6. Active Pyro & Confetti Burst Particles
      const bursts = burstParticlesRef.current;
      for (let i = bursts.length - 1; i >= 0; i--) {
        const bp = bursts[i];
        bp.x += bp.vx;
        bp.y += bp.vy;
        bp.vy += 0.22;
        bp.alpha -= 0.015;
        if (bp.alpha <= 0) {
          bursts.splice(i, 1);
          continue;
        }
        ctx.save();
        ctx.globalAlpha = Math.max(0, bp.alpha);
        ctx.fillStyle = bp.color;
        ctx.translate(bp.x, bp.y);
        ctx.rotate(bp.rot + bp.alpha * 5);
        ctx.fillRect(-bp.size / 2, -bp.size / 2, bp.size, bp.size * 0.65);
        ctx.restore();
      }

      if ((mode === "motion_3d" && isPlaying) || burstParticlesRef.current.length > 0) {
        animationFrameId = requestAnimationFrame(render);
      }
    };

    render();
    return () => {
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
    };
  }, [scene, mode, isPlaying, spectacleTier, compact]);

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    setIsDragging(true);
    targetRotYRef.current = null;
    dragStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      rotY,
      rotX,
    };
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!isDragging) return;
    const dx = e.clientX - dragStartRef.current.x;
    const dy = e.clientY - dragStartRef.current.y;
    setRotY(dragStartRef.current.rotY + dx * 0.65);
    setRotX(Math.max(-22, Math.min(24, dragStartRef.current.rotX - dy * 0.3)));
  };

  const handlePointerUp = () => {
    setIsDragging(false);
  };

  const cameraScale = cameraAngle === "closeup" ? 1.22 : cameraAngle === "wide" ? 0.88 : 1.0;
  const specularX = 50 + Math.sin((rotY * Math.PI) / 180) * 40;
  const surname = subjectName.split(" ").slice(-1)[0] || subjectName;
  const normAngle = ((rotY % 360) + 360) % 360;
  const isShowingBackFace = normAngle > 90 && normAngle < 270;

  return (
    <div
      className="relative overflow-hidden rounded-2xl border transition-all select-none"
      style={{
        borderColor:
          scene === "world_gala" ||
          scene === "competition_final" ||
          scene === "private_jet_flex" ||
          scene === "wonderkid_emergence"
            ? "rgba(245, 184, 61, 0.65)"
            : "rgba(0, 230, 118, 0.4)",
        background: "#04070F",
        boxShadow: "0 24px 60px rgba(0, 0, 0, 0.75), inset 0 1px 0 rgba(255,255,255,0.12)",
      }}
    >
      {/* Top Broadcast Control Bar */}
      <div
        className="relative z-20 flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 border-b"
        style={{
          background: "linear-gradient(90deg, rgba(8,12,24,0.96), rgba(16,24,42,0.94))",
          borderColor: "rgba(255,255,255,0.08)",
        }}
      >
        <div className="flex items-center gap-2">
          <span
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
            style={{
              background:
                mode === "motion_3d"
                  ? "rgba(0, 230, 118, 0.16)"
                  : "rgba(56, 189, 248, 0.16)",
              color: mode === "motion_3d" ? "#00E676" : "#38BDF8",
              border: `1px solid ${
                mode === "motion_3d" ? "rgba(0,230,118,0.4)" : "rgba(56,189,248,0.4)"
              }`,
            }}
          >
            {mode === "motion_3d" ? <Film size={11} /> : <Camera size={11} />}
            {mode === "motion_3d" ? "3D Motion Cinema (FIFA/eFootball)" : "3D Static Diorama (FM Style)"}
          </span>
          {badgeText && (
            <span
              className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
              style={{
                background: "rgba(245, 184, 61, 0.16)",
                color: "var(--gtex-gold)",
                border: "1px solid rgba(245, 184, 61, 0.4)",
              }}
            >
              {badgeText}
            </span>
          )}
        </div>

        {/* v2.0 Mode, Director Cut, 180° Flip, Pyro & Camera Switcher */}
        <div className="flex flex-wrap items-center gap-1.5">
          {/* Director Cut 3-Shot Button */}
          <button
            type="button"
            onClick={handleDirectorCut}
            className="px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-wider transition-all flex items-center gap-1 bg-amber-400 text-slate-950 hover:bg-amber-300 shadow"
            title="Play 3-Shot FIFA Walkout Director Cut"
          >
            <Clapperboard size={11} /> Director Cut
          </button>

          {/* 180° Front/Back Flip Button */}
          <button
            type="button"
            onClick={handleFlip180}
            className="px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all flex items-center gap-1 bg-white/10 hover:bg-white/15 text-white border border-white/15"
            title="Flip 180° between Front and True Back Face"
          >
            <RefreshCw size={11} className="text-emerald-400" /> Flip 180°
          </button>

          {/* Pyro Confetti Burst Button */}
          <button
            type="button"
            onClick={triggerPyroBurst}
            className="px-2 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all flex items-center gap-1 bg-white/5 hover:bg-white/15 text-amber-300 border border-amber-400/30"
            title="Fire Club Confetti & Pyro Burst"
          >
            <Sparkles size={11} /> Pyro
          </button>

          {/* Livery / Kit Edition Switcher */}
          <button
            type="button"
            onClick={() =>
              setLiveryVariant((v) =>
                v === "home" ? "gold" : v === "gold" ? "midnight" : "home"
              )
            }
            className="px-2 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all flex items-center gap-1 bg-white/5 hover:bg-white/15 text-cyan-300 border border-cyan-400/30"
            title="Cycle 3D Livery / Kit Edition (Home / Gold / Midnight)"
          >
            <Palette size={11} /> {liveryVariant}
          </button>

          <div className="inline-flex rounded-lg p-0.5 bg-black/50 border border-white/10">
            <button
              type="button"
              onClick={() => setMode("motion_3d")}
              className="px-2 py-1 rounded-md text-[10px] font-semibold transition-all flex items-center gap-1"
              style={{
                background: mode === "motion_3d" ? "rgba(0, 230, 118, 0.22)" : "transparent",
                color: mode === "motion_3d" ? "#00E676" : "var(--gtex-text-muted)",
              }}
            >
              <Film size={11} /> 3D Motion
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("fm_diorama");
                targetRotYRef.current = null;
                setRotY(-18);
                setRotX(8);
              }}
              className="px-2 py-1 rounded-md text-[10px] font-semibold transition-all flex items-center gap-1"
              style={{
                background: mode === "fm_diorama" ? "rgba(56, 189, 248, 0.22)" : "transparent",
                color: mode === "fm_diorama" ? "#38BDF8" : "var(--gtex-text-muted)",
              }}
            >
              <Camera size={11} /> FM Still
            </button>
          </div>

          <div className="hidden lg:inline-flex rounded-lg p-0.5 bg-black/50 border border-white/10">
            {(["wide", "hero", "closeup"] as const).map((cam) => (
              <button
                key={cam}
                type="button"
                onClick={() => setCameraAngle(cam)}
                className="px-2 py-1 rounded text-[10px] font-bold uppercase transition-all"
                style={{
                  background: cameraAngle === cam ? "rgba(245, 184, 61, 0.22)" : "transparent",
                  color: cameraAngle === cam ? "var(--gtex-gold)" : "var(--gtex-text-muted)",
                }}
              >
                {cam}
              </button>
            ))}
          </div>

          {mode === "motion_3d" && (
            <button
              type="button"
              onClick={() => setIsPlaying((p) => !p)}
              title={isPlaying ? "Pause 3D Motion" : "Play 3D Motion"}
              className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/80"
            >
              {isPlaying ? <Pause size={13} /> : <Play size={13} />}
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              targetRotYRef.current = null;
              setRotY(-18);
              setRotX(8);
              setCameraAngle("hero");
            }}
            title="Reset 3D Camera"
            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/80"
          >
            <RotateCcw size={13} />
          </button>
          <button
            type="button"
            onClick={() => {
              const next = !soundEnabled;
              setSoundEnabled(next);
              if (next) playProceduralSfx("boom", true);
            }}
            title="Toggle Procedural WebAudio Walkout & Pyro SFX"
            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/80"
          >
            {soundEnabled ? <Volume2 size={13} className="text-emerald-400" /> : <VolumeX size={13} />}
          </button>
        </div>
      </div>

      {/* Main 3D Stage Viewport */}
      <div
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
        className={`relative w-full ${
          compact ? "h-[285px]" : "h-[370px]"
        } flex items-center justify-center cursor-grab active:cursor-grabbing overflow-hidden`}
        style={{ perspective: "1200px" }}
      >
        {/* Background Volumetric 3D Canvas */}
        <canvas
          ref={canvasRef}
          width={800}
          height={420}
          className="absolute inset-0 w-full h-full object-cover pointer-events-none"
        />

        {/* Optional Pre-Rendered 3D Video Override Slot */}
        {videoUrl && mode === "motion_3d" && (
          <video
            src={videoUrl}
            autoPlay
            loop
            muted={!soundEnabled}
            playsInline
            className="absolute inset-0 w-full h-full object-cover opacity-55 pointer-events-none"
          />
        )}

        {/* Deep Plane (-140px): Architectural Stadium / Step-and-Repeat Press Wall */}
        <div
          className="absolute inset-x-10 top-5 bottom-16 rounded-2xl pointer-events-none transition-transform duration-150"
          style={{
            transform: `translateZ(-140px) rotateX(${rotX * 0.25}deg) rotateY(${rotY * 0.14}deg) scale(${cameraScale})`,
            border: "1px solid rgba(255,255,255,0.08)",
            background:
              "radial-gradient(circle at 50% 20%, rgba(255,255,255,0.06), rgba(0,0,0,0.55))",
            boxShadow: "inset 0 0 40px rgba(0,0,0,0.8)",
          }}
        >
          <div className="grid grid-cols-4 gap-3 p-4 opacity-25 text-[10px] font-black tracking-widest uppercase text-center text-white">
            {Array.from({ length: 12 }).map((_, idx) => (
              <div key={idx} className="border border-white/15 rounded py-1 px-2 truncate">
                {idx % 2 === 0 ? clubName : sponsorName}
              </div>
            ))}
          </div>
        </div>

        {/* Floor Plane: Multi-Ring Illuminated 3D Pedestal & Cast Shadow */}
        <div
          className="absolute bottom-6 w-80 h-24 rounded-full pointer-events-none"
          style={{
            transform: `rotateX(76deg) rotateZ(${rotY}deg) scale(${cameraScale})`,
            background:
              "radial-gradient(circle, rgba(245,184,61,0.42) 0%, rgba(0,230,118,0.22) 48%, rgba(56,189,248,0.12) 68%, transparent 78%)",
            border: `2px solid ${activePrimary}`,
            boxShadow: `0 0 45px ${activePrimary}66, inset 0 0 25px ${activeSecondary}44`,
          }}
        />
        <div
          className="absolute bottom-9 w-56 h-16 rounded-full pointer-events-none border border-dashed border-emerald-400/50"
          style={{
            transform: `rotateX(76deg) rotateZ(${-rotY * 1.4}deg) scale(${cameraScale})`,
          }}
        />

        {/* True Multi-Layer Dual-Sided 180° Volumetric 3D Centerpiece Assembly */}
        <div
          className="relative z-10 transition-transform duration-75"
          style={{
            transformStyle: "preserve-3d",
            transform: `scale(${cameraScale}) rotateX(${rotX}deg) rotateY(${rotY}deg)`,
          }}
        >
          {/* Extruded Side Wall Slabs (-10px, -5px, 0px, +5px, +10px) for solid 3D thickness at 90° */}
          {[-10, -5, 0, 5, 10].map((z) => (
            <div
              key={z}
              className="absolute inset-1 rounded-2xl pointer-events-none"
              style={{
                transform: `translateZ(${z}px)`,
                border: `2px solid ${activePrimary}55`,
                background: "rgba(9, 14, 28, 0.55)",
              }}
            />
          ))}

          {/* =====================================================================
              TRUE REVERSE BACK FACE (rotateY(180deg) translateZ(16px))
              Visible whenever rotated 90°..270° or via "Flip 180°" button!
             ===================================================================== */}
          <div
            className="absolute inset-0 rounded-2xl p-4 border-2 flex flex-col items-center justify-between text-center overflow-hidden"
            style={{
              transform: "rotateY(180deg) translateZ(16px)",
              backfaceVisibility: "hidden",
              background: "linear-gradient(150deg, rgba(15,23,42,0.98), rgba(4,8,18,0.99))",
              borderColor: activeSecondary,
              boxShadow: `0 22px 50px rgba(0,0,0,0.85), inset 0 0 28px ${activeSecondary}33`,
            }}
          >
            <div className="w-full flex items-center justify-between text-[10px] font-black uppercase tracking-wider text-amber-300 border-b border-white/10 pb-1.5">
              <span>
                {scene === "private_jet_flex" || scene === "luxury_turntable"
                  ? "🛋️ VIP INTERIOR / CASEBACK"
                  : scene === "facility_upgrade" ||
                    scene === "academy_upgrade" ||
                    scene === "stadium_ad_display"
                  ? "📐 3D ENGINEERING BLUEPRINT"
                  : "🔄 OFFICIAL REVERSE 3D VIEW"}
              </span>
              <span className="px-2 py-0.5 rounded bg-emerald-400 text-slate-950 font-black">
                180° BACK
              </span>
            </div>

            <div className="my-auto py-2 px-3 rounded-xl bg-white/[0.04] border border-white/15 w-full">
              <div className="text-[10px] font-bold uppercase tracking-widest text-cyan-300">
                {scene === "private_jet_flex"
                  ? "14-SEAT LEATHER CABIN & TACTICAL LOUNGE"
                  : scene === "luxury_turntable"
                  ? "OPEN SAPPHIRE TOURBILLON · 28,800 VPH"
                  : scene === "facility_upgrade" || scene === "stadium_ad_display"
                  ? `4-ZONE REVENUE: ${adSurfaceZone}`
                  : `${surname} · OFFICIAL SQUAD REGISTRATION`}
              </div>
              <div
                className="text-3xl font-black tracking-tight text-white mt-0.5"
                style={{ textShadow: "0 4px 12px rgba(0,0,0,0.9)" }}
              >
                {scene === "private_jet_flex"
                  ? "TAIL #GTX-VIP"
                  : scene === "facility_upgrade" || scene === "academy_upgrade"
                  ? `LEVEL ${facilityLevel}/5`
                  : `#${jerseyNumber} ${surname}`}
              </div>
            </div>

            <div className="w-full py-1 px-2 rounded-lg bg-amber-400/15 border border-amber-400/40 text-[10px] font-black text-amber-300 truncate">
              Verified by {clubName} · {ownerName}
            </div>
          </div>

          {/* =====================================================================
              1. 3D SCULPTED FOOTBALL JERSEY (SIGNING / BUILD-A-SON / WONDERKID / SPONSOR)
             ===================================================================== */}
          {(scene === "signing_walkout" ||
            scene === "build_a_son" ||
            scene === "stadium_sponsor" ||
            scene === "wonderkid_emergence") && (
            <div
              className="relative"
              style={{ transformStyle: "preserve-3d", backfaceVisibility: "hidden" }}
            >
              {/* Main Contoured 3D Jersey Silhouette & Body (translateZ +15px) */}
              <div
                className="relative w-52 h-56 rounded-2xl p-4 border-2 flex flex-col items-center justify-between overflow-hidden"
                style={{
                  transform: "translateZ(15px)",
                  transformStyle: "preserve-3d",
                  backfaceVisibility: "hidden",
                  background:
                    scene === "wonderkid_emergence"
                      ? "linear-gradient(150deg, #F59E0B 0%, #0b1322 60%, #10B981 100%)"
                      : `linear-gradient(145deg, ${activePrimary} 0%, #0a1222 68%, ${activeSecondary} 100%)`,
                  borderColor: "#FDE047",
                  boxShadow: `0 22px 48px -8px ${activePrimary}77, inset 0 0 30px rgba(255,255,255,0.25)`,
                }}
              >
                {/* Dynamic Specular Light Sheen */}
                <div
                  className="absolute inset-0 pointer-events-none"
                  style={{
                    background: `radial-gradient(circle at ${specularX}% 25%, rgba(255,255,255,0.32), transparent 60%)`,
                  }}
                />

                {/* Sculpted SVG Football Kit Silhouette Overlay */}
                <svg
                  viewBox="0 0 200 200"
                  className="absolute inset-0 w-full h-full opacity-35 pointer-events-none"
                >
                  <path
                    d="M55,20 L80,28 Q100,42 120,28 L145,20 L185,55 L162,85 L145,70 L145,180 L55,180 L55,70 L38,85 L15,55 Z"
                    fill="none"
                    stroke="#FFFFFF"
                    strokeWidth="4"
                  />
                </svg>

                {/* Top Shoulder Collar & OVR Badge (Floating at translateZ +16px) */}
                <div
                  className="w-full flex items-center justify-between text-[10px] font-black uppercase tracking-wider text-white z-10"
                  style={{ transform: "translateZ(16px)" }}
                >
                  <span className="px-2 py-0.5 rounded-md bg-black/65 border border-white/20 shadow">
                    {clubName.slice(0, 12)}
                  </span>
                  <span className="px-2 py-0.5 rounded-md bg-amber-400 text-slate-950 font-black shadow">
                    OVR {overallRating}
                  </span>
                </div>

                {/* Floating 3D Metallic Squad Number & Player Surname (translateZ +28px) */}
                <div
                  className="text-center my-0.5 z-10"
                  style={{ transform: "translateZ(28px)" }}
                >
                  <div
                    className="text-xs font-black tracking-[0.24em] uppercase text-white"
                    style={{ textShadow: "0 4px 10px rgba(0,0,0,0.9)" }}
                  >
                    {surname}
                  </div>
                  <div
                    className="text-5xl font-black leading-none tracking-tighter mt-0.5"
                    style={{
                      color: "#FFFFFF",
                      textShadow:
                        "0 3px 0 #D97706, 0 6px 0 #78350F, 0 12px 24px rgba(0,0,0,0.85)",
                    }}
                  >
                    #{jerseyNumber}
                  </div>
                </div>

                {/* Raised 3D Chest Sponsor Plate (translateZ +20px) */}
                <div
                  className="w-full py-1.5 px-2.5 rounded-lg bg-slate-950/85 border border-amber-400/60 text-center z-10 shadow-lg"
                  style={{ transform: "translateZ(20px)" }}
                >
                  <div className="text-[9px] uppercase tracking-widest text-amber-300 font-black truncate">
                    {scene === "wonderkid_emergence" ? "⚡ GOLDEN FLARE WALKOUT" : sponsorName}
                  </div>
                </div>
              </div>

              {/* Orbiting Front 3D DNA / Potential Halo (translateZ +36px) */}
              {(potentialRating || scene === "wonderkid_emergence" || scene === "build_a_son") && (
                <div
                  className="mt-2.5 px-3.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider text-center shadow-xl"
                  style={{
                    transform: "translateZ(36px)",
                    background: "linear-gradient(90deg, #064E3B, #047857)",
                    color: "#A7F3D0",
                    border: "1px solid #34D399",
                    boxShadow: "0 8px 20px rgba(0, 230, 118, 0.4)",
                  }}
                >
                  3D DNA Ceiling: {potentialRating || 95} POT
                </div>
              )}
            </div>
          )}

          {/* =====================================================================
              2. 3D SWEPT-WING EXECUTIVE JET ON LIT NIGHT RUNWAY & LUXURY VAULT
             ===================================================================== */}
          {(scene === "private_jet_flex" || scene === "luxury_turntable") && (
            <div
              className="relative"
              style={{ transformStyle: "preserve-3d", backfaceVisibility: "hidden" }}
            >
              <div
                className="w-68 h-52 rounded-2xl flex flex-col items-center justify-between p-4 border-2 relative overflow-hidden"
                style={{
                  transform: "translateZ(15px)",
                  transformStyle: "preserve-3d",
                  backfaceVisibility: "hidden",
                  background:
                    "radial-gradient(circle at 35% 25%, rgba(245,184,61,0.38), rgba(15,12,28,0.96) 72%)",
                  borderColor: "#FDE047",
                  boxShadow: "0 24px 55px rgba(245, 184, 61, 0.35), inset 0 0 32px rgba(245, 184, 61, 0.22)",
                }}
              >
                <div
                  className="absolute inset-0 pointer-events-none"
                  style={{
                    background: `radial-gradient(circle at ${specularX}% 20%, rgba(255,255,255,0.28), transparent 55%)`,
                  }}
                />

                <div
                  className="w-full flex items-center justify-between text-[10px] font-black uppercase tracking-wider text-amber-300 z-10"
                  style={{ transform: "translateZ(18px)" }}
                >
                  <span>{scene === "private_jet_flex" ? "✈️ 3D VIP NIGHT TARMAC" : "💎 3D BESPOKE VAULT"}</span>
                  <span className="px-2 py-0.5 rounded bg-amber-400 text-slate-950 font-black">
                    1 OF 10 MINTED
                  </span>
                </div>

                {/* 3D Sculpted Swept-Wing Jet or Multi-Gear Tourbillon (translateZ +32px) */}
                <div
                  className="relative flex items-center justify-center my-1"
                  style={{ transform: "translateZ(32px)" }}
                >
                  {scene === "private_jet_flex" || assetCategory === "jet" ? (
                    <div className="relative flex items-center justify-center">
                      <svg viewBox="0 0 220 90" className="w-48 h-24 drop-shadow-[0_10px_20px_rgba(245,184,61,0.6)]">
                        <defs>
                          <linearGradient id="fuselageGrad" x1="0" y1="0" x2="1" y2="1">
                            <stop offset="0%" stopColor="#FEF08A" />
                            <stop offset="50%" stopColor="#F59E0B" />
                            <stop offset="100%" stopColor="#78350F" />
                          </linearGradient>
                        </defs>
                        <polygon points="90,45 45,85 70,85 125,45" fill="url(#fuselageGrad)" />
                        <polygon points="90,45 55,8 78,8 125,45" fill="#FDE047" opacity="0.85" />
                        <polygon points="22,42 8,14 32,14 48,42" fill={activePrimary} stroke="#FDE047" strokeWidth="2" />
                        <path d="M18,45 Q110,30 205,45 Q110,58 18,45 Z" fill="#FFFFFF" stroke="#F59E0B" strokeWidth="2.5" />
                        <path d="M168,41 L188,44 L168,46 Z" fill="#0284C7" />
                      </svg>
                    </div>
                  ) : (
                    <div className="w-24 h-24 rounded-full flex items-center justify-center border-4 border-amber-300 bg-gradient-to-br from-amber-400/40 via-slate-900 to-amber-900/60 shadow-[0_0_35px_rgba(245,184,61,0.65)]">
                      <Sparkles size={42} className="text-amber-200" />
                    </div>
                  )}
                </div>

                <div
                  className="text-center z-10 w-full bg-black/65 rounded-lg py-1.5 px-2 border border-white/15"
                  style={{ transform: "translateZ(22px)" }}
                >
                  <div className="text-xs font-black text-white truncate">{subjectName}</div>
                  <div className="text-[10px] text-emerald-400 font-bold uppercase truncate">
                    Livery: {clubName} ({ownerName})
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* =====================================================================
              3. 3D STACKED-RING STADIUM CATHEDRAL & YOUTH CAMPUS CUTAWAY
             ===================================================================== */}
          {(scene === "facility_upgrade" ||
            scene === "academy_upgrade" ||
            scene === "stadium_ad_display") && (
            <div
              className="relative"
              style={{ transformStyle: "preserve-3d", backfaceVisibility: "hidden" }}
            >
              <div
                className="w-72 h-52 rounded-2xl p-4 border-2 flex flex-col items-center justify-between text-center relative overflow-hidden"
                style={{
                  transform: "translateZ(15px)",
                  transformStyle: "preserve-3d",
                  backfaceVisibility: "hidden",
                  background:
                    "linear-gradient(155deg, rgba(8, 47, 73, 0.95), rgba(4, 12, 26, 0.98))",
                  borderColor: scene === "stadium_ad_display" ? "#F5B83D" : "#38BDF8",
                  boxShadow: "0 24px 55px rgba(56, 189, 248, 0.32), inset 0 0 28px rgba(56, 189, 248, 0.2)",
                }}
              >
                <div
                  className="w-full flex items-center justify-between text-[10px] font-black uppercase text-cyan-300 z-10"
                  style={{ transform: "translateZ(18px)" }}
                >
                  <span>
                    {scene === "academy_upgrade"
                      ? "🌱 3D LA MASIA YOUTH CAMPUS"
                      : scene === "stadium_ad_display"
                      ? "📺 3D 4-ZONE STADIUM AD BOWL"
                      : "🏟️ 3D STADIUM CATHEDRAL"}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-amber-400 text-slate-950 font-black">
                    TIER L{facilityLevel}/5
                  </span>
                </div>

                {/* Multi-Tier 3D Isometric Stadium Bowl */}
                <div
                  className="relative w-52 h-28 flex items-center justify-center my-1"
                  style={{
                    transformStyle: "preserve-3d",
                    transform: "rotateX(48deg) translateZ(16px)",
                  }}
                >
                  <div
                    className="absolute inset-0 rounded-full border-4 border-cyan-300/80 shadow-[0_0_25px_rgba(56,189,248,0.5)]"
                    style={{ transform: "translateZ(26px)" }}
                  />
                  <div
                    className="absolute inset-2 rounded-full border-4 border-amber-400/90 bg-slate-900/90"
                    style={{ transform: "translateZ(14px)" }}
                  />
                  <div
                    className="relative w-36 h-16 rounded-full border-2 border-emerald-300 bg-emerald-600 flex items-center justify-center shadow-inner"
                    style={{ transform: "translateZ(4px)" }}
                  >
                    <div className="w-28 h-11 border border-white/75 rounded-sm flex items-center justify-center">
                      <div className="w-6 h-6 rounded-full border border-white/80" />
                    </div>
                  </div>
                </div>

                <div
                  className="w-full py-1.5 px-2.5 rounded-lg bg-black/75 border border-cyan-400/40 text-[10px] font-black text-amber-300 truncate z-10"
                  style={{ transform: "translateZ(24px)" }}
                >
                  {scene === "stadium_ad_display"
                    ? `${adSurfaceZone} · ${sponsorName}`
                    : subjectName}
                </div>
              </div>
            </div>
          )}

          {/* =====================================================================
              4. 3D VOLUMETRIC GOLDEN GLOBE TROPHY & FINALS PLINTH
             ===================================================================== */}
          {(scene === "world_gala" || scene === "competition_final") && (
            <div
              className="relative flex flex-col items-center"
              style={{ transformStyle: "preserve-3d", backfaceVisibility: "hidden" }}
            >
              <div
                className="w-36 h-36 rounded-full flex flex-col items-center justify-center border-4 relative"
                style={{
                  transform: "translateZ(22px)",
                  borderColor: "#FEF08A",
                  background: `radial-gradient(circle at ${specularX}% 28%, #FFFFFF 0%, #FEF08A 22%, #F59E0B 58%, #78350F 100%)`,
                  boxShadow: "0 18px 50px rgba(245, 184, 61, 0.8), inset 0 -12px 28px rgba(0,0,0,0.55)",
                }}
              >
                {scene === "competition_final" ? (
                  <Trophy size={48} className="text-amber-950 drop-shadow" />
                ) : (
                  <Award size={48} className="text-amber-950 drop-shadow" />
                )}
                <span className="text-[10px] font-black uppercase tracking-widest text-amber-950 mt-0.5">
                  {scene === "competition_final" ? "FINAL PLINTH" : "GTEX D'OR"}
                </span>
              </div>
              <div
                className="w-44 h-14 -mt-2 rounded-xl border-2 flex flex-col items-center justify-center px-3 shadow-2xl"
                style={{
                  transform: "translateZ(30px)",
                  background: "linear-gradient(180deg, #1E293B, #020617)",
                  borderColor: "#FDE047",
                }}
              >
                <span className="text-xs font-black text-amber-300 truncate max-w-[155px]">
                  {subjectName}
                </span>
                <span className="text-[9px] font-bold uppercase text-white/80 truncate max-w-[155px]">
                  {clubName}
                </span>
              </div>
            </div>
          )}

          {/* =====================================================================
              5. 3D KEYS TO THE CLUB TAKEOVER CHARTER & CROWN VAULT
             ===================================================================== */}
          {scene === "club_takeover" && (
            <div
              className="w-68 h-50 rounded-2xl p-4 border-2 flex flex-col items-center justify-between text-center relative"
              style={{
                transform: "translateZ(15px)",
                transformStyle: "preserve-3d",
                backfaceVisibility: "hidden",
                background:
                  "radial-gradient(circle at 50% 20%, rgba(245,184,61,0.4), rgba(8,14,28,0.97) 75%)",
                borderColor: "#FDE047",
                boxShadow: "0 24px 55px rgba(245, 184, 61, 0.4)",
              }}
            >
              <div
                className="text-[10px] font-black uppercase tracking-widest text-amber-300"
                style={{ transform: "translateZ(18px)" }}
              >
                👑 OFFICIAL 3D CLUB CHARTER & DEEDS
              </div>
              <div
                className="w-20 h-20 rounded-2xl border-2 border-amber-300 bg-amber-400/20 flex items-center justify-center shadow-[0_0_35px_rgba(245,184,61,0.6)]"
                style={{ transform: "translateZ(32px)" }}
              >
                <Crown size={42} className="text-amber-200" />
              </div>
              <div style={{ transform: "translateZ(22px)" }}>
                <div className="text-base font-black uppercase text-white">{clubName}</div>
                <div className="text-[10px] font-bold text-emerald-400 uppercase">
                  Keys Presented to {ownerName}
                </div>
              </div>
            </div>
          )}

          {/* =====================================================================
              6. 3D EXECUTIVE WAR ROOM, MANAGER DAY 1 & SKY-STUDIO BROADCAST DESK
             ===================================================================== */}
          {(scene === "club_announcement" ||
            scene === "new_ad_deal" ||
            scene === "negotiation_table" ||
            scene === "manager_arrival" ||
            scene === "boardroom_clash") && (
            <div
              className="relative"
              style={{ transformStyle: "preserve-3d", backfaceVisibility: "hidden" }}
            >
              <div
                className="w-72 h-48 rounded-2xl p-4 border-2 flex flex-col justify-between relative"
                style={{
                  transform: "translateZ(15px)",
                  transformStyle: "preserve-3d",
                  backfaceVisibility: "hidden",
                  background:
                    "linear-gradient(160deg, rgba(16, 28, 48, 0.96), rgba(7, 12, 24, 0.98))",
                  borderColor:
                    scene === "club_announcement" || scene === "new_ad_deal"
                      ? "#FDE047"
                      : agentMood === "hostile"
                      ? "rgba(239, 68, 68, 0.85)"
                      : agentMood === "tense"
                      ? "rgba(245, 184, 61, 0.85)"
                      : "rgba(0, 230, 118, 0.8)",
                  boxShadow: "0 24px 55px rgba(0,0,0,0.8)",
                }}
              >
                <div
                  className="flex items-center justify-between border-b border-white/10 pb-2"
                  style={{ transform: "translateZ(18px)" }}
                >
                  <div className="flex items-center gap-1.5">
                    {scene === "club_announcement" ? (
                      <Radio size={14} className="text-rose-400 animate-pulse" />
                    ) : scene === "new_ad_deal" ? (
                      <Tv size={14} className="text-amber-400" />
                    ) : (
                      <Shield size={14} className="text-amber-400" />
                    )}
                    <span className="text-[10px] font-black uppercase tracking-wider text-white">
                      {scene === "club_announcement"
                        ? "3D SKY-STUDIO COMMUNIQUÉ"
                        : scene === "new_ad_deal"
                        ? "3D COMMERCIAL DEAL UNVEIL"
                        : `${clubName} 3D SUITE`}
                    </span>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-amber-400 text-slate-950 text-[9px] font-black uppercase">
                    {scene === "club_announcement"
                      ? "LIVE WIRE"
                      : scene === "new_ad_deal"
                      ? sponsorName.slice(0, 14)
                      : scene === "manager_arrival"
                      ? "DAY 1 MANDATE"
                      : `AGENT: ${agentMood.toUpperCase()}`}
                  </span>
                </div>

                <div
                  className="my-auto text-center py-2 px-3 rounded-xl bg-white/[0.04] border border-white/10"
                  style={{ transform: "translateZ(30px)" }}
                >
                  <div className="text-sm font-black text-white uppercase truncate">{subjectName}</div>
                  <div className="text-[11px] text-cyan-300 font-semibold mt-0.5 truncate">{subjectRole}</div>
                </div>

                <div
                  className="w-full py-1.5 px-2.5 rounded-lg text-[10px] font-black text-center"
                  style={{
                    transform: "translateZ(20px)",
                    background: "rgba(245, 184, 61, 0.16)",
                    border: "1px solid rgba(245, 184, 61, 0.45)",
                    color: "#FDE047",
                  }}
                >
                  {scene === "club_announcement"
                    ? `Official Boardroom Statement · ${clubName}`
                    : scene === "new_ad_deal"
                    ? `Signed Commercial Partnership · ${sponsorName}`
                    : scene === "manager_arrival"
                    ? "Official Press & Training Ground Presentation"
                    : "Interactive 3D Contract & Release-Clause Table"}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Camera & Face Orientation HUD Pill */}
        <div className="absolute top-3 left-4 z-20 pointer-events-none flex flex-wrap items-center gap-1.5">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/75 border border-white/15 text-[10px] text-white/90 font-semibold">
            <Layers size={11} className="text-amber-400" />
            <span>
              {directorShotLabel || `360° Volumetric Rig · ${Math.round(normAngle)}°`}
            </span>
          </div>
          <span
            className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase"
            style={{
              background: isShowingBackFace ? "rgba(56,189,248,0.22)" : "rgba(0,230,118,0.2)",
              color: isShowingBackFace ? "#38BDF8" : "#00E676",
              border: `1px solid ${isShowingBackFace ? "#38BDF8" : "#00E676"}`,
            }}
          >
            {isShowingBackFace ? "180° BACK FACE" : "FRONT FACE"}
          </span>
        </div>
      </div>

      {/* Broadcast Lower-Third Banner */}
      <div
        className="relative z-20 px-4 py-3 border-t flex flex-col md:flex-row md:items-center md:justify-between gap-3"
        style={{
          background:
            "linear-gradient(90deg, rgba(6, 10, 20, 0.98) 0%, rgba(15, 23, 42, 0.96) 60%, rgba(10, 16, 30, 0.98) 100%)",
          borderColor: "rgba(245, 184, 61, 0.35)",
        }}
      >
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <h4 className="text-sm font-black uppercase tracking-wide text-white truncate">
              {title}
            </h4>
          </div>
          {subtitle && (
            <p className="text-xs text-white/75 mt-0.5 truncate">{subtitle}</p>
          )}
          {quote && (
            <p className="text-xs italic text-amber-300/95 mt-1 line-clamp-2">
              &ldquo;{quote}&rdquo;
            </p>
          )}
        </div>

        {/* Dynamic Telemetry Pills */}
        {stats.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            {stats.map((st, idx) => (
              <div
                key={idx}
                className="px-2.5 py-1 rounded-lg bg-black/50 border border-white/10 text-right"
              >
                <div className="text-[9px] uppercase tracking-wider text-white/55 font-bold">
                  {st.label}
                </div>
                <div
                  className="text-xs font-black"
                  style={{ color: st.accent || "#00E676" }}
                >
                  {st.value}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Social Flex Salute Button for Other Users on the App */}
        {(enableSocialSalute || scene === "private_jet_flex" || scene === "club_announcement") && (
          <button
            type="button"
            onClick={() => {
              if (!hasSaluted) {
                setSaluteCount((c) => c + 1);
                setHasSaluted(true);
                triggerPyroBurst();
              }
            }}
            className={`px-3 py-1.5 rounded-lg text-xs font-black uppercase tracking-wider transition-all flex items-center gap-1.5 shrink-0 border ${
              hasSaluted
                ? "bg-amber-400/20 border-amber-400 text-amber-300"
                : "bg-white/5 border-white/15 text-white hover:border-amber-400/50"
            }`}
            data-testid="social-salute-flex-btn"
          >
            <ThumbsUp size={13} className="text-amber-400" />
            <span>{hasSaluted ? "Saluted" : "Salute Flex"} ({saluteCount})</span>
          </button>
        )}

        {onActionClick && actionLabel && (
          <button
            type="button"
            onClick={onActionClick}
            className="px-3.5 py-2 rounded-lg text-xs font-black uppercase tracking-wider transition-all shrink-0"
            style={{
              background: "linear-gradient(135deg, #F5B83D, #D97706)",
              color: "#050811",
              boxShadow: "0 6px 20px rgba(245, 184, 61, 0.35)",
            }}
          >
            {actionLabel}
          </button>
        )}
      </div>
    </div>
  );
};
