import React, { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AlertTriangle, ArrowRight, Check, Dna, ShoppingCart, Sparkles, Sprout, Trash2 } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { clubCreateErrorMessage } from "./clubLocationCatalog";
import { ClubLocationFields, clubLocationPayload, useClubLocation } from "@/components/gtex/ClubLocationFields";
import { useAuth } from "@/lib/auth";
import { fmt, useClub } from "@/lib/owner";
import { Btn, Chip, Coin, Loading, Panel } from "@/components/gtex/ui";
import { MarketTable } from "@/components/gtex/MarketTable";
import { posShort } from "@/components/gtex/PlayerCard";
import { Cinema3DStage } from "@/components/gtex/Cinema3DStage";

const STEPS = [
  { key: "identity", label: "Club identity" },
  { key: "squad", label: "Sign starting squad" },
  { key: "manager", label: "Appoint manager" },
  { key: "academy", label: "Youth academy" },
  { key: "competition", label: "First competition" },
];

function Stepper({ index }: any) {
  return (
    <ol className="mb-10 grid grid-cols-2 gap-2 md:grid-cols-5" data-testid="onboarding-stepper">
      {STEPS.map((s, i) => (
        <li
          key={s.key}
          className={`rounded-sm border p-3 ${
            i === index
              ? "border-emerald-500/50 bg-emerald-500/10"
              : i < index
              ? "border-white/10 bg-white/[0.02]"
              : "border-white/[0.05]"
          }`}
        >
          <p className="gx-mono text-[10px] text-slate-500">STEP {i + 1}</p>
          <p className="flex items-center gap-2 text-sm font-semibold text-white">
            {i < index && <Check size={14} className="text-emerald-400" />}
            {s.label}
          </p>
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
      <div className="mb-5">
        <Cinema3DStage
          scene="club_takeover"
          compact
          title={`3D Keys to the Club · ${club.club_name}`}
          subtitle="Official Founding Charter & Stadium Center-Circle Walkout"
          badgeText="3D OWNER TAKEOVER"
          clubName={club.club_name}
          subjectName={club.club_name}
          quote="A new era begins under your executive stewardship."
          stats={[
            { label: "Launch Grant", value: "100,000 GTX", accent: "#00E676" },
            { label: "Fan Reserve", value: "1,000 FAN", accent: "#F5B83D" },
          ]}
        />
      </div>
      <p className="max-w-xl text-sm text-slate-300">
        Your club identity is registered. Activating it unlocks a{" "}
        <b className="text-white">100,000 GTEX Coin launch grant</b> in the club treasury (promotional: usable for signings and facilities, not withdrawable) plus 1,000 Fan Coin for gifting.
      </p>
      <Btn className="mt-6" onClick={activate} disabled={busy} data-testid="onboarding-activate-button">
        {busy ? "Activating…" : "Activate club"}
      </Btn>
    </Panel>
  );
}

function SquadStep({ clubId, onDone }: any) {
  const { data: club, refetch } = useClub(clubId);
  const [unsigningId, setUnsigningId] = useState<string | null>(null);
  const [autopicking, setAutopicking] = useState(false);
  const [tactic, setTactic] = useState("tiki_taka");
  const [formation, setFormation] = useState("4-3-3");
  const [budgetCap, setBudgetCap] = useState("85000");
  const [targetSquadSize, setTargetSquadSize] = useState("22");
  const [appointingMgr, setAppointingMgr] = useState<string | null>(null);

  const { data: mgrCatalog } = useQuery({
    queryKey: ["mgr-catalog-onboarding"],
    queryFn: async () => (await api.get("/managers/catalog", { params: { limit: 3 } })).data.items,
  });

  const squad = club?.squad?.filter((p: any) => !p.is_regen) || [];
  const hasGk = squad.some(
    (p: any) => (p.position || "").toLowerCase().includes("goal") || (p.position || "").toLowerCase() === "gk"
  );
  const isMatchEligible = club?.formation?.is_formed ?? (squad.length >= 22 && hasGk);
  const clubCash = Number(club?.economy?.cash_gtex || 0);

  useEffect(() => {
    if (club?.stage && club.stage !== "squad") onDone();
  }, [club?.stage, onDone]);

  const handleTacticChange = (nextTactic: string) => {
    setTactic(nextTactic);
    const map: Record<string, string> = {
      tiki_taka: "4-3-3",
      possession: "4-3-3",
      gegenpress: "4-2-3-1",
      counter: "4-2-3-1",
      direct: "4-4-2",
      low_block: "5-4-1",
    };
    if (map[nextTactic]) setFormation(map[nextTactic]);
  };

  const handlePreAppointManager = async (m: any) => {
    setAppointingMgr(m.manager_id);
    try {
      await api.post(`/owner/clubs/${clubId}/manager`, {
        manager: {
          manager_id: m.manager_id,
          display_name: m.display_name,
          rarity: m.rarity,
          mentality: m.mentality,
          tactics: m.tactics,
          traits: m.traits,
          philosophy_summary: m.philosophy_summary,
        },
      });
      const firstTactic = (m.tactics || [])[0] || "tiki_taka";
      handleTacticChange(firstTactic);
      toast.success(`Appointed ${m.display_name}! Staff will now recruit for ${firstTactic.replace(/_/g, " ")}.`);
      refetch();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setAppointingMgr(null);
    }
  };

  const handleUnsign = async (p: any) => {
    setUnsigningId(p.id);
    try {
      const { data } = await api.post(`/owner/clubs/${clubId}/unsign`, { player_id: p.id || p.player_ref });
      const refund = data?.refunded ?? data?.refund_amount ?? p.value_coin ?? 0;
      toast.success(`Removed ${p.name}. Refunded ${fmt(refund)} GTX to club treasury.`);
      refetch();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setUnsigningId(null);
    }
  };

  const handleAutopick = async () => {
    setAutopicking(true);
    try {
      const { data } = await api.post(`/owner/clubs/${clubId}/autopick`, {
        budget_gtex: Number(budgetCap) > 0 ? Number(budgetCap) : undefined,
        tactic,
        formation,
        target_squad_size: Number(targetSquadSize) || 11,
      });
      const count = data?.signed?.length ?? data?.signed_count ?? 0;
      toast.success(
        data?.message ||
          (count > 0
            ? `Staff auto-picked ${count} player(s) for ${data.formation || formation} (${(data.tactic || tactic).replace(/_/g, " ")})! Remaining cash: ${fmt(data.cash)} GTX`
            : "No affordable players found within current budget.")
      );
      refetch();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setAutopicking(false);
    }
  };

  return (
    <Panel
      eyebrow="Step 2 · Activate by acquiring players"
      title="Sign your starting squad"
      testid="onboarding-squad-step"
      action={
        <div className="flex flex-col items-end gap-1">
          <p className="text-[10px] uppercase tracking-widest text-slate-500">Club cash</p>
          <Coin amount={club?.economy?.cash_gtex} testid="onboarding-cash" />
        </div>
      }
    >
      {/* Club Legacy: Manager / GM / Chief Scout & Tactical Auto-Pick Controls */}
      <div
        className="mb-4 rounded-sm border border-emerald-500/20 bg-slate-950/80 p-4"
        data-testid="onboarding-tactical-recruitment-panel"
      >
        <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-white/10">
          <div>
            <p className="gx-eyebrow text-emerald-400">Club Legacy & Recruitment Committee</p>
            <p className="text-xs text-slate-300">
              Sign your Manager first or set your playing style (e.g. Tiki-Taka 4-3-3) & budget—your Manager, GM, and Chief Scout will auto-pick matching players.
            </p>
          </div>
          <Chip tone="cyan">
            Active Coach: {club?.manager?.name || "Interim Staff Committee"} · Fan Coin Upfront Staff Policy
          </Chip>
        </div>

        {(mgrCatalog || []).length > 0 && (
          <div className="mt-3 grid gap-2 md:grid-cols-3">
            {(mgrCatalog || []).map((m: any) => (
              <div
                key={m.manager_id}
                className="flex items-center justify-between rounded border border-white/10 bg-slate-900/60 px-3 py-2 text-xs"
              >
                <div>
                  <p className="font-semibold text-white">{m.display_name}</p>
                  <p className="text-[11px] text-slate-400">
                    {m.mentality} · {(m.tactics || []).slice(0, 2).join(", ").replace(/_/g, " ")}
                  </p>
                </div>
                <Btn
                  variant="ghost"
                  disabled={!!appointingMgr}
                  onClick={() => handlePreAppointManager(m)}
                  data-testid={`pre-appoint-manager-${m.manager_id}`}
                >
                  {appointingMgr === m.manager_id ? "…" : "Hire First"}
                </Btn>
              </div>
            ))}
          </div>
        )}

        <div className="mt-3 grid gap-3 sm:grid-cols-4">
          <label className="text-xs text-slate-400">
            Playing Style / Mentality
            <select
              value={tactic}
              onChange={(e) => handleTacticChange(e.target.value)}
              data-testid="onboarding-autopick-tactic"
              className="mt-1 w-full rounded border border-white/15 bg-slate-900 px-2.5 py-1.5 text-xs text-white"
            >
              <option value="tiki_taka">Tiki-Taka (4-3-3 Possession)</option>
              <option value="gegenpress">Gegenpress (4-2-3-1 High Press)</option>
              <option value="possession">Control Possession (4-3-3)</option>
              <option value="counter">Fast Counter-Attack (4-2-3-1)</option>
              <option value="direct">Direct Vertical (4-4-2)</option>
              <option value="low_block">Low-Block Fortress (5-4-1)</option>
            </select>
          </label>
          <label className="text-xs text-slate-400">
            Preferred Formation
            <select
              value={formation}
              onChange={(e) => setFormation(e.target.value)}
              data-testid="onboarding-autopick-formation"
              className="mt-1 w-full rounded border border-white/15 bg-slate-900 px-2.5 py-1.5 text-xs text-white"
            >
              <option value="4-3-3">4-3-3</option>
              <option value="4-2-3-1">4-2-3-1</option>
              <option value="4-4-2">4-4-2</option>
              <option value="3-5-2">3-5-2</option>
              <option value="3-4-3">3-4-3</option>
              <option value="5-4-1">5-4-1</option>
            </select>
          </label>
          <label className="text-xs text-slate-400">
            Recruitment Budget Cap (GTX)
            <input
              type="number"
              value={budgetCap}
              onChange={(e) => setBudgetCap(e.target.value)}
              data-testid="onboarding-autopick-budget"
              className="mt-1 w-full rounded border border-white/15 bg-slate-900 px-2.5 py-1.5 text-xs text-white"
            />
          </label>
          <label className="text-xs text-slate-400">
            Target Squad Size
            <input
              type="number"
              min={22}
              max={25}
              value={targetSquadSize}
              onChange={(e) => setTargetSquadSize(e.target.value)}
              data-testid="onboarding-autopick-size"
              className="mt-1 w-full rounded border border-white/15 bg-slate-900 px-2.5 py-1.5 text-xs text-white"
            />
          </label>
        </div>
      </div>

      {/* Top Status & Auto-pick Toolbar */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-sm border border-white/10 bg-slate-950/60 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <Chip tone={isMatchEligible ? "emerald" : "gold"} testid="onboarding-squad-count">
            {club?.formation?.progress_label || `${squad.length}/22 players signed`}
          </Chip>
          <Chip tone={hasGk ? "emerald" : "red"}>
            {hasGk ? "✓ Goalkeeper signed" : "⚠ Needs a goalkeeper"}
          </Chip>
          <span className="text-xs text-slate-400">
            A club becomes match-eligible with 22 players (First Team, Reserves, Academy) including a goalkeeper.
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Btn
            variant={isMatchEligible ? "ghost" : "primary"}
            disabled={autopicking || isMatchEligible}
            onClick={handleAutopick}
            className="flex items-center gap-1.5"
            data-testid="onboarding-autopick-button"
            title="Automatically sign affordable players to complete your squad within available funds"
          >
            <Sparkles size={14} className={autopicking ? "animate-spin" : "text-amber-300"} />
            {autopicking ? "Auto-picking…" : isMatchEligible ? "Squad Complete ✓" : "⚡ Auto-Pick within Budget"}
          </Btn>
        </div>
      </div>

      {/* Low cash warning if stuck */}
      {!isMatchEligible && clubCash < 800 && squad.length > 0 && (
        <div className="mb-6 flex items-start gap-3 rounded border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
          <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-400" />
          <div>
            <p className="font-semibold text-amber-300">Low Treasury Balance ({fmt(clubCash)} GTX remaining)</p>
            <p className="mt-0.5 text-slate-300">
              You need {11 - squad.length} more player(s){!hasGk ? " including a goalkeeper" : ""}, but minimum transfer fees start around 800 GTX.
              Remove any signed player below to receive a full refund, or use <b>Auto-Pick</b> to sign affordable talent.
            </p>
          </div>
        </div>
      )}

      {/* Squad Basket */}
      <div className="mb-8 rounded-sm border border-white/10 bg-slate-950/40 p-4" data-testid="squad-basket">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShoppingCart size={16} className="text-emerald-400" />
            <h3 className="text-sm font-semibold uppercase tracking-wider text-white">
              Player Basket <span className="text-xs font-normal text-slate-400">({squad.length} / 11 signed)</span>
            </h3>
          </div>
          {squad.length > 0 && (
            <span className="text-xs text-slate-400">
              Total Squad Value:{" "}
              <b className="text-emerald-300">
                {fmt(squad.reduce((sum: number, p: any) => sum + Number(p.value_coin || 0), 0))} GTX
              </b>
            </span>
          )}
        </div>

        {squad.length === 0 ? (
          <div className="rounded border border-dashed border-white/10 p-6 text-center text-xs text-slate-500">
            Your player basket is empty. Browse the transfer market below or click{" "}
            <b className="text-slate-300">"⚡ Auto-Pick within Budget"</b> above to assemble your starting 11 automatically.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
            {squad.map((p: any) => {
              const isGk =
                (p.position || "").toLowerCase().includes("goal") || (p.position || "").toLowerCase() === "gk";
              const posBadge = isGk
                ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                : (p.position || "").toLowerCase().includes("def")
                ? "bg-blue-500/20 text-blue-300 border-blue-500/40"
                : (p.position || "").toLowerCase().includes("mid")
                ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                : "bg-rose-500/20 text-rose-300 border-rose-500/40";

              const isRemoving = unsigningId === p.id;

              return (
                <div
                  key={p.id}
                  data-testid={`basket-player-${p.id}`}
                  className="group relative flex flex-col justify-between rounded border border-white/10 bg-slate-900/60 p-3 transition-colors hover:border-white/20"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`inline-block rounded border px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${posBadge}`}
                        >
                          {posShort(p.position)}
                        </span>
                        <span className="text-[10px] font-bold text-slate-400">{p.rating} OVR</span>
                      </div>
                      <p className="mt-1.5 truncate text-sm font-semibold text-white" title={p.name}>
                        {p.name}
                      </p>
                      <p className="gx-mono mt-0.5 text-xs text-emerald-300">
                        {fmt(p.value_coin)} GTX
                      </p>
                    </div>

                    <button
                      type="button"
                      disabled={isRemoving}
                      onClick={() => handleUnsign(p)}
                      title={`Remove ${p.name} and refund ~${fmt(p.value_coin)} GTX`}
                      data-testid={`remove-player-${p.id}`}
                      className="flex h-7 w-7 shrink-0 items-center justify-center rounded border border-rose-500/30 bg-rose-500/10 text-rose-300 transition-colors hover:bg-rose-500 hover:text-white disabled:opacity-50"
                    >
                      {isRemoving ? (
                        <span className="animate-spin text-xs">…</span>
                      ) : (
                        <Trash2 size={13} />
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Transfer Market Explorer */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="gx-eyebrow text-slate-400">Transfer Market Explorer</p>
          <span className="text-xs text-slate-500">Sign directly from the market below</span>
        </div>
        <MarketTable
          clubId={clubId}
          signedRefs={squad.map((p: any) => p.player_ref)}
          onSigned={() => refetch()}
          clubCash={clubCash}
        />
      </div>
    </Panel>
  );
}

function ManagerStep({ clubId, onDone }: any) {
  const { data } = useQuery({
    queryKey: ["mgr-catalog"],
    queryFn: async () => (await api.get("/managers/catalog", { params: { limit: 3 } })).data.items,
  });
  const [busy, setBusy] = useState<string | null>(null);
  const appoint = async (m: any | null) => {
    setBusy(m?.manager_id || "default");
    try {
      await api.post(`/owner/clubs/${clubId}/manager`, {
        manager: m
          ? {
              manager_id: m.manager_id,
              display_name: m.display_name,
              rarity: m.rarity,
              mentality: m.mentality,
              tactics: m.tactics,
              traits: m.traits,
              philosophy_summary: m.philosophy_summary,
            }
          : null,
      });
      onDone();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(null);
    }
  };
  return (
    <Panel eyebrow="Step 3 · Hire your football brain" title="Appoint a manager" testid="onboarding-manager-step">
      <p className="mb-6 text-sm text-slate-400">
        Managers carry the realism: they ask for budget, request players, react to facilities, and shape regen growth. First appointment is covered by the launch package.
      </p>
      <div className="grid gap-4 md:grid-cols-4">
        {(data || []).map((m: any) => (
          <div key={m.manager_id} className="flex flex-col rounded-sm border border-white/10 bg-slate-950/50 p-4">
            <Chip tone="cyan">{m.rarity}</Chip>
            <p className="gx-display mt-3 text-xl font-bold uppercase text-white">{m.display_name}</p>
            <p className="text-xs capitalize text-slate-400">
              {m.mentality} · {(m.tactics || []).slice(0, 2).join(", ").replace(/_/g, " ")}
            </p>
            <p className="mt-3 flex-1 text-xs text-slate-500">{m.philosophy_summary}</p>
            <Btn
              className="mt-4"
              variant="secondary"
              disabled={!!busy}
              onClick={() => appoint(m)}
              data-testid={`appoint-manager-${m.manager_id}`}
            >
              {busy === m.manager_id ? "…" : "Appoint"}
            </Btn>
          </div>
        ))}
        <div className="flex flex-col rounded-sm border border-dashed border-white/10 p-4">
          <Chip>Default</Chip>
          <p className="gx-display mt-3 text-xl font-bold uppercase text-white">GTEX staff coach</p>
          <p className="mt-3 flex-1 text-xs text-slate-500">
            A steady default manager. You can hire a named manager later from Manager & Squad.
          </p>
          <Btn
            className="mt-4"
            variant="ghost"
            disabled={!!busy}
            onClick={() => appoint(null)}
            data-testid="appoint-default-manager"
          >
            Use default
          </Btn>
        </div>
      </div>
    </Panel>
  );
}

function AcademyStep({ clubId, onDone }: { clubId: string; onDone: () => void }) {
  const { data: club, refetch } = useClub(clubId);
  const [busyIntake, setBusyIntake] = useState(false);

  const regens = (club?.squad || []).filter(
    (p: any) => p.is_regen || p.squad_status === "academy" || p.acquired_via === "academy"
  );

  const handleManualIntake = async () => {
    setBusyIntake(true);
    try {
      await api.post(`/owner/clubs/${clubId}/academy/intake`);
      toast.success("Genesis academy intake scouted! New wonderkids signed.");
      refetch();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyIntake(false);
    }
  };

  const hoydName = club?.staff?.head_of_youth_development?.name || "Marcus Vance";
  const hoydRating = club?.staff?.head_of_youth_development?.rating || 78;

  return (
    <Panel
      eyebrow="Step 4 · Youth Academy & Genesis Wonderkids"
      title="Inaugural Academy Intake"
      testid="onboarding-academy-step"
      action={
        <Btn onClick={onDone} className="flex items-center gap-2" data-testid="onboarding-proceed-competition">
          <span>Proceed to First Competition</span>
          <ArrowRight size={14} />
        </Btn>
      }
    >
      <div className="mb-6">
        <Cinema3DStage
          scene="academy_upgrade"
          compact
          title={`3D Youth Academy Campus · Genesis Intake`}
          subtitle={`${club?.club_name || "GTEX Club"} · Inaugural Class of Homegrown Wonderkids`}
          badgeText="3D GENESIS INTAKE"
          clubName={club?.club_name}
          facilityLevel={1}
          stats={[
            { label: "Genesis Regens", value: `${regens.length} Prospects`, accent: "#00E676" },
            { label: "Campus Tier", value: "Level 1 Academy", accent: "#38BDF8" },
            { label: "Ceilings", value: "85–95 POT", accent: "#F5B83D" },
          ]}
        />
      </div>

      {/* Head of Youth Development Briefing */}
      <div className="mb-6 rounded-sm border border-purple-500/20 bg-purple-950/20 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-purple-500/20 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
              <Sprout size={18} />
            </div>
            <div>
              <p className="text-xs font-bold text-white uppercase tracking-wider">
                {hoydName} <span className="text-[11px] font-normal text-purple-300">· Head of Youth Development (Rating: {hoydRating})</span>
              </p>
              <p className="text-[11px] text-slate-400">Youth Scouting & Development Briefing</p>
            </div>
          </div>
          <Chip tone="cyan">HOYD Autonomy Active</Chip>
        </div>
        <p className="mt-3 text-xs leading-relaxed text-slate-300">
          "Welcome to the training grounds, Boss. While the first-team squad was being finalized, our academy scouts canvassed local regional trials and secured our inaugural class of youth wonderkids. These regens are training on Pitch 3 and possess elite development ceilings. With proper match exposure, coaching, and facility upgrades, they will form the backbone of your dynasty."
        </p>
      </div>

      {/* Genesis Wonderkids Grid */}
      <div className="mb-6 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="gx-eyebrow text-emerald-400">Inaugural Academy Class</p>
            <p className="text-xs text-slate-400">High-potential homegrown talents signed directly to your youth roster</p>
          </div>
          {regens.length === 0 && (
            <Btn
              variant="secondary"
              disabled={busyIntake}
              onClick={handleManualIntake}
              className="flex items-center gap-1.5 text-xs"
              data-testid="onboarding-scout-genesis-intake"
            >
              <Sparkles size={13} className="text-amber-300" />
              <span>{busyIntake ? "Scouting Intake…" : "Scout Genesis Intake"}</span>
            </Btn>
          )}
        </div>

        {regens.length === 0 ? (
          <div className="rounded border border-dashed border-white/10 p-6 text-center text-xs text-slate-400">
            <p>Your genesis academy class is preparing for their medicals.</p>
            <Btn
              className="mt-3"
              disabled={busyIntake}
              onClick={handleManualIntake}
            >
              {busyIntake ? "Generating Wonderkids…" : "Trigger Inaugural Intake"}
            </Btn>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3" data-testid="onboarding-genesis-regens">
            {regens.map((p: any) => {
              const pers = p.personality || p.personality_json || {};
              const archetype = p.archetype || pers.archetype || "Ambitious Prodigy";
              const mood = p.mood_state || pers.mood || "Thriving";
              const monologue = p.inner_monologue || pers.inner_monologue || `Grinding daily with the academy coaches. When my call-up comes, I'll be 100% ready.`;
              const ceiling = Math.max(0, (p.potential || 85) - (p.rating || 60));

              return (
                <div
                  key={p.id || p.name}
                  className="flex flex-col justify-between rounded-xl border border-white/10 bg-slate-900/60 p-4 shadow-lg hover:border-emerald-500/30 transition-colors"
                  data-testid={`genesis-regen-${p.id}`}
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 border-b border-white/10 pb-3">
                      <div>
                        <span className="rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 text-[9px] font-black uppercase">
                          {archetype}
                        </span>
                        <h4 className="mt-1 text-sm font-bold text-white">{p.name}</h4>
                        <p className="text-[11px] text-slate-400">Age {p.age || 17} · {posShort(p.position)}</p>
                      </div>
                      <div className="text-right">
                        <span className="gx-mono text-lg font-black text-white">{p.rating}</span>
                        <span className="text-[10px] text-slate-500"> OVR</span>
                        <p className="gx-mono text-[11px] font-bold text-amber-300">POT {p.potential || 88}</p>
                      </div>
                    </div>

                    <div className="mt-3 space-y-2">
                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <span>Ceiling</span>
                        <span className="gx-mono text-emerald-300 font-bold">+{ceiling} Growth</span>
                      </div>
                      <div className="h-1.5 rounded-sm bg-white/5">
                        <div
                          className="h-1.5 rounded-sm bg-gradient-to-r from-emerald-500 to-amber-400"
                          style={{ width: `${Math.min(100, ((p.rating || 60) / Math.max(1, p.potential || 90)) * 100)}%` }}
                        />
                      </div>
                      <p className="text-[11px] text-slate-400">
                        Mood: <b className="text-slate-200">{mood}</b>
                      </p>
                      <div className="rounded border border-white/5 bg-black/40 p-2 text-[11px] italic text-slate-300">
                        "{monologue}"
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-[10px] text-slate-400">
                    <span className="text-purple-300">HOYD Monitored</span>
                    <span className="gx-mono text-emerald-300">{fmt(p.value_coin || 3500)} GTX</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Build-A-Son Legacy Program Educational Banner */}
      <div
        className="mb-6 rounded-xl border border-amber-500/30 bg-gradient-to-r from-amber-500/10 via-amber-950/20 to-black p-4"
        data-testid="onboarding-build-a-son-banner"
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/40">
              <Dna size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <p className="text-xs font-black uppercase tracking-wider text-amber-300">
                  Build-A-Son Legacy Program
                </p>
                <Chip tone="gold">Dynasty Feature</Chip>
              </div>
              <p className="mt-1 text-xs text-slate-300 leading-relaxed max-w-2xl">
                As your senior players establish legendary status, you can pass on their genetic DNA bloodlines, mental composure, and fan devotion to custom dynasty scions right here in your Academy Command (<b>/app/academy</b>).
              </p>
            </div>
          </div>
          <div className="shrink-0">
            <div className="text-right">
              <p className="text-[10px] text-slate-500 uppercase">Bloodlines Engine</p>
              <p className="text-xs font-bold text-amber-300">20/20 Loyalty Guarantee</p>
            </div>
          </div>
        </div>
      </div>

      {/* Primary Proceed Action */}
      <div className="flex items-center justify-between border-t border-white/10 pt-4">
        <p className="text-xs text-slate-400">
          Your wonderkids will continue developing as competitive matchdays and training cycles progress.
        </p>
        <Btn onClick={onDone} className="flex items-center gap-2" data-testid="onboarding-proceed-competition-bottom">
          <span>Proceed to First Competition</span>
          <ArrowRight size={14} />
        </Btn>
      </div>
    </Panel>
  );
}

function CompetitionStep({ clubId, onDone }: any) {
  const { data } = useQuery({
    queryKey: ["competitions"],
    queryFn: async () => (await api.get("/owner/competitions")).data.competitions,
  });
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
    <Panel
      eyebrow="Step 4"
      title="Enter your first competition"
      testid="onboarding-competition-step"
      action={
        <Btn variant="ghost" onClick={skip} data-testid="onboarding-skip-competition">
          Skip for now
        </Btn>
      }
    >
      <div className="grid gap-4 md:grid-cols-3">
        {open.map((c: any) => (
          <div key={c.id} className="rounded-sm border border-white/10 bg-slate-950/50 p-5">
            <div className="flex gap-2">
              <Chip tone="emerald">{c.tier}</Chip>
              <Chip>{c.format}</Chip>
            </div>
            <p className="gx-display mt-3 text-xl font-bold uppercase text-white">{c.name}</p>
            <p className="mt-1 text-xs text-slate-400">{c.description}</p>
            <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
              <div>
                <p className="text-slate-500">Entry</p>
                <Coin amount={c.entry_fee} />
              </div>
              <div>
                <p className="text-slate-500">Prize pool</p>
                <Coin amount={c.prize_pool} />
              </div>
            </div>
            <Btn
              className="mt-5 w-full"
              disabled={!!busy}
              onClick={() => enter(c.id)}
              data-testid={`onboarding-enter-${c.id}`}
            >
              {busy === c.id ? "…" : "Enter"}
            </Btn>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function CreateFirstClub({ onDone, onCancel }: any) {
  const [name, setName] = useState("");
  const loc = useClubLocation();
  const [busy, setBusy] = useState(false);
  const location = loc.validation;
  const clubName = name.trim();
  const create = async () => {
    if (clubName.length < 3) {
      toast.error("Enter a club name with at least 3 characters.");
      return;
    }
    const validatedLocation = loc.validation;
    if ("error" in validatedLocation) {
      toast.error(validatedLocation.error);
      return;
    }
    setBusy(true);
    try {
      const slug = `${clubName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now().toString(36).slice(-4)}`;
      await api.post("/clubs", {
        club_name: clubName,
        slug,
        short_name: clubName.slice(0, 12),
        primary_color: "#0F766E",
        secondary_color: "#F8FAFC",
        accent_color: "#F59E0B",
        ...clubLocationPayload(validatedLocation),
        club_type: "community",
      });
      onDone();
    } catch (e) {
      toast.error(clubCreateErrorMessage(e, errMsg));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div
      className="gx-pitch-grid flex min-h-screen items-center justify-center bg-[#070B11] px-4"
      data-testid="create-first-club"
    >
      <Panel eyebrow="First-club activation" title="Name your club" className="w-full max-w-lg">
        <input
          data-testid="first-club-name-input"
          aria-label="Club name"
          className="gx-input"
          placeholder="Club name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <div className="mt-3">
          <ClubLocationFields state={loc} testIdPrefix="first-club" disabled={busy} />
        </div>
        <Btn
          className="mt-4 w-full"
          disabled={clubName.length < 3 || !location.valid || busy}
          onClick={create}
          data-testid="first-club-create-button"
        >
          Create club
        </Btn>
        <Btn
          className="mt-2 w-full"
          variant="ghost"
          disabled={busy}
          onClick={onCancel}
          data-testid="skip-club-creation-button"
        >
          Not now — explore GTEX first
        </Btn>
      </Panel>
    </div>
  );
}

export default function Onboarding() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data, refetch, isLoading } = useQuery({
    queryKey: ["onboarding"],
    queryFn: async () => (await api.get("/owner/onboarding")).data,
    enabled: !!user,
  });
  if (loading || (user && isLoading)) return <Loading label="Preparing your club" />;
  if (!user) return <Navigate to="/login" replace />;
  const club = (data?.clubs || []).find((c: any) => !["active"].includes(c.stage)) || null;
  if (!club && !(data?.clubs || []).length) {
    return <CreateFirstClub onDone={() => refetch()} onCancel={() => navigate("/app")} />;
  }
  if (!club) return <Navigate to="/app" replace />;
  const [academyAcknowledged, setAcademyAcknowledged] = useState(() =>
    Boolean(club?.club_id && localStorage.getItem(`gtex.onboarding.academy.${club.club_id}`) === "acknowledged")
  );

  useEffect(() => {
    if (club?.club_id) {
      setAcademyAcknowledged(
        localStorage.getItem(`gtex.onboarding.academy.${club.club_id}`) === "acknowledged"
      );
    }
  }, [club?.club_id]);

  let index = 0;
  if (club.stage === "squad") {
    index = 1;
  } else if (club.stage === "manager") {
    index = 2;
  } else if (club.stage === "competition") {
    index = academyAcknowledged ? 4 : 3;
  } else {
    index = 4;
  }
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
        {index === 3 && (
          <AcademyStep
            clubId={club.club_id}
            onDone={() => {
              localStorage.setItem(`gtex.onboarding.academy.${club.club_id}`, "acknowledged");
              setAcademyAcknowledged(true);
            }}
          />
        )}
        {index === 4 && <CompetitionStep clubId={club.club_id} onDone={done} />}
        <p className="mt-6 text-xs text-slate-600">
          Club treasury: {fmt(club.cash)} GTX · Squad {club.squad_size}
        </p>
      </div>
    </div>
  );
}
