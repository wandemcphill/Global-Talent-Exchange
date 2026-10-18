import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Sprout } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, label, useActiveClub, useClub, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, PageHeader, Panel, TraitBar } from "@/components/gtex/ui";
import { PlayerCard } from "@/components/gtex/PlayerCard";
import { PackReveal } from "@/components/gtex/PackReveal";

const seenKey = (clubId: string) => `gtex.regens.seen.${clubId}`;
const readSeen = (clubId: string): string[] => JSON.parse(localStorage.getItem(seenKey(clubId)) || "[]");

const TRAITS = ["ambition", "loyalty", "marketability", "professionalism", "adaptability", "growth_responsiveness", "environment_sensitivity"];

function RegenCard({ p }: any) {
  const t = p.personality || {};
  const last = p.growth_log?.[p.growth_log.length - 1];
  const pressure = t.transfer_pressure ?? 0;
  const ceiling = Math.max(0, (p.potential || 0) - (p.rating || 0));
  const totalGain = (p.growth_log || []).reduce((s: number, g: any) => s + Number(g.gain || 0), 0);
  return (
    <div data-testid={`regen-card-${p.id}`} className="grid gap-4 rounded-md border border-white/10 bg-slate-950/40 p-4 sm:grid-cols-[180px_1fr]">
      <PlayerCard name={p.name} rating={p.rating} potential={p.potential} position={p.position} age={p.age} regen
        badge={pressure >= 60 ? "Unsettled" : ceiling >= 15 ? "Wonderkid" : "Academy"}
        stats={[{ k: "Ceiling", v: `+${ceiling}` }, { k: "Morale", v: p.morale }, { k: "Value", v: fmt(p.value_coin) }]} />
      <div className="min-w-0">
        <div className="mb-3 h-1.5 rounded-sm bg-white/5" title="Progress to potential">
          <div className="h-1.5 rounded-sm bg-gradient-to-r from-emerald-500 to-cyan-400 transition-[width] duration-700" style={{ width: `${Math.min(100, (p.rating / Math.max(1, p.potential)) * 100)}%` }} />
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
          {TRAITS.map((k) => <TraitBar key={k} label={label(k)} value={t[k] ?? 0} />)}
          <TraitBar label="Transfer pressure" value={pressure} max={100} />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Chip>{p.minutes} mins</Chip>
          {totalGain > 0 && <Chip tone="emerald">+{totalGain} recent growth</Chip>}
          {pressure >= 60 && <Chip tone="red">Wants game time</Chip>}
        </div>
        {last && (
          <p className="mt-3 border-t border-white/5 pt-3 text-xs text-slate-400" data-testid="regen-growth-explanation">
            <span className="gx-mono mr-1 text-[10px] uppercase text-slate-500">Day {last.day}</span>+{last.gain} · {last.explanation}
          </p>
        )}
      </div>
    </div>
  );
}

export default function Academy() {
  const { active } = useActiveClub();
  const { data: club, isLoading } = useClub(active?.club_id);
  const refresh = useRefreshOwner();
  const [busy, setBusy] = useState("");
  const [pack, setPack] = useState<any[]>([]);
  useEffect(() => {
    if (!club) {
      return;
    }
    const seen = new Set(readSeen(club.club_id));
    setPack(club.squad.filter((p: any) => p.is_regen && !seen.has(p.id)));
  }, [club]);
  if (isLoading || !club) return <Loading />;
  const regens = club.squad.filter((p: any) => p.is_regen);
  const closePack = () => {
    localStorage.setItem(seenKey(club.club_id), JSON.stringify(Array.from(new Set([...readSeen(club.club_id), ...regens.map((r: any) => r.id)]))));
    setPack([]);
  };
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
      {pack.length > 0 && <PackReveal regens={pack} onClose={closePack} />}
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
        <div className="grid gap-4 xl:grid-cols-2">{regens.map((p: any) => <RegenCard key={p.id} p={p} />)}</div>
      )}
    </div>
  );
}
