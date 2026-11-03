/**
 * GTEX Skin Engine — Theme Token Resolver
 * Resolves semantic design tokens into runtime CSS custom properties and DOM state.
 */

import { LayoutPresetId, SidebarMode, SkinManifest, UserAppearancePreferences } from "./SkinManifest";

export function resolveCssVariables(skin: SkinManifest): Record<string, string> {
  const t = skin.tokens;
  return {
    "--gx-bg": t.surfaceApp,
    "--gx-bg-gradient": t.surfaceAppGradient || t.surfaceApp,
    "--gx-card": t.surfaceCard,
    "--gx-line": t.borderSubtle,
    "--gx-line-strong": t.borderStrong,
    "--gx-border-focus": t.borderFocus,

    // Typography
    "--gx-text-primary": t.textPrimary,
    "--gx-text-secondary": t.textSecondary,
    "--gx-text-muted": t.textMuted,
    "--gx-text-accent": t.textAccent,

    // Surfaces
    "--gx-surface-panel": t.surfacePanel,
    "--gx-surface-panel-gradient": t.surfacePanelGradient || t.surfacePanel,
    "--gx-surface-panel-hover": t.surfacePanelHover,
    "--gx-surface-elevated": t.surfaceElevated,
    "--gx-surface-input": t.surfaceInput,
    "--gx-surface-input-focus": t.surfaceInputFocus,
    "--gx-surface-modal": t.surfaceModal,

    // Actions
    "--gx-btn-primary-bg": t.actionPrimaryBg,
    "--gx-btn-primary-text": t.actionPrimaryText,
    "--gx-btn-primary-hover": t.actionPrimaryHover,
    "--gx-btn-secondary-bg": t.actionSecondaryBg,
    "--gx-btn-secondary-border": t.actionSecondaryBorder,
    "--gx-btn-secondary-text": t.actionSecondaryText,
    "--gx-btn-danger-bg": t.actionDangerBg,
    "--gx-btn-danger-text": t.actionDangerText,

    // Status
    "--gx-status-success": t.statusSuccess,
    "--gx-status-warning": t.statusWarning,
    "--gx-status-danger": t.statusDanger,
    "--gx-status-info": t.statusInfo,

    // Football
    "--gx-football-pitch": t.footballPitch,
    "--gx-football-live": t.footballLive,
    "--gx-football-home": t.footballHomeTeam,
    "--gx-football-away": t.footballAwayTeam,
    "--gx-prestige-accent": t.prestigeAccent,

    // Advertising
    "--gx-ad-surface": t.adsSurface,
    "--gx-ad-border": t.adsBorder,
    "--gx-ad-bg": t.adsBackground,

    // Badges
    "--gx-badge-bg": t.badgeBg,
    "--gx-badge-border": t.badgeBorder,
    "--gx-badge-text": t.badgeText,
  };
}

export function applySkinToDOM(
  skin: SkinManifest,
  layout: LayoutPresetId = "comfortable",
  sidebar: SidebarMode = "expanded",
  accessibility?: UserAppearancePreferences["accessibility"],
  dataSaver: boolean = false,
): void {
  if (typeof document === "undefined") return;

  const root = document.documentElement;
  const cssVars = resolveCssVariables(skin);

  for (const [key, value] of Object.entries(cssVars)) {
    root.style.setProperty(key, value);
  }

  // Set explicit data attributes for scoped styling
  root.setAttribute("data-skin", skin.id);
  root.setAttribute("data-skin-light", skin.capabilities.hasLightCanvas ? "true" : "false");
  root.setAttribute("data-density", layout);
  root.setAttribute("data-sidebar", sidebar);
  root.setAttribute("data-contrast", accessibility?.highContrast ? "high" : "standard");
  root.setAttribute("data-text-scale", accessibility?.textScaling || "standard");
  root.setAttribute("data-reduced-motion", accessibility?.reducedMotion ? "true" : "false");
  root.setAttribute("data-data-saver", dataSaver ? "true" : "false");
  root.setAttribute("data-focus-rings", accessibility?.visibleFocusRings ? "visible" : "default");

  // Keep body background aligned with active skin surface
  if (document.body) {
    document.body.style.backgroundColor = skin.tokens.surfaceApp;
    document.body.style.color = skin.tokens.textPrimary;
  }
}
