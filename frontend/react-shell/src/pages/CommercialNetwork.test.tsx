declare const describe: any;
declare const it: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { api } from "@/lib/api";
import { formatNairaFromKobo } from "@/lib/commercial/api";
import CommercialPublicPortal from "./CommercialPublicPortal";
import AdvertiserAuthPage from "./AdvertiserAuthPage";
import { MatchSponsorIdentificationBadge, SilentMatchBroadcastPanel } from "@/components/advertising/GtexMatchBroadcastAds";

var mockNavigate = jest.fn();
var mockSetSearchParams = jest.fn();
var mockRefresh = jest.fn();
var mockToastError = jest.fn();
var mockToastSuccess = jest.fn();
var mockToastInfo = jest.fn();

jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...rest }: any) => (
    <a href={to} {...rest}>
      {children}
    </a>
  ),
  useLocation: () => ({ pathname: "/advertise" }),
  useNavigate: () => mockNavigate,
  useSearchParams: () => [new URLSearchParams(), mockSetSearchParams],
}));

jest.mock("@/lib/auth", () => ({
  useAuth: () => ({
    user: null,
    loading: false,
    refresh: mockRefresh,
  }),
}));

jest.mock("sonner", () => ({
  toast: {
    error: (...args: any[]) => mockToastError(...args),
    success: (...args: any[]) => mockToastSuccess(...args),
    info: (...args: any[]) => mockToastInfo(...args),
  },
}));

const samplePlacements = [
  {
    id: "pl-1",
    placement_key: "public_homepage",
    name: "Public Homepage Hero Showcase",
    division: "brand",
    category: "Public Website",
    description: "Primary silent commercial showcase on the public GTEX landing experience.",
    supported_media_types: ["image/png", "image/jpeg", "video/mp4"],
    aspect_ratio: "16:9",
    recommended_width: 1920,
    recommended_height: 1080,
    max_file_size_bytes: 26214400,
    max_duration_seconds: 30,
    requires_silent_media: true,
    weekly_rate_minor_ngn: 25000000,
    weekly_rate_formatted_ngn: "₦250,000.00",
    pricing_configured: true,
    is_enabled: true,
    delivery_surface_ready: true,
    frequency_cap_per_session: 10,
    rotation_interval_seconds: 30,
    priority_weight: 100,
    device_compatibility: ["desktop", "mobile"],
  },
];

const samplePackages = [
  {
    id: "pkg-1",
    package_code: "brand_starter_7d",
    name: "7-Day Brand Launch (Minimum Duration)",
    division: "brand",
    description: "7-day silent brand showcase across selected GTEX placements.",
    duration_days: 7,
    placement_keys: ["public_homepage"],
    is_bundle: false,
    is_subscription: false,
    billing_interval_days: null,
    price_minor_ngn: 25000000,
    price_formatted_ngn: "₦250,000.00",
    pricing_configured: true,
    currency: "NGN",
    discount_percent: 0,
    is_active: true,
    sort_order: 10,
  },
];

describe("GTEX Commercial Network Public Portal, Auth & Match Broadcast Ads", () => {
  let container: HTMLDivElement;
  let root: Root | null = null;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
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

  it("formats Nigerian Naira (NGN) from integer kobo and handles unconfigured state", () => {
    expect(formatNairaFromKobo(25000000)).toBe("₦250,000.00");
    expect(formatNairaFromKobo(null)).toContain("pending admin configuration");
  });

  it("renders public commercial portal with Reach the GTEX audience headline and NGN inventory", async () => {
    jest.spyOn(api, "get").mockImplementation(((url: string) => {
      if (url === "/v2/public/ads/placements") return Promise.resolve({ data: samplePlacements });
      if (url === "/v2/public/ads/packages") return Promise.resolve({ data: samplePackages });
      return Promise.resolve({ data: [] });
    }) as any);

    root = createRoot(container);
    await act(async () => {
      root?.render(<CommercialPublicPortal division="overview" />);
    });
    for (let i = 0; i < 4; i += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 10));
      });
    }

    const headline = container.querySelector('[data-testid="commercial-hero-headline"]');
    expect(headline?.textContent).toBe("Reach the GTEX audience.");
    expect(container.querySelector('[data-testid="division-brand-advertising"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="division-music-promotion"]')).toBeTruthy();
    expect(container.textContent).toContain("₦250,000.00");
  });

  it("renders dedicated advertiser registration with business, agency, and music account types", async () => {
    root = createRoot(container);
    await act(async () => {
      root?.render(<AdvertiserAuthPage mode="register" />);
    });

    expect(container.querySelector('[data-testid="advertiser-auth-page"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="account-type-business"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="account-type-agency"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="account-type-music"]')).toBeTruthy();
  });

  it("renders silent match broadcast panel and sponsor identification badge", async () => {
    jest.spyOn(api, "post").mockResolvedValue({ data: { ok: true } } as any);

    const sampleAd = {
      id: "ad-match-1",
      brand_name: "Zenith Bank",
      headline: "Official Matchday Banking Partner",
      description: "Instant Naira transfers during matchday.",
      placement: "live_match_panel",
      destination_url: "https://zenithbank.example.com",
      logo_url: "https://zenithbank.example.com/logo.png",
      creative_url: "https://zenithbank.example.com/spot.mp4",
      creative_media_type: "video/mp4",
      is_silent_creative: true,
      priority: 100,
    };

    root = createRoot(container);
    await act(async () => {
      root?.render(
        <div>
          <MatchSponsorIdentificationBadge ad={sampleAd} />
          <SilentMatchBroadcastPanel liveAd={sampleAd} halftimeAd={sampleAd} isHalftime={true} />
        </div>
      );
    });

    expect(container.querySelector('[data-testid="match-sponsor-id-badge"]')).toBeTruthy();
    const panel = container.querySelector('[data-testid="match-halftime-sponsorship-panel"]');
    expect(panel).toBeTruthy();
    expect(panel?.textContent).toContain("Halftime Official Sponsorship");
    const videoEl = panel?.querySelector("video") as HTMLVideoElement | null;
    expect(videoEl).toBeTruthy();
    expect(videoEl?.muted).toBe(true);
  });
});
