import React, { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  ArrowRight,
  Building2,
  CheckCircle2,
  CreditCard,
  Disc3,
  Globe,
  Layers,
  Lock,
  Mail,
  Megaphone,
  Music2,
  Play,
  Radio,
  ShieldCheck,
  Sparkles,
  Tv,
  Upload,
  Users,
} from "lucide-react";
import {
  AdPlacementSpec,
  AdPricingPackage,
  commercialApi,
  formatNairaMinor,
} from "@/lib/commercial/api";

export interface CommercialPublicPortalProps {
  division?: "overview" | "brands" | "music";
  initialTab?: "overview" | "brands" | "music" | "pricing" | "all" | string;
}

export default function CommercialPublicPortal({
  division,
  initialTab,
}: CommercialPublicPortalProps = {}) {
  const pathname = typeof window !== "undefined" ? window.location.pathname : "";
  const tabFromProp = initialTab || division;
  const initialFocus =
    tabFromProp === "music" || pathname.includes("/music")
      ? "music"
      : tabFromProp === "brands" || pathname.includes("/brands")
        ? "brand"
        : "all";

  const [activeTab, setActiveTab] = useState<"all" | "brand" | "music">(initialFocus);
  const [placements, setPlacements] = useState<AdPlacementSpec[]>([]);
  const [packages, setPackages] = useState<AdPricingPackage[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (tabFromProp === "music" || pathname.includes("/music")) setActiveTab("music");
    else if (tabFromProp === "brands" || pathname.includes("/brands")) setActiveTab("brand");
    else setActiveTab("all");
  }, [division, initialTab, tabFromProp, pathname]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const [pl, pkg] = await Promise.all([
          commercialApi.listPublicPlacements(),
          commercialApi.listPublicPackages(),
        ]);
        if (mounted) {
          setPlacements(pl);
          setPackages(pkg);
        }
      } catch {
        // Public page still renders static overview if backend is offline
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const brandPlacements = placements.filter((p) => p.division === "brand");
  const brandPackages = packages.filter((p) => p.division === "brand");
  const musicPackages = packages.filter((p) => p.division === "music");

  return (
    <div
      className="min-h-screen bg-[#050811] text-slate-100 selection:bg-emerald-500/30"
      data-testid="gtex-commercial-public-portal"
    >
      {/* Top Commercial Network Navigation */}
      <header className="sticky top-0 z-40 border-b border-white/10 bg-[#050811]/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-4">
            <Link to="/advertise" className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-teal-600 text-slate-950 font-black tracking-tighter shadow-lg shadow-emerald-500/20">
                GTEX
              </div>
              <div>
                <div className="text-xs font-bold uppercase tracking-[0.22em] text-emerald-400">
                  GTEX COMMERCIAL NETWORK
                </div>
                <div className="text-sm font-semibold text-white">
                  Brand Advertising &amp; Music Promotion
                </div>
              </div>
            </Link>
          </div>

          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-300">
            <Link
              to="/advertise"
              className={`transition hover:text-white ${activeTab === "all" ? "text-emerald-400 font-semibold" : ""}`}
            >
              Overview
            </Link>
            <Link
              to="/advertise/brands"
              className={`transition hover:text-white ${activeTab === "brand" ? "text-emerald-400 font-semibold" : ""}`}
            >
              Brand Advertising
            </Link>
            <Link
              to="/advertise/music"
              className={`transition hover:text-white ${activeTab === "music" ? "text-amber-400 font-semibold" : ""}`}
            >
              Music Promotion
            </Link>
            <Link to="/" className="text-slate-400 transition hover:text-slate-200">
              GTEX Platform
            </Link>
          </nav>

          <div className="flex items-center gap-3">
            <Link
              to="/advertiser/login"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-xs sm:text-sm font-semibold text-white transition hover:bg-white/10"
              data-testid="commercial-nav-login"
            >
              Advertiser Login
            </Link>
            <Link
              to="/advertiser/register"
              className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-500 px-4 py-2 text-xs sm:text-sm font-bold text-slate-950 transition hover:bg-emerald-400"
              data-testid="commercial-nav-register"
            >
              Create Advertiser Account
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden border-b border-white/10 py-16 sm:py-24">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(16,185,129,0.14),transparent_55%),radial-gradient(circle_at_bottom_left,rgba(245,158,11,0.10),transparent_50%)]" />
        <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1.5 text-xs font-bold uppercase tracking-widest text-emerald-300">
              <Sparkles className="h-3.5 w-3.5" />
              Official GTEX Commercial Network • Denominated in Nigerian Naira (₦)
            </div>
            <h1
              className="mt-6 text-4xl font-black tracking-tight text-white sm:text-6xl"
              data-testid="commercial-hero-headline"
            >
              Reach the GTEX audience.
            </h1>
            <p className="mt-5 text-lg leading-relaxed text-slate-300">
              Companies, advertising agencies, musicians, and record labels can purchase high-visibility
              brand placements and verified global audio rotation across the Global Talent Exchange ecosystem —
              with direct creative uploads, transparent Naira (NGN) billing, and genuine event-level analytics.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link
                to="/advertiser/register?type=business"
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-6 py-3.5 text-sm font-bold text-slate-950 shadow-lg shadow-emerald-500/20 transition hover:bg-emerald-400"
              >
                Launch Brand Campaign
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                to="/advertiser/register?type=music"
                className="inline-flex items-center gap-2 rounded-xl border border-amber-400/40 bg-amber-500/15 px-6 py-3.5 text-sm font-bold text-amber-200 transition hover:bg-amber-500/25"
              >
                <Music2 className="h-4 w-4" />
                Promote Your Music
              </Link>
              <Link
                to="/advertiser/register?type=agency"
                className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-5 py-3.5 text-sm font-semibold text-slate-200 transition hover:bg-white/10"
              >
                <Users className="h-4 w-4" />
                Agency Workspace
              </Link>
            </div>
          </div>

          {/* Two Primary Advertising Divisions */}
          <div className="mt-14 grid gap-8 lg:grid-cols-2">
            {/* Division 1: Brand Advertising */}
            <div
              className="flex flex-col justify-between rounded-3xl border border-emerald-500/25 bg-slate-900/75 p-8 shadow-2xl"
              data-testid="division-brand-advertising"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-2 rounded-lg bg-emerald-500/15 px-3 py-1 text-xs font-bold uppercase tracking-wider text-emerald-300">
                    <Building2 className="h-4 w-4" />
                    Division 01 • GTEX Brand Advertising
                  </span>
                  <span className="text-xs font-semibold text-slate-400">Min. 7 Days • Silent Visuals</span>
                </div>
                <h2 className="mt-4 text-2xl font-bold text-white">
                  Brand Advertising &amp; Match Broadcast Sponsorship
                </h2>
                <p className="mt-2 text-sm text-slate-300">
                  Built for companies, agencies, organisations, and corporate sponsors seeking silent,
                  broadcast-grade visibility across GTEX web, application, and live match surfaces.
                </p>

                <div className="mt-6">
                  <div className="text-xs font-bold uppercase tracking-wider text-slate-400">Designed For</div>
                  <div className="mt-2.5 flex flex-wrap gap-2">
                    {[
                      "Companies",
                      "Businesses",
                      "Advertising Agencies",
                      "Organisations",
                      "Products & Services",
                      "Corporate Sponsorships",
                    ].map((item) => (
                      <span
                        key={item}
                        className="rounded-lg border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-slate-200"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                </div>

                <ul className="mt-6 space-y-2.5 text-sm text-slate-300">
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                    Direct creative image (PNG, JPG, WebP) &amp; silent video (MP4, WebM) uploads — no external URLs
                  </li>
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                    9 centrally managed placements including Live Match Split-Screen, Halftime &amp; Stadium Perimeter
                  </li>
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                    System-calculated start &amp; end dates upon creative approval and verified NGN payment
                  </li>
                </ul>
              </div>

              <div className="mt-8 flex flex-wrap items-center gap-3 border-t border-white/10 pt-6">
                <Link
                  to="/advertiser/register?type=business"
                  className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-5 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-emerald-400"
                >
                  Start Brand Campaign
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  to="/advertise/brands"
                  className="rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-white/10"
                >
                  Explore Brand Inventory
                </Link>
              </div>
            </div>

            {/* Division 2: Music Promotion */}
            <div
              className="flex flex-col justify-between rounded-3xl border border-amber-500/25 bg-slate-900/75 p-8 shadow-2xl"
              data-testid="division-music-promotion"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-2 rounded-lg bg-amber-500/15 px-3 py-1 text-xs font-bold uppercase tracking-wider text-amber-300">
                    <Disc3 className="h-4 w-4" />
                    Division 02 • GTEX Music Promotion
                  </span>
                  <span className="text-xs font-semibold text-slate-400">7 / 21 / 30 / 42 Days • Global Audio</span>
                </div>
                <h2 className="mt-4 text-2xl font-bold text-white">
                  Global Music Player Rotation for Artists &amp; Labels
                </h2>
                <p className="mt-2 text-sm text-slate-300">
                  A dedicated, simplified audio promotion workflow that connects directly to GTEX&apos;s global
                  background music player across the Homepage, Club HQ, Halftime, and Post-Match screens.
                </p>

                <div className="mt-6">
                  <div className="text-xs font-bold uppercase tracking-wider text-slate-400">Designed For</div>
                  <div className="mt-2.5 flex flex-wrap gap-2">
                    {[
                      "Musicians",
                      "Producers",
                      "Record Labels",
                      "Independent Artists",
                      "Music Distributors & Promoters",
                    ].map((item) => (
                      <span
                        key={item}
                        className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-100"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                </div>

                <ul className="mt-6 space-y-2.5 text-sm text-slate-300">
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-amber-400" />
                    Direct MP3, WAV, OGG, M4A &amp; AAC audio upload with auto-filled track title and optional cover art
                  </li>
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-amber-400" />
                    Fair-rotation delivery inside the GTEX Global Music Player with halftime &amp; post-match resume
                  </li>
                  <li className="flex items-center gap-2.5">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-amber-400" />
                    Genuine playback metrics: started plays, qualified listens, completed listens &amp; unique listeners
                  </li>
                </ul>
              </div>

              <div className="mt-8 flex flex-wrap items-center gap-3 border-t border-white/10 pt-6">
                <Link
                  to="/advertiser/register?type=music"
                  className="inline-flex items-center gap-2 rounded-xl bg-amber-400 px-5 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-amber-300"
                >
                  Promote a Track Now
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  to="/advertise/music"
                  className="rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-white/10"
                >
                  View Music Packages
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Campaign Process Section */}
      <section className="border-b border-white/10 py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <div className="text-xs font-bold uppercase tracking-widest text-emerald-400">
                Streamlined Commercial Workflows
              </div>
              <h2 className="mt-2 text-3xl font-bold text-white">How GTEX Commercial Campaigns Work</h2>
            </div>
            <p className="max-w-xl text-sm text-slate-400">
              No manual start/end date guesswork and no external creative hosting required. Upload directly,
              complete NGN payment, and your campaign window begins automatically upon moderation approval.
            </p>
          </div>

          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                step: "Step 01",
                title: "Business or Artist Identity",
                desc: "Enter your company, agency, or artist details and upload your brand logo or cover artwork directly.",
                icon: Building2,
              },
              {
                step: "Step 02",
                title: "Select GTEX Inventory",
                desc: "Choose from 9 brand placements (Homepage, App, Live Match Panel, Halftime, Stadium) or Global Music Player Rotation.",
                icon: Layers,
              },
              {
                step: "Step 03",
                title: "Direct Creative / Audio Upload",
                desc: "Upload silent brand images/videos or master audio files directly with instant format and silent-video verification.",
                icon: Upload,
              },
              {
                step: "Step 04",
                title: "NGN Checkout & Auto-Activation",
                desc: "Pay securely in Nigerian Naira (₦) via Paystack or KoraPay. Start and end dates are calculated automatically on approval.",
                icon: CreditCard,
              },
            ].map((item) => (
              <div
                key={item.step}
                className="rounded-2xl border border-white/10 bg-slate-900/60 p-6"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-widest text-emerald-400">
                    {item.step}
                  </span>
                  <item.icon className="h-5 w-5 text-slate-400" />
                </div>
                <h3 className="mt-4 text-lg font-bold text-white">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Advertising Inventory & Formats */}
      {(activeTab === "all" || activeTab === "brand") && (
        <section className="border-b border-white/10 py-16" id="brand-inventory">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <div className="text-xs font-bold uppercase tracking-widest text-emerald-400">
                  Central Placement Registry
                </div>
                <h2 className="mt-2 text-3xl font-bold text-white">
                  Brand Advertising Inventory &amp; Specifications
                </h2>
              </div>
              <span className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1.5 text-xs font-semibold text-emerald-300">
                All Visual Placements Are Strictly Silent • Minimum 7 Days
              </span>
            </div>

            <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {(brandPlacements.length > 0
                ? brandPlacements
                : [
                    {
                      id: "1",
                      placement_key: "public_homepage",
                      name: "Public Homepage Spotlight & Banner",
                      category: "Public Website",
                      description: "High-impact silent visual placement on the public GTEX homepage.",
                      aspect_ratio: "16:9",
                      supported_media_types: ["image/png", "image/jpeg", "image/webp", "video/mp4"],
                      weekly_rate_minor_ngn: null,
                      pricing_configured: false,
                    },
                    {
                      id: "2",
                      placement_key: "live_match_panel",
                      name: "Live Match Silent Advertising Panel",
                      category: "Live Match Broadcast",
                      description: "Split-screen / side-by-side silent broadcast advertising panel during active matches.",
                      aspect_ratio: "16:9",
                      supported_media_types: ["image/png", "image/jpeg", "image/webp", "video/mp4"],
                      weekly_rate_minor_ngn: null,
                      pricing_configured: false,
                    },
                    {
                      id: "3",
                      placement_key: "halftime_sponsorship",
                      name: "Halftime Broadcast Sponsorship",
                      category: "Live Match Broadcast",
                      description: "Prominent halftime interval sponsorship showcase displayed when matches enter halftime.",
                      aspect_ratio: "16:9",
                      supported_media_types: ["image/png", "image/jpeg", "image/webp", "video/mp4"],
                      weekly_rate_minor_ngn: null,
                      pricing_configured: false,
                    },
                  ]
              ).map((pl: any) => (
                <div
                  key={pl.placement_key}
                  className="flex flex-col justify-between rounded-2xl border border-white/10 bg-slate-900/60 p-6"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="rounded-md bg-white/10 px-2.5 py-1 text-[11px] font-semibold text-slate-300">
                        {pl.category}
                      </span>
                      <span className="text-xs font-mono text-emerald-400">
                        Aspect {pl.aspect_ratio}
                      </span>
                    </div>
                    <h3 className="mt-3 text-lg font-bold text-white">{pl.name}</h3>
                    <p className="mt-1.5 text-xs leading-relaxed text-slate-400">{pl.description}</p>
                    <div className="mt-4 flex flex-wrap gap-1.5">
                      {(pl.supported_media_types || []).map((mime: string) => (
                        <span
                          key={mime}
                          className="rounded border border-white/10 bg-slate-950 px-2 py-0.5 text-[10px] font-mono text-slate-300"
                        >
                          {mime.replace("image/", "").replace("video/", "").toUpperCase()}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="mt-5 flex items-center justify-between border-t border-white/10 pt-4 text-xs">
                    <span className="text-slate-400">Weekly Rate (NGN):</span>
                    <span className="font-bold text-emerald-300">
                      {pl.pricing_configured && pl.weekly_rate_minor_ngn !== null
                        ? formatNairaMinor(pl.weekly_rate_minor_ngn)
                        : "Admin Configurable (NGN)"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* NGN Pricing & Packages Presentation */}
      <section className="border-b border-white/10 py-16" id="pricing-packages">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto">
            <div className="text-xs font-bold uppercase tracking-widest text-amber-400">
              Exclusive Nigerian Naira (₦ / NGN) Commercial Billing
            </div>
            <h2 className="mt-2 text-3xl font-bold text-white">
              Brand &amp; Music Promotion Packages
            </h2>
            <p className="mt-3 text-sm text-slate-400">
              All advertising rates, invoices, receipts, and recurring monthly subscriptions are billed
              exclusively in Nigerian Naira (NGN).
            </p>
          </div>

          <div className="mt-10 grid gap-8 lg:grid-cols-2">
            {/* Brand Packages */}
            <div className="rounded-3xl border border-white/10 bg-slate-900/50 p-6 sm:p-8">
              <h3 className="flex items-center gap-2 text-xl font-bold text-white">
                <Tv className="h-5 w-5 text-emerald-400" />
                Brand Advertising Packages (Min. 7 Days)
              </h3>
              <div className="mt-5 space-y-3">
                {(brandPackages.length > 0
                  ? brandPackages
                  : [
                      {
                        package_code: "brand_7d",
                        name: "7-Day Brand Campaign",
                        duration_days: 7,
                        description: "Minimum 7-day brand advertising campaign on selected GTEX placements.",
                        pricing_configured: false,
                        price_minor_ngn: null,
                        is_subscription: false,
                      },
                      {
                        package_code: "brand_14d",
                        name: "14-Day Multi-Week Brand Campaign",
                        duration_days: 14,
                        description: "2-week continuous brand presence across chosen GTEX commercial inventory.",
                        pricing_configured: false,
                        price_minor_ngn: null,
                        is_subscription: false,
                      },
                      {
                        package_code: "brand_30d",
                        name: "30-Day Brand Dominance Package",
                        duration_days: 30,
                        description: "Full 30-day brand campaign across web, application, and match broadcast surfaces.",
                        pricing_configured: false,
                        price_minor_ngn: null,
                        is_subscription: false,
                      },
                      {
                        package_code: "brand_monthly_sub",
                        name: "Monthly Recurring Brand Subscription",
                        duration_days: 30,
                        description: "Auto-renewing 30-day monthly brand subscription in NGN.",
                        pricing_configured: false,
                        price_minor_ngn: null,
                        is_subscription: true,
                      },
                    ]
                ).map((pkg: any) => (
                  <div
                    key={pkg.package_code}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-2xl border border-white/10 bg-slate-950/70 p-4"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white">{pkg.name}</span>
                        <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-[11px] font-semibold text-emerald-300">
                          {pkg.duration_days} Days {pkg.is_subscription ? "• Monthly" : ""}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-400">{pkg.description}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-sm font-bold text-emerald-300">
                        {pkg.pricing_configured && pkg.price_minor_ngn !== null
                          ? formatNairaMinor(pkg.price_minor_ngn)
                          : "Unconfigured (Admin NGN Rate)"}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Music Packages */}
            <div className="rounded-3xl border border-white/10 bg-slate-900/50 p-6 sm:p-8">
              <h3 className="flex items-center gap-2 text-xl font-bold text-white">
                <Radio className="h-5 w-5 text-amber-400" />
                Music Promotion Rotation Packages
              </h3>
              <div className="mt-5 space-y-3">
                {(musicPackages.length > 0
                  ? musicPackages
                  : [
                      {
                        package_code: "music_7d",
                        name: "7-Day Music Promotion",
                        duration_days: 7,
                        description: "7 days of verified promotional rotation in the GTEX Global Music Player.",
                        pricing_configured: false,
                        price_minor_ngn: null,
                        is_subscription: false,
                      },
                      {
                        package_code: "music_21d",
                        name: "21-Day Music Promotion",
                        duration_days: 21,
                        description: "21 days of verified promotional rotation across GTEX Homepage, App, Halftime & Post-Match.",
                        pricing_configured: false,
                        price_minor_ngn: null,
                        is_subscription: false,
                      },
                      {
                        package_code: "music_30d",
                        name: "30-Day Music Promotion",
                        duration_days: 30,
                        description: "30 days of high-frequency rotation in the GTEX Global Music Player.",
                        pricing_configured: false,
                        price_minor_ngn: null,
                        is_subscription: false,
                      },
                      {
                        package_code: "music_42d",
                        name: "42-Day Flagship Release Promotion",
                        duration_days: 42,
                        description: "6-week flagship single/EP rotation campaign across the GTEX Music Network.",
                        pricing_configured: false,
                        price_minor_ngn: null,
                        is_subscription: false,
                      },
                    ]
                ).map((pkg: any) => (
                  <div
                    key={pkg.package_code}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-2xl border border-white/10 bg-slate-950/70 p-4"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white">{pkg.name}</span>
                        <span className="rounded bg-amber-500/15 px-2 py-0.5 text-[11px] font-semibold text-amber-300">
                          {pkg.duration_days} Days {pkg.is_subscription ? "• Monthly" : ""}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-400">{pkg.description}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-sm font-bold text-amber-300">
                        {pkg.pricing_configured && pkg.price_minor_ngn !== null
                          ? formatNairaMinor(pkg.price_minor_ngn)
                          : "Unconfigured (Admin NGN Rate)"}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Support & Footer */}
      <footer className="py-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 rounded-2xl border border-white/10 bg-slate-900/60 p-6">
            <div>
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                <ShieldCheck className="h-5 w-5 text-emerald-400" />
                GTEX Commercial Network Support &amp; Agency Desk
              </div>
              <p className="mt-1 text-xs text-slate-400">
                Need multi-brand agency onboarding, custom stadium sponsorship packages, or NGN invoicing assistance?
                Contact the GTEX Commercial Desk at{" "}
                <a href="mailto:commercial@gtex.app" className="text-emerald-400 underline">
                  commercial@gtex.app
                </a>
                .
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Link
                to="/advertiser/login"
                className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-xs font-semibold text-white hover:bg-white/10"
              >
                Existing Advertiser Login
              </Link>
              <Link
                to="/advertiser/register"
                className="rounded-xl bg-emerald-500 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-emerald-400"
              >
                Register Advertiser Workspace
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
