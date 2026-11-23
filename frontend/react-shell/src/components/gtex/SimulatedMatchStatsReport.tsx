import React from "react";
import { Award, Shield, Target } from "lucide-react";

export interface SimulatedMatchGoal {
  minute: number;
  added_time?: number;
  clock_label?: string;
  side: "home" | "away";
  team_id?: string | null;
  team_name?: string;
  scorer_id?: string | null;
  scorer_name: string;
  assist_id?: string | null;
  assist_name?: string | null;
  is_penalty?: boolean;
  home_score?: number;
  away_score?: number;
  commentary?: string;
}

export interface SimulatedMatchCard {
  minute: number;
  clock_label?: string;
  side: "home" | "away";
  team_id?: string | null;
  team_name?: string;
  player_id?: string | null;
  player_name: string;
  card_type: string;
  commentary?: string;
}

export interface SimulatedMatchStats {
  home_possession?: number | null;
  away_possession?: number | null;
  home_shots?: number | null;
  away_shots?: number | null;
  home_shots_on_target?: number | null;
  away_shots_on_target?: number | null;
  home_saves?: number | null;
  away_saves?: number | null;
  home_expected_goals?: number | null;
  away_expected_goals?: number | null;
  home_yellow_cards?: number | null;
  away_yellow_cards?: number | null;
  home_red_cards?: number | null;
  away_red_cards?: number | null;
  home_big_chances?: number | null;
  away_big_chances?: number | null;
  home_assists?: number | null;
  away_assists?: number | null;
  home_key_passes?: number | null;
  away_key_passes?: number | null;
  home_tackles_won?: number | null;
  away_tackles_won?: number | null;
  home_interceptions?: number | null;
  away_interceptions?: number | null;
}

export interface SimulatedMatchPlayerStat {
  player_id: string;
  player_name: string;
  team_id?: string;
  team_name?: string;
  side: "home" | "away";
  role?: string;
  started?: boolean;
  minutes_played?: number;
  goals?: number;
  assists?: number;
  saves?: number;
  shots_on_target?: number;
  key_passes?: number;
  tackles_won?: number;
  interceptions?: number;
  yellow_cards?: number;
  red_card?: boolean;
  xg?: number;
  rating?: number | null;
  rating_summary?: string | null;
}

export interface SimulatedMatchMotm {
  available?: boolean;
  player_id?: string | null;
  player_name?: string | null;
  team_id?: string | null;
  team_name?: string | null;
  side?: "home" | "away" | null;
  role?: string | null;
  goals?: number;
  assists?: number;
  rating?: number | null;
  summary?: string | null;
}

export interface SimulatedMatchReport {
  match_id?: string;
  home_team_id?: string | null;
  away_team_id?: string | null;
  home_team_name: string;
  away_team_name: string;
  home_score: number;
  away_score: number;
  decided_by_penalties?: boolean;
  home_penalty_score?: number | null;
  away_penalty_score?: number | null;
  result?: string | null;
  summary_line?: string;
  stats?: SimulatedMatchStats | null;
  goals?: SimulatedMatchGoal[];
  cards?: SimulatedMatchCard[];
  player_stats?: SimulatedMatchPlayerStat[];
  motm?: SimulatedMatchMotm | null;
  key_highlights?: string[];
  is_simulated?: boolean;
}

interface StatBarRowProps {
  label: string;
  homeDisplay: string;
  awayDisplay: string;
  homeNum: number;
  awayNum: number;
}

function StatBarRow({ label, homeDisplay, awayDisplay, homeNum, awayNum }: StatBarRowProps) {
  const total = Math.max(0, homeNum) + Math.max(0, awayNum);
  const homePct = total > 0 ? Math.round((Math.max(0, homeNum) / total) * 100) : 50;
  const awayPct = 100 - homePct;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className="gx-mono font-bold text-emerald-300">{homeDisplay}</span>
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</span>
        <span className="gx-mono font-bold text-amber-300">{awayDisplay}</span>
      </div>
      <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full bg-emerald-400 transition-all duration-300"
          style={{ width: `${homePct}%` }}
        />
        <div
          className="h-full bg-amber-400 transition-all duration-300"
          style={{ width: `${awayPct}%` }}
        />
      </div>
    </div>
  );
}

function formatGoalClock(g: SimulatedMatchGoal): string {
  if (g.clock_label) return g.clock_label;
  if (g.added_time && g.added_time > 0) return `${g.minute}+${g.added_time}'`;
  return `${g.minute}'`;
}

export function SimulatedMatchStatsReport({
  report,
  compact = false,
}: {
  report: SimulatedMatchReport | null | undefined;
  compact?: boolean;
}) {
  if (!report) return null;

  const stats = report.stats || {};
  const goals = Array.isArray(report.goals) ? report.goals : [];
  const cards = Array.isArray(report.cards) ? report.cards : [];
  const playerStats = Array.isArray(report.player_stats) ? report.player_stats : [];
  const homeGoals = goals.filter((g) => g.side === "home");
  const awayGoals = goals.filter((g) => g.side === "away");
  const homeCards = cards.filter((c) => c.side === "home");
  const awayCards = cards.filter((c) => c.side === "away");
  const motm = report.motm;

  const statRows: StatBarRowProps[] = [];
  if (stats.home_possession != null && stats.away_possession != null) {
    statRows.push({
      label: "Possession",
      homeDisplay: `${Math.round(Number(stats.home_possession))}%`,
      awayDisplay: `${Math.round(Number(stats.away_possession))}%`,
      homeNum: Number(stats.home_possession),
      awayNum: Number(stats.away_possession),
    });
  }
  if (stats.home_shots != null && stats.away_shots != null) {
    statRows.push({
      label: "Shots",
      homeDisplay: String(stats.home_shots),
      awayDisplay: String(stats.away_shots),
      homeNum: Number(stats.home_shots),
      awayNum: Number(stats.away_shots),
    });
  }
  if (stats.home_shots_on_target != null && stats.away_shots_on_target != null) {
    statRows.push({
      label: "Shots on Target",
      homeDisplay: String(stats.home_shots_on_target),
      awayDisplay: String(stats.away_shots_on_target),
      homeNum: Number(stats.home_shots_on_target),
      awayNum: Number(stats.away_shots_on_target),
    });
  }
  if (stats.home_expected_goals != null && stats.away_expected_goals != null) {
    statRows.push({
      label: "Expected Goals (xG)",
      homeDisplay: Number(stats.home_expected_goals).toFixed(2),
      awayDisplay: Number(stats.away_expected_goals).toFixed(2),
      homeNum: Number(stats.home_expected_goals),
      awayNum: Number(stats.away_expected_goals),
    });
  }
  if (stats.home_assists != null && stats.away_assists != null) {
    statRows.push({
      label: "Assists",
      homeDisplay: String(stats.home_assists),
      awayDisplay: String(stats.away_assists),
      homeNum: Number(stats.home_assists),
      awayNum: Number(stats.away_assists),
    });
  }
  if (stats.home_saves != null && stats.away_saves != null) {
    statRows.push({
      label: "Goalkeeper Saves",
      homeDisplay: String(stats.home_saves),
      awayDisplay: String(stats.away_saves),
      homeNum: Number(stats.home_saves),
      awayNum: Number(stats.away_saves),
    });
  }
  if (stats.home_big_chances != null && stats.away_big_chances != null) {
    statRows.push({
      label: "Big Chances",
      homeDisplay: String(stats.home_big_chances),
      awayDisplay: String(stats.away_big_chances),
      homeNum: Number(stats.home_big_chances),
      awayNum: Number(stats.away_big_chances),
    });
  }
  if (!compact && stats.home_key_passes != null && stats.away_key_passes != null) {
    statRows.push({
      label: "Key Passes",
      homeDisplay: String(stats.home_key_passes),
      awayDisplay: String(stats.away_key_passes),
      homeNum: Number(stats.home_key_passes),
      awayNum: Number(stats.away_key_passes),
    });
  }
  if (!compact && stats.home_tackles_won != null && stats.away_tackles_won != null) {
    statRows.push({
      label: "Tackles Won",
      homeDisplay: String(stats.home_tackles_won),
      awayDisplay: String(stats.away_tackles_won),
      homeNum: Number(stats.home_tackles_won),
      awayNum: Number(stats.away_tackles_won),
    });
  }
  if (!compact && stats.home_interceptions != null && stats.away_interceptions != null) {
    statRows.push({
      label: "Interceptions",
      homeDisplay: String(stats.home_interceptions),
      awayDisplay: String(stats.away_interceptions),
      homeNum: Number(stats.home_interceptions),
      awayNum: Number(stats.away_interceptions),
    });
  }
  if (
    stats.home_yellow_cards != null &&
    stats.away_yellow_cards != null
  ) {
    const hY = Number(stats.home_yellow_cards || 0);
    const aY = Number(stats.away_yellow_cards || 0);
    const hR = Number(stats.home_red_cards || 0);
    const aR = Number(stats.away_red_cards || 0);
    statRows.push({
      label: "Cards (Y / R)",
      homeDisplay: `${hY} / ${hR}`,
      awayDisplay: `${aY} / ${aR}`,
      homeNum: hY + hR * 2,
      awayNum: aY + aR * 2,
    });
  }

  return (
    <div
      data-testid="simulated-match-report"
      className="space-y-4 rounded-xl border border-white/10 bg-slate-950/80 p-4 text-xs"
    >
      {/* Goal Scorers & Assists */}
      <div data-testid="simulated-match-scorers" className="space-y-2">
        <div className="flex items-center justify-between border-b border-white/10 pb-2">
          <span className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-wider text-emerald-300">
            <Target size={12} /> Goal Scorers & Assists
          </span>
          <span className="gx-mono text-[10px] text-slate-400">
            FT {report.home_score} – {report.away_score}
            {report.decided_by_penalties &&
            report.home_penalty_score != null &&
            report.away_penalty_score != null
              ? ` (${report.home_penalty_score}-${report.away_penalty_score} pens)`
              : ""}
          </span>
        </div>

        {goals.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                {report.home_team_name}
              </p>
              {homeGoals.length > 0 ? (
                homeGoals.map((g, idx) => (
                  <div
                    key={`hg-${idx}-${g.minute}`}
                    className="flex flex-wrap items-baseline justify-between gap-1 rounded border border-emerald-500/20 bg-emerald-500/5 px-2.5 py-1.5"
                  >
                    <div>
                      <span className="font-bold text-white">⚽ {g.scorer_name}</span>
                      {g.is_penalty && (
                        <span className="ml-1.5 rounded bg-amber-500/20 px-1 py-0.5 text-[9px] font-bold uppercase text-amber-300">
                          PEN
                        </span>
                      )}
                      {g.assist_name && (
                        <span className="ml-1.5 text-[11px] text-slate-300">
                          (ast. <b className="text-emerald-200">{g.assist_name}</b>)
                        </span>
                      )}
                    </div>
                    <span className="gx-mono text-[11px] font-bold text-emerald-300">
                      {formatGoalClock(g)}
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-[11px] italic text-slate-500">No goals</p>
              )}
            </div>

            <div className="space-y-1.5">
              <p className="text-[10px] font-bold uppercase tracking-wider text-amber-400">
                {report.away_team_name}
              </p>
              {awayGoals.length > 0 ? (
                awayGoals.map((g, idx) => (
                  <div
                    key={`ag-${idx}-${g.minute}`}
                    className="flex flex-wrap items-baseline justify-between gap-1 rounded border border-amber-500/20 bg-amber-500/5 px-2.5 py-1.5"
                  >
                    <div>
                      <span className="font-bold text-white">⚽ {g.scorer_name}</span>
                      {g.is_penalty && (
                        <span className="ml-1.5 rounded bg-amber-500/20 px-1 py-0.5 text-[9px] font-bold uppercase text-amber-300">
                          PEN
                        </span>
                      )}
                      {g.assist_name && (
                        <span className="ml-1.5 text-[11px] text-slate-300">
                          (ast. <b className="text-amber-200">{g.assist_name}</b>)
                        </span>
                      )}
                    </div>
                    <span className="gx-mono text-[11px] font-bold text-amber-300">
                      {formatGoalClock(g)}
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-[11px] italic text-slate-500">No goals</p>
              )}
            </div>
          </div>
        ) : (
          <p className="text-[11px] italic text-slate-400">
            Goalless draw ({report.home_score} – {report.away_score}) — neither side found the net.
          </p>
        )}
      </div>

      {/* Team Stats Comparison Bars */}
      {statRows.length > 0 && (
        <div data-testid="simulated-match-stats" className="space-y-2.5 border-t border-white/10 pt-3">
          <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-wider">
            <span className="text-emerald-300">{report.home_team_name}</span>
            <span className="text-slate-400">Match Statistics</span>
            <span className="text-amber-300">{report.away_team_name}</span>
          </div>
          <div className="space-y-2">
            {statRows.map((row) => (
              <StatBarRow key={row.label} {...row} />
            ))}
          </div>
        </div>
      )}

      {/* Discipline / Cards */}
      {cards.length > 0 && (
        <div data-testid="simulated-match-cards" className="border-t border-white/10 pt-3">
          <p className="mb-2 flex items-center gap-1.5 text-[10px] font-black uppercase tracking-wider text-slate-300">
            <Shield size={11} className="text-amber-400" /> Discipline & Bookings
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="space-y-1">
              {homeCards.map((c, idx) => (
                <div key={`hc-${idx}`} className="flex items-center justify-between text-[11px] text-slate-300">
                  <span>
                    <span
                      className={`mr-1.5 inline-block h-2.5 w-2 rounded-[1px] ${
                        c.card_type === "red_card" ? "bg-red-500" : "bg-amber-400"
                      }`}
                    />
                    {c.player_name}
                  </span>
                  <span className="gx-mono text-slate-400">{c.clock_label || `${c.minute}'`}</span>
                </div>
              ))}
            </div>
            <div className="space-y-1">
              {awayCards.map((c, idx) => (
                <div key={`ac-${idx}`} className="flex items-center justify-between text-[11px] text-slate-300">
                  <span>
                    <span
                      className={`mr-1.5 inline-block h-2.5 w-2 rounded-[1px] ${
                        c.card_type === "red_card" ? "bg-red-500" : "bg-amber-400"
                      }`}
                    />
                    {c.player_name}
                  </span>
                  <span className="gx-mono text-slate-400">{c.clock_label || `${c.minute}'`}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Man of the Match */}
      {motm?.available && motm.player_name && (
        <div
          data-testid="simulated-match-motm"
          className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-amber-400/30 bg-amber-500/10 px-3 py-2"
        >
          <div className="flex items-center gap-2">
            <Award size={15} className="shrink-0 text-amber-300" />
            <div>
              <p className="text-[10px] font-black uppercase tracking-wider text-amber-300">
                Man of the Match
              </p>
              <p className="font-bold text-white">
                {motm.player_name}{" "}
                <span className="font-normal text-slate-300">
                  ({motm.team_name || (motm.side === "home" ? report.home_team_name : report.away_team_name)})
                </span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 gx-mono text-[11px]">
            <span className="text-slate-200">
              {motm.goals ?? 0}G · {motm.assists ?? 0}A
            </span>
            {motm.rating != null && (
              <span className="rounded bg-amber-400 px-2 py-0.5 font-black text-slate-950">
                {Number(motm.rating).toFixed(1)}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Player Ratings / Individual Stats */}
      {playerStats.length > 0 && (
        <div data-testid="simulated-match-players" className="border-t border-white/10 pt-3">
          <p className="mb-2 text-[10px] font-black uppercase tracking-wider text-slate-400">
            {compact ? "Top Match Performers" : "Player Match Ratings & Contributions"}
          </p>
          {compact ? (
            <div className="grid gap-1.5 sm:grid-cols-2">
              {playerStats.slice(0, 4).map((p) => (
                <div
                  key={`${p.side}-${p.player_id}`}
                  className="flex items-center justify-between rounded border border-white/5 bg-white/[0.03] px-2.5 py-1.5"
                >
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-white">{p.player_name}</p>
                    <p className="truncate text-[10px] text-slate-400">
                      {p.team_name} · {p.role}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2 gx-mono text-[11px]">
                    {(p.goals || 0) > 0 && <span className="text-emerald-300">{p.goals}G</span>}
                    {(p.assists || 0) > 0 && <span className="text-cyan-300">{p.assists}A</span>}
                    {(p.saves || 0) > 0 && <span className="text-sky-300">{p.saves}SV</span>}
                    {p.rating != null && (
                      <span className="rounded bg-white/10 px-1.5 py-0.5 font-bold text-amber-300">
                        {Number(p.rating).toFixed(1)}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[11px]">
                <thead>
                  <tr className="border-b border-white/10 text-[10px] uppercase text-slate-400">
                    <th className="py-1.5 pr-2">Player</th>
                    <th className="py-1.5 px-2">Team</th>
                    <th className="py-1.5 px-1 text-center">Role</th>
                    <th className="py-1.5 px-1 text-center">G</th>
                    <th className="py-1.5 px-1 text-center">A</th>
                    <th className="py-1.5 px-1 text-center">KP</th>
                    <th className="py-1.5 px-1 text-center">SV</th>
                    <th className="py-1.5 pl-2 text-right">Rating</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {playerStats.slice(0, 14).map((p) => (
                    <tr key={`${p.side}-${p.player_id}`} className="hover:bg-white/[0.03]">
                      <td className="py-1.5 pr-2 font-semibold text-white">{p.player_name}</td>
                      <td className="py-1.5 px-2 text-slate-300">
                        <span className={p.side === "home" ? "text-emerald-300" : "text-amber-300"}>
                          {p.team_name}
                        </span>
                      </td>
                      <td className="py-1.5 px-1 text-center gx-mono text-slate-400">{p.role || "—"}</td>
                      <td className="py-1.5 px-1 text-center gx-mono font-bold text-emerald-300">
                        {p.goals || 0}
                      </td>
                      <td className="py-1.5 px-1 text-center gx-mono font-bold text-cyan-300">
                        {p.assists || 0}
                      </td>
                      <td className="py-1.5 px-1 text-center gx-mono text-slate-300">
                        {p.key_passes || 0}
                      </td>
                      <td className="py-1.5 px-1 text-center gx-mono text-slate-300">
                        {p.saves || 0}
                      </td>
                      <td className="py-1.5 pl-2 text-right gx-mono font-bold text-amber-300">
                        {p.rating != null ? Number(p.rating).toFixed(1) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
