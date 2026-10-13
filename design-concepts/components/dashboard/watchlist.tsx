import Image from "next/image";
import { formatCoin, players } from "@/lib/data";

export function Watchlist() {
  return (
    <section aria-labelledby="watchlist" className="rounded-xl border border-border bg-card">
      <header className="flex items-center justify-between border-b border-border px-5 py-4">
        <h2 id="watchlist" className="font-display text-xl font-bold uppercase">Watchlist</h2>
        <a href="/discover" className="text-sm text-primary hover:underline">See all</a>
      </header>
      <ul className="divide-y divide-border">
        {players.map((p) => {
          const up = p.change >= 0;
          return (
            <li key={p.id} className="flex items-center gap-4 px-5 py-3">
              <div className="relative size-10 shrink-0 overflow-hidden rounded-full bg-muted">
                <Image src={p.image} alt="" fill sizes="40px" className="object-cover object-[50%_15%]" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{p.name}</p>
                <p className="text-xs text-muted-foreground">
                  {p.position} · {p.club}
                </p>
              </div>
              <span className="hidden w-10 text-center font-display text-2xl font-bold sm:block">{p.ovr}</span>
              <div className="flex w-24 flex-col items-end">
                <span className="font-display text-lg font-bold text-accent">{formatCoin(p.price)}</span>
                <span className={`text-xs ${up ? "text-primary" : "text-destructive"}`}>
                  {up ? "+" : "-"}
                  {Math.abs(p.change).toFixed(1)}%
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
