import React, { useState } from "react";
import { toast } from "sonner";
import { Sprout } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, label, useActiveClub, useClub, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, PageHeader, Panel, TraitBar } from "@/components/gtex/ui";

const TRAITS = ["ambition", "loyalty", "marketability", "professionalism", "adaptability", "growth_responsiveness", "environment_sensitivity"];

function RegenCard({ p }: any) {
  const t = p.personality || {};
  const last = p.growth_log?.[p.growth_log.length - 1];
  const pressure = t.transfer_pressure ?? 0;
  return (
    <div data-testid={`regen-card-${p.id}`} className="gx-rise rounded-sm border border-white/10 bg-slate-950/40 p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="gx-display text-xl font-bold uppercase text-white">{p.name}</p>
          <p className="text-xs capitalize text-slate-400">{p.position} · age {p.age}</p>
        </div>
        <div className="text-right">
          <p className="gx-mono text-2xl font-bold text-emerald-300">{p.rating}</p>
          <p className="gx-mono text-[10px] text-slate-500">POT {p.potential}</p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2.5">
        {TRAITS.map((k) => <TraitBar key={k} label={label(k)} value={t[k] ?? 0} />)}
        <TraitBar label="Transfer pressure" value={pressure} max={100} />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Chip tone={p.morale >= 65 ? "emerald" : "gold"}>Morale {p.morale}</Chip>
        <Chip>{p.minutes} mins</Chip>
        <Chip tone="blue">Value {fmt(p.value_coin)}</Chip>
        {pressure >= 60 && <Chip tone="red">Unsettled</Chip>}
      </div>
      {last && (
        <p className="mt-3 border-t border-white/5 pt-3 text-xs text-slate-400" data-testid="regen-growth-explanation">
          <span className="gx-mono mr-1 text-[10px] uppercase text-slate-500">Day {last.day}</span>+{last.gain} · {last.explanation}
        </p>
      )}
    </div>
  );
}

export default function Academy() {
  const { active } = useActiveClub();
  const { data: club, isLoading } = useClub(active?.club_id);
  const refresh = useRefreshOwner();
  const [busy, setBusy] = useState("");
  if (isLoading || !club) return <Loading />;
  const regens = club.squad.filter((p: any) => p.is_regen);
  const run = async (kind: string) => {
    setBusy(kind);
    try {
      if (kind === "intake") {
        const { data } = await api.post(`/owner/clubs/${club.club_id}/academy/intake`);
        toast.success(`${data.regens.length} new regens joined the academy`);
      } else {
        await api.post(`/owner/clubs/${club.club_id}/advance`);
        toast.success("World day advanced: growth applied");
      }
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy("");
    }
  };
  const academyLevel = club.facilities.academy.level;
  return (
    <div data-testid="academy-page">
      <PageHeader eyebrow="Academy / regens" title="The youth pipeline" sub="Regens grow from facilities, manager youth skill, playing time, competition quality, morale and club prestige. Ambitious regens left on the bench will push for a move."
        action={<div className="flex gap-2"><Btn variant="secondary" disabled={!!busy} onClick={() => run("advance")} data-testid="academy-advance-button">Advance world day</Btn><Btn disabled={!!busy} onClick={() => run("intake")} data-testid="academy-intake-button"><Sprout size={14} />Scout intake · {fmt(1500 * academyLevel)} GTX</Btn></div>} />
      <Panel className="mb-6" testid="growth-inputs">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5 text-sm">
          <div><p className="gx-label">Training</p><p className="gx-mono text-white">L{club.facilities.training.level}</p></div>
          <div><p className="gx-label">Academy</p><p className="gx-mono text-white">L{academyLevel}</p></div>
          <div><p className="gx-label">Manager youth skill</p><p className="gx-mono text-white">{club.manager_profile?.youth_development}/20</p></div>
          <div><p className="gx-label">Prestige</p><p className="gx-mono text-white">{club.health.prestige}</p></div>
          <div><p className="gx-label">Academy value</p><Coin amount={regens.reduce((s: number, p: any) => s + Number(p.value_coin), 0)} /></div>
        </div>
      </Panel>
      {regens.length === 0 ? <Empty title="No regens yet" body="Run a scouting intake to bring in your first academy prospects." /> : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{regens.map((p: any) => <RegenCard key={p.id} p={p} />)}</div>
      )}
    </div>
  );
}
