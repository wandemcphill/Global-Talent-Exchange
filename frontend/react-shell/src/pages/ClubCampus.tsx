import React, { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import {
  Building2,
  Hammer,
  Sparkles,
  Shield,
  Users,
  TrendingUp,
  HeartPulse,
  GraduationCap,
  Layers,
  CheckCircle2,
  Clock,
  ArrowUpRight,
  Compass,
  Wrench,
  Eye,
  Trash2,
} from "lucide-react";
import { api } from "@/lib/api";
import { useActiveClub, useClubCampus, useRefreshOwner, fmt } from "@/lib/owner";
import { publicAssetPath } from "@/lib/publicPath";
import { CampusBuilder3D, CampusModuleInstance } from "@/components/gtex/CampusBuilder3D";

const resolveImg = (url?: string) => {
  if (!url) return publicAssetPath("/img/prestige/06_academy_campus_aerial_a.png");
  if (url.startsWith("http") || url.startsWith("data:")) return url;
  const clean = url.replace(/^\/console\//, "/");
  return publicAssetPath(clean);
};

const STAGE_LABELS: Record<string, { label: string; short: string; step: number; color: string }> = {
  site_prep: {
    label: "1. Site Preparation & Perimeter Fencing",
    short: "1. Site Prep",
    step: 1,
    color: "text-amber-300 bg-amber-500/15 border-amber-500/30",
  },
  groundworks: {
    label: "2. Excavation & Deep Groundworks",
    short: "2. Groundworks",
    step: 2,
    color: "text-amber-300 bg-amber-500/15 border-amber-500/30",
  },
  foundations: {
    label: "3. Concrete Foundations & Rebar Cages",
    short: "3. Foundations",
    step: 3,
    color: "text-orange-300 bg-orange-500/15 border-orange-500/30",
  },
  structural: {
    label: "4. Structural Steel Frame & Tower Crane",
    short: "4. Structural",
    step: 4,
    color: "text-sky-300 bg-sky-500/15 border-sky-500/30",
  },
  finishing: {
    label: "5. Facade Glazing & MEP Fit-Out (Ready)",
    short: "5. Finishing",
    step: 5,
    color: "text-purple-300 bg-purple-500/15 border-purple-500/30",
  },
  completed: {
    label: "6. Operational & Safety Certified",
    short: "6. Completed",
    step: 6,
    color: "text-emerald-300 bg-emerald-500/15 border-emerald-500/30",
  },
};

const ORDERED_STAGES = [
  "site_prep",
  "groundworks",
  "foundations",
  "structural",
  "finishing",
  "completed",
] as const;

export default function ClubCampus() {
  const { clubs, active, select } = useActiveClub();
  const clubId = active?.club_id;
  const { data: campus, isLoading } = useClubCampus(clubId);
  const refresh = useRefreshOwner();

  const [viewTab, setViewTab] = useState<"3d_builder" | "stadium" | "academy" | "projects_2d">("3d_builder");
  const [catFilter, setCatFilter] = useState<string>("all");
  const [selectedInstanceId, setSelectedInstanceId] = useState<string | null>("mod_stadium_core");
  const [selectedEmptyPlot, setSelectedEmptyPlot] = useState<{ x: number; y: number } | null>(null);
  const [activeBuildModuleKey, setActiveBuildModuleKey] = useState<string | null>(null);
  const [fastTrack, setFastTrack] = useState<boolean>(false);
  const [busy, setBusy] = useState<boolean>(false);

  const placedModules: CampusModuleInstance[] = campus?.placed_modules || [];
  const moduleCatalog: any[] = campus?.module_catalog || [];
  const zones = campus?.grid?.zones || [];
  const projects: any[] = campus?.construction_projects || [];
  const metrics = campus?.campus_metrics || {};
  const academyProspects: any[] = campus?.academy_campus_prospects || [];

  const selectedModule =
    placedModules.find((m) => m.instance_id === selectedInstanceId) || placedModules[0] || null;

  const filteredCatalog = moduleCatalog.filter(
    (c) => catFilter === "all" || c.category === catFilter
  );

  // Authoritative Owner Lifecycle Counts
  const existingCount = placedModules.length;
  const availableToConstructCount = moduleCatalog.filter(
    (c) =>
      c.availability_status === "available" ||
      ((campus?.prestige || 0) >= (c.min_prestige || 0) &&
        (campus?.cash_balance_gtex || 0) >= (c.base_cost_gtex || 0))
  ).length;
  const underConstructionCount = placedModules.filter(
    (m) => m.status === "under_construction"
  ).length;
  const readyForCompletionCount = placedModules.filter(
    (m) =>
      m.ready_for_completion ||
      (m.status === "under_construction" &&
        (m.construction_stage === "finishing" || Number(m.progress_pct || 0) >= 80))
  ).length;
  const completedCount = placedModules.filter((m) => m.status === "operational").length;
  const eligibleForUpgradeCount = placedModules.filter(
    (m) =>
      m.upgrade_eligible ??
      (m.status === "operational" && Number(m.level || 1) < Number(m.max_level || 5))
  ).length;

  const handlePlaceNewModule = async (moduleKey: string, x: number, y: number, rotation: number) => {
    if (!clubId || busy) return;
    setBusy(true);
    try {
      const res = await api.post(`/owner/clubs/${clubId}/campus/construct`, {
        operation: "place_new",
        module_key: moduleKey,
        x,
        y,
        rotation,
        initial_stage: "site_prep",
        fast_track_completion: fastTrack,
      });
      toast.success(
        `Commissioned ${res.data?.project?.module_name || moduleKey} at Grid (${x}, ${y})!`
      );
      setActiveBuildModuleKey(null);
      setSelectedEmptyPlot(null);
      if (res.data?.module?.instance_id) {
        setSelectedInstanceId(res.data.module.instance_id);
      }
      refresh();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail?.detail || err?.message || "Placement failed");
    } finally {
      setBusy(false);
    }
  };

  const handleMoveModule = async (instanceId: string, x: number, y: number, rotation: number) => {
    if (!clubId || busy) return;
    setBusy(true);
    try {
      await api.post(`/owner/clubs/${clubId}/campus/layout`, {
        action: "move",
        instance_id: instanceId,
        x,
        y,
        rotation,
      });
      toast.success(`Updated campus layout position to (${x}, ${y}) · ${rotation}°`);
      refresh();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail?.detail || err?.message || "Move failed");
    } finally {
      setBusy(false);
    }
  };

  const handleDemolishModule = async (instanceId: string) => {
    if (!clubId || busy) return;
    setBusy(true);
    try {
      await api.post(`/owner/clubs/${clubId}/campus/layout`, {
        action: "demolish",
        instance_id: instanceId,
      });
      toast.success("Module removed from campus grid.");
      if (selectedInstanceId === instanceId) setSelectedInstanceId(null);
      refresh();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail?.detail || err?.message || "Cannot demolish core module");
    } finally {
      setBusy(false);
    }
  };

  const handleUpgradeExisting = async (instanceId: string) => {
    if (!clubId || busy) return;
    setBusy(true);
    try {
      const res = await api.post(`/owner/clubs/${clubId}/campus/construct`, {
        operation: "upgrade_existing",
        instance_id: instanceId,
        fast_track_completion: fastTrack,
      });
      toast.success(
        `Upgrading ${res.data?.project?.module_name} to Level ${res.data?.project?.target_level}!`
      );
      refresh();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail?.detail || err?.message || "Upgrade failed");
    } finally {
      setBusy(false);
    }
  };

  const handleAdvanceProjectStage = async (instanceId: string, completeNow = false) => {
    if (!clubId || busy) return;
    setBusy(true);
    try {
      const res = await api.post(`/owner/clubs/${clubId}/campus/construct`, {
        operation: "advance_stage",
        instance_id: instanceId,
        fast_track_completion: completeNow,
      });
      toast.success(
        `Construction progressed to ${res.data?.project?.progress_pct}% (${res.data?.project?.stage})`
      );
      refresh();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail?.detail || err?.message || "Stage update failed");
    } finally {
      setBusy(false);
    }
  };

  if (!clubId) {
    return (
      <div className="p-8 text-center text-slate-300">
        Please claim or activate a club in the Control Center to access the 3D Club Campus Builder.
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12" data-testid="club-campus-page">
      {/* Flagship Header Banner */}
      <div className="relative rounded-3xl border border-emerald-500/30 bg-gradient-to-br from-slate-950 via-emerald-950/35 to-slate-900 p-6 overflow-hidden shadow-2xl">
        <div
          className="absolute inset-0 opacity-20 bg-cover bg-center pointer-events-none"
          style={{ backgroundImage: `url(${resolveImg("/img/prestige/10_club_campus_build_mode.png")})` }}
        />
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-semibold mb-2">
              <Compass className="w-3.5 h-3.5" /> GTEX INTERACTIVE 3D ARCHITECTURAL SUITE
            </div>
            <h1 className="text-2xl md:text-3xl font-black text-white tracking-tight">
              {campus?.club_name || active?.club_name} · Club Campus Builder
            </h1>
            <p className="text-sm text-slate-300 max-w-2xl mt-1">
              Sims-inspired 3D campus masterplanning. Place, rotate, and upgrade modular stadium stands, heated training
              pitches, biomechanics labs, hydrotherapy pools, and academy boarding complexes against the real GTEX
              treasury.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {clubs.length > 1 && (
              <select
                value={clubId}
                onChange={(e) => select(e.target.value)}
                className="px-3 py-2 rounded-xl bg-slate-900/90 border border-white/15 text-sm text-white"
              >
                {clubs.map((c: any) => (
                  <option key={c.club_id} value={c.club_id}>
                    {c.club_name}
                  </option>
                ))}
              </select>
            )}
            <div className="px-4 py-2.5 rounded-2xl bg-slate-900/90 border border-emerald-500/30">
              <div className="text-[11px] uppercase tracking-wider text-slate-400">Club Treasury</div>
              <div className="text-lg font-black text-emerald-400">
                {fmt(campus?.cash_balance_gtex)} <span className="text-xs font-semibold">GTEX</span>
              </div>
            </div>
            <div className="px-4 py-2.5 rounded-2xl bg-slate-900/90 border border-amber-500/30">
              <div className="text-[11px] uppercase tracking-wider text-slate-400">Prestige & World Day</div>
              <div className="text-lg font-black text-amber-300">
                {campus?.prestige || 50} <span className="text-xs font-normal text-slate-300">· Day {campus?.world_day || 1}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Live Gameplay Impact KPIs */}
        <div className="relative z-10 grid grid-cols-2 sm:grid-cols-5 gap-3 mt-5 pt-5 border-t border-white/10">
          <div className="rounded-xl bg-slate-950/75 border border-white/10 p-3">
            <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5 text-amber-400" /> Stadium Capacity
            </div>
            <div className="text-base font-black text-white mt-0.5">
              {fmt(metrics.stadium_capacity || 30000)} seats
            </div>
          </div>
          <div className="rounded-xl bg-slate-950/75 border border-white/10 p-3">
            <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-emerald-400" /> Matchday Revenue
            </div>
            <div className="text-base font-black text-emerald-300 mt-0.5">
              +{metrics.matchday_revenue_bonus_pct || 15}%
            </div>
          </div>
          <div className="rounded-xl bg-slate-950/75 border border-white/10 p-3">
            <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-sky-400" /> Training Velocity
            </div>
            <div className="text-base font-black text-sky-300 mt-0.5">
              +{metrics.training_efficiency_bonus_pct || 20}%
            </div>
          </div>
          <div className="rounded-xl bg-slate-950/75 border border-white/10 p-3">
            <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
              <HeartPulse className="w-3.5 h-3.5 text-cyan-400" /> Injury Prevention
            </div>
            <div className="text-base font-black text-cyan-300 mt-0.5">
              -{metrics.injury_reduction_pct || 22}% Risk
            </div>
          </div>
          <div className="rounded-xl bg-slate-950/75 border border-white/10 p-3">
            <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
              <GraduationCap className="w-3.5 h-3.5 text-purple-400" /> Academy Ceiling
            </div>
            <div className="text-base font-black text-purple-300 mt-0.5">
              +{metrics.academy_ceiling_bonus || 6} OVR
            </div>
          </div>
        </div>
      </div>

      {/* Mode Switcher Tabs + Quick Links */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          {[
            { id: "3d_builder", label: "3D Campus Build Mode", icon: Compass },
            { id: "stadium", label: "Stadium Expansion Architect", icon: Building2 },
            { id: "academy", label: "Academy Campus Precinct", icon: GraduationCap },
            {
              id: "projects_2d",
              label: `Construction Queue & 2D Inspector (${projects.length})`,
              icon: Hammer,
            },
          ].map((t) => {
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setViewTab(t.id as any)}
                className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition ${
                  viewTab === t.id
                    ? "bg-emerald-500 text-slate-950 shadow-lg shadow-emerald-500/20"
                    : "bg-slate-900 text-slate-300 border border-white/10 hover:bg-slate-800"
                }`}
              >
                <Icon className="w-4 h-4" />
                {t.label}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-2 text-xs">
          <Link
            to="/app/showroom"
            className="px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-200 border border-white/10 flex items-center gap-1"
          >
            Owner&apos;s Office <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
          <Link
            to="/app/inbox"
            className="px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-200 border border-white/10 flex items-center gap-1"
          >
            Club Comms <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
          <Link
            to="/app/newsroom"
            className="px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-200 border border-white/10 flex items-center gap-1"
          >
            GTEX Newsroom <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* TAB 1: INTERACTIVE 3D CAMPUS BUILD MODE */}
      {viewTab === "3d_builder" && (
        <div className="space-y-4">
          {/* 6-Category Owner Facility Status Overview Strip */}
          <div
            data-testid="campus-owner-status-summary"
            className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5"
          >
            <div className="rounded-xl bg-slate-900/95 border border-white/10 p-3 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">
                  Existing on Grid
                </div>
                <div className="text-lg font-black text-white">{existingCount}</div>
                <div className="text-[9px] text-slate-400">Active + Operational</div>
              </div>
              <span className="px-2 py-0.5 rounded bg-white/10 text-[10px] font-bold text-slate-200">
                Total Placed
              </span>
            </div>

            <div className="rounded-xl bg-slate-900/95 border border-emerald-500/30 p-3 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-emerald-300 font-bold">
                  Available to Construct
                </div>
                <div className="text-lg font-black text-emerald-400">
                  {availableToConstructCount} / {moduleCatalog.length}
                </div>
                <div className="text-[9px] text-emerald-300/75">Catalog Unlocked</div>
              </div>
              <span className="px-2 py-0.5 rounded bg-emerald-500/15 text-[10px] font-bold text-emerald-300">
                Blueprints
              </span>
            </div>

            <div className="rounded-xl bg-slate-900/95 border border-amber-500/30 p-3 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-amber-300 font-bold">
                  Under Construction
                </div>
                <div className="text-lg font-black text-amber-400">{underConstructionCount}</div>
                <div className="text-[9px] text-amber-300/75">Active Works (Stg 1–5)</div>
              </div>
              <span className="px-2 py-0.5 rounded bg-amber-500/15 text-[10px] font-bold text-amber-300">
                Active Sites
              </span>
            </div>

            <div className="rounded-xl bg-slate-900/95 border border-purple-500/30 p-3 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-purple-300 font-bold">
                  Ready for Completion
                </div>
                <div className="text-lg font-black text-purple-300">{readyForCompletionCount}</div>
                <div className="text-[9px] text-purple-300/75">In Stage 5 Fit-Out</div>
              </div>
              <span className="px-2 py-0.5 rounded bg-purple-500/15 text-[10px] font-bold text-purple-300">
                Final Stage
              </span>
            </div>

            <div className="rounded-xl bg-slate-900/95 border border-teal-500/30 p-3 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-teal-300 font-bold">
                  Already Completed
                </div>
                <div className="text-lg font-black text-teal-300">{completedCount}</div>
                <div className="text-[9px] text-teal-300/75">Stage 6 Operational</div>
              </div>
              <span className="px-2 py-0.5 rounded bg-teal-500/15 text-[10px] font-bold text-teal-300">
                Operational
              </span>
            </div>

            <div className="rounded-xl bg-slate-900/95 border border-sky-500/30 p-3 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-sky-300 font-bold">
                  Eligible for Upgrade
                </div>
                <div className="text-lg font-black text-sky-300">{eligibleForUpgradeCount}</div>
                <div className="text-[9px] text-sky-300/75">Operational Tier L1–L4</div>
              </div>
              <span className="px-2 py-0.5 rounded bg-sky-500/15 text-[10px] font-bold text-sky-300">
                Upgradeable
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
            <div className="xl:col-span-8 space-y-4">
              <CampusBuilder3D
                gridWidth={campus?.grid?.width || 24}
                gridHeight={campus?.grid?.height || 18}
                zones={zones}
                placedModules={placedModules}
                moduleCatalog={moduleCatalog}
                selectedInstanceId={selectedInstanceId}
                onSelectInstance={setSelectedInstanceId}
                selectedEmptyPlot={selectedEmptyPlot}
                onSelectEmptyPlot={setSelectedEmptyPlot}
                activeBuildModuleKey={activeBuildModuleKey}
                onClearBuildMode={() => setActiveBuildModuleKey(null)}
                onPlaceNewModule={handlePlaceNewModule}
                onMoveModule={handleMoveModule}
                onDemolishModule={handleDemolishModule}
                busy={busy || isLoading}
              />

              {/* Modular Building Catalogue Dock */}
              <div
                data-testid="campus-build-catalogue"
                className="rounded-2xl border border-white/10 bg-slate-900/90 p-5"
              >
                <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                  <div>
                    <h2 className="text-base font-bold text-white flex items-center gap-2">
                      <Layers className="w-4 h-4 text-emerald-400" /> Modular 3D Building Catalogue
                    </h2>
                    <p className="text-xs text-slate-400">
                      Select an empty plot on the 3D grid or choose any architectural blueprint below to preview and
                      commission construction.
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <label className="flex items-center gap-1.5 text-xs text-slate-300 bg-slate-950 px-3 py-1.5 rounded-lg border border-white/10 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={fastTrack}
                        onChange={(e) => setFastTrack(e.target.checked)}
                        className="rounded border-white/20 text-emerald-500"
                      />
                      Fast-Track Instant Build
                    </label>
                    {["all", "stadium", "training", "academy", "medical", "commercial", "operations"].map((cat) => (
                      <button
                        key={cat}
                        type="button"
                        onClick={() => setCatFilter(cat)}
                        className={`px-2.5 py-1 rounded-lg text-xs font-semibold capitalize ${
                          catFilter === cat
                            ? "bg-emerald-500 text-slate-950"
                            : "bg-white/5 text-slate-300 hover:bg-white/10"
                        }`}
                      >
                        {cat}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {filteredCatalog.map((mod) => {
                    const isActiveBuild = activeBuildModuleKey === mod.module_key;
                    const locked = (campus?.prestige || 0) < (mod.min_prestige || 0);
                    const placedCount =
                      mod.placed_count ??
                      placedModules.filter((m) => m.module_key === mod.module_key).length;
                    const buildingCount =
                      mod.under_construction_count ??
                      placedModules.filter(
                        (m) => m.module_key === mod.module_key && m.status === "under_construction"
                      ).length;

                    return (
                      <div
                        key={mod.module_key}
                        data-testid={`catalog-card-${mod.module_key}`}
                        className={`rounded-xl border overflow-hidden flex flex-col justify-between transition ${
                          isActiveBuild
                            ? "border-emerald-400 bg-emerald-950/30 ring-2 ring-emerald-500/30"
                            : "border-white/10 bg-slate-950/75 hover:border-white/25"
                        }`}
                      >
                        <div>
                          <div className="relative h-32 bg-slate-900 overflow-hidden">
                            <img
                              src={resolveImg(mod.image_url)}
                              alt={mod.name}
                              className="w-full h-full object-cover"
                            />
                            <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-slate-950/85 text-[10px] font-bold uppercase tracking-wider text-emerald-300 border border-white/10">
                              {mod.category} · {mod.footprint_w}×{mod.footprint_h} Tiles
                            </div>
                            <div className="absolute top-2 right-2 flex flex-col items-end gap-1">
                              {locked ? (
                                <span className="px-2 py-0.5 rounded bg-rose-950/90 text-[10px] font-bold text-rose-300 border border-rose-500/30">
                                  Req Prestige {mod.min_prestige}
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded bg-emerald-950/90 text-[10px] font-bold text-emerald-300 border border-emerald-500/30">
                                  Available to Construct
                                </span>
                              )}
                              {placedCount > 0 && (
                                <span className="px-2 py-0.5 rounded bg-slate-950/90 text-[10px] font-bold text-sky-300 border border-sky-500/30">
                                  Existing ×{placedCount}
                                  {buildingCount > 0 ? ` (${buildingCount} building)` : ""}
                                </span>
                              )}
                            </div>
                            <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-slate-950/90 text-[10px] font-semibold text-slate-300 border border-white/10">
                              {mod.build_days || 4}d Cycle · Min Prestige {mod.min_prestige || 40}
                            </div>
                            <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-slate-950/90 text-xs font-black text-amber-300 border border-amber-500/30">
                              {fmt(mod.base_cost_gtex)} GTEX
                            </div>
                          </div>
                          <div className="p-3">
                            <div className="text-sm font-bold text-white">{mod.name}</div>
                            <p className="text-[11px] text-slate-400 line-clamp-2 mt-1">{mod.description}</p>
                            <div className="flex flex-wrap gap-1 mt-2">
                              {Object.entries(mod.effects || {}).map(([k, v]) => (
                                <span
                                  key={k}
                                  className="px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-[10px] text-emerald-300 font-medium"
                                >
                                  +{String(v)} {k.replace(/_/g, " ")}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>

                        <div className="p-3 pt-0">
                          <button
                            type="button"
                            data-testid={`select-facility-${mod.module_key}`}
                            disabled={locked || busy}
                            onClick={() =>
                              setActiveBuildModuleKey(isActiveBuild ? null : mod.module_key)
                            }
                            className={`w-full py-2 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition ${
                              locked
                                ? "bg-white/5 text-slate-500 cursor-not-allowed"
                                : isActiveBuild
                                ? "bg-amber-500 text-slate-950"
                                : "bg-emerald-500 hover:bg-emerald-400 text-slate-950"
                            }`}
                          >
                            <Hammer className="w-3.5 h-3.5" />
                            {locked
                              ? `Requires Prestige ${mod.min_prestige}`
                              : isActiveBuild
                              ? "Previewing on 3D Grid (Click to Confirm)..."
                              : selectedEmptyPlot
                              ? `Preview on Plot (${selectedEmptyPlot.x}, ${selectedEmptyPlot.y})`
                              : "Select Facility for 3D Placement"}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Right Column: Selected Empty Plot Card, 3D Building Inspector & Staged Construction Log */}
            <div className="xl:col-span-4 space-y-4" data-testid="campus-building-inspector">
              {/* Selected Empty Plot Card */}
              {selectedEmptyPlot && (
                <div
                  data-testid="inspector-empty-plot-card"
                  className="rounded-2xl border border-emerald-400/50 bg-emerald-950/30 p-4 space-y-2.5 shadow-lg"
                >
                  <div className="flex items-center justify-between">
                    <span className="px-2.5 py-0.5 rounded-full bg-emerald-500 text-slate-950 text-[11px] font-black uppercase">
                      Empty Plot Selected
                    </span>
                    <button
                      type="button"
                      onClick={() => setSelectedEmptyPlot(null)}
                      className="text-xs text-slate-300 hover:text-white underline"
                    >
                      Clear Plot
                    </button>
                  </div>
                  <div className="text-sm font-black text-white">
                    Authoritative Grid Plot ({selectedEmptyPlot.x}, {selectedEmptyPlot.y})
                  </div>
                  <p className="text-xs text-slate-300">
                    Plot is unoccupied and ready for development. Select any unlocked facility from the{" "}
                    <strong>Modular 3D Building Catalogue</strong> to preview its footprint at ({selectedEmptyPlot.x},{" "}
                    {selectedEmptyPlot.y}), rotate if needed, and confirm construction.
                  </p>
                </div>
              )}

              {selectedModule ? (
                <div className="rounded-2xl border border-emerald-500/30 bg-slate-900/95 overflow-hidden shadow-xl">
                  <div className="relative h-48 bg-slate-950">
                    <img
                      src={resolveImg(selectedModule.image_url)}
                      alt={selectedModule.name}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/35 to-transparent" />
                    <div className="absolute top-3 left-3 right-3 flex flex-wrap items-center justify-between gap-1.5">
                      <div className="flex items-center gap-1.5">
                        <span
                          data-testid="inspector-level-badge"
                          className="px-2 py-0.5 rounded-full bg-emerald-500 text-slate-950 text-[11px] font-black"
                        >
                          L{selectedModule.level}/{selectedModule.max_level || 5}
                        </span>
                        <span className="px-2 py-0.5 rounded-full bg-slate-950/90 text-slate-200 text-[11px] font-semibold border border-white/15">
                          ({selectedModule.x}, {selectedModule.y}) · {selectedModule.effective_w}×
                          {selectedModule.effective_h} · {selectedModule.rotation || 0}°
                        </span>
                      </div>
                      <span
                        data-testid="inspector-lifecycle-badge"
                        className={`px-2 py-0.5 rounded-full text-[10px] font-black border ${
                          selectedModule.status === "under_construction"
                            ? selectedModule.ready_for_completion ||
                              selectedModule.construction_stage === "finishing"
                              ? "bg-purple-950/90 text-purple-200 border-purple-400/50"
                              : "bg-amber-950/90 text-amber-200 border-amber-400/50"
                            : selectedModule.level >= (selectedModule.max_level || 5)
                            ? "bg-teal-950/90 text-teal-200 border-teal-400/50"
                            : "bg-sky-950/90 text-sky-200 border-sky-400/50"
                        }`}
                      >
                        {selectedModule.status === "under_construction"
                          ? selectedModule.ready_for_completion ||
                            selectedModule.construction_stage === "finishing"
                            ? "Ready for Completion"
                            : "Under Construction"
                          : selectedModule.level >= (selectedModule.max_level || 5)
                          ? "Already Completed · Max L5"
                          : "Existing · Eligible for Upgrade"}
                      </span>
                    </div>
                    <div className="absolute bottom-3 left-3 right-3">
                      <div className="text-xs uppercase tracking-wider text-emerald-300 font-bold">
                        {selectedModule.category} Infrastructure
                      </div>
                      <h3 data-testid="inspector-facility-name" className="text-lg font-black text-white">
                        {selectedModule.name}
                      </h3>
                    </div>
                  </div>

                  <div className="p-4 space-y-4">
                    {/* Construction Stage Progress & 6-Stage Stepper */}
                    <div className="p-3 rounded-xl bg-slate-950 border border-white/10 space-y-2.5">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">Construction Stage</span>
                        <span
                          data-testid="inspector-stage-badge"
                          className={`px-2 py-0.5 rounded border text-[11px] font-bold ${
                            STAGE_LABELS[selectedModule.construction_stage]?.color ||
                            STAGE_LABELS.completed.color
                          }`}
                        >
                          {STAGE_LABELS[selectedModule.construction_stage]?.label ||
                            STAGE_LABELS.completed.label}
                        </span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-amber-400 to-emerald-400 transition-all duration-500"
                          style={{ width: `${selectedModule.progress_pct || 100}%` }}
                        />
                      </div>
                      <div className="flex justify-between text-[11px] text-slate-400">
                        <span>Progress: {selectedModule.progress_pct || 100}%</span>
                        <span>Structural Integrity: {selectedModule.condition || 98}%</span>
                      </div>

                      {/* 6-Stage Progression Stepper */}
                      <div
                        data-testid="inspector-stage-stepper"
                        className="grid grid-cols-3 gap-1.5 pt-1 border-t border-white/10"
                      >
                        {ORDERED_STAGES.map((stKey) => {
                          const stInfo = STAGE_LABELS[stKey];
                          const currentStep =
                            STAGE_LABELS[selectedModule.construction_stage]?.step || 6;
                          const isCurrent = selectedModule.construction_stage === stKey;
                          const isDone = currentStep > stInfo.step || currentStep === 6;
                          return (
                            <div
                              key={stKey}
                              className={`px-2 py-1 rounded text-[10px] font-bold border truncate ${
                                isCurrent
                                  ? "bg-amber-500/20 border-amber-400 text-amber-200"
                                  : isDone
                                  ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-300"
                                  : "bg-slate-900 border-white/5 text-slate-500"
                              }`}
                            >
                              {stInfo.short}
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed">{selectedModule.description}</p>

                    {/* Authoritative Cost, Development Level, Expected Completion & Upgrade Requirements */}
                    <div
                      data-testid="inspector-metadata-grid"
                      className="grid grid-cols-2 gap-2 text-xs"
                    >
                      <div className="p-2.5 rounded-xl bg-slate-950 border border-white/10">
                        <div className="text-[10px] uppercase text-slate-400">
                          Base / Next Upgrade Cost
                        </div>
                        <div className="font-black text-amber-300 mt-0.5">
                          {fmt(selectedModule.base_cost_gtex)} GTX{" "}
                          <span className="text-slate-400 font-normal">
                            ·{" "}
                            {selectedModule.next_upgrade_cost_gtex
                              ? `Next: ${fmt(selectedModule.next_upgrade_cost_gtex)} GTX`
                              : "Max L5"}
                          </span>
                        </div>
                      </div>

                      <div className="p-2.5 rounded-xl bg-slate-950 border border-white/10">
                        <div className="text-[10px] uppercase text-slate-400">
                          Development Level
                        </div>
                        <div className="font-black text-white mt-0.5">
                          Tier {selectedModule.level} of {selectedModule.max_level || 5}{" "}
                          <span className="text-emerald-400 font-semibold">
                            ({selectedModule.status === "operational" ? "Certified" : "Building"})
                          </span>
                        </div>
                      </div>

                      <div className="p-2.5 rounded-xl bg-slate-950 border border-white/10">
                        <div className="text-[10px] uppercase text-slate-400">
                          Expected Completion
                        </div>
                        <div className="font-bold text-slate-200 mt-0.5">
                          {selectedModule.status === "under_construction"
                            ? `Day ${
                                selectedModule.expected_completion_day ||
                                (campus?.world_day || 1) + (selectedModule.build_days || 4)
                              } (${selectedModule.remaining_days ?? 2}d left)`
                            : `Operational (${selectedModule.build_days || 4}d build cycle)`}
                        </div>
                      </div>

                      <div className="p-2.5 rounded-xl bg-slate-950 border border-white/10">
                        <div className="text-[10px] uppercase text-slate-400">
                          Upgrade Requirements
                        </div>
                        <div className="font-bold text-sky-300 mt-0.5">
                          {selectedModule.level >= (selectedModule.max_level || 5)
                            ? "Max Tier Reached"
                            : `Prestige ≥ ${
                                selectedModule.upgrade_min_prestige ||
                                selectedModule.min_prestige ||
                                40
                              } · ${fmt(selectedModule.next_upgrade_cost_gtex)} GTX`}
                        </div>
                      </div>
                    </div>

                    {/* Actual Gameplay Benefits (Current vs Next Level Delta) */}
                    <div data-testid="inspector-gameplay-benefits">
                      <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                        Authoritative Club Gameplay Benefits
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        {Object.entries(
                          selectedModule.current_effects || selectedModule.effects || {}
                        ).map(([k, v]) => {
                          const nextVal = selectedModule.next_level_effects?.[k];
                          return (
                            <div
                              key={k}
                              className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20"
                            >
                              <div className="text-[10px] uppercase text-slate-400">
                                {k.replace(/_/g, " ")}
                              </div>
                              <div className="text-sm font-black text-emerald-300">
                                +{String(v)} (L{selectedModule.level})
                              </div>
                              {nextVal !== undefined && (
                                <div className="text-[10px] text-sky-300 font-semibold mt-0.5">
                                  Next L{selectedModule.level + 1}: +{String(nextVal)}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="space-y-2 pt-2 border-t border-white/10">
                      {selectedModule.status === "under_construction" ? (
                        <div className="grid grid-cols-2 gap-2">
                          <button
                            type="button"
                            data-testid="advance-stage-btn"
                            disabled={busy}
                            onClick={() => handleAdvanceProjectStage(selectedModule.instance_id, false)}
                            className="py-2.5 px-3 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-black flex items-center justify-center gap-1.5"
                          >
                            <Wrench className="w-4 h-4" />
                            {selectedModule.construction_stage === "finishing"
                              ? "Certify & Complete (Stage 6)"
                              : "Advance Construction Stage"}
                          </button>
                          <button
                            type="button"
                            data-testid="complete-build-btn"
                            disabled={busy}
                            onClick={() => handleAdvanceProjectStage(selectedModule.instance_id, true)}
                            className="py-2.5 px-3 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-black flex items-center justify-center gap-1.5"
                          >
                            <CheckCircle2 className="w-4 h-4" /> Complete Build Now
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          data-testid="upgrade-facility-btn"
                          disabled={busy || selectedModule.level >= (selectedModule.max_level || 5)}
                          onClick={() => handleUpgradeExisting(selectedModule.instance_id)}
                          className="w-full py-2.5 px-4 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-slate-950 text-xs font-black flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20"
                        >
                          <Hammer className="w-4 h-4" />
                          {selectedModule.level >= (selectedModule.max_level || 5)
                            ? "Maximum Level 5 Certified"
                            : `Upgrade to Level ${selectedModule.level + 1} (${fmt(
                                selectedModule.next_upgrade_cost_gtex
                              )} GTEX)`}
                        </button>
                      )}

                      <div className="flex items-center justify-between gap-2">
                        {selectedModule.model_glb_url && (
                          <a
                            href={resolveImg(selectedModule.model_glb_url)}
                            download
                            className="flex-1 py-2 px-3 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-semibold text-center border border-white/10"
                          >
                            Download 3D .GLB Mesh
                          </a>
                        )}
                        {selectedModule.can_demolish && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => handleDemolishModule(selectedModule.instance_id)}
                            className="py-2 px-3 rounded-xl bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/30 text-xs font-semibold flex items-center gap-1"
                          >
                            <Trash2 className="w-3.5 h-3.5" /> Demolish
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}

              {/* Active Construction Projects Timeline */}
              <div className="rounded-2xl border border-white/10 bg-slate-900/90 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Clock className="w-4 h-4 text-amber-400" /> Staged Construction Log
                  </h3>
                  <span className="text-xs text-slate-400">{projects.length} recorded</span>
                </div>

                {projects.length === 0 ? (
                  <p className="text-xs text-slate-400 py-4 text-center">
                    No construction projects commissioned yet. Select a module from the catalogue or upgrade an existing
                    building.
                  </p>
                ) : (
                  <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                    {projects.slice(0, 8).map((p) => (
                      <div
                        key={p.project_id}
                        onClick={() => setSelectedInstanceId(p.instance_id)}
                        className="p-3 rounded-xl bg-slate-950 border border-white/10 hover:border-emerald-500/40 cursor-pointer transition"
                      >
                        <div className="flex items-center justify-between text-xs font-bold text-white">
                          <span>
                            {p.module_name} (L{p.target_level})
                          </span>
                          <span className="text-amber-300">{fmt(p.cost_gtex)} GTEX</span>
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1">
                          <span>Stage: {p.stage?.replace(/_/g, " ")}</span>
                          <span>{p.progress_pct}%</span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-slate-800 mt-1.5 overflow-hidden">
                          <div
                            className="h-full bg-emerald-400"
                            style={{ width: `${p.progress_pct}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: STADIUM EXPANSION ARCHITECT */}
      {viewTab === "stadium" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-7 rounded-2xl border border-amber-500/30 bg-slate-900 overflow-hidden">
            <img
              src={resolveImg("/img/prestige/11_stadium_expansion_construction.png")}
              alt="Stadium Expansion Construction"
              className="w-full h-80 object-cover"
            />
            <div className="p-6 space-y-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/15 text-amber-300 text-xs font-bold">
                STADIUM BOWL & GRANDSTAND ENGINEERING
              </div>
              <h2 className="text-2xl font-black text-white">
                {campus?.club_name} Arena Expansion Programme
              </h2>
              <p className="text-sm text-slate-300">
                Expand grandstand seating tiers, cantilever roof trusses, UEFA-spec broadcast floodlight pylons, and
                Directorate VIP skyboxes. Every stadium module commissioned on the 3D grid increases matchday gate
                receipts and home atmosphere.
              </p>
              <div className="grid grid-cols-3 gap-3 pt-2">
                <div className="p-3 rounded-xl bg-slate-950 border border-white/10">
                  <div className="text-xs text-slate-400">Current Capacity</div>
                  <div className="text-lg font-black text-white">{fmt(metrics.stadium_capacity)}</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-950 border border-white/10">
                  <div className="text-xs text-slate-400">After Next Tier</div>
                  <div className="text-lg font-black text-emerald-400">
                    {fmt((metrics.stadium_capacity || 30000) + 8500)}
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-slate-950 border border-white/10">
                  <div className="text-xs text-slate-400">Gate Revenue Lift</div>
                  <div className="text-lg font-black text-amber-300">
                    +{metrics.matchday_revenue_bonus_pct || 18}%
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-5 space-y-3">
            {placedModules
              .filter((m) => m.category === "stadium" || m.category === "commercial")
              .map((m) => (
                <div
                  key={m.instance_id}
                  className="p-4 rounded-2xl bg-slate-900 border border-white/10 flex items-center justify-between gap-4"
                >
                  <div>
                    <div className="text-xs text-emerald-400 font-bold uppercase">
                      Level {m.level} · {m.status === "operational" ? "Operational" : `Building (${m.progress_pct}%)`}
                    </div>
                    <div className="text-base font-bold text-white">{m.name}</div>
                    <div className="text-xs text-slate-400 mt-0.5">{m.description}</div>
                  </div>
                  <button
                    type="button"
                    disabled={busy || m.level >= 5}
                    onClick={() => handleUpgradeExisting(m.instance_id)}
                    className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-slate-950 text-xs font-black shrink-0"
                  >
                    {m.level >= 5 ? "Max L5" : `Upgrade (${fmt(m.next_upgrade_cost_gtex)} GTX)`}
                  </button>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* TAB 3: ACADEMY CAMPUS PRECINCT */}
      {viewTab === "academy" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-7 space-y-4">
            <div className="rounded-2xl border border-emerald-500/30 bg-slate-900 overflow-hidden">
              <img
                src={resolveImg("/img/prestige/12_elite_academy_complex.png")}
                alt="Elite Academy Complex"
                className="w-full h-72 object-cover"
              />
              <div className="p-6 space-y-3">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-300 text-xs font-bold">
                  NEXTGEN YOUTH DEVELOPMENT PRECINCT
                </div>
                <h2 className="text-2xl font-black text-white">
                  Elite Academy Boarding, Classrooms & Show Pitches
                </h2>
                <p className="text-sm text-slate-300">
                  Connected directly to the GTEX Academy Regen Engine. Upgrading your Academy HQ and Floodlit Show
                  Pitches raises the potential ceiling (+{metrics.academy_ceiling_bonus || 6} OVR) and intake quality of
                  newly generated club regens.
                </p>
              </div>
            </div>
          </div>

          <div className="lg:col-span-5 rounded-2xl border border-white/10 bg-slate-900 p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <GraduationCap className="w-4 h-4 text-emerald-400" /> Active Regens Training on Campus
              </h3>
              <Link to="/app/academy" className="text-xs text-emerald-400 hover:underline">
                Open Full Academy →
              </Link>
            </div>
            {academyProspects.length === 0 ? (
              <p className="text-xs text-slate-400">
                Trigger an Academy Intake in the Academy hub to populate youth scholars on your campus pitches.
              </p>
            ) : (
              <div className="space-y-2.5">
                {academyProspects.map((r) => (
                  <div
                    key={r.id}
                    className="p-3 rounded-xl bg-slate-950 border border-white/10 flex items-center justify-between"
                  >
                    <div>
                      <div className="text-sm font-bold text-white">{r.name}</div>
                      <div className="text-xs text-slate-400">
                        Position: {r.position} · Morale {r.morale}%
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs font-bold text-emerald-400">OVR {r.rating}</div>
                      <div className="text-[11px] text-amber-300">Ceiling {r.potential}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: ACCESSIBLE 2D MASTERPLAN & CONSTRUCTION QUEUE */}
      {viewTab === "projects_2d" && (
        <div className="rounded-2xl border border-white/10 bg-slate-900 p-6 space-y-4">
          <h2 className="text-lg font-bold text-white">
            Accessible Campus Module Registry & Construction Queue
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {placedModules.map((m) => (
              <div key={m.instance_id} className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase text-emerald-400">{m.category}</span>
                  <span className="text-xs text-slate-400">
                    Grid ({m.x}, {m.y}) · L{m.level}
                  </span>
                </div>
                <div className="text-sm font-bold text-white">{m.name}</div>
                <div className="text-xs text-slate-400">
                  Stage: {m.construction_stage} ({m.progress_pct}%)
                </div>
                <div className="flex gap-2 pt-2">
                  <button
                    type="button"
                    disabled={busy || m.level >= 5}
                    onClick={() => handleUpgradeExisting(m.instance_id)}
                    className="flex-1 py-1.5 rounded-lg bg-emerald-500 text-slate-950 text-xs font-bold disabled:opacity-40"
                  >
                    Upgrade ({fmt(m.next_upgrade_cost_gtex)} GTX)
                  </button>
                  {m.can_demolish && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleDemolishModule(m.instance_id)}
                      className="px-3 py-1.5 rounded-lg bg-rose-500/20 text-rose-300 text-xs font-bold"
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
