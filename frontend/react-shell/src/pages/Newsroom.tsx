import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useNewsroom, fmt } from "@/lib/owner";
import {
  BookOpen,
  Building,
  Calendar,
  CheckCircle2,
  Clock,
  ExternalLink,
  Flame,
  Gift,
  Newspaper,
  Plane,
  Radio,
  Share2,
  ShieldCheck,
  Trophy,
  X,
} from "lucide-react";
import { Loading } from "@/components/gtex/ui";
import { Cinema3DStage } from "@/components/gtex/Cinema3DStage";

export function Newsroom() {
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [activeStory, setActiveStory] = useState<any | null>(null);
  const { data, isLoading } = useNewsroom(undefined, selectedCategory, 40);
  const articles: any[] = data?.articles || [];

  const categories = [
    { key: "all", label: "Top Stories & Wire" },
    { key: "match_result", label: "Matchday Reports", icon: Trophy },
    { key: "facility_upgrade", label: "Club Infrastructure", icon: Building },
    { key: "private_jet_purchase", label: "Aviation & Jets", icon: Plane },
    { key: "player_gift", label: "Player Milestones", icon: Gift },
    { key: "new_signing_presentation", label: "Signing Unveilings", icon: Flame },
    { key: "build_a_son_induction", label: "Build-A-Son & Regens", icon: Radio },
    { key: "press_conference", label: "Rivalry & Press", icon: Newspaper },
  ];

  // Lead story is the most prominent or first verified article
  const leadStory = articles.find((a) => a.hero_image_url) || articles[0];
  const secondaryStories = articles.filter((a) => a.id !== leadStory?.id).slice(0, 3);
  const wireStories = articles.filter((a) => a.id !== leadStory?.id).slice(3);

  return (
    <div className="space-y-10 p-4 sm:p-8" data-testid="newsroom-screen">
      {/* Editorial Masthead */}
      <header className="relative border-b-2 border-white/10 pb-6 text-left">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-amber-400 text-xs font-black uppercase tracking-[0.2em]">
              <Newspaper size={16} />
              <span>GTEX GLOBAL EDITORIAL DESK · AUTHORITATIVE WIRE</span>
            </div>
            <h1 className="gx-display mt-1 text-4xl sm:text-6xl font-black uppercase tracking-tight text-white leading-none">
              The Boardroom Chronicle
            </h1>
            <p className="mt-2 text-xs sm:text-sm text-slate-300 max-w-2xl">
              Real-time, verified football reporting and club-owner developments. Every dispatch is strictly grounded in verified ledger and simulation events.
            </p>
          </div>

          {/* Grounding & Privacy Guarantee Seal */}
          <div className="flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-[#061c14] px-4 py-2.5 text-xs shadow-lg">
            <ShieldCheck className="size-5 text-emerald-400 shrink-0" />
            <div className="text-[11px] leading-tight">
              <span className="font-bold text-emerald-300">Grounding & Privacy Certified:</span>
              <p className="text-slate-400 mt-0.5">Confidential owner inboxes and private scouting remain protected.</p>
            </div>
          </div>
        </div>

        {/* Category Filter Navigation */}
        <nav className="flex items-center gap-2 overflow-x-auto pt-6" data-testid="newsroom-categories">
          {categories.map((cat) => {
            const Icon = cat.icon;
            const active = selectedCategory === cat.key;
            return (
              <button
                key={cat.key}
                onClick={() => setSelectedCategory(cat.key)}
                data-testid={`cat-${cat.key}`}
                className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold uppercase tracking-wider whitespace-nowrap transition-all ${
                  active
                    ? "bg-amber-500 text-slate-950 font-black shadow-[0_0_16px_rgba(245,158,11,0.4)]"
                    : "border border-white/10 bg-slate-900/60 text-slate-300 hover:border-amber-400/40 hover:text-white"
                }`}
              >
                {Icon && <Icon size={13} />}
                <span>{cat.label}</span>
              </button>
            );
          })}
        </nav>
      </header>

      {/* 3D Global Flex Wire (Private Jet Purchases for All Users) & 3D Official Club Announcement Studio */}
      <div className="grid gap-6 lg:grid-cols-2" data-testid="newsroom-3d-broadcast-row">
        <Cinema3DStage
          scene="private_jet_flex"
          compact
          enableSocialSalute
          title="3D Global Aviation Flex · G650 Executive Jet Commissioned"
          subtitle="Public 3D Runway Showcase for All GTEX App Users · Custom Club Tail-Fin Livery"
          badgeText="GLOBAL FLEX ALERT"
          clubName={leadStory?.club_name || "GTEX Superclub"}
          ownerName={leadStory?.owner_name || "Executive Owner"}
          subjectName="Gulfstream G650 Bespoke Club Edition"
          quote="Commissioned from the club treasury — inspect the 3D fuselage and salute this owner's flex."
          stats={[
            { label: "Club Prestige", value: "+12 PTS", accent: "#00E676" },
            { label: "Edition", value: "1 OF 10 MINTED", accent: "#F5B83D" },
          ]}
        />
        <Cinema3DStage
          scene="club_announcement"
          compact
          enableSocialSalute
          title={leadStory?.headline || "3D Official Club Communiqué & Breaking News Desk"}
          subtitle="Sky-Studio 3D Curved LED Broadcast Wall · Verified Club Statement"
          badgeText="3D CLUB ANNOUNCEMENT"
          clubName={leadStory?.club_name || "GTEX Broadcast Network"}
          subjectName={leadStory?.headline || "Official Boardroom Statement on Season Ambitions"}
          subjectRole={leadStory?.category ? `Wire Category: ${leadStory.category.replace(/_/g, " ").toUpperCase()}` : "Official Club Communiqué"}
          quote={leadStory?.summary || "The board of directors has ratified our continental roadmap and stadium expansion."}
        />
      </div>

      {isLoading ? (
        <Loading label="Transmitting verified dispatches from the news wire..." />
      ) : articles.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-white/10 p-16 text-center">
          <Newspaper className="mx-auto size-12 text-slate-600 mb-3" />
          <h3 className="gx-display text-2xl font-bold uppercase text-white">No Dispatches on this Wire</h3>
          <p className="text-sm text-slate-400 mt-1 max-w-md mx-auto">
            Stories generate automatically following verified match whistles, facility upgrades, and high-significance club transactions.
          </p>
        </div>
      ) : (
        <div className="space-y-12">
          {/* Dominant Editorial Lead Story */}
          {leadStory && (
            <article
              onClick={() => setActiveStory(leadStory)}
              className="group cursor-pointer relative overflow-hidden rounded-3xl border-2 border-white/15 bg-gradient-to-t from-slate-950 via-slate-900/90 to-[#07101a] shadow-2xl transition-all duration-300 hover:border-amber-400/60 hover:shadow-[0_20px_50px_rgba(245,158,11,0.15)]"
              data-testid="lead-story-card"
            >
              <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[440px]">
                {/* Hero imagery / fallback */}
                <div className="relative lg:col-span-7 h-64 lg:h-full bg-slate-950 overflow-hidden">
                  <img
                    src={leadStory.hero_image_url || "/img/hero.jpg"}
                    alt={leadStory.headline}
                    className="size-full object-cover object-center transition-transform duration-700 group-hover:scale-105"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = "/img/hero.jpg";
                    }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/30 to-transparent lg:bg-gradient-to-r lg:from-transparent lg:to-slate-950" />
                  <span className="absolute left-4 top-4 rounded bg-amber-500 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-slate-950 shadow-md">
                    Lead Editorial
                  </span>
                </div>

                {/* Editorial text & facts */}
                <div className="lg:col-span-5 p-6 sm:p-10 flex flex-col justify-between text-left space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center gap-3 text-xs text-amber-400 font-bold uppercase tracking-wider">
                      <span className="flex items-center gap-1">
                        <Clock size={12} /> {new Date(leadStory.created_at).toLocaleDateString()}
                      </span>
                      {leadStory.world_day && <span>· Day {leadStory.world_day}</span>}
                      <span className="rounded bg-emerald-500/20 text-emerald-300 px-2 py-0.5 text-[9px] font-black">
                        Verified Grounded
                      </span>
                    </div>

                    <h2 className="gx-display text-3xl sm:text-5xl font-black uppercase tracking-tight text-white leading-tight group-hover:text-amber-300 transition-colors">
                      {leadStory.headline}
                    </h2>

                    {leadStory.subhead && (
                      <p className="text-sm font-semibold text-slate-300 italic">
                        {leadStory.subhead}
                      </p>
                    )}

                    <p className="text-xs sm:text-sm text-slate-300 line-clamp-4 leading-relaxed">
                      {leadStory.editorial_narration || leadStory.body}
                    </p>
                  </div>

                  <div className="pt-4 border-t border-white/10 flex items-center justify-between">
                    <span className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                      Read Full Report <ExternalLink size={12} />
                    </span>
                    <span className="gx-mono text-[11px] text-slate-500">
                      Category: {leadStory.category.replace(/_/g, " ").toUpperCase()}
                    </span>
                  </div>
                </div>
              </div>
            </article>
          )}

          {/* Supporting Reports Grid (2-3 prominent columns) */}
          {secondaryStories.length > 0 && (
            <section className="space-y-4">
              <div className="flex items-center gap-2 border-b border-white/10 pb-2">
                <Flame size={18} className="text-amber-400" />
                <h3 className="gx-display text-2xl font-black uppercase text-white tracking-wide">
                  Top Verified Wire Dispatches
                </h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6" data-testid="secondary-stories-grid">
                {secondaryStories.map((story) => (
                  <article
                    key={story.id}
                    onClick={() => setActiveStory(story)}
                    className="group cursor-pointer rounded-2xl border border-white/10 bg-slate-900/60 overflow-hidden flex flex-col justify-between hover:border-amber-400/50 hover:shadow-xl transition-all"
                  >
                    {story.hero_image_url && (
                      <div className="relative h-44 w-full bg-slate-950 overflow-hidden">
                        <img
                          src={story.hero_image_url}
                          alt={story.headline}
                          className="size-full object-cover transition-transform duration-500 group-hover:scale-105"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = "none";
                          }}
                        />
                        <span className="absolute top-3 left-3 rounded bg-slate-950/80 border border-white/20 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-amber-300">
                          {story.category.replace(/_/g, " ")}
                        </span>
                      </div>
                    )}

                    <div className="p-5 flex-1 flex flex-col justify-between space-y-3">
                      <div className="space-y-2">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                          {new Date(story.created_at).toLocaleDateString()}
                        </p>
                        <h4 className="gx-display text-xl font-bold uppercase text-white group-hover:text-amber-300 transition-colors leading-snug">
                          {story.headline}
                        </h4>
                        <p className="text-xs text-slate-300 line-clamp-3 leading-relaxed">
                          {story.editorial_narration || story.body}
                        </p>
                      </div>

                      <div className="pt-3 border-t border-white/10 flex items-center justify-between text-[11px]">
                        <span className="font-bold text-emerald-400 flex items-center gap-1">
                          <CheckCircle2 size={12} /> Grounded
                        </span>
                        <span className="text-slate-400 group-hover:text-white transition-colors">
                          Read dispatch →
                        </span>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          )}

          {/* Chronological Wire Timeline */}
          {wireStories.length > 0 && (
            <section className="space-y-4">
              <div className="flex items-center gap-2 border-b border-white/10 pb-2">
                <Radio size={18} className="text-emerald-400 animate-pulse" />
                <h3 className="gx-display text-2xl font-black uppercase text-white tracking-wide">
                  Chronological News Wire
                </h3>
              </div>

              <div className="overflow-hidden rounded-2xl border border-white/10 bg-slate-900/60 divide-y divide-white/5" data-testid="chronological-wire">
                {wireStories.map((wire) => (
                  <div
                    key={wire.id}
                    onClick={() => setActiveStory(wire)}
                    className="group cursor-pointer p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 hover:bg-white/[0.03] transition-colors"
                  >
                    <div className="space-y-1 max-w-3xl">
                      <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase">
                        <span className="gx-mono text-emerald-400">{new Date(wire.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                        <span>·</span>
                        <span>{new Date(wire.created_at).toLocaleDateString()}</span>
                        <span>·</span>
                        <span className="text-amber-400">{wire.category.replace(/_/g, " ")}</span>
                      </div>
                      <h4 className="gx-display text-lg font-bold uppercase text-white group-hover:text-amber-300 transition-colors">
                        {wire.headline}
                      </h4>
                      <p className="text-xs text-slate-300 line-clamp-1">
                        {wire.editorial_narration || wire.body}
                      </p>
                    </div>

                    <span className="text-xs font-bold text-slate-400 group-hover:text-white shrink-0">
                      Open Report →
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      {/* Story Detail Read Modal */}
      {activeStory && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4"
          onClick={() => setActiveStory(null)}
          data-testid="story-detail-modal"
        >
          <div
            className="gx-scroll w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-3xl border-2 border-white/15 bg-[#071019] p-6 sm:p-10 text-white shadow-2xl space-y-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <span className="rounded bg-amber-500/20 text-amber-300 px-3 py-1 text-xs font-black uppercase tracking-wider">
                {activeStory.category.replace(/_/g, " ")}
              </span>
              <button
                onClick={() => setActiveStory(null)}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {activeStory.hero_image_url && (
              <div className="rounded-xl overflow-hidden max-h-72 w-full bg-slate-950">
                <img
                  src={activeStory.hero_image_url}
                  alt=""
                  className="size-full object-cover"
                />
              </div>
            )}

            <div className="space-y-3">
              <p className="gx-mono text-xs text-slate-400">
                Published {new Date(activeStory.created_at).toLocaleString()} {activeStory.world_day ? `· World Day ${activeStory.world_day}` : ""}
              </p>
              <h2 className="gx-display text-3xl sm:text-4xl font-black uppercase text-white leading-tight">
                {activeStory.headline}
              </h2>
              {activeStory.subhead && (
                <p className="text-sm font-semibold text-slate-300 italic border-l-2 border-amber-400 pl-3 py-1">
                  {activeStory.subhead}
                </p>
              )}
            </div>

            <div className="text-sm text-slate-200 leading-relaxed space-y-4 whitespace-pre-line pt-2">
              {activeStory.editorial_narration || activeStory.body}
            </div>

            {/* Verified Facts Breakdown */}
            {activeStory.established_facts && Object.keys(activeStory.established_facts).length > 0 && (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-400 uppercase tracking-wider">
                  <CheckCircle2 size={14} /> Verified Grounded Ledger Facts
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs text-slate-300 pt-1">
                  {Object.entries(activeStory.established_facts).map(([k, v]: any) => (
                    <div key={k}>
                      <span className="text-slate-500 uppercase text-[10px] block">{k.replace(/_/g, " ")}</span>
                      <span className="font-mono font-bold text-white">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
export default Newsroom;
