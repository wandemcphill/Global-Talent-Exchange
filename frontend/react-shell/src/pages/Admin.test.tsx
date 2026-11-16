declare const describe: any;
declare const it: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Admin from "./Admin";
import { api } from "@/lib/api";

let mockSearchParams = new URLSearchParams("");
const mockSetSearchParams = jest.fn((next: any) => {
  mockSearchParams = new URLSearchParams(next);
});

const mockToastSuccess = jest.fn();
const mockToastError = jest.fn();
const mockApiGet = jest.fn();
const mockApiPost = jest.fn();
const mockApiPut = jest.fn();
const mockApiPatch = jest.fn();

jest.mock("react-router-dom", () => ({
  Navigate: ({ to }: any) => <div data-testid="navigate-redirect">{to}</div>,
  useSearchParams: () => [mockSearchParams, mockSetSearchParams],
}));

jest.mock("@/lib/auth", () => ({
  useAuth: () => ({
    user: { id: "admin-1", username: "superadmin", role: "super_admin" },
  }),
}));

jest.mock("@/lib/owner", () => ({
  fmt: (v: any, decimals = 0) =>
    Number(v || 0).toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }),
  label: (s: any) => String(s || "").replace(/_/g, " "),
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

describe("Admin page unified economy, coin traders & KYC controls", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    mockSearchParams = new URLSearchParams("");
    mockSetSearchParams.mockClear();
    mockToastSuccess.mockReset();
    mockToastError.mockReset();
    mockedApi.get.mockReset();
    mockedApi.post.mockReset();
    mockedApi.put.mockReset();
    mockedApi.patch.mockReset();

    mockedApi.get.mockImplementation(async (url: string) => {
      if (url === "/owner/admin/review-queue") {
        return { data: { withdrawals: [], flags: [], held_payouts: [] } };
      }
      if (url === "/admin/god-mode/bootstrap") {
        return {
          data: {
            commissions: { buy_commission_bps: 250, sell_commission_bps: 250, withdrawal_fee_bps: 150 },
            competition_controls: { prize_pool_topup_pct: "15.00" },
            treasury_dashboard: {},
            payment_rails: [],
            audit_events: [],
          },
        };
      }
      if (url.startsWith("/admin/finance/users")) {
        return {
          data: [
            { id: "u-alice", email: "alice@example.com", username: "alice", display_name: "Alice", role: "user" },
            { id: "u-bob", email: "bob@example.com", username: "bob", display_name: "Bob", role: "user" },
          ],
        };
      }
      if (url.startsWith("/admin/god-mode/users/u-alice/points")) {
        return {
          data: {
            user_id: "u-alice",
            balance: "120.0000",
            lifetime_earned: "120.0000",
            source_scope: "personal_reward_points",
            recent_entries: [],
          },
        };
      }
      if (url === "/admin/coin-traders") {
        return {
          data: [
            {
              id: "trader-1",
              user_id: "u-trader-1",
              display_name: "Abuja Liquidity Desk",
              tier: "gold",
              status: "approved",
              verified_at: "2026-11-15T12:00:00Z",
              verification_provider: "didit",
            },
          ],
        };
      }
      if (url === "/admin/kyc/records") {
        return {
          data: [
            {
              id: "kyc-1",
              user_id: "u-trader-1",
              user_email: "trader1@example.com",
              trader_profile_id: "trader-1",
              trader_display_name: "Abuja Liquidity Desk",
              provider: "didit",
              verification_type: "full_kyc",
              provider_session_id: "sess-didit-01",
              status: "verified",
              decision: "Approved",
              checks_summary: { id_verification_status: "Approved", liveness_passed: true },
            },
          ],
        };
      }
      if (url.startsWith("/admin/treasury") || url.startsWith("/admin/creator")) {
        return { data: { items: [], total: 0 } };
      }
      return { data: [] };
    });
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  const renderAdmin = async () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    await act(async () => {
      root.render(
        <QueryClientProvider client={qc}>
          <Admin />
        </QueryClientProvider>
      );
    });
    await flush();
  };

  it("wires Give Coin, Transfer Between Users, and Grant Personal Points with dual GTC/FNC support", async () => {
    mockedApi.post.mockImplementation(async (url: string) => {
      if (url === "/admin/god-mode/wallets/credit") {
        return {
          data: {
            transaction_id: "tx-credit-1",
            user_id: "u-alice",
            username: "alice",
            unit: "credit",
            amount: "150.0000",
            balance_before: "0.0000",
            balance_after: "150.0000",
          },
        };
      }
      if (url === "/admin/god-mode/wallets/transfer") {
        return {
          data: {
            transaction_id: "tx-xfer-1",
            from_user_id: "u-alice",
            to_user_id: "u-bob",
            unit: "coin",
            amount: "40.0000",
            from_balance_before: "100.0000",
            from_balance_after: "60.0000",
            to_balance_before: "10.0000",
            to_balance_after: "50.0000",
          },
        };
      }
      if (url === "/admin/god-mode/points/grant") {
        return {
          data: {
            entry_id: "pt-1",
            reference: "godmode:points:grant:1",
            user_id: "u-alice",
            amount: "75.0000",
            balance_before: "120.0000",
            balance_after: "195.0000",
            lifetime_earned: "195.0000",
          },
        };
      }
      return { data: {} };
    });

    await renderAdmin();

    // Switch to economy tab via shortcut
    await act(async () => {
      (container.querySelector('[data-testid="admin-tab-economy-btn"]') as HTMLButtonElement).click();
    });
    await flush();

    // 1. Give someone Fan Coin (credit)
    await act(async () => {
      (container.querySelector('[data-testid="give-coin-user-option-u-alice"]') as HTMLButtonElement).click();
      setInputValue(container.querySelector('[data-testid="give-coin-unit-select"]') as HTMLSelectElement, "credit");
      setInputValue(container.querySelector('[data-testid="give-coin-amount-input"]') as HTMLInputElement, "150");
    });
    await act(async () => {
      (container.querySelector('[data-testid="give-coin-submit-btn"]') as HTMLButtonElement).click();
    });
    await flush();

    expect(mockedApi.post).toHaveBeenCalledWith(
      "/admin/god-mode/wallets/credit",
      expect.objectContaining({
        user_id: "u-alice",
        unit: "credit",
        amount: 150,
      })
    );
    expect(container.querySelector('[data-testid="give-coin-result"]')?.textContent).toContain("tx-credit-1");

    // 2. Transfer GTEX Coin (coin) from Alice to Bob
    await act(async () => {
      (container.querySelector('[data-testid="transfer-from-user-option-u-alice"]') as HTMLButtonElement).click();
      (container.querySelector('[data-testid="transfer-to-user-option-u-bob"]') as HTMLButtonElement).click();
      setInputValue(container.querySelector('[data-testid="transfer-coin-unit-select"]') as HTMLSelectElement, "coin");
      setInputValue(container.querySelector('[data-testid="transfer-coin-amount-input"]') as HTMLInputElement, "40");
    });
    await act(async () => {
      (container.querySelector('[data-testid="transfer-coin-submit-btn"]') as HTMLButtonElement).click();
    });
    await flush();

    expect(mockedApi.post).toHaveBeenCalledWith(
      "/admin/god-mode/wallets/transfer",
      expect.objectContaining({
        from_user_id: "u-alice",
        to_user_id: "u-bob",
        unit: "coin",
        amount: 40,
      })
    );
    expect(container.querySelector('[data-testid="transfer-coin-result"]')?.textContent).toContain("tx-xfer-1");

    // 3. Grant personal user points
    await act(async () => {
      (container.querySelector('[data-testid="grant-points-user-option-u-alice"]') as HTMLButtonElement).click();
    });
    await flush();
    expect(container.querySelector('[data-testid="selected-user-points-balance"]')?.textContent).toContain("120");

    await act(async () => {
      setInputValue(container.querySelector('[data-testid="grant-points-amount-input"]') as HTMLInputElement, "75");
    });
    await act(async () => {
      (container.querySelector('[data-testid="grant-points-submit-btn"]') as HTMLButtonElement).click();
    });
    await flush();

    expect(mockedApi.post).toHaveBeenCalledWith(
      "/admin/god-mode/points/grant",
      expect.objectContaining({
        user_id: "u-alice",
        amount: 75,
      })
    );
    expect(container.querySelector('[data-testid="grant-points-result"]')?.textContent).toContain("195");
  });

  it("queries /admin/coin-traders and /admin/kyc/records cleanly and issues trader FNC liquidity", async () => {
    mockedApi.post.mockResolvedValue({
      data: {
        flow: "issue",
        coin_unit: "credit",
        amount: "250.0000",
        reference: "liq-issue-250",
        available_balance: "1250.0000",
      },
    });

    await renderAdmin();

    await act(async () => {
      (container.querySelector('[data-testid="admin-tab-queues-btn"]') as HTMLButtonElement).click();
    });
    await flush();

    // Must NOT call double-prefixed /api/coin-traders
    const requestedUrls = mockedApi.get.mock.calls.map((c: any[]) => c[0]);
    expect(requestedUrls).toContain("/admin/coin-traders");
    expect(requestedUrls).toContain("/admin/kyc/records");
    expect(requestedUrls).not.toContain("/api/coin-traders");

    expect(container.querySelector('[data-testid="admin-kyc-records-list"]')?.textContent).toContain("sess-didit-01");

    await act(async () => {
      setInputValue(container.querySelector('[data-testid="trader-liquidity-unit-trader-1"]') as HTMLSelectElement, "credit");
      setInputValue(container.querySelector('[data-testid="trader-liquidity-amount-trader-1"]') as HTMLInputElement, "250");
    });
    await act(async () => {
      (container.querySelector('[data-testid="trader-issue-liquidity-trader-1"]') as HTMLButtonElement).click();
    });
    await flush();

    expect(mockedApi.post).toHaveBeenCalledWith(
      "/admin/coin-traders/trader-1/liquidity/issue",
      expect.objectContaining({
        coin_unit: "credit",
        amount: 250,
      })
    );
    expect(container.querySelector('[data-testid="trader-liquidity-result"]')?.textContent).toContain("liq-issue-250");
  });
});
