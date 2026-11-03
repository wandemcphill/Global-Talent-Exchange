declare const describe: any;
declare const it: any;
declare const test: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { api } from "@/lib/api";
import AdminAdvertising from "./AdminAdvertising";

var mockUserRole = "admin";
var mockToastError = jest.fn();
var mockToastSuccess = jest.fn();

jest.mock("@/lib/auth", () => ({
  useAuth: () => ({
    user: { id: "admin-user-1", email: "admin@gtex.test", role: mockUserRole },
    loading: false,
  }),
}));

jest.mock("react-router-dom", () => ({
  Navigate: ({ to }: { to: string }) => <div data-testid="navigated-to">{to}</div>,
}));

jest.mock("sonner", () => ({
  toast: {
    error: (...args: any[]) => mockToastError(...args),
    success: (...args: any[]) => mockToastSuccess(...args),
  },
}));

const sampleCampaign = {
  id: "camp-101",
  campaign_type: "brand",
  brand_name: "Nike Football",
  headline: "Unleash The Speed",
  description: "Next-gen cleats promotion",
  placement: "homepage_rail",
  destination_url: "https://nike.com/football",
  start_at: "2026-11-01T00:00:00Z",
  end_at: "2026-11-30T00:00:00Z",
  budget_amount: "5000",
  currency: "USD",
  pricing_model: "CPM",
  unit_price: "2.50",
  status: "pending",
  advertiser_id: "adv-1",
};

const sampleReport = {
  campaign_id: "camp-101",
  campaign_name: "Unleash The Speed",
  currency: "USD",
  impressions: 12500,
  clicks: 350,
  conversions: 18,
  ctr_percent: 2.8,
  estimated_spend: "31.25",
  billing_state: "unbilled",
};

describe("AdminAdvertising Moderation Desk", () => {
  let container: HTMLDivElement;
  let root: Root | null = null;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    mockUserRole = "admin";
    mockToastError.mockClear();
    mockToastSuccess.mockClear();
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(async () => {
    if (root) {
      await act(async () => {
        root?.unmount();
      });
      root = null;
    }
    if (container && container.parentNode) {
      container.parentNode.removeChild(container);
    }
    jest.restoreAllMocks();
  });

  const renderComponent = async () => {
    root = createRoot(container);
    await act(async () => {
      root?.render(<AdminAdvertising />);
    });
    for (let i = 0; i < 5; i += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 10));
      });
    }
  };

  it("calls canonical v2 versioned endpoints on mount", async () => {
    const getSpy = jest.spyOn(api, "get").mockImplementation(((url: string) => {
      if (url === "/v2/ads/brand/admin/campaigns") {
        return Promise.resolve({ data: [sampleCampaign] });
      }
      if (url === "/v2/ads/brand/admin/reports") {
        return Promise.resolve({ data: { reports: [sampleReport] } });
      }
      return Promise.reject(new Error(`Unexpected GET url: ${url}`));
    }) as any);

    await renderComponent();

    expect(getSpy).toHaveBeenCalledWith("/v2/ads/brand/admin/campaigns", {
      params: { status: "pending" },
    });
    expect(getSpy).toHaveBeenCalledWith("/v2/ads/brand/admin/reports");

    // Campaign item should be rendered
    const campaignCard = container.querySelector('[data-testid="campaign-card-camp-101"]');
    expect(campaignCard).toBeTruthy();
    expect(campaignCard?.textContent).toContain("Unleash The Speed");
    expect(campaignCard?.textContent).toContain("Nike Football");
  });

  it("displays explicit error state and retry button on 404/failure, never masquerading as empty queue", async () => {
    const getSpy = jest.spyOn(api, "get").mockImplementation(((url: string) => {
      if (url === "/v2/ads/brand/admin/campaigns") {
        const error: any = new Error("Request failed with status code 404");
        error.response = { status: 404, data: { detail: "Not found" } };
        return Promise.reject(error);
      }
      if (url === "/v2/ads/brand/admin/reports") {
        return Promise.resolve({ data: { reports: [] } });
      }
      return Promise.reject(new Error("Unexpected url"));
    }) as any);

    await renderComponent();

    // Critical assertion: empty state must NOT be rendered
    const emptyMsg = container.querySelector('[data-testid="empty-queue-message"]');
    expect(emptyMsg).toBeNull();

    // Error state container must be displayed
    const errorState = container.querySelector('[data-testid="campaigns-error-state"]');
    expect(errorState).toBeTruthy();
    expect(errorState?.textContent).toContain("Failed to load campaign moderation queue");

    // Retry button is available
    const retryBtn = container.querySelector('[data-testid="retry-campaigns-btn"]');
    expect(retryBtn).toBeTruthy();

    // Clicking retry attempts to refetch
    getSpy.mockImplementation(((url: string) => {
      if (url === "/v2/ads/brand/admin/campaigns") {
        return Promise.resolve({ data: [sampleCampaign] });
      }
      return Promise.resolve({ data: { reports: [] } });
    }) as any);

    await act(async () => {
      retryBtn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    for (let i = 0; i < 5; i += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 10));
      });
    }

    expect(container.querySelector('[data-testid="campaign-card-camp-101"]')).toBeTruthy();
  });

  it("renders empty queue message only when API genuinely returns empty array", async () => {
    jest.spyOn(api, "get").mockImplementation(((url: string) => {
      if (url === "/v2/ads/brand/admin/campaigns") {
        return Promise.resolve({ data: [] });
      }
      if (url === "/v2/ads/brand/admin/reports") {
        return Promise.resolve({ data: { reports: [] } });
      }
      return Promise.reject(new Error("Unexpected url"));
    }) as any);

    await renderComponent();

    const emptyMsg = container.querySelector('[data-testid="empty-queue-message"]');
    expect(emptyMsg).toBeTruthy();
    expect(emptyMsg?.textContent).toContain("No campaigns in this queue.");
    expect(container.querySelector('[data-testid="campaigns-error-state"]')).toBeNull();
  });

  it("handles report failure independently without breaking the moderation queue", async () => {
    jest.spyOn(api, "get").mockImplementation(((url: string) => {
      if (url === "/v2/ads/brand/admin/campaigns") {
        return Promise.resolve({ data: [sampleCampaign] });
      }
      if (url === "/v2/ads/brand/admin/reports") {
        const error: any = new Error("Telemetry service temporarily unavailable");
        error.response = { status: 503, data: { detail: "Service Unavailable" } };
        return Promise.reject(error);
      }
      return Promise.reject(new Error("Unexpected url"));
    }) as any);

    await renderComponent();

    // The campaign queue is still intact and functional
    expect(container.querySelector('[data-testid="campaign-card-camp-101"]')).toBeTruthy();

    // The reports error banner is displayed
    const reportsErrorBanner = container.querySelector('[data-testid="reports-error-banner"]');
    expect(reportsErrorBanner).toBeTruthy();
    expect(reportsErrorBanner?.textContent).toContain("Campaign telemetry could not be loaded");
  });

  it("submits moderation review to canonical /v2 endpoint", async () => {
    jest.spyOn(api, "get").mockImplementation(((url: string) => {
      if (url === "/v2/ads/brand/admin/campaigns") {
        return Promise.resolve({ data: [sampleCampaign] });
      }
      if (url === "/v2/ads/brand/admin/reports") {
        return Promise.resolve({ data: { reports: [sampleReport] } });
      }
      return Promise.resolve({ data: [] });
    }) as any);
    const postSpy = jest.spyOn(api, "post").mockResolvedValue({ data: { ...sampleCampaign, status: "approved" } } as any);

    await renderComponent();

    const approveBtn = container.querySelector('button[data-testid="admin-approve-camp-101"]') ||
      Array.from(container.querySelectorAll("button")).find((b: any) => b.textContent.includes("Approve"));

    expect(approveBtn).toBeTruthy();

    await act(async () => {
      approveBtn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    for (let i = 0; i < 5; i += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 10));
      });
    }

    expect(postSpy).toHaveBeenCalledWith(
      "/v2/ads/brand/admin/campaigns/camp-101/review",
      expect.objectContaining({ action: "approve" })
    );
    expect(mockToastSuccess).toHaveBeenCalledWith("Campaign approved.");
  });

  it("redirects non-admin users away from the desk", async () => {
    mockUserRole = "user";
    const getSpy = jest.spyOn(api, "get");

    await renderComponent();

    const navigated = container.querySelector('[data-testid="navigated-to"]');
    expect(navigated).toBeTruthy();
    expect(navigated?.textContent).toBe("/app");
    expect(getSpy).not.toHaveBeenCalled();
  });
});
