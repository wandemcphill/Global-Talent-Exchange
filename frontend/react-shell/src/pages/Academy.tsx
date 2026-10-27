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
        image={p.portrait_url}
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
  const dismissPack = () => {
    const next = Array.from(new Set([...readSeen(club.club_id), ...pack.map((p) => p.id)]));
    localStorage.setItem(seenKey(club.club_id), JSON.stringify(next));
    setPack([]);
  };
  const scoutIntake = async () => {
    setBusy("intake");
    try {
      const { data } = await api.post(`/owner/clubs/${club.club_id}/academy/intake`);
      toast.success(`Academy intake signed ${data.regens.length} new youth regens.`);
      setPack(data.regens);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy("");
    }
  };
  return (
    <div data-testid="academy-page">
      <PageHeader eyebrow="Regen incubator" title="Youth academy" sub="AI-generated regen players enter your academy. Facility levels decide the size and potential ceiling of your intake class."
        action={<Btn variant="primary" disabled={!!busy} onClick={scoutIntake} data-testid="scout-intake-button"><Sprout size={14} />{busy === "intake" ? "Signing…" : "Scout new intake"}</Btn>} />
      {pack.length > 0 && <PackReveal regens={pack} players={pack} onClose={dismissPack} onDismiss={dismissPack} />}
      <div className="space-y-4">
        {regens.length === 0 ? <Empty title="No academy players yet" body="Run an intake to discover new talent." /> : (
          <div className="grid gap-4 lg:grid-cols-2">
            {regens.map((p: any) => <RegenCard key={p.id} p={p} />)}
          </div>
        )}
      </div>
    </div>
  );
}
