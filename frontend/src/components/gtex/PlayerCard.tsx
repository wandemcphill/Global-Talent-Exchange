import React from "react";
import { Sparkles } from "lucide-react";

const POS: Record<string, string> = { goalkeeper: "GK", defender: "DEF", midfielder: "MID", forward: "FWD", attacker: "FWD", gk: "GK", df: "DEF", mf: "MID", fw: "FWD", striker: "ST", winger: "W", "centre-back": "CB", "center-back": "CB", "full-back": "FB", "central midfielder": "CM", "attacking midfielder": "AM", "defensive midfielder": "DM", "centre-forward": "CF" };
export const posShort = (p?: string) => (p ? POS[p.toLowerCase()] || p.slice(0, 3).toUpperCase() : "-");

const TIERS = {
  icon: { name: "Icon", card: "from-[#3a2a06] via-[#a77f1c] to-[#1b1304] border-amber-200/70", glow: "shadow-[0_0_32px_-6px_rgba(251,191,36,0.55)]", ink: "text-amber-100" },
  gold: { name: "Gold", card: "from-[#33280a] via-[#80661c] to-[#171104] border-amber-400/50", glow: "shadow-[0_0_24px_-10px_rgba(251,191,36,0.45)]", ink: "text-amber-100" },
  silver: { name: "Silver", card: "from-[#1c232c] via-[#566273] to-[#11161c] border-slate-300/40", glow: "", ink: "text-slate-100" },
  bronze: { name: "Bronze", card: "from-[#26170d] via-[#6f4426] to-[#120a05] border-orange-400/40", glow: "", ink: "text-orange-100" },
  regen: { name: "Regen", card: "from-[#032219] via-[#0d6b4f] to-[#02110c] border-emerald-300/50", glow: "shadow-[0_0_28px_-8px_rgba(16,185,129,0.55)]", ink: "text-emerald-50" },
};

export function tierOf(rating: number, regen?: boolean) {
  if (regen) return TIERS.regen;
  if (rating >= 85) return TIERS.icon;
  if (rating >= 75) return TIERS.gold;
  if (rating >= 65) return TIERS.silver;
  return TIERS.bronze;
}

function Portrait({ image, name }: { image?: string | null; name: string }) {
  const initials = name.split(" ").map((s) => s[0]).slice(0, 2).join("");
  if (image) return <img src={image} alt={name} loading="lazy" className="h-24 w-24 object-contain drop-shadow-[0_8px_12px_rgba(0,0,0,0.6)] transition-transform duration-300 group-hover:scale-105" />;
  return <div className="flex h-20 w-20 items-center justify-center rounded-full border border-white/20 bg-black/30 font-display text-2xl font-black text-white/70">{initials}</div>;
}

export function PlayerCard({ name, rating, potential, position, age, nationality, club, image, regen, stats = [], footer, onClick, testid, badge }: any) {
  const tier = tierOf(Number(rating || 0), regen);
  return (
    <div data-testid={testid} className={`group gx-rise relative flex flex-col overflow-hidden rounded-md border bg-gradient-to-b ${tier.card} ${tier.glow} transition-transform duration-300 hover:-translate-y-1`}>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_70%_0%,rgba(255,255,255,0.18),transparent_55%)]" />
      <button type="button" onClick={onClick} disabled={!onClick} className="relative flex items-start justify-between px-4 pt-4 text-left disabled:cursor-default" data-testid={testid ? `${testid}-open` : undefined}>
        <div className={tier.ink}>
          <p className="gx-display text-4xl font-black leading-none" data-testid={testid ? `${testid}-rating` : undefined}>{rating ?? "-"}</p>
          <p className="gx-mono mt-1 text-xs font-bold tracking-widest">{posShort(position)}</p>
          {potential != null && <p className="gx-mono mt-1 text-[10px] opacity-80">POT {potential}</p>}
          <p className="mt-2 text-[9px] font-bold uppercase tracking-[0.2em] opacity-70">{tier.name}</p>
        </div>
        <Portrait image={image} name={name || "?"} />
      </button>
      <div className="relative mt-2 border-y border-white/10 bg-black/25 px-4 py-2">
        <p className="gx-display truncate text-base font-bold uppercase text-white" title={name}>{name}</p>
        <p className="truncate text-[11px] text-white/60">{[nationality, club, age ? `${age}y` : null].filter(Boolean).join(" · ")}</p>
        {(badge || regen) && (
          <span className="absolute right-3 top-2 inline-flex items-center gap-1 rounded-sm bg-black/40 px-1.5 py-0.5 text-[9px] font-bold uppercase text-emerald-200">
            {regen && <Sparkles size={10} />}{badge || "Academy"}
          </span>
        )}
      </div>
      {stats.length > 0 && (
        <div className="relative grid grid-cols-3 gap-px bg-white/5">
          {stats.slice(0, 6).map((s: any) => (
            <div key={s.k} className="bg-black/20 px-1 py-1.5 text-center sm:px-2">
              <p className="gx-mono truncate text-[11px] font-bold text-white sm:text-sm">{s.v}</p>
              <p className="text-[9px] uppercase tracking-wider text-white/50">{s.k}</p>
            </div>
          ))}
        </div>
      )}
      {footer && <div className="relative mt-auto px-3 py-3">{footer}</div>}
    </div>
  );
}
