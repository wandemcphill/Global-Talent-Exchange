import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { fmt, useActiveClub, useClub, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, PageHeader, Panel } from "@/components/gtex/ui";
import { MarketTable } from "@/components/gtex/MarketTable";
import { ShareMarket } from "@/components/gtex/ShareMarket";

function SisterTransfer({ clubs, club }: any) {
  const refresh = useRefreshOwner();
  const [playerId, setPlayerId] = useState("");
  const [to, setTo] = useState("");
  const [fee, setFee] = useState("");
  const [check, setCheck] = useState<any>(null);
  const body = () => ({ player_id: playerId, to_club_id: to, fee: Number(fee || 0) });
  const runCheck = async () => {
    try {
      setCheck((await api.post("/owner/transfers/internal/check", body())).data);
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  const execute = async () => {
    try {
      const { data } = await api.post("/owner/transfers/internal", body());
      toast.success(`Transfer complete. ${data.notes.join(" ")}`);
      setCheck(null);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  const sisters = clubs.filter((c: any) => c.club_id !== club?.club_id);
  if (!sisters.length) return <p className="text-sm text-slate-500">Own a second club to move players between sister clubs. Related-party rules apply: no free transfers, fee within 80–130% of fair value, 14-day reciprocal cooldown, and repeated shuffling is flagged.</p>;
  return (
    <div className="grid gap-4 md:grid-cols-4" data-testid="sister-transfer-form">
      <select data-testid="sister-player-select" className="gx-input md:col-span-2" value={playerId} onChange={(e) => { setPlayerId(e.target.value); setCheck(null); }}>
        <option value="">Select player from {club?.club_name}</option>
        {(club?.squad || []).map((p: any) => <option key={p.id} value={p.id}>{p.name} · value {fmt(p.value_coin)}</option>)}
      </select>
      <select data-testid="sister-target-select" className="gx-input" value={to} onChange={(e) => { setTo(e.target.value); setCheck(null); }}>
        <option value="">To club</option>
        {sisters.map((s: any) => <option key={s.club_id} value={s.club_id}>{s.club_name}</option>)}
      </select>
      <input data-testid="sister-fee-input" className="gx-input" placeholder="Fee (GTX)" value={fee} onChange={(e) => { setFee(e.target.value); setCheck(null); }} />
      <div className="flex gap-2 md:col-span-4">
        <Btn variant="secondary" disabled={!playerId || !to} onClick={runCheck} data-testid="sister-check-button">Check fair-value rules</Btn>
        <Btn disabled={!check?.allowed} onClick={execute} data-testid="sister-execute-button">Execute transfer</Btn>
      </div>
      {check && (
        <div className="md:col-span-4 rounded-sm border border-white/10 p-4 text-sm" data-testid="sister-check-result">
          <p className="mb-2 text-slate-300">Fair value {fmt(check.fair_value)} · allowed band {fmt(check.band[0])}–{fmt(check.band[1])}</p>
          <div className="flex flex-wrap gap-2">{Object.entries(check.rules).map(([k, v]: any) => <Chip key={k} tone={v ? "emerald" : "red"}>{k.replace(/_/g, " ")}</Chip>)}</div>
          {check.shuffle_flag_risk && <p className="mt-2 text-amber-300">Warning: this would be a repeated related-party move. It will be flagged and the player's morale will drop.</p>}
        </div>
      )}
    </div>
  );
}

export default function Market() {
  const [params] = useSearchParams();
  const { clubs, active } = useActiveClub();
  const { data: club, refetch } = useClub(active?.club_id);
  const position = params.get("position") || "";
  return (
    <div data-testid="market-page" className="space-y-6">
      <PageHeader eyebrow="Market & transfers" title="Build the squad" sub={`Signing for ${active?.club_name || "-"}. Fees are paid from club cash and recorded on the unified ledger. Club cash: ${fmt(club?.economy?.cash_gtex)} GTX.`} />
      {position && <Chip tone="cyan" testid="manager-request-filter">Manager request: {position}</Chip>}
      <Panel eyebrow="World market · live player universe" title="Available players" testid="world-market-panel">
        <MarketTable clubId={active?.club_id} initialPosition={position} signedRefs={(club?.squad || []).map((p: any) => p.player_ref)} onSigned={() => refetch()} />
      </Panel>
      <Panel eyebrow="Player share market · live" title="Issued player markets" testid="share-market-panel">
        <ShareMarket />
      </Panel>
      <Panel eyebrow="Related-party · anti-collusion" title="Sister-club transfer" testid="sister-transfer-panel">
        <SisterTransfer clubs={clubs} club={club} />
      </Panel>
    </div>
  );
}
