/**
 * GTEX Skin Engine — Appearance Studio
 * Authoritative user-facing customisation studio under:
 * PROFILE → SETTINGS → APPEARANCE STUDIO (/app/settings/appearance)
 */

import React, { useState } from "react";
import { toast } from "sonner";
import {
  Check,
  CheckCircle2,
  Columns,
  Compass,
  Contrast,
  Eye,
  Gauge,
  Layers,
  Layout,
  Maximize2,
  Minimize2,
  Palette,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Shirt,
  Sparkles,
  Swords,
  Trophy,
  Type,
  Wifi,
  WifiOff,
  Zap,
} from "lucide-react";
import { useSkin } from "@/lib/skin-engine";
import { REGISTERED_FOOTBALL_MODULES } from "@/lib/skin-engine/ModuleViewRegistry";
import { APPROVED_ASSET_PACKS } from "@/lib/skin-engine/AssetPackLoader";
import { LayoutPresetId, SidebarMode, SkinId } from "@/lib/skin-engine/SkinManifest";
import { Btn, Chip, Coin, PageHeader, Panel } from "@/components/gtex/ui";
import { PlayerCard } from "@/components/gtex/PlayerCard";

type StudioTab =
  | "my-skins"
  | "layout"
  | "football-views"
  | "graphics"
  | "accessibility"
  | "data-saver";

export default function AppearanceStudio() {
  const {
    skin,
    skinId,
    previewSkin,
    previewSkinId,
    availableSkins,
    layoutPreset,
    sidebarMode,
    moduleViews,
    assetPackId,
    accessibility,
    dataSaver,
    isDirty,
    setSkin,
    setLayoutPreset,
    setSidebarMode,
    setModuleView,
    setAssetPack,
    setAccessibility,
    setDataSaver,
    setPreview,
    applyChanges,
    discardChanges,
    resetToDefault,
  } = useSkin();

  const [activeTab, setActiveTab] = useState<StudioTab>("my-skins");

  const effectiveSkin = previewSkin || skin;

  const handleApplySkin = (id: SkinId) => {
    setSkin(id);
    toast.success(`Active skin changed to ${effectiveSkin.name}`);
  };

  const handleApplyAllChanges = () => {
    applyChanges();
    toast.success("Appearance preferences applied and saved to your profile.");
  };

  const handleDiscard = () => {
    discardChanges();
    toast.info("Unsaved appearance changes discarded.");
  };

  const handleReset = () => {
    if (window.confirm("Restore official GTEX Matchday appearance and default views?")) {
      resetToDefault();
      toast.success("Restored GTEX Matchday reference appearance.");
    }
  };

  return (
    <div className="space-y-6" data-testid="appearance-studio-page">
      {/* Studio Header */}
      <PageHeader
        eyebrow="Profile & Settings"
        title="Appearance Studio"
        sub="Personalise how GTEX looks and how football modules are presented without altering underlying game rules or economic balances."
        action={
          <div className="flex flex-wrap items-center gap-2">
            {isDirty && (
              <>
                <Btn
                  variant="ghost"
                  onClick={handleDiscard}
                  data-testid="discard-appearance-button"
                  className="text-xs"
                >
                  Discard Changes
                </Btn>
                <Btn
                  variant="primary"
                  onClick={handleApplyAllChanges}
                  data-testid="apply-appearance-button"
                  className="text-xs flex items-center gap-1.5"
                >
                  <Check size={14} /> Apply Changes
                </Btn>
              </>
            )}
            <Btn
              variant="secondary"
              onClick={handleReset}
              data-testid="restore-default-appearance-button"
              className="text-xs flex items-center gap-1.5"
            >
              <RotateCcw size={13} /> Restore Default
            </Btn>
          </div>
        }
      />

      {/* Studio Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-1.5 border-b border-white/10 pb-3">
        <button
          type="button"
          onClick={() => setActiveTab("my-skins")}
          data-testid="tab-my-skins"
          className={`gx-btn text-xs flex items-center gap-2 ${
            activeTab === "my-skins" ? "gx-btn-primary" : "gx-btn-secondary"
          }`}
        >
          <Palette size={14} /> My Skins
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("layout")}
          data-testid="tab-layout"
          className={`gx-btn text-xs flex items-center gap-2 ${
            activeTab === "layout" ? "gx-btn-primary" : "gx-btn-secondary"
          }`}
        >
          <Layout size={14} /> Layout & Density
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("football-views")}
          data-testid="tab-football-views"
          className={`gx-btn text-xs flex items-center gap-2 ${
            activeTab === "football-views" ? "gx-btn-primary" : "gx-btn-secondary"
          }`}
        >
          <Swords size={14} /> Football Views
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("graphics")}
          data-testid="tab-graphics"
          className={`gx-btn text-xs flex items-center gap-2 ${
            activeTab === "graphics" ? "gx-btn-primary" : "gx-btn-secondary"
          }`}
        >
          <Layers size={14} /> Graphics & Packs
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("accessibility")}
          data-testid="tab-accessibility"
          className={`gx-btn text-xs flex items-center gap-2 ${
            activeTab === "accessibility" ? "gx-btn-primary" : "gx-btn-secondary"
          }`}
        >
          <Contrast size={14} /> Accessibility
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("data-saver")}
          data-testid="tab-data-saver"
          className={`gx-btn text-xs flex items-center gap-2 ${
            activeTab === "data-saver" ? "gx-btn-primary" : "gx-btn-secondary"
          }`}
        >
          <Wifi size={14} /> Data Saver
        </button>
      </div>

      {/* Live Preview Notification Strip if a Preview is Active */}
      {previewSkinId && (
        <div
          data-testid="live-preview-indicator"
          className="flex items-center justify-between rounded-xl border border-amber-500/40 bg-amber-950/70 p-3.5 text-xs text-amber-200 shadow-lg"
        >
          <span className="flex items-center gap-2">
            <Eye size={15} className="text-amber-300" />
            <span>
              Previewing <b>{effectiveSkin.name}</b> · Changes are temporary until applied.
            </span>
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => handleApplySkin(previewSkinId as SkinId)}
              className="rounded-lg bg-amber-500 px-3 py-1 font-bold text-black hover:bg-amber-400 text-xs"
            >
              Apply Skin
            </button>
            <button
              type="button"
              onClick={() => setPreview(null)}
              className="rounded-lg border border-white/20 bg-black/40 px-3 py-1 font-bold text-white hover:bg-white/10 text-xs"
            >
              Exit Preview
            </button>
          </div>
        </div>
      )}

      {/* ====================================================================
          TAB 1: MY SKINS
          ==================================================================== */}
      {activeTab === "my-skins" && (
        <div className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4" data-testid="skins-grid">
            {availableSkins.map((s) => {
              const isActive = s.id === skinId && !previewSkinId;
              const isPreviewing = s.id === previewSkinId;

              return (
                <div
                  key={s.id}
                  data-testid={`skin-card-${s.id}`}
                  className={`flex flex-col justify-between rounded-2xl border p-5 transition-all duration-300 ${
                    isActive
                      ? "border-emerald-500/80 bg-slate-900/90 shadow-[0_0_28px_rgba(16,185,129,0.25)] ring-1 ring-emerald-500/50"
                      : isPreviewing
                      ? "border-amber-400 bg-slate-900/90 shadow-[0_0_24px_rgba(245,158,11,0.25)] ring-1 ring-amber-400/50"
                      : "border-white/10 bg-slate-950/60 hover:border-white/20"
                  }`}
                >
                  {/* Top Swatch & Badges */}
                  <div>
                    <div
                      className="h-28 w-full rounded-xl p-3 flex flex-col justify-between border border-white/10 shadow-inner"
                      style={{
                        background:
                          s.preview.heroPreviewGradient ||
                          `linear-gradient(135deg, ${s.preview.backgroundColor}, ${s.preview.accentColor}33)`,
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <span className="rounded-full bg-black/60 px-2 py-0.5 text-[9px] font-black uppercase text-white tracking-wider border border-white/15">
                          {s.preview.badgeLabel}
                        </span>
                        {isActive && (
                          <span className="flex items-center gap-1 rounded-full bg-emerald-500/90 px-2 py-0.5 text-[9px] font-black uppercase text-slate-950 shadow">
                            <Check size={10} /> Active
                          </span>
                        )}
                        {isPreviewing && (
                          <span className="rounded-full bg-amber-400 px-2 py-0.5 text-[9px] font-black uppercase text-slate-950 shadow">
                            Previewing
                          </span>
                        )}
                      </div>

                      {/* Swatch dots */}
                      <div className="flex items-center gap-1.5">
                        <span
                          className="size-4 rounded-full border border-white/40 shadow-sm"
                          style={{ background: s.preview.accentColor }}
                        />
                        <span
                          className="size-4 rounded-full border border-white/40 shadow-sm"
                          style={{ background: s.preview.secondaryColor }}
                        />
                        <span
                          className="size-4 rounded-full border border-white/40 shadow-sm"
                          style={{ background: s.preview.backgroundColor }}
                        />
                        <span
                          className="size-4 rounded-full border border-white/40 shadow-sm"
                          style={{ background: s.preview.cardColor }}
                        />
                      </div>
                    </div>

                    <div className="mt-4">
                      <div className="flex items-center justify-between">
                        <h3 className="gx-display text-lg font-black uppercase text-white">
                          {s.name}
                        </h3>
                        <span className="gx-mono text-[10px] text-slate-400">v{s.version}</span>
                      </div>
                      <p className="text-[11px] font-semibold text-emerald-400/90 mt-0.5">
                        {s.author} · Compatible with GTEX {s.minAppVersion}
                      </p>
                      <p className="mt-2 text-xs text-slate-300 leading-relaxed line-clamp-3">
                        {s.description}
                      </p>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-1">
                      {s.tags.map((tag) => (
                        <span
                          key={tag}
                          className="rounded bg-white/5 px-2 py-0.5 text-[9px] font-medium text-slate-400"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="mt-5 flex items-center gap-2 pt-3 border-t border-white/[0.08]">
                    <Btn
                      variant={isActive ? "ghost" : "primary"}
                      disabled={isActive}
                      onClick={() => handleApplySkin(s.id)}
                      className="flex-1 py-1.5 text-xs font-bold"
                      data-testid={`apply-skin-${s.id}`}
                    >
                      {isActive ? "Active Skin" : "Apply Skin"}
                    </Btn>
                    <Btn
                      variant="secondary"
                      onClick={() => setPreview(isPreviewing ? null : s.id)}
                      className="py-1.5 px-3 text-xs"
                      data-testid={`preview-skin-${s.id}`}
                    >
                      {isPreviewing ? "Exit" : "Preview"}
                    </Btn>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ====================================================================
          TAB 2: LAYOUT & DENSITY PRESETS
          ==================================================================== */}
      {activeTab === "layout" && (
        <div className="space-y-6">
          <Panel eyebrow="Layer 2 — Interface Density" title="Display Spacing & Information Density">
            <p className="text-xs text-slate-400 mb-4 max-w-2xl">
              Control the spatial density across the entire platform. Data-dense layouts allow
              managers to inspect dozens of metrics simultaneously without scrolling.
            </p>

            <div className="grid gap-4 md:grid-cols-3" data-testid="layout-preset-options">
              {/* Comfortable */}
              <div
                onClick={() => setLayoutPreset("comfortable")}
                data-testid="preset-comfortable"
                className={`cursor-pointer rounded-xl border p-4 transition-all ${
                  layoutPreset === "comfortable"
                    ? "border-emerald-500 bg-emerald-500/10 shadow-lg"
                    : "border-white/10 bg-slate-900/60 hover:border-white/20"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-bold text-white text-sm">Comfortable</h4>
                  {layoutPreset === "comfortable" && (
                    <span className="rounded-full bg-emerald-500 size-2" />
                  )}
                </div>
                <p className="text-xs text-slate-400">
                  Standard sports broadcast density. Generous padding, large cards, and spacious
                  metric cards.
                </p>
                <div className="mt-3 flex gap-1.5">
                  <span className="h-4 flex-1 rounded bg-white/10" />
                  <span className="h-4 flex-1 rounded bg-white/10" />
                </div>
              </div>

              {/* Compact */}
              <div
                onClick={() => setLayoutPreset("compact")}
                data-testid="preset-compact"
                className={`cursor-pointer rounded-xl border p-4 transition-all ${
                  layoutPreset === "compact"
                    ? "border-emerald-500 bg-emerald-500/10 shadow-lg"
                    : "border-white/10 bg-slate-900/60 hover:border-white/20"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-bold text-white text-sm">Compact</h4>
                  {layoutPreset === "compact" && (
                    <span className="rounded-full bg-emerald-500 size-2" />
                  )}
                </div>
                <p className="text-xs text-slate-400">
                  Streamlined spatial padding. Optimized for laptops and mid-resolution desktop
                  screens.
                </p>
                <div className="mt-3 flex gap-1">
                  <span className="h-3.5 flex-1 rounded bg-white/10" />
                  <span className="h-3.5 flex-1 rounded bg-white/10" />
                  <span className="h-3.5 flex-1 rounded bg-white/10" />
                </div>
              </div>

              {/* Manager Dense */}
              <div
                onClick={() => setLayoutPreset("manager_dense")}
                data-testid="preset-manager-dense"
                className={`cursor-pointer rounded-xl border p-4 transition-all ${
                  layoutPreset === "manager_dense"
                    ? "border-emerald-500 bg-emerald-500/10 shadow-lg"
                    : "border-white/10 bg-slate-900/60 hover:border-white/20"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-bold text-white text-sm">Manager Dense</h4>
                  {layoutPreset === "manager_dense" && (
                    <span className="rounded-full bg-emerald-500 size-2" />
                  )}
                </div>
                <p className="text-xs text-slate-400">
                  Football Manager-level high density. Tight table rows, compact headers, and maximum
                  tabular metrics.
                </p>
                <div className="mt-3 flex gap-0.5">
                  <span className="h-2.5 flex-1 rounded bg-white/10" />
                  <span className="h-2.5 flex-1 rounded bg-white/10" />
                  <span className="h-2.5 flex-1 rounded bg-white/10" />
                  <span className="h-2.5 flex-1 rounded bg-white/10" />
                </div>
              </div>
            </div>
          </Panel>

          <Panel eyebrow="Navigation Style" title="Sidebar Display Mode">
            <div className="grid gap-4 sm:grid-cols-2 max-w-xl">
              <label
                onClick={() => setSidebarMode("expanded")}
                className={`cursor-pointer flex items-center justify-between rounded-xl border p-4 ${
                  sidebarMode === "expanded"
                    ? "border-emerald-500 bg-emerald-500/10"
                    : "border-white/10 bg-slate-900/60"
                }`}
              >
                <div>
                  <h4 className="font-bold text-white text-sm">Expanded Sidebar</h4>
                  <p className="text-xs text-slate-400 mt-0.5">Full categories and descriptive labels</p>
                </div>
                <input
                  type="radio"
                  name="sidebar-mode"
                  checked={sidebarMode === "expanded"}
                  onChange={() => setSidebarMode("expanded")}
                  className="text-emerald-500"
                />
              </label>

              <label
                onClick={() => setSidebarMode("compact")}
                className={`cursor-pointer flex items-center justify-between rounded-xl border p-4 ${
                  sidebarMode === "compact"
                    ? "border-emerald-500 bg-emerald-500/10"
                    : "border-white/10 bg-slate-900/60"
                }`}
              >
                <div>
                  <h4 className="font-bold text-white text-sm">Compact Rail</h4>
                  <p className="text-xs text-slate-400 mt-0.5">Icon navigation for maximum viewport width</p>
                </div>
                <input
                  type="radio"
                  name="sidebar-mode"
                  checked={sidebarMode === "compact"}
                  onChange={() => setSidebarMode("compact")}
                  className="text-emerald-500"
                />
              </label>
            </div>
          </Panel>
        </div>
      )}

      {/* ====================================================================
          TAB 3: FOOTBALL VIEWS
          ==================================================================== */}
      {activeTab === "football-views" && (
        <div className="space-y-6">
          <Panel
            eyebrow="Layer 3 — Football Modules"
            title="Module Presentation Modes"
          >
            <p className="text-xs text-slate-400 mb-6 max-w-2xl">
              Select how specific football activities are visualized. Presentation modes render the
              exact same authoritative game data and player identity through different visual lenses.
            </p>

            <div className="grid gap-6 md:grid-cols-2">
              {Object.values(REGISTERED_FOOTBALL_MODULES).map((mod) => {
                const currentView = moduleViews[mod.moduleKey] || mod.defaultView;

                return (
                  <div
                    key={mod.moduleKey}
                    data-testid={`module-setting-${mod.moduleKey}`}
                    className="flex flex-col justify-between rounded-xl border border-white/10 bg-slate-900/60 p-4 space-y-4"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <h4 className="gx-display text-base font-black uppercase text-white">
                          {mod.title}
                        </h4>
                        <span className="rounded bg-white/5 px-2 py-0.5 text-[9px] font-bold text-slate-400 uppercase">
                          {currentView}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">{mod.description}</p>
                    </div>

                    <div className="grid gap-2">
                      {mod.views.map((v) => {
                        const isSelected = currentView === v.id;
                        return (
                          <button
                            key={v.id}
                            type="button"
                            onClick={() => setModuleView(mod.moduleKey, v.id)}
                            data-testid={`view-option-${mod.moduleKey}-${v.id}`}
                            className={`flex items-start justify-between rounded-lg p-3 text-left transition-all ${
                              isSelected
                                ? "border border-emerald-500 bg-emerald-500/10 shadow-sm"
                                : "border border-white/5 bg-black/40 hover:border-white/15"
                            }`}
                          >
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-white text-xs">{v.label}</span>
                                {v.badge && (
                                  <span className="rounded bg-white/10 px-1.5 py-0.2 text-[8px] font-black uppercase text-slate-300">
                                    {v.badge}
                                  </span>
                                )}
                              </div>
                              <p className="text-[11px] text-slate-400 mt-0.5">{v.description}</p>
                            </div>
                            {isSelected && <Check size={14} className="text-emerald-400 shrink-0 mt-0.5" />}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </Panel>
        </div>
      )}

      {/* ====================================================================
          TAB 4: GRAPHICS & ASSET PACKS
          ==================================================================== */}
      {activeTab === "graphics" && (
        <div className="space-y-6">
          <Panel
            eyebrow="Layer 4 — Visual Assets"
            title="Approved Interface Textures & Stadium Ambience"
          >
            <p className="text-xs text-slate-400 mb-6 max-w-2xl">
              Approved decorative asset packs. Canonical player portraits, regen facebanks, legend
              portraits, and club crests remain strictly protected and authoritative.
            </p>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {APPROVED_ASSET_PACKS.map((pack) => {
                const isSelected = assetPackId === pack.id;

                return (
                  <div
                    key={pack.id}
                    onClick={() => setAssetPack(pack.id)}
                    data-testid={`asset-pack-${pack.id}`}
                    className={`cursor-pointer rounded-xl border p-4 transition-all ${
                      isSelected
                        ? "border-emerald-500 bg-emerald-500/10 shadow-lg"
                        : "border-white/10 bg-slate-900/60 hover:border-white/20"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-bold text-white text-sm">{pack.name}</h4>
                      {isSelected && <Check size={14} className="text-emerald-400" />}
                    </div>
                    <p className="text-xs text-slate-400">{pack.description}</p>
                    <div className={`mt-3 h-12 w-full rounded-lg border border-white/10 ${pack.cssClass}`} />
                  </div>
                );
              })}
            </div>
          </Panel>
        </div>
      )}

      {/* ====================================================================
          TAB 5: ACCESSIBILITY
          ==================================================================== */}
      {activeTab === "accessibility" && (
        <div className="space-y-6">
          <Panel
            eyebrow="WCAG 2.2 AA Compliance"
            title="Visual & Motor Accessibility Controls"
          >
            <div className="grid gap-4 md:grid-cols-2 max-w-2xl">
              {/* Reduced Motion */}
              <label
                data-testid="toggle-reduced-motion"
                className="flex items-center justify-between rounded-xl border border-white/10 bg-slate-900/60 p-4 cursor-pointer hover:border-white/20"
              >
                <div>
                  <h4 className="font-bold text-white text-sm">Reduced Motion</h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Suppress rise animations and pulsing live dots
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={accessibility.reducedMotion}
                  onChange={(e) => setAccessibility({ reducedMotion: e.target.checked })}
                  className="rounded border-white/20 text-emerald-500"
                />
              </label>

              {/* High Contrast */}
              <label
                data-testid="toggle-high-contrast"
                className="flex items-center justify-between rounded-xl border border-white/10 bg-slate-900/60 p-4 cursor-pointer hover:border-white/20"
              >
                <div>
                  <h4 className="font-bold text-white text-sm">Enhanced Contrast</h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Strengthen panel borders and high-contrast dividing lines
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={accessibility.highContrast}
                  onChange={(e) => setAccessibility({ highContrast: e.target.checked })}
                  className="rounded border-white/20 text-emerald-500"
                />
              </label>

              {/* Visible Focus Rings */}
              <label
                data-testid="toggle-focus-rings"
                className="flex items-center justify-between rounded-xl border border-white/10 bg-slate-900/60 p-4 cursor-pointer hover:border-white/20"
              >
                <div>
                  <h4 className="font-bold text-white text-sm">Focus Indicators</h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Display thick outline on active keyboard elements
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={accessibility.visibleFocusRings}
                  onChange={(e) => setAccessibility({ visibleFocusRings: e.target.checked })}
                  className="rounded border-white/20 text-emerald-500"
                />
              </label>

              {/* Text Scaling */}
              <div
                data-testid="select-text-scaling"
                className="rounded-xl border border-white/10 bg-slate-900/60 p-4 space-y-2"
              >
                <div>
                  <h4 className="font-bold text-white text-sm">Text Scaling</h4>
                  <p className="text-xs text-slate-400 mt-0.5">Scale typography platform-wide</p>
                </div>
                <select
                  value={accessibility.textScaling}
                  onChange={(e) =>
                    setAccessibility({ textScaling: e.target.value as any })
                  }
                  className="gx-input py-1 text-xs"
                >
                  <option value="standard">Standard (100%)</option>
                  <option value="large">Large (+10%)</option>
                  <option value="extra_large">Extra Large (+25%)</option>
                </select>
              </div>
            </div>
          </Panel>
        </div>
      )}

      {/* ====================================================================
          TAB 6: DATA SAVER
          ==================================================================== */}
      {activeTab === "data-saver" && (
        <div className="space-y-6">
          <Panel
            eyebrow="Bandwidth Optimization"
            title="Data Saver & Performance Mode"
          >
            <p className="text-xs text-slate-400 mb-4 max-w-2xl">
              Reduce network overhead for mobile connections. Defer non-critical decorative graphics
              while keeping all authoritative financial ledgers and player stats active.
            </p>

            <div className="max-w-xl">
              <label
                data-testid="toggle-data-saver"
                className="flex items-center justify-between rounded-xl border border-white/10 bg-slate-900/60 p-4 cursor-pointer hover:border-white/20"
              >
                <div className="flex items-center gap-3">
                  <span className="flex size-9 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400">
                    {dataSaver ? <WifiOff size={18} /> : <Wifi size={18} />}
                  </span>
                  <div>
                    <h4 className="font-bold text-white text-sm">Enable Data Saver</h4>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {dataSaver
                        ? "Active: Nonessential graphics deferred"
                        : "Off: Full broadcast graphics and high-res assets"}
                    </p>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={dataSaver}
                  onChange={(e) => setDataSaver(e.target.checked)}
                  className="rounded border-white/20 text-emerald-500"
                />
              </label>
            </div>
          </Panel>
        </div>
      )}

      {/* ====================================================================
          INTERACTIVE LIVE PREVIEW BAR (Part 11 Requirement)
          Shows realistic sample components under active/preview skin tokens!
          ==================================================================== */}
      <Panel
        eyebrow="Live Experience Sandbox"
        title={`Rendered Simulator · ${effectiveSkin.name}`}
      >
        <p className="text-xs text-slate-400 mb-5">
          Real-time preview of how semantic design tokens, density rules, and display modes render
          across key GTEX touchpoints.
        </p>

        <div className="grid gap-6 lg:grid-cols-12 items-start" data-testid="live-preview-sandbox">
          {/* Sample 1: Player Card */}
          <div className="lg:col-span-4 flex flex-col items-center">
            <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider mb-2">
              Player Market Touchpoint
            </p>
            <PlayerCard
              name="Victor Osimhen"
              rating={89}
              position="FWD"
              nationality="Nigeria"
              club="Galatasaray"
              tier="legendary"
              badge="MARQUEE TALISMAN"
              stats={[
                { k: "Value", v: "14.5k GTX" },
                { k: "PAC", v: 92 },
                { k: "SHO", v: 88 },
                { k: "PHY", v: 90 },
              ]}
              footer={
                <Btn variant="primary" className="w-full text-xs py-1">
                  Sign · <Coin amount={14500} />
                </Btn>
              }
            />
          </div>

          {/* Sample 2: Tactical & Financial Telemetry */}
          <div className="lg:col-span-8 space-y-4">
            <p className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">
              Management & Vault Telemetry
            </p>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-white/10 bg-slate-900/60 p-3">
                <span className="text-[10px] font-bold uppercase text-slate-400">Club Cash</span>
                <p className="gx-mono text-lg font-black text-white mt-1">
                  <Coin amount={245000} />
                </p>
              </div>
              <div className="rounded-xl border border-white/10 bg-slate-900/60 p-3">
                <span className="text-[10px] font-bold uppercase text-slate-400">Tactical Acumen</span>
                <p className="gx-mono text-lg font-black text-emerald-400 mt-1">88 / 100</p>
              </div>
              <div className="rounded-xl border border-white/10 bg-slate-900/60 p-3">
                <span className="text-[10px] font-bold uppercase text-slate-400">Prestige Standing</span>
                <p className="gx-mono text-lg font-black text-amber-300 mt-1">Tier 1 Sovereign</p>
              </div>
            </div>

            {/* Sample Squad Row in Manager Dense mode */}
            <div className="rounded-xl border border-white/10 bg-slate-950/80 p-3">
              <span className="text-[10px] font-bold uppercase text-slate-400">
                Squad Roster Table Mode
              </span>
              <div className="mt-2 flex items-center justify-between text-xs py-1.5 border-b border-white/10">
                <span className="font-mono text-amber-400 font-bold">ST #9</span>
                <span className="font-bold text-white">Victor Osimhen</span>
                <span className="font-mono text-emerald-400 font-bold">OVR 89</span>
                <span className="gx-chip border-emerald-500/40 text-emerald-300">Match Fit</span>
              </div>
            </div>
          </div>
        </div>
      </Panel>
    </div>
  );
}
