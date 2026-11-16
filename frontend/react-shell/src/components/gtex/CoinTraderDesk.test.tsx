declare const describe: any;
declare const it: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CoinTraderDesk, ClubCoinTraderFundingPanel } from "./CoinTraderDesk";
import { api } from "@/lib/api";

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
  },
}));

const mockedApi = {
  get: mockApiGet,
  post: mockApiPost,
  put: mockApiPut,
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
      if (url === "/coin-traders/me/orders") return { data: [] };
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
    expect(kycCard?.textContent).not.toContain("Smile ID");

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

  it("enforces NGN 200,000 GTC and NGN 50,000 FNC buyer minimums and submits dual-unit orders", async () => {
    mockUser = {
      id: "buyer-1",
      username: "buyer1",
      display_name: "Buyer One",
      account_type: "user",
    };

    const dualTrader = {
      id: "prof-dual",
      user_id: "u-dual",
      display_name: "Dual Coin Partners",
      tier: "gold",
      status: "approved",
      verified_at: "2026-11-15T10:00:00Z",
      rates: [
        {
          id: "r-coin",
          coin_unit: "coin",
          fiat_currency: "NGN",
          buy_rate_fiat: "950",
          sell_rate_fiat: "1000",
          min_coin_amount: "1",
          max_coin_amount: "100000",
          available_liquidity: "50000",
          is_active: true,
        },
        {
          id: "r-credit",
          coin_unit: "credit",
          fiat_currency: "NGN",
          buy_rate_fiat: "950",
          sell_rate_fiat: "1000",
          min_coin_amount: "1",
          max_coin_amount: "100000",
          available_liquidity: "50000",
          is_active: true,
        },
      ],
    };

    mockedApi.get.mockImplementation(async (url: string) => {
      if (url === "/coin-traders") return { data: [dualTrader] };
      if (url === "/coin-traders/orders") return { data: [] };
      return { data: null };
    });
    mockedApi.post.mockResolvedValue({ data: { id: "ord-new" } });

    await renderDesk();

    // Select trader and enter 100 GTC (100,000 NGN < 200,000 NGN)
    await act(async () => {
      setInputValue(container.querySelector('[data-testid="coin-trader-select"]') as HTMLSelectElement, "prof-dual");
      setInputValue(container.querySelector('[data-testid="coin-amount-input"]') as HTMLInputElement, "100");
    });

    const warning = container.querySelector('[data-testid="min-buyer-order-warning"]');
    expect(warning?.textContent).toContain("200,000");
    const submitBtn = container.querySelector('[data-testid="coin-order-submit"]') as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(true);

    // Switch to Fan Coin (credit) where 100 FNC = 100,000 NGN >= 50,000 NGN
    await act(async () => {
      (container.querySelector('[data-testid="coin-unit-credit"]') as HTMLButtonElement).click();
    });
    await act(async () => {
      setInputValue(container.querySelector('[data-testid="coin-trader-select"]') as HTMLSelectElement, "prof-dual");
      setInputValue(container.querySelector('[data-testid="coin-amount-input"]') as HTMLInputElement, "40");
    });
    expect(container.querySelector('[data-testid="min-buyer-order-warning"]')?.textContent).toContain("50,000");

    await act(async () => {
      setInputValue(container.querySelector('[data-testid="coin-amount-input"]') as HTMLInputElement, "60");
    });
    const enabledSubmit = container.querySelector('[data-testid="coin-order-submit"]') as HTMLButtonElement;
    expect(enabledSubmit.disabled).toBe(false);
    await act(async () => {
      enabledSubmit.click();
    });
    await flush();

    expect(mockedApi.post).toHaveBeenCalledWith(
      "/coin-traders/orders",
      expect.objectContaining({
        trader_profile_id: "prof-dual",
        direction: "user_buys",
        coin_unit: "credit",
        coin_amount: 60,
        fiat_currency: "NGN",
      })
    );
  });

  it("allows verified coin traders to publish Fan Coin rates and buy credit liquidity", async () => {
    mockUser = {
      id: "trader-user-2",
      username: "verified_desk",
      display_name: "Verified Desk",
      account_type: "coin_trader",
    };

    mockedApi.get.mockImplementation(async (url: string) => {
      if (url === "/coin-traders") return { data: [] };
      if (url === "/coin-traders/orders") return { data: [] };
      if (url === "/coin-traders/me") {
        return {
          data: {
            id: "prof-2",
            user_id: "trader-user-2",
            display_name: "Verified Desk",
            status: "approved",
            verified_at: "2026-11-15T10:00:00Z",
            rates: [],
          },
        };
      }
      if (url === "/coin-traders/me/orders") return { data: [] };
      return { data: null };
    });

    mockedApi.put.mockResolvedValue({ data: { id: "rate-1", coin_unit: "credit" } });
    mockedApi.post.mockImplementation(async (url: string) => {
      if (url === "/coin-traders/me/liquidity/quote") {
        return {
          data: {
            gross_amount: 1000,
            fee_amount: 0,
            net_amount: 1000,
            amount_fiat: 18000,
            currency_code: "NGN",
            unit: "credit",
            provider_key: "korapay",
          },
        };
      }
      if (url === "/coin-traders/me/liquidity/purchase") {
        return { data: { order_reference: "liq-1", checkout_url: "" } };
      }
      return { data: {} };
    });

    await renderDesk();

    // Switch rate publisher to Fan Coin (credit) and submit
    await act(async () => {
      (container.querySelector('[data-testid="trader-rate-unit-credit"]') as HTMLButtonElement).click();
    });
    await act(async () => {
      setInputValue(container.querySelector('[data-testid="trader-rate-buy-input"]') as HTMLInputElement, "19");
      setInputValue(container.querySelector('[data-testid="trader-rate-sell-input"]') as HTMLInputElement, "21");
    });
    await act(async () => {
      (container.querySelector('[data-testid="trader-rate-save-btn"]') as HTMLButtonElement).click();
    });
    await flush();

    expect(mockedApi.put).toHaveBeenCalledWith(
      "/coin-traders/me/rates",
      expect.objectContaining({
        coin_unit: "credit",
        fiat_currency: "NGN",
        buy_rate_fiat: 19,
        sell_rate_fiat: 21,
      })
    );
  });

  it("syncs suggested buyer minimum when switching traders without clobbering manual input", async () => {
    mockUser = {
      id: "buyer-2",
      username: "buyer2",
      display_name: "Buyer Two",
      account_type: "user",
    };

    const traderOne = {
      id: "prof-one",
      user_id: "u-one",
      display_name: "Rate One Desk",
      tier: "gold",
      status: "approved",
      verified_at: "2026-11-15T10:00:00Z",
      rates: [
        {
          id: "r-1",
          coin_unit: "coin",
          fiat_currency: "NGN",
          buy_rate_fiat: "900",
          sell_rate_fiat: "1000",
          min_coin_amount: "1",
          max_coin_amount: "100000",
          available_liquidity: "50000",
          is_active: true,
        },
      ],
    };
    const traderTwo = {
      id: "prof-two",
      user_id: "u-two",
      display_name: "Rate Two Desk",
      tier: "gold",
      status: "approved",
      verified_at: "2026-11-15T10:00:00Z",
      rates: [
        {
          id: "r-2",
          coin_unit: "coin",
          fiat_currency: "NGN",
          buy_rate_fiat: "450",
          sell_rate_fiat: "500",
          min_coin_amount: "1",
          max_coin_amount: "100000",
          available_liquidity: "50000",
          is_active: true,
        },
      ],
    };

    mockedApi.get.mockImplementation(async (url: string) => {
      if (url === "/coin-traders") return { data: [traderOne, traderTwo] };
      if (url === "/coin-traders/orders") return { data: [] };
      return { data: null };
    });

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    await act(async () => {
      root.render(
        <QueryClientProvider client={qc}>
          <ClubCoinTraderFundingPanel initialAmount="100" />
        </QueryClientProvider>
      );
    });
    await flush();
    await flush();

    const select = container.querySelector('[data-testid="coin-trader-select"]') as HTMLSelectElement;
    const amountInput = container.querySelector('[data-testid="coin-amount-input"]') as HTMLInputElement;
    expect(select.value).toBe("prof-one");
    expect(amountInput.value).toBe("200");

    // Switching to second trader (500 NGN/GTX) recalculates suggested buyer min (400 GTX)
    await act(async () => {
      setInputValue(select, "prof-two");
    });
    await flush();
    expect(amountInput.value).toBe("400");

    // Manual user edits remain preserved across prop updates
    await act(async () => {
      setInputValue(amountInput, "750");
      setInputValue(select, "prof-one");
    });
    await flush();
    expect(amountInput.value).toBe("750");
  });
});
