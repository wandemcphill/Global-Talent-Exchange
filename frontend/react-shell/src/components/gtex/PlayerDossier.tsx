import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowRight,
  Award,
  Calendar,
  Check,
  CheckCircle2,
  Clock,
  Compass,
  Dna,
  ExternalLink,
  Eye,
  FileText,
  Handshake,
  Shield,
  Sparkles,
  Trophy,
  UserCheck,
  Users,
  X,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, label, useActiveClub } from "@/lib/owner";
import { Btn, Chip, Loading, TraitBar } from "@/components/gtex/ui";
import { PlayerCard } from "./PlayerCard";
import { RegenCard } from "./RegenCard";
import {
  buildJourney,
  journeyLinks,
  SQUAD_SEASON_LABEL,
  Source,
  JourneyStep,
} from "@/lib/playerJourney";
import { toast } from "sonner";

export interface PlayerDossierProps {
  playerId: string | null;
  onClose: () => void;
  onMakeOffer?: (playerId: string) => void;
  onAddToWatchlist?: (playerId: string) => void;
}

export function PlayerDossier({ playerId, onClose, onMakeOffer, onAddToWatchlist }: PlayerDossierProps) {
  const qc = useQueryClient();
  const { active: activeClub } = useActiveClub();
  const [commissioningReport, setCommissioningReport] = useState(false);

  // 1. Primary player entity (regen or established real universe)
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

  // 2. Chronological narrative timeline
  const { data: timelineData = [] } = useQuery({
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

  // 3. Official career history table
  const { data: careerEntries = [] } = useQuery({
    queryKey: ["player-career-records", playerId],
    queryFn: async () => {
      try {
        const { data } = await api.get(`/players/${playerId}/career`);
        return Array.isArray(data) ? data : [];
      } catch {
        return [];
      }
    },
    enabled: !!playerId,
    retry: false,
  });

  // 4. Scout report query for active club
  const {
    data: scoutReport,
    isLoading: loadingScoutReport,
    error: scoutReportError,
    refetch: refetchScoutReport,
  } = useQuery({
    queryKey: ["player-scout-report", playerId, activeClub?.club_id],
    queryFn: async () => {
      if (!playerId || !activeClub?.club_id) return null;
      try {
        const { data } = await api.get(`/scout/reports/${playerId}`);
        return data;
      } catch (err: any) {
        if (err?.response?.status === 404) return null;
        throw err;
      }
    },
    enabled: !!playerId && !!activeClub?.club_id,
    retry: false,
  });

  // 5. Watchlist entries for active club
  const {
    data: watchlistData = [],
    isLoading: loadingWatchlist,
    error: watchlistError,
    refetch: refetchWatchlist,
  } = useQuery({
    queryKey: ["transfer-market-watchlist", activeClub?.club_id],
    queryFn: async () => {
      if (!activeClub?.club_id) return [];
      const { data } = await api.get("/transfer-market/watchlist", {
        params: { club_id: activeClub.club_id },
      });
      return data || [];
    },
    enabled: !!activeClub?.club_id,
    retry: false,
  });

  // 6. Market listings for this player
  const {
    data: playerListings = [],
    isLoading: loadingListings,
    error: listingsError,
    refetch: refetchListings,
  } = useQuery({
    queryKey: ["transfer-listings-player", playerId],
    queryFn: async () => {
      if (!playerId) return [];
      const { data } = await api.get("/transfer-hub/listings", {
        params: { player_id: playerId },
      });
      return data || [];
    },
    enabled: !!playerId,
    retry: false,
  });

  // 7. Active club's offers
  const {
    data: clubOffers = [],
    isLoading: loadingOffers,
    error: offersError,
    refetch: refetchOffers,
  } = useQuery({
    queryKey: ["transfer-offers", activeClub?.club_id],
    queryFn: async () => {
      if (!activeClub?.club_id) return [];
      const { data } = await api.get("/transfer-hub/offers", {
        params: { club_id: activeClub.club_id },
      });
      return data || [];
    },
    enabled: !!activeClub?.club_id,
    retry: false,
  });

  // 8. Active club's negotiations
  const {
    data: clubNegotiations = [],
    isLoading: loadingNegotiations,
    error: negotiationsError,
    refetch: refetchNegotiations,
  } = useQuery({
    queryKey: ["transfer-market-negotiations", activeClub?.club_id],
    queryFn: async () => {
      if (!activeClub?.club_id) return [];
      const { data } = await api.get("/transfer-market/negotiations", {
        params: { club_id: activeClub.club_id },
      });
      return data || [];
    },
    enabled: !!activeClub?.club_id,
    retry: false,
  });

  // 9. Active club's squad registration
  const {
    data: squadRegistration,
    isLoading: loadingRegistration,
    error: registrationError,
    refetch: refetchRegistration,
  } = useQuery({
    queryKey: ["squad-registration", activeClub?.club_id],
    queryFn: async () => {
      if (!activeClub?.club_id) return null;
      const { data } = await api.get(`/clubs/${encodeURIComponent(activeClub.club_id)}/squad-registration`, {
        params: { season_label: SQUAD_SEASON_LABEL },
      });
      return data;
    },
    enabled: !!activeClub?.club_id,
    retry: false,
  });

  if (!playerId) return null;

  const isLoading = loadingRegen && loadingReal;

  // Resolve player identity and provenance
  const isRegen = !!regenData || (realData && realData.is_regen);
  const p = regenData?.player || realData || {};
  const cardInfo = regenData?.card || {};
  const prestige = regenData?.prestige || {};
  const timeline = timelineData.length > 0 ? timelineData : regenData?.timeline || [];

  const name = p.name || p.player_name || "Scouted Prospect";
  const rating = Number(p.current_rating || p.rating || cardInfo.overall || 72);
  const potential = Number(p.potential || cardInfo.potential || Math.min(99, rating + 14));
  const position = p.position || p.primary_position || "MID";
  const age = p.age ?? 18;
  const nationality = p.nationality || "Global";
  const club = p.current_club_name || "GTEX Academy";
  const image = p.portrait_url || p.image_url;

  // Construct Sources for Journey Projection
  const reportSource: Source<any> = {
    status: loadingScoutReport ? "loading" : scoutReportError ? "error" : "ok",
    data: scoutReport,
    error: scoutReportError ? errMsg(scoutReportError) : undefined,
    httpStatus: (scoutReportError as any)?.response?.status,
  };

  const watchlistSource: Source<any[]> = {
    status: loadingWatchlist ? "loading" : watchlistError ? "error" : "ok",
    data: watchlistData,
    error: watchlistError ? errMsg(watchlistError) : undefined,
    httpStatus: (watchlistError as any)?.response?.status,
  };

  const listingsSource: Source<any[]> = {
    status: loadingListings ? "loading" : listingsError ? "error" : "ok",
    data: playerListings,
    error: listingsError ? errMsg(listingsError) : undefined,
    httpStatus: (listingsError as any)?.response?.status,
  };

  const offersSource: Source<any[]> = {
    status: loadingOffers ? "loading" : offersError ? "error" : "ok",
    data: clubOffers,
    error: offersError ? errMsg(offersError) : undefined,
    httpStatus: (offersError as any)?.response?.status,
  };

  const negotiationsSource: Source<any[]> = {
    status: loadingNegotiations ? "loading" : negotiationsError ? "error" : "ok",
    data: clubNegotiations,
    error: negotiationsError ? errMsg(negotiationsError) : undefined,
    httpStatus: (negotiationsError as any)?.response?.status,
  };

  const registrationSource: Source<any> = {
    status: loadingRegistration ? "loading" : registrationError ? "error" : "ok",
    data: squadRegistration,
    error: registrationError ? errMsg(registrationError) : undefined,
    httpStatus: (registrationError as any)?.response?.status,
  };

  const journeySteps = buildJourney({
    playerId,
    clubId: activeClub?.club_id || null,
    report: reportSource,
    watchlist: watchlistSource,
    listings: listingsSource,
    offers: offersSource,
    negotiations: negotiationsSource,
    registration: registrationSource,
    currentClubId: p.club_id,
  });

  // Commission a live scout report via backend endpoint
  const handleCommissionScoutReport = async () => {
    if (!activeClub?.club_id) {
      toast.error("Choose an active club before commissioning scouting.");
      return;
    }
    setCommissioningReport(true);
    try {
      await api.post(`/scout/report/${playerId}`);
      toast.success("Scout report generated and persisted.");
      await refetchScoutReport();
      await qc.invalidateQueries({ queryKey: ["player-scout-report", playerId] });
    } catch (e: any) {
      toast.error(errMsg(e));
    } finally {
      setCommissioningReport(false);
    }
  };

  const handleShortlistClick = async () => {
    if (onAddToWatchlist) {
      onAddToWatchlist(playerId);
      return;
    }
    if (!activeClub?.club_id) {
      toast.error("Select an active club before adding a target to shortlist.");
      return;
    }
    try {
      await api.post("/transfer-market/watchlist", {
        player_id: playerId,
        club_id: activeClub.club_id,
        source: "scouting_dossier",
      });
      toast.success("Player added to transfer shortlist.");
      await refetchWatchlist();
      await qc.invalidateQueries({ queryKey: ["transfer-market-watchlist", activeClub.club_id] });
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const handleOfferClick = () => {
    if (onMakeOffer) {
      onMakeOffer(playerId);
      return;
    }
    // Navigate or link to transfer hub
    window.location.href = journeyLinks.transferHub("listings", playerId);
  };

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
        {/* Dossier Header with Canonical Player ID */}
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
              <p className="gx-mono text-[10px] text-slate-400">Canonical ID: {playerId}</p>
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
                onClick={handleShortlistClick}
                className="gx-btn gx-btn-secondary w-full"
                data-testid="dossier-watchlist-btn"
              >
                <Sparkles size={14} className="text-amber-400" /> Shortlist
              </button>
              <button
                type="button"
                onClick={handleOfferClick}
                className="gx-btn gx-btn-primary w-full"
                data-testid="dossier-offer-btn"
              >
                <CheckCircle2 size={14} /> Transfer Offer
              </button>
            </div>

            {/* CONNECTED JOURNEY PIPELINE */}
            <section
              className="rounded-xl border border-emerald-500/30 bg-slate-900/80 p-4 space-y-4 shadow-xl"
              data-testid="dossier-journey-stepper"
            >
              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <div className="flex items-center gap-2">
                  <Compass size={16} className="text-emerald-400" />
                  <h3 className="gx-display text-sm font-black uppercase tracking-wider text-white">
                    Transfer & Contract Journey
                  </h3>
                </div>
                <span className="text-[10px] text-slate-400">
                  {activeClub?.club_name ? `Club: ${activeClub.club_name}` : "No club selected"}
                </span>
              </div>

              <div className="space-y-3">
                {journeySteps.map((step, idx) => {
                  const isDone = step.state === "done";
                  const isCurrent = step.state === "current";
                  const isBlocked = step.state === "blocked";
                  const isError = step.state === "error";
                  const isUnavailable = step.state === "unavailable";

                  const badgeColor = isDone
                    ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                    : isCurrent
                    ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40 animate-pulse"
                    : isBlocked
                    ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                    : isError
                    ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                    : "bg-slate-800 text-slate-400 border-white/10";

                  return (
                    <div
                      key={step.id}
                      className="rounded-lg border border-white/5 bg-black/40 p-3 space-y-1.5"
                      data-testid={`journey-step-${step.id}`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span
                            className={`flex size-5 items-center justify-center rounded-full border text-[10px] font-black ${badgeColor}`}
                          >
                            {isDone ? <Check size={10} /> : idx + 1}
                          </span>
                          <span className="text-xs font-bold uppercase tracking-wider text-white">
                            {step.title}
                          </span>
                        </div>
                        <span
                          className={`gx-mono rounded px-1.5 py-0.5 text-[9px] font-bold uppercase ${
                            isDone
                              ? "bg-emerald-950 text-emerald-300"
                              : isCurrent
                              ? "bg-cyan-950 text-cyan-300"
                              : "bg-slate-900 text-slate-400"
                          }`}
                        >
                          {step.state}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed pl-7">{step.detail}</p>

                      {/* Step-specific inline actions */}
                      <div className="pl-7 pt-1 flex flex-wrap gap-2">
                        {step.id === "report" && !scoutReport && (
                          <button
                            type="button"
                            onClick={handleCommissionScoutReport}
                            disabled={commissioningReport || !activeClub?.club_id}
                            className="gx-btn gx-btn-secondary text-[11px] py-1 px-2.5"
                            data-testid="commission-scout-report-btn"
                          >
                            {commissioningReport ? "Commissioning..." : "Commission Scout Report"}
                          </button>
                        )}
                        {step.action?.to && (
                          <a
                            href={step.action.to}
                            className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-400 hover:text-emerald-300 transition-colors"
                          >
                            {step.action.label} <ArrowRight size={11} />
                          </a>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* SCOUTING REPORT INTEL (when available) */}
            {scoutReport && (
              <div
                className="rounded-md border border-emerald-500/30 bg-emerald-950/20 p-4 space-y-3"
                data-testid="dossier-scout-intel"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-emerald-300">
                    <FileText size={15} />
                    <span className="text-xs font-black uppercase tracking-wider">
                      Verified Scout Intelligence
                    </span>
                  </div>
                  <span className="gx-mono text-[10px] font-bold text-emerald-400">
                    Accuracy {scoutReport.accuracy}%
                  </span>
                </div>
                <p className="text-xs text-slate-200 italic border-l-2 border-emerald-500/60 pl-2.5 py-1">
                  "{scoutReport.summary_text}"
                </p>
                <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                  <div className="bg-black/40 p-2 rounded">
                    <p className="text-[10px] text-slate-400 uppercase">Rarity Classification</p>
                    <p className="gx-display text-sm font-bold text-amber-300 uppercase">
                      {scoutReport.rarity_tier || "Standard"}
                    </p>
                  </div>
                  <div className="bg-black/40 p-2 rounded">
                    <p className="text-[10px] text-slate-400 uppercase">Scouted Potential</p>
                    <p className="gx-mono text-sm font-bold text-emerald-300">
                      {scoutReport.potential_range?.min ?? potential} -{" "}
                      {scoutReport.potential_range?.max ?? Math.min(99, potential + 5)}
                    </p>
                  </div>
                </div>
              </div>
            )}

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

            {/* Official Career History Table (when available from backend) */}
            {careerEntries.length > 0 && (
              <div className="rounded-md border border-white/10 bg-slate-900/60 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="gx-eyebrow text-slate-400">Career Participation Record</p>
                  <Award size={13} className="text-slate-400" />
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-white/10 text-[10px] text-slate-400 uppercase">
                        <th className="pb-1.5">Season</th>
                        <th className="pb-1.5">Club</th>
                        <th className="pb-1.5 text-right">Apps</th>
                        <th className="pb-1.5 text-right">Goals</th>
                        <th className="pb-1.5 text-right">Rating</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {careerEntries.map((c: any, i: number) => (
                        <tr key={c.id || i}>
                          <td className="py-1.5 gx-mono text-slate-300">{c.season || `S${c.season_number ?? i + 1}`}</td>
                          <td className="py-1.5 text-white font-medium">{c.club_name || c.club_id || "GTEX Academy"}</td>
                          <td className="py-1.5 text-right gx-mono text-slate-300">{c.matches ?? c.appearances ?? 0}</td>
                          <td className="py-1.5 text-right gx-mono text-emerald-400 font-bold">{c.goals ?? 0}</td>
                          <td className="py-1.5 text-right gx-mono text-amber-300">{c.average_rating ? Number(c.average_rating).toFixed(1) : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Chronological Narrative Timeline */}
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
