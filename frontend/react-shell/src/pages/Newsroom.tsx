import React, { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useActiveClub, useNewsroom, useRefreshOwner, fmt } from "@/lib/owner";
import { publicAssetPath } from "@/lib/publicPath";
import {
  Building,
  CheckCircle2,
  Clock,
  ExternalLink,
  Flame,
  Gift,
  Newspaper,
  Plane,
  Radio,
  ShieldCheck,
  Trophy,
  X,
  RefreshCw,
  Compass,
  Sparkles,
  AlertOctagon,
} from "lucide-react";
import { Loading } from "@/components/gtex/ui";
import { Cinema3DStage } from "@/components/gtex/Cinema3DStage";

const resolveNewsImage = (raw?: string, category?: string) => {
  if (raw && (raw.startsWith("http") || raw.startsWith("data:"))) return raw;
  if (raw) {
    const clean = raw.replace(/^\/console\//, "/");
    return publicAssetPath(clean);
  }
  if (category === "fleet_aviation" || category === "private_jet_purchase") {
    return publicAssetPath("/img/prestige/05_private_jet.png");
  }
  if (category === "infrastructure" || category === "facility_upgrade") {
    return publicAssetPath("/img/prestige/11_stadium_expansion_construction.png");
  }
  if (category === "academy_breakthrough" || category === "build_a_son_induction") {
    return publicAssetPath("/img/prestige/12_elite_academy_complex.png");
  }
  return publicAssetPath("/img/prestige/06_academy_campus_aerial_a.png");
};

export function Newsroom() {
  const { active } = useActiveClub();
  const clubId = active?.club_id;
  const refresh = useRefreshOwner();

  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [activeStory, setActiveStory] = useState<any | null>(null);
  const [syncing, setSyncing] = useState<boolean>(false);

  // Map UI filter keys to backend category keys when querying, or filter client-side
  const { data, isLoading, refetch } = useNewsroom(undefined, "all", 60);
  const allArticles: any[] = data?.articles || [];

  const articles = allArticles.filter((a) => {
    if (selectedCategory === "all") return true;
    const cat = String(a.category || "");
    if (selectedCategory === "match_result") return ["match_result", "match_report"].includes(cat);
    if (selectedCategory === "facility_upgrade") return ["facility_upgrade", "infrastructure"].includes(cat);
    if (selectedCategory === "private_jet_purchase") return ["private_jet_purchase", "fleet_aviation"].includes(cat);
    if (selectedCategory === "player_gift") return ["player_gift", "squad_culture"].includes(cat);
    if (selectedCategory === "build_a_son_induction")
      return ["build_a_son_induction", "academy_breakthrough"].includes(cat);
    if (selectedCategory === "press_conference")
      return ["press_conference", "club_announcement"].includes(cat);
    return cat === selectedCategory;
  });

  const categories = [
    { key: "all", label: "Top Stories & Wire" },
    { key: "match_result", label: "Matchday Reports", icon: Trophy },
    { key: "facility_upgrade", label: "Campus & Stadium", icon: Building },
    { key: "private_jet_purchase", label: "Aviation & Jets", icon: Plane },
    { key: "player_gift", label: "Player Milestones", icon: Gift },
    { key: "new_signing_presentation", label: "Signing Unveilings", icon: Flame },
    { key: "build_a_son_induction", label: "Academy & Regens", icon: Radio },
    { key: "press_conference", label: "Communiqués & Press", icon: Newspaper },
  ];

  const handleSyncVerifiedNews = async () => {
    if (!clubId || syncing) return;
    setSyncing(true);
    try {
      const res = await api.post(`/owner/clubs/${clubId}/newsroom/sync`);
      toast.success(
        `Newsroom synchronized (${res.data?.synced_new_articles || 0} new verified dispatches indexed).`
      );
      refetch();
      refresh();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail?.detail || "Unable to sync newsroom");
    } finally {
      setSyncing(false);
    }
  };

  const handleEditorialStatus = async (articleId: string, status: "approved" | "retracted") => {
    try {
      const res = await api.post(`/owner/newsroom/${articleId}/editorial-status`, {
        status,
        editorial_note:
          status === "approved"
            ? "Verified by Club Editorial Desk against GTEX Ledger."
            : "Retracted by Editorial Desk.",
      });
      toast.success(status === "approved" ? "Article provenance certified!" : "Article retracted from live wire.");
      if (status === "retracted") {
        setActiveStory(null);
      } else {
        setActiveStory(res.data);
      }
      refetch();
      refresh();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail?.detail || "Editorial update failed");
    }
  };

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
              <span>GTEX GLOBAL EDITORIAL DESK · VERIFIED EVENT PROVENANCE</span>
            </div>
            <h1 className="gx-display mt-1 text-4xl sm:text-6xl font-black uppercase tracking-tight text-white leading-none">
              The Boardroom Chronicle
            </h1>
            <p className="mt-2 text-xs sm:text-sm text-slate-300 max-w-2xl">
              Authoritative football journalism, verified matchday reports, 3D campus construction milestones, and
              aviation dispatches. Every story is strictly grounded in persisted GTEX database events with zero
              hallucinated figures.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {clubId && (
              <button
                type="button"
                disabled={syncing}
                onClick={handleSyncVerifiedNews}
                className="px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-slate-950 text-xs font-black flex items-center gap-2 shadow-lg shadow-emerald-500/20"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${syncing ? "animate-spin" : ""}`} />
                Sync Verified Club Events
              </button>
            )}
            <Link
              to="/app/campus"
              className="px-3.5 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/15 text-xs font-bold text-slate-200 flex items-center gap-1.5"
            >
              <Compass className="w-3.5 h-3.5 text-emerald-400" /> 3D Campus
            </Link>
            {/* Grounding & Privacy Guarantee Seal */}
            <div className="flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-[#061c14] px-4 py-2.5 text-xs shadow-lg">
              <ShieldCheck className="size-5 text-emerald-400 shrink-0" />
              <div className="text-[11px] leading-tight">
                <span className="font-bold text-emerald-300">Grounding & Privacy Certified:</span>
                <p className="text-slate-400 mt-0.5">Confidential owner inboxes and private scouting remain protected.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Category Filter Navigation */}
        <nav className="flex items-center gap-2 overflow-x-auto pt-6" data-testid="newsroom-categories">
          {categories.map((cat) => {
            const Icon = cat.icon;
            const isActive = selectedCategory === cat.key;
            return (
              <button
                key={cat.key}
                onClick={() => setSelectedCategory(cat.key)}
                data-testid={`cat-${cat.key}`}
                className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold uppercase tracking-wider whitespace-nowrap transition-all ${
                  isActive
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

      {/* 3D Global Flex Wire & 3D Official Club Announcement Studio */}
      <div className="grid gap-6 lg:grid-cols-2" data-testid="newsroom-3d-broadcast-row">
        <Cinema3DStage
          scene="private_jet_flex"
          compact
          enableSocialSalute
          title="3D Global Aviation Flex · Sovereign 900X Executive Jet"
          subtitle="Public 3D Runway Showcase for All GTEX App Users · Custom Club Tail-Fin Livery"
          badgeText="GLOBAL FLEX ALERT"
          clubName={leadStory?.established_facts?.club_name || active?.club_name || "GTEX Superclub"}
          ownerName={leadStory?.established_facts?.owner_display_name || "Executive Owner"}
          subjectName="GTEX Sovereign 900X Bespoke Club Edition"
          quote="Commissioned from the club treasury — inspect the 3D fuselage and salute this owner's flex."
          stats={[
            { label: "Club Prestige", value: "+8 PTS", accent: "#00E676" },
            { label: "Verified Ledger", value: "4,800 GTX", accent: "#F5B83D" },
          ]}
        />
        <Cinema3DStage
          scene="club_announcement"
          compact
          enableSocialSalute
          title={leadStory?.headline || "3D Official Club Communiqué & Breaking News Desk"}
          subtitle="Sky-Studio 3D Curved LED Broadcast Wall · Verified Club Statement"
          badgeText="3D CLUB ANNOUNCEMENT"
          clubName={leadStory?.established_facts?.club_name || active?.club_name || "GTEX Broadcast Network"}
          subjectName={leadStory?.headline || "Official Boardroom Statement on Season Ambitions"}
          subjectRole={
            leadStory?.category
              ? `Wire Category: ${leadStory.category.replace(/_/g, " ").toUpperCase()}`
              : "Official Club Communiqué"
          }
          quote={
            leadStory?.subheadline ||
            "The board of directors has ratified our continental roadmap and 3D stadium expansion."
          }
        />
      </div>

      {isLoading ? (
        <Loading label="Transmitting verified dispatches from the news wire..." />
      ) : articles.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-white/10 p-16 text-center space-y-4">
          <Newspaper className="mx-auto size-12 text-slate-600 mb-3" />
          <h3 className="gx-display text-2xl font-bold uppercase text-white">No Dispatches on this Wire</h3>
          <p className="text-sm text-slate-400 mt-1 max-w-md mx-auto">
            Stories generate automatically following verified match whistles, 3D campus upgrades, and high-significance
            club transactions.
          </p>
          {clubId && (
            <button
              type="button"
              onClick={handleSyncVerifiedNews}
              className="px-5 py-2.5 rounded-xl bg-amber-400 hover:bg-amber-300 text-slate-950 text-xs font-black"
            >
              Generate Verified Club Coverage Now
            </button>
          )}
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
                {/* Hero imagery */}
                <div className="relative lg:col-span-7 h-64 lg:h-full bg-slate-950 overflow-hidden">
                  <img
                    src={resolveNewsImage(leadStory.hero_image_url, leadStory.category)}
                    alt={leadStory.headline}
                    className="size-full object-cover object-center transition-transform duration-700 group-hover:scale-105"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/30 to-transparent lg:bg-gradient-to-r lg:from-transparent lg:to-slate-950" />
                  <div className="absolute left-4 top-4 flex items-center gap-2">
                    <span className="rounded bg-amber-500 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-slate-950 shadow-md">
                      Lead Editorial · In-Universe Verified
                    </span>
                    {leadStory.source_event_id && (
                      <span className="rounded bg-slate-950/85 border border-emerald-500/40 px-2.5 py-1 text-[10px] font-mono text-emerald-300">
                        Event #{String(leadStory.source_event_id).slice(0, 10)}
                      </span>
                    )}
                  </div>
                </div>

                {/* Editorial text & facts */}
                <div className="lg:col-span-5 p-6 sm:p-10 flex flex-col justify-between text-left space-y-4">
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-3 text-xs text-amber-400 font-bold uppercase tracking-wider">
                      <span className="flex items-center gap-1">
                        <Clock size={12} />{" "}
                        {leadStory.created_at ? new Date(leadStory.created_at).toLocaleDateString() : "Today"}
                      </span>
                      {leadStory.established_facts?.world_day && (
                        <span>· World Day {leadStory.established_facts.world_day}</span>
                      )}
                      <span className="rounded bg-emerald-500/20 text-emerald-300 px-2 py-0.5 text-[9px] font-black">
                        {leadStory.grounding_report?.valid !== false ? "100% Fact-Grounded" : "Verified"}
                      </span>
                    </div>

                    <h2 className="gx-display text-3xl sm:text-5xl font-black uppercase tracking-tight text-white leading-tight group-hover:text-amber-300 transition-colors">
                      {leadStory.headline}
                    </h2>

                    {(leadStory.subheadline || leadStory.subhead) && (
                      <p className="text-sm font-semibold text-slate-300 italic">
                        {leadStory.subheadline || leadStory.subhead}
                      </p>
                    )}

                    <p className="text-xs sm:text-sm text-slate-300 line-clamp-4 leading-relaxed">
                      {leadStory.editorial_narration || leadStory.body}
                    </p>
                  </div>

                  <div className="pt-4 border-t border-white/10 flex items-center justify-between">
                    <span className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                      Inspect Provenance & Full Report <ExternalLink size={12} />
                    </span>
                    <span className="gx-mono text-[11px] text-slate-500">
                      {(leadStory.category || "editorial").replace(/_/g, " ").toUpperCase()}
                    </span>
                  </div>
                </div>
              </div>
            </article>
          )}

          {/* Supporting Reports Grid */}
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
                    <div className="relative h-44 w-full bg-slate-950 overflow-hidden">
                      <img
                        src={resolveNewsImage(story.hero_image_url, story.category)}
                        alt={story.headline}
                        className="size-full object-cover transition-transform duration-500 group-hover:scale-105"
                      />
                      <span className="absolute top-3 left-3 rounded bg-slate-950/85 border border-white/20 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-amber-300">
                        {(story.category || "wire").replace(/_/g, " ")}
                      </span>
                    </div>

                    <div className="p-5 flex-1 flex flex-col justify-between space-y-3">
                      <div className="space-y-2">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                          {story.created_at ? new Date(story.created_at).toLocaleDateString() : "Today"}
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

              <div
                className="overflow-hidden rounded-2xl border border-white/10 bg-slate-900/60 divide-y divide-white/5"
                data-testid="chronological-wire"
              >
                {wireStories.map((wire) => (
                  <div
                    key={wire.id}
                    onClick={() => setActiveStory(wire)}
                    className="group cursor-pointer p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 hover:bg-white/[0.03] transition-colors"
                  >
                    <div className="space-y-1 max-w-3xl">
                      <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase">
                        <span className="gx-mono text-emerald-400">
                          {wire.created_at
                            ? new Date(wire.created_at).toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit",
                              })
                            : "LIVE"}
                        </span>
                        <span>·</span>
                        <span>{wire.created_at ? new Date(wire.created_at).toLocaleDateString() : "Today"}</span>
                        <span>·</span>
                        <span className="text-amber-400">{(wire.category || "wire").replace(/_/g, " ")}</span>
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

      {/* Story Detail & Provenance Verification Modal */}
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
              <div className="flex items-center gap-2">
                <span className="rounded bg-amber-500/20 text-amber-300 px-3 py-1 text-xs font-black uppercase tracking-wider">
                  {(activeStory.category || "editorial").replace(/_/g, " ")}
                </span>
                <span className="rounded bg-emerald-500/15 text-emerald-300 px-2.5 py-1 text-[11px] font-bold">
                  Status: {activeStory.status || "published"}
                </span>
              </div>
              <button
                onClick={() => setActiveStory(null)}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            <div className="rounded-xl overflow-hidden max-h-72 w-full bg-slate-950">
              <img
                src={resolveNewsImage(activeStory.hero_image_url, activeStory.category)}
                alt=""
                className="size-full object-cover"
              />
            </div>

            <div className="space-y-3">
              <p className="gx-mono text-xs text-slate-400">
                Published {activeStory.created_at ? new Date(activeStory.created_at).toLocaleString() : "Today"}{" "}
                {activeStory.established_facts?.world_day
                  ? `· World Day ${activeStory.established_facts.world_day}`
                  : ""}
                {activeStory.source_event_id ? ` · Source Event: ${activeStory.source_event_id}` : ""}
              </p>
              <h2 className="gx-display text-3xl sm:text-4xl font-black uppercase text-white leading-tight">
                {activeStory.headline}
              </h2>
              {(activeStory.subheadline || activeStory.subhead) && (
                <p className="text-sm font-semibold text-slate-300 italic border-l-2 border-amber-400 pl-3 py-1">
                  {activeStory.subheadline || activeStory.subhead}
                </p>
              )}
            </div>

            <div className="text-sm text-slate-200 leading-relaxed space-y-4 whitespace-pre-line pt-2">
              {activeStory.editorial_narration || activeStory.body}
            </div>

            {/* Verified Facts & Grounding Report Breakdown */}
            {activeStory.established_facts && Object.keys(activeStory.established_facts).length > 0 && (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-400 uppercase tracking-wider">
                    <CheckCircle2 size={14} /> Verified Grounded Ledger & Simulation Facts
                  </div>
                  <span className="text-[10px] font-mono text-emerald-300">
                    Unverified Numbers: {activeStory.grounding_report?.unverified_numbers?.length || 0}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs text-slate-300 pt-1">
                  {Object.entries(activeStory.established_facts).map(([k, v]: any) => (
                    <div key={k} className="p-2 rounded bg-slate-950/60 border border-white/5">
                      <span className="text-slate-500 uppercase text-[10px] block">{k.replace(/_/g, " ")}</span>
                      <span className="font-mono font-bold text-white">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Editorial Governance Actions */}
            <div className="flex items-center justify-between gap-3 pt-4 border-t border-white/10">
              <div className="text-[11px] text-slate-400">
                Editorial Governance · Authoritative Provenance Controls
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleEditorialStatus(activeStory.id, "approved")}
                  className="px-3.5 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-xs font-bold flex items-center gap-1.5"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" /> Certify Fact Check
                </button>
                <button
                  type="button"
                  onClick={() => handleEditorialStatus(activeStory.id, "retracted")}
                  className="px-3.5 py-2 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-300 text-xs font-bold flex items-center gap-1.5"
                >
                  <AlertOctagon className="w-3.5 h-3.5" /> Retract Story
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Newsroom;
