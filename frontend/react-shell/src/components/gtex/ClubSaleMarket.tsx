import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Building2, DollarSign, ShieldAlert, Sparkles, TrendingUp, Users } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { fmt } from "@/lib/owner";
import { Btn, Chip, Empty, Loading, Panel } from "@/components/gtex/ui";

interface ClubListing {
  id: string;
  club_id: string;
  club_name: string;
  league_tier?: number;
  asking_price: number;
  valuation?: number;
  squad_strength?: number;
  fanbase_size?: number;
  status: string;
  created_at?: string;
}

export function ClubSaleMarket() {
  const [tier, setTier] = useState<string>("");
  const [inquireModal, setInquireModal] = useState<ClubListing | null>(null);
  const [offerAmount, setOfferAmount] = useState<string>("");
  const [inquiryMessage, setInquiryMessage] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["club-sale-market-listings", tier],
    queryFn: async () => {
      try {
        const params: any = { limit: 50 };
        if (tier) params.league_tier = Number(tier);
        const res = await api.get("/api/clubs/sale-market/listings", { params });
        return res.data?.items || res.data?.listings || [];
      } catch (e) {
        // Fallback to legacy or empty
        try {
          const res = await api.get("/clubs/marketplace");
          return res.data?.items || res.data?.listings || [];
        } catch {
          return [];
        }
      }
    },
    staleTime: 60_000,
  });

  const listings: ClubListing[] = (data as any) || [];

  const handleInquire = async () => {
    if (!inquireModal) return;
    setSubmitting(true);
    try {
      await api.post(`/api/clubs/${inquireModal.club_id}/inquiries`, {
        message: inquiryMessage || "Interested in acquisition discussions.",
        offer_amount: offerAmount ? Number(offerAmount) : undefined,
      });
      toast.success(`Acquisition inquiry submitted for ${inquireModal.club_name}!`);
      setInquireModal(null);
      setOfferAmount("");
      setInquiryMessage("");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div data-testid="club-sale-market-container" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Building2 className="text-emerald-400" size={18} />
          <span className="text-sm font-semibold text-white">Live Club Acquisition Desk</span>
        </div>
        <div className="flex items-center gap-2">
          <select
            data-testid="club-sale-tier-filter"
            className="gx-input text-xs"
            value={tier}
            onChange={(e) => setTier(e.target.value)}
          >
            <option value="">All League Tiers</option>
            <option value="1">Tier 1 Elite</option>
            <option value="2">Tier 2 Challenger</option>
            <option value="3">Tier 3 Regional</option>
          </select>
          <Btn variant="secondary" onClick={() => refetch()} data-testid="club-sale-refresh-btn">
            Refresh
          </Btn>
        </div>
      </div>

      {isLoading ? (
        <Loading />
      ) : listings.length === 0 ? (
        <Empty
          title="No Clubs Currently Listed for Sale"
          body="All registered GTEX clubs are currently held by their active owners. To list your club for sale, visit the Boardroom in your Control Center."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="club-sale-listings-grid">
          {listings.map((item) => (
            <div
              key={item.id}
              data-testid={`club-sale-card-${item.club_id}`}
              className="rounded-sm border border-white/10 bg-black/40 p-4 space-y-3 hover:border-emerald-500/40 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="font-bold text-white text-base">{item.club_name}</h4>
                  <p className="text-xs text-slate-400">Tier {item.league_tier ?? 1} Club</p>
                </div>
                <Chip tone="emerald">Active Listing</Chip>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs border-y border-white/5 py-2">
                <div>
                  <span className="text-slate-400 block">Asking Price</span>
                  <span className="font-bold text-emerald-300">{fmt(item.asking_price)} GTX</span>
                </div>
                <div>
                  <span className="text-slate-400 block">Est. Valuation</span>
                  <span className="font-bold text-white">{fmt(item.valuation ?? item.asking_price)} GTX</span>
                </div>
                {item.squad_strength && (
                  <div>
                    <span className="text-slate-400 block">Squad Strength</span>
                    <span className="text-slate-200">{item.squad_strength} OVR</span>
                  </div>
                )}
                {item.fanbase_size && (
                  <div>
                    <span className="text-slate-400 block">Fanbase Reach</span>
                    <span className="text-slate-200">{fmt(item.fanbase_size)} fans</span>
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                <Btn
                  variant="primary"
                  className="w-full text-xs"
                  onClick={() => setInquireModal(item)}
                  data-testid={`inquire-btn-${item.club_id}`}
                >
                  Acquisition Offer
                </Btn>
              </div>
            </div>
          ))}
        </div>
      )}

      {inquireModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-sm border border-white/15 bg-slate-900 p-6 space-y-4">
            <h3 className="text-lg font-bold text-white">Acquisition Offer for {inquireModal.club_name}</h3>
            <p className="text-xs text-slate-400">
              Asking Price: <span className="text-emerald-400 font-bold">{fmt(inquireModal.asking_price)} GTX</span>.
              Escrow will verify funding upon acceptance.
            </p>
            <div className="space-y-2">
              <label className="text-xs text-slate-300 block">Offer Amount (GTX)</label>
              <input
                data-testid="offer-amount-input"
                className="gx-input w-full"
                placeholder={String(inquireModal.asking_price)}
                value={offerAmount}
                onChange={(e) => setOfferAmount(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs text-slate-300 block">Note to Club Owner</label>
              <textarea
                data-testid="inquiry-message-input"
                className="gx-input w-full h-20 text-xs"
                placeholder="Detail your plans for the club, sporting goals, or strategic alliance..."
                value={inquiryMessage}
                onChange={(e) => setInquiryMessage(e.target.value)}
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Btn variant="secondary" onClick={() => setInquireModal(null)}>
                Cancel
              </Btn>
              <Btn variant="primary" disabled={submitting} onClick={handleInquire} data-testid="submit-inquiry-btn">
                {submitting ? "Submitting..." : "Submit Formal Offer"}
              </Btn>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
