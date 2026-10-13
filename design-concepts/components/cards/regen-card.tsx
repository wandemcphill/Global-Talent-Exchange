import Image from "next/image";
import { Dna } from "lucide-react";
import { formatCoin, type Regen } from "@/lib/data";
import { cn } from "@/lib/utils";
import { Tilt } from "./tilt";

type RegenCardProps = {
  regen: Regen;
  className?: string;
};

/**
 * Regens are drawn as a tactics-board "blueprint": chalk dashes instead of a
 * photo frame, because the player is a projection still being written.
 */
export function RegenCard({ regen, className }: RegenCardProps) {
  const [low, high] = regen.ceiling;

  return (
    <Tilt className={cn("rounded-xl", className)} intensity={8}>
      <article
        aria-label={`Regen ${regen.name}, ${regen.position}, current ${regen.current}, potential ${low} to ${high}`}
        className="relative isolate flex aspect-[5/7] w-80 flex-col overflow-hidden rounded-xl bg-card bg-turf p-5 ring-1 ring-foreground/15"
      >
        <div
          aria-hidden
          className="chalk-dash pointer-events-none absolute inset-2.5 rounded-lg [--chalk-c:color-mix(in_oklab,var(--foreground)_28%,transparent)]"
        />

        <header className="relative flex items-center justify-between">
          <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.2em] text-foreground/80">
            <Dna className="size-3.5 text-primary" aria-hidden />
            Regen · Gen {regen.generation}
          </span>
          <span className="rounded-full border border-accent/50 px-2 py-0.5 font-display text-xs font-semibold tracking-wider text-accent">
            1 of 1
          </span>
        </header>

        {/* Portrait sits inside the centre circle */}
        <div className="relative mx-auto mt-4 grid size-36 place-items-center">
          <svg aria-hidden viewBox="0 0 100 100" className="absolute inset-0 size-full text-foreground/35">
            <circle cx="50" cy="50" r="48" fill="none" stroke="currentColor" strokeWidth="0.8" strokeDasharray="3 3" />
          </svg>
          <div className="relative size-28 overflow-hidden rounded-full ring-2 ring-primary/70">
            <Image src={regen.image} alt="" fill sizes="112px" className="object-cover object-[50%_20%]" />
          </div>
          <span className="absolute -bottom-1 rounded-md bg-primary px-2 py-0.5 font-display text-sm font-bold text-primary-foreground">
            {regen.position}
          </span>
        </div>

        <div className="relative mt-5 flex flex-col items-center text-center">
          <h3 className="font-display text-3xl font-bold uppercase leading-none text-balance">
            {regen.name}
          </h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {regen.archetype} · {regen.age} · {regen.nation}
          </p>
        </div>

        <PotentialBar current={regen.current} low={low} high={high} />

        <ol className="relative mt-4 flex flex-col gap-1.5 border-l border-dashed border-foreground/25 pl-3">
          {regen.lineage.map((item) => (
            <li key={item.label} className="flex items-baseline gap-2 text-xs">
              <span className="w-16 shrink-0 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                {item.label}
              </span>
              <span className="truncate text-foreground/90">{item.detail}</span>
            </li>
          ))}
        </ol>

        <footer className="relative mt-auto flex items-end justify-between pt-3">
          <span className="font-mono text-[10px] tracking-wider text-accent/80">{regen.serial}</span>
          <span className="font-display text-xl font-bold leading-none text-accent">
            {formatCoin(regen.price)}
            <span className="ml-1 text-[10px] text-accent/70">GTX</span>
          </span>
        </footer>
      </article>
    </Tilt>
  );
}

function PotentialBar({ current, low, high }: { current: number; low: number; high: number }) {
  const min = 40;
  const span = 99 - min;
  const pct = (v: number) => `${((v - min) / span) * 100}%`;

  return (
    <div className="relative mt-5 flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
          Now
          <span className="ml-1.5 font-display text-lg text-foreground">{current}</span>
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
          Ceiling
          <span className="ml-1.5 font-display text-lg text-accent">
            {low}–{high}
          </span>
        </span>
      </div>
      <div className="relative h-2 rounded-full bg-foreground/10" role="img" aria-label={`Current rating ${current}, projected ceiling ${low} to ${high}`}>
        <div className="absolute inset-y-0 left-0 rounded-full bg-primary" style={{ width: pct(current) }} />
        <div
          className="absolute inset-y-0 rounded-full bg-[repeating-linear-gradient(135deg,var(--accent)_0_3px,transparent_3px_6px)]"
          style={{ left: pct(low), width: `calc(${pct(high)} - ${pct(low)})` }}
        />
      </div>
    </div>
  );
}
