import Image from "next/image";
import { Play } from "lucide-react";

export function NextMatch() {
  return (
    <section aria-labelledby="next-match" className="relative isolate flex min-h-72 flex-col overflow-hidden rounded-xl border border-border">
      <Image src="/stadium-night.png" alt="" fill sizes="(min-width: 1024px) 400px, 100vw" className="-z-10 object-cover object-center" />
      <div className="absolute inset-0 -z-10 bg-gradient-to-t from-background via-background/70 to-background/30" />
      <div className="flex items-center justify-between p-5">
        <h2 id="next-match" className="text-xs font-semibold uppercase tracking-[0.2em] text-foreground/80">
          Fast Cup · Quarter-final
        </h2>
        <span className="flex items-center gap-1.5 rounded-full bg-destructive px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-foreground">
          <span className="size-1.5 animate-pulse-dot rounded-full bg-foreground" aria-hidden />
          In 14:32
        </span>
      </div>
      <div className="mt-auto flex flex-col gap-4 p-5">
        <div className="flex items-center justify-between gap-3 font-display uppercase">
          <span className="text-2xl font-bold leading-none md:text-3xl">Lagos Harbour</span>
          <span className="text-lg text-muted-foreground">vs</span>
          <span className="text-right text-2xl font-bold leading-none md:text-3xl">Malmö Nord</span>
        </div>
        <button
          type="button"
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          <Play className="size-4 fill-current" aria-hidden />
          Set lineup &amp; enter matchday
        </button>
      </div>
    </section>
  );
}
