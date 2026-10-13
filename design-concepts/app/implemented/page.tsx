import type { Metadata } from "next";
import Image from "next/image";
import { ConceptNav } from "@/components/concept-nav";

export const metadata: Metadata = {
  title: "Implemented — GTEX Floodlit",
  description: "Real renders of the Flutter screens on the Floodlit branch.",
};

const screens = [
  { name: "Player & regen cards", file: "cards", desktop: [1440, 900] as const },
  { name: "Dashboard (Command Center)", file: "dashboard" },
  { name: "Player discovery (Transfer desk)", file: "discover" },
  { name: "Login", file: "login" },
  { name: "Signup", file: "signup" },
];

function Shot({ src, alt, w, h, mobile }: { src: string; alt: string; w: number; h: number; mobile?: boolean }) {
  return (
    <figure className={mobile ? "flex w-full max-w-[260px] flex-col gap-2" : "flex min-w-0 flex-1 flex-col gap-2"}>
      <figcaption className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
        {mobile ? "Mobile 390" : `Desktop ${w}`}
      </figcaption>
      <a href={src} target="_blank" rel="noreferrer" className="overflow-hidden rounded-lg border border-border">
        <Image src={src} alt={alt} width={w} height={h} className="h-auto w-full" unoptimized />
      </a>
    </figure>
  );
}

export default function ImplementedPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <ConceptNav active="/implemented" />
      <main className="mx-auto flex max-w-7xl flex-col gap-14 px-4 py-10 md:px-8">
        <header className="flex flex-col gap-3">
          <p className="font-mono text-xs uppercase tracking-widest text-primary">Rendered from frontend/lib</p>
          <h1 className="font-sans text-4xl font-bold uppercase text-balance md:text-6xl">What&apos;s actually built</h1>
          <p className="max-w-2xl leading-relaxed text-pretty text-muted-foreground">
            These are not mockups. Each image is the real Flutter widget tree from the{" "}
            <code className="font-mono text-foreground">v0/gtex-design-concepts</code> branch, rendered by{" "}
            <code className="font-mono text-foreground">test/screenshots/floodlit_capture_test.dart</code> with the
            bundled fonts and fixture data. Click any image to open it full size.
          </p>
        </header>

        {screens.map((s) => (
          <section key={s.file} className="flex flex-col gap-4" aria-labelledby={`h-${s.file}`}>
            <h2 id={`h-${s.file}`} className="font-sans text-2xl font-bold uppercase">
              {s.name}
            </h2>
            {s.desktop ? (
              <Shot src={`/implemented/${s.file}.png`} alt={`${s.name} render`} w={s.desktop[0]} h={s.desktop[1]} />
            ) : (
              <div className="flex flex-col gap-6 md:flex-row md:items-start">
                <Shot src={`/implemented/${s.file}-desktop.png`} alt={`${s.name} desktop render`} w={1440} h={1000} />
                <Shot src={`/implemented/${s.file}-mobile.png`} alt={`${s.name} mobile render`} w={390} h={844} mobile />
              </div>
            )}
          </section>
        ))}
      </main>
    </div>
  );
}
