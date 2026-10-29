import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Crown, Flame, Globe, Medal, Swords, Trophy, Zap } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, label, useActiveClub, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, PageHeader, Panel, Stat } from "@/components/gtex/ui";

function CompCard({ c, clubId }: any) {
  const refresh = useRefreshOwner();
  const [busy, setBusy] = useState(false);
  const entered = c.my_club_ids?.length > 0;
  const enter = async () => {
    setBusy(true);
    try {
      await api.post(`/owner/competitions/${c.id}/enter`, { club_id: clubId });
      toast.success(`Entered ${c.name}`);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div data-testid={`competition-card-${c.id}`} className="flex flex-col rounded-sm border border-white/10 bg-slate-950/40 p-5 transition-colors hover:border-emerald-500/30">
      <div className="flex flex-wrap gap-2">
        <Chip tone={c.host_type === "gtex" ? "emerald" : "cyan"}>{c.host_type === "gtex" ? "GTEX-hosted" : "User-hosted"}</Chip>
        <Chip>{c.format}</Chip>
        <Chip tone={c.status === "open" ? "gold" : c.status === "running" ? "emerald" : "slate"}>{c.status}</Chip>
        {c.allow_same_owner && <Chip tone="red">Same-owner allowed</Chip>}
      </div>
      <p className="gx-display mt-3 text-xl font-bold uppercase text-white">{c.name}</p>
      <p className="mt-1 flex-1 text-xs text-slate-400">{c.description}</p>
      <div className="mt-4 grid grid-cols-3 gap-2 text-xs">
        <div><p className="text-slate-500">Entry</p><Coin amount={c.entry_fee} /></div>
        <div><p className="text-slate-500">Pool</p><Coin amount={c.prize_pool} /></div>
        <div><p className="text-slate-500">Clubs</p><span className="gx-mono text-white">{c.entrants}/{c.max_clubs}</span></div>
      </div>
      {c.invite_code && <p className="gx-mono mt-3 text-xs text-cyan-300" data-testid={`invite-code-${c.id}`}>Invite code: {c.invite_code}</p>}
      <div className="mt-4 flex gap-2">
        <Link to={`/app/competitions/${c.id}`} className="gx-btn gx-btn-secondary flex-1" data-testid={`view-competition-${c.id}`}>View</Link>
        {c.status === "open" && !entered && <Btn className="flex-1" disabled={busy || !clubId} onClick={enter} data-testid={`enter-competition-${c.id}`}>Enter</Btn>}
      </div>
    </div>
  );
}

function HostForm() {
  const refresh = useRefreshOwner();
  const [f, setF] = useState<any>({ name: "", format: "league", entry_fee: 0, max_clubs: 4, allow_same_owner: false });
  const submit = async (e: any) => {
    e.preventDefault();
    try {
      const { data } = await api.post("/owner/competitions", { ...f, entry_fee: Number(f.entry_fee), max_clubs: Number(f.max_clubs) });
      toast.success(`Hosted. Share invite code ${data.invite_code} with friends.`);
      refresh();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };
  return (
    <form onSubmit={submit} className="grid gap-3 md:grid-cols-6" data-testid="host-competition-form">
      <input required minLength={3} data-testid="host-name-input" className="gx-input md:col-span-2" placeholder="Friday Night Derby Cup" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
      <select data-testid="host-format-select" className="gx-input" value={f.format} onChange={(e) => setF({ ...f, format: e.target.value })}><option value="league">League</option><option value="knockout">Knockout</option></select>
      <input data-testid="host-fee-input" className="gx-input" type="number" min={0} placeholder="Entry fee" value={f.entry_fee} onChange={(e) => setF({ ...f, entry_fee: e.target.value })} />
      <select data-testid="host-size-select" className="gx-input" value={f.max_clubs} onChange={(e) => setF({ ...f, max_clubs: e.target.value })}>{[2, 4, 6, 8].map((n) => <option key={n} value={n}>{n} clubs</option>)}</select>
      <Btn type="submit" data-testid="host-submit-button">Host</Btn>
      <label className="flex items-center gap-2 text-xs text-slate-400 md:col-span-6">
        <input type="checkbox" data-testid="host-same-owner-checkbox" checked={f.allow_same_owner} onChange={(e) => setF({ ...f, allow_same_owner: e.target.checked })} />
        Allow clubs under common ownership (the competition will be publicly labelled "Same-owner allowed"). Platform fee on entry fees: 10%.
      </label>
    </form>
  );
}

function JoinCode({ clubId }: any) {
  const refresh = useRefreshOwner();
  const [code, setCode] = useState("");
  const join = async () => {
    try {
      await api.post("/owner/competitions/join-by-code", { code, club_id: clubId });
      toast.success("Joined friend competition");
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <div className="flex gap-2">
      <input data-testid="join-code-input" className="gx-input uppercase" placeholder="Invite code" value={code} onChange={(e) => setCode(e.target.value)} />
      <Btn variant="secondary" disabled={code.length < 4} onClick={join} data-testid="join-code-button">Join</Btn>
    </div>
  );
}

function QuickMatchmakingDesk({ activeClub }: { activeClub: any }) {
  const { user } = useAuth();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [style, setStyle] = useState<"possession" | "counter" | "balanced" | "direct">("balanced");
  const [matchStyle, setMatchStyle] = useState<"balanced" | "tactical_clash">("balanced");
  const [busy, setBusy] = useState(false);
  const [lastMatch, setLastMatch] = useState<any | null>(null);

  const { data: entitlement } = useQuery({
    queryKey: ["fast-match-entitlement"],
    queryFn: async () => {
      try {
        return (await api.get("/simulation-matchmaking/fast-match/entitlement")).data;
      } catch {
        return null;
      }
    },
  });

  const launchQuickGame = async () => {
    if (!user?.id || !activeClub?.club_id) {
      toast.error("Select an active club before entering matchmaking.");
      return;
    }
    setBusy(true);
    try {
      // Ensure simulation profile is registered for the active user/club
      await api.put(`/simulation-matchmaking/profiles/${user.id}`, {
        user_id: user.id,
        club_id: activeClub.club_id,
        club_name: activeClub.club_name || "GTEX FC",
        manager_rating: 1200 + Number(activeClub.prestige || 50) * 5,
        tactical_profile: {
          style,
          pressing: style === "counter" ? "medium" : "high",
          tempo: style === "possession" ? "normal" : "fast",
        },
        squad_strength: Math.min(99, Math.max(50, Number(activeClub.squad_ovr || 74))),
        squad_depth: 78,
        preferred_match_type: ["quick"],
        connection_quality: "excellent",
        region: "AF-WEST",
        availability: "online",
      });

      const { data } = await api.post("/simulation-matchmaking/quick-game", {
        mode: "quick_game",
        user_id: user.id,
        include_bots: true,
        preferences: {
          match_style: matchStyle,
          allow_tactical_clash: true,
          max_rating_delta: 150,
          max_squad_strength_delta: 15,
        },
      });
      setLastMatch(data);
      toast.success(`Matched vs ${data.opponent?.club_name || "Rival Club"} (${data.match_context?.tactical_story || "Tactical Clash"})!`);
      await qc.invalidateQueries({ queryKey: ["fast-match-entitlement"] });
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const settleQuickGame = async (matchId: string) => {
    setBusy(true);
    try {
      const { data } = await api.post(`/simulation-matchmaking/quick-game/${matchId}/settle`);
      toast.success(`Quick match settled: ${data.home_score}–${data.away_score} (${label(data.result)})`);
      setLastMatch((prev: any) => (prev ? { ...prev, settlement: data } : prev));
      await qc.invalidateQueries({ queryKey: ["fast-match-entitlement"] });
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel
      eyebrow="Canonical Simulation Matchmaking · Instant ELO Pairing"
      title="Instant Matchmaking & Tactical Clash"
      testid="simulation-matchmaking-panel"
    >
      <div className="grid gap-4 lg:grid-cols-12 items-center">
        <div className="space-y-2 lg:col-span-5">
          <p className="text-xs text-slate-300 leading-relaxed">
            Pair <b className="text-white">{activeClub?.club_name || "your club"}</b> against live owners or elite tactical bots via{" "}
            <span className="gx-mono text-emerald-300">/api/simulation-matchmaking/quick-game</span>.
          </p>
          <div className="flex flex-wrap gap-2 text-xs">
            <Chip tone="emerald">
              Free Run: {entitlement?.free_matches_remaining ?? 10}/{entitlement?.free_match_limit ?? 10} Remaining
            </Chip>
            <Chip tone="gold">Wins: {entitlement?.wins_count ?? 0}</Chip>
          </div>
        </div>

        <div className="grid gap-2 sm:grid-cols-3 lg:col-span-7">
          <select
            className="gx-input"
            value={style}
            onChange={(e) => setStyle(e.target.value as any)}
            data-testid="matchmaking-tactical-style"
          >
            <option value="balanced">Balanced Setup</option>
            <option value="possession">Possession Tiki-Taka</option>
            <option value="counter">Vertical Counter</option>
            <option value="direct">High-Tempo Direct</option>
          </select>

          <select
            className="gx-input"
            value={matchStyle}
            onChange={(e) => setMatchStyle(e.target.value as any)}
            data-testid="matchmaking-pairing-mode"
          >
            <option value="balanced">Balanced ELO Pairing</option>
            <option value="tactical_clash">Tactical Clash Priority</option>
          </select>

          <Btn onClick={launchQuickGame} disabled={busy || !activeClub?.club_id} data-testid="launch-quick-game-btn">
            <Swords size={14} />
            {busy ? "Matching…" : "Find Instant Match"}
          </Btn>
        </div>
      </div>

      {lastMatch && (
        <div
          className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 text-xs"
          data-testid="quick-game-result-banner"
        >
          <div>
            <p className="font-bold text-white text-sm">
              {activeClub?.club_name} vs. {lastMatch.opponent?.club_name} ({lastMatch.opponent?.region})
            </p>
            <p className="text-slate-300 mt-0.5">
              {lastMatch.match_context?.tactical_story} · Compatibility {lastMatch.match_context?.tactical_compatibility_score}% · Difficulty:{" "}
              <b className="uppercase text-amber-300">{lastMatch.match_context?.expected_difficulty}</b>
            </p>
            {lastMatch.settlement && (
              <p className="text-emerald-300 font-bold mt-1">
                Final Score: {lastMatch.settlement.home_score} – {lastMatch.settlement.away_score} ({label(lastMatch.settlement.result)})
              </p>
            )}
          </div>
          <div className="flex gap-2">
            {lastMatch.live_session?.session_route && (
              <Btn variant="secondary" onClick={() => navigate(`/app/matches/${lastMatch.match_id}`)}>
                Open 2D Pitch
              </Btn>
            )}
            {!lastMatch.settlement && (
              <Btn variant="gold" onClick={() => settleQuickGame(lastMatch.match_id)} disabled={busy}>
                <Zap size={13} /> Settle Match Result
              </Btn>
            )}
          </div>
        </div>
      )}
    </Panel>
  );
}

function GlobalLeaderboardPanel({ worldClubs }: { worldClubs: any[] }) {
  const [boardScope, setBoardScope] = useState<"global" | "clubs">("global");

  const { data: season } = useQuery({
    queryKey: ["leaderboard-season-current"],
    queryFn: async () => {
      try {
        return (await api.get("/v2/season/current")).data;
      } catch {
        return null;
      }
    },
  });

  const { data: globalBoard } = useQuery({
    queryKey: ["leaderboard-global"],
    queryFn: async () => {
      try {
        return (await api.get("/v2/leaderboard/global", { params: { limit: 15 } })).data;
      } catch {
        return null;
      }
    },
  });

  const entries: any[] = globalBoard?.entries || [];
  const sortedClubs = [...(worldClubs || [])]
    .sort((a, b) => Number(b.prestige || 0) - Number(a.prestige || 0) || Number(b.trophies || 0) - Number(a.trophies || 0))
    .slice(0, 10);

  return (
    <Panel
      eyebrow={`Canonical Season Rankings · ${season?.id ? `Season ${String(season.id).slice(0, 8)}` : "Active Season"}`}
      title="Global Leaderboards & Club Prestige Ranking"
      testid="global-leaderboard-panel"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
          {season && (
            <>
              <Chip tone="emerald">{label(season.status)}</Chip>
              <span>Days Remaining: <b className="text-white">{season.days_remaining}d</b></span>
              <span>Default ELO: <b className="text-white">{season.default_rating}</b></span>
            </>
          )}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setBoardScope("global")}
            className={`gx-btn ${boardScope === "global" ? "gx-btn-primary" : "gx-btn-ghost"} text-xs`}
          >
            <Globe size={13} /> ELO Ranking ({entries.length})
          </button>
          <button
            type="button"
            onClick={() => setBoardScope("clubs")}
            className={`gx-btn ${boardScope === "clubs" ? "gx-btn-primary" : "gx-btn-ghost"} text-xs`}
          >
            <Crown size={13} /> Club Prestige Table ({sortedClubs.length})
          </button>
        </div>
      </div>

      {boardScope === "global" && entries.length > 0 ? (
        <div className="gx-scroll overflow-x-auto">
          <table className="gx-table w-full min-w-[640px]">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Competitor</th>
                <th>Tier</th>
                <th>Rating</th>
                <th>W-D-L</th>
                <th>Win Rate</th>
                <th>Titles</th>
                <th>Earnings</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((row: any) => (
                <tr key={row.player_id} data-testid={`leaderboard-row-${row.player_id}`}>
                  <td className="gx-mono font-bold text-amber-300">#{row.rank}</td>
                  <td className="font-semibold text-white">{row.display_name}</td>
                  <td><Chip tone="gold">{label(row.tier)}</Chip></td>
                  <td className="gx-mono text-emerald-300">{row.rating}</td>
                  <td className="gx-mono text-xs">{row.wins}-{row.draws}-{row.losses}</td>
                  <td className="gx-mono">{Math.round(Number(row.win_rate || 0) * 100)}%</td>
                  <td className="gx-mono">{row.tournament_titles}</td>
                  <td className="gx-mono text-amber-300">{fmt(Number(row.earnings || 0))} GTX</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="gx-scroll overflow-x-auto">
          <table className="gx-table w-full min-w-[640px]">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Club</th>
                <th>Country</th>
                <th>Prestige</th>
                <th>Trophies</th>
                <th>Group</th>
              </tr>
            </thead>
            <tbody>
              {sortedClubs.map((c: any, idx: number) => (
                <tr key={c.club_id} data-testid={`club-rank-row-${c.club_id}`}>
                  <td className="gx-mono font-bold text-amber-300">#{idx + 1}</td>
                  <td className="font-semibold text-white">{c.club_name}</td>
                  <td className="text-slate-300">{c.country || "Global"}</td>
                  <td className="gx-mono text-emerald-300">{c.prestige ?? 60}</td>
                  <td className="gx-mono text-amber-300">{c.trophies ?? 0}</td>
                  <td>{c.multi_club_group ? <Chip tone="cyan">Multi-Club Group</Chip> : <span className="text-xs text-slate-500">Independent</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

export default function Competitions() {
  const { active } = useActiveClub();
  const { data, isLoading } = useQuery({ queryKey: ["competitions"], queryFn: async () => (await api.get("/owner/competitions")).data.competitions });
  const { data: worldClubs = [] } = useQuery({
    queryKey: ["world-clubs"],
    queryFn: async () => {
      try {
        return (await api.get("/owner/world/clubs")).data.clubs || [];
      } catch {
        return [];
      }
    },
  });

  const gtex = (data || []).filter((c: any) => c.host_type === "gtex");
  const user = (data || []).filter((c: any) => c.host_type === "user");
  return (
    <div data-testid="competitions-page" className="space-y-6">
      <PageHeader eyebrow="Competitions" title="Where prestige is earned" sub={`Entering as ${active?.club_name || "-"}. Same-owner clubs can't share a prize-sensitive bracket and are routed apart in knockouts.`} />
      {isLoading ? <Loading /> : (
        <>
          <QuickMatchmakingDesk activeClub={active} />
          <Panel eyebrow="GTEX-hosted" title="Platform competitions" testid="gtex-competitions-panel">
            <div className="grid gap-4 md:grid-cols-3">{gtex.map((c: any) => <CompCard key={c.id} c={c} clubId={active?.club_id} />)}</div>
          </Panel>
          <div className="grid gap-6 lg:grid-cols-12">
            <Panel eyebrow="User-hosted" title="Host a friend competition" className="lg:col-span-8" testid="host-panel"><HostForm /></Panel>
            <Panel eyebrow="Invite" title="Join with a code" className="lg:col-span-4" testid="join-panel"><JoinCode clubId={active?.club_id} /></Panel>
          </div>
          <Panel eyebrow="Friends & hosted" title="Your user-hosted competitions" testid="user-competitions-panel">
            {user.length === 0 ? <Empty title="None yet" body="Host one above or join with an invite code." /> : <div className="grid gap-4 md:grid-cols-3">{user.map((c: any) => <CompCard key={c.id} c={c} clubId={active?.club_id} />)}</div>}
          </Panel>
          <GlobalLeaderboardPanel worldClubs={worldClubs} />
        </>
      )}
    </div>
  );
}
