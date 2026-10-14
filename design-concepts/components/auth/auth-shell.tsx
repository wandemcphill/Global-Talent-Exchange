import Image from "next/image";
import Link from "next/link";
import { ConceptNav } from "@/components/concept-nav";

type AuthShellProps = {
  active: string;
  title: string;
  subtitle: string;
  children: React.ReactNode;
};

export function AuthShell({ active, title, subtitle, children }: AuthShellProps) {
  return (
    <>
      <ConceptNav active={active} />
      <div className="grid min-h-[calc(100dvh-57px)] lg:grid-cols-2">
        <aside className="relative isolate hidden overflow-hidden lg:flex">
          <Image src="/stadium-night.png" alt="" fill sizes="50vw" className="-z-10 object-cover" priority />
          <div className="absolute inset-0 -z-10 bg-gradient-to-t from-background via-background/40 to-transparent" />
          <div className="mt-auto flex flex-col gap-3 p-10">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-primary">Global Talent Exchange</p>
            <p className="font-display text-5xl font-bold uppercase leading-[0.95] text-balance">
              Scout them early. Own the story.
            </p>
            <p className="max-w-md leading-relaxed text-muted-foreground">
              Trade real player cards, develop one-of-one regens and take your club into matchday.
            </p>
          </div>
        </aside>
        <main className="flex items-center justify-center bg-turf px-4 py-12">
          <div className="flex w-full max-w-sm animate-rise flex-col gap-8">
            <header className="flex flex-col gap-2">
              <h1 className="font-display text-4xl font-bold uppercase leading-none">{title}</h1>
              <p className="text-sm leading-relaxed text-muted-foreground">{subtitle}</p>
            </header>
            {children}
          </div>
        </main>
      </div>
    </>
  );
}

export function Field({ label, type = "text", name, autoComplete }: { label: string; type?: string; name: string; autoComplete?: string }) {
  return (
    <label className="flex flex-col gap-1.5 text-sm">
      <span className="font-medium">{label}</span>
      <input
        name={name}
        type={type}
        autoComplete={autoComplete}
        required
        className="rounded-lg border border-border bg-input px-3 py-2.5 outline-none transition-shadow focus:ring-2 focus:ring-ring"
      />
    </label>
  );
}

export function AuthSwitch({ text, href, cta }: { text: string; href: string; cta: string }) {
  return (
    <p className="text-center text-sm text-muted-foreground">
      {text}{" "}
      <Link href={href} className="font-medium text-primary hover:underline">
        {cta}
      </Link>
    </p>
  );
}
