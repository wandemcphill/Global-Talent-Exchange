import { ChevronRight, Dna, Gavel, Users } from "lucide-react";

const actions = [
  { icon: Gavel, title: "Offer on Moreira expires", meta: "742.10 GTX · 2h left", tone: "text-accent" },
  { icon: Dna, title: "Mensah-Boateng ready to train", meta: "+3 OVR projected", tone: "text-primary" },
  { icon: Users, title: "Lineup has 1 injured starter", meta: "Lindqvist · hamstring", tone: "text-destructive" },
];

export function ActionQueue() {
  return (
    <section aria-labelledby="actions" className="rounded-xl border border-border bg-card">
      <h2 id="actions" className="border-b border-border px-5 py-4 font-display text-xl font-bold uppercase">
        Needs you
      </h2>
      <ul className="divide-y divide-border">
        {actions.map(({ icon: Icon, title, meta, tone }) => (
          <li key={title}>
            <button type="button" className="flex w-full items-center gap-3 px-5 py-3.5 text-left transition-colors hover:bg-muted">
              <span className={`grid size-9 shrink-0 place-items-center rounded-lg bg-muted ${tone}`}>
                <Icon className="size-4" aria-hidden />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">{title}</span>
                <span className="block text-xs text-muted-foreground">{meta}</span>
              </span>
              <ChevronRight className="size-4 text-muted-foreground" aria-hidden />
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
