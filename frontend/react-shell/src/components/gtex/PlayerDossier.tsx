import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Award, Calendar, CheckCircle2, ChevronRight, Dna, ExternalLink, Globe, Shield, Sparkles, Trophy, UserCheck, X } from "lucide-react";
import { api } from "@/lib/api";
import { fmt, label } from "@/lib/owner";
import { Btn, Chip, Loading, TraitBar } from "@/components/gtex/ui";
import { PlayerCard } from "./PlayerCard";
import { RegenCard } from "./RegenCard";

export interface PlayerDossierProps {
  playerId: string | null;
  onClose: () => void;
  onMakeOffer?: (playerId: string) => void;
  onAddToWatchlist?: (playerId: string) => void;
}

export function PlayerDossier({ playerId, onClose, onMakeOffer, onAddToWatchlist }: PlayerDossierProps) {
  // Query 1: Regen lookup or real player
  const { data: regenData, isLoading: loadingRegen } = useQuery({
    queryKey: ["regen-dossier", playerId],
    queryFn: async () => {
      try {
        const { data } = await api.get(`/regen-universe/player/${playerId}`);
        return data;
      } catch {
        return null;
      }
    },
    enabled: !!playerId,
    retry: false,
  });

  const { data: realData, isLoading: loadingReal } = useQuery({
    queryKey: ["real-dossier", playerId],
    queryFn: async () => {
      try {
        const { data } = await api.get(`/v2/players/real-universe/${playerId}`);
        return data;
      } catch {
        return null;
      }
    },
    enabled: !!playerId && !regenData,
    retry: false,
  });

  // Query 2: Timeline
  const { data: timelineData } = useQuery({
    queryKey: ["regen-timeline", playerId],
    queryFn: async () => {
      try {
        const { data } = await api.get(`/regen-universe/players/${playerId}/timeline`);
        return data?.items || [];
      } catch {
        return [];
      }
    },
    enabled: !!playerId,
    retry: false,
  });

  if (!playerId) return null;

  const isLoading = loadingRegen && loadingReal;

  // Resolved entities
  const isRegen = !!regenData || (realData && realData.is_regen);
  const p = regenData?.player || realData || {};
  const cardInfo = regenData?.card || {};
  const prestige = regenData?.prestige || {};
  const timeline = timelineData || regenData?.timeline || [];

  const name = p.name || p.player_name || "Scouted Prospect";
  const rating = Number(p.current_rating || p.rating || cardInfo.overall || 72);
  const potential = Number(p.potential || cardInfo.potential || Math.min(99, rating + 14));
  const position = p.position || p.primary_position || "MID";
  const age = p.age ?? 18;
  const nationality = p.nationality || "Global";
  const club = p.current_club_name || "GTEX Academy";
  const image = p.portrait_url || p.image_url;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/75 backdrop-blur-md transition-opacity"
      onClick={onClose}
      data-testid="player-dossier-modal"
    >
      <aside
        className="gx-scroll h-full w-full max-w-xl overflow-y-auto border-l border-white/10 bg-[#060c14] p-6 text-white shadow-2xl flex flex-col gap-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Dossier Header */}
        <div className="flex items-center justify-between border-b border-white/10 pb-4">
          <div className="flex items-center gap-2">
            <span className="flex size-7 items-center justify-center rounded-sm bg-emerald-500/20 text-emerald-400">
              <Dna size={16} />
            </span>
            <div>
              <p className="gx-eyebrow text-emerald-400">Official Player Dossier</p>
              <h2 className="gx-display text-xl font-black uppercase tracking-wide text-white">
                {name}
              </h2>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-sm p-1.5 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            data-testid="player-dossier-close"
          >
            <X size={20} />
          </button>
        </div>

        {isLoading ? (
          <Loading label="Synthesizing scouting intel..." />
        ) : (
          <div className="space-y-6">
            {/* Centerpiece Collectible Card */}
            <div className="flex justify-center py-2">
              {isRegen ? (
                <RegenCard
                  name={name}
                  rating={rating}
                  potential={potential}
                  position={position}
                  age={age}
                  nationality={nationality}
                  club={club}
                  image={image}
                  generation={cardInfo.generation ?? 1}
                  archetype={cardInfo.archetype ?? "Academy Prodigy"}
                  serial={cardInfo.serial_number}
                  price={regenData?.market_value_coin}
                  variant="full"
                />
              ) : (
                <PlayerCard
                  name={name}
                  rating={rating}
                  potential={potential}
                  position={position}
                  age={age}
                  nationality={nationality}
                  club={club}
                  image={image}
                  variant="full"
                />
              )}
            </div>

            {/* Quick Action Bar */}
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => onAddToWatchlist && onAddToWatchlist(playerId)}
                className="gx-btn gx-btn-secondary w-full"
                data-testid="dossier-watchlist-btn"
              >
                <Sparkles size={14} className="text-amber-400" /> Shortlist
              </button>
              <button
                type="button"
                onClick={() => onMakeOffer && onMakeOffer(playerId)}
                className="gx-btn gx-btn-primary w-full"
                data-testid="dossier-offer-btn"
              >
                <CheckCircle2 size={14} /> Transfer Offer
              </button>
            </div>

            {/* Scouting Badges & Verified Status */}
            <div className="rounded-md border border-white/10 bg-slate-900/60 p-4 space-y-2">
              <p className="gx-eyebrow text-slate-400">Scouting Classification</p>
              <div className="flex flex-wrap gap-2">
                <Chip tone="emerald">{isRegen ? "Gen 1-3 Verified Regen" : "Established Professional"}</Chip>
                <Chip tone="cyan">{position}</Chip>
                <Chip tone="gold">{nationality}</Chip>
                {potential - rating >= 10 && <Chip tone="purple">Wonderkid Potential</Chip>}
              </div>
              {regenData?.scouting_note && (
                <p className="mt-2 text-xs italic text-slate-300 border-l-2 border-emerald-500/50 pl-2.5 py-1">
                  "{regenData.scouting_note}"
                </p>
              )}
            </div>

            {/* Attributes Breakdown */}
            <div className="rounded-md border border-white/10 bg-slate-900/60 p-4 space-y-3">
              <p className="gx-eyebrow text-slate-400">Core Attributes & Radar</p>
              <div className="space-y-2">
                <TraitBar label="Pace" value={Math.min(99, Math.round(rating * 1.05))} max={99} />
                <TraitBar label="Technical" value={Math.min(99, Math.round(rating * 0.98))} max={99} />
                <TraitBar label="Tactical Vision" value={Math.min(99, Math.round(rating * 1.02))} max={99} />
                <TraitBar label="Physicality" value={Math.min(99, Math.round(rating * 0.94))} max={99} />
                <TraitBar label="Mentality / Composure" value={Math.min(99, Math.round(rating * 1.01))} max={99} />
              </div>
            </div>

            {/* Prestige & Honours */}
            {prestige.total_awards != null && prestige.total_awards > 0 && (
              <div className="rounded-md border border-amber-500/30 bg-amber-950/20 p-4 space-y-2">
                <div className="flex items-center gap-2 text-amber-300">
                  <Trophy size={16} />
                  <span className="text-xs font-black uppercase tracking-wider">Honours & Global Recognition</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center pt-2">
                  <div className="bg-black/40 p-2 rounded">
                    <p className="gx-display text-2xl font-bold text-amber-300">{prestige.total_awards}</p>
                    <p className="text-[9px] uppercase font-bold text-slate-400">Awards Won</p>
                  </div>
                  <div className="bg-black/40 p-2 rounded">
                    <p className="gx-display text-2xl font-bold text-emerald-300">#{prestige.peak_rank ?? 1}</p>
                    <p className="text-[9px] uppercase font-bold text-slate-400">Peak Rank</p>
                  </div>
                  <div className="bg-black/40 p-2 rounded">
                    <p className="gx-display text-2xl font-bold text-white">{prestige.legacy_score ?? "0.0"}</p>
                    <p className="text-[9px] uppercase font-bold text-slate-400">Legacy Score</p>
                  </div>
                </div>
              </div>
            )}

            {/* Career Timeline Wire */}
            <div className="rounded-md border border-white/10 bg-slate-900/60 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <p className="gx-eyebrow text-slate-400">Chronological Career Narrative</p>
                <Calendar size={13} className="text-slate-400" />
              </div>
              {timeline.length === 0 ? (
                <p className="text-xs text-slate-500">
                  Prospect newly surfaced in GTEX universe. Match performances and awards will build this timeline.
                </p>
              ) : (
                <ol className="relative border-l border-white/15 pl-4 space-y-3">
                  {timeline.slice(0, 5).map((evt: any, i: number) => (
                    <li key={evt.id || i} className="relative">
                      <span className="absolute -left-[21px] top-1 size-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
                      <p className="text-xs font-bold text-white uppercase">{evt.title || "Simulation Event"}</p>
                      <p className="text-[11px] text-slate-400">{evt.summary || evt.description}</p>
                      {evt.occurred_at && (
                        <p className="gx-mono text-[9px] text-emerald-400/80 mt-0.5">
                          {new Date(evt.occurred_at).toLocaleDateString()}
                        </p>
                      )}
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </div>
        )}
      </aside>
    </div>
  );
}
