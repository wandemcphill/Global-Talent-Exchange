import React, { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock, MessageSquare, ShieldCheck, Star } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { fmt, label, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip } from "@/components/gtex/ui";
import { coinUnitMeta, formatRemainingTime, type TradeOrder } from "./types";

const ACTIVE_PAYMENT = new Set(["payment_pending", "escrow_locked", "accepted"]);
const DONE_TONE: Record<string, "emerald" | "slate" | "red" | "gold"> = {
  released: "emerald",
  admin_released: "emerald",
  cancelled: "slate",
  expired: "slate",
  refunded: "slate",
  admin_refunded: "slate",
  disputed: "red",
};

interface Props {
  order: TradeOrder;
  asTrader?: boolean;
  traders?: any[];
}

export function CoinTraderOrderRoom({ order, asTrader = false, traders = [] }: Props) {
  const qc = useQueryClient();
  const refresh = useRefreshOwner();
  const [proofRef, setProofRef] = useState("");
  const [proofNote, setProofNote] = useState("");
  const [disputeReason, setDisputeReason] = useState("");
  const [showDisputeBox, setShowDisputeBox] = useState(false);
  const [chatText, setChatText] = useState("");
  const [showChat, setShowChat] = useState(false);
  const [ratingScore, setRatingScore] = useState(5);
  const [ratingComment, setRatingComment] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [countdown, setCountdown] = useState<string | null>(() =>
    formatRemainingTime(order.payment_window_expires_at),
  );

  useEffect(() => {
    setCountdown(formatRemainingTime(order.payment_window_expires_at));
    if (!order.payment_window_expires_at || !ACTIVE_PAYMENT.has(order.status)) return;
    const timer = setInterval(() => {
      setCountdown(formatRemainingTime(order.payment_window_expires_at));
    }, 1000);
    return () => clearInterval(timer);
  }, [order.payment_window_expires_at, order.status]);

  const buys = order.direction === "user_buys";
  const iSendFiat = asTrader ? !buys : buys;
  const iReceiveFiat = !iSendFiat;
  const trader = traders.find((t: any) => t.id === order.trader_profile_id);
  const unitInfo = coinUnitMeta(order.coin_unit);
  const base = `/coin-traders/orders/${order.id}`;
  const isCompleted = order.status === "released" || order.status === "admin_released";
  const canDispute = ACTIVE_PAYMENT.has(order.status) || order.status === "proof_submitted";
  const messages = order.messages || [];

  const runAction = async (key: string, path: string, body: any, okMsg: string) => {
    setBusy(key);
    try {
      await api.post(path, body);
      toast.success(okMsg);
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["coin-orders"] }),
        qc.invalidateQueries({ queryKey: ["coin-trader-dashboard"] }),
        qc.invalidateQueries({ queryKey: ["coin-trader-marketplace"] }),
      ]);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(null);
    }
  };

  const bankDetails =
    (order.counterparty_payment_details && order.counterparty_payment_details.length > 0
      ? order.counterparty_payment_details
      : trader?.bank_accounts) || [];

  const statusLabel =
    order.status === "created"
      ? "Awaiting Merchant Accept"
      : order.status === "payment_pending"
        ? "Awaiting Fiat Payment"
        : order.status === "proof_submitted"
          ? "Payment Submitted · Awaiting Release"
          : label(order.status);

  return (
    <div
      data-testid={`coin-order-${order.id}`}
      className="rounded-xl border border-gtex-graphite bg-gtex-midnight/80 p-4 text-sm shadow-md space-y-3"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-white">
              {buys ? (asTrader ? "Client buys" : "Buy") : asTrader ? "Client sells" : "Sell"}{" "}
              {fmt(order.coin_amount)} {unitInfo.code}
            </span>
            <span className="text-slate-300">for ₦{fmt(order.fiat_total, 2)}</span>
            <span className="text-xs text-slate-400">
              @ ₦{fmt(order.quoted_rate_fiat, 2)}/{unitInfo.code}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Order ID <span className="gx-mono text-slate-300">{order.id.slice(0, 8)}</span>
            {" · "}
            {asTrader
              ? `Client: ${order.customer_display_name || order.user_id.slice(0, 8)}`
              : `Merchant: ${order.trader_display_name || trader?.display_name || "Coin Trader"}`}
            {order.payment_method ? ` · ${order.payment_method}` : ""}
            {" · Fee: ₦0"}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {countdown && ACTIVE_PAYMENT.has(order.status) && (
            <span className="inline-flex items-center gap-1 rounded-md border border-amber-400/30 bg-amber-500/10 px-2 py-0.5 text-xs text-amber-200">
              <Clock size={12} /> {countdown}
            </span>
          )}
          <Chip tone={DONE_TONE[order.status] || "gold"}>{statusLabel}</Chip>
        </div>
      </div>

      {/* Escrow protection strip */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/[0.04] px-3 py-1.5 text-xs text-emerald-200">
        <span className="inline-flex items-center gap-1.5">
          <ShieldCheck size={14} className="text-emerald-400" />
          {buys
            ? "Merchant's coins are locked in GTEX canonical escrow."
            : "Customer's coins are locked in GTEX canonical escrow."}
        </span>
        {order.proof?.proof_reference && (
          <span className="text-slate-300">
            Transfer Ref: <b className="gx-mono text-white">{order.proof.proof_reference}</b>
          </span>
        )}
      </div>

      {/* Protected payment details (revealed only in active payment stages) */}
      {iSendFiat &&
        ACTIVE_PAYMENT.has(order.status) &&
        buys &&
        (bankDetails.length > 0 || order.terms_snapshot?.payment_instructions) && (
          <div className="rounded-lg border border-sky-400/25 bg-sky-500/[0.06] p-3 text-xs text-sky-100">
            <p className="font-semibold text-sky-200">
              Merchant Payment Details (Protected · Active Order Only)
            </p>
            {order.terms_snapshot?.payment_instructions && (
              <p className="mt-1">{order.terms_snapshot.payment_instructions}</p>
            )}
            {bankDetails.map((b: any, i: number) => (
              <p key={i} className="mt-1 gx-mono">
                {b.bank_name || b.bank || "Bank"} · {b.account_number || ""} ·{" "}
                {b.account_name || ""}
              </p>
            ))}
          </div>
        )}

      {!buys &&
        order.customer_payout_details &&
        (ACTIVE_PAYMENT.has(order.status) ||
          order.status === "created" ||
          order.status === "proof_submitted") && (
          <div className="rounded-lg border border-sky-400/25 bg-sky-500/[0.06] p-3 text-xs text-sky-100">
            <p className="font-semibold text-sky-200">Customer Naira Payout Account</p>
            <p className="mt-1 gx-mono">
              {order.customer_payout_details.bank_name || ""} ·{" "}
              {order.customer_payout_details.account_number || ""} ·{" "}
              {order.customer_payout_details.account_name || ""}
            </p>
          </div>
        )}

      {/* Action controls */}
      <div className="flex flex-wrap items-center gap-2">
        {asTrader && order.status === "created" && (
          <Btn
            disabled={busy !== null}
            onClick={() =>
              runAction("accept", `${base}/accept`, {}, "Order accepted. Payment window started.")
            }
            data-testid={`accept-order-${order.id}`}
          >
            {busy === "accept" ? "Accepting..." : "Accept Order"}
          </Btn>
        )}

        {iSendFiat && ACTIVE_PAYMENT.has(order.status) && (
          <div className="flex flex-wrap items-center gap-2">
            <input
              data-testid={`proof-input-${order.id}`}
              className="gx-input max-w-[200px] py-1.5 text-xs"
              placeholder="Bank transfer ref / NIP"
              value={proofRef}
              onChange={(e) => setProofRef(e.target.value)}
            />
            <input
              className="gx-input max-w-[180px] py-1.5 text-xs"
              placeholder="Optional note"
              value={proofNote}
              onChange={(e) => setProofNote(e.target.value)}
            />
            <Btn
              variant="secondary"
              disabled={proofRef.trim().length < 3 || busy !== null}
              onClick={() =>
                runAction(
                  "proof",
                  `${base}/proof`,
                  { proof_reference: proofRef.trim(), note: proofNote.trim() || undefined },
                  "Payment proof submitted.",
                )
              }
              data-testid={`submit-proof-${order.id}`}
            >
              {busy === "proof" ? "Submitting..." : "I've Sent the Naira"}
            </Btn>
          </div>
        )}

        {iReceiveFiat && order.status === "proof_submitted" && (
          <Btn
            disabled={busy !== null}
            onClick={() =>
              runAction(
                "confirm",
                `${base}/confirm`,
                {},
                "Payment confirmed and escrowed coins released.",
              )
            }
            data-testid={`confirm-order-${order.id}`}
          >
            {busy === "confirm" ? "Releasing..." : "Confirm Naira Received & Release Coins"}
          </Btn>
        )}

        {(order.status === "created" || (!iReceiveFiat && order.status === "payment_pending")) && (
          <Btn
            variant="ghost"
            disabled={busy !== null}
            onClick={() =>
              runAction("cancel", `${base}/cancel`, {}, "Order cancelled and escrow refunded.")
            }
            data-testid={`cancel-order-${order.id}`}
          >
            {asTrader && order.status === "created" ? "Decline" : "Cancel Order"}
          </Btn>
        )}

        {canDispute && (
          <Btn
            variant="danger"
            disabled={busy !== null}
            onClick={() => setShowDisputeBox((v) => !v)}
            data-testid={`dispute-order-${order.id}`}
          >
            Dispute
          </Btn>
        )}

        <Btn
          variant="ghost"
          onClick={() => setShowChat((v) => !v)}
          data-testid={`toggle-chat-${order.id}`}
        >
          <MessageSquare size={14} /> Chat ({messages.length})
        </Btn>
      </div>

      {showDisputeBox && canDispute && (
        <div className="rounded-lg border border-red-500/30 bg-red-950/25 p-3 space-y-2">
          <p className="text-xs font-semibold text-red-200">
            Open Escrow Dispute (Freezes release until admin investigation)
          </p>
          <div className="flex flex-wrap gap-2">
            <input
              className="gx-input flex-1 min-w-[220px] py-1.5 text-xs"
              placeholder="Explain the issue (e.g. paid Naira 20m ago, no release)"
              value={disputeReason}
              onChange={(e) => setDisputeReason(e.target.value)}
            />
            <Btn
              variant="danger"
              disabled={disputeReason.trim().length < 3 || busy !== null}
              onClick={() =>
                runAction(
                  "dispute",
                  `${base}/dispute`,
                  { reason: disputeReason.trim() },
                  "Dispute opened.",
                )
              }
            >
              Submit Dispute
            </Btn>
          </div>
        </div>
      )}

      {/* Order chat thread */}
      {showChat && (
        <div
          className="rounded-lg border border-white/10 bg-black/30 p-3 space-y-2"
          data-testid={`order-chat-${order.id}`}
        >
          <div className="max-h-40 space-y-1.5 overflow-y-auto text-xs">
            {messages.length === 0 ? (
              <p className="text-slate-500">No messages yet. Coordinate transfer details here.</p>
            ) : (
              messages.map((m) => (
                <div key={m.id} className="rounded bg-white/[0.04] px-2.5 py-1.5">
                  <span className="font-semibold text-amber-300">{m.sender_name}: </span>
                  <span className="text-slate-200">{m.message}</span>
                </div>
              ))
            )}
          </div>
          <div className="flex gap-2">
            <input
              className="gx-input flex-1 py-1.5 text-xs"
              placeholder="Message counterparty..."
              value={chatText}
              onChange={(e) => setChatText(e.target.value)}
            />
            <Btn
              variant="secondary"
              disabled={!chatText.trim() || busy !== null}
              onClick={async () => {
                const txt = chatText.trim();
                setChatText("");
                await runAction("msg", `${base}/messages`, { message: txt }, "Message sent");
              }}
            >
              Send
            </Btn>
          </div>
        </div>
      )}

      {/* Customer rating for completed transactions */}
      {!asTrader && isCompleted && !order.my_rating && (
        <div
          className="rounded-lg border border-amber-400/25 bg-amber-500/[0.05] p-3 space-y-2"
          data-testid={`rate-order-${order.id}`}
        >
          <p className="text-xs font-semibold text-amber-200 flex items-center gap-1.5">
            <CheckCircle2 size={14} className="text-emerald-400" /> Trade Completed · Rate this
            merchant
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setRatingScore(n)}
                  className={`p-1 ${n <= ratingScore ? "text-amber-400" : "text-slate-600"}`}
                  aria-label={`Rate ${n} stars`}
                >
                  <Star size={16} fill={n <= ratingScore ? "currentColor" : "none"} />
                </button>
              ))}
            </div>
            <input
              className="gx-input flex-1 min-w-[180px] py-1 text-xs"
              placeholder="Optional feedback (speed, communication)"
              value={ratingComment}
              onChange={(e) => setRatingComment(e.target.value)}
            />
            <Btn
              variant="secondary"
              disabled={busy !== null}
              onClick={() =>
                runAction(
                  "rate",
                  `${base}/rating`,
                  { score: ratingScore, comment: ratingComment.trim() || undefined },
                  "Rating submitted. Thank you!",
                )
              }
            >
              Submit Rating
            </Btn>
          </div>
        </div>
      )}

      {!asTrader && isCompleted && order.my_rating && (
        <p className="text-xs text-amber-300 flex items-center gap-1">
          <Star size={13} fill="currentColor" /> Your rating: {order.my_rating.score}/5
          {order.my_rating.comment ? ` — "${order.my_rating.comment}"` : ""}
        </p>
      )}
    </div>
  );
}
