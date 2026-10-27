import React, { useState } from "react";
import { Dna, Sparkles, TrendingUp, ShieldCheck } from "lucide-react";
import { posShort } from "./PlayerCard";

export interface RegenData {
  id?: string;
  name: string;
  rating?: number | string;
  currentRating?: number | string;
  potential?: number | string;
  potentialLow?: number;
  potentialHigh?: number;
  position?: string;
  age?: number | string;
  nationality?: string;
  nationalityCode?: string;
  club?: string;
  image?: string | null;
  generation?: number | string;
  archetype?: string;
  serial?: string;
  price?: number | string;
  change?: number;
  lineage?: Array<{ label: string; detail: string }>;
  traits?: string[];
  stats?: Array<{ k: string; v: string | number }>;
  badge?: string;
}

export interface RegenCardProps {
  regen?: RegenData | boolean | null;
  name?: string;
  rating?: number | string;
  potential?: number | string;
  position?: string;
  age?: number | string;
  nationality?: string;
  nationalityCode?: string;
  club?: string;
  image?: string | null;
  generation?: number | string;
  archetype?: string;
  serial?: string;
  price?: number | string;
  change?: number;
  lineage?: Array<{ label: string; detail: string }>;
  traits?: string[];
  stats?: Array<{ k: string; v: string | number }>;
  badge?: string;
  variant?: "full" | "compact" | "thumbnail";
  onClick?: () => void;
  testid?: string;
  className?: string;
  footer?: React.ReactNode;
}

export function resolveRegenFallback(position?: string): string {
  const p = (position || "").toLowerCase();
  if (p.includes("gk") || p.includes("keeper")) return "/img/players/keeper.png";
  if (p.includes("def") || p.includes("cb") || p.includes("back")) return "/img/players/defender.png";
  if (p.includes("mid") || p.includes("cm") || p.includes("dm") || p.includes("am")) return "/img/players/midfielder.png";
  if (p.includes("fwd") || p.includes("st") || p.includes("wing") || p.includes("att")) return "/img/players/striker.png";
  return "/img/players/regen.png";
}

export function formatGtexCoin(val?: number | string): string {
  if (val == null || val === "") return "-";
  const num = typeof val === "string" ? parseFloat(val) : val;
  if (isNaN(num)) return String(val);
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(2)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toLocaleString();
}

export function RegenPotentialBar({ current, low, high }: { current: number; low: number; high: number }) {
  const min = 40;
  const span = Math.max(1, 99 - min);
  const pct = (v: number) => `${Math.max(0, Math.min(100, ((v - min) / span) * 100))}%`;
  const currPct = pct(current);
  const lowPct = pct(low);
  const highPct = pct(high);

  return (
    <div className="relative mt-3 flex flex-col gap-1 w-full" aria-label={`Current: ${current}, Potential Ceiling: ${low}-${high}`}>
      <div className="flex items-baseline justify-between text-[10px] font-semibold tracking-wider text-emerald-300/80">
        <span className="flex items-center gap-1">
          CURRENT <span className="gx-mono text-sm font-black text-white">{current}</span>
        </span>
        <span className="flex items-center gap-1">
          CEILING <span className="gx-mono text-sm font-black text-amber-300">{low === high ? high : `${low}–${high}`}</span>
        </span>
      </div>
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-slate-900/80 border border-emerald-500/20">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)] transition-all duration-500"
          style={{ width: currPct }}
        />
        <div
          className="absolute inset-y-0 rounded-full opacity-70"
          style={{
            left: lowPct,
            width: `calc(${highPct} - ${lowPct})`,
            background: "repeating-linear-gradient(135deg, #f59e0b 0 3px, transparent 3px 6px)",
          }}
        />
      </div>
    </div>
  );
}

export function RegenCard(props: RegenCardProps) {
  const r: Partial<RegenData> = (typeof props.regen === "object" && props.regen !== null) ? props.regen : {};
  const name = props.name || r.name || "Prospect Regen";
  const rating = Number(props.rating ?? r.rating ?? r.currentRating ?? 68);
  const potential = Number(props.potential ?? r.potential ?? Math.min(99, rating + 14));
  const low = r.potentialLow ?? Math.max(rating, potential - 3);
  const high = r.potentialHigh ?? Math.max(low, potential + 3);
  const position = props.position || r.position || "MID";
  const age = props.age ?? r.age ?? 17;
  const nationality = props.nationality || r.nationality || "Global Academy";
  const club = props.club || r.club || "GTEX Academy";
  const generation = props.generation ?? r.generation ?? 1;
  const archetype = props.archetype || r.archetype || "Tactical Prospect";
  const serial = props.serial || r.serial || `RGN-${generation}-${Math.floor(1000 + (rating * 17) % 9000)}`;
  const price = props.price ?? r.price;
  const rawImage = props.image ?? r.image;
  const variant = props.variant || "full";
  const testid = props.testid || "regen-card";

  const [imgError, setImgError] = useState(false);
  const fallbackSrc = resolveRegenFallback(position);
  const imageSrc = !imgError && rawImage ? rawImage : fallbackSrc;

  // Thumbnail variant (dense table/avatar view)
  if (variant === "thumbnail") {
    return (
      <div
        data-testid={testid}
        onClick={props.onClick}
        className={`relative inline-flex items-center gap-2 rounded-md border border-emerald-500/40 bg-[#061812] px-2 py-1.5 transition-all ${
          props.onClick ? "cursor-pointer hover:border-emerald-400 hover:bg-[#09221a]" : ""
        } ${props.className || ""}`}
      >
        <div className="relative size-8 shrink-0 overflow-hidden rounded-full border border-emerald-400/60 bg-emerald-950/80">
          <img
            src={imageSrc}
            alt=""
            onError={() => setImgError(true)}
            loading="lazy"
            className="size-full object-cover"
          />
        </div>
        <div className="flex flex-col leading-tight min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="gx-mono text-xs font-black text-emerald-300">{rating}</span>
            <span className="truncate text-xs font-bold text-white">{name}</span>
          </div>
          <span className="gx-mono text-[9px] text-emerald-400/80">{posShort(position)} · Gen {generation}</span>
        </div>
      </div>
    );
  }

  // Compact variant (grid card)
  if (variant === "compact") {
    return (
      <div
        data-testid={testid}
        onClick={props.onClick}
        role={props.onClick ? "button" : undefined}
        tabIndex={props.onClick ? 0 : undefined}
        onKeyDown={(e) => {
          if (props.onClick && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            props.onClick();
          }
        }}
        className={`group relative flex flex-col overflow-hidden rounded-xl border border-emerald-500/35 bg-[#051310] p-3 shadow-lg shadow-black/40 transition-all duration-300 ${
          props.onClick ? "cursor-pointer hover:-translate-y-1 hover:border-emerald-400 hover:shadow-emerald-950/50" : ""
        } ${props.className || ""}`}
      >
        {/* Chalk border dashed overlay */}
        <div className="pointer-events-none absolute inset-1.5 rounded-lg border border-dashed border-emerald-400/20" />

        <div className="relative flex items-center justify-between">
          <span className="inline-flex items-center gap-1 rounded bg-emerald-950/80 px-1.5 py-0.5 text-[9px] font-black uppercase tracking-wider text-emerald-300 border border-emerald-500/30">
            <Dna size={10} className="text-emerald-400" /> GEN {generation}
          </span>
          <span className="gx-mono text-[10px] font-bold text-amber-300/90">1 of 1</span>
        </div>

        <div className="relative mt-2 flex items-center gap-3">
          <div className="relative size-16 shrink-0 overflow-hidden rounded-full border-2 border-emerald-400/70 bg-emerald-950 shadow-inner">
            <img
              src={imageSrc}
              alt=""
              onError={() => setImgError(true)}
              loading="lazy"
              className="size-full object-cover object-[50%_15%] transition-transform duration-300 group-hover:scale-105"
            />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline gap-1.5">
              <span className="gx-display text-2xl font-black leading-none text-emerald-400">{rating}</span>
              <span className="gx-mono text-xs font-bold text-slate-300">{posShort(position)}</span>
            </div>
            <p className="gx-display truncate text-sm font-black uppercase text-white tracking-wide">{name}</p>
            <p className="truncate text-[10px] text-emerald-200/60">{archetype} · {age}y</p>
          </div>
        </div>

        <RegenPotentialBar current={rating} low={low} high={high} />

        {price != null && (
          <div className="relative mt-2 pt-2 border-t border-emerald-500/20 flex items-center justify-between text-xs">
            <span className="text-[10px] uppercase font-bold text-slate-400">Value</span>
            <span className="gx-mono font-bold text-amber-300">{formatGtexCoin(price)} <span className="text-[10px] text-amber-400/70">GTX</span></span>
          </div>
        )}
        {props.footer && <div className="mt-2">{props.footer}</div>}
      </div>
    );
  }

  // Full signature collectible card (tactics board blueprint)
  return (
    <article
      data-testid={testid}
      onClick={props.onClick}
      role={props.onClick ? "button" : undefined}
      tabIndex={props.onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (props.onClick && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          props.onClick();
        }
      }}
      className={`group relative isolate flex aspect-[5/7.2] w-full max-w-[310px] flex-col overflow-hidden rounded-2xl border-2 border-emerald-500/40 bg-[#04120e] p-4 text-white shadow-2xl shadow-black/60 transition-all duration-300 ${
        props.onClick ? "cursor-pointer hover:-translate-y-1.5 hover:border-emerald-400 hover:shadow-[0_20px_50px_rgba(5,150,105,0.25)]" : ""
      } ${props.className || ""}`}
    >
      {/* Tactical pitch markings background */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_50%_0%,rgba(16,185,129,0.18),transparent_70%)]" />
      <div className="pointer-events-none absolute inset-2.5 rounded-xl border border-dashed border-emerald-400/30" />

      {/* Subtle pitch center circle mark */}
      <svg
        aria-hidden="true"
        viewBox="0 0 100 100"
        className="pointer-events-none absolute left-1/2 top-28 -translate-x-1/2 size-48 text-emerald-500/15"
      >
        <circle cx="50" cy="50" r="46" fill="none" stroke="currentColor" strokeWidth="0.75" strokeDasharray="3 3" />
        <circle cx="50" cy="50" r="2" fill="currentColor" />
      </svg>

      {/* Header bar */}
      <header className="relative z-10 flex items-center justify-between">
        <span className="flex items-center gap-1.5 rounded-md border border-emerald-400/40 bg-emerald-950/70 px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.16em] text-emerald-300 backdrop-blur-sm">
          <Dna size={12} className="text-emerald-400" />
          REGEN · GEN {generation}
        </span>
        <span className="flex items-center gap-1 rounded-full border border-amber-400/50 bg-amber-950/50 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-300">
          <Sparkles size={10} /> 1 OF 1
        </span>
      </header>

      {/* Centerpiece tactical portrait ring */}
      <div className="relative z-10 mx-auto mt-3 grid size-32 place-items-center">
        {/* Radar / coordinate accents */}
        <div className="absolute inset-0 rounded-full border border-dashed border-emerald-400/40 animate-[spin_40s_linear_infinite]" />
        <div className="relative size-28 overflow-hidden rounded-full border-2 border-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.35)] bg-emerald-950">
          <img
            src={imageSrc}
            alt={name}
            onError={() => setImgError(true)}
            loading="lazy"
            className="size-full object-cover object-[50%_15%] transition-transform duration-500 group-hover:scale-108"
          />
        </div>
        <span className="gx-mono absolute -bottom-1.5 rounded bg-emerald-500 px-2.5 py-0.5 text-xs font-black uppercase tracking-wider text-slate-950 shadow-md">
          {posShort(position)}
        </span>
      </div>

      {/* Player identity block */}
      <div className="relative z-10 mt-3 flex flex-col items-center text-center">
        <h3 className="gx-display truncate max-w-full text-2xl font-black uppercase tracking-tight text-white drop-shadow-sm" title={name}>
          {name}
        </h3>
        <p className="mt-0.5 text-[11px] font-medium text-emerald-200/70">
          {archetype} · {age}y · {nationality}
        </p>
        <p className="text-[10px] text-slate-400 truncate max-w-full">{club}</p>
      </div>

      {/* Potential ceiling progression bar */}
      <div className="relative z-10 px-1 mt-1">
        <RegenPotentialBar current={rating} low={low} high={high} />
      </div>

      {/* Lineage & DNA traits */}
      <div className="relative z-10 mt-2.5 flex-1 flex flex-col justify-center border-l-2 border-dashed border-emerald-500/30 pl-2.5 py-1 text-left space-y-1">
        <div className="flex items-baseline gap-2 text-[11px]">
          <span className="w-14 shrink-0 text-[9px] font-bold uppercase tracking-widest text-slate-400">Class</span>
          <span className="truncate text-emerald-100 font-medium">{archetype}</span>
        </div>
        <div className="flex items-baseline gap-2 text-[11px]">
          <span className="w-14 shrink-0 text-[9px] font-bold uppercase tracking-widest text-slate-400">Lineage</span>
          <span className="truncate text-emerald-100 font-medium">{nationality} Founding Cohort</span>
        </div>
        <div className="flex items-baseline gap-2 text-[11px]">
          <span className="w-14 shrink-0 text-[9px] font-bold uppercase tracking-widest text-slate-400">Status</span>
          <span className="truncate text-amber-300 font-semibold flex items-center gap-1">
            <ShieldCheck size={11} /> Verified Unique Asset
          </span>
        </div>
      </div>

      {/* Footer: Serial & Valuation */}
      <footer className="relative z-10 mt-auto pt-2 border-t border-emerald-500/25 flex items-end justify-between">
        <div className="flex flex-col">
          <span className="text-[9px] font-bold uppercase tracking-widest text-slate-400">Asset Serial</span>
          <span className="gx-mono text-[10px] tracking-wider text-emerald-300/80 font-bold">{serial}</span>
        </div>
        {price != null && (
          <div className="flex flex-col items-end">
            <span className="text-[9px] font-bold uppercase tracking-widest text-slate-400">Valuation</span>
            <span className="gx-display text-xl font-black leading-none text-amber-300">
              {formatGtexCoin(price)} <span className="gx-mono text-xs font-bold text-amber-400/80">GTX</span>
            </span>
          </div>
        )}
      </footer>

      {props.footer && <div className="relative z-10 mt-2">{props.footer}</div>}
    </article>
  );
}
