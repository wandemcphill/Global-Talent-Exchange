/**
 * GTEX Skin Engine — Layer 3: Football Module Display Modes
 * Player Profiles — Detailed Statistical Profile View (FM-Style)
 *
 * Provides deep analytical breakdowns, attribute matrices (Technical,
 * Mental, Physical), and career historical trajectories.
 * Authoritative data parity: Identical player entities and economics.
 */

import React from "react";
import { Activity, BarChart3, CheckCircle, Clock, Shield, Sparkles, TrendingUp, Zap } from "lucide-react";

export interface PlayerStatisticalProfileViewProps {
  player: any;
  rating: number;
  potential: number;
  position: string;
  age: number;
  nationality: string;
  club: string;
  careerEntries?: any[];
  scoutReport?: any;
}

export function PlayerStatisticalProfileView({
  player,
  rating,
  potential,
  position,
  age,
  nationality,
  club,
  careerEntries = [],
  scoutReport,
}: PlayerStatisticalProfileViewProps) {
  // Extract or synthesize attributes anchored Authoritatively to rating
  const baseAttr = Math.max(45, Math.min(99, rating));
  const rawAttrs = player.attributes || player.stats || {};

  // Attribute resolver helper
  const getAttr = (key: string, offset = 0) => {
    if (rawAttrs[key] != null) return Number(rawAttrs[key]);
    // Deterministic procedural attribute based on rating & position
    return Math.max(30, Math.min(99, baseAttr + offset));
  };

  const technical = [
    { label: "Finishing", value: getAttr("finishing", position === "FWD" ? 6 : -4) },
    { label: "Dribbling", value: getAttr("dribbling", position === "MID" || position === "FWD" ? 4 : -2) },
    { label: "Passing", value: getAttr("passing", position === "MID" ? 7 : -1) },
    { label: "First Touch", value: getAttr("first_touch", 3) },
    { label: "Tackling", value: getAttr("tackling", position === "DEF" ? 8 : -8) },
    { label: "Crossing", value: getAttr("crossing", 0) },
  ];

  const mental = [
    { label: "Composure", value: getAttr("composure", 2) },
    { label: "Vision", value: getAttr("vision", position === "MID" ? 6 : 0) },
    { label: "Decisions", value: getAttr("decisions", 1) },
    { label: "Positioning", value: getAttr("positioning", position === "DEF" ? 5 : -1) },
    { label: "Work Rate", value: getAttr("work_rate", 4) },
    { label: "Anticipation", value: getAttr("anticipation", 3) },
  ];

  const physical = [
    { label: "Pace", value: getAttr("pace", 5) },
    { label: "Acceleration", value: getAttr("acceleration", 4) },
    { label: "Stamina", value: getAttr("stamina", 3) },
    { label: "Strength", value: getAttr("strength", position === "DEF" ? 6 : -2) },
    { label: "Agility", value: getAttr("agility", 2) },
    { label: "Balance", value: getAttr("balance", 1) },
  ];

  const renderAttributeBar = (label: string, val: number) => {
    let colorClass = "text-slate-400";
    let bgClass = "bg-slate-600";
    if (val >= 85) {
      colorClass = "text-emerald-400 font-black";
      bgClass = "bg-emerald-400";
    } else if (val >= 75) {
      colorClass = "text-emerald-300 font-bold";
      bgClass = "bg-emerald-500/80";
    } else if (val >= 65) {
      colorClass = "text-amber-300 font-medium";
      bgClass = "bg-amber-400/80";
    }

    return (
      <div key={label} className="flex items-center justify-between text-xs py-1">
        <span className="text-slate-400 text-[11px]">{label}</span>
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-12 rounded-full bg-slate-800 overflow-hidden">
            <div className={`h-full ${bgClass}`} style={{ width: `${Math.min(100, (val / 99) * 100)}%` }} />
          </div>
          <span className={`gx-mono text-xs w-6 text-right ${colorClass}`}>{val}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6" data-testid="player-statistical-profile">
      {/* Identity Summary Bar */}
      <div className="rounded-xl border border-white/10 bg-slate-900/80 p-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
          <div className="border-r border-white/10 last:border-0">
            <p className="text-[10px] uppercase font-bold text-slate-400">Current Ability</p>
            <p className="gx-mono text-2xl font-black text-white mt-0.5">{rating} <span className="text-xs text-slate-400 font-normal">/99</span></p>
          </div>
          <div className="border-r border-white/10 last:border-0">
            <p className="text-[10px] uppercase font-bold text-slate-400">Potential Ceiling</p>
            <p className="gx-mono text-2xl font-black text-amber-400 mt-0.5">{potential} <span className="text-xs text-slate-400 font-normal">POT</span></p>
          </div>
          <div className="border-r border-white/10 last:border-0">
            <p className="text-[10px] uppercase font-bold text-slate-400">Growth Room</p>
            <p className="gx-mono text-2xl font-black text-emerald-400 mt-0.5">+{Math.max(0, potential - rating)}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-400">Archetype</p>
            <p className="text-xs font-bold text-cyan-300 mt-1 truncate">{player.archetype || "Tactical Specialist"}</p>
          </div>
        </div>
      </div>

      {/* FM 3-Column Attribute Grid */}
      <div className="grid gap-4 sm:grid-cols-3">
        {/* Technical */}
        <div className="rounded-xl border border-white/10 bg-slate-900/60 p-3.5 space-y-2">
          <div className="flex items-center gap-1.5 border-b border-white/10 pb-1.5 text-xs font-black uppercase text-cyan-400">
            <Zap size={13} /> Technical
          </div>
          <div className="divide-y divide-white/5">
            {technical.map((a) => renderAttributeBar(a.label, a.value))}
          </div>
        </div>

        {/* Mental */}
        <div className="rounded-xl border border-white/10 bg-slate-900/60 p-3.5 space-y-2">
          <div className="flex items-center gap-1.5 border-b border-white/10 pb-1.5 text-xs font-black uppercase text-amber-400">
            <Activity size={13} /> Mental
          </div>
          <div className="divide-y divide-white/5">
            {mental.map((a) => renderAttributeBar(a.label, a.value))}
          </div>
        </div>

        {/* Physical */}
        <div className="rounded-xl border border-white/10 bg-slate-900/60 p-3.5 space-y-2">
          <div className="flex items-center gap-1.5 border-b border-white/10 pb-1.5 text-xs font-black uppercase text-emerald-400">
            <TrendingUp size={13} /> Physical
          </div>
          <div className="divide-y divide-white/5">
            {physical.map((a) => renderAttributeBar(a.label, a.value))}
          </div>
        </div>
      </div>

      {/* Historical Career Records */}
      {careerEntries && careerEntries.length > 0 && (
        <div className="rounded-xl border border-white/10 bg-slate-900/60 p-4 space-y-3">
          <div className="flex items-center gap-2 text-xs font-black uppercase tracking-wider text-slate-300">
            <BarChart3 size={14} className="text-emerald-400" /> Historical Performance Log
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-white/10 text-[9px] uppercase text-slate-400">
                <tr>
                  <th className="py-1.5">Season</th>
                  <th className="py-1.5">Club</th>
                  <th className="py-1.5 text-center">Apps</th>
                  <th className="py-1.5 text-center">Goals</th>
                  <th className="py-1.5 text-center">Assists</th>
                  <th className="py-1.5 text-right">Avg Rating</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {careerEntries.slice(0, 5).map((c: any, i: number) => (
                  <tr key={i} className="text-slate-300">
                    <td className="py-1.5 font-bold">{c.season || `Season ${i + 1}`}</td>
                    <td className="py-1.5 text-slate-400">{c.club_name || club}</td>
                    <td className="py-1.5 text-center gx-mono">{c.appearances ?? c.matches ?? 18}</td>
                    <td className="py-1.5 text-center gx-mono">{c.goals ?? 0}</td>
                    <td className="py-1.5 text-center gx-mono">{c.assists ?? 0}</td>
                    <td className="py-1.5 text-right gx-mono font-bold text-emerald-400">
                      {c.average_rating ? Number(c.average_rating).toFixed(2) : "7.14"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
