import { ArrowUpRight } from "lucide-react";
import { formatCoin } from "@/lib/data";

const points = [12, 14, 13, 17, 16, 19, 22, 21, 24, 23, 27, 31, 29, 33, 36];

export function PortfolioHero() {
  const max = Math.max(...points);
  const min = Math.min(...points);
  const path = points
    .map((v, i) => {
      const x = (i / (points.length - 1)) * 100;
      const y = 40 - ((v - min) / (max - min)) * 36 - 2;
      return `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");

  return (
    <section aria-labelledby="portfolio" className="relative overflow-hidden rounded-xl border border-border bg-card bg-turf p-6">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div className="flex flex-col gap-1">
          <h2 id="portfolio" className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Squad value
          </h2>
          <p className="font-display text-6xl font-bold leading-none text-accent md:text-7xl">
            {formatCoin(18342.6)}
            <span className="ml-2 text-xl text-accent/70">GTX</span>
          </p>
          <p className="flex items-center gap-1 text-sm text-primary">
            <ArrowUpRight className="size-4" aria-hidden />
            +1,204.30 (7.0%) this week
          </p>
        </div>
        <dl className="flex gap-8">
          {[
            { k: "Cards", v: "23" },
            { k: "Regens", v: "4" },
            { k: "Club rank", v: "#312" },
          ].map((s) => (
            <div key={s.k} className="flex flex-col">
              <dt className="text-[11px] uppercase tracking-widest text-muted-foreground">{s.k}</dt>
              <dd className="font-display text-3xl font-bold">{s.v}</dd>
            </div>
          ))}
        </dl>
      </div>
      <svg viewBox="0 0 100 40" preserveAspectRatio="none" className="mt-6 h-24 w-full" role="img" aria-label="Squad value over the last 15 days, trending up">
        <defs>
          <linearGradient id="fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="var(--primary)" stopOpacity="0.35" />
            <stop offset="1" stopColor="var(--primary)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={`${path} L100,40 L0,40 Z`} fill="url(#fill)" />
        <path d={path} fill="none" stroke="var(--primary)" strokeWidth="1.2" vectorEffect="non-scaling-stroke" />
      </svg>
    </section>
  );
}
