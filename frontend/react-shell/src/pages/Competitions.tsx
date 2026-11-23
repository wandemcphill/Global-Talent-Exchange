import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Crown, ExternalLink, Flame, Globe, Medal, Shield, Swords, Trophy, Users, Zap } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, label, useActiveClub, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, PageHeader, Panel, Stat } from "@/components/gtex/ui";
import { CompetitionsTableView } from "@/components/gtex/CompetitionsTableView";
import { useSkin } from "@/lib/skin-engine";

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
  const fillPct = Math.min(100, Math.round(((c.entrants || 0) / (c.max_clubs || 1)) * 100));

  return (
    <div
      data-testid={`competition-card-${c.id}`}
      className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-gtex-graphite bg-gtex-slate/90 p-5 shadow-xl transition-all duration-300 hover:-translate-y-1 hover:border-gtex-emerald/60 hover:shadow-2xl"
    >
      {/* Top Arena Header */}
      <div>
        <div className="flex items-center justify-between gap-2 border-b border-white/5 pb-3">
          <div className="flex flex-wrap gap-1.5">
            <Chip tone={c.host_type === "gtex" ? "emerald" : "cyan"}>
              {c.host_type === "gtex" ? "GTEX Major" : "Community Cup"}
            </Chip>
            <Chip>{c.format?.toUpperCase()}</Chip>
            <Chip>Free entry</Chip>
          </div>
          <span
            className={`rounded-full px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider ${
              c.status === "open"
                ? "border border-amber-400/40 bg-amber-400/10 text-amber-300"
                : c.status === "running"
                  ? "border border-emerald-400/40 bg-emerald-400/10 text-emerald-300 animate-pulse"
                  : "border border-slate-700 bg-slate-800 text-slate-400"
            }`}
          >
            {c.status}
          </span>
        </div>

        <div className="mt-3 flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-gtex-midnight text-amber-300 shadow-inner">
            <Trophy size={18} />
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="gx-display text-lg font-bold uppercase tracking-tight text-white group-hover:text-emerald-300 transition-colors truncate">
              {c.name}
            </h3>
            <p className="text-xs text-slate-400 line-clamp-2 mt-0.5 leading-relaxed">
              {c.description}
            </p>
          </div>
        </div>

        {/* Prize & Entrant Metrics */}
        <div className="mt-4 grid grid-cols-3 gap-2 rounded-xl border border-white/5 bg-gtex-midnight/70 p-3 text-center">
          <div>
            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Entry</p>
            <p className="gx-mono text-xs font-bold text-white mt-0.5">FREE</p>
          </div>
          <div>
            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-500">
              Prize Pool
            </p>
            <p className="gx-mono text-xs font-black text-amber-300 mt-0.5">
              <Coin amount={c.prize_pool} />
            </p>
          </div>
          <div>
            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Bracket</p>
            <p className="gx-mono text-xs font-bold text-slate-300 mt-0.5">
              {c.entrants}/{c.max_clubs}
            </p>
          </div>
        </div>

        {/* Capacity Bar */}
        <div className="mt-2.5">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 to-amber-400 transition-all duration-500"
              style={{ width: `${fillPct}%` }}
            />
          </div>
        </div>

        {c.invite_code && (
          <p
            className="gx-mono mt-3 rounded bg-white/5 px-2 py-1 text-center text-xs text-cyan-300"
            data-testid={`invite-code-${c.id}`}
          >
            Invite Code: <b className="text-white tracking-widest">{c.invite_code}</b>
          </p>
        )}
      </div>

      {/* Action Footer */}
      <div className="mt-5 flex gap-2">
        <Link
          to={`/app/competitions/${c.id}`}
          className="gx-btn gx-btn-secondary flex-1 text-xs"
          data-testid={`view-competition-${c.id}`}
        >
          View Details
        </Link>
        {c.status === "open" && !entered && (
          <Btn
            className="flex-1 text-xs font-black uppercase tracking-wider"
            disabled={busy || !clubId}
            onClick={enter}
            data-testid={`enter-competition-${c.id}`}
          >
            {busy ? "Registering…" : "Enter Match"}
          </Btn>
        )}
      </div>
    </div>
  );
}

const HOST_TEMPLATES_KEY = "gtex-host-templates";

function HostForm({
  worldClubs = [],
  externalOpponent,
}: {
  worldClubs?: any[];
  externalOpponent?: any | null;
}) {
  const refresh = useRefreshOwner();
  const { active } = useActiveClub();
  const { user: currentUser } = useAuth();
  const [f, setF] = useState<any>({
    name: "",
    format: "league",
    max_clubs: 8,
    pin: "",
    winner_prize: "0",
    contribution: "0",
    template_key: "",
  });
  const [opponentQuery, setOpponentQuery] = useState("");
  const [opponents, setOpponents] = useState<any[]>([]);
  const [opponent, setOpponent] = useState<any | null>(null);

  useEffect(() => {
    if (externalOpponent && externalOpponent.id) {
      setOpponent(externalOpponent);
      setOpponentQuery(externalOpponent.club_name || "");
      setF((prev: any) => ({
        ...prev,
        name:
          prev.name ||
          `${active?.club_name || "GTEX"} vs ${externalOpponent.club_name || "Rival"} Cup`,
      }));
    }
  }, [externalOpponent, active?.club_name]);

  const rivalWorldClubs = (worldClubs || []).filter((c: any) => {
    const cid = c.club_id || c.id;
    if (!cid || cid === active?.club_id) return false;
    if (currentUser?.id && c.owner_user_id && String(c.owner_user_id) === String(currentUser.id)) {
      return false;
    }
    return true;
  });
  const [savedName, setSavedName] = useState("");
  const [saved, setSaved] = useState<any[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(HOST_TEMPLATES_KEY) || "[]");
    } catch {
      return [];
    }
  });
  const applyTemplate = (key: string) => {
    const presets: Record<string, any> = {
      weekend_league: {
        name: "Weekend League",
        format: "league",
        max_clubs: 10,
        template_key: "weekend_league",
      },
      cup_8: { name: "Friends Cup", format: "knockout", max_clubs: 8, template_key: "cup_8" },
    };
    const mine = saved.find((item) => item.id === key);
    setF({ ...f, ...(presets[key] || mine || {}), template_key: presets[key] ? key : "" });
  };
  const saveTemplate = () => {
    const name = savedName.trim();
    if (name.length < 3) {
      toast.error("Name the template before saving it.");
      return;
    }
    const next = [
      {
        id: `mine-${Date.now()}`,
        name,
        format: f.format,
        max_clubs: Number(f.max_clubs),
        pin: f.pin,
        winner_prize: f.winner_prize,
        contribution: f.contribution,
      },
      ...saved,
    ].slice(0, 12);
    localStorage.setItem(HOST_TEMPLATES_KEY, JSON.stringify(next));
    setSaved(next);
    setSavedName("");
    toast.success(`Saved template ${name}.`);
  };
  const searchOpponents = async (value: string) => {
    setOpponentQuery(value);
    if (value.trim().length < 2) {
      setOpponents([]);
      return;
    }
    try {
      const { data } = await api.get("/community/discovery/clubs", {
        params: { q: value.trim(), limit: 8 },
      });
      setOpponents(data.clubs || []);
    } catch {
      setOpponents([]);
    }
  };
  const submit = async (e: any) => {
    e.preventDefault();
    try {
      const { data } = await api.post("/owner/competitions", {
        name: f.name,
        format: f.format,
        max_clubs: Number(f.max_clubs),
        pin: f.pin || null,
        winner_prize: Number(f.winner_prize || 0),
        contribution: 0,
        template_key: f.template_key || null,
        club_id: active?.club_id || null,
        opponent_club_id: opponent?.id || null,
      });
      toast.success(`Hosted. Pin ${data.invite_code}.`);
      refresh();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };
  return (
    <form
      onSubmit={submit}
      className="grid gap-3 md:grid-cols-4"
      data-testid="host-competition-form"
    >
      <select
        className="gx-input md:col-span-2"
        value=""
        onChange={(e) => applyTemplate(e.target.value)}
        data-testid="host-template-select"
      >
        <option value="">Start from a template</option>
        <option value="weekend_league">Weekend league</option>
        <option value="cup_8">8-club cup</option>
        {saved.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </select>
      <input
        required
        minLength={3}
        data-testid="host-name-input"
        className="gx-input md:col-span-2"
        placeholder="Adekunle and Friends Cup"
        value={f.name}
        onChange={(e) => setF({ ...f, name: e.target.value, template_key: "" })}
      />
      <select
        data-testid="host-format-select"
        className="gx-input"
        value={f.format}
        onChange={(e) => setF({ ...f, format: e.target.value })}
      >
        <option value="league">League</option>
        <option value="knockout">Cup</option>
      </select>
      <select
        data-testid="host-size-select"
        className="gx-input"
        value={f.max_clubs}
        onChange={(e) => setF({ ...f, max_clubs: e.target.value })}
      >
        {[2, 4, 6, 8, 10, 12, 16].map((n) => (
          <option key={n} value={n}>
            {n} clubs
          </option>
        ))}
      </select>
      <input
        data-testid="host-opponent-input"
        className="gx-input md:col-span-2"
        placeholder="Opponent club"
        value={opponentQuery}
        onChange={(e) => searchOpponents(e.target.value)}
      />
      {opponents.length > 0 && (
        <div
          className="md:col-span-4 rounded border border-white/10 bg-black/40"
          data-testid="host-opponent-results"
        >
          {opponents.map((club) => (
            <button
              type="button"
              key={club.id}
              className="block w-full px-3 py-2 text-left text-sm text-white hover:bg-white/5"
              onClick={() => {
                setOpponent(club);
                setOpponentQuery(club.club_name);
                setOpponents([]);
              }}
            >
              {club.club_name}
              {club.city_name ? ` · ${club.city_name}` : ""}
            </button>
          ))}
        </div>
      )}
      {opponent && (
        <p className="text-xs text-emerald-300 md:col-span-4">
          Opponent: {opponent.club_name}. They receive the pin with the challenge.
        </p>
      )}
      {rivalWorldClubs.length > 0 && (
        <div
          className="md:col-span-4 flex flex-wrap items-center gap-1.5 text-xs"
          data-testid="host-quick-pick-rivals"
        >
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Quick-pick platform club:
          </span>
          {rivalWorldClubs.slice(0, 8).map((c: any) => {
            const cid = c.club_id || c.id;
            const isSelected = (opponent?.id || opponent?.club_id) === cid;
            return (
              <button
                type="button"
                key={cid}
                onClick={() => {
                  const picked = {
                    id: cid,
                    club_id: cid,
                    club_name: c.club_name,
                    slug: c.slug || cid,
                  };
                  setOpponent(picked);
                  setOpponentQuery(c.club_name);
                  setOpponents([]);
                  if (!f.name) {
                    setF((prev: any) => ({
                      ...prev,
                      name: `${active?.club_name || "GTEX"} vs ${c.club_name} Cup`,
                    }));
                  }
                }}
                className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold transition ${
                  isSelected
                    ? "border-emerald-400 bg-emerald-500/20 text-emerald-200"
                    : "border-white/15 bg-white/5 text-slate-200 hover:border-emerald-400/50 hover:text-white"
                }`}
              >
                {c.club_name}
              </button>
            );
          })}
        </div>
      )}
      <input
        data-testid="host-pin-input"
        className="gx-input uppercase"
        placeholder="Pin (optional)"
        maxLength={12}
        value={f.pin}
        onChange={(e) => setF({ ...f, pin: e.target.value.toUpperCase() })}
      />
      <input
        data-testid="host-prize-input"
        className="gx-input"
        type="number"
        min="0"
        placeholder="Winner purse"
        value={f.winner_prize}
        onChange={(e) => setF({ ...f, winner_prize: e.target.value })}
      />
      <Btn type="submit" data-testid="host-submit-button">
        Host
      </Btn>
      <div className="flex gap-2 md:col-span-3">
        <input
          className="gx-input"
          placeholder="Save these settings as my template"
          value={savedName}
          onChange={(e) => setSavedName(e.target.value)}
        />
        <Btn type="button" variant="secondary" onClick={saveTemplate}>
          Save template
        </Btn>
      </div>
      <p className="text-xs text-slate-400 md:col-span-4">
        Entering is free. Set a pin so a friend can join, and GTEX funds the winner purse.
      </p>
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
      <input
        data-testid="join-code-input"
        className="gx-input uppercase"
        placeholder="Invite code"
        value={code}
        onChange={(e) => setCode(e.target.value)}
      />
      <Btn
        variant="secondary"
        disabled={code.length < 4}
        onClick={join}
        data-testid="join-code-button"
      >
        Join
      </Btn>
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
    const prestige = activeClub.prestige ?? activeClub.health?.prestige ?? 45;
    const squadOvr = activeClub.squad_ovr ?? activeClub.health?.squad_ovr ?? 75;
    const rawDepth = activeClub.squad_depth ?? activeClub.health?.squad_depth;
    const depth =
      typeof rawDepth === "number"
        ? rawDepth
        : rawDepth === "deep"
          ? 90
          : rawDepth === "healthy"
            ? 75
            : 60;
    const region =
      activeClub.region ||
      activeClub.country_code ||
      activeClub.continent_code ||
      user?.region ||
      "AF-WEST";
    const filedProfile =
      prestige != null && squadOvr != null && typeof depth === "number" && Boolean(region);
    setBusy(true);
    try {
      if (filedProfile) {
        await api.put(`/simulation-matchmaking/profiles/${user.id}`, {
          user_id: user.id,
          club_id: activeClub.club_id,
          club_name: activeClub.club_name || "Unnamed club",
          manager_rating: 1200 + Number(prestige) * 5,
          tactical_profile: {
            style,
            pressing: style === "counter" ? "medium" : "high",
            tempo: style === "possession" ? "normal" : "fast",
          },
          squad_strength: Math.min(99, Math.max(1, Number(squadOvr))),
          squad_depth: Math.min(100, Math.max(1, Number(depth))),
          preferred_match_type: ["quick"],
          connection_quality: "good",
          region,
          availability: "online",
        });
      }

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
      toast.success(
        `Matched vs ${data.opponent?.club_name || "Rival Club"} (${data.match_context?.tactical_story || "Tactical Clash"})!`,
      );
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
      toast.success(
        `Quick match settled: ${data.home_score}–${data.away_score} (${label(data.result)})`,
      );
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
            Pair <b className="text-white">{activeClub?.club_name || "your club"}</b> against live
            owners or elite tactical bots via{" "}
            <span className="gx-mono text-emerald-300">/api/simulation-matchmaking/quick-game</span>
            .
          </p>
          <div className="flex flex-wrap gap-2 text-xs">
            <Chip tone="emerald">Entry is free</Chip>
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

          <Btn
            onClick={launchQuickGame}
            disabled={busy || !activeClub?.club_id}
            data-testid="launch-quick-game-btn"
          >
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
              {activeClub?.club_name} vs. {lastMatch.opponent?.club_name} (
              {lastMatch.opponent?.region})
            </p>
            <p className="text-slate-300 mt-0.5">
              {lastMatch.match_context?.tactical_story} · Compatibility{" "}
              {lastMatch.match_context?.tactical_compatibility_score}% · Difficulty:{" "}
              <b className="uppercase text-amber-300">
                {lastMatch.match_context?.expected_difficulty}
              </b>
            </p>
            {lastMatch.settlement && (
              <p className="text-emerald-300 font-bold mt-1">
                Final Score: {lastMatch.settlement.home_score} – {lastMatch.settlement.away_score} (
                {label(lastMatch.settlement.result)})
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {lastMatch.match_id && (
              <Btn
                variant="secondary"
                data-testid="play-quick-game-btn"
                onClick={() => navigate(`/app/match/${lastMatch.match_id}?live=1`)}
              >
                <Flame size={13} /> Play & Watch Match
              </Btn>
            )}
            {!lastMatch.settlement && (
              <Btn
                variant="gold"
                data-testid="settle-quick-game-btn"
                onClick={() => settleQuickGame(lastMatch.match_id)}
                disabled={busy}
              >
                <Zap size={13} /> Settle Match Result
              </Btn>
            )}
          </div>
        </div>
      )}
    </Panel>
  );
}

function GlobalLeaderboardPanel({
  worldClubs,
  activeClub,
  currentUserId,
  onChallengeClub,
  onInviteClub,
  busyClubId,
}: {
  worldClubs: any[];
  activeClub?: any;
  currentUserId?: string;
  onChallengeClub?: (club: any) => void;
  onInviteClub?: (club: any) => void;
  busyClubId?: string | null;
}) {
  const [boardScope, setBoardScope] = useState<"global" | "clubs">("clubs");

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
    .sort(
      (a, b) =>
        Number(b.prestige || 0) - Number(a.prestige || 0) ||
        Number(b.trophies || 0) - Number(a.trophies || 0),
    )
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
              <span>
                Days Remaining: <b className="text-white">{season.days_remaining}d</b>
              </span>
              <span>
                Default ELO: <b className="text-white">{season.default_rating}</b>
              </span>
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
                  <td>
                    <Chip tone="gold">{label(row.tier)}</Chip>
                  </td>
                  <td className="gx-mono text-emerald-300">{row.rating}</td>
                  <td className="gx-mono text-xs">
                    {row.wins}-{row.draws}-{row.losses}
                  </td>
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
          <table className="gx-table w-full min-w-[740px]">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Club</th>
                <th>Country</th>
                <th>Prestige</th>
                <th>Trophies</th>
                <th>Group</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedClubs.map((c: any, idx: number) => {
                const cid = c.club_id || c.id;
                const slug = c.slug || cid;
                const isOwn =
                  cid === activeClub?.club_id ||
                  Boolean(
                    currentUserId &&
                      c.owner_user_id &&
                      String(currentUserId) === String(c.owner_user_id),
                  );
                return (
                  <tr key={cid} data-testid={`club-rank-row-${cid}`}>
                    <td className="gx-mono font-bold text-amber-300">#{idx + 1}</td>
                    <td className="font-semibold text-white">
                      <Link
                        to={`/club/${encodeURIComponent(slug)}`}
                        className="inline-flex items-center gap-1.5 text-white hover:text-emerald-300 hover:underline"
                      >
                        <span>{c.club_name}</span>
                        <ExternalLink size={12} className="text-slate-400" />
                      </Link>
                      {isOwn && (
                        <span className="ml-2 rounded bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-bold uppercase text-emerald-300">
                          Your Club
                        </span>
                      )}
                    </td>
                    <td className="text-slate-300">{c.country || c.country_code || "Global"}</td>
                    <td className="gx-mono text-emerald-300">
                      {c.prestige == null ? "—" : c.prestige}
                    </td>
                    <td className="gx-mono text-amber-300">{c.trophies ?? 0}</td>
                    <td>
                      {c.multi_club_group ? (
                        <Chip tone="cyan">Multi-Club Group</Chip>
                      ) : (
                        <span className="text-xs text-slate-500">Independent</span>
                      )}
                    </td>
                    <td className="text-right">
                      <div className="inline-flex flex-wrap justify-end gap-1.5">
                        <Link
                          to={`/club/${encodeURIComponent(slug)}`}
                          className="gx-btn gx-btn-secondary text-[11px] px-2.5 py-1"
                          data-testid={`view-club-profile-${cid}`}
                        >
                          Profile & Squad
                        </Link>
                        {!isOwn && onChallengeClub && (
                          <button
                            type="button"
                            disabled={busyClubId === cid}
                            onClick={() => onChallengeClub(c)}
                            className="gx-btn gx-btn-primary text-[11px] px-2.5 py-1"
                            data-testid={`challenge-club-btn-${cid}`}
                          >
                            {busyClubId === cid ? "Sending…" : "Challenge Match"}
                          </button>
                        )}
                        {!isOwn && onInviteClub && (
                          <button
                            type="button"
                            disabled={busyClubId === cid}
                            onClick={() => onInviteClub(c)}
                            className="gx-btn gx-btn-secondary text-[11px] px-2.5 py-1"
                            data-testid={`invite-club-btn-${cid}`}
                          >
                            Invite to Cup
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

export default function Competitions() {
  const { active } = useActiveClub();
  const { user: currentUser } = useAuth();
  const [searchParams] = useSearchParams();
  const { getModuleView, setModuleView } = useSkin();
  const compView = getModuleView("competitions");
  const { data, isLoading } = useQuery({
    queryKey: ["competitions"],
    queryFn: async () => (await api.get("/owner/competitions")).data.competitions,
  });
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
  const { data: discoveryClubs = [] } = useQuery({
    queryKey: ["discovery-clubs-competitions"],
    queryFn: async () => {
      try {
        return (await api.get("/community/discovery/clubs", { params: { limit: 30 } })).data.clubs || [];
      } catch {
        return [];
      }
    },
  });

  const allPlatformClubs = React.useMemo(() => {
    const merged = new Map<string, any>();
    for (const c of worldClubs || []) {
      const id = c.club_id || c.id;
      if (id) merged.set(String(id), { ...c, club_id: id, id });
    }
    for (const c of discoveryClubs || []) {
      const id = c.id || c.club_id;
      if (!id) continue;
      const existing = merged.get(String(id)) || {};
      merged.set(String(id), {
        ...c,
        ...existing,
        club_id: id,
        id,
        slug: existing.slug || c.slug || id,
        club_name: existing.club_name || c.club_name,
        city_name: existing.city_name || c.city_name,
        country_code: existing.country_code || c.country_code,
        country:
          existing.country ||
          [c.city_name, c.country_code].filter(Boolean).join(", ") ||
          "Global",
        primary_color: existing.primary_color || c.primary_color || "#0F766E",
        owner_name:
          existing.owner_name ||
          c.owner?.display_name ||
          c.owner?.username ||
          "GTEX Club Owner",
        trophies: existing.trophies ?? c.trophy_count ?? 0,
      });
    }
    return Array.from(merged.values());
  }, [worldClubs, discoveryClubs]);

  const [selectedHostOpponent, setSelectedHostOpponent] = useState<any | null>(null);
  const [busyClubId, setBusyClubId] = useState<string | null>(null);

  useEffect(() => {
    const inviteId = searchParams.get("invite_club_id");
    const inviteName = searchParams.get("invite_club_name");
    if (inviteId) {
      setSelectedHostOpponent({
        id: inviteId,
        club_id: inviteId,
        club_name: inviteName || "Invited Club",
      });
    }
  }, [searchParams]);

  const [fixtureQuery, setFixtureQuery] = useState("");
  const [fixtures, setFixtures] = useState<any[]>([]);
  const searchFixtures = async () => {
    const q = fixtureQuery.trim();
    if (!q) {
      setFixtures([]);
      return;
    }
    try {
      const { data: found } = await api.get("/owner/competitions/fixtures", { params: { q } });
      setFixtures(found.fixtures || []);
    } catch (error) {
      toast.error(errMsg(error));
    }
  };
  const gtex = (data || []).filter((c: any) => c.host_type === "gtex");
  const user = (data || []).filter((c: any) => c.host_type === "user");
  const needle = fixtureQuery.trim().toLowerCase();
  const visibleGtex = needle
    ? gtex.filter((c: any) => `${c.name} ${c.description || ""}`.toLowerCase().includes(needle))
    : gtex;
  const visibleUser = needle
    ? user.filter((c: any) => `${c.name} ${c.description || ""}`.toLowerCase().includes(needle))
    : user;

  const handleChallengeClub = async (targetClub: any) => {
    const targetId = targetClub?.club_id || targetClub?.id;
    if (!active?.club_id || !targetId) {
      toast.error("Select your active club before sending a match challenge.");
      return;
    }
    if (active.club_id === targetId) {
      toast.error("You cannot challenge your own club.");
      return;
    }
    setBusyClubId(targetId);
    try {
      const created = await api.post(`/clubs/${active.club_id}/challenges`, {
        title: `Challenge ${targetClub.club_name || "club"}`.slice(0, 160),
        message: `${active.club_name || "Our club"} wants a match against ${targetClub.club_name || "your club"}.`,
        target_club_id: targetId,
        visibility: "private",
        stakes_text: "Friendly",
      });
      const challengeId = created.data?.challenge?.id || created.data?.card?.challenge_id;
      if (challengeId) {
        await api.post(`/challenges/${challengeId}/publish`);
      }
      toast.success(`Match challenge sent to ${targetClub.club_name}!`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyClubId(null);
    }
  };

  const handleInviteClubToCompetition = async (targetClub: any) => {
    const targetId = targetClub?.club_id || targetClub?.id;
    if (!active?.club_id || !targetId) {
      toast.error("Select your active club before sending a competition invite.");
      return;
    }
    if (active.club_id === targetId) {
      toast.error("You cannot invite your own club.");
      return;
    }
    setSelectedHostOpponent({
      id: targetId,
      club_id: targetId,
      club_name: targetClub.club_name,
      slug: targetClub.slug || targetId,
    });
    const openUserComp = user.find((comp: any) => comp.status === "open" && comp.invite_code);
    if (openUserComp) {
      setBusyClubId(targetId);
      try {
        const created = await api.post(`/clubs/${active.club_id}/challenges`, {
          title: `Join ${openUserComp.name}`.slice(0, 160),
          message: `You are invited to ${openUserComp.name}. Use pin ${openUserComp.invite_code} to enter with ${targetClub.club_name}.`,
          target_club_id: targetId,
          competition_id: openUserComp.id,
          visibility: "private",
          stakes_text: "Friend competition",
          metadata_json: {
            invite_code: openUserComp.invite_code,
            source: "friend_competition",
          },
        });
        const challengeId = created.data?.challenge?.id || created.data?.card?.challenge_id;
        if (challengeId) {
          await api.post(`/challenges/${challengeId}/publish`);
        }
        toast.success(
          `Invited ${targetClub.club_name} to ${openUserComp.name} (Pin ${openUserComp.invite_code})!`,
        );
        return;
      } catch (e) {
        toast.error(errMsg(e));
      } finally {
        setBusyClubId(null);
      }
    }
    const hostEl = document.querySelector('[data-testid="host-panel"]');
    if (hostEl && typeof hostEl.scrollIntoView === "function") {
      hostEl.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    toast.info(
      `Selected ${targetClub.club_name} as opponent in "Host a friend competition" below — click Host to send the invite pin!`,
    );
  };
  return (
    <div data-testid="competitions-page" className="space-y-6">
      <PageHeader
        eyebrow="Competitions"
        title="Where prestige is earned"
        sub={`Entering as ${active?.club_name || "-"} in ${active?.division_name || "Foundation"}. Entry is free. Same-owner clubs can't share a prize-sensitive bracket and are routed apart in knockouts.`}
        action={
          <div
            className="flex items-center gap-1 rounded-xl border border-white/10 bg-black/40 p-1"
            data-testid="competitions-view-toggle"
          >
            <button
              type="button"
              onClick={() => setModuleView("competitions", "discovery")}
              data-testid="comp-view-discovery"
              className={`rounded-lg px-2.5 py-1 text-xs font-bold transition ${
                compView === "discovery"
                  ? "bg-emerald-500 text-black shadow"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Tournament Cards
            </button>
            <button
              type="button"
              onClick={() => setModuleView("competitions", "table")}
              data-testid="comp-view-table"
              className={`rounded-lg px-2.5 py-1 text-xs font-bold transition ${
                compView === "table"
                  ? "bg-emerald-500 text-black shadow"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Fixtures Table
            </button>
          </div>
        }
      />
      {isLoading ? (
        <Loading />
      ) : (
        <>
          <div className="flex flex-wrap gap-2" data-testid="competition-search">
            <input
              className="gx-input min-w-64 flex-1"
              placeholder="Find a match by competition, club, or opponent"
              value={fixtureQuery}
              onChange={(e) => setFixtureQuery(e.target.value)}
            />
            <Btn variant="secondary" onClick={searchFixtures}>
              Search matches
            </Btn>
          </div>
          {fixtures.length > 0 && (
            <Panel eyebrow="Fixtures" title="Matching matches">
              {fixtures.map((fixture) => (
                <Link
                  key={fixture.id}
                  to={fixture.route || `/app/match/${fixture.id}`}
                  className="block rounded border border-white/5 px-3 py-2 text-sm text-white hover:border-emerald-500/40"
                >
                  {fixture.home_name} vs {fixture.away_name} · {fixture.competition_name} ·{" "}
                  {fixture.status}
                </Link>
              ))}
            </Panel>
          )}
          <QuickMatchmakingDesk activeClub={active} />
          {allPlatformClubs.length > 0 && (
            <Panel
              eyebrow="Live GTEX World Directory · Inspect Squads & Issue Challenges"
              title={`Platform Clubs & Rivals (${allPlatformClubs.length})`}
              testid="platform-clubs-directory"
            >
              <div className="grid gap-3 md:grid-cols-3">
                {allPlatformClubs.map((c: any) => {
                  const cid = c.club_id || c.id;
                  const slug = c.slug || cid;
                  const isOwn =
                    cid === active?.club_id ||
                    Boolean(
                      currentUser?.id &&
                        c.owner_user_id &&
                        String(currentUser.id) === String(c.owner_user_id),
                    );
                  return (
                    <div
                      key={cid}
                      data-testid={`platform-club-card-${cid}`}
                      className="flex flex-col justify-between rounded-xl border border-white/10 bg-slate-950/75 p-4 shadow-lg transition hover:border-emerald-400/50"
                    >
                      <div>
                        <div className="flex items-start justify-between gap-2">
                          <Link
                            to={`/club/${encodeURIComponent(slug)}`}
                            className="group flex items-center gap-2.5 min-w-0"
                          >
                            <span
                              className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-white/20 text-xs font-black text-white shadow"
                              style={{ background: c.primary_color || "#0F766E" }}
                            >
                              {String(c.short_name || c.club_name || "FC")
                                .slice(0, 3)
                                .toUpperCase()}
                            </span>
                            <div className="min-w-0">
                              <p className="truncate font-extrabold text-white group-hover:text-emerald-300 group-hover:underline">
                                {c.club_name}
                              </p>
                              <p className="truncate text-[11px] text-slate-400">
                                {c.country || c.country_code || "Global"} ·{" "}
                                {c.division_name || "Foundation"}
                              </p>
                            </div>
                          </Link>
                          {isOwn ? (
                            <Chip tone="emerald">Your Club</Chip>
                          ) : (
                            <Chip tone="cyan">Rival Club</Chip>
                          )}
                        </div>
                        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-300">
                          <span>
                            Prestige: <b className="text-emerald-300">{c.prestige ?? "—"}</b>
                          </span>
                          {c.squad_count != null && (
                            <span>
                              Squad: <b className="text-white">{c.squad_count} players</b>
                            </span>
                          )}
                          <span>
                            Trophies: <b className="text-amber-300">{c.trophies ?? 0}</b>
                          </span>
                        </div>
                        {c.owner_name && (
                          <p className="mt-1 text-[11px] text-slate-400">
                            Owner: <span className="text-slate-200">{c.owner_name}</span>
                          </p>
                        )}
                      </div>
                      <div className="mt-4 flex flex-wrap gap-1.5 border-t border-white/10 pt-3">
                        <Link
                          to={`/club/${encodeURIComponent(slug)}`}
                          className="gx-btn gx-btn-secondary flex-1 text-center text-[11px] py-1.5"
                          data-testid={`platform-club-view-${cid}`}
                        >
                          View Profile & Squad
                        </Link>
                        {!isOwn && (
                          <>
                            <button
                              type="button"
                              disabled={busyClubId === cid}
                              onClick={() => handleChallengeClub(c)}
                              className="gx-btn gx-btn-primary text-[11px] px-2.5 py-1.5"
                              data-testid={`platform-club-challenge-${cid}`}
                            >
                              {busyClubId === cid ? "Sending…" : "Challenge Match"}
                            </button>
                            <button
                              type="button"
                              disabled={busyClubId === cid}
                              onClick={() => handleInviteClubToCompetition(c)}
                              className="gx-btn gx-btn-secondary text-[11px] px-2.5 py-1.5"
                              data-testid={`platform-club-invite-${cid}`}
                            >
                              Invite to Cup
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </Panel>
          )}
          <Panel
            eyebrow="GTEX-hosted"
            title="Platform competitions"
            testid="gtex-competitions-panel"
          >
            {visibleGtex.length === 0 ? (
              <Empty
                title="No platform competitions are open"
                body="Host a competition for other clubs, or join one with an invite code. Entry is free."
              />
            ) : compView === "table" ? (
              <CompetitionsTableView competitions={visibleGtex} clubId={active?.club_id} />
            ) : (
              <div className="grid gap-4 md:grid-cols-3" data-testid="competitions-cards-grid">
                {visibleGtex.map((c: any) => (
                  <CompCard key={c.id} c={c} clubId={active?.club_id} />
                ))}
              </div>
            )}
          </Panel>
          <div className="grid gap-6 lg:grid-cols-12">
            <Panel
              eyebrow="User-hosted"
              title="Host a friend competition"
              className="lg:col-span-8"
              testid="host-panel"
            >
              <HostForm worldClubs={allPlatformClubs} externalOpponent={selectedHostOpponent} />
            </Panel>
            <Panel
              eyebrow="Invite"
              title="Join with a code"
              className="lg:col-span-4"
              testid="join-panel"
            >
              <JoinCode clubId={active?.club_id} />
            </Panel>
          </div>
          <Panel
            eyebrow="Friends & hosted"
            title="Your user-hosted competitions"
            testid="user-competitions-panel"
          >
            {visibleUser.length === 0 ? (
              <Empty title="None yet" body="Host one above or join with an invite code." />
            ) : (
              <div className="grid gap-4 md:grid-cols-3">
                {visibleUser.map((c: any) => (
                  <CompCard key={c.id} c={c} clubId={active?.club_id} />
                ))}
              </div>
            )}
          </Panel>
          <GlobalLeaderboardPanel
            worldClubs={allPlatformClubs}
            activeClub={active}
            currentUserId={currentUser?.id ? String(currentUser.id) : undefined}
            onChallengeClub={handleChallengeClub}
            onInviteClub={handleInviteClubToCompetition}
            busyClubId={busyClubId}
          />
        </>
      )}
    </div>
  );
}
