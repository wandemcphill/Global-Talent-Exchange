import React, { useState } from "react";
import { ArrowDownRight, ArrowUpRight, Award, ShieldCheck, Sparkles, Star } from "lucide-react";
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
    badge: "border-slate-500/40 bg-slate-900/80 text-slate-300",
    frame: "border-slate-700/60 bg-gradient-to-b from-[#111827] via-[#0b121e] to-[#070b11]",
    glow: "shadow-slate-950/60",
    accent: "text-slate-400",
    ratingText: "text-white",
  },
  elite: {
    name: "Elite",
    badge: "border-emerald-400/50 bg-emerald-950/70 text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.3)]",
    frame: "border-emerald-500/50 bg-gradient-to-b from-[#06241a] via-[#091b15] to-[#040e0a]",
    glow: "shadow-[0_16px_40px_rgba(16,185,129,0.22)]",
    accent: "text-emerald-400",
    ratingText: "text-emerald-300",
  },
  legendary: {
    name: "Legendary",
    badge: "border-amber-400/60 bg-amber-950/70 text-amber-300 shadow-[0_0_16px_rgba(245,158,11,0.4)]",
    frame: "border-amber-400/60 bg-gradient-to-b from-[#2a1d06] via-[#1c1407] to-[#0c0903]",
    glow: "shadow-[0_20px_50px_rgba(245,158,11,0.28)]",
    accent: "text-amber-400",
    ratingText: "text-amber-200",
  },
  regen: {
    name: "Regen",
    badge: "border-emerald-400/60 bg-emerald-950/80 text-emerald-300",
    frame: "border-emerald-500/50 bg-[#04120e]",
    glow: "shadow-[0_16px_40px_rgba(16,185,129,0.25)]",
    accent: "text-emerald-400",
    ratingText: "text-emerald-300",
  },
};

export function tierOf(rating: number, regen?: boolean): TierConfig {
  if (regen) return TIERS.regen;
  if (rating >= 85) return TIERS.legendary;
  if (rating >= 75) return TIERS.elite;
  return TIERS.standard;
}

export function resolvePlayerFallback(position?: string): string {
  const p = (position || "").toLowerCase();
  if (p.includes("gk") || p.includes("keeper")) return "/img/players/keeper.png";
  if (p.includes("def") || p.includes("cb") || p.includes("back")) return "/img/players/defender.png";
  if (p.includes("mid") || p.includes("cm") || p.includes("dm") || p.includes("am")) return "/img/players/midfielder.png";
  if (p.includes("fwd") || p.includes("st") || p.includes("wing") || p.includes("att")) return "/img/players/striker.png";
  return "/img/players/striker.png";
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
  // Extra regen passthroughs
  generation?: number | string;
  archetype?: string;
  serial?: string;
  lineage?: Array<{ label: string; detail: string }>;
  traits?: string[];
}

export function PlayerCard(props: PlayerCardProps) {
  // If explicitly flagged as regen, route to the dedicated Tactics-Board Regen collectible card
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
  const fallbackSrc = resolvePlayerFallback(position);
  const imageSrc = !imgError && image ? image : fallbackSrc;

  // Thumbnail variant (suitable for compact tables, tickers, chips)
  if (variant === "thumbnail") {
    return (
      <div
        data-testid={testid}
        onClick={onClick}
        className={`relative inline-flex items-center gap-2 rounded-md border ${tier.frame} px-2 py-1.5 transition-all ${
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

  // Compact variant (suitable for dense tactical line-ups and lists)
  if (variant === "compact") {
    return (
      <div
        data-testid={testid}
        onClick={onClick}
        role={onClick ? "button" : undefined}
        tabIndex={onClick ? 0 : undefined}
        onKeyDown={(e) => {
          if (onClick && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            onClick();
          }
        }}
        className={`group relative flex flex-col overflow-hidden rounded-xl border ${tier.frame} p-3.5 shadow-xl transition-all duration-300 ${
          onClick ? "cursor-pointer hover:-translate-y-1 hover:brightness-110" : ""
        } ${className}`}
      >
        <div className="flex items-start justify-between">
          <div className="flex flex-col leading-none">
            <span className={`gx-display text-3xl font-black ${tier.ratingText}`} data-testid={`${testid}-rating`}>
              {rating}
            </span>
            <span className="gx-mono mt-1 text-xs font-extrabold tracking-wider text-slate-300">
              {posShort(position)}
            </span>
            {potential != null && (
              <span className="gx-mono mt-0.5 text-[10px] text-emerald-400 font-bold">POT {potential}</span>
            )}
          </div>
          <div className="relative size-16 shrink-0 overflow-hidden rounded-full border-2 border-white/20 bg-slate-950/80 shadow-md">
            <img
              src={imageSrc}
              alt=""
              onError={() => setImgError(true)}
              loading="lazy"
              className="size-full object-cover object-[50%_15%] transition-transform duration-300 group-hover:scale-105"
            />
          </div>
        </div>

        <div className="mt-2.5">
          <p className="gx-display truncate text-sm font-black uppercase text-white tracking-wide" title={name}>
            {name}
          </p>
          <p className="truncate text-[10px] text-slate-400">
            {[nationality, club, age ? `${age}y` : null].filter(Boolean).join(" · ")}
          </p>
        </div>

        {price != null && (
          <div className="mt-2.5 pt-2 border-t border-white/10 flex items-center justify-between text-xs">
            <span className="text-[10px] uppercase font-bold text-slate-500">Fee / Value</span>
            <span className="gx-mono font-bold text-amber-300">{price} GTX</span>
          </div>
        )}
        {footer && <div className="mt-2">{footer}</div>}
      </div>
    );
  }

  // Full signature collectible player card
  const up = change != null ? change >= 0 : true;

  return (
    <article
      data-testid={testid}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (onClick && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onClick();
        }
      }}
      className={`group relative isolate flex aspect-[5/7.2] w-full max-w-[310px] flex-col overflow-hidden rounded-2xl border-2 ${tier.frame} ${tier.glow} p-4 text-white shadow-2xl transition-all duration-300 ${
        onClick ? "cursor-pointer hover:-translate-y-1.5 hover:shadow-2xl hover:brightness-105" : ""
      } ${className}`}
    >
      {/* Background card texture & dynamic lighting */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_70%_10%,rgba(255,255,255,0.12),transparent_60%)]" />

      {/* Decorative center-circle chalk watermark */}
      <svg
        aria-hidden="true"
        viewBox="0 0 100 100"
        className="pointer-events-none absolute -left-10 -top-10 size-40 text-white/5"
      >
        <circle cx="50" cy="50" r="44" fill="none" stroke="currentColor" strokeWidth="0.8" />
        <circle cx="50" cy="50" r="1.6" fill="currentColor" />
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
          <span className="mt-1 text-[11px] font-bold tracking-widest text-slate-400 uppercase">
            {nationality || "Global"}
          </span>
        </div>

        <div className="flex flex-col items-end gap-1.5">
          <span
            className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[9px] font-black uppercase tracking-widest ${tier.badge}`}
            data-testid={testid ? `${testid}-badge` : undefined}
          >
            {numRating >= 85 ? <Star size={10} className="fill-amber-300" /> : <ShieldCheck size={10} />}
            {badge || tier.name}
          </span>
          {potential != null && (
            <span className="gx-mono rounded bg-black/50 px-2 py-0.5 text-[10px] font-bold text-emerald-300 border border-emerald-500/30">
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
        {/* Soft bottom vignette for seamless attribute transition */}
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-slate-950 via-slate-950/60 to-transparent" />
      </div>

      {/* Identity block */}
      <div className="relative z-10 mt-auto flex flex-col text-left">
        <h3
          className="gx-display truncate max-w-full text-2xl sm:text-3xl font-black uppercase leading-none tracking-tight text-white drop-shadow-sm"
          title={name}
        >
          {name}
        </h3>
        <p className="mt-1 truncate text-xs text-slate-400 font-medium">
          {[club, age ? `${age} yrs` : null].filter(Boolean).join(" · ")}
        </p>
      </div>

      {/* Key attributes row */}
      {stats.length > 0 ? (
        <dl className="relative z-10 my-2.5 grid grid-cols-6 gap-0.5 border-y border-white/10 py-1.5 bg-black/40 rounded-sm">
          {stats.slice(0, 6).map((s) => (
            <div key={s.k} className="flex flex-col items-center">
              <dt className="text-[9px] font-bold tracking-wider text-slate-400 uppercase">{s.k}</dt>
              <dd className="gx-mono text-xs font-black text-white">{s.v}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <div className="relative z-10 my-2.5 border-y border-white/10 py-1.5 flex items-center justify-around bg-black/30 rounded-sm text-center">
          <div>
            <p className="text-[9px] font-bold tracking-wider text-slate-400 uppercase">TIER</p>
            <p className="gx-mono text-xs font-black text-amber-300 uppercase">{tier.name}</p>
          </div>
          <div>
            <p className="text-[9px] font-bold tracking-wider text-slate-400 uppercase">FORM</p>
            <p className="gx-mono text-xs font-black text-emerald-400">{form ?? "7.4"}</p>
          </div>
          <div>
            <p className="text-[9px] font-bold tracking-wider text-slate-400 uppercase">STATUS</p>
            <p className="gx-mono text-xs font-black text-slate-200">Active</p>
          </div>
        </div>
      )}

      {/* Footer: Market price / valuation & change */}
      {(price != null || change != null) ? (
        <footer className="relative z-10 flex items-end justify-between pt-1">
          {price != null && (
            <div className="flex flex-col">
              <span className="text-[9px] font-bold uppercase tracking-widest text-slate-500">Valuation</span>
              <span className="gx-display text-xl font-black leading-none text-amber-300">
                {price} <span className="gx-mono text-[10px] font-bold text-amber-400/80">GTX</span>
              </span>
            </div>
          )}
          {change != null && (
            <span
              className={`flex items-center gap-0.5 rounded px-1.5 py-0.5 gx-mono text-xs font-black ${
                up ? "bg-emerald-500/20 text-emerald-300" : "bg-red-500/20 text-red-300"
              }`}
            >
              {up ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
              {Math.abs(change).toFixed(1)}%
            </span>
          )}
        </footer>
      ) : (
        <footer className="relative z-10 flex items-center justify-between pt-1 text-[10px] text-slate-500 font-semibold">
          <span>GTEX PRO LEAGUE</span>
          <span className="gx-mono text-slate-400">#PLR-{rating}</span>
        </footer>
      )}

      {footer && <div className="relative z-10 mt-2">{footer}</div>}
    </article>
  );
}
