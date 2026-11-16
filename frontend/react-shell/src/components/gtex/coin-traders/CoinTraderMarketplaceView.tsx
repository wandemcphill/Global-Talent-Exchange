import React, { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Clock, Filter, ShieldCheck, Star, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { fmt } from "@/lib/owner";
import { Btn, Chip } from "@/components/gtex/ui";
import { CoinTraderTradeModal } from "./CoinTraderTradeModal";
import {
  coinUnitMeta,
  type CoinUnit,
  type MarketSide,
  type MarketplaceOffer,
  type MarketplaceResponse,
  type SortByOption,
} from "./types";

interface Props {
  isDedicatedTraderAccount?: boolean;
  onOrderCreated?: () => void;
}

export function CoinTraderMarketplaceView({
  isDedicatedTraderAccount = false,
  onOrderCreated,
}: Props) {
  const [coinUnit, setCoinUnit] = useState<CoinUnit>("coin");
  const [side, setSide] = useState<MarketSide>("sell"); // sell = trader sells -> customer buys
  const [fiatAmount, setFiatAmount] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("");
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [minCompletionRate, setMinCompletionRate] = useState("");
  const [minAvailableCoin, setMinAvailableCoin] = useState("");
  const [sortBy, setSortBy] = useState<SortByOption>("price_asc");
  const [selectedOffer, setSelectedOffer] = useState<MarketplaceOffer | null>(null);
  const [showMoreFilters, setShowMoreFilters] = useState(false);

  const unitInfo = coinUnitMeta(coinUnit);

  const switchSide = (nextSide: MarketSide) => {
    setSide(nextSide);
    if (nextSide === "sell" && sortBy === "price_desc") setSortBy("price_asc");
    if (nextSide === "buy" && sortBy === "price_asc") setSortBy("price_desc");
  };

  const params = useMemo(() => {
    const p: Record<string, any> = {
      coin_unit: coinUnit,
      side,
      fiat_currency: "NGN",
      sort_by: sortBy,
    };
    if (Number(fiatAmount) > 0) p.fiat_amount = Number(fiatAmount);
    if (paymentMethod.trim()) p.payment_method = paymentMethod.trim();
    if (verifiedOnly) p.verified_only = true;
    if (Number(minCompletionRate) > 0) p.min_completion_rate = Number(minCompletionRate);
    if (Number(minAvailableCoin) > 0) p.min_available_coin = Number(minAvailableCoin);
    return p;
  }, [
    coinUnit,
    side,
    sortBy,
    fiatAmount,
    paymentMethod,
    verifiedOnly,
    minCompletionRate,
    minAvailableCoin,
  ]);

  const { data: market, isLoading } = useQuery<MarketplaceResponse | null>({
    queryKey: ["coin-trader-marketplace", params],
    queryFn: async () => {
      try {
        const res = await api.get("/coin-traders/marketplace", { params });
        return res?.data ?? null;
      } catch {
        return null;
      }
    },
  });

  const offers = market?.offers || [];
  const refInfo = market?.market_reference;
  const hasFilters = Boolean(
    fiatAmount || paymentMethod || verifiedOnly || minCompletionRate || minAvailableCoin,
  );

  const clearFilters = () => {
    setFiatAmount("");
    setPaymentMethod("");
    setVerifiedOnly(false);
    setMinCompletionRate("");
    setMinAvailableCoin("");
  };

  const sortOptions: Array<{ id: SortByOption; label: string }> = [
    {
      id: side === "sell" ? "price_asc" : "price_desc",
      label: side === "sell" ? "Lowest Price" : "Highest Price",
    },
    { id: "most_orders", label: "Completed Orders" },
    { id: "completion_rate", label: "Completion Rate" },
    { id: "fastest", label: "Fastest Release" },
  ];

  return (
    <div className="space-y-4" data-testid="coin-trader-marketplace">
      {/* Top 4-Market Switcher: Buy/Sell + GTEX Coin / Fan Coin */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/10 bg-[#0B1018] p-3.5">
        <div className="flex flex-wrap items-center gap-3">
          {/* Buy / Sell Segmented Pill */}
          <div
            className="inline-flex rounded-xl bg-black/50 p-1 border border-white/10"
            role="tablist"
          >
            <button
              type="button"
              data-testid="market-side-buy"
              onClick={() => switchSide("sell")}
              className={`rounded-lg px-4 py-1.5 text-xs font-bold uppercase tracking-wider transition ${
                side === "sell"
                  ? "bg-emerald-500 text-black shadow"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Buy
            </button>
            <button
              type="button"
              data-testid="market-side-sell"
              onClick={() => switchSide("buy")}
              className={`rounded-lg px-4 py-1.5 text-xs font-bold uppercase tracking-wider transition ${
                side === "buy" ? "bg-rose-500 text-white shadow" : "text-slate-400 hover:text-white"
              }`}
            >
              Sell
            </button>
          </div>

          {/* Asset Switcher: GTEX Coin / Fan Coin */}
          <div className="flex flex-wrap gap-2">
            {(["coin", "credit"] as const).map((unit) => {
              const meta = coinUnitMeta(unit);
              return (
                <button
                  key={unit}
                  type="button"
                  data-testid={`coin-unit-${unit}`}
                  onClick={() => setCoinUnit(unit)}
                  className={`gx-btn py-1.5 px-3 text-xs ${
                    coinUnit === unit ? "gx-btn-primary" : "gx-btn-secondary"
                  }`}
                >
                  {meta.name} ({meta.code})
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-300">
          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/25 bg-emerald-500/10 px-2.5 py-1 text-emerald-300">
            <ShieldCheck size={13} /> Canonical Escrow · ₦0 P2P Fee
          </span>
        </div>
      </div>

      {/* Reference Rate & Value Proposition Banner */}
      {refInfo && (
        <div
          className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-400/20 bg-amber-500/[0.04] px-4 py-2.5 text-xs text-slate-300"
          data-testid="market-reference-banner"
        >
          <div>
            <b className="text-amber-300">
              {refInfo.name} ({refInfo.code}) Market Reference:
            </b>{" "}
            Direct platform buy{" "}
            <b className="text-white">₦{fmt(refInfo.direct_buy_rate_fiat, 2)}</b>
            {refInfo.direct_sell_rate_fiat ? (
              <>
                {" · "}Direct withdrawal{" "}
                <b className="text-white">₦{fmt(refInfo.direct_sell_rate_fiat, 2)}</b>
              </>
            ) : null}
            {" · "}Min P2P buy order <b className="text-white">₦{fmt(refInfo.min_p2p_buy_fiat)}</b>
          </div>
          <span className="text-emerald-300 font-semibold">
            {side === "sell"
              ? "Verified traders price below direct platform purchase"
              : "Compare merchant buying rates before locking escrow"}
          </span>
        </div>
      )}

      {/* Filter & Sort Toolbar */}
      <div className="space-y-3 rounded-xl border border-white/10 bg-white/[0.02] p-3">
        <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-5">
          <input
            data-testid="filter-fiat-amount"
            className="gx-input text-xs"
            type="number"
            min="0"
            placeholder={`NGN Amount (min ₦${fmt(unitInfo.minBuyerNgn)})`}
            value={fiatAmount}
            onChange={(e) => setFiatAmount(e.target.value)}
          />
          <select
            data-testid="filter-payment-method"
            className="gx-input text-xs"
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
          >
            <option value="">All Payment Methods</option>
            <option value="Bank Transfer">Bank Transfer</option>
            <option value="OPay">OPay</option>
            <option value="PalmPay">PalmPay</option>
            <option value="Kuda">Kuda</option>
          </select>
          <button
            type="button"
            data-testid="filter-verified-only"
            onClick={() => setVerifiedOnly((v) => !v)}
            className={`gx-btn justify-center text-xs ${verifiedOnly ? "gx-btn-primary" : "gx-btn-secondary"}`}
          >
            <ShieldCheck size={14} /> {verifiedOnly ? "ID Verified Only: ON" : "ID Verified Only"}
          </button>
          <button
            type="button"
            onClick={() => setShowMoreFilters((v) => !v)}
            className="gx-btn gx-btn-secondary justify-center text-xs"
          >
            <Filter size={14} /> More Filters
          </button>
          {hasFilters ? (
            <button
              type="button"
              onClick={clearFilters}
              className="gx-btn gx-btn-ghost justify-center text-xs"
            >
              Reset Filters
            </button>
          ) : (
            <div className="flex items-center justify-end text-xs text-slate-400">
              {offers.length} active {offers.length === 1 ? "offer" : "offers"}
            </div>
          )}
        </div>

        {showMoreFilters && (
          <div className="grid gap-2 border-t border-white/10 pt-2 sm:grid-cols-2 md:grid-cols-4">
            <select
              className="gx-input text-xs"
              value={minCompletionRate}
              onChange={(e) => setMinCompletionRate(e.target.value)}
            >
              <option value="">Any completion rate</option>
              <option value="90">90%+ completion</option>
              <option value="95">95%+ completion</option>
              <option value="98">98%+ completion</option>
            </select>
            <input
              className="gx-input text-xs"
              type="number"
              min="0"
              placeholder={`Min available ${unitInfo.code}`}
              value={minAvailableCoin}
              onChange={(e) => setMinAvailableCoin(e.target.value)}
            />
          </div>
        )}

        {/* Sort Pills */}
        <div className="flex flex-wrap items-center gap-2 border-t border-white/10 pt-2">
          <span className="text-[11px] uppercase tracking-wider text-slate-400 mr-1">Sort by:</span>
          {sortOptions.map((opt) => (
            <button
              key={opt.id}
              type="button"
              data-testid={`sort-${opt.id}`}
              onClick={() => setSortBy(opt.id)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                sortBy === opt.id
                  ? "bg-white/15 text-white border border-white/25"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Offer List or Truthful Empty State */}
      {isLoading ? (
        <div className="rounded-xl border border-white/10 p-6 text-center text-sm text-slate-400">
          Loading {unitInfo.name} offers...
        </div>
      ) : offers.length === 0 ? (
        <div
          className="rounded-2xl border border-white/10 bg-[#0B1018] p-8 text-center space-y-3"
          data-testid="marketplace-empty-state"
        >
          <p className="gx-eyebrow text-amber-300">
            {side === "sell" ? `Buy ${unitInfo.name}` : `Sell ${unitInfo.name}`} · NGN
          </p>
          <h3 className="gx-display text-xl font-black text-white">
            {hasFilters
              ? "No offers match your current filters"
              : `No active ${unitInfo.name} offers right now`}
          </h3>
          <p className="mx-auto max-w-xl text-sm leading-6 text-slate-400">
            {hasFilters
              ? "Adjust your NGN amount, payment method, or verification filter to view available merchants."
              : "GTEX never displays synthetic traders or fabricated quotes. Real offers appear here automatically as verified Coin Traders publish active adverts."}
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            {hasFilters && (
              <Btn variant="secondary" onClick={clearFilters}>
                Clear Filters
              </Btn>
            )}
            {!isDedicatedTraderAccount && (
              <Link
                to="/auth?role=coin_trader"
                className="gx-btn gx-btn-primary inline-flex items-center gap-1.5"
              >
                Become a Coin Trader <ArrowRight size={14} />
              </Link>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-3" data-testid="marketplace-offers-list">
          {offers.map((offer) => {
            const isFast =
              offer.completed_orders_count >= 3 &&
              offer.average_release_minutes > 0 &&
              offer.average_release_minutes <= 10;
            return (
              <div
                key={offer.advert_id}
                data-testid={`marketplace-offer-${offer.advert_id}`}
                className="rounded-2xl border border-white/10 bg-[#0B1018] p-4 transition hover:border-amber-400/35 space-y-3"
              >
                {/* Merchant row */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="flex size-7 items-center justify-center rounded-full bg-amber-400/20 text-xs font-black text-amber-300">
                      {offer.trader_display_name.slice(0, 1).toUpperCase()}
                    </span>
                    <span className="font-bold text-white">{offer.trader_display_name}</span>
                    <Chip tone={offer.is_didit_verified ? "emerald" : "gold"}>
                      {offer.verification_badge_label}
                    </Chip>
                    {offer.is_new_merchant && <Chip tone="slate">New Merchant</Chip>}
                    {isFast && (
                      <span className="inline-flex items-center gap-1 rounded bg-emerald-500/15 px-2 py-0.5 text-[11px] font-semibold text-emerald-300">
                        <Zap size={11} /> Fast release
                      </span>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-300">
                    <span>
                      {offer.completed_orders_count} Orders
                      {offer.total_orders_count > 0
                        ? ` (${offer.completion_rate.toFixed(1)}%)`
                        : ""}
                    </span>
                    <span className="inline-flex items-center gap-1 text-amber-300">
                      <Star size={12} fill={offer.rating_count > 0 ? "currentColor" : "none"} />
                      {offer.rating_count > 0
                        ? `${offer.rating.toFixed(1)} (${offer.rating_count})`
                        : "No ratings yet"}
                    </span>
                  </div>
                </div>

                {/* Price + Limits + CTA */}
                <div className="flex flex-wrap items-end justify-between gap-4">
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-baseline gap-2.5">
                      <span className="text-2xl font-black text-white">
                        ₦{fmt(offer.price_fiat, 2)}
                      </span>
                      <span className="text-xs text-slate-400">/ {unitInfo.code}</span>
                      {offer.savings_vs_direct_pct !== null &&
                        offer.savings_vs_direct_pct !== undefined &&
                        offer.savings_vs_direct_pct > 0 && (
                          <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-[11px] font-semibold text-emerald-300">
                            {side === "sell"
                              ? `Save ${offer.savings_vs_direct_pct.toFixed(1)}% vs direct`
                              : `+${offer.savings_vs_direct_pct.toFixed(1)}% vs direct withdrawal`}
                          </span>
                        )}
                    </div>

                    <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-400">
                      <span>
                        Limits:{" "}
                        <b className="text-slate-200">
                          ₦{fmt(offer.min_fiat_amount)} –{" "}
                          {Number(offer.max_fiat_amount) > 0
                            ? `₦${fmt(offer.max_fiat_amount)}`
                            : "Open"}
                        </b>
                      </span>
                      <span>
                        {side === "sell" ? "Available" : "Capacity"}:{" "}
                        <b className="text-slate-200">
                          {fmt(offer.available_coin)} {unitInfo.code}
                        </b>
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <Clock size={12} /> {offer.payment_window_minutes}m window
                        {offer.average_release_minutes > 0
                          ? ` · ~${Math.round(offer.average_release_minutes)}m avg`
                          : ""}
                      </span>
                    </div>

                    {/* Payment method pills */}
                    <div className="flex flex-wrap items-center gap-2 pt-0.5">
                      {(offer.payment_methods.length > 0
                        ? offer.payment_methods
                        : ["Bank Transfer"]
                      ).map((pm, idx) => (
                        <span
                          key={pm}
                          className="inline-flex items-center gap-1.5 rounded bg-white/[0.04] px-2 py-0.5 text-[11px] text-slate-300"
                        >
                          <span
                            className={`h-2.5 w-0.5 rounded ${idx % 2 === 0 ? "bg-amber-400" : "bg-emerald-400"}`}
                          />
                          {pm}
                        </span>
                      ))}
                      {offer.terms_text && (
                        <span className="text-[11px] text-slate-500 truncate max-w-xs">
                          · {offer.terms_text}
                        </span>
                      )}
                    </div>
                  </div>

                  <button
                    type="button"
                    data-testid={`select-offer-${offer.advert_id}`}
                    onClick={() => setSelectedOffer(offer)}
                    className={`rounded-xl px-5 py-2.5 text-sm font-bold shadow transition ${
                      side === "sell"
                        ? "bg-emerald-500 text-black hover:bg-emerald-400"
                        : "bg-rose-500 text-white hover:bg-rose-400"
                    }`}
                  >
                    {side === "sell" ? `Buy ${unitInfo.code}` : `Sell ${unitInfo.code}`}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {selectedOffer && (
        <CoinTraderTradeModal
          offer={selectedOffer}
          onClose={() => setSelectedOffer(null)}
          onOrderCreated={onOrderCreated}
        />
      )}
    </div>
  );
}
