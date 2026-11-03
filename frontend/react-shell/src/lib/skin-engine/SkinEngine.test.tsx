declare const describe: any;
declare const test: any;
declare const it: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import {
  SkinRegistry,
  GTEX_MATCHDAY_SKIN,
  GTEX_TOUCHLINE_PRO_SKIN,
  GTEX_PRO_LIGHT_SKIN,
  GTEX_DYNASTY_SKIN,
  resolveCssVariables,
  applySkinToDOM,
  validateSkinManifest,
  resolveSafeSkin,
  isCanonicalProtectedAsset,
  scanDeclarativeManifestSecurity,
  loadAppearancePreferences,
  saveAppearancePreferences,
  clearAppearancePreferences,
  DEFAULT_APPEARANCE_PREFERENCES,
  SkinProvider,
  useSkin,
} from "./index";
import { SkinAwareAdSlot } from "@/components/advertising/SkinAwareAdSlot";

describe("GTEX Skin Engine Architecture & Token Tests", () => {
  let container: HTMLDivElement;
  let root: Root | null = null;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    localStorage.clear();
    document.documentElement.removeAttribute("data-skin");
    document.documentElement.removeAttribute("data-density");
    document.documentElement.removeAttribute("data-contrast");
    document.documentElement.removeAttribute("data-text-scale");
    document.documentElement.removeAttribute("data-reduced-motion");
    document.documentElement.removeAttribute("data-data-saver");
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

  describe("Layer 1 — Theme Skins & Skin Registry", () => {
    it("registers all official skins: Matchday, Touchline Pro, Pro Light, and Dynasty preview", () => {
      const skins = SkinRegistry.getAll();
      expect(skins.length).toBeGreaterThanOrEqual(4);

      const ids = skins.map((s) => s.id);
      expect(ids).toContain("gtex-matchday");
      expect(ids).toContain("gtex-touchline-pro");
      expect(ids).toContain("gtex-pro-light");
      expect(ids).toContain("gtex-dynasty");
    });

    it("verifies GTEX Matchday is the authoritative reference default", () => {
      const def = SkinRegistry.getDefault();
      expect(def.id).toBe("gtex-matchday");
      expect(def.isOfficial).toBe(true);
      expect(def.tokens.surfaceApp).toBe("#050811");
      expect(def.tokens.statusSuccess).toBe("#10b981");
    });

    it("verifies Touchline Pro has management tactical tokens and cyan accents", () => {
      const skin = SkinRegistry.get("gtex-touchline-pro");
      expect(skin).toBeDefined();
      expect(skin?.tokens.textAccent).toBe("#06b6d4");
      expect(skin?.tokens.surfaceApp).toBe("#070a12");
      expect(skin?.capabilities.supportsDenseLayout).toBe(true);
    });

    it("verifies Pro Light provides light canvas tokens and high contrast values", () => {
      const skin = SkinRegistry.get("gtex-pro-light");
      expect(skin).toBeDefined();
      expect(skin?.capabilities.hasLightCanvas).toBe(true);
      expect(skin?.tokens.surfaceApp).toBe("#f8fafc");
      expect(skin?.tokens.textPrimary).toBe("#0f172a");
    });

    it("verifies Dynasty preserves standard green/amber/red status colors for economic clarity", () => {
      const skin = SkinRegistry.get("gtex-dynasty");
      expect(skin).toBeDefined();
      expect(skin?.tokens.prestigeAccent).toBe("#fbbf24");
      expect(skin?.tokens.statusSuccess).toBe("#10b981");
      expect(skin?.tokens.statusWarning).toBe("#f59e0b");
      expect(skin?.tokens.statusDanger).toBe("#ef4444");
    });

    it("resolves CSS custom properties correctly from tokens", () => {
      const vars = resolveCssVariables(GTEX_MATCHDAY_SKIN);
      expect(vars["--gx-bg"]).toBe("#050811");
      expect(vars["--gx-card"]).toBe("#0b1220");
      expect(vars["--gx-text-primary"]).toBe("#f8fafc");
      expect(vars["--gx-status-success"]).toBe("#10b981");
    });

    it("applies CSS custom properties and data attributes to document.documentElement", () => {
      applySkinToDOM(GTEX_PRO_LIGHT_SKIN, "manager_dense", "compact", {
        reducedMotion: true,
        textScaling: "large",
        highContrast: true,
        visibleFocusRings: true,
      }, true);

      const htmlRoot = document.documentElement;
      expect(htmlRoot.getAttribute("data-skin")).toBe("gtex-pro-light");
      expect(htmlRoot.getAttribute("data-skin-light")).toBe("true");
      expect(htmlRoot.getAttribute("data-density")).toBe("manager_dense");
      expect(htmlRoot.getAttribute("data-sidebar")).toBe("compact");
      expect(htmlRoot.getAttribute("data-contrast")).toBe("high");
      expect(htmlRoot.getAttribute("data-text-scale")).toBe("large");
      expect(htmlRoot.getAttribute("data-reduced-motion")).toBe("true");
      expect(htmlRoot.getAttribute("data-data-saver")).toBe("true");
    });
  });

  describe("Compatibility & Safe Fallbacks", () => {
    it("validates skin manifests and catches missing tokens", () => {
      const report = validateSkinManifest(GTEX_MATCHDAY_SKIN);
      expect(report.compatible).toBe(true);
      expect(report.errors).toHaveLength(0);

      const invalidReport = validateSkinManifest({ id: "broken" });
      expect(invalidReport.compatible).toBe(false);
      expect(invalidReport.errors.length).toBeGreaterThan(0);
    });

    it("safely falls back to GTEX Matchday when skin id is unknown or missing", () => {
      const resolved = resolveSafeSkin("unknown-nonexistent-skin");
      expect(resolved.id).toBe("gtex-matchday");

      const nullResolved = resolveSafeSkin(null);
      expect(nullResolved.id).toBe("gtex-matchday");
    });
  });

  describe("User Preferences Persistence", () => {
    it("loads default preferences when storage is empty", () => {
      const prefs = loadAppearancePreferences();
      expect(prefs.activeSkinId).toBe("gtex-matchday");
      expect(prefs.layoutPreset).toBe("comfortable");
      expect(prefs.moduleViews.market).toBe("cards");
      expect(prefs.moduleViews.squad).toBe("table");
    });

    it("persists and restores updated preferences", () => {
      const updated = {
        ...DEFAULT_APPEARANCE_PREFERENCES,
        activeSkinId: "gtex-touchline-pro",
        layoutPreset: "manager_dense" as const,
        moduleViews: {
          ...DEFAULT_APPEARANCE_PREFERENCES.moduleViews,
          market: "table" as const,
        },
      };

      saveAppearancePreferences(updated, "user-123");
      const restored = loadAppearancePreferences("user-123");

      expect(restored.activeSkinId).toBe("gtex-touchline-pro");
      expect(restored.layoutPreset).toBe("manager_dense");
      expect(restored.moduleViews.market).toBe("table");
    });

    it("clears preferences safely", () => {
      saveAppearancePreferences(DEFAULT_APPEARANCE_PREFERENCES, "user-456");
      clearAppearancePreferences("user-456");
      const loaded = loadAppearancePreferences("user-456");
      expect(loaded.activeSkinId).toBe("gtex-matchday");
    });
  });

  describe("Layer 4 — Canonical Asset Protection", () => {
    it("identifies canonical player portraits, facebanks, and crests as protected", () => {
      expect(isCanonicalProtectedAsset("https://res.cloudinary.com/gtex/player/102.png")).toBe(true);
      expect(isCanonicalProtectedAsset("https://cdn.sportmonks.com/images/soccer/player/34.png")).toBe(true);
      expect(isCanonicalProtectedAsset("/assets/facebank/regen_01.png")).toBe(true);
      expect(isCanonicalProtectedAsset("/assets/legend_portraits/maradona.png")).toBe(true);
      expect(isCanonicalProtectedAsset("/assets/club_crest/lagos_fc.png")).toBe(true);
      expect(isCanonicalProtectedAsset("/assets/national_flag/ng.png")).toBe(true);
    });

    it("allows non-canonical decorative texture assets", () => {
      expect(isCanonicalProtectedAsset("gx-pitch-grid")).toBe(false);
      expect(isCanonicalProtectedAsset("/textures/stadium_lights.svg")).toBe(false);
      expect(isCanonicalProtectedAsset(null)).toBe(false);
    });
  });

  describe("Security & Declarative Package Sandboxing", () => {
    it("passes clean declarative JSON manifests", () => {
      const cleanJson = JSON.stringify({
        format: "gtex-skin-declarative-v1",
        id: "community-skin-test",
        name: "Test Skin",
        tokens: { surfaceApp: "#111" },
      });
      const result = scanDeclarativeManifestSecurity(cleanJson);
      expect(result.passed).toBe(true);
      expect(result.violations).toHaveLength(0);
    });

    it("detects and rejects executable code, scripts, eval, and iframes", () => {
      const maliciousPayloads = [
        '<script>alert("hack")</script>',
        'javascript:void(0)',
        'eval("malicious")',
        '<iframe src="http://evil.com"></iframe>',
        'url("https://malicious-external-domain.com/tracker.png")',
      ];

      for (const payload of maliciousPayloads) {
        const result = scanDeclarativeManifestSecurity(payload);
        expect(result.passed).toBe(false);
        expect(result.violations.length).toBeGreaterThan(0);
      }
    });
  });

  describe("SkinProvider Integration & React Context", () => {
    function TestConsumer() {
      const {
        skin,
        layoutPreset,
        moduleViews,
        setSkin,
        setLayoutPreset,
        setModuleView,
        resetToDefault,
      } = useSkin();

      return (
        <div>
          <span data-testid="active-skin-name">{skin.name}</span>
          <span data-testid="active-layout">{layoutPreset}</span>
          <span data-testid="market-view">{moduleViews.market}</span>
          <button data-testid="btn-set-touchline" onClick={() => setSkin("gtex-touchline-pro")}>
            Set Touchline
          </button>
          <button data-testid="btn-set-dense" onClick={() => setLayoutPreset("manager_dense")}>
            Set Dense
          </button>
          <button data-testid="btn-set-market-table" onClick={() => setModuleView("market", "table")}>
            Set Market Table
          </button>
          <button data-testid="btn-reset" onClick={resetToDefault}>
            Reset
          </button>
        </div>
      );
    }

    it("provides initial state and allows switching skins and layouts", () => {
      root = createRoot(container);
      act(() => {
        root?.render(
          <SkinProvider>
            <TestConsumer />
          </SkinProvider>
        );
      });

      const skinSpan = container.querySelector('[data-testid="active-skin-name"]');
      const layoutSpan = container.querySelector('[data-testid="active-layout"]');
      const marketSpan = container.querySelector('[data-testid="market-view"]');

      expect(skinSpan?.textContent).toBe("GTEX Matchday");
      expect(layoutSpan?.textContent).toBe("comfortable");
      expect(marketSpan?.textContent).toBe("cards");

      // Switch skin
      const btnTouchline = container.querySelector('[data-testid="btn-set-touchline"]') as HTMLButtonElement;
      act(() => {
        btnTouchline.click();
      });
      expect(container.querySelector('[data-testid="active-skin-name"]')?.textContent).toBe("GTEX Touchline Pro");

      // Switch layout
      const btnDense = container.querySelector('[data-testid="btn-set-dense"]') as HTMLButtonElement;
      act(() => {
        btnDense.click();
      });
      expect(container.querySelector('[data-testid="active-layout"]')?.textContent).toBe("manager_dense");

      // Switch market module view
      const btnTable = container.querySelector('[data-testid="btn-set-market-table"]') as HTMLButtonElement;
      act(() => {
        btnTable.click();
      });
      expect(container.querySelector('[data-testid="market-view"]')?.textContent).toBe("table");

      // Reset
      const btnReset = container.querySelector('[data-testid="btn-reset"]') as HTMLButtonElement;
      act(() => {
        btnReset.click();
      });
      expect(container.querySelector('[data-testid="active-skin-name"]')?.textContent).toBe("GTEX Matchday");
    });
  });

  describe("Commercial Advertising Stability", () => {
    it("renders stable placement identifiers regardless of active skin", () => {
      root = createRoot(container);
      act(() => {
        root?.render(
          <SkinProvider>
            <SkinAwareAdSlot placement="homepage_hero" />
          </SkinProvider>
        );
      });

      const slot = container.querySelector('[data-testid="skin-aware-ad-slot-homepage_hero"]');
      expect(slot).toBeTruthy();
      expect(slot?.getAttribute("data-placement")).toBe("homepage_hero");
      expect(slot?.getAttribute("data-skin-id")).toBe("gtex-matchday");
    });
  });
});
