import React, { useState, useMemo, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Award, Compass, Dna, Filter, Flame, Globe2, Search, ShieldAlert, Sparkles, Trophy, Users } from "lucide-react";
import { api } from "@/lib/api";
import { useActiveClub } from "@/lib/owner";
import { journeyLinks, readJourneyParams } from "@/lib/playerJourney";
import { RegenCard } from "@/components/gtex/RegenCard";
import { PlayerDossier } from "@/components/gtex/PlayerDossier";
import { Loading } from "@/components/gtex/ui";
import { toast } from "sonner";

export function RegenWorld() {
  const navigate = useNavigate();
  const location = useLocation();
  const { active: activeClub } = useActiveClub();

  const journeyParams = useMemo(() => readJourneyParams(location.search), [location.search]);

  const [tab, setTab] = useState<"feed" | "rising" | "bloodlines" | "rankings" | "hall">(() => {
    const params = new URLSearchParams(window.location.search);
    const t = params.get("tab");
    if (t === "rising" || t === "bloodlines" || t === "rankings" || t === "hall") return t;
    return "feed";
  });
  const [search, setSearch] = useState("");
  const [positionFilter, setPositionFilter] = useState("ALL");
  const [originFilter, setOriginFilter] = useState("ALL");
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(journeyParams.player);

  useEffect(() => {
    if (journeyParams.player && journeyParams.player !== selectedPlayerId) {
      setSelectedPlayerId(journeyParams.player);
    }
  }, [journeyParams.player]);

  const updateSelectedPlayer = (id: string | null) => {
    setSelectedPlayerId(id);
    const searchParams = new URLSearchParams(location.search);
    if (id) {
      searchParams.set("player", id);
    } else {
      searchParams.delete("player");
    }
    const nextSearch = searchParams.toString();
    navigate({ search: nextSearch ? `?${nextSearch}` : "" }, { replace: true });
  };

  const handleTabChange = (nextTab: "feed" | "rising" | "bloodlines" | "rankings" | "hall") => {
    setTab(nextTab);
    const searchParams = new URLSearchParams(location.search);
    if (nextTab !== "feed") {
      searchParams.set("tab", nextTab);
    } else {
      searchParams.delete("tab");
    }
    const nextSearch = searchParams.toString();
    navigate({ search: nextSearch ? `?${nextSearch}` : "" }, { replace: true });
  };

  // Canonical Query 1: Scouting Feed
  const { data: scoutingData, isLoading: loadingScouting } = useQuery({
    queryKey: ["regen-scouting-feed"],
    queryFn: async () => {
      try {
        const { data } = await api.get("/regen-universe/scouting-feed", { params: { per_page: 30 } });
        return data?.items || [];
      } catch {
        return [];
      }
    },
  });

  // Canonical Query 2: Rising Stars
  const { data: risingData, isLoading: loadingRising } = useQuery({
    queryKey: ["regen-rising-stars"],
    queryFn: async () => {
      try {
        const { data } = await api.get("/regen-universe/rising-stars", { params: { per_page: 24, age_max: 21 } });
        return data?.entries || data?.items || [];
      } catch {
        return [];
      }
    },
  });

  // Canonical Query 3: Bloodlines
  const { data: bloodlinesData, isLoading: loadingBloodlines } = useQuery({
    queryKey: ["regen-bloodlines"],
    queryFn: async () => {
      try {
        const { data } = await api.get("/regen-universe/bloodlines", { params: { per_page: 20 } });
        return data?.items || [];
      } catch {
        return [];
      }
    },
    enabled: tab === "bloodlines",
  });

  // Canonical Query 4: Rankings
  const { data: rankingsData, isLoading: loadingRankings } = useQuery({
    queryKey: ["regen-rankings"],
    queryFn: async () => {
      try {
        const { data } = await api.get("/regen-universe/rankings", { params: { category: "overall", per_page: 25 } });
        return data?.entries || [];
      } catch {
        return [];
      }
    },
    enabled: tab === "rankings",
  });

  // Canonical Query 5: Hall of Fame
  const { data: hallData, isLoading: loadingHall } = useQuery({
    queryKey: ["regen-hall-of-fame"],
    queryFn: async () => {
      try {
        const { data } = await api.get("/regen-universe/hall-of-fame", { params: { per_page: 20 } });
        return data?.entries || [];
      } catch {
        return [];
      }
    },
    enabled: tab === "hall",
  });

  // Canonical Query 6: Generation Tracking Stats
  const { data: trackingData } = useQuery({
    queryKey: ["regen-tracking-stats"],
    queryFn: async () => {
      try {
        const { data } = await api.get("/regen-universe/tracking");
        return data;
      } catch {
        return null;
      }
    },
  });

  // Current active prospect list
  const activeItems = useMemo(() => {
    let list: any[] = [];
    if (tab === "feed") list = scoutingData || [];
    else if (tab === "rising") list = risingData || [];
    else return [];

    return list.filter((item) => {
      const p = item.player || item;
      const name = p.name || p.player_name || "";
      const pos = (p.position || p.primary_position || "").toUpperCase();
      const nation = (p.nationality || "").toUpperCase();

      if (search && !name.toLowerCase().includes(search.toLowerCase())) return false;
      if (positionFilter !== "ALL" && !pos.includes(positionFilter)) return false;
      if (originFilter !== "ALL" && !nation.includes(originFilter)) return false;
      return true;
    });
  }, [tab, scoutingData, risingData, search, positionFilter, originFilter]);

  const handleAddToWatchlist = async (id: string) => {
    try {
      await api.post("/transfer-market/watchlist", {
        player_id: id,
        club_id: activeClub?.club_id,
        source: "scouting_feed",
      });
      toast.success("Player added to transfer shortlist.");
    } catch {
      toast.info("Scouted player added to notes.");
    }
  };

  return (
    <div className="space-y-8 p-4 sm:p-8" data-testid="regen-world-screen">
      {/* World Introduction Hero Banner */}
      <section className="relative overflow-hidden rounded-2xl border-2 border-emerald-500/30 bg-gradient-to-br from-[#061e16] via-[#04120e] to-[#020906] p-6 sm:p-10 shadow-2xl">
        <div className="pointer-events-none absolute right-0 top-0 h-full w-1/2 bg-[radial-gradient(ellipse_at_70%_20%,rgba(16,185,129,0.2),transparent_75%)]" />
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/40 bg-emerald-950/80 px-3 py-1 text-[11px] font-black uppercase tracking-widest text-emerald-300 backdrop-blur-sm">
            <Sparkles size={12} /> GLOBAL REGEN UNIVERSE
          </div>
          <h1 className="gx-display mt-3 text-4xl sm:text-6xl font-black uppercase tracking-tight text-white leading-none">
            Talent Discovery Command
          </h1>
          <p className="mt-2 text-sm sm:text-base text-emerald-100/70">
            A living, generation-driven football scouting universe. Explore next-gen prospects, tracked bloodlines, and world ranking leaderboards.
          </p>

            {/* Quick World Stats Ticker */}
            <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3 text-left">
              <div className="rounded-lg border border-emerald-500/20 bg-black/40 p-3">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Gen Active</p>
                <p className="gx-mono text-xl font-black text-emerald-300">
                  Gen {trackingData?.current_generation ?? "1"}
                </p>
              </div>
              <div className="rounded-lg border border-emerald-500/20 bg-black/40 p-3">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Total Seeded</p>
                <p className="gx-mono text-xl font-black text-white">
                  {trackingData?.total_regens_generated != null ? `${trackingData.total_regens_generated}` : "—"}
                </p>
              </div>
              <div className="rounded-lg border border-emerald-500/20 bg-black/40 p-3">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Top Potential</p>
                <p className="gx-mono text-xl font-black text-amber-300">
                  {trackingData?.top_potential != null ? `${trackingData.top_potential} POT` : "—"}
                </p>
              </div>
              <div className="rounded-lg border border-emerald-500/20 bg-black/40 p-3">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Scouted Nations</p>
                <p className="gx-mono text-xl font-black text-cyan-300">
                  {trackingData?.nations_count != null ? `${trackingData.nations_count} Regions` : "—"}
                </p>
              </div>
            </div>
        </div>
      </section>

      {/* Navigation Lanes */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-4">
        <nav className="flex flex-wrap gap-2" data-testid="regen-world-tabs">
          {[
            { id: "feed", label: "Scouting Feed", icon: Compass },
            { id: "rising", label: "Rising Stars (U21)", icon: Flame },
            { id: "bloodlines", label: "DNA Bloodlines", icon: Dna },
            { id: "rankings", label: "Global Leaderboards", icon: Trophy },
            { id: "hall", label: "Hall of Fame", icon: Award },
          ].map((item) => {
            const Icon = item.icon;
            const active = tab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleTabChange(item.id as any)}
                data-testid={`tab-${item.id}`}
                className={`flex items-center gap-2 rounded-lg px-4 py-2.5 text-xs font-bold uppercase tracking-wider transition-all ${
                  active
                    ? "bg-emerald-500 text-slate-950 shadow-[0_0_16px_rgba(16,185,129,0.4)]"
                    : "border border-white/10 bg-slate-900/60 text-slate-300 hover:border-emerald-400/40 hover:text-white"
                }`}
              >
                <Icon size={14} />
                {item.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Discovery Filters Bar (Active for Feed & Rising) */}
      {(tab === "feed" || tab === "rising") && (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 bg-slate-900/60 p-4 rounded-xl border border-white/10" data-testid="regen-filter-bar">
          <div className="relative sm:col-span-2">
            <Search className="absolute left-3 top-3 size-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search prospects by name, archetype or serial..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="gx-input pl-9"
              data-testid="regen-search-input"
            />
          </div>
          <div>
            <select
              value={positionFilter}
              onChange={(e) => setPositionFilter(e.target.value)}
              className="gx-input"
              data-testid="regen-position-filter"
            >
              <option value="ALL">All Positions</option>
              <option value="GK">Goalkeepers (GK)</option>
              <option value="DEF">Defenders (CB/FB)</option>
              <option value="MID">Midfielders (CM/AM/DM)</option>
              <option value="FWD">Attackers (ST/W)</option>
            </select>
          </div>
          <div>
            <select
              value={originFilter}
              onChange={(e) => setOriginFilter(e.target.value)}
              className="gx-input"
              data-testid="regen-origin-filter"
            >
              <option value="ALL">All Nations</option>
              <option value="NIGERIA">Nigeria</option>
              <option value="GHANA">Ghana</option>
              <option value="SENEGAL">Senegal</option>
              <option value="ENGLAND">England</option>
              <option value="BRAZIL">Brazil</option>
            </select>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      {tab === "feed" || tab === "rising" ? (
        <div>
          {loadingScouting || loadingRising ? (
            <Loading label="Calibrating talent discovery grid..." />
          ) : activeItems.length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/10 p-12 text-center" data-testid="regen-empty-state">
              <Compass className="mx-auto size-10 text-emerald-400/50 mb-3" />
              <p className="gx-display text-xl font-bold uppercase text-white">No prospects match current filters</p>
              <p className="text-sm text-slate-400 mt-1">Try resetting position or region filters.</p>
              <button
                type="button"
                onClick={() => { setSearch(""); setPositionFilter("ALL"); setOriginFilter("ALL"); }}
                className="gx-btn gx-btn-secondary mt-4"
              >
                Reset Filters
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 place-items-center" data-testid="regen-grid">
              {activeItems.map((item: any, idx: number) => {
                const p = item.player || item;
                const id = p.id || p.player_id || `prospect-${idx}`;
                return (
                  <RegenCard
                    key={id}
                    testid={`regen-card-${id}`}
                    name={p.name || p.player_name || `Prospect #${idx + 1}`}
                    rating={p.current_rating || p.rating || 71}
                    potential={p.potential || 88}
                    position={p.position || p.primary_position || "MID"}
                    age={p.age ?? 18}
                    nationality={p.nationality || "Global"}
                    club={p.current_club_name || "GTEX Academy"}
                    image={p.portrait_url || p.image_url}
                    generation={p.generation ?? 1}
                    archetype={p.archetype || "Tactical Prodigy"}
                    serial={p.serial_number}
                    price={p.market_value_coin || 12000}
                    variant="full"
                    onClick={() => updateSelectedPlayer(id)}
                  />
                );
              })}
            </div>
          )}
        </div>
      ) : tab === "bloodlines" ? (
        <div className="space-y-4" data-testid="regen-bloodlines-view">
          <p className="gx-eyebrow text-emerald-400">Founding DNA Lineages</p>
          {loadingBloodlines ? (
            <Loading label="Tracing genetic pedigree..." />
          ) : bloodlinesData && bloodlinesData.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {bloodlinesData.map((bl: any) => (
                <div key={bl.id} className="rounded-xl border border-emerald-500/30 bg-[#051310] p-5 shadow-lg space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-xs font-black uppercase text-emerald-300">
                      <Dna size={14} /> Gen {bl.generation || 1}
                    </span>
                    <span className="gx-mono text-xs font-bold text-amber-300">{bl.count || 0} Lineage Seeds</span>
                  </div>
                  <h3 className="gx-display text-xl font-bold uppercase text-white">{bl.name}</h3>
                  <p className="text-xs text-slate-300">{bl.archetypes || bl.description || "Balanced Physical & Technical Traits"}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-6" data-testid="bloodlines-empty-state">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  {
                    name: "Owner's Bloodline Scion (Build-A-Son)",
                    gen: "Dynasty Heir",
                    perk: "20/20 Loyalty · 85–96 POT",
                    desc: "Inducted directly by Club Owners via the Academy Build-A-Son Endowment. Carries family legacy, elite composure, and fan adoration.",
                  },
                  {
                    name: "Street Cage Prodigy",
                    gen: "Concrete Five-a-Side",
                    perk: "+Clutch Derby Flair",
                    desc: "Fearless improviser forged on neighborhood concrete pitches; thrives under high-pressure floodlights.",
                  },
                  {
                    name: "Dynasty Legacy Scion",
                    gen: "Second-Generation Pro",
                    perk: "+Media Marketability",
                    desc: "Raised in elite dressing rooms with polished technique, high commercial value, and lofty personal ambition.",
                  },
                  {
                    name: "Academy Reject Chip-on-Shoulder",
                    gen: "Redemption Arc",
                    perk: "+25% Growth vs. Rivals",
                    desc: "Overlooked at age 14 and driven by relentless after-hours training to prove every doubter wrong.",
                  },
                ].map((arch) => (
                  <div key={arch.name} className="rounded-xl border border-emerald-500/30 bg-[#051310] p-5 shadow-lg space-y-2 text-left">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5 text-[10px] font-black uppercase text-emerald-300">
                        <Dna size={13} /> {arch.gen}
                      </span>
                      <span className="rounded bg-amber-500/20 px-2 py-0.5 text-[10px] font-bold text-amber-300">{arch.perk}</span>
                    </div>
                    <h3 className="gx-display text-lg font-bold uppercase text-white">{arch.name}</h3>
                    <p className="text-xs text-slate-300 leading-relaxed">{arch.desc}</p>
                  </div>
                ))}
              </div>
              <Dna className="mx-auto size-10 text-emerald-400/50 mb-3" />
              <p className="gx-display text-xl font-bold uppercase text-white">No active DNA lineages recorded</p>
              <p className="text-sm text-slate-400 mt-1">Founding bloodlines are established as academy regens graduate through competitive seasons.</p>
            </div>
          )}
        </div>
      ) : tab === "rankings" ? (
        <div className="space-y-4" data-testid="regen-rankings-view">
          <p className="gx-eyebrow text-emerald-400">Official GTEX World Leaderboard</p>
          {loadingRankings ? (
            <Loading label="Querying rankings engine..." />
          ) : rankingsData && rankingsData.length > 0 ? (
            <div className="overflow-hidden rounded-xl border border-white/10 bg-slate-900/60 shadow-xl">
              <table className="gx-table w-full">
                <thead>
                  <tr>
                    <th className="w-16">Rank</th>
                    <th>Prospect</th>
                    <th>Position</th>
                    <th>Category</th>
                    <th className="text-right">Ranking Score</th>
                  </tr>
                </thead>
                <tbody>
                  {rankingsData.map((entry: any) => (
                    <tr
                      key={entry.id || entry.rank}
                      onClick={() => entry.player_id && updateSelectedPlayer(entry.player_id)}
                      className="cursor-pointer hover:bg-emerald-500/10 transition-colors"
                    >
                      <td className="gx-mono font-black text-amber-300">#{entry.rank}</td>
                      <td className="font-bold text-white uppercase">{entry.player_name || entry.name}</td>
                      <td className="gx-mono text-emerald-400">{entry.position || "MID"}</td>
                      <td className="text-slate-400 text-xs">{entry.category || "Overall"}</td>
                      <td className="gx-mono font-bold text-right text-emerald-300">{entry.score ?? entry.ranking_score ?? "—"} pts</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-white/10 p-12 text-center" data-testid="rankings-empty-state">
              <Trophy className="mx-auto size-10 text-emerald-400/50 mb-3" />
              <p className="gx-display text-xl font-bold uppercase text-white">Leaderboards calibrating</p>
              <p className="text-sm text-slate-400 mt-1">Global rankings are updated following competitive matchday results.</p>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4" data-testid="regen-hall-view">
          <p className="gx-eyebrow text-amber-400">Regen Hall of Fame</p>
          {loadingHall ? (
            <Loading label="Consulting immortals archive..." />
          ) : hallData && hallData.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {hallData.map((entry: any) => (
                <div key={entry.id} className="rounded-xl border border-amber-400/40 bg-gradient-to-b from-[#1c1407] to-[#0c0903] p-5 shadow-2xl space-y-2">
                  <div className="flex items-center gap-2 text-amber-400">
                    <Trophy size={16} />
                    <span className="text-xs font-black uppercase tracking-wider">Immortalized Legend</span>
                  </div>
                  <h3 className="gx-display text-2xl font-black uppercase text-white">{entry.player_name || entry.name}</h3>
                  <div className="grid grid-cols-3 gap-2 pt-2 border-t border-amber-500/20 text-center">
                    <div>
                      <p className="gx-display text-xl font-bold text-amber-300">{entry.total_awards ?? 0}</p>
                      <p className="text-[9px] uppercase text-slate-400">Trophies</p>
                    </div>
                    <div>
                      <p className="gx-display text-xl font-bold text-emerald-300">{entry.legacy_score ?? "0.0"}</p>
                      <p className="text-[9px] uppercase text-slate-400">Legacy</p>
                    </div>
                    <div>
                      <p className="gx-display text-xl font-bold text-white">{entry.seasons_active ?? 1}</p>
                      <p className="text-[9px] uppercase text-slate-400">Seasons</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-white/10 p-12 text-center" data-testid="hall-empty-state">
              <Award className="mx-auto size-10 text-amber-400/50 mb-3" />
              <p className="gx-display text-xl font-bold uppercase text-white">No legends inducted yet</p>
              <p className="text-sm text-slate-400 mt-1">Hall of Fame inductions take place at the end of each global season cycle.</p>
            </div>
          )}
        </div>
      )}

      {/* Deep Dossier Modal */}
      {selectedPlayerId && (
        <PlayerDossier
          playerId={selectedPlayerId}
          onClose={() => updateSelectedPlayer(null)}
          onAddToWatchlist={handleAddToWatchlist}
          onMakeOffer={(id) => {
            updateSelectedPlayer(null);
            navigate(journeyLinks.transferHub("listings", id));
          }}
        />
      )}
    </div>
  );
}
export default RegenWorld;
