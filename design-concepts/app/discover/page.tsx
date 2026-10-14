import Image from "next/image";
import { AppShell } from "@/components/app-shell";
import { DiscoverBoard } from "@/components/discover/discover-board";
import { players } from "@/lib/data";

export const metadata = { title: "Discover — GTEX Concepts" };

export default function DiscoverPage() {
  const spotlight = players[0];
  return (
    <AppShell active="/discover">
      <div className="flex flex-col gap-8">
        <section aria-labelledby="spotlight" className="relative isolate flex min-h-64 overflow-hidden rounded-xl border border-border">
          <Image src={spotlight.image} alt={spotlight.name} fill sizes="100vw" className="-z-10 object-cover object-[70%_20%]" priority />
          <div className="absolute inset-0 -z-10 bg-gradient-to-r from-background via-background/85 to-transparent" />
          <div className="flex max-w-md flex-col justify-end gap-2 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Scout spotlight</p>
            <h1 id="spotlight" className="font-display text-5xl font-bold uppercase leading-none">
              {spotlight.name}
            </h1>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {spotlight.watchers.toLocaleString()} managers watching · 4 goals in his last 5 · price up {spotlight.change}% today.
            </p>
          </div>
        </section>
        <DiscoverBoard />
      </div>
    </AppShell>
  );
}
