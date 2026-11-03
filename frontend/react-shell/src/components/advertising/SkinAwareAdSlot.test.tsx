declare const describe: any;
declare const test: any;
declare const it: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { SkinProvider, useSkin } from "@/lib/skin-engine";
import { SkinAwareAdSlot } from "./SkinAwareAdSlot";
import { GtexAdCampaign, GtexAdvertisingProvider } from "./GtexAdvertising";

// Mock axios for ad endpoints and api client
jest.mock("axios", () => {
  const instance = {
    interceptors: {
      request: { use: () => {} },
      response: { use: () => {} },
    },
    get: () => Promise.resolve({ data: {} }),
    post: () => Promise.resolve({ data: {} }),
  };
  return {
    create: () => instance,
    get: () =>
      Promise.resolve({
        data: {
          campaigns: [
            {
              id: "camp-001",
              brand_name: "Apex Sports Global",
              headline: "Official Global Football Sponsor",
              description: "Elite matchday training wear and boots.",
              placement: "homepage_hero",
              destination_url: "https://apex-sports.example.com",
              logo_url: "https://apex-sports.example.com/logo.png",
              priority: 10,
            },
          ],
        },
      }),
    post: () => Promise.resolve({ data: { success: true } }),
  };
});

describe("Advertising Equivalence & Commercial Invariance Across Skins", () => {
  let container: HTMLDivElement;
  let root: Root | null = null;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    localStorage.clear();
  });

  afterEach(() => {
    if (root) {
      act(() => {
        root?.unmount();
      });
      root = null;
    }
    if (container && container.parentNode) {
      container.parentNode.removeChild(container);
    }
  });

  function SkinAdHarness({ currentSkinId }: { currentSkinId: string }) {
    const { setSkin } = useSkin();
    React.useEffect(() => {
      setSkin(currentSkinId as any);
    }, [currentSkinId, setSkin]);

    return (
      <GtexAdvertisingProvider>
        <SkinAwareAdSlot placement="homepage_hero" />
      </GtexAdvertisingProvider>
    );
  }

  const mountHarness = (skinId: string) => {
    root = createRoot(container);
    act(() => {
      root?.render(
        <SkinProvider>
          <SkinAdHarness currentSkinId={skinId} />
        </SkinProvider>
      );
    });
  };

  it("Matchday skin renders commercial placement with intact identity and destination", () => {
    mountHarness("gtex-matchday");

    const slot = container.querySelector('[data-testid="skin-aware-ad-slot-homepage_hero"]');
    expect(slot).toBeTruthy();
    expect(slot?.getAttribute("data-placement")).toBe("homepage_hero");
    expect(slot?.getAttribute("data-skin-id")).toBe("gtex-matchday");
  });

  it("Touchline Pro skin renders identical commercial placement without modifying contract", () => {
    mountHarness("gtex-touchline-pro");

    const slot = container.querySelector('[data-testid="skin-aware-ad-slot-homepage_hero"]');
    expect(slot).toBeTruthy();
    expect(slot?.getAttribute("data-placement")).toBe("homepage_hero");
    expect(slot?.getAttribute("data-skin-id")).toBe("gtex-touchline-pro");
  });

  it("Pro Light skin renders identical commercial placement with high visibility", () => {
    mountHarness("gtex-pro-light");

    const slot = container.querySelector('[data-testid="skin-aware-ad-slot-homepage_hero"]');
    expect(slot).toBeTruthy();
    expect(slot?.getAttribute("data-placement")).toBe("homepage_hero");
    expect(slot?.getAttribute("data-skin-id")).toBe("gtex-pro-light");
  });

  it("Dynasty luxury skin renders identical commercial placement without altering billing identity", () => {
    mountHarness("gtex-dynasty");

    const slot = container.querySelector('[data-testid="skin-aware-ad-slot-homepage_hero"]');
    expect(slot).toBeTruthy();
    expect(slot?.getAttribute("data-placement")).toBe("homepage_hero");
    expect(slot?.getAttribute("data-skin-id")).toBe("gtex-dynasty");
  });
});
