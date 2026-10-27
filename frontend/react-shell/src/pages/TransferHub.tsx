import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeftRight, Clock, DollarSign, Filter, Handshake, MessageSquare, Plus, Search, ShieldAlert, Sparkles, UserPlus, Users } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, useActiveClub } from "@/lib/owner";
import { Btn, Chip, Loading, TraitBar } from "@/components/gtex/ui";
import { PlayerCard } from "@/components/gtex/PlayerCard";
import { RegenCard } from "@/components/gtex/RegenCard";
import { PlayerDossier } from "@/components/gtex/PlayerDossier";
import { toast } from "sonner";

export type TransferLane = "listings" | "offers" | "negotiations" | "bids" | "shortlist";

export function TransferHub() {
  const qc = useQueryClient();
  const { active: activeClub } = useActiveClub();
  const [lane, setLane] = useState<TransferLane>("listings");
  const [search, setSearch] = useState("");
  const [selectedPosition, setSelectedPosition] = useState("ALL");
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);

  // Offer modal state
  const [offerListing, setOfferListing] = useState<any | null>(null);
  const [offerAmount, setOfferAmount] = useState<string>("");
  const [offerWage, setOfferWage] = useState<string>("");
  const [submittingOffer, setSubmittingOffer] = useState(false);

  // Lane 1: Listings Query
  const { data: listingsData, isLoading: loadingListings } = useQuery({
    queryKey: ["transfer-listings", selectedPosition],
    queryFn: async () => {
      try {
        const params: any = { status: "active" };
        if (selectedPosition !== "ALL") params.position = selectedPosition;
        const { data } = await api.get("/transfer-hub/listings", { params });
        return data || [];
      } catch {
        return [];
      }
    },
  });

  // Lane 2: Offers Query (Incoming & Outgoing for active club)
  const { data: offersData, isLoading: loadingOffers, refetch: refetchOffers } = useQuery({
    queryKey: ["transfer-offers", activeClub?.club_id],
    queryFn: async () => {
      try {
        const params: any = {};
        if (activeClub?.club_id) params.club_id = activeClub.club_id;
        const { data } = await api.get("/transfer-hub/offers", { params });
        return data || [];
      } catch {
        return [];
      }
    },
    enabled: !!activeClub?.club_id && lane === "offers",
  });

  // Read watchlist entries for the verified active club; the backend returns the
  // canonical player record and an active market listing only when one exists.
  const {
    data: shortlistData,
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

  const bidListings = (listingsData || []).filter(
    (listing: any) => listing.status === "open" && Number(listing.bid_count || 0) > 0,
  );

  const negotiationListings = (listingsData || []).filter(
    (listing: any) => Boolean(listing.negotiation_id),
  );
  const {
    data: negotiationsData,
    isLoading: loadingNegotiations,
  } = useQuery({
    queryKey: [
      "transfer-market-negotiations",
      activeClub?.club_id,
      negotiationListings.map((listing: any) => listing.id).sort().join(","),
    ],
    queryFn: async () => {
      const records = await Promise.all(
        negotiationListings.map(async (listing: any) => {
          try {
            const { data } = await api.get(
              `/transfer-market/listings/${listing.id}/negotiation`,
            );
            return { ...data, listing };
          } catch {
            // The listing feed can contain negotiations for other clubs. The
            // endpoint enforces ownership; inaccessible records are not shown.
            return null;
          }
        }),
      );
      return records.filter(Boolean);
    },
    enabled: !!activeClub?.club_id && lane === "negotiations" && negotiationListings.length > 0,
  });

  const [bidAmounts, setBidAmounts] = useState<Record<string, string>>({});
  const [placingBidId, setPlacingBidId] = useState<string | null>(null);

  // Actions on Offers
  const handleAcceptOffer = async (offerId: string) => {
    try {
      await api.post(`/transfer-hub/offers/${offerId}/accept`);
      toast.success("Transfer offer accepted! Deal submitted for league registration.");
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
    if (!rawAmount || !Number.isFinite(amount) || amount <= Number(listing.current_highest_bid || 0)) {
      toast.error("Enter a valid bid greater than the current highest bid.");
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
        amount: Number(offerAmount),
        proposed_wage: offerWage ? Number(offerWage) : undefined,
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

  // Filter listings
  const filteredListings = (listingsData || []).filter((l: any) => {
    const p = l.player || {};
    const name = (p.name || p.player_name || l.player_id || "").toLowerCase();
    if (search && !name.includes(search.toLowerCase())) return false;
    return true;
  });

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

          <div className="flex flex-wrap gap-2 text-xs">
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
          </div>
        </div>
      </section>

      {/* Five Lanes Navigation Tabs */}
      <nav className="flex flex-wrap gap-2 border-b border-white/10 pb-4" data-testid="transfer-hub-lanes">
        {[
          { id: "listings", label: "Market Listings", count: listingsData?.length, icon: ArrowLeftRight },
          { id: "offers", label: "Active Offers", count: offersData?.length, icon: Handshake },
          { id: "negotiations", label: "Negotiations", count: negotiationsData?.length, icon: MessageSquare },
          { id: "bids", label: "Window Bids", count: bidListings.length, icon: Clock },
          { id: "shortlist", label: "Shortlist", count: shortlistData?.length, icon: Sparkles },
        ].map((item) => {
          const Icon = item.icon;
          const active = lane === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setLane(item.id as any)}
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
          ) : filteredListings.length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
              <ArrowLeftRight className="mx-auto size-10 text-emerald-400/50 mb-3" />
              <p className="gx-display text-xl font-bold uppercase text-white">No active transfer listings</p>
              <p className="text-sm text-slate-400 mt-1">Clubs have not placed matching players on the market.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 place-items-center">
              {filteredListings.map((listing: any, i: number) => {
                const p = listing.player || {};
                const id = listing.player_id || p.id || `listing-${i}`;
                const isRegen = listing.asset_type === "regen" || p.is_regen;
                return (
                  <div key={listing.id || id} className="flex flex-col w-full max-w-[310px]">
                    {isRegen ? (
                      <RegenCard
                        name={p.name || p.player_name || "Listed Regen"}
                        rating={p.current_rating || p.rating || 72}
                        position={p.position || "MID"}
                        price={listing.asking_price}
                        variant="full"
                        onClick={() => setSelectedPlayerId(id)}
                      />
                    ) : (
                      <PlayerCard
                        name={p.name || p.player_name || "Listed Player"}
                        rating={p.rating || 76}
                        position={p.position || "FWD"}
                        price={listing.asking_price}
                        variant="full"
                        onClick={() => setSelectedPlayerId(id)}
                      />
                    )}
                    <button
                      type="button"
                      onClick={() => {
                        setOfferListing(listing);
                        setOfferAmount(String(listing.asking_price || 50000));
                      }}
                      className="gx-btn gx-btn-primary mt-2.5 w-full text-xs font-black shadow-md"
                      data-testid={`make-offer-btn-${listing.id || id}`}
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
          ) : (offersData || []).length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
              <Handshake className="mx-auto size-10 text-emerald-400/50 mb-3" />
              <p className="gx-display text-xl font-bold uppercase text-white">No open transfer offers</p>
              <p className="text-sm text-slate-400 mt-1">
                Browse listings to make an offer, or list squad players to invite bids.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {(offersData || []).map((offer: any) => {
                const isIncoming = offer.selling_club_id === activeClub?.club_id;
                return (
                  <div
                    key={offer.id}
                    className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-xl border border-white/10 bg-slate-900/60 p-4 shadow-lg"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`rounded px-2 py-0.5 text-[9px] font-black uppercase ${
                          isIncoming ? "bg-cyan-500/20 text-cyan-300" : "bg-emerald-500/20 text-emerald-300"
                        }`}>
                          {isIncoming ? "Incoming Offer" : "Outgoing Offer"}
                        </span>
                        <span className="gx-mono text-xs text-slate-400">ID: {offer.id.slice(0, 8)}</span>
                      </div>
                      <h4 className="gx-display text-lg font-bold uppercase text-white">
                        {offer.player_name || `Target Player #${offer.player_id?.slice(0, 6)}`}
                      </h4>
                      <p className="text-xs text-slate-300">
                        Offered: <b className="text-amber-300 font-mono">{fmt(offer.amount)} GTX</b> · Proposed Wage: <b className="text-white font-mono">{fmt(offer.proposed_wage || 2000)} GTX/w</b>
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      {isIncoming && offer.status === "pending" && (
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
                      <span className="gx-mono text-xs font-bold text-slate-400 uppercase">
                        Status: <b className="text-white">{offer.status || "Pending"}</b>
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Lane 3: Persisted negotiations only */}
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
          ) : (negotiationsData || []).length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
              <MessageSquare className="mx-auto size-10 text-emerald-400/50 mb-3" />
              <p className="gx-display text-xl font-bold uppercase text-white">No accessible active negotiations</p>
              <p className="text-sm text-slate-400 mt-1">
                This view only shows negotiations returned by the authenticated API. Browse market listings or active offers to start a real transfer workflow.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {(negotiationsData || []).map((negotiation: any) => (
                <div key={negotiation.id} className="rounded-xl border border-white/10 bg-slate-900/60 p-4 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="rounded bg-amber-500/20 text-amber-300 px-2 py-0.5 text-[9px] font-black uppercase">
                      {String(negotiation.status || "unknown").replaceAll("_", " ")}
                    </span>
                    <span className="gx-mono text-xs text-slate-400">Negotiation {String(negotiation.id).slice(0, 8)}</span>
                  </div>
                  <h4 className="gx-display text-xl font-bold uppercase text-white">
                    {negotiation.listing?.player?.full_name || `Player ${negotiation.player_id}`}
                  </h4>
                  <p className="text-xs text-slate-300">
                    Listing {String(negotiation.listing_id).slice(0, 8)} · Expected role: {negotiation.expected_role || "Not recorded"}
                  </p>
                  <p className="text-xs text-slate-400">
                    {negotiation.wage_offer_amount != null
                      ? `Recorded wage offer: ${fmt(negotiation.wage_offer_amount)} GTX/w`
                      : "No wage offer is recorded for this negotiation."}
                  </p>
                  <div className="pt-2 border-t border-white/10">
                    <button
                      type="button"
                      onClick={() => setSelectedPlayerId(negotiation.player_id)}
                      className="gx-btn gx-btn-secondary text-xs"
                    >
                      View player dossier
                    </button>
                  </div>
                </div>
              ))}
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
              <p className="gx-display text-xl font-bold uppercase text-white">No active listings with bids</p>
              <p className="text-sm text-slate-400 mt-1">This lane only shows live bid state returned by the transfer-market API.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {bidListings.map((listing: any) => {
                const currentHighest = Number(listing.current_highest_bid || 0);
                const enteredAmount = bidAmounts[listing.id] || "";
                const amountIsValid = enteredAmount.trim() !== ""
                  && Number.isFinite(Number(enteredAmount))
                  && Number(enteredAmount) > currentHighest;
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
                        Current highest: {fmt(listing.current_highest_bid)} GTX
                      </p>
                    </div>
                    <div className="flex flex-col gap-2 sm:w-64">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        Your bid (GTX)
                      </label>
                      <input
                        type="number"
                        min={currentHighest + 0.01}
                        value={enteredAmount}
                        onChange={(event) => setBidAmounts((previous) => ({
                          ...previous,
                          [listing.id]: event.target.value,
                        }))}
                        placeholder={`Greater than ${String(listing.current_highest_bid)}`}
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
              {(shortlistData || []).length} saved target{(shortlistData || []).length === 1 ? "" : "s"}
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
          ) : (shortlistData || []).length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
              <Sparkles className="mx-auto size-10 text-emerald-400/50 mb-3" />
              <p className="gx-display text-xl font-bold uppercase text-white">No saved scouting targets</p>
              <p className="text-sm text-slate-400 mt-1">
                Open a real player's dossier and use Add to Watchlist. Saved targets will appear here after the backend confirms the write.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {(shortlistData || []).map((entry: any) => {
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

      {/* Deep Dossier Modal */}
      {selectedPlayerId && (
        <PlayerDossier
          playerId={selectedPlayerId}
          onClose={() => setSelectedPlayerId(null)}
          onMakeOffer={(id) => {
            setSelectedPlayerId(null);
            setOfferListing({ id, asking_price: 50000 });
            setOfferAmount("50000");
          }}
          onAddToWatchlist={async (id) => {
            try {
              await api.post("/transfer-market/watchlist", {
                player_id: id,
                club_id: activeClub?.club_id,
                source: "scouting_dossier",
              });
              toast.success("Player added to transfer market watchlist.");
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
