import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, RefreshCw, Shield, Sliders, Sparkles, Tv } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import {
  buildLineupPayload,
  LINEUP_FORMATIONS,
  normalizeLineupPlan,
  normalizeLineupSquad,
  type LineupPlayer,
} from "@/pages/lineupModel";
import { buildSilhouetteDataUri, posShort, sanitizeRealPlayerImage } from "./PlayerCard";

export interface MatchdaySquadMember {
  player_id: string;
  full_name: string;
  short_name: string;
  shirt_number: number;
  position: string;
  rating: number;
  portrait_url: string | null;
  is_captain?: boolean;
  is_signed?: boolean;
  is_regen?: boolean;
}

export interface MatchdayTeamSheet {
  clubId: string;
  clubName: string;
  formation: string;
  starters: MatchdaySquadMember[];
  substitutes: MatchdaySquadMember[];
  hero: MatchdaySquadMember;
  avgRating: number;
  signedStarterCount: number;
}

const DEFAULT_NUMBERS = [1, 2, 4, 5, 3, 6, 8, 10, 7, 11, 9];
const SUB_NUMBERS = [13, 14, 15, 16, 17, 18, 20, 21, 23];

const ACADEMY_SURNAMES_POOL = [
  { name: "D. Rushworth", pos: "GK", rating: 78 },
  { name: "M. van Ewijk", pos: "RB", rating: 79 },
  { name: "B. Thomas", pos: "CB", rating: 78 },
  { name: "L. Kitching", pos: "CB", rating: 77 },
  { name: "J. Dasilva", pos: "LB", rating: 78 },
  { name: "M. Grimes", pos: "DM", rating: 81 },
  { name: "J. Rudoni", pos: "CM", rating: 80 },
  { name: "V. Torp", pos: "CM", rating: 79 },
  { name: "E. Mason-Clark", pos: "LW", rating: 80 },
  { name: "B. Thomas-Asante", pos: "RW", rating: 79 },
  { name: "H. Wright", pos: "ST", rating: 82 },
  { name: "R. Roefs", pos: "GK", rating: 77 },
  { name: "T. Hume", pos: "RB", rating: 79 },
  { name: "L. O'Nien", pos: "CB", rating: 78 },
  { name: "O. Alderete", pos: "CB", rating: 80 },
  { name: "R. Mandava", pos: "LB", rating: 80 },
  { name: "G. Xhaka", pos: "DM", rating: 84 },
  { name: "N. Sadiki", pos: "CM", rating: 78 },
  { name: "C. Rigg", pos: "CM", rating: 79 },
  { name: "E. Le Fée", pos: "AM", rating: 81 },
  { name: "I. Angulo", pos: "LW", rating: 78 },
  { name: "B. Brobbey", pos: "ST", rating: 82 },
  { name: "B. Wilson", pos: "GK", rating: 75 },
  { name: "L. Woolfenden", pos: "CB", rating: 76 },
  { name: "J. Latibeaudiere", pos: "CB", rating: 76 },
  { name: "J. Bidwell", pos: "LB", rating: 75 },
  { name: "F. Onyeka", pos: "DM", rating: 78 },
  { name: "J. Eccles", pos: "CM", rating: 76 },
  { name: "T. Sakamoto", pos: "RW", rating: 78 },
  { name: "M. Talbi", pos: "CB", rating: 77 },
  { name: "W. Isidor", pos: "ST", rating: 78 },
  { name: "E. Simms", pos: "ST", rating: 78 },
];

function hashSeed(input: string): number {
  let h = 2166136261;
  for (let i = 0; i < input.length; i += 1) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h >>> 0);
}

function extractBroadcastSurname(fullName: string): string {
  const clean = (fullName || "Player").trim();
  const parts = clean.split(/\s+/).filter(Boolean);
  if (parts.length <= 1) return clean;
  const particles = new Set(["van", "von", "de", "del", "della", "da", "di", "le", "la", "el", "al", "st.", "st"]);
  if (parts.length >= 2 && particles.has(parts[parts.length - 2].toLowerCase())) {
    return `${parts[parts.length - 2]} ${parts[parts.length - 1]}`;
  }
  return parts[parts.length - 1];
}

function classifyRoleBucket(position?: string): "GK" | "DEF" | "MID" | "FWD" {
  const p = (position || "").toLowerCase();
  if (/(^|[^a-z])(gk|goalkeeper|keeper)([^a-z]|$)/.test(p)) return "GK";
  if (/(def|cb|lb|rb|wb|back|d\s)/.test(p)) return "DEF";
  if (/(st|cf|fw|lw|rw|forward|striker|attacker|winger)/.test(p)) return "FWD";
  return "MID";
}

function clubMonogram(name: string): string {
  const words = (name || "GTEX")
    .replace(/[^A-Za-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 0 && !["FC", "CF", "SC", "AC"].includes(w.toUpperCase()));
  if (words.length >= 2) return `${words[0][0]}${words[1][0]}`.toUpperCase();
  return (words[0] || "GX").slice(0, 2).toUpperCase();
}

const EDITORIAL_ACCENTS = [
  { wordmark: "#DE869B", subText: "#C96A82", badgeBg: "#DE869B" }, // Sunderland coral-rose editorial
  { wordmark: "#5B9BD5", subText: "#3A7BB8", badgeBg: "#5B9BD5" }, // Coventry sky-blue editorial
  { wordmark: "#45B68C", subText: "#27946B", badgeBg: "#45B68C" }, // GTEX emerald-mint editorial
  { wordmark: "#D98A4E", subText: "#B96B30", badgeBg: "#D98A4E" }, // Warm amber-terracotta editorial
  { wordmark: "#8F7CC4", subText: "#6E5AA6", badgeBg: "#8F7CC4" }, // Royal violet editorial
];

function buildTeamSheetFromRoster(opts: {
  clubId: string;
  clubName: string;
  roster: LineupPlayer[];
  savedStarterIds: string[];
  savedBenchIds: string[];
  formation: string;
  lineupMode: "strongest" | "rotate";
  useSmartSuggestion: boolean;
  pitchPlayers?: Array<{
    player_id?: string;
    name?: string;
    shirt_number?: number;
    role?: string;
  }>;
}): MatchdayTeamSheet {
  const {
    clubId,
    clubName,
    roster,
    savedStarterIds,
    savedBenchIds,
    formation,
    lineupMode,
    useSmartSuggestion,
    pitchPlayers,
  } = opts;

  const seed = hashSeed(`${clubId}:${clubName}`);
  const validFormation = (LINEUP_FORMATIONS as readonly string[]).includes(formation) ? formation : "4-3-3";
  const [defCount, ...restLines] = validFormation.split("-").map((n) => Number(n) || 3);
  const fwdCount = restLines[restLines.length - 1] || 3;
  const midCount = Math.max(1, 10 - defCount - fwdCount);

  const byId = new Map<string, LineupPlayer>();
  roster.forEach((p) => byId.set(p.player_id, p));

  let chosenSignedStarters: LineupPlayer[] = [];
  const usedIds = new Set<string>();

  // Honor saved lineup unless owner explicitly triggers smart suggestion or rotation mode
  if (!useSmartSuggestion && lineupMode !== "rotate" && savedStarterIds.length > 0) {
    savedStarterIds.forEach((id) => {
      const found = byId.get(id);
      if (found && !usedIds.has(found.player_id) && chosenSignedStarters.length < 11) {
        chosenSignedStarters.push(found);
        usedIds.add(found.player_id);
      }
    });
  }

  // Smart tactical suggestion fill by role bucket (GK -> DEF -> MID -> FWD)
  if (chosenSignedStarters.length < 11 && roster.length > 0) {
    const remaining = roster.filter((p) => !usedIds.has(p.player_id));
    const sortFn = (a: LineupPlayer, b: LineupPlayer) => {
      const ra = Number(a.rating ?? 76);
      const rb = Number(b.rating ?? 76);
      return lineupMode === "rotate" ? ra - rb : rb - ra;
    };
    const gks = remaining.filter((p) => classifyRoleBucket(p.position) === "GK").sort(sortFn);
    const defs = remaining.filter((p) => classifyRoleBucket(p.position) === "DEF").sort(sortFn);
    const mids = remaining.filter((p) => classifyRoleBucket(p.position) === "MID").sort(sortFn);
    const fwds = remaining.filter((p) => classifyRoleBucket(p.position) === "FWD").sort(sortFn);

    const hasKeeperAlready = chosenSignedStarters.some((p) => classifyRoleBucket(p.position) === "GK");
    const pick = (pool: LineupPlayer[], count: number) => {
      for (const candidate of pool) {
        if (count <= 0 || chosenSignedStarters.length >= 11) break;
        if (!usedIds.has(candidate.player_id)) {
          chosenSignedStarters.push(candidate);
          usedIds.add(candidate.player_id);
          count -= 1;
        }
      }
    };

    if (!hasKeeperAlready && gks.length > 0) {
      chosenSignedStarters = [gks[0], ...chosenSignedStarters];
      usedIds.add(gks[0].player_id);
    }
    pick(defs, defCount);
    pick(mids, midCount);
    pick(fwds, fwdCount);

    // Fill any open signed slots with best remaining outfielders
    const anyLeft = remaining.filter((p) => !usedIds.has(p.player_id)).sort(sortFn);
    pick(anyLeft, 11 - chosenSignedStarters.length);
  }

  // Convert signed starters into MatchdaySquadMember
  const starters: MatchdaySquadMember[] = chosenSignedStarters.slice(0, 11).map((p, idx) => {
    const numBase = DEFAULT_NUMBERS[idx] || idx + 2;
    return {
      player_id: p.player_id,
      full_name: p.player_name,
      short_name: extractBroadcastSurname(p.player_name),
      shirt_number: numBase,
      position: posShort(p.position),
      rating: Math.round(Number(p.rating ?? 78)),
      portrait_url: sanitizeRealPlayerImage(p.portrait_url, false),
      is_signed: true,
    };
  });

  const signedStarterCount = starters.length;

  // If live pitchPlayers were supplied for an AI/opponent club with 0 signed roster rows, use them
  if (starters.length === 0 && pitchPlayers && pitchPlayers.length > 0) {
    pitchPlayers.slice(0, 11).forEach((pp, idx) => {
      const fullName = pp.name || ACADEMY_SURNAMES_POOL[(seed + idx) % ACADEMY_SURNAMES_POOL.length].name;
      starters.push({
        player_id: pp.player_id || `live-${clubId}-${idx}`,
        full_name: fullName,
        short_name: extractBroadcastSurname(fullName),
        shirt_number: pp.shirt_number || DEFAULT_NUMBERS[idx] || idx + 1,
        position: pp.role || (idx === 0 ? "GK" : idx <= 4 ? "DEF" : idx <= 7 ? "MID" : "FWD"),
        rating: 79 + ((seed + idx) % 7),
        portrait_url: null,
        is_signed: false,
      });
    });
  }

  // Fill any remaining slots up to 11 starters with deterministic matchday squad call-ups
  const usedNames = new Set(starters.map((s) => s.short_name.toLowerCase()));
  const usedNumbers = new Set(starters.map((s) => s.shirt_number));
  let poolCursor = seed % ACADEMY_SURNAMES_POOL.length;

  if (starters.length > 0 && !starters.some((s) => s.position === "GK")) {
    // Ensure slot 0 has a goalkeeper if club roster lacked one
    if (starters.length < 11) {
      const gkEntry = ACADEMY_SURNAMES_POOL.find((e) => e.pos === "GK") || ACADEMY_SURNAMES_POOL[0];
      starters.unshift({
        player_id: `acad-gk-${clubId}`,
        full_name: gkEntry.name,
        short_name: extractBroadcastSurname(gkEntry.name),
        shirt_number: usedNumbers.has(1) ? 19 : 1,
        position: "GK",
        rating: gkEntry.rating,
        portrait_url: null,
        is_signed: false,
      });
      usedNames.add(extractBroadcastSurname(gkEntry.name).toLowerCase());
      usedNumbers.add(starters[0].shirt_number);
    }
  }

  while (starters.length < 11) {
    const idx = starters.length;
    const candidate = ACADEMY_SURNAMES_POOL[poolCursor % ACADEMY_SURNAMES_POOL.length];
    poolCursor += 1;
    const surname = extractBroadcastSurname(candidate.name);
    if (usedNames.has(surname.toLowerCase())) continue;
    usedNames.add(surname.toLowerCase());
    let shirt = DEFAULT_NUMBERS[idx] || idx + 12;
    while (usedNumbers.has(shirt)) shirt += 11;
    usedNumbers.add(shirt);
    starters.push({
      player_id: `acad-${clubId}-${idx}`,
      full_name: candidate.name,
      short_name: surname,
      shirt_number: shirt,
      position: idx === 0 ? "GK" : candidate.pos,
      rating: lineupMode === "rotate" ? candidate.rating - 2 : candidate.rating,
      portrait_url: null,
      is_signed: false,
    });
  }

  // Appoint Captain: highest-rated signed starter (or highest-rated starter overall)
  let captainIdx = 0;
  let bestScore = -1;
  starters.forEach((s, idx) => {
    const score = s.rating + (s.is_signed ? 15 : 0) + (idx > 0 ? 2 : 0);
    if (score > bestScore) {
      bestScore = score;
      captainIdx = idx;
    }
  });
  starters[captainIdx] = { ...starters[captainIdx], is_captain: true };

  // Build 7-9 Substitutes from savedBenchIds + remaining signed players + academy bench
  const substitutes: MatchdaySquadMember[] = [];
  const benchCandidates: LineupPlayer[] = [];
  savedBenchIds.forEach((id) => {
    const p = byId.get(id);
    if (p && !usedIds.has(p.player_id)) {
      benchCandidates.push(p);
      usedIds.add(p.player_id);
    }
  });
  roster.forEach((p) => {
    if (!usedIds.has(p.player_id)) {
      benchCandidates.push(p);
      usedIds.add(p.player_id);
    }
  });

  benchCandidates.slice(0, 9).forEach((p, idx) => {
    let shirt = SUB_NUMBERS[idx] || 22 + idx;
    while (usedNumbers.has(shirt)) shirt += 1;
    usedNumbers.add(shirt);
    const surname = extractBroadcastSurname(p.player_name);
    usedNames.add(surname.toLowerCase());
    substitutes.push({
      player_id: p.player_id,
      full_name: p.player_name,
      short_name: surname,
      shirt_number: shirt,
      position: posShort(p.position),
      rating: Math.round(Number(p.rating ?? 75)),
      portrait_url: sanitizeRealPlayerImage(p.portrait_url, false),
      is_signed: true,
    });
  });

  while (substitutes.length < 8) {
    const idx = substitutes.length;
    const candidate = ACADEMY_SURNAMES_POOL[poolCursor % ACADEMY_SURNAMES_POOL.length];
    poolCursor += 1;
    const surname = extractBroadcastSurname(candidate.name);
    if (usedNames.has(surname.toLowerCase())) continue;
    usedNames.add(surname.toLowerCase());
    let shirt = SUB_NUMBERS[idx] || 24 + idx;
    while (usedNumbers.has(shirt)) shirt += 1;
    usedNumbers.add(shirt);
    substitutes.push({
      player_id: `bench-${clubId}-${idx}`,
      full_name: candidate.name,
      short_name: surname,
      shirt_number: shirt,
      position: candidate.pos,
      rating: candidate.rating - 2,
      portrait_url: null,
      is_signed: false,
    });
  }

  // Hero spotlight player: prefer a starter WITH a verified real photo (captain first, then highest GSI), else captain
  const picturedStarters = starters.filter((s) => Boolean(s.portrait_url));
  const hero =
    picturedStarters.find((s) => s.is_captain) ||
    [...picturedStarters].sort((a, b) => b.rating - a.rating)[0] ||
    starters[captainIdx] ||
    starters[0];

  const avgRating = Math.round(starters.reduce((sum, s) => sum + s.rating, 0) / starters.length);

  return {
    clubId,
    clubName,
    formation: validFormation,
    starters,
    substitutes,
    hero,
    avgRating,
    signedStarterCount,
  };
}

export function useClubMatchdaySheet(opts: {
  clubId?: string;
  clubName?: string;
  lineupMode?: "strongest" | "rotate";
  formationOverride?: string;
  useSmartSuggestion?: boolean;
  pitchPlayers?: Array<{
    player_id?: string;
    name?: string;
    shirt_number?: number;
    role?: string;
  }>;
}) {
  const clubId = opts.clubId || "";
  const isRealClub = Boolean(clubId && !clubId.startsWith("ai:"));

  const rosterQuery = useQuery({
    queryKey: ["lineup-squad", clubId],
    queryFn: async () =>
      normalizeLineupSquad((await api.get(`/market/clubs/${encodeURIComponent(clubId)}/players`)).data),
    enabled: isRealClub,
    staleTime: 30_000,
  });

  const planQuery = useQuery({
    queryKey: ["lineup-plan", clubId],
    queryFn: async () => {
      try {
        return normalizeLineupPlan((await api.get(`/clubs/${encodeURIComponent(clubId)}/lineup`)).data);
      } catch {
        return normalizeLineupPlan({});
      }
    },
    enabled: isRealClub,
    staleTime: 30_000,
  });

  const sheet = useMemo(
    () =>
      buildTeamSheetFromRoster({
        clubId: clubId || "club-home",
        clubName: opts.clubName || "GTEX FC",
        roster: rosterQuery.data || [],
        savedStarterIds: planQuery.data?.starter_player_ids || [],
        savedBenchIds: planQuery.data?.bench_player_ids || [],
        formation: opts.formationOverride || planQuery.data?.formation || "4-3-3",
        lineupMode: opts.lineupMode || "strongest",
        useSmartSuggestion: Boolean(opts.useSmartSuggestion),
        pitchPlayers: opts.pitchPlayers,
      }),
    [
      clubId,
      opts.clubName,
      rosterQuery.data,
      planQuery.data,
      opts.formationOverride,
      opts.lineupMode,
      opts.useSmartSuggestion,
      opts.pitchPlayers,
    ],
  );

  return {
    sheet,
    roster: rosterQuery.data || [],
    isLoading: isRealClub && (rosterQuery.isLoading || planQuery.isLoading),
  };
}

/**
 * Style A: Coventry Broadcast Dark Tunnel Split Card ("Starting XI")
 */
export function TunnelStartingXICard({
  sheet,
  opponentName,
  competitionName,
  roundLabel,
  testid,
}: {
  sheet: MatchdayTeamSheet;
  opponentName?: string;
  competitionName?: string;
  roundLabel?: string;
  testid?: string;
}) {
  const heroFallback = buildSilhouetteDataUri(sheet.hero.position, sheet.hero.rating >= 85);
  const [heroSrc, setHeroSrc] = useState<string>(sheet.hero.portrait_url || heroFallback);

  React.useEffect(() => {
    setHeroSrc(sheet.hero.portrait_url || buildSilhouetteDataUri(sheet.hero.position, sheet.hero.rating >= 85));
  }, [sheet.hero.portrait_url, sheet.hero.position, sheet.hero.rating]);

  return (
    <div
      data-testid={testid || "matchday-tunnel-xi-card"}
      className="relative overflow-hidden rounded-xl border border-sky-400/20 bg-[#050811] text-white shadow-[0_24px_60px_rgba(2,6,23,0.85)]"
      style={{
        backgroundImage:
          "radial-gradient(circle at 78% 36%, rgba(56, 189, 248, 0.24) 0%, rgba(14, 116, 144, 0.08) 38%, rgba(5, 8, 17, 0.98) 72%), linear-gradient(135deg, #04070e 0%, #091326 54%, #050914 100%)",
      }}
    >
      {/* Subtle vertical tunnel stadium light beam */}
      <div
        className="pointer-events-none absolute inset-y-0 right-[24%] w-24 opacity-25 blur-2xl"
        style={{
          background: "linear-gradient(180deg, rgba(125,211,252,0.55) 0%, rgba(56,189,248,0.12) 60%, transparent 100%)",
        }}
      />

      <div className="relative z-10 grid min-h-[470px] grid-cols-12">
        {/* Left Column: Starting XI & Bench */}
        <div className="col-span-7 sm:col-span-7 flex flex-col justify-between p-5 sm:p-6">
          <div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-[10px] font-bold uppercase tracking-[0.22em] text-sky-300/80">
                {sheet.clubName} · {sheet.formation}
              </span>
              {roundLabel && (
                <span className="rounded bg-sky-500/15 px-2 py-0.5 text-[9px] font-black uppercase tracking-wider text-sky-300">
                  {roundLabel}
                </span>
              )}
            </div>

            {/* Signature "Starting / XI" Typography */}
            <div className="mt-2 mb-4 select-none">
              <p className="text-lg sm:text-xl font-bold tracking-tight text-sky-100/95 leading-none">
                Starting
              </p>
              <p className="gx-display text-[54px] sm:text-[64px] font-black tracking-tighter text-white leading-[0.84]">
                XI
              </p>
            </div>

            {/* 11 Starters Vertical List */}
            <ol className="space-y-1 text-[13px] sm:text-[14px] leading-snug" data-testid="tunnel-starters-list">
              {sheet.starters.map((player) => (
                <li
                  key={player.player_id}
                  className="group flex items-baseline gap-2.5 rounded px-1 py-0.5 transition-colors hover:bg-white/[0.04]"
                >
                  <span className="gx-mono w-5 shrink-0 text-right text-[11px] font-bold text-sky-300/80">
                    {player.shirt_number}
                  </span>
                  <span className="truncate font-semibold tracking-tight text-white">
                    {player.short_name}
                    {player.is_captain && (
                      <span className="ml-1.5 text-[11px] font-black text-sky-300">(C)</span>
                    )}
                  </span>
                  <span className="ml-auto hidden sm:inline-block gx-mono text-[10px] text-slate-400/80">
                    {player.position} · {player.rating}
                  </span>
                </li>
              ))}
            </ol>

            {/* Compact Substitutes Block */}
            <div className="mt-4 border-t border-white/10 pt-2.5">
              <p className="text-[9px] font-black uppercase tracking-[0.2em] text-sky-300/70">
                Substitutes
              </p>
              <p className="mt-0.5 text-[10.5px] leading-relaxed text-slate-300/80">
                {sheet.substitutes.map((s) => s.short_name).join(", ")}.
              </p>
            </div>
          </div>

          {/* Footer Club Crests & Broadcast Mark */}
          <div className="mt-4 flex items-center gap-2.5 pt-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full border border-sky-300/40 bg-sky-500/15 text-[11px] font-black text-sky-200 shadow-inner">
              {clubMonogram(sheet.clubName)}
            </div>
            {opponentName && (
              <>
                <span className="text-[10px] font-bold text-slate-500">VS</span>
                <div className="flex h-7 w-7 items-center justify-center rounded-full border border-white/15 bg-white/5 text-[10px] font-bold text-slate-300">
                  {clubMonogram(opponentName)}
                </div>
              </>
            )}
            <div className="ml-1 border-l border-white/10 pl-2.5">
              <p className="text-[9px] font-black uppercase tracking-[0.18em] text-sky-300">
                {competitionName || "GTEX MATCHDAY LIVE"}
              </p>
              <p className="text-[9px] text-slate-400">
                Avg XI GSI {sheet.avgRating}
              </p>
            </div>
          </div>
        </div>

        {/* Right Column: Dramatic Rim-Lit Hero Player Spotlight */}
        <div className="col-span-5 sm:col-span-5 relative flex flex-col justify-end overflow-hidden">
          <div className="relative mx-auto flex h-full w-full items-end justify-center pt-8">
            <img
              src={heroSrc}
              alt={sheet.hero.full_name}
              onError={() => setHeroSrc(heroFallback)}
              className="max-h-[370px] w-full object-contain object-bottom drop-shadow-[0_14px_28px_rgba(56,189,248,0.28)] transition-transform duration-500"
            />
            <div
              className="pointer-events-none absolute inset-x-0 bottom-0 h-28"
              style={{
                background: "linear-gradient(180deg, transparent 0%, rgba(5,8,17,0.86) 68%, #050811 100%)",
              }}
            />
          </div>

          <div className="relative z-10 p-3 sm:p-4 text-right">
            <span className="inline-block rounded bg-sky-400/15 border border-sky-300/30 px-1.5 py-0.5 text-[9px] font-black uppercase tracking-widest text-sky-200">
              #{sheet.hero.shirt_number} {sheet.hero.is_captain ? "CAPTAIN" : "KEY STARTER"}
            </span>
            <p className="mt-1 truncate text-xs sm:text-sm font-black uppercase tracking-wide text-white">
              {sheet.hero.full_name}
            </p>
            <p className="gx-mono text-[10px] text-sky-300/90">
              {sheet.hero.position} · GSI {sheet.hero.rating}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Style B: Sunderland Editorial Matchday Poster ("LINEUP")
 */
export function EditorialLineupPosterCard({
  sheet,
  venueName,
  matchdayNumber = 1,
  dateLabel,
  testid,
}: {
  sheet: MatchdayTeamSheet;
  venueName?: string;
  matchdayNumber?: number | string;
  dateLabel?: string;
  testid?: string;
}) {
  const accent = useMemo(() => {
    const idx = hashSeed(sheet.clubName) % EDITORIAL_ACCENTS.length;
    return EDITORIAL_ACCENTS[idx];
  }, [sheet.clubName]);

  const heroFallback = buildSilhouetteDataUri(sheet.hero.position, sheet.hero.rating >= 85);
  const [heroSrc, setHeroSrc] = useState<string>(sheet.hero.portrait_url || heroFallback);

  React.useEffect(() => {
    setHeroSrc(sheet.hero.portrait_url || buildSilhouetteDataUri(sheet.hero.position, sheet.hero.rating >= 85));
  }, [sheet.hero.portrait_url, sheet.hero.position, sheet.hero.rating]);

  const formattedDate =
    dateLabel ||
    new Date()
      .toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" })
      .replace(/\//g, ".");
  const formattedMd = String(matchdayNumber).padStart(2, "0");
  const arenaLabel = (venueName || `${sheet.clubName} Stadium`).toUpperCase();

  return (
    <div
      data-testid={testid || "matchday-editorial-poster-card"}
      className="relative overflow-hidden rounded-2xl border border-[#25354B] bg-[#0E1A2C] text-white shadow-[0_24px_60px_rgba(0,0,0,0.85)]"
      style={{
        backgroundImage:
          "radial-gradient(circle at 20% 20%, rgba(229,182,63,0.12) 0%, rgba(20,36,58,0.95) 55%, #080F1C 100%)",
      }}
    >
      {/* Top Condensed Editorial Matchday Metadata Strip */}
      <div className="px-4 sm:px-6 pt-3.5">
        <div className="flex items-center justify-between gap-2 border-b border-[#25354B] pb-1.5 text-[9.5px] sm:text-[10.5px] font-black uppercase tracking-[0.14em] text-slate-300">
          <span className="truncate">
            MATCHDAY {formattedMd} · LIVE FROM {arenaLabel} · {formattedDate}
          </span>
          <span className="shrink-0 gx-mono text-[9.5px] font-black text-[#00E8A8] bg-[#00C991]/15 px-2 py-0.5 rounded border border-[#00C991]/30">
            {sheet.formation}
          </span>
        </div>
      </div>

      {/* Giant Oversized Editorial "LINEUP" Display Wordmark (Layered Behind Hero Cutout) */}
      <div className="relative min-h-[435px] px-4 sm:px-6 pb-5 pt-1">
        <div
          aria-hidden="true"
          className="pointer-events-none select-none overflow-hidden text-center leading-none"
        >
          <span
            className="gx-display block text-[68px] sm:text-[86px] font-black uppercase tracking-[-0.04em] drop-shadow-[0_4px_24px_rgba(0,0,0,0.7)]"
            style={{ color: accent.wordmark, lineHeight: 0.88 }}
          >
            LINEUP
          </span>
        </div>

        <div className="relative z-10 -mt-5 sm:-mt-7 grid grid-cols-12 items-end gap-2">
          {/* Left Hero Cutout Overlapping "LI" of LINEUP */}
          <div className="col-span-5 flex flex-col justify-end self-stretch">
            <div className="relative mt-auto flex items-end justify-center">
              <img
                src={heroSrc}
                alt={sheet.hero.full_name}
                onError={() => setHeroSrc(heroFallback)}
                className="max-h-[300px] w-full object-contain object-bottom drop-shadow-[0_16px_28px_rgba(0,0,0,0.85)]"
              />
            </div>
            <div className="mt-1.5 rounded-xl border border-[#25354B] bg-[#080F1C]/95 px-2.5 py-1.5 text-center text-white shadow-lg backdrop-blur-md">
              <p className="truncate text-[10.5px] font-black uppercase tracking-wider text-[#00E8A8]">
                {sheet.hero.short_name} #{sheet.hero.shirt_number}
              </p>
              <p className="text-[9px] uppercase tracking-widest text-slate-400 font-semibold">
                {sheet.clubName} · GSI {sheet.hero.rating}
              </p>
            </div>
          </div>

          {/* Center-Right Numbered Uppercase Bold Starting XI Stack */}
          <div className="col-span-7 flex flex-col items-center text-center">
            <ol className="space-y-1 sm:space-y-1.5" data-testid="editorial-starters-list">
              {sheet.starters.map((player) => (
                <li
                  key={player.player_id}
                  className="flex items-baseline justify-center gap-2 leading-none"
                >
                  <span className="gx-mono text-[10px] sm:text-[11px] font-black text-[#E5B63F]">
                    {String(player.shirt_number).padStart(2, "0")}
                  </span>
                  <span className="gx-display text-[15px] sm:text-[18px] font-black uppercase tracking-tight text-white hover:text-[#00E8A8] transition-colors">
                    {player.short_name}
                    {player.is_captain ? " (C)" : ""}
                  </span>
                </li>
              ))}
            </ol>

            {/* Centered Club-Accent Uppercase Substitutes Block */}
            <div className="mt-4 max-w-[260px] border-t border-[#25354B] pt-2.5 text-center">
              <p
                className="text-[9.5px] sm:text-[10px] font-black uppercase leading-snug tracking-[0.06em]"
                style={{ color: accent.subText }}
              >
                {sheet.substitutes.map((s) => s.short_name.toUpperCase()).join(", ")}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Full Matchday Lineup Suggestion & Broadcast Presentation Panel
 */
export function MatchdayLineupBroadcast({
  homeClubId,
  homeClubName,
  awayClubId,
  awayClubName,
  editableClubId,
  competitionName,
  roundLabel,
  matchdayNumber = 1,
  venueName,
  lineupMode = "strongest",
  formationOverride,
  onFormationChange,
  homePitchPlayers,
  awayPitchPlayers,
  defaultView,
}: {
  homeClubId?: string;
  homeClubName: string;
  awayClubId?: string;
  awayClubName?: string;
  editableClubId?: string;
  competitionName?: string;
  roundLabel?: string;
  matchdayNumber?: number | string;
  venueName?: string;
  lineupMode?: "strongest" | "rotate";
  formationOverride?: string;
  onFormationChange?: (formation: string) => void;
  homePitchPlayers?: Array<{ player_id?: string; name?: string; shirt_number?: number; role?: string }>;
  awayPitchPlayers?: Array<{ player_id?: string; name?: string; shirt_number?: number; role?: string }>;
  defaultView?: "dual" | "tunnel" | "editorial";
}) {
  const queryClient = useQueryClient();
  const hasAway = Boolean(awayClubName);
  const [viewStyle, setViewStyle] = useState<"dual" | "tunnel" | "editorial">(
    defaultView || (hasAway ? "dual" : "tunnel"),
  );
  const [localFormation, setLocalFormation] = useState<string>(formationOverride || "");
  const [useSmartSuggestion, setUseSmartSuggestion] = useState<boolean>(true);
  const [savingSuggested, setSavingSuggested] = useState<boolean>(false);

  const activeFormation = formationOverride || localFormation || undefined;

  const home = useClubMatchdaySheet({
    clubId: homeClubId,
    clubName: homeClubName,
    lineupMode: editableClubId && editableClubId === awayClubId ? "strongest" : lineupMode,
    formationOverride:
      !editableClubId || editableClubId === homeClubId ? activeFormation : undefined,
    useSmartSuggestion,
    pitchPlayers: homePitchPlayers,
  });

  const away = useClubMatchdaySheet({
    clubId: awayClubId || "ai:away",
    clubName: awayClubName || "Away XI",
    lineupMode: editableClubId && editableClubId === awayClubId ? lineupMode : "strongest",
    formationOverride:
      editableClubId && editableClubId === awayClubId ? activeFormation : undefined,
    useSmartSuggestion,
    pitchPlayers: awayPitchPlayers,
  });

  const myTarget =
    editableClubId && editableClubId === awayClubId && hasAway ? away : home;
  const canPersistToClub = Boolean(
    editableClubId && !editableClubId.startsWith("ai:") && myTarget.roster.length > 0,
  );

  const handleSaveSuggestion = async () => {
    if (!editableClubId || !canPersistToClub) return;
    setSavingSuggested(true);
    try {
      const signedStarterIds = myTarget.sheet.starters
        .filter((s) => s.is_signed)
        .map((s) => s.player_id);
      const signedBenchIds = myTarget.sheet.substitutes
        .filter((s) => s.is_signed)
        .map((s) => s.player_id);
      const payload = buildLineupPayload(
        myTarget.sheet.formation,
        signedStarterIds,
        signedBenchIds,
        myTarget.roster.map((p) => p.player_id),
      );
      const saved = (
        await api.put(`/clubs/${encodeURIComponent(editableClubId)}/lineup`, payload)
      ).data;
      queryClient.setQueryData(["lineup-plan", editableClubId], normalizeLineupPlan(saved));
      setUseSmartSuggestion(false);
      toast.success(`Matchday Starting XI (${myTarget.sheet.formation}) locked in for ${myTarget.sheet.clubName}!`);
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setSavingSuggested(false);
    }
  };

  return (
    <div className="space-y-4" data-testid="matchday-lineup-broadcast">
      {/* Smart Matchday Lineup Suggestion Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-500/25 bg-slate-950/75 px-4 py-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/40 bg-emerald-500/15 px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider text-emerald-300">
            <Sparkles size={11} /> AI Matchday XI Suggestion
          </span>
          <span className="text-xs text-slate-300">
            <b className="text-white">{myTarget.sheet.clubName}</b> ·{" "}
            <span className="gx-mono text-emerald-300">{myTarget.sheet.formation}</span> · Avg XI GSI{" "}
            <b className="gx-mono text-amber-300">{myTarget.sheet.avgRating}</b> · Captain{" "}
            <b className="text-sky-300">{myTarget.sheet.hero.short_name}</b>
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Formation Quick Selector */}
          <label className="flex items-center gap-1.5 rounded border border-white/10 bg-white/[0.03] px-2 py-1 text-[11px] text-slate-300">
            <Sliders size={11} className="text-emerald-400" />
            <select
              aria-label="Matchday formation"
              value={activeFormation || myTarget.sheet.formation}
              onChange={(e) => {
                setLocalFormation(e.target.value);
                setUseSmartSuggestion(true);
                onFormationChange?.(e.target.value);
              }}
              className="bg-transparent gx-mono text-[11px] font-bold text-white focus:outline-none"
            >
              {LINEUP_FORMATIONS.map((f) => (
                <option key={f} value={f} className="bg-slate-900 text-white">
                  {f}
                </option>
              ))}
            </select>
          </label>

          {/* Toggle Saved vs Auto-Suggested Best XI */}
          <button
            type="button"
            onClick={() => setUseSmartSuggestion((prev) => !prev)}
            className="inline-flex items-center gap-1 rounded border border-sky-400/35 bg-sky-500/10 px-2.5 py-1 text-[10px] font-black uppercase tracking-wider text-sky-300 hover:bg-sky-500/20"
          >
            <RefreshCw size={11} />
            {useSmartSuggestion ? "Suggested Best XI" : "Saved Club XI"}
          </button>

          {canPersistToClub && (
            <button
              type="button"
              disabled={savingSuggested}
              onClick={handleSaveSuggestion}
              data-testid="lock-suggested-xi-btn"
              className="inline-flex items-center gap-1 rounded border border-emerald-400/50 bg-emerald-500/20 px-2.5 py-1 text-[10px] font-black uppercase tracking-wider text-emerald-200 hover:bg-emerald-500/30 disabled:opacity-50"
            >
              <Check size={11} />
              {savingSuggested ? "Locking XI…" : "Lock In XI"}
            </button>
          )}

          {editableClubId && !editableClubId.startsWith("ai:") && (
            <Link
              to={`/app/lineup?club_id=${encodeURIComponent(editableClubId)}`}
              className="inline-flex items-center gap-1 rounded border border-white/15 bg-white/5 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-200 hover:border-white/30"
            >
              <Shield size={11} /> Edit Squad XI →
            </Link>
          )}

          {/* Broadcast Graphic Theme Switcher */}
          <div className="flex items-center rounded border border-white/10 bg-black/50 p-0.5">
            {hasAway && (
              <button
                type="button"
                onClick={() => setViewStyle("dual")}
                className={`rounded-xs px-2 py-0.5 text-[10px] font-black uppercase transition-colors ${
                  viewStyle === "dual" ? "bg-emerald-500/25 text-emerald-300" : "text-slate-400 hover:text-white"
                }`}
              >
                Dual Sheet
              </button>
            )}
            <button
              type="button"
              onClick={() => setViewStyle("tunnel")}
              className={`inline-flex items-center gap-1 rounded-xs px-2 py-0.5 text-[10px] font-black uppercase transition-colors ${
                viewStyle === "tunnel" ? "bg-sky-500/25 text-sky-300" : "text-slate-400 hover:text-white"
              }`}
            >
              <Tv size={10} /> Tunnel XI
            </button>
            <button
              type="button"
              onClick={() => setViewStyle("editorial")}
              className={`rounded-xs px-2 py-0.5 text-[10px] font-black uppercase transition-colors ${
                viewStyle === "editorial" ? "bg-rose-400/25 text-rose-200" : "text-slate-400 hover:text-white"
              }`}
            >
              Editorial Poster
            </button>
          </div>
        </div>
      </div>

      {/* Broadcast Cards Grid */}
      {viewStyle === "dual" && hasAway ? (
        <div className="grid gap-5 xl:grid-cols-2">
          <TunnelStartingXICard
            sheet={home.sheet}
            opponentName={awayClubName}
            competitionName={competitionName}
            roundLabel={roundLabel || `MATCHDAY ${matchdayNumber}`}
            testid="home-tunnel-xi-card"
          />
          <EditorialLineupPosterCard
            sheet={away.sheet}
            venueName={venueName || `${homeClubName} Arena`}
            matchdayNumber={matchdayNumber}
            testid="away-editorial-poster-card"
          />
        </div>
      ) : viewStyle === "tunnel" ? (
        <div className={hasAway ? "grid gap-5 xl:grid-cols-2" : "max-w-2xl"}>
          <TunnelStartingXICard
            sheet={myTarget.sheet}
            opponentName={
              myTarget.sheet.clubName === homeClubName ? awayClubName : homeClubName
            }
            competitionName={competitionName}
            roundLabel={roundLabel || `MATCHDAY ${matchdayNumber}`}
          />
          {hasAway && myTarget.sheet.clubName === homeClubName && (
            <TunnelStartingXICard
              sheet={away.sheet}
              opponentName={homeClubName}
              competitionName={competitionName}
              roundLabel="OPPONENT XI"
              testid="opponent-tunnel-xi-card"
            />
          )}
        </div>
      ) : (
        <div className={hasAway ? "grid gap-5 xl:grid-cols-2" : "max-w-2xl"}>
          <EditorialLineupPosterCard
            sheet={myTarget.sheet}
            venueName={venueName || `${homeClubName} Arena`}
            matchdayNumber={matchdayNumber}
          />
          {hasAway && myTarget.sheet.clubName === homeClubName && (
            <EditorialLineupPosterCard
              sheet={away.sheet}
              venueName={venueName || `${homeClubName} Arena`}
              matchdayNumber={matchdayNumber}
              testid="opponent-editorial-poster-card"
            />
          )}
        </div>
      )}
    </div>
  );
}
