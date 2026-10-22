import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
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
  const [amount, setAmount] = useState("10");
  const trader = traders.find((t: any) => t.id === traderId);
  const rate = trader ? rateOf(trader) : null;
  const unitPrice = rate ? Number(direction === "user_buys" ? rate.sell_rate_fiat : rate.buy_rate_fiat) : 0;
  const submit = () =>
    act("/coin-traders/orders", { trader_profile_id: traderId, direction, coin_unit: "coin", coin_amount: Number(amount), fiat_currency: "NGN", idempotency_key: `web-${Date.now()}-${Math.random().toString(36).slice(2, 8)}` }, "Order created. Waiting for the trader to accept.");
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
      <Btn disabled={!rate || Number(amount) <= 0} onClick={submit} data-testid="coin-order-submit">{direction === "user_buys" ? "Buy" : "Sell"} GTX</Btn>
      {rate && (
        <p className="text-xs text-slate-400 md:col-span-5" data-testid="coin-order-preview">
          {direction === "user_buys" ? "You pay" : "You receive"} <b className="text-white">₦{fmt(unitPrice * Number(amount || 0), 2)}</b> at ₦{fmt(unitPrice, 2)} per GTEX Coin · limits {fmt(rate.min_coin_amount)}–{fmt(rate.max_coin_amount) || "∞"} GTX.{" "}
          {direction === "user_sells" ? "Your coins are locked in escrow until you confirm the Naira arrived." : "The trader's coins are locked in escrow until they confirm your payment."}
        </p>
      )}
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
  const meQuery = useQuery({ queryKey: ["coin-trader-me"], queryFn: async () => (await api.get("/coin-traders/me")).data, retry: false });
  const me = meQuery.data;
  const status = String(me?.status || "").toLowerCase();
  const isTrader = isDedicatedTraderAccount && me && status === "approved";
  const missingProfile = !meQuery.isLoading && !me && [403, 404].includes(Number((meQuery.error as any)?.response?.status));
  const showApplication = isDedicatedTraderAccount && (missingProfile || status === "rejected");
  const { data: deskOrders } = useQuery({ queryKey: ["coin-orders", "desk"], queryFn: async () => (await api.get("/coin-traders/orders", { params: { as_trader: true } })).data, enabled: !!isTrader });
  const list = (traders || []).filter((t: any) => t.user_id !== user?.id);
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
      toast.success("Coin Trader application submitted. Trading tools unlock after approval.");
    } catch (error: any) {
      setApplyError(errMsg(error));
    } finally {
      setApplying(false);
    }
  };

  return (
    <Panel eyebrow="GTEX Coin · P2P marketplace" title="Coin Traders" testid="coin-traders-panel" className="lg:col-span-12">
      <p className="mb-4 text-sm text-slate-400">
        User accounts can buy or sell GTEX Coin with approved Naira traders through escrow-protected orders. Operating a trader desk requires a dedicated Coin Trader account created through the Coin Trader signup path; a User account cannot be promoted into that lane.
      </p>
      {!isDedicatedTraderAccount && (
        <div className="mb-5 rounded-lg border border-white/10 bg-white/[0.02] p-3 text-sm text-slate-400" data-testid="dedicated-trader-signup-notice">
          This is a customer account lane, not a trader-desk application. Sign out and create a separate Coin Trader account to operate a trader desk.
        </div>
      )}

      {showApplication && (
        <div className="mb-6 rounded-xl border border-amber-400/25 bg-amber-500/[0.05] p-4" data-testid="coin-trader-application">
          <p className="gx-label text-amber-300">{status === "rejected" ? "Resubmit application" : "Become a coin trader"}</p>
          <h3 className="gx-display mt-1 text-xl font-bold uppercase text-white">Apply for trader status</h3>
          <p className="mt-2 max-w-3xl text-sm leading-5 text-slate-400">
            Applications are reviewed before trader-desk tools are enabled. This account is already a dedicated Coin Trader account; approval will not turn a User account into a Trader account.
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
      {me && status !== "approved" && (
        <div className="mb-6 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] p-4" data-testid="coin-trader-application-status">
          <p className="gx-label">Your trader application</p>
          <p className="mt-1 text-sm font-bold text-white">{me.display_name} · {label(status)}</p>
          <p className="mt-2 text-sm text-slate-400">
            {status === "applied" || status === "pending"
              ? "Your dedicated Coin Trader account is awaiting desk approval. It remains in the Coin Trader lane while approval is pending."
              : "Trader operations are not enabled for this application status."}
          </p>
        </div>
      )}

      {list.length === 0 ? <Empty title="No approved traders yet" body="The marketplace will show approved liquidity partners when available." /> : <OrderForm traders={list} />}
      <p className="gx-label mt-6">My orders</p>
      <div className="space-y-2" data-testid="my-coin-orders">
        {(orders || []).length === 0 && <p className="text-sm text-slate-500">No coin trades yet.</p>}
        {(orders || []).map((o: any) => <OrderRow key={o.id} o={o} traders={traders || []} />)}
      </div>
      {isTrader && (
        <>
          <p className="gx-label mt-6">My trader desk · {me.display_name}</p>
          <div className="space-y-2" data-testid="trader-desk-orders">
            {(deskOrders || []).length === 0 && <p className="text-sm text-slate-500">No client orders.</p>}
            {(deskOrders || []).map((o: any) => <OrderRow key={o.id} o={o} asTrader traders={traders || []} />)}
          </div>
        </>
      )}
    </Panel>
  );
}
