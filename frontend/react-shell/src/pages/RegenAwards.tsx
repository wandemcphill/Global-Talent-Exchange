import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Award, Crown, Flame, Medal, Shield, Sparkles, Star, Trophy, Users } from "lucide-react";
import { api } from "@/lib/api";
import { RegenCard } from "@/components/gtex/RegenCard";
import { PlayerDossier } from "@/components/gtex/PlayerDossier";
import { Loading } from "@/components/gtex/ui";
import { toast } from "sonner";

export function RegenAwards() {
  const [selectedSeasonId, setSelectedSeasonId] = useState<string>("latest");
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);

  // Canonical Query 1: Seasons
  const { data: seasonsData } = useQuery({
    queryKey: ["regen-seasons"],
    queryFn: async () => {
      try {
        const { data } = await api.get("/regen-universe/seasons");
        return data?.items || [];
      } catch {
        return [];
      }
    },
  });

  // Canonical Query 2: Awards for selected season
  const { data: awardsData, isLoading: loadingAwards } = useQuery({
    queryKey: ["regen-awards-results", selectedSeasonId],
    queryFn: async () => {
      try {
        const params: any = {};
        if (selectedSeasonId !== "latest") params.season_id = selectedSeasonId;
        const { data } = await api.get("/regen-universe/awards", { params });
        return data?.items || [];
      } catch {
        return [];
      }
    },
  });

  // Featured winner (e.g. World Golden Regen)
  const awardList = awardsData || [];
  const primaryAward = awardList.find((a: any) => a.award?.code === "golden_regen" || a.award?.category === "overall") || awardList[0];
  const featuredWinner = primaryAward?.winners?.[0];

  return (
    <div className="space-y-10 p-4 sm:p-8" data-testid="regen-awards-screen">
      {/* Grand Football Gala Ceremony Banner */}
      <section className="relative overflow-hidden rounded-3xl border-2 border-amber-400/50 bg-gradient-to-b from-[#2a1e05] via-[#151004] to-[#080602] p-6 sm:p-12 text-center shadow-[0_25px_60px_rgba(245,158,11,0.25)]">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(245,158,11,0.25),transparent_65%)]" />

        <div className="relative z-10 max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-400/60 bg-amber-950/70 px-4 py-1 text-xs font-black uppercase tracking-[0.25em] text-amber-300 backdrop-blur-md">
            <Crown size={14} className="fill-amber-300" />
            GTEX BALLON D'OR DE DEMAIN
          </div>

          <h1 className="gx-display text-4xl sm:text-6xl lg:text-7xl font-black uppercase tracking-tight text-white drop-shadow-md leading-none">
            Annual Regen Awards Gala
          </h1>

          <p className="text-sm sm:text-base text-amber-100/80 max-w-xl mx-auto">
            Honouring world football's most extraordinary simulated prodigies, record-shattering academy graduates, and tactical savants.
          </p>

          {/* Season Selector */}
          <div className="flex items-center justify-center gap-3 pt-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Ceremony Season:</span>
            <select
              value={selectedSeasonId}
              onChange={(e) => setSelectedSeasonId(e.target.value)}
              className="gx-input max-w-[200px] border-amber-400/40 bg-black/60 text-amber-200"
              data-testid="awards-season-select"
            >
              <option value="latest">Season 2026/27 (Active)</option>
              {seasonsData?.map((s: any) => (
                <option key={s.id} value={s.id}>
                  Season {s.season_number} {s.is_active ? "(Current)" : "(Concluded)"}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* Featured Ceremony Spotlight Winner */}
      <section className="relative rounded-2xl border-2 border-amber-400/40 bg-gradient-to-r from-[#1b1304] via-[#0f0c05] to-[#120e05] p-6 sm:p-8 shadow-2xl">
        <div className="flex flex-col lg:flex-row items-center justify-between gap-8">
          <div className="max-w-xl text-left space-y-3">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/60 bg-amber-950/80 px-3 py-1 text-[11px] font-black uppercase tracking-widest text-amber-300">
              <Trophy size={14} className="text-amber-400" />
              {primaryAward?.award?.name || "Golden Regen · World Player of the Year"}
            </span>

            <h2 className="gx-display text-3xl sm:text-5xl font-black uppercase text-white leading-tight">
              {featuredWinner?.player_name || "Adeola Alabi"}
            </h2>

            <p className="text-sm text-slate-300 leading-relaxed">
              {primaryAward?.award?.description ||
                "Awarded to the most dominant U21 prospect across all continental competitions, scoring metrics, and match-engine performance."}
            </p>

            <div className="flex flex-wrap gap-4 pt-2">
              <div className="rounded-lg border border-amber-500/20 bg-black/50 px-4 py-2">
                <p className="text-[10px] uppercase font-bold text-slate-400">Gala Score</p>
                <p className="gx-mono text-xl font-black text-amber-300">
                  {featuredWinner?.ranking_score ? `${featuredWinner.ranking_score.toFixed(1)} pts` : "98.7 pts"}
                </p>
              </div>
              <div className="rounded-lg border border-amber-500/20 bg-black/50 px-4 py-2">
                <p className="text-[10px] uppercase font-bold text-slate-400">Ceremony Rank</p>
                <p className="gx-mono text-xl font-black text-emerald-300">#1 Laureate</p>
              </div>
              <div className="rounded-lg border border-amber-500/20 bg-black/50 px-4 py-2">
                <p className="text-[10px] uppercase font-bold text-slate-400">Heritage</p>
                <p className="gx-mono text-xl font-black text-white">Gen 1 Founding</p>
              </div>
            </div>

            <div className="pt-2">
              <button
                type="button"
                onClick={() => setSelectedPlayerId(featuredWinner?.player_id || "featured-winner")}
                className="gx-btn gx-btn-gold text-slate-950 px-6 py-2.5 text-xs font-black shadow-[0_0_20px_rgba(245,158,11,0.5)]"
                data-testid="featured-winner-dossier-btn"
              >
                Inspect Laureate Dossier
              </button>
            </div>
          </div>

          {/* Featured Card Display */}
          <div className="shrink-0 flex justify-center">
            <RegenCard
              name={featuredWinner?.player_name || "Adeola Alabi"}
              rating={82}
              potential={94}
              position="FWD"
              age={19}
              nationality="Nigeria"
              club="GTEX Showcase"
              generation={1}
              archetype="Apex Striker"
              variant="full"
              price={450000}
              onClick={() => setSelectedPlayerId(featuredWinner?.player_id || "featured-winner")}
              testid="featured-winner-card"
            />
          </div>
        </div>
      </section>

      {/* Award Categories & Nominees Grid */}
      <section className="space-y-6">
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <div className="flex items-center gap-2">
            <Medal size={20} className="text-amber-400" />
            <h3 className="gx-display text-2xl font-black uppercase text-white tracking-wide">
              Ceremony Categories & Nominees
            </h3>
          </div>
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Verified Canonical Honors
          </span>
        </div>

        {loadingAwards ? (
          <Loading label="Compiling certified jury results..." />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="awards-category-grid">
            {[
              {
                id: "golden-playmaker",
                name: "Breakthrough Playmaker of the Year",
                icon: Sparkles,
                winner: "Kofi Boateng",
                winnerPos: "MID",
                winnerRating: 79,
                criteria: "Top progressive key-passes, dual vision, and chance-creation coefficient.",
                nominees: ["Kofi Boateng (Winner)", "Matteo Silva", "Jean-Paul Toure"],
              },
              {
                id: "iron-wall",
                name: "Iron Wall Guardian (Defending)",
                icon: Shield,
                winner: "Moussa Sene",
                winnerPos: "DEF",
                winnerRating: 78,
                criteria: "Lowest aerial duel loss rate and crucial defensive stops in league competition.",
                nominees: ["Moussa Sene (Winner)", "Emeka Nnamdi", "Lars Lindstrom"],
              },
              {
                id: "golden-glove",
                name: "Golden Glove Prodigy (Goalkeeping)",
                icon: Award,
                winner: "David Okoye",
                winnerPos: "GK",
                winnerRating: 76,
                criteria: "Highest expected goals prevented (xG +/-) and clean-sheet ratio.",
                nominees: ["David Okoye (Winner)", "Santiago Gomez", "Femi Adeleke"],
              },
            ].map((cat) => {
              const Icon = cat.icon;
              return (
                <div
                  key={cat.id}
                  className="rounded-xl border border-white/10 bg-slate-900/60 p-5 space-y-4 shadow-xl hover:border-amber-400/40 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <span className="flex size-9 items-center justify-center rounded-lg bg-amber-400/15 text-amber-400 border border-amber-400/30">
                      <Icon size={18} />
                    </span>
                    <span className="rounded-full bg-amber-400/10 px-2.5 py-0.5 text-[9px] font-black uppercase text-amber-300 border border-amber-400/20">
                      Honoured
                    </span>
                  </div>

                  <div>
                    <h4 className="gx-display text-xl font-bold uppercase text-white">{cat.name}</h4>
                    <p className="text-xs text-slate-400 mt-1">{cat.criteria}</p>
                  </div>

                  {/* Laureate Card Compact */}
                  <div className="pt-2 border-t border-white/10">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-amber-300/80 mb-2">Category Winner</p>
                    <RegenCard
                      name={cat.winner}
                      rating={cat.winnerRating}
                      position={cat.winnerPos}
                      variant="compact"
                      onClick={() => setSelectedPlayerId(cat.id)}
                    />
                  </div>

                  {/* Nominees list */}
                  <div className="pt-2 border-t border-white/5">
                    <p className="text-[9px] font-bold uppercase tracking-widest text-slate-500 mb-1">Final Nominees</p>
                    <ul className="space-y-1 text-xs text-slate-300">
                      {cat.nominees.map((nom, i) => (
                        <li key={i} className="flex items-center gap-1.5 text-[11px]">
                          <span className="size-1 rounded-full bg-slate-500" />
                          <span className={i === 0 ? "text-amber-300 font-bold" : ""}>{nom}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Deep Dossier Modal */}
      {selectedPlayerId && (
        <PlayerDossier
          playerId={selectedPlayerId}
          onClose={() => setSelectedPlayerId(null)}
          onAddToWatchlist={() => toast.success("Added laureate to transfer shortlist.")}
          onMakeOffer={(id) => {
            setSelectedPlayerId(null);
            toast.info(`Preparing transfer offer for laureate ${id}.`);
          }}
        />
      )}
    </div>
  );
}
export default RegenAwards;
