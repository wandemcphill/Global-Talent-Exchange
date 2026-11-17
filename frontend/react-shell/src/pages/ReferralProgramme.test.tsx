declare const describe: any;
declare const it: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Referrals from "./Referrals";
import ReferralAdmin from "./ReferralAdmin";

let mockUser: any = { id: "user-1", role: "user", account_type: "user" };
const mockApiGet = jest.fn();
const mockApiPost = jest.fn();
var mockToastSuccess = jest.fn();
var mockToastError = jest.fn();

jest.mock("react-router-dom", () => ({
  Navigate: ({ to }: any) => <div data-testid="redirect-to" data-to={to} />,
  Link: ({ to, children }: any) => <a href={to}>{children}</a>,
}));

jest.mock("@/lib/auth", () => ({
  useAuth: () => ({ user: mockUser, loading: false }),
}));

jest.mock("@/lib/api", () => ({
  errMsg: (error: any) => error?.response?.data?.detail || error?.message || "error",
  api: {
    get: (...args: any[]) => mockApiGet(...args),
    post: (...args: any[]) => mockApiPost(...args),
    defaults: { baseURL: "http://127.0.0.1:8000/api" },
  },
}));

jest.mock("sonner", () => ({
  toast: {
    success: (...args: any[]) => mockToastSuccess(...args),
    error: (...args: any[]) => mockToastError(...args),
  },
}));

const affiliate = {
  code: "CREATOR10",
  link: "https://playgtex.app/signup?ref=CREATOR10",
  explanation: "Register with this referral code and receive a 10% bonus on your first qualifying deposit.",
  registrations: 2,
  qualifying_deposits: 1,
  referred_deposit_volume: { NGN: "100000.00" },
  pending_commission: { NGN: "10000.00" },
  approved_commission: {},
  paid_commission: {},
  reversed_commission: {},
  payouts: [],
};

function render(node: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  act(() => {
    root.render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
  });
  return { container, root };
}

async function flush() {
  for (let attempt = 0; attempt < 8; attempt += 1) {
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 25));
    });
  }
}

function setInput(element: HTMLInputElement, value: string) {
  act(() => {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set;
    setter?.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

describe("Referral dashboards", () => {
  let root: Root | null = null;
  let container: HTMLDivElement | null = null;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    mockUser = { id: "user-1", role: "user", account_type: "user" };
    mockApiGet.mockReset();
    mockApiPost.mockReset();
    mockApiGet.mockImplementation((url: string) => {
      if (url === "/owner/onboarding") return Promise.resolve({ data: { clubs: [] } });
      if (url === "/referrals/me/affiliate") return Promise.resolve({ data: affiliate });
      if (url === "/admin/referrals/affiliate/overview") {
        return Promise.resolve({ data: { clicks: 7, registrations: 3, first_deposits: 1, conversion_rate: "0.33", fraud_flags: 0, partners: 1 } });
      }
      return Promise.resolve({ data: [] });
    });
  });

  afterEach(() => {
    act(() => root?.unmount());
    container?.remove();
  });

  it.each([
    ["user", [], "Member"],
    ["user", [{ id: "club-1" }], "Club owner"],
    ["creator", [], "Creator"],
    ["coin_trader", [], "Coin trader"],
  ])("shows the %s lane as %s", async (accountType, clubs, label) => {
    mockUser = { id: "user-1", role: "user", account_type: accountType };
    mockApiGet.mockImplementation((url: string) => {
      if (url === "/owner/onboarding") return Promise.resolve({ data: { clubs } });
      return Promise.resolve({ data: affiliate });
    });
    ({ container, root } = render(<Referrals />));
    await flush();
    expect(container?.querySelector('[data-testid="referrals-account-lane"]')?.textContent).toBe(label);
    expect(container?.querySelector('[data-testid="referrals-code"]')?.textContent).toBe("CREATOR10");
  });

  it("loads admin overview from the API and does not report a failed payout as paid", async () => {
    mockUser = { id: "admin-1", role: "admin", account_type: "user" };
    mockApiPost.mockRejectedValueOnce({ response: { data: { detail: "Payment reference was rejected" } } });
    ({ container, root } = render(<ReferralAdmin />));
    await flush();
    expect(container?.querySelector('[data-testid="referral-admin-overview"]')?.textContent).toContain("7");
    act(() => {
      (container?.querySelector('[data-testid="referral-admin-tab-payouts"]') as HTMLButtonElement).click();
    });
    await flush();
    setInput(container?.querySelector('[data-testid="referral-admin-batch-id"]') as HTMLInputElement, "batch-1");
    setInput(container?.querySelector('[data-testid="referral-admin-payment-reference"]') as HTMLInputElement, "BANK-1");
    await act(async () => {
      (container?.querySelector('[data-testid="referral-admin-payouts"] form') as HTMLFormElement).dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
    });
    expect(container?.querySelector('[data-testid="referral-admin-error"]')?.textContent).toContain("Payment reference was rejected");
    expect(container?.querySelector('[data-testid="referral-admin-success"]')).toBeNull();
  });
});
