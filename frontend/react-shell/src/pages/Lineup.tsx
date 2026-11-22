import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, CircleHelp, Save, ShieldCheck, Users } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { useActiveClub, useClub } from "@/lib/owner";
import { Btn, Chip, Empty, Loading, PageHeader, Panel } from "@/components/gtex/ui";
import { MatchdayLineupBroadcast } from "@/components/gtex/MatchdayLineupBroadcast";
import { KitBakedMark } from "@/components/gtex/KitBakedMark";
import {
  buildLineupPayload,
  LINEUP_FORMATIONS,
  lineupRoleLabels,
  lineupFormationRows,
  lineupSheet,
  normalizeLineupSquad,
  type LineupPlayer,
} from "./lineupModel";

function playerPositionLine(position?: string | null): "GK" | "DEF" | "MID" | "FWD" {
  const raw = String(position || "")
    .trim()
    .toUpperCase()
    .split("/")[0]
    .trim();
  if (raw === "GK" || raw === "GOALKEEPER" || raw.startsWith("GOAL")) return "GK";
  if (
    ["CB", "LB", "RB", "LWB", "RWB", "DF", "DEF", "SW"].includes(raw) ||
    raw.startsWith("DEF") ||
    raw.includes("BACK")
  ) {
    return "DEF";
  }
  if (
    ["DM", "CDM", "CM", "AM", "CAM", "LM", "RM", "MF", "MID"].includes(raw) ||
    raw.startsWith("MID")
  ) {
    return "MID";
  }
  if (
    ["ST", "CF", "LW", "RW", "SS", "FW", "FWD", "ATT"].includes(raw) ||
    raw.startsWith("FORW") ||
    raw.startsWith("STRIK")
  ) {
    return "FWD";
  }
  return "MID";
}

function formationLineTargets(shape: string): { def: number; mid: number; fwd: number } {
  const parts = String(shape || "4-3-3")
    .split("-")
    .map((p) => Number(p))
    .filter((n) => Number.isFinite(n) && n > 0);
  if (parts.length >= 3 && parts.reduce((acc, n) => acc + n, 0) === 10) {
    return {
      def: parts[0],
      fwd: parts[parts.length - 1],
      mid: parts.slice(1, -1).reduce((acc, n) => acc + n, 0),
    };
  }
  return { def: 4, mid: 3, fwd: 3 };
}

function slotPlayersForShape(
  shape: string,
  firstTeamPool: LineupPlayer[],
  preferredIds: string[] = [],
): string[] {
  const byId = new Map(firstTeamPool.map((p) => [p.player_id, p]));
  const preferred = preferredIds
    .map((id) => byId.get(id))
    .filter((p): p is LineupPlayer => Boolean(p));
  const ranked = [...firstTeamPool].sort(
    (a, b) =>
      Number(b.effective_match_rating ?? b.rating ?? 0) -
      Number(a.effective_match_rating ?? a.rating ?? 0),
  );
  const candidates: LineupPlayer[] = [];
  const seen = new Set<string>();
  for (const p of [...preferred, ...ranked]) {
    if (!seen.has(p.player_id)) {
      candidates.push(p);
      seen.add(p.player_id);
    }
  }
  const used = new Set<string>();
  const takeLine = (line: "GK" | "DEF" | "MID" | "FWD", count: number) => {
    const out: LineupPlayer[] = [];
    for (const p of candidates) {
      if (out.length >= count) break;
      if (used.has(p.player_id)) continue;
      if (playerPositionLine(p.position) === line) {
        out.push(p);
        used.add(p.player_id);
      }
    }
    return out;
  };
  const targets = formationLineTargets(shape);
  const gk = takeLine("GK", 1);
  const defs = takeLine("DEF", targets.def);
  const mids = takeLine("MID", targets.mid);
  const fwds = takeLine("FWD", targets.fwd);
  const topUp = (bucket: LineupPlayer[], count: number, allowGk = false) => {
    for (const p of candidates) {
      if (bucket.length >= count) break;
      if (used.has(p.player_id)) continue;
      if (!allowGk && playerPositionLine(p.position) === "GK") continue;
      bucket.push(p);
      used.add(p.player_id);
    }
  };
  topUp(gk, 1, true);
  topUp(defs, targets.def);
  topUp(mids, targets.mid);
  topUp(fwds, targets.fwd);
  const ordered = [...gk, ...defs, ...mids, ...fwds].slice(0, 11).map((p) => p.player_id);
  return [...ordered, ...Array(11).fill("")].slice(0, 11);
}

function mapClubDetailToRoster(clubDetail: any) {
  return {
    squad: normalizeLineupSquad({
      items: (clubDetail?.squad || []).map((player: any) => ({
        player_id: player.id,
        player_name: player.name,
        position: player.position_display || player.position,
        rating: player.rating,
        portrait_url: player.portrait_url,
        squad_status: player.squad_status,
        is_regen: player.is_regen,
        age: player.age,
        minutes: player.minutes,
        acquired_via: player.acquired_via,
        morale: player.morale,
        mood_state: player.mood_state,
        performance_shift: player.performance_shift,
        effective_match_rating: player.effective_match_rating,
      })),
    }),
    filedIds: (clubDetail?.matchday_xi || []).map((player: any) => String(player.id)),
    filedBench: (clubDetail?.matchday_bench || []).map((player: any) => String(player.id)),
    filedFormation: clubDetail?.matchday_formation || clubDetail?.tactics?.formation || "",
    tactics: clubDetail?.tactics || null,
  };
}

export default function Lineup() {
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const { clubs, active } = useActiveClub();
  const clubId = searchParams.get("club_id") || active?.club_id || undefined;
  const club = clubs.find((item: any) => item.club_id === clubId) || active;
  const cachedClubQuery = useClub(clubId);
  const [formation, setFormation] = useState("3-4-3");
  const [starters, setStarters] = useState<string[]>(Array(11).fill(""));
  const [bench, setBench] = useState<string[]>([]);
  const [benchCandidate, setBenchCandidate] = useState("");
  const [saving, setSaving] = useState(false);
  const initializedClubRef = useRef<string | null>(null);
  const rosterQuery = useQuery({
    queryKey: ["lineup-editor", clubId],
    queryFn: async () => {
      const clubDetail = (await api.get("/owner/clubs/" + encodeURIComponent(String(clubId)))).data;
      return mapClubDetailToRoster(clubDetail);
    },
    enabled: Boolean(clubId),
    retry: 2,
  });
  const effectiveRoster = useMemo(
    () =>
      rosterQuery.data ||
      (cachedClubQuery.data ? mapClubDetailToRoster(cachedClubQuery.data) : null),
    [rosterQuery.data, cachedClubQuery.data],
  );
  const players: LineupPlayer[] = effectiveRoster?.squad || [];
  const firstTeam = players.filter((player) => lineupSheet(player) === "first_team");
  const reserve = players.filter((player) => lineupSheet(player) === "reserve");
  const benchPool = reserve.length
    ? reserve
    : players.filter((player) => lineupSheet(player) === "first_team");
  const roles = useMemo(() => lineupRoleLabels(formation), [formation]);
  const selectedStarters = useMemo(() => new Set(starters.filter(Boolean)), [starters]);
  const selectedBench = useMemo(() => new Set(bench), [bench]);
  const availableForBench = benchPool.filter(
    (player) => !selectedStarters.has(player.player_id) && !selectedBench.has(player.player_id),
  );

  useEffect(() => {
    if (!effectiveRoster || initializedClubRef.current === clubId) return;
    initializedClubRef.current = clubId || null;
    const filedIds = effectiveRoster.filedIds || [];
    const managerFormations: string[] = Array.isArray(effectiveRoster.tactics?.formations)
      ? effectiveRoster.tactics.formations
      : [];
    const rawFormation =
      effectiveRoster.filedFormation || effectiveRoster.tactics?.formation || "3-4-3";
    const resolvedFormation =
      managerFormations.length > 0 && !managerFormations.includes(rawFormation)
        ? managerFormations[0]
        : rawFormation;
    setFormation(resolvedFormation);
    const slotOnePlayer = firstTeam.find((p) => p.player_id === filedIds[1]);
    const needsPositionRepair =
      filedIds.length < 11 ||
      (slotOnePlayer && playerPositionLine(slotOnePlayer.position) === "FWD");
    if (needsPositionRepair && firstTeam.length > 0) {
      setStarters(slotPlayersForShape(resolvedFormation, firstTeam, filedIds));
    } else {
      setStarters([...filedIds.slice(0, 11), ...Array(11).fill("")].slice(0, 11));
    }
    setBench(effectiveRoster.filedBench || []);
  }, [clubId, effectiveRoster, firstTeam]);

  const applyFormationChange = (nextShape: string) => {
    setFormation(nextShape);
    if (firstTeam.length > 0) {
      setStarters((current) => slotPlayersForShape(nextShape, firstTeam, current.filter(Boolean)));
    }
  };

  const setStarter = (index: number, playerId: string) => {
    setStarters((current) =>
      current.map((currentId, slot) => (slot === index ? playerId : currentId)),
    );
    if (playerId) setBench((current) => current.filter((id) => id !== playerId));
  };

  const autoFillLineup = async () => {
    if (!clubId) return;
    const fallbackBestXi = () => {
      const next = slotPlayersForShape(formation, firstTeam);
      setStarters(next);
      const selected = new Set(next.filter(Boolean));
      setBench((current) => current.filter((id) => !selected.has(id)));
      toast.success("Best available XI selected by position and rating.");
    };
    try {
      const { data } = await api.get(
        "/owner/clubs/" + encodeURIComponent(clubId) + "/matchday-selection",
      );
      const ids = (data?.starting_xi_ids || []).map((id: any) => String(id)).filter(Boolean);
      if (ids.length === 0) {
        fallbackBestXi();
        return;
      }
      const benchIds = (data?.bench_ids || []).map((id: any) => String(id));
      if (data?.formation) setFormation(String(data.formation));
      setStarters([...ids.slice(0, 11), ...Array(11).fill("")].slice(0, 11));
      setBench(benchIds);
      toast.success(
        data?.verdict_reason ||
          `${data?.selected_by_manager_name || "The manager"} filed this eleven.`,
      );
    } catch {
      fallbackBestXi();
    }
  };

  const saveLineup = async () => {
    if (!clubId) return;
    const payload = buildLineupPayload(
      formation,
      starters,
      bench,
      players.map((player) => player.player_id),
    );
    if (payload.starter_player_ids.length !== new Set(payload.starter_player_ids).size) {
      toast.error("Each player can only occupy one starting position.");
      return;
    }
    setSaving(true);
    try {
      const filed = (
        await api.post("/owner/clubs/" + encodeURIComponent(clubId) + "/lineup-preference", {
          preferred_formation: formation,
          preferred_player_ids: payload.starter_player_ids,
          preferred_bench_ids: payload.bench_player_ids,
          note: "Owner lineup request from the first-team sheet",
        })
      ).data;
      const filedIds = filed?.manager_selection?.starting_xi_ids || payload.starter_player_ids;
      const filedBench = filed?.manager_selection?.bench_ids || payload.bench_player_ids;
      setStarters([...filedIds.slice(0, 11), ...Array(11).fill("")].slice(0, 11));
      setBench(filedBench);
      queryClient.setQueryData(["lineup-editor", clubId], (current: any) => ({
        ...(current || {}),
        filedIds,
        filedBench,
        filedFormation: formation,
      }));
      queryClient.setQueryData(["lineup-squad", clubId], (current: any) => {
        if (!current || Array.isArray(current)) return current;
        return { ...current, ownerBook: true, filedIds, filedBench, filedFormation: formation };
      });
      const verdict = filed?.manager_selection?.verdict_reason;
      toast.success(verdict || "The first-team manager filed this eleven.");
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setSaving(false);
    }
  };

  if (!clubId) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Squad room"
          title="Lineup & Tactics"
          sub="Choose a club before building your starting XI."
        />
        <Panel title="No active club">
          <p className="text-sm text-slate-400">
            The lineup editor needs an owned club and its authoritative player roster.
          </p>
          <Link
            to="/app/clubs"
            className="gx-btn gx-btn-primary mt-4 inline-flex"
            data-testid="lineup-choose-club"
          >
            Choose a club <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Panel>
      </div>
    );
  }

  if (rosterQuery.isLoading && !effectiveRoster)
    return <Loading label="Loading lineup and squad" />;

  if (rosterQuery.isError && !effectiveRoster) {
    const message = rosterQuery.error
      ? errMsg(rosterQuery.error)
      : "The filed eleven could not be loaded.";
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Squad room"
          title="Lineup & Tactics"
          sub="The editor reads and saves the club's real lineup."
        />
        <Panel title="Lineup temporarily unavailable">
          <p className="text-sm text-slate-400">{message}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Btn
              variant="secondary"
              onClick={() => {
                void rosterQuery.refetch();
              }}
            >
              Retry
            </Btn>
            <Link to="/app/squad" className="gx-btn gx-btn-ghost inline-flex items-center">
              <ArrowLeft className="mr-2 h-4 w-4" /> Back to Squad room
            </Link>
          </div>
        </Panel>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="lineup-page">
      <PageHeader
        eyebrow="First-team sheet · matchday eleven"
        title="Lineup & Tactics (Owner Preference)"
        sub={
          (club?.club_name || "Your club") +
          " · the match plays the eleven filed from this first-team sheet. The bench comes from the reserve sheet."
        }
        action={
          <Link
            to="/app/squad"
            className="gx-btn gx-btn-ghost inline-flex items-center"
            data-testid="lineup-back-to-squad"
          >
            <ArrowLeft className="mr-2 h-4 w-4" /> Squad room
          </Link>
        }
      />
      <div
        data-testid="lineup-non-binding-preference-banner"
        className="rounded-xl border border-amber-400/35 bg-amber-500/10 p-4 text-xs text-amber-100"
      >
        <p className="font-black uppercase tracking-wider text-amber-300">
          The match plays the eleven on the first-team sheet
        </p>
        <p className="mt-1 leading-relaxed text-slate-200">
          Saving files that eleven with the first-team manager. Players on the academy sheet stay
          out of it. A youth player comes in when you move him onto the first team, or when the
          manager has already agreed minutes in the{" "}
          <Link to="/app/inbox" className="underline text-emerald-300">
            Owner Inbox
          </Link>
          .
        </p>
      </div>
      <Panel
        title="Formation & starting XI"
        eyebrow="Match plan"
        testid="lineup-editor-panel"
        className="lg:col-span-12"
      >
        <div className="grid gap-6 xl:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
          <div className="space-y-4">
            <label className="block text-sm font-medium text-slate-300" htmlFor="lineup-formation">
              Formation
            </label>
            <select
              id="lineup-formation"
              data-testid="lineup-formation-select"
              className="gx-input w-full"
              value={formation}
              onChange={(event) => applyFormationChange(event.target.value)}
            >
              {LINEUP_FORMATIONS.map((option) => (
                <option key={option} value={option}>
                  {option === "4-1-2-1-2"
                    ? "4-1-2-1-2 (Diamond 4-4-2)"
                    : option === "4-4-2" && effectiveRoster?.tactics?.fallback_formation === "4-4-2"
                      ? "4-4-2 (Fallback)"
                      : option}
                </option>
              ))}
            </select>
            {Array.isArray(effectiveRoster?.tactics?.formations) &&
            effectiveRoster.tactics.formations.length > 0 ? (
              <div
                className="flex flex-wrap items-center gap-1.5"
                data-testid="manager-preferred-formations"
              >
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Manager shapes:
                </span>
                {effectiveRoster.tactics.formations.map((shape: string) => (
                  <button
                    key={shape}
                    type="button"
                    onClick={() => applyFormationChange(shape)}
                    className={`rounded-full border px-2.5 py-0.5 text-[10px] font-bold transition ${
                      formation === shape
                        ? "border-emerald-400 bg-emerald-500/20 text-emerald-200"
                        : "border-white/10 bg-slate-900/60 text-slate-300 hover:border-emerald-400/50 hover:text-white"
                    }`}
                  >
                    {shape === "4-1-2-1-2"
                      ? "4-1-2-1-2 Diamond"
                      : shape === "4-4-2" &&
                          effectiveRoster?.tactics?.fallback_formation === "4-4-2"
                        ? "4-4-2 (Fallback)"
                        : shape}
                  </button>
                ))}
              </div>
            ) : null}
            <div className="rounded-xl border border-gtex-emerald/30 bg-gradient-to-b from-gtex-slate to-gtex-midnight p-5 shadow-xl">
              <div className="mb-3 flex items-center justify-between gap-3">
                <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-200">
                  Tactical pitch
                </span>
                <Chip tone="emerald">{formation}</Chip>
              </div>
              <div className="relative overflow-hidden rounded-xl border border-gtex-emerald/40 bg-emerald-950/60 px-4 py-5 shadow-inner">
                <div className="pointer-events-none absolute inset-2 border border-white/15" />
                <div className="pointer-events-none absolute left-1/2 top-2 bottom-2 w-px bg-white/15" />
                <div className="pointer-events-none absolute left-1/2 top-1/2 h-16 w-16 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/15" />
                <div className="relative flex flex-col items-center gap-2">
                  {lineupFormationRows(formation).map((row, lineIndex) => (
                    <div key={lineIndex} className="flex w-full flex-wrap justify-center gap-2">
                      {row.map((slotIndex) => {
                        const role = roles[slotIndex] || "Player";
                        const player = players.find(
                          (item) => item.player_id === starters[slotIndex],
                        );
                        return (
                          <div
                            key={slotIndex}
                            className="flex min-w-0 max-w-[31%] flex-1 flex-col items-center rounded-xl border border-white/20 bg-gtex-midnight/90 px-2.5 py-2 text-center shadow-md"
                          >
                            <div className="relative mb-1 flex items-center justify-center">
                              {player?.portrait_url ? (
                                <img
                                  src={player.portrait_url}
                                  alt={player.player_name}
                                  className="h-10 w-10 rounded-full border-2 border-emerald-400/70 bg-slate-900 object-cover shadow-md"
                                />
                              ) : (
                                <KitBakedMark size={28} />
                              )}
                              <span className="absolute -bottom-1 -right-2 rounded-full border border-emerald-400/60 bg-slate-950 px-1.5 py-0.2 text-[9px] font-black text-emerald-200 shadow">
                                {player
                                  ? player.rating
                                    ? Math.round(player.rating)
                                    : "XI"
                                  : slotIndex + 1}
                              </span>
                            </div>
                            <span className="mt-0.5 w-full truncate text-[10px] font-semibold text-white">
                              {player?.player_name || role}
                            </span>
                            <span className="w-full truncate text-[9px] text-slate-400">
                              {player?.position
                                ? `${role} · ${player.position.split("/")[0].trim()}`
                                : role}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                <span>{starters.filter(Boolean).length} of 11 starting positions filled</span>
                <span>{firstTeam.length} on the first-team sheet</span>
              </div>
            </div>
            <div className="flex items-start gap-2 rounded-xl border border-gtex-graphite bg-gtex-slate/80 p-4 text-xs leading-5 text-slate-300">
              <CircleHelp className="mt-0.5 h-4 w-4 shrink-0 text-cyan-300" />
              Formation sets the shape. Choose a player for each position; the same player cannot be
              used twice. At least eleven eligible players, including a goalkeeper, are needed for
              competition registration.
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <h3 className="gx-h3">Starting XI</h3>
              <Chip tone={starters.filter(Boolean).length === 11 ? "emerald" : "gold"}>
                {starters.filter(Boolean).length}/11 selected
              </Chip>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {roles.map((role, index) => {
                const currentId = starters[index] || "";
                const usedByOtherSlots = new Set(
                  starters.filter((id, slot) => slot !== index && Boolean(id)),
                );
                const options = firstTeam.filter(
                  (player) => !usedByOtherSlots.has(player.player_id),
                );
                return (
                  <div key={index} className="min-w-0 rounded-sm border border-white/10 p-3">
                    <label
                      htmlFor={"lineup-slot-" + index}
                      className="mb-2 block text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500"
                    >
                      {String(index + 1).padStart(2, "0")} · {role}
                    </label>
                    <select
                      id={"lineup-slot-" + index}
                      data-testid={"lineup-slot-" + index}
                      aria-label={"Starting position " + (index + 1) + " " + role}
                      className="gx-input w-full"
                      value={currentId}
                      onChange={(event) => setStarter(index, event.target.value)}
                    >
                      <option value="">Select player</option>
                      {options.map((player) => (
                        <option key={player.player_id} value={player.player_id}>
                          {player.player_name}
                          {player.position ? " · " + player.position : ""}
                          {player.mood_state ? ` · ${player.mood_state}` : ""}
                          {typeof player.performance_shift === "number" &&
                          player.performance_shift !== 0
                            ? ` (${player.performance_shift > 0 ? "+" : ""}${player.performance_shift} OVR)`
                            : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                );
              })}
            </div>
            <div className="flex flex-wrap items-center gap-2 pt-2">
              <Btn
                variant="secondary"
                onClick={autoFillLineup}
                disabled={players.length === 0}
                data-testid="auto-fill-lineup-button"
              >
                <Users className="mr-2 h-4 w-4" /> Use the manager's XI
              </Btn>
              <Btn
                onClick={saveLineup}
                disabled={saving || players.length === 0}
                data-testid="save-lineup-button"
              >
                <Save className="mr-2 h-4 w-4" /> {saving ? "Saving lineup…" : "Save lineup"}
              </Btn>
              <span className="text-xs text-slate-500">
                Saved lineups are persisted through GTEX's club-lineup API.
              </span>
            </div>
          </div>
        </div>
      </Panel>

      <Panel
        title="Manager & coaching staff"
        eyebrow="Tactical support"
        testid="lineup-manager-panel"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div
            className="max-w-2xl text-sm leading-6 text-slate-300"
            data-testid="lineup-manager-tactics"
          >
            <p className="font-semibold text-white">
              {rosterQuery.data?.tactics?.manager_name || "No manager appointed"}
              {rosterQuery.data?.tactics?.formation
                ? ` · ${rosterQuery.data.tactics.formation}`
                : ""}
              {rosterQuery.data?.tactics?.style ? ` · ${rosterQuery.data.tactics.style}` : ""}
            </p>
            {Array.isArray(rosterQuery.data?.tactics?.formations) &&
            rosterQuery.data.tactics.formations.length > 1 ? (
              <p className="text-xs text-emerald-300">
                Tactics plan: {rosterQuery.data.tactics.formations.join(" · ")}
                {rosterQuery.data?.tactics?.pressing
                  ? ` · ${String(rosterQuery.data.tactics.pressing).replace(/_/g, " ")}`
                  : ""}
              </p>
            ) : null}
            <p className="text-slate-400">
              {rosterQuery.data?.tactics?.tactical_flexibility != null
                ? `Tactical flexibility & influence ${rosterQuery.data.tactics.tactical_flexibility}. `
                : ""}
              {rosterQuery.data?.tactics?.youth_development != null
                ? `Youth rating ${rosterQuery.data.tactics.youth_development}. `
                : ""}
              {rosterQuery.data?.tactics?.tactical_match_bonus != null
                ? `That adds +${rosterQuery.data.tactics.tactical_match_bonus} to the match. `
                : ""}
              The match plays this manager's shape unless their flexibility covers another one.
              Saving asks them to accept the eleven.
            </p>
          </div>
          <Link
            to="/app/squad"
            className="gx-btn gx-btn-secondary inline-flex shrink-0 items-center"
            data-testid="lineup-manage-manager-link"
          >
            Manage manager <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </div>
      </Panel>

      <Panel title="Substitutes & bench" eyebrow="Matchday options" testid="lineup-bench-panel">
        {availableForBench.length === 0 && bench.length === 0 ? (
          <Empty
            title="No bench options available"
            body="Select fewer starters or add eligible players to this club before preparing substitutes."
            testid="lineup-bench-empty"
          />
        ) : (
          <>
            <p className="mb-4 text-sm text-slate-400">
              The bench is the reserve sheet. Players already in the eleven cannot also sit there.
            </p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <select
                aria-label="Choose a substitute"
                data-testid="lineup-bench-candidate"
                className="gx-input min-w-0 flex-1"
                value={benchCandidate}
                onChange={(event) => setBenchCandidate(event.target.value)}
              >
                <option value="">Choose a substitute</option>
                {availableForBench.map((player) => (
                  <option key={player.player_id} value={player.player_id}>
                    {player.player_name}
                    {player.position ? " · " + player.position : ""}
                  </option>
                ))}
              </select>
              <Btn
                variant="secondary"
                disabled={!benchCandidate}
                onClick={() => {
                  if (
                    benchCandidate &&
                    !selectedStarters.has(benchCandidate) &&
                    !selectedBench.has(benchCandidate)
                  )
                    setBench((current) => [...current, benchCandidate]);
                  setBenchCandidate("");
                }}
                data-testid="add-bench-player"
              >
                <Users className="mr-2 h-4 w-4" /> Add to bench
              </Btn>
            </div>
            {bench.length > 0 && (
              <div
                className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3"
                data-testid="lineup-bench-list"
              >
                {bench.map((id) => {
                  const player = players.find((item) => item.player_id === id);
                  return (
                    <div
                      key={id}
                      className="flex min-w-0 items-center justify-between gap-3 rounded-sm border border-white/10 p-3"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-white">
                          {player?.player_name || "Unknown player"}
                        </p>
                        <p className="text-xs text-slate-500">
                          {player?.position || "Squad player"}
                          {player?.rating ? " · OVR " + Math.round(player.rating) : ""}
                        </p>
                      </div>
                      <Btn
                        variant="ghost"
                        className="shrink-0"
                        onClick={() => setBench((current) => current.filter((item) => item !== id))}
                        aria-label={"Remove " + (player?.player_name || "player") + " from bench"}
                      >
                        Remove
                      </Btn>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </Panel>

      <Panel
        title="Official Matchday Broadcast Team Sheet"
        eyebrow="Live TV & Editorial Preview"
        testid="lineup-broadcast-preview-panel"
      >
        <MatchdayLineupBroadcast
          homeClubId={clubId}
          homeClubName={club?.club_name || "Your Club"}
          editableClubId={clubId}
          formationOverride={formation}
          onFormationChange={setFormation}
          defaultView="tunnel"
        />
      </Panel>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-sm border border-white/10 p-4">
        <div className="flex items-start gap-2 text-sm text-slate-400">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
          <span>
            The saved tactical lineup is separate from competition registration. Sync, submit, and
            lock the registered squad on the Squad room page.
          </span>
        </div>
        <Link
          to="/app/squad"
          className="gx-btn gx-btn-secondary inline-flex items-center"
          data-testid="lineup-registration-link"
        >
          Squad registration <ArrowRight className="ml-2 h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}
