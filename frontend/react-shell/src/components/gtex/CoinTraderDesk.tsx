import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, ShieldAlert, AlertTriangle, ExternalLink, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, label, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Empty, Panel } from "@/components/gtex/ui";

const ACTIVE = ["payment_pending", "escrow_locked", "accepted"];
const DONE_TONE: any = { released: "emerald", admin_released: "emerald", cancelled: "slate", refunded: "slate", admin_refunded: "slate", disputed: "red" };
const DIDIT_HANDOFF_HOSTS = new Set(["verify.didit.me", "verification.didit.me"]);

type CoinUnit = "coin" | "credit";

function coinUnitMeta(rawUnit: any): { unit: CoinUnit; code: string; name: string; minBuyerNgn: number } {
  const normalized = String(rawUnit || "coin").toLowerCase();
  if (normalized === "credit") {
    return { unit: "credit", code: "FNC", name: "Fan Coin", minBuyerNgn: 50000 };
  }
  return { unit: "coin", code: "GTC", name: "GTEX Coin", minBuyerNgn: 200000 };
}

function isTrustedDiditHandoffUrl(rawUrl: unknown): rawUrl is string {
  if (typeof rawUrl !== "string" || !rawUrl.trim()) return false;
  try {
    const parsed = new URL(rawUrl);
    return parsed.protocol === "https:" && DIDIT_HANDOFF_HOSTS.has(parsed.hostname.toLowerCase());
  } catch {
    return false;
  }
}

function rateOf(t: any, coinUnit: CoinUnit = "coin") {
  return (
    (t.rates || []).find(
      (r: any) => String(r.coin_unit || "coin").toLowerCase() === coinUnit && r.is_active !== false
    ) || null
  );
}

function useOrderActions() {
  const qc = useQueryClient();
  const refresh = useRefreshOwner();
  return async (path: string, body: any, ok: string) => {
    try {
      await api.post(path, body);
      toast.success(ok);
      qc.invalidateQueries({ queryKey: ["coin-orders"] });
      qc.invalidateQueries({ queryKey: ["club-squad-funding-finance"] });
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
}

function OrderRow({ o, asTrader, traders }: any) {
  const act = useOrderActions();
  const [proof, setProof] = useState("");
  const buys = o.direction === "user_buys";
  const iSendFiat = asTrader ? !buys : buys;
  const iReceiveFiat = !iSendFiat;
  const trader = traders.find((t: any) => t.id === o.trader_profile_id);
  const unitInfo = coinUnitMeta(o.coin_unit);
  const base = `/coin-traders/orders/${o.id}`;
  return (
    <div data-testid={`coin-order-${o.id}`} className="rounded-xl border border-gtex-graphite bg-gtex-midnight/70 p-4 text-sm shadow-md">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-white">
          {buys ? (asTrader ? "Client buys" : "Buy") : asTrader ? "Client sells" : "Sell"} <b>{fmt(o.coin_amount)} {unitInfo.code}</b> ({unitInfo.name}) for ₦{fmt(o.fiat_total)}
          <span className="ml-2 text-xs text-slate-500">{asTrader ? "" : `via ${trader?.display_name || "trader"}`} · ₦{fmt(o.quoted_rate_fiat)}/{unitInfo.code}</span>
        </p>
        <Chip tone={DONE_TONE[o.status] || "gold"}>{label(o.status)}</Chip>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {asTrader && o.status === "created" && <Btn onClick={() => act(`${base}/accept`, {}, "Order accepted, escrow locked")} data-testid={`accept-order-${o.id}`}>Accept & lock escrow</Btn>}
        {iSendFiat && ACTIVE.includes(o.status) && (
          <>
            <input data-testid={`proof-input-${o.id}`} className="gx-input max-w-[220px] py-1.5" placeholder="Bank transfer reference" value={proof} onChange={(e) => setProof(e.target.value)} />
            <Btn variant="secondary" disabled={proof.length < 3} onClick={() => act(`${base}/proof`, { proof_reference: proof }, "Payment proof submitted")} data-testid={`submit-proof-${o.id}`}>I've sent the Naira</Btn>
          </>
        )}
        {iReceiveFiat && o.status === "proof_submitted" && <Btn onClick={() => act(`${base}/confirm`, {}, "Naira received confirmed, coins released")} data-testid={`confirm-order-${o.id}`}>Confirm Naira received & release</Btn>}
        {!asTrader && o.status === "created" && <Btn variant="ghost" onClick={() => act(`${base}/cancel`, {}, "Order cancelled")} data-testid={`cancel-order-${o.id}`}>Cancel</Btn>}
        {[...ACTIVE, "proof_submitted"].includes(o.status) && <Btn variant="danger" onClick={() => act(`${base}/dispute`, { reason: "Payment not received or not as agreed" }, "Dispute opened for admin review")} data-testid={`dispute-order-${o.id}`}>Dispute</Btn>}
      </div>
      {iSendFiat && ACTIVE.includes(o.status) && (o.terms_snapshot?.payment_instructions || trader?.bank_accounts?.length > 0) && (
        <p className="mt-2 text-xs text-slate-400">Pay to: {o.terms_snapshot?.payment_instructions || trader.bank_accounts.map((b: any) => `${b.bank_name || b.bank || ""} ${b.account_number || ""} ${b.account_name || ""}`).join(" · ")}</p>
      )}
    </div>
  );
}

function OrderForm({ traders, coinOnly = false, buyOnly = false, initialAmount = "4000" }: any) {
  const act = useOrderActions();
  const [coinUnit, setCoinUnit] = useState<CoinUnit>("coin");
  const [traderId, setTraderId] = useState(traders?.[0]?.id || "");
  const [direction, setDirection] = useState("user_buys");
  const [amount, setAmount] = useState(initialAmount);
  const unitInfo = coinUnitMeta(coinUnit);
  const trader = traders.find((t: any) => t.id === traderId);
  const rate = trader ? rateOf(trader, coinUnit) : null;
  const unitPrice = rate ? Number(direction === "user_buys" ? rate.sell_rate_fiat : rate.buy_rate_fiat) : 0;
  const fiatTotal = unitPrice * Number(amount || 0);
  const minBuyerNgn = unitInfo.minBuyerNgn;
  const isBelowMinBuyerOrder = direction === "user_buys" && fiatTotal < minBuyerNgn;

  const submit = () => {
    if (isBelowMinBuyerOrder) {
      toast.error(`Minimum buyer order value for ${unitInfo.name} purchases is ₦${fmt(minBuyerNgn)}.`);
      return;
    }
    act(
      "/coin-traders/orders",
      {
        trader_profile_id: traderId,
        direction,
        coin_unit: coinUnit,
        coin_amount: Number(amount),
        fiat_currency: "NGN",
        idempotency_key: `web-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      },
      "Order created. Waiting for the trader to accept."
    );
  };

  return (
    <div className="space-y-3" data-testid="coin-order-form">
      {!coinOnly && <div className="flex flex-wrap items-center gap-2">
        <span className="gx-label mr-1">Asset lane</span>
        {(["coin", "credit"] as const).map((unitOption) => {
          const meta = coinUnitMeta(unitOption);
          return (
            <button
              key={unitOption}
              type="button"
              data-testid={`coin-unit-${unitOption}`}
              onClick={() => {
                setCoinUnit(unitOption);
                setTraderId("");
                if (unitOption === "credit" && amount === "4000") {
                  setAmount("20000");
                } else if (unitOption === "coin" && amount === "20000") {
                  setAmount("4000");
                }
              }}
              className={`gx-btn py-1.5 px-3 text-xs ${coinUnit === unitOption ? "gx-btn-primary" : "gx-btn-secondary"}`}
            >
              {meta.name} ({meta.code} · Buy min ₦{fmt(meta.minBuyerNgn)})
            </button>
          );
        })}
      </div>}

      <div className="grid gap-3 md:grid-cols-5">
        <select data-testid="coin-trader-select" className="gx-input md:col-span-2" value={traderId} onChange={(e) => setTraderId(e.target.value)}>
          <option value="">Choose a verified {unitInfo.code} trader</option>
          {traders.map((t: any) => {
            const r = rateOf(t, coinUnit);
            return (
              <option key={t.id} value={t.id} disabled={!r}>
                {t.display_name} · {t.tier}{r ? ` · buy ₦${fmt(r.sell_rate_fiat)} / sell ₦${fmt(r.buy_rate_fiat)}` : ` · no ${unitInfo.code} rate`}
              </option>
            );
          })}
        </select>
        {!buyOnly && <div className="flex gap-1">
          {[["user_buys", "Buy"], ["user_sells", "Sell"]].map(([v, l]) => <button key={v} type="button" data-testid={`coin-direction-${v}`} onClick={() => setDirection(v)} className={`gx-btn flex-1 ${direction === v ? "gx-btn-primary" : "gx-btn-secondary"}`}>{l}</button>)}
        </div>}
        <input data-testid="coin-amount-input" className="gx-input" type="number" min={1} value={amount} onChange={(e) => setAmount(e.target.value)} />
        <Btn disabled={!rate || Number(amount) <= 0 || isBelowMinBuyerOrder} onClick={submit} data-testid="coin-order-submit">
          {direction === "user_buys" ? "Buy" : "Sell"} {unitInfo.code}
        </Btn>

        {isBelowMinBuyerOrder && rate && (
          <p className="text-xs text-amber-400 md:col-span-5 flex items-center gap-1.5" data-testid="min-buyer-order-warning">
            <AlertTriangle size={14} />
            ₦{fmt(minBuyerNgn)} minimum buyer order required for {unitInfo.name} ({unitInfo.code}). Current total: ₦{fmt(fiatTotal, 2)} (Set coin amount to at least {Math.ceil(minBuyerNgn / (unitPrice || 1))} {unitInfo.code}).
          </p>
        )}

        {rate && !isBelowMinBuyerOrder && (
          <p className="text-xs text-slate-400 md:col-span-5" data-testid="coin-order-preview">
            {direction === "user_buys" ? "You pay" : "You receive"} <b className="text-white">₦{fmt(unitPrice * Number(amount || 0), 2)}</b> at ₦{fmt(unitPrice, 2)} per {unitInfo.name} ({unitInfo.code}) · limits {fmt(rate.min_coin_amount)}–{fmt(rate.max_coin_amount) || "∞"} {unitInfo.code}.{" "}
            {direction === "user_sells" ? "Your coins are locked in escrow until you confirm the Naira arrived." : "The trader's coins are locked in escrow until they confirm your payment."}
          </p>
        )}
      </div>
    </div>
  );
}

export function ClubCoinTraderFundingPanel({ initialAmount = "4000" }: any) {
  const { user } = useAuth();
  const { data: traders, isLoading: tradersLoading } = useQuery({
    queryKey: ["coin-traders"],
    queryFn: async () => (await api.get("/coin-traders")).data,
  });
  const { data: orders, isLoading: ordersLoading } = useQuery({
    queryKey: ["coin-orders", "me"],
    queryFn: async () => (await api.get("/coin-traders/orders")).data,
  });
  const approved = (traders || []).filter(
    (trader: any) =>
      trader.user_id !== user?.id &&
      Boolean(trader.verified_at) &&
      Boolean(rateOf(trader, "coin"))
  );
  const gtexOrders = (orders || []).filter(
    (order: any) => String(order.coin_unit || "coin").toLowerCase() === "coin"
  );
  const firstTraderRate = Number((approved[0] ? rateOf(approved[0], "coin") : null)?.sell_rate_fiat || 0);
  const minimumCoinAmount = firstTraderRate > 0 ? Math.ceil(200000 / firstTraderRate) : 1;
  const suggestedCoinAmount = Math.max(1, Math.ceil(Number(initialAmount) || 0), minimumCoinAmount);

  return (
    <div className="rounded-xl border border-cyan-500/20 bg-slate-950/60 p-4" data-testid="club-funding-coin-traders">
      <p className="gx-label text-cyan-300">Option 2 · Verified Coin Traders</p>
      <h4 className="gx-display mt-1 text-lg font-bold uppercase text-white">Buy GTX from a Coin Trader</h4>
      <p className="mt-2 text-xs leading-relaxed text-slate-400">
        Choose an approved, identity-verified trader. Orders are escrow-protected: the trader accepts, you submit Naira payment proof, and GTX is released to your wallet after confirmation. GTEX Coin buyer orders have a ₦200,000 minimum; any surplus stays in your wallet for later use.
      </p>
      {tradersLoading ? (
        <p className="mt-3 text-xs text-slate-500">Loading verified GTEX Coin traders…</p>
      ) : approved.length ? (
        <div className="mt-4">
          <OrderForm traders={approved} coinOnly buyOnly initialAmount={String(suggestedCoinAmount)} />
        </div>
      ) : (
        <p className="mt-3 rounded border border-amber-400/20 bg-amber-400/5 p-3 text-xs text-amber-200">
          No approved and verified GTEX Coin traders are currently available. Use the platform purchase option or check back later.
        </p>
      )}
      <div className="mt-5 border-t border-white/10 pt-4">
        <p className="gx-label">Your GTEX Coin trader orders</p>
        {ordersLoading ? (
          <p className="mt-2 text-xs text-slate-500">Loading orders…</p>
        ) : gtexOrders.length ? (
          <div className="mt-2 space-y-2">
            {gtexOrders.map((order: any) => <OrderRow key={order.id} o={order} traders={traders || []} />)}
          </div>
        ) : (
          <p className="mt-2 text-xs text-slate-500">No GTEX Coin trader orders yet.</p>
        )}
      </div>
    </div>
  );
}

function TraderVerificationCard({ profile, onVerified }: { profile: any; onVerified?: () => void }) {
  const [verificationType, setVerificationType] = useState<"full_kyc" | "government_id" | "bvn_nin" | "liveness">("full_kyc");
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
        toast.success("DIDit verification session started. Complete checks in the DIDit window; activation occurs after provider confirmation.");
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
    <div className="mb-6 rounded-xl border border-indigo-400/30 bg-indigo-500/[0.05] p-5" data-testid="trader-kyc-card">
      <div className="flex items-start gap-3">
        <ShieldCheck className="size-6 text-indigo-400 shrink-0 mt-0.5" />
        <div className="flex-1 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="gx-display text-base font-bold uppercase text-white">Authoritative DIDit Trader Identity Verification</h3>
            {kycStatus?.status && (
              <Chip tone={kycStatus.status === "verified" ? "emerald" : kycStatus.status === "rejected" ? "red" : "gold"}>
                {label(kycStatus.decision || kycStatus.status)}
              </Chip>
            )}
          </div>
          <p className="text-xs leading-5 text-slate-300">
            Coin Traders must complete DIDit identity verification (Government ID, Nigerian BVN/NIN where configured in workflow, selfie comparison, and liveness) before publishing rates, accepting orders, or acquiring inventory.
          </p>
          {kycStatus && (
            <div className="rounded-lg border border-white/10 bg-black/25 px-3 py-2 text-xs text-slate-300" data-testid="trader-kyc-status-summary">
              Provider: <b>{kycStatus.provider}</b> · Ref: <b>{kycStatus.provider_reference || "--"}</b> · Decision: <b>{label(kycStatus.decision || kycStatus.status)}</b>
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
            <Btn disabled={initiating} onClick={handleInitiate} data-testid="initiate-trader-kyc-btn">
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
  const { data: traders } = useQuery({ queryKey: ["coin-traders"], queryFn: async () => (await api.get("/coin-traders")).data });
  const { data: orders } = useQuery({ queryKey: ["coin-orders", "me"], queryFn: async () => (await api.get("/coin-traders/orders")).data });
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
  const isTrader = isDedicatedTraderAccount && me && status === "approved" && isVerified && !isSuspended;
  const missingProfile = !meQuery.isLoading && !me && [403, 404].includes(Number((meQuery.error as any)?.response?.status));
  const showApplication = isDedicatedTraderAccount && (missingProfile || status === "rejected");
  const { data: deskOrders } = useQuery({ queryKey: ["coin-orders", "desk"], queryFn: async () => (await api.get("/coin-traders/orders", { params: { as_trader: true } })).data, enabled: !!isTrader });
  const list = (traders || []).filter((t: any) => t.user_id !== user?.id && Boolean(t.verified_at));

  const [applyName, setApplyName] = useState(String(user?.display_name || user?.username || ""));
  const [countryCode, setCountryCode] = useState("");
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
        payment_methods: [],
        bank_accounts: [],
        metadata_json: {},
      });
      await qc.invalidateQueries({ queryKey: ["coin-trader-me"] });
      await qc.invalidateQueries({ queryKey: ["coin-traders"] });
      toast.success("Coin Trader application submitted. Complete identity verification to activate your desk.");
    } catch (error: any) {
      setApplyError(errMsg(error));
    } finally {
      setApplying(false);
    }
  };

  return (
    <Panel eyebrow="GTEX Coin · P2P marketplace" title="Coin Traders" testid="coin-traders-panel" className="lg:col-span-12">
      <p className="mb-4 text-sm text-slate-400">
        Ordinary User and Creator accounts can buy or sell GTEX Coin (GTC, min buyer order ₦200,000) and Fan Coin (FNC, min buyer order ₦50,000) with verified Naira traders through escrow-protected orders with no universal KYC gate. Operating a trader desk is an exclusive lane requiring DIDit identity verification.
      </p>
      {!isDedicatedTraderAccount && (
        <div className="mb-5 rounded-lg border border-white/10 bg-white/[0.02] p-3 text-sm text-slate-400" data-testid="dedicated-trader-signup-notice">
          This is a customer account lane, not a trader-desk application. Sign out and create a separate Coin Trader account to operate a trader desk.
        </div>
      )}

      {showApplication && (
        <div className="mb-6 rounded-xl border border-amber-400/25 bg-amber-500/[0.05] p-4" data-testid="coin-trader-application">
          <p className="gx-label text-amber-300">{status === "rejected" ? "Resubmit desk application" : "Set up trader desk"}</p>
          <h3 className="gx-display mt-1 text-xl font-bold uppercase text-white">Set up your trader desk</h3>
          <p className="mt-2 max-w-3xl text-sm leading-5 text-slate-400">
            Your dedicated Coin Trader account needs a registered desk profile followed by identity verification before it can quote rates or accept client orders.
          </p>
          <form onSubmit={submitTraderApplication} className="mt-4 grid gap-3 md:grid-cols-3">
            <label className="block">
              <span className="gx-label">Trader desk name</span>
              <input required minLength={2} maxLength={120} className="gx-input mt-2" value={applyName} onChange={(e) => setApplyName(e.target.value)} placeholder="Lagos Liquidity Desk" />
            </label>
            <label className="block">
              <span className="gx-label">Country code (optional)</span>
              <input maxLength={8} className="gx-input mt-2" value={countryCode} onChange={(e) => setCountryCode(e.target.value)} placeholder="NG" />
            </label>
            <div className="flex items-end">
              <Btn type="submit" disabled={applying} className="w-full">{applying ? "Submitting..." : "Submit trader application"}</Btn>
            </div>
            {applyError && <p role="alert" className="md:col-span-3 text-sm text-red-300">{applyError}</p>}
          </form>
        </div>
      )}

      {meQuery.isLoading && <p className="mb-4 text-sm text-slate-500">Checking your trader application...</p>}
      {meQuery.isError && !missingProfile && (
        <div className="mb-4 rounded border border-red-500/20 bg-red-950/20 p-3 text-sm text-red-200" data-testid="coin-trader-profile-error">
          Trader application status could not be loaded: {errMsg(meQuery.error)}
        </div>
      )}

      {isDedicatedTraderAccount && isSuspended && (
        <div className="mb-6 rounded-xl border border-red-500/30 bg-red-950/30 p-4 text-sm text-red-200" data-testid="trader-suspended-notice">
          <div className="flex items-center gap-2 font-semibold">
            <ShieldAlert size={18} />
            <span>Trader Desk Suspended</span>
          </div>
          <p className="mt-1 text-xs text-red-300">
            This trader desk has been suspended by GTEX Compliance. All trading functions, rates, and liquidity purchases are temporarily disabled.
          </p>
        </div>
      )}

      {isDedicatedTraderAccount && me && !isVerified && !isSuspended && (
        <TraderVerificationCard profile={me} onVerified={() => qc.invalidateQueries({ queryKey: ["coin-trader-me"] })} />
      )}

      {me && status !== "approved" && !isSuspended && (
        <div className="mb-6 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] p-4" data-testid="coin-trader-application-status">
          <p className="gx-label">Your trader application</p>
          <p className="mt-1 text-sm font-bold text-white">{me.display_name} · {label(status)}</p>
          <p className="mt-2 text-sm text-slate-400">
            {status === "applied" || status === "pending"
              ? "Your dedicated Coin Trader account is awaiting desk verification. Complete identity verification above to activate."
              : "Trader operations are not enabled for this application status."}
          </p>
        </div>
      )}

      {list.length === 0 ? <Empty title="No verified traders yet" body="The marketplace will show verified liquidity partners when available." /> : <OrderForm traders={list} />}
      <p className="gx-label mt-6">My orders</p>
      <div className="space-y-2" data-testid="my-coin-orders">
        {(orders || []).length === 0 && <p className="text-sm text-slate-500">No coin trades yet.</p>}
        {(orders || []).map((o: any) => <OrderRow key={o.id} o={o} traders={traders || []} />)}
      </div>
      {isTrader && (
        <>
          <p className="gx-label mt-6">My trader desk · {me.display_name}</p>
          <TraderRatePublisher profile={me} onSaved={() => qc.invalidateQueries({ queryKey: ["coin-trader-me"] })} />
          <TraderLiquidityPurchase onPurchased={() => qc.invalidateQueries({ queryKey: ["coin-trader-me"] })} />
          <p className="gx-label mt-6">Desk client orders</p>
          <div className="space-y-2" data-testid="trader-desk-orders">
            {(deskOrders || []).length === 0 && <p className="text-sm text-slate-500">No client orders.</p>}
            {(deskOrders || []).map((o: any) => <OrderRow key={o.id} o={o} asTrader traders={traders || []} />)}
          </div>
        </>
      )}
    </Panel>
  );
}

function TraderRatePublisher({ profile, onSaved }: { profile: any; onSaved?: () => void }) {
  const qc = useQueryClient();
  const [coinUnit, setCoinUnit] = useState<CoinUnit>("coin");
  const existing = (profile?.rates || []).find(
    (r: any) => String(r.coin_unit || "coin").toLowerCase() === coinUnit
  );
  const [buyRate, setBuyRate] = useState(String(existing?.buy_rate_fiat ?? (coinUnit === "credit" ? 2.5 : 50)));
  const [sellRate, setSellRate] = useState(String(existing?.sell_rate_fiat ?? (coinUnit === "credit" ? 3 : 56)));
  const [minAmount, setMinAmount] = useState(String(existing?.min_coin_amount ?? (coinUnit === "credit" ? 20000 : 4000)));
  const [maxAmount, setMaxAmount] = useState(String(existing?.max_coin_amount ?? 100000));
  const [liquidity, setLiquidity] = useState(String(existing?.available_liquidity ?? 50000));
  const [isActive, setIsActive] = useState(existing?.is_active ?? true);
  const [saving, setSaving] = useState(false);

  const selectUnit = (nextUnit: CoinUnit) => {
    setCoinUnit(nextUnit);
    const rate = (profile?.rates || []).find(
      (r: any) => String(r.coin_unit || "coin").toLowerCase() === nextUnit
    );
    setBuyRate(String(rate?.buy_rate_fiat ?? (nextUnit === "credit" ? 2.5 : 50)));
    setSellRate(String(rate?.sell_rate_fiat ?? (nextUnit === "credit" ? 3 : 56)));
    setMinAmount(String(rate?.min_coin_amount ?? (nextUnit === "credit" ? 20000 : 4000)));
    setMaxAmount(String(rate?.max_coin_amount ?? 100000));
    setLiquidity(String(rate?.available_liquidity ?? 50000));
    setIsActive(rate?.is_active ?? true);
  };

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    const buy = Number(buyRate);
    const sell = Number(sellRate);
    if (!Number.isFinite(buy) || buy <= 0 || !Number.isFinite(sell) || sell <= 0 || sell < buy) {
      toast.error("Enter valid buy and sell rates where sell rate >= buy rate.");
      return;
    }
    setSaving(true);
    try {
      await api.put("/coin-traders/me/rates", {
        coin_unit: coinUnit,
        fiat_currency: "NGN",
        buy_rate_fiat: buy,
        sell_rate_fiat: sell,
        min_coin_amount: Number(minAmount) || 0,
        max_coin_amount: Number(maxAmount) || 0,
        available_liquidity: Number(liquidity) || 0,
        is_active: isActive,
      });
      toast.success(`${coinUnitMeta(coinUnit).name} rate updated.`);
      await qc.invalidateQueries({ queryKey: ["coin-trader-me"] });
      await qc.invalidateQueries({ queryKey: ["coin-traders"] });
      if (onSaved) onSaved();
    } catch (error: any) {
      toast.error(errMsg(error));
    } finally {
      setSaving(false);
    }
  };

  const unitInfo = coinUnitMeta(coinUnit);

  return (
    <form onSubmit={handleSave} className="mt-3 rounded-xl border border-white/10 bg-white/[0.02] p-4" data-testid="trader-rate-publisher-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h4 className="gx-label text-slate-300">Desk Rate Publisher</h4>
          <p className="mt-0.5 text-xs text-slate-400">
            Configure independent Naira rates and limits for GTEX Coin (GTC) and Fan Coin (FNC).
          </p>
        </div>
        <div className="flex gap-2">
          {(["coin", "credit"] as const).map((unit) => (
            <button
              key={unit}
              type="button"
              data-testid={`trader-rate-unit-${unit}`}
              onClick={() => selectUnit(unit)}
              className={`gx-btn py-1.5 px-3 text-xs ${coinUnit === unit ? "gx-btn-primary" : "gx-btn-secondary"}`}
            >
              {coinUnitMeta(unit).code}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-6">
        <label className="block">
          <span className="gx-label">Desk buy (₦/{unitInfo.code})</span>
          <input data-testid="trader-rate-buy-input" className="gx-input mt-1" type="number" step="0.01" min={0.01} value={buyRate} onChange={(e) => setBuyRate(e.target.value)} />
        </label>
        <label className="block">
          <span className="gx-label">Desk sell (₦/{unitInfo.code})</span>
          <input data-testid="trader-rate-sell-input" className="gx-input mt-1" type="number" step="0.01" min={0.01} value={sellRate} onChange={(e) => setSellRate(e.target.value)} />
        </label>
        <label className="block">
          <span className="gx-label">Min ({unitInfo.code})</span>
          <input data-testid="trader-rate-min-input" className="gx-input mt-1" type="number" min={0} value={minAmount} onChange={(e) => setMinAmount(e.target.value)} />
        </label>
        <label className="block">
          <span className="gx-label">Max ({unitInfo.code})</span>
          <input data-testid="trader-rate-max-input" className="gx-input mt-1" type="number" min={0} value={maxAmount} onChange={(e) => setMaxAmount(e.target.value)} />
        </label>
        <label className="block">
          <span className="gx-label">Liquidity ({unitInfo.code})</span>
          <input data-testid="trader-rate-liquidity-input" className="gx-input mt-1" type="number" min={0} value={liquidity} onChange={(e) => setLiquidity(e.target.value)} />
        </label>
        <div className="flex flex-col justify-end gap-2">
          <label className="flex items-center gap-2 text-xs text-slate-300">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            Active lane
          </label>
          <Btn type="submit" disabled={saving} data-testid="trader-rate-save-btn">
            {saving ? "Saving..." : `Save ${unitInfo.code} Rate`}
          </Btn>
        </div>
      </div>
    </form>
  );
}

function TraderLiquidityPurchase({ onPurchased }: { onPurchased?: () => void }) {
  const [coinUnit, setCoinUnit] = useState<CoinUnit>("coin");
  const [amount, setAmount] = useState("4000");
  const [provider, setProvider] = useState<"korapay" | "paystack">("korapay");
  const [submitting, setSubmitting] = useState(false);
  const qc = useQueryClient();
  const unitInfo = coinUnitMeta(coinUnit);

  const { data: quote, isLoading: quoteLoading } = useQuery({
    queryKey: ["liquidity-quote", coinUnit, amount, provider],
    queryFn: async () => {
      if (!Number(amount) || Number(amount) <= 0) return null;
      const { data } = await api.post("/coin-traders/me/liquidity/quote", {
        amount: Number(amount),
        provider,
        coin_unit: coinUnit,
      });
      return data;
    },
    enabled: Number(amount) > 0,
  });

  const belowMinimum = Boolean(quote && Number(quote.amount_fiat) < unitInfo.minBuyerNgn);

  const handlePurchase = async () => {
    if (!Number(amount) || Number(amount) <= 0 || belowMinimum) return;
    setSubmitting(true);
    try {
      const { data } = await api.post("/coin-traders/me/liquidity/purchase", {
        amount: Number(amount),
        provider,
        coin_unit: coinUnit,
        callback_url: `${window.location.origin}/payment/callback`,
      });
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        toast.success("Liquidity purchase initiated.");
        qc.invalidateQueries({ queryKey: ["coin-trader-me"] });
        if (onPurchased) onPurchased();
      }
    } catch (e: any) {
      toast.error(errMsg(e));
    } finally {
      setSubmitting(false);
    }
  };

  const providerLabel = provider === "korapay" ? "KoraPay" : "Paystack";

  return (
    <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.02] p-4" data-testid="trader-liquidity-purchase-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h4 className="gx-label text-slate-300">Add Trading Liquidity / Buy Inventory</h4>
          <p className="mt-1 text-xs text-slate-400">
            Acquire GTEX Coin (GTC, ₦50/unit, ₦200,000 minimum) or Fan Coin (FNC, ₦2.50/unit, ₦50,000 minimum) inventory to back your desk orders.
          </p>
        </div>
        <div className="flex gap-2">
          {(["coin", "credit"] as const).map((unit) => (
            <button
              key={unit}
              type="button"
              data-testid={`trader-liquidity-unit-${unit}`}
              onClick={() => {
                setCoinUnit(unit);
                if (unit === "credit" && amount === "4000") {
                  setAmount("20000");
                } else if (unit === "coin" && amount === "20000") {
                  setAmount("4000");
                }
              }}
              className={`gx-btn py-1.5 px-3 text-xs ${coinUnit === unit ? "gx-btn-primary" : "gx-btn-secondary"}`}
            >
              {coinUnitMeta(unit).code}
            </button>
          ))}
        </div>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-4">
        <div>
          <label className="gx-label">Provider</label>
          <div className="mt-1 flex gap-2">
            {(["korapay", "paystack"] as const).map((p) => (
              <button
                key={p}
                type="button"
                data-testid={`trader-liquidity-provider-${p}`}
                onClick={() => setProvider(p)}
                className={`gx-btn flex-1 py-1.5 text-xs ${provider === p ? "gx-btn-primary" : "gx-btn-secondary"}`}
              >
                {p === "korapay" ? "KoraPay" : "Paystack"}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="gx-label">Amount ({unitInfo.code})</label>
          <input
            data-testid="trader-liquidity-amount-input"
            className="gx-input mt-1"
            type="number"
            min={1}
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
        </div>
        <div className="md:col-span-2 flex flex-col justify-end">
          {quote && (
            <div className="mb-2 text-xs text-slate-400 flex flex-wrap gap-x-4" data-testid="trader-liquidity-quote">
              <span>Fiat: <b className="text-white">₦{fmt(quote.amount_fiat)}</b></span>
              <span>Platform fee: <b className="text-white">{fmt(quote.fee_amount)} {unitInfo.code}</b></span>
              <span>Processor fee: <b className="text-white">{fmt(quote.processor_fee)} {unitInfo.code}</b></span>
              <span>Net: <b className="text-emerald-400">{fmt(quote.net_amount)} {unitInfo.code}</b></span>
            </div>
          )}
          {belowMinimum && (
            <p className="mb-2 text-xs text-amber-300" data-testid="trader-liquidity-minimum-warning">
              Minimum purchase is ₦{fmt(unitInfo.minBuyerNgn)} for {unitInfo.name}.
            </p>
          )}
          <Btn
            disabled={submitting || quoteLoading || !Number(amount) || Number(amount) <= 0 || belowMinimum}
            onClick={handlePurchase}
            data-testid="trader-liquidity-submit"
          >
            {submitting ? "Initiating..." : `Buy ${unitInfo.code} with ${providerLabel}`}
          </Btn>
        </div>
      </div>
    </div>
  );
}
