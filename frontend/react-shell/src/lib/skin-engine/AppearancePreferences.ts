/**
 * GTEX Skin Engine — User Appearance Preferences
 * Persistence and state restoration for visual skins, density presets, and football views.
 */

import { UserAppearancePreferences } from "./SkinManifest";

export const PREFERENCES_STORAGE_KEY = "gtex_appearance_prefs_v1";
export const PREFERENCES_SCHEMA_VERSION = 1;

export const DEFAULT_APPEARANCE_PREFERENCES: UserAppearancePreferences = {
  version: PREFERENCES_SCHEMA_VERSION,
  activeSkinId: "gtex-matchday",
  layoutPreset: "comfortable",
  sidebarMode: "expanded",
  moduleViews: {
    market: "cards",
    squad: "table",
    profiles: "dossier",
    match_center: "broadcast",
    competitions: "discovery",
    scouting: "cards",
  },
  assetPackId: "pack-pitch-grid",
  accessibility: {
    reducedMotion: false,
    textScaling: "standard",
    highContrast: false,
    visibleFocusRings: false,
  },
  dataSaver: false,
  updatedAt: new Date().toISOString(),
};

function getScopedKey(userId?: string | null): string {
  return userId ? `${PREFERENCES_STORAGE_KEY}_${userId}` : PREFERENCES_STORAGE_KEY;
}

export function loadAppearancePreferences(userId?: string | null): UserAppearancePreferences {
  if (typeof window === "undefined" || !window.localStorage) {
    return DEFAULT_APPEARANCE_PREFERENCES;
  }

  try {
    const key = getScopedKey(userId);
    const raw = window.localStorage.getItem(key) || window.localStorage.getItem(PREFERENCES_STORAGE_KEY);
    if (!raw) {
      return DEFAULT_APPEARANCE_PREFERENCES;
    }

    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") {
      return DEFAULT_APPEARANCE_PREFERENCES;
    }

    // Merge with defaults to guarantee all fields exist even after engine updates
    return {
      ...DEFAULT_APPEARANCE_PREFERENCES,
      ...parsed,
      moduleViews: {
        ...DEFAULT_APPEARANCE_PREFERENCES.moduleViews,
        ...(parsed.moduleViews || {}),
      },
      accessibility: {
        ...DEFAULT_APPEARANCE_PREFERENCES.accessibility,
        ...(parsed.accessibility || {}),
      },
    };
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("Failed to read appearance preferences from storage. Using defaults.", err);
    return DEFAULT_APPEARANCE_PREFERENCES;
  }
}

export function saveAppearancePreferences(
  prefs: UserAppearancePreferences,
  userId?: string | null,
): void {
  if (typeof window === "undefined" || !window.localStorage) return;

  try {
    const updated: UserAppearancePreferences = {
      ...prefs,
      version: PREFERENCES_SCHEMA_VERSION,
      updatedAt: new Date().toISOString(),
    };

    const payload = JSON.stringify(updated);
    const key = getScopedKey(userId);
    window.localStorage.setItem(key, payload);

    // Also persist to global key for guest / pre-auth rendering
    window.localStorage.setItem(PREFERENCES_STORAGE_KEY, payload);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("Failed to write appearance preferences to storage.", err);
  }
}

export function clearAppearancePreferences(userId?: string | null): void {
  if (typeof window === "undefined" || !window.localStorage) return;

  try {
    const key = getScopedKey(userId);
    window.localStorage.removeItem(key);
    window.localStorage.removeItem(PREFERENCES_STORAGE_KEY);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("Failed to clear appearance preferences.", err);
  }
}
