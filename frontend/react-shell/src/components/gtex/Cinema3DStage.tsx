import React, { useEffect, useRef, useState } from "react";
import {
  Camera,
  Film,
  Maximize2,
  RotateCcw,
  Sparkles,
  Volume2,
  VolumeX,
  Eye,
  Play,
  Pause,
  Shield,
  Award,
  Layers,
} from "lucide-react";

export type Cinema3DSceneType =
  | "signing_walkout"
  | "negotiation_table"
  | "luxury_turntable"
  | "world_gala"
  | "build_a_son"
  | "manager_arrival"
  | "stadium_sponsor"
  | "boardroom_clash";

export type Cinema3DMode = "motion_3d" | "fm_diorama";

export interface Cinema3DStageProps {
  scene: Cinema3DSceneType;
  title: string;
  subtitle?: string;
  badgeText?: string;
  clubName?: string;
  primaryColor?: string;
  secondaryColor?: string;
  subjectName?: string;
  subjectRole?: string;
  jerseyNumber?: number | string;
  overallRating?: number | string;
  potentialRating?: number | string;
  sponsorName?: string;
  spectacleTier?: "standard_press" | "floodlight_walkout" | "galactico_helicopter";
  assetCategory?: "watch" | "jet" | "car" | "facility" | "trophy" | string;
  quote?: string;
  stats?: Array<{ label: string; value: string; accent?: string }>;
  videoUrl?: string;
  defaultMode?: Cinema3DMode;
  compact?: boolean;
  agentMood?: "calm" | "tense" | "eager" | "hostile";
  onActionClick?: () => void;
  actionLabel?: string;
}

/**
 * GTEX 3D Presentation & Diorama Engine
 * Combines:
 *  1. FIFA / eFootball-style 3D Motion Cinema (60fps Canvas 3D volumetric lights, flashbulbs,
 *     confetti, and interactive 360-degree 3D centerpiece rotation).
 *  2. Football Manager-style 3D Static Diorama Stills (multi-plane architectural depth parallax
 *     with broadcast lower-thirds and press/boardroom framing).
 */
export const Cinema3DStage: React.FC<Cinema3DStageProps> = ({
  scene,
  title,
  subtitle,
  badgeText,
  clubName = "GTEX FC",
  primaryColor = "#00E676",
  secondaryColor = "#F5B83D",
  subjectName = "MARQUEE STAR",
  subjectRole = "First-Team Signing",
  jerseyNumber = 9,
  overallRating = 88,
  potentialRating,
  sponsorName = "GTEX GLOBAL AIRWAYS",
  spectacleTier = "floodlight_walkout",
  assetCategory = "watch",
  quote,
  stats = [],
  videoUrl,
  defaultMode = "motion_3d",
  compact = false,
  agentMood = "eager",
  onActionClick,
  actionLabel,
}) => {
  const [mode, setMode] = useState<Cinema3DMode>(defaultMode);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [soundEnabled, setSoundEnabled] = useState<boolean>(false);
  const [rotY, setRotY] = useState<number>(0);
  const [rotX, setRotX] = useState<number>(6);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [cameraAngle, setCameraAngle] = useState<"wide" | "hero" | "closeup">("hero");
  const dragStartRef = useRef<{ x: number; y: number; rotY: number; rotX: number }>({
    x: 0,
    y: 0,
    rotY: 0,
    rotX: 6,
  });
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Auto-rotation in Motion 3D mode when not dragging
  useEffect(() => {
    if (mode !== "motion_3d" || !isPlaying || isDragging) return;
    let rafId: number;
    let lastTime = performance.now();
    const animate = (now: number) => {
      const dt = (now - lastTime) / 1000;
      lastTime = now;
      setRotY((prev) => (prev + dt * 28) % 360);
      rafId = requestAnimationFrame(animate);
    };
    rafId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafId);
  }, [mode, isPlaying, isDragging]);

  // 60fps Volumetric Stadium Lighting, Paparazzi Flashbulbs & Gold Confetti Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let tick = 0;

    const particles = Array.from({ length: compact ? 28 : 55 }, (_, i) => ({
      x: (i * 73) % 800,
      y: (i * 47) % 420,
      z: 0.25 + ((i * 19) % 75) / 100,
      vx: (((i * 13) % 10) - 5) * 0.25,
      vy: scene === "world_gala" || scene === "signing_walkout" ? 0.55 + ((i % 5) * 0.2) : -0.35,
      size: 2 + (i % 4),
      gold: i % 2 === 0,
    }));

    const flashes = Array.from({ length: 6 }, (_, i) => ({
      x: 100 + i * 115,
      y: 70 + (i % 3) * 45,
      phase: i * 1.1,
    }));

    const render = () => {
      if (mode === "motion_3d" && isPlaying) {
        tick += 0.025;
      }
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      // 1. Deep 3D Studio / Stadium Horizon Gradient
      const bgGrad = ctx.createRadialGradient(w * 0.5, h * 0.32, 10, w * 0.5, h * 0.5, w * 0.75);
      if (scene === "world_gala") {
        bgGrad.addColorStop(0, "rgba(65, 45, 10, 0.92)");
        bgGrad.addColorStop(0.55, "rgba(16, 14, 24, 0.96)");
        bgGrad.addColorStop(1, "rgba(5, 6, 12, 1)");
      } else if (scene === "luxury_turntable") {
        bgGrad.addColorStop(0, "rgba(38, 28, 52, 0.92)");
        bgGrad.addColorStop(0.6, "rgba(12, 14, 22, 0.97)");
        bgGrad.addColorStop(1, "rgba(4, 6, 10, 1)");
      } else if (scene === "negotiation_table" || scene === "boardroom_clash") {
        bgGrad.addColorStop(0, "rgba(20, 38, 55, 0.92)");
        bgGrad.addColorStop(0.6, "rgba(10, 16, 28, 0.97)");
        bgGrad.addColorStop(1, "rgba(4, 8, 16, 1)");
      } else {
        bgGrad.addColorStop(0, "rgba(12, 52, 38, 0.9)");
        bgGrad.addColorStop(0.55, "rgba(9, 19, 32, 0.96)");
        bgGrad.addColorStop(1, "rgba(4, 8, 15, 1)");
      }
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, w, h);

      // 2. 3D Perspective Floor Grid (FM / FIFA Studio Floor)
      const horizonY = h * 0.64;
      ctx.save();
      ctx.strokeStyle =
        scene === "world_gala"
          ? "rgba(245, 184, 61, 0.16)"
          : "rgba(0, 230, 118, 0.14)";
      ctx.lineWidth = 1;

      // Perspective radial lines from vanishing point
      const vpX = w * 0.5 + Math.sin(tick * 0.6) * (mode === "motion_3d" ? 18 : 0);
      for (let i = -8; i <= 8; i++) {
        ctx.beginPath();
        ctx.moveTo(vpX, horizonY);
        ctx.lineTo(vpX + i * 95, h);
        ctx.stroke();
      }
      // Horizontal depth planes
      for (let r = 1; r <= 6; r++) {
        const py = horizonY + Math.pow(r / 6, 1.7) * (h - horizonY);
        ctx.beginPath();
        ctx.moveTo(0, py);
        ctx.lineTo(w, py);
        ctx.stroke();
      }
      ctx.restore();

      // 3. Volumetric 3D Floodlight Cones
      const beamCount = spectacleTier === "galactico_helicopter" ? 4 : 3;
      for (let b = 0; b < beamCount; b++) {
        const bx = (w / (beamCount + 1)) * (b + 1);
        const sway = mode === "motion_3d" ? Math.sin(tick * 1.1 + b * 1.4) * 45 : 0;
        const beamGrad = ctx.createLinearGradient(bx, 0, bx + sway, h * 0.85);
        const beamColor =
          b % 2 === 0
            ? "rgba(245, 184, 61, 0.16)"
            : "rgba(0, 230, 118, 0.13)";
        beamGrad.addColorStop(0, beamColor);
        beamGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

        ctx.save();
        ctx.fillStyle = beamGrad;
        ctx.beginPath();
        ctx.moveTo(bx - 16, 0);
        ctx.lineTo(bx + 16, 0);
        ctx.lineTo(bx + sway + 130, h * 0.88);
        ctx.lineTo(bx + sway - 130, h * 0.88);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
      }

      // 4. Paparazzi Camera Flashbulbs (for Signings, Gala, Manager Arrival)
      if (
        scene === "signing_walkout" ||
        scene === "world_gala" ||
        scene === "manager_arrival" ||
        scene === "build_a_son"
      ) {
        flashes.forEach((f) => {
          const pulse = Math.max(0, Math.sin(tick * 3.8 + f.phase));
          if (pulse > 0.82) {
            const radius = (pulse - 0.82) * 190;
            const fg = ctx.createRadialGradient(f.x, f.y, 1, f.x, f.y, radius);
            fg.addColorStop(0, "rgba(255, 255, 255, 0.9)");
            fg.addColorStop(0.3, "rgba(245, 184, 61, 0.35)");
            fg.addColorStop(1, "rgba(255, 255, 255, 0)");
            ctx.fillStyle = fg;
            ctx.beginPath();
            ctx.arc(f.x, f.y, radius, 0, Math.PI * 2);
            ctx.fill();
          }
        });
      }

      // 5. Floating 3D Depth Particles / Gold Gala Confetti
      particles.forEach((p) => {
        if (mode === "motion_3d" && isPlaying) {
          p.x = (p.x + p.vx + w) % w;
          p.y = (p.y + p.vy + h) % h;
        }
        ctx.save();
        ctx.fillStyle = p.gold
          ? `rgba(245, 184, 61, ${0.35 + p.z * 0.5})`
          : `rgba(56, 189, 248, ${0.25 + p.z * 0.45})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * p.z, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      });

      if (mode === "motion_3d" && isPlaying) {
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

  const cameraScale = cameraAngle === "closeup" ? 1.18 : cameraAngle === "wide" ? 0.88 : 1.0;

  return (
    <div
      className="relative overflow-hidden rounded-xl border transition-all select-none"
      style={{
        borderColor:
          scene === "world_gala" || spectacleTier === "galactico_helicopter"
            ? "rgba(245, 184, 61, 0.55)"
            : "rgba(0, 230, 118, 0.35)",
        background: "#050811",
        boxShadow: "0 20px 50px rgba(0, 0, 0, 0.65)",
      }}
    >
      {/* Top Broadcast Control Bar */}
      <div
        className="relative z-20 flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 border-b"
        style={{
          background: "linear-gradient(90deg, rgba(10,15,28,0.95), rgba(18,25,43,0.92))",
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
                background: "rgba(245, 184, 61, 0.15)",
                color: "var(--gtex-gold)",
                border: "1px solid rgba(245, 184, 61, 0.35)",
              }}
            >
              {badgeText}
            </span>
          )}
        </div>

        {/* Mode & Camera Switcher */}
        <div className="flex items-center gap-1.5">
          <div className="inline-flex rounded-lg p-0.5 bg-black/50 border border-white/10">
            <button
              type="button"
              onClick={() => setMode("motion_3d")}
              className="px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all flex items-center gap-1"
              style={{
                background: mode === "motion_3d" ? "rgba(0, 230, 118, 0.22)" : "transparent",
                color: mode === "motion_3d" ? "#00E676" : "var(--gtex-text-muted)",
              }}
            >
              <Film size={11} /> 3D Video / Motion
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("fm_diorama");
                setRotY(-14);
                setRotX(5);
              }}
              className="px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all flex items-center gap-1"
              style={{
                background: mode === "fm_diorama" ? "rgba(56, 189, 248, 0.22)" : "transparent",
                color: mode === "fm_diorama" ? "#38BDF8" : "var(--gtex-text-muted)",
              }}
            >
              <Camera size={11} /> FM 3D Still
            </button>
          </div>

          <div className="hidden sm:inline-flex rounded-lg p-0.5 bg-black/50 border border-white/10">
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
              setRotY(0);
              setRotX(6);
              setCameraAngle("hero");
            }}
            title="Reset 3D Camera"
            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/80"
          >
            <RotateCcw size={13} />
          </button>
          <button
            type="button"
            onClick={() => setSoundEnabled((s) => !s)}
            title="Toggle Crowd & Shutter Audio FX"
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
          compact ? "h-[270px]" : "h-[360px]"
        } flex items-center justify-center cursor-grab active:cursor-grabbing overflow-hidden`}
        style={{ perspective: "1100px" }}
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

        {/* FM-Style Architectural Press / Stadium Backdrop Wall */}
        <div
          className="absolute inset-x-10 top-6 bottom-16 rounded-2xl pointer-events-none transition-transform duration-300"
          style={{
            transform: `translateZ(-120px) rotateX(${rotX * 0.25}deg) rotateY(${rotY * 0.12}deg) scale(${cameraScale})`,
            border: "1px solid rgba(255,255,255,0.07)",
            background:
              "radial-gradient(circle at 50% 25%, rgba(255,255,255,0.05), rgba(0,0,0,0.45))",
          }}
        >
          {/* Step-and-Repeat Sponsor Wall Pattern */}
          <div className="grid grid-cols-4 gap-3 p-4 opacity-25 text-[10px] font-black tracking-widest uppercase text-center text-white">
            {Array.from({ length: 12 }).map((_, idx) => (
              <div key={idx} className="border border-white/15 rounded py-1 px-2 truncate">
                { idx % 2 === 0 ? clubName : sponsorName }
              </div>
            ))}
          </div>
        </div>

        {/* 3D Pedestal / Turntable Ring */}
        <div
          className="absolute bottom-8 w-72 h-20 rounded-full pointer-events-none"
          style={{
            transform: `rotateX(74deg) rotateZ(${rotY}deg) scale(${cameraScale})`,
            background:
              "radial-gradient(circle, rgba(245,184,61,0.35) 0%, rgba(0,230,118,0.18) 55%, transparent 75%)",
            border: "2px solid rgba(245, 184, 61, 0.55)",
            boxShadow: "0 0 35px rgba(245, 184, 61, 0.35)",
          }}
        />

        {/* Interactive 3D Centerpiece Object */}
        <div
          className="relative z-10 transition-transform duration-75"
          style={{
            transformStyle: "preserve-3d",
            transform: `scale(${cameraScale}) rotateX(${rotX}deg) rotateY(${rotY}deg)`,
          }}
        >
          {/* SCENE A: 3D KIT / SIGNING WALKOUT / BUILD-A-SON / STADIUM SPONSOR */}
          {(scene === "signing_walkout" ||
            scene === "build_a_son" ||
            scene === "stadium_sponsor") && (
            <div className="relative flex flex-col items-center">
              {/* 3D Sculpted Club Jersey Card */}
              <div
                className="relative w-44 h-52 rounded-2xl flex flex-col items-center justify-between p-4 border-2"
                style={{
                  background: `linear-gradient(145deg, ${primaryColor}, #0b1322 75%, ${secondaryColor})`,
                  borderColor: "rgba(245, 184, 61, 0.75)",
                  boxShadow: `0 18px 40px -10px ${primaryColor}66, inset 0 0 24px rgba(255,255,255,0.22)`,
                }}
              >
                {/* Jersey Shoulders & Collar */}
                <div className="w-full flex items-center justify-between text-[10px] font-extrabold uppercase tracking-wider text-white/90">
                  <span className="px-1.5 py-0.5 rounded bg-black/40 border border-white/15">
                    {clubName.slice(0, 12)}
                  </span>
                  <span className="px-1.5 py-0.5 rounded bg-amber-400/20 text-amber-300 border border-amber-400/40">
                    OVR {overallRating}
                  </span>
                </div>

                {/* Big 3D Metallic Squad Number & Player Back Print */}
                <div className="text-center my-1">
                  <div className="text-[11px] font-black tracking-[0.2em] uppercase text-white drop-shadow">
                    {subjectName.split(" ").slice(-1)[0]}
                  </div>
                  <div
                    className="text-5xl font-black leading-none tracking-tighter"
                    style={{
                      color: "#FFFFFF",
                      textShadow: "0 4px 14px rgba(0,0,0,0.7), 0 0 20px rgba(245,184,61,0.55)",
                    }}
                  >
                    #{jerseyNumber}
                  </div>
                </div>

                {/* Front/Chest Sponsor Strip */}
                <div className="w-full py-1 px-2 rounded bg-black/55 border border-white/15 text-center">
                  <div className="text-[8px] uppercase tracking-widest text-amber-300 font-bold truncate">
                    {sponsorName}
                  </div>
                </div>
              </div>

              {/* Potential / Bloodline Floating Halo */}
              {potentialRating && (
                <div
                  className="mt-2 px-3 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider"
                  style={{
                    background: "rgba(0, 230, 118, 0.2)",
                    color: "#00E676",
                    border: "1px solid rgba(0, 230, 118, 0.5)",
                  }}
                >
                  3D DNA Ceiling: {potentialRating} POT
                </div>
              )}
            </div>
          )}

          {/* SCENE B: 3D LUXURY SHOWROOM TURNTABLE & UNBOXING VAULT */}
          {scene === "luxury_turntable" && (
            <div className="relative flex flex-col items-center">
              <div
                className="w-48 h-48 rounded-2xl flex flex-col items-center justify-center p-5 border-2 relative"
                style={{
                  background:
                    "radial-gradient(circle at 30% 25%, rgba(245,184,61,0.32), rgba(20,16,34,0.95) 70%)",
                  borderColor: "rgba(245, 184, 61, 0.8)",
                  boxShadow: "0 20px 45px rgba(245, 184, 61, 0.28), inset 0 0 30px rgba(245, 184, 61, 0.18)",
                }}
              >
                <div className="text-[10px] font-black uppercase tracking-widest text-amber-300 mb-2">
                  3D BESPOKE VAULT
                </div>
                <div
                  className="w-20 h-20 rounded-full flex items-center justify-center border-2 mb-2"
                  style={{
                    borderColor: "#F5B83D",
                    background: "linear-gradient(135deg, rgba(245,184,61,0.35), rgba(0,0,0,0.7))",
                    boxShadow: "0 0 25px rgba(245,184,61,0.45)",
                  }}
                >
                  <Sparkles size={36} className="text-amber-300" />
                </div>
                <div className="text-sm font-black text-white text-center leading-tight">
                  {subjectName}
                </div>
                <div className="text-[10px] text-emerald-400 font-bold uppercase mt-1">
                  {assetCategory.toUpperCase()} · 360° 3D SPECIMEN
                </div>
              </div>
            </div>
          )}

          {/* SCENE C: 3D GTEX WORLD PLAYER OF THE YEAR GALA (BALLON D'OR TROPHY) */}
          {scene === "world_gala" && (
            <div className="relative flex flex-col items-center">
              {/* 3D Golden Globe Trophy */}
              <div
                className="w-36 h-36 rounded-full flex flex-col items-center justify-center border-4 relative"
                style={{
                  borderColor: "#FDE047",
                  background:
                    "radial-gradient(circle at 35% 30%, #FEF08A, #F59E0B 55%, #78350F 100%)",
                  boxShadow: "0 0 50px rgba(245, 184, 61, 0.75), inset 0 -10px 25px rgba(0,0,0,0.45)",
                }}
              >
                <Award size={48} className="text-amber-950 drop-shadow" />
                <span className="text-[9px] font-black uppercase tracking-widest text-amber-950 mt-0.5">
                  GTEX D&apos;OR
                </span>
              </div>
              {/* Onyx Pedestal Base */}
              <div
                className="w-28 h-12 -mt-2 rounded-b-xl border-2 flex flex-col items-center justify-center"
                style={{
                  background: "linear-gradient(180deg, #1E293B, #020617)",
                  borderColor: "#F5B83D",
                }}
              >
                <span className="text-[10px] font-black text-amber-300 truncate max-w-[96px]">
                  {subjectName}
                </span>
                <span className="text-[8px] uppercase text-white/70">{clubName}</span>
              </div>
            </div>
          )}

          {/* SCENE D: 3D TRANSFER / CONTRACT NEGOTIATION TABLE & BOARDROOM CLASH */}
          {(scene === "negotiation_table" ||
            scene === "manager_arrival" ||
            scene === "boardroom_clash") && (
            <div className="relative flex flex-col items-center">
              <div
                className="w-64 h-44 rounded-2xl p-4 border-2 flex flex-col justify-between"
                style={{
                  background:
                    "linear-gradient(160deg, rgba(16, 28, 48, 0.96), rgba(7, 12, 24, 0.98))",
                  borderColor:
                    agentMood === "hostile"
                      ? "rgba(239, 68, 68, 0.75)"
                      : agentMood === "tense"
                      ? "rgba(245, 184, 61, 0.75)"
                      : "rgba(0, 230, 118, 0.7)",
                  boxShadow: "0 20px 45px rgba(0,0,0,0.75)",
                }}
              >
                <div className="flex items-center justify-between border-b border-white/10 pb-2">
                  <div className="flex items-center gap-1.5">
                    <Shield size={14} className="text-amber-400" />
                    <span className="text-[10px] font-black uppercase tracking-wider text-white">
                      {clubName} 3D SUITE
                    </span>
                  </div>
                  <span
                    className="px-2 py-0.5 rounded text-[9px] font-bold uppercase"
                    style={{
                      background:
                        agentMood === "hostile"
                          ? "rgba(239,68,68,0.2)"
                          : agentMood === "tense"
                          ? "rgba(245,184,61,0.2)"
                          : "rgba(0,230,118,0.2)",
                      color:
                        agentMood === "hostile"
                          ? "#F87171"
                          : agentMood === "tense"
                          ? "#FBBF24"
                          : "#34D399",
                    }}
                  >
                    {scene === "manager_arrival"
                      ? "DAY 1 MANDATE"
                      : scene === "boardroom_clash"
                      ? "WAR ROOM"
                      : `AGENT: ${agentMood.toUpperCase()}`}
                  </span>
                </div>

                {/* 3D Holo-Dossier / Executive Silhouette */}
                <div className="my-auto text-center">
                  <div className="text-sm font-black text-white">{subjectName}</div>
                  <div className="text-[11px] text-cyan-300 font-semibold">{subjectRole}</div>
                </div>

                {/* Mahogany Desk Reflection Bar */}
                <div
                  className="w-full py-1.5 px-2.5 rounded-lg text-[10px] font-bold text-center"
                  style={{
                    background: "rgba(245, 184, 61, 0.14)",
                    border: "1px solid rgba(245, 184, 61, 0.35)",
                    color: "var(--gtex-gold)",
                  }}
                >
                  {scene === "manager_arrival"
                    ? "Official Press & Training Ground Presentation"
                    : "Interactive 3D Contract & Release-Clause Table"}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Drag Hint Pill */}
        <div className="absolute top-3 left-4 z-20 pointer-events-none flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/55 border border-white/10 text-[10px] text-white/70">
          <Layers size={11} className="text-amber-400" />
          Drag 360° to rotate 3D camera · {rotY.toFixed(0)}°
        </div>
      </div>

      {/* Broadcast Lower-Third Banner (FM / Sky Sports / UEFA Gala Style) */}
      <div
        className="relative z-20 px-4 py-3 border-t flex flex-col md:flex-row md:items-center md:justify-between gap-3"
        style={{
          background:
            "linear-gradient(90deg, rgba(6, 10, 20, 0.98) 0%, rgba(15, 23, 42, 0.96) 60%, rgba(10, 16, 30, 0.98) 100%)",
          borderColor: "rgba(245, 184, 61, 0.3)",
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
