import React from "react";
import { publicUrl } from "@/lib/publicPath";

export type IntroAudience = "member" | "trader";

const FILMS: Record<
  IntroAudience,
  { src: string; eyebrow: string; title: string; caption: string; testId: string }
> = {
  member: {
    src: "/videos/gtex-user-introduction.mp4?v=20261119-gtexfc",
    eyebrow: "For club owners",
    title: "How a GTEX member starts",
    caption:
      "GTEX FC from login through the kit, the grant, the coin quote, the manager, the dressing room, and the free cups.",
    testId: "intro-video-member",
  },
  trader: {
    src: "/videos/gtex-coin-trader-introduction.mp4",
    eyebrow: "For coin traders",
    title: "How a coin trader earns",
    caption:
      "Wholesale at ₦50, your own buy and sell prices, the ₦200,000 minimum, escrow, and the referral.",
    testId: "intro-video-trader",
  },
};

export function ProductIntroVideo({ audience }: { audience: IntroAudience }) {
  const film = FILMS[audience];
  return (
    <figure
      className="overflow-hidden rounded-2xl border border-white/10 bg-[#070B11]"
      data-testid={film.testId}
    >
      <video
        className="aspect-video w-full bg-black"
        controls
        playsInline
        preload="metadata"
        src={publicUrl(film.src)}
      >
        {film.title}
      </video>
      <figcaption className="space-y-1 px-4 py-3">
        <p className="text-[10px] font-black uppercase tracking-[0.18em] text-emerald-300">
          {film.eyebrow}
        </p>
        <p className="text-sm font-bold text-white">{film.title}</p>
        <p className="text-xs leading-5 text-slate-400">{film.caption}</p>
      </figcaption>
    </figure>
  );
}

export function LandingIntroVideos() {
  return (
    <section
      className="relative mx-auto max-w-[1440px] px-6 pb-2 pt-8 sm:px-12"
      data-testid="landing-intro-videos"
      aria-labelledby="landing-intro-videos-title"
    >
      <p className="font-['Barlow_Condensed'] text-xs font-extrabold uppercase tracking-[0.2em] text-[#36E38A]">
        Watch before you join
      </p>
      <h2
        id="landing-intro-videos-title"
        className="mt-2 font-['Barlow_Condensed'] text-3xl font-black uppercase tracking-tight text-white sm:text-5xl"
      >
        See GTEX in a few minutes
      </h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-[#9AA7BD]">
        One film for members who want a club. One film for coin traders who run a desk.
      </p>
      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <ProductIntroVideo audience="member" />
        <ProductIntroVideo audience="trader" />
      </div>
    </section>
  );
}
