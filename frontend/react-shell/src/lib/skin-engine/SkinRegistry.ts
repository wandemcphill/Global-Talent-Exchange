/**
 * GTEX Skin Engine — Official Skin Registry
 * Official skins: GTEX Matchday, GTEX Touchline Pro, GTEX Pro Light, GTEX Dynasty.
 */

import { SkinManifest } from "./SkinManifest";

export const GTEX_MATCHDAY_SKIN: SkinManifest = {
  id: "gtex-matchday",
  name: "GTEX Matchday",
  version: "1.0.0",
  engineVersion: "1.0.0",
  minAppVersion: "2027.1",
  author: "GTEX Creative Engine",
  description:
    "The canonical GTEX 2027 reference skin. Midnight navy, emerald stadium glow, champagne gold accents, and balanced broadcast density.",
  tagline: "Authoritative broadcast matchday experience",
  category: "official",
  status: "active",
  isOfficial: true,
  tokens: {
    surfaceApp: "#050811",
    surfaceAppGradient: "linear-gradient(180deg, #050811 0%, #03060c 100%)",
    surfacePanel: "rgba(11, 18, 32, 0.92)",
    surfacePanelGradient:
      "linear-gradient(155deg, rgba(17, 27, 48, 0.86) 0%, rgba(9, 15, 28, 0.94) 65%, rgba(6, 10, 20, 0.98) 100%)",
    surfacePanelHover: "rgba(16, 26, 46, 0.96)",
    surfaceElevated: "#0f1a2e",
    surfaceInput: "rgba(3, 6, 14, 0.85)",
    surfaceInputFocus: "rgba(5, 10, 22, 0.95)",
    surfaceCard: "#0b1220",
    surfaceModal: "#070b14",

    textPrimary: "#f8fafc",
    textSecondary: "#94a3b8",
    textMuted: "#64748b",
    textAccent: "#10b981",

    borderSubtle: "rgba(255, 255, 255, 0.11)",
    borderStrong: "rgba(255, 255, 255, 0.22)",
    borderFocus: "#10b981",

    actionPrimaryBg: "linear-gradient(135deg, #34d399 0%, #10b981 55%, #059669 100%)",
    actionPrimaryText: "#022c22",
    actionPrimaryHover: "linear-gradient(135deg, #6ee7b7 0%, #10b981 55%, #047857 100%)",
    actionSecondaryBg: "rgba(255, 255, 255, 0.05)",
    actionSecondaryBorder: "rgba(255, 255, 255, 0.15)",
    actionSecondaryText: "#f1f5f9",
    actionDangerBg: "rgba(239, 68, 68, 0.14)",
    actionDangerText: "#fca5a5",

    statusSuccess: "#10b981",
    statusWarning: "#f59e0b",
    statusDanger: "#ef4444",
    statusInfo: "#38bdf8",

    footballPitch: "#0c3827",
    footballLive: "#10b981",
    footballHomeTeam: "#10b981",
    footballAwayTeam: "#f59e0b",
    prestigeAccent: "#f59e0b",

    adsSurface: "#071421",
    adsBorder: "rgba(16, 185, 129, 0.45)",
    adsBackground:
      "radial-gradient(ellipse at 0% 50%, rgba(16, 185, 129, 0.17), transparent 38%), linear-gradient(110deg, #071421 0%, #0b1728 48%, #121326 100%)",

    badgeBg: "rgba(16, 185, 129, 0.15)",
    badgeBorder: "rgba(16, 185, 129, 0.35)",
    badgeText: "#34d399",
  },
  capabilities: {
    supportsDenseLayout: true,
    supportsPitch25D: true,
    supportsDataSaver: true,
    supportsHighContrast: true,
    hasLightCanvas: false,
  },
  preview: {
    accentColor: "#10b981",
    secondaryColor: "#f59e0b",
    backgroundColor: "#050811",
    cardColor: "#0b1220",
    badgeLabel: "OFFICIAL DEFAULT",
    heroPreviewGradient: "linear-gradient(135deg, #050811, #0a1f18 60%, #050811)",
  },
  tags: ["Official", "Default", "Broadcast", "Emerald", "Dark"],
};

export const GTEX_TOUCHLINE_PRO_SKIN: SkinManifest = {
  id: "gtex-touchline-pro",
  name: "GTEX Touchline Pro",
  version: "1.0.0",
  engineVersion: "1.0.0",
  minAppVersion: "2027.1",
  author: "GTEX Football Operations",
  description:
    "Football Manager-inspired dugout skin engineered for maximum statistical density, rapid multi-column scanning, and deep tactical analysis.",
  tagline: "High-density management intelligence",
  category: "official",
  status: "active",
  isOfficial: true,
  tokens: {
    surfaceApp: "#070a12",
    surfaceAppGradient: "linear-gradient(180deg, #070a12 0%, #04060b 100%)",
    surfacePanel: "rgba(13, 19, 32, 0.95)",
    surfacePanelGradient:
      "linear-gradient(160deg, rgba(16, 23, 38, 0.98) 0%, rgba(10, 15, 27, 0.98) 100%)",
    surfacePanelHover: "rgba(20, 30, 48, 0.98)",
    surfaceElevated: "#121b2d",
    surfaceInput: "#04070f",
    surfaceInputFocus: "#080e1d",
    surfaceCard: "#0d1422",
    surfaceModal: "#080d17",

    textPrimary: "#f1f5f9",
    textSecondary: "#94a3b8",
    textMuted: "#64748b",
    textAccent: "#06b6d4",

    borderSubtle: "rgba(255, 255, 255, 0.14)",
    borderStrong: "rgba(255, 255, 255, 0.28)",
    borderFocus: "#06b6d4",

    actionPrimaryBg: "linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)",
    actionPrimaryText: "#082f49",
    actionPrimaryHover: "linear-gradient(135deg, #22d3ee 0%, #06b6d4 100%)",
    actionSecondaryBg: "rgba(255, 255, 255, 0.04)",
    actionSecondaryBorder: "rgba(255, 255, 255, 0.16)",
    actionSecondaryText: "#e2e8f0",
    actionDangerBg: "rgba(239, 68, 68, 0.14)",
    actionDangerText: "#fca5a5",

    statusSuccess: "#10b981",
    statusWarning: "#f59e0b",
    statusDanger: "#ef4444",
    statusInfo: "#06b6d4",

    footballPitch: "#082f1f",
    footballLive: "#06b6d4",
    footballHomeTeam: "#06b6d4",
    footballAwayTeam: "#f59e0b",
    prestigeAccent: "#38bdf8",

    adsSurface: "#09121f",
    adsBorder: "rgba(6, 182, 212, 0.4)",
    adsBackground:
      "radial-gradient(ellipse at 0% 50%, rgba(6, 182, 212, 0.15), transparent 40%), linear-gradient(110deg, #08111d 0%, #0d1a29 100%)",

    badgeBg: "rgba(6, 182, 212, 0.15)",
    badgeBorder: "rgba(6, 182, 212, 0.35)",
    badgeText: "#22d3ee",
  },
  capabilities: {
    supportsDenseLayout: true,
    supportsPitch25D: true,
    supportsDataSaver: true,
    supportsHighContrast: true,
    hasLightCanvas: false,
  },
  preview: {
    accentColor: "#06b6d4",
    secondaryColor: "#10b981",
    backgroundColor: "#070a12",
    cardColor: "#0d1422",
    badgeLabel: "TACTICAL PRO",
    heroPreviewGradient: "linear-gradient(135deg, #070a12, #08212e 60%, #070a12)",
  },
  tags: ["Tactical", "Football Manager", "High-Density", "Cyan", "Analytical"],
};

export const GTEX_PRO_LIGHT_SKIN: SkinManifest = {
  id: "gtex-pro-light",
  name: "GTEX Pro Light",
  version: "1.0.0",
  engineVersion: "1.0.0",
  minAppVersion: "2027.1",
  author: "GTEX Design Systems",
  description:
    "Sophisticated daylight and analytical light skin. Crisp porcelain surfaces, slate typography, high-contrast tables, and emerald accents.",
  tagline: "Precision daylight analytical skin",
  category: "official",
  status: "active",
  isOfficial: true,
  tokens: {
    surfaceApp: "#f8fafc",
    surfaceAppGradient: "linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)",
    surfacePanel: "#ffffff",
    surfacePanelGradient: "linear-gradient(165deg, #ffffff 0%, #f8fafc 100%)",
    surfacePanelHover: "#f8fafc",
    surfaceElevated: "#ffffff",
    surfaceInput: "#ffffff",
    surfaceInputFocus: "#ffffff",
    surfaceCard: "#ffffff",
    surfaceModal: "#ffffff",

    textPrimary: "#0f172a",
    textSecondary: "#334155",
    textMuted: "#64748b",
    textAccent: "#059669",

    borderSubtle: "#e2e8f0",
    borderStrong: "#cbd5e1",
    borderFocus: "#059669",

    actionPrimaryBg: "linear-gradient(135deg, #059669 0%, #047857 100%)",
    actionPrimaryText: "#ffffff",
    actionPrimaryHover: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
    actionSecondaryBg: "#f1f5f9",
    actionSecondaryBorder: "#cbd5e1",
    actionSecondaryText: "#0f172a",
    actionDangerBg: "#fee2e2",
    actionDangerText: "#991b1b",

    statusSuccess: "#059669",
    statusWarning: "#d97706",
    statusDanger: "#dc2626",
    statusInfo: "#0284c7",

    footballPitch: "#166534",
    footballLive: "#059669",
    footballHomeTeam: "#059669",
    footballAwayTeam: "#d97706",
    prestigeAccent: "#059669",

    adsSurface: "#f8fafc",
    adsBorder: "#cbd5e1",
    adsBackground:
      "radial-gradient(ellipse at 0% 50%, rgba(5, 150, 105, 0.08), transparent 45%), linear-gradient(110deg, #ffffff 0%, #f8fafc 100%)",

    badgeBg: "rgba(5, 150, 105, 0.1)",
    badgeBorder: "rgba(5, 150, 105, 0.3)",
    badgeText: "#047857",
  },
  capabilities: {
    supportsDenseLayout: true,
    supportsPitch25D: true,
    supportsDataSaver: true,
    supportsHighContrast: true,
    hasLightCanvas: true,
  },
  preview: {
    accentColor: "#059669",
    secondaryColor: "#0284c7",
    backgroundColor: "#f8fafc",
    cardColor: "#ffffff",
    badgeLabel: "PRO LIGHT",
    heroPreviewGradient: "linear-gradient(135deg, #f8fafc, #ecfdf5 60%, #f8fafc)",
  },
  tags: ["Light", "Clean", "Daylight", "High-Contrast", "Slate", "WCAG AAA"],
};

export const GTEX_DYNASTY_SKIN: SkinManifest = {
  id: "gtex-dynasty",
  name: "GTEX Dynasty",
  version: "1.0.0",
  engineVersion: "1.0.0",
  minAppVersion: "2027.1",
  author: "GTEX Executive Chamber",
  description:
    "Prestige club ownership skin. Deep obsidian surfaces, warm champagne tones, and metallic gold accents for high-roller boardrooms.",
  tagline: "Prestige club ownership & boardroom luxury",
  category: "official",
  status: "preview",
  isOfficial: true,
  tokens: {
    surfaceApp: "#08080a",
    surfaceAppGradient: "linear-gradient(180deg, #08080a 0%, #050507 100%)",
    surfacePanel: "rgba(18, 15, 12, 0.94)",
    surfacePanelGradient:
      "linear-gradient(155deg, rgba(28, 22, 16, 0.95) 0%, rgba(14, 11, 9, 0.98) 100%)",
    surfacePanelHover: "rgba(35, 28, 20, 0.98)",
    surfaceElevated: "#231a12",
    surfaceInput: "#070504",
    surfaceInputFocus: "#140f09",
    surfaceCard: "#130f0a",
    surfaceModal: "#0b0907",

    textPrimary: "#fdf8ee",
    textSecondary: "#d6c7b2",
    textMuted: "#8f8272",
    textAccent: "#f59e0b",

    borderSubtle: "rgba(245, 158, 11, 0.22)",
    borderStrong: "rgba(245, 158, 11, 0.45)",
    borderFocus: "#f59e0b",

    actionPrimaryBg: "linear-gradient(135deg, #fde047 0%, #f59e0b 58%, #d97706 100%)",
    actionPrimaryText: "#090602",
    actionPrimaryHover: "linear-gradient(135deg, #fef08a 0%, #fbbf24 58%, #b45309 100%)",
    actionSecondaryBg: "rgba(245, 158, 11, 0.08)",
    actionSecondaryBorder: "rgba(245, 158, 11, 0.3)",
    actionSecondaryText: "#fdf8ee",
    actionDangerBg: "rgba(239, 68, 68, 0.14)",
    actionDangerText: "#fca5a5",

    // Status colors strictly preserved for economic clarity
    statusSuccess: "#10b981",
    statusWarning: "#f59e0b",
    statusDanger: "#ef4444",
    statusInfo: "#38bdf8",

    footballPitch: "#1c2b18",
    footballLive: "#f59e0b",
    footballHomeTeam: "#f59e0b",
    footballAwayTeam: "#ffffff",
    prestigeAccent: "#fbbf24",

    adsSurface: "#14100b",
    adsBorder: "rgba(245, 158, 11, 0.35)",
    adsBackground:
      "radial-gradient(ellipse at 0% 50%, rgba(245, 158, 11, 0.12), transparent 45%), linear-gradient(110deg, #14100b 0%, #1e1710 100%)",

    badgeBg: "rgba(245, 158, 11, 0.18)",
    badgeBorder: "rgba(245, 158, 11, 0.45)",
    badgeText: "#fbbf24",
  },
  capabilities: {
    supportsDenseLayout: true,
    supportsPitch25D: true,
    supportsDataSaver: true,
    supportsHighContrast: true,
    hasLightCanvas: false,
  },
  preview: {
    accentColor: "#f59e0b",
    secondaryColor: "#fbbf24",
    backgroundColor: "#08080a",
    cardColor: "#130f0a",
    badgeLabel: "DYNASTY PREVIEW",
    heroPreviewGradient: "linear-gradient(135deg, #08080a, #281d09 60%, #08080a)",
  },
  tags: ["Luxury", "Gold", "Prestige", "Owner", "Obsidian"],
};

const OFFICIAL_SKINS: SkinManifest[] = [
  GTEX_MATCHDAY_SKIN,
  GTEX_TOUCHLINE_PRO_SKIN,
  GTEX_PRO_LIGHT_SKIN,
  GTEX_DYNASTY_SKIN,
];

class SkinRegistryImpl {
  private registry: Map<string, SkinManifest> = new Map();

  constructor() {
    for (const skin of OFFICIAL_SKINS) {
      this.registry.set(skin.id, skin);
    }
  }

  public getAll(): SkinManifest[] {
    return Array.from(this.registry.values());
  }

  public get(id: string): SkinManifest | undefined {
    return this.registry.get(id);
  }

  public getDefault(): SkinManifest {
    return GTEX_MATCHDAY_SKIN;
  }

  public register(skin: SkinManifest): void {
    if (!skin || !skin.id) {
      throw new Error("Invalid skin manifest: missing id");
    }
    this.registry.set(skin.id, skin);
  }

  public isRegistered(id: string): boolean {
    return this.registry.has(id);
  }
}

export const SkinRegistry = new SkinRegistryImpl();
