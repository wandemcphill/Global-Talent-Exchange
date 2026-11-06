import React, { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  Award,
  BookOpen,
  Building,
  Bus,
  CalendarDays,
  CheckCircle2,
  Copy,
  ExternalLink,
  Flame,
  Globe,
  Lock,
  MapPin,
  Palette,
  School,
  Share2,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Trophy,
  Users,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { API, api } from "@/lib/api";
import { Cinema3DStage } from "@/components/gtex/Cinema3DStage";

export type PublicPlayerSummary = {
  id: string;
  name: string;
  position: string;
  age?: number | null;
  rating?: number | null;
  potential?: number | null;
  is_regen?: boolean;
  portrait_url?: string | null;
};

export type PublicStaffMember = {
  role: string;
  title: string;
  name?: string | null;
  rating?: number | null;
  appointed: boolean;
};

export type PublicCoachBus = {
  name: string;
  category: string;
  catalog_price?: string | null;
  edition_number?: number | null;
  preview_file?: string | null;
  fallback_label?: string | null;
  supply_cap?: number | null;
};

export type PublicTrophy = {
  id: string;
  name: string;
  competition: string;
  season?: string | null;
  position?: number;
};

export type PublicOwnerDossier = {
  id: string;
  display_name: string;
  club_count: number;
  public_clubs: Array<{
    id: string;
    name: string;
    short_name?: string | null;
    slug?: string | null;
    city?: string | null;
    country_code?: string | null;
    crest_url?: string | null;
    primary_color?: string | null;
    secondary_color?: string | null;
  }>;
  net_worth?: string | null;
  net_worth_currency?: string;
  luxury_asset_count: number;
  profile_path?: string;
};

export type PublicClubDossier = {
  club: {
    id: string;
    name: string;
    short_name?: string | null;
    slug?: string | null;
    description?: string | null;
    crest_url?: string | null;
    primary_color?: string | null;
    secondary_color?: string | null;
    accent_color?: string | null;
    country_code?: string | null;
    region_name?: string | null;
    city_name?: string | null;
    founded_year?: number | null;
    home_venue_name?: string | null;
  };
  owner: PublicOwnerDossier;
  stadium: {
    name: string;
    level?: number | null;
    capacity?: number | null;
    theme_key?: string | null;
    image_asset?: string | null;
  };
  facilities: {
    training_level?: number | null;
    academy_level?: number | null;
    medical_level?: number | null;
    branding_level?: number | null;
    youth_recruitment_level?: number | null;
    academy_image_asset?: string | null;
  };
  academy: {
    level?: number | null;
    capacity?: number | null;
    prospect_count: number;
    prospects: Array<{
      id: string;
      name: string;
      position: string;
      age: number;
      potential: number;
      portrait_url?: string | null;
    }>;
  };
  squad: {
    player_count: number;
    players: PublicPlayerSummary[];
    best_player?: PublicPlayerSummary | null;
    most_promising_player?: PublicPlayerSummary | null;
  };
  staff: PublicStaffMember[];
  coach_buses: PublicCoachBus[];
  trophies: PublicTrophy[];
};

function crestSource(reference?: string | null) {
  if (!reference) return null;
  if (/^(https?:|data:)/i.test(reference)) return reference;
  const apiOrigin = API.replace(/\/api\/?$/, "");
  if (reference.startsWith("/api/")) return `${apiOrigin}${reference}`;
  if (reference.startsWith("api/")) return `${apiOrigin}/${reference}`;
  if (reference.startsWith("/")) return reference;
  return `${API}/media/${reference.replace(/^\/+/, "")}`;
}

function formatGtx(raw?: string | number | null, currency = "GTX") {
  if (raw === null || raw === undefined || raw === "") return "Not disclosed";
  const num = typeof raw === "string" ? parseFloat(raw) : raw;
  if (isNaN(num)) return `${raw} ${currency}`;
  if (Math.abs(num) >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M ${currency}`;
  if (Math.abs(num) >= 1_000) return `${(num / 1_000).toFixed(1)}K ${currency}`;
  return `${num.toLocaleString()} ${currency}`;
}

function placementBadge(position?: number) {
  if (position === 1) return { label: "Champions", tone: "bg-amber-400 text-slate-950" };
  if (position === 2) return { label: "Runners-up", tone: "bg-slate-300 text-slate-950" };
  if (position === 3) return { label: "Third place", tone: "bg-amber-700 text-white" };
  if (position) return { label: `Rank #${position}`, tone: "bg-slate-800 text-slate-300" };
  return { label: "Honour", tone: "bg-amber-500/20 text-amber-300" };
}

function normalizePositionGroup(position?: string | null): "GK" | "DEF" | "MID" | "FWD" | "OTHER" {
  const p = (position || "").toUpperCase().trim();
  if (p === "GK" || p.includes("GOAL")) return "GK";
  if (["CB", "LB", "RB", "LWB", "RWB", "DEF", "DEFENDER"].some((k) => p.startsWith(k))) return "DEF";
  if (["CM", "DM", "AM", "LM", "RM", "MID", "MIDFIELDER"].some((k) => p.startsWith(k))) return "MID";
  if (["ST", "CF", "LW", "RW", "FW", "FWD", "FORWARD", "STRIKER", "WINGER"].some((k) => p.startsWith(k))) return "FWD";
  return "OTHER";
}

export default function PublicClubProfile() {
  const { clubSlug } = useParams<{ clubSlug: string }>();
  const [crestFailed, setCrestFailed] = useState(false);
  const [positionFilter, setPositionFilter] = useState<string>("ALL");
  const [ownerModalOpen, setOwnerModalOpen] = useState(false);

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery<PublicClubDossier>({
    queryKey: ["public-club-profile", clubSlug],
    queryFn: async () => {
      try {
        const res = await api.get(`/api/clubs/${encodeURIComponent(clubSlug || "")}/public-profile`);
        return res.data;
      } catch (err: any) {
        // Fallback to legacy showroom if the club is indexed by code or older showroom route
        try {
          const legacyRes = await api.get(`/owner/public/showroom/${encodeURIComponent(clubSlug || "")}`);
          const legacy = legacyRes.data;
          return {
            club: {
              id: legacy.club_id || clubSlug || "",
              name: legacy.club_name,
              short_name: legacy.short_name,
              slug: clubSlug,
              description: legacy.description,
              crest_url: legacy.crest_url,
              primary_color: legacy.primary_color,
              secondary_color: legacy.secondary_color,
              country_code: legacy.country_code,
              city_name: legacy.city,
              founded_year: legacy.founded,
              home_venue_name: legacy.home_venue_name,
            },
            owner: {
              id: legacy.owner_user_id || "",
              display_name: legacy.owner_name || "GTEX Club Owner",
              club_count: 1,
              public_clubs: [],
              luxury_asset_count: 0,
            },
            stadium: {
              name: legacy.home_venue_name || `${legacy.club_name} Arena`,
              level: 1,
              capacity: 25000,
            },
            facilities: {
              training_level: 1,
              academy_level: 1,
              medical_level: 1,
              branding_level: 1,
              youth_recruitment_level: 1,
            },
            academy: {
              level: 1,
              capacity: 24,
              prospect_count: 0,
              prospects: [],
            },
            squad: {
              player_count: 0,
              players: [],
              best_player: null,
              most_promising_player: null,
            },
            staff: [
              { role: "manager", title: "Manager", name: legacy.manager_name || null, appointed: Boolean(legacy.manager_name) },
              { role: "general_manager", title: "General Manager", name: null, appointed: false },
              { role: "head_of_youth_development", title: "Head of Youth Development", name: null, appointed: false },
              { role: "coach", title: "First-Team Coach", name: null, appointed: false },
            ],
            coach_buses: [],
            trophies: (legacy.trophies || []).map((t: any, idx: number) => ({
              id: `trophy-${idx}`,
              name: t.competition,
              competition: t.competition,
              season: t.year ? String(t.year) : undefined,
              position: t.position,
            })),
          };
        } catch {
          throw err;
        }
      }
    },
    enabled: Boolean(clubSlug),
    retry: false,
    staleTime: 30_000,
  });

  React.useEffect(() => {
    setCrestFailed(false);
  }, [data?.club?.crest_url]);

  const handleShare = () => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(window.location.href);
      toast.success("Public club profile link copied to clipboard!");
    } else {
      toast.info(window.location.href);
    }
  };

  if (isLoading) {
    return (
      <main className="min-h-screen bg-[#070B11] px-5 py-28 text-center text-slate-400" data-testid="public-club-loading">
        <div className="mx-auto mb-4 size-10 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
        <p className="gx-eyebrow text-emerald-400">GTEX Club Profile Archive</p>
        <p className="mt-2 text-sm text-slate-300">Loading verified public club dossier…</p>
      </main>
    );
  }

  if (isError || !data) {
    const status = (error as any)?.response?.status;
    const isPrivate = status === 404 || status === 403;
    const title = isPrivate ? "This public profile isn't published" : "We couldn't load this club";
    const description = isPrivate
      ? "This club may be set to private by its owner, or the URL slug is not registered in the GTEX world."
      : "The public profile service did not return a usable dossier. No simulated data has been substituted.";
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#070B11] px-5 py-16" data-testid="public-club-error">
        <section className="w-full max-w-xl rounded-2xl border border-white/10 bg-slate-900/80 p-8 text-center shadow-2xl backdrop-blur-md">
          {isPrivate ? (
            <Lock className="mx-auto mb-4 text-amber-400" size={38} />
          ) : (
            <ShieldCheck className="mx-auto mb-4 text-rose-400" size={38} />
          )}
          <p className="gx-eyebrow text-slate-400">GTEX · Public Club Dossier</p>
          <h1 className="gx-display mt-3 text-3xl font-bold uppercase text-white">{title}</h1>
          <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-slate-400">{description}</p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <button className="gx-btn gx-btn-secondary" onClick={() => refetch()} disabled={isFetching}>
              {isFetching ? "Retrying…" : "Try again"}
            </button>
            <Link to="/" className="gx-btn gx-btn-primary">
              GTEX Home <ArrowRight size={14} />
            </Link>
          </div>
        </section>
      </main>
    );
  }

  const { club, owner, stadium, facilities, academy, squad, staff, coach_buses, trophies } = data;
  const crest = crestSource(club.crest_url);
  const location = [club.city_name, club.region_name, club.country_code].filter(Boolean).join(" · ");
  const primary = club.primary_color || "#0F766E";
  const secondary = club.secondary_color || "#F8FAFC";
  const accent = club.accent_color || "#F59E0B";

  const allPlayers = squad?.players || [];
  const filteredPlayers =
    positionFilter === "ALL"
      ? allPlayers
      : allPlayers.filter((p) => normalizePositionGroup(p.position) === positionFilter);

  return (
    <main className="min-h-screen bg-[#070B11] text-slate-200" data-testid="public-club-profile-view">
      {/* 1. HERO & IDENTITY */}
      <header className="relative isolate overflow-hidden border-b border-white/10">
        <img
          src="/console/img/showroom/arena_imperiale_stadium.webp"
          alt="GTEX stadium architecture"
          className="absolute inset-0 -z-20 h-full min-h-[580px] w-full object-cover object-center"
        />
        <div className="absolute inset-0 -z-10 bg-gradient-to-r from-[#070B11] via-[#070B11]/92 to-[#070B11]/60" />
        <div className="absolute inset-0 -z-10 bg-gradient-to-t from-[#070B11] via-transparent to-[#070B11]/60" />

        <div className="mx-auto max-w-[1380px] px-5 pb-16 pt-6 sm:px-8 lg:px-12 lg:pb-20">
          <nav className="flex items-center justify-between gap-4">
            <Link to="/" className="gx-display text-2xl font-black tracking-tight text-white" aria-label="GTEX home">
              GTEX<span className="text-emerald-400">.</span>
            </Link>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleShare}
                className="gx-btn gx-btn-secondary text-xs flex items-center gap-1.5"
                title="Share club profile"
              >
                <Share2 size={13} />
                <span className="hidden sm:inline">Share</span>
              </button>
              <Link to="/login" className="gx-btn gx-btn-primary text-xs flex items-center gap-1.5">
                <span>Enter World</span>
                <ExternalLink size={13} />
              </Link>
            </div>
          </nav>

          <div className="mt-12 flex max-w-5xl flex-col items-start gap-7 sm:mt-16 sm:flex-row sm:items-end">
            {/* Crest / Monogram */}
            <div
              className="flex size-32 shrink-0 items-center justify-center overflow-hidden rounded-2xl border-2 bg-slate-950/85 p-3 shadow-2xl backdrop-blur-md sm:size-40"
              style={{ borderColor: primary }}
            >
              {crest && !crestFailed ? (
                <img
                  src={crest}
                  alt={`${club.name} crest`}
                  className="h-full w-full object-contain"
                  onError={() => setCrestFailed(true)}
                />
              ) : (
                <span className="gx-display text-4xl font-black" style={{ color: secondary }}>
                  {(club.short_name || club.name).slice(0, 3).toUpperCase()}
                </span>
              )}
            </div>

            <div className="min-w-0 flex-1">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/20 px-3 py-0.5 text-xs font-bold text-emerald-300 border border-emerald-500/30">
                  <ShieldCheck size={14} /> Official Public Profile
                </span>
                <span className="rounded-full bg-white/10 px-2.5 py-0.5 text-xs font-mono text-slate-300">
                  {club.short_name || club.name.slice(0, 4).toUpperCase()}
                </span>
              </div>

              <h1 className="gx-display max-w-3xl break-words text-4xl font-black uppercase leading-[0.92] tracking-tight text-white sm:text-6xl lg:text-7xl">
                {club.name}
              </h1>

              {club.description && (
                <p className="mt-4 max-w-2xl text-sm leading-relaxed text-slate-300">
                  {club.description}
                </p>
              )}

              <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-xs sm:text-sm text-slate-300">
                {location && (
                  <span className="inline-flex items-center gap-1.5">
                    <MapPin size={15} className="text-emerald-400" /> {location}
                  </span>
                )}
                {club.founded_year && (
                  <span className="inline-flex items-center gap-1.5">
                    <CalendarDays size={15} className="text-amber-400" /> Founded {club.founded_year}
                  </span>
                )}
                {stadium?.name && (
                  <span className="inline-flex items-center gap-1.5">
                    <Building size={15} className="text-cyan-400" /> {stadium.name}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* KEY METRICS BAR */}
          <div className="mt-10 grid grid-cols-2 gap-3 sm:grid-cols-4 max-w-4xl">
            <div className="border-l-2 border-emerald-400 bg-black/40 px-4 py-3 backdrop-blur-sm rounded-r-lg">
              <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Senior Squad</p>
              <p className="gx-display mt-0.5 text-2xl font-bold text-white">{squad?.player_count || 0}</p>
              <p className="text-[11px] text-slate-400">Registered players</p>
            </div>
            <div className="border-l-2 border-cyan-400 bg-black/40 px-4 py-3 backdrop-blur-sm rounded-r-lg">
              <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Academy Talent</p>
              <p className="gx-display mt-0.5 text-2xl font-bold text-white">{academy?.prospect_count || 0}</p>
              <p className="text-[11px] text-slate-400">Active prospects</p>
            </div>
            <div className="border-l-2 border-amber-400 bg-black/40 px-4 py-3 backdrop-blur-sm rounded-r-lg">
              <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Trophies & Honours</p>
              <p className="gx-display mt-0.5 text-2xl font-bold text-white">{trophies?.length || 0}</p>
              <p className="text-[11px] text-slate-400">Recorded finishes</p>
            </div>
            <div className="border-l-2 border-purple-400 bg-black/40 px-4 py-3 backdrop-blur-sm rounded-r-lg">
              <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Home Ground</p>
              <p className="gx-display mt-0.5 text-2xl font-bold text-white">
                {stadium?.level ? `Level ${stadium.level}` : "Verified"}
              </p>
              <p className="text-[11px] text-slate-400">{stadium?.capacity ? `${stadium.capacity.toLocaleString()} seats` : "Match arena"}</p>
            </div>
          </div>
        </div>
      </header>

      {/* 2. PRIVACY NOTICE / HONEST BADGING */}
      <div className="bg-slate-900/60 border-b border-white/5 py-2.5 px-5 sm:px-8 lg:px-12">
        <div className="mx-auto max-w-[1380px] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span className="size-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="font-semibold text-slate-300">Public Dossier:</span>
            <span>All records shown are approved for public sporting reference. Internal wages, ledgers and confidential notes remain sealed.</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="size-3.5 rounded-full border border-white/20" style={{ backgroundColor: primary }} title="Primary" />
            <span className="size-3.5 rounded-full border border-white/20" style={{ backgroundColor: secondary }} title="Secondary" />
            <span className="size-3.5 rounded-full border border-white/20" style={{ backgroundColor: accent }} title="Accent" />
            <span className="font-mono text-[10px] text-slate-500 uppercase">Colours</span>
          </div>
        </div>
      </div>

      {/* 3. MAIN CONTENT GRID */}
      <div className="mx-auto max-w-[1380px] px-5 py-12 sm:px-8 lg:px-12 lg:py-16 space-y-16">

        {/* SECTION A: STADIUM FEATURE */}
        <section aria-labelledby="stadium-heading">
          <div className="mb-4">
            <p className="gx-eyebrow text-cyan-400">The Home Ground</p>
            <h2 id="stadium-heading" className="gx-display text-3xl font-bold uppercase text-white">
              Stadium & Matchday Atmosphere
            </h2>
          </div>

          <div className="grid gap-6 lg:grid-cols-12 rounded-2xl border border-white/10 bg-slate-900/50 overflow-hidden shadow-xl">
            <div className="lg:col-span-5 relative min-h-[220px]">
              <img
                src="/console/img/showroom/arena_imperiale_stadium.webp"
                alt={stadium?.name || "Club stadium"}
                className="h-full w-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/30 to-transparent lg:bg-gradient-to-r lg:from-transparent lg:to-slate-900/80" />
              <div className="absolute bottom-4 left-4">
                <span className="rounded bg-black/60 px-2 py-1 text-xs font-mono font-bold text-cyan-300 border border-cyan-400/30 backdrop-blur-sm">
                  {stadium?.theme_key ? `Theme: ${stadium.theme_key}` : "Arena Architecture"}
                </span>
              </div>
            </div>

            <div className="lg:col-span-7 p-6 sm:p-8 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between gap-4">
                  <h3 className="gx-display text-2xl sm:text-3xl font-black uppercase text-white">
                    {stadium?.name || club.home_venue_name || `${club.name} Stadium`}
                  </h3>
                  {stadium?.level && (
                    <span className="rounded-full bg-cyan-400/10 px-3 py-1 text-xs font-mono font-bold text-cyan-300 border border-cyan-400/20">
                      Tier {stadium.level}
                    </span>
                  )}
                </div>
                <p className="mt-3 text-sm text-slate-300 leading-relaxed">
                  The home base for all domestic and continental fixtures. Matchday revenue and ticket demand scale directly with stadium infrastructure and fan engagement.
                </p>
              </div>

              <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 gap-4 border-t border-white/10 pt-4">
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">Capacity</span>
                  <p className="gx-mono text-lg font-bold text-white mt-0.5">
                    {stadium?.capacity ? `${stadium.capacity.toLocaleString()} seats` : "Unrated"}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">Match Pitch</span>
                  <p className="gx-mono text-lg font-bold text-emerald-400 mt-0.5">Hybrid Turf</p>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">Campus Link</span>
                  <p className="text-sm font-bold text-cyan-300 mt-0.5">Verified Asset</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION B: FOOTBALL DEPARTMENT (STANDOUT PLAYERS & LEADERSHIP) */}
        <section aria-labelledby="department-heading" className="space-y-6">
          <div>
            <p className="gx-eyebrow text-emerald-400">Football Operations</p>
            <h2 id="department-heading" className="gx-display text-3xl font-bold uppercase text-white">
              Standout Talent & Leadership
            </h2>
          </div>

          {/* Standout Player Cards */}
          <div className="grid gap-6 md:grid-cols-2">
            {/* Best Player */}
            <div className="rounded-2xl border border-amber-500/30 bg-gradient-to-br from-amber-500/10 via-slate-900/60 to-slate-950 p-6 shadow-xl relative overflow-hidden">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-amber-300">
                  <Award size={15} /> Best Player
                </span>
                <span className="rounded bg-amber-400/20 px-2 py-0.5 text-[10px] font-mono font-bold text-amber-200 border border-amber-400/30">
                  MARQUEE
                </span>
              </div>

              {squad?.best_player ? (
                <div className="mt-5 flex items-center gap-5">
                  <div className="size-20 sm:size-24 rounded-2xl bg-slate-900 border-2 border-amber-400/40 overflow-hidden shrink-0 flex items-center justify-center">
                    {squad.best_player.portrait_url ? (
                      <img
                        src={squad.best_player.portrait_url}
                        alt={squad.best_player.name}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <Users className="text-amber-300/60" size={32} />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="gx-display text-2xl font-bold text-white uppercase truncate">
                      {squad.best_player.name}
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      {squad.best_player.position} · Age {squad.best_player.age || "—"}
                      {squad.best_player.is_regen && " · Regen Wonderkid"}
                    </p>
                    <div className="mt-3 flex items-center gap-4">
                      {squad.best_player.rating && (
                        <div>
                          <span className="text-[9px] uppercase font-mono text-slate-400">Rating</span>
                          <p className="gx-mono text-xl font-black text-amber-300">{squad.best_player.rating}</p>
                        </div>
                      )}
                      {squad.best_player.potential && (
                        <div>
                          <span className="text-[9px] uppercase font-mono text-slate-400">Potential</span>
                          <p className="gx-mono text-xl font-black text-emerald-400">{squad.best_player.potential}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="mt-6 text-sm text-slate-400">No standout senior player designated in public roster.</p>
              )}
            </div>

            {/* Most Promising Player */}
            <div className="rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 via-slate-900/60 to-slate-950 p-6 shadow-xl relative overflow-hidden">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-emerald-300">
                  <Flame size={15} /> Most Promising
                </span>
                <span className="rounded bg-emerald-400/20 px-2 py-0.5 text-[10px] font-mono font-bold text-emerald-200 border border-emerald-400/30">
                  PROSPECT
                </span>
              </div>

              {squad?.most_promising_player ? (
                <div className="mt-5 flex items-center gap-5">
                  <div className="size-20 sm:size-24 rounded-2xl bg-slate-900 border-2 border-emerald-400/40 overflow-hidden shrink-0 flex items-center justify-center">
                    {squad.most_promising_player.portrait_url ? (
                      <img
                        src={squad.most_promising_player.portrait_url}
                        alt={squad.most_promising_player.name}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <Sparkles className="text-emerald-300/60" size={32} />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="gx-display text-2xl font-bold text-white uppercase truncate">
                      {squad.most_promising_player.name}
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      {squad.most_promising_player.position} · Age {squad.most_promising_player.age || "—"}
                      {squad.most_promising_player.is_regen && " · Regen Pipeline"}
                    </p>
                    <div className="mt-3 flex items-center gap-4">
                      {squad.most_promising_player.rating && (
                        <div>
                          <span className="text-[9px] uppercase font-mono text-slate-400">Current</span>
                          <p className="gx-mono text-xl font-black text-slate-200">{squad.most_promising_player.rating}</p>
                        </div>
                      )}
                      {squad.most_promising_player.potential && (
                        <div>
                          <span className="text-[9px] uppercase font-mono text-slate-400">Ceiling</span>
                          <p className="gx-mono text-xl font-black text-emerald-300">{squad.most_promising_player.potential}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="mt-6 text-sm text-slate-400">No young breakthrough prospect designated in public roster.</p>
              )}
            </div>
          </div>

          {/* Executive & Football Leadership Hierarchy */}
          <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-4 flex items-center gap-2">
              <Users size={16} className="text-cyan-400" /> Executive & Coaching Leadership
            </h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {staff && staff.length > 0 ? (
                staff.map((person) => (
                  <div
                    key={person.role}
                    className="rounded-xl border border-white/5 bg-black/40 p-4 transition-all hover:border-white/15"
                  >
                    <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">{person.title}</p>
                    <p className="gx-display text-lg font-bold text-white mt-1 truncate">
                      {person.name || "Vacant"}
                    </p>
                    <div className="mt-2 flex items-center justify-between text-xs">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${person.appointed ? "bg-emerald-500/20 text-emerald-300" : "bg-slate-800 text-slate-400"}`}>
                        {person.appointed ? "Appointed" : "Unassigned"}
                      </span>
                      {person.rating && (
                        <span className="font-mono font-bold text-amber-300">
                          {person.rating} RTG
                        </span>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-400 col-span-4">Staff details not published.</p>
              )}
            </div>
          </div>
        </section>

        {/* SECTION C: PUBLIC SQUAD DIRECTORY */}
        <section aria-labelledby="squad-heading" className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
            <div>
              <p className="gx-eyebrow text-slate-400">Senior Roster</p>
              <h2 id="squad-heading" className="gx-display text-3xl font-bold uppercase text-white">
                Public Squad Directory
              </h2>
            </div>
            {/* Position filter buttons */}
            <div className="flex flex-wrap gap-1.5 bg-black/40 p-1 rounded-xl border border-white/10">
              {["ALL", "GK", "DEF", "MID", "FWD"].map((pos) => (
                <button
                  key={pos}
                  onClick={() => setPositionFilter(pos)}
                  className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors ${
                    positionFilter === pos ? "bg-emerald-500 text-slate-950 shadow" : "text-slate-400 hover:text-white"
                  }`}
                >
                  {pos}
                </button>
              ))}
            </div>
          </div>

          {filteredPlayers.length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/10 bg-slate-900/30 p-8 text-center text-slate-400">
              No registered players match the selected position filter.
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-white/10 bg-slate-900/50">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="border-b border-white/10 bg-black/40 text-[10px] font-bold uppercase text-slate-400 tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Player</th>
                    <th className="py-3 px-3">Position</th>
                    <th className="py-3 px-3">Age</th>
                    <th className="py-3 px-3 text-right">Rating</th>
                    <th className="py-3 px-3 text-right">Potential</th>
                    <th className="py-3 px-4 text-center">Type</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {filteredPlayers.map((p) => (
                    <tr key={p.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="py-3 px-4 font-bold text-white flex items-center gap-2">
                        {p.name}
                      </td>
                      <td className="py-3 px-3 font-mono text-xs text-cyan-300">{p.position}</td>
                      <td className="py-3 px-3 text-slate-400">{p.age ?? "—"}</td>
                      <td className="py-3 px-3 text-right font-mono font-bold text-amber-300">
                        {p.rating ?? "—"}
                      </td>
                      <td className="py-3 px-3 text-right font-mono font-bold text-emerald-400">
                        {p.potential ?? "—"}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${p.is_regen ? "bg-purple-500/20 text-purple-300" : "bg-blue-500/20 text-blue-300"}`}>
                          {p.is_regen ? "Regen" : "Senior"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* SECTION D: ACADEMY & FACILITIES (WITH DIRECT LINKS) */}
        <section aria-labelledby="facilities-heading" className="space-y-6">
          <div>
            <p className="gx-eyebrow text-amber-400">Youth Infrastructure</p>
            <h2 id="facilities-heading" className="gx-display text-3xl font-bold uppercase text-white">
              Academy & Performance Facilities
            </h2>
          </div>

          <div className="grid gap-6 lg:grid-cols-12 rounded-2xl border border-white/10 bg-slate-900/50 p-6 sm:p-8">
            <div className="lg:col-span-4 flex flex-col justify-between">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                  <School size={16} /> Youth Development Complex
                </span>
                <h3 className="gx-display text-2xl font-black uppercase text-white mt-2">
                  Level {academy?.level || facilities?.academy_level || 1} Academy
                </h3>
                <p className="text-xs text-slate-300 mt-2 leading-relaxed">
                  The proving ground for generational regens and academy intakes. High academy tier accelerates tactical IQ and potential fulfillment.
                </p>

                <div className="mt-4 space-y-1.5 text-xs text-slate-400">
                  <p>Capacity Limit: <b className="text-white">{academy?.capacity || 24} prospects</b></p>
                  <p>Active In Pipeline: <b className="text-emerald-400">{academy?.prospect_count || 0} prospects</b></p>
                </div>
              </div>

              {/* Direct Facility Navigation Links */}
              <div className="mt-6 flex flex-wrap gap-2">
                <Link
                  to="/app/campus"
                  className="gx-btn gx-btn-secondary text-xs flex items-center gap-1.5"
                >
                  <Building size={13} />
                  <span>3D Campus</span>
                </Link>
                <Link
                  to="/app/showroom"
                  className="gx-btn gx-btn-secondary text-xs flex items-center gap-1.5"
                >
                  <Sparkles size={13} />
                  <span>Showroom</span>
                </Link>
                <Link
                  to="/app/academy"
                  className="gx-btn gx-btn-primary text-xs flex items-center gap-1.5"
                >
                  <School size={13} />
                  <span>Academy Complex</span>
                </Link>
              </div>
            </div>

            {/* Facilities Level Matrix */}
            <div className="lg:col-span-8 grid grid-cols-2 sm:grid-cols-3 gap-3">
              {[
                { label: "Training Facility", level: facilities?.training_level ?? 1, icon: Building, color: "text-emerald-400" },
                { label: "Academy Complex", level: facilities?.academy_level ?? academy?.level ?? 1, icon: School, color: "text-amber-400" },
                { label: "Medical Centre", level: facilities?.medical_level ?? 1, icon: Stethoscope, color: "text-rose-400" },
                { label: "Youth Recruitment", level: facilities?.youth_recruitment_level ?? 1, icon: Globe, color: "text-cyan-400" },
                { label: "Commercial & Branding", level: facilities?.branding_level ?? 1, icon: Palette, color: "text-purple-400" },
                { label: "Stadium Quality", level: stadium?.level ?? 1, icon: Building, color: "text-blue-400" },
              ].map((item) => (
                <div key={item.label} className="rounded-xl border border-white/5 bg-black/40 p-4 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <item.icon className={item.color} size={18} />
                    <span className="gx-mono text-xs font-bold text-slate-400">L{item.level}/5</span>
                  </div>
                  <div className="mt-4">
                    <p className="text-[11px] font-bold text-white">{item.label}</p>
                    <div className="mt-2 flex gap-1">
                      {[1, 2, 3, 4, 5].map((idx) => (
                        <div
                          key={idx}
                          className={`h-1 flex-1 rounded-full ${idx <= item.level ? "bg-emerald-400" : "bg-white/10"}`}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Academy Prospects Watchlist */}
          {academy?.prospects && academy.prospects.length > 0 && (
            <div className="rounded-2xl border border-white/10 bg-slate-900/40 p-6">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4 flex items-center gap-1.5">
                <Sparkles size={14} className="text-emerald-400" /> Academy Watchlist
              </h3>
              <div className="grid gap-3 sm:grid-cols-3">
                {academy.prospects.map((p) => (
                  <div key={p.id} className="rounded-xl border border-white/5 bg-black/40 p-4">
                    <p className="font-bold text-white">{p.name}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{p.position} · Age {p.age}</p>
                    <div className="mt-3 flex items-center justify-between text-xs">
                      <span className="text-[10px] text-slate-400 uppercase font-mono">Potential</span>
                      <span className="font-mono font-bold text-emerald-400">{p.potential} POT</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* SECTION E: TEAM TRAVEL & COACH BUSES */}
        <section aria-labelledby="fleet-heading" className="space-y-4">
          <div>
            <p className="gx-eyebrow text-purple-400">Team Transport</p>
            <h2 id="fleet-heading" className="gx-display text-3xl font-bold uppercase text-white">
              Club Coach Fleet & Assets
            </h2>
          </div>

          {coach_buses && coach_buses.length > 0 ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {coach_buses.map((bus, idx) => (
                <div key={idx} className="rounded-2xl border border-purple-500/20 bg-slate-900/60 p-5 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="inline-flex items-center gap-1.5 text-xs font-bold text-purple-300">
                        <Bus size={15} /> {bus.category?.toUpperCase() || "TEAM TRANSPORT"}
                      </span>
                      {bus.edition_number && (
                        <span className="gx-mono text-[10px] text-slate-400">
                          #{bus.edition_number} {bus.supply_cap ? `/ ${bus.supply_cap}` : ""}
                        </span>
                      )}
                    </div>
                    <h3 className="gx-display text-xl font-bold text-white mt-3">{bus.name}</h3>
                  </div>
                  {bus.catalog_price && (
                    <p className="mt-4 text-xs font-mono text-purple-200">
                      Fleet Value: {formatGtx(bus.catalog_price)}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-white/10 bg-slate-900/30 p-8 text-center text-slate-400 flex items-center justify-center gap-3">
              <Bus size={22} className="text-slate-500" />
              <span>No custom coach buses registered in this club's public transport fleet yet.</span>
            </div>
          )}
        </section>

        {/* SECTION F: OWNER SPOTLIGHT */}
        <section aria-labelledby="owner-heading">
          <div className="rounded-2xl border border-amber-500/30 bg-gradient-to-r from-amber-500/[0.08] via-slate-900/80 to-black p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-2xl">
            <div className="flex items-center gap-5">
              <div className="size-16 sm:size-20 rounded-2xl bg-amber-400/10 border-2 border-amber-400/30 flex items-center justify-center text-amber-300 shrink-0">
                <Users size={32} />
              </div>
              <div>
                <p className="text-[10px] uppercase font-bold tracking-wider text-amber-300">Club Ownership</p>
                <h3 className="gx-display text-2xl sm:text-3xl font-black uppercase text-white mt-0.5">
                  {owner?.display_name || "GTEX Club Owner"}
                </h3>
                <p className="text-xs text-slate-300 mt-1">
                  Controls {owner?.club_count || 1} verified GTEX club{owner?.club_count === 1 ? "" : "s"} · {owner?.luxury_asset_count || 0} registered personal luxury assets
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {owner?.net_worth && (
                <div className="text-right">
                  <span className="text-[10px] uppercase font-bold text-slate-400">Owner Net Worth</span>
                  <p className="gx-mono text-xl font-black text-amber-300">
                    {formatGtx(owner.net_worth, owner.net_worth_currency || "GTX")}
                  </p>
                </div>
              )}
              <button
                type="button"
                onClick={() => setOwnerModalOpen(true)}
                className="gx-btn gx-btn-primary text-xs"
              >
                Owner Persona
              </button>
            </div>
          </div>
        </section>

        {/* SECTION G: ACHIEVEMENTS & HONOURS */}
        <section aria-labelledby="honours-heading" className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="gx-eyebrow text-amber-400">Silverware Cabinet</p>
              <h2 id="honours-heading" className="gx-display text-3xl font-bold uppercase text-white">
                Honours & Achievements
              </h2>
            </div>
            <span className="gx-mono text-xs text-slate-500">{trophies?.length || 0} RECORDS</span>
          </div>

          {trophies && trophies.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {trophies.map((trophy, idx) => {
                const badge = placementBadge(trophy.position);
                return (
                  <div
                    key={trophy.id || idx}
                    className="rounded-xl border border-white/10 bg-slate-900/50 p-5 flex flex-col justify-between hover:border-amber-400/40 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${badge.tone}`}>
                          {badge.label}
                        </span>
                        <h3 className="gx-display text-xl font-bold text-white mt-2">
                          {trophy.name || trophy.competition}
                        </h3>
                      </div>
                      <Trophy className="text-amber-400 shrink-0 mt-1" size={22} />
                    </div>
                    {trophy.season && (
                      <div className="mt-4 border-t border-white/5 pt-2 text-xs font-mono text-slate-400">
                        Season: {trophy.season}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-white/10 bg-slate-900/30 p-10 text-center text-slate-400">
              <Trophy className="mx-auto mb-3 text-slate-600" size={32} />
              <p className="font-bold text-white">A record still being written</p>
              <p className="text-xs text-slate-400 mt-1">Honours and podium finishes will update as competitions conclude.</p>
            </div>
          )}
        </section>

        {/* SECTION H: 3D SHOWCASE & INSPECTION */}
        <section aria-label="3D Club Inspection">
          <Cinema3DStage
            scene="stadium_arena_match"
            compact
            enableSocialSalute
            title={`3D Match & Hangar Inspection · ${club.name}`}
            subtitle={`Visitor Experience · ${location || "Global GTEX Network"}`}
            badgeText="VERIFIED 3D STAGE"
            clubName={club.name}
            primaryColor={primary}
            secondaryColor={secondary}
            subjectName={`${club.name} Stadium & Facilities`}
            quote="Inspect this club's 3D facilities, pitch arena, and matchday presentation."
            stats={[
              { label: "Recorded Honours", value: `${trophies?.length || 0}`, accent: "#F5B83D" },
              { label: "Stadium Status", value: stadium?.level ? `Tier ${stadium.level}` : "Verified", accent: "#00E676" },
            ]}
          />
        </section>
      </div>

      {/* OWNER MODAL */}
      {ownerModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl border border-amber-500/30 bg-slate-950 p-6 shadow-2xl relative">
            <button
              type="button"
              onClick={() => setOwnerModalOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white"
            >
              <X size={20} />
            </button>

            <p className="text-[10px] uppercase font-bold text-amber-400 tracking-wider">Owner Persona</p>
            <h2 className="gx-display text-2xl font-black uppercase text-white mt-1">
              {owner?.display_name || "Club Owner"}
            </h2>

            <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-lg bg-slate-900/80 p-3 border border-white/5">
                <span className="text-slate-400">Clubs Owned</span>
                <p className="text-base font-bold text-white mt-0.5">{owner?.club_count || 1}</p>
              </div>
              <div className="rounded-lg bg-slate-900/80 p-3 border border-white/5">
                <span className="text-slate-400">Luxury Assets</span>
                <p className="text-base font-bold text-white mt-0.5">{owner?.luxury_asset_count || 0}</p>
              </div>
            </div>

            {owner?.public_clubs && owner.public_clubs.length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-bold text-slate-300 mb-2">Public Club Portfolio</p>
                <div className="space-y-2">
                  {owner.public_clubs.map((c) => (
                    <Link
                      key={c.id}
                      to={`/club/${c.slug || c.id}`}
                      onClick={() => setOwnerModalOpen(false)}
                      className="flex items-center justify-between rounded-lg bg-slate-900/60 p-2.5 border border-white/5 hover:border-amber-400/40 text-xs text-white"
                    >
                      <span className="font-bold">{c.name}</span>
                      <span className="text-slate-400">{c.city || c.country_code}</span>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            <button
              type="button"
              onClick={() => setOwnerModalOpen(false)}
              className="mt-6 w-full gx-btn gx-btn-secondary text-xs"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* FOOTER */}
      <footer className="border-t border-white/10 px-5 py-8 text-center text-xs text-slate-500">
        GTEX · Public Club Dossier · Verified matchday identity, academy records, and honours.
      </footer>
    </main>
  );
}
