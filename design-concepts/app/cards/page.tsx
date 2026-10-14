import { ConceptNav } from "@/components/concept-nav";
import { PlayerCard } from "@/components/cards/player-card";
import { RegenCard } from "@/components/cards/regen-card";
import { players, regens } from "@/lib/data";

const rules = [
  { title: "Rating reads first", body: "OVR sits inside a chalk centre-circle at 60–72px. Nothing else on the card is that size." },
  { title: "Tier is the frame", body: "Standard: chalk line. Elite: pitch-green ring and glow. Legendary: floodlight-gold ring and gold rating." },
  { title: "Gold means money", body: "Gold is reserved for price and 1-of-1 serials, so a player's value is always findable at a glance." },
  { title: "Regens are blueprints", body: "Dashed chalk frame, portrait in the centre circle, and a hatched ceiling range — the player is still being drawn." },
];

export default function CardsPage() {
  const standard = players.find((p) => p.tier === "standard")!;
  const elite = players.find((p) => p.tier === "elite")!;
  const legendary = players.find((p) => p.tier === "legendary")!;

  return (
    <>
      <ConceptNav active="/cards" />
      <main className="mx-auto max-w-7xl px-4 py-12 md:px-8">
        <header className="flex max-w-2xl flex-col gap-3">
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-primary">Signature object</p>
          <h1 className="font-display text-5xl font-bold uppercase leading-none text-balance">Player &amp; regen cards</h1>
          <p className="leading-relaxed text-muted-foreground">
            Hover a card on desktop — it tilts and catches the floodlight. Three tiers share one layout so
            collections scan cleanly; regens get their own visual language.
          </p>
        </header>

        <section aria-label="Card tiers" className="mt-12 flex flex-wrap items-start justify-center gap-10 lg:justify-between">
          {[standard, elite, legendary].map((p) => (
            <figure key={p.id} className="flex flex-col items-center gap-3">
              <PlayerCard player={p} />
              <figcaption className="font-display text-sm font-semibold uppercase tracking-widest text-muted-foreground">
                {p.tier}
              </figcaption>
            </figure>
          ))}
          <figure className="flex flex-col items-center gap-3">
            <RegenCard regen={regens[0]} className="scale-[0.8] origin-top -mb-24" />
            <figcaption className="font-display text-sm font-semibold uppercase tracking-widest text-muted-foreground">
              Regen
            </figcaption>
          </figure>
        </section>

        <section aria-labelledby="rules" className="mt-16">
          <h2 id="rules" className="font-display text-3xl font-bold uppercase">Card rules</h2>
          <ul className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {rules.map((r) => (
              <li key={r.title} className="flex flex-col gap-2 rounded-xl border border-border bg-card p-5">
                <h3 className="font-semibold">{r.title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{r.body}</p>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </>
  );
}
