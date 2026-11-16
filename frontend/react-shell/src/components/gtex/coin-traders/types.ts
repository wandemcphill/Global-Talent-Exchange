export type CoinUnit = "coin" | "credit";
export type MarketSide = "sell" | "buy"; // sell = trader sells (customer buys), buy = trader buys (customer sells)
export type TradeDirection = "user_buys" | "user_sells";
export type SortByOption = "price_asc" | "price_desc" | "completion_rate" | "fastest" | "most_orders";

export const DIDIT_HANDOFF_HOSTS = new Set(["verify.didit.me", "verification.didit.me"]);

export interface CoinUnitMeta {
  unit: CoinUnit;
  code: string;
  name: string;
  minBuyerNgn: number;
}

export function coinUnitMeta(rawUnit: unknown): CoinUnitMeta {
  const normalized = String(rawUnit || "coin").toLowerCase();
  if (normalized === "credit") {
    return { unit: "credit", code: "FNC", name: "Fan Coin", minBuyerNgn: 50000 };
  }
  return { unit: "coin", code: "GTC", name: "GTEX Coin", minBuyerNgn: 200000 };
}

export function isTrustedDiditHandoffUrl(rawUrl: unknown): rawUrl is string {
  if (typeof rawUrl !== "string" || !rawUrl.trim()) return false;
  try {
    const parsed = new URL(rawUrl);
    return parsed.protocol === "https:" && DIDIT_HANDOFF_HOSTS.has(parsed.hostname.toLowerCase());
  } catch {
    return false;
  }
}

export function formatRemainingTime(expiresAt?: string | null): string | null {
  if (!expiresAt) return null;
  const diffMs = new Date(expiresAt).getTime() - Date.now();
  if (Number.isNaN(diffMs)) return null;
  if (diffMs <= 0) return "Expired";
  const totalSec = Math.floor(diffMs / 1000);
  const mins = Math.floor(totalSec / 60);
  const secs = totalSec % 60;
  return `${mins}m ${secs.toString().padStart(2, "0")}s`;
}

export interface MarketplaceOffer {
  advert_id: string;
  trader_profile_id: string;
  trader_display_name: string;
  country_code?: string | null;
  trader_tier: string;
  is_approved: boolean;
  is_didit_verified: boolean;
  verification_badge_label: string;
  verified_at?: string | null;
  is_new_merchant: boolean;
  completed_orders_count: number;
  total_orders_count: number;
  completion_rate: number;
  average_release_minutes: number;
  rating: number;
  rating_count: number;
  dispute_score: number;
  last_active_at?: string | null;
  coin_unit: CoinUnit;
  fiat_currency: string;
  side: MarketSide;
  pricing_mode: "fixed" | "floating";
  price_fiat: string | number;
  reference_rate_fiat?: string | number | null;
  price_deviation_pct?: number | null;
  savings_vs_direct_pct?: number | null;
  min_coin_amount: string | number;
  max_coin_amount: string | number;
  min_fiat_amount: string | number;
  max_fiat_amount: string | number;
  available_coin: string | number;
  daily_remaining_coin?: string | number | null;
  payment_window_minutes: number;
  payment_methods: string[];
  terms_text?: string | null;
  platform_fee_fiat: string | number;
  updated_at: string;
}

export interface MarketReferenceUnit {
  coin_unit: CoinUnit;
  name: string;
  code: string;
  direct_buy_rate_fiat: string | number;
  direct_sell_rate_fiat?: string | number | null;
  trader_wholesale_rate_fiat?: string | number | null;
  min_p2p_buy_fiat: string | number;
  min_trader_buy_rate_fiat?: string | number | null;
  max_trader_buy_rate_fiat?: string | number | null;
  min_trader_sell_rate_fiat?: string | number | null;
  max_trader_sell_rate_fiat?: string | number | null;
  max_trader_spread_fiat?: string | number | null;
  platform_fee_fiat: string | number;
}

export interface MarketplaceResponse {
  coin_unit: CoinUnit;
  side: MarketSide;
  fiat_currency: string;
  total: number;
  offers: MarketplaceOffer[];
  market_reference: MarketReferenceUnit;
}

export interface TraderAdvert {
  id: string;
  trader_profile_id: string;
  coin_unit: CoinUnit;
  fiat_currency: string;
  side: MarketSide;
  pricing_mode: "fixed" | "floating";
  price_fiat: string | number;
  effective_price_fiat: string | number;
  spread_fiat: string | number;
  reference_rate_fiat?: string | number | null;
  price_deviation_pct?: number | null;
  min_coin_amount: string | number;
  max_coin_amount: string | number;
  min_fiat_amount: string | number;
  max_fiat_amount: string | number;
  available_coin: string | number;
  daily_limit_coin?: string | number | null;
  daily_remaining_coin?: string | number | null;
  payment_window_minutes: number;
  payment_methods: string[];
  terms_text?: string | null;
  status: "draft" | "active" | "paused" | "admin_paused" | "closed";
  admin_paused_reason?: string | null;
  governance_status: string;
  governance_reasons: string[];
  updated_at: string;
}

export interface MerchantDashboardData {
  profile: any;
  balances: {
    coin_available: string | number;
    coin_reserved: string | number;
    credit_available: string | number;
    credit_reserved: string | number;
  };
  order_counts: {
    new_orders: number;
    awaiting_payment: number;
    payment_submitted: number;
    completed: number;
    cancelled: number;
    expired: number;
    disputed: number;
  };
  performance: {
    total_volume_fiat: string | number;
    completed_orders: number;
    total_orders: number;
    completion_rate: number;
    average_release_minutes: number;
    rating: number;
    rating_count: number;
    dispute_score: number;
    realised_profit_fiat?: string | number | null;
    realised_profit_note: string;
  };
  adverts: TraderAdvert[];
}

export interface TradeOrder {
  id: string;
  trader_profile_id: string;
  user_id: string;
  direction: TradeDirection;
  coin_unit: CoinUnit;
  coin_amount: string | number;
  quoted_rate_fiat: string | number;
  fiat_total: string | number;
  fiat_currency: string;
  status: string;
  escrow_owner_user_id?: string | null;
  payment_method?: string | null;
  advert_id?: string | null;
  payment_window_minutes?: number | null;
  quote_expires_at?: string | null;
  fee_coin?: string | number;
  fee_fiat?: string | number;
  payment_window_expires_at?: string | null;
  accepted_at?: string | null;
  proof_submitted_at?: string | null;
  released_at?: string | null;
  cancelled_at?: string | null;
  disputed_at?: string | null;
  proof?: Record<string, any>;
  terms_snapshot?: Record<string, any>;
  ledger_refs?: Record<string, any>;
  messages?: Array<{
    id: string;
    order_id: string;
    sender_user_id: string;
    sender_name: string;
    message: string;
    created_at: string;
  }>;
  counterparty_payment_details?: Array<Record<string, any>>;
  customer_payout_details?: Record<string, any> | null;
  trader_display_name?: string | null;
  customer_display_name?: string | null;
  my_rating?: { id: string; score: number; comment?: string | null; created_at: string } | null;
  metadata_json?: Record<string, any>;
}
