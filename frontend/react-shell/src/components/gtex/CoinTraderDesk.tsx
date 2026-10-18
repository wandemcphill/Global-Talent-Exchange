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
  const { data: traders } = useQuery({ queryKey: ["coin-traders"], queryFn: async () => (await api.get("/coin-traders")).data });
  const { data: orders } = useQuery({ queryKey: ["coin-orders", "me"], queryFn: async () => (await api.get("/coin-traders/orders")).data });
  const { data: me } = useQuery({ queryKey: ["coin-trader-me"], queryFn: async () => (await api.get("/coin-traders/me")).data, retry: false });
  const isTrader = me && String(me.status) === "approved";
  const { data: deskOrders } = useQuery({ queryKey: ["coin-orders", "desk"], queryFn: async () => (await api.get("/coin-traders/orders", { params: { as_trader: true } })).data, enabled: !!isTrader });
  const list = (traders || []).filter((t: any) => t.user_id !== user?.id);
  return (
    <Panel eyebrow="Peer-to-peer · escrow protected" title="Coin traders" testid="coin-traders-panel" className="lg:col-span-12">
      <p className="mb-4 text-sm text-slate-400">Buy or sell GTEX Coin with verified Naira coin traders. Trades settle in the same wallet that funds your clubs, so coins you buy here can be injected into a club straight away.</p>
      {list.length === 0 ? <Empty title="No verified traders yet" body="Approved coin traders will appear here." /> : <OrderForm traders={list} />}
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
