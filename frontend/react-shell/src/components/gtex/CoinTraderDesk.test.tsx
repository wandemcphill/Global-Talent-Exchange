declare const describe: any;
declare const it: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CoinTraderDesk } from "./CoinTraderDesk";

let mockUser: any = {
  id: "user-1",
  username: "buyer1",
  display_name: "Buyer One",
  account_type: "user",
};

const mockToastSuccess = jest.fn();
const mockToastError = jest.fn();
const mockRefreshOwner = jest.fn();
const mockApiGet = jest.fn();
const mockApiPost = jest.fn();
const mockApiPut = jest.fn();
const mockApiPatch = jest.fn();

jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...rest }: any) => (
    <a href={String(to || "#")} {...rest}>
      {children}
    </a>
  ),
}));

jest.mock("@/lib/auth", () => ({
  useAuth: () => ({ user: mockUser }),
}));

jest.mock("@/lib/owner", () => ({
  fmt: (v: any, decimals = 0) =>
    Number(v || 0).toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }),
  label: (s: any) => String(s || "").replace(/_/g, " "),
  useRefreshOwner: () => mockRefreshOwner,
}));

jest.mock("sonner", () => ({
  toast: {
    success: (...args: any[]) => mockToastSuccess(...args),
    error: (...args: any[]) => mockToastError(...args),
  },
}));

jest.mock("@/lib/api", () => ({
  errMsg: (e: any) => e?.response?.data?.detail || e?.message || "error",
  api: {
    get: (...args: any[]) => mockApiGet(...args),
    post: (...args: any[]) => mockApiPost(...args),
    put: (...args: any[]) => mockApiPut(...args),
    patch: (...args: any[]) => mockApiPatch(...args),
  },
}));

const mockedApi = {
  get: mockApiGet,
  post: mockApiPost,
  put: mockApiPut,
  patch: mockApiPatch,
};

async function flush() {
  for (let i = 0; i < 6; i++) {
    await act(async () => {
      await Promise.resolve();
      await new Promise((r) => setTimeout(r, 0));
    });
  }
}

function setInputValue(el: HTMLInputElement | HTMLSelectElement, value: string) {
  const proto = el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
  setter?.call(el, value);
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
}

describe("CoinTraderDesk", () => {
  let container: HTMLDivElement;
  let root: Root;
  let originalOpen: any;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    originalOpen = window.open;
    window.open = jest.fn();
    mockToastSuccess.mockReset();
    mockToastError.mockReset();
    mockedApi.get.mockReset();
    mockedApi.post.mockReset();
    mockedApi.put.mockReset();
    mockedApi.patch.mockReset();
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
    window.open = originalOpen;
  });

  const renderDesk = async () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    await act(async () => {
      root.render(
        <QueryClientProvider client={qc}>
          <CoinTraderDesk />
        </QueryClientProvider>
      );
    });
    await flush();
  };

  it("renders truthful empty state with Become a Coin Trader CTA when zero active offers exist", async () => {
    mockUser = { id: "buyer-0", username: "buyer0", display_name: "Buyer Zero", account_type: "user" };
    mockedApi.get.mockImplementation(async (url: string) => {
      if (url === "/coin-traders/marketplace") {
        return {
          data: {
            coin_unit: "coin",
            side: "sell",
            fiat_currency: "NGN",
            total: 0,
            offers: [],
            market_reference: {
              coin_unit: "coin",
              name: "GTEX Coin",
              code: "GTC",
              direct_buy_rate_fiat: "60",
              direct_sell_rate_fiat: "48",
              min_p2p_buy_fiat: "200000",
              platform_fee_fiat: "0",
            },
          },
        };
      }
      return { data: [] };
    });

    await renderDesk();

    const empty = container.querySelector('[data-testid="marketplace-empty-state"]');
    expect(empty).not.toBeNull();
    expect(empty?.textContent).toContain("No active GTEX Coin offers right now");
    expect(empty?.textContent).toContain("Become a Coin Trader");
  });

  it("initiates DIDit verification with verification_type and trusted handoff_url only", async () => {
    mockUser = {
      id: "trader-user-1",
      username: "lagos_desk",
      display_name: "Lagos Desk",
      account_type: "coin_trader",
    };

    mockedApi.get.mockImplementation(async (url: string) => {
      if (url === "/coin-traders") return { data: [] };
      if (url === "/coin-traders/orders") return { data: [] };
      if (url === "/coin-traders/me") {
        return {
          data: {
            id: "prof-1",
            user_id: "trader-user-1",
            display_name: "Lagos Desk",
            status: "applied",
            verified_at: null,
            rates: [],
          },
        };
      }
      if (url === "/coin-traders/verification/status") {
        return {
          data: {
            provider: "didit",
            provider_reference: "gtex-ref-1",
            status: "pending",
            decision: "Not Started",
          },
        };
      }
      return { data: [] };
    });

    mockedApi.post.mockImplementation(async (url: string) => {
      if (url === "/coin-traders/verification/initiate") {
        return {
          data: {
            provider: "didit",
            verification_type: "bvn_nin",
            provider_session_id: "didit-sess-123",
            provider_reference: "gtex-ref-123",
            handoff_url: "https://verify.didit.me/session/didit-sess-123",
            status: "pending",
          },
        };
      }
      return { data: {} };
    });

    await renderDesk();

    const kycCard = container.querySelector('[data-testid="trader-kyc-card"]');
    expect(kycCard).not.toBeNull();
    expect(kycCard?.textContent).not.toContain("Sandbox");

    const select = container.querySelector('[data-testid="trader-kyc-type-select"]') as HTMLSelectElement;
    await act(async () => {
      setInputValue(select, "bvn_nin");
    });

    const btn = container.querySelector('[data-testid="initiate-trader-kyc-btn"]') as HTMLButtonElement;
    await act(async () => {
      btn.click();
    });
    await flush();

    expect(mockedApi.post).toHaveBeenCalledWith("/coin-traders/verification/initiate", {
      provider: "didit",
      verification_type: "bvn_nin",
      callback_url: `${window.location.origin}/trader/verification/callback`,
    });
    expect(window.open).toHaveBeenCalledWith(
      "https://verify.didit.me/session/didit-sess-123",
      "_blank",
      "noopener,noreferrer"
    );
    const link = container.querySelector('[data-testid="trader-kyc-handoff-link"]') as HTMLAnchorElement;
    expect(link?.getAttribute("href")).toBe("https://verify.didit.me/session/didit-sess-123");
  });

  it("enforces NGN 200,000 GTC / NGN 50,000 FNC buyer minimums in Trade Modal and places advert orders", async () => {
    mockUser = { id: "buyer-1", username: "buyer1", display_name: "Buyer One", account_type: "user" };

    const makeMarket = (unit: "coin" | "credit") => ({
      coin_unit: unit,
      side: "sell",
      fiat_currency: "NGN",
      total: 1,
      offers: [
        {
          advert_id: `adv-${unit}`,
          trader_profile_id: "prof-dual",
          trader_display_name: "Dual Coin Partners",
          trader_tier: "gold",
          is_approved: true,
          is_didit_verified: true,
          verification_badge_label: "ID Verified",
          is_new_merchant: false,
          completed_orders_count: 14,
          total_orders_count: 14,
          completion_rate: 100,
          average_release_minutes: 4,
          rating: 4.9,
          rating_count: 12,
          dispute_score: 0,
          coin_unit: unit,
          fiat_currency: "NGN",
          side: "sell",
          pricing_mode: "fixed",
          price_fiat: unit === "coin" ? "55" : "3.2",
          reference_rate_fiat: unit === "coin" ? "60" : "4",
          price_deviation_pct: -8.3,
          savings_vs_direct_pct: 8.3,
          min_coin_amount: "1",
          max_coin_amount: "100000",
          min_fiat_amount: unit === "coin" ? "200000" : "50000",
          max_fiat_amount: "3000000",
          available_coin: "50000",
          payment_window_minutes: 15,
          payment_methods: ["Bank Transfer", "OPay"],
          terms_text: "Same-name transfer only.",
          platform_fee_fiat: "0",
          updated_at: "2026-11-16T10:00:00Z",
        },
      ],
      market_reference: {
        coin_unit: unit,
        name: unit === "coin" ? "GTEX Coin" : "Fan Coin",
        code: unit === "coin" ? "GTC" : "FNC",
        direct_buy_rate_fiat: unit === "coin" ? "60" : "4",
        direct_sell_rate_fiat: unit === "coin" ? "48" : null,
        min_p2p_buy_fiat: unit === "coin" ? "200000" : "50000",
        platform_fee_fiat: "0",
      },
    });

    mockedApi.get.mockImplementation(async (url: string, cfg?: any) => {
      if (url === "/coin-traders/marketplace") {
        const u = cfg?.params?.coin_unit === "credit" ? "credit" : "coin";
        return { data: makeMarket(u) };
      }
      if (url === "/coin-traders/orders") return { data: [] };
      return { data: [] };
    });
    mockedApi.post.mockResolvedValue({ data: { id: "ord-new" } });

    await renderDesk();

    // Open GTC trade modal
    await act(async () => {
      (container.querySelector('[data-testid="select-offer-adv-coin"]') as HTMLButtonElement).click();
    });
    await flush();

    // Enter 100,000 NGN (< 200,000 minimum)
    await act(async () => {
      setInputValue(container.querySelector('[data-testid="modal-amount-input"]') as HTMLInputElement, "100000");
    });
    expect(container.querySelector('[data-testid="modal-validation-warning"]')?.textContent).toContain("200,000");
    expect((container.querySelector('[data-testid="modal-submit-order"]') as HTMLButtonElement).disabled).toBe(true);

    // Close and switch to Fan Coin (credit)
    await act(async () => {
      (container.querySelector('[aria-label="Close"]') as HTMLButtonElement).click();
    });
    await act(async () => {
      (container.querySelector('[data-testid="coin-unit-credit"]') as HTMLButtonElement).click();
    });
    await flush();

    await act(async () => {
      (container.querySelector('[data-testid="select-offer-adv-credit"]') as HTMLButtonElement).click();
    });
    await flush();

    await act(async () => {
      setInputValue(container.querySelector('[data-testid="modal-amount-input"]') as HTMLInputElement, "40000");
    });
    expect(container.querySelector('[data-testid="modal-validation-warning"]')?.textContent).toContain("50,000");

    await act(async () => {
      setInputValue(container.querySelector('[data-testid="modal-amount-input"]') as HTMLInputElement, "64000");
    });
    const submitBtn = container.querySelector('[data-testid="modal-submit-order"]') as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(false);

    await act(async () => {
      submitBtn.click();
    });
    await flush();

    expect(mockedApi.post).toHaveBeenCalledWith(
      "/coin-traders/orders",
      expect.objectContaining({
        trader_profile_id: "prof-dual",
        advert_id: "adv-credit",
        direction: "user_buys",
        coin_unit: "credit",
        coin_amount: 20000,
        fiat_currency: "NGN",
      })
    );
  });

  it("displays separated balances and publishes Fan Coin adverts from Merchant Dashboard", async () => {
    mockUser = {
      id: "trader-user-2",
      username: "verified_desk",
      display_name: "Verified Desk",
      account_type: "coin_trader",
    };

    mockedApi.get.mockImplementation(async (url: string) => {
      if (url === "/coin-traders/me") {
        return {
          data: {
            id: "prof-2",
            user_id: "trader-user-2",
            display_name: "Verified Desk",
            tier: "gold",
            status: "approved",
            verified_at: "2026-11-15T10:00:00Z",
            is_didit_verified: true,
            verification_provider: "didit",
            verification_badge_label: "ID Verified",
            payment_methods: [{ label: "Bank Transfer", type: "bank_transfer" }],
            bank_accounts: [{ bank_name: "GTBank", account_number: "0123456789", account_name: "Verified Desk" }],
          },
        };
      }
      if (url === "/coin-traders/me/dashboard") {
        return {
          data: {
            profile: { id: "prof-2", display_name: "Verified Desk", tier: "gold", status: "approved" },
            balances: {
              coin_available: "12000",
              coin_reserved: "3000",
              credit_available: "50000",
              credit_reserved: "0",
            },
            order_counts: {
              new_orders: 1,
              awaiting_payment: 0,
              payment_submitted: 0,
              completed: 4,
              cancelled: 0,
              expired: 0,
              disputed: 0,
            },
            performance: {
              total_volume_fiat: "1250000",
              completed_orders: 4,
              total_orders: 4,
              completion_rate: 100,
              average_release_minutes: 5,
              rating: 0,
              rating_count: 0,
              dispute_score: 0,
              realised_profit_fiat: null,
              realised_profit_note: "Insufficient matched cycles",
            },
            adverts: [],
          },
        };
      }
      return { data: [] };
    });

    mockedApi.put.mockResolvedValue({ data: { id: "adv-1" } });

    await renderDesk();

    const overview = container.querySelector('[data-testid="merchant-overview-panel"]');
    expect(overview?.textContent).toContain("12,000.00 GTC");
    expect(overview?.textContent).toContain("3,000.00 GTC");
    expect(overview?.textContent).toContain("No ratings yet");

    // Switch to Adverts tab and publish
    await act(async () => {
      (container.querySelector('[data-testid="merchant-tab-adverts"]') as HTMLButtonElement).click();
    });
    await flush();

    await act(async () => {
      (container.querySelector('[data-testid="advert-publish-btn"]') as HTMLButtonElement).click();
    });
    await flush();

    expect(mockedApi.put).toHaveBeenCalledWith(
      "/coin-traders/me/adverts",
      expect.objectContaining({
        coin_unit: "coin",
        side: "sell",
        status: "active",
      })
    );
  });
});
