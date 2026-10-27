import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
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
  Gift,
  Plus,
  Trash2,
  CheckCircle,
  ExternalLink,
  ChevronRight,
  Sparkles,
} from "lucide-react";

export function ClubStory() {
  const { clubId: routeClubId } = useParams<{ clubId?: string }>();
  const { active } = useActiveClub();
  const clubId = routeClubId || active?.club_id;
  const qc = useQueryClient();

  const { data, isLoading } = useClubStory(clubId);
  const { data: clubProfile } = useClub(clubId);
  const [activeTab, setActiveTab] = useState<
    "timeline" | "issues" | "relationships" | "watchlist" | "schedule" | "legacy"
  >("timeline");

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

  if (isLoading || !data) {
    return (
      <div className="py-24 text-center text-slate-500">
        <div className="inline-block w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full animate-spin mb-3"></div>
        <p className="text-sm">Compiling Club Chronicle & World History...</p>
      </div>
    );
  }

  const {
    club_name,
    is_owner,
    privacy_redacted,
    crest_url,
    prestige,
    world_day,
    timeline = [],
    unresolved_issues = [],
    relationships = {},
    scouting_watchlist = [],
    schedule = {},
    achievements = [],
    owner_legacy = {},
  } = data;

  const staff = relationships.staff || [];
  const players = relationships.players || [];
  const recentMatches = schedule.recent || [];
  const upcomingMatches = schedule.upcoming || [];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
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
              World match records, achievements, and public milestones are synchronized across this save.
              Confidential scouting watchlists, internal contract expectations, and private owner inbox items are isolated and
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
            <img
              src={crest_url}
              alt={club_name}
              className="w-full h-full object-contain"
              onError={(e) => {
                (e.target as HTMLElement).style.display = "none";
              }}
            />
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-center md:justify-start space-x-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20">
                {is_owner ? "Your Club" : "Opponent Club"}
              </span>
              <span className="text-xs text-slate-400">World Day {world_day}</span>
            </div>
            <h1 className="text-3xl font-extrabold text-white">{club_name}</h1>
            <p className="text-xs text-slate-400">
              {owner_legacy.era_title || "Modern Football Era"} · Prestige Level {prestige}/100
            </p>
          </div>
        </div>

        {/* Legacy Benchmarks */}
        <div className="grid grid-cols-3 gap-3 shrink-0 text-center w-full md:w-auto">
          <div className="bg-slate-950/60 border border-slate-800 rounded-xl px-4 py-3">
            <div className="text-[10px] uppercase font-bold text-slate-400">Honors</div>
            <div className="text-xl font-bold text-amber-400 mt-0.5">{achievements.length}</div>
          </div>
          <div className="bg-slate-950/60 border border-slate-800 rounded-xl px-4 py-3">
            <div className="text-[10px] uppercase font-bold text-slate-400">Prestige</div>
            <div className="text-xl font-bold text-emerald-400 mt-0.5">{prestige}</div>
          </div>
          <div className="bg-slate-950/60 border border-slate-800 rounded-xl px-4 py-3">
            <div className="text-[10px] uppercase font-bold text-slate-400">Squad</div>
            <div className="text-xl font-bold text-blue-400 mt-0.5">{players.length}</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center space-x-2 border-b border-slate-800 pb-3 overflow-x-auto no-scrollbar">
        {[
          { key: "timeline", label: "Timeline & Lore", icon: Clock },
          { key: "issues", label: `Unresolved Issues (${unresolved_issues.length})`, icon: Shield, hidden: privacy_redacted },
          { key: "relationships", label: "Staff & Squad", icon: Users },
          { key: "watchlist", label: `Scouting Dossier (${scouting_watchlist.length})`, icon: Search, hidden: privacy_redacted },
          { key: "schedule", label: "Save Fixtures", icon: Calendar },
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
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-colors whitespace-nowrap ${
                  active
                    ? "bg-amber-500 text-slate-950 shadow"
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
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-white">Chronological Club Events</h2>
            <span className="text-xs text-slate-400">Verified transactions & pitch outcomes</span>
          </div>

          {timeline.length === 0 ? (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-12 text-center text-slate-500 text-xs">
              No milestone events recorded yet. Complete private jet acquisitions, facility upgrades, or match days to populate the timeline.
            </div>
          ) : (
            <div className="relative pl-6 border-l-2 border-slate-800 space-y-6">
              {timeline.map((item: any, i: number) => {
                const isBroadcast = item.type === "broadcast";
                return (
                  <div key={item.id || i} className="relative group">
                    {/* Bullet */}
                    <div className="absolute -left-[31px] top-1.5 w-4 h-4 rounded-full bg-slate-950 border-2 border-amber-400 flex items-center justify-center">
                      <div className="w-1.5 h-1.5 rounded-full bg-amber-400"></div>
                    </div>

                    <div className="bg-slate-900/70 border border-slate-800/80 rounded-xl p-4 space-y-2 hover:border-slate-700 transition-colors">
                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <span className="uppercase font-semibold text-amber-400 tracking-wider text-[10px]">
                          {item.category?.replace(/_/g, " ")}
                        </span>
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

      {/* TAB CONTENT: UNRESOLVED ISSUES */}
      {activeTab === "issues" && !privacy_redacted && (
        <div className="space-y-4">
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
                          <span>Due: {new Date(issue.deadline_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
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
        <div className="space-y-8">
          {/* Executive & Staff */}
          <div className="space-y-3">
            <h2 className="text-base font-bold text-white">Club Leadership & Technical Staff</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {staff.map((s: any, idx: number) => (
                <div key={idx} className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-2">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="font-semibold text-amber-400 uppercase text-[10px]">{s.role}</span>
                    <span>Rating: {s.rating}/99</span>
                  </div>
                  <h3 className="text-sm font-bold text-white">{s.name}</h3>
                  <p className="text-xs text-slate-400">Mentality: {s.mentality}</p>
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
                  key={p.id}
                  className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center space-x-4 hover:border-slate-700 transition-colors"
                >
                  <img
                    src={p.portrait_url}
                    alt={p.name}
                    className="w-14 h-14 rounded-xl object-cover bg-slate-950 border border-white/10 shrink-0"
                    onError={(e) => {
                      (e.target as HTMLElement).style.display = "none";
                    }}
                  />

                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-slate-800 text-slate-300">
                        {p.position}
                      </span>
                      <span className="text-xs font-mono text-emerald-400 font-bold">{p.rating} OVR</span>
                    </div>

                    <h4 className="text-sm font-bold text-white truncate">{p.name}</h4>

                    {/* Morale Bar */}
                    <div className="space-y-0.5">
                      <div className="flex justify-between text-[10px] text-slate-400">
                        <span>Morale</span>
                        <span>{p.morale}%</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            p.morale > 75 ? "bg-emerald-400" : p.morale > 50 ? "bg-amber-400" : "bg-red-400"
                          }`}
                          style={{ width: `${Math.min(100, p.morale)}%` }}
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
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Confidential Scouting Dossier</h2>
              <p className="text-xs text-slate-400">Private recruitment targets isolated to club leadership</p>
            </div>
            {is_owner && (
              <button
                onClick={() => setIsAddWatchlistOpen(true)}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition-colors"
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
                      <div className="text-sm font-bold text-emerald-400">{w.current_rating} → {w.potential_rating} POT</div>
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
        <div className="space-y-6">
          <h2 className="text-lg font-bold text-white">Save Match History & Fixtures</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Upcoming */}
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-amber-400 uppercase tracking-wider">Upcoming Fixtures</h3>
              {upcomingMatches.length === 0 ? (
                <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-xs">
                  No scheduled fixtures.
                </div>
              ) : (
                upcomingMatches.map((m: any) => (
                  <div key={m.id} className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
                    <span className="text-xs font-semibold text-white">{m.home_name} vs {m.away_name}</span>
                    <span className="text-[11px] text-slate-400">Round {m.round}</span>
                  </div>
                ))
              )}
            </div>

            {/* Recent */}
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-emerald-400 uppercase tracking-wider">Recent Results</h3>
              {recentMatches.length === 0 ? (
                <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-xs">
                  No completed fixtures recorded.
                </div>
              ) : (
                recentMatches.map((m: any) => (
                  <div key={m.id} className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
                    <span className="text-xs font-semibold text-white">{m.home_name} {m.home_goals} - {m.away_goals} {m.away_name}</span>
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
        <div className="space-y-6">
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4">
            <h2 className="text-lg font-bold text-white">Boardroom Honors & Legacy</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {achievements.map((ach: any) => (
                <div key={ach.id} className="bg-slate-950/70 border border-amber-500/20 rounded-xl p-4 flex items-start space-x-3">
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
