/**
 * GTEX Skin Engine — Layer 3: Football Module Display Modes
 * Scouting & Regen World — FM-Style Scouting Database Table View
 *
 * Renders a high-density tabular scouting database with sorting,
 * filtering, and rapid signing actions.
 * Authoritative data parity: Identical player entities and economics.
 */

import React, { useState, useMemo } from "react";
import { ArrowUpDown, ChevronDown, ChevronUp, Eye, Sparkles, TrendingUp, Users } from "lucide-react";

export interface ScoutingTableItem {
  id: string;
  name: string;
  rating: number;
  potential: number;
  position: string;
  age: number;
  nationality: string;
  club: string;
  generation: number;
  archetype: string;
  serial?: string;
  price: number;
  rawItem: any;
}

export interface ScoutingTableViewProps {
  items: ScoutingTableItem[];
  onSelectPlayer: (id: string) => void;
  onAddToWatchlist?: (id: string) => void;
}

type SortField = "name" | "rating" | "potential" | "age" | "price" | "generation";

export function ScoutingTableView({
  items,
  onSelectPlayer,
  onAddToWatchlist,
}: ScoutingTableViewProps) {
  const [sortField, setSortField] = useState<SortField>("potential");
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAsc((prev) => !prev);
    } else {
      setSortField(field);
      setSortAsc(false); // default desc for ratings
    }
  };

  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) => {
      let valA: any = a[sortField];
      let valB: any = b[sortField];

      if (typeof valA === "string") {
        valA = valA.toLowerCase();
        valB = valB.toLowerCase();
      }

      if (valA < valB) return sortAsc ? -1 : 1;
      if (valA > valB) return sortAsc ? 1 : -1;
      return 0;
    });
  }, [items, sortField, sortAsc]);

  const renderSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown size={12} className="opacity-40" />;
    }
    return sortAsc ? (
      <ChevronUp size={12} className="text-emerald-400" />
    ) : (
      <ChevronDown size={12} className="text-emerald-400" />
    );
  };

  return (
    <div
      className="overflow-x-auto rounded-xl border border-white/10 bg-slate-950/80 shadow-2xl"
      data-testid="scouting-table-view"
    >
      <table className="w-full text-left text-xs">
        <thead className="border-b border-white/10 bg-black/60 text-[10px] font-black uppercase tracking-wider text-slate-400">
          <tr>
            <th
              className="cursor-pointer px-4 py-3 hover:text-white"
              onClick={() => handleSort("name")}
            >
              <div className="flex items-center gap-1.5">
                <span>Prospect</span>
                {renderSortIcon("name")}
              </div>
            </th>
            <th className="px-3 py-3">Pos</th>
            <th
              className="cursor-pointer px-3 py-3 hover:text-white"
              onClick={() => handleSort("age")}
            >
              <div className="flex items-center gap-1.5">
                <span>Age</span>
                {renderSortIcon("age")}
              </div>
            </th>
            <th className="px-3 py-3">Nation / Club</th>
            <th
              className="cursor-pointer px-3 py-3 hover:text-white"
              onClick={() => handleSort("generation")}
            >
              <div className="flex items-center gap-1.5">
                <span>Gen</span>
                {renderSortIcon("generation")}
              </div>
            </th>
            <th
              className="cursor-pointer px-3 py-3 hover:text-white"
              onClick={() => handleSort("rating")}
            >
              <div className="flex items-center gap-1.5">
                <span>OVR</span>
                {renderSortIcon("rating")}
              </div>
            </th>
            <th
              className="cursor-pointer px-3 py-3 hover:text-white"
              onClick={() => handleSort("potential")}
            >
              <div className="flex items-center gap-1.5">
                <span>POT</span>
                {renderSortIcon("potential")}
              </div>
            </th>
            <th className="px-3 py-3">Archetype</th>
            <th
              className="cursor-pointer px-3 py-3 text-right hover:text-white"
              onClick={() => handleSort("price")}
            >
              <div className="flex items-center justify-end gap-1.5">
                <span>Value (GX)</span>
                {renderSortIcon("price")}
              </div>
            </th>
            <th className="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {sortedItems.map((p) => {
            const potentialDelta = Math.max(0, p.potential - p.rating);

            return (
              <tr
                key={p.id}
                data-testid={`scouting-row-${p.id}`}
                className="transition-colors hover:bg-white/[0.03]"
              >
                {/* Name & Serial */}
                <td className="px-4 py-3">
                  <div className="flex flex-col">
                    <span className="font-bold text-white text-xs">{p.name}</span>
                    {p.serial && (
                      <span className="gx-mono text-[9px] text-slate-500">{p.serial}</span>
                    )}
                  </div>
                </td>

                {/* Position */}
                <td className="px-3 py-3">
                  <span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] font-black uppercase text-slate-200">
                    {p.position}
                  </span>
                </td>

                {/* Age */}
                <td className="px-3 py-3 font-semibold text-slate-300">{p.age}</td>

                {/* Nation & Club */}
                <td className="px-3 py-3">
                  <div className="flex flex-col">
                    <span className="text-slate-300">{p.nationality}</span>
                    <span className="text-[10px] text-slate-500">{p.club}</span>
                  </div>
                </td>

                {/* Gen */}
                <td className="px-3 py-3">
                  <span className="gx-mono text-[11px] font-bold text-emerald-400">
                    Gen {p.generation}
                  </span>
                </td>

                {/* Current Rating */}
                <td className="px-3 py-3">
                  <span className="gx-mono text-sm font-black text-white">{p.rating}</span>
                </td>

                {/* Potential Rating */}
                <td className="px-3 py-3">
                  <div className="flex items-center gap-1.5">
                    <span className="gx-mono text-sm font-black text-amber-400">
                      {p.potential}
                    </span>
                    {potentialDelta > 0 && (
                      <span className="text-[10px] font-bold text-emerald-400">
                        +{potentialDelta}
                      </span>
                    )}
                  </div>
                </td>

                {/* Archetype */}
                <td className="px-3 py-3">
                  <span className="text-[11px] text-slate-400">{p.archetype}</span>
                </td>

                {/* Valuation */}
                <td className="px-3 py-3 text-right">
                  <span className="gx-mono text-xs font-black text-emerald-300">
                    {p.price.toLocaleString()} GX
                  </span>
                </td>

                {/* Actions */}
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    {onAddToWatchlist && (
                      <button
                        type="button"
                        onClick={() => onAddToWatchlist(p.id)}
                        className="rounded p-1 text-slate-400 hover:bg-white/10 hover:text-amber-400 transition-colors"
                        title="Add to Shortlist"
                      >
                        <Sparkles size={14} />
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => onSelectPlayer(p.id)}
                      data-testid={`dossier-btn-${p.id}`}
                      className="rounded bg-emerald-500/20 px-2.5 py-1 text-[11px] font-bold uppercase text-emerald-300 hover:bg-emerald-500/30 transition-all flex items-center gap-1"
                    >
                      <Eye size={12} /> Dossier
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
