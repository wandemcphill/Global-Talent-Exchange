import React, { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Award,
  BarChart3,
  CreditCard,
  Megaphone,
  Pause,
  Play,
  Plus,
  ShieldCheck,
  Trash2,
  Wallet,
} from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { fmt, label } from "@/lib/owner";
import { Btn, Chip } from "@/components/gtex/ui";
import { CoinTraderOrderRoom } from "./CoinTraderOrderRoom";
import {
  coinUnitMeta,
  type CoinUnit,
  type MarketSide,
  type MerchantDashboardData,
  type TradeOrder,
  type TraderAdvert,
} from "./types";

type DashTab = "overview" | "adverts" | "orders" | "inventory" | "payments" | "performance";

const PAYMENT_OPTIONS = ["Bank Transfer", "OPay", "PalmPay", "Kuda", "Moniepoint"];

interface Props {
  profile: any;
  deskOrders: TradeOrder[];
}

export function CoinTraderMerchantDashboard({ profile, deskOrders }: Props) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<DashTab>("overview");
  const [orderFilter, setOrderFilter] = useState<string>("all");

  const { data: dash } = useQuery<MerchantDashboardData | null>({
    queryKey: ["coin-trader-dashboard"],
    queryFn: async () => {
      try {
        const res = await api.get("/coin-traders/me/dashboard");
        return res?.data ?? null;
      } catch {
        return null;
      }
    },
  });

  const balances = dash?.balances || {
    coin_available: 0,
    coin_reserved: 0,
    credit_available: 0,
    credit_reserved: 0,
  };
  const counts = dash?.order_counts || {
    new_orders: deskOrders.filter((o) => o.status === "created").length,
    awaiting_payment: deskOrders.filter((o) => o.status === "payment_pending").length,
    payment_submitted: deskOrders.filter((o) => o.status === "proof_submitted").length,
    completed: deskOrders.filter((o) => ["released", "admin_released"].includes(o.status)).length,
    cancelled: deskOrders.filter((o) =>
      ["cancelled", "refunded", "admin_refunded"].includes(o.status),
    ).length,
    expired: deskOrders.filter((o) => o.status === "expired").length,
    disputed: deskOrders.filter((o) => o.status === "disputed").length,
  };
  const perf = dash?.performance || {
    total_volume_fiat: profile?.completed_volume_fiat || 0,
    completed_orders: profile?.completed_orders_count || 0,
    total_orders: profile?.total_orders_count || deskOrders.length,
    completion_rate: profile?.completion_rate || 0,
    average_release_minutes: profile?.average_release_minutes || 0,
    rating: profile?.rating || 0,
    rating_count: profile?.rating_count || 0,
    dispute_score: profile?.dispute_score || 0,
    realised_profit_fiat: null,
    realised_profit_note: "Insufficient matched buy/sell cycles yet.",
  };
  const adverts = dash?.adverts || [];

  const filteredOrders = useMemo(() => {
    if (orderFilter === "all") return deskOrders;
    if (orderFilter === "new") return deskOrders.filter((o) => o.status === "created");
    if (orderFilter === "active")
      return deskOrders.filter((o) => ["payment_pending", "proof_submitted"].includes(o.status));
    if (orderFilter === "completed")
      return deskOrders.filter((o) => ["released", "admin_released"].includes(o.status));
    if (orderFilter === "cancelled")
      return deskOrders.filter((o) =>
        ["cancelled", "refunded", "admin_refunded", "expired"].includes(o.status),
      );
    if (orderFilter === "disputed") return deskOrders.filter((o) => o.status === "disputed");
    return deskOrders;
  }, [deskOrders, orderFilter]);

  const invalidateAll = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["coin-trader-dashboard"] }),
      qc.invalidateQueries({ queryKey: ["coin-trader-me"] }),
      qc.invalidateQueries({ queryKey: ["coin-trader-marketplace"] }),
      qc.invalidateQueries({ queryKey: ["coin-traders"] }),
    ]);
  };

  const tabs: Array<{ id: DashTab; label: string; icon: React.ReactNode }> = [
    { id: "overview", label: "Overview", icon: <BarChart3 size={14} /> },
    { id: "adverts", label: `Adverts (${adverts.length})`, icon: <Megaphone size={14} /> },
    { id: "orders", label: `Orders (${deskOrders.length})`, icon: <ShieldCheck size={14} /> },
    { id: "inventory", label: "Inventory & Wallet", icon: <Wallet size={14} /> },
    { id: "payments", label: "Payment Methods", icon: <CreditCard size={14} /> },
    { id: "performance", label: "Performance", icon: <Award size={14} /> },
  ];

  return (
    <div
      className="space-y-4 rounded-2xl border border-amber-400/20 bg-[#0A0E17] p-5"
      data-testid="merchant-dashboard"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="gx-label text-amber-300">Merchant Business Desk</p>
          <h3 className="gx-display text-xl font-black text-white">
            {profile.display_name} · <span className="capitalize">{profile.tier}</span>
          </h3>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Chip tone={profile.is_didit_verified ? "emerald" : "gold"}>
            {profile.verification_badge_label ||
              (profile.verified_at ? "Approved by GTEX" : "Pending")}
          </Chip>
          <Chip tone={profile.status === "approved" ? "emerald" : "red"}>
            {label(profile.status)}
          </Chip>
        </div>
      </div>

      {/* Sub-navigation */}
      <div className="flex flex-wrap gap-2 border-b border-white/10 pb-3">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            data-testid={`merchant-tab-${t.id}`}
            onClick={() => setTab(t.id)}
            className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
              tab === t.id
                ? "bg-amber-400 text-black shadow"
                : "border border-white/10 bg-white/[0.03] text-slate-300 hover:bg-white/10"
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* A. OVERVIEW */}
      {tab === "overview" && (
        <div className="space-y-4" data-testid="merchant-overview-panel">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="GTEX Coin Available"
              value={`${fmt(balances.coin_available, 2)} GTC`}
              accent="text-emerald-400"
            />
            <StatCard
              label="GTEX Coin Reserved (Escrow)"
              value={`${fmt(balances.coin_reserved, 2)} GTC`}
              accent="text-amber-300"
            />
            <StatCard
              label="Fan Coin Available"
              value={`${fmt(balances.credit_available, 2)} FNC`}
              accent="text-emerald-400"
            />
            <StatCard
              label="Fan Coin Reserved (Escrow)"
              value={`${fmt(balances.credit_reserved, 2)} FNC`}
              accent="text-amber-300"
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Total Volume" value={`₦${fmt(perf.total_volume_fiat, 2)}`} />
            <StatCard
              label="Completed Orders"
              value={`${perf.completed_orders}`}
              sub={`${perf.completion_rate.toFixed(1)}% completion`}
            />
            <StatCard
              label="Customer Rating"
              value={perf.rating_count > 0 ? `${perf.rating.toFixed(1)} / 5` : "No ratings yet"}
              sub={
                perf.rating_count > 0
                  ? `${perf.rating_count} verified reviews`
                  : "Earns after completed orders"
              }
            />
            <StatCard
              label="Realised P2P Profit"
              value={
                perf.realised_profit_fiat !== null && perf.realised_profit_fiat !== undefined
                  ? `₦${fmt(perf.realised_profit_fiat, 2)}`
                  : "N/A"
              }
              sub={perf.realised_profit_note}
            />
          </div>

          <div className="grid gap-2 grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 rounded-xl border border-white/10 bg-white/[0.02] p-3 text-center text-xs">
            <PipelineStat label="New" count={counts.new_orders} />
            <PipelineStat label="Awaiting Pay" count={counts.awaiting_payment} />
            <PipelineStat label="Proof Sent" count={counts.payment_submitted} />
            <PipelineStat label="Completed" count={counts.completed} tone="text-emerald-400" />
            <PipelineStat label="Cancelled" count={counts.cancelled} />
            <PipelineStat label="Expired" count={counts.expired} />
            <PipelineStat label="Disputed" count={counts.disputed} tone="text-rose-400" />
          </div>
        </div>
      )}

      {/* B. ADVERT MANAGEMENT */}
      {tab === "adverts" && (
        <AdvertManagerSection
          adverts={adverts}
          balances={balances}
          profilePaymentMethods={profile.payment_methods || []}
          onChanged={invalidateAll}
        />
      )}

      {/* C. ORDER MANAGEMENT */}
      {tab === "orders" && (
        <div className="space-y-3" data-testid="merchant-orders-panel">
          <div className="flex flex-wrap gap-2">
            {[
              ["all", "All"],
              ["new", `New (${counts.new_orders})`],
              ["active", `Active (${counts.awaiting_payment + counts.payment_submitted})`],
              ["disputed", `Disputed (${counts.disputed})`],
              ["completed", `Completed (${counts.completed})`],
              ["cancelled", `Cancelled/Expired (${counts.cancelled + counts.expired})`],
            ].map(([k, lbl]) => (
              <button
                key={k}
                type="button"
                onClick={() => setOrderFilter(k)}
                className={`rounded-lg px-3 py-1 text-xs font-semibold ${
                  orderFilter === k ? "bg-white/15 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                {lbl}
              </button>
            ))}
          </div>
          {filteredOrders.length === 0 ? (
            <p className="text-sm text-slate-500">No client orders in this view.</p>
          ) : (
            <div className="space-y-2" data-testid="trader-desk-orders">
              {filteredOrders.map((o) => (
                <CoinTraderOrderRoom key={o.id} order={o} asTrader />
              ))}
            </div>
          )}
        </div>
      )}

      {/* D. INVENTORY & WALLET */}
      {tab === "inventory" && (
        <div className="space-y-4" data-testid="merchant-inventory-panel">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="GTEX Coin Available"
              value={`${fmt(balances.coin_available, 4)} GTC`}
              accent="text-emerald-400"
            />
            <StatCard
              label="GTEX Coin Reserved"
              value={`${fmt(balances.coin_reserved, 4)} GTC`}
              accent="text-amber-300"
            />
            <StatCard
              label="Fan Coin Available"
              value={`${fmt(balances.credit_available, 4)} FNC`}
              accent="text-emerald-400"
            />
            <StatCard
              label="Fan Coin Reserved"
              value={`${fmt(balances.credit_reserved, 4)} FNC`}
              accent="text-amber-300"
            />
          </div>
          <TraderLiquidityPurchase onPurchased={invalidateAll} />
        </div>
      )}

      {/* E. PAYMENT METHODS & BANK ACCOUNTS */}
      {tab === "payments" && <PaymentMethodsManager profile={profile} onSaved={invalidateAll} />}

      {/* F. PERFORMANCE */}
      {tab === "performance" && (
        <div className="space-y-4" data-testid="merchant-performance-panel">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Completion Rate" value={`${perf.completion_rate.toFixed(1)}%`} />
            <StatCard
              label="Avg Release Time"
              value={
                perf.average_release_minutes > 0
                  ? `${Math.round(perf.average_release_minutes)} mins`
                  : "N/A"
              }
            />
            <StatCard label="Dispute Rate" value={`${perf.dispute_score.toFixed(1)}%`} />
            <StatCard
              label="Account Standing"
              value={label(profile.status)}
              sub={`Tier: ${label(profile.tier)}`}
            />
          </div>
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-xs text-slate-300 space-y-1.5">
            <p className="font-bold text-white">How to rank higher on GTEX P2P</p>
            <p>
              1. Complete DIDit identity verification so customers see the "ID Verified" shield
              badge and your offers appear under "ID Verified Only".
            </p>
            <p>
              2. Keep competitive Naira rates below the direct platform buy price (₦60/GTC, ₦4/FNC)
              and accept incoming orders quickly.
            </p>
            <p>
              3. Release escrowed coins promptly after confirming Naira receipt to improve your
              average release time and 5-star customer rating.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label: title, value, sub, accent = "text-white" }: any) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5">
      <p className="text-[11px] uppercase tracking-wider text-slate-400">{title}</p>
      <p className={`mt-1 text-lg font-black ${accent}`}>{value}</p>
      {sub && <p className="mt-0.5 text-[11px] text-slate-400">{sub}</p>}
    </div>
  );
}

function PipelineStat({ label: title, count, tone = "text-white" }: any) {
  return (
    <div>
      <p className="text-[11px] text-slate-400">{title}</p>
      <p className={`text-base font-bold ${tone}`}>{count}</p>
    </div>
  );
}

function AdvertManagerSection({ adverts, balances, profilePaymentMethods, onChanged }: any) {
  const [coinUnit, setCoinUnit] = useState<CoinUnit>("coin");
  const [side, setSide] = useState<MarketSide>("sell");
  const [pricingMode, setPricingMode] = useState<"fixed" | "floating">("fixed");
  const [priceFiat, setPriceFiat] = useState("56");
  const [spreadFiat, setSpreadFiat] = useState("-4");
  const [minCoin, setMinCoin] = useState("4000");
  const [maxCoin, setMaxCoin] = useState("50000");
  const [dailyLimit, setDailyLimit] = useState("");
  const [windowMins, setWindowMins] = useState("15");
  const [selectedMethods, setSelectedMethods] = useState<string[]>(["Bank Transfer"]);
  const [termsText, setTermsText] = useState("");
  const [saving, setSaving] = useState(false);

  const unitInfo = coinUnitMeta(coinUnit);
  const availWallet =
    coinUnit === "coin"
      ? Number(balances.coin_available || 0)
      : Number(balances.credit_available || 0);

  const loadIntoForm = (ad: TraderAdvert) => {
    setCoinUnit(ad.coin_unit);
    setSide(ad.side);
    setPricingMode(ad.pricing_mode);
    setPriceFiat(String(ad.price_fiat));
    setSpreadFiat(String(ad.spread_fiat));
    setMinCoin(String(ad.min_coin_amount));
    setMaxCoin(String(ad.max_coin_amount));
    setDailyLimit(ad.daily_limit_coin ? String(ad.daily_limit_coin) : "");
    setWindowMins(String(ad.payment_window_minutes));
    setSelectedMethods(ad.payment_methods.length ? ad.payment_methods : ["Bank Transfer"]);
    setTermsText(ad.terms_text || "");
  };

  const toggleMethod = (m: string) => {
    setSelectedMethods((curr) => (curr.includes(m) ? curr.filter((x) => x !== m) : [...curr, m]));
  };

  const publishAdvert = async (statusValue: "active" | "draft") => {
    setSaving(true);
    try {
      await api.put("/coin-traders/me/adverts", {
        coin_unit: coinUnit,
        fiat_currency: "NGN",
        side,
        pricing_mode: pricingMode,
        price_fiat: Number(priceFiat) || (coinUnit === "coin" ? 56 : 3.2),
        spread_fiat: Number(spreadFiat) || 0,
        min_coin_amount: Number(minCoin) || 0,
        max_coin_amount: Number(maxCoin) || 0,
        daily_limit_coin: Number(dailyLimit) > 0 ? Number(dailyLimit) : null,
        payment_window_minutes: Number(windowMins) || 15,
        payment_methods: selectedMethods.length ? selectedMethods : ["Bank Transfer"],
        terms_text: termsText.trim() || null,
        status: statusValue,
      });
      toast.success(`Advert saved (${statusValue}).`);
      await onChanged();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setSaving(false);
    }
  };

  const setStatus = async (advertId: string, nextStatus: "active" | "paused" | "closed") => {
    try {
      await api.patch(`/coin-traders/me/adverts/${advertId}/status`, { status: nextStatus });
      toast.success(`Advert ${nextStatus}.`);
      await onChanged();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const availableMethodChoices = Array.from(
    new Set([
      ...PAYMENT_OPTIONS,
      ...profilePaymentMethods
        .map((m: any) => (typeof m === "string" ? m : m?.label || m?.name || m?.type))
        .filter(Boolean),
    ]),
  );

  return (
    <div className="space-y-4" data-testid="merchant-adverts-panel">
      {/* Existing adverts list */}
      {adverts.length > 0 && (
        <div className="space-y-2">
          <p className="gx-label text-slate-300">Your Adverts</p>
          {adverts.map((ad: TraderAdvert) => {
            const meta = coinUnitMeta(ad.coin_unit);
            return (
              <div
                key={ad.id}
                data-testid={`merchant-advert-${ad.id}`}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.02] p-3 text-xs"
              >
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Chip tone={ad.side === "sell" ? "emerald" : "gold"}>
                      {ad.side === "sell" ? `Sell ${meta.code}` : `Buy ${meta.code}`}
                    </Chip>
                    <b className="text-sm text-white">₦{fmt(ad.effective_price_fiat, 2)}</b>
                    <span className="text-slate-400">({ad.pricing_mode})</span>
                    <Chip
                      tone={
                        ad.status === "active"
                          ? "emerald"
                          : ad.status === "admin_paused"
                            ? "red"
                            : "slate"
                      }
                    >
                      {label(ad.status)}
                    </Chip>
                  </div>
                  <p className="text-slate-400">
                    Limits: {fmt(ad.min_coin_amount)} – {fmt(ad.max_coin_amount) || "Open"}{" "}
                    {meta.code} · Available:{" "}
                    <b className="text-white">
                      {fmt(ad.available_coin)} {meta.code}
                    </b>{" "}
                    · Window: {ad.payment_window_minutes}m · Methods:{" "}
                    {ad.payment_methods.join(", ") || "—"}
                  </p>
                  {ad.admin_paused_reason && (
                    <p className="text-rose-300">Admin pause reason: {ad.admin_paused_reason}</p>
                  )}
                </div>

                <div className="flex flex-wrap gap-2">
                  <Btn variant="secondary" onClick={() => loadIntoForm(ad)}>
                    Edit
                  </Btn>
                  {ad.status === "active" && (
                    <Btn
                      variant="ghost"
                      onClick={() => setStatus(ad.id, "paused")}
                      data-testid={`pause-advert-${ad.id}`}
                    >
                      <Pause size={13} /> Pause
                    </Btn>
                  )}
                  {(ad.status === "paused" || ad.status === "draft") && (
                    <Btn
                      onClick={() => setStatus(ad.id, "active")}
                      data-testid={`resume-advert-${ad.id}`}
                    >
                      <Play size={13} /> Resume
                    </Btn>
                  )}
                  {ad.status !== "closed" && (
                    <Btn variant="danger" onClick={() => setStatus(ad.id, "closed")}>
                      Close
                    </Btn>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create / Update advert form */}
      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="gx-label text-amber-300">Create or Edit Advert</p>
            <p className="text-xs text-slate-400">
              Wallet available for {unitInfo.code}:{" "}
              <b className="text-white">
                {fmt(availWallet, 2)} {unitInfo.code}
              </b>
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {(["coin", "credit"] as const).map((u) => (
              <button
                key={u}
                type="button"
                onClick={() => {
                  setCoinUnit(u);
                  setPriceFiat(
                    u === "coin"
                      ? side === "sell"
                        ? "56"
                        : "49"
                      : side === "sell"
                        ? "3.2"
                        : "2.5",
                  );
                  setMinCoin(u === "coin" ? "4000" : "20000");
                }}
                className={`gx-btn py-1 px-3 text-xs ${coinUnit === u ? "gx-btn-primary" : "gx-btn-secondary"}`}
              >
                {coinUnitMeta(u).name} ({coinUnitMeta(u).code})
              </button>
            ))}
            {(["sell", "buy"] as const).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => {
                  setSide(s);
                  setPriceFiat(
                    coinUnit === "coin"
                      ? s === "sell"
                        ? "56"
                        : "49"
                      : s === "sell"
                        ? "3.2"
                        : "2.5",
                  );
                }}
                className={`gx-btn py-1 px-3 text-xs ${side === s ? "gx-btn-primary" : "gx-btn-secondary"}`}
              >
                {s === "sell"
                  ? `Sell ${unitInfo.code} (to buyers)`
                  : `Buy ${unitInfo.code} (from sellers)`}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4">
          <label className="block">
            <span className="gx-label">Pricing Mode</span>
            <select
              className="gx-input mt-1 text-xs"
              value={pricingMode}
              onChange={(e) => setPricingMode(e.target.value as any)}
            >
              <option value="fixed">Fixed Price (NGN)</option>
              <option value="floating">Floating (Reference ± Spread)</option>
            </select>
          </label>
          {pricingMode === "fixed" ? (
            <label className="block">
              <span className="gx-label">Price (₦ / {unitInfo.code})</span>
              <input
                className="gx-input mt-1 text-xs"
                type="number"
                step="0.01"
                value={priceFiat}
                onChange={(e) => setPriceFiat(e.target.value)}
              />
            </label>
          ) : (
            <label className="block">
              <span className="gx-label">Spread vs Reference (₦)</span>
              <input
                className="gx-input mt-1 text-xs"
                type="number"
                step="0.01"
                value={spreadFiat}
                onChange={(e) => setSpreadFiat(e.target.value)}
              />
            </label>
          )}
          <label className="block">
            <span className="gx-label">Min Order ({unitInfo.code})</span>
            <input
              className="gx-input mt-1 text-xs"
              type="number"
              value={minCoin}
              onChange={(e) => setMinCoin(e.target.value)}
            />
          </label>
          <label className="block">
            <span className="gx-label">Max Order ({unitInfo.code})</span>
            <input
              className="gx-input mt-1 text-xs"
              type="number"
              value={maxCoin}
              onChange={(e) => setMaxCoin(e.target.value)}
            />
          </label>
          <label className="block">
            <span className="gx-label">Daily Limit ({unitInfo.code}, optional)</span>
            <input
              className="gx-input mt-1 text-xs"
              type="number"
              placeholder="No daily cap"
              value={dailyLimit}
              onChange={(e) => setDailyLimit(e.target.value)}
            />
          </label>
          <label className="block">
            <span className="gx-label">Payment Window (mins)</span>
            <input
              className="gx-input mt-1 text-xs"
              type="number"
              min={5}
              max={120}
              value={windowMins}
              onChange={(e) => setWindowMins(e.target.value)}
            />
          </label>
          <label className="block sm:col-span-2">
            <span className="gx-label">Merchant Terms</span>
            <input
              className="gx-input mt-1 text-xs"
              placeholder="e.g. Same-name transfers only, upload receipt"
              value={termsText}
              onChange={(e) => setTermsText(e.target.value)}
            />
          </label>
        </div>

        <div className="space-y-1.5">
          <span className="gx-label">Accepted Payment Methods</span>
          <div className="flex flex-wrap gap-2">
            {availableMethodChoices.map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => toggleMethod(m)}
                className={`rounded-lg px-2.5 py-1 text-xs border ${
                  selectedMethods.includes(m)
                    ? "border-emerald-400/50 bg-emerald-500/15 text-emerald-200"
                    : "border-white/10 bg-white/[0.02] text-slate-400"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap gap-2 pt-1">
          <Btn
            disabled={saving}
            onClick={() => publishAdvert("active")}
            data-testid="advert-publish-btn"
          >
            {saving ? "Saving..." : "Publish Active Advert"}
          </Btn>
          <Btn variant="secondary" disabled={saving} onClick={() => publishAdvert("draft")}>
            Save as Draft
          </Btn>
        </div>
      </div>
    </div>
  );
}

function PaymentMethodsManager({
  profile,
  onSaved,
}: {
  profile: any;
  onSaved: () => Promise<void>;
}) {
  const [bankAccounts, setBankAccounts] = useState<
    Array<{ bank_name: string; account_number: string; account_name: string }>
  >(() =>
    (profile.bank_accounts || []).map((b: any) => ({
      bank_name: b.bank_name || b.bank || "",
      account_number: b.account_number || "",
      account_name: b.account_name || "",
    })),
  );
  const [methods, setMethods] = useState<string[]>(() =>
    (profile.payment_methods || [])
      .map((m: any) => (typeof m === "string" ? m : m?.label || m?.name || m?.type))
      .filter(Boolean),
  );
  const [newBank, setNewBank] = useState({ bank_name: "", account_number: "", account_name: "" });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setBankAccounts(
      (profile.bank_accounts || []).map((b: any) => ({
        bank_name: b.bank_name || b.bank || "",
        account_number: b.account_number || "",
        account_name: b.account_name || "",
      })),
    );
  }, [profile]);

  const addBank = () => {
    if (
      !newBank.bank_name.trim() ||
      newBank.account_number.trim().length < 6 ||
      !newBank.account_name.trim()
    ) {
      toast.error("Enter bank name, valid account number, and account name.");
      return;
    }
    setBankAccounts((curr) => [...curr, { ...newBank }]);
    if (!methods.includes(newBank.bank_name.trim()) && !methods.includes("Bank Transfer")) {
      setMethods((m) => [...m, "Bank Transfer"]);
    }
    setNewBank({ bank_name: "", account_number: "", account_name: "" });
  };

  const saveProfilePayments = async () => {
    setSaving(true);
    try {
      await api.put("/coin-traders/me", {
        payment_methods: methods.map((m) => ({
          label: m,
          type: m.toLowerCase().replace(/\s+/g, "_"),
        })),
        bank_accounts: bankAccounts,
      });
      toast.success("Merchant payment methods & receiving accounts updated.");
      await onSaved();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4" data-testid="merchant-payments-panel">
      <div className="rounded-xl border border-sky-400/25 bg-sky-500/[0.05] p-3 text-xs text-sky-200">
        Your bank account numbers are <b>never shown publicly</b> on marketplace adverts. They are
        revealed only to a customer inside an active accepted order.
      </div>

      <div className="space-y-2">
        <p className="gx-label text-slate-300">Receiving Bank Accounts</p>
        {bankAccounts.length === 0 ? (
          <p className="text-xs text-slate-500">No receiving bank accounts saved yet.</p>
        ) : (
          bankAccounts.map((b, i) => (
            <div
              key={i}
              className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-xs"
            >
              <span className="gx-mono text-white">
                {b.bank_name} · {b.account_number} · {b.account_name}
              </span>
              <button
                type="button"
                onClick={() => setBankAccounts((curr) => curr.filter((_, idx) => idx !== i))}
                className="text-rose-400 hover:text-rose-300"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))
        )}

        <div className="grid gap-2 sm:grid-cols-4 pt-1">
          <input
            className="gx-input text-xs"
            placeholder="Bank (e.g. GTBank, OPay)"
            value={newBank.bank_name}
            onChange={(e) => setNewBank({ ...newBank, bank_name: e.target.value })}
          />
          <input
            className="gx-input text-xs"
            placeholder="Account Number"
            value={newBank.account_number}
            onChange={(e) => setNewBank({ ...newBank, account_number: e.target.value })}
          />
          <input
            className="gx-input text-xs"
            placeholder="Account Name"
            value={newBank.account_name}
            onChange={(e) => setNewBank({ ...newBank, account_name: e.target.value })}
          />
          <Btn variant="secondary" onClick={addBank}>
            <Plus size={14} /> Add Account
          </Btn>
        </div>
      </div>

      <div className="space-y-2">
        <p className="gx-label text-slate-300">Default Accepted Payment Methods</p>
        <div className="flex flex-wrap gap-2">
          {PAYMENT_OPTIONS.map((m) => (
            <button
              key={m}
              type="button"
              onClick={() =>
                setMethods((curr) =>
                  curr.includes(m) ? curr.filter((x) => x !== m) : [...curr, m],
                )
              }
              className={`rounded-lg px-3 py-1 text-xs border ${
                methods.includes(m)
                  ? "border-emerald-400/50 bg-emerald-500/15 text-emerald-200"
                  : "border-white/10 bg-white/[0.02] text-slate-400"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      <Btn disabled={saving} onClick={saveProfilePayments} data-testid="save-merchant-payments">
        {saving ? "Saving..." : "Save Payment Settings"}
      </Btn>
    </div>
  );
}

export function TraderLiquidityPurchase({ onPurchased }: { onPurchased?: () => void }) {
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
        qc.invalidateQueries({ queryKey: ["coin-trader-dashboard"] });
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
    <div
      className="rounded-xl border border-white/10 bg-white/[0.02] p-4"
      data-testid="trader-liquidity-purchase-panel"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h4 className="gx-label text-slate-300">Acquire Wholesale Trading Inventory</h4>
          <p className="mt-1 text-xs text-slate-400">
            Buy GTEX Coin (₦50/GTC, ₦200,000 minimum) or Fan Coin (₦2.50/FNC, ₦50,000 minimum)
            inventory to back sell adverts.
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
                if (unit === "credit" && amount === "4000") setAmount("20000");
                else if (unit === "coin" && amount === "20000") setAmount("4000");
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
            <div
              className="mb-2 text-xs text-slate-400 flex flex-wrap gap-x-4"
              data-testid="trader-liquidity-quote"
            >
              <span>
                Fiat: <b className="text-white">₦{fmt(quote.amount_fiat)}</b>
              </span>
              <span>
                Platform fee:{" "}
                <b className="text-white">
                  {fmt(quote.fee_amount)} {unitInfo.code}
                </b>
              </span>
              <span>
                Processor fee:{" "}
                <b className="text-white">
                  {fmt(quote.processor_fee)} {unitInfo.code}
                </b>
              </span>
              <span>
                Net:{" "}
                <b className="text-emerald-400">
                  {fmt(quote.net_amount)} {unitInfo.code}
                </b>
              </span>
            </div>
          )}
          {belowMinimum && (
            <p
              className="mb-2 text-xs text-amber-300"
              data-testid="trader-liquidity-minimum-warning"
            >
              Minimum purchase is ₦{fmt(unitInfo.minBuyerNgn)} for {unitInfo.name}.
            </p>
          )}
          <Btn
            disabled={
              submitting || quoteLoading || !Number(amount) || Number(amount) <= 0 || belowMinimum
            }
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
