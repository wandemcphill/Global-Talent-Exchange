/**
 * GTEX Skin Engine — Football Module View: Competitions Table & Fixtures View
 * Structured tabular presentation for tournament brackets and fixtures (Layer 3).
 */

import React from "react";
import { Link } from "react-router-dom";
import { Chip, Coin } from "./ui";

interface CompetitionsTableViewProps {
  competitions: any[];
  clubId?: string;
}

export function CompetitionsTableView({ competitions, clubId }: CompetitionsTableViewProps) {
  if (!competitions || competitions.length === 0) {
    return <p className="text-xs text-slate-500 py-4">No active tournament listings.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-white/10 bg-slate-950/60 shadow-lg" data-testid="competitions-table-view">
      <table className="w-full text-left text-xs gx-table">
        <thead>
          <tr className="border-b border-white/15 bg-white/[0.04] text-[10px] font-black uppercase text-slate-400">
            <th className="py-2.5 px-3">Tournament</th>
            <th className="py-2.5 px-3">Host Type</th>
            <th className="py-2.5 px-3">Format</th>
            <th className="py-2.5 px-3">Status</th>
            <th className="py-2.5 px-3 text-right">Entry Fee</th>
            <th className="py-2.5 px-3 text-right">Prize Pool</th>
            <th className="py-2.5 px-3 text-center">Clubs</th>
            <th className="py-2.5 px-3 text-center">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/[0.06]">
          {competitions.map((c: any) => {
            const entered = c.my_club_ids?.length > 0;

            return (
              <tr key={c.id} data-testid={`competition-row-${c.id}`} className="hover:bg-emerald-500/[0.05]">
                <td className="py-2.5 px-3">
                  <Link to={`/app/competitions/${c.id}`} className="font-bold text-white hover:text-emerald-300">
                    {c.name}
                  </Link>
                  {c.invite_code && (
                    <span className="block font-mono text-[10px] text-cyan-300 mt-0.5">
                      Code: {c.invite_code}
                    </span>
                  )}
                </td>
                <td className="py-2.5 px-3">
                  <Chip tone={c.host_type === "gtex" ? "emerald" : "cyan"}>
                    {c.host_type === "gtex" ? "GTEX" : "User"}
                  </Chip>
                </td>
                <td className="py-2.5 px-3 uppercase text-[11px] text-slate-300">{c.format}</td>
                <td className="py-2.5 px-3">
                  <Chip tone={c.status === "open" ? "gold" : c.status === "running" ? "emerald" : "slate"}>
                    {c.status}
                  </Chip>
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-white">
                  <Coin amount={c.entry_fee} />
                </td>
                <td className="py-2.5 px-3 text-right font-mono font-bold text-amber-300">
                  <Coin amount={c.prize_pool} />
                </td>
                <td className="py-2.5 px-3 text-center font-mono text-slate-300">
                  {c.entrants}/{c.max_clubs}
                </td>
                <td className="py-2.5 px-3 text-center">
                  <Link
                    to={`/app/competitions/${c.id}`}
                    className="gx-btn gx-btn-secondary py-1 px-3 text-[11px]"
                    data-testid={`view-competition-row-${c.id}`}
                  >
                    View
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
