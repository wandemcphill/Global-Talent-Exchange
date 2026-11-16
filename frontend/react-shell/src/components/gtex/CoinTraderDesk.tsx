import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, RefreshCw, ShieldAlert, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, label } from "@/lib/owner";
import { Btn, Chip, Panel } from "@/components/gtex/ui";
import { CoinTraderMarketplaceView } from "./coin-traders/CoinTraderMarketplaceView";
import { CoinTraderMerchantDashboard } from "./coin-traders/CoinTraderMerchantDashboard";
import { CoinTraderOrderRoom } from "./coin-traders/CoinTraderOrderRoom";
import { CoinTraderTradeModal } from "./coin-traders/CoinTraderTradeModal";
import {
  isTrustedDiditHandoffUrl,
  type MarketplaceOffer,
  type MarketplaceResponse,
  type TradeOrder,
} from "./coin-traders/types";

function TraderVerificationCard({ onVerified }: { onVerified?: () => void }) {
  const [verificationType, setVerificationType] = useState<
    "full_kyc" | "government_id" | "bvn_nin" | "liveness"
  >("full_kyc");
  const [initiating, setInitiating] = useState(false);
  const [handoffUrl, setHandoffUrl] = useState<string | null>(null);
  const qc = useQueryClient();

  const statusQuery = useQuery({
    queryKey: ["coin-trader-verification-status"],
    queryFn: async () => (await api.get("/coin-traders/verification/status")).data,
    retry: false,
  });

  const handleInitiate = async () => {
    setInitiating(true);
    try {
      const { data } = await api.post("/coin-traders/verification/initiate", {
        provider: "didit",
        verification_type: verificationType,
        callback_url: `${window.location.origin}/trader/verification/callback`,
      });
      const candidateUrl = data.handoff_url || data.session_url;
      if (isTrustedDiditHandoffUrl(candidateUrl)) {
        setHandoffUrl(candidateUrl);
        window.open(candidateUrl, "_blank", "noopener,noreferrer");
        toast.success(
          "DIDit verification session started. Complete checks in the DIDit window; activation occurs after provider confirmation.",
        );
      } else {
        setHandoffUrl(null);
        toast.success("Verification session created. Waiting for DIDit session status update.");
      }
      qc.invalidateQueries({ queryKey: ["coin-trader-verification-status"] });
      qc.invalidateQueries({ queryKey: ["coin-trader-me"] });
      if (onVerified) onVerified();
    } catch (err: any) {
      toast.error("Failed to initiate DIDit verification: " + errMsg(err));
    } finally {
      setInitiating(false);
    }
  };

  const kycStatus = statusQuery.data;

  return (
    <div
      className="mb-6 rounded-xl border border-indigo-400/30 bg-indigo-500/[0.05] p-5"
      data-testid="trader-kyc-card"
    >
      <div className="flex items-start gap-3">
        <ShieldCheck className="size-6 text-indigo-400 shrink-0 mt-0.5" />
        <div className="flex-1 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="gx-display text-base font-bold uppercase text-white">
              Authoritative DIDit Trader Identity Verification
            </h3>
            {kycStatus?.status && (
              <Chip
                tone={
                  kycStatus.status === "verified"
                    ? "emerald"
                    : kycStatus.status === "rejected"
                      ? "red"
                      : "gold"
                }
              >
                {label(kycStatus.decision || kycStatus.status)}
              </Chip>
            )}
          </div>
          <p className="text-xs leading-5 text-slate-300">
            Coin Traders complete DIDit identity verification (Government ID, Nigerian BVN/NIN where
            configured in workflow, selfie comparison, and liveness) to earn the ID Verified badge
            and activate merchant operations.
          </p>
          {kycStatus && (
            <div
              className="rounded-lg border border-white/10 bg-black/25 px-3 py-2 text-xs text-slate-300"
              data-testid="trader-kyc-status-summary"
            >
              Provider: <b>{kycStatus.provider}</b> · Ref:{" "}
              <b>{kycStatus.provider_reference || "--"}</b> · Decision:{" "}
              <b>{label(kycStatus.decision || kycStatus.status)}</b>
              {kycStatus.rejection_reason ? ` · Reason: ${kycStatus.rejection_reason}` : ""}
            </div>
          )}
          <div className="pt-2 flex flex-wrap items-center gap-3">
            <select
              aria-label="DIDit verification flow"
              data-testid="trader-kyc-type-select"
              className="gx-input max-w-[280px] py-1.5 text-xs"
              value={verificationType}
              onChange={(e) => setVerificationType(e.target.value as any)}
            >
              <option value="full_kyc">Full KYC (Government ID + Face + Liveness)</option>
              <option value="government_id">Government ID & Face Match</option>
              <option value="bvn_nin">Nigeria BVN / NIN + Liveness</option>
              <option value="liveness">Live Liveness Re-check</option>
            </select>
            <Btn
              disabled={initiating}
              onClick={handleInitiate}
              data-testid="initiate-trader-kyc-btn"
            >
              {initiating ? "Connecting to DIDit..." : "Start DIDit Verification"}
            </Btn>
            <Btn
              variant="secondary"
              onClick={() => {
                qc.invalidateQueries({ queryKey: ["coin-trader-verification-status"] });
                qc.invalidateQueries({ queryKey: ["coin-trader-me"] });
              }}
              data-testid="refresh-trader-kyc-btn"
            >
              <RefreshCw size={14} /> Refresh Status
            </Btn>
            {handoffUrl && (
              <a
                href={handoffUrl}
                target="_blank"
                rel="noopener noreferrer"
                data-testid="trader-kyc-handoff-link"
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-300 underline"
              >
                Open DIDit Session <ExternalLink size={12} />
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function CoinTraderDesk() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const accountType = String(user?.account_type || user?.accountType || "user").toLowerCase();
  const isDedicatedTraderAccount = accountType === "coin_trader";

  const [section, setSection] = useState<"marketplace" | "orders" | "merchant">(
    isDedicatedTraderAccount ? "merchant" : "marketplace",
  );

  const { data: traders = [] } = useQuery<any[]>({
    queryKey: ["coin-traders"],
    queryFn: async () => (await api.get("/coin-traders")).data || [],
  });
  const { data: orders = [] } = useQuery<TradeOrder[]>({
    queryKey: ["coin-orders", "me"],
    queryFn: async () => (await api.get("/coin-traders/orders")).data || [],
  });
  const meQuery = useQuery({
    queryKey: ["coin-trader-me"],
    queryFn: async () => (await api.get("/coin-traders/me")).data,
    retry: false,
    enabled: isDedicatedTraderAccount,
  });

  const me = meQuery.data;
  const status = String(me?.status || "").toLowerCase();
  const isVerified = Boolean(me?.verified_at);
  const isSuspended = Boolean(me?.suspended_at) || status === "suspended";
  const isFrozen = status === "frozen";
  const isTrader =
    isDedicatedTraderAccount && me && status === "approved" && isVerified && !isSuspended;
  const canViewDeskOrders =
    isDedicatedTraderAccount && Boolean(me) && (isTrader || isFrozen || isSuspended);
  const missingProfile =
    !meQuery.isLoading &&
    !me &&
    [403, 404].includes(Number((meQuery.error as any)?.response?.status));
  const showApplication = isDedicatedTraderAccount && (missingProfile || status === "rejected");

  const { data: deskOrders = [] } = useQuery<TradeOrder[]>({
    queryKey: ["coin-orders", "desk"],
    queryFn: async () =>
      (await api.get("/coin-traders/orders", { params: { as_trader: true } })).data || [],
    enabled: canViewDeskOrders,
  });

  const [applyName, setApplyName] = useState(String(user?.display_name || user?.username || ""));
  const [countryCode, setCountryCode] = useState("NG");
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState("");

  const submitTraderApplication = async (event: React.FormEvent) => {
    event.preventDefault();
    setApplyError("");
    if (applyName.trim().length < 2) {
      setApplyError("Enter the public name for your trader desk.");
      return;
    }
    setApplying(true);
    try {
      await api.post("/coin-traders/apply", {
        display_name: applyName.trim(),
        ...(countryCode.trim() ? { country_code: countryCode.trim().toUpperCase() } : {}),
        terms: {
          same_name_account_only: true,
          payment_proof_required: true,
          kyc_required: false,
        },
        payment_methods: [{ label: "Bank Transfer", type: "bank_transfer" }],
        bank_accounts: [],
        metadata_json: {},
      });
      await qc.invalidateQueries({ queryKey: ["coin-trader-me"] });
      await qc.invalidateQueries({ queryKey: ["coin-traders"] });
      toast.success(
        "Coin Trader application submitted. Complete identity verification to activate your desk.",
      );
    } catch (error: any) {
      setApplyError(errMsg(error));
    } finally {
      setApplying(false);
    }
  };

  const activeOrderCount = orders.filter((o) =>
    ["created", "payment_pending", "proof_submitted", "disputed"].includes(o.status),
  ).length;

  return (
    <Panel
      eyebrow="GTEX Coin & Fan Coin · P2P Marketplace"
      title="Coin Traders"
      testid="coin-traders-panel"
      className="lg:col-span-12"
    >
      <p className="mb-4 text-sm text-slate-400">
        Buy or sell GTEX Coin (GTC, min buyer order ₦200,000) and Fan Coin (FNC, min buyer order
        ₦50,000) directly with verified Naira merchants through canonical GTEX escrow protection and
        zero P2P platform fees.
      </p>

      {/* Top Section Tabs */}
      <div className="mb-5 flex flex-wrap gap-2 border-b border-white/10 pb-3">
        <button
          type="button"
          data-testid="tab-p2p-marketplace"
          onClick={() => setSection("marketplace")}
          className={`gx-btn py-1.5 px-4 text-xs ${
            section === "marketplace" ? "gx-btn-primary" : "gx-btn-secondary"
          }`}
        >
          P2P Marketplace
        </button>
        <button
          type="button"
          data-testid="tab-my-orders"
          onClick={() => setSection("orders")}
          className={`gx-btn py-1.5 px-4 text-xs ${section === "orders" ? "gx-btn-primary" : "gx-btn-secondary"}`}
        >
          My Orders ({orders.length}
          {activeOrderCount > 0 ? ` · ${activeOrderCount} active` : ""})
        </button>
        {isDedicatedTraderAccount && (
          <button
            type="button"
            data-testid="tab-merchant-desk"
            onClick={() => setSection("merchant")}
            className={`gx-btn py-1.5 px-4 text-xs ${
              section === "merchant" ? "gx-btn-primary" : "gx-btn-secondary"
            }`}
          >
            Merchant Dashboard
          </button>
        )}
      </div>

      {/* Onboarding & Verification notices for Coin Trader accounts */}
      {isDedicatedTraderAccount && (section === "merchant" || !isTrader) && (
        <>
          {showApplication && (
            <div
              className="mb-6 rounded-xl border border-amber-400/25 bg-amber-500/[0.05] p-4"
              data-testid="coin-trader-application"
            >
              <p className="gx-label text-amber-300">
                {status === "rejected" ? "Resubmit desk application" : "Set up trader desk"}
              </p>
              <h3 className="gx-display mt-1 text-xl font-bold uppercase text-white">
                Set up your trader desk
              </h3>
              <p className="mt-2 max-w-3xl text-sm leading-5 text-slate-400">
                Your dedicated Coin Trader account needs a registered desk profile followed by
                identity verification before publishing adverts or accepting client orders.
              </p>
              <form onSubmit={submitTraderApplication} className="mt-4 grid gap-3 md:grid-cols-3">
                <label className="block">
                  <span className="gx-label">Trader desk name</span>
                  <input
                    required
                    minLength={2}
                    maxLength={120}
                    className="gx-input mt-2"
                    value={applyName}
                    onChange={(e) => setApplyName(e.target.value)}
                    placeholder="Lagos Liquidity Desk"
                  />
                </label>
                <label className="block">
                  <span className="gx-label">Country code (optional)</span>
                  <input
                    maxLength={8}
                    className="gx-input mt-2"
                    value={countryCode}
                    onChange={(e) => setCountryCode(e.target.value)}
                    placeholder="NG"
                  />
                </label>
                <div className="flex items-end">
                  <Btn type="submit" disabled={applying} className="w-full">
                    {applying ? "Submitting..." : "Submit trader application"}
                  </Btn>
                </div>
                {applyError && (
                  <p role="alert" className="md:col-span-3 text-sm text-red-300">
                    {applyError}
                  </p>
                )}
              </form>
            </div>
          )}

          {meQuery.isLoading && (
            <p className="mb-4 text-sm text-slate-500">Checking your trader application...</p>
          )}
          {meQuery.isError && !missingProfile && (
            <div
              className="mb-4 rounded border border-red-500/20 bg-red-950/20 p-3 text-sm text-red-200"
              data-testid="coin-trader-profile-error"
            >
              Trader application status could not be loaded: {errMsg(meQuery.error)}
            </div>
          )}

          {isSuspended && (
            <div
              className="mb-6 rounded-xl border border-red-500/30 bg-red-950/30 p-4 text-sm text-red-200"
              data-testid="trader-suspended-notice"
            >
              <div className="flex items-center gap-2 font-semibold">
                <ShieldAlert size={18} />
                <span>Trader Desk Suspended</span>
              </div>
              <p className="mt-1 text-xs text-red-300">
                This trader desk has been suspended by GTEX Compliance. New adverts and orders are
                disabled; existing escrow orders can still be completed or resolved safely below.
              </p>
            </div>
          )}

          {me && !me.is_didit_verified && me.verification_provider !== "didit" && !isSuspended && (
            <TraderVerificationCard
              onVerified={() => qc.invalidateQueries({ queryKey: ["coin-trader-me"] })}
            />
          )}

          {me && status !== "approved" && !isSuspended && !isFrozen && (
            <div
              className="mb-6 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] p-4"
              data-testid="coin-trader-application-status"
            >
              <p className="gx-label">Your trader application</p>
              <p className="mt-1 text-sm font-bold text-white">
                {me.display_name} · {label(status)}
              </p>
              <p className="mt-2 text-sm text-slate-400">
                {status === "applied" || status === "pending"
                  ? "Complete DIDit verification above or wait for admin desk approval to start publishing adverts."
                  : "Trader operations are not enabled for this application status."}
              </p>
            </div>
          )}
        </>
      )}

      {/* Marketplace Section */}
      {section === "marketplace" && (
        <CoinTraderMarketplaceView
          isDedicatedTraderAccount={isDedicatedTraderAccount}
          onOrderCreated={() => setSection("orders")}
        />
      )}

      {/* Customer Orders Section */}
      {section === "orders" && (
        <div className="space-y-3" data-testid="my-coin-orders">
          {orders.length === 0 ? (
            <p className="text-sm text-slate-500">
              No coin trades yet. Browse the P2P Marketplace to get started.
            </p>
          ) : (
            orders.map((o) => <CoinTraderOrderRoom key={o.id} order={o} traders={traders} />)
          )}
        </div>
      )}

      {/* Merchant Dashboard Section */}
      {section === "merchant" && canViewDeskOrders && me && (
        <CoinTraderMerchantDashboard profile={me} deskOrders={deskOrders} />
      )}
    </Panel>
  );
}

export function ClubCoinTraderFundingPanel({ initialAmount = "4000" }: { initialAmount?: string }) {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [selectedOffer, setSelectedOffer] = useState<MarketplaceOffer | null>(null);

  const { data: traders = [] } = useQuery<any[]>({
    queryKey: ["coin-traders"],
    queryFn: async () => (await api.get("/coin-traders")).data || [],
  });
  const { data: market, isLoading: marketLoading } = useQuery<MarketplaceResponse | null>({
    queryKey: ["coin-trader-marketplace", "club-funding-gtex"],
    queryFn: async () => {
      try {
        const res = await api.get("/coin-traders/marketplace", {
          params: {
            coin_unit: "coin",
            side: "sell",
            fiat_currency: "NGN",
            sort_by: "price_asc",
          },
        });
        return res?.data ?? null;
      } catch {
        return null;
      }
    },
  });
  const { data: orders = [], isLoading: ordersLoading } = useQuery<TradeOrder[]>({
    queryKey: ["coin-orders", "me"],
    queryFn: async () => (await api.get("/coin-traders/orders")).data || [],
  });

  const ownProfileIds = new Set(
    traders.filter((t) => user?.id && t.user_id === user.id).map((t) => String(t.id)),
  );
  const offers = (market?.offers || []).filter(
    (offer) =>
      offer.coin_unit === "coin" &&
      offer.side === "sell" &&
      !ownProfileIds.has(String(offer.trader_profile_id)),
  );
  const gtexOrders = orders.filter(
    (order) => String(order.coin_unit || "coin").toLowerCase() === "coin",
  );
  const requestedCoins = Math.max(0, Math.ceil(Number(initialAmount) || 0));

  return (
    <div
      className="rounded-xl border border-cyan-500/20 bg-slate-950/60 p-4"
      data-testid="club-funding-coin-traders"
    >
      <p className="gx-label text-cyan-300">Option 2 · Verified Coin Traders</p>
      <h4 className="gx-display mt-1 text-lg font-bold uppercase text-white">
        Buy GTX from a Coin Trader
      </h4>
      <p className="mt-2 text-xs leading-relaxed text-slate-400">
        Choose an approved, identity-verified merchant advert. Orders are escrow-protected through the
        GTEX order room with zero P2P platform fees. GTEX Coin buyer orders have a ₦200,000 minimum;
        any surplus stays in your wallet for later use.
      </p>

      {marketLoading ? (
        <p className="mt-3 text-xs text-slate-500">Loading verified GTEX Coin trader offers…</p>
      ) : offers.length ? (
        <div className="mt-4 space-y-2.5" data-testid="club-funding-offers-list">
          {offers.map((offer) => {
            const unitRate = Number(offer.price_fiat || 0);
            const minFiat = Math.max(200000, Number(offer.min_fiat_amount || 0));
            const minOrderCoins = unitRate > 0 ? Math.ceil(minFiat / unitRate) : 1;
            const suggestedCoins = Math.max(1, requestedCoins, minOrderCoins);
            return (
              <div
                key={offer.advert_id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/10 bg-black/30 p-3 text-xs"
              >
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-white">{offer.trader_display_name}</span>
                    {offer.verification_badge_label && (
                      <Chip tone={offer.is_didit_verified ? "emerald" : "gold"}>
                        {offer.verification_badge_label}
                      </Chip>
                    )}
                  </div>
                  <p className="text-slate-400">
                    Rate: <b className="text-white">₦{fmt(unitRate, 2)}</b> / GTC · Available:{" "}
                    <b className="text-slate-200">{fmt(offer.available_coin)} GTC</b> · Suggested gap
                    order: <b className="text-cyan-300">{fmt(suggestedCoins)} GTC</b>
                  </p>
                </div>
                <Btn
                  variant="primary"
                  onClick={() => setSelectedOffer(offer)}
                  data-testid={`club-funding-select-${offer.advert_id}`}
                >
                  Buy GTC
                </Btn>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="mt-3 rounded border border-amber-400/20 bg-amber-400/5 p-3 text-xs text-amber-200">
          No approved and verified GTEX Coin trader offers are currently available. Use the platform
          purchase option or check back later.
        </p>
      )}

      <div className="mt-5 border-t border-white/10 pt-4">
        <p className="gx-label">Your GTEX Coin trader orders</p>
        {ordersLoading ? (
          <p className="mt-2 text-xs text-slate-500">Loading orders…</p>
        ) : gtexOrders.length ? (
          <div className="mt-2 space-y-2">
            {gtexOrders.map((order) => (
              <CoinTraderOrderRoom key={order.id} order={order} traders={traders} />
            ))}
          </div>
        ) : (
          <p className="mt-2 text-xs text-slate-500">No GTEX Coin trader orders yet.</p>
        )}
      </div>

      {selectedOffer && (
        <CoinTraderTradeModal
          offer={selectedOffer}
          onClose={() => setSelectedOffer(null)}
          onOrderCreated={() => {
            qc.invalidateQueries({ queryKey: ["coin-orders"] });
            qc.invalidateQueries({ queryKey: ["coin-trader-marketplace"] });
          }}
        />
      )}
    </div>
  );
}
