import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  Menu,
  X,
  ArrowRight,
  Globe2,
  Shield,
  Tv,
  UserSearch,
  Trophy,
  Users,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { publicUrl } from "@/lib/publicPath";
import { GtexLiveWorldPulse } from "./landingModels";

interface GtexHomeNavProps {
  pulse: GtexLiveWorldPulse | null;
  jackpotLabel?: string | null;
  onScrollToSection: (id: string) => void;
}

export const GtexHomeNav: React.FC<GtexHomeNavProps> = ({
  pulse,
  jackpotLabel,
  onScrollToSection,
}) => {
  const { user } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { label: "World", id: "world", wideOnly: false },
    { label: "Clubs", id: "ownership", wideOnly: false },
    { label: "TV Money", id: "finance", wideOnly: false },
    { label: "Regens", id: "regens", wideOnly: false },
    { label: "Tournaments", id: "competitions", wideOnly: false },
    { label: "Universe", id: "universe", wideOnly: true },
    { label: "Trust", id: "trust", wideOnly: true },
  ];

  const mobileNavItems = [
    {
      id: "world",
      Icon: Globe2,
      title: "The living world",
      subtitle: "News, milestones and broadcasts",
    },
    {
      id: "ownership",
      Icon: Shield,
      title: "Club ownership",
      subtitle: "Build your club and prestige",
    },
    {
      id: "finance",
      Icon: Tv,
      title: "TV money & club finance",
      subtitle: "Broadcast revenue and club economics",
    },
    {
      id: "regens",
      Icon: UserSearch,
      title: "Regens & player development",
      subtitle: "Discover and develop future stars",
    },
    {
      id: "competitions",
      Icon: Trophy,
      title: "Competitions & jackpots",
      subtitle: "Tournaments, rules and prize events",
    },
    {
      id: "universe",
      Icon: Users,
      title: "The wider football universe",
      subtitle: "Managers and national-team rentals",
    },
    {
      id: "trust",
      Icon: ShieldCheck,
      title: "Trust & rules",
      subtitle: "Currencies, eligibility and disclosures",
    },
  ];

  const handleNavClick = (id: string) => {
    onScrollToSection(id);
    setMobileMenuOpen(false);
  };

  const compactNumber = (val: number) => {
    if (val >= 1000000) return `${(val / 1000000).toFixed(1)}m`;
    if (val >= 1000) return `${(val / 1000).toFixed(val >= 10000 ? 0 : 1)}k`;
    return `${val}`;
  };

  return (
    <header className="fixed top-0 inset-x-0 z-50 h-[72px] border-b border-[#22385A] bg-[#0B1626]/95 backdrop-blur-md">
      <div className="mx-auto flex h-full max-w-[1440px] items-center justify-between px-4 sm:px-8">
        {/* Brand & Live Pulse Chip */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => handleNavClick("hero")}
            className="flex items-center gap-2.5 text-left transition-opacity hover:opacity-90"
          >
            <span className="font-['Barlow_Condensed'] text-2xl font-black tracking-widest text-[#F2F4F8]">
              GTEX
            </span>
            <span className="hidden sm:inline-block rounded border border-[#D4AF37]/40 bg-[#D4AF37]/10 px-2 py-0.5 font-['Barlow_Condensed'] text-xs font-bold tracking-wider text-[#D4AF37]">
              2027
            </span>
          </button>

          {pulse && pulse.usersOnline > 0 && (
            <div className="hidden sm:flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-semibold text-emerald-400">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-[#36E38A]"></span>
              </span>
              <span>{compactNumber(pulse.usersOnline)} live</span>
            </div>
          )}

          {jackpotLabel && (
            <div className="hidden lg:flex items-center gap-1.5 rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 font-['JetBrains_Mono'] text-[11px] font-bold text-[#E8C766]">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400"></span>
              <span>{jackpotLabel}</span>
            </div>
          )}
        </div>

        {/* Desktop Navigation Links */}
        <nav className="hidden lg:flex items-center gap-6">
          {navLinks.map((link) => (
            <button
              key={link.id}
              onClick={() => handleNavClick(link.id)}
              className={`${link.wideOnly ? "hidden xl:inline-block" : ""} text-xs font-semibold uppercase tracking-wider text-[#9AA7BD] transition-colors hover:text-[#F2F4F8]`}
            >
              {link.label}
            </button>
          ))}
        </nav>

        {/* Auth Affordance & Primary Action */}
        <div className="flex items-center gap-3">
          <Link
            to={user ? "/app" : "/login"}
            data-testid="landing-login-link"
            className="px-3.5 py-2 text-xs font-bold uppercase tracking-wider text-[#9AA7BD] transition-colors hover:text-white"
          >
            {user ? "Open console" : "Sign in"}
          </Link>
          <Link
            to="/signup"
            data-testid="landing-nav-signup"
            className="flex items-center gap-1.5 rounded-md border border-[#D4AF37] bg-[#D4AF37] px-4 py-2 text-xs font-extrabold uppercase tracking-wider text-[#0B1626] shadow-[0_0_20px_rgba(212,175,55,0.25)] transition-[transform,background-color] hover:bg-[#E8C766] active:scale-[0.98]"
          >
            Enter GTEX
          </Link>

          {/* Mobile hamburger toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden p-2 text-[#9AA7BD] hover:text-white"
            aria-label="Open homepage navigation"
          >
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-b border-[#22385A] bg-[#0B1626] px-6 py-6 shadow-2xl">
          <p className="font-['Barlow_Condensed'] text-xs font-extrabold uppercase tracking-[0.15em] text-[#D4AF37]">
            Explore GTEX
          </p>
          <p className="mt-2 text-[13px] leading-snug text-[#9AA7BD]">
            Your football world, one destination at a time.
          </p>
          <div className="mt-4 divide-y divide-[#22385A] border-t border-[#22385A]">
            {mobileNavItems.map(({ id, Icon, title, subtitle }) => (
              <button
                key={id}
                onClick={() => handleNavClick(id)}
                className="flex w-full items-center gap-3 py-2.5 text-left hover:bg-[#13233A]/60"
              >
                <span className="flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-[10px] border border-[#22385A] bg-[#1A2E4A] text-[#D4AF37]">
                  <Icon size={19} />
                </span>
                <span className="flex-1">
                  <span className="block text-sm font-bold text-[#F2F4F8]">{title}</span>
                  <span className="block text-[11px] text-[#6B7A93]">{subtitle}</span>
                </span>
                <ArrowRight size={14} className="text-[#6B7A93]" />
              </button>
            ))}
          </div>

          <div className="mt-6 flex flex-col gap-2 pt-4 border-t border-[#22385A]">
            <Link
              to={user ? "/app" : "/signup"}
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center justify-center gap-2 rounded-lg bg-[#D4AF37] py-2.5 text-xs font-extrabold uppercase tracking-wider text-[#0B1626]"
            >
              Enter GTEX <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      )}
    </header>
  );
};
