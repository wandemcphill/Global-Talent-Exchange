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
import AdvertiserAds from "./AdvertiserAds";

var mockToastError = jest.fn();
var mockToastSuccess = jest.fn();

jest.mock("sonner", () => ({
  toast: {
    error: (...args: any[]) => mockToastError(...args),
    success: (...args: any[]) => mockToastSuccess(...args),
  },
}));

const sampleProfile = {
  company_name: "Puma Sports",
  contact_name: "Alex Smith",
  website_url: "https://puma.com",
  billing_email: "billing@puma.com",
};

const sampleCampaign = {
  id: "camp-201",
  campaign_type: "brand" as const,
  brand_name: "Puma Sports",
  headline: "Forever Faster Season Launch",
  description: "Global brand campaign",
  placement: "homepage_rail",
  destination_url: "https://puma.com/faster",
  logo_url: "https://puma.com/logo.png",
  creative_url: "https://puma.com/banner.jpg",
  start_at: "2026-11-01T00:00:00Z",
  end_at: "2026-11-30T00:00:00Z",
  budget_amount: "3000",
  currency: "USD",
  pricing_model: "CPM" as const,
  unit_price: "4.50",
  status: "draft",
};

const sampleReport = {
  campaign_id: "camp-201",
  campaign_name: "Forever Faster Season Launch",
  currency: "USD",
  budget_amount: "3000",
  impressions: 5000,
  clicks: 120,
  conversions: 8,
  ctr_percent: 2.4,
  estimated_spend: "22.50",
  estimated_budget_remaining: "2977.50",
  billing_state: "unbilled",
};

describe("AdvertiserAds Studio", () => {
  let container: HTMLDivElement;
  let root: Root | null = null;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    window.scrollTo = jest.fn();
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
      root?.render(<AdvertiserAds />);
    });
    for (let i = 0; i < 5; i += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 10));
      });
    }
  };

  it("calls canonical v2 advertiser endpoints on mount", async () => {
    const getSpy = jest.spyOn(api, "get").mockImplementation(((url: string) => {
      if (url === "/v2/ads/brand/profile") {
        return Promise.resolve({ data: sampleProfile });
      }
      if (url === "/v2/ads/brand/campaigns") {
        return Promise.resolve({ data: [sampleCampaign] });
      }
      if (url === "/v2/ads/brand/reports") {
        return Promise.resolve({ data: { reports: [sampleReport] } });
      }
      return Promise.reject(new Error(`Unexpected GET url: ${url}`));
    }) as any);

    await renderComponent();

    expect(getSpy).toHaveBeenCalledWith("/v2/ads/brand/profile");
    expect(getSpy).toHaveBeenCalledWith("/v2/ads/brand/campaigns");
    expect(getSpy).toHaveBeenCalledWith("/v2/ads/brand/reports");

    // Profile inputs populated
    const companyInput = container.querySelector('input[value="Puma Sports"]');
    expect(companyInput).toBeTruthy();

    // Campaign listed
    const campaignRow = container.querySelector('[data-testid="campaign-row-camp-201"]');
    expect(campaignRow).toBeTruthy();
    expect(campaignRow?.textContent).toContain("Forever Faster Season Launch");
  });

  it("displays explicit error state and retry button on campaign load failure, not masquerading as empty inventory", async () => {
    const getSpy = jest.spyOn(api, "get").mockImplementation(((url: string) => {
      if (url === "/v2/ads/brand/profile") {
        return Promise.resolve({ data: sampleProfile });
      }
      if (url === "/v2/ads/brand/campaigns") {
        const err: any = new Error("Request failed with status code 404");
        err.response = { status: 404, data: { detail: "Endpoint Not Found" } };
        return Promise.reject(err);
      }
      if (url === "/v2/ads/brand/reports") {
        return Promise.resolve({ data: { reports: [] } });
      }
      return Promise.reject(new Error("Unexpected url"));
    }) as any);

    await renderComponent();

    // Critical assertion: must NOT display "No campaigns created yet"
    const emptyMsg = container.querySelector('[data-testid="empty-campaigns-message"]');
    expect(emptyMsg).toBeNull();

    // Error container is rendered with retry button
    const errorState = container.querySelector('[data-testid="advertiser-campaigns-error-state"]');
    expect(errorState).toBeTruthy();
    expect(errorState?.textContent).toContain("Failed to load campaigns");

    const retryBtn = container.querySelector('[data-testid="retry-advertiser-campaigns-btn"]');
    expect(retryBtn).toBeTruthy();

    // Clicking retry refetches
    getSpy.mockImplementation(((url: string) => {
      if (url === "/v2/ads/brand/campaigns") {
        return Promise.resolve({ data: [sampleCampaign] });
      }
      return Promise.resolve({ data: sampleProfile });
    }) as any);

    await act(async () => {
      retryBtn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    for (let i = 0; i < 5; i += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 10));
      });
    }

    expect(container.querySelector('[data-testid="campaign-row-camp-201"]')).toBeTruthy();
  });

  it("handles profile error independently without stopping campaign inventory", async () => {
    jest.spyOn(api, "get").mockImplementation(((url: string) => {
      if (url === "/v2/ads/brand/profile") {
        const err: any = new Error("Internal Server Error");
        err.response = { status: 500, data: { detail: "Profile DB Error" } };
        return Promise.reject(err);
      }
      if (url === "/v2/ads/brand/campaigns") {
        return Promise.resolve({ data: [sampleCampaign] });
      }
      if (url === "/v2/ads/brand/reports") {
        return Promise.resolve({ data: { reports: [] } });
      }
      return Promise.reject(new Error("Unexpected url"));
    }) as any);

    await renderComponent();

    // Profile error banner displayed
    const profileError = container.querySelector('[data-testid="profile-error-banner"]');
    expect(profileError).toBeTruthy();
    expect(profileError?.textContent).toContain("Profile sync error");

    // Campaigns still rendered successfully
    expect(container.querySelector('[data-testid="campaign-row-camp-201"]')).toBeTruthy();
  });

  it("handles reports error independently without stopping campaign inventory", async () => {
    jest.spyOn(api, "get").mockImplementation(((url: string) => {
      if (url === "/v2/ads/brand/profile") {
        return Promise.resolve({ data: sampleProfile });
      }
      if (url === "/v2/ads/brand/campaigns") {
        return Promise.resolve({ data: [sampleCampaign] });
      }
      if (url === "/v2/ads/brand/reports") {
        const err: any = new Error("Service Unavailable");
        err.response = { status: 503, data: { detail: "Clickhouse Down" } };
        return Promise.reject(err);
      }
      return Promise.reject(new Error("Unexpected url"));
    }) as any);

    await renderComponent();

    const reportsError = container.querySelector('[data-testid="advertiser-reports-error-state"]');
    expect(reportsError).toBeTruthy();
    expect(reportsError?.textContent).toContain("Campaign telemetry could not be loaded");

    // Campaigns still rendered successfully
    expect(container.querySelector('[data-testid="campaign-row-camp-201"]')).toBeTruthy();
  });

  it("submits a campaign for review to canonical /v2 endpoint", async () => {
    jest.spyOn(api, "get").mockImplementation(((url: string) => {
      if (url === "/v2/ads/brand/profile") return Promise.resolve({ data: sampleProfile });
      if (url === "/v2/ads/brand/campaigns") return Promise.resolve({ data: [sampleCampaign] });
      if (url === "/v2/ads/brand/reports") return Promise.resolve({ data: { reports: [] } });
      return Promise.reject(new Error("Unexpected url"));
    }) as any);
    const postSpy = jest.spyOn(api, "post").mockResolvedValue({ data: { ok: true } } as any);

    await renderComponent();

    const submitBtn = Array.from(container.querySelectorAll("button")).find(
      (b: any) => b.textContent.includes("Submit for review")
    );
    expect(submitBtn).toBeTruthy();

    await act(async () => {
      submitBtn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    for (let i = 0; i < 5; i += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 10));
      });
    }

    expect(postSpy).toHaveBeenCalledWith("/v2/ads/brand/campaigns/camp-201/submit");
    expect(mockToastSuccess).toHaveBeenCalledWith("Campaign submitted for GTEX review.");
  });

  it("edits an existing campaign draft and submits via /v2/ads/brand/campaigns/:id", async () => {
    jest.spyOn(api, "get").mockImplementation(((url: string) => {
      if (url === "/v2/ads/brand/profile") return Promise.resolve({ data: sampleProfile });
      if (url === "/v2/ads/brand/campaigns") return Promise.resolve({ data: [sampleCampaign] });
      if (url === "/v2/ads/brand/reports") return Promise.resolve({ data: { reports: [] } });
      return Promise.reject(new Error("Unexpected url"));
    }) as any);
    const putSpy = jest.spyOn(api, "put").mockResolvedValue({ data: sampleCampaign } as any);

    await renderComponent();

    // Click Edit on the campaign
    const editBtn = Array.from(container.querySelectorAll("button")).find(
      (b: any) => b.textContent.trim() === "Edit"
    );
    expect(editBtn).toBeTruthy();

    await act(async () => {
      editBtn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    const form = container.querySelector('[data-testid="campaign-workspace-form"]');
    expect(form).toBeTruthy();

    // Submit the edited form
    await act(async () => {
      form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });
    for (let i = 0; i < 5; i += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 10));
      });
    }

    expect(putSpy).toHaveBeenCalledWith(
      "/v2/ads/brand/campaigns/camp-201",
      expect.objectContaining({
        brand_name: "Puma Sports",
        placement: "homepage_rail",
      })
    );
    expect(mockToastSuccess).toHaveBeenCalledWith("Draft campaign updated.");
  });
});
