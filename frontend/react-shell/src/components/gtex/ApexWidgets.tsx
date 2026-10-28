import React, { useEffect, useMemo, useRef, useState } from "react";
import { Sparkles, TrendingUp, Zap, Search, Compass, ArrowUpRight } from "lucide-react";
import { fmt } from "@/lib/owner";

/* ============================================================================
   1. MOUSE-REACTIVE 3D-TILT HOLOGRAPHIC FOIL PLAYER CARD + 6-AXIS RADAR
   ============================================================================ */
export interface HolographicPlayerCardProps {
  name: string;
  position?: string;
  overall: number;
  potential?: number;
  clubName?: string;
  priceGtx?: number;
  jerseyNumber?: number | string;
  badgeLabel?: string;
  tier?: "diamond" | "gold" | "emerald" | "obsidian";
  stats6?: [number, number, number, number, number, number]; // PAC, SHO, PAS, DRI, DEF, PHY (0..99)
  actionLabel?: string;
  onAction?: () => void;
  testid?: string;
}

export const HolographicPlayerCard: React.FC<HolographicPlayerCardProps> = ({
  name,
  position = "ST",
  overall = 88,
  potential,
  clubName = "GTEX FC",
  priceGtx,
  jerseyNumber = 9,
  badgeLabel,
  tier,
  stats6,
  actionLabel = "3D Walkout →",
  onAction,
  testid,
}) => {
  const cardRef = useRef<HTMLDivElement | null>(null);
  const [tilt, setTilt] = useState<{ rx: number; ry: number; gx: number; gy: number; active: boolean }>({
    rx: 0,
    ry: 0,
    gx: 50,
    gy: 30,
    active: false,
  });

  const resolvedTier =
    tier ||
    ((potential && potential >= 94) || overall >= 91
      ? "diamond"
      : overall >= 85
      ? "gold"
      : "emerald");

  const borderStyle =
    resolvedTier === "diamond"
      ? "border-amber-300/90 shadow-[0_18px_42px_-8px_rgba(251,191,36,0.38)]"
      : resolvedTier === "gold"
      ? "border-amber-400/75 shadow-[0_18px_40px_-8px_rgba(245,158,11,0.28)]"
      : resolvedTier === "emerald"
      ? "border-emerald-400/75 shadow-[0_18px_40px_-8px_rgba(16,185,129,0.28)]"
      : "border-white/20 shadow-xl";

  const bgGradient =
    resolvedTier === "diamond"
      ? "linear-gradient(145deg, #1e1b4b 0%, #090d16 54%, #422006 100%)"
      : resolvedTier === "gold"
      ? "linear-gradient(145deg, #271a0c 0%, #090d16 58%, #062c22 100%)"
      : "linear-gradient(145deg, #062e22 0%, #090d16 58%, #0c192e 100%)";

  // Compute 6-axis radar points (PAC, SHO, PAS, DRI, DEF, PHY)
  const radarValues = useMemo(() => {
    if (stats6) return stats6;
    const base = Math.max(60, Math.min(98, Number(overall) || 85));
    const isDef = ["CB", "LB", "RB", "CDM", "GK"].includes(position.toUpperCase());
    return [
      Math.min(99, base + 4),
      isDef ? Math.max(52, base - 14) : Math.min(99, base + 2),
      Math.min(99, base),
      Math.min(99, base + 3),
      isDef ? Math.min(99, base + 5) : Math.max(48, base - 18),
      Math.min(99, base - 1),
    ];
  }, [stats6, overall, position]);

  const radarPolygonPoints = useMemo(() => {
    const cx = 50;
    const cy = 50;
    const maxR = 40;
    const angles = [-90, -30, 30, 90, 150, 210];
    return radarValues
      .map((v, idx) => {
        const r = (Math.max(35, Math.min(99, v)) / 100) * maxR;
        const rad = (angles[idx] * Math.PI) / 180;
        const x = (cx + Math.cos(rad) * r).toFixed(1);
        const y = (cy + Math.sin(rad) * r).toFixed(1);
        return `${x},${y}`;
      })
      .join(" ");
  }, [radarValues]);

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    setTilt({
      rx: (0.5 - y) * 20,
      ry: (x - 0.5) * 24,
      gx: Math.round(x * 100),
      gy: Math.round(y * 100),
      active: true,
    });
  };

  const handlePointerLeave = () => {
    setTilt({ rx: 0, ry: 0, gx: 50, gy: 30, active: false });
  };

  return (
    <div style={{ perspective: "950px" }} data-testid={testid}>
      <div
        ref={cardRef}
        onPointerMove={handlePointerMove}
        onPointerLeave={handlePointerLeave}
        onClick={onAction}
        className={`group relative rounded-2xl border-2 p-4 flex flex-col justify-between overflow-hidden select-none cursor-pointer transition-transform duration-100 ${borderStyle}`}
        style={{
          transformStyle: "preserve-3d",
          transform: `rotateX(${tilt.rx}deg) rotateY(${tilt.ry}deg) scale(${tilt.active ? 1.02 : 1})`,
          background: bgGradient,
          boxShadow: "inset 0 1px 0 rgba(255,255,255,0.3)",
        }}
      >
        {/* Dynamic Mouse-Reactive Holographic Foil Glare */}
        <div
          className="pointer-events-none absolute inset-0 transition-opacity duration-200"
          style={{
            opacity: tilt.active ? 0.85 : 0.45,
            background: `radial-gradient(circle at ${tilt.gx}% ${tilt.gy}%, rgba(253,224,71,0.45), rgba(16,185,129,0.28) 38%, rgba(56,189,248,0.18) 58%, transparent 75%)`,
            mixBlendMode: "screen",
          }}
        />

        {/* Top Row: OVR Shield & Tier Pill */}
        <div
          className="relative z-10 flex items-start justify-between gap-2"
          style={{ transform: "translateZ(18px)" }}
        >
          <div className="flex items-center gap-2">
            <div className="flex flex-col items-center justify-center rounded-xl bg-gradient-to-b from-amber-300 to-amber-500 px-2.5 py-1 text-slate-950 shadow-lg">
              <span className="gx-display text-2xl font-black leading-none">{overall}</span>
              <span className="text-[10px] font-black uppercase leading-tight">{position}</span>
            </div>
            <div>
              <span className="gx-mono text-[10px] font-bold uppercase text-amber-300/90 block">
                #{jerseyNumber} · {clubName}
              </span>
              <h4 className="gx-display text-lg font-black uppercase tracking-tight text-white leading-tight truncate max-w-[145px]">
                {name}
              </h4>
            </div>
          </div>

          <span className="shrink-0 rounded-full border border-amber-300/50 bg-amber-400/20 px-2 py-0.5 text-[9px] font-black uppercase tracking-wider text-amber-200">
            {badgeLabel || (resolvedTier === "diamond" ? "★ TOTY FOIL" : "★ PRO FOIL")}
          </span>
        </div>

        {/* Center Row: 6-Axis Attribute Breakdown + SVG Radar Polygon */}
        <div
          className="relative z-10 my-3 flex items-center justify-between gap-2 rounded-xl border border-white/10 bg-black/40 p-2.5"
          style={{ transform: "translateZ(24px)" }}
        >
          <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[10px] font-bold">
            <div className="flex items-center justify-between gap-1.5">
              <span className="text-slate-400">PAC</span>
              <span className="gx-mono text-emerald-300">{radarValues[0]}</span>
            </div>
            <div className="flex items-center justify-between gap-1.5">
              <span className="text-slate-400">DRI</span>
              <span className="gx-mono text-emerald-300">{radarValues[3]}</span>
            </div>
            <div className="flex items-center justify-between gap-1.5">
              <span className="text-slate-400">SHO</span>
              <span className="gx-mono text-amber-300">{radarValues[1]}</span>
            </div>
            <div className="flex items-center justify-between gap-1.5">
              <span className="text-slate-400">DEF</span>
              <span className="gx-mono text-sky-300">{radarValues[4]}</span>
            </div>
            <div className="flex items-center justify-between gap-1.5">
              <span className="text-slate-400">PAS</span>
              <span className="gx-mono text-white">{radarValues[2]}</span>
            </div>
            <div className="flex items-center justify-between gap-1.5">
              <span className="text-slate-400">PHY</span>
              <span className="gx-mono text-white">{radarValues[5]}</span>
            </div>
          </div>

          {/* 6-Axis Radar Polygon */}
          <svg viewBox="0 0 100 100" className="h-16 w-16 shrink-0 overflow-visible">
            <polygon
              points="50,10 85,30 85,70 50,90 15,70 15,30"
              fill="rgba(255,255,255,0.04)"
              stroke="rgba(255,255,255,0.22)"
              strokeWidth="1"
            />
            <polygon
              points="50,25 72,37 72,63 50,75 28,63 28,37"
              fill="none"
              stroke="rgba(255,255,255,0.12)"
              strokeWidth="1"
            />
            <polygon
              points={radarPolygonPoints}
              fill="rgba(16,185,129,0.34)"
              stroke="#10b981"
              strokeWidth="2"
            />
          </svg>
        </div>

        {/* Bottom Row: Potential / Valuation & Shimmer Action Pill */}
        <div
          className="relative z-10 flex items-center justify-between gap-2 pt-1 text-xs"
          style={{ transform: "translateZ(16px)" }}
        >
          <div className="flex items-center gap-1.5">
            {potential && (
              <span className="rounded bg-emerald-500/20 border border-emerald-400/40 px-2 py-0.5 text-[10px] font-black text-emerald-300">
                {potential} POT
              </span>
            )}
            {priceGtx !== undefined && (
              <span className="gx-mono text-xs font-extrabold text-amber-300">
                {fmt(priceGtx)} GTX
              </span>
            )}
          </div>
          <span className="inline-flex items-center gap-1 rounded-lg bg-emerald-500 px-2.5 py-1 text-[10px] font-black uppercase text-slate-950 shadow group-hover:bg-emerald-400 transition">
            <Sparkles size={11} /> {actionLabel}
          </span>
        </div>
      </div>
    </div>
  );
};

/* ============================================================================
   2. ROBINHOOD-GRADE LIVE SVG TELEMETRY SPARKLINE & ROLLING COUNTER CARD
   ============================================================================ */
export interface TelemetrySparklineCardProps {
  title: string;
  subtitle?: string;
  amount: number;
  currency?: string;
  deltaLabel?: string;
  trustScore?: number;
  hypeScore?: number;
  series?: number[];
}

export const TelemetrySparklineCard: React.FC<TelemetrySparklineCardProps> = ({
  title,
  subtitle = "Real-Time Club Treasury & Commercial Pulse",
  amount = 248500,
  currency = "GTX",
  deltaLabel = "▲ +14.8% LIVE VELOCITY",
  trustScore = 92,
  hypeScore = 96,
  series = [62, 68, 64, 78, 74, 88, 94, 100],
}) => {
  const [displayAmount, setDisplayAmount] = useState<number>(amount);

  useEffect(() => {
    const startVal = displayAmount;
    const endVal = Number(amount) || 0;
    if (startVal === endVal) return;
    let rafId: number;
    const startTime = performance.now();
    const duration = 650;
    const step = (now: number) => {
      const p = Math.min(1, (now - startTime) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplayAmount(Math.round(startVal + (endVal - startVal) * eased));
      if (p < 1) rafId = requestAnimationFrame(step);
    };
    rafId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(rafId);
  }, [amount]);

  const { linePath, areaPath, lastPoint } = useMemo(() => {
    const w = 280;
    const h = 76;
    const min = Math.min(...series);
    const max = Math.max(...series, min + 1);
    const pts = series.map((v, i) => {
      const x = (i / Math.max(1, series.length - 1)) * (w - 12) + 6;
      const y = h - 10 - ((v - min) / (max - min)) * (h - 22);
      return { x, y };
    });
    const dLine = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
    const last = pts[pts.length - 1] || { x: w - 6, y: 14 };
    const dArea = `${dLine} L${last.x.toFixed(1)},${h} L6,${h} Z`;
    return { linePath: dLine, areaPath: dArea, lastPoint: last };
  }, [series]);

  return (
    <div className="gx-panel gx-panel-live flex flex-col justify-between">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <span className="gx-eyebrow flex items-center gap-1.5">
            <span className="gx-live-dot inline-block h-2 w-2 rounded-full bg-emerald-400" />
            {title}
          </span>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="gx-display text-3xl sm:text-4xl font-black tracking-tight text-white">
              {fmt(displayAmount)}
            </span>
            <span className="gx-mono rounded bg-sky-500/20 border border-sky-400/40 px-2 py-0.5 text-xs font-extrabold text-sky-300">
              {currency}
            </span>
          </div>
          <p className="mt-0.5 text-xs font-medium text-slate-400">{subtitle}</p>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/40 bg-emerald-500/15 px-2.5 py-1 text-[11px] font-extrabold text-emerald-300">
          <TrendingUp size={12} /> {deltaLabel}
        </span>
      </div>

      {/* Glowing SVG Area Sparkline */}
      <div className="my-3 h-20 w-full">
        <svg viewBox="0 0 280 76" className="h-full w-full overflow-visible">
          <defs>
            <linearGradient id="gtexSparkArea" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.42" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
            </linearGradient>
          </defs>
          <path d={areaPath} fill="url(#gtexSparkArea)" />
          <path
            d={linePath}
            fill="none"
            stroke="#10b981"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <circle
            cx={lastPoint.x}
            cy={lastPoint.y}
            r="5"
            fill="#fde047"
            className="gx-live-dot"
          />
        </svg>
      </div>

      {/* Radial Gauge Footer */}
      <div className="grid grid-cols-2 gap-2.5 border-t border-white/10 pt-3">
        <div className="flex items-center gap-2.5 rounded-xl border border-white/10 bg-slate-950/60 p-2.5">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 border-emerald-400 text-xs font-black text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.35)]">
            {trustScore}%
          </div>
          <div className="min-w-0">
            <div className="text-xs font-bold text-white truncate">Board Confidence</div>
            <div className="text-[11px] text-emerald-400 font-semibold truncate">Dynasty Secure</div>
          </div>
        </div>
        <div className="flex items-center gap-2.5 rounded-xl border border-white/10 bg-slate-950/60 p-2.5">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 border-amber-400 text-xs font-black text-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.35)]">
            {hypeScore}%
          </div>
          <div className="min-w-0">
            <div className="text-xs font-bold text-white truncate">Global Fan Hype</div>
            <div className="text-[11px] text-amber-300 font-semibold truncate">Box-Office Surge</div>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ============================================================================
   3. INTERACTIVE 2.5D TACTICAL TURF PITCH WITH CHEMISTRY LINKS
   ============================================================================ */
export interface TacticalPitch25DProps {
  formation?: string;
  players?: Array<{
    id?: string | number;
    name: string;
    position?: string;
    overall?: number;
  }>;
  onSelectPlayer?: (player: any) => void;
}

export const TacticalPitch25D: React.FC<TacticalPitch25DProps> = ({
  formation = "4-3-3",
  players = [],
  onSelectPlayer,
}) => {
  const nodes = useMemo(() => {
    const coords = [
      { x: 50, y: 16, role: "ST" },
      { x: 22, y: 26, role: "LW" },
      { x: 78, y: 26, role: "RW" },
      { x: 50, y: 44, role: "CAM" },
      { x: 30, y: 54, role: "CM" },
      { x: 70, y: 54, role: "CM" },
      { x: 16, y: 74, role: "LB" },
      { x: 38, y: 76, role: "CB" },
      { x: 62, y: 76, role: "CB" },
      { x: 84, y: 74, role: "RB" },
      { x: 50, y: 90, role: "GK" },
    ];
    return coords.map((c, idx) => {
      const p = players[idx];
      const surname = p?.name ? String(p.name).split(" ").slice(-1)[0] : c.role;
      return {
        ...c,
        player: p,
        label: surname,
        ovr: p?.overall || 84 + (idx % 6),
      };
    });
  }, [players]);

  return (
    <div className="gx-panel overflow-hidden">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <span className="gx-eyebrow">2.5D INTERACTIVE TACTICAL PITCH</span>
          <h3 className="gx-h3 mt-0.5">Formation {formation} · Chemistry Matrix</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-lg border border-amber-400/50 bg-amber-400/15 px-2.5 py-1 text-xs font-black text-amber-300">
            ⚡ SQUAD CHEM 98/100
          </span>
        </div>
      </div>

      <div className="relative flex items-center justify-center py-2" style={{ perspective: "750px" }}>
        <div
          className="relative h-[230px] w-full rounded-2xl border-2 border-emerald-400/65 overflow-hidden shadow-2xl"
          style={{
            transform: "rotateX(22deg)",
            background:
              "repeating-linear-gradient(0deg, #065f46 0px, #065f46 22px, #047857 22px, #047857 44px)",
            boxShadow: "0 22px 45px rgba(0,0,0,0.78), inset 0 0 30px rgba(0,0,0,0.45)",
          }}
        >
          {/* Pitch Markings & Glowing Chemistry Links SVG */}
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 h-full w-full">
            <rect x="4" y="4" width="92" height="92" fill="none" stroke="rgba(255,255,255,0.35)" strokeWidth="0.8" />
            <line x1="4" y1="50" x2="96" y2="50" stroke="rgba(255,255,255,0.35)" strokeWidth="0.8" />
            <circle cx="50" cy="50" r="12" fill="none" stroke="rgba(255,255,255,0.35)" strokeWidth="0.8" />
            <rect x="28" y="4" width="44" height="14" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="0.7" />
            <rect x="28" y="82" width="44" height="14" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="0.7" />

            {/* Chemistry Links */}
            <line x1="50" y1="16" x2="22" y2="26" stroke="#fde047" strokeWidth="1.2" />
            <line x1="50" y1="16" x2="78" y2="26" stroke="#10b981" strokeWidth="1.2" />
            <line x1="50" y1="16" x2="50" y2="44" stroke="#fde047" strokeWidth="1.4" />
            <line x1="22" y1="26" x2="30" y2="54" stroke="#10b981" strokeWidth="1.1" />
            <line x1="78" y1="26" x2="70" y2="54" stroke="#10b981" strokeWidth="1.1" />
            <line x1="50" y1="44" x2="30" y2="54" stroke="#fde047" strokeWidth="1.1" />
            <line x1="50" y1="44" x2="70" y2="54" stroke="#fde047" strokeWidth="1.1" />
            <line x1="30" y1="54" x2="38" y2="76" stroke="#38bdf8" strokeWidth="1.1" />
            <line x1="70" y1="54" x2="62" y2="76" stroke="#38bdf8" strokeWidth="1.1" />
            <line x1="38" y1="76" x2="62" y2="76" stroke="#10b981" strokeWidth="1.2" />
            <line x1="16" y1="74" x2="38" y2="76" stroke="#10b981" strokeWidth="1.0" />
            <line x1="84" y1="74" x2="62" y2="76" stroke="#10b981" strokeWidth="1.0" />
            <line x1="38" y1="76" x2="50" y2="90" stroke="#fde047" strokeWidth="1.1" />
            <line x1="62" y1="76" x2="50" y2="90" stroke="#fde047" strokeWidth="1.1" />
          </svg>

          {/* Player Tokens */}
          {nodes.map((n, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => n.player && onSelectPlayer?.(n.player)}
              style={{ left: `${n.x}%`, top: `${n.y}%` }}
              className="absolute -translate-x-1/2 -translate-y-1/2 flex items-center gap-1 rounded-full border border-amber-300/80 bg-slate-950/90 px-2 py-0.5 text-[10px] font-black text-white shadow-lg transition transform hover:scale-110 hover:border-emerald-400"
            >
              <span className="text-amber-300">{n.ovr}</span>
              <span className="truncate max-w-[64px] uppercase">{n.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

/* ============================================================================
   4. GLOBAL CTRL+K / ⌘K EXECUTIVE COMMAND PALETTE MODAL
   ============================================================================ */
export interface CommandPaletteModalProps {
  open: boolean;
  onClose: () => void;
  items: Array<{ to: string; label: string; category?: string }>;
  onNavigate: (to: string) => void;
}

export const CommandPaletteModal: React.FC<CommandPaletteModalProps> = ({
  open,
  onClose,
  items,
  onNavigate,
}) => {
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (open) setQuery("");
  }, [open]);

  if (!open) return null;

  const filtered = items.filter((i) =>
    `${i.label} ${i.category || ""}`.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/75 p-4 pt-20 backdrop-blur-md"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl overflow-hidden rounded-2xl border border-emerald-400/40 bg-slate-950 shadow-[0_24px_60px_rgba(0,0,0,0.85)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 border-b border-white/10 px-4 py-3">
          <Search size={16} className="text-emerald-400" />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Jump to any GTEX command deck, 3D stage, or market hub..."
            className="w-full bg-transparent text-sm text-white placeholder:text-slate-500 outline-none"
          />
          <kbd className="rounded border border-white/15 bg-white/5 px-2 py-0.5 text-[10px] font-bold text-slate-400">
            ESC
          </kbd>
        </div>
        <div className="max-h-80 overflow-y-auto p-2 space-y-1 gx-scroll">
          {filtered.map((item) => (
            <button
              key={item.to}
              type="button"
              onClick={() => {
                onNavigate(item.to);
                onClose();
              }}
              className="flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-xs font-bold text-slate-200 transition hover:bg-emerald-500/15 hover:text-white"
            >
              <div className="flex items-center gap-2.5">
                <Compass size={14} className="text-emerald-400" />
                <span className="uppercase tracking-wider">{item.label}</span>
              </div>
              <span className="flex items-center gap-1 text-[10px] text-amber-300 font-semibold">
                {item.category || "COMMAND DECK"} <ArrowUpRight size={12} />
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
