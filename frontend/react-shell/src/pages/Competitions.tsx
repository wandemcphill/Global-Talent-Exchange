import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { useActiveClub, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, PageHeader, Panel } from "@/components/gtex/ui";

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

export default function Competitions() {
  const { active } = useActiveClub();
  const { data, isLoading } = useQuery({ queryKey: ["competitions"], queryFn: async () => (await api.get("/owner/competitions")).data.competitions });
  const gtex = (data || []).filter((c: any) => c.host_type === "gtex");
  const user = (data || []).filter((c: any) => c.host_type === "user");
  return (
    <div data-testid="competitions-page" className="space-y-6">
      <PageHeader eyebrow="Competitions" title="Where prestige is earned" sub={`Entering as ${active?.club_name || "-"}. Same-owner clubs can't share a prize-sensitive bracket and are routed apart in knockouts.`} />
      {isLoading ? <Loading /> : (
        <>
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
        </>
      )}
    </div>
  );
}
