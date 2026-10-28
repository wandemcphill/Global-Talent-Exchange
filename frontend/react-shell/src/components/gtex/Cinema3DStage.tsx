import React, { useEffect, useRef, useState } from "react";
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
  Plane,
  Building2,
  Trophy,
  Radio,
  Tv,
  Crown,
  ThumbsUp,
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

/**
 * GTEX 3D Presentation, Broadcast & Diorama Engine (Full 17-Scene Suite)
 * Combines:
 *  1. FIFA / eFootball-style 3D Motion Cinema (60fps Canvas 3D volumetric lights, flashbulbs,
 *     confetti, runway strobes, and interactive 360-degree 3D centerpiece rotation).
 *  2. Football Manager-style 3D Static Diorama Stills (multi-plane architectural depth parallax
 *     with broadcast lower-thirds and press/boardroom/hangar framing).
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
  facilityLevel = 3,
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
  initialSalutes = 42,
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
  const [saluteCount, setSaluteCount] = useState<number>(initialSalutes);
  const [hasSaluted, setHasSaluted] = useState<boolean>(false);

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
      setRotY((prev) => (prev + dt * 26) % 360);
      rafId = requestAnimationFrame(animate);
    };
    rafId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafId);
  }, [mode, isPlaying, isDragging]);

  // 60fps Volumetric Stadium Lighting, Paparazzi Flashbulbs, Runway Strobes & Gold Confetti Canvas
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

    const particles = Array.from({ length: compact ? 30 : 58 }, (_, i) => ({
      x: (i * 73) % 800,
      y: (i * 47) % 420,
      z: 0.25 + ((i * 19) % 75) / 100,
      vx: (((i * 13) % 10) - 5) * 0.25,
      vy: isGoldHeavy || scene === "signing_walkout" ? 0.6 + ((i % 5) * 0.2) : -0.35,
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

      // 1. Deep 3D Studio / Stadium / Hangar Horizon Gradient
      const bgGrad = ctx.createRadialGradient(w * 0.5, h * 0.32, 10, w * 0.5, h * 0.5, w * 0.75);
      if (isGoldHeavy) {
        bgGrad.addColorStop(0, "rgba(65, 45, 10, 0.92)");
        bgGrad.addColorStop(0.55, "rgba(16, 14, 24, 0.96)");
        bgGrad.addColorStop(1, "rgba(5, 6, 12, 1)");
      } else if (
        scene === "facility_upgrade" ||
        scene === "academy_upgrade" ||
        scene === "stadium_ad_display"
      ) {
        bgGrad.addColorStop(0, "rgba(10, 48, 70, 0.92)");
        bgGrad.addColorStop(0.6, "rgba(8, 18, 32, 0.97)");
        bgGrad.addColorStop(1, "rgba(3, 7, 14, 1)");
      } else if (scene === "club_announcement" || scene === "new_ad_deal") {
        bgGrad.addColorStop(0, "rgba(55, 18, 38, 0.92)");
        bgGrad.addColorStop(0.6, "rgba(12, 14, 26, 0.97)");
        bgGrad.addColorStop(1, "rgba(4, 6, 12, 1)");
      } else {
        bgGrad.addColorStop(0, "rgba(12, 52, 38, 0.9)");
        bgGrad.addColorStop(0.55, "rgba(9, 19, 32, 0.96)");
        bgGrad.addColorStop(1, "rgba(4, 8, 15, 1)");
      }
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, w, h);

      // 2. 3D Perspective Floor Grid (Blueprint / Runway / Stadium Floor)
      const horizonY = h * 0.64;
      ctx.save();
      ctx.strokeStyle = isGoldHeavy
        ? "rgba(245, 184, 61, 0.18)"
        : scene === "facility_upgrade" || scene === "academy_upgrade"
        ? "rgba(56, 189, 248, 0.22)"
        : "rgba(0, 230, 118, 0.14)";
      ctx.lineWidth = 1;

      const vpX = w * 0.5 + Math.sin(tick * 0.6) * (mode === "motion_3d" ? 18 : 0);
      for (let i = -8; i <= 8; i++) {
        ctx.beginPath();
        ctx.moveTo(vpX, horizonY);
        ctx.lineTo(vpX + i * 95, h);
        ctx.stroke();
      }
      for (let r = 1; r <= 6; r++) {
        const py = horizonY + Math.pow(r / 6, 1.7) * (h - horizonY);
        ctx.beginPath();
        ctx.moveTo(0, py);
        ctx.lineTo(w, py);
        ctx.stroke();
      }
      ctx.restore();

      // 3. Volumetric 3D Floodlight Cones
      const beamCount = isGoldHeavy || spectacleTier === "galactico_helicopter" ? 4 : 3;
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

      // 4. Paparazzi Camera Flashbulbs & Runway Strobes
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
          scene === "world_gala" ||
          scene === "competition_final" ||
          scene === "private_jet_flex" ||
          scene === "wonderkid_emergence"
            ? "rgba(245, 184, 61, 0.6)"
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

        {/* FM-Style Architectural Press / Stadium / Hangar Backdrop Wall */}
        <div
          className="absolute inset-x-10 top-6 bottom-16 rounded-2xl pointer-events-none transition-transform duration-300"
          style={{
            transform: `translateZ(-120px) rotateX(${rotX * 0.25}deg) rotateY(${rotY * 0.12}deg) scale(${cameraScale})`,
            border: "1px solid rgba(255,255,255,0.07)",
            background:
              "radial-gradient(circle at 50% 25%, rgba(255,255,255,0.05), rgba(0,0,0,0.45))",
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
          {/* 1. KIT / SIGNING WALKOUT / BUILD-A-SON / WONDERKID EMERGENCE */}
          {(scene === "signing_walkout" ||
            scene === "build_a_son" ||
            scene === "stadium_sponsor" ||
            scene === "wonderkid_emergence") && (
            <div className="relative flex flex-col items-center">
              <div
                className="relative w-44 h-52 rounded-2xl flex flex-col items-center justify-between p-4 border-2"
                style={{
                  background:
                    scene === "wonderkid_emergence"
                      ? "linear-gradient(145deg, #F59E0B, #0b1322 65%, #10B981)"
                      : `linear-gradient(145deg, ${primaryColor}, #0b1322 75%, ${secondaryColor})`,
                  borderColor: "rgba(245, 184, 61, 0.85)",
                  boxShadow: `0 18px 40px -10px ${primaryColor}66, inset 0 0 24px rgba(255,255,255,0.22)`,
                }}
              >
                <div className="w-full flex items-center justify-between text-[10px] font-extrabold uppercase tracking-wider text-white/90">
                  <span className="px-1.5 py-0.5 rounded bg-black/40 border border-white/15">
                    {clubName.slice(0, 12)}
                  </span>
                  <span className="px-1.5 py-0.5 rounded bg-amber-400/20 text-amber-300 border border-amber-400/40">
                    OVR {overallRating}
                  </span>
                </div>

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

                <div className="w-full py-1 px-2 rounded bg-black/55 border border-white/15 text-center">
                  <div className="text-[8px] uppercase tracking-widest text-amber-300 font-bold truncate">
                    {scene === "wonderkid_emergence" ? "GOLDEN FLARE WALKOUT" : sponsorName}
                  </div>
                </div>
              </div>

              {(potentialRating || scene === "wonderkid_emergence") && (
                <div
                  className="mt-2 px-3 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider"
                  style={{
                    background: "rgba(245, 184, 61, 0.25)",
                    color: "#FDE047",
                    border: "1px solid rgba(245, 184, 61, 0.6)",
                  }}
                >
                  Generational Ceiling: {potentialRating || 95} POT
                </div>
              )}
            </div>
          )}

          {/* 2. NEW CLUB OWNER ("KEYS TO THE CLUB" 3D TAKEOVER CEREMONY) */}
          {scene === "club_takeover" && (
            <div className="w-64 h-48 rounded-2xl p-4 border-2 flex flex-col items-center justify-between text-center"
              style={{
                background: "radial-gradient(circle at 50% 20%, rgba(245,184,61,0.35), rgba(8,14,28,0.96) 75%)",
                borderColor: "#F5B83D",
                boxShadow: "0 20px 50px rgba(245, 184, 61, 0.35)",
              }}
            >
              <div className="text-[10px] font-black uppercase tracking-widest text-amber-300">
                OFFICIAL 3D CLUB CHARTER & DEEDS
              </div>
              <div className="w-20 h-20 rounded-2xl border-2 border-amber-400 bg-amber-400/15 flex items-center justify-center shadow-lg">
                <Crown size={40} className="text-amber-300" />
              </div>
              <div>
                <div className="text-base font-black uppercase text-white">{clubName}</div>
                <div className="text-[10px] font-bold text-emerald-400 uppercase">
                  Keys Presented to {ownerName}
                </div>
              </div>
            </div>
          )}

          {/* 3. FACILITY / STADIUM & ACADEMY 3D ARCHITECTURAL BLUEPRINT-TO-CATHEDRAL */}
          {(scene === "facility_upgrade" ||
            scene === "academy_upgrade" ||
            scene === "stadium_ad_display") && (
            <div
              className="w-68 h-48 rounded-2xl p-4 border-2 flex flex-col items-center justify-between text-center"
              style={{
                background:
                  "linear-gradient(155deg, rgba(8, 47, 73, 0.92), rgba(6, 16, 32, 0.98))",
                borderColor: scene === "stadium_ad_display" ? "#F5B83D" : "#38BDF8",
                boxShadow: "0 20px 45px rgba(56, 189, 248, 0.28)",
              }}
            >
              <div className="w-full flex items-center justify-between text-[10px] font-black uppercase text-cyan-300">
                <span>
                  {scene === "academy_upgrade"
                    ? "3D LA MASIA YOUTH CAMPUS"
                    : scene === "stadium_ad_display"
                    ? "3D STADIUM AD BOWL CUTAWAY"
                    : "3D STADIUM CATHEDRAL CUTAWAY"}
                </span>
                <span className="px-2 py-0.5 rounded bg-cyan-500/20 border border-cyan-400/40 text-amber-300">
                  LVL {facilityLevel}/5
                </span>
              </div>

              {/* 3D Tiered Stadium Bowl Rings */}
              <div className="relative w-44 h-24 rounded-full border-4 border-cyan-400/70 bg-emerald-950/80 flex items-center justify-center shadow-inner">
                <div className="w-32 h-14 rounded-full border-2 border-amber-400/80 bg-emerald-500/30 flex items-center justify-center">
                  <Building2 size={24} className="text-white" />
                </div>
              </div>

              <div className="w-full py-1 px-2 rounded bg-black/60 border border-cyan-400/30 text-[10px] font-bold text-amber-300 truncate">
                {scene === "stadium_ad_display"
                  ? `${adSurfaceZone} · ${sponsorName}`
                  : subjectName}
              </div>
            </div>
          )}

          {/* 4. BIG COMPETITION FINALS & WORLD GALA 3D TROPHY PLINTH */}
          {(scene === "world_gala" || scene === "competition_final") && (
            <div className="relative flex flex-col items-center">
              <div
                className="w-36 h-36 rounded-full flex flex-col items-center justify-center border-4 relative"
                style={{
                  borderColor: "#FDE047",
                  background:
                    "radial-gradient(circle at 35% 30%, #FEF08A, #F59E0B 55%, #78350F 100%)",
                  boxShadow: "0 0 50px rgba(245, 184, 61, 0.75), inset 0 -10px 25px rgba(0,0,0,0.45)",
                }}
              >
                {scene === "competition_final" ? (
                  <Trophy size={48} className="text-amber-950 drop-shadow" />
                ) : (
                  <Award size={48} className="text-amber-950 drop-shadow" />
                )}
                <span className="text-[9px] font-black uppercase tracking-widest text-amber-950 mt-0.5">
                  {scene === "competition_final" ? "FINAL PLINTH" : "GTEX D'OR"}
                </span>
              </div>
              <div
                className="w-36 h-12 -mt-2 rounded-b-xl border-2 flex flex-col items-center justify-center px-2"
                style={{
                  background: "linear-gradient(180deg, #1E293B, #020617)",
                  borderColor: "#F5B83D",
                }}
              >
                <span className="text-[10px] font-black text-amber-300 truncate max-w-[125px]">
                  {subjectName}
                </span>
                <span className="text-[8px] uppercase text-white/70 truncate max-w-[125px]">
                  {clubName}
                </span>
              </div>
            </div>
          )}

          {/* 5. PRIVATE JET PURCHASE NEWS & VISITOR HANGAR SHOWCASE (FOR OTHER USERS) */}
          {(scene === "private_jet_flex" || scene === "luxury_turntable") && (
            <div className="relative flex flex-col items-center">
              <div
                className="w-60 h-48 rounded-2xl flex flex-col items-center justify-between p-4 border-2 relative"
                style={{
                  background:
                    "radial-gradient(circle at 30% 25%, rgba(245,184,61,0.34), rgba(18,14,32,0.96) 72%)",
                  borderColor: "rgba(245, 184, 61, 0.85)",
                  boxShadow: "0 20px 45px rgba(245, 184, 61, 0.32), inset 0 0 30px rgba(245, 184, 61, 0.18)",
                }}
              >
                <div className="w-full flex items-center justify-between text-[9px] font-black uppercase tracking-wider text-amber-300">
                  <span>{scene === "private_jet_flex" ? "3D VIP NIGHT RUNWAY" : "3D BESPOKE VAULT"}</span>
                  <span className="px-1.5 py-0.5 rounded bg-amber-400/20 border border-amber-400/40">
                    1 OF 10 MINTED
                  </span>
                </div>

                <div
                  className="w-20 h-20 rounded-full flex items-center justify-center border-2"
                  style={{
                    borderColor: "#F5B83D",
                    background: "linear-gradient(135deg, rgba(245,184,61,0.35), rgba(0,0,0,0.75))",
                    boxShadow: "0 0 28px rgba(245,184,61,0.5)",
                  }}
                >
                  {scene === "private_jet_flex" || assetCategory === "jet" ? (
                    <Plane size={38} className="text-amber-300 -rotate-12" />
                  ) : (
                    <Sparkles size={36} className="text-amber-300" />
                  )}
                </div>

                <div className="text-center">
                  <div className="text-sm font-black text-white leading-tight">{subjectName}</div>
                  <div className="text-[10px] text-emerald-400 font-bold uppercase mt-0.5">
                    Tail-Fin Livery: {clubName} ({ownerName})
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 6. BREAKING CLUB ANNOUNCEMENT STUDIO & NEW AD DEAL HANDSHAKE */}
          {(scene === "club_announcement" ||
            scene === "new_ad_deal" ||
            scene === "negotiation_table" ||
            scene === "manager_arrival" ||
            scene === "boardroom_clash") && (
            <div className="relative flex flex-col items-center">
              <div
                className="w-68 h-46 rounded-2xl p-4 border-2 flex flex-col justify-between"
                style={{
                  background:
                    "linear-gradient(160deg, rgba(16, 28, 48, 0.96), rgba(7, 12, 24, 0.98))",
                  borderColor:
                    scene === "club_announcement" || scene === "new_ad_deal"
                      ? "#F5B83D"
                      : agentMood === "hostile"
                      ? "rgba(239, 68, 68, 0.75)"
                      : agentMood === "tense"
                      ? "rgba(245, 184, 61, 0.75)"
                      : "rgba(0, 230, 118, 0.7)",
                  boxShadow: "0 20px 45px rgba(0,0,0,0.75)",
                }}
              >
                <div className="flex items-center justify-between border-b border-white/10 pb-2">
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
                  <span className="px-2 py-0.5 rounded bg-amber-400/20 text-amber-300 text-[9px] font-bold uppercase">
                    {scene === "club_announcement"
                      ? "LIVE WIRE"
                      : scene === "new_ad_deal"
                      ? sponsorName.slice(0, 14)
                      : scene === "manager_arrival"
                      ? "DAY 1 MANDATE"
                      : `AGENT: ${agentMood.toUpperCase()}`}
                  </span>
                </div>

                <div className="my-auto text-center py-2">
                  <div className="text-sm font-black text-white uppercase">{subjectName}</div>
                  <div className="text-[11px] text-cyan-300 font-semibold mt-0.5">{subjectRole}</div>
                </div>

                <div
                  className="w-full py-1.5 px-2.5 rounded-lg text-[10px] font-bold text-center"
                  style={{
                    background: "rgba(245, 184, 61, 0.14)",
                    border: "1px solid rgba(245, 184, 61, 0.35)",
                    color: "var(--gtex-gold)",
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

        {/* Drag Hint Pill */}
        <div className="absolute top-3 left-4 z-20 pointer-events-none flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/55 border border-white/10 text-[10px] text-white/70">
          <Layers size={11} className="text-amber-400" />
          Drag 360° to rotate 3D camera · {rotY.toFixed(0)}°
        </div>
      </div>

      {/* Broadcast Lower-Third Banner */}
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

        {/* Social Flex Salute Button for Other Users on the App */}
        {(enableSocialSalute || scene === "private_jet_flex" || scene === "club_announcement") && (
          <button
            type="button"
            onClick={() => {
              if (!hasSaluted) {
                setSaluteCount((c) => c + 1);
                setHasSaluted(true);
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
