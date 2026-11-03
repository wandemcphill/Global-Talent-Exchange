import React, { useMemo, useRef, useState } from "react";
import { ArrowDownRight, ArrowUpRight, ShieldCheck, Star } from "lucide-react";
import { RegenCard } from "./RegenCard";

export const POS: Record<string, string> = {
  goalkeeper: "GK",
  defender: "DEF",
  midfielder: "MID",
  forward: "FWD",
  attacker: "FWD",
  gk: "GK",
  df: "DEF",
  mf: "MID",
  fw: "FWD",
  striker: "ST",
  winger: "W",
  "centre-back": "CB",
  "center-back": "CB",
  "full-back": "FB",
  "central midfielder": "CM",
  "attacking midfielder": "AM",
  "defensive midfielder": "DM",
  "centre-forward": "CF",
};

export const posShort = (p?: string): string =>
  p ? POS[p.toLowerCase()] || p.slice(0, 3).toUpperCase() : "-";

export type TierType = "standard" | "elite" | "legendary" | "regen";

export interface TierConfig {
  name: string;
  badge: string;
  frame: string;
  glow: string;
  accent: string;
  ratingText: string;
}

export const TIERS: Record<TierType, TierConfig> = {
  standard: {
    name: "Standard",
    badge: "border-[#25354B] bg-[#14243A] text-slate-300",
    frame: "border-[#25354B] bg-gradient-to-b from-[#14243A] via-[#0E1A2C] to-[#080F1C]",
    glow: "shadow-black/70",
    accent: "text-slate-400",
    ratingText: "text-white",
  },
  elite: {
    name: "Elite",
    badge: "border-[#00C991]/50 bg-[#00C991]/15 text-[#00E8A8] shadow-[0_0_12px_rgba(0,201,145,0.25)]",
    frame: "border-[#00C991]/60 bg-gradient-to-b from-[#082E22] via-[#0E1A2C] to-[#080F1C]",
    glow: "shadow-[0_16px_40px_rgba(0,201,145,0.22)]",
    accent: "text-[#00C991]",
    ratingText: "text-[#00E8A8]",
  },
  legendary: {
    name: "Legendary",
    badge: "border-[#E5B63F]/60 bg-[#E5B63F]/15 text-[#E5B63F] shadow-[0_0_16px_rgba(229,182,63,0.35)]",
    frame: "border-[#E5B63F]/75 bg-gradient-to-b from-[#2E240D] via-[#14243A] to-[#080F1C]",
    glow: "shadow-[0_20px_50px_rgba(229,182,63,0.28)]",
    accent: "text-[#E5B63F]",
    ratingText: "text-[#E5B63F]",
  },
  regen: {
    name: "Regen",
    badge: "border-[#00C991]/60 bg-[#00C991]/15 text-[#00E8A8]",
    frame: "border-[#00C991]/50 bg-gradient-to-b from-[#082E22] via-[#0E1A2C] to-[#080F1C]",
    glow: "shadow-[0_16px_40px_rgba(0,201,145,0.22)]",
    accent: "text-[#00C991]",
    ratingText: "text-[#00E8A8]",
  },
};

export function tierOf(rating: number, regen?: boolean): TierConfig {
  if (regen) return TIERS.regen;
  if (rating >= 85) return TIERS.legendary;
  if (rating >= 75) return TIERS.elite;
  return TIERS.standard;
}

const FAKE_REAL_PLAYER_IMAGE_TOKENS = [
  "regen_newgen_faces",
  "generated-media",
  "regen_portraits",
  "national_regen_portraits",
  "sportmonks.com/images/soccer/placeholder",
  "/img/players/",
];

export function sanitizeRealPlayerImage(image?: string | null, isRegen?: boolean): string | null {
  if (!image || typeof image !== "string") return null;
  const trimmed = image.trim();
  if (!trimmed) return null;
  if (!isRegen) {
    const lower = trimmed.toLowerCase();
    if (FAKE_REAL_PLAYER_IMAGE_TOKENS.some((tok) => lower.includes(tok))) {
      return null;
    }
  }
  return trimmed;
}

export function buildSilhouetteDataUri(position?: string, isLegendary?: boolean): string {
  const posLabel = posShort(position);
  const accent = isLegendary ? "#E5B63F" : "#00C991";
  const bgTop = isLegendary ? "#2E240D" : "#14243A";
  const bgBot = isLegendary ? "#14243A" : "#080F1C";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 260" fill="none"><defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="${bgTop}" stop-opacity="0.45"/><stop offset="100%" stop-color="${bgBot}" stop-opacity="0.1"/></linearGradient><linearGradient id="sil" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#64748B"/><stop offset="65%" stop-color="#334155"/><stop offset="100%" stop-color="#0F172A"/></linearGradient></defs><circle cx="120" cy="118" r="88" fill="url(#bg)" stroke="${accent}" stroke-opacity="0.32" stroke-width="1.5"/><path d="M120 52c21 0 37 17 37 39 0 18-10 33-24 39l1 9c33 9 57 32 64 68H42c7-36 31-59 64-68l1-9c-14-6-24-21-24-39 0-22 16-39 37-39Z" fill="url(#sil)" stroke="rgba(255,255,255,0.22)" stroke-width="1.6"/><path d="M97 143l23 18 23-18" stroke="${accent}" stroke-opacity="0.75" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/><rect x="96" y="176" width="48" height="20" rx="10" fill="rgba(8,15,28,0.85)" stroke="${accent}" stroke-opacity="0.55" stroke-width="1.2"/><text x="120" y="190" text-anchor="middle" fill="#E2E8F0" font-family="monospace" font-weight="800" font-size="11" letter-spacing="1">${posLabel}</text></svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

export function resolvePlayerFallback(position?: string, isLegendary?: boolean): string {
  return buildSilhouetteDataUri(position, isLegendary);
}

function buildRadarPolygon(rating: number, position?: string): string {
  const base = Math.max(58, Math.min(98, rating || 78));
  const pos = (position || "").toUpperCase();
  const isDef = pos.includes("DEF") || pos.includes("CB") || pos.includes("FB") || pos.includes("GK");
  const vals = [
    Math.min(99, base + 4),
    isDef ? Math.max(48, base - 14) : Math.min(99, base + 3),
    Math.min(99, base + 1),
    Math.min(99, base + 2),
    isDef ? Math.min(99, base + 6) : Math.max(46, base - 16),
    Math.min(99, base),
  ];
  const angles = [-90, -30, 30, 90, 150, 210];
  return vals
    .map((v, i) => {
      const r = (v / 100) * 38;
      const rad = (angles[i] * Math.PI) / 180;
      return `${(50 + Math.cos(rad) * r).toFixed(1)},${(50 + Math.sin(rad) * r).toFixed(1)}`;
    })
    .join(" ");
}

export interface PlayerCardProps {
  name?: string;
  rating?: number | string;
  potential?: number | string;
  position?: string;
  age?: number | string;
  nationality?: string;
  club?: string;
  image?: string | null;
  regen?: boolean;
  tier?: TierType;
  stats?: Array<{ k: string; v: string | number }>;
  footer?: React.ReactNode;
  onClick?: () => void;
  testid?: string;
  badge?: string;
  variant?: "full" | "compact" | "thumbnail";
  price?: number | string;
  change?: number;
  form?: string | number;
  className?: string;
  generation?: number | string;
  archetype?: string;
  serial?: string;
  lineage?: Array<{ label: string; detail: string }>;
  traits?: string[];
}

export function PlayerCard(props: PlayerCardProps) {
  if (props.regen) {
    return <RegenCard {...props} />;
  }

  const {
    name = "Player",
    rating = 75,
    potential,
    position = "MID",
    age,
    nationality,
    club,
    image,
    stats = [],
    footer,
    onClick,
    testid = "player-card",
    badge,
    variant = "full",
    price,
    change,
    form,
    className = "",
  } = props;

  const numRating = Number(rating || 0);
  const tier = props.tier ? TIERS[props.tier] || tierOf(numRating) : tierOf(numRating);
  const [imgError, setImgError] = useState(false);
  const cardRef = useRef<HTMLElement | null>(null);
  const [holo, setHolo] = useState<{ rx: number; ry: number; gx: number; gy: number; active: boolean }>({
    rx: 0,
    ry: 0,
    gx: 50,
    gy: 25,
    active: false,
  });

  const isLegendaryTier = props.tier === "legendary" || numRating >= 85;
  const fallbackSrc = useMemo(
    () => resolvePlayerFallback(position, isLegendaryTier),
    [position, isLegendaryTier],
  );
  const cleanImage = useMemo(() => sanitizeRealPlayerImage(image, props.regen), [image, props.regen]);
  const imageSrc = !imgError && cleanImage ? cleanImage : fallbackSrc;
  const radarPts = useMemo(() => buildRadarPolygon(numRating, position), [numRating, position]);

  const handleMove = (e: React.PointerEvent<HTMLElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    setHolo({
      rx: (0.5 - y) * 14,
      ry: (x - 0.5) * 18,
      gx: Math.round(x * 100),
      gy: Math.round(y * 100),
      active: true,
    });
  };

  const handleLeave = () => {
    setHolo({ rx: 0, ry: 0, gx: 50, gy: 25, active: false });
  };

  // Thumbnail variant
  if (variant === "thumbnail") {
    return (
      <div
        data-testid={testid}
        onClick={onClick}
        className={`relative inline-flex items-center gap-2 rounded-lg border ${tier.frame} px-2.5 py-1.5 transition-all ${
          onClick ? "cursor-pointer hover:brightness-125" : ""
        } ${className}`}
      >
        <div className="relative size-8 shrink-0 overflow-hidden rounded-full border border-white/20 bg-black/40">
          <img
            src={imageSrc}
            alt=""
            onError={() => setImgError(true)}
            loading="lazy"
            className="size-full object-cover object-[50%_15%]"
          />
        </div>
        <div className="flex flex-col min-w-0 leading-tight">
          <div className="flex items-center gap-1.5">
            <span className={`gx-mono text-xs font-black ${tier.ratingText}`} data-testid={`${testid}-rating`}>
              {rating}
            </span>
            <span className="truncate text-xs font-bold text-white">{name}</span>
          </div>
          <span className="gx-mono text-[9px] text-slate-400">
            {posShort(position)} {club ? `· ${club}` : ""}
          </span>
        </div>
      </div>
    );
  }

  // Compact variant with 3D-Tilt Holographic Foil & Mini 6-Axis Radar
  if (variant === "compact") {
    return (
      <div
        ref={(el) => {
          cardRef.current = el;
        }}
        data-testid={testid}
        onClick={onClick}
        onPointerMove={handleMove}
        onPointerLeave={handleLeave}
        role={onClick ? "button" : undefined}
        tabIndex={onClick ? 0 : undefined}
        onKeyDown={(e) => {
          if (onClick && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            onClick();
          }
        }}
        style={{
          transformStyle: "preserve-3d",
          transform: `perspective(850px) rotateX(${holo.rx}deg) rotateY(${holo.ry}deg) scale(${holo.active ? 1.02 : 1})`,
          boxShadow: "inset 0 1px 0 rgba(255,255,255,0.18)",
        }}
        className={`group relative flex flex-col overflow-hidden rounded-2xl border ${tier.frame} p-3.5 shadow-xl transition-transform duration-100 ${
          onClick ? "cursor-pointer" : ""
        } ${className}`}
      >
        {/* Holographic Foil Glare */}
        <div
          className="pointer-events-none absolute inset-0 transition-opacity duration-200"
          style={{
            opacity: holo.active ? 0.8 : 0.28,
            background: `radial-gradient(circle at ${holo.gx}% ${holo.gy}%, rgba(229,182,63,0.35), rgba(0,201,145,0.20) 40%, transparent 72%)`,
            mixBlendMode: "screen",
          }}
        />

        <div className="relative z-10 flex items-start justify-between gap-2">
          <div className="flex flex-col leading-none">
            <span className={`gx-display text-3xl font-black ${tier.ratingText}`} data-testid={`${testid}-rating`}>
              {rating}
            </span>
            <span className="gx-mono mt-1 text-xs font-extrabold tracking-wider text-slate-200">
              {posShort(position)}
            </span>
            {potential != null && (
              <span className="gx-mono mt-1 inline-block rounded bg-[#00C991]/20 border border-[#00C991]/40 px-1.5 py-0.5 text-[10px] text-[#00E8A8] font-extrabold">
                POT {potential}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* 6-Axis Attribute Mini Radar */}
            <svg viewBox="0 0 100 100" className="h-12 w-12 shrink-0 overflow-visible opacity-85">
              <polygon
                points="50,10 85,30 85,70 50,90 15,70 15,30"
                fill="rgba(255,255,255,0.04)"
                stroke="rgba(255,255,255,0.22)"
                strokeWidth="1.2"
              />
              <polygon
                points={radarPts}
                fill="rgba(0,201,145,0.35)"
                stroke="#00C991"
                strokeWidth="2.2"
              />
            </svg>
            <div className="relative size-14 shrink-0 overflow-hidden rounded-full border-2 border-white/20 bg-[#080F1C] shadow-md">
              <img
                src={imageSrc}
                alt=""
                onError={() => setImgError(true)}
                loading="lazy"
                className="size-full object-cover object-[50%_15%] transition-transform duration-300 group-hover:scale-105"
              />
            </div>
          </div>
        </div>

        <div className="relative z-10 mt-2.5">
          <p className="gx-display truncate text-base font-black uppercase text-white tracking-wide" title={name}>
            {name}
          </p>
          <p className="truncate text-[10px] font-medium text-slate-300">
            {[nationality, club, age ? `${age}y` : null].filter(Boolean).join(" · ")}
          </p>
        </div>

        {price != null && (
          <div className="relative z-10 mt-2.5 pt-2 border-t border-white/10 flex items-center justify-between text-xs">
            <span className="text-[10px] uppercase font-bold text-slate-400">Valuation</span>
            <span className="gx-mono font-extrabold text-[#E5B63F]">{price} GTX</span>
          </div>
        )}
        {footer && <div className="relative z-10 mt-2">{footer}</div>}
      </div>
    );
  }

  // Full signature collectible 3D-Tilt Holographic player card
  const up = change != null ? change >= 0 : true;

  return (
    <article
      ref={(el) => {
        cardRef.current = el;
      }}
      data-testid={testid}
      onClick={onClick}
      onPointerMove={handleMove}
      onPointerLeave={handleLeave}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (onClick && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onClick();
        }
      }}
      style={{
        transformStyle: "preserve-3d",
        transform: `perspective(950px) rotateX(${holo.rx}deg) rotateY(${holo.ry}deg) scale(${holo.active ? 1.02 : 1})`,
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.22)",
      }}
      className={`group relative isolate flex aspect-[5/7.2] w-full max-w-[310px] flex-col overflow-hidden rounded-2xl border-2 ${tier.frame} ${tier.glow} p-4 text-white shadow-2xl transition-transform duration-100 ${
        onClick ? "cursor-pointer" : ""
      } ${className}`}
    >
      {/* Dynamic Mouse-Reactive Holographic Foil Glare */}
      <div
        className="pointer-events-none absolute inset-0 transition-opacity duration-200"
        style={{
          opacity: holo.active ? 0.85 : 0.35,
          background: `radial-gradient(circle at ${holo.gx}% ${holo.gy}%, rgba(229,182,63,0.38), rgba(0,201,145,0.22) 38%, rgba(66,185,236,0.14) 58%, transparent 74%)`,
          mixBlendMode: "screen",
        }}
      />

      {/* Decorative 6-Axis Radar Watermark in Top-Right */}
      <svg
        aria-hidden="true"
        viewBox="0 0 100 100"
        className="pointer-events-none absolute right-3 top-14 size-20 opacity-80 z-10"
      >
        <polygon
          points="50,10 85,30 85,70 50,90 15,70 15,30"
          fill="rgba(0,0,0,0.35)"
          stroke="rgba(255,255,255,0.22)"
          strokeWidth="1.2"
        />
        <polygon
          points={radarPts}
          fill="rgba(0,201,145,0.35)"
          stroke="#00C991"
          strokeWidth="2.2"
        />
      </svg>

      {/* Header bar: Tier badge & verified icons */}
      <header className="relative z-10 flex items-start justify-between">
        <div className="flex flex-col leading-none">
          <span
            className={`gx-display text-5xl sm:text-6xl font-black tracking-tight ${tier.ratingText} drop-shadow-md`}
            data-testid={`${testid}-rating`}
          >
            {rating}
          </span>
          <span className="gx-mono mt-1 text-sm font-black tracking-wider text-slate-200">
            {posShort(position)}
          </span>
          <span className="mt-1 text-[11px] font-bold tracking-widest text-slate-300 uppercase">
            {nationality || "Global"}
          </span>
        </div>

        <div className="flex flex-col items-end gap-1.5">
          <span
            className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[9px] font-black uppercase tracking-widest ${tier.badge}`}
            data-testid={testid ? `${testid}-badge` : undefined}
          >
            {numRating >= 85 ? <Star size={10} className="fill-[#E5B63F]" /> : <ShieldCheck size={10} />}
            {badge || tier.name}
          </span>
          {potential != null && (
            <span className="gx-mono rounded bg-black/60 px-2 py-0.5 text-[10px] font-bold text-[#00E8A8] border border-[#00C991]/40">
              POT {potential}
            </span>
          )}
        </div>
      </header>

      {/* Featured large player portrait */}
      <div className="relative z-0 mx-auto -mt-6 h-[46%] w-full flex items-center justify-center">
        <img
          src={imageSrc}
          alt={name}
          onError={() => setImgError(true)}
          loading="lazy"
          className="h-full max-h-48 w-auto object-contain object-bottom drop-shadow-[0_12px_24px_rgba(0,0,0,0.85)] transition-transform duration-500 group-hover:scale-105"
        />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-[#080F1C] via-[#080F1C]/60 to-transparent" />
      </div>

      {/* Identity block */}
      <div className="relative z-10 mt-auto flex flex-col text-left">
        <h3
          className="gx-display truncate max-w-full text-2xl sm:text-3xl font-black uppercase leading-none tracking-tight text-white drop-shadow-sm"
          title={name}
        >
          {name}
        </h3>
        <p className="mt-1 truncate text-xs text-slate-300 font-medium">
          {[club, age ? `${age} yrs` : null].filter(Boolean).join(" · ")}
        </p>
      </div>

      {/* Key attributes row */}
      {stats.length > 0 ? (
        <dl className="relative z-10 my-2.5 grid grid-cols-6 gap-0.5 border-y border-white/10 py-1.5 bg-black/50 rounded-lg">
          {stats.slice(0, 6).map((s) => (
            <div key={s.k} className="flex flex-col items-center">
              <dt className="text-[9px] font-bold tracking-wider text-slate-400 uppercase">{s.k}</dt>
              <dd className="gx-mono text-xs font-black text-white">{s.v}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <div className="relative z-10 my-2.5 border-y border-white/10 py-1.5 flex items-center justify-around bg-black/45 rounded-lg text-center">
          <div>
            <p className="text-[9px] font-bold tracking-wider text-slate-400 uppercase">TIER</p>
            <p className="gx-mono text-xs font-black text-[#E5B63F] uppercase">{tier.name}</p>
          </div>
          <div>
            <p className="text-[9px] font-bold tracking-wider text-slate-400 uppercase">FORM</p>
            <p className="gx-mono text-xs font-black text-[#00E8A8]">{form ?? "7.4"}</p>
          </div>
          <div>
            <p className="text-[9px] font-bold tracking-wider text-slate-400 uppercase">FOIL</p>
            <p className="gx-mono text-xs font-black text-[#42B9EC]">3D HOLO</p>
          </div>
        </div>
      )}

      {/* Footer: Market price / valuation & change */}
      {price != null || change != null ? (
        <footer className="relative z-10 flex items-end justify-between pt-1">
          {price != null && (
            <div className="flex flex-col">
              <span className="text-[9px] font-bold uppercase tracking-widest text-slate-400">Valuation</span>
              <span className="gx-display text-xl font-black leading-none text-[#E5B63F]">
                {price} <span className="gx-mono text-[10px] font-bold text-[#E5B63F]/80">GTX</span>
              </span>
            </div>
          )}
          {change != null && (
            <span
              className={`flex items-center gap-0.5 rounded px-1.5 py-0.5 gx-mono text-xs font-black ${
                up ? "bg-[#00C991]/20 text-[#00E8A8]" : "bg-red-500/20 text-red-300"
              }`}
            >
              {up ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
              {Math.abs(change).toFixed(1)}%
            </span>
          )}
        </footer>
      ) : (
        <footer className="relative z-10 flex items-center justify-between pt-1 text-[10px] text-slate-400 font-semibold">
          <span>GTEX PRO HOLO</span>
          <span className="gx-mono text-[#E5B63F]/90">#PLR-{rating}</span>
        </footer>
      )}

      {footer && <div className="relative z-10 mt-2">{footer}</div>}
    </article>
  );
}
