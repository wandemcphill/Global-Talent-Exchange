import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, CircleHelp, Save, ShieldCheck, Users } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { useActiveClub } from "@/lib/owner";
import { Btn, Chip, Empty, Loading, PageHeader, Panel } from "@/components/gtex/ui";
import {
  buildLineupPayload,
  LINEUP_FORMATIONS,
  lineupRoleLabels,
  lineupFormationRows,
  normalizeLineupPlan,
  normalizeLineupSquad,
  type LineupPlayer,
} from "./lineupModel";

export default function Lineup() {
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const { clubs, active } = useActiveClub();
  const clubId = searchParams.get("club_id") || active?.club_id || undefined;
  const club = clubs.find((item: any) => item.club_id === clubId) || active;
  const [formation, setFormation] = useState("4-3-3");
  const [starters, setStarters] = useState<string[]>(Array(11).fill(""));
  const [bench, setBench] = useState<string[]>([]);
  const [benchCandidate, setBenchCandidate] = useState("");
  const [saving, setSaving] = useState(false);
  const initializedClubRef = useRef<string | null>(null);
  const rosterQuery = useQuery({
    queryKey: ["lineup-squad", clubId],
    queryFn: async () =>
      normalizeLineupSquad((await api.get("/market/clubs/" + encodeURIComponent(String(clubId)) + "/players")).data),
    enabled: Boolean(clubId),
  });
  const planQuery = useQuery({
    queryKey: ["lineup-plan", clubId],
    queryFn: async () =>
      normalizeLineupPlan((await api.get("/clubs/" + encodeURIComponent(String(clubId)) + "/lineup")).data),
    enabled: Boolean(clubId),
  });
  const players: LineupPlayer[] = rosterQuery.data || [];
  const roles = useMemo(() => lineupRoleLabels(formation), [formation]);
  const selectedStarters = useMemo(() => new Set(starters.filter(Boolean)), [starters]);
  const selectedBench = useMemo(() => new Set(bench), [bench]);
  const availableForBench = players.filter(
    (player) => !selectedStarters.has(player.player_id) && !selectedBench.has(player.player_id),
  );

  useEffect(() => {
    if (!planQuery.data || initializedClubRef.current === clubId) return;
    initializedClubRef.current = clubId || null;
    setFormation(planQuery.data.formation);
    setStarters([...planQuery.data.starter_player_ids.slice(0, 11), ...Array(11).fill("")].slice(0, 11));
    setBench(planQuery.data.bench_player_ids);
  }, [clubId, planQuery.data]);

  const setStarter = (index: number, playerId: string) => {
    setStarters((current) => current.map((currentId, slot) => slot === index ? playerId : currentId));
    if (playerId) setBench((current) => current.filter((id) => id !== playerId));
  };

  const autoFillLineup = () => {
    const isKeeper = (player: LineupPlayer) =>
      /(^|[^a-z])(gk|goalkeeper|keeper)([^a-z]|$)/i.test(player.position || "");
    const keepers = players
      .filter(isKeeper)
      .sort((a, b) => Number(b.rating || 0) - Number(a.rating || 0));
    const goalkeeper = keepers[0];
    const outfield = players
      .filter((player) => !isKeeper(player))
      .sort((a, b) => Number(b.rating || 0) - Number(a.rating || 0));
    const next = [
      goalkeeper?.player_id || "",
      ...outfield.slice(0, 10).map((player) => player.player_id),
    ];
    setStarters([...next, ...Array(11).fill("")].slice(0, 11));
    const selected = new Set(next.filter(Boolean));
    setBench((current) => current.filter((id) => !selected.has(id)));
    if (!goalkeeper) {
      toast.warning("No goalkeeper was identified in this roster. Select the goalkeeper position manually.");
    } else {
      toast.success("Best available XI selected by rating, with a goalkeeper in goal.");
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
      const saved = (await api.put("/clubs/" + encodeURIComponent(clubId) + "/lineup", payload)).data;
      queryClient.setQueryData(["lineup-plan", clubId], normalizeLineupPlan(saved));
      toast.success("Lineup saved.");
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setSaving(false);
    }
  };

  if (!clubId) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Squad room" title="Lineup & Tactics" sub="Choose a club before building your starting XI." />
        <Panel title="No active club">
          <p className="text-sm text-slate-400">The lineup editor needs an owned club and its authoritative player roster.</p>
          <Link to="/app/clubs" className="gx-btn gx-btn-primary mt-4 inline-flex" data-testid="lineup-choose-club">
            Choose a club <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Panel>
      </div>
    );
  }

  if (rosterQuery.isLoading || planQuery.isLoading) return <Loading label="Loading lineup and squad" />;

  if (rosterQuery.isError || planQuery.isError) {
    const message = rosterQuery.error ? errMsg(rosterQuery.error) : errMsg(planQuery.error);
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Squad room" title="Lineup & Tactics" sub="The editor reads and saves the club's real lineup." />
        <Panel title="Lineup temporarily unavailable">
          <p className="text-sm text-slate-400">{message}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Btn variant="secondary" onClick={() => { void rosterQuery.refetch(); void planQuery.refetch(); }}>Retry</Btn>
            <Link to="/app/squad" className="gx-btn gx-btn-ghost inline-flex items-center"><ArrowLeft className="mr-2 h-4 w-4" /> Back to Squad room</Link>
          </div>
        </Panel>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="lineup-page">
      <PageHeader
        eyebrow="Tactics & roster"
        title="Lineup & Tactics"
        sub={(club?.club_name || "Your club") + " · choose a formation, assign starters, manage the bench, and save to the match engine."}
        action={
          <Link to="/app/squad" className="gx-btn gx-btn-ghost inline-flex items-center" data-testid="lineup-back-to-squad">
            <ArrowLeft className="mr-2 h-4 w-4" /> Squad room
          </Link>
        }
      />
      <Panel title="Formation & starting XI" eyebrow="Match plan" testid="lineup-editor-panel" className="lg:col-span-12">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
          <div className="space-y-4">
            <label className="block text-sm font-medium text-slate-300" htmlFor="lineup-formation">Formation</label>
            <select id="lineup-formation" data-testid="lineup-formation-select" className="gx-input w-full" value={formation} onChange={(event) => setFormation(event.target.value)}>
              {LINEUP_FORMATIONS.map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
            <div className="rounded-sm border border-emerald-400/20 bg-gradient-to-b from-emerald-950/80 to-slate-950 p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-200">Tactical pitch</span>
                <Chip tone="emerald">{formation}</Chip>
              </div>
              <div className="relative overflow-hidden rounded-sm border border-white/20 bg-emerald-900/50 px-3 py-4">
                <div className="pointer-events-none absolute inset-2 border border-white/15" />
                <div className="pointer-events-none absolute left-1/2 top-2 bottom-2 w-px bg-white/15" />
                <div className="pointer-events-none absolute left-1/2 top-1/2 h-16 w-16 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/15" />
                <div className="relative flex flex-col items-center gap-2">
                  {lineupFormationRows(formation).map((row, lineIndex) => (
                    <div key={lineIndex} className="flex w-full flex-wrap justify-center gap-2">
                      {row.map((slotIndex) => {
                        const role = roles[slotIndex] || "Player";
                        const player = players.find((item) => item.player_id === starters[slotIndex]);
                        return (
                          <div key={slotIndex} className="flex min-w-0 max-w-[31%] flex-1 flex-col items-center rounded-sm border border-white/15 bg-slate-950/80 px-2 py-2 text-center">
                            <span className="mb-1 flex h-7 w-7 items-center justify-center rounded-full border border-emerald-300/40 bg-emerald-400/10 text-[10px] font-bold text-emerald-100">{player ? (player.rating ? Math.round(player.rating) : "XI") : slotIndex + 1}</span>
                            <span className="w-full truncate text-[10px] font-semibold text-white">{player?.player_name || role}</span>
                            <span className="w-full truncate text-[9px] text-slate-400">{role}</span>
                          </div>
                        );
                      })}
                    </div>
                  ))}

                </div>
              </div>
              <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                <span>{starters.filter(Boolean).length} of 11 starting positions filled</span>
                <span>{players.length} players available</span>
              </div>
            </div>
            <div className="flex items-start gap-2 rounded-sm border border-white/10 p-3 text-xs leading-5 text-slate-400">
              <CircleHelp className="mt-0.5 h-4 w-4 shrink-0 text-cyan-300" />
              Formation sets the shape. Choose a player for each position; the same player cannot be used twice. At least eleven eligible players, including a goalkeeper, are needed for competition registration.
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <h3 className="gx-h3">Starting XI</h3>
              <Chip tone={starters.filter(Boolean).length === 11 ? "emerald" : "gold"}>{starters.filter(Boolean).length}/11 selected</Chip>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {roles.map((role, index) => {
                const currentId = starters[index] || "";
                const usedByOtherSlots = new Set(starters.filter((id, slot) => slot !== index && Boolean(id)));
                const options = players.filter((player) => !usedByOtherSlots.has(player.player_id));
                return (
                  <div key={index} className="min-w-0 rounded-sm border border-white/10 p-3">
                    <label htmlFor={"lineup-slot-" + index} className="mb-2 block text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">
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
                          {player.player_name}{player.position ? " · " + player.position : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                );
              })}
            </div>
            <div className="flex flex-wrap items-center gap-2 pt-2">
              <Btn variant="secondary" onClick={autoFillLineup} disabled={players.length === 0} data-testid="auto-fill-lineup-button">
                <Users className="mr-2 h-4 w-4" /> Auto-fill XI
              </Btn>
              <Btn onClick={saveLineup} disabled={saving || players.length === 0} data-testid="save-lineup-button">
                <Save className="mr-2 h-4 w-4" /> {saving ? "Saving lineup…" : "Save lineup"}
              </Btn>
              <span className="text-xs text-slate-500">Saved lineups are persisted through GTEX's club-lineup API.</span>
            </div>
          </div>
        </div>
      </Panel>

      <Panel title="Manager & coaching staff" eyebrow="Tactical support" testid="lineup-manager-panel">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-2xl text-sm leading-6 text-slate-400">
            Choose a manager whose tactical style fits the selected formation. React's manager hiring and management actions are available from the Squad room.
          </p>
          <Link to="/app/squad" className="gx-btn gx-btn-secondary inline-flex shrink-0 items-center" data-testid="lineup-manage-manager-link">
            Manage manager <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </div>
      </Panel>

      <Panel title="Substitutes & bench" eyebrow="Matchday options" testid="lineup-bench-panel">
        {availableForBench.length === 0 && bench.length === 0 ? (
          <Empty title="No bench options available" body="Select fewer starters or add eligible players to this club before preparing substitutes." testid="lineup-bench-empty" />
        ) : (
          <>
            <p className="mb-4 text-sm text-slate-400">Choose reserve players from this club's roster. Players already assigned to the starting XI cannot also occupy the bench.</p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <select aria-label="Choose a substitute" data-testid="lineup-bench-candidate" className="gx-input min-w-0 flex-1" value={benchCandidate} onChange={(event) => setBenchCandidate(event.target.value)}>
                <option value="">Choose a substitute</option>
                {availableForBench.map((player) => <option key={player.player_id} value={player.player_id}>{player.player_name}{player.position ? " · " + player.position : ""}</option>)}
              </select>
              <Btn variant="secondary" disabled={!benchCandidate} onClick={() => { if (benchCandidate && !selectedStarters.has(benchCandidate) && !selectedBench.has(benchCandidate)) setBench((current) => [...current, benchCandidate]); setBenchCandidate(""); }} data-testid="add-bench-player">
                <Users className="mr-2 h-4 w-4" /> Add to bench
              </Btn>
            </div>
            {bench.length > 0 && (
              <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3" data-testid="lineup-bench-list">
                {bench.map((id) => {
                  const player = players.find((item) => item.player_id === id);
                  return (
                    <div key={id} className="flex min-w-0 items-center justify-between gap-3 rounded-sm border border-white/10 p-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-white">{player?.player_name || "Unknown player"}</p>
                        <p className="text-xs text-slate-500">{player?.position || "Squad player"}{player?.rating ? " · OVR " + Math.round(player.rating) : ""}</p>
                      </div>
                      <Btn variant="ghost" className="shrink-0" onClick={() => setBench((current) => current.filter((item) => item !== id))} aria-label={"Remove " + (player?.player_name || "player") + " from bench"}>Remove</Btn>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </Panel>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-sm border border-white/10 p-4">
        <div className="flex items-start gap-2 text-sm text-slate-400">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
          <span>The saved tactical lineup is separate from competition registration. Sync, submit, and lock the registered squad on the Squad room page.</span>
        </div>
        <Link to="/app/squad" className="gx-btn gx-btn-secondary inline-flex items-center" data-testid="lineup-registration-link">
          Squad registration <ArrowRight className="ml-2 h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}
