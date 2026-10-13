import Image from "next/image";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { formatCoin, type Player, type Tier } from "@/lib/data";
import { cn } from "@/lib/utils";
import { Tilt } from "./tilt";

const tierStyles: Record<Tier, { ring: string; label: string; badge: string; glow: string }> = {
  standard: {
    ring: "ring-1 ring-foreground/15",
    label: "Standard",
    badge: "bg-foreground/10 text-foreground",
    glow: "",
  },
  elite: {
    ring: "ring-1 ring-primary/60",
    label: "Elite",
    badge: "bg-primary text-primary-foreground",
    glow: "shadow-[0_24px_60px_-20px_color-mix(in_oklab,var(--primary)_55%,transparent)]",
  },
  legendary: {
    ring: "ring-2 ring-accent",
    label: "Legendary",
    badge: "bg-accent text-accent-foreground",
    glow: "shadow-[0_28px_70px_-18px_color-mix(in_oklab,var(--accent)_60%,transparent)]",
  },
};

const attrOrder = ["PAC", "SHO", "PAS", "DRI", "DEF", "PHY"] as const;

type PlayerCardProps = {
  player: Player;
  size?: "md" | "lg";
  className?: string;
};

export function PlayerCard({ player, size = "md", className }: PlayerCardProps) {
  const tier = tierStyles[player.tier];
  const up = player.change >= 0;

  return (
    <Tilt className={cn("rounded-xl", className)}>
      <article
        aria-label={`${player.name}, ${player.position}, overall ${player.ovr}`}
        className={cn(
          "relative isolate flex aspect-[5/7] flex-col overflow-hidden rounded-xl bg-card",
          tier.ring,
          tier.glow,
          size === "lg" ? "w-80" : "w-64",
        )}
      >
        {/* Portrait */}
        <div className="absolute inset-x-0 top-0 h-[66%]">
          <Image
            src={player.image}
            alt=""
            fill
            sizes="320px"
            className="object-cover object-[50%_12%]"
            priority={size === "lg"}
          />
          <div className="absolute inset-0 bg-gradient-to-b from-card/10 via-transparent to-card" />
        </div>

        {/* Centre-circle chalk mark behind the rating */}
        <svg
          aria-hidden
          viewBox="0 0 100 100"
          className="absolute -left-10 -top-10 size-40 text-foreground/20"
        >
          <circle cx="50" cy="50" r="44" fill="none" stroke="currentColor" strokeWidth="0.8" />
          <circle cx="50" cy="50" r="1.6" fill="currentColor" />
        </svg>

        <header className="relative flex items-start justify-between p-4">
          <div className="flex flex-col leading-none">
            <span
              className={cn(
                "font-display font-extrabold",
                size === "lg" ? "text-7xl" : "text-6xl",
                player.tier === "legendary" ? "text-accent" : "text-foreground",
              )}
            >
              {player.ovr}
            </span>
            <span className="font-display text-xl font-semibold tracking-wide text-foreground/90">
              {player.position}
            </span>
            <span className="mt-1 text-[11px] font-semibold tracking-widest text-foreground/70">
              {player.nation}
            </span>
          </div>
          <span
            className={cn(
              "rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest",
              tier.badge,
            )}
          >
            {tier.label}
          </span>
        </header>

        <div className="relative mt-auto flex flex-col gap-3 p-4">
          <div className="flex flex-col">
            <h3
              className={cn(
                "font-display font-bold uppercase leading-none text-balance",
                size === "lg" ? "text-4xl" : "text-3xl",
              )}
            >
              {player.shortName}
            </h3>
            <p className="mt-1 truncate text-xs text-muted-foreground">{player.club}</p>
          </div>

          <dl className="grid grid-cols-6 gap-1 border-y border-foreground/10 py-2">
            {attrOrder.map((key) => (
              <div key={key} className="flex flex-col items-center">
                <dt className="text-[9px] font-semibold tracking-widest text-muted-foreground">
                  {key}
                </dt>
                <dd className="font-display text-lg font-bold leading-tight">
                  {player.attrs[key]}
                </dd>
              </div>
            ))}
          </dl>

          <div className="flex items-end justify-between">
            <div className="flex flex-col">
              <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                Price
              </span>
              <span className="font-display text-2xl font-bold leading-none text-accent">
                {formatCoin(player.price)}
                <span className="ml-1 text-xs font-semibold text-accent/70">GTX</span>
              </span>
            </div>
            <span
              className={cn(
                "flex items-center gap-0.5 rounded-md px-1.5 py-0.5 font-display text-base font-bold",
                up ? "bg-primary/15 text-primary" : "bg-destructive/15 text-destructive",
              )}
            >
              {up ? <ArrowUpRight className="size-4" aria-hidden /> : <ArrowDownRight className="size-4" aria-hidden />}
              {Math.abs(player.change).toFixed(1)}%
              <span className="sr-only">{up ? "up" : "down"} today</span>
            </span>
          </div>
        </div>
      </article>
    </Tilt>
  );
}
