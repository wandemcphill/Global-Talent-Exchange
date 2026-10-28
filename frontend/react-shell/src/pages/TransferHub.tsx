import React, { useState, useEffect, useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowLeftRight,
  ArrowRight,
  Camera,
  CheckCircle2,
  Clock,
  Filter,
  Flame,
  Handshake,
  Megaphone,
  MessageSquare,
  Search,
  Shirt,
  Sparkles,
  UserCheck,
  X,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, useActiveClub, useClub } from "@/lib/owner";
import { Loading } from "@/components/gtex/ui";
import { PlayerDossier } from "@/components/gtex/PlayerDossier";
import {
  describeNegotiation,
  describeOffer,
  formatWhen,
  isNegotiationActionable,
  journeyLinks,
  readJourneyParams,
  TransferLane,
} from "@/lib/playerJourney";
import { toast } from "sonner";

export function TransferHub() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const { active: activeClub } = useActiveClub();
  const { data: clubDetail } = useClub(activeClub?.club_id);

  const journeyParams = useMemo(() => readJourneyParams(location.search), [location.search]);

  const [lane, setLane] = useState<TransferLane>(journeyParams.lane || "listings");
  const [targetPlayerId, setTargetPlayerId] = useState<string | null>(journeyParams.player);
  const [search, setSearch] = useState("");
  const [selectedPosition, setSelectedPosition] = useState("ALL");
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);

  // New Signing Presentation / Unveil Ceremony Modal State
  const [unveilingPlayer, setUnveilingPlayer] = useState<any | null>(null);
  const [shirtNumber, setShirtNumber] = useState("9");
  const [unveilTheme, setUnveilTheme] = useState<"stadium_floodlights" | "boardroom_press" | "viral_helicopter">("stadium_floodlights");
  const [unveilQuote, setUnveilQuote] = useState("I came here to lift trophies under these floodlights and make history for the supporters.");
  const [unveiledReceipt, setUnveiledReceipt] = useState<any | null>(null);

  useEffect(() => {
    if (journeyParams.lane && journeyParams.lane !== lane) {
      setLane(journeyParams.lane);
    }
    if (journeyParams.player !== targetPlayerId) {
      setTargetPlayerId(journeyParams.player);
    }
  }, [journeyParams.lane, journeyParams.player]);

  const updateLane = (nextLane: TransferLane) => {
    setLane(nextLane);
    const searchParams = new URLSearchParams(location.search);
    searchParams.set("lane", nextLane);
    navigate({ search: `?${searchParams.toString()}` }, { replace: true });
  };

  const clearTargetFilter = () => {
    setTargetPlayerId(null);
    const searchParams = new URLSearchParams(location.search);
    searchParams.delete("player");
    const nextSearch = searchParams.toString();
    navigate({ search: nextSearch ? `?${nextSearch}` : "" }, { replace: true });
  };

  // Offer modal state
  const [offerListing, setOfferListing] = useState<any | null>(null);
  const [offerAmount, setOfferAmount] = useState<string>("");
  const [offerWage, setOfferWage] = useState<string>("");
  const [submittingOffer, setSubmittingOffer] = useState(false);

  // Persisted negotiation contract-offer modal state
  const [contractOfferNegotiation, setContractOfferNegotiation] = useState<any | null>(null);
  const [contractWageOffer, setContractWageOffer] = useState<string>("");
  const [contractYears, setContractYears] = useState<string>("3");
  const [contractExpectedRole, setContractExpectedRole] = useState<string>("");
  const [submittingContractOffer, setSubmittingContractOffer] = useState(false);

  // Lane 1: Listings Query
  const {
    data: listingsData = [],
    isLoading: loadingListings,
    error: listingsError,
    refetch: refetchListings,
  } = useQuery({
    queryKey: ["transfer-listings", selectedPosition],
    queryFn: async () => {
      const params: any = { status: "open" };
      if (selectedPosition !== "ALL") params.position = selectedPosition;
      const { data } = await api.get("/transfer-hub/listings", { params });
      return data || [];
    },
  });

  // Lane 2: Offers Query (Incoming & Outgoing for active club)
  const {
    data: offersData = [],
    isLoading: loadingOffers,
    error: offersError,
    refetch: refetchOffers,
  } = useQuery({
    queryKey: ["transfer-offers", activeClub?.club_id],
    queryFn: async () => {
      const params: any = {};
      if (activeClub?.club_id) params.club_id = activeClub.club_id;
      const { data } = await api.get("/transfer-hub/offers", { params });
      return data || [];
    },
    enabled: !!activeClub?.club_id && lane === "offers",
  });

  // Read watchlist entries for the verified active club
  const {
    data: shortlistData = [],
    isLoading: loadingShortlist,
    error: shortlistError,
    refetch: refetchShortlist,
  } = useQuery({
    queryKey: ["transfer-market-watchlist", activeClub?.club_id],
    queryFn: async () => {
      if (!activeClub?.club_id) return [];
      const { data } = await api.get("/transfer-market/watchlist", {
        params: { club_id: activeClub.club_id },
      });
      return data || [];
    },
    enabled: !!activeClub?.club_id && lane === "shortlist",
  });

  const bidListings = listingsData.filter(
    (listing: any) => listing.status === "open",
  );

  const {
    data: negotiationsData = [],
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
    enabled: !!activeClub?.club_id && lane === "negotiations",
  });

  const [bidAmounts, setBidAmounts] = useState<Record<string, string>>({});
  const [placingBidId, setPlacingBidId] = useState<string | null>(null);

  // Actions on Offers
  const handleAcceptOffer = async (offerId: string) => {
    try {
      const { data } = await api.post(`/transfer-hub/offers/${offerId}/accept`);
      const resolvedStatus = String(data?.status || "updated").replace(/_/g, " ");
      toast.success(`Transfer offer ${resolvedStatus}.`);
      refetchOffers();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const handleRejectOffer = async (offerId: string) => {
    try {
      await api.post(`/transfer-hub/offers/${offerId}/reject`);
      toast.info("Transfer offer rejected.");
      refetchOffers();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const handlePlaceBid = async (listing: any) => {
    const rawAmount = bidAmounts[listing.id];
    const amount = Number(rawAmount);
    if (!activeClub?.club_id) {
      toast.error("Select an active club before placing a bid.");
      return;
    }
    const bidThreshold =
      Number(listing.current_highest_bid || 0) > 0
        ? Number(listing.current_highest_bid)
        : Number(listing.base_price || 0);
    if (!rawAmount || !Number.isFinite(amount) || amount <= bidThreshold) {
      toast.error(`Enter a valid bid greater than ${fmt(bidThreshold)} GTX.`);
      return;
    }

    setPlacingBidId(listing.id);
    try {
      await api.post(`/transfer-market/listings/${listing.id}/bids`, {
        bidder_club_id: activeClub.club_id,
        amount,
        activity_context: "react_transfer_hub_bid_lane",
      });
      toast.success("Bid submitted to the transfer market.");
      setBidAmounts((previous) => ({ ...previous, [listing.id]: "" }));
      await qc.invalidateQueries({ queryKey: ["transfer-listings"] });
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setPlacingBidId(null);
    }
  };

  // Submit new offer
  const handleSubmitOffer = async () => {
    if (!offerListing || !offerAmount || !activeClub?.club_id) return;
    setSubmittingOffer(true);
    try {
      await api.post(`/transfer-hub/listings/${offerListing.id}/offers`, {
        bidder_club_id: activeClub.club_id,
        offer_type: "transfer",
        cash_amount: Number(offerAmount),
        conditional_terms: offerWage ? { proposed_weekly_wage: Number(offerWage) } : {},
        message: offerWage ? `Proposed weekly wage: ${Number(offerWage)} GTX/w` : undefined,
      });
      toast.success(`Formal offer of ${fmt(offerAmount)} GTX submitted to selling club!`);
      setOfferListing(null);
      setOfferAmount("");
      setOfferWage("");
      qc.invalidateQueries({ queryKey: ["transfer-offers"] });
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setSubmittingOffer(false);
    }
  };

  const handleSubmitContractOffer = async () => {
    if (!contractOfferNegotiation || !activeClub?.club_id) return;
    const wage = Number(contractWageOffer);
    const years = Number(contractYears);
    if (!contractWageOffer.trim() || !Number.isFinite(wage) || wage < 0 || !Number.isInteger(years) || years < 1 || years > 5) {
      toast.error("Enter a valid weekly wage and contract length (1–5 years).");
      return;
    }

    setSubmittingContractOffer(true);
    try {
      const { data: updatedNeg } = await api.post(
        `/transfer-market/listings/${contractOfferNegotiation.listing_id}/contract-offer`,
        {
          bidder_club_id: activeClub.club_id,
          wage_offer_amount: wage,
          contract_years: years,
          expected_role: contractExpectedRole.trim() || undefined,
        },
      );
      toast.success("Contract offer submitted to the transfer workflow.");
      const targetName = contractOfferNegotiation.player_name || `Player ${contractOfferNegotiation.player_id}`;
      setContractOfferNegotiation(null);
      setContractWageOffer("");
      setContractYears("3");
      setContractExpectedRole("");
      if (updatedNeg?.status === "completed") {
        setUnveilingPlayer({
          player_id: updatedNeg.player_id,
          name: targetName,
          position: updatedNeg.expected_role || "STARTER",
          rating: 82,
        });
      }
      await qc.invalidateQueries({ queryKey: ["transfer-market-negotiations", activeClub.club_id] });
      await qc.invalidateQueries({ queryKey: ["transfer-offers", activeClub.club_id] });
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setSubmittingContractOffer(false);
    }
  };

  const handleSyncTeamDynamics = async (positionDemand: string) => {
    if (!activeClub?.club_id) return;
    try {
      await api.post(`/transfer-market/coaches/${activeClub.club_id}/demands`, {
        position: positionDemand,
        urgency: "high",
        preferred_style: "high_intensity",
        min_rating: 72,
      });
      await api.put(`/transfer-market/clubs/${activeClub.club_id}/team-dynamics`, {
        dressing_room_morale: 84,
        tactical_cohesion: 80,
        leadership_balance: 78,
        wage_harmony: 82,
      });
      toast.success(`First-Team Manager transfer demand (${positionDemand}) & dressing-room dynamics synced!`);
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const handleConfirmUnveiling = () => {
    if (!unveilingPlayer) return;
    const shirtSalesBonus = unveilTheme === "viral_helicopter" ? 1850 : unveilTheme === "stadium_floodlights" ? 1200 : 750;
    setUnveiledReceipt({
      player: unveilingPlayer,
      shirtNumber,
      theme: unveilTheme,
      quote: unveilQuote,
      shirtSalesBonus,
      moraleBoost: 8,
    });
    setUnveilingPlayer(null);
    toast.success(`Unveiled ${unveilingPlayer.name} (#${shirtNumber}) to the global press room!`);
  };

  // Filter listings
  const filteredListings = listingsData.filter((l: any) => {
    const p = l.player || {};
    const name = (p.full_name || p.name || p.player_name || l.player_id || "").toLowerCase();
    if (targetPlayerId && l.player_id !== targetPlayerId) return false;
    if (search && !name.includes(search.toLowerCase())) return false;
    return true;
  });

  // Filter negotiations
  const filteredNegotiations = negotiationsData.filter((n: any) => {
    if (targetPlayerId && n.player_id !== targetPlayerId) return false;
    return true;
  });

  // Filter offers
  const filteredOffers = offersData.filter((offer: any) => {
    if (targetPlayerId) {
      const matchListing = listingsData.find((l: any) => l.id === offer.listing_id);
      if (matchListing && matchListing.player_id !== targetPlayerId) return false;
    }
    return true;
  });

  // Filter shortlist
  const filteredShortlist = shortlistData.filter((entry: any) => {
    if (targetPlayerId && entry.player_id !== targetPlayerId) return false;
    return true;
  });

  const squadCandidates: any[] = clubDetail?.squad || [];

  return (
    <div className="space-y-8 p-4 sm:p-8" data-testid="transfer-hub-screen">
      {/* Transfer Command Header */}
      <section className="relative overflow-hidden rounded-2xl border-2 border-emerald-500/30 bg-gradient-to-r from-[#071912] via-[#09151e] to-[#0a1017] p-6 sm:p-8 shadow-2xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/50 bg-emerald-950/80 px-3 py-1 text-[11px] font-black uppercase tracking-widest text-emerald-300">
              <ArrowLeftRight size={12} /> SPORTING TRANSFERS WORKSPACE
            </div>
            <h1 className="gx-display mt-2 text-3xl sm:text-5xl font-black uppercase tracking-tight text-white leading-none">
              Club Transfer Hub
            </h1>
            <p className="mt-1 text-xs sm:text-sm text-slate-300">
              Active Negotiator for <b className="text-white">{activeClub?.club_name || "Active Club"}</b> · Real contracts, official bids, and verified settlements.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            <div className="rounded-lg border border-white/10 bg-black/40 px-3.5 py-2">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Transfer Budget</p>
              <p className="gx-mono text-lg font-black text-emerald-300">
                {activeClub?.transfer_budget != null ? fmt(activeClub.transfer_budget) : "—"} <span className="text-[10px] text-emerald-400/80">GTX</span>
              </p>
            </div>
            <div className="rounded-lg border border-white/10 bg-black/40 px-3.5 py-2">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Wage Room</p>
              <p className="gx-mono text-lg font-black text-amber-300">
                {activeClub?.wage_budget != null ? fmt(activeClub.wage_budget) : "—"} <span className="text-[10px] text-amber-400/80">GTX/w</span>
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                const candidate = squadCandidates[0] || {
                  player_id: "star-signing",
                  name: "Star Signing",
                  position: "ST",
                  rating: 84,
                };
                setUnveilingPlayer(candidate);
              }}
              className="gx-btn gx-btn-primary text-xs flex items-center gap-1.5"
              data-testid="open-signing-presentation-btn"
            >
              <Camera size={14} /> Stage Signing Presentation
            </button>
          </div>
        </div>

        {/* Transfer Drama, Super-Agent Rumors & Coach Demands Strip */}
        <div
          className="mt-5 grid gap-3 md:grid-cols-3 rounded-xl border border-white/10 bg-black/40 p-3.5 text-xs"
          data-testid="transfer-drama-strip"
        >
          <div className="flex items-start gap-2.5">
            <Flame size={16} className="text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold uppercase tracking-wider text-amber-300 text-[10px]">Window Drama & Rumor Mill</p>
              <p className="text-slate-300 mt-0.5">
                Super-agent <b>Mino Sterling</b> is briefing media that rival clubs are preparing late release-clause raids before the deadline.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <Megaphone size={16} className="text-cyan-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold uppercase tracking-wider text-cyan-300 text-[10px]">Manager Priority Target</p>
              <p className="text-slate-300 mt-0.5">
                First-Team Manager requests a high-pressing spine signing to maintain dressing-room ambition.
              </p>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => handleSyncTeamDynamics("ST")}
              className="gx-btn gx-btn-secondary text-xs"
              data-testid="sync-coach-demand-st"
            >
              Log Manager ST Demand
            </button>
            <button
              type="button"
              onClick={() => handleSyncTeamDynamics("CB")}
              className="gx-btn gx-btn-ghost text-xs"
              data-testid="sync-coach-demand-cb"
            >
              Log CB Demand
            </button>
          </div>
        </div>

        {/* Active Journey Filter Pill (carried canonical ID) */}
        {targetPlayerId && (
          <div
            className="mt-4 inline-flex items-center gap-2 rounded-lg border border-cyan-500/40 bg-cyan-950/60 px-3 py-1.5 text-xs text-cyan-200"
            data-testid="target-player-filter-banner"
          >
            <span>
              Target prospect: <b className="font-mono text-white">{targetPlayerId}</b>
            </span>
            <button
              type="button"
              onClick={clearTargetFilter}
              className="rounded p-0.5 hover:bg-white/10 text-slate-300 hover:text-white"
              title="Clear player filter"
            >
              <X size={14} />
            </button>
          </div>
        )}
      </section>

      {/* Five Lanes Navigation Tabs */}
      <nav className="flex flex-wrap gap-2 border-b border-white/10 pb-4" data-testid="transfer-hub-lanes">
        {[
          { id: "listings", label: "Market Listings", count: filteredListings.length, icon: ArrowLeftRight },
          { id: "offers", label: "Active Offers", count: filteredOffers.length, icon: Handshake },
          { id: "negotiations", label: "Negotiations", count: filteredNegotiations.length, icon: MessageSquare },
          { id: "bids", label: "Window Bids", count: bidListings.length, icon: Clock },
          { id: "shortlist", label: "Shortlist", count: filteredShortlist.length, icon: Sparkles },
        ].map((item) => {
          const Icon = item.icon;
          const active = lane === item.id;
          return (
            <button
              key={item.id}
              onClick={() => updateLane(item.id as any)}
              data-testid={`lane-${item.id}`}
              className={`flex items-center gap-2 rounded-lg px-4 py-2.5 text-xs font-bold uppercase tracking-wider transition-all ${
                active
                  ? "bg-emerald-500 text-slate-950 shadow-[0_0_16px_rgba(16,185,129,0.35)]"
                  : "border border-white/10 bg-slate-900/60 text-slate-300 hover:border-emerald-400/40 hover:text-white"
              }`}
            >
              <Icon size={14} />
              {item.label}
              {item.count != null && item.count > 0 && (
                <span className={`gx-mono rounded px-1.5 py-0.2 text-[10px] font-black ${
                  active ? "bg-slate-950 text-emerald-300" : "bg-white/10 text-slate-200"
                }`}>
                  {item.count}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Lane 1: Listings */}
      {lane === "listings" && (
        <div className="space-y-6" data-testid="lane-listings-view">
          {/* Filters Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 bg-slate-900/60 p-4 rounded-xl border border-white/10">
            <div className="relative sm:col-span-2">
              <Search className="absolute left-3 top-3 size-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search listed players, asking price or club..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="gx-input pl-9"
              />
            </div>
            <div>
              <select
                value={selectedPosition}
                onChange={(e) => setSelectedPosition(e.target.value)}
                className="gx-input"
              >
                <option value="ALL">All Positions</option>
                <option value="GK">Goalkeepers</option>
                <option value="DEF">Defenders</option>
                <option value="MID">Midfielders</option>
                <option value="FWD">Attackers</option>
              </select>
            </div>
            <div className="flex items-center text-xs text-slate-400 px-2">
              <span>{filteredListings.length} Sporting Listings Available</span>
            </div>
          </div>

          {loadingListings ? (
            <Loading label="Querying transfer market listings..." />
          ) : listingsError ? (
            <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-6 text-center">
              <p className="gx-display text-lg font-bold uppercase text-white">Market listings unavailable</p>
              <p className="text-sm text-slate-300 mt-1">{errMsg(listingsError)}</p>
              <button type="button" onClick={() => refetchListings()} className="gx-btn gx-btn-secondary mt-3 text-xs">Retry</button>
            </div>
          ) : filteredListings.length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
              <ArrowLeftRight className="mx-auto size-10 text-emerald-400/50 mb-3" />
              <p className="gx-display text-xl font-bold uppercase text-white">No active transfer listings</p>
              <p className="text-sm text-slate-400 mt-1">
                {targetPlayerId
                  ? `Target prospect ${targetPlayerId} is not currently listed by their club.`
                  : "Clubs have not placed matching players on the market."}
              </p>
              {targetPlayerId && (
                <button
                  type="button"
                  onClick={clearTargetFilter}
                  className="gx-btn gx-btn-secondary mt-4 text-xs"
                >
                  View All Listings
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 place-items-center">
              {filteredListings.map((listing: any) => {
                const p = listing.player || {};
                const playerId = listing.player_id || p.id;
                return (
                  <div key={listing.id} className="flex flex-col w-full max-w-[310px]">
                    <div className="flex-1 rounded-xl border border-white/10 bg-slate-900/70 p-4 space-y-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="gx-display text-lg font-bold uppercase text-white">
                            {p.full_name || playerId}
                          </h3>
                          <p className="text-xs text-slate-400 mt-1">
                            {p.normalized_position || "Position not recorded"}
                          </p>
                        </div>
                        <span className="shrink-0 gx-mono text-xs font-black text-amber-300">
                          {fmt(listing.base_price)} GTX
                        </span>
                      </div>
                      <p className="text-xs text-slate-400">
                        {p.current_club_name ? `Current club: ${p.current_club_name}` : "Current club not recorded"}
                      </p>
                      {p.market_value != null && (
                        <p className="text-xs text-slate-400">
                          Imported market reference: €{new Intl.NumberFormat("en-IE", { maximumFractionDigits: 0 }).format(Number(p.market_value))}
                        </p>
                      )}
                      <p className="text-xs text-slate-500">
                        Listing status: {listing.status} · {Math.ceil(Number(listing.time_remaining || 0) / 60)} minutes remaining
                      </p>
                      <button
                        type="button"
                        onClick={() => setSelectedPlayerId(playerId)}
                        className="gx-btn gx-btn-secondary w-full text-xs"
                      >
                        Open player dossier
                      </button>
                    </div>
                    <button
                      type="button"
                      disabled={!activeClub?.club_id || listing.status !== "open"}
                      onClick={() => {
                        setOfferListing(listing);
                        setOfferAmount(String(listing.base_price ?? ""));
                      }}
                      className="gx-btn gx-btn-primary mt-2.5 w-full text-xs font-black shadow-md disabled:cursor-not-allowed disabled:opacity-50"
                      data-testid={`make-offer-btn-${listing.id}`}
                    >
                      <Handshake size={14} /> Submit Club Offer
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Lane 2: Offers */}
      {lane === "offers" && (
        <div className="space-y-4" data-testid="lane-offers-view">
          {loadingOffers ? (
            <Loading label="Gathering offer transactions..." />
          ) : !activeClub?.club_id ? (
            <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
              <Handshake className="mx-auto size-10 text-emerald-400/50 mb-3" />
              <p className="gx-display text-xl font-bold uppercase text-white">Choose an active club</p>
              <p className="text-sm text-slate-400 mt-1">Offers are scoped to a club you are authorized to manage.</p>
            </div>
          ) : offersError ? (
            <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-6 text-center">
              <p className="gx-display text-lg font-bold uppercase text-white">Transfer offers unavailable</p>
              <p className="text-sm text-slate-300 mt-1">{errMsg(offersError)}</p>
              <button type="button" onClick={() => refetchOffers()} className="gx-btn gx-btn-secondary mt-3 text-xs">Retry</button>
            </div>
          ) : filteredOffers.length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
              <Handshake className="mx-auto size-10 text-emerald-400/50 mb-3" />
              <p className="gx-display text-xl font-bold uppercase text-white">No open transfer offers</p>
              <p className="text-sm text-slate-400 mt-1">
                Browse listings to make an offer, or list squad players to invite bids.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredOffers.map((offer: any) => {
                const isIncoming = offer.seller_club_id === activeClub?.club_id;
                const matchListing = listingsData.find(
                  (listing: any) => listing.id === offer.listing_id,
                );
                const offerPlayerName =
                  matchListing?.player?.full_name || `Listing ${String(offer.listing_id).slice(0, 8)}`;
                const offerPlayerId = matchListing?.player_id;
                const offerIsActionable = ["open", "countered"].includes(String(offer.status));
                const offerStatusView = describeOffer(offer.status);

                return (
                  <div
                    key={offer.id}
                    className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-xl border border-white/10 bg-slate-900/60 p-4 shadow-lg"
                    data-testid={`transfer-offer-row-${offer.id}`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`rounded px-2 py-0.5 text-[9px] font-black uppercase ${
                          isIncoming ? "bg-cyan-500/20 text-cyan-300" : "bg-emerald-500/20 text-emerald-300"
                        }`}>
                          {isIncoming ? "Incoming Offer" : "Outgoing Offer"}
                        </span>
                        <span className="gx-mono text-xs text-slate-400">ID: {offer.id.slice(0, 8)}</span>
                        {offerPlayerId && (
                          <span className="gx-mono text-[10px] text-slate-500">Player: {offerPlayerId}</span>
                        )}
                      </div>
                      <h4 className="gx-display text-lg font-bold uppercase text-white">
                        {offerPlayerName}
                      </h4>
                      <p className="text-xs text-slate-300">
                        Offered: <b className="text-amber-300 font-mono">{fmt(offer.cash_amount)} GTX</b> · Proposed Wage: <b className="text-white font-mono">{offer.conditional_terms?.proposed_weekly_wage != null ? `${fmt(offer.conditional_terms.proposed_weekly_wage)} GTX/w` : "Not specified"}</b>
                      </p>
                      <p className="text-[11px] text-slate-400 italic">
                        {offerStatusView.explanation}
                      </p>
                    </div>

                    <div className="flex flex-col sm:flex-row items-end sm:items-center gap-2">
                      {isIncoming && offerIsActionable && (
                        <>
                          <button
                            type="button"
                            onClick={() => handleAcceptOffer(offer.id)}
                            className="gx-btn gx-btn-primary text-xs"
                            data-testid={`accept-offer-${offer.id}`}
                          >
                            Accept
                          </button>
                          <button
                            type="button"
                            onClick={() => handleRejectOffer(offer.id)}
                            className="gx-btn gx-btn-danger text-xs"
                            data-testid={`reject-offer-${offer.id}`}
                          >
                            Reject
                          </button>
                        </>
                      )}

                      {!isIncoming && offer.status === "accepted" && (
                        <button
                          type="button"
                          onClick={() => updateLane("negotiations")}
                          className="gx-btn gx-btn-primary text-xs font-bold"
                        >
                          Negotiate Terms <ArrowRight size={12} className="ml-1 inline" />
                        </button>
                      )}

                      <span className="gx-mono text-xs font-bold uppercase">
                        Status: <b className={offerStatusView.tone === "emerald" ? "text-emerald-300" : offerStatusView.tone === "red" ? "text-rose-400" : "text-white"}>{offerStatusView.label}</b>
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Lane 3: Persisted negotiations */}
      {lane === "negotiations" && (
        <div className="space-y-4" data-testid="lane-negotiations-view">
          {loadingNegotiations ? (
            <Loading label="Loading persisted transfer negotiations..." />
          ) : !activeClub?.club_id ? (
            <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
              <MessageSquare className="mx-auto size-10 text-emerald-400/50 mb-3" />
              <p className="gx-display text-xl font-bold uppercase text-white">Choose an active club</p>
              <p className="text-sm text-slate-400 mt-1">Negotiations are scoped to a club you are authorized to manage.</p>
            </div>
          ) : negotiationsError ? (
            <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-6 text-center">
              <p className="gx-display text-lg font-bold uppercase text-white">Negotiations unavailable</p>
              <p className="text-sm text-slate-300 mt-1">{errMsg(negotiationsError)}</p>
              <button
                type="button"
                onClick={() => refetchNegotiations()}
                className="gx-btn gx-btn-secondary mt-3 text-xs"
              >
                Retry
              </button>
            </div>
          ) : filteredNegotiations.length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
              <MessageSquare className="mx-auto size-10 text-emerald-400/50 mb-3" />
              <p className="gx-display text-xl font-bold uppercase text-white">No accessible active negotiations</p>
              <p className="text-sm text-slate-400 mt-1">
                {targetPlayerId
                  ? `No active negotiation recorded for prospect ${targetPlayerId}. Once a transfer offer is accepted, negotiations start automatically.`
                  : "This view only shows negotiations returned by the authenticated API. Browse market listings or active offers to start a real transfer workflow."}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredNegotiations.map((negotiation: any) => {
                const statusView = describeNegotiation(negotiation.status, {
                  decisionDueAt: negotiation.decision_due_at,
                });
                const isCompleted = negotiation.status === "completed";
                const isBuyer = negotiation.bidder_club_id === activeClub?.club_id;
                const actionable = isBuyer && isNegotiationActionable(negotiation.status);

                return (
                  <div
                    key={negotiation.id}
                    className="rounded-xl border border-white/10 bg-slate-900/70 p-5 space-y-4 shadow-xl"
                    data-testid={`negotiation-card-${negotiation.id}`}
                  >
                    {/* Header */}
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-3">
                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded px-2.5 py-0.5 text-[10px] font-black uppercase ${
                            statusView.tone === "emerald"
                              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                              : statusView.tone === "cyan"
                              ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                              : statusView.tone === "red"
                              ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                              : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                          }`}
                        >
                          {statusView.label}
                        </span>
                        <span className="gx-mono text-xs text-slate-400">ID: {negotiation.id.slice(0, 8)}</span>
                      </div>
                      <span className="text-xs text-slate-400">
                        {negotiation.selling_club_id} → {negotiation.bidder_club_id}
                      </span>
                    </div>

                    {/* Player Info */}
                    <div>
                      <h4 className="gx-display text-2xl font-black uppercase text-white">
                        {negotiation.player_name || `Player ${negotiation.player_id}`}
                      </h4>
                      <p className="gx-mono text-xs text-slate-400 mt-0.5">
                        Canonical Player ID: {negotiation.player_id}
                      </p>
                      <p className="text-xs text-slate-300 mt-2">
                        Listing {String(negotiation.listing_id).slice(0, 8)} · Expected role: {negotiation.expected_role || "Not specified"} · {negotiation.contract_years} year contract
                      </p>
                      <p className="text-xs text-slate-400 mt-0.5">{statusView.explanation}</p>
                    </div>

                    {/* DECISION LOOP BREAKDOWN: Player, Coach, Agent */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
                      {/* Player Decision */}
                      <div className="rounded-lg border border-white/5 bg-black/40 p-3 space-y-1.5">
                        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Player Decision</p>
                        {negotiation.player_decision ? (
                          <>
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-white capitalize">{negotiation.player_decision.interest_level || "Neutral"}</span>
                              <span className="gx-mono text-xs text-emerald-300">{negotiation.player_decision.decision_score?.toFixed(0)}/100</span>
                            </div>
                            {negotiation.player_decision.concerns?.length > 0 && (
                              <p className="text-[11px] text-amber-300">
                                Concerns: {negotiation.player_decision.concerns.join(", ")}
                              </p>
                            )}
                          </>
                        ) : (
                          <p className="text-xs text-slate-500 italic">No player response recorded yet.</p>
                        )}
                      </div>

                      {/* Coach Opinion */}
                      <div className="rounded-lg border border-white/5 bg-black/40 p-3 space-y-1.5">
                        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Coach Tactical Opinion</p>
                        {negotiation.coach_opinion ? (
                          <>
                            <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                              negotiation.coach_opinion.stance === "approve"
                                ? "bg-emerald-950 text-emerald-300"
                                : negotiation.coach_opinion.stance === "reject"
                                ? "bg-rose-950 text-rose-300"
                                : "bg-slate-800 text-slate-300"
                            }`}>
                              Stance: {negotiation.coach_opinion.stance}
                            </span>
                            <p className="text-[11px] text-slate-300">{negotiation.coach_opinion.reason || "Tactical alignment noted."}</p>
                          </>
                        ) : (
                          <p className="text-xs text-slate-500 italic">Coach stance not recorded.</p>
                        )}
                      </div>

                      {/* Agent Negotiation */}
                      <div className="rounded-lg border border-white/5 bg-black/40 p-3 space-y-1.5">
                        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Agent Clause Demands</p>
                        {negotiation.agent_negotiation ? (
                          <>
                            <span className="text-xs font-bold text-white uppercase">{negotiation.agent_negotiation.action}</span>
                            {negotiation.agent_negotiation.demands?.length > 0 ? (
                              <p className="text-[11px] text-cyan-300">
                                Demands: {negotiation.agent_negotiation.demands.join(", ")}
                              </p>
                            ) : (
                              <p className="text-[11px] text-slate-400">No special clauses demanded.</p>
                            )}
                          </>
                        ) : (
                          <p className="text-xs text-slate-500 italic">Agent has not raised demands.</p>
                        )}
                      </div>
                    </div>

                    {/* Completion banner or Action bar */}
                    {isCompleted ? (
                      <div className="rounded-lg border border-emerald-500/40 bg-emerald-950/40 p-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 size={18} className="text-emerald-400 shrink-0" />
                          <div>
                            <p className="text-xs font-bold text-white">Transfer & Contract Finalized</p>
                            <p className="text-[11px] text-emerald-200">
                              Player is signed to your club. Unveil them to the media or proceed to Squad room.
                            </p>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() =>
                              setUnveilingPlayer({
                                player_id: negotiation.player_id,
                                name: negotiation.player_name || `Player ${negotiation.player_id}`,
                                position: negotiation.expected_role || "STARTER",
                                rating: 83,
                              })
                            }
                            className="gx-btn gx-btn-secondary text-xs inline-flex items-center gap-1"
                          >
                            <Camera size={12} /> Unveil Signing
                          </button>
                          <a
                            href={journeyLinks.squad(negotiation.player_id)}
                            className="gx-btn gx-btn-primary text-xs shrink-0 inline-flex items-center gap-1"
                          >
                            Register in Squad <ArrowRight size={12} />
                          </a>
                        </div>
                      </div>
                    ) : (
                      <div className="pt-2 border-t border-white/10 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => setSelectedPlayerId(negotiation.player_id)}
                          className="gx-btn gx-btn-secondary text-xs"
                        >
                          View player dossier
                        </button>
                        {actionable && (
                          <button
                            type="button"
                            onClick={() => {
                              setContractOfferNegotiation(negotiation);
                              setContractWageOffer(
                                negotiation.wage_offer_amount == null ? "" : String(negotiation.wage_offer_amount),
                              );
                              setContractYears(String(negotiation.contract_years || 3));
                              setContractExpectedRole(negotiation.expected_role || "");
                            }}
                            className="gx-btn gx-btn-primary text-xs"
                            data-testid={`contract-offer-${negotiation.id}`}
                          >
                            Submit contract terms
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Lane 4: Persisted market bids */}
      {lane === "bids" && (
        <div className="space-y-4" data-testid="lane-bids-view">
          <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-4 text-xs text-amber-200 flex items-center gap-2">
            <Clock size={16} /> Bids below or equal to the current highest bid are rejected by the market.
          </div>
          {!activeClub?.club_id ? (
            <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
              <Clock className="mx-auto size-10 text-emerald-400/50 mb-3" />
              <p className="gx-display text-xl font-bold uppercase text-white">Choose an active club</p>
              <p className="text-sm text-slate-400 mt-1">Bids can only be submitted for a club you are authorized to manage.</p>
            </div>
          ) : bidListings.length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
              <Clock className="mx-auto size-10 text-emerald-400/50 mb-3" />
              <p className="gx-display text-xl font-bold uppercase text-white">No open transfer listings</p>
              <p className="text-sm text-slate-400 mt-1">Open transfer listings will appear here when the market has eligible players available to bid on.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {bidListings.map((listing: any) => {
                const currentHighest = Number(listing.current_highest_bid || 0);
                const bidThreshold = currentHighest > 0 ? currentHighest : Number(listing.base_price || 0);
                const enteredAmount = bidAmounts[listing.id] || "";
                const amountIsValid = enteredAmount.trim() !== ""
                  && Number.isFinite(Number(enteredAmount))
                  && Number(enteredAmount) > bidThreshold;
                return (
                  <div key={listing.id} className="flex flex-col gap-4 rounded-xl border border-white/10 bg-slate-900/60 p-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0">
                      <h4 className="gx-display text-lg font-bold uppercase text-white">
                        {listing.player?.full_name || listing.player_id}
                      </h4>
                      <p className="text-xs text-slate-400">
                        Highest bidder: {listing.current_bid?.club_name || "Name unavailable"}
                        {" · "}Time remaining: {Math.ceil(Number(listing.time_remaining || 0) / 60)} min
                      </p>
                      <p className="gx-mono mt-1 text-sm font-black text-amber-300">
                        {currentHighest > 0
                          ? `Current highest bid: ${fmt(currentHighest)} GTX`
                          : `No bids yet · Opening bid must exceed ${fmt(listing.base_price)} GTX`}
                      </p>
                    </div>
                    <div className="flex flex-col gap-2 sm:w-64">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        Your bid (GTX)
                      </label>
                      <input
                        type="number"
                        min={bidThreshold + 0.01}
                        value={enteredAmount}
                        onChange={(event) => setBidAmounts((previous) => ({
                          ...previous,
                          [listing.id]: event.target.value,
                        }))}
                        placeholder={`Greater than ${String(bidThreshold)}`}
                        className="gx-input"
                        data-testid={`bid-amount-${listing.id}`}
                      />
                      <button
                        type="button"
                        onClick={() => handlePlaceBid(listing)}
                        disabled={!amountIsValid || placingBidId === listing.id}
                        className="gx-btn gx-btn-primary text-xs disabled:cursor-not-allowed disabled:opacity-50"
                        data-testid={`place-bid-${listing.id}`}
                      >
                        {placingBidId === listing.id ? "Submitting..." : "Submit bid"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Lane 5: Persisted club shortlist */}
      {lane === "shortlist" && (
        <div className="space-y-4" data-testid="lane-shortlist-view">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="gx-eyebrow text-emerald-400">Club Scouting Shortlist</p>
              <p className="text-xs text-slate-400 mt-1">Players saved by scouting actions for the active club.</p>
            </div>
            <span className="text-xs text-slate-400">
              {filteredShortlist.length} saved target{filteredShortlist.length === 1 ? "" : "s"}
            </span>
          </div>
          {loadingShortlist ? (
            <Loading label="Loading the club's persisted scouting shortlist..." />
          ) : !activeClub?.club_id ? (
            <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
              <Sparkles className="mx-auto size-10 text-emerald-400/50 mb-3" />
              <p className="gx-display text-xl font-bold uppercase text-white">Choose an active club</p>
              <p className="text-sm text-slate-400 mt-1">Shortlist entries are private to the authenticated club context.</p>
            </div>
          ) : shortlistError ? (
            <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-6 text-center">
              <p className="gx-display text-lg font-bold uppercase text-white">Could not load shortlist</p>
              <p className="text-sm text-slate-300 mt-1">{errMsg(shortlistError)}</p>
              <button type="button" onClick={() => refetchShortlist()} className="gx-btn gx-btn-secondary mt-3 text-xs">Retry</button>
            </div>
          ) : filteredShortlist.length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
              <Sparkles className="mx-auto size-10 text-emerald-400/50 mb-3" />
              <p className="gx-display text-xl font-bold uppercase text-white">No saved scouting targets</p>
              <p className="text-sm text-slate-400 mt-1">
                Open a prospect's dossier and click Shortlist. Saved targets appear here after the backend confirms the write.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredShortlist.map((entry: any) => {
                const player = entry.player || {};
                const listing = entry.active_listing;
                const hasListing = Boolean(listing?.id);
                return (
                  <div key={entry.id} className="rounded-xl border border-white/10 bg-slate-900/60 p-4 space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="gx-mono text-xs font-bold text-emerald-400">
                        {player.normalized_position || "Position not recorded"}
                      </span>
                      {listing ? (
                        <span className="gx-mono text-xs font-bold text-amber-300">
                          {fmt(listing.base_price)} GTX
                        </span>
                      ) : (
                        <span className="gx-mono text-xs text-slate-400">Not listed</span>
                      )}
                    </div>
                    <h4 className="gx-display text-lg font-bold uppercase text-white">
                      {player.full_name || entry.player_id}
                    </h4>
                    <p className="gx-mono text-[10px] text-slate-400">Canonical ID: {entry.player_id}</p>
                    <p className="text-xs text-slate-400">
                      {player.current_club_name ? `Current club: ${player.current_club_name}` : "No current club is recorded."}
                    </p>
                    {player.market_value != null && (
                      <p className="text-xs text-slate-400">
                        Imported market value: €{new Intl.NumberFormat("en-IE", { maximumFractionDigits: 0 }).format(Number(player.market_value))}
                      </p>
                    )}
                    <p className="text-xs text-slate-500">Saved via {entry.source || "scouting"}.</p>
                    <div className="pt-2 border-t border-white/10 flex gap-2">
                      <button
                        type="button"
                        onClick={() => setSelectedPlayerId(entry.player_id)}
                        className="gx-btn gx-btn-secondary text-xs flex-1"
                      >
                        Dossier
                      </button>
                      <button
                        type="button"
                        disabled={!hasListing || !activeClub?.club_id}
                        onClick={() => {
                          if (!listing) return;
                          setOfferListing(listing);
                          setOfferAmount(String(listing.base_price));
                        }}
                        className="gx-btn gx-btn-primary text-xs flex-1 disabled:cursor-not-allowed disabled:opacity-50"
                        title={hasListing ? "Prepare a formal offer for this market listing" : "This player has no active transfer listing"}
                      >
                        Offer
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Offer Modal */}
      {offerListing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-emerald-500/40 bg-[#07130e] p-6 shadow-2xl space-y-4">
            <h3 className="gx-display text-2xl font-black uppercase text-white">
              Submit Sporting Transfer Offer
            </h3>
            <p className="text-xs text-slate-300">
              Offering from: <b className="text-emerald-400">{activeClub?.club_name}</b>
            </p>

            <div className="space-y-3">
              <div>
                <label className="gx-label">Transfer Fee (GTX)</label>
                <input
                  type="number"
                  value={offerAmount}
                  onChange={(e) => setOfferAmount(e.target.value)}
                  className="gx-input"
                  placeholder="e.g. 50000"
                  data-testid="offer-amount-input"
                />
              </div>
              <div>
                <label className="gx-label">Proposed Weekly Wage (GTX)</label>
                <input
                  type="number"
                  value={offerWage}
                  onChange={(e) => setOfferWage(e.target.value)}
                  className="gx-input"
                  placeholder="e.g. 2500"
                  data-testid="offer-wage-input"
                />
              </div>
            </div>

            <div className="flex gap-3 pt-3">
              <button
                type="button"
                onClick={() => setOfferListing(null)}
                className="gx-btn gx-btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmitOffer}
                disabled={submittingOffer || !offerAmount}
                className="gx-btn gx-btn-primary flex-1"
                data-testid="submit-offer-confirm-btn"
              >
                {submittingOffer ? "Submitting..." : "Send Formal Offer"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Contract negotiation modal */}
      {contractOfferNegotiation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-emerald-500/40 bg-[#07130e] p-6 shadow-2xl space-y-4">
            <h3 className="gx-display text-2xl font-black uppercase text-white">
              Submit Contract Terms
            </h3>
            <p className="text-xs text-slate-300">
              {contractOfferNegotiation.player_name || `Player ${contractOfferNegotiation.player_id}`}
              {" · "}Listing {String(contractOfferNegotiation.listing_id).slice(0, 8)}
            </p>
            <div className="space-y-3">
              <div>
                <label className="gx-label">Weekly Wage Offer (GTX)</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={contractWageOffer}
                  onChange={(event) => setContractWageOffer(event.target.value)}
                  className="gx-input"
                  placeholder="Enter weekly wage"
                  data-testid="contract-wage-input"
                />
              </div>
              <div>
                <label className="gx-label">Contract Length</label>
                <select
                  value={contractYears}
                  onChange={(event) => setContractYears(event.target.value)}
                  className="gx-input"
                  data-testid="contract-years-select"
                >
                  <option value="1">1 year</option>
                  <option value="2">2 years</option>
                  <option value="3">3 years</option>
                  <option value="4">4 years</option>
                  <option value="5">5 years</option>
                </select>
              </div>
              <div>
                <label className="gx-label">Expected Squad Role</label>
                <input
                  type="text"
                  maxLength={40}
                  value={contractExpectedRole}
                  onChange={(event) => setContractExpectedRole(event.target.value)}
                  className="gx-input"
                  placeholder="e.g. starter, rotation"
                  data-testid="contract-role-input"
                />
              </div>
            </div>
            <div className="flex gap-3 pt-3">
              <button
                type="button"
                onClick={() => setContractOfferNegotiation(null)}
                className="gx-btn gx-btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmitContractOffer}
                disabled={submittingContractOffer || !contractWageOffer.trim()}
                className="gx-btn gx-btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
                data-testid="submit-contract-offer"
              >
                {submittingContractOffer ? "Submitting..." : "Submit terms"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* NEW SIGNING PRESENTATION / UNVEIL MODAL */}
      {unveilingPlayer && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4"
          role="dialog"
          aria-modal="true"
          data-testid="new-signing-presentation-modal"
        >
          <div className="w-full max-w-lg rounded-2xl border border-amber-400/50 bg-gradient-to-br from-slate-900 via-slate-950 to-emerald-950/30 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/20 px-3 py-1 text-[10px] font-black uppercase tracking-wider text-amber-300">
                <Camera size={12} /> Official Club Signing Presentation
              </span>
              <button type="button" onClick={() => setUnveilingPlayer(null)} className="text-slate-400 hover:text-white">
                <X size={16} />
              </button>
            </div>

            <h3 className="gx-display text-2xl font-black uppercase text-white">
              Unveil {unveilingPlayer.name} at {activeClub?.club_name}
            </h3>

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="gx-label">Select Squad Player / Signing</label>
                <select
                  className="gx-input mt-1"
                  value={unveilingPlayer.id || unveilingPlayer.player_id}
                  onChange={(e) => {
                    const found = squadCandidates.find((s: any) => String(s.id || s.player_id) === e.target.value);
                    if (found) setUnveilingPlayer(found);
                  }}
                >
                  <option value={unveilingPlayer.id || unveilingPlayer.player_id}>{unveilingPlayer.name}</option>
                  {squadCandidates.map((s: any) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.position} · OVR {s.rating})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="gx-label">Assign Jersey Number</label>
                <input
                  type="number"
                  min={1}
                  max={99}
                  value={shirtNumber}
                  onChange={(e) => setShirtNumber(e.target.value)}
                  className="gx-input mt-1"
                  data-testid="signing-shirt-number-input"
                />
              </div>
            </div>

            <div>
              <label className="gx-label">Presentation Spectacle Tier</label>
              <div className="grid grid-cols-3 gap-2 mt-1">
                {[
                  { id: "boardroom_press", label: "Press Flash", bonus: "+750 Shirt GTX" },
                  { id: "stadium_floodlights", label: "Floodlight Pitch", bonus: "+1,200 Shirt GTX" },
                  { id: "viral_helicopter", label: "VIP Helicopter", bonus: "+1,850 Shirt GTX" },
                ].map((tier) => (
                  <button
                    key={tier.id}
                    type="button"
                    onClick={() => setUnveilTheme(tier.id as any)}
                    className={`rounded-xl border p-2.5 text-left text-xs transition ${
                      unveilTheme === tier.id
                        ? "border-amber-400 bg-amber-500/20 text-white"
                        : "border-white/10 bg-black/40 text-slate-300"
                    }`}
                  >
                    <p className="font-bold">{tier.label}</p>
                    <p className="text-[10px] text-emerald-300 mt-0.5">{tier.bonus}</p>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="gx-label">Player First Press Quote</label>
              <input
                type="text"
                maxLength={180}
                value={unveilQuote}
                onChange={(e) => setUnveilQuote(e.target.value)}
                className="gx-input mt-1"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <button type="button" onClick={() => setUnveilingPlayer(null)} className="gx-btn gx-btn-secondary flex-1">
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmUnveiling}
                className="gx-btn gx-btn-primary flex-1"
                data-testid="confirm-signing-presentation-btn"
              >
                <Shirt size={14} /> Broadcast Unveiling
              </button>
            </div>
          </div>
        </div>
      )}

      {/* UNVEILED SIGNING RECEIPT MODAL */}
      {unveiledReceipt && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4"
          role="dialog"
          aria-modal="true"
          data-testid="signing-unveiled-receipt"
        >
          <div className="w-full max-w-md rounded-2xl border border-emerald-400/50 bg-gradient-to-br from-slate-900 via-slate-950 to-emerald-950/40 p-6 text-center shadow-2xl space-y-4">
            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full border-2 border-amber-400 bg-amber-400/15 text-2xl font-black text-amber-300">
              #{unveiledReceipt.shirtNumber}
            </div>
            <p className="text-[10px] font-black uppercase tracking-widest text-emerald-400">
              Official Signing Unveiled · {activeClub?.club_name}
            </p>
            <h3 className="gx-display text-3xl font-black uppercase text-white">
              {unveiledReceipt.player.name}
            </h3>
            <blockquote className="rounded-xl border border-white/10 bg-black/40 p-3 text-xs italic text-slate-200">
              “{unveiledReceipt.quote}”
            </blockquote>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
                <span className="text-[10px] uppercase text-slate-400 block">Replica Shirt Surge</span>
                <span className="gx-mono font-black text-amber-300">+{fmt(unveiledReceipt.shirtSalesBonus)} GTX</span>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
                <span className="text-[10px] uppercase text-slate-400 block">Supporter & Player Morale</span>
                <span className="gx-mono font-black text-emerald-300">+{unveiledReceipt.moraleBoost} Boost</span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setUnveiledReceipt(null)}
              className="gx-btn gx-btn-primary w-full"
            >
              Return to Transfer Hub
            </button>
          </div>
        </div>
      )}

      {/* Deep Dossier Modal */}
      {selectedPlayerId && (
        <PlayerDossier
          playerId={selectedPlayerId}
          onClose={() => setSelectedPlayerId(null)}
          onMakeOffer={(playerId) => {
            setSelectedPlayerId(null);
            const matchListing = listingsData.find(
              (item: any) => item.player_id === playerId && item.status === "open",
            );
            if (!matchListing) {
              toast.error("A formal offer requires an active transfer-market listing for this player.");
              return;
            }
            setOfferListing(matchListing);
            setOfferAmount(String(matchListing.base_price));
          }}
          onAddToWatchlist={async (id) => {
            if (!activeClub?.club_id) {
              toast.error("Select an active club before saving a scouting target.");
              return;
            }
            try {
              await api.post("/transfer-market/watchlist", {
                player_id: id,
                club_id: activeClub.club_id,
                source: "scouting_dossier",
              });
              toast.success("Player added to transfer market watchlist.");
              await qc.invalidateQueries({ queryKey: ["transfer-market-watchlist", activeClub.club_id] });
            } catch (e) {
              toast.error(errMsg(e));
            }
          }}
        />
      )}
    </div>
  );
}
export default TransferHub;
