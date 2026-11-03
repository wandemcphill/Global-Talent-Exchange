/**
 * GTEX Skin Engine — Skin Provider & Context
 * Central state and token distribution across the GTEX React application.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useAuth } from "@/lib/auth";
import {
  DEFAULT_APPEARANCE_PREFERENCES,
  loadAppearancePreferences,
  saveAppearancePreferences,
} from "./AppearancePreferences";
import {
  LayoutPresetId,
  SidebarMode,
  SkinId,
  SkinManifest,
  UserAppearancePreferences,
} from "./SkinManifest";
import { resolveSafeSkin } from "./SkinCompatibility";
import { GTEX_MATCHDAY_SKIN, SkinRegistry } from "./SkinRegistry";
import { applySkinToDOM } from "./ThemeTokenResolver";
import { getDefaultModuleView } from "./ModuleViewRegistry";

export interface SkinContextValue {
  skin: SkinManifest;
  skinId: SkinId;
  previewSkin: SkinManifest | null;
  previewSkinId: string | null;
  availableSkins: SkinManifest[];
  layoutPreset: LayoutPresetId;
  sidebarMode: SidebarMode;
  moduleViews: Record<string, string>;
  assetPackId: string;
  accessibility: UserAppearancePreferences["accessibility"];
  dataSaver: boolean;
  isDirty: boolean;

  // Actions
  setSkin: (id: SkinId) => void;
  setLayoutPreset: (preset: LayoutPresetId) => void;
  setSidebarMode: (mode: SidebarMode) => void;
  setModuleView: (moduleKey: string, viewId: string) => void;
  getModuleView: (moduleKey: string) => string;
  setAssetPack: (packId: string) => void;
  setAccessibility: (updates: Partial<UserAppearancePreferences["accessibility"]>) => void;
  setDataSaver: (enabled: boolean) => void;
  setPreview: (id: string | null) => void;
  applyChanges: () => void;
  discardChanges: () => void;
  resetToDefault: () => void;
}

const SkinContext = createContext<SkinContextValue | null>(null);

export function SkinProvider({ children }: { children: React.ReactNode }) {
  let user: any = null;
  try {
    const auth = useAuth();
    user = auth?.user || null;
  } catch {
    user = null;
  }
  const userId = user?.id || user?.user_id || null;

  // Saved preferences in persistence
  const [persistedPrefs, setPersistedPrefs] = useState<UserAppearancePreferences>(() =>
    loadAppearancePreferences(userId),
  );

  // Staged / working preferences
  const [prefs, setPrefs] = useState<UserAppearancePreferences>(persistedPrefs);

  // Live preview skin (optional transient override without saving)
  const [previewId, setPreviewId] = useState<string | null>(null);

  // Re-hydrate preferences if authenticated user changes
  useEffect(() => {
    const loaded = loadAppearancePreferences(userId);
    setPersistedPrefs(loaded);
    setPrefs(loaded);
  }, [userId]);

  // Determine active displayed skin (preview takes precedence if set)
  const effectiveSkinId = previewId || prefs.activeSkinId;
  const activeSkin = useMemo(() => resolveSafeSkin(effectiveSkinId), [effectiveSkinId]);
  const previewSkin = useMemo(() => (previewId ? resolveSafeSkin(previewId) : null), [previewId]);
  const availableSkins = useMemo(() => SkinRegistry.getAll(), []);

  // Update DOM tokens whenever active skin, layout, or accessibility changes
  useEffect(() => {
    applySkinToDOM(
      activeSkin,
      prefs.layoutPreset,
      prefs.sidebarMode,
      prefs.accessibility,
      prefs.dataSaver,
    );
  }, [activeSkin, prefs.layoutPreset, prefs.sidebarMode, prefs.accessibility, prefs.dataSaver]);

  const setSkin = useCallback((id: SkinId) => {
    setPrefs((prev) => {
      const next = { ...prev, activeSkinId: id };
      saveAppearancePreferences(next, userId);
      return next;
    });
    setPersistedPrefs((prev) => ({ ...prev, activeSkinId: id }));
    setPreviewId(null);
  }, [userId]);

  const setLayoutPreset = useCallback((layoutPreset: LayoutPresetId) => {
    setPrefs((prev) => {
      const next = { ...prev, layoutPreset };
      saveAppearancePreferences(next, userId);
      return next;
    });
    setPersistedPrefs((prev) => ({ ...prev, layoutPreset }));
  }, [userId]);

  const setSidebarMode = useCallback((sidebarMode: SidebarMode) => {
    setPrefs((prev) => {
      const next = { ...prev, sidebarMode };
      saveAppearancePreferences(next, userId);
      return next;
    });
    setPersistedPrefs((prev) => ({ ...prev, sidebarMode }));
  }, [userId]);

  const setModuleView = useCallback((moduleKey: string, viewId: string) => {
    setPrefs((prev) => {
      const next = {
        ...prev,
        moduleViews: {
          ...prev.moduleViews,
          [moduleKey]: viewId,
        },
      };
      saveAppearancePreferences(next, userId);
      return next;
    });
    setPersistedPrefs((prev) => ({
      ...prev,
      moduleViews: {
        ...prev.moduleViews,
        [moduleKey]: viewId,
      },
    }));
  }, [userId]);

  const getModuleView = useCallback(
    (moduleKey: string): string => {
      return prefs.moduleViews?.[moduleKey] || getDefaultModuleView(moduleKey);
    },
    [prefs.moduleViews],
  );

  const setAssetPack = useCallback((assetPackId: string) => {
    setPrefs((prev) => {
      const next = { ...prev, assetPackId };
      saveAppearancePreferences(next, userId);
      return next;
    });
    setPersistedPrefs((prev) => ({ ...prev, assetPackId }));
  }, [userId]);

  const setAccessibility = useCallback(
    (updates: Partial<UserAppearancePreferences["accessibility"]>) => {
      setPrefs((prev) => {
        const next = {
          ...prev,
          accessibility: {
            ...prev.accessibility,
            ...updates,
          },
        };
        saveAppearancePreferences(next, userId);
        return next;
      });
      setPersistedPrefs((prev) => ({
        ...prev,
        accessibility: {
          ...prev.accessibility,
          ...updates,
        },
      }));
    },
    [userId],
  );

  const setDataSaver = useCallback((dataSaver: boolean) => {
    setPrefs((prev) => {
      const next = { ...prev, dataSaver };
      saveAppearancePreferences(next, userId);
      return next;
    });
    setPersistedPrefs((prev) => ({ ...prev, dataSaver }));
  }, [userId]);

  const setPreview = useCallback((id: string | null) => {
    setPreviewId(id);
  }, []);

  const applyChanges = useCallback(() => {
    if (previewId) {
      setSkin(previewId as SkinId);
      setPreviewId(null);
    }
  }, [previewId, setSkin]);

  const discardChanges = useCallback(() => {
    setPreviewId(null);
    setPrefs(persistedPrefs);
  }, [persistedPrefs]);

  const resetToDefault = useCallback(() => {
    setPreviewId(null);
    setPrefs(DEFAULT_APPEARANCE_PREFERENCES);
    setPersistedPrefs(DEFAULT_APPEARANCE_PREFERENCES);
    saveAppearancePreferences(DEFAULT_APPEARANCE_PREFERENCES, userId);
  }, [userId]);

  const isDirty = useMemo(() => {
    if (previewId !== null && previewId !== persistedPrefs.activeSkinId) return true;
    return JSON.stringify(prefs) !== JSON.stringify(persistedPrefs);
  }, [previewId, prefs, persistedPrefs]);

  const value = useMemo<SkinContextValue>(
    () => ({
      skin: activeSkin,
      skinId: activeSkin.id,
      previewSkin,
      previewSkinId: previewId,
      availableSkins,
      layoutPreset: prefs.layoutPreset,
      sidebarMode: prefs.sidebarMode,
      moduleViews: prefs.moduleViews,
      assetPackId: prefs.assetPackId,
      accessibility: prefs.accessibility,
      dataSaver: prefs.dataSaver,
      isDirty,

      setSkin,
      setLayoutPreset,
      setSidebarMode,
      setModuleView,
      getModuleView,
      setAssetPack,
      setAccessibility,
      setDataSaver,
      setPreview,
      applyChanges,
      discardChanges,
      resetToDefault,
    }),
    [
      activeSkin,
      previewSkin,
      previewId,
      availableSkins,
      prefs.layoutPreset,
      prefs.sidebarMode,
      prefs.moduleViews,
      prefs.assetPackId,
      prefs.accessibility,
      prefs.dataSaver,
      isDirty,
      setSkin,
      setLayoutPreset,
      setSidebarMode,
      setModuleView,
      getModuleView,
      setAssetPack,
      setAccessibility,
      setDataSaver,
      setPreview,
      applyChanges,
      discardChanges,
      resetToDefault,
    ],
  );

  return <SkinContext.Provider value={value}>{children}</SkinContext.Provider>;
}

const DEFAULT_FALLBACK_SKIN_CONTEXT: SkinContextValue = {
  skin: GTEX_MATCHDAY_SKIN,
  skinId: "gtex-matchday",
  previewSkin: null,
  previewSkinId: null,
  availableSkins: SkinRegistry.getAll(),
  layoutPreset: "comfortable",
  sidebarMode: "expanded",
  moduleViews: {},
  assetPackId: "standard",
  accessibility: DEFAULT_APPEARANCE_PREFERENCES.accessibility,
  dataSaver: false,
  isDirty: false,
  setSkin: () => {},
  setLayoutPreset: () => {},
  setSidebarMode: () => {},
  setModuleView: () => {},
  getModuleView: (moduleKey: string) => getDefaultModuleView(moduleKey),
  setAssetPack: () => {},
  setAccessibility: () => {},
  setDataSaver: () => {},
  setPreview: () => {},
  applyChanges: () => {},
  discardChanges: () => {},
  resetToDefault: () => {},
};

export function useSkin(): SkinContextValue {
  const context = useContext(SkinContext);
  if (!context) {
    // Fail-safe graceful fallback for isolated test harnesses or sub-trees
    return DEFAULT_FALLBACK_SKIN_CONTEXT;
  }
  return context;
}
