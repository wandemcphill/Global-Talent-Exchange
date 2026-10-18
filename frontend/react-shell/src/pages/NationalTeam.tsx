import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Flag, Wand2 } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, label, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, PageHeader, Panel } from "@/components/gtex/ui";
import { PlayerCard } from "@/components/gtex/PlayerCard";

const BASE = "/national-team-engine";
const COUNTRIES = [["NG", "Nigeria"], ["GH", "Ghana"], ["SN", "Senegal"], ["CM", "Cameroon"], ["CI", "Côte d'Ivoire"], ["EG", "Egypt"], ["MA", "Morocco"], ["ZA", "South Africa"], ["BR", "Brazil"], ["AR", "Argentina"], ["FR", "France"], ["GB", "England"], ["ES", "Spain"], ["DE", "Germany"], ["PT", "Portugal"]];
const POSITIONS = ["", "goalkeeper", "defender", "midfielder", "forward"];

function EnterForm({ comp, onDone }: any) {
  const [code, setCode] = useState("NG");
  const enter = async () => {
    const name = COUNTRIES.find((c) => c[0] === code)?.[1];
    try {
      await api.post(`${BASE}/competitions/${comp.id}/rental-entry`, { country_code: code, country_name: name });
      toast.success(`You now manage ${name} in ${comp.title}`);
      onDone();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <div className="flex flex-wrap items-end gap-3" data-testid="national-enter-form">
      <div><p className="gx-label mb-1">Nation</p>
        <select data-testid="national-country-select" className="gx-input" value={code} onChange={(e) => setCode(e.target.value)}>
          {COUNTRIES.map(([c, n]) => <option key={c} value={c}>{n}</option>)}
        </select>
      </div>
      <Btn onClick={enter} data-testid="national-enter-button"><Flag size={14} />Take charge of the national team</Btn>
    </div>
  );
}

function RentCard({ p, entry, onRented }: any) {
  const [busy, setBusy] = useState(false);
  const ok = p.eligibility?.eligible !== false;
  const rent = async () => {
    setBusy(true);
    try {
      await api.post(`${BASE}/entries/${entry.id}/rentals`, { player_id: p.player_id });
      toast.success(`${p.player_name} rented for the tournament`);
      onRented();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <PlayerCard testid={`rental-card-${p.player_id}`} name={p.player_name} rating={p.overall_rating} position={p.primary_position} age={p.age} nationality={p.nationality} club={p.current_club_name} image={p.image_url || p.portrait_url} regen={p.is_regen}
      badge={p.tier_label} stats={[{ k: "Loan", v: fmt(p.loan_price_coin, 1) }, { k: "GSI", v: p.gsi }, { k: "Value", v: fmt(p.base_value_coin, 0) }]}
      footer={<Btn className="w-full justify-center" variant="secondary" disabled={busy || !ok} title={ok ? "" : (p.eligibility?.reasons || []).join(", ")} onClick={rent} data-testid={`rent-player-${p.player_id}`}>{!ok ? label(p.eligibility?.reasons?.[0] || "not eligible") : busy ? "Renting…" : <>Rent · <Coin amount={p.loan_price_coin} /></>}</Btn>} />
  );
}

function RentalPool({ comp, entry, onRented }: any) {
  const [position, setPosition] = useState("");
  const [nationOnly, setNationOnly] = useState(true);
  const [limit, setLimit] = useState(12);
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["rental-pool", comp.id, entry.id, position, nationOnly, limit],
    queryFn: async () => (await api.get(`${BASE}/competitions/${comp.id}/rental-pool`, { params: { limit, entry_id: entry.id, ...(nationOnly ? { country_code: entry.country_code } : {}), ...(position ? { position } : {}) } })).data,
    placeholderData: (prev: any) => prev,
  });
  return (
    <Panel eyebrow={`${fmt(data?.total)} players available`} title="Rental pool" testid="rental-pool-panel"
      action={<div className="flex flex-wrap gap-1">
        <button data-testid="rental-nation-toggle" onClick={() => setNationOnly(!nationOnly)} className={`gx-btn ${nationOnly ? "gx-btn-primary" : "gx-btn-secondary"}`}>{nationOnly ? `${entry.country_name} only` : "All nations"}</button>
        {POSITIONS.map((p) => <button key={p || "all"} data-testid={`rental-filter-${p || "all"}`} onClick={() => setPosition(p)} className={`gx-btn capitalize ${position === p ? "gx-btn-primary" : "gx-btn-ghost"}`}>{p || "All"}</button>)}
      </div>}>
      {isLoading ? <Loading label="Calling up players" /> : !data?.items?.length ? <Empty title="No players in this pool" body="Try all nations or another position." /> : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">{data.items.map((p: any) => <RentCard key={p.player_id} p={p} entry={entry} onRented={onRented} />)}</div>
      )}
      {data && data.total > data.items.length && <div className="mt-5 text-center"><Btn variant="secondary" disabled={isFetching} onClick={() => setLimit(limit + 12)} data-testid="rental-load-more">{isFetching ? "Scouting…" : "Load more players"}</Btn></div>}
    </Panel>
  );
}

function AutoBuild({ comp, entry }: any) {
  const [budget, setBudget] = useState("500");
  const [plan, setPlan] = useState<any>(null);
  const run = async () => {
    try {
      setPlan((await api.post(`${BASE}/competitions/${comp.id}/auto-build-squad`, { country_code: entry.country_code, budget_coin: Number(budget) })).data);
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <Panel eyebrow="AI scout" title="Auto-build a squad" testid="auto-build-panel" className="lg:col-span-5">
      <div className="flex gap-2"><input data-testid="auto-build-budget" className="gx-input w-32" value={budget} onChange={(e) => setBudget(e.target.value.replace(/[^\d.]/g, ""))} /><Btn variant="secondary" onClick={run} data-testid="auto-build-button"><Wand2 size={14} />Suggest squad</Btn></div>
      {plan && (
        <div className="mt-4 text-sm" data-testid="auto-build-result">
          <p className="text-slate-300">{plan.formation} · {plan.selected_count}/{plan.squad_size} picked · cost <Coin amount={plan.total_cost_coin} /> · left <Coin amount={plan.remaining_budget_coin} /></p>
          <ul className="gx-scroll mt-3 max-h-64 space-y-1 overflow-auto">{plan.players.map((p: any) => <li key={p.player_id} className="flex justify-between border-b border-white/5 py-1 text-xs"><span className="text-white">{p.assigned_slot} · {p.player_name}</span><span className="gx-mono text-slate-400">{p.overall_rating} · {fmt(p.loan_price_coin, 1)}</span></li>)}</ul>
        </div>
      )}
    </Panel>
  );
}

function EntryRoster({ entryId, refreshKey }: any) {
  const { data: e, refetch } = useQuery({ queryKey: ["national-entry", entryId, refreshKey], queryFn: async () => (await api.get(`${BASE}/entries/${entryId}`)).data });
  if (!e) return <Loading />;
  const roster = e.rental_squad_members || [];
  const claim = async () => {
    try {
      await api.post(`${BASE}/entries/${entryId}/free-players/claim`);
      toast.success("Free players claimed");
      refetch();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };
  return (
    <Panel eyebrow={`${e.country_name} · ${roster.length}/${e.minimum_squad_size} minimum`} title="Your national squad" testid="national-roster-panel" className="lg:col-span-7"
      action={e.free_players_remaining > 0 && <Btn variant="gold" onClick={claim} data-testid="claim-free-players">Claim {e.free_players_remaining} free players</Btn>}>
      <div className="mb-4 h-1.5 rounded-sm bg-white/5"><div className="h-1.5 rounded-sm bg-emerald-400 transition-[width] duration-700" style={{ width: `${Math.min(100, (roster.length / e.minimum_squad_size) * 100)}%` }} /></div>
      {roster.length === 0 ? <Empty title="No players yet" body="Rent players from the pool below or claim your free picks." /> : (
        <div className="grid gap-2 sm:grid-cols-2">{roster.map((m: any) => (
          <div key={m.id} data-testid={`roster-${m.player_id}`} className="flex items-center justify-between rounded-sm border border-white/10 px-3 py-2 text-sm">
            <span className="text-white">{m.shirt_number ? `#${m.shirt_number} ` : ""}{m.player_name}</span>
            <span className="flex items-center gap-2"><Chip tone={m.source_type === "free" ? "gold" : "cyan"}>{label(m.source_type)}</Chip><span className="gx-mono text-emerald-300">{m.overall_rating}</span></span>
          </div>
        ))}</div>
      )}
    </Panel>
  );
}

export default function NationalTeam() {
  const { user } = useAuth();
  const isAdmin = ["admin", "super_admin"].includes(String(user?.role).toLowerCase());
  const [selected, setSelected] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const qc = useQueryClient();
  const refreshOwner = useRefreshOwner();
  const onRented = () => {
    setTick((t) => t + 1);
    refreshOwner();
    qc.invalidateQueries({ queryKey: ["rental-pool"] });
  };
  const comps = useQuery({ queryKey: ["national-comps"], queryFn: async () => (await api.get(`${BASE}/competitions`)).data });
  const history = useQuery({ queryKey: ["national-history", tick], queryFn: async () => (await api.get(`${BASE}/me/history`)).data });
  const list: any[] = comps.data || [];
  const managed: any[] = history.data?.managed_entries || [];
  const comp = list.find((c) => c.id === selected) || list.find((c) => managed.some((e) => e.competition_id === c.id)) || list[0];
  const entry = managed.find((e: any) => e.competition_id === comp?.id);
  const seed = async () => {
    try {
      await api.post(`/admin${BASE}/competitions/seed-defaults`);
      toast.success("Default national tournaments seeded");
      comps.refetch();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <div data-testid="national-team-page" className="space-y-6">
      <PageHeader eyebrow="International duty" title="National team rentals" sub="Take charge of a nation for a tournament, rent real players and regens on time-limited loans, and pay the loan fee from your GTEX wallet."
        action={isAdmin && <Btn variant="secondary" onClick={seed} data-testid="seed-national-competitions">Seed default tournaments</Btn>} />
      {comps.isLoading ? <Loading /> : list.length === 0 ? <Empty testid="national-empty" title="No national tournaments open" body={isAdmin ? "Seed the default tournaments to open rentals." : "An admin hasn't opened a national tournament yet. Check back soon."} /> : (
        <>
          <div className="gx-scroll flex gap-2 overflow-x-auto" data-testid="national-comp-tabs">
            {list.map((c) => <button key={c.id} data-testid={`national-comp-${c.key}`} onClick={() => setSelected(c.id)} className={`gx-btn whitespace-nowrap ${comp?.id === c.id ? "gx-btn-primary" : "gx-btn-secondary"}`}>{c.title}<span className="ml-1 text-[10px] opacity-70">{label(c.status)}</span></button>)}
          </div>
          {comp && !entry && <Panel eyebrow={`${comp.season_label} · ${label(comp.format_type)} · ${label(comp.age_band)}`} title={comp.title} testid="national-comp-panel"><EnterForm comp={comp} onDone={() => setTick(tick + 1)} /></Panel>}
          {comp && entry && (
            <>
              <div className="grid gap-6 lg:grid-cols-12">
                <EntryRoster entryId={entry.id} refreshKey={tick} />
                <AutoBuild comp={comp} entry={entry} />
              </div>
              <RentalPool comp={comp} entry={entry} onRented={onRented} />
            </>
          )}
        </>
      )}
    </div>
  );
}
