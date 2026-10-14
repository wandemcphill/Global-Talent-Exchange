import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { ConceptNav } from "@/components/concept-nav";
import { PlayerCard } from "@/components/cards/player-card";
import { RegenCard } from "@/components/cards/regen-card";
import { players, regens } from "@/lib/data";

const findings = [
  {
    area: "Design system",
    problem:
      "Two competing palettes (AppColors neon volt vs. GtexColors) and four type families — Barlow Condensed, Inter, DM Mono, plus DM Sans hard-coded inside the player card.",
    fix: "One token set, two families: Barlow Condensed for numbers and names, Inter for everything else.",
  },
  {
    area: "Player card",
    problem:
      "A 2,100-line widget with three layouts and dozens of props. Rating, price, form, badges and chips compete at the same weight, so nothing reads first.",
    fix: "One hierarchy: rating → name → six attributes → price. Tier is expressed by the frame, not by more chips.",
  },
  {
    area: "Regen card",
    problem:
      "Regen violet (#E040FB) is the same value as the admin role colour, and the DNA watermark renders at 5.5% opacity — the regen identity is effectively invisible.",
    fix: "Regens become a chalk ‘blueprint’: a projection still being drawn, with a visible potential range and lineage.",
  },
  {
    area: "Home dashboard",
    problem:
      "A 4,300-line home screen that surfaces developer diagnostics (API host, runtime, sync rail) next to the user's portfolio.",
    fix: "A command center with one question per zone: what am I worth, what's on next, what should I do.",
  },
  {
    area: "Auth",
    problem:
      "Login and signup share a generic form shell that could belong to any product; role choice for creators is buried in fields.",
    fix: "Floodlit split screen with the product promise on one side; signup chooses a role first, then asks for details.",
  },
  {
    area: "Information architecture",
    problem: "30 screens, several duplicated as _v2 variants, so the same task has two entry points.",
    fix: "Retire v1 screens; a five-item nav: Home, Discover, Market, Club, Match.",
  },
];

export default function AuditPage() {
  return (
    <>
      <ConceptNav active="/" />
      <main className="bg-turf">
        <section className="mx-auto grid max-w-7xl items-center gap-12 px-4 py-14 md:px-8 lg:grid-cols-[1.1fr_1fr] lg:py-20">
          <div className="flex animate-rise flex-col gap-6">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-primary">
              GTEX UI/UX audit · Floodlit direction
            </p>
            <h1 className="font-display text-5xl font-bold uppercase leading-[0.95] text-balance md:text-7xl">
              Every screen should feel like the moment the floodlights come on.
            </h1>
            <p className="max-w-xl leading-relaxed text-muted-foreground text-pretty">
              Global Talent Exchange is a football talent market: you trade player cards, scout and develop
              regens, run a club and watch matches. The current app has the features but not the stage. This
              concept rebuilds the surfaces around one signature object — the card.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link
                href="/cards"
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-3 font-medium text-primary-foreground transition-opacity hover:opacity-90"
              >
                See the cards <ArrowRight className="size-4" aria-hidden />
              </Link>
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 rounded-lg border border-border px-5 py-3 font-medium transition-colors hover:bg-muted"
              >
                Command center
              </Link>
            </div>
          </div>
          <div className="flex items-center justify-center gap-6">
            <div className="hidden translate-y-8 -rotate-3 sm:block">
              <RegenCard regen={regens[0]} />
            </div>
            <div className="rotate-2">
              <PlayerCard player={players[0]} size="lg" />
            </div>
          </div>
        </section>

        <section aria-labelledby="findings" className="mx-auto max-w-7xl px-4 pb-20 md:px-8">
          <h2 id="findings" className="font-display text-3xl font-bold uppercase">
            What we found
          </h2>
          <ul className="mt-6 grid gap-px overflow-hidden rounded-xl border border-border bg-border md:grid-cols-2 lg:grid-cols-3">
            {findings.map((f) => (
              <li key={f.area} className="flex flex-col gap-3 bg-card p-6">
                <h3 className="font-display text-xl font-bold uppercase tracking-wide">{f.area}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{f.problem}</p>
                <p className="mt-auto border-t border-border pt-3 text-sm leading-relaxed">
                  <span className="font-semibold text-primary">Proposal: </span>
                  {f.fix}
                </p>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </>
  );
}
