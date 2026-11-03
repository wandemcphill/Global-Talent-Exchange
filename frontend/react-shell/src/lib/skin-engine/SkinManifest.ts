/**
 * GTEX Skin Engine — Skin Manifest Specification
 * Authoritative schema for GTEX themes, layout presets, and design tokens.
 */

export type SkinId =
  | "gtex-matchday"
  | "gtex-touchline-pro"
  | "gtex-pro-light"
  | "gtex-dynasty"
  | (string & {});

export type LayoutPresetId = "comfortable" | "compact" | "manager_dense";
export type SidebarMode = "expanded" | "compact";

export interface SemanticTokens {
  // Surfaces
  surfaceApp: string;
  surfaceAppGradient?: string;
  surfacePanel: string;
  surfacePanelGradient?: string;
  surfacePanelHover: string;
  surfaceElevated: string;
  surfaceInput: string;
  surfaceInputFocus: string;
  surfaceCard: string;
  surfaceModal: string;

  // Typography
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  textAccent: string;

  // Borders & Dividers
  borderSubtle: string;
  borderStrong: string;
  borderFocus: string;

  // Actions
  actionPrimaryBg: string;
  actionPrimaryText: string;
  actionPrimaryHover: string;
  actionSecondaryBg: string;
  actionSecondaryBorder: string;
  actionSecondaryText: string;
  actionDangerBg: string;
  actionDangerText: string;

  // Status & Telemetry
  statusSuccess: string;
  statusWarning: string;
  statusDanger: string;
  statusInfo: string;

  // Football & Sports Accents
  footballPitch: string;
  footballLive: string;
  footballHomeTeam: string;
  footballAwayTeam: string;
  prestigeAccent: string;

  // Commercial / Advertising Surfaces
  adsSurface: string;
  adsBorder: string;
  adsBackground: string;

  // Badges & Micro-metrics
  badgeBg: string;
  badgeBorder: string;
  badgeText: string;
}

export interface SkinCapabilities {
  supportsDenseLayout: boolean;
  supportsPitch25D: boolean;
  supportsDataSaver: boolean;
  supportsHighContrast: boolean;
  hasLightCanvas?: boolean;
}

export interface SkinManifest {
  id: SkinId;
  name: string;
  version: string;
  engineVersion: string;
  minAppVersion: string;
  author: string;
  description: string;
  tagline: string;
  category: "official" | "community" | "experimental";
  status: "active" | "preview" | "deprecated";
  isOfficial: boolean;
  tokens: SemanticTokens;
  capabilities: SkinCapabilities;
  preview: {
    accentColor: string;
    secondaryColor: string;
    backgroundColor: string;
    cardColor: string;
    badgeLabel: string;
    heroPreviewGradient?: string;
  };
  tags: string[];
}

export interface UserAppearancePreferences {
  version: number;
  activeSkinId: SkinId;
  layoutPreset: LayoutPresetId;
  sidebarMode: SidebarMode;
  moduleViews: {
    market: "cards" | "table";
    squad: "table" | "cards" | "pitch";
    profiles: "dossier" | "stats";
    match_center: "broadcast" | "tactical" | "compact";
    competitions: "discovery" | "table";
    scouting: "cards" | "table";
    [key: string]: string;
  };
  assetPackId: string;
  accessibility: {
    reducedMotion: boolean;
    textScaling: "standard" | "large" | "extra_large";
    highContrast: boolean;
    visibleFocusRings: boolean;
  };
  dataSaver: boolean;
  updatedAt: string;
}
