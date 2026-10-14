"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { PlayerCard } from "@/components/cards/player-card";
import { RegenCard } from "@/components/cards/regen-card";
import { players, regens } from "@/lib/data";
import { cn } from "@/lib/utils";

const positions = ["All", "GK", "DEF", "MID", "FWD", "Regens"] as const;
type Filter = (typeof positions)[number];

const group: Record<string, Filter> = { GK: "GK", CB: "DEF", CM: "MID", ST: "FWD" };

export function DiscoverBoard() {
  const [filter, setFilter] = useState<Filter>("All");
  const [query, setQuery] = useState("");

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return players.filter(
      (p) =>
        (filter === "All" || group[p.position] === filter) &&
        (!q || p.name.toLowerCase().includes(q) || p.club.toLowerCase().includes(q)),
    );
  }, [filter, query]);

  const showRegens = filter === "All" || filter === "Regens";

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-3 md:flex-row md:items-center">
        <label className="flex flex-1 items-center gap-2 rounded-lg bg-input px-3 py-2.5 focus-within:ring-2 focus-within:ring-ring">
          <Search className="size-4 text-muted-foreground" aria-hidden />
          <span className="sr-only">Search players or clubs</span>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search players, clubs, nations"
            className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
        </label>
        <div role="group" aria-label="Filter by position" className="flex gap-1 overflow-x-auto">
          {positions.map((pos) => (
            <button
              key={pos}
              type="button"
              aria-pressed={filter === pos}
              onClick={() => setFilter(pos)}
              className={cn(
                "whitespace-nowrap rounded-lg px-3.5 py-2 font-display text-sm font-semibold uppercase tracking-wider transition-colors",
                filter === pos ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              {pos}
            </button>
          ))}
        </div>
      </div>

      <p className="text-sm text-muted-foreground" aria-live="polite">
        {visible.length + (showRegens ? regens.length : 0)} results
      </p>

      <div className="flex flex-wrap justify-center gap-8 sm:justify-start">
        {filter !== "Regens" && visible.map((p) => <PlayerCard key={p.id} player={p} />)}
        {showRegens && regens.map((r) => <RegenCard key={r.id} regen={r} className="w-64 [&>article]:w-64" />)}
      </div>
    </div>
  );
}
