import React, { useEffect, useState } from "react";
import { useParams, Link, useLocation } from "react-router-dom";
import { useClubStory, useActiveClub, useClub, fmt } from "@/lib/owner";
import { api } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  Shield,
  ShieldAlert,
  Clock,
  Award,
  Users,
  Search,
  Calendar,
  Plus,
  Trash2,
  CheckCircle,
  ExternalLink,
  ChevronRight,
  Sparkles,
  Newspaper,
  Inbox,
  Gauge,
  Megaphone,
  Flame,
  Trophy,
  Sprout,
  Swords,
  History,
  AlertTriangle,
} from "lucide-react";

export function ClubStory() {
  const { clubId: routeClubId } = useParams<{ clubId?: string }>();
  const { active } = useActiveClub();
  const clubId = routeClubId || active?.club_id;
  const qc = useQueryClient();

  const { data, isLoading, isError, refetch } = useClubStory(clubId);
  const { data: clubProfile } = useClub(clubId);
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const tabParam = searchParams.get("tab");
  const wantsLegacy =
    location.pathname.includes("trophies") ||
    location.pathname.includes("dynasty") ||
    tabParam === "legacy" ||
    location.hash === "#legacy";
  const wantsSupporters = tabParam === "supporters" || location.hash === "#supporters";
  const wantsArchive = tabParam === "archive" || location.hash === "#archive";

  const [activeTab, setActiveTab] = useState<
    | "timeline"
    | "supporters"
    | "archive"
    | "issues"
    | "relationships"
    | "watchlist"
    | "schedule"
    | "dispatches"
    | "legacy"
  >(wantsLegacy ? "legacy" : wantsSupporters ? "supporters" : wantsArchive ? "archive" : "timeline");

  const [timelineCategoryFilter, setTimelineCategoryFilter] = useState<string>("all");

  // Supporter engagement state
  const [engageAction, setEngageAction] = useState<
    "public_statement" | "supporter_meeting" | "community_initiative" | "respond_to_concern" | "ticketing_decision"
  >("public_statement");
  const [engageStance, setEngageStance] = useState<string>("collaborative");
  const [engageMessage, setEngageMessage] = useState<string>(
    "We respect our supporters' heritage and are building sustainable long-term success together."
  );
  const [engageTicketTier, setEngageTicketTier] = useState<string>("standard");
  const [engageInvestment, setEngageInvestment] = useState<number>(300);
  const [isEngaging, setIsEngaging] = useState<boolean>(false);
  const [engageFeedback, setEngageFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (
      location.pathname.includes("trophies") ||
      location.pathname.includes("dynasty") ||
      tabParam === "legacy" ||
      location.hash === "#legacy"
    ) {
      setActiveTab("legacy");
    } else if (tabParam === "supporters" || location.hash === "#supporters") {
      setActiveTab("supporters");
    } else if (tabParam === "archive" || location.hash === "#archive") {
      setActiveTab("archive");
    }
  }, [location.pathname, location.search, location.hash, tabParam]);

  // Watchlist modal state
  const [isAddWatchlistOpen, setIsAddWatchlistOpen] = useState(false);
  const [targetName, setTargetName] = useState("");
  const [targetPosition, setTargetPosition] = useState("FWD");
  const [targetAge, setTargetAge] = useState(18);
  const [targetRating, setTargetRating] = useState(72);
  const [targetPotential, setTargetPotential] = useState(88);
  const [targetValue, setTargetValue] = useState(350);
  const [targetPriority, setTargetPriority] = useState("high");
  const [targetNotes, setTargetNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleAddWatchlist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clubId || !targetName) return;
    setIsSubmitting(true);
    try {
      await api.post(`/owner/clubs/${clubId}/watchlist`, {
        player_name: targetName,
        position: targetPosition,
        age: Number(targetAge),
        current_rating: Number(targetRating),
        potential_rating: Number(targetPotential),
        estimated_value_gtex: Number(targetValue),
        priority: targetPriority,
        scout_notes: targetNotes,
        recommendation: "Priority Target",
      });
      qc.invalidateQueries({ queryKey: ["story", clubId] });
      qc.invalidateQueries({ queryKey: ["watchlist", clubId] });
      setIsAddWatchlistOpen(false);
      setTargetName("");
      setTargetNotes("");
    } catch (err: any) {
      alert(err?.response?.data?.detail?.detail || "Failed to add target to watchlist.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemoveWatchlist = async (itemId: string) => {
    if (!clubId) return;
    if (!confirm("Remove this player from confidential scouting watchlist?")) return;
    try {
      await api.delete(`/owner/clubs/${clubId}/watchlist/${itemId}`);
      qc.invalidateQueries({ queryKey: ["story", clubId] });
      qc.invalidateQueries({ queryKey: ["watchlist", clubId] });
    } catch (err: any) {
      alert("Failed to remove watchlist item.");
    }
  };

  const handleEngageSupporters = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clubId || isEngaging) return;
    setIsEngaging(true);
    setEngageFeedback(null);
    try {
      const res = await api.post(`/owner/clubs/${clubId}/supporters/engage`, {
        action_type: engageAction,
        stance: engageStance,
        message: engageMessage,
        ticket_price_tier: engageAction === "ticketing_decision" ? engageTicketTier : undefined,
        community_investment_gtex: engageAction === "community_initiative" ? Number(engageInvestment) : 0,
      });
      const latestReaction = res.data?.recent_reactions?.[0];
      if (latestReaction?.contradiction_detected) {
        setEngageFeedback(
          `Contradiction detected by supporters: ${latestReaction.contradiction_reason || latestReaction.summary}`
        );
      } else {
        setEngageFeedback(
          latestReaction?.headline || "Supporter engagement recorded and sentiment updated across all segments."
        );
      }
      qc.invalidateQueries({ queryKey: ["story", clubId] });
      qc.invalidateQueries({ queryKey: ["supporters", clubId] });
      qc.invalidateQueries({ queryKey: ["club-history", clubId] });
    } catch (err: any) {
      setEngageFeedback(err?.response?.data?.detail?.detail || "Unable to complete supporter engagement action.");
    } finally {
      setIsEngaging(false);
    }
  };

  if (!clubId) {
    return (
      <div
        className="max-w-3xl mx-auto my-12 rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-10 text-center space-y-3"
        data-testid="club-story-empty"
      >
        <p className="text-base font-bold text-white">No Club Selected</p>
        <p className="text-xs text-slate-400">
          Claim or activate a club from the Control Center to view its institutional chronicle and living history.
        </p>
        <Link to="/app" className="inline-block px-4 py-2 rounded-xl bg-amber-500 text-slate-950 text-xs font-black">
          Return to Control Center
        </Link>
      </div>
    );
  }
  if (isError) {
    return (
      <div
        className="max-w-3xl mx-auto my-12 rounded-2xl border border-rose-500/30 bg-rose-950/20 p-10 text-center space-y-3"
        data-testid="club-story-error"
      >
        <p className="text-base font-bold text-white">Unable to Load Club Chronicle</p>
        <p className="text-xs text-rose-200/80">
          Institutional history and supporter sentiment could not be reached right now.
        </p>
        <button
          type="button"
          onClick={() => refetch()}
          className="px-4 py-2 rounded-xl bg-rose-500 hover:bg-rose-400 text-slate-950 text-xs font-black"
          data-testid="club-story-retry-btn"
        >
          Retry Chronicle
        </button>
      </div>
    );
  }
  if (isLoading || !data) {
    return (
      <div className="py-24 text-center text-slate-500" data-testid="club-story-loading">
        <div className="inline-block w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full animate-spin mb-3"></div>
        <p className="text-sm font-semibold">Compiling Club Chronicle & World History...</p>
      </div>
    );
  }

  // Normalize contract fields safely from both root-level and nested backend structures
  const club = data.club || {};
  const club_name = club.club_name || data.club_name || active?.club_name || "Club Chronicle";
  const crest_url = club.crest_url || data.crest_url || active?.crest_url;
  const world_day = club.world_day ?? data.world_day ?? active?.world_day ?? 1;
  const is_owner = data.is_owner ?? true;
  const privacy_redacted = data.privacy_redacted ?? false;
  const timeline = data.timeline || [];
  const unresolved_issues = data.unresolved_issues || [];
  const relationships = data.relationships || {};
  const scouting_watchlist = data.scouting_watchlist || [];
  const upcomingMatches = data.upcoming_schedule || data.schedule?.upcoming || [];
  const recentMatches = data.recent_results || data.schedule?.recent || [];
  const club_news = data.club_news || [];
  const achievements = data.achievements || [];
  const owner_legacy = data.owner_legacy || {};
  const prestige = owner_legacy.prestige ?? club.prestige ?? data.prestige ?? 50;

  // Supporter Ecosystem & Institutional Archive payloads
  const supportersData = data.supporters || {};
  const supProfile = supportersData.profile || {
    supporter_culture_label: "Community & Youth Traditionalists",
    overall_sentiment: 65,
    confidence_in_owner: 65,
    confidence_in_manager: 68,
    loyalty_index: 72,
    matchday_enthusiasm: 66,
    accumulated_frustration: 0,
    ticket_price_tier: "standard",
    active_protest_stage: "none",
    attendance_modifier_pct: 0,
    owner_credibility_score: 72,
  };
  const supSegments: any[] = supportersData.segments || [];
  const supAtmosphere = supportersData.matchday_atmosphere || {};
  const supReactions: any[] = supportersData.recent_reactions || [];
  const institutionalPulse = data.institutional_pulse || null;
  const reputationDims = data.reputation_dimensions || institutionalPulse?.reputation_dimensions || null;
  const unifiedTimeline: any[] = data.unified_timeline || institutionalPulse?.unified_timeline || [];

  const archiveData = data.institutional_archive || {};
  const seasonArchive: any[] = archiveData.season_archive || [];
  const managerialHistory: any[] = archiveData.managerial_history || [];
  const transferHistory: any[] = archiveData.transfer_history || [];
  const academyLegacy: any[] = archiveData.academy_legacy || [];
  const historicRivalries: any[] = archiveData.historic_rivalries || [];
  const clubRecords = archiveData.club_records || {};
  const narrativeChapters: any[] = archiveData.narrative_chapters || [];

  const filteredTimeline = timeline.filter((item: any) => {
    if (timelineCategoryFilter === "all") return true;
    return item.category === timelineCategoryFilter;
  });

  const manager = relationships.manager;
  const staff =
    relationships.staff ||
    (manager
      ? [
          {
            name: manager.name || "Head Coach",
            role: manager.role || "Head Coach",
            rating: manager.rating ?? 75,
            mentality: manager.mentality || "Tactical",
            reputation: manager.reputation ?? "Regional",
            portrait_url: manager.portrait_url,
          },
        ]
      : []);
  const players = relationships.players || [];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8" data-testid="club-story-screen">
      {/* Surface Demarcation & Navigation Bridge */}
      <nav aria-label="Club Surface Directory" className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
        <div className="flex items-center gap-2 rounded-xl border border-amber-400/40 bg-amber-400/10 px-3 py-2 text-amber-200 shadow-sm">
          <BookOpen className="h-4 w-4 shrink-0 text-amber-300" />
          <div className="min-w-0">
            <div className="text-[10px] uppercase font-black tracking-wider text-amber-400">Current Surface</div>
            <div className="truncate font-bold text-white">Club Chronicle</div>
          </div>
        </div>
        <Link
          to="/app/showroom"
          className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2 text-slate-300 hover:border-amber-400/40 hover:text-white transition-colors"
          data-testid="link-to-showroom"
        >
          <Sparkles className="h-4 w-4 shrink-0 text-amber-300" />
          <div className="min-w-0">
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Luxury Fleet</div>
            <div className="truncate font-bold">Owner Showroom</div>
          </div>
        </Link>
        <Link
          to="/app/newsroom"
          className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2 text-slate-300 hover:border-blue-400/40 hover:text-white transition-colors"
          data-testid="link-to-newsroom"
        >
          <Newspaper className="h-4 w-4 shrink-0 text-blue-400" />
          <div className="min-w-0">
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500">World Editorial</div>
            <div className="truncate font-bold">AI Newsroom</div>
          </div>
        </Link>
        <Link
          to="/app/inbox"
          className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2 text-slate-300 hover:border-purple-400/40 hover:text-white transition-colors"
          data-testid="link-to-inbox"
        >
          <Inbox className="h-4 w-4 shrink-0 text-purple-400" />
          <div className="min-w-0">
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Private Desk</div>
            <div className="truncate font-bold">Owner Decisions</div>
          </div>
        </Link>
        <Link
          to="/app"
          className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2 text-slate-300 hover:border-emerald-400/40 hover:text-white transition-colors"
          data-testid="link-to-control-center"
        >
          <Gauge className="h-4 w-4 shrink-0 text-emerald-400" />
          <div className="min-w-0">
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Daily Health</div>
            <div className="truncate font-bold">Control Center</div>
          </div>
        </Link>
      </nav>

      {/* Public profile button if available */}
      {clubProfile?.public_profile_slug && (
        <div className="flex justify-end">
          <Link
            to={`/club/${encodeURIComponent(clubProfile.public_profile_slug)}`}
            className="gx-btn gx-btn-secondary"
            data-testid="open-public-club-profile"
          >
            <ExternalLink className="h-3.5 w-3.5" /> View public club profile
          </Link>
        </div>
      )}

      {/* Privacy Isolation Alert for Shared Save Participants */}
      {privacy_redacted && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 flex items-start space-x-3 text-amber-200">
          <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <p className="font-semibold text-amber-300">Shared Save Participant View</p>
            <p className="text-slate-300">
              World match records, achievements, and public milestones are synchronized across this save. Confidential
              scouting watchlists, internal contract expectations, and private owner inbox items are isolated and
              redacted for non-owners.
            </p>
          </div>
        </div>
      )}

      {/* Hero Header */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 md:p-8 flex flex-col md:flex-row items-center md:items-start justify-between gap-6 relative overflow-hidden">
        <div className="flex flex-col md:flex-row items-center space-y-4 md:space-y-0 md:space-x-6 text-center md:text-left">
          {/* Crest */}
          <div className="w-24 h-24 rounded-2xl bg-slate-950 border-2 border-amber-500/30 overflow-hidden flex items-center justify-center shrink-0 shadow-lg p-2">
            {crest_url ? (
              <img
                src={crest_url}
                alt={club_name}
                className="w-full h-full object-contain"
                onError={(e) => {
                  (e.target as HTMLElement).style.display = "none";
                }}
              />
            ) : (
              <span className="text-2xl font-black text-amber-400 font-display">
                {(club_name || "GTX").slice(0, 3).toUpperCase()}
              </span>
            )}
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-center md:justify-start space-x-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20">
                {is_owner ? "Your Club" : "Opponent Club"}
              </span>
              <span className="text-xs text-slate-400">World Day {world_day}</span>
              {club.city && (
                <span className="text-xs text-slate-500">
                  · {club.city}
                  {club.country_code ? `, ${club.country_code}` : ""}
                </span>
              )}
            </div>
            <h1 className="text-3xl font-extrabold text-white" data-testid="club-story-title">
              {club_name}
            </h1>
            <p className="text-xs text-slate-400">
              {owner_legacy.tier || owner_legacy.era_label || "Modern Football Era"} · Prestige Level {prestige}/100 ·{" "}
              <span className="text-emerald-400 font-semibold">{supProfile.supporter_culture_label}</span>
            </p>
          </div>
        </div>

        {/* Legacy & Supporter Benchmarks */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 shrink-0 text-center w-full md:w-auto">
          <div className="bg-slate-950/60 border border-slate-800 rounded-xl px-4 py-3">
            <div className="text-[10px] uppercase font-bold text-slate-400">Honors</div>
            <div className="text-xl font-bold text-amber-400 mt-0.5">{achievements.length}</div>
          </div>
          <div className="bg-slate-950/60 border border-slate-800 rounded-xl px-4 py-3">
            <div className="text-[10px] uppercase font-bold text-slate-400">Win Rate</div>
            <div className="text-xl font-bold text-emerald-400 mt-0.5">{owner_legacy.win_rate_pct ?? 0}%</div>
          </div>
          <div className="bg-slate-950/60 border border-slate-800 rounded-xl px-4 py-3">
            <div className="text-[10px] uppercase font-bold text-slate-400">Fan Sentiment</div>
            <div className="text-xl font-bold text-cyan-400 mt-0.5">{supProfile.overall_sentiment}/100</div>
          </div>
          <div className="bg-slate-950/60 border border-slate-800 rounded-xl px-4 py-3">
            <div className="text-[10px] uppercase font-bold text-slate-400">Squad</div>
            <div className="text-xl font-bold text-blue-400 mt-0.5">{players.length}</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div
        className="flex items-center space-x-2 border-b border-slate-800 pb-3 overflow-x-auto no-scrollbar"
        data-testid="club-story-tabs"
      >
        {[
          { key: "timeline", label: "Timeline & Lore", icon: Clock },
          { key: "supporters", label: `Supporters & Atmosphere (${supSegments.length || 6})`, icon: Megaphone },
          { key: "archive", label: "Institutional Archive", icon: History },
          { key: "dispatches", label: `Club Dispatches (${club_news.length})`, icon: Newspaper },
          {
            key: "issues",
            label: `Unresolved Issues (${unresolved_issues.length})`,
            icon: Shield,
            hidden: privacy_redacted,
          },
          { key: "relationships", label: "Staff & Squad", icon: Users },
          {
            key: "watchlist",
            label: `Scouting Dossier (${scouting_watchlist.length})`,
            icon: Search,
            hidden: privacy_redacted,
          },
          { key: "schedule", label: `Save Fixtures (${upcomingMatches.length + recentMatches.length})`, icon: Calendar },
          { key: "legacy", label: "Owner Legacy", icon: Award },
        ]
          .filter((t) => !t.hidden)
          .map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as any)}
                data-testid={`tab-${tab.key}`}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-colors whitespace-nowrap ${
                  active
                    ? "bg-amber-500 text-slate-950 shadow font-bold"
                    : "text-slate-400 hover:text-white hover:bg-slate-900 border border-transparent"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
      </div>

      {/* TAB CONTENT: TIMELINE */}
      {activeTab === "timeline" && (
        <div className="space-y-4" data-testid="timeline-tab-content">
          {(reputationDims || unifiedTimeline.length > 0) && (
            <div
              className="rounded-xl border border-emerald-500/25 bg-slate-900/80 p-4 space-y-3"
              data-testid="unified-club-timeline-panel"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="text-[10px] font-black uppercase tracking-wider text-emerald-400">
                    Unified Living Club Pulse · Canonical Event Correlation
                  </div>
                  <div className="text-xs text-slate-300">
                    Every canonical decision, matchday reaction, press dispatch, and historical entry share one authoritative clock.
                  </div>
                </div>
                {reputationDims && (
                  <div className="flex flex-wrap gap-2 text-[11px]">
                    <span className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-emerald-300 font-bold">
                      Club Rep {reputationDims.overall_reputation_prestige}/100
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-cyan-300 font-bold">
                      Academy Identity {reputationDims.academy_and_youth_identity}/100
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-amber-300 font-bold">
                      Stability {reputationDims.institutional_stability}/100
                    </span>
                  </div>
                )}
              </div>
              {unifiedTimeline.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                  {unifiedTimeline.slice(0, 4).map((ut: any) => (
                    <div
                      key={ut.id}
                      className="rounded-lg bg-slate-950/75 border border-slate-800 p-3 space-y-1 text-xs"
                    >
                      <div className="flex items-center justify-between text-[10px]">
                        <span className="font-bold uppercase text-amber-400">
                          World Day {ut.world_day} · {String(ut.source_subsystem || ut.category || "club").replace(/_/g, " ")}
                        </span>
                        <span className="px-1.5 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
                          {(ut.projections || []).length} linked effects
                        </span>
                      </div>
                      <div className="font-semibold text-white truncate">{ut.title}</div>
                      <div className="flex flex-wrap gap-1 pt-0.5">
                        {ut.linked_supporter_event && (
                          <span className="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 text-[10px]">
                            Supporters ({ut.linked_supporter_event.overall_sentiment_delta >= 0 ? "+" : ""}
                            {ut.linked_supporter_event.overall_sentiment_delta})
                          </span>
                        )}
                        {(ut.linked_media_stories || []).length > 0 && (
                          <span className="px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-300 text-[10px]">
                            Media ({ut.linked_media_stories.length})
                          </span>
                        )}
                        {ut.linked_history_entry && (
                          <span className="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 text-[10px]">
                            Archive
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-white">Chronological Club Events & Institutional Ledger</h2>
              <span className="text-xs text-slate-400">
                Permanent club milestones, managerial transitions, transfers, academy debuts & pitch outcomes
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {[
                { key: "all", label: "All Events" },
                { key: "club_creation", label: "Founding" },
                { key: "managerial_change", label: "Managers" },
                { key: "player_signing", label: "Signings" },
                { key: "academy_debut", label: "Academy Debuts" },
                { key: "historic_rivalry", label: "Rivalries" },
                { key: "supporter_movement", label: "Supporters" },
              ].map((flt) => (
                <button
                  key={flt.key}
                  type="button"
                  onClick={() => setTimelineCategoryFilter(flt.key)}
                  className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                    timelineCategoryFilter === flt.key
                      ? "bg-amber-400 text-slate-950 font-bold"
                      : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
                  }`}
                >
                  {flt.label}
                </button>
              ))}
            </div>
          </div>

          {filteredTimeline.length === 0 ? (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-12 text-center text-slate-500 text-xs">
              No milestone events recorded yet. Complete showroom acquisitions, facility upgrades, or match days to
              populate the chronicle.
            </div>
          ) : (
            <div className="relative pl-6 border-l-2 border-slate-800 space-y-6">
              {filteredTimeline.map((item: any, i: number) => {
                return (
                  <div key={item.id || i} className="relative group">
                    {/* Bullet */}
                    <div className="absolute -left-[31px] top-1.5 w-4 h-4 rounded-full bg-slate-950 border-2 border-amber-400 flex items-center justify-center">
                      <div className="w-1.5 h-1.5 rounded-full bg-amber-400"></div>
                    </div>

                    <div className="bg-slate-900/70 border border-slate-800/80 rounded-xl p-4 space-y-2 hover:border-slate-700 transition-colors">
                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <div className="flex items-center gap-2">
                          <span className="uppercase font-semibold text-amber-400 tracking-wider text-[10px]">
                            {item.category?.replace(/_/g, " ")}
                          </span>
                          {item.world_day && (
                            <span className="text-[10px] text-slate-500">· World Day {item.world_day}</span>
                          )}
                          {item.is_major_milestone && (
                            <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[9px] font-bold uppercase">
                              Milestone
                            </span>
                          )}
                        </div>
                        {item.created_at && <span>{new Date(item.created_at).toLocaleDateString()}</span>}
                      </div>

                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-1">
                          <h3 className="text-sm font-bold text-white">{item.title}</h3>
                          <p className="text-xs text-slate-300">{item.summary}</p>
                        </div>

                        {item.image_url && (
                          <img
                            src={item.image_url}
                            alt={item.title}
                            className="w-12 h-12 rounded-lg object-cover border border-slate-800 shrink-0 bg-slate-950"
                            onError={(e) => {
                              (e.target as HTMLElement).style.display = "none";
                            }}
                          />
                        )}
                      </div>

                      {item.verified_price_gtex && Number(item.verified_price_gtex) > 0 && (
                        <div className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-mono">
                          <CheckCircle className="w-3 h-3" />
                          <span>Verified: {fmt(item.verified_price_gtex)} GTX</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: SUPPORTERS & ATMOSPHERE */}
      {activeTab === "supporters" && (
        <div className="space-y-8" data-testid="supporters-tab-content">
          {/* Active Protest / Campaign Banner if triggered */}
          {supProfile.active_protest_stage && supProfile.active_protest_stage !== "none" && (
            <div
              className="rounded-2xl border border-rose-500/40 bg-rose-950/30 p-5 flex items-start gap-4 text-rose-200"
              data-testid="supporter-protest-alert"
            >
              <AlertTriangle className="w-6 h-6 text-rose-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="text-[10px] font-black uppercase tracking-widest text-rose-400">
                  Active Supporter Campaign · Stage: {String(supProfile.active_protest_stage).replace(/_/g, " ")}
                </div>
                <h3 className="text-base font-bold text-white">
                  {supProfile.active_campaign_headline ||
                    "Supporter Groups Demand Accountability & Clear Institutional Direction"}
                </h3>
                <p className="text-xs text-slate-300">
                  Accumulated frustration ({supProfile.accumulated_frustration}/100) and recent decisions have triggered
                  organised supporter action. Attendance impact: {supProfile.attendance_modifier_pct}%.
                </p>
              </div>
            </div>
          )}

          {/* Supporter Overview KPIs */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <div className="text-[10px] uppercase font-bold text-slate-400">Overall Sentiment</div>
              <div className="text-2xl font-black text-emerald-400 mt-1">{supProfile.overall_sentiment}/100</div>
              <div className="text-[11px] text-slate-500 mt-0.5">Weighted across 6 segments</div>
            </div>
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <div className="text-[10px] uppercase font-bold text-slate-400">Owner Credibility</div>
              <div className="text-2xl font-black text-amber-400 mt-1">{supProfile.owner_credibility_score}/100</div>
              <div className="text-[11px] text-slate-500 mt-0.5">Statement vs action alignment</div>
            </div>
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <div className="text-[10px] uppercase font-bold text-slate-400">Loyalty Index</div>
              <div className="text-2xl font-black text-cyan-400 mt-1">{supProfile.loyalty_index}/100</div>
              <div className="text-[11px] text-slate-500 mt-0.5">Institutional attachment</div>
            </div>
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <div className="text-[10px] uppercase font-bold text-slate-400">Scar Tissue Memory</div>
              <div className="text-2xl font-black text-rose-400 mt-1">{supProfile.accumulated_frustration}/100</div>
              <div className="text-[11px] text-slate-500 mt-0.5">Dampens single-win recovery</div>
            </div>
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <div className="text-[10px] uppercase font-bold text-slate-400">Ticket Policy</div>
              <div className="text-lg font-black text-white uppercase mt-1">{supProfile.ticket_price_tier}</div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                Attendance mod: {supProfile.attendance_modifier_pct >= 0 ? "+" : ""}
                {supProfile.attendance_modifier_pct}%
              </div>
            </div>
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <div className="text-[10px] uppercase font-bold text-slate-400">Matchday Atmosphere</div>
              <div className="text-2xl font-black text-purple-400 mt-1">
                {supAtmosphere.crowd_intensity ?? supProfile.matchday_enthusiasm}/100
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">{supAtmosphere.chant_volume_db ?? 94} dB roar</div>
            </div>
          </div>

          {/* 6 Distinct Supporter Segments */}
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-bold text-white">Supporter Segments & Distinct Expectations</h2>
              <p className="text-xs text-slate-400">
                Different supporter groups interpret club decisions, ticket pricing, signings, and youth pathways
                differently.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="supporter-segments-grid">
              {supSegments.map((seg: any) => (
                <div
                  key={seg.segment_key}
                  data-testid={`segment-${seg.segment_key}`}
                  className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3 flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        {seg.population_share_pct}% Share · {fmt(seg.member_count)} Fans
                      </span>
                      <span
                        className={`text-[10px] font-black uppercase px-2 py-0.5 rounded ${
                          seg.sentiment >= 68
                            ? "bg-emerald-500/20 text-emerald-300"
                            : seg.sentiment >= 45
                            ? "bg-amber-500/20 text-amber-300"
                            : "bg-rose-500/20 text-rose-300"
                        }`}
                      >
                        {seg.status_label}
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-white">{seg.segment_name}</h3>
                    <p className="text-xs text-slate-400">{seg.expectations?.core_demand}</p>

                    <div className="space-y-1 pt-1">
                      <div className="flex justify-between text-[11px]">
                        <span className="text-slate-400">Sentiment</span>
                        <span className="font-mono font-bold text-white">{seg.sentiment}/100</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            seg.sentiment >= 68
                              ? "bg-emerald-400"
                              : seg.sentiment >= 45
                              ? "bg-amber-400"
                              : "bg-rose-400"
                          }`}
                          style={{ width: `${Math.min(100, seg.sentiment)}%` }}
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2 pt-2 text-[10px] text-slate-400">
                      <div className="bg-slate-950/60 rounded p-2">
                        <span className="block text-slate-500">Loyalty</span>
                        <span className="font-bold text-cyan-300">{seg.loyalty}/100</span>
                      </div>
                      <div className="bg-slate-950/60 rounded p-2">
                        <span className="block text-slate-500">Owner Trust</span>
                        <span className="font-bold text-amber-300">{seg.owner_approval}/100</span>
                      </div>
                      <div className="bg-slate-950/60 rounded p-2">
                        <span className="block text-slate-500">Scar Tissue</span>
                        <span className="font-bold text-rose-300">{seg.scar_tissue}/100</span>
                      </div>
                    </div>
                  </div>

                  {seg.recent_memory && seg.recent_memory.length > 0 && (
                    <div className="pt-3 border-t border-slate-800/80 text-[11px] text-slate-300">
                      <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Latest Memory</span>
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate">{seg.recent_memory[0].headline}</span>
                        <span
                          className={`font-mono font-bold shrink-0 ${
                            seg.recent_memory[0].delta >= 0 ? "text-emerald-400" : "text-rose-400"
                          }`}
                        >
                          {seg.recent_memory[0].delta >= 0 ? "+" : ""}
                          {seg.recent_memory[0].delta}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Matchday Atmosphere & Owner Engagement Console */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Matchday Atmosphere Presentation Layer */}
            <div className="bg-slate-900/85 border border-slate-800 rounded-2xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-black uppercase tracking-wider text-amber-400">
                    Matchday Presentation Layer
                  </div>
                  <h3 className="text-lg font-bold text-white">Stadium Atmosphere & Terrace Activity</h3>
                </div>
                <Flame className="w-5 h-5 text-amber-400" />
              </div>

              <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
                <div className="text-xs font-bold text-emerald-300">
                  {supAtmosphere.stadium_ambience || "Vibrant Home Support — Steady Chants from the Match-Going Core"}
                </div>
                <div className="text-[11px] text-slate-400">
                  Dominant Mood:{" "}
                  <b className="text-white uppercase">{String(supAtmosphere.dominant_mood || "committed").replace(/_/g, " ")}</b>{" "}
                  · Rivalry Heat: <b className="text-amber-300">{supAtmosphere.rivalry_intensity ?? 15}/100</b>
                </div>
              </div>

              {supAtmosphere.banners && supAtmosphere.banners.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[10px] font-bold uppercase text-slate-400">Visible Stadium Banners</div>
                  {supAtmosphere.banners.map((b: string, idx: number) => (
                    <div
                      key={idx}
                      className="px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs font-mono font-bold text-amber-200"
                    >
                      "{b}"
                    </div>
                  ))}
                </div>
              )}

              {supAtmosphere.chants && supAtmosphere.chants.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[10px] font-bold uppercase text-slate-400">Terrace Chants & Reactions</div>
                  {supAtmosphere.chants.map((c: string, idx: number) => (
                    <div key={idx} className="text-xs text-slate-300 italic">
                      ♪ "{c}"
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Owner Supporter Engagement Console */}
            {is_owner && (
              <div className="bg-slate-900/85 border border-slate-800 rounded-2xl p-6 space-y-4">
                <div>
                  <div className="text-[10px] font-black uppercase tracking-wider text-emerald-400">
                    Owner Engagement & Governance
                  </div>
                  <h3 className="text-lg font-bold text-white">Engage With Supporters</h3>
                  <p className="text-xs text-slate-400">
                    Statements that contradict actual club behaviour (such as promising affordable access while charging
                    exploitative prices) reduce credibility instead of restoring confidence.
                  </p>
                </div>

                <form onSubmit={handleEngageSupporters} className="space-y-3" data-testid="supporter-engage-form">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-semibold text-slate-300">Engagement Action</label>
                      <select
                        value={engageAction}
                        onChange={(e) => setEngageAction(e.target.value as any)}
                        data-testid="supporter-engage-action-select"
                        className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                      >
                        <option value="public_statement">Issue Public Club Statement</option>
                        <option value="supporter_meeting">Convene Supporter Trust Meeting</option>
                        <option value="community_initiative">Launch Community Initiative</option>
                        <option value="respond_to_concern">Respond to Supporter Concerns</option>
                        <option value="ticketing_decision">Update Matchday Ticket Pricing Policy</option>
                      </select>
                    </div>

                    {engageAction === "ticketing_decision" ? (
                      <div>
                        <label className="text-xs font-semibold text-slate-300">Ticket Pricing Tier</label>
                        <select
                          value={engageTicketTier}
                          onChange={(e) => setEngageTicketTier(e.target.value)}
                          data-testid="supporter-ticket-tier-select"
                          className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                        >
                          <option value="affordable">Affordable (Community Access)</option>
                          <option value="standard">Standard Matchday Rate</option>
                          <option value="premium">Premium Pricing</option>
                          <option value="exploitative">Exploitative Max Extraction</option>
                        </select>
                      </div>
                    ) : engageAction === "community_initiative" ? (
                      <div>
                        <label className="text-xs font-semibold text-slate-300">Community Commitment (GTX)</label>
                        <input
                          type="number"
                          min={100}
                          max={10000}
                          value={engageInvestment}
                          onChange={(e) => setEngageInvestment(Number(e.target.value))}
                          className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                        />
                      </div>
                    ) : (
                      <div>
                        <label className="text-xs font-semibold text-slate-300">Posture / Stance</label>
                        <select
                          value={engageStance}
                          onChange={(e) => setEngageStance(e.target.value)}
                          className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                        >
                          <option value="collaborative">Collaborative & Transparent</option>
                          <option value="concessional">Concessional & Reform-Minded</option>
                          <option value="ambitious">Ambitious & High-Standards</option>
                          <option value="dismissive">Dismissive / Defiant</option>
                        </select>
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300">Official Message / Policy Note</label>
                    <textarea
                      rows={2}
                      value={engageMessage}
                      onChange={(e) => setEngageMessage(e.target.value)}
                      data-testid="supporter-engage-message"
                      className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    />
                  </div>

                  {engageFeedback && (
                    <div
                      className="p-3 rounded-lg bg-slate-950 border border-amber-500/30 text-xs text-amber-200"
                      data-testid="supporter-engage-feedback"
                    >
                      {engageFeedback}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isEngaging}
                    data-testid="supporter-engage-submit"
                    className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition-colors"
                  >
                    {isEngaging ? "Recording..." : "Execute Supporter Engagement"}
                  </button>
                </form>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB CONTENT: INSTITUTIONAL ARCHIVE */}
      {activeTab === "archive" && (
        <div className="space-y-8" data-testid="archive-tab-content">
          {/* Fact-Grounded Historical Narrative Chapters */}
          <div className="space-y-3">
            <h2 className="text-lg font-bold text-white">Historical Storytelling & Defining Eras</h2>
            <p className="text-xs text-slate-400">
              Generated strictly from verified club milestones, competition finishes, managerial tenures, and academy
              breakthroughs.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="archive-narrative-chapters">
              {narrativeChapters.map((ch: any) => (
                <div
                  key={ch.chapter_key}
                  className="bg-slate-900/80 border border-amber-500/20 rounded-2xl p-5 space-y-2"
                >
                  <div className="text-[10px] font-black uppercase tracking-wider text-amber-400">{ch.era_label}</div>
                  <h3 className="text-base font-bold text-white">{ch.title}</h3>
                  <p className="text-xs text-slate-300 leading-relaxed">{ch.narrative}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Club All-Time Records */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Trophy className="w-4 h-4 text-amber-400" /> All-Time Institutional Club Records
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
              <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3">
                <span className="text-[10px] uppercase text-slate-500 block">Most Appearances</span>
                <span className="font-bold text-white block mt-1">
                  {clubRecords.most_appearances?.player_name || "—"}
                </span>
                <span className="text-[11px] text-emerald-400">
                  {clubRecords.most_appearances ? `${clubRecords.most_appearances.appearances} apps` : "No matches yet"}
                </span>
              </div>
              <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3">
                <span className="text-[10px] uppercase text-slate-500 block">Leading Goalscorer</span>
                <span className="font-bold text-white block mt-1">
                  {clubRecords.all_time_top_scorer?.player_name || "—"}
                </span>
                <span className="text-[11px] text-amber-400">
                  {clubRecords.all_time_top_scorer ? `${clubRecords.all_time_top_scorer.goals} goals` : "0 goals"}
                </span>
              </div>
              <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3">
                <span className="text-[10px] uppercase text-slate-500 block">Biggest Victory</span>
                <span className="font-bold text-white block mt-1">
                  {clubRecords.biggest_victory ? clubRecords.biggest_victory.score : "—"}
                </span>
                <span className="text-[11px] text-slate-400 truncate block">
                  {clubRecords.biggest_victory ? `vs ${clubRecords.biggest_victory.opponent}` : "No wins yet"}
                </span>
              </div>
              <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3">
                <span className="text-[10px] uppercase text-slate-500 block">Heaviest Defeat</span>
                <span className="font-bold text-white block mt-1">
                  {clubRecords.heaviest_defeat ? clubRecords.heaviest_defeat.score : "—"}
                </span>
                <span className="text-[11px] text-slate-400 truncate block">
                  {clubRecords.heaviest_defeat ? `vs ${clubRecords.heaviest_defeat.opponent}` : "Unbeaten"}
                </span>
              </div>
              <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3">
                <span className="text-[10px] uppercase text-slate-500 block">Record Signing</span>
                <span className="font-bold text-white block mt-1">
                  {clubRecords.record_signing?.player_name || "—"}
                </span>
                <span className="text-[11px] text-cyan-400">
                  {clubRecords.record_signing ? `${fmt(clubRecords.record_signing.fee_gtex)} GTX` : "—"}
                </span>
              </div>
              <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3">
                <span className="text-[10px] uppercase text-slate-500 block">Record Sale</span>
                <span className="font-bold text-white block mt-1">{clubRecords.record_sale?.player_name || "—"}</span>
                <span className="text-[11px] text-emerald-400">
                  {clubRecords.record_sale ? `${fmt(clubRecords.record_sale.fee_gtex)} GTX` : "—"}
                </span>
              </div>
            </div>
          </div>

          {/* Managerial History & Season Archive Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Managerial History */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4">
              <h3 className="text-base font-bold text-white">Managerial Roll of Honour & Tenures</h3>
              {managerialHistory.length === 0 ? (
                <p className="text-xs text-slate-500">No managerial tenures recorded yet.</p>
              ) : (
                <div className="space-y-3" data-testid="managerial-history-list">
                  {managerialHistory.map((m: any) => (
                    <div key={m.id} className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-bold text-white">{m.manager_name}</span>
                        <span
                          className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                            m.status === "active"
                              ? "bg-emerald-500/20 text-emerald-300"
                              : "bg-slate-800 text-slate-400"
                          }`}
                        >
                          {m.status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300">{m.tenure_summary}</p>
                      <div className="text-[11px] text-slate-400 font-mono">
                        Record: {m.wins}W-{m.draws}D-{m.losses}L ({m.win_rate_pct}% win) · Trophies: {m.trophies_won}
                        {m.departure_reason ? ` · Reason: ${m.departure_reason.replace(/_/g, " ")}` : ""}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Season Archive */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4">
              <h3 className="text-base font-bold text-white">Season Campaign Archive</h3>
              {seasonArchive.length === 0 ? (
                <p className="text-xs text-slate-500">
                  Complete your first competition season to populate the permanent season archive.
                </p>
              ) : (
                <div className="space-y-3" data-testid="season-archive-list">
                  {seasonArchive.map((s: any) => (
                    <div key={s.id} className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-bold text-white">
                          {s.season_label} · {s.competition_name}
                        </span>
                        <span className="text-xs font-black text-amber-400">
                          Position #{s.final_position} ({s.promotion_status.replace(/_/g, " ")})
                        </span>
                      </div>
                      <p className="text-xs text-slate-300">{s.narrative_summary}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Academy Legacy, Transfer Ledger & Historic Rivalries */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Academy Legacy */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Sprout className="w-4 h-4 text-emerald-400" /> Academy Graduates & Debuts ({academyLegacy.length})
              </h3>
              {academyLegacy.length === 0 ? (
                <p className="text-xs text-slate-500">Promote academy prospects and play them in matches to record debuts.</p>
              ) : (
                <div className="space-y-2.5">
                  {academyLegacy.slice(0, 6).map((g: any) => (
                    <div key={g.id} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs space-y-1">
                      <div className="flex justify-between font-bold text-white">
                        <span>
                          {g.player_name} ({g.position})
                        </span>
                        <span className="text-emerald-400">{g.current_rating} OVR</span>
                      </div>
                      <div className="text-[11px] text-slate-400">
                        Apps: {g.first_team_appearances} · Goals: {g.first_team_goals} ·{" "}
                        {g.debut_opponent_name ? `Debut vs ${g.debut_opponent_name}` : "Awaiting senior debut"}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Transfer History */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3">
              <h3 className="text-sm font-bold text-white">Transfer History Ledger ({transferHistory.length})</h3>
              {transferHistory.length === 0 ? (
                <p className="text-xs text-slate-500">No player arrivals or departures recorded yet.</p>
              ) : (
                <div className="space-y-2.5">
                  {transferHistory.slice(0, 6).map((t: any) => (
                    <div key={t.id} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs space-y-1">
                      <div className="flex justify-between font-bold text-white">
                        <span>
                          {t.player_name} ({t.overall_rating} OVR)
                        </span>
                        <span className={t.direction === "arrival" ? "text-cyan-400" : "text-amber-400"}>
                          {t.direction.toUpperCase()} · {fmt(t.fee_gtex)} GTX
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400">{t.narrative_note}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Historic Rivalries */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Swords className="w-4 h-4 text-rose-400" /> Historic Rivalries ({historicRivalries.length})
              </h3>
              {historicRivalries.length === 0 ? (
                <p className="text-xs text-slate-500">
                  Rivalries evolve organically from repeated competition encounters and high-stakes clashes.
                </p>
              ) : (
                <div className="space-y-2.5" data-testid="historic-rivalries-list">
                  {historicRivalries.slice(0, 6).map((r: any) => (
                    <div key={r.id} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs space-y-1">
                      <div className="flex justify-between font-bold text-white">
                        <span>vs {r.rival_club_name}</span>
                        <span className="text-rose-400 uppercase text-[10px]">
                          {r.rivalry_tier.replace(/_/g, " ")} ({r.intensity_score}/100)
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        Played {r.matches_played}: {r.wins}W-{r.draws}D-{r.losses}L (GF {r.goals_for} / GA{" "}
                        {r.goals_against})
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: CLUB DISPATCHES */}
      {activeTab === "dispatches" && (
        <div className="space-y-4" data-testid="dispatches-tab-content">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Verified Club Dispatches</h2>
              <p className="text-xs text-slate-400">
                Public announcements and editorial reports grounded in club milestones
              </p>
            </div>
            <Link
              to="/app/newsroom"
              className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1 font-semibold"
            >
              <span>Explore All World News</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          </div>

          {club_news.length === 0 ? (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-12 text-center text-slate-500 text-xs">
              <Newspaper className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              No public news dispatches recorded for this club yet. Match outcomes and major acquisitions will publish
              dispatches here.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {club_news.map((art: any) => (
                <article
                  key={art.id}
                  className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden hover:border-amber-400/40 transition-colors flex flex-col justify-between"
                >
                  <div className="p-4 space-y-2">
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-blue-500/10 text-blue-300 border border-blue-500/20">
                        {art.category?.replace(/_/g, " ")}
                      </span>
                      {art.created_at && <span>{new Date(art.created_at).toLocaleDateString()}</span>}
                    </div>

                    <h3 className="text-sm font-bold text-white leading-snug">{art.headline}</h3>
                    {art.subheadline && <p className="text-xs text-slate-400">{art.subheadline}</p>}
                    {art.editorial_narration && (
                      <p className="text-xs text-slate-300 line-clamp-3 bg-slate-950/40 p-2.5 rounded border border-slate-800/60 italic">
                        "{art.editorial_narration}"
                      </p>
                    )}
                  </div>

                  <div className="px-4 py-3 border-t border-slate-800/80 flex items-center justify-between text-xs bg-slate-950/30">
                    <span className="text-[10px] text-emerald-400 font-medium flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" /> Grounded dispatch
                    </span>
                    <Link
                      to="/app/newsroom"
                      className="text-amber-400 hover:text-amber-300 font-bold flex items-center gap-1"
                    >
                      Read full story <ChevronRight className="w-3 h-3" />
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: UNRESOLVED ISSUES */}
      {activeTab === "issues" && !privacy_redacted && (
        <div className="space-y-4" data-testid="issues-tab-content">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-white">Pending Boardroom Decisions & Deadlines</h2>
            <Link to="/app/inbox" className="text-xs text-amber-400 hover:text-amber-300 flex items-center space-x-1">
              <span>Open Personal Inbox</span>
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>

          {unresolved_issues.length === 0 ? (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-12 text-center text-slate-500 text-xs">
              <CheckCircle className="w-8 h-8 text-emerald-500 mx-auto mb-2 opacity-80" />
              All boardroom decisions and player matters are up to date.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {unresolved_issues.map((issue: any) => (
                <div
                  key={issue.id}
                  className="bg-slate-900/80 border border-amber-500/20 rounded-xl p-5 space-y-3 flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        {issue.category?.replace(/_/g, " ")}
                      </span>
                      {issue.deadline_at && (
                        <span className="text-[11px] text-amber-400 font-mono flex items-center space-x-1">
                          <Clock className="w-3 h-3" />
                          <span>
                            Due:{" "}
                            {new Date(issue.deadline_at).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </span>
                      )}
                    </div>

                    <h3 className="text-sm font-bold text-white">{issue.title}</h3>
                    <p className="text-xs text-slate-300">{issue.body || issue.what}</p>
                  </div>

                  <div className="pt-3 border-t border-slate-800 flex justify-end">
                    <Link
                      to="/app/inbox"
                      className="text-xs bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-3 py-1.5 rounded transition-colors"
                    >
                      Resolve in Inbox
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: RELATIONSHIPS */}
      {activeTab === "relationships" && (
        <div className="space-y-8" data-testid="relationships-tab-content">
          {/* Executive & Staff */}
          <div className="space-y-3">
            <h2 className="text-base font-bold text-white">Club Leadership & Technical Staff</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {staff.map((s: any, idx: number) => (
                <div key={idx} className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-2">
                  <div className="flex items-center gap-3">
                    {s.portrait_url ? (
                      <img
                        src={s.portrait_url}
                        alt=""
                        className="h-12 w-12 rounded-full object-cover bg-slate-800 shrink-0"
                      />
                    ) : null}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <span className="font-semibold text-amber-400 uppercase text-[10px]">
                          {s.role || "Technical Staff"}
                        </span>
                        <span>Rating: {s.rating ?? 75}/99</span>
                      </div>
                      <h3 className="text-sm font-bold text-white">{s.name}</h3>
                      <p className="text-xs text-slate-400">
                        Mentality: {s.mentality || "Tactical"} · {s.reputation || "Professional"}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Squad Roster with Portraits & Morale */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white">Squad Roster & Player Morale</h2>
              <span className="text-xs text-slate-400">High morale boosts pitch performance</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {players.map((p: any) => (
                <div
                  key={p.id || p.player_id}
                  className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center space-x-4 hover:border-slate-700 transition-colors"
                >
                  {p.portrait_url ? (
                    <img
                      src={p.portrait_url}
                      alt={p.name}
                      className="w-14 h-14 rounded-xl object-cover bg-slate-950 border border-white/10 shrink-0"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = "none";
                      }}
                    />
                  ) : (
                    <div className="w-14 h-14 rounded-xl bg-slate-800 flex items-center justify-center text-sm font-bold text-amber-400 shrink-0">
                      {(p.name || "?").slice(0, 2).toUpperCase()}
                    </div>
                  )}

                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-slate-800 text-slate-300">
                        {p.position || "Player"}
                      </span>
                      <span className="text-xs font-mono text-emerald-400 font-bold">
                        {p.rating ?? p.overall_rating ?? "—"} OVR
                      </span>
                    </div>

                    <h4 className="text-sm font-bold text-white truncate">{p.name}</h4>
                    {p.is_regen && (
                      <span className="inline-block px-1.5 py-0.2 rounded text-[9px] font-black uppercase tracking-wider bg-purple-500/10 text-purple-300 border border-purple-500/20">
                        Academy Regen
                      </span>
                    )}

                    {/* Morale Bar */}
                    <div className="space-y-0.5">
                      <div className="flex justify-between text-[10px] text-slate-400">
                        <span>Morale</span>
                        <span>{p.morale ?? 75}%</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            (p.morale ?? 75) > 75
                              ? "bg-emerald-400"
                              : (p.morale ?? 75) > 50
                              ? "bg-amber-400"
                              : "bg-red-400"
                          }`}
                          style={{ width: `${Math.min(100, p.morale ?? 75)}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: WATCHLIST */}
      {activeTab === "watchlist" && !privacy_redacted && (
        <div className="space-y-4" data-testid="watchlist-tab-content">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Confidential Scouting Dossier</h2>
              <p className="text-xs text-slate-400">Private recruitment targets isolated to club leadership</p>
            </div>
            {is_owner && (
              <button
                onClick={() => setIsAddWatchlistOpen(true)}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition-colors"
                data-testid="add-scouting-target-button"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Target</span>
              </button>
            )}
          </div>

          {scouting_watchlist.length === 0 ? (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-12 text-center text-slate-500 text-xs">
              No recruitment targets currently tracked. Add players to scout their form and release clauses.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {scouting_watchlist.map((w: any) => (
                <div
                  key={w.id}
                  className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-3 relative group"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-slate-800 text-slate-300">
                          {w.position}
                        </span>
                        <span className="text-xs text-slate-400">{w.age} yrs</span>
                        <span className="px-1.5 py-0.2 rounded text-[9px] uppercase font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          {w.priority} priority
                        </span>
                      </div>
                      <h3 className="text-base font-bold text-white mt-1">{w.player_name}</h3>
                    </div>

                    <div className="text-right">
                      <div className="text-sm font-bold text-emerald-400">
                        {w.current_rating} → {w.potential_rating} POT
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">{fmt(w.estimated_value_gtex)} GTX</div>
                    </div>
                  </div>

                  {w.scout_notes && (
                    <div className="text-xs text-slate-300 bg-slate-950/60 p-2.5 rounded border border-slate-800 italic">
                      "{w.scout_notes}"
                    </div>
                  )}

                  <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-800/80">
                    <span className="text-amber-400 font-medium">{w.recommendation || "Monitor closely"}</span>
                    {is_owner && (
                      <button
                        onClick={() => handleRemoveWatchlist(w.id)}
                        className="text-slate-500 hover:text-red-400 p-1 rounded transition-colors"
                        title="Remove target"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: SCHEDULE */}
      {activeTab === "schedule" && (
        <div className="space-y-6" data-testid="schedule-tab-content">
          <h2 className="text-lg font-bold text-white">Save Match History & Fixtures</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Upcoming */}
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-amber-400 uppercase tracking-wider">
                Upcoming Fixtures ({upcomingMatches.length})
              </h3>
              {upcomingMatches.length === 0 ? (
                <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-xs">
                  No scheduled fixtures.
                </div>
              ) : (
                upcomingMatches.map((m: any) => (
                  <div
                    key={m.id}
                    className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between"
                  >
                    <span className="text-xs font-semibold text-white">
                      {m.home_name} vs {m.away_name}
                    </span>
                    <span className="text-[11px] text-slate-400">Round {m.round}</span>
                  </div>
                ))
              )}
            </div>

            {/* Recent */}
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-emerald-400 uppercase tracking-wider">
                Recent Results ({recentMatches.length})
              </h3>
              {recentMatches.length === 0 ? (
                <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-xs">
                  No completed fixtures recorded.
                </div>
              ) : (
                recentMatches.map((m: any) => (
                  <div
                    key={m.id}
                    className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between"
                  >
                    <span className="text-xs font-semibold text-white">
                      {m.home_name} {m.home_goals} - {m.away_goals} {m.away_name}
                    </span>
                    <span className="text-[11px] text-emerald-400 font-mono">FT (R{m.round})</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: LEGACY */}
      {activeTab === "legacy" && (
        <div className="space-y-6" data-testid="legacy-tab-content">
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4">
            <h2 className="text-lg font-bold text-white">Boardroom Honors & Legacy</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {achievements.map((ach: any) => (
                <div
                  key={ach.id}
                  className="bg-slate-950/70 border border-amber-500/20 rounded-xl p-4 flex items-start space-x-3"
                >
                  <Award className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <h3 className="text-sm font-bold text-white">{ach.title}</h3>
                    <p className="text-xs text-slate-400 mt-0.5">{ach.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Add Watchlist Modal */}
      {isAddWatchlistOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white">Add Scouting Target</h3>
            <form onSubmit={handleAddWatchlist} className="space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-300">Player Name</label>
                <input
                  type="text"
                  required
                  value={targetName}
                  onChange={(e) => setTargetName(e.target.value)}
                  placeholder="e.g. Victor Boniface"
                  className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-slate-300">Position</label>
                  <select
                    value={targetPosition}
                    onChange={(e) => setTargetPosition(e.target.value)}
                    className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-400"
                  >
                    <option value="GK">GK</option>
                    <option value="DEF">DEF</option>
                    <option value="MID">MID</option>
                    <option value="FWD">FWD</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-300">Age</label>
                  <input
                    type="number"
                    value={targetAge}
                    onChange={(e) => setTargetAge(Number(e.target.value))}
                    className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-400"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs font-medium text-slate-300">Current OVR</label>
                  <input
                    type="number"
                    value={targetRating}
                    onChange={(e) => setTargetRating(Number(e.target.value))}
                    className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-400"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-300">Potential</label>
                  <input
                    type="number"
                    value={targetPotential}
                    onChange={(e) => setTargetPotential(Number(e.target.value))}
                    className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-400"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-300">Est. GTX</label>
                  <input
                    type="number"
                    value={targetValue}
                    onChange={(e) => setTargetValue(Number(e.target.value))}
                    className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-400"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300">Scout Notes</label>
                <textarea
                  value={targetNotes}
                  onChange={(e) => setTargetNotes(e.target.value)}
                  placeholder="Confidential tactical assessment..."
                  rows={3}
                  className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-400"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddWatchlistOpen(false)}
                  className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-lg text-xs font-bold bg-amber-500 hover:bg-amber-400 text-slate-950 transition-colors"
                >
                  {isSubmitting ? "Adding..." : "Add to Dossier"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
