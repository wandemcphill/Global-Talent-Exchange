/**
 * GTEX Skin Engine — Layer 3: Football Module Display Modes
 * Scouting & Regen World — Prospect Development Pipeline View
 *
 * Visual pipeline grouping prospects by developmental ceiling and growth trajectory.
 * Authoritative data parity: Identical player entities and economics.
 */

import React from "react";
import { Award, Compass, Eye, Flame, Sparkles, TrendingUp, Zap } from "lucide-react";
import { ScoutingTableItem } from "./ScoutingTableView";

export interface ScoutingDevelopmentViewProps {
  items: ScoutingTableItem[];
  onSelectPlayer: (id: string) => void;
  onAddToWatchlist?: (id: string) => void;
}

export function ScoutingDevelopmentView({
  items,
  onSelectPlayer,
  onAddToWatchlist,
}: ScoutingDevelopmentViewProps) {
  // Partition prospects into developmental cohorts
  const eliteWonderkids = items.filter((p) => p.potential >= 88);
  const primeAscendants = items.filter((p) => p.potential >= 80 && p.potential < 88);
  const academyFoundations = items.filter((p) => p.potential < 80);

  const renderCohortSection = (
    title: string,
    subtitle: string,
    cohortItems: ScoutingTableItem[],
    accentColor: string,
    icon: React.ReactNode,
  ) => {
    return (
      <section className="space-y-3" data-testid={`cohort-${title.toLowerCase().replace(/\s+/g, "-")}`}>
        <div className="flex items-center justify-between border-b border-white/10 pb-2">
          <div className="flex items-center gap-2">
            <span className="flex size-6 items-center justify-center rounded bg-white/5" style={{ color: accentColor }}>
              {icon}
            </span>
            <div>
              <h3 className="gx-display text-sm font-black uppercase tracking-wider text-white">
                {title}
              </h3>
              <p className="text-[11px] text-slate-400">{subtitle}</p>
            </div>
          </div>
          <span className="rounded-full bg-white/5 px-2 py-0.5 text-[10px] font-bold text-slate-300">
            {cohortItems.length} Prospects
          </span>
        </div>

        {cohortItems.length === 0 ? (
          <div className="rounded-lg border border-dashed border-white/10 p-6 text-center text-xs text-slate-500">
            No prospects currently identified in this development bracket.
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {cohortItems.map((p) => {
              const headroom = Math.max(0, p.potential - p.rating);
              const progressPercent = Math.min(100, Math.round((p.rating / p.potential) * 100));

              return (
                <div
                  key={p.id}
                  data-testid={`development-card-${p.id}`}
                  className="rounded-xl border border-white/10 bg-slate-900/70 p-4 transition-all hover:border-white/20 hover:shadow-lg flex flex-col justify-between space-y-3"
                >
                  {/* Top Details */}
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="rounded bg-white/10 px-1.5 py-0.5 text-[9px] font-black uppercase text-slate-200">
                        {p.position} · {p.nationality}
                      </span>
                      <span className="gx-mono text-[10px] font-bold text-emerald-400">
                        Gen {p.generation}
                      </span>
                    </div>

                    <h4 className="mt-2 font-black uppercase text-white text-sm truncate">{p.name}</h4>
                    <p className="text-[11px] text-slate-400">{p.archetype} · {p.club}</p>
                  </div>

                  {/* Rating / Potential Gauge */}
                  <div className="space-y-1.5 bg-black/40 p-2.5 rounded-lg border border-white/5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400 text-[10px] uppercase font-bold">OVR {p.rating}</span>
                      <span className="font-black text-amber-300 flex items-center gap-1 text-[11px]">
                        <Zap size={11} /> {p.potential} POT
                      </span>
                    </div>

                    {/* Progress Bar */}
                    <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden flex">
                      <div
                        className="bg-emerald-400 transition-all duration-500"
                        style={{ width: `${progressPercent}%` }}
                      />
                      <div
                        className="bg-amber-400/60 transition-all duration-500"
                        style={{ width: `${100 - progressPercent}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-0.5">
                      <span>Maturity: {progressPercent}%</span>
                      <span className="text-emerald-400 font-bold">+{headroom} Growth Room</span>
                    </div>
                  </div>

                  {/* Bottom Footer Actions */}
                  <div className="flex items-center justify-between pt-1 border-t border-white/5">
                    <span className="gx-mono text-xs font-bold text-emerald-300">
                      {p.price.toLocaleString()} GX
                    </span>
                    <button
                      type="button"
                      onClick={() => onSelectPlayer(p.id)}
                      data-testid={`dossier-dev-btn-${p.id}`}
                      className="rounded bg-white/10 px-2.5 py-1 text-[11px] font-bold uppercase text-white hover:bg-emerald-500 hover:text-black transition-all flex items-center gap-1"
                    >
                      <Eye size={12} /> Dossier
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    );
  };

  return (
    <div className="space-y-8" data-testid="scouting-development-view">
      {renderCohortSection(
        "Tier 1 · Elite Wonderkids",
        "Generational ceilings (88+ POT) projected to dominate world football.",
        eliteWonderkids,
        "#f59e0b",
        <Flame size={16} />,
      )}

      {renderCohortSection(
        "Tier 2 · Prime Ascendants",
        "High-tier talent (80-87 POT) capable of slotting directly into top-flight squad rotations.",
        primeAscendants,
        "#10b981",
        <TrendingUp size={16} />,
      )}

      {renderCohortSection(
        "Tier 3 · Academy Foundations",
        "Solid developmental prospects (<80 POT) providing depth and tactical versatility.",
        academyFoundations,
        "#06b6d4",
        <Compass size={16} />,
      )}
    </div>
  );
}
