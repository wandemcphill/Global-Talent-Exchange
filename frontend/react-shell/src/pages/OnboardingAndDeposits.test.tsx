declare const describe: any;
declare const it: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import PaymentCallback from "./PaymentCallback";
import Onboarding from "./Onboarding";

let mockSearchParams = new URLSearchParams();
let mockUser: any = {
  id: "owner-1",
  username: "owner1",
  display_name: "Owner One",
  account_type: "user",
};
let mockClubData: any = null;
const mockApiGet = jest.fn();
const mockApiPost = jest.fn();
const mockNavigate = jest.fn();
const mockSetSearchParams = jest.fn();
const mockToastError = jest.fn();
const mockToastSuccess = jest.fn();

jest.mock("react-router-dom", () => ({
  Navigate: ({ to }: any) => <div data-testid="redirect-to" data-to={to} />,
  useNavigate: () => mockNavigate,
  useSearchParams: () => [mockSearchParams, mockSetSearchParams],
}));

jest.mock("@/lib/auth", () => ({
  useAuth: () => ({ user: mockUser, loading: false }),
}));

jest.mock("@/lib/api", () => ({
  errMsg: (e: any) => e?.response?.data?.detail || e?.message || "error",
  api: {
    get: (...args: any[]) => mockApiGet(...args),
    post: (...args: any[]) => mockApiPost(...args),
  },
}));

jest.mock("@/lib/publicPath", () => ({
  publicUrl: (path: string) => path,
}));

const mockClubRefetch = jest.fn();

jest.mock("@/lib/owner", () => ({
  fmt: (v: any, decimals = 0) =>
    Number(v || 0).toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }),
  useClub: () => ({
    data: mockClubData,
    refetch: mockClubRefetch,
    isLoading: false,
  }),
}));

jest.mock("sonner", () => ({
  toast: {
    error: (...args: any[]) => mockToastError(...args),
    success: (...args: any[]) => mockToastSuccess(...args),
  },
}));

jest.mock("@/components/gtex/Cinema3DStage", () => ({
  Cinema3DStage: ({ title, stats }: any) => (
    <div data-testid="cinema-stage">
      <span>{title}</span>
      {(stats || []).map((s: any) => (
        <span key={s.label}>
          {s.label}: {s.value}
        </span>
      ))}
    </div>
  ),
}));

jest.mock("@/components/gtex/MarketTable", () => ({
  MarketTable: () => <div data-testid="market-table" />,
}));

jest.mock("@/components/gtex/CoinTraderDesk", () => ({
  ClubCoinTraderFundingPanel: ({ initialAmount }: any) => (
    <div data-testid="mock-coin-trader-panel" data-initial-amount={initialAmount} />
  ),
}));

jest.mock("@/components/gtex/ClubLocationFields", () => ({
  ClubLocationFields: () => <div data-testid="club-location-fields" />,
  clubLocationPayload: () => ({}),
  useClubLocation: () => ({}),
}));

jest.mock("./clubLocationCatalog", () => ({
  clubCreateErrorMessage: (e: any) => e?.message || "error",
}));

jest.mock("three/examples/jsm/loaders/GLTFLoader.js", () => ({
  GLTFLoader: class {
    load(_url: string, onLoad?: (gltf: { scene: object }) => void) {
      onLoad?.({ scene: { traverse() {}, children: [] } });
    }
  },
}));

async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("PaymentCallback and Onboarding grant/funding flows", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    mockApiGet.mockReset();
    mockApiPost.mockReset();
    mockNavigate.mockReset();
    mockToastError.mockReset();
    mockToastSuccess.mockReset();
    mockClubData = null;
  });

  afterEach(async () => {
    await act(async () => {
      root.unmount();
    });
    container.remove();
  });

  it("omits provider param in PaymentCallback when URL lacks provider and passes it when present", async () => {
    mockApiGet.mockResolvedValue({ data: { status: "pending" } });

    mockSearchParams = new URLSearchParams("reference=gtex_kora_ref_1");
    await act(async () => {
      root.render(<PaymentCallback />);
    });
    await flush();
    expect(mockApiGet).toHaveBeenCalledWith("/owner/deposits/verify/gtex_kora_ref_1", undefined);

    mockApiGet.mockClear();
    mockSearchParams = new URLSearchParams("reference=gtex_kora_ref_2&provider=korapay");
    await act(async () => {
      root.render(<PaymentCallback />);
    });
    await flush();
    expect(mockApiGet).toHaveBeenCalledWith("/owner/deposits/verify/gtex_kora_ref_2", {
      params: { provider: "korapay" },
    });
  });

  it("renders dynamic launch grant copy and falls back to enabled deposit provider with loaded rate", async () => {
    mockClubData = {
      club_id: "club-1",
      club_name: "Lagos United",
      stage: "squad",
      cash: "2500",
      squad: [],
      economy: { cash_gtex: "2500", squad_grant: "2500" },
      formation: {
        total_registered_players: 12,
        remaining_to_form: 10,
        has_goalkeeper: false,
        is_formed: false,
      },
    };

    mockApiGet.mockImplementation(async (url: string) => {
      if (url === "/owner/onboarding") {
        return {
          data: {
            clubs: [{ club_id: "club-1", club_name: "Lagos United", stage: "squad", squad_size: 12, cash: "2500" }],
            launch_grant: 3500,
            launch_grant_owner_limit: 500,
          },
        };
      }
      if (url === "/owner/finance") {
        return {
          data: {
            wallet: { gtex_total: "0" },
            payment_providers: { korapay: false, paystack: true },
            treasury_rates: { deposit_rate: 100, deposit_direction: "fiat_per_coin" },
          },
        };
      }
      if (url === "/managers/catalog") return { data: { items: [] } };
      return { data: {} };
    });

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    await act(async () => {
      root.render(
        <QueryClientProvider client={qc}>
          <Onboarding />
        </QueryClientProvider>
      );
    });
    await flush();
    await flush();
    await flush();

    // Incomplete squad copy shows registered progress rather than claiming 22 starter players are registered.
    const basket = container.querySelector('[data-testid="squad-basket"]');
    expect(basket?.textContent).toContain("No additional market signings yet (12 of 22 players registered, goalkeeper still needed)");

    // SquadFundingPanel falls back to Paystack when KoraPay is disabled and Paystack is enabled.
    const buyBtn = container.querySelector('[data-testid="squad-platform-buy"]') as HTMLButtonElement;
    expect(buyBtn.disabled).toBe(false);

    mockApiPost.mockResolvedValueOnce({ data: { authorization_url: "" } });
    const amountInput = container.querySelector('[data-testid="squad-platform-amount"]') as HTMLInputElement;
    expect(Number(amountInput.value)).toBeGreaterThanOrEqual(100);
    await act(async () => {
      buyBtn.click();
    });
    await flush();
    expect(mockApiPost).toHaveBeenCalledWith(
      "/owner/deposits/init",
      expect.objectContaining({ provider: "paystack" })
    );
  });

  it("renders dynamic launch grant copy from onboarding API in IdentityStep", async () => {
    mockApiGet.mockImplementation(async (url: string) => {
      if (url === "/owner/onboarding") {
        return {
          data: {
            clubs: [{ club_id: "club-2", club_name: "Abuja Stars", stage: "identity", squad_size: 0, cash: "0" }],
            launch_grant: 3500,
            launch_grant_owner_limit: 500,
          },
        };
      }
      return { data: {} };
    });
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    await act(async () => {
      root.render(
        <QueryClientProvider client={qc}>
          <Onboarding />
        </QueryClientProvider>
      );
    });
    await flush();
    await flush();
    expect(container.querySelector('[data-testid="onboarding-identity-step"]')?.textContent).toContain("3,500 GTX");
    expect(container.querySelector('[data-testid="onboarding-identity-step"]')?.textContent).toContain("first 500 eligible club owners");
  });
});
