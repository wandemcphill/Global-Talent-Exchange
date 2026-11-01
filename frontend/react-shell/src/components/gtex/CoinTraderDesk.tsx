import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, ShieldAlert, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, label, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Empty, Panel } from "@/components/gtex/ui";

const ACTIVE = ["payment_pending", "escrow_locked", "accepted"];
const DONE_TONE: any = { released: "emerald", admin_released: "emerald", cancelled: "slate", refunded: "slate", admin_refunded: "slate", disputed: "red" };

function rateOf(t: any) {
  return (t.rates || []).find((r: any) => r.coin_unit === "coin" && r.is_active !== false) || null;
}

function useOrderActions() {
  const qc = useQueryClient();
  const refresh = useRefreshOwner();
  return async (path: string, body: any, ok: string) => {
    try {
      await api.post(path, body);
      toast.success(ok);
      qc.invalidateQueries({ queryKey: ["coin-orders"] });
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
  const base = `/coin-traders/orders/${o.id}`;
  return (
    <div data-testid={`coin-order-${o.id}`} className="rounded-sm border border-white/10 p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-white">
          {buys ? (asTrader ? "Client buys" : "Buy") : asTrader ? "Client sells" : "Sell"} <b>{fmt(o.coin_amount)} GTX</b> for ₦{fmt(o.fiat_total)}
          <span className="ml-2 text-xs text-slate-500">{asTrader ? "" : `via ${trader?.display_name || "trader"}`} · ₦{fmt(o.quoted_rate_fiat)}/coin</span>
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
        <p className="mt-2 text-xs text-slate-400">Pay to: {o.terms_snapshot?.payment_instructions || trader.bank_accounts.map((b: any) => `${b.bank_name || ""} ${b.account_number || ""} ${b.account_name || ""}`).join(" · ")}</p>
      )}
    </div>
  );
}

function OrderForm({ traders }: any) {
  const act = useOrderActions();
  const [traderId, setTraderId] = useState("");
  const [direction, setDirection] = useState("user_buys");
  const [amount, setAmount] = useState("250");
  const trader = traders.find((t: any) => t.id === traderId);
  const rate = trader ? rateOf(trader) : null;
  const unitPrice = rate ? Number(direction === "user_buys" ? rate.sell_rate_fiat : rate.buy_rate_fiat) : 0;
  const fiatTotal = unitPrice * Number(amount || 0);
  const isBelowMinBuyerOrder = direction === "user_buys" && fiatTotal < 200000;

  const submit = () => {
    if (isBelowMinBuyerOrder) {
      toast.error("Minimum buyer order value for GTEX Coin purchases is ₦200,000.");
      return;
    }
    act(
      "/coin-traders/orders",
      {
        trader_profile_id: traderId,
        direction,
        coin_unit: "coin",
        coin_amount: Number(amount),
        fiat_currency: "NGN",
        idempotency_key: `web-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      },
      "Order created. Waiting for the trader to accept."
    );
  };

  return (
    <div className="grid gap-3 md:grid-cols-5" data-testid="coin-order-form">
      <select data-testid="coin-trader-select" className="gx-input md:col-span-2" value={traderId} onChange={(e) => setTraderId(e.target.value)}>
        <option value="">Choose a verified trader</option>
        {traders.map((t: any) => {
          const r = rateOf(t);
          return <option key={t.id} value={t.id} disabled={!r}>{t.display_name} · {t.tier}{r ? ` · buy ₦${fmt(r.sell_rate_fiat)} / sell ₦${fmt(r.buy_rate_fiat)}` : " · no rate"}</option>;
        })}
      </select>
      <div className="flex gap-1">
        {[["user_buys", "Buy"], ["user_sells", "Sell"]].map(([v, l]) => <button key={v} data-testid={`coin-direction-${v}`} onClick={() => setDirection(v)} className={`gx-btn flex-1 ${direction === v ? "gx-btn-primary" : "gx-btn-secondary"}`}>{l}</button>)}
      </div>
      <input data-testid="coin-amount-input" className="gx-input" type="number" min={1} value={amount} onChange={(e) => setAmount(e.target.value)} />
      <Btn disabled={!rate || Number(amount) <= 0 || isBelowMinBuyerOrder} onClick={submit} data-testid="coin-order-submit">{direction === "user_buys" ? "Buy" : "Sell"} GTX</Btn>

      {isBelowMinBuyerOrder && rate && (
        <p className="text-xs text-amber-400 md:col-span-5 flex items-center gap-1.5" data-testid="min-buyer-order-warning">
          <AlertTriangle size={14} />
          ₦200,000 minimum buyer order required. Current total: ₦{fmt(fiatTotal, 2)} (Set coin amount to at least {Math.ceil(200000 / (unitPrice || 1))} GTX).
        </p>
      )}

      {rate && !isBelowMinBuyerOrder && (
        <p className="text-xs text-slate-400 md:col-span-5" data-testid="coin-order-preview">
          {direction === "user_buys" ? "You pay" : "You receive"} <b className="text-white">₦{fmt(unitPrice * Number(amount || 0), 2)}</b> at ₦{fmt(unitPrice, 2)} per GTEX Coin · limits {fmt(rate.min_coin_amount)}–{fmt(rate.max_coin_amount) || "∞"} GTX.{" "}
          {direction === "user_sells" ? "Your coins are locked in escrow until you confirm the Naira arrived." : "The trader's coins are locked in escrow until they confirm your payment."}
        </p>
      )}
    </div>
  );
}

function TraderVerificationCard({ profile, onVerified }: { profile: any; onVerified?: () => void }) {
  const [provider, setProvider] = useState<"sandbox" | "didit" | "smile_id">("sandbox");
  const [initiating, setInitiating] = useState(false);
  const qc = useQueryClient();

  const handleInitiate = async () => {
    setInitiating(true);
    try {
      const { data } = await api.post("/coin-traders/verification/initiate", {
        provider,
        id_type: "bvn",
        callback_url: `${window.location.origin}/trader/verification/callback`,
      });
      if (data.session_url) {
        window.open(data.session_url, "_blank");
      }
      toast.success(`Verification initiated with ${data.provider}. Trader desk activates automatically upon authoritative provider result.`);
      qc.invalidateQueries({ queryKey: ["coin-trader-me"] });
      if (onVerified) onVerified();
    } catch (err: any) {
      toast.error("Failed to initiate verification: " + errMsg(err));
    } finally {
      setInitiating(false);
    }
  };

  return (
    <div className="mb-6 rounded-xl border border-indigo-400/30 bg-indigo-500/[0.05] p-5" data-testid="trader-kyc-card">
      <div className="flex items-start gap-3">
        <ShieldCheck className="size-6 text-indigo-400 shrink-0 mt-0.5" />
        <div className="space-y-2">
          <h3 className="gx-display text-base font-bold uppercase text-white">Full Trader Identity Verification Required</h3>
          <p className="text-xs leading-5 text-slate-300">
            Coin Traders must complete authoritative identity verification before conducting marketplace trading, publishing rates, or buying desk liquidity. Supported verification methods include Government ID / Nigerian BVN or NIN with live selfie liveness detection.
          </p>
          <div className="pt-2 flex flex-wrap items-center gap-3">
            <select className="gx-input max-w-[240px] py-1.5 text-xs" value={provider} onChange={(e) => setProvider(e.target.value as any)}>
              <option value="sandbox">Sandbox Provider (Instant verification test)</option>
              <option value="didit">DIDit (Government ID & Facial Comparison)</option>
              <option value="smile_id">Smile ID (BVN/NIN & Liveness)</option>
            </select>
            <Btn disabled={initiating} onClick={handleInitiate} data-testid="initiate-trader-kyc-btn">
              {initiating ? "Starting session..." : "Verify Identity Now"}
            </Btn>
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
          kyc_required: true,
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
        Ordinary User accounts can buy or sell GTEX Coin with verified Naira traders through escrow-protected orders with no universal KYC gate. Operating a trader desk is an exclusive lane requiring dedicated trader verification.
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

function TraderLiquidityPurchase({ onPurchased }: { onPurchased?: () => void }) {
  const [amount, setAmount] = useState("1000");
  const [provider, setProvider] = useState<"korapay" | "paystack">("korapay");
  const [submitting, setSubmitting] = useState(false);
  const qc = useQueryClient();

  const { data: quote, isLoading: quoteLoading } = useQuery({
    queryKey: ["liquidity-quote", amount, provider],
    queryFn: async () => {
      if (!Number(amount) || Number(amount) <= 0) return null;
      const { data } = await api.post("/coin-traders/me/liquidity/quote", {
        amount: Number(amount),
        provider,
        coin_unit: "coin",
      });
      return data;
    },
    enabled: Number(amount) > 0,
  });

  const handlePurchase = async () => {
    if (!Number(amount) || Number(amount) <= 0) return;
    setSubmitting(true);
    try {
      const { data } = await api.post("/coin-traders/me/liquidity/purchase", {
        amount: Number(amount),
        provider,
        coin_unit: "coin",
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
      <h4 className="gx-label text-slate-300">Add Trading Liquidity / Buy Inventory</h4>
      <p className="mt-1 text-xs text-slate-400">
        Acquire GTEX Coin inventory to back your desk orders. Purchased coins automatically update your trading liquidity and available balance upon verified payment.
      </p>
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
          <label className="gx-label">Amount (GTX)</label>
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
              <span>Platform fee: <b className="text-white">{fmt(quote.fee_amount)} GTX</b></span>
              <span>Processor fee: <b className="text-white">{fmt(quote.processor_fee)} GTX</b></span>
              <span>Net: <b className="text-emerald-400">{fmt(quote.net_amount)} GTX</b></span>
            </div>
          )}
          <Btn
            disabled={submitting || quoteLoading || !Number(amount) || Number(amount) <= 0}
            onClick={handlePurchase}
            data-testid="trader-liquidity-submit"
          >
            {submitting ? "Initiating..." : `Buy with ${providerLabel}`}
          </Btn>
        </div>
      </div>
    </div>
  );
}
