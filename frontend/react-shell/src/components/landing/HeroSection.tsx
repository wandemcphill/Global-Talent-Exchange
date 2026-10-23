import React from "react";
import { Link } from "react-router-dom";
import { Shield, Sparkles, ArrowRightLeft, Trophy, ArrowRight, Globe } from "lucide-react";
import { publicUrl } from "@/lib/publicPath";
import { GtexLiveWorldPulse } from "./landingModels";

interface HeroSectionProps {
  pulse: GtexLiveWorldPulse | null;
  onExplore: () => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ pulse, onExplore }) => {
  const compactNumber = (val: number) => {
    if (val >= 1000000) return `${(val / 1000000).toFixed(1)}m`;
    if (val >= 1000) return `${(val / 1000).toFixed(val >= 10000 ? 0 : 1)}k`;
    return `${val}`;
  };

  const clubsCount = pulse?.clubsOnGtex ? compactNumber(pulse.clubsOnGtex) : "1,240+";

  return (
    <section id="hero" className="relative min-h-[92vh] overflow-hidden bg-[#0B1626] pt-[72px]">
      {/* Stadium Background Poster */}
      <img
        src={publicUrl("/img/gtex_landing_single_poster.png")}
        onError={(e) => {
          // Fallback to hero.jpg if single poster unavailable
          (e.target as HTMLImageElement).src = publicUrl("/img/hero.jpg");
        }}
        alt="GTEX Stadium Atmosphere"
        className="absolute inset-0 h-full w-full object-cover object-right opacity-35"
      />

      {/* Deep Navy Editorial Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-r from-[#0B1626] via-[#0B1626]/95 via-60% to-[#0B1626]/30" />
      <div className="gx-pitch-grid absolute inset-0 opacity-40" />

      {/* Editorial Content */}
      <div className="relative mx-auto flex max-w-[1440px] flex-col justify-center px-6 py-16 sm:px-12 lg:min-h-[calc(92vh-72px)] lg:py-24">
        <div className="max-w-3xl">
          {/* Eyebrow with living green pulse */}
          <div className="flex items-center gap-2.5">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#36E38A] opacity-75"></span>
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-[#36E38A]"></span>
            </span>
            <p className="font-['Barlow_Condensed'] text-xs sm:text-sm font-extrabold uppercase tracking-[0.2em] text-[#36E38A]">
              THE LIVING FOOTBALL UNIVERSE • 2027
            </p>
          </div>

          {/* Primary Editorial Headline */}
          <h1 className="mt-5 font-['Barlow_Condensed'] text-5xl font-black uppercase leading-[0.88] tracking-tight text-[#F2F4F8] sm:text-7xl lg:text-[100px]">
            FOOTBALL,
            <br />
            REBUILT.
          </h1>

          {/* Tagline */}
          <p className="mt-6 text-base font-bold text-[#E8C766] sm:text-xl lg:text-2xl">
            Build your club. Discover the next superstar. Compete for glory. Build your legacy.
          </p>

          {/* Mission */}
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#9AA7BD] sm:text-base">
            Own up to three clubs, hire managers, develop regens, earn TV money, trade talent and compete for prizes in one living football world.
          </p>

          {/* Conversion Calls to Action */}
          <div className="mt-10 flex flex-wrap items-center gap-4">
            <Link
              to="/signup"
              data-testid="landing-activate-club-cta"
              className="group flex items-center gap-2 rounded-lg border border-[#D4AF37] bg-[#D4AF37] px-7 py-3.5 font-['Barlow_Condensed'] text-base font-black uppercase tracking-wider text-[#0B1626] shadow-[0_0_30px_rgba(212,175,55,0.3)] transition-all duration-200 hover:bg-[#E8C766] hover:shadow-[0_0_40px_rgba(212,175,55,0.5)] active:scale-[0.98]"
            >
              <span>Create free account</span>
              <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" />
            </Link>

            <button
              onClick={onExplore}
              className="flex items-center gap-2 rounded-lg border border-[#22385A] bg-[#13233A]/80 px-6 py-3.5 font-['Barlow_Condensed'] text-base font-bold uppercase tracking-wider text-[#F2F4F8] backdrop-blur-md transition-colors hover:border-[#D4AF37]/50 hover:bg-[#1A2E4A]"
            >
              <Globe size={18} className="text-[#38BDF8]" />
              <span>Explore the universe</span>
            </button>
          </div>

          {/* Micro Badges */}
          <div className="mt-8 flex flex-wrap gap-2.5">
            {[
              { label: "Own", icon: Shield },
              { label: "Develop", icon: Sparkles },
              { label: "Trade", icon: ArrowRightLeft },
              { label: "Compete", icon: Trophy },
            ].map((badge) => (
              <div
                key={badge.label}
                className="flex items-center gap-2 rounded-md border border-[#22385A] bg-[#13233A]/70 px-3 py-1.5 backdrop-blur-sm"
              >
                <badge.icon size={13} className="text-[#D4AF37]" />
                <span className="text-xs font-bold text-[#F2F4F8]">{badge.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* World Pulse indicator tag at bottom right */}
      <div className="hidden md:flex absolute bottom-8 right-8 items-center gap-2.5 rounded-full border border-emerald-500/40 bg-[#13233A]/90 px-4 py-2 backdrop-blur-md shadow-lg">
        <span className="h-2 w-2 rounded-full bg-[#36E38A] animate-pulse"></span>
        <span className="font-['Barlow_Condensed'] text-xs font-extrabold uppercase tracking-widest text-[#F2F4F8]">
          WORLD PULSE • {clubsCount} CLUBS
        </span>
      </div>
    </section>
  );
};
