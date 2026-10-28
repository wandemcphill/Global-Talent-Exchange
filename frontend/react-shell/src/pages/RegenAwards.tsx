import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Award, Crown, Flame, Medal, Shield, Sparkles, Star, Trophy, Users } from "lucide-react";
import { api } from "@/lib/api";
import { RegenCard } from "@/components/gtex/RegenCard";
import { PlayerDossier } from "@/components/gtex/PlayerDossier";
import { Loading } from "@/components/gtex/ui";
import { Cinema3DStage } from "@/components/gtex/Cinema3DStage";
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

      {/* 3D World Player of the Year & Ballon d'Or Stage */}
      <Cinema3DStage
        scene="world_gala"
        title={`3D GTEX Ballon d'Or de Demain · ${featuredWinner?.player_name || "World #1 Laureate"}`}
        subtitle="Monaco Theatre · Volumetric 3D Golden Globe Pedestal & Spotlight Sweep"
        badgeText="3D BALLON D'OR GALA"
        clubName={featuredWinner?.club_name || "GTEX World XI"}
        subjectName={featuredWinner?.player_name || "Golden Boy Laureate"}
        overallRating={featuredWinner?.rating || 94}
        quote="Crowned on the 3D Monaco stage as the most dominant prodigy of the GTEX season."
        stats={[
          { label: "Gala Rank", value: "#1 WORLDWIDE", accent: "#FDE047" },
          { label: "Award Score", value: `${featuredWinner?.ranking_score ?? "98.6"} PTS`, accent: "#00E676" },
        ]}
      />

      {/* Featured Ceremony Spotlight Winner */}
      {featuredWinner ? (
        <section className="relative rounded-2xl border-2 border-amber-400/40 bg-gradient-to-r from-[#1b1304] via-[#0f0c05] to-[#120e05] p-6 sm:p-8 shadow-2xl">
          <div className="flex flex-col lg:flex-row items-center justify-between gap-8">
            <div className="max-w-xl text-left space-y-3">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/60 bg-amber-950/80 px-3 py-1 text-[11px] font-black uppercase tracking-widest text-amber-300">
                <Trophy size={14} className="text-amber-400" />
                {primaryAward?.award?.name || "Golden Regen · World Player of the Year"}
              </span>

              <h2 className="gx-display text-3xl sm:text-5xl font-black uppercase text-white leading-tight">
                {featuredWinner.player_name || featuredWinner.name}
              </h2>

              <p className="text-sm text-slate-300 leading-relaxed">
                {primaryAward?.award?.description ||
                  "Awarded to the most dominant U21 prospect across all continental competitions, scoring metrics, and match-engine performance."}
              </p>

              <div className="flex flex-wrap gap-4 pt-2">
                {featuredWinner.ranking_score != null && (
                  <div className="rounded-lg border border-amber-500/20 bg-black/50 px-4 py-2">
                    <p className="text-[10px] uppercase font-bold text-slate-400">Gala Score</p>
                    <p className="gx-mono text-xl font-black text-amber-300">
                      {featuredWinner.ranking_score.toFixed(1)} pts
                    </p>
                  </div>
                )}
                <div className="rounded-lg border border-amber-500/20 bg-black/50 px-4 py-2">
                  <p className="text-[10px] uppercase font-bold text-slate-400">Ceremony Rank</p>
                  <p className="gx-mono text-xl font-black text-emerald-300">#1 Laureate</p>
                </div>
              </div>

              {featuredWinner.player_id && (
                <div className="pt-2">
                  <button
                    type="button"
                    onClick={() => setSelectedPlayerId(featuredWinner.player_id)}
                    className="gx-btn gx-btn-gold text-slate-950 px-6 py-2.5 text-xs font-black shadow-[0_0_20px_rgba(245,158,11,0.5)]"
                    data-testid="featured-winner-dossier-btn"
                  >
                    Inspect Laureate Dossier
                  </button>
                </div>
              )}
            </div>

            <div className="shrink-0 flex justify-center">
              <RegenCard
                name={featuredWinner.player_name || featuredWinner.name}
                rating={featuredWinner.rating || 82}
                potential={featuredWinner.potential || 94}
                position={featuredWinner.position || "FWD"}
                variant="full"
                onClick={() => featuredWinner.player_id && setSelectedPlayerId(featuredWinner.player_id)}
                testid="featured-winner-card"
              />
            </div>
          </div>
        </section>
      ) : (
        <section className="relative rounded-2xl border border-amber-500/30 bg-gradient-to-r from-[#140e03] to-[#0a0702] p-8 text-center" data-testid="awards-balloting-banner">
          <Trophy className="mx-auto size-12 text-amber-400/60 mb-2" />
          <h2 className="gx-display text-2xl font-black uppercase text-white">Ballon d'Or Ceremony In Session</h2>
          <p className="text-sm text-slate-400 max-w-lg mx-auto mt-1">
            Global jury deliberation is currently ongoing for this cycle. The laureates will be officially announced once season fixtures conclude.
          </p>
        </section>
      )}

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
        ) : awardList.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="awards-category-grid">
            {awardList.map((item: any) => {
              const award = item.award || item;
              const winner = item.winners?.[0] || award.winner;
              const nominees: any[] = item.nominees || (winner ? [winner.player_name || winner.name] : []);
              return (
                <div
                  key={award.id || award.code || award.name}
                  className="rounded-xl border border-white/10 bg-slate-900/60 p-5 space-y-4 shadow-xl hover:border-amber-400/40 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <span className="flex size-9 items-center justify-center rounded-lg bg-amber-400/15 text-amber-400 border border-amber-400/30">
                      <Medal size={18} />
                    </span>
                    <span className="rounded-full bg-amber-400/10 px-2.5 py-0.5 text-[9px] font-black uppercase text-amber-300 border border-amber-400/20">
                      {winner ? "Honoured" : "Nominees Finalised"}
                    </span>
                  </div>

                  <div>
                    <h4 className="gx-display text-xl font-bold uppercase text-white">{award.name}</h4>
                    <p className="text-xs text-slate-400 mt-1">{award.description || award.criteria || "Official category honour."}</p>
                  </div>

                  {winner && (
                    <div className="pt-2 border-t border-white/10">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-amber-300/80 mb-2">Category Winner</p>
                      <RegenCard
                        name={winner.player_name || winner.name}
                        rating={winner.rating || winner.overall || 78}
                        position={winner.position || "MID"}
                        variant="compact"
                        onClick={() => winner.player_id && setSelectedPlayerId(winner.player_id)}
                      />
                    </div>
                  )}

                  {nominees.length > 0 && (
                    <div className="pt-2 border-t border-white/5">
                      <p className="text-[9px] font-bold uppercase tracking-widest text-slate-500 mb-1">Final Nominees</p>
                      <ul className="space-y-1 text-xs text-slate-300">
                        {nominees.map((nom: any, i: number) => {
                          const nomName = typeof nom === "string" ? nom : (nom.player_name || nom.name);
                          return (
                            <li key={i} className="flex items-center gap-1.5 text-[11px]">
                              <span className="size-1 rounded-full bg-slate-500" />
                              <span className={i === 0 && winner ? "text-amber-300 font-bold" : ""}>{nomName}</span>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-white/10 p-12 text-center" data-testid="awards-empty-state">
            <Trophy className="mx-auto size-10 text-amber-400/50 mb-3" />
            <p className="gx-display text-xl font-bold uppercase text-white">Ceremony balloting in progress</p>
            <p className="text-sm text-slate-400 mt-1">Honours and category laureates will be verified at the conclusion of active competitive play.</p>
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
