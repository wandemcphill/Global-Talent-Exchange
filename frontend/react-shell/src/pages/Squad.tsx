import React, { useState, useMemo } from "react";
import { ArrowRight, CheckCircle2, AlertCircle, X } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { fmt, useActiveClub, useClub, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Loading, PageHeader, Panel, TraitBar } from "@/components/gtex/ui";
import { PlayerCard } from "@/components/gtex/PlayerCard";
import { PlayerDrawer } from "@/components/gtex/PlayerDrawer";
import { journeyLinks, readJourneyParams, SQUAD_SEASON_LABEL } from "@/lib/playerJourney";

function ManagerSheet({ club }: any) {
  const m = club.manager_profile || {};
  const refresh = useRefreshOwner();
  const fire = async () => {
    if (!window.confirm("Dismissing the manager triggers compensation and unsettles the squad. Continue?")) return;
    try {
      const { data } = await api.post(`/owner/clubs/${club.club_id}/manager/fire`);
      toast.warning(`Paid ${fmt(data.compensation)} GTX compensation. ${data.why}`);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <Panel eyebrow="Manager realism engine" title={m.name} testid="manager-sheet" className="lg:col-span-5"
      action={!m.is_default && <Btn variant="danger" onClick={fire} data-testid="fire-manager-button">Dismiss</Btn>}>
      <div className="mb-5 flex flex-wrap gap-2">
        <Chip tone="cyan">{m.tactical_preference}</Chip>
        <Chip tone="gold">Temperament: {m.temperament}</Chip>
        <Chip tone="purple">{m.rarity}</Chip>
      </div>
      <div className="space-y-3">
        <TraitBar label="Tactical Vision" value={m.tactics_stat} />
        <TraitBar label="Discipline" value={m.discipline} />
        <TraitBar label="Youth Development" value={m.youth_dev} />
        <TraitBar label="Player Loyalty" value={m.loyalty} />
      </div>
      <p className="mt-4 text-xs italic text-slate-400">"{m.philosophy_summary}"</p>
    </Panel>
  );
}

function HireManager({ club }: any) {
  const refresh = useRefreshOwner();
  const [busy, setBusy] = useState<string | null>(null);
  const { data: catalog = [] } = useQuery({ queryKey: ["mgr-catalog-6"], queryFn: async () => (await api.get("/managers/catalog", { params: { limit: 6 } })).data.items });
  const hire = async (m: any) => {
    setBusy(m.manager_id);
    try {
      await api.post(`/owner/clubs/${club.club_id}/manager`, { manager: { manager_id: m.manager_id, display_name: m.display_name, rarity: m.rarity, mentality: m.mentality, tactics: m.tactics, traits: m.traits, philosophy_summary: m.philosophy_summary } });
      toast.success(`Hired ${m.display_name} as manager.`);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(null);
    }
  };
  return (
    <Panel eyebrow="Candidate market" title="Available managers" testid="hire-manager-panel" className="lg:col-span-12">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {catalog.map((m: any) => (
          <div key={m.manager_id} className="rounded border border-white/10 bg-slate-900/60 p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-semibold text-white">{m.display_name}</p>
                <p className="text-xs text-slate-400">{m.mentality} · {m.rarity}</p>
              </div>
              <Btn variant="secondary" onClick={() => hire(m)} disabled={busy === m.manager_id}>
                {busy === m.manager_id ? "Hiring…" : "Hire"}
              </Btn>
            </div>
            <p className="mt-2 text-xs text-slate-400">{m.philosophy_summary}</p>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function SquadCards({ club }: any) {
  const [selected, setSelected] = useState<any | null>(null);
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" data-testid="squad-cards-grid">
        {club.squad.map((p: any) => (
          <div key={p.id} className="cursor-pointer" onClick={() => setSelected(p)}>
            <PlayerCard
              name={p.name}
              rating={p.rating}
              potential={p.potential}
              position={p.position}
              age={p.age}
              nationality={p.nationality}
              club={club.club_name}
              image={p.image || p.portrait_url || p.image_url}
              regen={Boolean(p.is_regen)}
              variant="compact"
              testid={`squad-player-${p.id}`}
              onClick={() => setSelected(p)}
            />
          </div>
        ))}
      </div>
      <PlayerDrawer player={selected} open={Boolean(selected)} onClose={() => setSelected(null)} />
    </>
  );
}

function SquadTable({ club, targetPlayerId }: any) {
  const [view, setView] = useState<"table" | "cards">("table");
  const [mentality, setMentality] = useState(club.mentality || "balanced");
  const save = async (m: string) => {
    try {
      await api.put(`/owner/clubs/${club.club_id}/mentality`, { mentality: m });
      setMentality(m);
      toast.success(`Default mentality updated to ${m}.`);
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <Panel eyebrow={`${club.squad.length} players`} title="Squad" testid="squad-table-panel" className="lg:col-span-7"
      action={<div className="flex flex-wrap gap-1">{["cards", "table"].map((v) => <button key={v} data-testid={`squad-view-${v}`} onClick={() => setView(v as any)} className={`gx-btn ${view === v ? "gx-btn-primary" : "gx-btn-ghost"}`}>{v}</button>)}<span className="mx-1 w-px bg-white/10" />{["defensive", "balanced", "attacking"].map((m) => <button key={m} data-testid={`default-mentality-${m}`} onClick={() => save(m)} className={`gx-btn ${mentality === m ? "gx-btn-primary" : "gx-btn-secondary"}`}>{m}</button>)}</div>}>
      {view === "cards" ? <div className="gx-scroll max-h-[640px] overflow-auto pr-1"><SquadCards club={club} /></div> : (
      <div className="gx-scroll max-h-[560px] overflow-auto">
        <table className="gx-table w-full min-w-[620px]">
          <thead><tr><th>Player</th><th>Pos</th><th>Age</th><th>Rtg/Pot</th><th>Morale</th><th>Mins</th><th>Value</th></tr></thead>
          <tbody>
            {club.squad.map((p: any) => {
              const isTarget = targetPlayerId && (p.id === targetPlayerId || p.player_id === targetPlayerId);
              return (
                <tr
                  key={p.id}
                  data-testid={`squad-row-${p.id}`}
                  className={isTarget ? "bg-emerald-500/10 border-l-4 border-emerald-400" : ""}
                >
                  <td className="font-medium text-white">
                    {p.name} {p.is_regen && <Chip tone="emerald">Regen</Chip>} {p.status === "listed" && <Chip tone="gold">Listed</Chip>} {p.injured_days > 0 && <Chip tone="red">Injured</Chip>}
                    {isTarget && <Chip tone="cyan">Target Prospect</Chip>}
                  </td>
                  <td className="capitalize">{p.position}</td>
                  <td className="gx-mono">{p.age}</td>
                  <td className="gx-mono">{p.rating}<span className="text-slate-500">/{p.potential}</span></td>
                  <td className="gx-mono">{p.morale}</td>
                  <td className="gx-mono">{p.minutes}</td>
                  <td className="gx-mono font-medium text-emerald-300">{fmt(p.value_coin)}</td>
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


function SquadRegistrationPanel({ club, targetPlayerId }: any) {
  const [busy, setBusy] = useState("");
  const registrationQuery = useQuery({
    queryKey: ["squad-registration", club.club_id],
    queryFn: async () =>
      (await api.get("/clubs/" + encodeURIComponent(club.club_id) + "/squad-registration", {
        params: { season_label: SQUAD_SEASON_LABEL },
      })).data,
    enabled: Boolean(club?.club_id),
  });
  const registration = registrationQuery.data || null;
  const status = String(registration?.status || "not synced").toLowerCase();
  const endpoint = "/clubs/" + encodeURIComponent(club.club_id) + "/squad-registration";

  const targetInRegistration = Boolean(
    targetPlayerId && (registration?.players || []).some((rp: any) => rp.player_id === targetPlayerId || rp.id === targetPlayerId),
  );
  const targetInClubSquad = Boolean(
    targetPlayerId && (club.squad || []).some((sp: any) => sp.id === targetPlayerId || sp.player_id === targetPlayerId),
  );

  const sync = async () => {
    setBusy("sync");
    try {
      await api.post(endpoint, { season_label: SQUAD_SEASON_LABEL, player_ids: [] });
      await registrationQuery.refetch();
      toast.success("Club squad synced for registration.");
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusy("");
    }
  };
  const submit = async () => {
    if (!registration) {
      toast.error("Sync the squad first, then submit registration.");
      return;
    }
    setBusy("submit");
    try {
      await api.post(endpoint + "/submit", undefined, { params: { season_label: SQUAD_SEASON_LABEL } });
      await registrationQuery.refetch();
      toast.success("Squad registration submitted.");
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusy("");
    }
  };
  const lock = async () => {
    if (!window.confirm("Locking the squad finalizes this competition roster for the current registration window. Continue?")) return;
    setBusy("lock");
    try {
      await api.post(endpoint + "/lock", undefined, { params: { season_label: SQUAD_SEASON_LABEL } });
      await registrationQuery.refetch();
      toast.success("Squad registration locked.");
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusy("");
    }
  };
  const tone = status === "locked" ? "emerald" : status === "submitted" ? "cyan" : status === "draft" ? "gold" : "slate";
  const canSync = status !== "locked";
  const canSubmit = Boolean(registration) && status !== "locked";
  const canLock = Boolean(registration) && status !== "locked";

  return (
    <Panel
      eyebrow="Competition readiness"
      title="Lineup & squad registration"
      testid="squad-registration-panel"
      className="mb-6"
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <Chip tone={tone}>{status === "not synced" ? "Not synced" : status}</Chip>
          <span className="text-xs text-slate-400">
            {registration ? String((registration.players || []).length) + " registered players" : "No roster registered yet"}
          </span>
          <span className="text-xs text-slate-500">Season: {registration?.season_label || SQUAD_SEASON_LABEL}</span>
        </div>

        {/* Targeted prospect journey status */}
        {targetPlayerId && (
          <div
            className={`rounded-lg p-3 text-xs border flex items-center justify-between gap-2 ${
              targetInRegistration
                ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-200"
                : targetInClubSquad
                ? "bg-amber-950/40 border-amber-500/40 text-amber-200"
                : "bg-slate-900/60 border-white/10 text-slate-300"
            }`}
            data-testid="target-prospect-registration-status"
          >
            <div className="flex items-center gap-2">
              {targetInRegistration ? (
                <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
              ) : (
                <AlertCircle size={16} className="text-amber-400 shrink-0" />
              )}
              <span>
                {targetInRegistration
                  ? `Target prospect ${targetPlayerId} is confirmed in this competition registration (${status}).`
                  : targetInClubSquad
                  ? `Target prospect ${targetPlayerId} is in your club squad roster, but not yet included in the competition registration. Click "Sync squad" below to update the roster.`
                  : `Target prospect ${targetPlayerId} is not in this club's squad yet. Verify transfer settlement in the Transfer Hub before registering.`}
              </span>
            </div>
          </div>
        )}

        {registration && Object.keys(registration.position_summary || {}).length > 0 && (
          <div className="flex flex-wrap gap-2" data-testid="squad-registration-position-summary">
            {Object.entries(registration.position_summary || {}).map(([position, count]: [string, any]) => (
              <Chip key={position}>{position}: {count}</Chip>
            ))}
          </div>
        )}
        <p className="max-w-3xl text-sm leading-6 text-slate-400">
          Sync the current club roster, submit it for eligibility checks, then lock it when ready. Registration is persisted separately from the tactical starting XI.
        </p>
        {registrationQuery.isError && (
          <p role="alert" className="text-sm text-amber-300">
            Registration status could not be loaded. Sync can retry the registration request.
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <Btn
            variant="secondary"
            onClick={sync}
            disabled={Boolean(busy) || registrationQuery.isLoading || !canSync}
            data-testid="squad-sync-registration-button"
          >
            {busy === "sync" ? "Syncing…" : "Sync squad"}
          </Btn>
          <Btn
            onClick={submit}
            disabled={Boolean(busy) || registrationQuery.isLoading || !canSubmit}
            data-testid="squad-submit-registration-button"
          >
            {busy === "submit" ? "Submitting…" : "Submit registration"}
          </Btn>
          <Btn
            variant="secondary"
            onClick={lock}
            disabled={Boolean(busy) || registrationQuery.isLoading || !canLock}
            data-testid="squad-lock-registration-button"
          >
            {busy === "lock" ? "Locking…" : "Lock registration"}
          </Btn>
        </div>
        {status === "locked" && (
          <p className="text-xs text-emerald-300">This registration is locked. The squad must be reopened through an authorized lifecycle flow before it can be changed.</p>
        )}
      </div>
    </Panel>
  );
}

export default function Squad() {
  const location = useLocation();
  const navigate = useNavigate();
  const { active } = useActiveClub();

  const journeyParams = useMemo(() => readJourneyParams(location.search), [location.search]);
  const targetPlayerId = journeyParams.player;

  const {
    data: club,
    isLoading,
    isError,
    refetch,
  } = useClub(active?.club_id);

  const clearTarget = () => {
    const searchParams = new URLSearchParams(location.search);
    searchParams.delete("player");
    const nextSearch = searchParams.toString();
    navigate({ search: nextSearch ? `?${nextSearch}` : "" }, { replace: true });
  };

  if (!active?.club_id) {
    return (
      <div data-testid="squad-no-club" className="space-y-6">
        <PageHeader
          eyebrow="Owner workspace"
          title="Choose a club to manage a squad"
          sub="Your GTEX member account is ready. Squad and manager tools become available when you create, join, or take over a club."
        />
        <Panel eyebrow="Club ownership is optional" title="Start with the club that is right for you">
          <p className="text-sm leading-6 text-slate-300">
            You can explore GTEX and manage eligible national-team activities without
            owning a club. To open the squad roster, first choose a club for your
            owner workspace.
          </p>
          <Link
            to="/app/clubs"
            data-testid="squad-choose-club-link"
            className="gx-btn gx-btn-primary mt-4 inline-flex"
          >
            Create or choose a club
          </Link>
        </Panel>
      </div>
    );
  }

  if (isLoading) return <Loading label="Loading your squad..." />;

  if (isError || !club) {
    return (
      <div data-testid="squad-unavailable" className="space-y-6">
        <PageHeader
          eyebrow="Owner workspace"
          title="Squad temporarily unavailable"
          sub="GTEX could not load this club's squad. Your club data has not been changed."
        />
        <Panel eyebrow="Connection status" title="Unable to load squad details">
          <p className="text-sm leading-6 text-slate-300">
            Retry the request. If the problem continues, return to My Clubs and
            select the club again.
          </p>
          <Btn variant="secondary" className="mt-4" onClick={() => void refetch()}>
            Retry squad
          </Btn>
          <Link
            to="/app/clubs"
            className="gx-btn gx-btn-ghost ml-2 mt-4 inline-flex"
          >
            Open My Clubs
          </Link>
        </Panel>
      </div>
    );
  }

  return (
    <div data-testid="squad-page">
      <PageHeader
        eyebrow="Manager & squad"
        title="Squad room"
        sub={club.club_name + " · " + club.squad.length + " registered players · Wage bill " + fmt(club.wage_bill) + " GTX / match"}
        action={
          <Link
            to={"/app/lineup?club_id=" + encodeURIComponent(club.club_id)}
            data-testid="open-lineup-tactics-button"
            className="gx-btn gx-btn-primary inline-flex items-center"
          >
            Open Lineup & Tactics <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        }
      />

      {targetPlayerId && (
        <div className="mb-4 flex items-center justify-between rounded-lg border border-cyan-500/40 bg-cyan-950/60 p-3 text-xs text-cyan-200">
          <span>
            Tracking journey target prospect: <b className="font-mono text-white">{targetPlayerId}</b>
          </span>
          <button
            type="button"
            onClick={clearTarget}
            className="rounded p-0.5 hover:bg-white/10 text-slate-300 hover:text-white"
            title="Clear target filter"
          >
            <X size={14} />
          </button>
        </div>
      )}

      <SquadRegistrationPanel club={club} targetPlayerId={targetPlayerId} />
      <div className="grid gap-6 lg:grid-cols-12">
        <ManagerSheet club={club} />
        <SquadTable club={club} targetPlayerId={targetPlayerId} />
        <HireManager club={club} />
      </div>
    </div>
  );
}
