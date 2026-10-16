import React, { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { ArrowDownRight, ArrowUpRight, FastForward, Radio } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, label, useControlCenter, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, Panel, Stat } from "@/components/gtex/ui";
import { InboxItem } from "@/components/gtex/InboxItem";

function FixturesRail({ fx }: any) {
  const cards = [...(fx.upcoming || []).map((m: any) => ({ ...m, kind: "Next" })), ...(fx.recent || []).map((m: any) => ({ ...m, kind: "Result" }))];
  return (
    <Panel eyebrow="Competition & fixtures rail" title="Matchday" testid="block-fixtures" live={fx.upcoming?.length > 0} action={<Link to="/app/competitions" className="gx-btn gx-btn-ghost" data-testid="fixtures-view-all">All competitions</Link>}>
      <div className="gx-scroll flex gap-3 overflow-x-auto pb-2">
        {cards.length === 0 && <Empty title="No fixtures yet" body="Enter a competition to get a schedule." action={<Link className="gx-btn gx-btn-primary" to="/app/competitions">Find a competition</Link>} />}
        {cards.map((m: any) => (
          <Link key={m.id} to={m.status === "scheduled" ? `/app/competitions/${m.competition_id}` : `/app/match/${m.id}`} data-testid={`fixture-card-${m.id}`} className="min-w-[230px] rounded-sm border border-white/10 bg-slate-950/50 p-4 transition-colors hover:border-emerald-500/40">
            <div className="flex items-center justify-between">
              <Chip tone={m.kind === "Next" ? "emerald" : "slate"}>{m.kind === "Next" ? <><Radio size={10} className="gx-live-dot" /> Round {m.round}</> : `Round ${m.round}`}</Chip>
            </div>
            <p className="mt-3 truncate text-sm text-white">{m.home_name}</p>
            <p className="truncate text-sm text-white">{m.away_name}</p>
            <p className="gx-mono mt-2 text-lg font-bold text-emerald-300">{m.status === "scheduled" ? "vs" : `${m.home_goals} – ${m.away_goals}`}</p>
          </Link>
        ))}
        {(fx.open_competitions || []).filter((c: any) => !c.my_club_ids?.length).slice(0, 2).map((c: any) => (
          <Link key={c.id} to="/app/competitions" className="min-w-[230px] rounded-sm border border-dashed border-cyan-500/30 p-4 hover:border-cyan-400/60">
            <Chip tone="cyan">Open entry</Chip>
            <p className="mt-3 text-sm font-semibold text-white">{c.name}</p>
            <p className="mt-1 text-xs text-slate-400">Pool <Coin amount={c.prize_pool} /></p>
          </Link>
        ))}
      </div>
    </Panel>
  );
}

function ClubsBlock({ data }: any) {
  return (
    <Panel eyebrow={`My clubs · ${data.clubs.length}/${data.max_clubs}`} title="Club portfolio" testid="block-my-clubs" className="lg:col-span-8"
      action={data.ownership_group && <Chip tone="gold" testid="ownership-group-label">{data.ownership_group.label}</Chip>}>
      <div className="grid gap-3 md:grid-cols-3">
        {data.clubs.map((c: any) => {
          const up = Number(c.value_trend) >= 0;
          return (
            <Link to="/app/clubs" key={c.club_id} data-testid={`club-card-${c.club_id}`} className="rounded-sm border border-white/10 bg-slate-950/40 p-4 transition-colors hover:border-emerald-500/40">
              <div className="flex items-center gap-3">
                <span className="gx-display flex h-10 w-10 items-center justify-center rounded-sm text-sm font-black" style={{ background: c.primary_color, color: c.secondary_color }}>{(c.short_name || c.club_name).slice(0, 3).toUpperCase()}</span>
                <div className="min-w-0">
                  <p className="truncate font-semibold text-white">{c.club_name}</p>
                  <p className="text-xs text-slate-500">{c.competition?.name || "No active competition"}</p>
                </div>
              </div>
              <div className="mt-4 flex items-end justify-between">
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-slate-500">Club value</p>
                  <Coin amount={c.value} className="text-lg" />
                </div>
                <span className={`gx-mono flex items-center text-xs ${up ? "text-emerald-400" : "text-red-400"}`}>{up ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}{fmt(c.value_trend)}</span>
              </div>
              <div className="mt-3 flex items-center justify-between text-xs">
                <span className="text-slate-400">{c.manager?.name}</span>
                <Chip tone={(c.manager?.mood ?? 70) >= 60 ? "emerald" : (c.manager?.mood ?? 70) >= 40 ? "gold" : "red"}>Mood {c.manager?.mood ?? "-"}</Chip>
              </div>
            </Link>
          );
        })}
        {data.clubs.length < data.max_clubs && (
          <Link to="/app/clubs" data-testid="add-club-link" className="flex min-h-[160px] items-center justify-center rounded-sm border border-dashed border-white/10 text-sm text-slate-500 hover:border-emerald-500/40 hover:text-white">+ Add a club</Link>
        )}
      </div>
    </Panel>
  );
}

function EconomyBlock({ econ }: any) {
  const w = econ.wallet;
  const sources = Object.entries(econ.earnings_sources || {}).filter(([, v]: any) => Number(v) > 0);
  return (
    <Panel eyebrow="Club economy snapshot" title="Money" testid="block-economy" className="lg:col-span-4" action={<Link to="/app/finance" className="gx-btn gx-btn-ghost">Ledger</Link>}>
      <div className="grid grid-cols-2 gap-4">
        <Stat label="Club cash" value={<Coin amount={econ.club_cash_total} />} testid="econ-club-cash" />
        <Stat label="Withdrawable" value={<Coin amount={w.withdrawable} />} testid="econ-withdrawable" />
        <Stat label="Pending payouts" value={<Coin amount={econ.pending_payouts} />} />
        <Stat label="Gifts received" value={<Coin amount={econ.gifts_received_fan_coin} currency="FAN" />} />
      </div>
      <div className="mt-5 space-y-1.5 border-t border-white/5 pt-4">
        <p className="text-[10px] uppercase tracking-widest text-slate-500">Earnings sources (net)</p>
        {sources.length === 0 && <p className="text-xs text-slate-500">No earnings yet. Play home matches and sign sponsors.</p>}
        {sources.map(([k, v]: any) => (
          <div key={k} className="flex justify-between text-sm"><span className="capitalize text-slate-400">{label(k)}</span><Coin amount={v} /></div>
        ))}
      </div>
    </Panel>
  );
}

function HealthBlock({ health }: any) {
  return (
    <Panel eyebrow="Live club health" title="Vitals" testid="block-health" className="lg:col-span-3">
      <div className="space-y-5">
        {health.map((h: any) => (
          <div key={h.club_id} data-testid={`health-${h.club_id}`}>
            <p className="mb-2 text-sm font-semibold text-white">{h.club_name}</p>
            <div className="grid grid-cols-2 gap-3">
              <Stat label="Cash" value={<Coin amount={h.cash} />} />
              <Stat label="Squad depth" value={`${h.squad_size} · ${h.squad_depth}`} tone={h.squad_depth === "thin" ? "warn" : "good"} />
              <Stat label="Morale" value={h.morale} tone={h.morale >= 65 ? "good" : h.morale >= 45 ? "warn" : "bad"} />
              <Stat label="Injuries" value={h.injuries} tone={h.injuries ? "warn" : "good"} />
              <Stat label="Academy output" value={`${h.academy_output}/${h.academy_players}`} hint="regens rated 60+" />
              <Stat label="Fan engagement" value={`${h.fan_engagement}%`} hint={`${fmt(h.fans)} fans`} />
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

export default function ControlCenter() {
  const { data, isLoading } = useControlCenter();
  const refresh = useRefreshOwner();
  const [busy, setBusy] = useState(false);
  if (isLoading || !data) return <Loading label="Loading Owner Control Center" />;
  const advance = async () => {
    setBusy(true);
    try {
      for (const c of data.clubs) await api.post(`/owner/clubs/${c.club_id}/advance`);
      toast.success("A new world day: growth applied, new events in your inbox.");
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div data-testid="control-center-page" className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="gx-eyebrow mb-2">Owner Control Center · World day {data.clubs[0]?.world_day ?? 0}</p>
          <h1 className="gx-h2">Good to see you, {data.user.display_name || data.user.username}.</h1>
          <p className="mt-1 text-sm text-slate-400">{data.decisions.length} decisions waiting. Integrity score {data.integrity.score}/100.</p>
        </div>
        <Btn variant="secondary" onClick={advance} disabled={busy} data-testid="advance-world-day-button"><FastForward size={14} />{busy ? "Simulating…" : "Advance world day"}</Btn>
      </div>
      <FixturesRail fx={data.fixtures} />
      <div className="grid gap-6 lg:grid-cols-12">
        <ClubsBlock data={data} />
        <EconomyBlock econ={data.economy} />
        <Panel eyebrow="Today's decisions" title="Board table" testid="block-decisions" className="lg:col-span-5">
          <div className="space-y-3">
            {data.decisions.length === 0 && <Empty title="All clear" body="No decisions pending. Advance the world day to see what happens next." />}
            {data.decisions.map((i: any) => <InboxItem key={i.id} item={i} />)}
          </div>
        </Panel>
        <Panel eyebrow="Owner inbox" title="Latest" testid="block-inbox" className="lg:col-span-4" action={<Link to="/app/inbox" className="gx-btn gx-btn-ghost" data-testid="inbox-view-all">Open inbox ({data.inbox_open_count})</Link>}>
          <div className="space-y-3">
            {data.inbox.length === 0 && <Empty title="Inbox empty" />}
            {data.inbox.slice(0, 5).map((i: any) => <InboxItem key={i.id} item={i} compact />)}
          </div>
        </Panel>
        <HealthBlock health={data.health} />
      </div>
    </div>
  );
}
