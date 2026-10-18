import React, { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { useControlCenter, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Loading, PageHeader, Panel } from "@/components/gtex/ui";

function Standings({ rows, myIds }: any) {
  return (
    <div className="gx-scroll overflow-x-auto">
      <table className="gx-table w-full min-w-[560px]" data-testid="standings-table">
        <thead><tr><th>#</th><th>Club</th><th>P</th><th>W</th><th>D</th><th>L</th><th>GD</th><th>Pts</th></tr></thead>
        <tbody>
          {rows.map((r: any, i: number) => (
            <tr key={r.club_id} className={myIds.includes(r.club_id) ? "bg-emerald-500/[0.06]" : ""}>
              <td className="gx-mono text-slate-500">{r.final_position || i + 1}</td>
              <td className="font-medium text-white">{r.club_name} {r.is_ai && <span className="text-[10px] text-slate-500">AI</span>} {r.eliminated && <Chip tone="red">Out</Chip>}</td>
              <td className="gx-mono">{r.played}</td><td className="gx-mono">{r.won}</td><td className="gx-mono">{r.drawn}</td><td className="gx-mono">{r.lost}</td>
              <td className="gx-mono">{r.gf - r.ga}</td><td className="gx-mono font-bold text-emerald-300">{r.points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PlayPanel({ comp, clubId }: any) {
  const navigate = useNavigate();
  const refresh = useRefreshOwner();
  const [mentality, setMentality] = useState("balanced");
  const [lineup, setLineup] = useState("strongest");
  const [busy, setBusy] = useState(false);
  const next = comp.fixtures.find((m: any) => m.status === "scheduled" && [m.home_club_id, m.away_club_id].includes(clubId));
  const play = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/owner/competitions/${comp.id}/play-next`, { club_id: clubId, mentality, lineup_mode: lineup });
      refresh();
      navigate(`/app/match/${data.match.id}?club=${clubId}&live=1`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };
  const forfeit = async () => {
    if (!next || !window.confirm("Forfeiting costs a 0-3 loss, -3 points and an integrity flag. Continue?")) return;
    try {
      const { data } = await api.post(`/owner/matches/${next.id}/forfeit`, { club_id: clubId });
      toast.warning(data.penalty);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  if (comp.status === "finished") return <p className="text-sm text-slate-400">Competition finished. Prizes were paid to club treasuries via the ledger (held if under integrity review).</p>;
  return (
    <div data-testid="play-panel" className="space-y-4">
      <p className="text-sm text-slate-300">{next ? `Next: ${next.home_name} vs ${next.away_name} (Round ${next.round})` : comp.status === "open" ? "Kick-off fills remaining slots with AI clubs and generates the schedule." : "No fixture for your club this round."}</p>
      <div>
        <p className="gx-label">Mentality (light owner control)</p>
        <div className="flex gap-1">{["defensive", "balanced", "attacking"].map((m) => <button key={m} data-testid={`mentality-${m}`} onClick={() => setMentality(m)} className={`gx-btn ${mentality === m ? "gx-btn-primary" : "gx-btn-secondary"}`}>{m}</button>)}</div>
      </div>
      <div>
        <p className="gx-label">Lineup</p>
        <div className="flex gap-1">{["strongest", "rotate"].map((m) => <button key={m} data-testid={`lineup-${m}`} onClick={() => setLineup(m)} className={`gx-btn ${lineup === m ? "gx-btn-primary" : "gx-btn-secondary"}`}>{m}</button>)}</div>
        {lineup === "rotate" && comp.prize_sensitive && <p className="mt-2 text-xs text-amber-300">Rotating in a prize-sensitive competition is monitored. Repeated weakening (or against a sister club) triggers an integrity review.</p>}
      </div>
      <div className="flex gap-2">
        <Btn onClick={play} disabled={busy || (!next && comp.status !== "open")} data-testid="play-next-button">{busy ? "Simulating…" : "Play next match"}</Btn>
        {next && <Btn variant="danger" onClick={forfeit} data-testid="forfeit-button">Forfeit</Btn>}
      </div>
    </div>
  );
}

export default function CompetitionDetail() {
  const { id } = useParams();
  const { data: cc } = useControlCenter();
  const { data: comp, isLoading } = useQuery({ queryKey: ["competition", id], queryFn: async () => (await api.get(`/owner/competitions/${id}`)).data });
  if (isLoading || !comp) return <Loading />;
  const myIds = comp.my_club_ids || [];
  const myClub = myIds[0] || cc?.clubs?.[0]?.club_id;
  const rounds: Record<string, any[]> = {};
  comp.fixtures.forEach((m: any) => { (rounds[m.round] = rounds[m.round] || []).push(m); });
  return (
    <div data-testid="competition-detail-page" className="space-y-6">
      <PageHeader eyebrow={`${comp.host_type === "gtex" ? "GTEX-hosted" : "User-hosted"} · ${comp.format}`} title={comp.name} sub={comp.description}
        action={<div className="flex gap-4"><div><p className="text-[10px] uppercase text-slate-500">Prize pool</p><Coin amount={comp.prize_pool} /></div><div><p className="text-[10px] uppercase text-slate-500">Round</p><span className="gx-mono text-white">{comp.current_round}/{comp.total_rounds || "-"}</span></div></div>} />
      <div className="grid gap-6 lg:grid-cols-12">
        <Panel eyebrow="Table" title="Standings" className="lg:col-span-7" testid="standings-panel"><Standings rows={comp.standings} myIds={myIds} /></Panel>
        <Panel eyebrow="Pre-match" title="Owner decisions" className="lg:col-span-5" live testid="owner-match-panel">
          {myIds.length ? <PlayPanel comp={comp} clubId={myClub} /> : <p className="text-sm text-slate-400">You haven't entered this competition.</p>}
        </Panel>
        <Panel eyebrow="Schedule" title="Fixtures" className="lg:col-span-12" testid="fixtures-panel">
          <div className="grid gap-4 md:grid-cols-3">
            {Object.entries(rounds).map(([r, ms]) => (
              <div key={r}>
                <p className="gx-eyebrow mb-2">Round {r}</p>
                {ms.map((m: any) => (
                  <Link key={m.id} to={m.status === "scheduled" ? "#" : `/app/match/${m.id}?club=${myClub}`} className="mb-1 flex justify-between rounded-sm border border-white/5 px-3 py-2 text-sm hover:border-emerald-500/30" data-testid={`fixture-${m.id}`}>
                    <span className="truncate">{m.home_name} – {m.away_name}</span>
                    <span className="gx-mono text-emerald-300">{m.status === "scheduled" ? "vs" : `${m.home_goals}-${m.away_goals}`}</span>
                  </Link>
                ))}
              </div>
            ))}
            {comp.fixtures.length === 0 && <p className="text-sm text-slate-500">Schedule is generated at kick-off.</p>}
          </div>
        </Panel>
      </div>
    </div>
  );
}
