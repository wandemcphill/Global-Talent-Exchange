declare const describe: any;
declare const test: any;
declare const it: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { SkinProvider } from "@/lib/skin-engine";
import AppearanceStudio from "./AppearanceStudio";

// Mock sonner toast
jest.mock("sonner", () => ({
  toast: {
    success: () => {},
    info: () => {},
    error: () => {},
  },
}));

describe("AppearanceStudio UI & Customization Tests", () => {
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

  const mountStudio = () => {
    root = createRoot(container);
    act(() => {
      root?.render(
        <SkinProvider>
          <AppearanceStudio />
        </SkinProvider>
      );
    });
  };

  it("renders the Appearance Studio with all 6 navigation tabs", () => {
    mountStudio();

    expect(container.querySelector('[data-testid="appearance-studio-page"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="tab-my-skins"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="tab-layout"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="tab-football-views"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="tab-graphics"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="tab-accessibility"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="tab-data-saver"]')).toBeTruthy();
  });

  it("renders the official skins: Matchday, Touchline Pro, Pro Light, Dynasty", () => {
    mountStudio();

    expect(container.querySelector('[data-testid="skin-card-gtex-matchday"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="skin-card-gtex-touchline-pro"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="skin-card-gtex-pro-light"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="skin-card-gtex-dynasty"]')).toBeTruthy();
  });

  it("switches to Layout tab and allows selecting density presets", () => {
    mountStudio();

    const tabLayout = container.querySelector('[data-testid="tab-layout"]') as HTMLButtonElement;
    act(() => {
      tabLayout.click();
    });

    expect(container.querySelector('[data-testid="preset-comfortable"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="preset-compact"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="preset-manager-dense"]')).toBeTruthy();

    // Select Manager Dense
    const denseBtn = container.querySelector('[data-testid="preset-manager-dense"]') as HTMLDivElement;
    act(() => {
      denseBtn.click();
    });
    expect(document.documentElement.getAttribute("data-density")).toBe("manager_dense");
  });

  it("switches to Football Views tab and displays registered modules", () => {
    mountStudio();

    const tabViews = container.querySelector('[data-testid="tab-football-views"]') as HTMLButtonElement;
    act(() => {
      tabViews.click();
    });

    expect(container.querySelector('[data-testid="module-setting-market"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="module-setting-squad"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="module-setting-match_center"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="module-setting-competitions"]')).toBeTruthy();

    // Select FM table view for market
    const optionBtn = container.querySelector('[data-testid="view-option-market-table"]') as HTMLButtonElement;
    act(() => {
      optionBtn.click();
    });
    expect(optionBtn.className).toContain("border-emerald-500");
  });

  it("switches to Accessibility tab and toggles accessibility controls", () => {
    mountStudio();

    const tabAccess = container.querySelector('[data-testid="tab-accessibility"]') as HTMLButtonElement;
    act(() => {
      tabAccess.click();
    });

    expect(container.querySelector('[data-testid="toggle-reduced-motion"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="toggle-high-contrast"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="toggle-focus-rings"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="select-text-scaling"]')).toBeTruthy();
  });

  it("switches to Data Saver tab and renders toggle", () => {
    mountStudio();

    const tabDataSaver = container.querySelector('[data-testid="tab-data-saver"]') as HTMLButtonElement;
    act(() => {
      tabDataSaver.click();
    });

    expect(container.querySelector('[data-testid="toggle-data-saver"]')).toBeTruthy();
  });

  it("renders the Live Experience Sandbox simulator", () => {
    mountStudio();

    expect(container.querySelector('[data-testid="live-preview-sandbox"]')).toBeTruthy();
    expect(container.textContent).toContain("Victor Osimhen");
  });
});
