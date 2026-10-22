import React from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  ExternalLink,
  MapPin,
  ShieldCheck,
  Trophy,
} from "lucide-react";
import { api } from "@/lib/api";

type TrophyRecord = {
  competition: string;
  tier?: string | null;
  position: number;
  year?: number | null;
};

type PublicClubProfileData = {
  club_name: string;
  short_name?: string | null;
  city?: string | null;
  country_code?: string | null;
  primary_color?: string | null;
  secondary_color?: string | null;
  founded?: number | null;
  crest_url?: string | null;
  trophies: TrophyRecord[];
};

function crestSource(reference?: string | null) {
  if (!reference) return null;
  if (/^(https?:|data:)/i.test(reference)) return reference;
  if (reference.startsWith("/")) return reference;
  if (reference.startsWith("api/media/")) return `/${reference}`;
  return `/api/media/${reference.replace(/^\/+/, "")}`;
}

function placementLabel(position: number) {
  if (position === 1) return "Champions";
  if (position === 2) return "Runners-up";
  if (position === 3) return "Third place";
  return `Place ${position}`;
}

export default function PublicClubProfile() {
  const { clubSlug } = useParams<{ clubSlug: string }>();
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery<PublicClubProfileData>({
    queryKey: ["public-club-profile", clubSlug],
    queryFn: async () => (await api.get(`/owner/public/showroom/${encodeURIComponent(clubSlug || "")}`)).data,
    enabled: Boolean(clubSlug),
    retry: false,
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <main className="min-h-screen bg-[#070B11] px-5 py-24 text-center text-slate-400">
        <div className="mx-auto mb-4 size-9 animate-spin rounded-full border-2 border-amber-400 border-t-transparent" />
        <p className="gx-eyebrow">GTEX club archive</p>
        <p className="mt-2 text-sm">Loading verified club details…</p>
      </main>
    );
  }

  if (isError || !data) {
    const status = (error as any)?.response?.status;
    const title = status === 404 ? "This public profile isn't available" : "We couldn't load this club";
    const description =
      status === 404
        ? "The club may not exist or its owner has chosen not to publish a public profile."
        : "The public club service did not return a usable profile. No sample data has been substituted.";
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#070B11] px-5 py-16">
        <section className="w-full max-w-xl rounded-xl border border-white/10 bg-slate-900/70 p-8 text-center shadow-2xl">
          <ShieldCheck className="mx-auto mb-4 text-amber-400" size={34} />
          <p className="gx-eyebrow">GTEX · Public club profile</p>
          <h1 className="gx-display mt-3 text-3xl font-bold uppercase text-white">{title}</h1>
          <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-slate-400">{description}</p>
          <div className="mt-7 flex flex-wrap justify-center gap-3">
            <button className="gx-btn gx-btn-secondary" onClick={() => refetch()} disabled={isFetching}>
              {isFetching ? "Retrying…" : "Try again"}
            </button>
            <Link to="/" className="gx-btn gx-btn-primary">
              GTEX home <ArrowRight size={14} />
            </Link>
          </div>
        </section>
      </main>
    );
  }

  const crest = crestSource(data.crest_url);
  const location = [data.city, data.country_code].filter(Boolean).join(", ");
  const trophies = Array.isArray(data.trophies) ? data.trophies : [];
  const primary = data.primary_color || "#0F766E";
  const secondary = data.secondary_color || "#F8FAFC";

  return (
    <main className="min-h-screen bg-[#070B11] text-slate-200">
      <header className="relative isolate overflow-hidden border-b border-white/10">
        <img
          src="/console/img/showroom/arena_imperiale_stadium.webp"
          alt="GTEX stadium architecture"
          className="absolute inset-0 -z-20 h-full min-h-[560px] w-full object-cover object-center"
        />
        <div className="absolute inset-0 -z-10 bg-gradient-to-r from-[#070B11] via-[#070B11]/90 to-[#070B11]/45" />
        <div className="absolute inset-0 -z-10 bg-gradient-to-t from-[#070B11] via-transparent to-[#070B11]/50" />
        <div className="mx-auto max-w-[1380px] px-5 pb-16 pt-6 sm:px-8 lg:px-12 lg:pb-24">
          <nav className="flex items-center justify-between gap-4">
            <Link to="/" className="gx-display text-2xl font-black tracking-tight text-white" aria-label="GTEX home">
              GTEX<span className="text-emerald-400">.</span>
            </Link>
            <Link to="/login" className="gx-btn gx-btn-secondary">
              Enter the world <ExternalLink size={13} />
            </Link>
          </nav>

          <div className="mt-12 flex max-w-4xl flex-col items-start gap-7 sm:mt-20 sm:flex-row sm:items-end">
            <div
              className="flex size-28 shrink-0 items-center justify-center overflow-hidden rounded-2xl border-2 bg-slate-950/80 p-3 shadow-2xl backdrop-blur-md sm:size-36"
              style={{ borderColor: `${primary}cc` }}
            >
              {crest ? (
                <img
                  src={crest}
                  alt={`${data.club_name} crest`}
                  className="h-full w-full object-contain"
                  onError={(event) => {
                    (event.currentTarget as HTMLImageElement).style.display = "none";
                  }}
                />
              ) : (
                <span className="gx-display text-3xl font-black" style={{ color: secondary }}>
                  {(data.short_name || data.club_name).slice(0, 3).toUpperCase()}
                </span>
              )}
            </div>

            <div className="min-w-0 flex-1">
              <p className="gx-eyebrow mb-3 flex items-center gap-2 text-emerald-300">
                <ShieldCheck size={14} /> Official public club profile
              </p>
              <h1 className="gx-display max-w-3xl break-words text-5xl font-black uppercase leading-[0.9] tracking-tight text-white sm:text-6xl lg:text-8xl">
                {data.club_name}
              </h1>
              {data.short_name && (
                <p className="gx-mono mt-4 text-sm font-bold tracking-[0.24em]" style={{ color: secondary }}>
                  {data.short_name}
                </p>
              )}
              <div className="mt-5 flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate-300">
                {location && (
                  <span className="inline-flex items-center gap-2">
                    <MapPin size={15} className="text-emerald-300" /> {location}
                  </span>
                )}
                {data.founded && (
                  <span className="inline-flex items-center gap-2">
                    <CalendarDays size={15} className="text-emerald-300" /> Founded {data.founded}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="mt-12 grid max-w-3xl grid-cols-2 gap-3 sm:grid-cols-3">
            <div className="border-l-2 border-amber-400 bg-black/40 px-4 py-4 backdrop-blur-sm">
              <p className="gx-eyebrow text-slate-400">Honours record</p>
              <p className="gx-display mt-1 text-3xl font-bold text-white">{trophies.length}</p>
              <p className="mt-1 text-xs text-slate-400">Recorded podium finishes</p>
            </div>
            <div className="border-l-2 border-emerald-400 bg-black/40 px-4 py-4 backdrop-blur-sm">
              <p className="gx-eyebrow text-slate-400">Profile status</p>
              <p className="gx-display mt-1 text-3xl font-bold text-white">PUBLIC</p>
              <p className="mt-1 text-xs text-slate-400">Owner-published identity</p>
            </div>
            <div className="col-span-2 border-l-2 border-white/30 bg-black/40 px-4 py-4 backdrop-blur-sm sm:col-span-1">
              <p className="gx-eyebrow text-slate-400">Club colours</p>
              <div className="mt-3 flex items-center gap-2">
                <span className="size-7 rounded-full border border-white/20" style={{ backgroundColor: primary }} />
                <span className="size-7 rounded-full border border-white/20" style={{ backgroundColor: secondary }} />
                <span className="gx-mono text-[10px] text-slate-300">IDENTITY</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <section className="mx-auto grid max-w-[1380px] gap-10 px-5 py-12 sm:px-8 lg:grid-cols-[minmax(0,1fr)_300px] lg:px-12 lg:py-16">
        <div>
          <div className="flex flex-wrap items-end justify-between gap-4 border-b border-white/10 pb-5">
            <div>
              <p className="gx-eyebrow text-amber-400">Club archive</p>
              <h2 className="gx-display mt-2 text-3xl font-bold uppercase text-white sm:text-4xl">Honours & milestones</h2>
            </div>
            <span className="gx-mono text-xs text-slate-500">{trophies.length.toString().padStart(2, "0")} RECORDS</span>
          </div>

          {trophies.length === 0 ? (
            <div className="mt-5 rounded-xl border border-dashed border-white/15 bg-white/[0.02] px-6 py-12 text-center">
              <Trophy className="mx-auto mb-4 text-slate-600" size={30} />
              <h3 className="gx-display text-2xl font-bold uppercase text-white">A record still being written</h3>
              <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-400">
                No podium finishes are recorded for this club yet. The honours panel will update when competitions publish verified results.
              </p>
            </div>
          ) : (
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              {trophies.map((item, index) => (
                <article
                  key={`${item.competition}-${item.year ?? "unknown"}-${item.position}-${index}`}
                  className="group relative overflow-hidden rounded-lg border border-white/10 bg-slate-900/55 p-5 transition-colors hover:border-amber-400/40"
                >
                  <div className="absolute inset-y-0 left-0 w-1" style={{ backgroundColor: item.position === 1 ? "#F59E0B" : item.position === 2 ? "#CBD5E1" : "#B77946" }} />
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="gx-eyebrow text-slate-500">{item.tier || "Competition"}</p>
                      <h3 className="gx-display mt-2 break-words text-2xl font-bold uppercase leading-tight text-white">{item.competition}</h3>
                    </div>
                    <Trophy className="mt-1 shrink-0 text-amber-400" size={21} />
                  </div>
                  <div className="mt-6 flex items-center justify-between gap-2 border-t border-white/10 pt-3">
                    <span className="text-xs font-semibold text-slate-300">{placementLabel(item.position)}</span>
                    <span className="gx-mono text-xs text-amber-300">{item.year ?? "Year not recorded"}</span>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>

        <aside className="space-y-4">
          <div className="rounded-xl border border-white/10 bg-slate-900/60 p-5">
            <p className="gx-eyebrow">Public access</p>
            <h3 className="gx-display mt-2 text-2xl font-bold uppercase text-white">Club identity, not private books</h3>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              This profile uses the club's published identity and recorded competition podiums. Private finances, player contracts, staff matters and owner inventory stay out of the public response.
            </p>
          </div>
          <Link to="/" className="gx-btn gx-btn-secondary w-full justify-between">
            <span className="inline-flex items-center gap-2"><ArrowLeft size={14} /> Back to GTEX</span>
            <ArrowRight size={14} />
          </Link>
        </aside>
      </section>

      <footer className="border-t border-white/10 px-5 py-6 text-center text-xs text-slate-600">
        GTEX · Public club archive · Displayed honours are derived from recorded competition finishes.
      </footer>
    </main>
  );
}
