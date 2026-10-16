import React, { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Check } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, useClub } from "@/lib/owner";
import { Btn, Chip, Coin, Loading, Panel } from "@/components/gtex/ui";
import { MarketTable } from "@/components/gtex/MarketTable";

const STEPS = [
  { key: "identity", label: "Club identity" },
  { key: "squad", label: "Sign starting squad" },
  { key: "manager", label: "Appoint manager" },
  { key: "competition", label: "First competition" },
];

function Stepper({ index }: any) {
  return (
    <ol className="mb-10 grid grid-cols-2 gap-2 md:grid-cols-4" data-testid="onboarding-stepper">
      {STEPS.map((s, i) => (
        <li key={s.key} className={`rounded-sm border p-3 ${i === index ? "border-emerald-500/50 bg-emerald-500/10" : i < index ? "border-white/10 bg-white/[0.02]" : "border-white/[0.05]"}`}>
          <p className="gx-mono text-[10px] text-slate-500">STEP {i + 1}</p>
          <p className="flex items-center gap-2 text-sm font-semibold text-white">{i < index && <Check size={14} className="text-emerald-400" />}{s.label}</p>
        </li>
      ))}
    </ol>
  );
}

function IdentityStep({ club, onDone }: any) {
  const [busy, setBusy] = useState(false);
  const activate = async () => {
    setBusy(true);
    try {
      await api.post(`/owner/clubs/${club.club_id}/activate`);
      onDone();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Panel eyebrow="Step 1" title={`Confirm ${club.club_name}`} testid="onboarding-identity-step">
      <p className="max-w-xl text-sm text-slate-300">Your club identity is registered. Activating it unlocks a <b className="text-white">100,000 GTEX Coin launch grant</b> in the club treasury (promotional: usable for signings and facilities, not withdrawable) plus 1,000 Fan Coin for gifting.</p>
      <Btn className="mt-6" onClick={activate} disabled={busy} data-testid="onboarding-activate-button">{busy ? "Activating…" : "Activate club"}</Btn>
    </Panel>
  );
}

function SquadStep({ clubId, onDone }: any) {
  const { data: club, refetch } = useClub(clubId);
  const squad = club?.squad?.filter((p: any) => !p.is_regen) || [];
  const hasGk = squad.some((p: any) => p.position.startsWith("goal"));
  useEffect(() => {
    if (club?.stage && club.stage !== "squad") onDone();
  }, [club?.stage, onDone]);
  return (
    <Panel eyebrow="Step 2 · Activate by acquiring players" title="Sign your starting squad" testid="onboarding-squad-step"
      action={<div className="text-right"><p className="text-[10px] uppercase tracking-widest text-slate-500">Club cash</p><Coin amount={club?.economy?.cash_gtex} testid="onboarding-cash" /></div>}>
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <Chip tone={squad.length >= 11 ? "emerald" : "gold"} testid="onboarding-squad-count">{squad.length}/11 players</Chip>
        <Chip tone={hasGk ? "emerald" : "red"}>{hasGk ? "Goalkeeper signed" : "Needs a goalkeeper"}</Chip>
        <span className="text-xs text-slate-500">Why: a club becomes match-eligible with 11 players including a goalkeeper.</span>
      </div>
      <MarketTable clubId={clubId} signedRefs={squad.map((p: any) => p.player_ref)} onSigned={() => refetch()} />
    </Panel>
  );
}

function ManagerStep({ clubId, onDone }: any) {
  const { data } = useQuery({ queryKey: ["mgr-catalog"], queryFn: async () => (await api.get("/managers/catalog", { params: { limit: 3 } })).data.items });
  const [busy, setBusy] = useState<string | null>(null);
  const appoint = async (m: any | null) => {
    setBusy(m?.manager_id || "default");
    try {
      await api.post(`/owner/clubs/${clubId}/manager`, { manager: m ? { manager_id: m.manager_id, display_name: m.display_name, rarity: m.rarity, mentality: m.mentality, tactics: m.tactics, traits: m.traits, philosophy_summary: m.philosophy_summary } : null });
      onDone();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(null);
    }
  };
  return (
    <Panel eyebrow="Step 3 · Hire your football brain" title="Appoint a manager" testid="onboarding-manager-step">
      <p className="mb-6 text-sm text-slate-400">Managers carry the realism: they ask for budget, request players, react to facilities, and shape regen growth. First appointment is covered by the launch package.</p>
      <div className="grid gap-4 md:grid-cols-4">
        {(data || []).map((m: any) => (
          <div key={m.manager_id} className="flex flex-col rounded-sm border border-white/10 bg-slate-950/50 p-4">
            <Chip tone="cyan">{m.rarity}</Chip>
            <p className="gx-display mt-3 text-xl font-bold uppercase text-white">{m.display_name}</p>
            <p className="text-xs capitalize text-slate-400">{m.mentality} · {(m.tactics || []).slice(0, 2).join(", ").replace(/_/g, " ")}</p>
            <p className="mt-3 flex-1 text-xs text-slate-500">{m.philosophy_summary}</p>
            <Btn className="mt-4" variant="secondary" disabled={!!busy} onClick={() => appoint(m)} data-testid={`appoint-manager-${m.manager_id}`}>{busy === m.manager_id ? "…" : "Appoint"}</Btn>
          </div>
        ))}
        <div className="flex flex-col rounded-sm border border-dashed border-white/10 p-4">
          <Chip>Default</Chip>
          <p className="gx-display mt-3 text-xl font-bold uppercase text-white">GTEX staff coach</p>
          <p className="mt-3 flex-1 text-xs text-slate-500">A steady default manager. You can hire a named manager later from Manager & Squad.</p>
          <Btn className="mt-4" variant="ghost" disabled={!!busy} onClick={() => appoint(null)} data-testid="appoint-default-manager">Use default</Btn>
        </div>
      </div>
    </Panel>
  );
}

function CompetitionStep({ clubId, onDone }: any) {
  const { data } = useQuery({ queryKey: ["competitions"], queryFn: async () => (await api.get("/owner/competitions")).data.competitions });
  const [busy, setBusy] = useState<string | null>(null);
  const enter = async (id: string) => {
    setBusy(id);
    try {
      await api.post(`/owner/competitions/${id}/enter`, { club_id: clubId });
      toast.success("Entered. Your fixtures are on the Competition rail.");
      onDone();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(null);
    }
  };
  const skip = async () => {
    await api.post(`/owner/clubs/${clubId}/finish-onboarding`);
    onDone();
  };
  const open = (data || []).filter((c: any) => c.status === "open" && c.host_type === "gtex");
  return (
    <Panel eyebrow="Step 4" title="Enter your first competition" testid="onboarding-competition-step" action={<Btn variant="ghost" onClick={skip} data-testid="onboarding-skip-competition">Skip for now</Btn>}>
      <div className="grid gap-4 md:grid-cols-3">
        {open.map((c: any) => (
          <div key={c.id} className="rounded-sm border border-white/10 bg-slate-950/50 p-5">
            <div className="flex gap-2"><Chip tone="emerald">{c.tier}</Chip><Chip>{c.format}</Chip></div>
            <p className="gx-display mt-3 text-xl font-bold uppercase text-white">{c.name}</p>
            <p className="mt-1 text-xs text-slate-400">{c.description}</p>
            <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
              <div><p className="text-slate-500">Entry</p><Coin amount={c.entry_fee} /></div>
              <div><p className="text-slate-500">Prize pool</p><Coin amount={c.prize_pool} /></div>
            </div>
            <Btn className="mt-5 w-full" disabled={!!busy} onClick={() => enter(c.id)} data-testid={`onboarding-enter-${c.id}`}>{busy === c.id ? "…" : "Enter"}</Btn>
          </div>
        ))}
      </div>
    </Panel>
  );
}

export default function Onboarding() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data, refetch, isLoading } = useQuery({ queryKey: ["onboarding"], queryFn: async () => (await api.get("/owner/onboarding")).data, enabled: !!user });
  if (loading || (user && isLoading)) return <Loading label="Preparing your club" />;
  if (!user) return <Navigate to="/login" replace />;
  const club = (data?.clubs || []).find((c: any) => !["active"].includes(c.stage)) || null;
  if (!club) return <Navigate to="/app" replace />;
  const index = { not_started: 0, squad: 1, manager: 2, competition: 3 }[club.stage as string] ?? 3;
  const next = () => refetch();
  const done = async () => {
    await qc.invalidateQueries({ queryKey: ["cc"] });
    navigate("/app");
  };
  return (
    <div className="gx-pitch-grid min-h-screen bg-[#070B11] px-4 py-10 sm:px-10" data-testid="onboarding-page">
      <div className="mx-auto max-w-[1200px]">
        <p className="gx-eyebrow mb-2">First-club activation</p>
        <h1 className="gx-h2 mb-8">{club.club_name}: from paperwork to matchday</h1>
        <Stepper index={index} />
        {index === 0 && <IdentityStep club={club} onDone={next} />}
        {index === 1 && <SquadStep clubId={club.club_id} onDone={next} />}
        {index === 2 && <ManagerStep clubId={club.club_id} onDone={next} />}
        {index === 3 && <CompetitionStep clubId={club.club_id} onDone={done} />}
        <p className="mt-6 text-xs text-slate-600">Club treasury: {fmt(club.cash)} GTX · Squad {club.squad_size}</p>
      </div>
    </div>
  );
}
