import React, { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Clock, ShieldCheck, Star, X } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { fmt, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip } from "@/components/gtex/ui";
import { coinUnitMeta, type MarketplaceOffer } from "./types";

interface Props {
  offer: MarketplaceOffer;
  onClose: () => void;
  onOrderCreated?: () => void;
}

export function CoinTraderTradeModal({ offer, onClose, onOrderCreated }: Props) {
  const qc = useQueryClient();
  const refresh = useRefreshOwner();
  const unitInfo = coinUnitMeta(offer.coin_unit);
  const isUserBuying = offer.side === "sell";
  const price = Number(offer.price_fiat);
  const minFiat = Number(offer.min_fiat_amount || 0);
  const maxFiat = Number(offer.max_fiat_amount || 0);
  const availableCoin = Number(offer.available_coin || 0);

  const [inputMode, setInputMode] = useState<"fiat" | "coin">("fiat");
  const [fiatInput, setFiatInput] = useState(() => {
    const start = isUserBuying ? Math.max(minFiat, unitInfo.minBuyerNgn) : Math.max(minFiat, Math.round(1000 * price));
    return String(Math.round(start));
  });
  const [coinInput, setCoinInput] = useState(() => {
    const startFiat = isUserBuying ? Math.max(minFiat, unitInfo.minBuyerNgn) : Math.max(minFiat, Math.round(1000 * price));
    return price > 0 ? String(Math.ceil(startFiat / price)) : "0";
  });
  const [paymentMethod, setPaymentMethod] = useState(offer.payment_methods[0] || "Bank Transfer");
  const [bankName, setBankName] = useState("");
  const [accountNumber, setAccountNumber] = useState("");
  const [accountName, setAccountName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [quoteSecs, setQuoteSecs] = useState(60);

  useEffect(() => {
    const t = setInterval(() => setQuoteSecs((s) => (s > 0 ? s - 1 : 0)), 1000);
    return () => clearInterval(t);
  }, []);

  const handleFiatChange = (val: string) => {
    setInputMode("fiat");
    setFiatInput(val);
    const num = Number(val);
    if (Number.isFinite(num) && num > 0 && price > 0) {
      setCoinInput((num / price).toFixed(4).replace(/\.?0+$/, ""));
    } else {
      setCoinInput("0");
    }
  };

  const handleCoinChange = (val: string) => {
    setInputMode("coin");
    setCoinInput(val);
    const num = Number(val);
    if (Number.isFinite(num) && num > 0 && price > 0) {
      setFiatInput((num * price).toFixed(2).replace(/\.?0+$/, ""));
    } else {
      setFiatInput("0");
    }
  };

  const coinNum = Number(coinInput || 0);
  const fiatNum = Number(fiatInput || 0);
  const belowMinBuyer = isUserBuying && fiatNum < unitInfo.minBuyerNgn;
  const belowAdvertMin = Number(offer.min_coin_amount) > 0 && coinNum < Number(offer.min_coin_amount);
  const aboveAdvertMax = Number(offer.max_coin_amount) > 0 && coinNum > Number(offer.max_coin_amount);
  const aboveLiquidity = isUserBuying && coinNum > availableCoin;
  const missingSellBank =
    !isUserBuying && (!bankName.trim() || accountNumber.trim().length < 6 || !accountName.trim());

  const validationMessage = belowMinBuyer
    ? `Minimum ${unitInfo.name} buyer order is ₦${fmt(unitInfo.minBuyerNgn)}.`
    : belowAdvertMin
      ? `Minimum order for this advert is ${fmt(offer.min_coin_amount)} ${unitInfo.code}.`
      : aboveAdvertMax
        ? `Exceeds advert maximum of ${fmt(offer.max_coin_amount)} ${unitInfo.code}.`
        : aboveLiquidity
          ? `Exceeds merchant's live available inventory (${fmt(availableCoin)} ${unitInfo.code}).`
          : missingSellBank
            ? "Enter your receiving Naira bank account details so the merchant can pay you."
            : null;

  const deviationPct = offer.price_deviation_pct;
  const showDeviationWarning = deviationPct !== null && deviationPct !== undefined && Math.abs(deviationPct) >= 3;

  const submitOrder = async () => {
    if (validationMessage || coinNum <= 0) {
      toast.error(validationMessage || "Enter a valid trade amount.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/coin-traders/orders", {
        trader_profile_id: offer.trader_profile_id,
        advert_id: offer.advert_id,
        direction: isUserBuying ? "user_buys" : "user_sells",
        coin_unit: offer.coin_unit,
        coin_amount: Number(coinNum.toFixed(4)),
        fiat_currency: offer.fiat_currency,
        expected_rate_fiat: price,
        payment_method: paymentMethod,
        ...(isUserBuying
          ? {}
          : {
              customer_payout_details: {
                bank_name: bankName.trim(),
                account_number: accountNumber.trim(),
                account_name: accountName.trim(),
              },
            }),
        idempotency_key: `web-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      });
      toast.success("Order placed and coins locked in GTEX escrow.");
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["coin-orders"] }),
        qc.invalidateQueries({ queryKey: ["coin-trader-marketplace"] }),
      ]);
      refresh();
      if (onOrderCreated) onOrderCreated();
      onClose();
    } catch (e: any) {
      toast.error(errMsg(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm"
      data-testid="coin-trade-modal"
    >
      <div className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-white/15 bg-[#0C1018] p-5 text-sm shadow-2xl space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="gx-label text-amber-300">{isUserBuying ? "Buy from Coin Trader" : "Sell to Coin Trader"}</p>
            <h3 className="gx-display text-xl font-black text-white">
              {isUserBuying ? "Buy" : "Sell"} {unitInfo.name} ({unitInfo.code})
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/30 bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-300">
              <ShieldCheck size={13} /> Escrow Protected
            </span>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Price + quote timer */}
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3.5 py-2.5">
          <div className="flex items-baseline gap-2">
            <span className="text-xs text-slate-400">{isUserBuying ? "Selling Rate" : "Buying Rate"}</span>
            <span className={`text-lg font-bold ${isUserBuying ? "text-emerald-400" : "text-rose-400"}`}>
              ₦{fmt(price, 2)} / {unitInfo.code}
            </span>
          </div>
          <span className="inline-flex items-center gap-1 text-xs text-slate-400">
            <Clock size={12} /> {quoteSecs > 0 ? `Quote valid ${quoteSecs}s` : "Rate verified on submit"}
          </span>
        </div>

        {showDeviationWarning && (
          <div className="flex items-start gap-2 rounded-xl border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
            <AlertTriangle size={15} className="shrink-0 mt-0.5" />
            <span>
              This price is {Math.abs(deviationPct!).toFixed(2)}% {deviationPct! > 0 ? "higher" : "lower"} than the GTEX reference rate
              {offer.reference_rate_fiat ? ` (₦${fmt(offer.reference_rate_fiat, 2)})` : ""}.
            </span>
          </div>
        )}

        {/* Dual amount input box */}
        <div className="rounded-xl border border-white/10 bg-black/40 p-4 space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setInputMode("fiat")}
                className={inputMode === "fiat" ? "border-b-2 border-amber-400 pb-1 font-semibold text-white" : "pb-1"}
              >
                By Naira (NGN)
              </button>
              <button
                type="button"
                onClick={() => setInputMode("coin")}
                className={inputMode === "coin" ? "border-b-2 border-amber-400 pb-1 font-semibold text-white" : "pb-1"}
              >
                By {unitInfo.code} Quantity
              </button>
            </div>
            <span className="inline-flex items-center gap-1">
              <Clock size={12} /> {offer.payment_window_minutes}m pay window
            </span>
          </div>

          <div className="flex items-center gap-2 rounded-xl border border-white/15 bg-[#121723] px-3 py-2.5">
            <input
              data-testid="modal-amount-input"
              type="number"
              min="0"
              step="any"
              className="w-full bg-transparent text-2xl font-bold text-white outline-none"
              value={inputMode === "fiat" ? fiatInput : coinInput}
              onChange={(e) => (inputMode === "fiat" ? handleFiatChange(e.target.value) : handleCoinChange(e.target.value))}
            />
            <span className="text-xs font-bold text-slate-300">{inputMode === "fiat" ? "NGN" : unitInfo.code}</span>
            {maxFiat > 0 && (
              <button
                type="button"
                onClick={() =>
                  inputMode === "fiat"
                    ? handleFiatChange(String(Math.floor(maxFiat)))
                    : handleCoinChange(String(Math.min(Number(offer.max_coin_amount || availableCoin), availableCoin)))
                }
                className="text-xs font-bold text-amber-400 hover:text-amber-300 pl-2 border-l border-white/15"
              >
                Max
              </button>
            )}
          </div>

          <div className="flex flex-wrap justify-between gap-2 text-xs text-slate-400">
            <span>
              Limits: <b className="text-slate-200">₦{fmt(minFiat)} – {maxFiat > 0 ? `₦${fmt(maxFiat)}` : "Open"}</b>
            </span>
            <span>
              {isUserBuying ? "Available" : "Merchant Cap"}:{" "}
              <b className="text-slate-200">{fmt(availableCoin)} {unitInfo.code}</b>
            </span>
          </div>

          <div className="rounded-lg bg-white/[0.04] px-3 py-2 text-xs flex flex-wrap justify-between gap-2">
            <span className="text-slate-300">
              {isUserBuying ? "You pay" : "You sell"}:{" "}
              <b className="text-white">
                {isUserBuying ? `₦${fmt(fiatNum, 2)}` : `${fmt(coinNum, 4)} ${unitInfo.code}`}
              </b>
            </span>
            <span className="text-slate-300">
              {isUserBuying ? "You receive" : "You receive"}:{" "}
              <b className="text-emerald-400">
                {isUserBuying ? `${fmt(coinNum, 4)} ${unitInfo.code}` : `₦${fmt(fiatNum, 2)}`}
              </b>
            </span>
            <span className="text-slate-400">Fee: <b className="text-white">₦0</b></span>
          </div>
        </div>

        {/* Payment method */}
        <div className="space-y-2">
          <label className="gx-label">Payment method</label>
          <select
            className="gx-input"
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
            data-testid="modal-payment-method"
          >
            {(offer.payment_methods.length > 0 ? offer.payment_methods : ["Bank Transfer"]).map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        {/* Customer payout details when selling coins */}
        {!isUserBuying && (
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3 space-y-2">
            <p className="gx-label text-amber-300">Your Naira Payout Account (shared only with this merchant)</p>
            <div className="grid gap-2 sm:grid-cols-3">
              <input
                className="gx-input text-xs"
                placeholder="Bank (e.g. GTBank, OPay)"
                value={bankName}
                onChange={(e) => setBankName(e.target.value)}
                data-testid="sell-payout-bank"
              />
              <input
                className="gx-input text-xs"
                placeholder="Account Number"
                value={accountNumber}
                onChange={(e) => setAccountNumber(e.target.value)}
                data-testid="sell-payout-number"
              />
              <input
                className="gx-input text-xs"
                placeholder="Account Name"
                value={accountName}
                onChange={(e) => setAccountName(e.target.value)}
                data-testid="sell-payout-name"
              />
            </div>
          </div>
        )}

        {/* Merchant identity & terms */}
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="font-bold text-white">{offer.trader_display_name}</span>
              <Chip tone={offer.is_didit_verified ? "emerald" : "gold"}>{offer.verification_badge_label}</Chip>
              {offer.is_new_merchant && <Chip tone="slate">New Merchant</Chip>}
            </div>
            <div className="text-xs text-slate-300 flex items-center gap-1">
              <Star size={13} className="text-amber-400" fill={offer.rating_count > 0 ? "currentColor" : "none"} />
              {offer.rating_count > 0 ? `${offer.rating.toFixed(1)} (${offer.rating_count})` : "No ratings yet"}
            </div>
          </div>
          <p className="text-xs text-slate-400">
            {offer.completed_orders_count} Completed Orders ·{" "}
            {offer.total_orders_count > 0 ? `${offer.completion_rate.toFixed(1)}% Completion` : "First trades in progress"}
            {offer.average_release_minutes > 0 ? ` · ~${Math.round(offer.average_release_minutes)}m avg release` : ""}
          </p>
          <div className="border-t border-white/10 pt-2 text-xs text-slate-400 space-y-1">
            <p className="font-semibold text-slate-300">Advertiser Terms & Escrow Rules</p>
            <p className="text-[11px] leading-5">
              Coins are escrowed in the canonical GTEX ledger upon order creation. Never release or pay outside this order room.
            </p>
            {offer.terms_text && <p className="text-slate-200">{offer.terms_text}</p>}
          </div>
        </div>

        {validationMessage && (
          <p className="text-xs text-amber-300 flex items-center gap-1.5" data-testid="modal-validation-warning">
            <AlertTriangle size={14} /> {validationMessage}
          </p>
        )}

        {/* Footer CTA */}
        <div className="flex items-center justify-between gap-3 pt-1">
          <div>
            <p className="text-lg font-black text-white">
              {isUserBuying ? `₦${fmt(fiatNum, 2)}` : `${fmt(coinNum, 4)} ${unitInfo.code}`}
            </p>
            <p className="text-[11px] text-slate-400">Total Payable</p>
          </div>
          <Btn
            disabled={submitting || Boolean(validationMessage) || coinNum <= 0}
            onClick={submitOrder}
            data-testid="modal-submit-order"
          >
            {submitting
              ? "Locking Escrow..."
              : isUserBuying
                ? `Buy ${unitInfo.code}`
                : `Sell ${unitInfo.code}`}
          </Btn>
        </div>
      </div>
    </div>
  );
}
