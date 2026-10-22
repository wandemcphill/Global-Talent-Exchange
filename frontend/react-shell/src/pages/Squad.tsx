import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { fmt, useActiveClub, useClub, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Loading, PageHeader, Panel, TraitBar } from "@/components/gtex/ui";
import { PlayerCard } from "@/components/gtex/PlayerCard";
import { PlayerDrawer } from "@/components/gtex/PlayerDrawer";

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
        <Chip>Discipline: {m.discipline_style}</Chip>
        <Chip>Media: {m.media_style}</Chip>
        <Chip tone="blue">Transfers: {m.transfer_preference}</Chip>
      </div>
      <div className="space-y-3">
        <TraitBar label="Mood" value={m.mood} max={100} testid="manager-mood" />
        <TraitBar label="Ambition" value={m.ambition} />
        <TraitBar label="Loyalty" value={m.loyalty} />
        <TraitBar label="Youth development" value={m.youth_development} />
        <TraitBar label="Tactical quality" value={m.tactical_quality} />
      </div>
      <p className="mt-5 text-xs text-slate-500">{m.philosophy}</p>
      <p className="mt-2 text-xs text-slate-500">How this matters: tactical quality adds matchday strength, youth development drives regen growth, temperament and ambition decide how often and how loudly the manager makes demands.</p>
    </Panel>
  );
}

function HireManager({ club }: any) {
  const refresh = useRefreshOwner();
  const { data } = useQuery({ queryKey: ["mgr-catalog-6"], queryFn: async () => (await api.get("/managers/catalog", { params: { limit: 6 } })).data.items });
  if (!club.manager_profile?.is_default) return null;
  const hire = async (m: any) => {
    try {
      await api.post(`/owner/clubs/${club.club_id}/manager`, { manager: { manager_id: m.manager_id, display_name: m.display_name, rarity: m.rarity, mentality: m.mentality, tactics: m.tactics, traits: m.traits, philosophy_summary: m.philosophy_summary } });
      toast.success(`${m.display_name} appointed`);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <Panel eyebrow="Hire" title="Available managers" testid="hire-manager-panel" className="lg:col-span-12">
      <div className="grid gap-3 md:grid-cols-3">
        {(data || []).map((m: any) => (
          <div key={m.manager_id} className="flex items-center justify-between rounded-sm border border-white/10 p-3">
            <div><p className="text-sm font-semibold text-white">{m.display_name}</p><p className="text-xs capitalize text-slate-500">{m.rarity} · {m.mentality}</p></div>
            <Btn variant="secondary" onClick={() => hire(m)} data-testid={`hire-manager-${m.manager_id}`}>Appoint</Btn>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function SquadCards({ club }: any) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3" data-testid="squad-cards">
      {club.squad.map((p: any) => (
        <PlayerCard key={p.id} testid={`squad-card-${p.id}`} name={p.name} rating={p.rating} potential={p.potential} position={p.position} age={p.age} regen={p.is_regen}
          image={p.portrait_url}
          badge={p.status === "listed" ? "Listed" : p.injured_days > 0 ? "Injured" : undefined}
          onClick={!p.is_regen && p.player_ref ? () => setOpen(p.player_ref) : undefined}
          stats={[{ k: "Morale", v: p.morale }, { k: "Mins", v: p.minutes }, { k: "Value", v: fmt(p.value_coin) }]} />
      ))}
      <PlayerDrawer playerId={open} onClose={() => setOpen(null)} />
    </div>
  );
}

function SquadTable({ club }: any) {
  const refresh = useRefreshOwner();
  const [mentality, setMentality] = useState(club.mentality);
  const [view, setView] = useState<"cards" | "table">("cards");
  const save = async (m: string) => {
    setMentality(m);
    await api.put(`/owner/clubs/${club.club_id}/mentality`, { mentality: m });
    refresh();
  };
  return (
    <Panel eyebrow={`${club.squad.length} players`} title="Squad" testid="squad-table-panel" className="lg:col-span-7"
      action={<div className="flex flex-wrap gap-1">{["cards", "table"].map((v) => <button key={v} data-testid={`squad-view-${v}`} onClick={() => setView(v as any)} className={`gx-btn ${view === v ? "gx-btn-primary" : "gx-btn-ghost"}`}>{v}</button>)}<span className="mx-1 w-px bg-white/10" />{["defensive", "balanced", "attacking"].map((m) => <button key={m} data-testid={`default-mentality-${m}`} onClick={() => save(m)} className={`gx-btn ${mentality === m ? "gx-btn-primary" : "gx-btn-secondary"}`}>{m}</button>)}</div>}>
      {view === "cards" ? <div className="gx-scroll max-h-[640px] overflow-auto pr-1"><SquadCards club={club} /></div> : (
      <div className="gx-scroll max-h-[560px] overflow-auto">
        <table className="gx-table w-full min-w-[620px]">
          <thead><tr><th>Player</th><th>Pos</th><th>Age</th><th>Rtg/Pot</th><th>Morale</th><th>Mins</th><th>Value</th></tr></thead>
          <tbody>
            {club.squad.map((p: any) => (
              <tr key={p.id} data-testid={`squad-row-${p.id}`}>
                <td className="font-medium text-white">{p.name} {p.is_regen && <Chip tone="emerald">Regen</Chip>} {p.status === "listed" && <Chip tone="gold">Listed</Chip>} {p.injured_days > 0 && <Chip tone="red">Injured</Chip>}</td>
                <td className="capitalize">{p.position}</td>
                <td className="gx-mono">{p.age}</td>
                <td className="gx-mono">{p.rating}<span className="text-slate-500">/{p.potential}</span></td>
                <td className="gx-mono">{p.morale}</td>
                <td className="gx-mono">{p.minutes}</td>
                <td className="gx-mono font-medium text-emerald-300">{fmt(p.value_coin)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      )}
    </Panel>
  );
}

export default function Squad() {
  const { active } = useActiveClub();
  const {
    data: club,
    isLoading,
    isError,
    refetch,
  } = useClub(active?.club_id);

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
        eyebrow="Tactics & roster"
        title={club.club_name}
        sub={`${club.squad.length} registered players · Wage bill ${fmt(club.wage_bill)} GTX / match`}
      />
      <div className="grid gap-6 lg:grid-cols-12">
        <ManagerSheet club={club} />
        <SquadTable club={club} />
        <HireManager club={club} />
      </div>
    </div>
  );
}
