/**
 * GTEX Skin Engine — Football Module View: FM-Style Player Scouting Table
 * High-density Football Manager data table presentation for the Player Market.
 */

import React from "react";
import { ArrowUpDown, Crown, ShieldAlert, Sparkles, UserCheck } from "lucide-react";
import { fmt } from "@/lib/owner";
import { Btn, Chip, Coin } from "@/components/gtex/ui";
import { posShort } from "./PlayerCard";

interface MarketTableViewProps {
  players: any[];
  signedRefs: string[];
  clubId?: string;
  clubCash?: number | string;
  busyPlayerId?: string | null;
  onSign: (player: any) => void;
  onOpenDossier: (playerId: string) => void;
}

export function MarketTableView({
  players,
  signedRefs = [],
  clubId,
  clubCash,
  busyPlayerId,
  onSign,
  onOpenDossier,
}: MarketTableViewProps) {
  const cashNum = Number(clubCash || 0);

  return (
    <div className="overflow-x-auto rounded-xl border border-white/10 bg-slate-950/60 shadow-xl" data-testid="market-fm-table-view">
      <table className="w-full text-left text-xs gx-table">
        <thead>
          <tr className="border-b border-white/15 bg-white/[0.04] text-[10px] font-black uppercase tracking-wider text-slate-400">
            <th className="py-2.5 px-3">Pos</th>
            <th className="py-2.5 px-3">OVR</th>
            <th className="py-2.5 px-3">Player Name</th>
            <th className="py-2.5 px-3 hidden sm:table-cell">Nat</th>
            <th className="py-2.5 px-3 hidden md:table-cell">Age</th>
            <th className="py-2.5 px-3 hidden lg:table-cell">Current Club</th>
            <th className="py-2.5 px-3 hidden xl:table-cell">Tier & Rules</th>
            <th className="py-2.5 px-3 text-right">Fair Value</th>
            <th className="py-2.5 px-3 text-right">Fee (GTX)</th>
            <th className="py-2.5 px-3 text-center">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/[0.06]">
          {players.map((p: any) => {
            const pid = p.player_id;
            const owned = signedRefs.includes(pid);
            const price = p.quote?.price ?? 0;
            const rating = Number(p.quote?.rating ?? p.overall_rating ?? 60);
            const unaffordable = cashNum > 0 && price > cashNum && !owned;
            const tierNorm = String(p.real_player_tier || "").toLowerCase();
            const isLegend = tierNorm === "legend";
            const isRegen = p.is_regen || p.is_real_player === false;
            const isRestricted = isLegend || isRegen || rating >= 80;
            const isWonderkid = tierNorm === "wonderkid";
            const isBusy = busyPlayerId === pid;

            return (
              <tr
                key={pid}
                data-testid={`market-row-${pid}`}
                className="group transition-colors hover:bg-emerald-500/[0.08]"
              >
                {/* Pos */}
                <td className="py-2.5 px-3">
                  <span
                    className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-black uppercase font-mono ${
                      p.position === "goalkeeper" || p.position === "GK"
                        ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                        : p.position === "forward" || p.position === "FWD" || p.position === "ST"
                        ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                        : p.position === "midfielder" || p.position === "MID"
                        ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                        : "bg-sky-500/20 text-sky-300 border border-sky-500/30"
                    }`}
                  >
                    {posShort(p.position)}
                  </span>
                </td>

                {/* Rating */}
                <td className="py-2.5 px-3 font-mono font-black text-sm">
                  <span
                    className={
                      rating >= 85
                        ? "text-amber-300"
                        : rating >= 78
                        ? "text-emerald-300"
                        : "text-slate-200"
                    }
                  >
                    {rating}
                  </span>
                </td>

                {/* Name */}
                <td className="py-2.5 px-3 font-bold text-white">
                  <button
                    type="button"
                    onClick={() => onOpenDossier(pid)}
                    className="text-left font-bold text-white hover:text-emerald-300 hover:underline flex items-center gap-1.5"
                  >
                    <span>{p.canonical_display_name || p.player_name || p.name}</span>
                    {isLegend && <Crown size={12} className="text-amber-400 shrink-0" />}
                    {isWonderkid && <Sparkles size={12} className="text-emerald-400 shrink-0" />}
                  </button>
                  {p.playstyle && (
                    <p className="text-[10px] font-medium text-cyan-400/90 mt-0.5 truncate max-w-[180px]">
                      {p.playstyle}
                    </p>
                  )}
                </td>

                {/* Nat */}
                <td className="py-2.5 px-3 text-slate-400 hidden sm:table-cell font-mono">
                  {p.nationality || "—"}
                </td>

                {/* Age */}
                <td className="py-2.5 px-3 text-slate-300 hidden md:table-cell font-mono">
                  {p.age || "—"}
                </td>

                {/* Current Club */}
                <td className="py-2.5 px-3 text-slate-300 hidden lg:table-cell truncate max-w-[140px]">
                  {p.current_club_name || "Free Agent"}
                </td>

                {/* Tier & Rules */}
                <td className="py-2.5 px-3 hidden xl:table-cell">
                  {isLegend ? (
                    <span className="rounded bg-amber-500/20 px-2 py-0.5 text-[9px] font-black uppercase text-amber-300 border border-amber-500/40">
                      ★ ICON · 1 OF 1
                    </span>
                  ) : isWonderkid ? (
                    <span className="rounded bg-cyan-500/20 px-2 py-0.5 text-[9px] font-black uppercase text-cyan-300 border border-cyan-500/40">
                      Wonderkid
                    </span>
                  ) : isRestricted ? (
                    <span className="rounded bg-slate-800 px-2 py-0.5 text-[9px] font-bold uppercase text-slate-300">
                      Paid GTX Only
                    </span>
                  ) : (
                    <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[9px] font-bold uppercase text-emerald-300">
                      Promo Eligible
                    </span>
                  )}
                </td>

                {/* Value */}
                <td className="py-2.5 px-3 text-right font-mono text-slate-300">
                  {p.current_value_credits != null ? fmt(p.current_value_credits, 1) : fmt(price, 1)}
                </td>

                {/* Fee */}
                <td className="py-2.5 px-3 text-right font-mono font-bold text-white">
                  <Coin amount={price} />
                </td>

                {/* Action */}
                <td className="py-2.5 px-3 text-center">
                  <Btn
                    className="py-1 px-3 text-[11px]"
                    variant={owned ? "ghost" : unaffordable ? "outline" : "secondary"}
                    disabled={owned || isBusy || !clubId || unaffordable}
                    onClick={() => onSign(p)}
                    data-testid={`sign-player-row-${pid}`}
                  >
                    {owned ? (
                      <span className="flex items-center gap-1 text-emerald-400">
                        <UserCheck size={12} /> In Squad
                      </span>
                    ) : isBusy ? (
                      "Signing…"
                    ) : unaffordable ? (
                      <span className="text-slate-500">Short Funds</span>
                    ) : (
                      "Sign"
                    )}
                  </Btn>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
